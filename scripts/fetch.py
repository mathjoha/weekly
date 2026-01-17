#!/usr/bin/env python3
"""Fetch repository data from GitHub API."""

import fnmatch
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
        "homepage": repo_info.get("homepage") or None,
        "stars": repo_info["stargazers_count"],
        "forks": repo_info["forks_count"],
        "open_issues": repo_info["open_issues_count"],
        "default_branch": repo_info["default_branch"],
        "updated_at": repo_info["updated_at"],
    }
    
    # Recent commits (from default branch + dev + most recently updated branch)
    if "commits" in config.get("metrics", []):
        commits_url = f"{base_url}/commits"
        branches_to_check = {data["default_branch"]}

        # Get branches to find 'dev' and most recently updated
        branches_url = f"{base_url}/branches"
        response = requests.get(branches_url, headers=headers, params={"per_page": 30})
        if response.status_code == 200:
            branches = response.json()
            # Add 'dev' if it exists
            branch_names = {b["name"] for b in branches}
            if "dev" in branch_names:
                branches_to_check.add("dev")
            # Find most recently updated branch (check up to 10 branches to limit API calls)
            if branches:
                most_recent = None
                most_recent_date = None
                for branch in branches[:10]:
                    if branch["name"] in branches_to_check:
                        continue  # Skip branches we're already checking
                    commit_url = branch.get("commit", {}).get("url")
                    if commit_url:
                        resp = requests.get(commit_url, headers=headers)
                        if resp.status_code == 200:
                            commit_date = resp.json().get("commit", {}).get("committer", {}).get("date")
                            if commit_date and (most_recent_date is None or commit_date > most_recent_date):
                                most_recent_date = commit_date
                                most_recent = branch["name"]
                if most_recent:
                    branches_to_check.add(most_recent)

        # Fetch commits from all branches, deduplicate by SHA
        seen_shas = set()
        all_commits = []
        for branch in branches_to_check:
            response = requests.get(commits_url, headers=headers, params={"sha": branch, "since": since, "per_page": 100})
            if response.status_code == 200:
                for commit in response.json():
                    if commit["sha"] not in seen_shas:
                        seen_shas.add(commit["sha"])
                        all_commits.append(commit)

        data["commits_this_week"] = len(all_commits)
        data["commit_authors"] = list(set(
            c["commit"]["author"]["name"] for c in all_commits if c.get("commit", {}).get("author")
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


def fetch_org_repos(org: str) -> list[str]:
    """Fetch all public repository names for an organization."""
    headers = get_headers()
    url = f"https://api.github.com/orgs/{org}/repos"
    repos = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page, "type": "public"})
        response.raise_for_status()
        page_repos = response.json()

        if not page_repos:
            break

        repos.extend([r["full_name"] for r in page_repos if not r["archived"]])
        page += 1

    return repos


def fetch_user_repos(user: str) -> list[str]:
    """Fetch all public repository names for a user."""
    headers = get_headers()
    url = f"https://api.github.com/users/{user}/repos"
    repos = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params={"per_page": 100, "page": page, "type": "public"})
        response.raise_for_status()
        page_repos = response.json()

        if not page_repos:
            break

        repos.extend([r["full_name"] for r in page_repos if not r["archived"]])
        page += 1

    return repos


def matches_pattern(repo_name: str, pattern: str) -> bool:
    """Check if repo name matches a glob pattern."""
    return fnmatch.fnmatch(repo_name, pattern)


def main():
    """Main entry point."""
    config = load_config()
    blacklist = config.get("blacklist", [])
    whitelist = set(config.get("whitelist", []))

    # Gather all public repos from orgs and users
    all_repos = set()

    for org in config.get("organizations", []):
        print(f"Fetching repos from org: {org}")
        org_repos = fetch_org_repos(org)
        all_repos.update(org_repos)

    for user in config.get("users", []):
        print(f"Fetching repos from user: {user}")
        user_repos = fetch_user_repos(user)
        all_repos.update(user_repos)

    # Add whitelisted private repos
    all_repos.update(whitelist)

    # Remove blacklisted repos (supports patterns)
    all_repos = {
        repo for repo in all_repos
        if not any(matches_pattern(repo, pattern) for pattern in blacklist)
    }
    
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
