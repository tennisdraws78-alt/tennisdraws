"""Fetch ATP and WTA rankings.

Primary source: Tennis Abstract (tennisabstract.com) — has 2000+ players, no API key needed.
Fallback: RapidAPI Tennis Live Data — capped at 500 players per call.

Rankings are cached to rankings/cache.json and refreshed weekly (every Monday).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
import config

_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Manual name corrections (source name → correct name)
NAME_CORRECTIONS = {
    "Xin Yu Wang": "Xinyu Wang",
}

# Tennis Abstract URLs
TA_ATP_URL = "https://tennisabstract.com/reports/atpRankings.html"
TA_WTA_URL = "https://tennisabstract.com/reports/wtaRankings.html"


def _last_monday_utc() -> datetime:
    """Return the start of the most recent Monday (UTC)."""
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()  # Monday=0
    last_monday = now - timedelta(days=days_since_monday)
    return last_monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _is_cache_fresh() -> bool:
    """Check if rankings cache exists and was updated since last Monday UTC."""
    if not os.path.exists(_CACHE_PATH):
        return False
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated_str = data.get("updated")
        if not updated_str:
            return False
        updated = datetime.fromisoformat(updated_str)
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return updated >= _last_monday_utc()
    except (json.JSONDecodeError, ValueError, OSError):
        return False


def _load_cache(gender: str) -> list[dict]:
    """Load cached rankings for a gender ('M' or 'F')."""
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = "atp" if gender == "M" else "wta"
        return data.get(key, [])
    except (json.JSONDecodeError, OSError):
        return []


def _save_cache(gender: str, players: list[dict]) -> None:
    """Save fetched rankings to cache for a gender."""
    data: dict = {}
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    key = "atp" if gender == "M" else "wta"
    data[key] = players
    data["updated"] = datetime.now(timezone.utc).isoformat()
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


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
        name = NAME_CORRECTIONS.get(name, name)
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
        raw_name = entry.get("rowName", team.get("name", ""))
        players.append({
            "name": NAME_CORRECTIONS.get(raw_name, raw_name),
            "rank": rank,
            "gender": gender,
            "country_code": country.get("alpha3", ""),
            "country_name": country.get("name", ""),
            "points": entry.get("points", 0),
        })

    return players


def fetch_atp_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch ATP rankings up to max_rank.

    Uses weekly cache — only fetches fresh rankings on Mondays (or when cache
    is missing/stale).
    """
    print(f"Fetching ATP rankings (up to {max_rank})...")

    # Check cache first (refreshes weekly on Monday)
    if _is_cache_fresh():
        cached = _load_cache("M")
        if cached:
            # Filter to max_rank
            cached = [p for p in cached if p.get("rank", 9999) <= max_rank]
            print(f"  Using cached ATP rankings ({len(cached)} players, updated this week)")
            return cached

    # Try Tennis Abstract first (has 2000+ players)
    players = _fetch_from_tennis_abstract(TA_ATP_URL, "M", max_rank)
    if players:
        print(f"  Got {len(players)} ATP players from Tennis Abstract")
        _save_cache("M", players)
        return players

    # Fallback to RapidAPI live (capped at 500)
    print("  Tennis Abstract failed, falling back to RapidAPI Live (max 500)...")
    players = _fetch_from_rapidapi(config.ATP_RANKINGS_URL, "M", max_rank)
    print(f"  Got {len(players)} ATP players from RapidAPI Live")
    if players:
        _save_cache("M", players)
    return players


def fetch_wta_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch WTA rankings up to max_rank.

    Uses weekly cache — only fetches fresh rankings on Mondays (or when cache
    is missing/stale).
    """
    print(f"Fetching WTA rankings (up to {max_rank})...")

    # Check cache first (refreshes weekly on Monday)
    if _is_cache_fresh():
        cached = _load_cache("F")
        if cached:
            cached = [p for p in cached if p.get("rank", 9999) <= max_rank]
            print(f"  Using cached WTA rankings ({len(cached)} players, updated this week)")
            return cached

    # Try Tennis Abstract first (has 2000+ players)
    players = _fetch_from_tennis_abstract(TA_WTA_URL, "F", max_rank)
    if players:
        print(f"  Got {len(players)} WTA players from Tennis Abstract")
        _save_cache("F", players)
        return players

    # Fallback to RapidAPI live (capped at 500)
    print("  Tennis Abstract failed, falling back to RapidAPI Live (max 500)...")
    players = _fetch_from_rapidapi(config.WTA_RANKINGS_URL, "F", max_rank)
    print(f"  Got {len(players)} WTA players from RapidAPI Live")
    if players:
        _save_cache("F", players)
    return players


def fetch_all_rankings(max_rank: int = 1500) -> list[dict]:
    """Fetch both ATP and WTA rankings."""
    atp = fetch_atp_rankings(max_rank)
    time.sleep(config.REQUEST_DELAY)
    wta = fetch_wta_rankings(max_rank)
    return atp + wta
