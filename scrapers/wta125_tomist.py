"""Scraper for tomistgg WTA 125 entry lists.

Source: https://tomistgg.github.io/tenis-fem-arg/
Static HTML page with inline tournamentData JS object containing WTA 125 entry lists.
"""
from __future__ import annotations

import re
import json
import time
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Map type field to section display names
SECTION_MAP = {
    "MAIN": "Main Draw",
    "QUAL": "Qualifying",
}


def _fetch_page() -> str:
    """Fetch the full HTML page with retries."""
    url = config.WTA125_TOMIST_URL
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)  # larger timeout for 13MB page
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] WTA125 Tomist fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return ""


def _extract_tournament_data(html: str) -> dict:
    """Extract the tournamentData JS object using brace-depth matching.

    Returns dict: {url_key: [{name, country, rank_num, rank, type, pos}, ...], ...}
    """
    marker = "const tournamentData = "
    idx = html.find(marker)
    if idx == -1:
        print("  Warning: tournamentData not found in page")
        return {}

    start = idx + len(marker)

    # Brace-depth matching to find the complete JSON object
    depth = 0
    end = start
    for i in range(start, len(html)):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    json_str = html[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  Warning: Could not parse tournamentData: {e}")
        return {}


def _parse_tournament_metadata(html: str) -> dict:
    """Parse the <select id="tSelect"> dropdown to extract tournament names and weeks.

    Returns dict: {url_key: {"name": "WTA 125 Oeiras 2", "week": "Feb 16"}, ...}
    """
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", id="tSelect")
    if not select:
        print("  Warning: tSelect dropdown not found")
        return {}

    metadata = {}
    current_week = ""

    for child in select.children:
        if not hasattr(child, 'name') or child.name is None:
            continue

        if child.name == "option":
            text = child.get_text(strip=True)
            value = child.get("value", "")

            # Week header options are disabled
            if child.get("disabled") is not None:
                # "WEEK OF FEBRUARY 16" -> "Feb 16"
                week_match = re.search(r"WEEK OF (\w+)\s+(\d+)", text)
                if week_match:
                    month_name = week_match.group(1).capitalize()
                    day = week_match.group(2)
                    # Abbreviate month
                    month_abbrev = month_name[:3]
                    current_week = f"{month_abbrev} {day}"
                continue

            # Tournament option
            if value and text:
                metadata[value] = {
                    "name": text,
                    "week": current_week,
                }

    return metadata


def _convert_week_header(header_text: str) -> str:
    """Convert 'WEEK OF FEBRUARY 16' to 'Feb 16' format."""
    match = re.search(r"WEEK OF (\w+)\s+(\d+)", header_text)
    if match:
        month = match.group(1).capitalize()[:3]
        day = match.group(2)
        return f"{month} {day}"
    return header_text


def scrape_all() -> list[dict]:
    """Scrape WTA 125 entry lists from tomistgg.

    Returns list of entry dicts in the standard format.
    """
    print("Scraping WTA 125 entries from TomistGG...")

    html = _fetch_page()
    if not html:
        print("  ERROR: Could not fetch TomistGG page")
        return []

    # Extract raw tournament data
    tournament_data = _extract_tournament_data(html)
    if not tournament_data:
        print("  ERROR: No tournament data found")
        return []

    # Extract tournament names and weeks from dropdown
    metadata = _parse_tournament_metadata(html)

    # Filter to WTA 125 tournaments only (URLs containing "125")
    wta125_keys = [k for k in tournament_data if "125" in k]

    entries = []
    for url_key in wta125_keys:
        players = tournament_data[url_key]
        meta = metadata.get(url_key, {})
        tournament_name = meta.get("name", url_key)
        week = meta.get("week", "")

        # Strip "WTA 125 " prefix from tournament name for normalization
        # e.g. "WTA 125 Oeiras 2" -> "Oeiras 2"
        clean_name = re.sub(r"^WTA\s+125\s+", "", tournament_name, flags=re.IGNORECASE).strip()
        if not clean_name:
            clean_name = tournament_name

        for player in players:
            section = SECTION_MAP.get(player.get("type", ""), "Main Draw")
            rank = player.get("rank_num", 0)
            if isinstance(rank, str):
                try:
                    rank = int(rank)
                except ValueError:
                    rank = 0

            entries.append({
                "tournament": clean_name,
                "tier": "WTA 125",
                "week": week,
                "section": section,
                "player_name": player.get("name", ""),
                "player_rank": rank,
                "player_country": player.get("country", ""),
                "gender": "F",
                "withdrawn": False,
                "source": "TomistGG",
            })

    print(f"  Found {len(entries)} WTA 125 entries across {len(wta125_keys)} tournaments")
    return entries
