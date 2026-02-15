"""Scraper for official draw PDFs — ATP (protennislive.com) and WTA (wtafiles.wtatennis.com).

Fetches main-draw PDF sheets for active tournaments and extracts the
"Withdrawals" section at the bottom.  Each withdrawal includes the player
name and, when available, the reason (e.g. "left knee injury").

ATP format:  F. Marozsan ()   or   A. Vukic (shoulder)
WTA format:  B. Krejcikova left knee injury
"""
from __future__ import annotations

import io
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pdfplumber

import config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# Tournament discovery
# ---------------------------------------------------------------------------

# ATP tournament ID ranges to scan.  protennislive.com doesn't expose an
# index, so we use HEAD requests (fast) to probe known ranges.
# Main-tour IDs cluster in 300–520; Challengers scatter across many ranges.
ATP_ID_RANGES = [
    range(300, 520),       # Main tour (250/500/1000)
    range(1200, 1300),     # Challengers
    range(2200, 2300),     # Challengers
    range(2780, 2850),     # Challengers
    range(2900, 2980),     # Challengers
    range(3050, 3100),     # Challengers
    range(9100, 9200),     # Challengers
    range(9400, 9500),     # Challengers
    range(9600, 9650),     # Challengers
]


def _discover_atp_pdf_ids(year: int) -> list[int]:
    """Probe protennislive.com to find which ATP tournament PDFs exist."""
    all_ids = []
    for r in ATP_ID_RANGES:
        all_ids.extend(r)

    found = []

    def _check(tid: int):
        url = config.ATP_DRAW_PDF_URL.format(year=year, tournament_id=tid)
        try:
            resp = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                cl = int(resp.headers.get("content-length", "0"))
                if cl > 5000:  # Skip tiny/empty files
                    return tid
        except requests.RequestException:
            pass
        return None

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_check, tid): tid for tid in all_ids}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                found.append(result)

    found.sort()
    return found


def _discover_wta_tournaments(year: int) -> list[dict]:
    """Get WTA tournament list from the official API (same as wta_official.py)."""
    today = datetime.now()
    # Look back 2 weeks and forward 6 weeks
    start = today - timedelta(weeks=2)
    end = today + timedelta(weeks=6)

    params = {
        "from": start.strftime("%Y-%m-%d"),
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
        print(f"  Error fetching WTA calendar for draw PDFs: {e}")
        return []

    tournaments = []
    for t in data.get("content", []):
        tg = t.get("tournamentGroup", {})
        tid = tg.get("id")
        if not tid:
            continue

        city = t.get("city", "")
        level = t.get("level", "")
        start_date = t.get("startDate", "")
        status = t.get("status", "")

        week = ""
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                week = f"{dt.strftime('%b')} {dt.day}"
            except ValueError:
                week = ""

        tournaments.append({
            "id": tid,
            "name": city.title(),
            "tier": level,
            "week": week,
            "status": status,
        })

    return tournaments


# ---------------------------------------------------------------------------
# PDF downloading & text extraction
# ---------------------------------------------------------------------------

def _download_pdf(url: str) -> bytes | None:
    """Download a PDF, returning raw bytes or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > 5000:
            return resp.content
    except requests.RequestException:
        pass
    return None


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF (last page usually has withdrawals)."""
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
        # Check last page first (most common location), then all pages
        texts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
        return "\n".join(texts)
    except Exception:
        return ""


def _extract_tournament_info(pdf_text: str) -> dict:
    """Extract tournament name, location, and dates from PDF header lines."""
    lines = pdf_text.split("\n")[:5]
    name = lines[0].strip() if lines else "Unknown"
    location = lines[1].strip() if len(lines) > 1 else ""

    # Extract dates like "9 February — 15 February 2026"
    # or "February 8-14 2026"
    week = ""
    for line in lines[:4]:
        m = re.search(r"(\d+)\s+(January|February|March|April|May|June|July|August|September|October|November|December)", line)
        if m:
            day = m.group(1)
            month = m.group(2)[:3]
            week = f"{month} {day}"
            break
        m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)", line)
        if m:
            month = m.group(1)[:3]
            day = m.group(2)
            week = f"{month} {day}"
            break

    return {"name": name, "location": location, "week": week}


# ---------------------------------------------------------------------------
# Withdrawal parsing
# ---------------------------------------------------------------------------

