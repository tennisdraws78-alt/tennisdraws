"""Scraper for spaziotennis.com — ATP and WTA entry lists."""
from __future__ import annotations

import re
import time
import requests
from bs4 import BeautifulSoup
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Section headers in Italian and their normalized names
SECTION_HEADERS = {
    "entry list": "Main Draw",
    "main draw": "Main Draw",
    "alternates": "Alternates",
    "qualificazioni": "Qualifying",
    "qualifying": "Qualifying",
}


def _fetch_page(url: str) -> str:
    """Fetch HTML with retries."""
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            print(f"  [Retry {attempt+1}/{config.MAX_RETRIES}] SpazioTennis fetch error: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    return ""


def _get_tournament_links(hub_html: str) -> list[dict]:
    """Extract upcoming tournament entry list links from the hub page.

    The page has two sections separated by <h2> tags:
    - "PROSSIMI TORNEI" (upcoming) — we want these
    - "GIA' DISPUTATI" (already played) — skip these

    Returns list of {name, url, gender, tier} dicts.
    """
    soup = BeautifulSoup(hub_html, "html.parser")

    # Find the two section boundaries
    upcoming_h2 = None
    past_h2 = None
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True).upper()
        if "PROSSIMI" in text:
            upcoming_h2 = h2
        elif "DISPUTAT" in text:
            past_h2 = h2

    # Italian month names to English abbreviations
    it_months = {
        "GENNAIO": "Jan", "FEBBRAIO": "Feb", "MARZO": "Mar",
        "APRILE": "Apr", "MAGGIO": "May", "GIUGNO": "Jun",
        "LUGLIO": "Jul", "AGOSTO": "Aug", "SETTEMBRE": "Sep",
        "OTTOBRE": "Oct", "NOVEMBRE": "Nov", "DICEMBRE": "Dec",
    }

    def _translate_date(text: str) -> str:
        """Convert Italian date like '09-15 FEBBRAIO' to 'Feb 9-15'.

        Also handles two-month ranges: '23 FEBBRAIO – 01 MARZO' -> 'Feb 23 - Mar 1'
        """
        text = text.strip().upper()
        # Replace all Italian month names with English abbreviations
        for it, en in it_months.items():
            text = text.replace(it, en)
        # If no month was found, return empty
        if not any(en in text for en in it_months.values()):
            return ""
        # Normalize dashes and spaces
        text = text.replace("–", "-").replace("  ", " ").strip()
        # Remove leading zeros from day numbers
        text = re.sub(r"\b0(\d)", r"\1", text)

        # Reorder "DD-DD Mon" -> "Mon DD-DD" and "DD Mon - DD Mon" -> "Mon DD - Mon DD"
        # Single month: "9-15 Feb" -> "Feb 9-15"
        m = re.match(r"^(\d{1,2}(?:-\d{1,2})?)\s+(\w{3})$", text)
        if m:
            return f"{m.group(2)} {m.group(1)}"
        # Two months: "23 Feb - 1 Mar" -> "Feb 23 - Mar 1"
        m = re.match(r"^(\d{1,2})\s+(\w{3})\s*-\s*(\d{1,2})\s+(\w{3})$", text)
        if m:
            return f"{m.group(2)} {m.group(1)} - {m.group(4)} {m.group(3)}"
        # "DD - DD Mon" (same month, like "4 - 14 Mar")
        m = re.match(r"^(\d{1,2})\s*-\s*(\d{1,2})\s+(\w{3})$", text)
        if m:
            return f"{m.group(3)} {m.group(1)}-{m.group(2)}"
        return text

    # Collect links with their date context from the upcoming section
    candidate_links = []  # list of (link_element, date_string)
    current_date = ""

    if upcoming_h2 and past_h2:
        current = upcoming_h2.find_next()
        while current and current != past_h2:
            # Check for date headers in <p> or <strong> elements
            if current.name in ("p", "strong"):
                el_text = current.get_text(strip=True).upper()
                # Date patterns: "09-15 FEBBRAIO", "23 FEBBRAIO – 01 MARZO", "04 – 14 MARZO"
                if any(m in el_text for m in it_months):
                    translated = _translate_date(el_text)
                    if translated:
                        current_date = translated

            if current.name == "a" and current.get("href"):
                candidate_links.append((current, current_date))
            current = current.find_next()
    else:
        # Fallback: use all links on the page
        for link in soup.find_all("a", href=True):
            candidate_links.append((link, ""))

    tournaments = []
    seen_urls = set()

    for link, date_str in candidate_links:
        href = link.get("href", "")
        text = link.get_text(strip=True).upper()

        if "/trn/ent/entry-list" not in href:
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        if "2025" in href:
            continue

        # Determine gender and tier from link text
        gender = "M"
        tier = "ATP"
        if "WTA" in text:
            gender = "F"
            tier = "WTA"
        if "CHALLENGER" in text:
            tier = "ATP Challenger"
        if "QUALIFICAZIONI" in text:
            tier = "Qualifying"

        # Extract tournament name from link text
        name = text.replace("ENTRY LIST", "").strip()
        name = re.sub(r"^\d+\s*", "", name).strip()

        # Use the date from the hub page header
        week = date_str

        tournaments.append({
            "name": name,
            "url": href,
            "gender": gender,
            "tier": tier,
            "week": week,
        })

    return tournaments


