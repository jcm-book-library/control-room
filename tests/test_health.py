"""Run: python3 tests/test_health.py   (no network)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import health  # noqa: E402

GEN = "2026-11-25T01:00:00Z"
BASE = {"old"}


def repo(name="old", **kw):
    r = {"name": name, "health": [], "pull_requests": {"count": 0, "items": []}, "latest_run": None,
         "quiet": False, "dormant": False, "days_quiet": 1, "charter_missing": False}
    r.update(kw)
    return r


def pr(created, draft=False):
    return {"title": "Fix", "html_url": "http://pr", "created_at": created, "draft": draft}


def run(repos, ideas=(), **extra):
    d = {"generated_at": GEN, "repos": repos, "ideas": list(ideas)}
    d.update(extra)
    return health.build(d, BASE)


class Health(unittest.TestCase):
    def test_all_clear(self):
        text, n, m = run([repo()])
        self.assertEqual((n, m), (0, 0))
        self.assertIn("ALL CLEAR: nothing needs you.", text)
        self.assertNotIn("NEEDS YOU", text)
        self.assertIn("- 1 repos, 0 open pull requests, 0 open ideas.", text)
        self.assertTrue(text.endswith("Next update: tomorrow morning.\n"))

    def test_pr_age_and_draft(self):
        text, n, _ = run([repo(pull_requests={"count": 3, "items": [
            pr("2026-11-17T00:00:00Z"), pr("2026-11-19T01:00:00Z"), pr("2026-10-01T00:00:00Z", True)]})])
        self.assertEqual(n, 1)
        self.assertIn("pull request open 8 days: Fix http://pr", text)

    def test_failed_run(self):
        text, n, _ = run([repo(latest_run={"conclusion": "failure", "name": "CI", "html_url": "http://run"},
                               health=["Last run on main failed: CI"])])
        self.assertEqual(n, 1)
        self.assertIn("old: the latest run on main failed (CI): http://run", text)

    def test_default_branch(self):
        text, n, m = run([repo(health=["Default branch is dev, not main"]), repo("b", health=["No main branch"])])
        self.assertEqual((n, m), (2, 0))
        self.assertIn("old: default branch is dev, not main. Fix: repo Settings, General, Default branch.", text)
        self.assertIn("b: has no main branch.", text)

    def test_new_repo_charter(self):
        text, n, _ = run([repo("fresh", charter_missing=True), repo("old", charter_missing=True)])
        self.assertEqual(n, 1)
        self.assertIn("fresh: new repo with no project.json.", text)
        self.assertNotIn("old: new repo", text)

    def test_dormant_and_other_health(self):
        text, n, m = run([repo(dormant=True, quiet=True, days_quiet=120, health=["Pages mismatch"])])
        self.assertEqual((n, m), (0, 2))
        self.assertIn("old: no activity for 120 days. Pause it or archive it?", text)
        self.assertIn("- old: Pages mismatch", text)
        self.assertNotIn("Quiet for", text)

    def test_quiet_and_ideas(self):
        ideas = [{"title": "a", "created_at": "2026-01-01"}, {"title": "d", "created_at": "2026-04-01"},
                 {"title": "b", "created_at": "2026-02-01"}, {"title": "c", "created_at": "2026-03-01"}]
        text, _, _ = run([repo("q", quiet=True, days_quiet=50)], ideas)
        self.assertIn("Quiet for 30 to 90 days: q.", text)
        self.assertIn("Newest ideas: d; c; b.", text)
        self.assertIn("4 open ideas", text)

    def test_error_field(self):
        text, n, _ = run([], error="No repos found.")
        self.assertEqual(n, 1)
        self.assertIn("The daily dashboard run had a problem: No repos found. Open control-room", text)

    def test_melbourne_rollover(self):
        text, _, _ = health.build({"generated_at": "2026-11-24T19:17:00Z", "repos": []}, BASE)
        self.assertTrue(text.startswith("Health check, Wed 25 Nov 2026\n"))
        self.assertIn("Data from the daily run on 25 Nov 2026, 6:17am Melbourne.", text)

    def test_unreadable_input(self):
        out = os.path.join(os.environ.get("TMPDIR", "/tmp"), "health-test-out.md")
        self.assertEqual(health.main(["x", "/nonexistent/repos.json", out]), 1)
        os.remove(out)


if __name__ == "__main__":
    unittest.main()
