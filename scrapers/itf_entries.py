"""Scraper for ITF Men's and Women's tournament entry lists.

Two data sources:
1. itf-entries.netlify.app — React SPA with tab-separated entry data (~39 tournaments)
2. itftennis.com — Official ITF site with structured tables (~158 tournaments)

Uses Playwright for headless browser automation with concurrent scraping.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

_playwright_available = True
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    _playwright_available = False

# Map entry group prefixes to section names (netlify format)
SECTION_MAP = {
    "MD": "Main Draw",
    "Q": "Qualifying",
    "ALT": "Alternates",
}

# Number of concurrent browser workers
CONCURRENT_WORKERS = 5


def _get_tournament_list(page, gender: str) -> list[dict]:
    """Get list of tournaments from the netlify listing page.

    Each row has two links:
    1. Relative path (e.g. /tournament/M-ITF-TUR-2026-006) — for netlify data
    2. Absolute ITF URL (e.g. https://www.itftennis.com/...) — for official site data

    Only ~20% of tournaments have the netlify data; the rest point to ITF.
    """
    url_path = "men-tournaments" if gender == "M" else "women-tournaments"
    page.goto(
        f"https://itf-entries.netlify.app/{url_path}",
        timeout=config.PLAYWRIGHT_TIMEOUT,
    )
    page.wait_for_load_state("networkidle", timeout=config.PLAYWRIGHT_TIMEOUT)
    time.sleep(3)

    tournaments = []
    rows = page.query_selector_all("table tbody tr")

    for row in rows:
        links = row.query_selector_all("td a")
        if not links:
            continue

        netlify_path = ""
        itf_url = ""
        name = ""

        for link in links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()
            if href.startswith("/tournament/"):
                netlify_path = href
                name = text
            elif "itftennis.com" in href:
                itf_url = href
                if not name:
                    name = text

        if not name:
            continue

        cells = row.query_selector_all("td")
        dates = ""
        if len(cells) >= 4:
            dates = cells[3].inner_text().strip()

        tournaments.append({
            "name": name,
            "netlify_path": netlify_path,
            "itf_url": itf_url,
            "dates": dates,
        })

    return tournaments


def _parse_netlify_text(text: str, tournament: dict, gender: str) -> list[dict]:
    """Parse tournament entry list text from the netlify app.

    Entry lines are tab-separated:
    "MD DA\t1\tPlayer Name (COUNTRY)\tITF link\t278\t3.52\t\t\t1"
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    entries = []

    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue

        entry_group = parts[0].strip()

        section = None
        for prefix, section_name in SECTION_MAP.items():
            if entry_group.startswith(prefix):
                section = section_name
                break
        if not section:
            continue

        player_text = parts[2].strip()
        if player_text in ("Special exempt", "Available slot", "Qualifier", ""):
            continue

        player_match = re.match(r"^(.+?)\s*\(([A-Z]{2,3})\)\s*$", player_text)
        if player_match:
            name = player_match.group(1).strip()
            country = player_match.group(2)
        else:
            name = player_text.strip()
            country = ""

        if not name or not re.search(r"[A-Za-z]", name):
            continue

        atp_rank = 0
        if len(parts) > 4 and parts[4].strip().isdigit():
            atp_rank = int(parts[4].strip())

        entries.append({
            "tournament": tournament["name"],
            "tier": "ITF",
            "week": tournament.get("dates", ""),
            "section": section,
            "player_name": name,
            "player_rank": atp_rank,
            "player_country": country,
            "withdrawn": False,
            "gender": gender,
            "source": "ITFEntries",
        })

    return entries


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

        section = section_order[section_idx] if section_idx < len(section_order) else "Alternates"
        section_idx += 1

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

            atp_rank = 0
            if rank_col >= 0 and len(cells) > rank_col:
                rank_text = cells[rank_col].inner_text().strip()
                if rank_text.isdigit():
                    atp_rank = int(rank_text)

            entries.append({
                "tournament": tournament["name"],
                "tier": "ITF",
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
                    if t["netlify_path"]:
                        url = f"https://itf-entries.netlify.app{t['netlify_path']}"
                        page.goto(url, timeout=config.PLAYWRIGHT_TIMEOUT)
                        page.wait_for_load_state("networkidle", timeout=config.PLAYWRIGHT_TIMEOUT)
                        time.sleep(0.5)

                        text = page.inner_text("body")
                        entries = _parse_netlify_text(text, t, gender)
                        ranked = [e for e in entries if e["player_rank"] > 0]
                        all_entries.extend(ranked)

                    elif t["itf_url"]:
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
                        ranked = [e for e in entries if e["player_rank"] > 0 and not e["withdrawn"]]
                        all_entries.extend(ranked)

                except Exception:
                    continue
        finally:
            browser.close()

    return all_entries


def _scrape_gender(gender: str, limit: int = 0) -> list[dict]:
    """Scrape ITF tournaments for a given gender."""
    if not _playwright_available:
        print("  Playwright not installed. Skipping ITF entries.")
        print("  Install: pip install playwright && python -m playwright install chromium")
        return []

    gender_label = "Men" if gender == "M" else "Women"
    print(f"Scraping ITF Entries ({gender_label})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            tournaments = _get_tournament_list(page, gender)
        finally:
            browser.close()

    total_count = len(tournaments)
    # Only scrape tournaments that have netlify data (entry lists published).
    # ITF-only tournaments are future events without acceptance lists yet.
    tournaments = [t for t in tournaments if t["netlify_path"]]

    if limit > 0:
        tournaments = tournaments[:limit]
        print(f"  Scraping {len(tournaments)} {gender_label.lower()}'s tournaments (limited)")
    else:
        print(f"  Found {len(tournaments)} {gender_label.lower()}'s tournaments with entry data "
              f"(of {total_count} total)")

    if not tournaments:
        return []

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
                      f"{len(batch_entries)} ranked entries from {len(batch)} tournaments")
            except Exception as e:
                print(f"  Batch {batch_idx} failed: {e}")

    print(f"  Found {len(all_entries)} ranked {gender_label.lower()}'s ITF entries")
    return all_entries


def scrape_men(limit: int = 0) -> list[dict]:
    """Scrape ITF men's entry lists."""
    return _scrape_gender("M", limit)


def scrape_women(limit: int = 0) -> list[dict]:
    """Scrape ITF women's entry lists."""
    return _scrape_gender("F", limit)


def scrape_all(limit: int = 0) -> list[dict]:
    """Scrape both men's and women's ITF entry lists."""
    men = scrape_men(limit)
    women = scrape_women(limit)
    return men + women
