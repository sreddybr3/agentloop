# Agent Skills

Agent Skills is an open format for extending AI agent capabilities with specialized knowledge and workflows. Skills are folders containing instructions, scripts, and resources that agents can discover and use to perform better at specific tasks. The format is maintained by Anthropic and designed to be portable across different AI agents and development tools including VS Code with GitHub Copilot, Claude Code, and OpenAI Codex.

The core mechanism uses progressive disclosure to manage context efficiently: agents load only skill names and descriptions at startup, then load full instructions when a skill is activated, and finally load supporting files (scripts, references, assets) only when needed. This keeps the base context small while giving agents access to specialized knowledge on demand. Skills are self-documenting, extensible, and easy to version control and share.

## SKILL.md File Format

Every skill requires a `SKILL.md` file with YAML frontmatter containing `name` and `description` fields, followed by Markdown instructions. The name must be lowercase, use only letters, numbers, and hyphens, and match the parent directory name.

```markdown
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
compatibility: Requires Python 3.10+ and pdfplumber
metadata:
  author: example-org
  version: "1.0"
allowed-tools: Bash(python:*) Read
---

# PDF Processing

## When to use this skill
Use this skill when the user needs to work with PDF files.

## How to extract text
Use pdfplumber for text extraction:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## How to fill forms
1. Analyze form fields: `python scripts/analyze_form.py input.pdf`
2. Create field mapping in `field_values.json`
3. Fill the form: `python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

## Skill Directory Structure

A skill is a directory containing a `SKILL.md` file and optional supporting directories for scripts, references, and assets. Scripts should be self-contained or clearly document dependencies.

```
my-skill/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
│   ├── extract.py
│   └── validate.sh
├── references/       # Optional: documentation
│   └── REFERENCE.md
└── assets/           # Optional: templates, resources
    └── template.json
```

## CLI: Validate a Skill

The `skills-ref` CLI validates that a skill has proper frontmatter, correct naming conventions, and required fields. Returns exit code 0 for valid skills, 1 for validation errors.

```bash
# Install skills-ref
python -m venv .venv
source .venv/bin/activate
pip install -e ./skills-ref

# Validate a skill directory
skills-ref validate ./my-skill

# Output on success:
# Valid skill: ./my-skill

# Output on failure:
# Validation failed for ./my-skill:
#   - Skill name 'My-Skill' must be lowercase
#   - Directory name 'my-skill' must match skill name 'My-Skill'
```

## CLI: Read Skill Properties

Extract skill metadata from the YAML frontmatter and output as JSON. Useful for programmatic access to skill information.

```bash
skills-ref read-properties ./pdf-processing

# Output:
# {
#   "name": "pdf-processing",
#   "description": "Extract PDF text, fill forms, merge files. Use when handling PDFs.",
#   "license": "Apache-2.0",
#   "compatibility": "Requires Python 3.10+ and pdfplumber",
#   "metadata": {
#     "author": "example-org",
#     "version": "1.0"
#   }
# }
```

## CLI: Generate Prompt XML

Generate the `<available_skills>` XML block for inclusion in agent system prompts. This format is recommended for Anthropic's Claude models.

```bash
skills-ref to-prompt ./pdf-processing ./data-analysis

# Output:
# <available_skills>
# <skill>
# <name>
# pdf-processing
# </name>
# <description>
# Extract PDF text, fill forms, merge files. Use when handling PDFs.
# </description>
# <location>
# /path/to/pdf-processing/SKILL.md
# </location>
# </skill>
# <skill>
# <name>
# data-analysis
# </name>
# <description>
# Analyze datasets, generate charts, and create summary reports.
# </description>
# <location>
# /path/to/data-analysis/SKILL.md
# </location>
# </skill>
# </available_skills>
```

## Python API: validate()

Validate a skill directory and return a list of validation error messages. An empty list means the skill is valid.