def _parse_atp_withdrawals(text: str) -> list[dict]:
    """Parse ATP withdrawal section.

    ATP format in the bottom-right area of the draw PDF:
        Withdrawals          Retirements/W.O.
        F. Marozsan ()       T. Seyboth Wild (Right leg)
        A. Vukic (shoulder)

    The text is extracted as a single line mixing columns, e.g.:
        "Last Direct Acceptance Seeded Players Alternates/Lucky Losers Withdrawals Retirements/W.O."
        "Roberto Bautista Agut - 90 Player Rank T. Boogaard (LL) F. Marozsan () "
        "ATP Supervisor 1 de Minaur, Alex 6 H. Medjedovic (LL) A. Vukic (shoulder)"

    We look for patterns like "X. Name (reason)" after "Withdrawals" header.
    """
    withdrawals = []

    # Find the withdrawal section - look for the "Withdrawals" header line
    lines = text.split("\n")
    wd_start = -1
    for i, line in enumerate(lines):
        if re.search(r"Withdrawal", line, re.IGNORECASE):
            wd_start = i
            break

    if wd_start < 0:
        return []

    # Collect all text after the "Withdrawals" header
    wd_text = "\n".join(lines[wd_start:])

    # ATP withdrawal format: "Initial. Surname (reason)" or "Initial. Surname ()"
    # Also handles: "C. Garin (Illness)" and compound names "T. Seyboth Wild (Right leg)"
    # Pattern: letter followed by dot, space, then name, then parenthesized reason
    pattern = r"([A-Z][a-z]?\.\s+[A-Z][A-Za-z' -]+?)\s*\(([^)]*)\)"

    for m in re.finditer(pattern, wd_text):
        raw_name = m.group(1).strip()
        reason = m.group(2).strip()

        # Skip lucky losers / alternates which also use (LL) format
        if reason.upper() in ("LL", "ALT", "SE", "WC", "Q"):
            continue

        # Clean up the name: "A. Vukic" → "A. Vukic"
        # Remove any trailing numbers (rank) that might have attached
        raw_name = re.sub(r"\s+\d+$", "", raw_name)

        withdrawals.append({
            "player_name": raw_name,
            "reason": reason if reason else "",
        })

    return withdrawals


