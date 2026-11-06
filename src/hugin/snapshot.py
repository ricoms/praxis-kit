"""Repository research snapshot: collect a GitHub repo's PRs, reviews, CI runs,
releases, deployments, issues and branches into a role-mapped edge list, then
compute flow, review, CI, DORA and hygiene signals from it.

  hugin snapshot collect --repo OWNER/NAME --since ISO --until ISO --roles roles.json
                         --out DIR [--raw DIR] [--board OWNER/N --capacity DAYS [--target TITLE]]
                         [--checkout DIR]
  hugin snapshot report DIR [--json]

`collect` writes DIR/window.json, nodes.jsonl, edges.jsonl and metrics.json, and
prints the Markdown reading. Raw API responses, which hold logins and titles, go
to --raw (default ~/.cache/repo-snapshots/OWNER-NAME/UNTIL) and stay local.
"""
import argparse
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from hugin import velocity

Raw = dict[str, Any]
Node = dict[str, Any]
Edge = dict[str, Any]
Metrics = dict[str, Any]

FAILED_DEPLOY = {"error", "failure"}
KIND_LABELS = {"bug", "enhancement", "question"}
STALE_PR_DAYS = 14
LARGE_PR_LINES = 1000
RUNS_PAGE_CAP = 1000
MOVE_WINDOW_S = 60
CHECK_PATHSPECS = (".github/workflows", "semgrep", ":(glob)**/*_test.*", ":(glob)**/test_*", ":(glob)**/*_spec.*",
                   ":(glob)**/*.test.*", ":(glob)**/*.spec.*")
TEXT_PATTERNS = {
    "reverts_commit": re.compile(r"This reverts commit ([0-9a-f]{7,40})"),
    "reverts_pr": re.compile(r"\bReverts (?:([\w.-]+/[\w.-]+))?#(\d+)"),
    "review_of": re.compile(r"\breview of #(\d+)", re.I),
    "adr": re.compile(r"\bADR[- ]?0*(\d{1,4})\b|\bdecisions/0*(\d{1,4})-", re.I),
    "decide": re.compile(r"\b(decide[sd]?|decisions?|accept(?:s|ed)?|approve[sd]?|ratif(?:y|ies|ied))\b", re.I),
    "ref": re.compile(r"(?<![\w/#])#(\d+)\b"),
}


# ── GitHub access ──────────────────────────────────────────────


