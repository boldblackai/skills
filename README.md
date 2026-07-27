# boldblackai/skills

A curated registry of [Hermes Agent](https://hermes-agent.nousresearch.com) skills, optimized for [harness](https://github.com/boldblackai/harness) and [bclaw](https://github.com/boldblackai/create-bclaw) environments — but usable by any Hermes user.

## What's here

Each skill is a self-contained directory with a `SKILL.md` (the skill definition, parsed by Hermes at load time) and any supporting scripts, templates, or references. Browse the [registry manifest](registry.yaml) for the canonical list of published skills with versions and metadata.

## Installing

### Option 1: Clone into your skills directory

```bash
# Clone the whole registry into your Hermes skills dir
git clone https://github.com/boldblackai/skills.git ~/.hermes/skills/boldblackai
```

Hermes will discover all skills on next session start.

### Option 2: Git submodule

```bash
cd ~/.hermes/skills
git init  # if not already a git repo
git submodule add https://github.com/boldblackai/skills.git boldblackai
```

### Option 3: Copy individual skills

```bash
# Copy just the skill you need
cp -r creative/image-gen ~/.hermes/skills/creative/
```

## Registry format

Skills are declared in [`registry.yaml`](registry.yaml). Each entry:

```yaml
- name: image-gen          # matches SKILL.md frontmatter name
  version: 1.0.0
  category: creative
  author: BoldBlack
  description: Generate images via OpenRouter's Image API
  tags: [image, generation, openrouter]
  dependencies: []          # required env vars, system tools, etc.
  path: creative/image-gen  # directory relative to repo root
```

The registry is the source of truth for what's published. CI validates that every entry matches an actual `SKILL.md` on disk, and vice versa.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Skills must pass `python3 scripts/validate.py` before merge.

## License

MIT — see [LICENSE](LICENSE).
