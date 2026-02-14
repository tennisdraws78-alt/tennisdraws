#!/usr/bin/env python3
"""Tennis Player Entry List Tracker — CLI entry point.

Fetches rankings and scrapes entry lists from multiple sources to show
which tournaments each ranked player has signed up for.

Usage:
    python main.py                          # Full run, both genders, up to rank 500
    python main.py --gender men             # Men only
    python main.py --gender women           # Women only
    python main.py --max-rank 100           # Top 100 only
    python main.py --skip-itf              # Skip ITF entries (faster, no Playwright needed)
    python main.py --skip-spazio           # Skip Spazio Tennis
    python main.py --output results.csv     # Custom output filename
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings

# Suppress SSL warnings from urllib3 on older macOS
warnings.filterwarnings("ignore", category=Warning)

sys.path.insert(0, ".")

from rankings.api_client import fetch_atp_rankings, fetch_wta_rankings
from scrapers.ticktock import scrape_all as scrape_ticktock
from scrapers.spaziotennis import scrape_all as scrape_spazio
from scrapers.wta_official import scrape_all as scrape_wta
from scrapers.itf_entries import scrape_all as scrape_itf
from scrapers.wta125_tomist import scrape_all as scrape_wta125
from matching.name_matcher import build_player_entry_map
from output.csv_writer import write_csv
from output.site_writer import write_site_data


def main():
    parser = argparse.ArgumentParser(
        description="Tennis Player Entry List Tracker"
    )
    parser.add_argument(
        "--gender",
        choices=["men", "women", "both"],
        default="both",
        help="Which gender to track (default: both)",
    )
    parser.add_argument(
        "--max-rank",
        type=int,
        default=1500,
        help="Maximum ranking to include (default: 1500)",
    )
    parser.add_argument(
        "--skip-wta",
        action="store_true",
        help="Skip WTA Official website scraping",
    )
    parser.add_argument(
        "--skip-itf",
        action="store_true",
        help="Skip ITF entries scraping (faster, no Playwright needed)",
    )
    parser.add_argument(
        "--skip-spazio",
        action="store_true",
        help="Skip Spazio Tennis scraping",
    )
    parser.add_argument(
        "--skip-wta125",
        action="store_true",
        help="Skip WTA 125 TomistGG scraping",
    )
    parser.add_argument(
        "--limit-itf",
        type=int,
        default=0,
        help="Limit ITF scraping to first N tournaments (0 = all, default: 0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV filename (default: auto-generated with timestamp)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Tennis Player Entry List Tracker")
    print("=" * 60)
    print()

    # Step 1: Fetch rankings
    print("--- STEP 1: Fetching Rankings ---")
    players = []
    if args.gender in ("men", "both"):
        players.extend(fetch_atp_rankings(args.max_rank))
        time.sleep(1)
    if args.gender in ("women", "both"):
        players.extend(fetch_wta_rankings(args.max_rank))

    if not players:
        print("ERROR: No players fetched. Check API key and connectivity.")
        sys.exit(1)

    print(f"\nTotal ranked players: {len(players)}")
    print()

    # Step 2: Scrape entry lists from all sources
    print("--- STEP 2: Scraping Entry Lists ---")
    all_entries = []

    # Source 1: Tick Tock Tennis (always included — fast, reliable)
    ticktock_entries = scrape_ticktock()
    all_entries.extend(ticktock_entries)
    print()

    # Source 2: Spazio Tennis
    if not args.skip_spazio:
        time.sleep(1)
        spazio_entries = scrape_spazio()
        all_entries.extend(spazio_entries)
        print()
    else:
        print("Skipping Spazio Tennis (--skip-spazio)")
        print()

    # Source 3: WTA Official (requests + BeautifulSoup)
    if not args.skip_wta:
        time.sleep(1)
        wta_entries = scrape_wta()
        all_entries.extend(wta_entries)
        print()
    else:
        print("Skipping WTA Official (--skip-wta)")
        print()

    # Source 4: WTA 125 from TomistGG
    if not args.skip_wta125:
        time.sleep(1)
        wta125_entries = scrape_wta125()
        all_entries.extend(wta125_entries)
        print()
    else:
        print("Skipping WTA 125 TomistGG (--skip-wta125)")
        print()

    # Source 5: ITF Entries (requires Playwright)
    if not args.skip_itf:
        time.sleep(1)
        itf_entries = scrape_itf(limit=args.limit_itf)
        all_entries.extend(itf_entries)
        print()
    else:
        print("Skipping ITF Entries (--skip-itf)")
        print()

    # Filter entries by gender
    if args.gender == "men":
        all_entries = [e for e in all_entries if e.get("gender") == "M"]
    elif args.gender == "women":
        all_entries = [e for e in all_entries if e.get("gender") == "F"]

    print(f"Total entry list records: {len(all_entries)}")
    print()

    # Step 3: Match players to entries
    print("--- STEP 3: Matching Players to Entries ---")
    player_entry_map = build_player_entry_map(players, all_entries)
    print()

    # Collect raw entries for tiers that need full entry lists
    raw_full = [
        e for e in all_entries
        if "Challenger" in e.get("tier", "") or "125" in e.get("tier", "")
    ]
    print(f"Full entry list records (Challenger + WTA 125): {len(raw_full)}")
    print()

    # Step 4: Generate output
    print("--- STEP 4: Generating Output ---")
    csv_path = write_csv(players, player_entry_map, args.output)
    site_path = write_site_data(players, player_entry_map, raw_full)

    print()
    print("=" * 60)
    print(f"  Done! Results saved to:")
    print(f"    CSV:  {csv_path}")
    print(f"    Site: {site_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
