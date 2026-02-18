"""Scraper for canaltenis.com — ATP, WTA and Challenger entry lists.

CanalTenis is a Spanish-language tennis blog that publishes structured
entry list articles covering Grand Slams, ATP 1000/500/250, WTA 1000/500/250,
and ATP Challengers.

Discovery: crawl the /category/entrylist/ hub pages to find article links,
then scrape each article for player tables.
"""
from __future__ import annotations

import re
import time
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Spanish month names -> English abbreviations (for date parsing)
ES_MONTHS = {
    "enero": "Jan", "febrero": "Feb", "marzo": "Mar",
    "abril": "Apr", "mayo": "May", "junio": "Jun",
    "julio": "Jul", "agosto": "Aug", "septiembre": "Sep",
    "octubre": "Oct", "noviembre": "Nov", "diciembre": "Dec",
}

# Spanish tournament names -> canonical config key
TOURNAMENT_ALIASES = {
    "cherburgo": "Cherbourg",
    "nueva delhi": "New Delhi",
    "open australia": "Australian Open",
    "adelaida": "Adelaide",
    "abu dhabi": "Abu Dhabi",
    "pekin": "Beijing",
    "tokio": "Tokyo",
    "dubai": "Dubai",
    "dub\u00e1i": "Dubai",
    "r\u00edo open": "Rio de Janeiro",
    "rio open": "Rio de Janeiro",
    "r\u00edo de janeiro": "Rio de Janeiro",
    "r\u00edo janeiro": "Rio de Janeiro",
    "chile open": "Santiago",
    "argentina open": "Buenos Aires",
    "buenos aires": "Buenos Aires",
    "m\u00e9rida": "Merida",
    "concepc\u00edon": "Concepcion",
    "concepci\u00f3n": "Concepcion",
    "san pablo": "Sao Paulo",
    "s\u00e3o paulo": "Sao Paulo",
    "saint brieuc": "St. Brieuc",
}

# Maximum category pages to crawl (safety limit)
MAX_CATEGORY_PAGES = 5