def gh(*args: str, attempts: int = 4) -> str:
    for attempt in range(attempts):
        proc = subprocess.run(["gh", *args], capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout
        if attempt + 1 == attempts or not any(code in proc.stderr for code in ("502", "503", "504", "timeout")):
            raise SystemExit(f"gh {' '.join(args[:3])}: {proc.stderr.strip()}")
        time.sleep(2 ** attempt)
    raise AssertionError("gh: attempts must be at least 1")


def rest(path: str) -> list[Any]:
    """`gh api --paginate --slurp` always returns a list: list endpoints are flattened, anything else is the
    list of pages."""
    out = gh("api", "--paginate", "--slurp", path)
    pages = json.loads(out)
    if pages and isinstance(pages[0], list):
        return [x for page in pages for x in page]
    return cast(list[Any], pages)


PR_QUERY = """query($owner:String!,$name:String!,$endCursor:String){repository(owner:$owner,name:$name){
pullRequests(first:40,after:$endCursor,orderBy:{field:CREATED_AT,direction:ASC}){
pageInfo{hasNextPage endCursor}
nodes{number title body author{__typename login} createdAt mergedAt closedAt state isDraft additions deletions
baseRefName headRefName mergeCommit{oid}
reviews(first:100){totalCount nodes{author{__typename login} state submittedAt}}
closingIssuesReferences(first:20){nodes{number repository{nameWithOwner}}}}}}}"""

ISSUE_QUERY = """query($owner:String!,$name:String!,$endCursor:String){repository(owner:$owner,name:$name){
issues(first:50,after:$endCursor,orderBy:{field:CREATED_AT,direction:ASC}){
pageInfo{hasNextPage endCursor}
nodes{number title body author{__typename login} createdAt closedAt state stateReason
labels(first:30){nodes{name}} assignees(first:10){nodes{__typename login}} milestone{title dueOn}
timelineItems(first:50,itemTypes:[MILESTONED_EVENT,DEMILESTONED_EVENT]){totalCount nodes{__typename
... on MilestonedEvent{milestoneTitle createdAt} ... on DemilestonedEvent{milestoneTitle createdAt}}}}}}}"""


def graphql_all(query: str, repo: str, key: str) -> list[Node]:
    owner, name = repo.split("/")
    out = gh("api", "graphql", "--paginate", "--slurp", "-f", f"query={query}", "-F", f"owner={owner}", "-F", f"name={name}")
    return [n for page in json.loads(out) for n in page["data"]["repository"][key]["nodes"]]


def fetch_runs(repo: str, first_day: dt.date, last_day: dt.date, coverage: defaultdict[str, list[Any]]) -> list[Node]:
    runs, day = [], first_day
    while day <= last_day:
        pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/actions/runs?created={day.isoformat()}&per_page=100"))
        total = pages[0]["total_count"] if pages else 0
        if total > RUNS_PAGE_CAP:
            coverage["run_days_capped"].append(day.isoformat())
        runs += [r for page in pages for r in page["workflow_runs"]]
        day += dt.timedelta(days=1)
    return runs


def fetch(repo: str, since: dt.datetime, until: dt.datetime) -> tuple[Raw, dict[str, list[Any]]]:
    coverage: defaultdict[str, list[Any]] = defaultdict(list)
    meta = json.loads(gh("api", f"repos/{repo}"))
    rulesets = [json.loads(gh("api", f"repos/{repo}/rulesets/{r['id']}")) for r in rest(f"repos/{repo}/rulesets")]
    prs = graphql_all(PR_QUERY, repo, "pullRequests")
    issues = graphql_all(ISSUE_QUERY, repo, "issues")
    first_day = parse(meta["created_at"]).date()
    runs = fetch_runs(repo, first_day, (until - dt.timedelta(microseconds=1)).date(), coverage)
    releases = rest(f"repos/{repo}/releases?per_page=100")
    for rel in releases:
        rel["sha"] = json.loads(gh("api", f"repos/{repo}/commits/{rel['tag_name']}"))["sha"]
    deployments = rest(f"repos/{repo}/deployments?per_page=100")
    for d in deployments:
        d["statuses"] = rest(f"repos/{repo}/deployments/{d['id']}/statuses?per_page=100")
    previous: dict[str, str] = {}
    for d in sorted(deployments, key=lambda d: d["created_at"]):
        base = previous.get(d["environment"])
        previous[d["environment"]] = d["sha"]
        if base and base != d["sha"]:
            cmp = json.loads(gh("api", f"repos/{repo}/compare/{base}...{d['sha']}"))
            d["contains"] = [{"sha": c["sha"], "date": c["commit"]["committer"]["date"], "message": c["commit"]["message"]}
                             for c in cmp["commits"]]
            if cmp["total_commits"] > len(cmp["commits"]):
                coverage["compare_truncated"].append(d["id"])
        else:
            d["contains"] = []
    branches = rest(f"repos/{repo}/branches?per_page=100")
    milestones = rest(f"repos/{repo}/milestones?state=all&per_page=100")
    return {"repo": meta, "rulesets": rulesets, "prs": prs, "issues": issues, "runs": runs, "releases": releases,
            "deployments": deployments, "branches": branches, "milestones": milestones}, dict(coverage)


def fetch_board(board: str) -> Raw:
    owner, number = board.rsplit("/", 1)
    items = json.loads(gh("project", "item-list", number, "--owner", owner, "--limit", "5000", "--format", "json"))
    return {**items, "source": board, "fetched_on": dt.date.today().isoformat()}


# ── Edge list ──────────────────────────────────────────────────


def parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


class Roles:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping: dict[str, str] = mapping
        self.unmapped: set[str] = set()

    def __call__(self, actor: dict[str, Any] | None) -> str:
        actor = actor or {}
        login = actor.get("login")
        if not login:
            return "ghost"
        if login in self.mapping:
            return self.mapping[login]
        if actor.get("__typename") == "Bot":
            return "bot"
        self.unmapped.add(login)
        return "unmapped"


def revert_merges(git: Callable[..., str], commits: list[dict[str, str]], ref: str) -> dict[str, str]:
    """Each revert commit that reached `ref` through a merge, mapped to the first-parent merge that brought it in."""
    mainline = git("rev-list", "--first-parent", "--reverse", ref).split()
    on_mainline = set(mainline)
    out: dict[str, str] = {}
    for c in commits:
        if c["sha"] in on_mainline or not TEXT_PATTERNS["reverts_commit"].search(c["message"]):
            continue
        # --first-parent would prune the merged branch's own descendants of the commit, so walk every path and take
        # the oldest mainline commit on it: the merge that brought the commit in.
        descendants = set(git("rev-list", "--ancestry-path", f"{c['sha']}..{ref}").split())
        merge = next((sha for sha in mainline if sha in descendants), None)
        if merge:
            out[c["sha"]] = merge
    return out


def read_checkout(checkout: Path, default_branch: str) -> tuple[list[dict[str, str]], dict[str, str], dict[str, list[int]]]:
    """Commit messages on the default branch, the merge that brought in each revert commit, and the check files
    (workflows, rules, tests) that cite an ADR."""
    git: Callable[..., str] = lambda *a: subprocess.run(["git", "-C", str(checkout), *a], capture_output=True, text=True, check=True).stdout
    git("fetch", "--quiet", "origin", default_branch)
    log = git("log", f"origin/{default_branch}", "--format=%H%x1f%cI%x1f%B%x1e")
    commits = [dict(zip(("sha", "date", "message"), rec.strip("\n").split("\x1f", 2))) for rec in log.split("\x1e") if rec.strip()]
    grep = subprocess.run(["git", "-C", str(checkout), "grep", "-I", "-o", "-i", "-E", r"ADR[- ]?[0-9]{1,4}|decisions/[0-9]{1,4}-",
                           f"origin/{default_branch}", "--", *CHECK_PATHSPECS], capture_output=True, text=True)
    if grep.returncode not in (0, 1):
        raise SystemExit(f"git grep: {grep.stderr.strip()}")
    checks: defaultdict[str, set[int]] = defaultdict(set)
    for line in grep.stdout.splitlines():
        _, path, match = line.split(":", 2)
        checks[path].update(adr_numbers(match))
    return commits, revert_merges(git, commits, f"origin/{default_branch}"), {path: sorted(n) for path, n in checks.items()}


def adr_numbers(text: str | None) -> set[int]:
    return {int(a or b) for a, b in TEXT_PATTERNS["adr"].findall(text or "")}


def text_edges(raw: Raw, nodes: dict[str, Node]) -> list[Edge]:
    """Links read from PR and issue text and commit messages. Each edge names the field and pattern that matched,
    never the text, and points only at nodes that exist."""
    edges: list[Edge] = []
    repo = raw["repo"]["full_name"].lower()
    commit_pr = {n["merge_sha"]: f"pr:{n['number']}" for n in nodes.values() if n["kind"] == "pr" and n.get("merge_sha")}
    messages = {c["sha"]: c for c in raw.get("commits") or [c for d in raw["deployments"] for c in d["contains"]]}
    for c in messages.values():
        nodes.setdefault(f"commit:{c['sha']}", {"id": f"commit:{c['sha']}", "kind": "commit", "sha": c["sha"], "date": c["date"]})
    shas = sorted(n["sha"] for n in nodes.values() if n["kind"] == "commit")

    def add(src: str, dst: str, typ: str, field: str, pattern: str) -> None:
        if dst in nodes and dst != src:
            edges.append({"src": src, "dst": dst, "type": typ, "source": "text", "evidence": f"{field}:{pattern}", "attrs": {}})

    def number_node(n: str) -> str:
        return f"pr:{n}" if f"pr:{n}" in nodes else f"issue:{n}"

    def scan(src: str, field: str, text: str | None, revert_src: str | None = None) -> None:
        text = text or ""
        revert_src = revert_src or src
        reverted = {n for owner, n in TEXT_PATTERNS["reverts_pr"].findall(text) if owner.lower() in ("", repo)}
        for n in reverted:
            add(revert_src, f"pr:{n}", "reverts", field, "reverts_pr")
        for short in TEXT_PATTERNS["reverts_commit"].findall(text):
            full = next((sha for sha in shas if sha.startswith(short)), None)
            if full:
                add(revert_src, commit_pr.get(full, f"commit:{full}"), "reverts", field, "reverts_commit")
        reviewed = set(TEXT_PATTERNS["review_of"].findall(text))
        for n in reviewed:
            add(src, f"pr:{n}", "review_of", field, "review_of")
        decides = field == "issue.title" and TEXT_PATTERNS["decide"].search(text)
        for n in adr_numbers(text):
            nodes.setdefault(f"adr:{n}", {"id": f"adr:{n}", "kind": "adr", "number": n})
            add(src, f"adr:{n}", "decides" if decides else "cites", field, "decide" if decides else "adr")
        for n in set(TEXT_PATTERNS["ref"].findall(text)) - reviewed - reverted:
            add(src, number_node(n), "references", field, "ref")

    for p in raw["prs"]:
        scan(f"pr:{p['number']}", "pr.title", p["title"])
        scan(f"pr:{p['number']}", "pr.body", p["body"])
    for i in raw["issues"]:
        scan(f"issue:{i['number']}", "issue.title", i["title"])
        scan(f"issue:{i['number']}", "issue.body", i["body"])
    merged_by = raw.get("revert_merges") or {}
    for c in messages.values():
        src = commit_pr.get(c["sha"], f"commit:{c['sha']}")
        scan(src, "commit.message", c["message"], commit_pr.get(merged_by.get(c["sha"])))
    for path, numbers in (raw.get("checks") or {}).items():
        nodes[f"check:{path}"] = {"id": f"check:{path}", "kind": "check", "path": path}
        for n in numbers:
            nodes.setdefault(f"adr:{n}", {"id": f"adr:{n}", "kind": "adr", "number": n})
            add(f"check:{path}", f"adr:{n}", "cites", "checkout", "adr")
    return edges


def build(raw: Raw, roles: Roles, board: dict[str, Any] | None = None) -> tuple[list[Node], list[Edge]]:
    nodes: dict[str, Node] = {}
    edges: list[Edge] = []

    def node(nid: str, kind: str, **attrs: Any) -> None:
        nodes[nid] = {"id": nid, "kind": kind, **attrs}

    def edge(src: str, dst: str, typ: str, evidence: str, **attrs: Any) -> None:
        edges.append({"src": src, "dst": dst, "type": typ, "source": "api", "evidence": evidence, "attrs": attrs})

    meta = raw["repo"]
    default = meta["default_branch"]
    rulesets = []
    for r in raw["rulesets"]:
        approvals = [rule["parameters"].get("required_approving_review_count", 0)
                     for rule in r.get("rules", []) if rule["type"] == "pull_request"]
        rulesets.append({"name": r["name"], "enforcement": r["enforcement"], "required_approvals": max(approvals, default=None)})
    node("repo", "repo", default_branch=default, delete_branch_on_merge=meta.get("delete_branch_on_merge"), rulesets=rulesets)

    for p in raw["prs"]:
        pid = f"pr:{p['number']}"
        node(pid, "pr", number=p["number"], created=p["createdAt"], merged=p["mergedAt"], closed=p["closedAt"],
             merge_sha=(p["mergeCommit"] or {}).get("oid"),
             state=p["state"], draft=p["isDraft"], size=p["additions"] + p["deletions"], base=p["baseRefName"],
             base_is_default=p["baseRefName"] == default, head=p["headRefName"],
             reviews_truncated=p["reviews"]["totalCount"] > len(p["reviews"]["nodes"]))
        author = roles(p["author"])
        edge(f"person:{author}", pid, "authored", "pullRequest.author")
        if p["mergeCommit"]:
            sha = p["mergeCommit"]["oid"]
            nodes.setdefault(f"commit:{sha}", {"id": f"commit:{sha}", "kind": "commit", "sha": sha, "date": p["mergedAt"]})
            edge(pid, f"commit:{sha}", "merged_as", "pullRequest.mergeCommit")
        for r in p["reviews"]["nodes"]:
            edge(f"person:{roles(r['author'])}", pid, "reviewed", "pullRequest.reviews",
                 state=r["state"], at=r["submittedAt"], self=r["author"] == p["author"])
        for ref in p["closingIssuesReferences"]["nodes"]:
            if ref["repository"]["nameWithOwner"] == meta["full_name"]:
                edge(pid, f"issue:{ref['number']}", "closes", "pullRequest.closingIssuesReferences")

    if "milestones" not in raw or any("timelineItems" not in i or "body" not in i for i in raw["issues"]) \
            or any("body" not in p for p in raw["prs"]) \
            or any("message" not in c for d in raw["deployments"] for c in d["contains"]):
        raise SystemExit("the raw cache predates milestone events or text fields: collect again without --reuse-raw")
    for m in raw["milestones"]:
        node(f"milestone:{m['title']}", "milestone", title=m["title"], due=m["due_on"], state=m["state"])

    for i in raw["issues"]:
        iid = f"issue:{i['number']}"
        node(iid, "issue", number=i["number"], state=i["state"], state_reason=i["stateReason"], created=i["createdAt"],
             closed=i["closedAt"], labels=[lab["name"] for lab in i["labels"]["nodes"]],
             milestone=(i["milestone"] or {}).get("title"), milestone_due=(i["milestone"] or {}).get("dueOn"),
             events_truncated=i["timelineItems"]["totalCount"] > len(i["timelineItems"]["nodes"]))
        edge(f"person:{roles(i['author'])}", iid, "filed", "issue.author")
        for a in i["assignees"]["nodes"]:
            edge(f"person:{roles(a)}", iid, "assigned", "issue.assignees")
        for ev in i["timelineItems"]["nodes"]:
            typ = "milestoned" if ev["__typename"] == "MilestonedEvent" else "demilestoned"
            nodes.setdefault(f"milestone:{ev['milestoneTitle']}",
                             {"id": f"milestone:{ev['milestoneTitle']}", "kind": "milestone", "title": ev["milestoneTitle"],
                              "due": None, "state": None})
            edge(iid, f"milestone:{ev['milestoneTitle']}", typ, "issue.timelineItems", at=ev["createdAt"])

    if board:
        repo_url = f"https://github.com/{meta['full_name']}"
        items = [r for r in raw["board"]["items"] if r.get("repository") == repo_url]
        for it in velocity.parse(items, argparse.Namespace(**board)):
            if f"issue:{it.number}" in nodes:
                nodes[f"issue:{it.number}"]["board"] = {**asdict(it), "due": it.due.isoformat() if it.due else None}

    for r in raw["runs"]:
        node(f"run:{r['id']}", "run", workflow=r["name"], conclusion=r["conclusion"], status=r["status"],
             event=r["event"], on_default=r["head_branch"] == default, created=r["created_at"])

    for rel in raw["releases"]:
        rid = f"release:{rel['tag_name']}"
        node(rid, "release", tag=rel["tag_name"], published=rel["published_at"], prerelease=rel["prerelease"], draft=rel["draft"])
        edge(rid, f"commit:{rel['sha']}", "tags", "commits/{tag}")

    for d in raw["deployments"]:
        did = f"deployment:{d['id']}"
        states = [s["state"] for s in d["statuses"]]
        final = next((s for s in states if s != "inactive"), "unknown")
        payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        node(did, "deployment", env=d["environment"], created=d["created_at"], ref=d["ref"], deploy_kind=payload.get("kind"),
             final_state=final, states=states)
        edge(did, f"commit:{d['sha']}", "deploys", "deployment.sha")
        for c in d["contains"]:
            nodes.setdefault(f"commit:{c['sha']}", {"id": f"commit:{c['sha']}", "kind": "commit", "sha": c["sha"], "date": c["date"]})
            edge(did, f"commit:{c['sha']}", "contains", "compare/{previous}...{sha}")

    for b in raw["branches"]:
        node(f"branch:{b['name']}", "branch", name=b["name"], sha=b["commit"]["sha"], default=b["name"] == default)

    edges += text_edges(raw, nodes)

    for nid in {e["src"] for e in edges if e["src"].startswith("person:")}:
        node(nid, "person", role=nid.split(":", 1)[1])
    return list(nodes.values()), edges


# ── Metrics ────────────────────────────────────────────────────


def hours(a: str, b: str) -> float:
    return (parse(b) - parse(a)).total_seconds() / 3600


def spread(values: list[float]) -> dict[str, Any] | None:
    if not values:
        return None
    values = sorted(values)
    q = statistics.quantiles(values, n=20, method="inclusive") if len(values) > 1 else [values[0]] * 19
    return {"n": len(values), "median": round(statistics.median(values), 1), "p75": round(q[14], 1), "p90": round(q[17], 1)}


def share(part: float | None, whole: float | None) -> float | None:
    return round(part / whole, 3) if whole and part is not None else None


def renamed_titles(issues: list[Node], milestones: list[Node], events: list[Edge]) -> tuple[dict[str, str], set[str]]:
    """Events keep a milestone's title at the time. When an issue's last event set title T and the issue now sits
    in M, T was M's earlier name; a title with conflicting or no such evidence stays unresolved."""
    current = {m["title"] for m in milestones if m["due"] is not None or m["state"] is not None}
    now = {i["id"]: i["milestone"] for i in issues if not i.get("events_truncated")}
    last: dict[str, Edge] = {}
    for e in sorted(events, key=lambda e: e["attrs"]["at"]):
        last[e["src"]] = e
    votes: defaultdict[str, set[str]] = defaultdict(set)
    for iid, e in last.items():
        old = e["dst"].split(":", 1)[1]
        if e["type"] == "milestoned" and old not in current and now.get(iid) and now[iid] != old:
            votes[old].add(now[iid])
    alias = {old: new.pop() for old, new in votes.items() if len(new) == 1}
    unresolved = {e["dst"].split(":", 1)[1] for e in events} - current - set(alias)
    return alias, unresolved


def carry_over(issues: list[Node], milestones: list[Node], edges: list[Edge], until: dt.datetime) -> Metrics:
    """An item carries over when it leaves a sprint while open, for a later sprint, after the sprint began (the
    previous sprint's due date; the first sprint's is inferred from the gap between the first two due dates).
    Leaving earlier is re-planning; leaving for no sprint or an earlier one is other."""
    before: Callable[[str | None], bool] = lambda ts: ts is not None and parse(ts) < until
    closed = {i["id"]: i["closed"] for i in issues}
    events = sorted((e for e in edges if e["type"] in ("milestoned", "demilestoned")), key=lambda e: e["attrs"]["at"])
    alias, unresolved = renamed_titles(issues, milestones, events)
    title: Callable[[Edge], str] = lambda e: alias.get(e["dst"].split(":", 1)[1], e["dst"].split(":", 1)[1])
    sprints = sorted((m for m in milestones if m["due"]), key=lambda m: m["due"])
    due = {m["title"]: m["due"] for m in sprints}
    dues = [parse(m["due"]) for m in sprints]
    began = {m["title"]: dues[k - 1] for k, m in enumerate(sprints) if k}
    if len(sprints) > 1:
        began[sprints[0]["title"]] = dues[0] - (dues[1] - dues[0])
    ever: defaultdict[str, set[str]] = defaultdict(set)
    left: defaultdict[str, defaultdict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for i in issues:
        if i["milestone"] and before(i["created"]):
            ever[i["milestone"]].add(i["id"])
    by_issue: defaultdict[str, list[Edge]] = defaultdict(list)
    for e in events:
        if before(e["attrs"]["at"]):
            by_issue[e["src"]].append(e)
            ever[title(e)].add(e["src"])
    for iid, es in by_issue.items():
        for e in es:
            at = e["attrs"]["at"]
            if e["type"] != "demilestoned" or (closed[iid] is not None and parse(closed[iid]) <= parse(at)):
                continue
            src = title(e)
            # GitHub records a milestone change as a demilestone and a milestone at the same moment, in either order.
            nxt = next((title(x) for x in es if x["type"] == "milestoned" and title(x) != src
                        and abs((parse(x["attrs"]["at"]) - parse(at)).total_seconds()) <= MOVE_WINDOW_S), None)
            if nxt in due and src in due and due[nxt] > due[src]:
                way = "carried_over" if parse(at) >= began[src] else "replanned_early"
            else:
                way = "left_other"
            left[src][way].add(iid)

    def row(m: Node) -> dict[str, Any]:
        counts: dict[str, int | None] = {w: len(left[m["title"]][w]) for w in ("carried_over", "replanned_early", "left_other")}
        if m["title"] not in began:
            counts.update(carried_over=None, replanned_early=None)
        return {"sprint": m["title"], "due": m["due"], "ever": len(ever[m["title"]]), **counts,
                "share": share(counts["carried_over"], len(ever[m["title"]]))}

    rows = [row(m) for m in sprints]
    elapsed = [r for r in rows if parse(r["due"]) < until]
    total_ever = sum(r["ever"] for r in elapsed)
    total_carried = None if any(r["carried_over"] is None for r in elapsed) else sum(r["carried_over"] for r in elapsed)
    return {"sprints": rows, "elapsed": {"sprints": len(elapsed), "ever": total_ever, "carried_over": total_carried,
                                         "share": share(total_carried, total_ever)},
            "renamed_titles": len(alias), "unresolved_titles": len(unresolved)}


def board_reading(issues: list[Node], milestones: list[Node], edges: list[Edge], until: dt.datetime, board: dict[str, Any]) -> Metrics:
    items = [velocity.Item(**{**b, "due": dt.date.fromisoformat(b["due"]) if b["due"] else None})
             for i in issues if (b := i.get("board"))]
    as_of = dt.date.fromisoformat(board["as_of"]) if board.get("as_of") else until.date()
    reading = {"as_of": as_of.isoformat(), "items": len(items),
               "sprints": [{**r, "due": r["due"].isoformat() if r["due"] else None,
                            "done_share": share(r["done"], board["capacity"])} for r in velocity.sprints(items)],
               "ratios_by_phase": velocity.ratios(items, "phase"), "ratios_by_type": velocity.ratios(items, "type"),
               "coverage": velocity.coverage(items), "carry_over": carry_over(issues, milestones, edges, until)}
    if board.get("target"):
        m = velocity.margin(items, board["capacity"], board["target"], as_of)
        reading["margin"] = {**m, "due": m["due"].isoformat()} if "due" in m else m
    return reading


def lineage(nodes: list[Node], edges: list[Edge], since: dt.datetime, until: dt.datetime,
            reviewed: Callable[[str], bool]) -> Metrics:
    """Three path queries. Each names the edge sources it relies on."""
    inside: Callable[[str | None], bool] = lambda ts: ts is not None and since <= parse(ts) < until
    by_id = {n["id"]: n for n in nodes}
    prs = [n for n in nodes if n["kind"] == "pr"]
    out: defaultdict[str, defaultdict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for e in edges:
        out[e["type"]][e["src"]].add(e["dst"])
    reached: defaultdict[str, set[str]] = defaultdict(set)
    for typ in ("contains", "deploys"):
        for d, commits in out[typ].items():
            reached[d] |= commits
    merged_as = {src: next(iter(dst)) for src, dst in out["merged_as"].items()}
    deploys = sorted((n for n in nodes if n["kind"] == "deployment"), key=lambda d: d["created"])

    def commit_of(nid: str) -> str | None:
        return merged_as.get(nid) if nid.startswith("pr:") else nid

    def first_deploy(nid: str) -> Node | None:
        return next((d for d in deploys if commit_of(nid) in reached[d["id"]]), None)

    reverts: list[dict[str, Any]] = []
    for src, dsts in out["reverts"].items():
        for dst in dsts:
            reverter, reverted = by_id.get(src, {}), by_id.get(dst, {})
            at = reverter.get("merged") or reverter.get("date")
            if not inside(at):
                continue
            at = cast(str, at)
            reverted_at = reverted.get("merged") or reverted.get("date")
            shipped = first_deploy(dst)
            failed = [d for d in deploys if d["final_state"] in FAILED_DEPLOY and commit_of(dst) in reached[d["id"]]
                      and parse(d["created"]) <= parse(at)]
            reverts.append({"reverter": src, "reverted": dst,
                            "hours_to_revert": round(hours(reverted_at, at), 1) if reverted_at else None,
                            "reverted_was_deployed": shipped is not None, "failed_deploys_between": [d["id"] for d in failed]})
    failed_in_window = [d for d in deploys if d["final_state"] in FAILED_DEPLOY and inside(d["created"])]
    explained = {f for r in reverts for f in r["failed_deploys_between"]}

    merged_into: defaultdict[str, list[Node]] = defaultdict(list)
    for p in sorted((p for p in prs if p["merged"]), key=lambda p: parse(p["merged"])):
        merged_into[p["base"]].append(p)
    stories: list[dict[str, Any]] = []
    for story in (p for p in prs if p["base_is_default"] and p["merged"]):
        previous = [s["merged"] for s in merged_into[story["base"]]
                    if s["head"] == story["head"] and parse(s["merged"]) < parse(story["merged"])]
        start = parse(previous[-1]) if previous else None
        slices = [p for p in merged_into[story["head"]]
                  if parse(p["merged"]) <= parse(story["merged"]) and (start is None or parse(p["merged"]) > start)]
        if not slices or not inside(story["merged"]):
            continue
        shipped = first_deploy(story["id"])
        stories.append({"story_pr": story["id"], "slices": len(slices), "slices_reviewed": sum(reviewed(p["id"]) for p in slices),
                        "story_reviewed": reviewed(story["id"]), "first_slice_merged": min(p["merged"] for p in slices),
                        "story_merged": story["merged"],
                        "merge_to_deploy_h": round(hours(story["merged"], shipped["created"]), 1) if shipped else None})

    adrs: list[dict[str, Any]] = []
    for adr in sorted((n for n in nodes if n["kind"] == "adr"), key=lambda n: n["number"]):
        citing = [src for src, dsts in out["cites"].items() if adr["id"] in dsts]
        decide = [src for src, dsts in out["decides"].items() if adr["id"] in dsts]
        cited_prs = [c for c in citing if c.startswith("pr:")]
        dates = sorted(filter(None, (by_id[c].get("created") or by_id[c].get("date") for c in citing if c in by_id)))
        adrs.append({"adr": adr["number"], "decide_issues": len(decide),
                     "decide_issues_closed": sum(by_id[c]["state"] == "CLOSED" for c in decide),
                     "citing_prs": len(cited_prs), "citing_prs_in_window": sum(inside(by_id[c]["created"]) for c in cited_prs),
                     "citing_commits": sum(c.startswith("commit:") for c in citing),
                     "checks": sorted(by_id[c]["path"] for c in citing if c.startswith("check:")),
                     "first_cited": dates[0] if dates else None, "last_cited": dates[-1] if dates else None})

    return {
        "reverts": {"sources": ["text", "api"], "chains": reverts, "failed_deploys": len(failed_in_window),
                    "failed_deploys_followed_by_revert": len(explained & {d["id"] for d in failed_in_window})},
        "stories": {"sources": ["api"], "merged_in_window": stories},
        "decisions": {"sources": ["text"], "adrs": adrs,
                      "with_check": sum(bool(a["checks"]) for a in adrs), "without_decide_issue": sum(not a["decide_issues"] for a in adrs)},
        "text_edges": dict(Counter(e["evidence"].split(":")[1] for e in edges if e["source"] == "text")),
    }


def compute(nodes: list[Node], edges: list[Edge], since: dt.datetime, until: dt.datetime,
            board: dict[str, Any] | None = None) -> Metrics:
    by_kind: defaultdict[str, list[Node]] = defaultdict(list)
    for n in nodes:
        by_kind[n["kind"]].append(n)
    inside: Callable[[str | None], bool] = lambda ts: ts is not None and since <= parse(ts) < until
    before: Callable[[str | None], bool] = lambda ts: ts is not None and parse(ts) < until
    author = {e["dst"]: e["src"].split(":", 1)[1] for e in edges if e["type"] == "authored"}
    reviews: defaultdict[str, list[Edge]] = defaultdict(list)
    for e in edges:
        if e["type"] == "reviewed":
            reviews[e["dst"]].append(e)
    repo = by_kind["repo"][0]

    def outside(pid: str, approved_only: bool = False) -> bool:
        return any(not r["attrs"]["self"] and r["src"] != "person:bot" and (not approved_only or r["attrs"]["state"] == "APPROVED")
                   for r in reviews[pid])

    prs = by_kind["pr"]
    opened = [p for p in prs if inside(p["created"])]
    merged = [p for p in prs if inside(p["merged"])]
    closed = [p for p in prs if p["state"] == "CLOSED" and inside(p["closed"])]
    merged_all = [p for p in prs if before(p["merged"])]
    role: Callable[[Node], str] = lambda p: author[p["id"]]

    def flow(ms: list[Node]) -> dict[str, Any]:
        return {"time_to_merge_h": spread([hours(p["created"], p["merged"]) for p in ms]),
                "time_to_merge_h_by_role": {r: spread([hours(p["created"], p["merged"]) for p in ms if role(p) == r])
                                            for r in sorted({role(p) for p in ms})}}

    def review(ms: list[Node]) -> dict[str, Any]:
        no_review = [p for p in ms if not outside(p["id"])]
        no_approval = [p for p in ms if not outside(p["id"], approved_only=True)]
        return {"merged": len(ms), "no_outside_review": len(no_review), "no_outside_review_share": share(len(no_review), len(ms)),
                "no_outside_review_by_role": dict(Counter(map(role, no_review))),
                "no_outside_review_by_target": dict(Counter("default" if p["base_is_default"] else "other" for p in no_review)),
                "no_outside_approval": len(no_approval), "no_outside_approval_share": share(len(no_approval), len(ms))}

    given = Counter(e["src"].split(":", 1)[1] for e in edges
                    if e["type"] == "reviewed" and not e["attrs"]["self"] and e["src"] != "person:bot" and inside(e["attrs"]["at"]))
    sizes = [p["size"] for p in merged]

    runs = [r for r in by_kind["run"] if inside(r["created"])]
    runs_all = [r for r in by_kind["run"] if before(r["created"])]

    def ci(rs: list[Node]) -> dict[str, Any]:
        per: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for r in rs:
            per[r["workflow"]][r["conclusion"] or r["status"]] += 1
        failed = sum(r["conclusion"] == "failure" for r in rs)
        return {"runs": len(rs), "failed": failed, "cancelled": sum(r["conclusion"] == "cancelled" for r in rs),
                "failure_rate": share(failed, len(rs)), "failed_on_default": sum(r["conclusion"] == "failure" and r["on_default"] for r in rs),
                "by_workflow": {w: dict(c) for w, c in sorted(per.items())}}

    deploys = sorted(by_kind["deployment"], key=lambda d: d["created"])
    contains: defaultdict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e["type"] in ("contains", "deploys"):
            contains[e["src"]].add(e["dst"])
    merged_as = {e["dst"]: e["src"] for e in edges if e["type"] == "merged_as"}
    pr_by_id = {p["id"]: p for p in prs}

    def dora(env: str) -> dict[str, Any]:
        ds = [d for d in deploys if d["env"] == env and before(d["created"])]
        win = [d for d in ds if inside(d["created"])]
        failed = [d for d in win if d["final_state"] in FAILED_DEPLOY]
        restore: list[float] = []
        for f in failed:
            nxt = next((d for d in ds if d["created"] > f["created"] and d["final_state"] == "success"), None)
            if nxt:
                restore.append(hours(f["created"], nxt["created"]))
        first_deploy: dict[str, str] = {}
        for d in ds:
            for c in contains[d["id"]]:
                pid = merged_as.get(c)
                if pid and pid not in first_deploy:
                    first_deploy[pid] = d["created"]
        lead = [hours(pr_by_id[pid]["merged"], at) for pid, at in first_deploy.items() if inside(at)]
        days = (until - since).total_seconds() / 86400
        return {"deploys": len(win), "deploys_total": len(ds), "per_week": round(len(win) / days * 7, 2),
                "failed": len(failed), "change_failure_rate": share(len(failed), len(win)),
                "time_to_restore_h": spread(restore), "merge_to_deploy_h": spread(lead)}

    issues = by_kind["issue"]
    open_issues = [i for i in issues if i["state"] == "OPEN"]
    assignees: defaultdict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e["type"] == "assigned":
            assignees[e["dst"]].append(e["src"].split(":", 1)[1])
    kind: Callable[[Node], str | None] = lambda i: next((lab for lab in i["labels"] if lab in KIND_LABELS or lab.startswith("type:")), None)

    open_prs = [p for p in prs if p["state"] == "OPEN"]
    merged_heads = {p["head"] for p in merged_all}
    open_heads = {p["head"] for p in open_prs}
    live = [b for b in by_kind["branch"] if not b["default"]]

    return {
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "flow": {"opened": len(opened), "opened_by_role": dict(Counter(map(role, opened))),
                 "merged": len(merged), "merged_by_role": dict(Counter(map(role, merged))),
                 "closed_unmerged": len(closed), **flow(merged),
                 "size_median": statistics.median(sizes) if sizes else None,
                 "large_share": share(sum(s >= LARGE_PR_LINES for s in sizes), len(sizes)),
                 "merged_into_default": sum(p["base_is_default"] for p in merged),
                 "merged_into_other": sum(not p["base_is_default"] for p in merged)},
        "review": {**review(merged), "reviews_given_by_role": dict(given),
                   "top_reviewer_share": share(max(given.values(), default=0), sum(given.values())),
                   "rulesets": repo["rulesets"]},
        "ci": ci(runs),
        "releases": {"in_window": sum(inside(r["published"]) for r in by_kind["release"]),
                     "total": sum(before(r["published"]) for r in by_kind["release"])},
        "dora": {env: dora(env) for env in sorted({d["env"] for d in deploys})},
        "issues": {"open": len(open_issues), "opened": sum(inside(i["created"]) for i in issues),
                   "closed": sum(inside(i["closed"]) for i in issues),
                   "closed_not_planned": sum(inside(i["closed"]) and i["state_reason"] == "NOT_PLANNED" for i in issues),
                   "open_by_kind": dict(Counter(kind(i) or "none" for i in open_issues)),
                   "open_unassigned": sum(not assignees[i["id"]] for i in open_issues),
                   "open_assigned_by_role": dict(Counter(r for i in open_issues for r in assignees[i["id"]])),
                   "open_bug": sum("bug" in i["labels"] for i in open_issues)},
        "hygiene": {"open_prs": len(open_prs), "open_prs_by_role": dict(Counter(map(role, open_prs))),
                    "stale_open_prs": sum((until - parse(p["created"])).days > STALE_PR_DAYS for p in open_prs),
                    "live_branches": len(live),
                    "merged_not_deleted": sum(b["name"] in merged_heads and b["name"] not in open_heads for b in live),
                    "delete_branch_on_merge": repo["delete_branch_on_merge"]},
        "cumulative": {"prs": sum(before(p["created"]) for p in prs), **review(merged_all), **flow(merged_all),
                       "ci": {k: v for k, v in ci(runs_all).items() if k != "by_workflow"}},
        **({"board": board_reading(issues, by_kind["milestone"], edges, until, board)} if board else {}),
        "lineage": lineage(nodes, edges, since, until, outside),
    }


# ── Reading ────────────────────────────────────────────────────


def markdown(m: Metrics, window: dict[str, Any]) -> str:
    f, r, c = m["flow"], m["review"], m["ci"]
    lines = [f"## Repository snapshot, {window['since']} → {window['until']}", ""]
    if window.get("coverage_warnings"):
        lines += ["**Coverage warnings:** " + "; ".join(window["coverage_warnings"]), ""]
    ttm = f["time_to_merge_h"] or {}
    lines += [
        f"- **PRs:** {f['opened']} opened, {f['merged']} merged, {f['closed_unmerged']} closed unmerged. "
        f"Median open → merge {ttm.get('median')} h (p90 {ttm.get('p90')} h). Median size {f['size_median']} lines.",
        f"- **Review:** {r['no_outside_review']} of {r['merged']} merged PRs had no outside review "
        f"({r['no_outside_review_share']}); {r['no_outside_approval']} had no outside approval.",
        f"- **CI:** {c['runs']} runs, {c['failed']} failed ({c['failure_rate']}), {c['failed_on_default']} on the default branch.",
        f"- **Releases:** {m['releases']['in_window']} in the window, {m['releases']['total']} in total.",
        "", "| Environment | Deploys | Change failure rate | Time to restore, median h | Merge → deploy, median h |",
        "| --- | --: | --: | --: | --: |"]
    for env, d in m["dora"].items():
        lines.append(f"| {env} | {d['deploys']} | {d['change_failure_rate']} | {(d['time_to_restore_h'] or {}).get('median')} "
                     f"| {(d['merge_to_deploy_h'] or {}).get('median')} |")
    if "board" in m:
        b = m["board"]
        co, cov = b["carry_over"]["elapsed"], b["coverage"]
        carried = (f"{co['carried_over']} of {co['ever']} items in {co['sprints']} elapsed sprints carried over to a "
                   f"later sprint ({co['share']})." if co["carried_over"] is not None else
                   "Carry-over is unknown: with one sprint, its start cannot be inferred.")
        lines += ["", f"- **Board, as of {b['as_of']}:** {carried} "
                  f"{cov['with_actual']} of {cov['estimated_done']} done estimated items have an actual."]
        if b["carry_over"]["unresolved_titles"] and co["carried_over"] is not None:
            lines.append(f"- **Carry-over is a lower bound:** {b['carry_over']['unresolved_titles']} old milestone "
                         "title(s) in events could not be matched to a current milestone.")
        if "margin" in b:
            lines.append(f"- **Margin** to {b['margin']['target']}: " + (f"{b['margin']['margin']:+.1f} d"
                         if "margin" in b["margin"] else f"{b['margin']['matches']} milestones match; pass a unique part"))
    lines += ["", "Full figures: `metrics.json`."]
    return "\n".join(lines)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def utc(ts: str) -> dt.datetime:
    t = parse(ts)
    if t.tzinfo is None:
        raise argparse.ArgumentTypeError(f"{ts}: give a UTC offset, such as 2026-10-28T15:00:00Z")
    return t.astimezone(dt.timezone.utc)


def add_arguments(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--repo", required=True)
    c.add_argument("--since", required=True, type=utc)
    c.add_argument("--until", required=True, type=utc)
    c.add_argument("--roles", required=True, type=Path)
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--raw", type=Path)
    c.add_argument("--reuse-raw", action="store_true", help="rebuild from the --raw directory instead of fetching again")
    c.add_argument("--board", help="project board as OWNER/NUMBER; adds the board reading")
    c.add_argument("--checkout", type=Path, help="a local clone: adds every commit message and the checks citing an ADR")
    c.set_defaults(board_fields=velocity.add_board_args(c), fail=c.error)
    r = sub.add_parser("report")
    r.add_argument("dir", type=Path)
    r.add_argument("--json", action="store_true")


def run(args: argparse.Namespace) -> int:
    if args.action == "collect":
        if args.board and args.capacity is None:
            args.fail("--board needs --capacity")
        raw_dir = args.raw or Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"),
                                   "repo-snapshots", args.repo.replace("/", "-"), args.until.date().isoformat())
        if args.reuse_raw:
            raw = {f.stem: json.loads(f.read_text()) for f in raw_dir.glob("*.json")}
            coverage = raw.pop("coverage")
            if args.board and (raw.get("board") or {}).get("source") != args.board:
                raw["board"] = fetch_board(args.board)
                (raw_dir / "board.json").write_text(json.dumps(raw["board"]))
        else:
            raw, coverage = fetch(args.repo, args.since, args.until)
            if args.board:
                raw["board"] = fetch_board(args.board)
            raw_dir.mkdir(parents=True, exist_ok=True)
            for key, value in {**raw, "coverage": coverage}.items():
                (raw_dir / f"{key}.json").write_text(json.dumps(value))
        board = {**{k: getattr(args, k) for k in args.board_fields}, "as_of": raw["board"]["fetched_on"]} if args.board else None
        roles = Roles(json.loads(args.roles.read_text()))
        if args.checkout and "revert_merges" not in raw:
            raw["commits"], raw["revert_merges"], raw["checks"] = read_checkout(args.checkout, raw["repo"]["default_branch"])
            for key in ("commits", "revert_merges", "checks"):
                (raw_dir / f"{key}.json").write_text(json.dumps(raw[key]))
        nodes, edges = build(raw, roles, board)
        warnings = [f"{len(coverage.get('run_days_capped', []))} day(s) over the runs API's {RUNS_PAGE_CAP}-result cap"] \
            if coverage.get("run_days_capped") else []
        if coverage.get("compare_truncated"):
            warnings.append(f"{len(coverage['compare_truncated'])} deployment compare(s) truncated at 250 commits")
        if roles.unmapped:
            warnings.append(f"{len(roles.unmapped)} login(s) not in the roles file, counted as 'unmapped'")
            print("unmapped logins (add them to the roles file): " + ", ".join(sorted(roles.unmapped)), file=sys.stderr)
        truncated = sum(n.get("reviews_truncated", False) for n in nodes)
        if truncated:
            warnings.append(f"{truncated} PR(s) with more than 100 reviews, reviews truncated")
        events_truncated = sum(n.get("events_truncated", False) for n in nodes)
        if events_truncated:
            warnings.append(f"{events_truncated} issue(s) with more than 50 milestone events, events truncated")
        if "revert_merges" not in raw and any(e["type"] == "reverts" for e in edges):
            warnings.append("no revert-merge mapping (collect with --checkout): a revert merged through a merge-commit PR "
                            "may be counted twice in revert chains")
        if not any(n["kind"] == "pr" for n in nodes):
            warnings.append("no PRs returned: check the repo name and the signed-in account")
        window = {"repo": args.repo, "since": args.since.isoformat(), "until": args.until.isoformat(),
                  "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                  "counts": dict(Counter(n["kind"] for n in nodes)), "edges": dict(Counter(e["type"] for e in edges)),
                  "coverage_warnings": warnings, "board": board, "checkout": "commits" in raw}
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "window.json").write_text(json.dumps(window, indent=2))
        write_jsonl(args.out / "nodes.jsonl", nodes)
        write_jsonl(args.out / "edges.jsonl", edges)
        target = args.out
    else:
        target = args.dir

    window = json.loads((target / "window.json").read_text())
    metrics = compute(read_jsonl(target / "nodes.jsonl"), read_jsonl(target / "edges.jsonl"),
                      parse(window["since"]), parse(window["until"]), window.get("board"))
    (target / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2) if getattr(args, "json", False) else markdown(metrics, window))
    return 0