```python
from pathlib import Path
from skills_ref import validate

# Validate a valid skill
errors = validate(Path("./pdf-processing"))
if not errors:
    print("Skill is valid!")
else:
    for error in errors:
        print(f"Error: {error}")

# Example validation errors:
# - Missing required field in frontmatter: name
# - Skill name 'PDF-Processing' must be lowercase
# - Directory name 'pdf-skill' must match skill name 'pdf-processing'
# - Description exceeds 1024 character limit (1250 chars)
# - Skill name cannot start or end with a hyphen
```

## Python API: read_properties()

Parse the YAML frontmatter from a skill's SKILL.md file and return a `SkillProperties` object with all metadata fields.

```python
from pathlib import Path
from skills_ref import read_properties, ParseError, ValidationError

try:
    props = read_properties(Path("./pdf-processing"))

    # Access required fields
    print(f"Name: {props.name}")
    print(f"Description: {props.description}")

    # Access optional fields (may be None)
    print(f"License: {props.license}")
    print(f"Compatibility: {props.compatibility}")
    print(f"Allowed Tools: {props.allowed_tools}")
    print(f"Metadata: {props.metadata}")

    # Convert to dictionary (excludes None values)
    data = props.to_dict()
    # {'name': 'pdf-processing', 'description': '...', 'license': 'Apache-2.0', ...}

except ParseError as e:
    print(f"Failed to parse SKILL.md: {e}")
except ValidationError as e:
    print(f"Invalid skill properties: {e}")
```

## Python API: to_prompt()

Generate the `<available_skills>` XML block for multiple skill directories. Use this to build the skill catalog section of an agent's system prompt.

```python
from pathlib import Path
from skills_ref import to_prompt

# Generate prompt for multiple skills
skill_dirs = [
    Path("./skills/pdf-processing"),
    Path("./skills/data-analysis"),
    Path("./skills/code-review")
]

xml_prompt = to_prompt(skill_dirs)
print(xml_prompt)

# Output:
# <available_skills>
# <skill>
# <name>
# pdf-processing
# </name>
# <description>
# Extract PDF text, fill forms, merge files. Use when handling PDFs.
# </description>
# <location>
# /absolute/path/to/skills/pdf-processing/SKILL.md
# </location>
# </skill>
# ...
# </available_skills>

# Use in agent system prompt
system_prompt = f"""
You are an AI assistant with access to specialized skills.

{xml_prompt}

When a task matches a skill's description, read the SKILL.md at the listed location.
"""
```

## Python API: find_skill_md()

Locate the SKILL.md file within a skill directory. Prefers uppercase `SKILL.md` but accepts lowercase `skill.md`.

```python
from pathlib import Path
from skills_ref import find_skill_md

# Find SKILL.md in a directory
skill_md_path = find_skill_md(Path("./my-skill"))

if skill_md_path:
    print(f"Found skill file at: {skill_md_path}")
    content = skill_md_path.read_text()
else:
    print("No SKILL.md found in directory")
```

## Python API: SkillProperties Model

The `SkillProperties` dataclass represents parsed skill metadata with required and optional fields.

```python
from skills_ref import SkillProperties

# Create SkillProperties directly
props = SkillProperties(
    name="my-skill",
    description="A custom skill for specific tasks.",
    license="MIT",
    compatibility="Requires Node.js 18+",
    allowed_tools="Bash(npm:*) Read Write",
    metadata={"author": "myteam", "version": "2.0"}
)

# Convert to dictionary for serialization
data = props.to_dict()
# {
#   "name": "my-skill",
#   "description": "A custom skill for specific tasks.",
#   "license": "MIT",
#   "compatibility": "Requires Node.js 18+",
#   "allowed-tools": "Bash(npm:*) Read Write",
#   "metadata": {"author": "myteam", "version": "2.0"}
# }

import json
print(json.dumps(data, indent=2))
```

## Error Handling

The library provides specific exception types for different error conditions. All exceptions inherit from `SkillError`.

