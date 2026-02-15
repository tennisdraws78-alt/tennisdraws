"""Scrape WTA entry lists from the official WTA website.

Uses the public WTA API to discover upcoming tournaments, then scrapes
each tournament's player-list page for entry data.

Requires: requests, beautifulsoup4 (no Playwright needed).
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

import config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

LEVEL_MAP = {
    "WTA 1000": "WTA 1000",
    "WTA 500": "WTA 500",
    "WTA 250": "WTA 250",
    "WTA 125": "WTA 125",
}


def _fetch_tournament_calendar() -> list[dict]:
    """Fetch upcoming WTA tournaments from the official API."""
    today = datetime.now()
    # Look 8 weeks ahead
    end = today + timedelta(weeks=8)

    params = {
        "from": today.strftime("%Y-%m-%d"),
        "to": end.strftime("%Y-%m-%d"),
        "excludeLevels": "ITF",
        "pageSize": "50",
    }

    try:
        resp = requests.get(
            config.WTA_API_URL,
            params=params,
            headers=HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Error fetching WTA calendar: {e}")
        return []

    tournaments = []
    for t in data.get("content", []):
        tid = t.get("tournamentGroup", {}).get("id")
        if not tid:
            continue

        city = t.get("city", "")
        level = t.get("level", "")
        tier = LEVEL_MAP.get(level, level)
        start_date = t.get("startDate", "")

        # Convert "2026-02-15" → "Feb 15"
        week = ""
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                week = f"{dt.strftime('%b')} {dt.day}"  # "Feb 15" (no leading zero)
            except ValueError:
                week = ""

        # Build a slug from the city for URL (any slug works, ID is what matters)
        slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-") or "t"

        tournaments.append({
            "id": tid,
            "slug": slug,
            "year": t.get("year", datetime.now().year),
            "name": city.title(),  # "DOHA" → "Doha"
            "tier": tier,
            "week": week,
            "status": t.get("status", ""),
        })

    return tournaments


def _scrape_player_list(tournament: dict) -> list[dict]:
    """Scrape the player list page for a single tournament."""
    url = config.WTA_PLAYER_LIST_URL.format(
        id=tournament["id"],
        slug=tournament["slug"],
        year=tournament["year"],
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"    Error scraping {tournament['name']}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    entries = []
    current_section = "Main Draw"

    # Walk all elements looking for section markers and player names
    for tag in soup.find_all(True):
        # Check for section changes via data-ui-tab or text content
        ui_tab = (tag.get("data-ui-tab") or "").lower()
        text = tag.get_text(strip=True).lower()

        if "qualifying" in ui_tab or text == "qualifying":
            current_section = "Qualifying"
        elif "main draw" in ui_tab or text == "main draw":
            current_section = "Main Draw"
        elif "doubles" in ui_tab or text == "doubles":
            current_section = "DOUBLES"

        # Extract player name from data-tracking attribute
        player_name = tag.get("data-tracking-player-name")
        if not player_name or current_section == "DOUBLES":
            continue

        name = player_name.strip()
        if not name:
            continue

        # Try to extract country from nearby flag image or sibling
        country = ""
        # Look for an <img> with a flag in siblings or parent
        parent = tag.parent
        if parent:
            flag_img = parent.find("img", src=re.compile(r"flags/"))
            if flag_img:
                country = (flag_img.get("alt") or "").strip().upper()

        entries.append({
            "player_name": name,
            "player_country": country,
            "tournament": tournament["name"],
            "tier": tournament["tier"],
            "section": current_section,
            "week": tournament["week"],
            "source": "WTA Official",
            "gender": "F",
            "withdrawn": False,
        })

    return entries


def scrape_all() -> list[dict]:
    """Scrape WTA entry lists from the official website.

    Returns a list of entry dicts in the standard format.
    """
    print("Scraping WTA Official...")
    tournaments = _fetch_tournament_calendar()
    if not tournaments:
        print("  No upcoming WTA tournaments found")
        return []

    print(f"  Found {len(tournaments)} upcoming WTA tournaments")

    all_entries = []
    for i, t in enumerate(tournaments):
        print(f"  [{i + 1}/{len(tournaments)}] {t['name']} ({t['tier']})...", end="")
        entries = _scrape_player_list(t)
        all_entries.extend(entries)

        # Count sections
        md = sum(1 for e in entries if e["section"] == "Main Draw")
        q = sum(1 for e in entries if e["section"] == "Qualifying")
        print(f" {md} MD, {q} Q")

        if i < len(tournaments) - 1:
            time.sleep(config.REQUEST_DELAY)

    print(f"  Total: {len(all_entries)} entries from {len(tournaments)} tournaments")
    return all_entries