def _parse_player_line(line: str) -> dict:
    """Parse a player line like 'Alcaraz,Carlos ESP 1' or 'OUT Djokovic,Novak SRB 4'.

    Returns dict with name, country, rank, withdrawn, or None if not a player line.
    """
    line = line.strip()
    if not line or len(line) < 5:
        return None

    # Detect [DEL] marker from <del> tag extraction
    withdrawn = False
    status = ""
    if line.startswith("[DEL]"):
        withdrawn = True
        line = line[5:]

    # Detect status prefixes
    for prefix in ["OUT ", "IN ", "PR ", "LL ", "SE ", "WC "]:
        if line.startswith(prefix):
            status = prefix.strip()
            withdrawn = prefix.strip() == "OUT"
            line = line[len(prefix):].strip()
            break

    # Remove alternate numbering like "2 Majchrzak,Kamil POL 59"
    line = re.sub(r"^\d+\s+", "", line).strip()
    # Also remove patterns like "(1)" that appear in some alternates
    line = re.sub(r"\(\d+\)\s*", "", line).strip()

    # Expected format: LastName,FirstName COUNTRY RANK
    # Country is 2-3 letter code, Rank is a number
    # Some players might have missing country or rank

    # Try the standard pattern: Name,Name CC### or Name,Name CC ##
    match = re.match(
        r"^([A-Za-zÀ-ÿ\s\-\'\.]+),([A-Za-zÀ-ÿ\s\-\'\.]+)\s+([A-Z]{2,3})\s+(\d+)$",
        line
    )
    if match:
        last_name = match.group(1).strip()
        first_name = match.group(2).strip()
        country = match.group(3)
        rank = int(match.group(4))
        return {
            "player_name": f"{first_name} {last_name}",
            "player_country": country,
            "player_rank": rank,
            "withdrawn": withdrawn,
            "status": status,
        }

    # Try without country: Name,Name RANK (some entries miss country)
    match = re.match(
        r"^([A-Za-zÀ-ÿ\s\-\'\.]+),([A-Za-zÀ-ÿ\s\-\'\.]+)\s+(\d+)$",
        line
    )
    if match:
        last_name = match.group(1).strip()
        first_name = match.group(2).strip()
        rank = int(match.group(3))
        return {
            "player_name": f"{first_name} {last_name}",
            "player_country": "",
            "player_rank": rank,
            "withdrawn": withdrawn,
            "status": status,
        }

    # Try with country but no rank
    match = re.match(
        r"^([A-Za-zÀ-ÿ\s\-\'\.]+),([A-Za-zÀ-ÿ\s\-\'\.]+)\s+([A-Z]{2,3})$",
        line
    )
    if match:
        last_name = match.group(1).strip()
        first_name = match.group(2).strip()
        country = match.group(3)
        return {
            "player_name": f"{first_name} {last_name}",
            "player_country": country,
            "player_rank": 0,
            "withdrawn": withdrawn,
            "status": status,
        }

    return None


