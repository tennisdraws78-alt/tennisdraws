"""Scraper for Wikipedia — tournament wild cards and entry methods.

Fetches "Other entrants" sections from Wikipedia tournament pages
(e.g. 2026_Mérida_Open) to extract wild card, protected ranking,
lucky loser, and special exempt entries.

Uses the MediaWiki API (action=parse) — no HTML scraping needed.
"""
from __future__ import annotations

import re
import time
import requests

import config

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "TennisDrawsBot/1.0 (tennis draws project)"}

# Maps calendar tournament name → Wikipedia article title.
# Only needed when the article name differs from "2026_{Name}_Open"
# or "2026_{Name}" patterns.
WIKI_ARTICLE_MAP = {
    # ATP
    "Doha": "2026_Qatar_ExxonMobil_Open",
    "Rotterdam": "2026_ABN_AMRO_Open",
    "Buenos Aires": "2026_Argentina_Open",
    "Rio de Janeiro": "2026_Rio_Open",
    "Acapulco": "2026_Abierto_Mexicano",
    "Indian Wells": "2026_BNP_Paribas_Open",
    "Miami": "2026_Miami_Open",
    "Monte Carlo": "2026_Monte-Carlo_Masters",
    "Barcelona": "2026_Barcelona_Open",
    "Madrid": "2026_Madrid_Open",
    "Rome": "2026_Italian_Open",
    "French Open": "2026_French_Open",
    "Queens Club": "2026_Queen's_Club_Championships",
    "Halle": "2026_Halle_Open",
    "Wimbledon": "2026_Wimbledon_Championships",
    "Hamburg": "2026_Hamburg_European_Open",
    "Montreal": "2026_National_Bank_Open",
    "Cincinnati": "2026_Cincinnati_Open",
    "US Open": "2026_US_Open_(tennis)",
    "Shanghai": "2026_Shanghai_Masters",
    "Basel": "2026_Swiss_Indoors",
    "Vienna": "2026_Erste_Bank_Open",
    "Paris": "2026_Paris_Masters",
    "Turin": "2026_ATP_Finals",
    "Australian Open": "2026_Australian_Open",
    # WTA
    "Dubai": "2026_Dubai_Tennis_Championships",
    "Austin": "2026_ATX_Open",
    "Merida": "2026_Mérida_Open",
    "Charleston": "2026_Charleston_Open",
    "Stuttgart": "2026_Porsche_Tennis_Grand_Prix",
    "Guadalajara": "2026_Guadalajara_Open",
    "Strasbourg": "2026_Internationaux_de_Strasbourg",
    "Berlin": "2026_Berlin_Open",
    "Nottingham": "2026_Nottingham_Open",
    "Bad Homburg": "2026_Bad_Homburg_Open",
    "Rabat": "2026_Grand_Prix_SAR_La_Princesse_Lalla_Meryem",
    "Monterrey": "2026_Abierto_GNP_Seguros",
    "Cleveland": "2026_Tennis_in_the_Land",
}

# Entry method detection from descriptive sentences
_ENTRY_METHOD_PATTERNS = [
    (re.compile(r"wildcard", re.IGNORECASE), "WC"),
    (re.compile(r"protected ranking", re.IGNORECASE), "PR"),
    (re.compile(r"special exempt", re.IGNORECASE), "SE"),
    (re.compile(r"lucky loser", re.IGNORECASE), "LL"),
    (re.compile(r"qualifying draw", re.IGNORECASE), "Q"),
    (re.compile(r"qualif", re.IGNORECASE), "Q"),
]

# Section for qualifying wild cards
_QUAL_WC_PATTERN = re.compile(
    r"wildcard.*qualif|qualif.*wildcard", re.IGNORECASE
)


def _guess_article_names(tournament: str) -> list[str]:
    """Generate candidate Wikipedia article titles for a tournament."""
    # Check explicit map first
    if tournament in WIKI_ARTICLE_MAP:
        return [WIKI_ARTICLE_MAP[tournament]]

    # Try common patterns
    safe = tournament.replace(" ", "_")
    return [
        f"2026_{safe}_Open",
        f"2026_{safe}",
        f"2026_{safe}_Championships",
    ]


def _page_exists(title: str) -> bool:
    """Check if a Wikipedia page exists."""
    params = {
        "action": "query",
        "titles": title,
        "format": "json",
    }
    try:
        resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        pages = resp.json().get("query", {}).get("pages", {})
        return "-1" not in pages
    except Exception:
        return False


def _find_other_entrants_section(title: str) -> int | None:
    """Find the section index for 'Other entrants' under Singles.

    Returns the section index, or None if not found.
    """
    params = {
        "action": "parse",
        "page": title,
        "prop": "sections",
        "format": "json",
    }
    try:
        resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
    except Exception:
        return None

    if "parse" not in data:
        return None

    sections = data["parse"]["sections"]
    # Find "Singles main draw entrants" or "Singles main-draw entrants"
    singles_idx = None
    for s in sections:
        if re.search(r"singles.*main.*draw.*entrant", s["line"], re.IGNORECASE):
            singles_idx = int(s["index"])
            break

    if singles_idx is None:
        return None

    # Find the first "Other entrants" after the singles section
    for s in sections:
        idx = int(s["index"])
        if idx > singles_idx and "other entrant" in s["line"].lower():
            return idx
        # Stop if we've gone past singles into doubles
        if idx > singles_idx and "doubles" in s["line"].lower():
            break

    return None


