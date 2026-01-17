#!/usr/bin/env python3
"""Aggregate raw GitHub data into weekly summary."""

import json
from datetime import datetime
from pathlib import Path


def load_raw_data() -> dict:
    """Load raw data from fetch step."""
    raw_path = Path(__file__).parent.parent / "data_raw" / "raw.json"
    with open(raw_path) as f:
        return json.load(f)


def aggregate(raw: dict) -> dict:
    """Aggregate repository data into summary."""
    repos = raw["repositories"]
    
    # Per-repo summaries
    repo_summaries = []
    for repo in repos:
        repo_summaries.append({
            "name": repo["name"],
            "url": repo["url"],
            "description": repo.get("description"),
            "activity": {
                "commits": repo.get("commits_this_week", 0),
                "prs_opened": repo.get("prs_opened_this_week", 0),
                "prs_merged": repo.get("prs_merged_this_week", 0),
                "issues_opened": repo.get("issues_opened_this_week", 0),
                "issues_closed": repo.get("issues_closed_this_week", 0),
            },
            "state": {
                "stars": repo.get("stars", 0),
                "forks": repo.get("forks", 0),
                "open_issues": repo.get("issues_open", 0),
                "open_prs": repo.get("prs_open", 0),
                "contributors": repo.get("total_contributors", 0),
            },
            "authors": repo.get("commit_authors", []),
        })
    
    # Overall totals
    totals = {
        "repositories": len(repos),
        "commits": sum(r.get("commits_this_week", 0) for r in repos),
        "prs_opened": sum(r.get("prs_opened_this_week", 0) for r in repos),
        "prs_merged": sum(r.get("prs_merged_this_week", 0) for r in repos),
        "issues_opened": sum(r.get("issues_opened_this_week", 0) for r in repos),
        "issues_closed": sum(r.get("issues_closed_this_week", 0) for r in repos),
        "total_stars": sum(r.get("stars", 0) for r in repos),
        "total_contributors": len(set(
            author for r in repos for author in r.get("commit_authors", [])
        )),
    }
    
    # Active repos (any activity this week)
    active_repos = [
        r["name"] for r in repos
        if r.get("commits_this_week", 0) > 0
        or r.get("prs_opened_this_week", 0) > 0
        or r.get("issues_opened_this_week", 0) > 0
    ]
    
    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "fetched_at": raw["fetched_at"],
        "totals": totals,
        "active_repos": active_repos,
        "repositories": repo_summaries,
    }


def main():
    """Main entry point."""
    raw = load_raw_data()
    summary = aggregate(raw)
    
    # Save to docs/data with date filename
    output_dir = Path(__file__).parent.parent / "docs" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = summary["date"]
    output_path = output_dir / f"{date_str}.json"
    
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"Saved aggregated data to {output_path}")


if __name__ == "__main__":
    main()