```python
from pathlib import Path
from skills_ref import validate, read_properties, SkillError, ParseError, ValidationError

skill_path = Path("./my-skill")

try:
    # Attempt to read properties
    props = read_properties(skill_path)
    print(f"Loaded skill: {props.name}")

except ParseError as e:
    # SKILL.md is missing or has invalid YAML
    print(f"Parse error: {e}")
    # Examples:
    # - "SKILL.md not found in ./my-skill"
    # - "SKILL.md must start with YAML frontmatter (---)"
    # - "Invalid YAML in frontmatter: ..."

except ValidationError as e:
    # Required fields are missing or invalid
    print(f"Validation error: {e}")
    print(f"All errors: {e.errors}")
    # Examples:
    # - "Missing required field in frontmatter: name"
    # - "Field 'description' must be a non-empty string"

except SkillError as e:
    # Catch-all for any skill-related error
    print(f"Skill error: {e}")
```

## Self-Contained Python Scripts with Inline Dependencies

Skills can bundle scripts that declare their own dependencies using PEP 723 inline metadata. Run with `uv run` for automatic dependency resolution.

```python
# scripts/extract.py
# /// script
# dependencies = [
#   "beautifulsoup4>=4.12,<5",
#   "requests>=2.31",
# ]
# requires-python = ">=3.10"
# ///

import sys
from bs4 import BeautifulSoup
import requests

def extract_text(url: str) -> str:
    """Extract text content from a webpage."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.decompose()

    return soup.get_text(separator="\n", strip=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run scripts/extract.py <url>", file=sys.stderr)
        sys.exit(1)

    text = extract_text(sys.argv[1])
    print(text)
```

```bash
# Run the script (uv automatically installs dependencies)
uv run scripts/extract.py https://example.com
```

## Integrating Skills into an Agent

Client implementors should follow the progressive disclosure pattern: discover skills at startup, disclose the catalog to the model, and activate skills on demand.

```python
from pathlib import Path
from skills_ref import read_properties, to_prompt, find_skill_md

# Step 1: Discover skills from standard locations
skill_locations = [
    Path.home() / ".agents/skills",           # User-level skills
    Path.cwd() / ".agents/skills",            # Project-level skills
]

discovered_skills = []
for location in skill_locations:
    if location.exists():
        for skill_dir in location.iterdir():
            if skill_dir.is_dir() and find_skill_md(skill_dir):
                try:
                    props = read_properties(skill_dir)
                    discovered_skills.append({
                        "name": props.name,
                        "description": props.description,
                        "path": skill_dir
                    })
                except Exception as e:
                    print(f"Warning: Failed to load {skill_dir}: {e}")

# Step 2: Generate catalog for system prompt
skill_dirs = [s["path"] for s in discovered_skills]
catalog_xml = to_prompt(skill_dirs)

system_prompt = f"""
You are an AI assistant with access to specialized skills.

The following skills provide specialized instructions for specific tasks.
When a task matches a skill's description, read the SKILL.md at the listed location.

{catalog_xml}
"""

# Step 3: Activate skills when model requests them
def activate_skill(skill_name: str) -> str:
    """Load full skill instructions when the model activates a skill."""
    for skill in discovered_skills:
        if skill["name"] == skill_name:
            skill_md = find_skill_md(skill["path"])
            return skill_md.read_text()
    return f"Error: Skill '{skill_name}' not found"

# Example activation
instructions = activate_skill("pdf-processing")
```

## Summary

Agent Skills provides a standardized way to extend AI agent capabilities through portable, version-controlled packages of instructions and code. The format supports use cases ranging from simple text-based instructions to complex workflows with bundled scripts, references, and assets. Skills work across multiple AI agents and development tools, making organizational knowledge and specialized procedures shareable and reusable.

The `skills-ref` reference library offers both CLI and Python API interfaces for validating skills, reading their properties, and generating prompt XML for agent integration. Client implementors can use the library to build skills-compatible agents that discover, catalog, and activate skills following the progressive disclosure pattern. The format's simplicity (just a `SKILL.md` file at minimum) combined with its extensibility (optional scripts, references, assets) makes it suitable for everything from quick personal automations to enterprise-wide knowledge capture.
