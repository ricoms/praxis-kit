# References

The evidence behind the constitution and its practices. Each note records what one source claims, how strongly it
supports the claim, and what this kit adopted from it. People read the notes during review. Agents query them
during development through qmd.

The notes are written in our own words. The sources themselves are not committed: most are not licensed for
redistribution, and the PDFs are heavy. `just references-fetch` downloads every arXiv source into this folder,
where `.gitignore` keeps it out of git.

## Searching

`just docs-index` registers this folder, `docs/ai-sdlc/` and `CONSTITUTION.md` with [qmd](https://github.com/tobi/qmd)
as the `praxis-kit` collection, then builds the embeddings. After that:

```sh
qmd query "evidence for the complexity ratchet"   # hybrid search, re-ranked
qmd search "one-way door"                          # keyword only
```

## Note format

One file per source, named `<arxiv-id>-<slug>.md`, or `<slug>.md` for a source without an arXiv id. The
frontmatter `informs` list names the constitution sections and practices the source supports, as paths from the
repository root. Those links are what connect the evidence to the rules.

```markdown
---
id: arXiv:0000.00000
title: Full title
authors: First Author, Second Author
year: 2026
venue: where it was published, or "preprint"
url: https://arxiv.org/abs/0000.00000
license: the source's license
read: what was read, e.g. "full text" or "abstract and conclusions"
informs:
  - CONSTITUTION.md#anchor
tags: [tag, tag]
---

# Short title

**In one sentence:** what the source shows.

## Claim
## Evidence
## Adopted
## Not adopted
## Limits
```

**Evidence** holds measured numbers and their setting, not the authors' adjectives. **Adopted** says where in the kit
each idea lives. **Not adopted** records what was deliberately left out and why, so the question is not reopened by
accident. **Limits** says what the source cannot show and what the note's author did not read.
