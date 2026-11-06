import contextlib
import copy
import datetime as dt
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from hugin import cli, snapshot

SINCE = dt.datetime(2026, 1, 10, tzinfo=dt.timezone.utc)
UNTIL = dt.datetime(2026, 1, 20, tzinfo=dt.timezone.utc)
ALICE = {"__typename": "User", "login": "alice"}
BOB = {"__typename": "User", "login": "bob"}
BOT = {"__typename": "Bot", "login": "dependabot"}
S1 = {"title": "Sprint 1", "dueOn": "2026-01-12T00:00:00Z"}
S2 = {"title": "Sprint 2 · V1", "dueOn": "2026-01-26T00:00:00Z"}
S3 = {"title": "Sprint 3", "dueOn": "2026-02-09T00:00:00Z"}
BOARD = {"capacity": 5.0, "target": "V1", "done_status": "Done", "estimate_field": "Estimate", "actual_field": "Actual",
         "remaining_field": "Remaining Work", "phase_field": "Phase"}


def events(*rows):
    return {"totalCount": len(rows), "nodes": [{"__typename": t, "milestoneTitle": m["title"], "createdAt": at}
                                               for t, m, at in rows]}


def card(number, milestone, status, repo="o/r", **fields):
    return {"content": {"type": "Issue", "number": number}, "repository": f"https://github.com/{repo}",
            "milestone": milestone, "status": status, "labels": fields.pop("labels", []), **fields}


def pr(number, author, created, merged=None, closed=None, base="main", head=None, size=10, reviews=(), merge_sha=None,
       body=""):
    return {"number": number, "title": f"change {number}", "body": body, "author": author, "createdAt": created, "mergedAt": merged, "closedAt": closed or merged,
            "state": "MERGED" if merged else ("CLOSED" if closed else "OPEN"), "isDraft": False,
            "additions": size, "deletions": 0, "baseRefName": base, "headRefName": head or f"b{number}",
            "mergeCommit": {"oid": merge_sha} if merge_sha else None,
            "reviews": {"totalCount": len(reviews), "nodes": [{"author": a, "state": s, "submittedAt": t} for a, s, t in reviews]},
            "closingIssuesReferences": {"nodes": []}}


def run(i, conclusion, created, branch="main", name="CI"):
    return {"id": i, "name": name, "conclusion": conclusion, "status": "completed", "event": "push",
            "head_branch": branch, "created_at": created}


def deployment(i, created, sha, states, contains=(), env="staging"):
    return {"id": i, "environment": env, "created_at": created, "ref": sha, "sha": sha, "payload": {},
            "statuses": [{"state": s} for s in states], "contains": [{"sha": c, "date": created, "message": ""} for c in contains]}


