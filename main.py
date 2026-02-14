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
from scrapers.draw_pdfs import scrape_all as scrape_draws
from matching.name_matcher import build_player_entry_map
from output.csv_writer import write_csv
from output.site_writer import write_site_data


def _attach_draw_reasons(all_entries: list[dict]) -> None:
    """Attach withdrawal reasons from OfficialDraw entries to existing withdrawals,
    and expand abbreviated OfficialDraw names to full names for matching.

    OfficialDraw PDFs use abbreviated names ("A. Vukic") while Spazio/TickTock
    have full names ("Aleksandar Vukic").

    Strategy:
    1. Build a lookup from abbreviated names to reasons (from OfficialDraw)
    2. For each non-OfficialDraw withdrawal, attach reason if found
    3. For remaining OfficialDraw entries, try to expand the abbreviated name
       to a full name by looking up initial+surname in ALL entries (including
       non-withdrawn ones — the player may appear in other tournaments)
    4. Keep expanded-name OfficialDraw entries; remove unexpandable ones
    """
    import re

    # Separate OfficialDraw entries from others
    draw_entries = [e for e in all_entries if e.get("source") == "OfficialDraw"]
    if not draw_entries:
        return

    # Build lookup: (initial, surname_lower, gender) -> list of draw entries
    draw_by_key = {}
    for de in draw_entries:
        name = de.get("player_name", "")
        gender = de.get("gender", "")
        m = re.match(r"([A-Z][a-z]{0,3})\.\s+(.+)", name)
        if not m:
            continue
        initial = m.group(1)[0].upper()
        surname = m.group(2).strip().lower()
        key = (initial, surname, gender)
        draw_by_key.setdefault(key, []).append(de)

    # Build reverse lookup: (initial, surname, gender) -> full name
    # from all non-OfficialDraw entries
    full_name_lookup = {}
    for entry in all_entries:
        if entry.get("source") == "OfficialDraw":
            continue
        full_name = entry.get("player_name", "")
        gender = entry.get("gender", "")
        if not full_name:
            continue
        parts = full_name.strip().split()
        if len(parts) < 2:
            continue
        initial = parts[0][0].upper()
        surname = " ".join(parts[1:]).lower()
        surname_last = parts[-1].lower()
        key = (initial, surname, gender)
        key_last = (initial, surname_last, gender)
        if key not in full_name_lookup:
            full_name_lookup[key] = full_name
        if key_last not in full_name_lookup:
            full_name_lookup[key_last] = full_name

    # Step 1: Attach reasons to existing withdrawn entries from other sources
    matched_reasons = 0
    matched_keys = set()
    for entry in all_entries:
        if entry.get("source") == "OfficialDraw":
            continue
        if not entry.get("withdrawn"):
            continue

        full_name = entry.get("player_name", "")
        gender = entry.get("gender", "")
        parts = full_name.strip().split()
        if len(parts) < 2:
            continue

        initial = parts[0][0].upper()
        surname = " ".join(parts[1:]).lower()
        surname_last = parts[-1].lower()
        key = (initial, surname, gender)
        key_last = (initial, surname_last, gender)

        # Find matching draw entry with a reason
        for k in (key, key_last):
            if k in draw_by_key:
                for de in draw_by_key[k]:
                    reason = de.get("reason", "")
                    if reason and not entry.get("reason"):
                        entry["reason"] = reason
                        matched_reasons += 1
                        matched_keys.add(k)
                        break

    # Step 2: Expand abbreviated names for unmatched OfficialDraw entries
    expanded = 0
    for key, draw_list in draw_by_key.items():
        for de in draw_list:
            full = full_name_lookup.get(key)
            if not full:
                # Try with just last word of surname
                surname_parts = key[1].split()
                if len(surname_parts) > 1:
                    alt_key = (key[0], surname_parts[-1], key[2])
                    full = full_name_lookup.get(alt_key)
            if full:
                de["player_name"] = full
                expanded += 1

    # Remove OfficialDraw entries that couldn't be expanded (can't match to players)
    unexpanded = [
        e for e in draw_entries
        if not re.match(r"[A-Z][a-z]{0,3}\.", e.get("player_name", ""))
        is None
    ]
    kept = [
        e for e in draw_entries
        if re.match(r"[A-Z][a-z]{0,3}\.", e.get("player_name", ""))
        is None
    ]
    removed = len(draw_entries) - len(kept)
    all_entries[:] = [e for e in all_entries if e.get("source") != "OfficialDraw"] + kept

    if matched_reasons:
        print(f"  Attached {matched_reasons} withdrawal reason(s) from official draw PDFs")
    if expanded:
        print(f"  Expanded {expanded} abbreviated names to full names")
    if kept:
        print(f"  Kept {len(kept)} OfficialDraw withdrawal entries (name expanded)")
    if removed:
        print(f"  Removed {removed} OfficialDraw entries (couldn't expand name)")


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
        "--skip-draws",
        action="store_true",
        help="Skip official draw PDF scraping (ATP + WTA)",
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

    # Source 5: Official Draw PDFs (ATP + WTA withdrawals with reasons)
    if not args.skip_draws:
        time.sleep(1)
        draw_entries = scrape_draws()
        all_entries.extend(draw_entries)
        print()
    else:
        print("Skipping Official Draw PDFs (--skip-draws)")
        print()

    # Source 6: ITF Entries (requires Playwright)
    if not args.skip_itf:
        time.sleep(1)
        itf_entries = scrape_itf(limit=args.limit_itf)
        all_entries.extend(itf_entries)
        print()
    else:
        print("Skipping ITF Entries (--skip-itf)")
        print()

    # Attach OfficialDraw withdrawal reasons to entries from other sources.
    # Draw PDFs use abbreviated names ("A. Vukic") that can't fuzzy-match to
    # full player names, but other scrapers have the full names.  We match
    # them by initial + surname and merge the "reason" field.
    _attach_draw_reasons(all_entries)

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
