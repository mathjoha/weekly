#!/usr/bin/env python3
"""Fetch repository data from GitHub API."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_headers() -> dict:
    """Get headers for GitHub API requests."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_repo_data(owner: str, repo: str, config: dict) -> dict:
    """Fetch data for a single repository."""
    headers = get_headers()
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    # Basic repo info
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    repo_info = response.json()
    
    # Calculate date window for activity
    since = (datetime.utcnow() - timedelta(days=config.get("activity_window", 7))).isoformat() + "Z"
    
    data = {
        "name": repo_info["full_name"],
        "description": repo_info.get("description"),
        "url": repo_info["html_url"],
        "stars": repo_info["stargazers_count"],
        "forks": repo_info["forks_count"],
        "open_issues": repo_info["open_issues_count"],
        "default_branch": repo_info["default_branch"],
        "updated_at": repo_info["updated_at"],
    }
    
    # Recent commits
    if "commits" in config.get("metrics", []):
        commits_url = f"{base_url}/commits"
        response = requests.get(commits_url, headers=headers, params={"since": since, "per_page": 100})
        if response.status_code == 200:
            commits = response.json()
            data["commits_this_week"] = len(commits)
            data["commit_authors"] = list(set(
                c["commit"]["author"]["name"] for c in commits if c.get("commit", {}).get("author")
            ))
    
    # Recent pull requests
    if "pull_requests" in config.get("metrics", []):
        prs_url = f"{base_url}/pulls"
        response = requests.get(prs_url, headers=headers, params={"state": "all", "per_page": 100})
        if response.status_code == 200:
            prs = response.json()
            recent_prs = [pr for pr in prs if pr["created_at"] >= since]
            data["prs_opened_this_week"] = len([pr for pr in recent_prs if pr["created_at"] >= since])
            data["prs_merged_this_week"] = len([
                pr for pr in recent_prs 
                if pr.get("merged_at") and pr["merged_at"] >= since
            ])
            data["prs_open"] = len([pr for pr in prs if pr["state"] == "open"])
    
    # Recent issues
    if "issues" in config.get("metrics", []):
        issues_url = f"{base_url}/issues"
        response = requests.get(issues_url, headers=headers, params={"state": "all", "since": since, "per_page": 100})
        if response.status_code == 200:
            issues = [i for i in response.json() if "pull_request" not in i]  # Exclude PRs
            data["issues_opened_this_week"] = len([i for i in issues if i["created_at"] >= since])
            data["issues_closed_this_week"] = len([
                i for i in issues 
                if i.get("closed_at") and i["closed_at"] >= since
            ])
            data["issues_open"] = len([i for i in issues if i["state"] == "open"])
    
    # Contributors
    if "contributors" in config.get("metrics", []):
        contributors_url = f"{base_url}/contributors"
        response = requests.get(contributors_url, headers=headers, params={"per_page": 100})
        if response.status_code == 200:
            data["total_contributors"] = len(response.json())
    
    return data


def fetch_org_repos(org: str, config: dict) -> list[str]:
    """Fetch all repository names for an organization."""
    headers = get_headers()
    url = f"https://api.github.com/orgs/{org}/repos"
    repos = []
    page = 1
    
    while True:
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        response.raise_for_status()
        page_repos = response.json()
        
        if not page_repos:
            break
            
        repos.extend([r["full_name"] for r in page_repos if not r["archived"]])
        page += 1
    
    return repos


def main():
    """Main entry point."""
    config = load_config()
    exclude = set(config.get("exclude", []))
    
    # Gather all repos to fetch
    all_repos = set(config.get("repositories", []))
    
    for org in config.get("organizations", []):
        org_repos = fetch_org_repos(org, config)
        all_repos.update(org_repos)
    
    # Remove excluded repos
    all_repos -= exclude
    
    # Fetch data for each repo
    results = []
    for repo_full_name in sorted(all_repos):
        owner, repo = repo_full_name.split("/")
        print(f"Fetching {repo_full_name}...")
        try:
            data = fetch_repo_data(owner, repo, config)
            results.append(data)
        except requests.HTTPError as e:
            print(f"  Error fetching {repo_full_name}: {e}")
    
    # Save raw results
    output_dir = Path(__file__).parent.parent / "data_raw"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "raw.json", "w") as f:
        json.dump({
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "repositories": results,
        }, f, indent=2)
    
    print(f"Fetched data for {len(results)} repositories")


if __name__ == "__main__":
    main()
