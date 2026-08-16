# AGENTS.md

## Project Overview

**boldblackai/skills** is a public registry of Hermes Agent skills. It's a curated marketplace — skills live here as self-contained directories with a declarative registry manifest (`registry.yaml`) as the source of truth.

The repo is optimized for [harness](https://github.com/boldblackai/harness) / [dispatch](https://github.com/boldblackai/create-dispatch) setups, but usable by any Hermes user.

## Repository Structure

```
boldblackai/skills/
├── registry.yaml              # Source of truth: every published skill listed here
├── scripts/
│   └── validate.py            # CI validator: checks registry ↔ disk consistency
├── .github/workflows/
│   └── validate.yml           # Runs validate.py on every PR
├── CONTRIBUTING.md            # How to add a skill
├── <category>/                # Skill categories (creative, software-development, etc.)
│   └── <skill-name>/
│       ├── SKILL.md           # Skill definition (frontmatter + instructions)
│       └── scripts/           # Supporting scripts (optional)
└── README.md
```

## Key Commands

```bash
# Validate the registry (requires PyYAML)
pip install pyyaml
python3 scripts/validate.py

# Validate in CI (automatic on PR)
# .github/workflows/validate.yml
```

## Conventions

- **registry.yaml is the source of truth.** Every skill on disk must have an entry, and every entry must point to a real SKILL.md. The validator enforces bidirectional consistency.
- **Name and version must match.** The `name` and `version` in registry.yaml must match the SKILL.md frontmatter exactly.
- **No skills published yet.** The initial scaffold has an empty registry. Skills will be added in subsequent PRs.
- **Category dirs mirror Hermes conventions:** `creative`, `software-development`, `github`, `media`, `research`, `productivity`, etc.
- **MIT licensed.** All contributions must be MIT-compatible.

## GitHub Actions

All third-party action references in `.github/workflows/` must be pinned to their full 40-character commit SHA with a version tag in a trailing comment:

```yaml
uses: owner/repo@<40-char-sha> # v1.2.3
```

Never use tag-only references (e.g. `actions/checkout@v4`). When adding or updating an action, resolve the tag to a SHA using `gh api repos/OWNER/REPO/commits/TAG --jq '.sha'`. Local composite actions (`./.github/actions/*`) are exempt.

## When Working in This Repo

- **Adding a skill:** Follow CONTRIBUTING.md. Always update both the skill files AND registry.yaml, then run the validator.
- **Never commit secrets.** Reference env vars (`OPENROUTER_API_KEY`, etc.) in SKILL.md, never hardcode values.
- **Audit for internal references.** This is public — no internal URLs, hostnames, paths, or project names.
