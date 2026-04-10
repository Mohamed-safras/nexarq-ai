"""
Diff cleaner — strips git metadata before sending to agents.

Raw git diff includes headers like:
  diff --git a/file.ts b/file.ts
  index abc123..def456 100644
  --- a/file.ts
  +++ b/file.ts
  @@ -10,6 +10,8 @@

These confuse small models which treat header text as code.
This module strips all metadata and presents only the actual changes
in a clean, agent-readable format.
"""
from __future__ import annotations

import re

# Languages where test/docstring/type analysis makes sense
CODE_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go", "rust", "ruby",
    "php", "swift", "kotlin", "scala", "cpp", "c", "csharp", "dart",
    "elixir", "haskell", "lua", "perl", "r", "objective-c",
}

# Languages that are purely documentation / config
DOC_LANGUAGES = {
    "markdown", "text", "rst", "asciidoc", "html",
}

CONFIG_LANGUAGES = {
    "yaml", "toml", "json", "xml", "ini", "dockerfile",
}


def clean_diff(raw_diff: str) -> str:
    """
    Convert raw git diff into a clean, model-readable format.

    Input (raw git diff):
        diff --git a/src/auth.ts b/src/auth.ts
        index abc..def 100644
        --- a/src/auth.ts
        +++ b/src/auth.ts
        @@ -10,6 +10,8 @@ class Auth {
         existing line
        +added line
        -removed line

    Output (clean):
        === src/auth.ts ===
         existing line
        +added line
        -removed line
    """
    result: list[str] = []
    current_file: str | None = None
    current_lines: list[str] = []

    def flush():
        if current_file and current_lines:
            # Only include if there are actual changes (+/- lines)
            has_changes = any(
                l.startswith("+") or l.startswith("-")
                for l in current_lines
            )
            if has_changes:
                result.append(f"\n=== {current_file} ===")
                result.extend(current_lines)

    for line in raw_diff.splitlines():
        # New file section
        if line.startswith("diff --git "):
            flush()
            current_lines = []
            # Extract "b/filename" path
            m = re.search(r" b/(.+)$", line)
            current_file = m.group(1) if m else line
            continue

        # Skip all git metadata lines
        if (line.startswith("index ")
                or line.startswith("new file mode")
                or line.startswith("deleted file mode")
                or line.startswith("old mode")
                or line.startswith("new mode")
                or line.startswith("rename from")
                or line.startswith("rename to")
                or line.startswith("similarity index")
                or line.startswith("Binary files")
                or line.startswith("--- ")
                or line.startswith("+++ ")):
            continue

        # Replace @@ hunk header with a blank separator
        if line.startswith("@@ "):
            current_lines.append("")
            continue

        # Keep content lines as-is
        current_lines.append(line)

    flush()
    return "\n".join(result).strip()


def is_code_diff(languages: set[str]) -> bool:
    """Return True if the diff contains at least one real code language."""
    return bool(languages & CODE_LANGUAGES)


def is_doc_only_diff(languages: set[str]) -> bool:
    """Return True if the diff contains ONLY documentation files."""
    return bool(languages) and not (languages & (CODE_LANGUAGES | CONFIG_LANGUAGES))
