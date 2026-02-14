"""Fetch ATP and WTA rankings.

Primary source: Tennis Abstract (tennisabstract.com) — has 2000+ players, no API key needed.
Fallback: RapidAPI Tennis Live Data — capped at 500 players per call.
"""
from __future__ import annotations

import time
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Tennis Abstract URLs
TA_ATP_URL = "https://tennisabstract.com/reports/atpRankings.html"
TA_WTA_URL = "https://tennisabstract.com/reports/wtaRankings.html"


def _fetch_from_tennis_abstract(url: str, gender: str, max_rank: int) -> list[dict]:
    """Scrape rankings from Tennis Abstract HTML table.

    Table columns: Rank | Player | Country | Birthdate
    Player names use non-breaking spaces (\xa0) between first and last name.
    """
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            break
        except requests.RequestException as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] Tennis Abstract fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    else:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", id="reportable") or soup.find("table")
    if not table:
        print("  Warning: No rankings table found on Tennis Abstract")
        return []

    players = []
    rows = table.find_all("tr")[1:]  # skip header

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        rank_text = cells[0].get_text(strip=True)
        if not rank_text.isdigit():
            continue
        rank = int(rank_text)

        if rank > max_rank:
            break

        # Name uses \xa0 (non-breaking space) — replace with regular space
        name = cells[1].get_text(strip=True).replace("\xa0", " ")
        country = cells[2].get_text(strip=True)

        players.append({
            "name": name,
            "rank": rank,
            "gender": gender,
            "country_code": country,
            "country_name": "",
            "points": 0,
        })

    return players


def _fetch_from_rapidapi(url: str, gender: str, max_rank: int) -> list[dict]:
    """Fallback: fetch rankings from RapidAPI (max 500)."""
    headers = {
        "x-rapidapi-key": config.RAPIDAPI_KEY,
        "x-rapidapi-host": config.RAPIDAPI_HOST,
    }
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("rankings", [])
            break
        except (requests.RequestException, ValueError) as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] RapidAPI fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    else:
        return []

    players = []
    for entry in raw:
        rank = entry.get("ranking", 9999)
        if rank > max_rank:
            continue
        team = entry.get("team", {})
        country = entry.get("country", {}) or team.get("country", {})
        players.append({
            "name": entry.get("rowName", team.get("name", "")),
            "rank": rank,
            "gender": gender,
            "country_code": country.get("alpha3", ""),
            "country_name": country.get("name", ""),
            "points": entry.get("points", 0),
        })

    return players


def fetch_atp_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch ATP rankings up to max_rank."""
    print(f"Fetching ATP rankings (up to {max_rank})...")

    # Try Tennis Abstract first (has 2000+ players)
    players = _fetch_from_tennis_abstract(TA_ATP_URL, "M", max_rank)
    if players:
        print(f"  Got {len(players)} ATP players from Tennis Abstract")
        return players

    # Fallback to RapidAPI (capped at 500)
    print("  Tennis Abstract failed, falling back to RapidAPI (max 500)...")
    players = _fetch_from_rapidapi(config.ATP_RANKINGS_URL, "M", max_rank)
    print(f"  Got {len(players)} ATP players from RapidAPI")
    return players


def fetch_wta_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch WTA rankings up to max_rank."""
    print(f"Fetching WTA rankings (up to {max_rank})...")

    players = _fetch_from_tennis_abstract(TA_WTA_URL, "F", max_rank)
    if players:
        print(f"  Got {len(players)} WTA players from Tennis Abstract")
        return players

    print("  Tennis Abstract failed, falling back to RapidAPI (max 500)...")
    players = _fetch_from_rapidapi(config.WTA_RANKINGS_URL, "F", max_rank)
    print(f"  Got {len(players)} WTA players from RapidAPI")
    return players


def fetch_all_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch both ATP and WTA rankings."""
    atp = fetch_atp_rankings(max_rank)
    time.sleep(config.REQUEST_DELAY)
    wta = fetch_wta_rankings(max_rank)
    return atp + wta