RAW = {
    "repo": {"default_branch": "main", "delete_branch_on_merge": False, "full_name": "o/r"},
    "rulesets": [{"name": "main", "enforcement": "disabled",
                  "rules": [{"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]}],
    "prs": [
        pr(1, ALICE, "2026-01-11T00:00:00Z", merged="2026-01-11T02:00:00Z", size=100, merge_sha="aaaaaaa1",
           reviews=[(BOB, "APPROVED", "2026-01-11T01:00:00Z")], body="Implements ADR 0002. See #10 and #999."),
        pr(2, ALICE, "2026-01-12T00:00:00Z", merged="2026-01-12T04:00:00Z", size=2000, merge_sha="bbbbbbb2", head="story/x",
           reviews=[(BOB, "COMMENTED", "2026-01-12T01:00:00Z"), (ALICE, "APPROVED", "2026-01-12T02:00:00Z")]),
        pr(3, BOB, "2026-01-13T00:00:00Z", merged="2026-01-13T10:00:00Z", base="story/x", size=50, merge_sha="ccccccc3",
           reviews=[(BOT, "APPROVED", "2026-01-13T01:00:00Z")]),
        pr(4, BOB, "2026-01-05T00:00:00Z", merged="2026-01-06T00:00:00Z", merge_sha="ddddddd4"),
        pr(5, BOT, "2026-01-14T00:00:00Z", closed="2026-01-15T00:00:00Z"),
        pr(6, BOB, "2026-01-01T00:00:00Z", head="open-old"),
    ],
    "issues": [
        {"number": 10, "title": "a bug", "body": "", "author": ALICE, "createdAt": "2026-01-11T00:00:00Z", "closedAt": None, "state": "OPEN",
         "stateReason": None, "labels": {"nodes": [{"name": "bug"}]}, "assignees": {"nodes": [BOB]}, "milestone": S2,
         "timelineItems": events(("MilestonedEvent", S1, "2026-01-11T01:00:00Z"), ("DemilestonedEvent", S1, "2026-01-11T12:00:00Z"),
                                 ("MilestonedEvent", S2, "2026-01-11T12:00:00Z"))},
        {"number": 11, "title": "Decide ADR 0002", "body": "", "author": BOB, "createdAt": "2026-01-02T00:00:00Z", "closedAt": "2026-01-12T00:00:00Z",
         "state": "CLOSED", "stateReason": "NOT_PLANNED", "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S2,
         "timelineItems": events(("MilestonedEvent", S1, "2026-01-03T00:00:00Z"), ("DemilestonedEvent", S1, "2026-01-13T00:00:00Z"))},
        {"number": 12, "title": "t", "body": "Relates to ADR 0002.", "author": BOB, "createdAt": "2026-01-03T00:00:00Z", "closedAt": None, "state": "OPEN",
         "stateReason": None, "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S1,
         "timelineItems": events(("MilestonedEvent", {"title": "Sprint one"}, "2026-01-03T00:00:00Z"))},
        {"number": 13, "title": "t", "body": "", "author": BOB, "createdAt": "2026-01-03T00:00:00Z", "closedAt": None, "state": "OPEN",
         "stateReason": None, "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S2,
         "timelineItems": events(("MilestonedEvent", {"title": "Sprint one"}, "2026-01-04T00:00:00Z"),
                                 ("DemilestonedEvent", {"title": "Sprint one"}, "2026-01-08T00:00:00Z"),
                                 ("MilestonedEvent", {"title": "Gone"}, "2026-01-08T00:00:00Z"),
                                 ("DemilestonedEvent", {"title": "Gone"}, "2026-01-09T00:00:00Z"),
                                 ("MilestonedEvent", S2, "2026-01-09T00:00:00Z"))},
        *({"number": n, "title": "t", "body": "", "author": BOB, "createdAt": "2026-01-02T00:00:00Z", "closedAt": "2026-01-05T00:00:00Z",
           "state": "CLOSED", "stateReason": "COMPLETED", "labels": {"nodes": []}, "assignees": {"nodes": []},
           "milestone": m, "timelineItems": events(("MilestonedEvent", {"title": "Split"}, "2026-01-02T00:00:00Z"))}
          for n, m in ((14, S1), (15, S2))),
        {"number": 16, "title": "Risk: the cache in ADR 0002 can go stale", "body": "", "author": BOB, "createdAt": "2026-01-02T00:00:00Z", "closedAt": "2026-01-05T00:00:00Z",
         "state": "CLOSED", "stateReason": "COMPLETED", "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S3,
         "timelineItems": events(("MilestonedEvent", S2, "2026-01-02T00:00:00Z"), ("DemilestonedEvent", S2, "2026-01-04T00:00:00Z"),
                                 ("MilestonedEvent", S3, "2026-01-04T00:00:00Z"))},
        {"number": 17, "title": "t", "body": "", "author": BOB, "createdAt": "2026-01-02T00:00:00Z", "closedAt": "2026-01-05T00:00:00Z",
         "state": "CLOSED", "stateReason": "COMPLETED", "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S1,
         "timelineItems": events(("MilestonedEvent", S2, "2026-01-02T00:00:00Z"), ("DemilestonedEvent", S2, "2026-01-03T00:00:00Z"),
                                 ("MilestonedEvent", S1, "2026-01-03T00:00:00Z"))},
    ],
    "commits": [
        {"sha": "bbbbbbb2", "date": "2026-01-12T04:00:00Z", "message": "change 2\n\nreview of #1"},
        {"sha": "eeeeeee5", "date": "2026-01-12T06:00:00Z",
         "message": "Revert change 2\n\nThis reverts commit bbbbbbb2. Per ADR-0007."},
    ],
    "checks": {"semgrep/rules.yml": [2]},
    "milestones": [{"title": S1["title"], "due_on": S1["dueOn"], "state": "closed"},
                   {"title": S2["title"], "due_on": S2["dueOn"], "state": "open"},
                   {"title": S3["title"], "due_on": S3["dueOn"], "state": "open"}],
    "board": {"items": [
        card(10, S2, "Todo", estimate=2, **{"remaining Work": 1}),
        card(11, S2, "Done", estimate=1, actual=2, phase="Plan", labels=["type:task"]),
        card(12, S1, "Todo", estimate=3),
        card(12, S1, "Done", repo="o/other", estimate=50, actual=50),
        {"content": {"type": "PullRequest", "number": 3}, "repository": "https://github.com/o/r", "milestone": S1,
         "status": "Done", "estimate": 9},
    ]},
    "runs": [run(1, "success", "2026-01-11T00:00:00Z"), run(2, "failure", "2026-01-11T01:00:00Z"),
             run(3, "failure", "2026-01-12T00:00:00Z", branch="b2"), run(4, "cancelled", "2026-01-12T01:00:00Z"),
             run(5, "failure", "2026-01-02T00:00:00Z")],
    "releases": [{"tag_name": "v1", "published_at": "2026-01-11T03:00:00Z", "prerelease": False, "draft": False, "sha": "aaaaaaa1"}],
    "deployments": [
        deployment(100, "2026-01-11T03:00:00Z", "aaaaaaa1", ["inactive", "success"], contains=["ddddddd4", "aaaaaaa1"]),
        deployment(101, "2026-01-12T05:00:00Z", "bbbbbbb2", ["error"], contains=["bbbbbbb2"]),
        deployment(102, "2026-01-12T07:00:00Z", "bbbbbbb2", ["success"]),
        {**deployment(90, "2026-01-01T00:00:00Z", "ddddddd4", ["failure"]), "environment": "prod"},
    ],
    "branches": [{"name": "main", "commit": {"sha": "bbbbbbb2"}}, {"name": "b1", "commit": {"sha": "x"}},
                 {"name": "open-old", "commit": {"sha": "y"}}, {"name": "never-pr", "commit": {"sha": "z"}}],
}


class SnapshotMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        roles = snapshot.Roles({"alice": "Dev A", "bob": "Dev B"})
        nodes, edges = snapshot.build(RAW, roles, BOARD)
        cls.unmapped = roles.unmapped
        cls.edge_types = {e["type"] for e in edges}
        cls.edges = edges
        cls.m = snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)

    def test_roles_replace_logins_and_bots_are_typed(self):
        self.assertEqual(self.unmapped, set())
        self.assertEqual(self.m["flow"]["opened_by_role"], {"Dev A": 2, "Dev B": 1, "bot": 1})
        self.assertTrue({"authored", "reviewed", "merged_as", "deploys", "contains", "tags"} <= self.edge_types)

    def test_flow(self):
        f = self.m["flow"]
        self.assertEqual((f["opened"], f["merged"], f["closed_unmerged"]), (4, 3, 1))
        self.assertEqual(f["time_to_merge_h"]["median"], 4.0)
        self.assertEqual(f["size_median"], 100)
        self.assertEqual(f["large_share"], 0.333)
        self.assertEqual((f["merged_into_default"], f["merged_into_other"]), (2, 1))

    def test_review_ignores_self_and_bot_reviews(self):
        r = self.m["review"]
        self.assertEqual(r["no_outside_review"], 1)
        self.assertEqual(r["no_outside_review_by_role"], {"Dev B": 1})
        self.assertEqual(r["no_outside_approval"], 2)
        self.assertEqual(r["reviews_given_by_role"], {"Dev B": 2})
        self.assertEqual(r["rulesets"][0]["required_approvals"], 1)

    def test_ci(self):
        c = self.m["ci"]
        self.assertEqual((c["runs"], c["failed"], c["cancelled"], c["failed_on_default"]), (4, 2, 1, 1))
        self.assertEqual(c["failure_rate"], 0.5)
        self.assertEqual(self.m["cumulative"]["ci"]["failed"], 3)

    def test_dora(self):
        d = self.m["dora"]["staging"]
        self.assertEqual((d["deploys"], d["failed"]), (3, 1))
        self.assertEqual(d["change_failure_rate"], 0.333)
        self.assertEqual(d["time_to_restore_h"]["median"], 2.0)
        self.assertEqual(d["merge_to_deploy_h"]["n"], 3)
        self.assertEqual(d["merge_to_deploy_h"]["median"], 1.0)

    def test_issues_and_hygiene(self):
        i, h = self.m["issues"], self.m["hygiene"]
        self.assertEqual((i["open"], i["opened"], i["closed"], i["closed_not_planned"]), (3, 1, 1, 1))
        self.assertEqual(i["open_by_kind"], {"bug": 1, "none": 2})
        self.assertEqual((i["open_unassigned"], i["open_bug"]), (2, 1))
        self.assertEqual(i["open_assigned_by_role"], {"Dev B": 1})
        self.assertEqual((h["open_prs"], h["stale_open_prs"]), (1, 1))
        self.assertEqual((h["live_branches"], h["merged_not_deleted"]), (3, 1))

    def test_board_reading_uses_this_repos_issues_only(self):
        b = self.m["board"]
        self.assertEqual(b["items"], 3)
        sprints = {r["sprint"]: (r["planned"], r["done"], r["open"], r["done_share"]) for r in b["sprints"]}
        self.assertEqual(sprints, {"Sprint 1": (3, 0, 1, 0.0), "Sprint 2 · V1": (3, 1, 1, 0.2)})
        self.assertEqual((b["margin"]["sprints_left"], b["margin"]["work_left"], b["margin"]["margin"]), (1, 4, 1.0))
        self.assertEqual((b["ratios_by_phase"]["Plan"]["pairs"], b["ratios_by_phase"]["Plan"]["ratio"]), (1, 2.0))
        self.assertEqual(b["coverage"], {"estimated_done": 1, "with_actual": 1, "missing": 0})

    def test_carry_over_separates_carried_replanned_and_other(self):
        co = self.m["board"]["carry_over"]
        rows = {r["sprint"]: (r["ever"], r["carried_over"], r["replanned_early"], r["left_other"]) for r in co["sprints"]}
        self.assertEqual(rows, {"Sprint 1": (6, 1, 0, 1), "Sprint 2 · V1": (6, 0, 1, 1), "Sprint 3": (1, 0, 0, 0)})
        self.assertEqual(co["elapsed"], {"sprints": 1, "ever": 6, "carried_over": 1, "share": 0.167})
        self.assertEqual((co["renamed_titles"], co["unresolved_titles"]), (1, 2))

    def test_text_edges_record_pattern_and_only_reach_existing_nodes(self):
        text = [e for e in self.edges if e["source"] == "text"]
        self.assertIn({"src": "pr:2", "dst": "pr:1", "type": "review_of", "source": "text",
                       "evidence": "commit.message:review_of", "attrs": {}}, text)
        self.assertIn(("pr:1", "issue:10", "references"), {(e["src"], e["dst"], e["type"]) for e in text})
        self.assertFalse(any(e["dst"].endswith(":999") for e in text))
        self.assertFalse(any(e["type"] == "references" and e["dst"] == "pr:1" for e in text))

    def test_revert_chain_links_the_failed_deploy(self):
        r = self.m["lineage"]["reverts"]
        self.assertEqual(r["chains"], [{"reverter": "commit:eeeeeee5", "reverted": "pr:2", "hours_to_revert": 2.0,
                                        "reverted_was_deployed": True, "failed_deploys_between": ["deployment:101"]}])
        self.assertEqual((r["failed_deploys"], r["failed_deploys_followed_by_revert"]), (1, 1))

    def test_story_rollup_takes_the_slices_merged_into_its_own_use_of_the_head(self):
        raw = copy.deepcopy(RAW)
        raw["prs"][2].update(createdAt="2026-01-11T20:00:00Z", mergedAt="2026-01-12T03:00:00Z", closedAt="2026-01-12T03:00:00Z")
        raw["prs"] += [pr(7, ALICE, "2026-01-15T00:00:00Z", merged="2026-01-16T00:00:00Z", head="story/x"),
                       pr(8, BOB, "2026-01-14T00:00:00Z", merged="2026-01-15T00:00:00Z", base="story/x")]
        nodes, edges = snapshot.build(raw, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        stories = snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)["lineage"]["stories"]["merged_in_window"]
        self.assertEqual(sorted(stories, key=lambda s: s["story_pr"]), [
            {"story_pr": "pr:2", "slices": 1, "slices_reviewed": 0, "story_reviewed": True,
             "first_slice_merged": "2026-01-12T03:00:00Z", "story_merged": "2026-01-12T04:00:00Z", "merge_to_deploy_h": 1.0},
            {"story_pr": "pr:7", "slices": 1, "slices_reviewed": 0, "story_reviewed": False,
             "first_slice_merged": "2026-01-15T00:00:00Z", "story_merged": "2026-01-16T00:00:00Z", "merge_to_deploy_h": None}])

    def rebuild(self, change):
        raw = copy.deepcopy(RAW)
        change(raw)
        nodes, edges = snapshot.build(raw, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        return edges, snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)

    def test_revert_span_compares_instants_not_offset_strings(self):
        _, m = self.rebuild(lambda raw: raw["commits"][1].update(date="2026-01-12T03:00:00-03:00"))
        self.assertEqual(m["lineage"]["reverts"]["chains"][0]["failed_deploys_between"], ["deployment:101"])

    def test_revert_of_a_commit_known_only_from_the_checkout(self):
        def change(raw):
            raw["commits"] = [{"sha": "fffffff6", "date": "2026-01-12T01:00:00Z", "message": "direct push"},
                              {"sha": "eeeeeee5", "date": "2026-01-12T06:00:00Z", "message": "This reverts commit fffffff6."}]
        edges, _ = self.rebuild(change)
        self.assertIn(("commit:eeeeeee5", "commit:fffffff6"), {(e["src"], e["dst"]) for e in edges if e["type"] == "reverts"})

    def test_revert_of_another_repository_is_not_linked(self):
        edges, _ = self.rebuild(lambda raw: raw["prs"][0].update(body="Reverts other/lib#4"))
        self.assertNotIn(("pr:1", "pr:4"), {(e["src"], e["dst"]) for e in edges if e["type"] == "reverts"})

    def test_failed_deploy_that_did_not_carry_the_reverted_change_is_not_between(self):
        _, m = self.rebuild(lambda raw: raw["deployments"].append(
            deployment(103, "2026-01-12T05:30:00Z", "ddddddd4", ["failure"], env="prod")))
        r = m["lineage"]["reverts"]
        self.assertEqual(r["chains"][0]["failed_deploys_between"], ["deployment:101"])
        self.assertEqual((r["failed_deploys"], r["failed_deploys_followed_by_revert"]), (2, 1))

    def revert_prs(self, raw, *prs):
        raw["prs"] += list(prs)
        raw["commits"] = [{"sha": "bbbbbbb2", "date": "2026-01-12T04:00:00Z", "message": "change 2"},
                          {"sha": "1111111a", "date": "2026-01-12T05:00:00Z", "message": "This reverts commit bbbbbbb2."}]
        raw["revert_merges"] = {"1111111a": "a20a20a2"}

    def test_revert_merged_through_a_merge_commit_pr_is_one_chain(self):
        _, m = self.rebuild(lambda raw: self.revert_prs(
            raw, pr(20, ALICE, "2026-01-12T05:00:00Z", merged="2026-01-12T06:00:00Z", merge_sha="a20a20a2", body="Reverts o/r#2")))
        self.assertEqual([(c["reverter"], c["reverted"]) for c in m["lineage"]["reverts"]["chains"]], [("pr:20", "pr:2")])

    def test_revert_relanded_and_reverted_again_is_two_chains(self):
        def change(raw):
            self.revert_prs(raw, pr(20, ALICE, "2026-01-12T05:00:00Z", merged="2026-01-12T06:00:00Z", merge_sha="a20a20a2",
                                    body="Reverts o/r#2"),
                            pr(22, BOB, "2026-01-14T00:00:00Z", merged="2026-01-14T01:00:00Z", merge_sha="2222222b",
                               body="Reverts o/r#2"))
            raw["commits"].append({"sha": "2222222b", "date": "2026-01-14T01:00:00Z", "message": "This reverts commit bbbbbbb2."})
        _, m = self.rebuild(change)
        self.assertEqual(sorted((c["reverter"], c["reverted"]) for c in m["lineage"]["reverts"]["chains"]),
                         [("pr:20", "pr:2"), ("pr:22", "pr:2")])

    def test_decide_title_in_past_tense(self):
        edges, _ = self.rebuild(lambda raw: raw["issues"][1].update(title="ADR 0002 accepted"))
        self.assertIn(("issue:11", "adr:2"), {(e["src"], e["dst"]) for e in edges if e["type"] == "decides"})

    def test_decision_lineage(self):
        d = self.m["lineage"]["decisions"]
        adrs = {a["adr"]: a for a in d["adrs"]}
        self.assertEqual((adrs[2]["decide_issues"], adrs[2]["decide_issues_closed"], adrs[2]["citing_prs"],
                          adrs[2]["citing_prs_in_window"], adrs[2]["checks"]), (1, 1, 1, 1, ["semgrep/rules.yml"]))
        self.assertEqual((adrs[7]["decide_issues"], adrs[7]["citing_commits"], adrs[7]["checks"]), (0, 1, []))
        self.assertEqual((d["with_check"], d["without_decide_issue"]), (1, 1))

    def test_cumulative_counts_history_before_the_window(self):
        c = self.m["cumulative"]
        self.assertEqual((c["prs"], c["merged"], c["no_outside_review"]), (6, 4, 2))


class CarryOverMoves(unittest.TestCase):
    def carried(self, *rows):
        raw = copy.deepcopy(RAW)
        raw["issues"] = [{"number": 30, "title": "t", "body": "", "author": BOB, "createdAt": "2026-01-02T00:00:00Z", "closedAt": None, "state": "OPEN",
                          "stateReason": None, "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S3,
                          "timelineItems": events(("MilestonedEvent", S2, "2026-01-02T00:00:00Z"), *rows)}]
        nodes, edges = snapshot.build(raw, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        co = snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)["board"]["carry_over"]
        return next((r["carried_over"], r["left_other"]) for r in co["sprints"] if r["sprint"] == S2["title"])

    def test_milestone_event_listed_before_the_demilestone_is_still_the_destination(self):
        self.assertEqual(self.carried(("MilestonedEvent", S3, "2026-01-13T00:00:00Z"),
                                      ("DemilestonedEvent", S2, "2026-01-13T00:00:00Z")), (1, 0))

    def test_leaving_for_no_sprint_is_not_carry_over_even_if_a_sprint_is_set_later(self):
        self.assertEqual(self.carried(("DemilestonedEvent", S2, "2026-01-13T00:00:00Z"),
                                      ("MilestonedEvent", S3, "2026-01-19T00:00:00Z")), (0, 1))

    def test_leaving_the_first_sprint_before_it_began_is_replanning(self):
        raw = copy.deepcopy(RAW)
        raw["issues"] = [{"number": 31, "title": "t", "body": "", "author": BOB, "createdAt": "2025-12-01T00:00:00Z", "closedAt": None,
                          "state": "OPEN", "stateReason": None, "labels": {"nodes": []}, "assignees": {"nodes": []}, "milestone": S2,
                          "timelineItems": events(("MilestonedEvent", S1, "2025-12-01T00:00:00Z"),
                                                  ("DemilestonedEvent", S1, "2025-12-10T00:00:00Z"),
                                                  ("MilestonedEvent", S2, "2025-12-10T00:00:00Z"))}]
        nodes, edges = snapshot.build(raw, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        co = snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)["board"]["carry_over"]
        self.assertEqual(next((r["carried_over"], r["replanned_early"]) for r in co["sprints"] if r["sprint"] == S1["title"]), (0, 1))

    def test_a_single_sprint_has_unknown_carry_over(self):
        raw = copy.deepcopy(RAW)
        raw["milestones"] = raw["milestones"][:1]
        nodes, edges = snapshot.build(raw, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        co = snapshot.compute(nodes, edges, SINCE, UNTIL, BOARD)["board"]["carry_over"]
        self.assertEqual([(r["sprint"], r["carried_over"], r["share"]) for r in co["sprints"]], [(S1["title"], None, None)])
        self.assertEqual((co["elapsed"]["carried_over"], co["elapsed"]["share"]), (None, None))


class RevertMerges(unittest.TestCase):
    def test_a_revert_brought_in_by_a_merge_maps_to_that_merge_and_a_mainline_commit_to_none(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        git = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                        capture_output=True, text=True, check=True, env=env).stdout.strip()

        def commit(name):
            (repo / name).write_text(name)
            git("add", name)
            git("commit", "-qm", name)
            return git("rev-parse", "HEAD")

        git("init", "-q", "-b", "main")
        commit("a")
        git("checkout", "-qb", "feature")
        change = commit("x")
        git("checkout", "-q", "main")
        git("merge", "-q", "--no-ff", "feature", "-m", "merge feature")
        git("checkout", "-qb", "revert")
        git("revert", "--no-edit", change)
        branch_revert = git("rev-parse", "HEAD")
        commit("y")
        git("checkout", "-q", "main")
        commit("b")
        git("merge", "-q", "--no-ff", "revert", "-m", "merge revert")
        merge = git("rev-parse", "HEAD")
        git("revert", "--no-edit", branch_revert)
        mainline_revert = git("rev-parse", "HEAD")
        git("checkout", "-qb", "later")
        commit("c")
        git("checkout", "-q", "main")
        git("merge", "-q", "--no-ff", "later", "-m", "merge later")
        commits = [{"sha": sha, "message": git("log", "-1", "--format=%B", sha)} for sha in (branch_revert, mainline_revert)]
        self.assertEqual(snapshot.revert_merges(git, commits, "main"), {branch_revert: merge})


class SnapshotCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        nodes, edges = snapshot.build(RAW, snapshot.Roles({"alice": "Dev A", "bob": "Dev B"}), BOARD)
        self.window = {"repo": "o/r", "since": SINCE.isoformat(), "until": UNTIL.isoformat(), "board": BOARD,
                       "coverage_warnings": [], "checkout": False}
        (self.dir / "window.json").write_text(json.dumps(self.window))
        snapshot.write_jsonl(self.dir / "nodes.jsonl", nodes)
        snapshot.write_jsonl(self.dir / "edges.jsonl", edges)
        self.metrics = snapshot.compute(snapshot.read_jsonl(self.dir / "nodes.jsonl"),
                                        snapshot.read_jsonl(self.dir / "edges.jsonl"), SINCE, UNTIL, BOARD)

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["snapshot", "report", str(self.dir), *extra])
        return code, out.getvalue()

    def test_report_prints_the_reading_and_writes_metrics(self):
        code, out = self.report()
        self.assertEqual(code, 0)
        self.assertEqual(out, snapshot.markdown(self.metrics, self.window) + "\n")
        self.assertEqual(json.loads((self.dir / "metrics.json").read_text()), json.loads(json.dumps(self.metrics)))

    def test_report_json_prints_the_metrics(self):
        code, out = self.report("--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), json.loads(json.dumps(self.metrics)))

    def test_collect_with_board_requires_capacity(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            cli.main(["snapshot", "collect", "--repo", "o/r", "--since", "2026-01-10T00:00:00Z",
                      "--until", "2026-01-20T00:00:00Z", "--roles", "roles.json", "--out", "out", "--board", "o/1"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--board needs --capacity", err.getvalue())


if __name__ == "__main__":
    unittest.main()
