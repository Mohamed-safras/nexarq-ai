"""Tests for git diff engine – language detection, context extraction, dynamic behaviour."""
from __future__ import annotations

import pytest
from pathlib import Path

from nexarq_cli.git.diff import (
    DiffEngine, DiffResult, FileDiff,
    _detect_language, _fingerprint_content, _infer_change_type, _detect_repo_type,
)


# ── Extension-based detection (still works) ───────────────────────────────────

class TestExtensionBasedDetection:
    def test_python(self):       assert _detect_language("app.py") == "python"
    def test_typescript(self):   assert _detect_language("src/index.tsx") == "typescript"
    def test_go(self):           assert _detect_language("main.go") == "go"
    def test_rust(self):         assert _detect_language("src/lib.rs") == "rust"
    def test_dockerfile(self):   assert _detect_language("Dockerfile") == "dockerfile"
    def test_sql(self):          assert _detect_language("schema.sql") == "sql"
    def test_yaml(self):         assert _detect_language("config.yml") == "yaml"
    def test_kotlin(self):       assert _detect_language("App.kt") == "kotlin"
    def test_scala(self):        assert _detect_language("Main.scala") == "scala"
    def test_elixir(self):       assert _detect_language("mix.exs") == "elixir"
    def test_dart(self):         assert _detect_language("main.dart") == "dart"


# ── Shebang-based detection ───────────────────────────────────────────────────

class TestShebangDetection:
    def test_python_shebang(self):
        content = "#!/usr/bin/env python3\nprint('hello')"
        assert _detect_language("script", content) == "python"

    def test_bash_shebang(self):
        content = "#!/bin/bash\necho hello"
        assert _detect_language("run", content) == "bash"

    def test_node_shebang(self):
        content = "#!/usr/bin/env node\nconsole.log('hi')"
        assert _detect_language("cli", content) == "javascript"

    def test_ruby_shebang(self):
        content = "#!/usr/bin/env ruby\nputs 'hi'"
        assert _detect_language("script", content) == "ruby"

    def test_shebang_beats_extension(self):
        # File has .txt extension but Python shebang
        content = "#!/usr/bin/env python3\nimport os"
        assert _detect_language("runner.txt", content) == "python"

    def test_no_shebang_no_extension_uses_content(self):
        content = "def foo():\n    return 1\n\nclass Bar:\n    pass"
        lang = _detect_language("mystery_file", content)
        assert lang == "python"


# ── Content-based detection (language-agnostic, no extension needed) ──────────

class TestContentBasedDetection:
    def test_python_from_content(self):
        content = "from nexarq_cli.models import User\n\ndef process(data):\n    return data"
        assert _detect_language("noext", content) == "python"

    def test_go_from_content(self):
        content = "package main\n\nimport \"fmt\"\n\nfunc main() {\n\tfmt.Println(\"hi\")\n}"
        assert _detect_language("noext", content) == "go"

    def test_java_from_content(self):
        content = "public class Hello {\n    public static void main(String[] args) {}\n}"
        assert _detect_language("noext", content) == "java"

    def test_rust_from_content(self):
        content = "use std::io;\nfn main() -> Result<(), io::Error> {\n    Ok(())\n}"
        assert _detect_language("noext", content) == "rust"

    def test_sql_from_content(self):
        content = "SELECT id, name FROM users WHERE active = TRUE"
        assert _detect_language("query", content) == "sql"

    def test_dockerfile_from_content(self):
        content = "FROM python:3.11\nRUN pip install nexarq\nCMD [\"nexarq\", \"run\"]"
        assert _detect_language("Dockerfile.prod", content) == "dockerfile"

    def test_terraform_from_content(self):
        content = 'resource "aws_s3_bucket" "data" {\n  bucket = "my-bucket"\n}'
        assert _detect_language("infra.tf.bak", content) == "terraform"

    def test_javascript_from_content(self):
        content = "const express = require('express')\nconst app = express()"
        assert _detect_language("server", content) == "javascript"


# ── Filename-based detection (special files) ──────────────────────────────────

class TestFilenameDetection:
    def test_makefile(self):      assert _detect_language("Makefile") == "makefile"
    def test_gemfile(self):       assert _detect_language("Gemfile") == "ruby"
    def test_vagrantfile(self):   assert _detect_language("Vagrantfile") == "ruby"
    def test_package_json(self):  assert _detect_language("package.json") == "json"
    def test_go_mod(self):        assert _detect_language("go.mod") == "go-modules"
    def test_requirements(self):  assert _detect_language("requirements.txt") == "pip-requirements"
    def test_dotenv(self):        assert _detect_language(".env") == "dotenv"


# ── Fingerprint for unknown/exotic file types ─────────────────────────────────