def _fetch_section_wikitext(title: str, section_idx: int) -> str:
    """Fetch the wikitext for a specific section."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "section": str(section_idx),
        "format": "json",
    }
    try:
        resp = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
        if "parse" in data:
            return data["parse"]["wikitext"]["*"]
    except Exception:
        pass
    return ""


def _parse_entrants_wikitext(wikitext: str) -> list[dict]:
    """Parse 'Other entrants' wikitext to extract players and entry methods.

    Expected format:
        The following players received [[Wild card (sports)|wildcard]]s into the singles main draw:
        * {{flagicon|COL}} [[Camila Osorio]]
        * {{flagicon|TUR}} [[Zeynep Sönmez]]

        The following players received entry using a protected ranking:
        * {{flagicon|CHN}} [[Shang Juncheng]]

    Returns list of {player_name, country, entry_method, section}.
    """
    results = []
    current_method = ""
    current_section = "Main Draw"

    for line in wikitext.split("\n"):
        line = line.strip()

        # Detect descriptive sentence that sets the entry method
        if line.startswith("The following") or line.startswith("the following"):
            current_method = ""
            for pattern, method in _ENTRY_METHOD_PATTERNS:
                if pattern.search(line):
                    current_method = method
                    break

            # Check if this is qualifying wild cards
            if _QUAL_WC_PATTERN.search(line):
                current_section = "Qualifying"
                current_method = "WC"
            elif "qualifying" in line.lower():
                current_section = "Qualifying"
            else:
                current_section = "Main Draw"
            continue

        # Parse player bullet points: * {{flagicon|COL}} [[Camila Osorio]]
        if line.startswith("*"):
            # Extract country from {{flagicon|XXX}}
            flag_m = re.search(r"\{\{flagicon\|(\w{2,3})\}\}", line)
            country = flag_m.group(1) if flag_m else ""

            # Extract player name from [[Player Name]] or [[Link|Display Name]]
            name_m = re.search(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]", line)
            if name_m:
                player_name = name_m.group(2) if name_m.group(2) else name_m.group(1)
                # Clean up any remaining markup
                player_name = player_name.strip()

                if player_name and current_method:
                    results.append({
                        "player_name": player_name,
                        "country": country,
                        "entry_method": current_method,
                        "section": current_section,
                    })

    return results


def scrape_all() -> list[dict]:
    """Scrape Wikipedia for wild cards and entry methods.

    Iterates through ATP and WTA calendars, fetches "Other entrants"
    sections, and returns entries in standard scraper format.
    """
    print("Scraping Wikipedia for wild cards and entry methods...")

    all_calendars = [
        (getattr(config, "ATP_CALENDAR", {}), "M"),
        (getattr(config, "WTA_CALENDAR", {}), "F"),
    ]

    entries = []
    found_count = 0
    tried_count = 0

    for calendar, gender in all_calendars:
        for tourn_name, meta in calendar.items():
            # Skip non-standard events
            if tourn_name in ("United Cup", "Hopman Cup"):
                continue

            tried_count += 1
            city, country, surface, dates, tier = meta

            # Extract week from dates: "23 Feb - 1 Mar" → "Feb 23"
            dm = re.match(r"(\d{1,2})\s+(\w{3})", dates)
            week = f"{dm.group(2)} {dm.group(1)}" if dm else ""

            # Find Wikipedia article
            candidates = _guess_article_names(tourn_name)
            article = None
            for candidate in candidates:
                if _page_exists(candidate):
                    article = candidate
                    break
                time.sleep(0.5)

            if not article:
                continue

            # Find "Other entrants" section
            section_idx = _find_other_entrants_section(article)
            if section_idx is None:
                time.sleep(0.5)
                continue

            # Fetch and parse the section
            wikitext = _fetch_section_wikitext(article, section_idx)
            if not wikitext:
                time.sleep(0.5)
                continue

            entrants = _parse_entrants_wikitext(wikitext)
            found_count += 1

            for entrant in entrants:
                # Only keep WC, PR, SE, LL (skip Q since we have better sources)
                if entrant["entry_method"] == "Q":
                    continue

                entries.append({
                    "tournament": tourn_name,
                    "tier": tier,
                    "week": week,
                    "section": entrant["section"],
                    "player_name": entrant["player_name"],
                    "player_country": entrant["country"],
                    "player_rank": 0,
                    "withdrawn": False,
                    "gender": gender,
                    "source": "Wikipedia",
                    "entry_method": entrant["entry_method"],
                })

            time.sleep(1)  # Rate limiting

    print(f"  Found {found_count} tournaments with entrant data "
          f"(tried {tried_count})")
    print(f"  Extracted {len(entries)} entries "
          f"(WC/PR/SE/LL)")
    return entries
