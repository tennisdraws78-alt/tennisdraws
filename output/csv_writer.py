"""Generate CSV output from player-tournament match data."""
from __future__ import annotations

import os
import csv
from datetime import datetime
import config


def write_csv(
    players: list[dict],
    player_entry_map: dict[str, list[dict]],
    filename: str = None,
) -> str:
    """Write the player-tournament mapping to a CSV file.

    Args:
        players: List of ranked players
        player_entry_map: Dict mapping "name|gender" -> list of entry dicts
        filename: Output filename (default: auto-generated with timestamp)

    Returns:
        Path to the generated CSV file.
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"entry_lists_{timestamp}.csv"

    filepath = os.path.join(config.OUTPUT_DIR, filename)

    fieldnames = [
        "Rank",
        "Player",
        "Gender",
        "Country",
        "Tournament",
        "Tier",
        "Section",
        "Week",
        "Source",
        "Withdrawn",
    ]

    rows = []

    for player in sorted(players, key=lambda p: (p.get("gender", ""), p.get("rank", 9999))):
        player_key = f"{player['name']}|{player.get('gender', '')}"
        entries = player_entry_map.get(player_key, [])

        gender_label = "Men" if player.get("gender") == "M" else "Women"

        if entries:
            # Deduplicate entries by (tournament, section)
            seen = set()
            for entry in entries:
                dedup_key = (entry["tournament"], entry["section"], entry["source"])
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                rows.append({
                    "Rank": player.get("rank", ""),
                    "Player": player["name"],
                    "Gender": gender_label,
                    "Country": player.get("country_code", entry.get("player_country", "")),
                    "Tournament": entry.get("tournament", ""),
                    "Tier": entry.get("tier", ""),
                    "Section": entry.get("section", ""),
                    "Week": entry.get("week", ""),
                    "Source": entry.get("source", ""),
                    "Withdrawn": "Yes" if entry.get("withdrawn") else "",
                })
        else:
            rows.append({
                "Rank": player.get("rank", ""),
                "Player": player["name"],
                "Gender": gender_label,
                "Country": player.get("country_code", ""),
                "Tournament": "No entries found",
                "Tier": "",
                "Section": "",
                "Week": "",
                "Source": "",
                "Withdrawn": "",
            })

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCSV written to: {filepath}")
    print(f"  Total rows: {len(rows)}")
    players_with_entries = sum(
        1 for p in players
        if player_entry_map.get(f"{p['name']}|{p.get('gender', '')}")
    )
    print(f"  Players with entries: {players_with_entries}/{len(players)}")

    return filepath