class TestFingerprintDetection:
    def test_graphql_detected(self):
        content = "type User {\n  id: ID!\n  name: String!\n}\n\nquery GetUser {\n  user { id }\n}"
        lang = _detect_language("schema.gql2", content)
        assert lang == "graphql"

    def test_protobuf_detected(self):
        content = 'syntax = "proto3";\nmessage User {\n  string name = 1;\n}'
        lang = _detect_language("user.proto2", content)
        assert lang == "protobuf"

    def test_toml_detected(self):
        content = "[package]\nname = \"myapp\"\nversion = \"1.0.0\"\n\n[dependencies]\n"
        lang = _detect_language("config.conf", content)
        assert lang in ("toml", "ini", "text")  # May match either config format

    def test_nginx_config(self):
        content = "server {\n  listen 80;\n  location / {\n    proxy_pass http://backend;\n  }\n}"
        lang = _detect_language("site.conf", content)
        assert lang == "nginx"

    def test_unknown_extension_returns_text(self):
        lang = _detect_language("data.xyz123")
        assert lang == "text"

    def test_erb_template(self):
        lang = _detect_language("view.html.erb")
        assert lang == "ruby"

    def test_jinja_template(self):
        lang = _detect_language("template.j2")
        assert lang == "html"


# ── Change type inference ─────────────────────────────────────────────────────

class TestChangeTypeInference:
    def test_conventional_commit_fix(self):
        assert _infer_change_type("fix: resolve null pointer in auth", []) == "bug_fix"

    def test_conventional_commit_feat(self):
        assert _infer_change_type("feat: add OAuth2 login", []) == "new_feature"

    def test_conventional_commit_refactor(self):
        assert _infer_change_type("refactor: extract auth helpers", []) == "refactor"

    def test_conventional_commit_docs(self):
        assert _infer_change_type("docs: update API reference", []) == "documentation"

    def test_conventional_commit_perf(self):
        assert _infer_change_type("perf: cache user lookups", []) == "performance"

    def test_free_form_bugfix(self):
        assert _infer_change_type("bugfix for login race condition", []) == "bug_fix"

    def test_free_form_security(self):
        assert _infer_change_type("security: patch XSS vulnerability", []) == "security"

    def test_file_hints_sql(self):
        assert _infer_change_type("update schema", ["db/migrations/001_add_users.sql"]) == "database_change"

    def test_unknown_commit_returns_general(self):
        assert _infer_change_type("wip", []) == "general"


# ── DiffResult context properties ─────────────────────────────────────────────

class TestDiffResultContext:
    def _make_result(self, files):
        return DiffResult(
            commit_hash="abc123",
            commit_message="feat: new stuff",
            files=files,
        )

    def test_has_new_files(self):
        f = FileDiff("new.py", "python", 10, 0, "", is_new_file=True)
        r = self._make_result([f])
        assert r.has_new_files is True

    def test_no_new_files(self):
        f = FileDiff("old.py", "python", 5, 2, "", is_new_file=False)
        r = self._make_result([f])
        assert r.has_new_files is False

    def test_has_test_files(self):
        f = FileDiff("tests/test_auth.py", "python", 5, 0, "")
        r = self._make_result([f])
        assert r.has_test_files is True

    def test_has_migration_files(self):
        f = FileDiff("db/migration_001.sql", "sql", 30, 0, "")
        r = self._make_result([f])
        assert r.has_migration_files is True

    def test_has_security_sensitive_files(self):
        f = FileDiff("src/auth/login.py", "python", 5, 0, "")
        r = self._make_result([f])
        assert r.has_security_sensitive_files is True

    def test_has_config_files(self):
        f = FileDiff("config/settings.yaml", "yaml", 3, 0, "")
        r = self._make_result([f])
        assert r.has_config_files is True

    def test_is_multi_language(self):
        files = [
            FileDiff("src/api.py", "python", 5, 0, ""),
            FileDiff("frontend/app.ts", "typescript", 10, 0, ""),
        ]
        r = self._make_result(files)
        assert r.is_multi_language is True

    def test_primary_language_most_changed(self):
        files = [
            FileDiff("a.py", "python", 100, 0, ""),
            FileDiff("b.go", "go", 5, 0, ""),
        ]
        r = self._make_result(files)
        assert r.primary_language == "python"

    def test_context_summary_contains_fields(self):
        r = DiffResult(
            commit_hash="abc", commit_message="feat: x",
            branch="main", author="alice", change_type="new_feature",
            all_languages=["python", "typescript"],
            files=[FileDiff("a.py", "python", 10, 5, "")],
            total_added=10, total_removed=5,
        )
        summary = r.context_summary()
        assert "main" in summary
        assert "alice" in summary
        assert "new_feature" in summary
        assert "python" in summary


# ── DiffEngine parse from text ────────────────────────────────────────────────

class TestDiffEngine:
    SAMPLE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
