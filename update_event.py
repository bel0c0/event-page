"""
update_event.py — Push event data + images to GitHub repo.
Vercel auto-deploys on every push, so the live page updates automatically.

Usage:
  python update_event.py \
    --title "My Event" \
    --subtitle "Tagline here" \
    --date "May 18, 2026" \
    --time "6:00 PM - 9:00 PM" \
    --location "123 Main St" \
    --description "Event description..." \
    --highlights "Free food" "Live music" "Networking" \
    --images /path/to/hero.jpg /path/to/photo2.jpg \
    --rsvp-url "https://example.com/rsvp"

Environment variables required:
  GITHUB_TOKEN   — Personal access token with 'repo' scope
  GITHUB_REPO    — e.g. "username/event-page"
"""

import argparse
import base64
import json
import os
import sys
import requests
from pathlib import Path

GITHUB_API = "https://api.github.com"


def get_env(name):
    val = os.environ.get(name)
    if not val:
        print(f"Error: {name} environment variable is required.")
        sys.exit(1)
    return val


def github_headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_file_sha(token, repo, path):
    """Get the SHA of an existing file (needed for updates)."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    r = requests.get(url, headers=github_headers(token))
    if r.status_code == 200:
        return r.json()["sha"]
    return None


def push_file(token, repo, path, content_bytes, message, branch="main"):
    """Create or update a file in the GitHub repo."""
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    encoded = base64.b64encode(content_bytes).decode("utf-8")

    payload = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }

    # If file exists, include its SHA to update it
    sha = get_file_sha(token, repo, path)
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=github_headers(token), json=payload)
    if r.status_code in (200, 201):
        print(f"  OK: {path}")
        return True
    else:
        print(f"  FAILED: {path} — {r.status_code} {r.text[:200]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Update event page via GitHub API")
    parser.add_argument("--title", required=True, help="Event title")
    parser.add_argument("--subtitle", default="", help="Event subtitle/tagline")
    parser.add_argument("--date", required=True, help="Event date (e.g. 'May 18, 2026')")
    parser.add_argument("--time", default="", help="Event time (e.g. '6:00 PM - 9:00 PM')")
    parser.add_argument("--location", default="", help="Event location")
    parser.add_argument("--description", required=True, help="Event description")
    parser.add_argument("--highlights", nargs="*", default=[], help="List of highlight items")
    parser.add_argument("--images", nargs="*", default=[], help="Paths to image files to upload")
    parser.add_argument("--rsvp-url", default="", help="RSVP link URL")
    parser.add_argument("--email", default="", help="Contact email")
    parser.add_argument("--phone", default="", help="Contact phone")
    parser.add_argument("--branch", default="main", help="Git branch (default: main)")

    args = parser.parse_args()

    token = get_env("GITHUB_TOKEN")
    repo = get_env("GITHUB_REPO")

    print(f"Updating event page in {repo}...\n")

    # 1. Upload images first
    image_paths_in_repo = []
    for img_path in args.images:
        p = Path(img_path)
        if not p.exists():
            print(f"  WARNING: Image not found: {img_path}, skipping")
            continue

        repo_path = f"images/{p.name}"
        image_paths_in_repo.append(repo_path)

        print(f"Uploading image: {p.name}")
        with open(p, "rb") as f:
            push_file(token, repo, repo_path, f.read(),
                      f"Update image: {p.name}", args.branch)

    # 2. Build and push event.json
    event_data = {
        "title": args.title,
        "subtitle": args.subtitle,
        "date": args.date,
        "time": args.time,
        "location": args.location,
        "description": args.description,
        "highlights": args.highlights,
        "rsvp_url": args.rsvp_url,
        "images": image_paths_in_repo if image_paths_in_repo else ["images/hero.jpg"],
        "contact": {
            "email": args.email,
            "phone": args.phone,
        },
    }

    event_json = json.dumps(event_data, indent=2)
    print("\nUpdating event.json")
    push_file(token, repo, "event.json", event_json.encode("utf-8"),
              f"Update event: {args.title}", args.branch)

    print("\nDone! Vercel will auto-deploy in ~30 seconds.")


if __name__ == "__main__":
    main()
