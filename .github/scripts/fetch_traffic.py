"""
Fetches GitHub traffic data (views + clones) for the current repo and
appends any new days to traffic-history/views.json and clones.json,
plus a combined traffic-history/summary.csv for easy charting.

Requires env vars: GH_TOKEN, REPO (in "owner/repo" format).
"""
import json
import os
import csv
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

GH_TOKEN = os.environ["GH_TOKEN"]
REPO = os.environ["REPO"]
API_BASE = f"https://api.github.com/repos/{REPO}/traffic"
OUT_DIR = Path("traffic-history")
OUT_DIR.mkdir(exist_ok=True)


def api_get(path):
    req = urllib.request.Request(
        f"{API_BASE}/{path}",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def load_existing(filename):
    path = OUT_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def merge_daily(existing, new_entries):
    """new_entries is a list of {"timestamp": ..., "count": ..., "uniques": ...}"""
    for entry in new_entries:
        day = entry["timestamp"][:10]  # YYYY-MM-DD
        existing[day] = {"count": entry["count"], "uniques": entry["uniques"]}
    return existing


def save(filename, data):
    with open(OUT_DIR / filename, "w") as f:
        json.dump(dict(sorted(data.items())), f, indent=2)


def write_csv(views, clones):
    all_days = sorted(set(views) | set(clones))
    with open(OUT_DIR / "summary.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "views", "unique_views", "clones", "unique_clones"])
        for day in all_days:
            v = views.get(day, {"count": 0, "uniques": 0})
            c = clones.get(day, {"count": 0, "uniques": 0})
            writer.writerow([day, v["count"], v["uniques"], c["count"], c["uniques"]])


def main():
    views_data = api_get("views")
    clones_data = api_get("clones")

    existing_views = load_existing("views.json")
    existing_clones = load_existing("clones.json")

    merged_views = merge_daily(existing_views, views_data.get("views", []))
    merged_clones = merge_daily(existing_clones, clones_data.get("clones", []))

    save("views.json", merged_views)
    save("clones.json", merged_clones)
    write_csv(merged_views, merged_clones)

    print(f"Updated {len(merged_views)} days of views, {len(merged_clones)} days of clones "
          f"as of {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