index abc..def 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,4 +1,7 @@
+import hashlib
+
 def login(user, password):
-    pass
+    hashed = hashlib.md5(password.encode()).hexdigest()
+    return db.query(f"SELECT * FROM users WHERE hash='{hashed}'")
"""
    NEW_FILE_DIFF = """\
diff --git a/app/api/routes.go b/app/api/routes.go
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/app/api/routes.go
@@ -0,0 +1,8 @@
+package api
+
+import "net/http"
+
+func Register(mux *http.ServeMux) {
+\tmux.HandleFunc("/health", healthHandler)
+}
"""

    def setup_method(self):
        self.engine = DiffEngine()

    def test_parse_from_text(self):
        result = self.engine.from_text(self.SAMPLE_DIFF)
        assert len(result.files) == 1
        assert result.files[0].path == "src/auth.py"

    def test_content_based_language_detection(self):
        """Language detected from diff content, not just filename."""
        result = self.engine.from_text(self.SAMPLE_DIFF)
        assert result.files[0].language == "python"

    def test_new_file_flag(self):
        result = self.engine.from_text(self.NEW_FILE_DIFF)
        assert result.files[0].is_new_file is True

    def test_go_detected_from_content(self):
        result = self.engine.from_text(self.NEW_FILE_DIFF)
        assert result.files[0].language == "go"

    def test_added_removed_counts(self):
        result = self.engine.from_text(self.SAMPLE_DIFF)
        f = result.files[0]
        assert f.added_lines == 4
        assert f.removed_lines == 1

    def test_primary_language(self):
        result = self.engine.from_text(self.SAMPLE_DIFF)
        assert result.primary_language == "python"

    def test_combined_diff_includes_path(self):
        result = self.engine.from_text(self.SAMPLE_DIFF)
        assert "src/auth.py" in result.combined_diff()

    def test_exclusion_pattern_explicit(self):
        engine = DiffEngine(exclude_patterns=["*.py"])
        result = engine.from_text(self.SAMPLE_DIFF)
        assert len(result.files) == 0

    def test_empty_diff(self):
        result = self.engine.from_text("")
        assert result.files == []
        assert result.primary_language == "unknown"

    def test_change_type_inferred_from_diff(self):
        engine = DiffEngine()
        result = engine._parse_diff(self.SAMPLE_DIFF, "abc", "fix: sql injection")
        assert result.change_type == "bug_fix"

    def test_all_languages_populated(self):
        multi = self.SAMPLE_DIFF + "\n" + self.NEW_FILE_DIFF
        result = self.engine.from_text(multi)
        assert len(result.all_languages) >= 1

    def test_context_summary_non_empty(self):
        result = self.engine.from_text(self.SAMPLE_DIFF)
        assert len(result.context_summary()) > 10


# ── Repo type detection ───────────────────────────────────────────────────────

class TestRepoTypeDetection:
    def test_python_repo(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='foo'")
        ecosystems = _detect_repo_type(tmp_path)
        assert "python" in ecosystems

    def test_node_repo(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "app"}')
        ecosystems = _detect_repo_type(tmp_path)
        assert "nodejs" in ecosystems

    def test_go_repo(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/app\ngo 1.21")
        ecosystems = _detect_repo_type(tmp_path)
        assert "go" in ecosystems

    def test_rust_repo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "myapp"')
        ecosystems = _detect_repo_type(tmp_path)
        assert "rust" in ecosystems

    def test_empty_dir_no_ecosystem(self, tmp_path):
        ecosystems = _detect_repo_type(tmp_path)
        assert ecosystems == {}

    def test_multi_ecosystem(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "requirements.txt").write_text("flask\n")
        ecosystems = _detect_repo_type(tmp_path)
        assert "nodejs" in ecosystems
        assert "python" in ecosystems


# ── Dynamic exclusion patterns ────────────────────────────────────────────────

class TestDynamicExclusion:
    def test_node_repo_excludes_lockfile(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        engine = DiffEngine(repo_path=tmp_path)
        patterns = engine._get_exclude_patterns(tmp_path)
        assert any("package-lock" in p for p in patterns)

    def test_rust_repo_excludes_cargo_lock(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname="a"')
        engine = DiffEngine(repo_path=tmp_path)
        patterns = engine._get_exclude_patterns(tmp_path)
        assert any("Cargo.lock" in p for p in patterns)

    def test_user_provided_patterns_override(self, tmp_path):
        engine = DiffEngine(exclude_patterns=["*.custom"])
        patterns = engine._get_exclude_patterns(tmp_path)
        assert patterns == ["*.custom"]

    def test_always_excludes_minified_js(self, tmp_path):
        engine = DiffEngine(repo_path=tmp_path)
        patterns = engine._get_exclude_patterns(tmp_path)
        assert any("*.min.js" in p for p in patterns)
