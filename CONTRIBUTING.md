# Contributing

Skills contributions welcome! This is a public registry — quality matters.

## Adding a skill

1. **Create the skill directory:** `<category>/<skill-name>/SKILL.md`
   - Categories mirror Hermes conventions: `creative`, `software-development`, `github`, `media`, `research`, etc.
   - Use lowercase-hyphens for the skill name.

2. **Write SKILL.md** with valid YAML frontmatter:

   ```yaml
   ---
   name: my-skill-name
   description: Use when <trigger>. <what it does>.
   version: 1.0.0
   author: Your Name
   license: MIT
   ---

   # My Skill

   Body content here.
   ```

   Required fields: `name`, `description` (≤ 1024 chars).
   See the [Hermes skill authoring guide](https://hermes-agent.nousresearch.com/docs/skills) for full conventions.

3. **Add to `registry.yaml`:**

   ```yaml
   skills:
     - name: my-skill-name       # must match SKILL.md frontmatter
       version: 1.0.0             # must match SKILL.md frontmatter
       category: creative
       author: Your Name
       description: One-line summary
       tags: [tag1, tag2]
       dependencies:             # required env vars or tools
         - SOME_API_KEY
       path: creative/my-skill-name
   ```

4. **Validate locally:**

   ```bash
   pip install pyyaml
   python3 scripts/validate.py
   ```

   Fix all errors before pushing. Warnings (like skill-on-disk-without-registry-entry) are informational.

5. **Open a PR.** CI runs the validator automatically.

## Guidelines

- **Self-contained:** Each skill should work without external setup beyond declared dependencies.
- **Hermes-specific knowledge is fine.** The target audience is Hermes users — that's the value prop.
- **No secrets.** Never commit API keys, tokens, or credentials. Reference env vars instead.
- **Audit for internal references** before publishing. No hardcoded internal URLs, hostnames, or paths.
- **One skill per PR** for review clarity.

## License

By contributing, you agree your contributions are licensed under the [MIT license](LICENSE).
