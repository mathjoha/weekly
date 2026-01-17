# GitHub Progress Tracker

Automated weekly progress tracking across your GitHub repositories. Runs entirely on GitHub Actions, publishes to GitHub Pages.

## Features

- **Weekly automated collection** of commits, PRs, issues, contributors
- **Static site** with historical data access (`/team/2026-01-19`)
- **Team templates** for filtered views per project leader
- **Diff view** to compare any two weeks
- **Zero infrastructure** — just GitHub

## Quick Start

1. **Fork this repository**

2. **Create a Personal Access Token**
   - Go to GitHub Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens
   - Create a token with read access to your repos/orgs
   - Add it as a repository secret named `GH_PAT`

3. **Configure your repos**
   
   Edit `config.yaml`:
   ```yaml
   repositories:
     - your-username/repo-one
     - your-username/repo-two
   
   organizations:
     - your-org-name
   
   exclude:
     - your-org-name/repo-to-skip
   ```

4. **Enable GitHub Pages**
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`, folder: `/docs`

5. **Run the workflow**
   - Go to Actions → Weekly Progress Report → Run workflow
   - Or wait for Monday 9am UTC

## Team Templates

Create filtered views for different teams by adding files to `docs/templates/`:

```json
{
  "id": "team-alpha",
  "name": "Team Alpha",
  "description": "Frontend projects",
  "repos": [
    "your-org/frontend-app",
    "your-org/ui-components"
  ],
  "metrics": {
    "highlight": ["commits", "prs_merged"],
    "hide": ["stars", "forks"]
  }
}
```

Then update `docs/templates/index.json` to include the new template.

Access at: `https://your-username.github.io/repo/#/team-alpha`

## URL Structure

| URL | View |
|-----|------|
| `/#/` | All repos, latest week |
| `/#/2026-01-19` | All repos, specific week |
| `/#/team-alpha` | Team Alpha, latest week |
| `/#/team-alpha/2026-01-19` | Team Alpha, specific week |
| `/#/team-alpha/2026-01-19/diff/2026-01-12` | Team Alpha, diff between weeks |

## Local Development

```bash
# Install dependencies
pip install requests pyyaml

# Set your token
export GITHUB_TOKEN=ghp_xxxx

# Run manually
python scripts/fetch.py
python scripts/aggregate.py
python scripts/update_index.py

# Serve the site
cd docs && python -m http.server 8000
```

## Customization

- **Schedule**: Edit `.github/workflows/weekly-report.yml` cron expression
- **Metrics**: Edit `config.yaml` to change what's collected
- **Styling**: Edit `docs/index.html` CSS variables

## License

MIT
