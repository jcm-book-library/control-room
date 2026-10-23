#!/usr/bin/env python3
"""Collect public data about every repo owned by a GitHub account and write it as JSON.

The owner can be a personal account or an organisation: the organisation endpoint is
tried first and a 404 falls back to the user endpoint.

Usage: python3 tools/collect.py [output_path] [--limit N]
Env:   GITHUB_TOKEN (optional), OWNER (default jcm-book-library; ORG still accepted)
Python 3 standard library only. One failed call never fails the whole run, but finding
no repos at all writes an "error" field and exits non-zero so nothing empty gets published.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
OWNER = os.environ.get("OWNER") or os.environ.get("ORG") or "jcm-book-library"
TOKEN = os.environ.get("GITHUB_TOKEN")
LAST_STATUS = {"code": None}


def api(path):
    """GET a GitHub API path. Returns parsed JSON or None. Sets LAST_STATUS['code']."""
    url = path if path.startswith("http") else API + path
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "control-room-collector",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    LAST_STATUS["code"] = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            LAST_STATUS["code"] = resp.status
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        LAST_STATUS["code"] = e.code
        print("warn: %s -> HTTP %s" % (path, e.code), file=sys.stderr)
    except Exception as e:  # timeouts, DNS, bad JSON
        print("warn: %s -> %s" % (path, e), file=sys.stderr)
    return None


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def list_repos(owner):
    """Return (repos, owner_type). owner_type is "org", "user" or None if neither endpoint worked."""
    owner_type = "org"
    path = "/orgs/%s/repos?per_page=100&type=all&page=%d"
    repos, page = [], 1
    while page <= 20:
        batch = api(path % (owner, page))
        if batch is None and page == 1 and owner_type == "org" and LAST_STATUS["code"] == 404:
            print("info: %s is not an organisation, trying it as a user account" % owner, file=sys.stderr)
            owner_type = "user"
            path = "/users/%s/repos?type=owner&per_page=100&page=%d"
            continue
        if batch is None and page == 1:
            return [], None
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos, owner_type


def get_main(o, r):
    d = api("/repos/%s/%s/branches/main" % (o, r))
    if not d:
        return {"exists": LAST_STATUS["code"] != 404 and None, "sha": None, "date": None, "message": None,
                "_code": LAST_STATUS["code"]}
    c = d.get("commit") or {}
    inner = c.get("commit") or {}
    msg = (inner.get("message") or "").split("\n")[0]
    return {"exists": True, "sha": c.get("sha"),
            "date": (inner.get("committer") or {}).get("date"), "message": msg,
            "_code": 200}


def get_charter(o, r):
    d = api("/repos/%s/%s/contents/project.json?ref=main" % (o, r))
    if not d or not isinstance(d, dict) or not d.get("content"):
        return None
    try:
        return json.loads(base64.b64decode(d["content"]).decode("utf-8"))
    except Exception as e:
        print("warn: bad project.json in %s: %s" % (r, e), file=sys.stderr)
        return None


def get_run(o, r):
    d = api("/repos/%s/%s/actions/runs?branch=main&per_page=1" % (o, r))
    runs = (d or {}).get("workflow_runs") or []
    if not runs:
        return None
    x = runs[0]
    return {"name": x.get("name"), "status": x.get("status"), "conclusion": x.get("conclusion"),
            "html_url": x.get("html_url"), "created_at": x.get("created_at")}


def get_pages(o, r):
    d = api("/repos/%s/%s/pages" % (o, r))
    code = LAST_STATUS["code"]
    if not d:
        return None, code
    src = d.get("source") or {}
    return {"html_url": d.get("html_url"), "build_type": d.get("build_type"),
            "source": {"branch": src.get("branch")} if src else None}, code


def get_prs(o, r):
    d = api("/repos/%s/%s/pulls?state=open&per_page=100" % (o, r))
    if d is None:
        return {"count": None, "items": []}
    return {"count": len(d), "items": [{"title": p.get("title"), "html_url": p.get("html_url")} for p in d]}


def get_ideas(owner, owner_type):
    qualifier = "user" if owner_type == "user" else "org"
    d = api("/search/issues?q=%s:%s+label:idea+is:issue+is:open&per_page=100" % (qualifier, owner))
    out = []
    for i in (d or {}).get("items", []):
        repo = (i.get("repository_url") or "").rsplit("/", 1)[-1]
        out.append({"repo": repo, "title": i.get("title"), "html_url": i.get("html_url"),
                    "created_at": i.get("created_at")})
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out


def build_repo(org, repo, now):
    name = repo["name"]
    main = get_main(org, name)
    main_code = main.pop("_code")
    charter = get_charter(org, name) if main["exists"] else None
    run = get_run(org, name)
    pages, pages_code = get_pages(org, name)
    prs = get_prs(org, name)

    health = []
    default = repo.get("default_branch")
    if main_code == 404:
        health.append("No main branch")
    if default and default != "main":
        health.append("Default branch is %s, not main" % default)
    if run and run.get("conclusion") == "failure":
        health.append("Last run on main failed: %s" % (run.get("name") or "unnamed run"))
    if pages and pages.get("build_type") == "legacy" and (pages.get("source") or {}).get("branch") != "main":
        health.append("GitHub Pages publishes from %s, not main" % ((pages.get("source") or {}).get("branch") or "an unknown branch"))
    if charter and charter.get("live") and pages is None and pages_code == 404:
        health.append("Charter says it's live but Pages is off")

    last = parse_date(main.get("date")) or parse_date(repo.get("pushed_at"))
    days = max(0, (now - last).days) if last else None
    return {
        "name": name,
        "html_url": repo.get("html_url"),
        "description": repo.get("description"),
        "default_branch": default,
        "pushed_at": repo.get("pushed_at"),
        "open_issues_count": repo.get("open_issues_count"),
        "main": main,
        "charter": charter,
        "latest_run": run,
        "pages": pages,
        "pull_requests": prs,
        "health": health,
        "days_quiet": days,
        "quiet": days is not None and days > 30,
        "dormant": days is not None and days > 90,
        "charter_missing": charter is None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", nargs="?", default="site/data/repos.json")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)

    listed, owner_type = list_repos(OWNER)
    raw = [r for r in listed if not r.get("archived")]
    if args.limit:
        raw = raw[: args.limit]
    repos = []
    for r in raw:
        try:
            repos.append(build_repo(OWNER, r, now))
        except Exception as e:  # never let one repo sink the run
            print("warn: skipped %s: %s" % (r.get("name"), e), file=sys.stderr)
    ideas = get_ideas(OWNER, owner_type) if owner_type else []

    out = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "owner": OWNER, "owner_type": owner_type,
           "repos": repos, "ideas": ideas}
    error = None
    if owner_type is None:
        error = ("Couldn't list repos for %s: GitHub answered HTTP %s. A 404 means it isn't an "
                 "organisation or a user account." % (OWNER, LAST_STATUS["code"] or "no response"))
    elif not repos:
        error = "No repos found for %s (checked as %s account). The collector found nothing to show." % (
            OWNER, "an organisation" if owner_type == "org" else "a user")
    if error:
        out["error"] = error
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote %s: %d repos, %d ideas" % (args.output, len(repos), len(ideas)))
    if error:
        print("error: " + error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