def _parse_wta_player_line(line: str) -> dict:
    """Parse a WTA player line from Spazio Tennis.

    WTA format: '1\u200b ARYNA SABALENKA 1\u200b'
    or: '2\u200b IGA SWIATEK (POL) 2\u200b'
    or: '11\u200b BARBORA KREJCIKOVA (CZE) PR10'

    Returns dict with name, country, rank, or None if not a player line.
    """
    # Remove zero-width spaces
    line = line.replace("\u200b", "").strip()
    if not line or len(line) < 5:
        return None

    # Detect [DEL] marker from <del> tag extraction
    withdrawn = False
    if line.startswith("[DEL]"):
        withdrawn = True
        line = line[5:].strip()

    # Detect OUT prefix (WTA format: "OUT ARYNA SABALENKA 1")
    if line.upper().startswith("OUT "):
        withdrawn = True
        line = line[4:].strip()

    # Format: [SEED_NUM] NAME (COUNTRY) RANK_OR_PR
    # or: [SEED_NUM] NAME RANK
    # Seed number is optional — OUT lines don't have one.
    # Try with country in parentheses
    match = re.match(
        r"^(?:\d+\s+)?(.+?)\s+\(([A-Z]{2,3})\)\s+(?:PR)?(\d+)\s*$",
        line
    )
    if match:
        name = match.group(1).strip()
        country = match.group(2)
        rank = int(match.group(3))
        # Convert ALL CAPS name to Title Case
        name = _title_case_name(name)
        return {
            "player_name": name,
            "player_country": country,
            "player_rank": rank,
            "withdrawn": withdrawn,
            "status": "OUT" if withdrawn else "",
        }

    # Try without country
    match = re.match(
        r"^(?:\d+\s+)?(.+?)\s+(?:PR)?(\d+)\s*$",
        line
    )
    if match:
        name = match.group(1).strip()
        rank = int(match.group(2))
        # Make sure name is actually text (not just numbers)
        if re.search(r"[A-Za-z]", name):
            name = _title_case_name(name)
            return {
                "player_name": name,
                "player_country": "",
                "player_rank": rank,
                "withdrawn": withdrawn,
                "status": "OUT" if withdrawn else "",
            }

    return None


def _parse_plain_name_line(line: str) -> dict:
    """Parse a plain name line like 'Coco Gauff' or 'Elena-Gabriela Ruse'.

    Used for pages that list only player names without rank/country/seed.
    Returns dict with name and empty rank/country, or None if not a player line.
    """
    line = line.strip()
    if not line or len(line) < 4:
        return None

    # Must be at least two words (first + last name)
    words = line.split()
    if len(words) < 2:
        return None

    # All words must be alphabetic (with hyphens/apostrophes allowed)
    for w in words:
        cleaned = w.replace("-", "").replace("'", "").replace("'", "")
        if not cleaned.isalpha():
            return None

    # Skip known non-player lines (section headers, navigation, etc.)
    upper = line.upper()
    skip_phrases = [
        "ENTRY LIST", "MAIN DRAW", "ALTERNATES", "QUALIFYING",
        "CALENDARIO", "TUTTE LE", "IL CALENDARIO", "QUI IL",
        "PROSSIMI TORNEI", "GIA DISPUTATI",
    ]
    for phrase in skip_phrases:
        if phrase in upper:
            return None

    # Apply title case if the name is ALL CAPS
    name = _title_case_name(line) if line == line.upper() else line

    return {
        "player_name": name,
        "player_country": "",
        "player_rank": 0,
        "withdrawn": False,
        "status": "",
    }


def _title_case_name(name: str) -> str:
    """Convert ALL CAPS name to Title Case, handling particles like 'de', 'van'."""
    particles = {"de", "di", "da", "van", "von", "del", "la", "le"}
    words = name.split()
    result = []
    for w in words:
        if w.lower() in particles and result:  # don't lowercase first word
            result.append(w.lower())
        else:
            result.append(w.capitalize())
    return " ".join(result)


def _extract_lines_with_del(article) -> list[str]:
    """Extract text lines, marking <del>/<s>/<strike> content with [DEL] prefix."""
    for tag in article.find_all(["del", "s", "strike"]):
        tag.replace_with(f"[DEL]{tag.get_text()}")
    text = article.get_text(separator="\n")
    return [l.strip() for l in text.split("\n") if l.strip()]