def _parse_wta_withdrawals(pdf_bytes: bytes) -> list[dict]:
    """Parse WTA withdrawal section using positional word extraction.

    WTA draw PDFs have columnar layout at the bottom:
        Withdrawals              Retirements
        B. Krejcikova left knee  E. Raducanu illness
        P. Badosa right hip      Ka. Pliskova right knee

    Plain text extraction mixes columns, so we use pdfplumber word
    positions to isolate the Withdrawals column (between its header
    x-position and the Retirements header x-position).

    Each line is then parsed as: "Initial. Surname reason_text"
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except Exception:
        return []

    withdrawals = []

    # Check each page (usually last page has withdrawals)
    for page in reversed(pdf.pages):
        words = page.extract_words()
        if not words:
            continue

        # Find "Withdrawals" header position
        wd_headers = [w for w in words if "Withdrawal" in w["text"]]
        if not wd_headers:
            continue

        wd_x = wd_headers[0]["x0"]
        wd_y = wd_headers[0]["top"]

        # Find "Retirements" header to define right boundary of WD column
        ret_headers = [w for w in words if "Retirement" in w["text"]]
        ret_x = ret_headers[0]["x0"] if ret_headers else page.width

        # Extract words in the Withdrawals column below the header
        col_words = [
            w for w in words
            if w["x0"] >= wd_x - 5
            and w["x1"] < ret_x - 5
            and w["top"] > wd_y + 2
        ]
        col_words.sort(key=lambda w: (round(w["top"], 0), w["x0"]))

        # Group words into lines by Y position
        from itertools import groupby
        for _y, grp in groupby(col_words, key=lambda w: round(w["top"], 0)):
            line_words = sorted(grp, key=lambda w: w["x0"])
            line_text = " ".join(w["text"] for w in line_words).strip()

            # Stop at Lucky Losers / Alternates section
            if re.search(r"Lucky|Alternate", line_text, re.IGNORECASE):
                break

            # Skip empty or header-like lines
            if not line_text or line_text.lower().startswith("player"):
                continue

            # Parse "Initial. Surname reason_text"
            # Strategy: split line into words, find where name ends and
            # reason begins.  Name = initial + capitalized surname words.
            # Reason starts at the first lowercase word (or known keyword
            # like Illness, Injury) after at least one surname word.
            line_text = re.sub(r"\s*\[WC\]\s*", " ", line_text).strip()

            m = re.match(r"([A-Z][a-z]{0,3}\.)\s+(.+)", line_text)
            if not m:
                continue

            initial = m.group(1)
            rest = m.group(2).strip()

            # Split rest into words and find where surname ends
            words_rest = rest.split()
            name_parts = []
            reason_parts = []
            found_reason = False

            for wi, word in enumerate(words_rest):
                if found_reason:
                    reason_parts.append(word)
                elif wi == 0:
                    # First word is always part of surname
                    name_parts.append(word)
                elif word[0].isupper() and not found_reason:
                    # Could be continuation of surname OR start of reason
                    # Check if it looks like a reason keyword
                    reason_keywords = [
                        "Illness", "Injury", "Right", "Left", "Low",
                        "Change", "Sickness", "Abdominal", "Adductor",
                        "Stomach", "Viral", "Personal",
                    ]
                    if word in reason_keywords:
                        found_reason = True
                        reason_parts.append(word)
                    else:
                        name_parts.append(word)
                else:
                    # Lowercase word = start of reason
                    found_reason = True
                    reason_parts.append(word)

            raw_name = initial + " " + " ".join(name_parts)
            reason = " ".join(reason_parts)

            # Clean reason: remove trailing numbers, "replaced seed" lines
            reason = re.sub(r"\s+\d+$", "", reason)
            if "replaced seed" in reason.lower():
                reason = ""

            # Remove any trailing numbers from name
            raw_name = re.sub(r"\s+\d+$", "", raw_name)

            withdrawals.append({
                "player_name": raw_name,
                "reason": reason,
            })

        # Found withdrawals on this page, no need to check others
        if withdrawals:
            break

    return withdrawals


# ---------------------------------------------------------------------------
# Main scrape functions
# ---------------------------------------------------------------------------

def _determine_tier(pdf_text: str, tournament_name: str) -> str:
    """Determine the tournament tier from PDF content."""
    text_lower = pdf_text.lower()
    name_lower = tournament_name.lower()

    # Check for tier indicators
    if "challenge" in text_lower[:500] or "challenge" in name_lower:
        return "ATP Challenger"
    if "itf" in text_lower[:200]:
        return "ITF"

    # Check prize money for tier hints
    if any(kw in name_lower for kw in ["indian wells", "miami", "madrid", "rome", "shanghai", "montreal", "toronto", "cincinnati"]):
        return "ATP 1000"

    # Default by looking at prize money
    m = re.search(r"(?:USD|EUR|EURO|AUD)\s*[\d,\s]+(\d{3})", pdf_text[:500])
    if m:
        # Rough heuristic based on prize money
        amount_str = re.sub(r"[^\d]", "", pdf_text[:500].split(m.group())[0].split("$")[-1] if "$" in pdf_text[:500] else "0")
        try:
            amount = int(amount_str) if amount_str else 0
        except ValueError:
            amount = 0

    return "ATP"


def scrape_atp() -> list[dict]:
    """Scrape ATP draw PDFs for withdrawal information."""
    print("Scraping ATP Draw PDFs...")
    year = datetime.now().year

    # Discover which PDFs exist
    print("  Discovering ATP tournament PDFs...")
    atp_ids = _discover_atp_pdf_ids(year)
    print(f"  Found {len(atp_ids)} ATP draw PDFs")

    entries = []
    for i, tid in enumerate(atp_ids):
        url = config.ATP_DRAW_PDF_URL.format(year=year, tournament_id=tid)
        pdf_bytes = _download_pdf(url)
        if not pdf_bytes:
            continue

        text = _extract_pdf_text(pdf_bytes)
        if not text:
            continue

        info = _extract_tournament_info(text)
        withdrawals = _parse_atp_withdrawals(text)

        if withdrawals:
            tier = _determine_tier(text, info["name"])
            print(f"  [{i+1}/{len(atp_ids)}] {info['name']}: {len(withdrawals)} withdrawal(s)")

            for wd in withdrawals:
                entries.append({
                    "tournament": info["name"],
                    "tier": tier,
                    "week": info["week"],
                    "section": "Main Draw",
                    "player_name": wd["player_name"],
                    "player_rank": 0,
                    "player_country": "",
                    "withdrawn": True,
                    "reason": wd["reason"],
                    "gender": "M",
                    "source": "OfficialDraw",
                })

        if i < len(atp_ids) - 1 and (i + 1) % 5 == 0:
            time.sleep(0.5)  # Be gentle

    print(f"  Total ATP draw withdrawals: {len(entries)}")
    return entries


def scrape_wta() -> list[dict]:
    """Scrape WTA draw PDFs for withdrawal information."""
    print("Scraping WTA Draw PDFs...")
    year = datetime.now().year

    tournaments = _discover_wta_tournaments(year)
    # Only process tournaments that are in progress or recently finished
    active = [
        t for t in tournaments
        if t["status"] in ("inProgress", "past")
    ]
    print(f"  Found {len(active)} active/recent WTA tournaments with draws")

    entries = []
    for i, t in enumerate(active):
        url = config.WTA_DRAW_PDF_URL.format(year=year, tournament_id=t["id"])
        pdf_bytes = _download_pdf(url)
        if not pdf_bytes:
            continue

        withdrawals = _parse_wta_withdrawals(pdf_bytes)

        if withdrawals:
            print(f"  [{i+1}/{len(active)}] {t['name']} ({t['tier']}): {len(withdrawals)} withdrawal(s)")

            for wd in withdrawals:
                entries.append({
                    "tournament": t["name"],
                    "tier": t["tier"],
                    "week": t["week"],
                    "section": "Main Draw",
                    "player_name": wd["player_name"],
                    "player_rank": 0,
                    "player_country": "",
                    "withdrawn": True,
                    "reason": wd["reason"],
                    "gender": "F",
                    "source": "OfficialDraw",
                })

        if i < len(active) - 1:
            time.sleep(0.5)

    print(f"  Total WTA draw withdrawals: {len(entries)}")
    return entries


def scrape_all() -> list[dict]:
    """Scrape both ATP and WTA draw PDFs for withdrawals."""
    atp = scrape_atp()
    time.sleep(1)
    wta = scrape_wta()
    return atp + wta