def _fetch_page(url: str) -> str:
    """Fetch HTML with retries."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] CanalTenis fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return ""


def _get_article_links() -> list[str]:
    """Crawl category pages to collect entry-list article URLs."""
    all_links: list[str] = []
    seen: set[str] = set()

    for page_num in range(1, MAX_CATEGORY_PAGES + 1):
        if page_num == 1:
            url = config.CANALTENIS_CATEGORY_URL
        else:
            url = f"{config.CANALTENIS_CATEGORY_URL}page/{page_num}/"

        html = _fetch_page(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")

        # Find article links — they appear as <a> tags with href containing "entry-list-"
        found_new = False
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "entry-list-" not in href:
                continue
            # Normalize URL
            if not href.startswith("http"):
                href = "https://canaltenis.com" + href
            # Remove trailing slashes for dedup
            href = href.rstrip("/")
            if href not in seen:
                seen.add(href)
                all_links.append(href)
                found_new = True

        if not found_new:
            break  # No new links found, stop pagination

        time.sleep(config.REQUEST_DELAY)

    # Deduplicate while preserving order
    return all_links


def _build_calendar_lookup() -> dict:
    """Build a unified lookup: lowercase tournament name -> (tier, week, gender).

    Merges ATP_CALENDAR, WTA_CALENDAR, WTA125_CALENDAR, and CHALLENGER_CALENDAR.
    """
    lookup = {}

    for name, (city, country, surface, dates, tier) in config.ATP_CALENDAR.items():
        # Extract week start from dates like "9 Feb - 15 Feb"
        week = _dates_to_week(dates)
        lookup[name.lower()] = {"tier": tier, "week": week, "gender": "M"}

    for name, (city, country, surface, dates, tier) in config.WTA_CALENDAR.items():
        week = _dates_to_week(dates)
        key = name.lower()
        # Don't overwrite ATP entry for shared tournaments (Grand Slams)
        if key not in lookup:
            lookup[key] = {"tier": tier, "week": week, "gender": "F"}
        else:
            # Store WTA variant with suffix
            lookup[key + "|f"] = {"tier": tier, "week": week, "gender": "F"}

    for name, (city, country, surface, dates, tier) in getattr(config, "WTA125_CALENDAR", {}).items():
        week = _dates_to_week(dates)
        key = name.lower()
        if key not in lookup:
            lookup[key] = {"tier": tier, "week": week, "gender": "F"}
        else:
            lookup[key + "|f"] = {"tier": tier, "week": week, "gender": "F"}

    for name, (city, country, surface, dates, tier) in getattr(config, "CHALLENGER_CALENDAR", {}).items():
        week = _dates_to_week(dates)
        key = name.lower()
        if key not in lookup:
            lookup[key] = {"tier": tier, "week": week, "gender": "M"}
        else:
            # Don't overwrite WTA entries — store challenger with |m suffix
            existing = lookup[key]
            if existing["gender"] != "M":
                lookup[key + "|m"] = {"tier": tier, "week": week, "gender": "M"}
            else:
                lookup[key] = {"tier": tier, "week": week, "gender": "M"}

    return lookup


def _dates_to_week(dates: str) -> str:
    """Convert '9 Feb - 15 Feb' or '2 Mar - 8 Mar' to 'Feb 9' or 'Mar 2'."""
    m = re.match(r"(\d+)\s+(\w+)", dates.strip())
    if m:
        day = m.group(1)
        month = m.group(2)
        return f"{month} {day}"
    return ""


def _resolve_tournament(raw_name: str, gender: str, calendar: dict) -> dict:
    """Look up tournament in calendar to get tier and week.

    Returns dict with keys: name, tier, week.
    """
    lower = raw_name.strip().lower()

    # Step 1: Check if the raw name has a direct alias -> canonical name
    canonical = TOURNAMENT_ALIASES.get(lower)
    if canonical:
        lower = canonical.lower()
        raw_name = canonical

    # Step 2: Try gender-specific lookup first (most precise)
    gender_suffix = "|f" if gender == "F" else "|m"
    meta = calendar.get(lower + gender_suffix)
    if meta:
        return {"name": raw_name.strip(), "tier": meta["tier"], "week": meta["week"]}

    # Step 3: Try direct lookup in calendar (check gender match)
    meta = calendar.get(lower)
    if meta:
        if not gender or meta["gender"] == gender:
            return {"name": raw_name.strip(), "tier": meta["tier"], "week": meta["week"]}
        # Direct key exists but wrong gender — still use if no gender-specific alternative
        return {"name": raw_name.strip(), "tier": meta["tier"], "week": meta["week"]}

    # Step 4: Try partial alias match (for multi-word aliases like "rio open")
    for alias, canon in TOURNAMENT_ALIASES.items():
        if alias in lower and alias != lower:
            canon_lower = canon.lower()
            meta = calendar.get(canon_lower)
            if meta:
                return {"name": canon, "tier": meta["tier"], "week": meta["week"]}
            # Try gender-specific
            meta = calendar.get(canon_lower + gender_suffix)
            if meta:
                return {"name": canon, "tier": meta["tier"], "week": meta["week"]}

    # Step 5: Try partial match against calendar keys (exact substring)
    for key, val in calendar.items():
        if "|" in key:
            continue
        if lower == key or lower in key or key in lower:
            # Prefer gender match
            if gender == "M" and val["gender"] == "M":
                return {"name": raw_name.strip(), "tier": val["tier"], "week": val["week"]}
            if gender == "F" and val["gender"] == "F":
                return {"name": raw_name.strip(), "tier": val["tier"], "week": val["week"]}

    # Step 6: Partial match ignoring gender
    for key, val in calendar.items():
        if "|" in key:
            continue
        if lower in key or key in lower:
            return {"name": raw_name.strip(), "tier": val["tier"], "week": val["week"]}

    return {"name": raw_name.strip(), "tier": "", "week": ""}


def _parse_heading(heading_text: str) -> dict:
    """Parse an <h2> heading like 'Entry List ATP Challenger Hersonissos 2 2026'
    or 'Entry List ATP Indian Wells 2026' or 'Entry List WTA Indian Wells 2026'
    or 'Alternates Entry List ATP Challenger Kigali 2 2026'.

    Returns dict with: section, gender, tournament_raw, is_challenger
    """
    text = heading_text.strip()
    result = {
        "section": "Main Draw",
        "gender": "",
        "tournament_raw": "",
        "is_challenger": False,
        "is_wta125": False,
    }

    # Detect section
    if "alternate" in text.lower():
        result["section"] = "Alternates"
    elif "qualy" in text.lower() or "qualifying" in text.lower():
        result["section"] = "Qualifying"

    # Remove common prefixes
    cleaned = re.sub(r"(?i)^alternates?\s+", "", text)
    cleaned = re.sub(r"(?i)^entry\s+list\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^qualy\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^qualifying\s+", "", cleaned)

    # Detect gender, challenger, and WTA 125
    if re.match(r"(?i)^ATP\s+Challenger\b", cleaned):
        result["gender"] = "M"
        result["is_challenger"] = True
        cleaned = re.sub(r"(?i)^ATP\s+Challenger\s+", "", cleaned)
    elif re.match(r"(?i)^ATP\b", cleaned):
        result["gender"] = "M"
        cleaned = re.sub(r"(?i)^ATP\s+", "", cleaned)
    elif re.match(r"(?i)^WTA\s+125\b", cleaned):
        result["gender"] = "F"
        result["is_wta125"] = True
        cleaned = re.sub(r"(?i)^WTA\s+125\s+", "", cleaned)
    elif re.match(r"(?i)^WTA\b", cleaned):
        result["gender"] = "F"
        cleaned = re.sub(r"(?i)^WTA\s+", "", cleaned)

    # Remove year at the end
    cleaned = re.sub(r"\s*\d{4}\s*$", "", cleaned).strip()

    # Remove parenthetical suffixes like "(ATP Buenos Aires)" or "(ATP Río Janeiro)"
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned).strip()

    result["tournament_raw"] = cleaned
    return result


def _parse_player_cell(text: str) -> dict | None:
    """Parse a player cell like '1. Lorenzo Giustino (ITA)' or '22. SE' or '27. Q'.

    Returns dict with player_name, player_country or None for placeholders.
    """
    text = text.strip()

    # Skip placeholder entries: "22. SE", "24. WC", "27. Q", "28. LL"
    if re.match(r"^\d+\.\s*(SE|WC|Q|LL)\s*$", text):
        return None

    # Match: "1. Player Name (COUNTRY)"
    m = re.match(r"^\d+\.\s*(.+?)\s*\(([A-Z]{2,3})\)\s*$", text)
    if m:
        return {
            "player_name": m.group(1).strip(),
            "player_country": m.group(2).strip(),
        }

    return None


def _parse_rank_cell(text: str) -> dict:
    """Parse a ranking cell. Handles:
    - '206' -> rank=206, entry_method=''
    - '56 (PR 259)' -> rank=56, entry_method='PR'
    - '–' or '-' -> rank=0, entry_method=''
    """
    text = text.strip()

    # Protected ranking: "56 (PR 259)"
    m = re.match(r"^(\d+)\s*\(PR\s+\d+\)", text)
    if m:
        return {"rank": int(m.group(1)), "entry_method": "PR"}

    # Simple number
    m = re.match(r"^(\d+)$", text)
    if m:
        return {"rank": int(m.group(1)), "entry_method": ""}

    # Dash or em-dash (placeholder)
    return {"rank": 0, "entry_method": ""}


def _scrape_article(url: str, calendar: dict) -> list[dict]:
    """Scrape a single CanalTenis entry list article.

    Returns list of player entry dicts.
    """
    html = _fetch_page(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    entries: list[dict] = []

    # Detect gender from URL as fallback
    url_lower = url.lower()
    url_gender = ""
    if "atp-challenger" in url_lower or "entry-list-atp-" in url_lower:
        url_gender = "M"
    elif "entry-list-wta-" in url_lower:
        url_gender = "F"

    # Find all tables with class tabla-tenis
    tables = soup.find_all("table", class_="tabla-tenis")
    if not tables:
        # Fallback: try finding any table in the article content
        article = soup.find("article") or soup.find("div", class_="entry-content")
        if article:
            tables = article.find_all("table")

    if not tables:
        return []

    # For each table, find the preceding <h2> to determine section/gender/tournament
    for table in tables:
        # Walk backward to find the closest <h2> before this table
        heading_info = _find_preceding_heading(table)
        if not heading_info:
            continue

        parsed = _parse_heading(heading_info)
        gender = parsed["gender"] or url_gender
        if not gender:
            # Default based on content
            gender = "M"

        tournament_raw = parsed["tournament_raw"]
        if not tournament_raw:
            continue

        # Resolve tournament against calendar
        resolved = _resolve_tournament(tournament_raw, gender, calendar)
        tournament_name = resolved["name"]
        tier = resolved["tier"]
        week = resolved["week"]

        # If no tier from calendar, try to infer from heading
        if not tier:
            if parsed["is_challenger"]:
                tier = "ATP Challenger"
            elif parsed.get("is_wta125"):
                tier = "WTA 125"
            elif gender == "M":
                tier = "ATP"
            elif gender == "F":
                tier = "WTA"

        # Parse table rows
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            player_text = cells[0].get_text(strip=True)
            rank_text = cells[1].get_text(strip=True)

            player = _parse_player_cell(player_text)
            if not player:
                continue  # Skip placeholders (WC, Q, SE, LL)

            rank_info = _parse_rank_cell(rank_text)

            entries.append({
                "player_name": player["player_name"],
                "player_rank": rank_info["rank"],
                "player_country": player["player_country"],
                "tournament": tournament_name,
                "tier": tier,
                "week": week,
                "section": parsed["section"],
                "gender": gender,
                "withdrawn": False,
                "source": "CanalTenis",
                "entry_method": rank_info["entry_method"],
            })

    return entries


def _find_preceding_heading(element) -> str | None:
    """Walk backward through siblings and parents to find the nearest <h2>
    or <h3> heading before the given element."""
    # Check previous siblings first
    for sibling in element.previous_siblings:
        if hasattr(sibling, "name"):
            if sibling.name in ("h2", "h3"):
                return sibling.get_text(strip=True)
            # Also check within the sibling for headings
            if sibling.name in ("div", "section"):
                headings = sibling.find_all(["h2", "h3"])
                if headings:
                    return headings[-1].get_text(strip=True)

    # Try parent's previous siblings
    parent = element.parent
    if parent:
        for sibling in parent.previous_siblings:
            if hasattr(sibling, "name"):
                if sibling.name in ("h2", "h3"):
                    return sibling.get_text(strip=True)

    return None


def scrape_all() -> list[dict]:
    """Main entry point: discover articles and scrape entry lists.

    Returns list of player entry dicts matching the standard scraper format.
    """
    print("CanalTenis: Discovering entry list articles...")
    article_links = _get_article_links()
    print(f"  Found {len(article_links)} entry list articles")

    if not article_links:
        return []

    calendar = _build_calendar_lookup()
    all_entries: list[dict] = []

    for i, url in enumerate(article_links):
        print(f"  [{i+1}/{len(article_links)}] Scraping: {url.split('/')[-2] if '/' in url else url}")
        entries = _scrape_article(url, calendar)
        all_entries.extend(entries)
        print(f"    -> {len(entries)} players")

        if i < len(article_links) - 1:
            time.sleep(config.REQUEST_DELAY)

    print(f"CanalTenis: Total entries scraped: {len(all_entries)}")
    return all_entries
