"""Scraper for entries.ticktocktennis.com — ATP and WTA entry lists."""
from __future__ import annotations

import re
import json
import time
import requests
import config

# Map tier keys to display names
TIER_MAP = {
    "atp1000": "ATP 1000",
    "atp500": "ATP 500",
    "atp250": "ATP 250",
    "atp125": "ATP Challenger",
    "wta1000": "WTA 1000",
    "wta500": "WTA 500",
    "wta250": "WTA 250",
    "wta125": "WTA 125",
    "itf": "ITF",
}

# Map section keys to display names
SECTION_MAP = {
    "main": "Main Draw",
    "qual": "Qualifying",
    "alt": "Alternates",
    "wc": "Wild Card",
    "qualWc": "Qualifying WC",
    "qualAlt": "Qualifying Alt",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def _fetch_page(url: str) -> str:
    """Fetch HTML content with retries."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] TickTock fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return ""


def _extract_week_dates(html: str) -> dict:
    """Extract week-to-date mapping from the tab buttons in the HTML.

    Tabs look like: <... class="week-tab ..." onclick="showWeek('week1', this)">Feb 16<...
    Returns e.g. {"week1": "Feb 16", "week2": "Feb 23", "week3": "Mar 2"}
    """
    dates = {}
    for m in re.finditer(
        r"""showWeek\(['"](\w+)['"]""" + r"""[^>]*>([^<]+)<""",
        html,
    ):
        week_key = m.group(1)
        date_text = m.group(2).strip()
        if date_text:
            dates[week_key] = date_text
    return dates


def _extract_js_data(html: str, var_name: str) -> dict:
    """Extract the JavaScript data object (atpData or wtaData) from HTML.

    The data is structured as:
        const atpData = { week1: {}, week2: {}, week3: {}, week4: {} };
        atpData.week1 = { "atp500": [ { name: "Doha", main: [[1,"Name","CC"]], qual: [...] }, ... ] };

    We extract each week assignment and parse the JS object literal into Python.
    """
    result = {}

    # Find each week assignment: atpData.week1 = { ... };
    week_pattern = rf'{var_name}\.(week\d+)\s*=\s*'
    splits = list(re.finditer(week_pattern, html))

    for match in splits:
        week_key = match.group(1)
        start = match.end()

        # Use brace-depth matching to find the complete object
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

        chunk = html[start:end]

        # Convert JS object literal to valid JSON
        js_obj = _js_to_json(chunk)

        try:
            result[week_key] = json.loads(js_obj)
        except json.JSONDecodeError as e:
            print(f"  Warning: Could not parse {var_name}.{week_key}: {e}")
            result[week_key] = {}

    return result


def _js_to_json(js_str: str) -> str:
    """Convert JavaScript object literal to valid JSON.

    Handles:
    - Unquoted keys: name: -> "name":
    - Single-quoted strings (though not seen in this data)
    - Trailing commas
    """
    # Quote unquoted property keys
    # Match word characters at start of a key position (after { or ,)
    result = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r' "\1":', js_str)

    # Remove trailing commas before } or ]
    result = re.sub(r',\s*([}\]])', r'\1', result)

    return result


def _parse_tournaments(data: dict, gender: str, week_dates: dict = None, source_url: str = "") -> list[dict]:
    """Parse the extracted data into a flat list of tournament entries.

    Returns list of dicts with keys:
        tournament, tier, week, section, player_name, player_rank, player_country, withdrawn, gender, source
    """
    entries = []

    for week_key, tiers in data.items():
        if not isinstance(tiers, dict):
            continue
        # Use actual date if available (e.g. "Feb 16"), fallback to "Week 1"
        if week_dates and week_key in week_dates:
            week_label = week_dates[week_key]
        else:
            num = re.sub(r"\D", "", week_key)
            week_label = f"Week {num}" if num else week_key

        for tier_key, tournaments in tiers.items():
            tier_name = TIER_MAP.get(tier_key, tier_key.upper())

            if not isinstance(tournaments, list):
                continue

            for tournament in tournaments:
                if not isinstance(tournament, dict):
                    continue
                t_name = tournament.get("name", "Unknown")

                # Process each section (main, qual, alt, wc, qualWc, qualAlt)
                for section_key, section_label in SECTION_MAP.items():
                    players = tournament.get(section_key, [])
                    if not isinstance(players, list):
                        continue

                    for player in players:
                        if not isinstance(player, list) or len(player) < 3:
                            continue

                        rank = player[0]
                        name = player[1]
                        country = player[2]
                        # 4th element is status flag like "W" for withdrawn
                        withdrawn = len(player) > 3 and player[3] == "W"

                        entries.append({
                            "tournament": t_name,
                            "tier": tier_name,
                            "week": week_label,
                            "section": section_label,
                            "player_name": name,
                            "player_rank": rank,
                            "player_country": country,
                            "withdrawn": withdrawn,
                            "gender": gender,
                            "source": "TickTockTennis",
                            "source_url": source_url,
                        })

    return entries


def scrape_atp() -> list[dict]:
    """Scrape ATP entry lists from Tick Tock Tennis."""
    print("Scraping Tick Tock Tennis (ATP)...")
    html = _fetch_page(config.TICKTOCK_ATP_URL)
    if not html:
        print("  Failed to fetch ATP page")
        return []

    week_dates = _extract_week_dates(html)
    data = _extract_js_data(html, "atpData")
    entries = _parse_tournaments(data, "M", week_dates, config.TICKTOCK_ATP_URL)

    active = [e for e in entries if not e["withdrawn"]]
    withdrawn = [e for e in entries if e["withdrawn"]]
    print(f"  Found {len(active)} active entries, {len(withdrawn)} withdrawals across {len(data)} weeks")
    return entries


def scrape_wta() -> list[dict]:
    """Scrape WTA entry lists from Tick Tock Tennis."""
    print("Scraping Tick Tock Tennis (WTA)...")
    html = _fetch_page(config.TICKTOCK_WTA_URL)
    if not html:
        print("  Failed to fetch WTA page")
        return []

    week_dates = _extract_week_dates(html)
    data = _extract_js_data(html, "wtaData")
    entries = _parse_tournaments(data, "F", week_dates, config.TICKTOCK_WTA_URL)

    active = [e for e in entries if not e["withdrawn"]]
    withdrawn = [e for e in entries if e["withdrawn"]]
    print(f"  Found {len(active)} active entries, {len(withdrawn)} withdrawals across {len(data)} weeks")
    return entries


def scrape_all() -> list[dict]:
    """Scrape both ATP and WTA entry lists."""
    atp = scrape_atp()
    time.sleep(config.REQUEST_DELAY)
    wta = scrape_wta()
    return atp + wta
