#!/usr/bin/env python3
"""Monthly standards audit: check every repo against the automatic checks in STANDARDS.md.

Usage: python3 tools/audit.py [--out-dir reports] [--month YYYY-MM] [--only repo1,repo2]
                              [--repos-json PATH] [--repos-dir DIR] [--baseline PATH]
  (default)    the repo list and open `standard` issues come from repos.json on the `data` branch
               of the control-room repo (no GitHub API call); each repo is cloned (default branch).
  --repos-json use this local copy of repos.json instead of the data branch.
  --repos-dir  use already-cloned folders DIR/<repo> and skip cloning and the GitHub API
               (default branch is read from DIR/<repo>/.audit-default-branch, else "main";
               no open `standard` issues are read).
  --baseline   baseline file to compare with (default reports/baseline-2026-11-16.json).
Writes <out-dir>/audit-YYYY-MM.md and <out-dir>/audit-YYYY-MM.json.
Env: GITHUB_TOKEN (optional), OWNER (default jcm-book-library).

This repo and its reports are public. The R7 check (emails, secret keys, sheet ids) records
only the repo, the file, the kind of thing and a count. The matched text is never kept,
written or printed. Cloned content is treated as data: nothing in it is run.
Python 3 standard library only.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BASELINE = os.path.join(ROOT, "reports", "baseline-2026-11-16.json")
TEMPLATE_BUILD = os.path.join(ROOT, "templates", "tools", "build-pages.py")
OWNER_ONLY_SQL = os.path.join(ROOT, "supabase", "owner-only.sql")
STANDARDS_VERSION = 1

CHECKS = ["R1", "R2", "R3", "R4", "R5", "R7", "A1", "A2", "A3", "A4", "A6", "A8", "A9"]
APP_CHECKS = ["A1", "A2", "A3", "A4", "A6", "A8", "A9"]
LABELS = {
    "R1": "R1 default branch main",
    "R2": "R2 CLAUDE.md short, points to the rules",
    "R3": "R3 README",
    "R4": "R4 charter (project.json) complete",
    "R5": "R5 HANDOVER.md",
    "R7": "R7 no private data in code",
    "A1": "A1 build script matches template",
    "A2": "A2 home-screen install",
    "A3": "A3 shared colour tokens",
    "A4": "A4 tests in the repo",
    "A6": "A6 scripts and fonts",
    "A8": "A8 shared sign-in",
    "A9": "A9 owner-only schema",
}
NOT_CHECKED = [
    "R6 (reference material in docs/)",
    "R7 (manual part: personal figures)",
    "A3 (look and font)",
    "A4 (a test against a fake of the data store)",
    "A5 (phone first)",
    "A7 (data on Supabase)",
    "A10 (left rail, reserved for version 2)",
    "T1 to T7 (media trackers)",
    "S1 to S5 (sessions)",
]

CHARTER_FIELDS = ["name", "repo", "purpose", "family", "stage", "live", "tags", "audience", "standards", "updated"]
STAGES = ["Idea", "Planning", "Building", "Working", "Mature", "Paused"]
AUDIENCES = ["owner", "family", "partner", "public"]
TOKENS = ["--bg", "--surface", "--raise", "--line", "--fg", "--muted"]
ICONS = ["icons/favicon-32.png", "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png"]
SKIP_DIRS = {".git", "node_modules"}
R7_SKIP_DIRS = {"dist", "vendor"}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json", "composer.lock",
             "Pipfile.lock", "poetry.lock", "Cargo.lock", "go.sum", "bun.lockb"}
MAX_SCAN_BYTES = 1024 * 1024
MAX_READ_BYTES = 8 * 1024 * 1024
ASSET_TLDS = {"png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "css", "js", "mjs", "json", "map", "woff", "woff2"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.([A-Za-z]{2,})")
SECRET_RES = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{20,}"),
    re.compile(r"sb_secret_[A-Za-z0-9_-]{8,}"),
    re.compile(r"service_role[\s\S]{0,200}?eyJ[\w-]{10,}\.[\w-]{10,}\."),
]
SHEET_RES = [
    re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{25,})"),
    re.compile(r"(?:spreadsheetId|SHEET_ID|sheetId)\s*[:=]\s*['\"]([A-Za-z0-9_-]{30,60})['\"]"),
]
# Obviously fake ids (test fixtures, examples) are not counted.
PLACEHOLDER_PARTS = ("test", "fake", "dummy", "example", "sample", "abcdef", "123456", "xxxxx", "sheet_id")
BUILD_SETTING_RE = re.compile(r"^(SHORT_NAME|THEME_COLOUR|LANG)\s*=")
OWN_BUILD_RE = re.compile(r"(?i)\b(vite|own build|different build|built by (github )?actions)\b")
TEST_WORD_RE = re.compile(r"(?i)\btest")  # test, tests, testing; not "latest"


def res(result, why=None, **extra):
    out = {"result": result, "why": why}
    out.update(extra)
    return out


# ---------------------------------------------------------------- reading a repo folder

class Repo:
    """A folder on disk. Never follows symlinks, never runs anything."""

    def __init__(self, path):
        self.path = path
        self.files = []  # (relative posix path, size)
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if os.path.islink(full):
                    continue
                rel = os.path.relpath(full, path).replace(os.sep, "/")
                try:
                    self.files.append((rel, os.path.getsize(full)))
                except OSError:
                    pass
        self.rels = {r for r, _ in self.files}

    def has(self, rel):
        return rel in self.rels

    def read(self, rel, limit=MAX_READ_BYTES):
        if rel not in self.rels:
            return None
        try:
            with open(os.path.join(self.path, rel), "rb") as f:
                return f.read(limit).decode("utf-8", errors="replace")
        except OSError:
            return None

    def by_ext(self, *exts):
        return sorted(r for r, _ in self.files if r.lower().endswith(exts))


def words(text):
    return len(text.split())


def is_test_path(rel):
    parts = rel.lower().split("/")
    name = parts[-1]
    return (any(p in ("test", "tests", "__tests__") for p in parts[:-1]) or ".test." in name
            or ".spec." in name or name.startswith("test_") or name.endswith("_test.py"))


# ---------------------------------------------------------------- checks

def check_r1(default_branch):
    if default_branch == "main":
        return res("pass")
    return res("fail", "default branch is %s, not main" % (default_branch or "unknown"))


def check_r2(repo):
    text = repo.read("CLAUDE.md")
    if text is None:
        return res("fail", "no CLAUDE.md")
    problems = []
    n = words(text)
    if n > 400:
        problems.append("%d words, over 400" % n)
    low = text.lower()
    for key, shown in (("house-rules", "HOUSE-RULES.md"), ("standards", "STANDARDS.md"),
                       ("handover", "HANDOVER.md")):
        if key not in low:
            problems.append("doesn't mention %s" % shown)
    return res("fail", "; ".join(problems)) if problems else res("pass")


def load_charter(repo):
    """Returns (data, problem). problem is None when project.json parsed to an object."""
    text = repo.read("project.json")
    if text is None:
        return None, "no project.json"
    try:
        data = json.loads(text)
    except ValueError:
        return None, "project.json isn't valid JSON"
    if not isinstance(data, dict):
        return None, "project.json isn't a JSON object"
    return data, None


def same_test_r2(repo):
    """The looser test the baseline used: 400 words or fewer and points to HOUSE-RULES."""
    text = repo.read("CLAUDE.md")
    ok = text is not None and words(text) <= 400 and "house-rules" in text.lower()
    return "pass" if ok else "fail"


def check_r3(repo):
    text = repo.read("README.md")
    if text is None:
        return res("fail", "no README.md")
    problems = []
    charter, _ = load_charter(repo)
    live = charter.get("live") if charter else None
    if isinstance(live, str) and live.strip():
        if re.sub(r"^https?://", "", live.strip()).rstrip("/") not in text:  # the scheme may be left off
            problems.append("README doesn't have the live link")
    if not TEST_WORD_RE.search(text):
        problems.append("README doesn't say how to test")
    return res("fail", "; ".join(problems)) if problems else res("pass")


def check_r4(repo):
    data, problem = load_charter(repo)
    if problem:
        return res("fail", problem)
    extra = {"standards": data.get("standards")}
    problems = []
    missing = [f for f in CHARTER_FIELDS if f not in data]
    if missing:
        problems.append("missing %s" % ", ".join(missing))
    if "stage" in data and data["stage"] not in STAGES:
        problems.append("stage isn't one of %s" % ", ".join(STAGES))
    if "audience" in data and data["audience"] not in AUDIENCES:
        problems.append("audience isn't one of %s" % ", ".join(AUDIENCES))
    v = data.get("standards")
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v < STANDARDS_VERSION:
        problems.append("brought up to standards v%s, now v%d" % (v, STANDARDS_VERSION))
    if problems:
        return res("fail", "; ".join(problems), **extra)
    return res("pass", **extra)


def check_r5(repo):
    text = repo.read("HANDOVER.md")
    if text is None:
        return res("fail", "no HANDOVER.md")
    n = words(text)
    if n > 800:
        return res("fail", "%d words, over 800" % n)
    return res("pass")


def scan_text(text):
    """Return counts of {email, secret, sheet-id} in text. Matched text is never kept."""
    counts = {"email": 0, "secret": 0, "sheet-id": 0}
    for m in EMAIL_RE.finditer(text):
        addr = m.group(0).lower()
        local, _, domain = addr.rpartition("@")
        if "noreply" in local or "noreply" in domain or domain.endswith("users.noreply.github.com"):
            continue
        if domain in ("example.com", "example.org") or domain.endswith((".example.com", ".example.org")):
            continue
        if local == "git" and domain == "github.com":
            continue
        if m.group(1).lower() in ASSET_TLDS:  # things like icon@2x.png
            continue
        if domain == "anthropic.com":
            start = text.rfind("\n", 0, m.start()) + 1
            end = text.find("\n", m.end())
            line = text[start:end if end != -1 else len(text)].lower()
            if "co-authored-by" in line or "signed-off-by" in line:
                continue
        counts["email"] += 1
    for rx in SECRET_RES:
        counts["secret"] += sum(1 for _ in rx.finditer(text))
    for rx in SHEET_RES:
        counts["sheet-id"] += sum(1 for m in rx.finditer(text)
                                  if not any(p in m.group(1).lower() for p in PLACEHOLDER_PARTS))
    return counts


def scan_repo_private(repo):
    """List of {file, kind, count}. Nothing else is recorded."""
    findings = []
    for rel, size in repo.files:
        parts = rel.split("/")
        if any(p in R7_SKIP_DIRS for p in parts[:-1]) or parts[-1] in LOCKFILES or parts[-1].endswith(".lock"):
            continue
        if size > MAX_SCAN_BYTES:
            continue
        try:
            with open(os.path.join(repo.path, rel), "rb") as f:
                data = f.read(MAX_SCAN_BYTES + 1)
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        counts = scan_text(data.decode("utf-8", errors="replace"))
        for kind in ("email", "secret", "sheet-id"):
            if counts[kind]:
                findings.append({"file": rel, "kind": kind, "count": counts[kind]})
    findings.sort(key=lambda f: (f["file"], f["kind"]))
    return findings


def describe_findings(findings):
    names = {"email": "email address", "secret": "secret key", "sheet-id": "sheet id"}
    bits = ["%s in %s (%d)" % (names[f["kind"]], f["file"], f["count"]) for f in findings[:5]]
    if len(findings) > 5:
        bits.append("and %d more" % (len(findings) - 5))
    return ", ".join(bits)


def check_r7(repo, name, d5):
    findings = scan_repo_private(repo)
    bad = [f for f in findings if f["kind"] in ("email", "secret")]
    sheets = [f for f in findings if f["kind"] == "sheet-id"]
    if bad:
        return res("fail", describe_findings(bad + sheets), findings=findings)
    if sheets:
        if name in d5:
            return res("pass", "existing sheet ids allowed until it moves to Supabase (D5)", findings=findings)
        return res("fail", "new sheet id in code: " + describe_findings(sheets), findings=findings)
    return res("pass", findings=findings)


def normalise_build(text):
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
             if not BUILD_SETTING_RE.match(ln)]
    return "\n".join(lines).strip()


def check_a1(repo, template_text):
    readme = repo.read("README.md") or ""
    if repo.has("tools/build-pages.py"):
        if template_text is None:
            return res("unknown", "the template build script couldn't be read")
        mine = normalise_build(repo.read("tools/build-pages.py") or "")
        if mine == normalise_build(template_text):
            return res("pass")
        return res("fail", "build script differs from the template")
    if OWN_BUILD_RE.search(readme):
        return res("pass")
    return res("fail", "no build script and the README doesn't explain the build")


def check_a2(repo):
    missing = [p for p in (["manifest.webmanifest"] + ICONS) if not repo.has(p)]
    if missing:
        return res("fail", "missing " + ", ".join(missing))
    return res("pass")


def main_page(repo):
    for p in ("app.html", "index.html"):
        if repo.has(p):
            return p
    return None


def check_a3(repo):
    page = main_page(repo)
    if page is None:
        return res("fail", "no app.html or index.html")
    text = repo.read(page) or ""
    declared = "\n".join(re.findall(r":root\s*\{([^}]*)\}", text))
    missing = [t for t in TOKENS if not re.search(r"(?<![\w-])%s\s*:" % re.escape(t), declared)]
    if missing:
        return res("fail", "%s doesn't declare %s in :root" % (page, ", ".join(missing)))
    return res("pass")


def check_a4(repo):
    found = any(r.startswith(("tests/", "test/")) for r in repo.rels)
    if not found:
        for rel in repo.rels:
            base = rel.rsplit("/", 1)[-1]
            if (any(fnmatch.fnmatch(base, "*test*" + e) for e in (".py", ".js", ".mjs", ".ts"))
                    or fnmatch.fnmatch(base, "*.spec.*")
                    or fnmatch.fnmatch(base, "*.test.*")):
                found = True
                break
    if not found:
        return res("fail", "no tests in the repo")
    texts = (repo.read("README.md") or "") + "\n" + (repo.read("tests/README.md") or "")
    if not TEST_WORD_RE.search(texts):
        return res("fail", "tests exist but the README doesn't say how to run them")
    return res("pass")


URL_ATTR_RE = re.compile(r"""(?is)<(script|link)\b([^>]*)>""")
SRC_RE = re.compile(r"""(?is)\bsrc\s*=\s*["']([^"']+)["']""")
HREF_RE = re.compile(r"""(?is)\bhref\s*=\s*["']([^"']+)["']""")
REL_RE = re.compile(r"""(?is)\brel\s*=\s*["']([^"']+)["']""")
CSS_URL_RE = re.compile(r"""(?is)(?:@import\s+(?:url\(\s*)?|url\(\s*)["']?((?:https?:)?//[^"')\s]+)""")


def host_of(url):
    if url.startswith("//"):
        url = "https:" + url
    return (urlparse(url).hostname or "").lower()


def is_external(url):
    return url.startswith(("http://", "https://", "//"))


def check_a6(repo):
    bad_script_hosts, bad_style_hosts, unpinned = set(), set(), False
    for rel in repo.by_ext(".html"):
        text = repo.read(rel) or ""
        for m in URL_ATTR_RE.finditer(text):
            tag, attrs = m.group(1).lower(), m.group(2)
            if tag == "script":
                s = SRC_RE.search(attrs)
                if s and is_external(s.group(1)):
                    host = host_of(s.group(1))
                    if host == "accounts.google.com":  # Google sign-in script; can't come from cdnjs
                        continue
                    if host != "cdnjs.cloudflare.com":
                        bad_script_hosts.add(host)
                    elif not re.search(r"/\d+\.\d+", urlparse("https:" + s.group(1) if s.group(1).startswith("//")
                                                              else s.group(1)).path):
                        unpinned = True
            else:
                h, r = HREF_RE.search(attrs), REL_RE.search(attrs)
                rels = (r.group(1).lower() if r else "")
                if h and is_external(h.group(1)) and ("stylesheet" in rels or "preload" in rels):
                    host = host_of(h.group(1))
                    if host not in ("fonts.googleapis.com", "fonts.gstatic.com"):
                        bad_style_hosts.add(host)
        for m in CSS_URL_RE.finditer(text):
            host = host_of(m.group(1))
            if host not in ("fonts.googleapis.com", "fonts.gstatic.com"):
                bad_style_hosts.add(host)
    problems = []
    if bad_script_hosts:
        problems.append("scripts from " + ", ".join(sorted(bad_script_hosts)))
    if bad_style_hosts:
        problems.append("styles or fonts from " + ", ".join(sorted(bad_style_hosts)))
    if unpinned:
        problems.append("unpinned cdnjs script")
    return res("fail", "; ".join(problems)) if problems else res("pass")


def code_files(repo):
    return [r for r in repo.by_ext(".html", ".js", ".mjs", ".ts") if not is_test_path(r)]


def check_a8(repo):
    for rel in code_files(repo):
        if "jcm-sb-session" in (repo.read(rel) or ""):
            return res("pass")
    return res("fail", "not on the shared sign-in yet")


SCHEMA_RES = [re.compile(r"""\.schema\(\s*['"](\w+)['"]"""),
              re.compile(r"""db\s*:\s*\{\s*schema\s*:\s*['"](\w+)['"]""")]


def owner_only_schemas(sql_text):
    out = set()
    for block in re.findall(r"v_schemas[^;=]*:=\s*array\[([^\]]*)\]", sql_text or ""):
        out.update(re.findall(r"'([^']+)'", block))
    return out


def check_a9(repo, locked):
    schemas, uses = set(), False
    for rel in code_files(repo):
        text = repo.read(rel) or ""
        if "supabase.co" in text or "@supabase/supabase-js" in text or "supabase.createClient" in text:
            uses = True
        for rx in SCHEMA_RES:
            schemas.update(rx.findall(text))
    if not uses:
        return res("n/a", "doesn't use Supabase")
    if not schemas:
        return res("unknown", "uses Supabase but the schema name couldn't be found")
    off = sorted(s for s in schemas if s not in ("books", "family") and s not in locked)
    if off:
        return res("fail", "schema %s isn't on the owner-only list" % ", ".join(off))
    return res("pass")


# ---------------------------------------------------------------- one repo

def repo_kind(name, repo, baseline_by_name):
    b = baseline_by_name.get(name)
    if b is not None:
        return "app" if b.get("kind") == "app" else "other"
    if repo is not None and (repo.has("app.html") or repo.has("index.html")):
        return "app"
    return "other"


def audit_repo(name, path, default_branch, ctx):
    repo = Repo(path)
    kind = repo_kind(name, repo, ctx["baseline_by_name"])
    checks = {
        "R1": check_r1(default_branch),
        "R2": check_r2(repo),
        "R3": check_r3(repo),
        "R4": check_r4(repo),
        "R5": check_r5(repo),
        "R7": check_r7(repo, name, ctx["d5"]),
    }
    checks["R2"]["baseline_test"] = same_test_r2(repo)
    checks["R3"]["baseline_test"] = "pass" if repo.has("README.md") else "fail"
    checks["R5"]["baseline_test"] = "pass" if repo.has("HANDOVER.md") else "fail"
    if kind == "app":
        checks["A1"] = check_a1(repo, ctx["template"])
        checks["A2"] = check_a2(repo)
        checks["A3"] = check_a3(repo)
        checks["A4"] = check_a4(repo)
        checks["A6"] = check_a6(repo)
        checks["A8"] = check_a8(repo)
        checks["A9"] = check_a9(repo, ctx["locked"])
    else:
        for c in APP_CHECKS:
            checks[c] = res("n/a", "not an app")
    return {"repo": name, "kind": kind, "default_branch": default_branch, "checks": checks}


def unknown_repo(name, reason, ctx):
    b = ctx["baseline_by_name"].get(name)
    kind = ("app" if b.get("kind") == "app" else "other") if b else "unknown"
    ids = CHECKS if kind in ("app", "unknown") else [c for c in CHECKS if c not in APP_CHECKS]
    checks = {c: res("unknown", reason) for c in ids}
    for c in APP_CHECKS:
        checks.setdefault(c, res("n/a", "not an app"))
    return {"repo": name, "kind": kind, "default_branch": None,
            "checks": {c: checks[c] for c in CHECKS}}


# ---------------------------------------------------------------- baseline

# The baseline file has no field for the default branch. STANDARDS.md section 6 says 17 of 20
# met R1 and names these three as the gaps (they had a claude/ branch as default on 16 Nov 26).
BASELINE_R1_GAPS = {"shopping-list", "travel-app", "travel-planner"}


def baseline_statuses(b):
    """Map check id -> 'pass' | 'fail' | 'n/a' | None (not recorded) for one baseline entry."""
    def yn(v):
        return None if v is None else ("pass" if v else "fail")

    is_app = b.get("kind") == "app"
    cm = b.get("claude_md") or {}
    pj = b.get("project_json") or {}
    pwa = b.get("pwa") or {}
    priv = b.get("private_data_in_code") or {}
    out = {"R1": "fail" if b["repo"] in BASELINE_R1_GAPS else "pass"}
    out["R2"] = yn(bool(cm.get("exists")) and (cm.get("words") or 10 ** 9) <= 400
                   and bool(cm.get("points_to_house_rules")))
    out["R3"] = yn(b.get("readme_exists"))
    out["R4"] = yn(bool(pj.get("exists")) and all(f in (pj.get("fields_present") or []) for f in CHARTER_FIELDS))
    out["R5"] = yn("HANDOVER.md" in (b.get("handover_plan_files") or []))
    # Sheet ids are allowed for existing repos (D5), so R7 here means no emails and no keys.
    out["R7"] = yn(not priv.get("emails") and not priv.get("api_keys_or_tokens")) if priv else None
    if not is_app:
        for c in APP_CHECKS:
            out[c] = "n/a"
        return out
    md5 = (b.get("build_script") or {}).get("md5_matches_template")
    out["A1"] = yn(md5)
    icons = pwa.get("icons_present") or []
    has_icons = all(any(i.startswith(k) for i in icons) for k in ("favicon-32", "apple-touch-icon", "192", "512"))
    out["A2"] = yn(bool(pwa.get("manifest_exists")) and has_icons) if pwa else None
    names = (b.get("theme") or {}).get("root_css_variable_names")
    out["A3"] = yn(all(t in names for t in TOKENS)) if names is not None else None
    out["A4"] = yn((b.get("tests") or {}).get("exists")) if "tests" in b else None
    out["A6"] = None
    out["A8"] = yn((b.get("sign_in") or {}).get("uses_shared_session_key_jcm_sb_session")) if "sign_in" in b else None
    out["A9"] = None
    return out


def compare(baseline, results):
    by_name = {b["repo"]: b for b in baseline["repos"]}
    now_names = [r["repo"] for r in results]
    rows = {}
    for c in CHECKS:
        base_status = {}
        for r in results:
            b = by_name.get(r["repo"])
            if b:
                base_status[r["repo"]] = baseline_statuses(b).get(c)
        recorded = any(s in ("pass", "fail") for s in base_status.values())
        now = {r["repo"]: r["checks"][c].get("baseline_test", r["checks"][c]["result"]) for r in results}
        full = {r["repo"]: r["checks"][c]["result"] for r in results}
        rows[c] = {
            "label": LABELS[c],
            "baseline_recorded": recorded,
            "baseline_count": sum(1 for s in base_status.values() if s == "pass") if recorded else None,
            "now_count": sum(1 for s in now.values() if s == "pass"),
            "now_full_count": sum(1 for s in full.values() if s == "pass"),
            "gained": sorted((n for n, s in base_status.items() if s == "fail" and now[n] == "pass"),
                             key=str.lower),
            "lost": sorted((n for n, s in base_status.items() if s == "pass" and now[n] == "fail"),
                           key=str.lower),
        }
    return {
        "baseline_taken": baseline.get("taken"),
        "rows": rows,
        "new_repos": sorted((n for n in now_names if n not in by_name), key=str.lower),
        "not_in_this_run": sorted((n for n in by_name if n not in now_names), key=str.lower),
    }


# ---------------------------------------------------------------- report

def short_date(d):
    return "%d %s" % (d.day, d.strftime("%b %y"))


def render_md(month, now, results, comparison, issues, issues_note):
    month_dt = datetime.strptime(month + "-01", "%Y-%m-%d")
    lines = ["# Standards audit, %s" % month_dt.strftime("%B %Y"),
             "Standards version %d. %d repos checked on %s." % (STANDARDS_VERSION, len(results), short_date(now)),
             "", "## Behind the standard"]
    clean = []
    for r in results:
        fails = [(c, v) for c, v in r["checks"].items() if v["result"] == "fail"]
        if fails:
            lines.append("- %s: %s" % (r["repo"], ", ".join("%s (%s)" % (c, v["why"]) for c, v in fails)))
        elif not any(v["result"] == "unknown" for v in r["checks"].values()):
            clean.append(r["repo"])
    if not any(line.startswith("- ") for line in lines):
        lines.append("None.")
    lines.append("")
    lines.append("Meeting every automatic check: %s." % (", ".join(clean) if clean else "none"))

    taken = comparison.get("baseline_taken")
    try:
        taken = short_date(datetime.strptime(taken, "%Y-%m-%d"))
    except (TypeError, ValueError):
        taken = str(taken)
    lines += ["", "## Compared with the baseline (%s)" % taken,
              "| Standard | Baseline | Now (same test) | Gained | Lost | Now (full standard) |",
              "|---|---|---|---|---|---|"]
    for c in CHECKS:
        row = comparison["rows"][c]
        base = str(row["baseline_count"]) if row["baseline_recorded"] else "not recorded"
        lines.append("| %s | %s | %d | %s | %s | %d |" % (
            row["label"], base, row["now_count"],
            ", ".join(row["gained"]) or "–", ", ".join(row["lost"]) or "–", row["now_full_count"]))
    lines += ["",
              "Gained and lost use the same test the baseline used: R2 is 400 words or fewer and points to "
              "HOUSE-RULES, R3 is a README exists, R5 is HANDOVER.md exists. The last column is today's full "
              "standard. The baseline was looser for R2 (it didn't check for STANDARDS.md or HANDOVER.md) "
              "and R3 (it only checked a README exists, not the live link or testing). For R7 the baseline "
              "count means no emails or keys, because existing sheet ids are allowed (D5). "
              "R1 comes from STANDARDS.md section 6. A4 in the baseline didn't check the README. "
              "A6 and A9 weren't recorded."]
    if comparison["new_repos"]:
        lines.append("New since the baseline: %s." % ", ".join(comparison["new_repos"]))
    if comparison["not_in_this_run"]:
        lines.append("In the baseline but not in this run: %s." % ", ".join(comparison["not_in_this_run"]))

    lines += ["", "## Couldn't check automatically"]
    n_before = len(lines)
    for r in results:
        unk = [(c, v) for c, v in r["checks"].items() if v["result"] == "unknown"]
        if unk:
            lines.append("- %s: %s" % (r["repo"], ", ".join("%s (%s)" % (c, v["why"]) for c, v in unk)))
    if len(lines) == n_before:
        lines.append("Nothing.")

    lines += ["", "## Open `standard` issues"]
    if issues_note:
        lines.append(issues_note)
    elif not issues:
        lines.append("None open.")
    else:
        lines += ["- %s %s" % (i["title"], i["url"]) for i in issues]

    lines += ["", "## Not checked by the script", ", ".join(NOT_CHECKED) + ".", "",
              "Allowed exceptions: A6 allows the Google sign-in script from accounts.google.com, "
              "because it can't come from cdnjs. R7 ignores sheet ids that are obviously fake "
              "(test, fake, dummy, example, sample and similar).", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- running

def clone_repo(owner, name, dest):
    """Shallow clone of the default branch. Returns None on success, else a short reason."""
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    try:
        p = subprocess.run(["git", "clone", "-q", "--depth", "1",
                            "https://github.com/%s/%s" % (owner, name), dest],
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return "the repo couldn't be downloaded in time"
    return None if p.returncode == 0 else "the repo couldn't be downloaded"


ISSUES_MISSING = "Not available yet: the daily run hasn't collected them."


def issues_from(data):
    """Open `standard` issues from repos.json data: (list, note). The key may be missing."""
    items = data.get("standard_issues") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return [], ISSUES_MISSING
    return [{"title": i.get("title"), "url": i.get("html_url")} for i in items if isinstance(i, dict)], None


def fetch_repos_json(owner):
    """repos.json from the `data` branch of the control-room repo (no API call). None if it fails."""
    with tempfile.TemporaryDirectory(prefix="audit-data-") as tmp:
        dest = os.path.join(tmp, "c")
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            p = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", "data",
                                "https://github.com/%s/control-room" % owner, dest],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            if p.returncode != 0:
                return None
            with open(os.path.join(dest, "repos.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None


def build_ctx(baseline):
    template = None
    try:
        with open(TEMPLATE_BUILD, encoding="utf-8") as f:
            template = f.read()
    except OSError:
        pass
    try:
        with open(OWNER_ONLY_SQL, encoding="utf-8") as f:
            locked = owner_only_schemas(f.read())
    except OSError:
        locked = set()
    by_name = {b["repo"]: b for b in baseline["repos"]}
    d5 = {n for n, b in by_name.items() if (b.get("private_data_in_code") or {}).get("sheet_or_project_ids") is True}
    return {"template": template, "locked": locked, "baseline_by_name": by_name, "d5": d5}


def run(args, now=None):
    now = now or datetime.now(timezone.utc)
    month = args.month or now.strftime("%Y-%m")
    with open(args.baseline, encoding="utf-8") as f:
        baseline = json.load(f)
    ctx = build_ctx(baseline)
    only = {s.strip() for s in args.only.split(",") if s.strip()} if args.only else None
    results = []
    issues, issues_note = [], ISSUES_MISSING
    data = None
    if args.repos_json or not args.repos_dir:
        if args.repos_json:
            with open(args.repos_json, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = fetch_repos_json(collect.OWNER)
        if not isinstance(data, dict) or not isinstance(data.get("repos"), list):
            print("error: couldn't read the repo list (repos.json)", file=sys.stderr)
            return 1
        issues, issues_note = issues_from(data)

    if args.repos_dir:
        names = sorted((d for d in os.listdir(args.repos_dir)
                        if not d.startswith(".") and os.path.isdir(os.path.join(args.repos_dir, d))), key=str.lower)
        for name in names:
            if only and name not in only:
                continue
            path = os.path.join(args.repos_dir, name)
            branch = "main"
            try:
                with open(os.path.join(path, ".audit-default-branch"), encoding="utf-8") as f:
                    branch = f.read().strip() or "main"
            except OSError:
                pass
            results.append(audit_repo(name, path, branch, ctx))
    else:
        raw = [r for r in data["repos"] if r.get("name") and not r.get("archived")
               and (not only or r["name"] in only)]
        for r in sorted(raw, key=lambda x: x["name"].lower()):
            name = r["name"]
            with tempfile.TemporaryDirectory(prefix="audit-") as tmp:
                dest = os.path.join(tmp, name)
                try:
                    reason = clone_repo(collect.OWNER, name, dest)
                    if reason:
                        print("warn: %s: %s" % (name, reason), file=sys.stderr)
                        results.append(unknown_repo(name, reason, ctx))
                    else:
                        results.append(audit_repo(name, dest, r.get("default_branch"), ctx))
                except Exception as e:  # never let one repo sink the run; type only, no content
                    print("warn: %s: audit failed (%s)" % (name, type(e).__name__), file=sys.stderr)
                    results.append(unknown_repo(name, "the audit couldn't read this repo", ctx))

    results.sort(key=lambda r: r["repo"].lower())
    comparison = compare(baseline, results)
    out = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "standards_version": STANDARDS_VERSION,
           "repos": results, "baseline_comparison": comparison, "standard_issues": issues,
           "not_checked": NOT_CHECKED}
    if issues_note:
        out["standard_issues_note"] = issues_note
    os.makedirs(args.out_dir, exist_ok=True)
    jpath = os.path.join(args.out_dir, "audit-%s.json" % month)
    mpath = os.path.join(args.out_dir, "audit-%s.md" % month)
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(render_md(month, now, results, comparison, issues, issues_note))
    print("wrote %s and %s: %d repos" % (mpath, jpath, len(results)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "reports"))
    ap.add_argument("--month", default=None, help="YYYY-MM (default: this month)")
    ap.add_argument("--only", default=None, help="comma-separated repo names")
    ap.add_argument("--repos-json", default=None, help="local repos.json instead of the data branch")
    ap.add_argument("--repos-dir", default=None)
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    args = ap.parse_args(argv)
    if args.month and not re.fullmatch(r"\d{4}-\d{2}", args.month):
        ap.error("--month must look like 2026-11")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
