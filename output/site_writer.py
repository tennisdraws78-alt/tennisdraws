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
import config


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
                # Prefer withdrawn status from any source
                if entry.get("withdrawn"):
                    for idx_d, existing in enumerate(deduped):
                        if (existing["tournament"] == tourn_name
                                and existing["section"] == section
                                and existing["week"] == week_val):
                            if not existing.get("withdrawn"):
                                deduped[idx_d]["withdrawn"] = True
                                deduped[idx_d]["source"] = entry.get("source", existing["source"])
                            break
                # Also allow OfficialDraw to attach reason and withdrawal_type
                if entry.get("source") == "OfficialDraw" and entry.get("reason"):
                    for idx_d, existing in enumerate(deduped):
                        if (existing["tournament"] == tourn_name
                                and existing["section"] == section
                                and existing["week"] == week_val):
                            deduped[idx_d]["source"] = "OfficialDraw"
                            deduped[idx_d]["reason"] = entry.get("reason", "")
                            deduped[idx_d]["withdrawn"] = True
                            if entry.get("withdrawal_type"):
                                deduped[idx_d]["withdrawal_type"] = entry["withdrawal_type"]
                            break
                continue
            seen.add(dedup_key)

            if week_val:
                all_weeks.add(week_val)

            raw_tier = entry.get("tier", "")
            # Enrich challenger tier with specific category (50/75/100/125/175)
            if raw_tier.lower() in ("atp challenger", "challenger"):
                _cc = getattr(config, "CHALLENGER_CATEGORIES", {})
                cat_lvl = _cc.get(tourn_name)
                if cat_lvl:
                    raw_tier = f"ATP Challenger {cat_lvl}"
            entry_data = {
                "tournament": tourn_name,
                "tier": raw_tier,
                "section": section,
                "week": week_val,
                "source": entry.get("source", ""),
                "withdrawn": bool(entry.get("withdrawn")),
            }
            reason = entry.get("reason", "")
            if reason:
                entry_data["reason"] = reason
            wd_type = entry.get("withdrawal_type", "")
            if wd_type:
                entry_data["withdrawal_type"] = wd_type
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
            if wd_type:
                tp_entry["withdrawal_type"] = wd_type
            tournament_players[t_key].append(tp_entry)

        # Remove false withdrawals: if a player is withdrawn from a lower
        # section (e.g. Qualifying) but active in a higher section (e.g. Main
        # Draw) for the same tournament+week, they were promoted — not withdrawn.
        SECTION_RANK = {"Alternates": 0, "Qualifying": 1, "Main Draw": 2}
        active_keys = set()
        for d in deduped:
            if not d.get("withdrawn"):
                active_keys.add((d["tournament"], d["week"], SECTION_RANK.get(d["section"], -1)))
        before_promo = len(deduped)
        deduped = [
            d for d in deduped
            if not (
                d.get("withdrawn")
                and any(
                    t == d["tournament"] and w == d["week"] and sr > SECTION_RANK.get(d["section"], -1)
                    for t, w, sr in active_keys
                )
            )
        ]
        if len(deduped) < before_promo:
            pass  # silently drop promoted entries

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
            if not entry.get("withdrawn"):
                seen_tournaments[t_key]["playerCount"] += 1

    # Keep calendars separate for tier-aware lookup
    _atp_cal = getattr(config, "ATP_CALENDAR", {})
    _wta_cal = getattr(config, "WTA_CALENDAR", {})
    _wta125_cal = getattr(config, "WTA125_CALENDAR", {})
    _chall_cats = getattr(config, "CHALLENGER_CATEGORIES", {})

    def _cal_lookup(name, tier=""):
        """Find calendar metadata, preferring the calendar matching the tier."""
        tier_l = tier.lower()
        if "wta 125" in tier_l:
            if name in _wta125_cal:
                return _wta125_cal[name]
        if "wta" in tier_l:
            if name in _wta_cal:
                return _wta_cal[name]
        if name in _atp_cal:
            return _atp_cal[name]
        # Fallback: try all calendars
        return _wta_cal.get(name) or _wta125_cal.get(name)

    def _cal_week(dates_str):
        """Parse '2 Jan - 11 Jan' → 'Jan 2' canonical week format."""
        if not dates_str:
            return ""
        dm = re.match(r"(\d{1,2})\s+(\w{3})", dates_str)
        return f"{dm.group(2)} {dm.group(1)}" if dm else ""

    for t_key in sorted(seen_tournaments, key=lambda k: _week_sort_key(seen_tournaments[k]["week"])):
        t = seen_tournaments[t_key]
        td = {
            "name": t["name"],
            "tier": t["tier"],
            "week": t["week"],
            "playerCount": t["playerCount"],
            "sections": sorted(t["sections"]),
        }
        # Enrich with calendar metadata (surface, dates, city, country, tier, week)
        meta = _cal_lookup(t["name"], t["tier"])
        if meta:
            td["city"] = meta[0]
            td["country"] = meta[1]
            td["surface"] = meta[2]
            td["dates"] = meta[3]
            if len(meta) > 4:
                td["tier"] = meta[4]
            # Override week with official calendar week
            cal_wk = _cal_week(meta[3])
            if cal_wk:
                td["week"] = cal_wk
        # Enrich challenger tier with specific category (50/75/100/125/175)
        if td["tier"].lower() in ("atp challenger", "challenger"):
            cat_level = _chall_cats.get(t["name"])
            if cat_level:
                td["tier"] = f"ATP Challenger {cat_level}"
        tournaments_data.append(td)

    # --- Inject all calendar tournaments that have no scraped entries yet ---
    all_cal = {}
    all_cal.update(_wta125_cal)
    all_cal.update(_wta_cal)
    all_cal.update(_atp_cal)
    seen_names = {t["name"].lower() for t in tournaments_data}
    for cal_name, meta in all_cal.items():
        if cal_name.lower() not in seen_names:
            td = {
                "name": cal_name,
                "tier": meta[4] if len(meta) > 4 else "",
                "week": _cal_week(meta[3]),
                "playerCount": 0,
                "sections": [],
                "city": meta[0],
                "country": meta[1],
                "surface": meta[2],
                "dates": meta[3],
            }
            tournaments_data.append(td)

    # Re-sort after injecting calendar-only tournaments
    tournaments_data.sort(key=lambda t: _week_sort_key(t.get("week", "")))

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
            # Enrich challenger tier with specific category
            entry_tier = meta["tier"]
            if entry_tier.lower() in ("atp challenger", "challenger"):
                cat_level = _chall_cats.get(meta["name"])
                if cat_level:
                    entry_tier = f"ATP Challenger {cat_level}"
            full_entries_data[t_key] = {
                "name": meta["name"],
                "tier": entry_tier,
                "week": meta["week"],
                "source": meta["source"],
                "gender": meta["gender"],
                "players": deduped_players,
            }

            # Also add/update in tournaments_data if not already present
            if t_key not in seen_tournaments:
                seen_tournaments[t_key] = True
                new_td = {
                    "name": meta["name"],
                    "tier": entry_tier,
                    "week": meta["week"],
                    "playerCount": len(deduped_players),
                    "sections": sorted(set(p["s"] for p in deduped_players)),
                    "hasFullList": True,
                }
                cal_meta = _cal_lookup(meta["name"], meta.get("tier", ""))
                if cal_meta:
                    new_td["city"] = cal_meta[0]
                    new_td["country"] = cal_meta[1]
                    new_td["surface"] = cal_meta[2]
                    new_td["dates"] = cal_meta[3]
                    if len(cal_meta) > 4:
                        new_td["tier"] = cal_meta[4]
                tournaments_data.append(new_td)
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
    unique_tournaments = len(tournaments_data)

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
