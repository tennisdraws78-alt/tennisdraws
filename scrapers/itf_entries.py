"""Scraper for ITF Men's and Women's tournament entry lists.

Scrapes acceptance lists directly from the official ITF website
(itftennis.com) by first discovering tournaments from the calendar
pages, then navigating to each tournament's /acceptance-list page.

Uses Playwright for headless browser automation (required — Incapsula
bot protection blocks raw HTTP requests).
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import config

_playwright_available = True
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    _playwright_available = False

# Number of concurrent browser workers
CONCURRENT_WORKERS = 5

# Month abbreviation lookup
_MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_NUM_TO_ABBR = {v: k.capitalize() for k, v in _MONTH_ABBR.items()}

# Build reverse lookup: UPPER CASE city -> canonical Title Case city
# from config.ITF_CALENDAR to handle tricky cases like "ElSheikh"
_CITY_LOOKUP: dict[str, str] = {}


def _build_city_lookup():
    """Populate _CITY_LOOKUP from config.ITF_CALENDAR."""
    cal = getattr(config, "ITF_CALENDAR", [])
    for entry in cal:
        city = entry[0]  # e.g., "Sharm ElSheikh", "San Diego, CA"
        _CITY_LOOKUP[city.upper()] = city


_build_city_lookup()

# Known ITF tier prefixes (longer first to avoid partial matches)
_ITF_TIER_PREFIXES = ("W100", "W75", "W50", "W35", "W15", "M25", "M15")


def _title_case_city(name: str) -> str:
    """Convert an UPPER CASE city name to Title Case, preserving state abbreviations.

    "SAN DIEGO, CA" -> "San Diego, CA"
    "VERO BEACH, FL" -> "Vero Beach, FL"
    "MONASTIR" -> "Monastir"
    "SHARM ELSHEIKH" -> "Sharm ElSheikh" (via config lookup)
    """
    if not name:
        return name

    # Try exact lookup from config first
    canonical = _CITY_LOOKUP.get(name.upper())
    if canonical:
        return canonical

    # Split on comma to handle "CITY, STATE" patterns
    parts = name.split(",")
    if len(parts) == 2:
        city = parts[0].strip()
        state = parts[1].strip()
        # If state part is 2-3 letters, it's a US state abbreviation — keep uppercase
        if len(state) <= 3 and state.isalpha():
            city_title = _CITY_LOOKUP.get(city.upper()) or city.title()
            return f"{city_title}, {state.upper()}"
        return f"{city.title()}, {state.title()}"

    return name.title()


def _parse_tournament_name(text: str) -> tuple[str, str]:
    """Parse ITF tournament display name into (city, tier_prefix).

    Input examples from the ITF calendar page:
        "W100 SAN DIEGO, CA"  -> ("San Diego, CA", "W100")
        "M25 MONASTIR"        -> ("Monastir", "M25")
        "W75 PORTO"           -> ("Porto", "W75")
        "W75 ANDRÉZIEUX-BOUTHÉON" -> ("Andrézieux-Bouthéon", "W75")

    Returns:
        (city, tier_prefix): city in Title Case, tier_prefix like "W100".
        If no tier prefix found, returns (text_in_title_case, "").
    """
    text = text.strip()
    tier_prefix = ""
    city_part = text

    for prefix in _ITF_TIER_PREFIXES:
        # Match prefix at start (case-insensitive)
        if text.upper().startswith(prefix + " "):
            tier_prefix = prefix.upper()
            city_part = text[len(prefix):].strip()
            break

    city = _title_case_city(city_part)
    return city, tier_prefix


def _normalize_player_name(name: str) -> str:
    """Fix ALL CAPS names from ITF site: 'Martha MATOULA' -> 'Martha Matoula'."""
    if not name:
        return name
    words = name.split()
    fixed = []
    for w in words:
        # Only fix words that are entirely uppercase and longer than 1 char
        if len(w) > 1 and w.isalpha() and w == w.upper():
            fixed.append(w.capitalize())
        else:
            fixed.append(w)
    return " ".join(fixed)


def _parse_date_range(dates_str: str) -> tuple[date | None, date | None]:
    """Parse ITF date string like '16 Feb - 22 Feb 2026', '16 Feb to 22 Feb 2026', or '16 - 22 Feb'.

    Returns (start_date, end_date) or (None, None) on failure.
    """
    if not dates_str:
        return None, None
    # Try "DD Mon - DD Mon YYYY" or "DD Mon - DD Mon"
    m = re.match(
        r"(\d{1,2})\s+(\w{3}).*?(\d{1,2})\s+(\w{3})(?:\s+(\d{4}))?",
        dates_str.strip(),
    )
    if m:
        year = int(m.group(5)) if m.group(5) else date.today().year
        try:
            start = date(year, _MONTH_ABBR.get(m.group(2).lower(), 1), int(m.group(1)))
            end = date(year, _MONTH_ABBR.get(m.group(4).lower(), 1), int(m.group(3)))
            return start, end
        except (ValueError, KeyError):
            pass
    # Try "DD - DD Mon YYYY" or "DD to DD Mon YYYY"
    m2 = re.match(r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s+(\w{3})(?:\s+(\d{4}))?", dates_str.strip())
    if m2:
        year = int(m2.group(4)) if m2.group(4) else date.today().year
        mon = _MONTH_ABBR.get(m2.group(3).lower(), 1)
        try:
            start = date(year, mon, int(m2.group(1)))
            end = date(year, mon, int(m2.group(2)))
            return start, end
        except (ValueError, KeyError):
            pass
    return None, None


def _normalize_week(dates_str: str) -> str:
    """Convert dates string to canonical week format 'Mon DD'."""
    start, _ = _parse_date_range(dates_str)
    if start:
        abbr = _MONTH_NUM_TO_ABBR.get(start.month, "")
        return f"{abbr} {start.day}"
    # Fallback: try to extract first "DD Mon" pattern
    m = re.match(r"(\d{1,2})\s+(\w{3})", dates_str.strip())
    if m:
        return f"{m.group(2)} {m.group(1)}"
    return dates_str.strip()


def _discover_tournaments_from_calendar(page, gender: str) -> list[dict]:
    """Discover tournaments from the official ITF calendar pages.

    Navigates to the ITF tournament calendar for the current and next
    3 months, extracts tournament links and dates, and filters to
    upcoming tournaments starting within [today, today + 30d].
    """
    if gender == "M":
        cal_path = "mens-world-tennis-tour-calendar"
    else:
        cal_path = "womens-world-tennis-tour-calendar"

    today = date.today()
    cutoff_start = today  # Only upcoming, not past/live
    cutoff_end = today + timedelta(days=30)  # 1 month ahead

    tournaments = []
    seen_urls = set()
    cookies_dismissed = False

    for month_offset in range(4):
        # Calculate the month to scrape
        target = today.replace(day=1)
        for _ in range(month_offset):
            target = (target + timedelta(days=32)).replace(day=1)

        url = (
            f"https://www.itftennis.com/en/tournament-calendar/"
            f"{cal_path}/?categories=All&startdate={target:%Y-%m}"
        )

        try:
            page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=config.PLAYWRIGHT_TIMEOUT)
            time.sleep(2)

            # Dismiss cookie banner once
            if not cookies_dismissed:
                try:
                    decline_btn = page.query_selector('button:has-text("Decline")')
                    if decline_btn and decline_btn.is_visible():
                        decline_btn.click()
                        time.sleep(0.5)
                        cookies_dismissed = True
                except Exception:
                    pass

            # Find all tournament links on the calendar page
            links = page.query_selector_all('a[href*="/en/tournament/"]')
            for link in links:
                href = link.get_attribute("href") or ""
                if not href or href in seen_urls:
                    continue

                # Skip non-tournament links (like "View All" etc.)
                if "/tournament-calendar/" in href:
                    continue

                text = link.inner_text().strip()
                if not text or len(text) < 2:
                    continue

                seen_urls.add(href)

                # Normalize to full URL
                if href.startswith("/"):
                    href = "https://www.itftennis.com" + href

                # Extract dates from the sibling date cell in the table row
                dates = ""
                try:
                    date_el = link.evaluate_handle(
                        """el => {
                            let row = el.closest('tr');
                            if (row) {
                                let dateSpan = row.querySelector('td.date span.date, td.date .date');
                                if (dateSpan) return dateSpan;
                                let dateTd = row.querySelector('td.date');
                                if (dateTd) return dateTd;
                            }
                            let card = el.closest('[class*="card"]');
                            if (card) {
                                let dateEl = card.querySelector('[class*="date"]');
                                if (dateEl) return dateEl;
                            }
                            return el.parentElement.parentElement;
                        }"""
                    )
                    if date_el and date_el.as_element():
                        date_text = date_el.as_element().inner_text().strip()
                        # Remove "Date:" label if present
                        date_text = re.sub(r"^Date:\s*", "", date_text, flags=re.IGNORECASE)
                        date_match = re.search(
                            r"(\d{1,2}\s+\w{3}\s*(?:-|to)\s*\d{1,2}\s+\w{3}(?:\s+\d{4})?)",
                            date_text,
                        )
                        if date_match:
                            dates = date_match.group(1).strip()
                except Exception:
                    pass

                # Extract category/tier from the sibling category cell
                cat_text = ""
                try:
                    cat_el = link.evaluate_handle(
                        """el => {
                            let row = el.closest('tr');
                            if (row) {
                                let catSpan = row.querySelector('td.category span.category, td.category .category');
                                if (catSpan) return catSpan;
                                let catTd = row.querySelector('td.category');
                                if (catTd) return catTd;
                            }
                            return null;
                        }"""
                    )
                    if cat_el and cat_el.as_element():
                        cat_text = cat_el.as_element().inner_text().strip()
                        cat_text = re.sub(r"^Category:\s*", "", cat_text, flags=re.IGNORECASE).strip()
                except Exception:
                    pass

                # Skip tournaments without dates (junk links from page header/sidebar)
                if not dates:
                    continue

                # Filter by date range
                start_dt, _ = _parse_date_range(dates)
                if start_dt:
                    if start_dt < cutoff_start or start_dt > cutoff_end:
                        continue

                # Parse tournament name into city + tier prefix
                city, tier_prefix = _parse_tournament_name(text)
                # Use category cell as fallback for tier prefix
                if not tier_prefix and cat_text:
                    tier_prefix = cat_text.upper()

                # Skip tournaments without a valid tier prefix (e.g., Juniors, Wheelchair)
                if not tier_prefix:
                    continue

                full_tier = f"ITF {tier_prefix}"

                tournaments.append({
                    "name": city,                # "San Diego, CA" (Title Case)
                    "tier_prefix": tier_prefix,  # "W100"
                    "full_tier": full_tier,       # "ITF W100"
                    "itf_url": href,
                    "dates": dates,
                })

        except Exception as e:
            print(f"    Calendar page failed for {target:%Y-%m}: {e}")
            continue

        time.sleep(2)  # Rate limiting between calendar pages

    return tournaments


def _parse_itf_official_tables(page, tournament: dict, gender: str) -> list[dict]:
    """Parse acceptance list tables from the official ITF website.

    Tables have columns: POSITION, PLAYER, ATP/WTA RANKING, ITF RANKING, ...
    PLAYER cell format: "COUNTRY_CODE\\nPlayer Name"
    """
    entries = []

    tables = page.query_selector_all("table")
    section_order = ["Main Draw", "Qualifying", "Alternates"]
    section_idx = 0

    for table in tables:
        rows = table.query_selector_all("tr")
        if len(rows) < 2:
            continue

        header_row = rows[0]
        header_cells = header_row.query_selector_all("th, td")
        header_texts = [c.inner_text().strip().upper() for c in header_cells]

        if "PLAYER" not in header_texts:
            continue

        player_col = header_texts.index("PLAYER")
        rank_col = -1
        info_col = -1
        for i, h in enumerate(header_texts):
            if ("ATP" in h or "WTA" in h) and "RANKING" in h:
                rank_col = i
            elif h == "INFORMATION":
                info_col = i

        # Detect section from preceding heading text on the page
        detected_section = ""
        try:
            heading_el = table.evaluate_handle(
                """el => {
                    let prev = el.previousElementSibling;
                    for (let i = 0; i < 5 && prev; i++) {
                        let txt = prev.innerText.trim().toUpperCase();
                        if (txt.includes('MAIN DRAW')) return prev;
                        if (txt.includes('QUALIFYING')) return prev;
                        if (txt.includes('ALTERNATE')) return prev;
                        if (txt.includes('WITHDRAWAL')) return prev;
                        prev = prev.previousElementSibling;
                    }
                    return null;
                }"""
            )
            if heading_el and heading_el.as_element():
                heading_text = heading_el.as_element().inner_text().strip().upper()
                if "WITHDRAWAL" in heading_text:
                    detected_section = "Withdrawals"
                elif "MAIN DRAW" in heading_text:
                    detected_section = "Main Draw"
                elif "QUALIFYING" in heading_text:
                    detected_section = "Qualifying"
                elif "ALTERNATE" in heading_text:
                    detected_section = "Alternates"
        except Exception:
            pass

        if detected_section:
            section = detected_section
        else:
            section = section_order[section_idx] if section_idx < len(section_order) else "Alternates"
        section_idx += 1

        # Skip the Withdrawals table entirely — these are not active entries
        if section == "Withdrawals":
            continue

        for row in rows[1:]:
            cells = row.query_selector_all("td")
            if len(cells) <= player_col:
                continue

            player_text = cells[player_col].inner_text().strip()
            if not player_text:
                continue

            withdrawn = False
            if info_col >= 0 and len(cells) > info_col:
                info_text = cells[info_col].inner_text().strip()
                if info_text.startswith("W "):
                    withdrawn = True

            parts = player_text.split("\n")
            if len(parts) >= 2:
                country = parts[0].strip()
                name = parts[1].strip()
            else:
                country = ""
                name = player_text.strip()

            if not name or not re.search(r"[A-Za-z]", name):
                continue

            # Skip placeholder entries like "(Special Exempt, if needed)"
            if name.startswith("("):
                continue

            # Normalize ALL CAPS names
            name = _normalize_player_name(name)

            atp_rank = 0
            if rank_col >= 0 and len(cells) > rank_col:
                rank_text = cells[rank_col].inner_text().strip()
                if rank_text.isdigit():
                    atp_rank = int(rank_text)

            entries.append({
                "tournament": tournament["name"],
                "tier": tournament.get("full_tier", "ITF"),
                "week": tournament.get("dates", ""),
                "section": section,
                "player_name": name,
                "player_rank": atp_rank,
                "player_country": country,
                "withdrawn": withdrawn,
                "gender": gender,
                "source": "ITFEntries",
            })

    return entries


def _worker_scrape_batch(tournaments: list[dict], gender: str, worker_id: int) -> list[dict]:
    """Worker function: launches its own Playwright browser and scrapes a batch."""
    all_entries = []
    cookies_dismissed = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            for t in tournaments:
                try:
                    url = t["itf_url"].rstrip("/")
                    if not url.endswith("/acceptance-list"):
                        url += "/acceptance-list"

                    page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT)
                    page.wait_for_load_state("networkidle", timeout=config.PLAYWRIGHT_TIMEOUT)
                    time.sleep(1)

                    if not cookies_dismissed:
                        try:
                            decline_btn = page.query_selector('button:has-text("Decline")')
                            if decline_btn and decline_btn.is_visible():
                                decline_btn.click()
                                time.sleep(0.5)
                                cookies_dismissed = True
                        except Exception:
                            pass

                    entries = _parse_itf_official_tables(page, t, gender)
                    all_entries.extend(entries)

                    time.sleep(1.5)  # Rate limiting between tournaments

                except Exception:
                    continue
        finally:
            browser.close()

    return all_entries


def _scrape_gender(gender: str, limit: int = 0) -> tuple[list[dict], dict]:
    """Scrape ITF tournaments for a given gender.

    Returns:
        (ranked_entries, raw_itf_data):
        - ranked_entries: entries with player_rank > 0 (for main pipeline)
        - raw_itf_data: dict keyed by composite key with full entry lists
    """
    if not _playwright_available:
        print("  Playwright not installed. Skipping ITF entries.")
        print("  Install: pip install playwright && python -m playwright install chromium")
        return [], {}

    gender_label = "Men" if gender == "M" else "Women"
    print(f"Scraping ITF Entries ({gender_label})...")

    # Step 1: Discover tournaments from calendar
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            tournaments = _discover_tournaments_from_calendar(page, gender)
        finally:
            browser.close()

    print(f"  Found {len(tournaments)} {gender_label.lower()}'s tournaments in date range")

    if limit > 0:
        tournaments = tournaments[:limit]
        print(f"  Limited to {len(tournaments)} tournaments")

    if not tournaments:
        return [], {}

    # Step 2: Scrape acceptance lists concurrently
    num_workers = min(CONCURRENT_WORKERS, len(tournaments))
    batch_size = (len(tournaments) + num_workers - 1) // num_workers
    batches = []
    for i in range(0, len(tournaments), batch_size):
        batches.append(tournaments[i:i + batch_size])

    print(f"  Scraping with {num_workers} concurrent browsers...")

    all_entries = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(_worker_scrape_batch, batch, gender, idx): idx
            for idx, batch in enumerate(batches)
        }

        completed = 0
        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                batch_entries = future.result()
                all_entries.extend(batch_entries)
                completed += 1
                batch = batches[batch_idx]
                print(f"  Batch {completed}/{len(batches)} done: "
                      f"{len(batch_entries)} entries from {len(batch)} tournaments")
            except Exception as e:
                print(f"  Batch {batch_idx} failed: {e}")

    # Step 3: Split into ranked (for pipeline) and raw (for ITF page)
    ranked_entries = [e for e in all_entries if e["player_rank"] > 0]

    # Group all entries by tournament for the ITF page
    raw_itf_data = {}
    tourn_entries = defaultdict(list)
    tourn_meta = {}

    for entry in all_entries:
        t_name = entry["tournament"]
        t_tier = entry.get("tier", "ITF")
        week = _normalize_week(entry.get("week", ""))
        # Key format must match frontend buildItfKey():
        # city.lower() + "|" + tier.lower() + "|" + gender.lower() + "|" + week.lower()
        t_key = f"{t_name.lower()}|{t_tier.lower()}|{gender_label.lower()}|{week.lower()}"

        if t_key not in tourn_meta:
            tourn_meta[t_key] = {
                "name": t_name,
                "tier": t_tier,
                "gender": gender_label,
                "week": week,
                "dates": entry.get("week", ""),
            }

        tourn_entries[t_key].append({
            "n": entry["player_name"],
            "r": entry["player_rank"],
            "c": entry["player_country"],
            "s": entry["section"],
            "w": entry["withdrawn"],
        })

    for t_key, players in tourn_entries.items():
        # Deduplicate by name+section
        seen = {}
        deduped = []
        for p in players:
            pkey = (p["n"].lower(), p["s"])
            if pkey not in seen:
                seen[pkey] = p
                deduped.append(p)
            else:
                # Prefer entry with rank
                if p["r"] > 0 and seen[pkey]["r"] == 0:
                    seen[pkey]["r"] = p["r"]
                if p["c"] and not seen[pkey]["c"]:
                    seen[pkey]["c"] = p["c"]

        # Sort: ranked first (by rank), then unranked
        deduped.sort(key=lambda x: (x["r"] if x["r"] > 0 else 9999))

        raw_itf_data[t_key] = {
            **tourn_meta[t_key],
            "players": deduped,
        }

    print(f"  Total: {len(all_entries)} entries ({len(ranked_entries)} ranked) "
          f"from {len(raw_itf_data)} tournaments")
    return ranked_entries, raw_itf_data


def scrape_men(limit: int = 0) -> tuple[list[dict], dict]:
    """Scrape ITF men's entry lists."""
    return _scrape_gender("M", limit)


def scrape_women(limit: int = 0) -> tuple[list[dict], dict]:
    """Scrape ITF women's entry lists."""
    return _scrape_gender("F", limit)


def scrape_all(limit: int = 0) -> tuple[list[dict], dict]:
    """Scrape both men's and women's ITF entry lists.

    Returns:
        (ranked_entries, raw_itf_data):
        - ranked_entries: entries with player_rank > 0 (for main pipeline)
        - raw_itf_data: combined dict of all tournament entry lists
    """
    men_ranked, men_raw = scrape_men(limit)
    women_ranked, women_raw = scrape_women(limit)

    combined_raw = {}
    combined_raw.update(men_raw)
    combined_raw.update(women_raw)

    return men_ranked + women_ranked, combined_raw
