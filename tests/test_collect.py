"""Run: python3 tests/test_collect.py   (no network: the GitHub API is faked)"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import collect  # noqa: E402


def fake_api(routes):
    """routes: {path_prefix: (status, body)}. Unknown paths answer 404."""
    calls = []

    def api(path):
        calls.append(path)
        for prefix, (code, body) in routes.items():
            if path.startswith(prefix):
                collect.LAST_STATUS["code"] = code
                return body if code == 200 else None
        collect.LAST_STATUS["code"] = 404
        return None
    return api, calls


REPO = {"name": "tv-tracker", "default_branch": "main", "pushed_at": "2026-10-01T00:00:00Z"}


class ListRepos(unittest.TestCase):
    def test_org(self):
        api, calls = fake_api({"/orgs/x/repos?per_page=100&type=all&page=1": (200, [REPO]),
                               "/orgs/x/repos?per_page=100&type=all&page=2": (200, [])})
        with mock.patch.object(collect, "api", api):
            repos, kind = collect.list_repos("x")
        self.assertEqual((len(repos), kind), (1, "org"))
        self.assertFalse(any(c.startswith("/users/") for c in calls))

    def test_user_fallback_on_404(self):
        api, calls = fake_api({"/orgs/x/repos": (404, None),
                               "/users/x/repos?type=owner&per_page=100&page=1": (200, [REPO, dict(REPO, name="b")]),
                               "/users/x/repos?type=owner&per_page=100&page=2": (200, [])})
        with mock.patch.object(collect, "api", api):
            repos, kind = collect.list_repos("x")
        self.assertEqual(([r["name"] for r in repos], kind), (["tv-tracker", "b"], "user"))

    def test_neither(self):
        api, _ = fake_api({})
        with mock.patch.object(collect, "api", api):
            self.assertEqual(collect.list_repos("x"), ([], None))

    def test_org_error_other_than_404_does_not_fall_back(self):
        api, calls = fake_api({"/orgs/x/repos": (500, None)})
        with mock.patch.object(collect, "api", api):
            self.assertEqual(collect.list_repos("x"), ([], None))
        self.assertFalse(any(c.startswith("/users/") for c in calls))


class Ideas(unittest.TestCase):
    def test_qualifier(self):
        for kind, q in (("user", "q=user:x+"), ("org", "q=org:x+")):
            api, calls = fake_api({"/search/issues": (200, {"items": []})})
            with mock.patch.object(collect, "api", api):
                collect.get_ideas("x", kind)
            self.assertIn(q, calls[0])


class Main(unittest.TestCase):
    def run_main(self, routes):
        api, _ = fake_api(routes)
        out = os.path.join(tempfile.mkdtemp(), "repos.json")
        with mock.patch.object(collect, "api", api), mock.patch.object(collect, "OWNER", "x"), \
                mock.patch.object(sys, "argv", ["collect.py", out]):
            try:
                collect.main()
                code = 0
            except SystemExit as e:
                code = e.code
        with open(out) as f:
            return code, json.load(f)

    def test_empty_writes_error_and_fails(self):
        code, data = self.run_main({"/users/x/repos": (200, [])})
        self.assertEqual(code, 1)
        self.assertEqual(data["repos"], [])
        self.assertIn("No repos found", data["error"])

    def test_unknown_owner_writes_error_and_fails(self):
        code, data = self.run_main({})
        self.assertEqual(code, 1)
        self.assertIn("Couldn't list repos", data["error"])

    def test_user_account_succeeds(self):
        code, data = self.run_main({"/users/x/repos?type=owner&per_page=100&page=1": (200, [REPO]),
                                    "/search/issues?q=user:x": (200, {"items": []})})
        self.assertEqual(code, 0)
        self.assertNotIn("error", data)
        self.assertEqual((data["owner_type"], len(data["repos"])), ("user", 1))


if __name__ == "__main__":
    unittest.main()
