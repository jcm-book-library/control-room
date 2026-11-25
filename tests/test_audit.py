"""Run: python3 tests/test_audit.py   (no network: repos are fake folders, the API is faked)"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import audit  # noqa: E402
import collect  # noqa: E402

EMAIL = "someone.private@gmail.com"
SHEET = "1QmZpWkRvTnYbHcLsJdFgXuEaOiBt7Vq9KyMrSw0PhNz"

GOOD_CLAUDE = "Read HOUSE-RULES.md, STANDARDS.md and HANDOVER.md first.\n"
GOOD_PROJECT = {"name": "X", "repo": "x", "purpose": "p", "family": "Home", "stage": "Working", "live": None,
                "tags": [], "audience": "owner", "standards": 1, "updated": "2026-11-01"}
PAGE = ("<html><head><style>:root{--bg:#000;--surface:#111;--raise:#222;--line:#333;--fg:#fff;--muted:#999}"
        "</style></head><body>hi</body></html>")


def write(root, rel, text="", mode="w"):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode) as f:
        f.write(text)


def make_repo(base, name, app=True, **over):
    """A repo folder that passes every check, then apply overrides: {relpath: text or None (delete)}."""
    root = os.path.join(base, name)
    files = {"CLAUDE.md": GOOD_CLAUDE, "README.md": "How to test: run the tests.\n", "HANDOVER.md": "short\n",
             "project.json": json.dumps(GOOD_PROJECT)}
    if app:
        files.update({"app.html": PAGE, "tools/build-pages.py": "SHORT_NAME = 'a'\nprint('x')\n",
                      "manifest.webmanifest": "{}", "tests/t.py": "",
                      "app.js": "localStorage.getItem('jcm-sb-session')"})
        for i in audit.ICONS:
            files[i] = "png"
    files.update(over)
    for rel, text in files.items():
        if text is not None:
            write(root, rel, text)
    return root


class Ctx:
    template = "SHORT_NAME = 'tpl'\nTHEME_COLOUR = 'x'\nprint('x')\n"

    @staticmethod
    def make(d5=(), baseline_repos=()):
        return {"template": Ctx.template, "locked": {"brain"},
                "baseline_by_name": {b["repo"]: b for b in baseline_repos}, "d5": set(d5)}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def audit(self, name="x", branch="main", d5=(), baseline_repos=(), **over):
        self.n = getattr(self, "n", 0) + 1
        root = make_repo(os.path.join(self.tmp, "run%d" % self.n), name, **over)
        return audit.audit_repo(name, root, branch, Ctx.make(d5, baseline_repos))["checks"]


class RepoChecks(Base):
    def test_clean_repo_passes_everything(self):
        checks = self.audit()
        self.assertEqual({k: v["result"] for k, v in checks.items() if v["result"] != "pass"},
                         {"A9": "n/a"})

    def test_r1(self):
        self.assertEqual(self.audit(branch="claude/x")["R1"]["result"], "fail")

    def test_r1_from_marker_file(self):
        make_repo(self.tmp, "r1")
        write(os.path.join(self.tmp, "r1"), ".audit-default-branch", "claude/old\n")
        out = os.path.join(self.tmp, "out")
        audit.main(["--repos-dir", self.tmp, "--out-dir", out, "--month", "2026-11", "--only", "r1"])
        data = json.load(open(os.path.join(out, "audit-2026-11.json")))
        self.assertEqual(data["repos"][0]["checks"]["R1"]["result"], "fail")

    def test_r2_words_and_mentions(self):
        c = self.audit(**{"CLAUDE.md": "HOUSE-RULES " + "word " * 450})["R2"]
        self.assertEqual(c["result"], "fail")
        self.assertIn("451 words", c["why"])
        self.assertIn("doesn't mention STANDARDS.md", c["why"])
        self.assertIn("doesn't mention HANDOVER.md", c["why"])
        self.assertNotIn("HOUSE-RULES.md", c["why"])
        self.assertEqual(self.audit(**{"CLAUDE.md": None})["R2"]["why"], "no CLAUDE.md")

    def test_r3(self):
        proj = dict(GOOD_PROJECT, live="https://x.github.io/x/")
        c = self.audit(**{"project.json": json.dumps(proj), "README.md": "Live: https://x.github.io/x\nrun the tests"})["R3"]
        self.assertEqual(c["result"], "pass")
        c = self.audit(**{"project.json": json.dumps(proj), "README.md": "Live: x.github.io/x/\nrun the tests"})["R3"]
        self.assertEqual(c["result"], "pass")
        c = self.audit(**{"project.json": json.dumps(proj), "README.md": "nothing here, latest news"})["R3"]
        self.assertIn("live link", c["why"])
        self.assertIn("how to test", c["why"])

    def test_r4_missing_fields_and_old_version(self):
        proj = {k: v for k, v in GOOD_PROJECT.items() if k not in ("audience", "standards")}
        c = self.audit(**{"project.json": json.dumps(proj)})["R4"]
        self.assertEqual(c["result"], "fail")
        self.assertIn("audience, standards", c["why"])
        c = self.audit(**{"project.json": json.dumps(dict(GOOD_PROJECT, standards=0, stage="Done"))})["R4"]
        self.assertIn("brought up to standards v0, now v1", c["why"])
        self.assertIn("stage", c["why"])
        self.assertEqual(c["standards"], 0)
        self.assertEqual(self.audit(**{"project.json": "{nope"})["R4"]["result"], "fail")

    def test_r5(self):
        self.assertEqual(self.audit(**{"HANDOVER.md": "w " * 801})["R5"]["result"], "fail")
        self.assertEqual(self.audit(**{"HANDOVER.md": None})["R5"]["why"], "no HANDOVER.md")

    def test_r7_email_found_and_ignored_kinds(self):
        text = ("contact %s\nnoreply@x.com a@users.noreply.github.com b@example.com git@github.com icon@2x.png\n"
                "Co-Authored-By: C <noreply@anthropic.com>\n") % EMAIL
        c = self.audit(**{"notes.txt": text})["R7"]
        self.assertEqual(c["result"], "fail")
        self.assertEqual(c["findings"], [{"file": "notes.txt", "kind": "email", "count": 1}])
        self.assertNotIn(EMAIL, json.dumps(c))

    def test_r7_secrets(self):
        for text in ["-----BEGIN RSA PRIVATE KEY-----", "ghp_" + "a" * 30, "AKIA" + "A" * 16, "sk-" + "a" * 24,
                     "service_role = 'eyJ" + "a" * 12 + "." + "b" * 12 + ".sig'"]:
            self.assertEqual(self.audit(name="s", **{"k.js": text})["R7"]["findings"][0]["kind"], "secret", text)
        ok = "sb_publishable_abcdef eyJ%s.%s.sig" % ("a" * 12, "b" * 12)
        self.assertEqual(self.audit(name="s2", **{"k.js": ok})["R7"]["result"], "pass")

    def test_r7_skips_binary_and_lockfiles_and_big(self):
        write(os.path.join(self.tmp, "b"), "x.bin", "\0" + EMAIL, mode="w")
        c = self.audit(name="b", **{"package-lock.json": EMAIL, "node_modules/m.js": EMAIL,
                                    "big.txt": EMAIL + " " * (1024 * 1024 + 5)})["R7"]
        self.assertEqual(c["result"], "pass")

    def test_r7_sheet_id_allowed_for_d5_only(self):
        files = {"app.js": "const SHEET_ID = '%s';" % SHEET}
        old = self.audit(name="old", d5={"old"}, **files)["R7"]
        self.assertEqual(old["result"], "pass")
        self.assertIn("D5", old["why"])
        new = self.audit(name="new", d5={"old"}, **files)["R7"]
        self.assertEqual(new["result"], "fail")
        self.assertIn("new sheet id", new["why"])
        url = self.audit(name="u", **{"a.md": "https://docs.google.com/spreadsheets/d/%s/edit" % SHEET})["R7"]
        self.assertEqual(url["findings"][0]["kind"], "sheet-id")
        self.assertNotIn(SHEET, json.dumps([old, new, url]))

    def test_r7_placeholder_sheet_ids_ignored(self):
        for pid in ("1TEST" + "a" * 35, "1" + "b" * 10 + "fake" + "c" * 25, "1abcdef" + "g" * 30, "x" * 40,
                    "1" + "z" * 8 + "123456" + "y" * 26, "SHEET_ID_" + "q" * 25, "an-Example-" + "k" * 25):
            c = self.audit(name="ph", **{"a.js": "const sheetId = '%s';" % pid})["R7"]
            self.assertEqual((c["result"], c["findings"]), ("pass", []), pid)
        c = self.audit(name="real", **{"a.js": "const sheetId = '%s';" % SHEET})["R7"]
        self.assertEqual(c["result"], "fail")

    def test_a6_google_sign_in_allowed(self):
        html = '<script src="https://accounts.google.com/gsi/client"></script>'
        self.assertEqual(self.audit(**{"a.html": html})["A6"]["result"], "pass")

    def test_baseline_test_fields(self):
        c = self.audit(**{"CLAUDE.md": "HOUSE-RULES", "HANDOVER.md": "w " * 900, "README.md": "x"})
        self.assertEqual((c["R2"]["result"], c["R2"]["baseline_test"]), ("fail", "pass"))
        self.assertEqual((c["R5"]["result"], c["R5"]["baseline_test"]), ("fail", "pass"))
        self.assertEqual((c["R3"]["result"], c["R3"]["baseline_test"]), ("fail", "pass"))

    def test_a1(self):
        same = "SHORT_NAME = 'other'\r\nTHEME_COLOUR = 'y'  \nLANG = 'en'\nprint('x')   \n"
        self.assertEqual(self.audit(**{"tools/build-pages.py": same})["A1"]["result"], "pass")
        c = self.audit(**{"tools/build-pages.py": "print('y')\n"})["A1"]
        self.assertEqual((c["result"], c["why"]), ("fail", "build script differs from the template"))
        self.assertEqual(self.audit(**{"tools/build-pages.py": None})["A1"]["result"], "fail")
        self.assertEqual(self.audit(**{"tools/build-pages.py": None, "README.md": "Built with Vite. test"})["A1"]["result"], "pass")

    def test_a2_missing_icon(self):
        c = self.audit(**{"icons/icon-512.png": None})["A2"]
        self.assertEqual(c["result"], "fail")
        self.assertEqual(c["why"], "missing icons/icon-512.png")

    def test_a3(self):
        self.assertEqual(self.audit(**{"app.html": "<style>:root{--bg:#0;--fg-dim:#1}</style>"})["A3"]["result"], "fail")
        self.assertIn("--surface", self.audit(**{"app.html": "<style>:root{--bg:#0}</style>"})["A3"]["why"])

    def test_a4(self):
        self.assertEqual(self.audit(**{"tests/t.py": None})["A4"]["result"], "fail")
        c = self.audit(**{"README.md": "Nothing about it, the latest build."})["A4"]
        self.assertIn("README", c["why"])
        self.assertEqual(self.audit(**{"tests/t.py": None, "x.spec.js": ""})["A4"]["result"], "pass")
        self.assertEqual(self.audit(**{"tests/t.py": None, "tools/test-x.js": ""})["A4"]["result"], "pass")

    def test_a6(self):
        html = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/vue/3.4.1/vue.min.js"></script>'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto">'
                '<script src="local.js"></script>')
        self.assertEqual(self.audit(**{"a.html": html})["A6"]["result"], "pass")
        bad = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/vue/vue.min.js"></script>'
               '<script src="https://cdn.example.net/x.js"></script>'
               '<style>@import url("https://fonts.other.org/f.css");</style>')
        c = self.audit(**{"a.html": bad})["A6"]
        self.assertEqual(c["result"], "fail")
        self.assertIn("cdn.example.net", c["why"])
        self.assertIn("fonts.other.org", c["why"])
        self.assertIn("unpinned cdnjs script", c["why"])

    def test_a8(self):
        self.assertEqual(self.audit(**{"app.js": "nothing"})["A8"]["result"], "fail")
        self.assertEqual(self.audit(**{"app.js": "nothing", "tests/x.js": "jcm-sb-session"})["A8"]["result"], "fail")

    def test_a9_na_pass_unknown_fail(self):
        self.assertEqual(self.audit()["A9"]["result"], "n/a")
        sb = "import {createClient} from '@supabase/supabase-js';"
        self.assertEqual(self.audit(name="p", **{"app.js": sb + "c.schema('books')"})["A9"]["result"], "pass")
        self.assertEqual(self.audit(name="p2", **{"app.js": sb + "createClient(u,k,{db:{schema:'brain'}})"})["A9"]["result"], "pass")
        c = self.audit(name="u", **{"app.js": sb})["A9"]
        self.assertEqual((c["result"], c["why"]), ("unknown", "uses Supabase but the schema name couldn't be found"))
        self.assertEqual(self.audit(name="f", **{"app.js": sb + "c.schema('pantry')"})["A9"]["result"], "fail")

    def test_owner_only_parse(self):
        self.assertIn("brain", audit.owner_only_schemas(open(audit.OWNER_ONLY_SQL).read()))

    def test_non_app_gets_na(self):
        checks = self.audit(name="doc", app=False)
        self.assertTrue(all(checks[c]["result"] == "n/a" for c in audit.APP_CHECKS))

    def test_symlink_not_followed(self):
        secret = os.path.join(self.tmp, "outside.txt")
        write(self.tmp, "outside.txt", EMAIL)
        root = make_repo(self.tmp, "sl")
        os.symlink(secret, os.path.join(root, "link.txt"))
        c = audit.audit_repo("sl", root, "main", Ctx.make())["checks"]["R7"]
        self.assertEqual(c["result"], "pass")


class Baseline(unittest.TestCase):
    def test_gained_and_lost(self):
        base = {"taken": "2026-11-16", "repos": [
            {"repo": "a", "kind": "app", "claude_md": {"exists": True, "words": 900, "points_to_house_rules": True},
             "readme_exists": True, "handover_plan_files": []},
            {"repo": "b", "kind": "app", "claude_md": {"exists": True, "words": 100, "points_to_house_rules": True},
             "readme_exists": True, "handover_plan_files": ["HANDOVER.md"]},
            {"repo": "travel-app", "kind": "planning-only", "claude_md": {"exists": True, "words": 100,
                                                                         "points_to_house_rules": True}}]}

        def result(**kw):
            out = {c: audit.res(kw.get(c, "pass")) for c in audit.CHECKS}
            if kw.get("R2") == "full-only":  # fails the full standard but not the baseline's test
                out["R2"] = dict(audit.res("fail"), baseline_test="pass")
            return out
        now = [{"repo": "a", "kind": "app", "checks": result()},
               {"repo": "B", "kind": "app", "checks": result()},
               {"repo": "b", "kind": "app", "checks": result(R2="fail", R5="fail")},
               {"repo": "travel-app", "kind": "other", "checks": result()},
               {"repo": "newbie", "kind": "app", "checks": result()}]
        cmp_ = audit.compare(base, now)
        r2, r5, r1 = cmp_["rows"]["R2"], cmp_["rows"]["R5"], cmp_["rows"]["R1"]
        self.assertEqual((r2["gained"], r2["lost"]), (["a"], ["b"]))
        self.assertEqual((r2["baseline_count"], r2["now_count"]), (2, 4))
        self.assertEqual((r5["gained"], r5["lost"]), (["a", "travel-app"], ["b"]))
        self.assertEqual(r1["gained"], ["travel-app"])
        self.assertEqual(cmp_["new_repos"], ["B", "newbie"])
        self.assertFalse(cmp_["rows"]["A9"]["baseline_recorded"])
        now[2]["checks"] = result(R2="full-only")
        r2 = audit.compare(base, now)["rows"]["R2"]
        self.assertEqual(r2["lost"], [])  # stricter test today, not a real loss
        self.assertEqual((r2["now_count"], r2["now_full_count"]), (5, 4))

    def test_real_baseline_r1_is_17(self):
        base = json.load(open(audit.DEFAULT_BASELINE))
        n = sum(1 for b in base["repos"] if audit.baseline_statuses(b)["R1"] == "pass")
        self.assertEqual(n, 17)


class Runs(Base):
    def test_repos_json_file_and_issue_states(self):
        pj = os.path.join(self.tmp, "r.json")
        out = os.path.join(self.tmp, "out")
        json.dump({"repos": [{"name": "Gone"}], "standard_issues": []}, open(pj, "w"))
        with mock.patch.object(audit, "clone_repo", return_value="nope"), \
                mock.patch.object(audit, "fetch_repos_json", side_effect=AssertionError("no data-branch clone")), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            audit.main(["--repos-json", pj, "--out-dir", out, "--month", "2026-11"])
        self.assertIn("None open.", open(os.path.join(out, "audit-2026-11.md")).read())

    def test_unreadable_repo_list_exits_nonzero(self):
        with mock.patch.object(audit, "fetch_repos_json", return_value=None), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--out-dir", os.path.join(self.tmp, "o")]), 1)

    def test_no_private_text_in_any_output(self):
        make_repo(self.tmp, "leaky", **{"notes.txt": "mail %s" % EMAIL, "k.js": "const SHEET_ID = '%s';" % SHEET})
        make_repo(self.tmp, "fine")
        out = os.path.join(self.tmp, "out")
        so, se = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
            audit.main(["--repos-dir", self.tmp, "--out-dir", out, "--month", "2026-11"])
        files = [open(os.path.join(out, f)).read() for f in os.listdir(out)]
        self.assertEqual(len(files), 2)
        blob = "\n".join(files + [so.getvalue(), se.getvalue()])
        self.assertNotIn(EMAIL, blob)
        self.assertNotIn("gmail", blob)
        self.assertNotIn(SHEET, blob)
        md = open(os.path.join(out, "audit-2026-11.md")).read()
        self.assertIn("leaky: R7 (email address in notes.txt (1)", md)
        self.assertIn("## Not checked by the script", md)
        self.assertIn("Not available yet: the daily run hasn't collected them.", md)

    def test_clone_failure_makes_everything_unknown(self):
        listed = {"repos": [{"name": "Gone", "default_branch": "main"}, {"name": "old", "archived": True}],
                  "standard_issues": [{"title": "Add X", "html_url": "https://github.com/o/control-room/issues/1",
                                       "created_at": "d"}]}
        out = os.path.join(self.tmp, "out")
        with mock.patch.object(audit, "fetch_repos_json", return_value=listed), \
                mock.patch.object(audit, "clone_repo", return_value="the repo couldn't be downloaded"), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            audit.main(["--out-dir", out, "--month", "2026-11"])
        data = json.load(open(os.path.join(out, "audit-2026-11.json")))
        self.assertEqual([r["repo"] for r in data["repos"]], ["Gone"])
        checks = data["repos"][0]["checks"]
        self.assertTrue(all(v["result"] == "unknown" and "downloaded" in v["why"] for v in checks.values()))
        self.assertEqual(data["standard_issues"], [{"title": "Add X", "url": "https://github.com/o/control-room/issues/1"}])
        md = open(os.path.join(out, "audit-2026-11.md")).read()
        self.assertIn("## Couldn't check automatically\n- Gone: R1 (the repo couldn't be downloaded)", md)
        self.assertIn("- Add X https://github.com/o/control-room/issues/1", md)


if __name__ == "__main__":
    unittest.main()
