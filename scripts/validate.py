#!/usr/bin/env python3
"""
Validate the skills registry.

Checks:
  1. registry.yaml parses and has the expected schema
  2. Every registry entry has a matching <path>/SKILL.md on disk
  3. Every SKILL.md on disk (that looks like a skill) has a registry entry
  4. SKILL.md frontmatter `name` and `version` match the registry entry
  5. SKILL.md frontmatter is valid (has name, description; description <= 1024 chars)

Exit code 0 = all valid, 1 = errors found.
"""

import re
import sys
from pathlib import Path

# YAML is available as a stdlib-free fallback via the vendored parser below,
# but prefer PyYAML if installed (it handles edge cases better).
def load_yaml(text):
    """Load YAML text. Raises ImportError if PyYAML is not installed."""
    try:
        import yaml
    except ImportError:
        raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
    return yaml.safe_load(text)


try:
    load_yaml("test: 1")
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "registry.yaml"
MAX_DESCRIPTION_LENGTH = 1024
MAX_NAME_LENGTH = 64


def parse_frontmatter(content):
    """Parse YAML frontmatter from a SKILL.md file. Returns (frontmatter_dict, body_str)."""
    if not content.startswith("---"):
        return None, content

    # Find closing ---
    m = re.search(r"\n---\s*\n", content[3:])
    if not m:
        return None, content

    fm_text = content[3 : 3 + m.start()]
    body = content[3 + m.end() :]

    try:
        fm = load_yaml(fm_text)
    except Exception:
        return None, body

    if not isinstance(fm, dict):
        return None, body

    return fm, body


def validate_skill_md(skill_path):
    """Validate a SKILL.md's frontmatter. Returns list of error strings."""
    errors = []
    content = skill_path.read_text()

    fm, body = parse_frontmatter(content)
    if fm is None:
        errors.append(f"{skill_path}: missing or invalid YAML frontmatter")
        return errors

    name = fm.get("name")
    desc = fm.get("description")

    if not name:
        errors.append(f"{skill_path}: frontmatter missing 'name'")
    elif not isinstance(name, str):
        errors.append(f"{skill_path}: 'name' must be a string")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(
            f"{skill_path}: name '{name}' exceeds {MAX_NAME_LENGTH} chars"
        )
    elif not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        errors.append(
            f"{skill_path}: name '{name}' must be lowercase, hyphens/underscores only"
        )

    if not desc:
        errors.append(f"{skill_path}: frontmatter missing 'description'")
    elif not isinstance(desc, str):
        errors.append(f"{skill_path}: 'description' must be a string")
    elif len(desc) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"{skill_path}: description exceeds {MAX_DESCRIPTION_LENGTH} chars ({len(desc)})"
        )

    if not body.strip():
        errors.append(f"{skill_path}: empty body after frontmatter")

    return errors


def find_skill_files():
    """Find all SKILL.md files under category dirs, excluding scripts/, references/, etc."""
    skills = {}
    # Category dirs are top-level directories (not hidden, not scripts/.github/etc)
    skip_dirs = {"scripts", ".github", ".git", "node_modules", "references", "templates", "assets"}
    for item in REPO_ROOT.iterdir():
        if not item.is_dir() or item.name.startswith(".") or item.name in skip_dirs:
            continue
        for skill_md in item.rglob("SKILL.md"):
            rel = skill_md.relative_to(REPO_ROOT).parent
            skills[str(rel)] = skill_md
    return skills


def main():
    if not HAS_YAML:
        print("ERROR: PyYAML is required. Install: pip install pyyaml")
        return 1

    errors = []
    warnings = []

    # 1. Load registry
    if not REGISTRY_PATH.exists():
        errors.append("registry.yaml not found")
        print_errors(errors, warnings)
        return 1

    registry_text = REGISTRY_PATH.read_text()
    try:
        registry = load_yaml(registry_text)
    except Exception as e:
        errors.append(f"registry.yaml: failed to parse: {e}")
        print_errors(errors, warnings)
        return 1

    if not isinstance(registry, dict):
        errors.append("registry.yaml: root must be a mapping")
        print_errors(errors, warnings)
        return 1

    reg_skills = registry.get("skills", [])
    if reg_skills is None:
        reg_skills = []
    if not isinstance(reg_skills, list):
        errors.append("registry.yaml: 'skills' must be a list")
        print_errors(errors, warnings)
        return 1

    # Build registry index
    reg_by_path = {}
    reg_by_name = {}
    for entry in reg_skills:
        if not isinstance(entry, dict):
            errors.append(f"registry.yaml: entry is not a mapping: {entry}")
            continue
        path = entry.get("path")
        name = entry.get("name")
        if path:
            reg_by_path[path] = entry
        if name:
            reg_by_name[name] = entry

    # 2 & 3. Cross-check registry vs disk
    disk_skills = find_skill_files()

    # Registry entries that don't exist on disk
    for path, entry in sorted(reg_by_path.items()):
        skill_md = REPO_ROOT / path / "SKILL.md"
        if not skill_md.exists():
            errors.append(
                f"registry entry '{entry.get('name', path)}': SKILL.md not found at {path}/SKILL.md"
            )

    # Skills on disk not in registry
    for path, skill_md in sorted(disk_skills.items()):
        if path not in reg_by_path:
            warnings.append(f"{path}/SKILL.md exists on disk but has no registry entry")

    # 4. Cross-check name/version match
    for path, entry in sorted(reg_by_path.items()):
        skill_md = REPO_ROOT / path / "SKILL.md"
        if not skill_md.exists():
            continue  # already reported above

        fm_errors = validate_skill_md(skill_md)
        errors.extend(fm_errors)
        if fm_errors:
            continue  # skip name/version check if frontmatter is broken

        fm, _ = parse_frontmatter(skill_md.read_text())
        if fm is None:
            continue  # validate_skill_md already reported the error
        reg_name = entry.get("name")
        reg_version = str(entry.get("version", ""))

        if fm.get("name") != reg_name:
            errors.append(
                f"{path}: registry name '{reg_name}' != SKILL.md name '{fm.get('name')}'"
            )

        fm_version = str(fm.get("version", ""))
        if reg_version and fm_version and reg_version != fm_version:
            errors.append(
                f"{path}: registry version '{reg_version}' != SKILL.md version '{fm_version}'"
            )

    # 5. Also validate all on-disk skills (even those without registry entries,
    #    so contributors catch frontmatter issues early)
    for path, skill_md in sorted(disk_skills.items()):
        fm_errors = validate_skill_md(skill_md)
        if path in reg_by_path:
            continue  # already validated above
        errors.extend(fm_errors)

    print_errors(errors, warnings)
    return 1 if errors else 0


def print_errors(errors, warnings):
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    total = len(errors)
    warn_total = len(warnings)
    if total == 0:
        if warn_total:
            print(f"\n✓ Valid ({warn_total} warning(s))")
        else:
            print("\n✓ Valid")
    else:
        print(f"\n✗ {total} error(s), {warn_total} warning(s)")


if __name__ == "__main__":
    sys.exit(main())
