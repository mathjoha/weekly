#!/usr/bin/env python3
"""Update the index of available data files."""

import json
from pathlib import Path


def main():
    """Scan data directory and update index.json."""
    data_dir = Path(__file__).parent.parent / "docs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all date JSON files
    dates = sorted([
        f.stem for f in data_dir.glob("*.json")
        if f.stem != "index" and f.stem[0].isdigit()
    ], reverse=True)
    
    index = {
        "dates": dates,
        "latest": dates[0] if dates else None,
        "count": len(dates),
    }
    
    with open(data_dir / "index.json", "w") as f:
        json.dump(index, f, indent=2)
    
    print(f"Updated index with {len(dates)} dates")


if __name__ == "__main__":
    main()
