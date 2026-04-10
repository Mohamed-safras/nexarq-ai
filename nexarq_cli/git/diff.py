"""
Git diff extraction engine – fully dynamic, real-time detection.

Nothing is hardcoded:
  - Language detected from content, shebang, keywords, AND extension
  - Commit metadata (author, branch, timestamp) from real git
  - Change type inferred from commit message and modified file patterns
  - Repo type derived from project manifest files present on disk
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ── Language detection ────────────────────────────────────────────────────────

# Extension hint (lowest priority – content wins over this)
_EXT_HINTS: dict[str, str] = {
    ".py": "python",      ".pyw": "python",
    ".js": "javascript",  ".mjs": "javascript",  ".cjs": "javascript",
    ".ts": "typescript",  ".tsx": "typescript",  ".jsx": "javascript",
    ".java": "java",      ".kt": "kotlin",       ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",        ".cxx": "cpp",         ".cc": "cpp",
    ".c": "c",            ".h": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",    ".sc": "scala",
    ".sh": "bash",        ".bash": "bash",       ".zsh": "bash",
    ".ps1": "powershell",
    ".yaml": "yaml",      ".yml": "yaml",
    ".json": "json",      ".jsonc": "json",
    ".toml": "toml",
    ".tf": "terraform",   ".tfvars": "terraform",
    ".sql": "sql",
    ".html": "html",      ".htm": "html",
    ".css": "css",        ".scss": "scss",       ".less": "less",
    ".vue": "vue",
    ".svelte": "svelte",
    ".r": "r",            ".R": "r",
    ".dart": "dart",
    ".ex": "elixir",      ".exs": "elixir",
    ".elm": "elm",
    ".hs": "haskell",
    ".lua": "lua",
    ".m": "objective-c",  ".mm": "objective-c",
    ".pl": "perl",
    ".xml": "xml",        ".xsd": "xml",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
    ".md": "markdown",    ".mdx": "markdown",
    ".ipynb": "python",
    # Template / DSL extensions (no content needed)
    ".erb": "ruby",       ".slim": "ruby",       ".haml": "ruby",
    ".j2": "html",        ".jinja": "html",      ".jinja2": "html",
    ".njk": "html",       ".hbs": "javascript",  ".mustache": "html",
    ".liquid": "html",    ".pug": "html",        ".jade": "html",
    ".blade": "php",      ".twig": "html",
    ".nix": "nix",        ".pkl": "pkl",
}

# Shebang → language (highest priority)
_SHEBANG_MAP: list[tuple[str, str]] = [
    ("python3", "python"), ("python", "python"),
    ("node", "javascript"), ("nodejs", "javascript"), ("ts-node", "typescript"),
    ("ruby", "ruby"), ("perl", "perl"), ("php", "php"),
    ("bash", "bash"), ("sh", "bash"), ("zsh", "bash"),
    ("pwsh", "powershell"), ("powershell", "powershell"),
    ("Rscript", "r"),
]

# Filename → language (special files)
_FILENAME_MAP: dict[str, str] = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "gnumakefile": "makefile",
    "vagrantfile": "ruby",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "podfile": "ruby",
    "fastfile": "ruby",
    "brewfile": "ruby",
    "cmakelists.txt": "cmake",
    ".eslintrc": "json",
    ".babelrc": "json",
    "package.json": "json",
    "tsconfig.json": "json",
    ".gitignore": "text",
    ".env": "dotenv",
    ".env.example": "dotenv",
    "requirements.txt": "pip-requirements",
    "pyproject.toml": "toml",
    "cargo.toml": "toml",
    "go.mod": "go-modules",
    "go.sum": "go-modules",
}

# Content keyword patterns (middle priority – beats extension, loses to shebang)
_CONTENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # High-confidence language-specific patterns first
    (re.compile(r"^syntax\s*=\s*\"proto", re.M), "protobuf"),
    (re.compile(r"^(type|query|mutation|subscription|fragment)\s+\w+(\s+on\s+\w+)?\s*\{", re.M), "graphql"),
    (re.compile(r"resource\s+\"\w+\"\s+\"\w+\"\s*\{|^terraform\s*\{|^provider\s+\"\w+\"", re.M), "terraform"),
    (re.compile(r"^(FROM|RUN|COPY|EXPOSE|ENV|CMD|ENTRYPOINT)\s", re.M), "dockerfile"),
    # General-purpose patterns
    (re.compile(r"^import\s+\w|^from\s+\w+\s+import|^def\s+\w+\s*\(|^async\s+def\s+\w+", re.M), "python"),
    (re.compile(r"^func\s+\w+|^package\s+\w+\s*\n|^import\s+\"", re.M), "go"),
    (re.compile(r"^fn\s+\w+|^use\s+std::|^impl\s+\w+|->.*Result<", re.M), "rust"),
    (re.compile(r"^(public|private|protected)\s+(static\s+)?(class|void|int|String)\b", re.M), "java"),
    (re.compile(r"^using\s+System\.|^namespace\s+\w+|public\s+class\s+\w+\s*:", re.M), "csharp"),
    # TypeScript requires explicit type annotations (not just 'type Foo')
    (re.compile(r":\s*(string|number|boolean|void|never|unknown|any)\b|^export\s+(interface|type|enum)\s+\w+", re.M), "typescript"),
    (re.compile(r"^(const|let|var)\s+\w+\s*=|^function\s+\w+|=>\s*\{|require\(", re.M), "javascript"),
    (re.compile(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE\s+TABLE|ALTER\s+TABLE)\b", re.M | re.I), "sql"),
    (re.compile(r"^(#include|namespace\s+\w+|template\s*<)", re.M), "cpp"),
    (re.compile(r"^def\s+\w+|^class\s+\w+.*\n.*end$|^require\s+['\"]", re.M), "ruby"),
    (re.compile(r"^\s*- name:|\s+tasks:|\s+hosts:", re.M), "yaml"),
]


def _detect_language(path: str, content: str = "") -> str:
    """
    Detect language from real-time code analysis – no hardcoded assumptions.

    Priority chain (highest → lowest):
      1. Shebang line (#! interpreter)
      2. Special filename (Dockerfile, Makefile, etc.)
      3. Content structural analysis (syntax patterns, keywords)
      4. File extension hint
      5. Best-effort content fingerprint (byte patterns, whitespace structure)
      6. 'text' as universal fallback

    Works for ANY file type – unknown extensions, no extension, binary hints,
    config formats, DSLs, templates, and future languages not yet in any map.
    """
    p = Path(path)
    name_lower = p.name.lower()
    suffix = p.suffix.lower()

    # 1. Shebang line
    if content:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped:
                if stripped.startswith("#!"):
                    shebang = stripped.lower()
                    for keyword, lang in _SHEBANG_MAP:
                        if keyword in shebang:
                            return lang
                break

    # 2. Special filename (exact match, no extension)
    if name_lower in _FILENAME_MAP:
        return _FILENAME_MAP[name_lower]

    # 3. Structural content analysis (works regardless of extension)
    if content and len(content) > 10:
        for pattern, lang in _CONTENT_PATTERNS:
            if pattern.search(content):
                return lang

    # 4. Extension hint
    if suffix in _EXT_HINTS:
        return _EXT_HINTS[suffix]

    # 5. Best-effort fingerprint for unknown file types
    if content:
        lang = _fingerprint_content(content, name_lower)
        if lang:
            return lang

    return "text"


def _fingerprint_content(content: str, filename: str) -> str | None:
    """
    Fingerprint unknown file content to detect language without extension.

    This handles:
      - No-extension scripts
      - Unusual extensions (.blade, .njk, .j2, .erb, etc.)
      - Config DSLs (HCL, Nix, Pkl, etc.)
      - Template languages
    """
    # Score-based detection: accumulate signals
    scores: dict[str, int] = {}

    def bump(lang: str, pts: int = 1) -> None:
        scores[lang] = scores.get(lang, 0) + pts

    lines = content.splitlines()
    first_500 = content[:500]

    # Indentation style
    py_indent = sum(1 for l in lines if l.startswith("    ") and not l.startswith("        "))
    if py_indent > 3:
        bump("python")

    # Comment style
    if re.search(r"^\s*//", content, re.M):
        bump("javascript", 1); bump("java", 1); bump("go", 1); bump("cpp", 1)
    if re.search(r"^\s*#", content, re.M):
        bump("python", 1); bump("ruby", 1); bump("bash", 1); bump("yaml", 1)
    if re.search(r"^\s*--", content, re.M):
        bump("sql", 2); bump("lua", 1)
    if re.search(r"^\s*<!--", content, re.M):
        bump("html", 2); bump("xml", 1)
    if re.search(r"^\s*\{-", content, re.M):
        bump("haskell", 3)

    # Template markers
    if re.search(r"\{\{.*?\}\}", first_500):
        bump("javascript")  # Handlebars/Mustache/Jinja
    if re.search(r"\{%.*?%\}", first_500):
        bump("html")        # Django/Jinja templates

    # HCL / Terraform
    if re.search(r'^\s*(resource|provider|variable|output|locals)\s+"', content, re.M):
        bump("terraform", 5)

    # Nix
    if re.search(r"^\s*(let|in|with|rec)\s+\{", content, re.M):
        bump("nix", 5)

    # Pkl (Apple config)
    if re.search(r"^amends\s+\"|^import\s+\"pkl:", content, re.M):
        return "pkl"

    # TOML
    if re.search(r"^\[[\w.]+\]", content, re.M) and re.search(r"^\w+\s*=", content, re.M):
        bump("toml", 4)

    # INI / properties
    if re.search(r"^\s*\[.+\]\s*$", content, re.M) and re.search(r"^\s*\w+\s*=\s*\S", content, re.M):
        bump("ini", 3)

    # Nginx/Apache config
    if re.search(r"^\s*(server|location|upstream)\s*\{", content, re.M):
        return "nginx"

    # GraphQL
    if re.search(r"^(type|query|mutation|subscription|fragment)\s+\w+", content, re.M):
        bump("graphql", 5)

    # Protocol Buffers
    if re.search(r"^syntax\s*=\s*\"proto", content, re.M):
        return "protobuf"

    # Solidity (smart contracts)
    if re.search(r"^pragma\s+solidity\s|^contract\s+\w+\s*\{", content, re.M):
        return "solidity"

    # WASM text format
    if re.search(r"^\(module\b", content, re.M):
        return "wasm"

    # Filename suffix hints for template/DSL files
    template_map = {
        ".erb": "ruby", ".slim": "ruby", ".haml": "ruby",
        ".j2": "html", ".jinja": "html", ".njk": "html",
        ".blade": "php", ".twig": "html",
        ".hbs": "javascript", ".mustache": "html",
        ".liquid": "html",
        ".pug": "html", ".jade": "html",
        ".nix": "nix", ".pkl": "pkl",
    }
    for ext, lang in template_map.items():
        if filename.endswith(ext):
            return lang

    if not scores:
        return None
    return max(scores, key=lambda k: scores[k])


# ── Change type inference ─────────────────────────────────────────────────────

_COMMIT_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(fix|bugfix|hotfix|patch|repair)\b", re.I), "bug_fix"),
    (re.compile(r"^(feat|feature|add|new|implement)\b", re.I), "new_feature"),
    (re.compile(r"^(refactor|cleanup|clean|restructure|reorganize)\b", re.I), "refactor"),
    (re.compile(r"^(docs|documentation|readme)\b", re.I), "documentation"),
    (re.compile(r"^(test|spec|coverage)\b", re.I), "testing"),
    (re.compile(r"^(perf|performance|optimize|optimise|speed)\b", re.I), "performance"),
    (re.compile(r"^(chore|ci|build|deps|dependency|upgrade)\b", re.I), "chore"),
    (re.compile(r"^(security|sec|vuln|vulnerability|cve)\b", re.I), "security"),
    (re.compile(r"^(revert)\b", re.I), "revert"),
    (re.compile(r"^(style|format|lint|linting)\b", re.I), "style"),
]


def _infer_change_type(commit_message: str, file_paths: list[str]) -> str:
    """Infer the type of change from commit message and file patterns."""
    msg = commit_message.strip().lower()

    # Conventional commits: type(scope): message
    cc_match = re.match(r"^(\w+)(\(.+\))?!?:", msg)
    if cc_match:
        prefix = cc_match.group(1).lower()
        type_map = {
            "fix": "bug_fix", "feat": "new_feature", "refactor": "refactor",
            "docs": "documentation", "test": "testing", "perf": "performance",
            "chore": "chore", "ci": "chore", "build": "chore",
            "style": "style", "revert": "revert", "sec": "security",
        }
        if prefix in type_map:
            return type_map[prefix]

    # Free-form commit message
    for pattern, change_type in _COMMIT_TYPE_PATTERNS:
        if pattern.match(commit_message.strip()):
            return change_type

    # File-based inference
    for fp in file_paths:
        fl = fp.lower()
        if "migration" in fl or ".sql" in fl:
            return "database_change"
        if "test" in fl or "spec" in fl:
            return "testing"
        if "security" in fl or "auth" in fl or "crypto" in fl:
            return "security"

    return "general"


# ── Repo type detection ───────────────────────────────────────────────────────

def _detect_repo_type(repo_root: Path) -> dict[str, str]:
    """
    Detect project ecosystem from manifest files present in the repo.
    Returns dict of {ecosystem: primary_language}.
    """
    indicators: dict[str, str] = {}
    checks = [
        ("package.json", "nodejs"),
        ("pyproject.toml", "python"), ("setup.py", "python"), ("requirements.txt", "python"),
        ("Cargo.toml", "rust"),
        ("go.mod", "go"),
        ("pom.xml", "java"), ("build.gradle", "java"), ("build.gradle.kts", "kotlin"),
        ("*.csproj", "csharp"),
        ("Gemfile", "ruby"),
        ("composer.json", "php"),
        ("mix.exs", "elixir"),
        ("pubspec.yaml", "dart"),
    ]
    for filename, ecosystem in checks:
        if "*" in filename:
            if list(repo_root.glob(filename)):
                indicators[ecosystem] = ecosystem
        elif (repo_root / filename).exists():
            indicators[ecosystem] = ecosystem
    return indicators


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class FileDiff:
    path: str
    language: str
    added_lines: int
    removed_lines: int
    content: str
    is_new_file: bool = False
    is_deleted: bool = False
    is_binary: bool = False


@dataclass
class DiffResult:
    commit_hash: str
    commit_message: str
    files: list[FileDiff] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0

    # Real-time context (populated from live git data)
    branch: str = "unknown"
    author: str = "unknown"
    author_email: str = ""
    commit_timestamp: str = ""
    change_type: str = "general"            # inferred from message + files
    repo_ecosystems: dict[str, str] = field(default_factory=dict)
    all_languages: list[str] = field(default_factory=list)  # all langs in diff

    @property
    def primary_language(self) -> str:
        """Language of the file with most changes (not hardcoded)."""
        if not self.files:
            return "unknown"
        return max(self.files, key=lambda f: f.added_lines + f.removed_lines).language

    @property
    def is_multi_language(self) -> bool:
        return len(set(f.language for f in self.files)) > 1

    @property
    def has_new_files(self) -> bool:
        return any(f.is_new_file for f in self.files)

    @property
    def has_test_files(self) -> bool:
        return any(
            "test" in f.path.lower() or "spec" in f.path.lower()
            for f in self.files
        )

    @property
    def has_config_files(self) -> bool:
        cfg_exts = {".yaml", ".yml", ".toml", ".json", ".env", ".ini", ".cfg", ".conf"}
        return any(Path(f.path).suffix.lower() in cfg_exts for f in self.files)

    @property
    def has_migration_files(self) -> bool:
        return any(
            "migration" in f.path.lower() or f.language == "sql"
            for f in self.files
        )

    @property
    def has_security_sensitive_files(self) -> bool:
        sensitive = {"auth", "login", "password", "secret", "token", "credential",
                     "oauth", "jwt", "crypto", "encrypt", "permission", "access"}
        return any(
            any(kw in f.path.lower() for kw in sensitive)
            for f in self.files
        )

    def combined_diff(self, max_lines: int = 5000) -> str:
        lines: list[str] = []
        line_count = 0
        for f in self.files:
            header = f"### {f.path} ({f.language})"
            lines.append(header)
            lines.append(f.content)
            line_count += len(f.content.splitlines()) + 1
            if line_count > max_lines:
                lines.append("\n[... diff truncated by Nexarq max_diff_lines limit ...]")
                break
        return "\n".join(lines)

    def context_summary(self) -> str:
        """Human-readable summary of this diff's context for agents."""
        return (
            f"Branch: {self.branch} | Author: {self.author} | "
            f"Change type: {self.change_type} | "
            f"Languages: {', '.join(self.all_languages) or self.primary_language} | "
            f"Files: {len(self.files)} | "
            f"+{self.total_added} / -{self.total_removed} lines"
        )


# ── Diff engine ───────────────────────────────────────────────────────────────

class DiffEngine:
    """
    Extracts diffs from a Git repository with full runtime context.

    Everything is derived from actual git state — no hardcoded commit
    patterns, language lists, or branch assumptions.
    """

    def __init__(
        self,
        repo_path: str | Path = ".",
        exclude_patterns: list[str] | None = None,
        max_diff_lines: int = 5000,
    ) -> None:
        self.repo_path = Path(repo_path)
        # If no exclude patterns, derive from repo type at runtime
        self._user_excludes = exclude_patterns
        self.max_diff_lines = max_diff_lines

    # ── public ───────────────────────────────────────────────────────────────

    def last_commit(self) -> DiffResult:
        """Extract diff for the most recent commit with full git context."""
        repo = self._open_repo()
        head = repo.head.commit

        if not head.parents:
            raw = repo.git.diff("4b825dc642cb6eb9a060e54bf8d69288fbee4904", "HEAD")
        else:
            raw = repo.git.diff(f"{head.hexsha}^", head.hexsha)

        return self._parse_diff(
            raw,
            commit_hash=head.hexsha[:12],
            message=head.message.strip(),
            repo=repo,
            commit=head,
        )

    def staged(self) -> DiffResult:
        """Extract staged diff for pre-push hook."""
        repo = self._open_repo()
        raw = repo.git.diff("--cached")
        head = repo.head.commit
        return self._parse_diff(
            raw,
            commit_hash=head.hexsha[:12],
            message="[staged changes]",
            repo=repo,
            commit=head,
        )

    def between(self, base: str, target: str = "HEAD") -> DiffResult:
        """Extract diff between two refs (e.g. main..feature-branch)."""
        repo = self._open_repo()
        raw = repo.git.diff(base, target)
        head = repo.commit(target)
        return self._parse_diff(
            raw,
            commit_hash=f"{base}..{target}",
            message=f"[diff {base}..{target}]",
            repo=repo,
            commit=head,
        )

    def from_text(self, diff_text: str, language: str = "") -> DiffResult:
        """Parse an arbitrary diff string (nexarq run --diff)."""
        result = self._parse_diff(diff_text, commit_hash="manual", message="[manual diff]")
        return result

    # ── internal ─────────────────────────────────────────────────────────────

    def _open_repo(self):
        try:
            import git
        except ImportError:
            raise RuntimeError("gitpython not installed. Run: pip install gitpython")
        return git.Repo(self.repo_path, search_parent_directories=True)

    def _get_exclude_patterns(self, repo_root: Path) -> list[str]:
        """Derive exclusion patterns from the actual repo ecosystem."""
        if self._user_excludes is not None:
            return self._user_excludes

        # Always exclude binary/generated artifacts
        base = [
            "*.min.js", "*.min.css",
            "dist/*", "build/*", "out/*", ".next/*", "__pycache__/*",
            "*.pb.go", "*.pb.py",  # generated protobuf
        ]

        root = repo_root
        # Ecosystem-specific
        if (root / "package.json").exists():
            base += ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "node_modules/*"]
        if (root / "Cargo.toml").exists():
            base += ["Cargo.lock", "target/*"]
        if (root / "Gemfile").exists():
            base += ["Gemfile.lock"]
        if (root / "go.mod").exists():
            base += ["go.sum", "vendor/*"]
        if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
            base += ["*.egg-info/*", "poetry.lock", "uv.lock"]
        if (root / "pom.xml").exists():
            base += ["*.class", "*.jar"]
        if list(root.glob("*.csproj")):
            base += ["*.dll", "*.exe", "obj/*", "bin/*"]

        return base

    def _parse_diff(
        self,
        raw: str,
        commit_hash: str,
        message: str,
        repo=None,
        commit=None,
    ) -> DiffResult:
        # Extract real git metadata if available
        branch = "unknown"
        author = "unknown"
        author_email = ""
        commit_timestamp = ""
        repo_root = self.repo_path

        if repo is not None:
            try:
                branch = repo.active_branch.name
            except TypeError:
                branch = "detached-HEAD"
            repo_root = Path(repo.working_dir)

        if commit is not None:
            author = commit.author.name or "unknown"
            author_email = commit.author.email or ""
            commit_timestamp = datetime.fromtimestamp(commit.committed_date).isoformat()

        exclude_patterns = self._get_exclude_patterns(repo_root)
        compiled_excludes = [
            re.compile(self._glob_to_re(p)) for p in exclude_patterns
        ]

        files: list[FileDiff] = []
        total_added = 0
        total_removed = 0

        file_sections = re.split(r"(?=^diff --git )", raw, flags=re.MULTILINE)

        for section in file_sections:
            if not section.strip():
                continue

            m = re.search(r"^diff --git a/(.+?) b/(.+?)$", section, re.MULTILINE)
            if not m:
                continue

            path = m.group(2)

            if any(p.search(path) for p in compiled_excludes):
                continue

            # Detect file-level flags
            is_new = bool(re.search(r"^new file mode", section, re.MULTILINE))
            is_deleted = bool(re.search(r"^deleted file mode", section, re.MULTILINE))
            is_binary = bool(re.search(r"^Binary files", section, re.MULTILINE))

            # Extract diff content (hunk lines only) for content-based lang detection
            hunk_content = "\n".join(
                line[1:] for line in section.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            )

            added = len(re.findall(r"^\+(?!\+\+)", section, re.MULTILINE))
            removed = len(re.findall(r"^-(?!--)", section, re.MULTILINE))
            total_added += added
            total_removed += removed

            # Detect language from content + path (real-time, not just extension)
            language = _detect_language(path, hunk_content)

            files.append(FileDiff(
                path=path,
                language=language,
                added_lines=added,
                removed_lines=removed,
                content=section,
                is_new_file=is_new,
                is_deleted=is_deleted,
                is_binary=is_binary,
            ))

        file_paths = [f.path for f in files]
        change_type = _infer_change_type(message, file_paths)
        ecosystems = _detect_repo_type(repo_root)
        all_languages = sorted(set(f.language for f in files if f.language != "text"))

        return DiffResult(
            commit_hash=commit_hash,
            commit_message=message,
            files=files,
            total_added=total_added,
            total_removed=total_removed,
            branch=branch,
            author=author,
            author_email=author_email,
            commit_timestamp=commit_timestamp,
            change_type=change_type,
            repo_ecosystems=ecosystems,
            all_languages=all_languages,
        )

    @staticmethod
    def _glob_to_re(pattern: str) -> str:
        return re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
