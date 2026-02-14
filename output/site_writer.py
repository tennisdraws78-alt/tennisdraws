"""Generate the docs/data.js file for the interactive tennis website."""
from __future__ import annotations

import os
import json
import re
from datetime import datetime
from collections import defaultdict

from output.html_writer import (
    _normalize_tournament_name,
    _normalize_week,
    _merge_close_weeks,
    _extract_start_date,
    _week_sort_key,
)


def write_site_data(
    players: list[dict],
    player_entry_map: dict[str, list[dict]],
    raw_entries: list[dict] = None,
    output_dir: str = None,
) -> str:
    """Generate docs/data.js with all player and tournament data.

    Args:
        players: List of ranked players from rankings API.
        player_entry_map: Dict mapping "name|gender" -> list of entry dicts.
        raw_entries: Optional list of raw entry dicts for full entry lists
                     (Challenger + WTA 125 tiers — includes unranked players).
        output_dir: Output directory (default: docs/ in project root).

    Returns:
        Path to the generated data.js file.
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs"
        )
    os.makedirs(output_dir, exist_ok=True)

    # --- Pass 1: collect all weeks and build merge map ---
    all_raw_weeks = set()
    for player in players:
        player_key = f"{player['name']}|{player.get('gender', '')}"
        for entry in player_entry_map.get(player_key, []):
            week_val = entry.get("week", "")
            week_val = re.sub(r"\s*\u2754\s*$", "", week_val)
            week_val = re.sub(r"\s*\?\s*$", "", week_val).strip()
            week_val = _normalize_week(week_val)
            if week_val:
                all_raw_weeks.add(week_val)

    week_merge_map = _merge_close_weeks(all_raw_weeks)

    # --- Pass 2: build player data with deduped entries ---
    players_data = []
    all_weeks = set()
    tournament_players = defaultdict(list)  # tournament_key -> list of player entries

    for player in sorted(players, key=lambda p: (p.get("gender", ""), p.get("rank", 9999))):
        player_key = f"{player['name']}|{player.get('gender', '')}"
        entries = player_entry_map.get(player_key, [])
        gender_label = "Men" if player.get("gender") == "M" else "Women"

        seen = set()
        deduped = []
        for entry in entries:
            week_val = entry.get("week", "")
            week_val = re.sub(r"\s*\u2754\s*$", "", week_val)
            week_val = re.sub(r"\s*\?\s*$", "", week_val).strip()
            week_val = _normalize_week(week_val)
            week_val = week_merge_map.get(week_val, week_val)

            tourn_name = _normalize_tournament_name(entry.get("tournament", ""))
            section = entry.get("section", "")

            dedup_key = (tourn_name, section, week_val)
            if dedup_key in seen:
                # If duplicate, prefer OfficialDraw source (has reason)
                if entry.get("source") == "OfficialDraw" and entry.get("reason"):
                    # Replace existing entry with OfficialDraw version
                    for idx_d, existing in enumerate(deduped):
                        if (existing["tournament"] == tourn_name
                                and existing["section"] == section
                                and existing["week"] == week_val):
                            deduped[idx_d]["source"] = "OfficialDraw"
                            deduped[idx_d]["reason"] = entry.get("reason", "")
                            deduped[idx_d]["withdrawn"] = True
                            break
                continue
            seen.add(dedup_key)

            if week_val:
                all_weeks.add(week_val)

            entry_data = {
                "tournament": tourn_name,
                "tier": entry.get("tier", ""),
                "section": section,
                "week": week_val,
                "source": entry.get("source", ""),
                "withdrawn": bool(entry.get("withdrawn")),
            }
            reason = entry.get("reason", "")
            if reason:
                entry_data["reason"] = reason
            deduped.append(entry_data)

            # Build tournament index
            t_key = tourn_name.lower()
            tp_entry = {
                "player": player["name"],
                "rank": player.get("rank", 9999),
                "country": player.get("country_code", ""),
                "gender": gender_label,
                "section": section,
                "source": entry.get("source", ""),
                "withdrawn": bool(entry.get("withdrawn")),
            }
            if reason:
                tp_entry["reason"] = reason
            tournament_players[t_key].append(tp_entry)

        deduped.sort(key=lambda e: _week_sort_key(e["week"]))

        players_data.append({
            "rank": player.get("rank", 9999),
            "name": player["name"],
            "gender": gender_label,
            "country": player.get("country_code", ""),
            "entries": deduped,
        })

    # Sort weeks chronologically
    sorted_weeks = sorted(all_weeks, key=_week_sort_key)

    # --- Build tournament index ---
    tournaments_data = []
    seen_tournaments = {}
    for player in players_data:
        for entry in player["entries"]:
            t_key = entry["tournament"].lower()
            if t_key not in seen_tournaments:
                seen_tournaments[t_key] = {
                    "name": entry["tournament"],
                    "tier": entry["tier"],
                    "week": entry["week"],
                    "playerCount": 0,
                    "sections": set(),
                }
            seen_tournaments[t_key]["sections"].add(entry["section"])
            seen_tournaments[t_key]["playerCount"] += 1

    for t_key in sorted(seen_tournaments, key=lambda k: _week_sort_key(seen_tournaments[k]["week"])):
        t = seen_tournaments[t_key]
        tournaments_data.append({
            "name": t["name"],
            "tier": t["tier"],
            "week": t["week"],
            "playerCount": t["playerCount"],
            "sections": sorted(t["sections"]),
        })

    # --- Build full entry lists for Challenger/125 tiers ---
    full_entries_data = {}
    if raw_entries:
        # Group raw entries by normalized tournament name
        raw_by_tournament = defaultdict(list)
        raw_tournament_meta = {}  # key -> {name, tier, week, source, gender}

        for entry in raw_entries:
            tourn_name = _normalize_tournament_name(entry.get("tournament", ""))
            week_val = entry.get("week", "")
            week_val = re.sub(r"\s*\u2754\s*$", "", week_val)
            week_val = re.sub(r"\s*\?\s*$", "", week_val).strip()
            week_val = _normalize_week(week_val)
            week_val = week_merge_map.get(week_val, week_val)

            t_key = tourn_name.lower()

            if t_key not in raw_tournament_meta:
                raw_tournament_meta[t_key] = {
                    "name": tourn_name,
                    "tier": entry.get("tier", ""),
                    "week": week_val,
                    "source": entry.get("source", ""),
                    "gender": "Women" if entry.get("gender") == "F" else "Men",
                }

            # Dedup players by name within a tournament
            player_name = entry.get("player_name", "")
            section = entry.get("section", "Main Draw")
            country = entry.get("player_country", "") or entry.get("country_code", "")
            raw_by_tournament[t_key].append({
                "n": player_name,
                "r": entry.get("player_rank", 0),
                "c": country,
                "s": section,
                "w": bool(entry.get("withdrawn")),
            })

        # Deduplicate players within each tournament and build output
        for t_key, players_list in raw_by_tournament.items():
            seen_names = {}  # (name_lower, section) -> player dict
            for p in players_list:
                pkey = (p["n"].lower(), p["s"])
                if pkey not in seen_names:
                    seen_names[pkey] = p
                else:
                    # Prefer entry with rank data and country data
                    existing = seen_names[pkey]
                    if (not existing["r"] and p["r"]) or (not existing["c"] and p["c"]):
                        # Merge: take best of both
                        if p["r"] and not existing["r"]:
                            existing["r"] = p["r"]
                        if p["c"] and not existing["c"]:
                            existing["c"] = p["c"]
            deduped_players = list(seen_names.values())

            # Sort by rank (0 = unranked at end)
            deduped_players.sort(
                key=lambda p: (p["r"] if p["r"] > 0 else 9999)
            )

            meta = raw_tournament_meta[t_key]
            full_entries_data[t_key] = {
                "name": meta["name"],
                "tier": meta["tier"],
                "week": meta["week"],
                "source": meta["source"],
                "gender": meta["gender"],
                "players": deduped_players,
            }

            # Also add/update in tournaments_data if not already present
            if t_key not in seen_tournaments:
                seen_tournaments[t_key] = True
                tournaments_data.append({
                    "name": meta["name"],
                    "tier": meta["tier"],
                    "week": meta["week"],
                    "playerCount": len(deduped_players),
                    "sections": sorted(set(p["s"] for p in deduped_players)),
                    "hasFullList": True,
                })
            else:
                # Update player count to reflect full list
                for td in tournaments_data:
                    if td["name"].lower() == t_key:
                        td["playerCount"] = len(deduped_players)
                        td["hasFullList"] = True
                        break

        # Re-sort tournaments by week
        tournaments_data.sort(key=lambda t: _week_sort_key(t.get("week", "")))

        print(f"  Full entry lists: {len(full_entries_data)} tournaments, "
              f"{sum(len(fe['players']) for fe in full_entries_data.values())} total players")

    # --- Compute stats ---
    total_players = len(players_data)
    players_with_entries = sum(1 for p in players_data if p["entries"])
    total_entries = sum(len(p["entries"]) for p in players_data)
    unique_tournaments = len(seen_tournaments)

    stats = {
        "totalPlayers": total_players,
        "playersWithEntries": players_with_entries,
        "totalEntries": total_entries,
        "uniqueTournaments": unique_tournaments,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # --- Write data.js ---
    data = {
        "players": players_data,
        "weeks": sorted_weeks,
        "tournaments": tournaments_data,
        "fullEntries": full_entries_data,
        "stats": stats,
    }

    filepath = os.path.join(output_dir, "data.js")
    json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("window.TENNIS_DATA=")
        f.write(json_str)
        f.write(";")

    print(f"\nSite data written to: {filepath}")
    print(f"  Total players: {total_players}")
    print(f"  Players with entries: {players_with_entries}/{total_players}")
    print(f"  Total entries: {total_entries}")
    print(f"  Unique tournaments: {unique_tournaments}")
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  File size: {size_kb:.0f} KB")

    return filepath