def _parse_tournament_page(html: str, tournament_info: dict) -> list[dict]:
    """Parse a single tournament entry list page into player entries."""
    soup = BeautifulSoup(html, "html.parser")

    # Get text content from the article body
    article = (
        soup.find("div", class_="entry-content")
        or soup.find("article")
        or soup.find("div", class_="post-content")
        or soup.body
    )
    if not article:
        return []

    lines = _extract_lines_with_del(article)

    entries = []
    current_section = "Main Draw"
    past_header = False  # Track if we've seen the ENTRY LIST header
    is_challenger = "CHALLENGER" in tournament_info.get("tier", "").upper()
    current_tournament = tournament_info["name"]
    current_tier = tournament_info["tier"]
    week = tournament_info.get("week", "")

    for line in lines:
        line_upper = line.upper()

        # Detect section changes
        if "ALTERNATES" in line_upper:
            current_section = "Alternates"
            continue
        if "QUALIFICAZION" in line_upper or "QUALIFYING" in line_upper:
            current_section = "Qualifying"
            continue
        if "ENTRY LIST" in line_upper and any(
            t in line_upper for t in ["ATP", "WTA", "CHALLENGER"]
        ):
            current_section = "Main Draw"
            past_header = True

            # For Challenger pages, extract per-tournament name from header
            # e.g. "ENTRY LIST ATP CHALLENGER 125 LILLE"
            if is_challenger:
                ch_match = re.match(
                    r".*ENTRY\s+LIST\s+ATP\s+CHALLENGER\s+(\d+)\s+(.+)",
                    line_upper,
                )
                if ch_match:
                    level = ch_match.group(1)
                    city = ch_match.group(2).strip()
                    # Clean up city name (keep periods and hyphens)
                    city = re.sub(r"[^\w\s\-\.]", "", city).strip()
                    # Add space after period for title casing (ST.BRIEUC -> St. Brieuc)
                    city = re.sub(r"\.(?=[A-Za-z])", ". ", city)
                    city = _title_case_name(city)
                    current_tournament = f"{city} (CH {level})"
                    current_tier = f"ATP Challenger {level}"

            continue

        # Try parsing as a player line (ATP format first, then WTA format)
        player = _parse_player_line(line) or _parse_wta_player_line(line)
        if player:
            past_header = True
            entries.append({
                "tournament": current_tournament,
                "tier": current_tier,
                "week": week,
                "section": current_section,
                "player_name": player["player_name"],
                "player_rank": player["player_rank"],
                "player_country": player["player_country"],
                "withdrawn": player["withdrawn"],
                "gender": tournament_info["gender"],
                "source": "SpazioTennis",
            })

    # If no structured entries found, try plain-name parsing as fallback.
    # Some pages (e.g. early WTA entry lists) only list player names.
    if not entries:
        past_header = False
        for line in lines:
            line_upper = line.upper()
            if "ENTRY LIST" in line_upper:
                past_header = True
                continue
            if not past_header:
                continue
            player = _parse_plain_name_line(line)
            if player:
                entries.append({
                    "tournament": current_tournament,
                    "tier": current_tier,
                    "week": week,
                    "section": "Main Draw",
                    "player_name": player["player_name"],
                    "player_rank": player["player_rank"],
                    "player_country": player["player_country"],
                    "withdrawn": player["withdrawn"],
                    "gender": tournament_info["gender"],
                    "source": "SpazioTennis",
                })

    return _fix_cross_section_withdrawals(entries)


def _fix_cross_section_withdrawals(entries: list[dict]) -> list[dict]:
    """Remove false withdrawals where a player moved to a higher section.

    If a player is OUT in Alternates but appears in Main Draw → not withdrawn
    (they got promoted because someone else withdrew).
    """
    SECTION_RANK = {"Alternates": 0, "Qualifying": 1, "Main Draw": 2}

    # Group by normalized player name
    by_player = {}
    for e in entries:
        key = e["player_name"].lower()
        by_player.setdefault(key, []).append(e)

    fixed = 0
    for name, player_entries in by_player.items():
        # Find highest section where player appears and is NOT withdrawn
        active_sections = [
            SECTION_RANK.get(e["section"], -1)
            for e in player_entries if not e["withdrawn"]
        ]
        if not active_sections:
            continue
        max_active = max(active_sections)

        # Clear withdrawn flag for entries in lower sections
        for e in player_entries:
            if e["withdrawn"]:
                wd_rank = SECTION_RANK.get(e["section"], -1)
                if wd_rank < max_active:
                    e["withdrawn"] = False
                    fixed += 1

    if fixed:
        print(f"    ↳ Fixed {fixed} false withdrawal(s) (promoted to higher section)")

    return entries


def scrape_all() -> list[dict]:
    """Scrape all upcoming tournament entry lists from Spazio Tennis."""
    print("Scraping Spazio Tennis...")

    # Step 1: Get hub page
    hub_html = _fetch_page(config.SPAZIOTENNIS_HUB_URL)
    if not hub_html:
        print("  Failed to fetch hub page")
        return []

    # Step 2: Extract tournament links
    tournaments = _get_tournament_links(hub_html)
    print(f"  Found {len(tournaments)} tournament links")

    # Step 3: Scrape each tournament page
    all_entries = []
    for i, t in enumerate(tournaments):
        print(f"  [{i+1}/{len(tournaments)}] Scraping {t['name']}...")
        time.sleep(config.REQUEST_DELAY)

        html = _fetch_page(t["url"])
        if not html:
            continue

        entries = _parse_tournament_page(html, t)
        all_entries.extend(entries)
        active = [e for e in entries if not e["withdrawn"]]
        print(f"    → {len(active)} active, {len(entries) - len(active)} withdrawn")

    print(f"  Total: {len(all_entries)} entries from {len(tournaments)} tournaments")
    return all_entries
