#!/usr/bin/env python3
"""Write the daily health report from the repo data that collect.py just wrote.

Usage: python3 tools/health.py [repos_json] [out_md]
Defaults: site/data/repos.json and site/data/health-latest.md
Python 3 standard library only. Public repo facts only. Exits 1 only if the input can't be read.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Australia/Melbourne")
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports", "baseline-2026-11-16.json")


def parse(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def baseline_names(path=BASELINE):
    try:
        with open(path, encoding="utf-8") as f:
            return {r.get("repo") for r in json.load(f).get("repos", [])}
    except Exception:
        return set()


def build(data, baseline):
    """Return (text, needs_count, look_count)."""
    gen = parse(data.get("generated_at")) or datetime.now(timezone.utc)
    local = gen.astimezone(TZ)
    day = "%s %d %s %d" % (local.strftime("%a"), local.day, local.strftime("%b"), local.year)
    hour = local.hour % 12 or 12
    when = "%d:%02d%s" % (hour, local.minute, "am" if local.hour < 12 else "pm")
    needs, look = [], []

    if data.get("error"):
        needs.append("The daily dashboard run had a problem: %s. Open control-room, Actions, "
                     "Collect repo data and publish." % str(data["error"]).rstrip("."))

    repos = data.get("repos") or []
    for r in repos:
        name = r.get("name") or "unknown"
        used = set()
        for msg in r.get("health") or []:
            m = re.match(r"Default branch is (.+?), not main", msg)
            if m:
                needs.append("%s: default branch is %s, not main. Fix: repo Settings, General, Default branch."
                             % (name, m.group(1)))
                used.add(msg)
            elif msg.startswith("No main branch"):
                needs.append("%s: has no main branch." % name)
                used.add(msg)
            elif msg.startswith("Last run on main failed"):
                used.add(msg)  # reported below from latest_run
        for p in (r.get("pull_requests") or {}).get("items") or []:
            created = parse(p.get("created_at"))
            if created and not p.get("draft") and (gen - created).days > 7:
                needs.append("%s: pull request open %d days: %s %s"
                             % (name, (gen - created).days, p.get("title"), p.get("html_url")))
        run = r.get("latest_run") or {}
        if run.get("conclusion") == "failure":
            needs.append("%s: the latest run on main failed (%s): %s"
                         % (name, run.get("name") or "unnamed run", run.get("html_url")))
        if name not in baseline and r.get("charter_missing"):
            needs.append("%s: new repo with no project.json. Fix: add project.json, a CLAUDE.md that "
                         "points at the house rules, and a README (see templates/)." % name)
        if r.get("dormant"):
            look.append("%s: no activity for %s days. Pause it or archive it?" % (name, r.get("days_quiet")))
        for msg in r.get("health") or []:
            if msg not in used:
                look.append("%s: %s" % (name, msg))

    prs = sum((r.get("pull_requests") or {}).get("count") or 0 for r in repos)
    ideas = data.get("ideas") or []
    good = ["%d repos, %d open pull requests, %d open ideas." % (len(repos), prs, len(ideas))]
    quiet = [r.get("name") for r in repos if r.get("quiet") and not r.get("dormant")]
    if quiet:
        good.append("Quiet for 30 to 90 days: %s." % ", ".join(quiet))
    titles = [i.get("title") for i in sorted(ideas, key=lambda i: i.get("created_at") or "", reverse=True)
              if i.get("title")][:3]
    if titles:
        good.append("Newest ideas: %s." % "; ".join(titles))

    lines = ["Health check, " + day, "Data from the daily run on %d %s %d, %s Melbourne."
             % (local.day, local.strftime("%b"), local.year, when), ""]
    if not needs and not look:
        lines += ["ALL CLEAR: nothing needs you.", ""]
    if needs:
        lines += ["NEEDS YOU"] + ["- " + x for x in needs] + [""]
    if look:
        lines += ["WORTH A LOOK"] + ["- " + x for x in look] + [""]
    lines += ["GOOD TO KNOW"] + ["- " + x for x in good] + ["", "Next update: tomorrow morning."]
    return "\n".join(lines) + "\n", len(needs), len(look)


def main(argv):
    src = argv[1] if len(argv) > 1 else "site/data/repos.json"
    out = argv[2] if len(argv) > 2 else "site/data/health-latest.md"
    try:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except Exception as e:
        text = "Health check: could not read the dashboard data (%s).\n" % type(e).__name__
        code = 1
        counts = (1, 0)
    else:
        text, n, m = build(data, baseline_names())
        code, counts = 0, (n, m)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print("health: %d need you, %d worth a look" % counts)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
