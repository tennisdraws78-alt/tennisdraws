"""Generate a self-contained HTML dashboard from player-tournament match data."""
from __future__ import annotations

import os
import json
import re
import unicodedata
from datetime import datetime
import config


MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _extract_start_date(week: str) -> tuple:
    """Extract the start (month, day) from any week label format.

    Returns (month_num, day_num) or None if unparseable.

    Handles:
    - "Feb 16" (TickTock) → (2, 16)
    - "Feb 9-15" (Spazio) → (2, 9)
    - "Feb 23 - Mar 1" (Spazio) → (2, 23)
    - "09 Feb to 15 Feb 2026" (ITF) → (2, 9)
    - "Mar 4-14" (Spazio) → (3, 4)
    """
    if not week:
        return None

    # "Mon DD" or "Mon DD-DD" or "Mon DD - Mon DD": "Feb 16", "Feb 9-15", "Feb 23 - Mar 1"
    m = re.match(r"(\w{3})\s+(\d{1,2})", week)
    if m and m.group(1) in MONTHS:
        return (MONTHS[m.group(1)], int(m.group(2)))

    # "DD Mon to DD Mon YYYY" format from ITF: "09 Feb to 15 Feb 2026"
    m = re.match(r"(\d{1,2})\s+(\w{3})\s+to", week)
    if m and m.group(2) in MONTHS:
        return (MONTHS[m.group(2)], int(m.group(1)))

    return None


def _normalize_week(week: str) -> str:
    """Normalize a week label to canonical 'Mon DD' form using its start date.

    This merges overlapping labels from different sources:
    - TickTock "Feb 16" + Spazio "Feb 16-22" → both become "Feb 16"
    """
    date = _extract_start_date(week)
    if date is None:
        return week  # keep as-is
    month_num, day = date
    # Reverse lookup month name
    month_name = next(k for k, v in MONTHS.items() if v == month_num)
    return f"{month_name} {day}"


def _merge_close_weeks(weeks: set) -> dict:
    """Build a mapping from each week label to a canonical one.

    Weeks whose start dates are within 5 days of each other get merged
    to the earliest one. This handles cases like TickTock "Mar 2" and
    Spazio "Mar 4" referring to the same tournament week.

    Returns dict mapping original week string -> canonical week string.
    """
    # Sort weeks by their date value
    dated = []
    undated = []
    for w in weeks:
        date = _extract_start_date(w)
        if date:
            dated.append((date[0] * 100 + date[1], date, w))
        else:
            undated.append(w)

    dated.sort()

    # Group weeks within 5 days of each other
    merge_map = {}
    groups = []
    for sort_key, date, label in dated:
        # Check if this fits in the last group
        if groups and sort_key - groups[-1][0] <= 5:
            groups[-1][1].append(label)
        else:
            groups.append((sort_key, [label]))

    # Map each label in a group to the first (earliest) label
    for _, labels in groups:
        canonical = labels[0]
        for label in labels:
            merge_map[label] = canonical

    for w in undated:
        merge_map[w] = w

    return merge_map


# Map official / sponsor tournament names → canonical city-based names.
# Keys must be lowercase.  Add new aliases as tournaments change sponsors.
TOURNAMENT_ALIASES = {
    # ── Grand Slams ──
    "australian open": "Australian Open",
    "roland garros": "Roland Garros",
    "wimbledon": "Wimbledon",
    "the championships, wimbledon": "Wimbledon",
    "us open": "US Open",

    # ── ATP Tour (250 / 500 / 1000) ──
    "united cup": "United Cup",
    "brisbane international presented by anz": "Brisbane",
    "brisbane international": "Brisbane",
    "bank of china hong kong tennis open": "Hong Kong",
    "adelaide international": "Adelaide",
    "asb classic": "Auckland",
    "open occitanie": "Montpellier",
    "dallas open": "Dallas",
    "nexo dallas open": "Dallas",
    "abn amro open": "Rotterdam",
    "ieb+ argentina open": "Buenos Aires",
    "argentina open": "Buenos Aires",
    "qatar exxonmobil open": "Doha",
    "qatar open": "Doha",
    "rio open presented by claro": "Rio de Janeiro",
    "rio open": "Rio de Janeiro",
    "brasil open": "Rio de Janeiro",
    "delray beach open": "Delray Beach",
    "abierto mexicano telcel presentado por hsbc": "Acapulco",
    "abierto mexicano de tenis": "Acapulco",
    "mexican open": "Acapulco",
    "dubai duty free tennis championships": "Dubai",
    "bci seguros chileopen": "Santiago",
    "bnp paribas open": "Indian Wells",
    "miami open presented by itau": "Miami",
    "miami open": "Miami",
    "tiriac open presented by unicredit bank": "Bucharest",
    "tiriac open": "Bucharest",
    "fayez sarofim & co. u.s. men's clay court championship": "Houston",
    "grand prix hassan ii": "Marrakech",
    "rolex monte-carlo masters": "Monte Carlo",
    "monte-carlo masters": "Monte Carlo",
    "barcelona open banc sabadell": "Barcelona",
    "barcelona open": "Barcelona",
    "bmw open by bitpanda": "Munich",
    "bmw open": "Munich",
    "mutua madrid open": "Madrid",
    "internazionali bnl d'italia": "Rome",
    "internazionali d'italia": "Rome",
    "bitpanda hamburg open": "Hamburg",
    "gonet geneva open": "Geneva",
    "boss open": "Stuttgart",
    "libema open": "'s-Hertogenbosch",
    "terra wortmann open": "Halle",
    "halle open": "Halle",
    "hsbc championships": "London",
    "cinch championships": "London",
    "the hsbc championships": "London",
    "mallorca championships presented by ecotrans group": "Mallorca",
    "mallorca championships": "Mallorca",
    "lexus eastbourne open": "Eastbourne",
    "nordea open": "Bastad",
    "efg swiss open gstaad": "Gstaad",
    "plava laguna croatia open": "Umag",
    "generali open": "Kitzbuhel",
    "millennium estoril open": "Estoril",
    "mubadala citi dc open": "Washington",
    "mubadala dc open": "Washington",
    "mifel tennis open by telcel oppo": "Los Cabos",
    "national bank open presented by rogers": "Montreal",
    "national bank open": "Montreal",
    "canadian open": "Montreal",
    "cincinnati open": "Cincinnati",
    "western & southern open": "Cincinnati",
    "winston-salem open": "Winston-Salem",
    "chengdu open": "Chengdu",
    "lynk & co hangzhou open": "Hangzhou",
    "laver cup": "Laver Cup",
    "kinoshita group japan open tennis championships": "Tokyo",
    "kinoshita group japan open": "Tokyo",
    "china open": "Beijing",
    "rolex shanghai masters": "Shanghai",
    "shanghai masters": "Shanghai",
    "almaty open": "Almaty",
    "bnp paribas fortis european open": "Brussels",
    "grand prix auvergne-rhone-alpes": "Lyon",
    "swiss indoors basel": "Basel",
    "erste bank open": "Vienna",
    "rolex paris masters": "Paris",
    "bnp paribas nordic open": "Stockholm",
    "nitto atp finals": "ATP Finals",
    "next gen atp finals": "Next Gen Finals",

    # ── WTA Tour (250 / 500 / 1000) ──
    "qatar totalenergies open": "Doha",
    "qatar totalenergies open 2026": "Doha",
    "mubadala abu dhabi open presented by abu dhabi sports council": "Abu Dhabi",
    "mubadala abu dhabi open": "Abu Dhabi",
    "ostrava open": "Ostrava",
    "transylvania open powered by kaufland": "Cluj-Napoca",
    "transylvania open": "Cluj-Napoca",
    "merida open": "Merida",
    "mérida open": "Merida",
    "atx open": "Austin",
    "credit one charleston open": "Charleston",
    "copa colsanitas": "Bogota",
    "upper austria ladies linz": "Linz",
    "porsche tennis grand prix": "Stuttgart",
    "open capfinances rouen métropole": "Rouen",
    "open capfinances rouen metropole": "Rouen",
    "internationaux de strasbourg": "Strasbourg",
    "grand prix de son altesse royale la princesse lalla meryem": "Rabat",
    "vanda pharmaceuticals berlin tennis open": "Berlin",
    "lexus nottingham open": "Nottingham",
    "bad homburg open powered by solarwatt": "Bad Homburg",
    "bad homburg open": "Bad Homburg",
    "unicredit iasi open": "Iasi",
    "livesport prague open 2026": "Prague",
    "livesport prague open": "Prague",
    "msc hamburg ladies open": "Hamburg",
    "tennis in the land powered by rocket": "Cleveland",
    "tennis in the land": "Cleveland",
    "abierto gnp seguros": "Monterrey",
    "guadalajara open presented by santander": "Guadalajara",
    "guadalajara open": "Guadalajara",
    "sp open": "Sao Paulo",
    "singapore tennis open": "Singapore",
    "korea open": "Seoul",
    "wuhan open": "Wuhan",
    "ningbo open": "Ningbo",
    "toray pan pacific open tennis": "Tokyo",
    "toray pan pacific open": "Tokyo",
    "guangzhou open": "Guangzhou",
    "chennai open": "Chennai",
    "jiangxi open": "Jiujiang",
    "prudential hong kong tennis open": "Hong Kong",
    "wta finals riyadh": "WTA Finals",
    "wta finals": "WTA Finals",
    "hobart international": "Hobart",

    # ── ATP Challenger ──
    "bengaluru open": "Bengaluru",
    "workday canberra international": "Canberra",
    "bnc tennis open": "Noumea",
    "bangkok open 1": "Bangkok",
    "bangkok open 2": "Bangkok 2",
    "lexus nottingham challenger": "Nottingham",
    "aat challenger edicion tca": "Buenos Aires CH",
    "lexus glasgow challenger": "Glasgow",
    "indoor oeiras open 1": "Oeiras",
    "oeiras indoor 2": "Oeiras 2",
    "oeiras open 3": "Oeiras 3",
    "itajai open": "Itajai",
    "soma bay open": "Soma Bay",
    "novaworld phan thiet challenger 1": "Phan Thiet",
    "novaworld phan thiet challenger 2": "Phan Thiet 2",
    "bahrain open tennis challenger": "Bahrain",
    "open quimper bretagne occidentale": "Quimper",
    "better buzz coffee san diego open": "San Diego",
    "dove men+care concepción": "Concepcion",
    "dove men+care concepcion": "Concepcion",
    "quini 6 rosario challenger presentado por el gobierno de santa fe": "Rosario",
    "brisbane tennis international #1": "Brisbane",
    "brisbane tennis international #2": "Brisbane 2",
    "brisbane tennis international": "Brisbane",
    "cleveland open": "Cleveland",
    "tenerife challenger 1": "Tenerife",
    "tenerife challenger 2": "Tenerife 2",
    "tenerife challenger": "Tenerife",
    "koblenz tennis open": "Koblenz",
    "start romagna cup -1° trofeo città di cesenatico": "Cesenatico",
    "terega open pau pyrenees": "Pau",
    "terega open pau pyrénées": "Pau",
    "steve carter baton rouge challenger": "Baton Rouge",
    "baton rouge challenger": "Baton Rouge",
    "new delhi challenger": "New Delhi",
    "iloilo challenger": "Iloilo",
    "genting highlands challenger": "Genting Highlands",
    "munich ultra paraguay open": "Asuncion",
    "morelia open": "Morelia",
    "napoli tennis cup": "Naples",
    "iii challenger montemar ene construccion": "Montemar",
    "yokkaichi challenger": "Yokkaichi",
    "split open": "Split",
    "open menorca": "Menorca",
    "banorte tennis open": "San Luis Potosi",
    "são léo open de tênis": "Sao Leopoldo",
    "sao leo open de tenis": "Sao Leopoldo",
    "open città della disfida - barletta": "Barletta",
    "koyushokucho miyazaki challenger": "Miyazaki",
    "mexico city open": "Mexico City",
    "atkinsons monza open": "Monza",
    "campeonato internacional de tenis": "Campinas",
    "elizabeth moore sarasota open": "Sarasota",
    "wuning 1": "Wuning",
    "wuning 2": "Wuning 2",
    "busan open": "Busan",
    "tallahassee tennis challenger": "Tallahassee",
    "yucatan open": "Merida CH",
    "savannah challenger": "Savannah",
    "shymkent 1": "Shymkent",
    "shymkent 2": "Shymkent 2",
    "cote d'ivoire open 1": "Abidjan",
    "cote d'ivoire open 2": "Abidjan 2",
    "danube upper austria open": "Mauthausen",
    "salzburg open": "Salzburg",
    "challenger aix-en-provence": "Aix-en-Provence",
    "uams health little rock open": "Little Rock",
    "internazionali di tennis - citta'di vicenza": "Vicenza",
    "centurion 1": "Centurion",
    "centurion 2": "Centurion 2",
    "centurion 3": "Centurion 3",
    "internazionali di tennis città di perugia": "Perugia",
    "lexus birmingham open": "Birmingham",
    "neckarcup 2.0": "Heilbronn",
    "unicredit czech open": "Prostejov",
    "texas spine and joint men's championship": "Tyler",
    "bratislava open": "Bratislava",
    "lexus ilkley open": "Ilkley",
    "open sopra steria": "Lyon CH",
    "enea poznan open": "Poznan",
    "intaro open": "Targu Mures",
    "aspria tennis cup trofeo bcs": "Milan",
    "ion tiriac challenger": "Brasov",
    "internationaux de tennis de troyes": "Troyes",
    "hall of fame open": "Newport",
    "brawo open": "Braunschweig",
    "citta' di trieste": "Trieste",
    "lincoln challenger": "Lincoln",
    "open ciudad de pozoblanco": "Pozoblanco",
    "cranbrook tennis classic": "Bloomfield Hills",
    "open castilla y leon villa de el espinar": "Segovia",
    "internazionali di tennis san marino open": "San Marino",
    "svijany open": "Liberec",
    "cary tennis classic": "Cary",
    "royan atlantique open": "Royan",
    # Truncated scraper names (scrapers sometimes cut off long names)
    "quini 6 rosario challenger presentado por el gobierno de": "Rosario",
    "start romagna cup -1° trofeo città di": "Cesenatico",
    "start romagna cup -1° trofeo citta di": "Cesenatico",
    "start romagna cup": "Cesenatico",
    "brasília": "Brasilia",
    "new dehli": "New Delhi",
    "maha open": "Pune",
    "challenger città di lugano": "Lugano",
    "challenger citta di lugano": "Lugano",
    "open saint-brieuc armor agglomération": "St. Brieuc",
    "open saint-brieuc armor agglomeration": "St. Brieuc",
    "st brieuc": "St. Brieuc",
    "costa cálida region de murcia": "Murcia",
    "costa calida region de murcia": "Murcia",
    "košice": "Kosice",
    "vancouver": "Vancouver",
    "durham, nc": "Durham",
    "durham nc": "Durham",

    # ── WTA 125 ──
    "oeiras 1 jamor indoor": "Oeiras",
    "oeiras 2 jamor indoor": "Oeiras 2",
    "oeiras jamor ladies open": "Oeiras 3",
    "oeiras open ceto": "Oeiras 4",
    "open arena les sables d'olonne": "Les Sables d'Olonne",
    "les sables d'olonne": "Les Sables d'Olonne",
    "dow tennis classic": "Midland",
    "megasaray hotels open": "Antalya",
    "austin 125": "Austin 125",
    "dubrovnik open": "Dubrovnik",
    "catalonia open solgironès": "La Bisbal d'Emporda",
    "catalonia open solgirones": "La Bisbal d'Emporda",
    "l'open 35 de saint malo": "Saint Malo",
    "istanbul open": "Istanbul",
    "parma ladies open presented by iren": "Parma",
    "parma ladies open": "Parma",
    "trophée clarins": "Paris 125",
    "trophee clarins": "Paris 125",
    "open delle puglie trofeo": "Foggia",
    "makarska open": "Makarska",
    "l&t mumbai open": "Mumbai",
}


def _strip_accents(text: str) -> str:
    """'Mérida' → 'Merida', 'Três-Rivières' → 'Tres-Rivieres'"""
    nfkd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfkd if unicodedata.category(c) != 'Mn')


def _normalize_tournament_name(name: str) -> str:
    """Normalize tournament name so entries from different sources merge.

    Handles three source formats:
    - Spazio:    "ATP DOHA", "Baton Rouge (CH 50)"  (ALL CAPS / city + CH level)
    - TickTock:  "Doha", "Steve Carter Baton Rouge Challenger"  (official names)
    - Draw PDFs: "ABN AMRO Open", "Nexo Dallas Open"  (sponsor names from PDF header)

    Strategy:
    1. Check alias table for exact match (sponsor → city)
    2. Strip ATP/WTA prefix and title-case ALL-CAPS names
    3. For Challengers with "(CH ##)" suffix, extract city name for alias lookup
    """
    if not name:
        return name

    # Check alias table first (case-insensitive, accent-insensitive)
    alias = TOURNAMENT_ALIASES.get(_strip_accents(name).lower().strip())
    if alias:
        return alias

    # Strip "ATP " or "WTA " prefix
    stripped = re.sub(r"^(?:ATP|WTA)\s+", "", name)

    # If the result is ALL-CAPS (and not a short acronym), title-case it
    if stripped == stripped.upper() and len(stripped) > 3:
        # Title case, but handle "DE", "DI" etc. properly
        words = stripped.split()
        result = []
        for i, w in enumerate(words):
            if i > 0 and w.upper() in ("DE", "DI", "DA", "DO", "DEL", "LA", "LE"):
                result.append(w.lower())
            else:
                result.append(w.capitalize())
        stripped = " ".join(result)

    # Strip "(CH ##)" suffix from Challenger names so they merge with
    # TickTock names that don't include the level.  The tier badge already
    # shows the level (e.g. "ATP Challenger 50").
    ch_match = re.match(r"^(.+?)\s*\(CH\s*\d+\)$", stripped)
    if ch_match:
        stripped = ch_match.group(1).strip()

    # Check alias again after stripping/title-casing
    alias2 = TOURNAMENT_ALIASES.get(_strip_accents(stripped).lower().strip())
    if alias2:
        return alias2

    return _strip_accents(stripped)


def _week_sort_key(week: str) -> tuple:
    """Return a sort key for week values to order chronologically."""
    if not week:
        return (2, 0)

    date = _extract_start_date(week)
    if date:
        return (0, date[0] * 100 + date[1])

    # Fallback "Week N" (shouldn't appear anymore but just in case)
    m = re.match(r"Week\s+(\d+)", week)
    if m:
        return (1, int(m.group(1)))

    return (2, 0)


def write_html(
    players: list[dict],
    player_entry_map: dict[str, list[dict]],
    filename: str = None,
) -> str:
    """Write the player-tournament mapping to a self-contained HTML dashboard.

    Args:
        players: List of ranked players
        player_entry_map: Dict mapping "name|gender" -> list of entry dicts
        filename: Output filename (default: auto-generated with timestamp)

    Returns:
        Path to the generated HTML file.
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_{timestamp}.html"

    filepath = os.path.join(config.OUTPUT_DIR, filename)

    # Build data for JSON embedding — two passes:
    # Pass 1: collect all normalized weeks, then merge close ones
    # Pass 2: apply merged week labels to entries

    # Pass 1: collect all unique normalized weeks
    all_raw_weeks = set()
    for player in players:
        player_key = f"{player['name']}|{player.get('gender', '')}"
        for entry in player_entry_map.get(player_key, []):
            week_val = entry.get("week", "")
            week_val = re.sub(r"\s*\u2754\s*$", "", week_val)
            week_val = re.sub(r"\s*\?\s*$", "", week_val).strip()
            week_val = _normalize_week(week_val)
            if week_val:
                all_raw_weeks.add(week_val)

    # Merge weeks within 5 days of each other (e.g. "Mar 2" + "Mar 4" → "Mar 2")
    week_merge_map = _merge_close_weeks(all_raw_weeks)

    # Pass 2: build player data with merged weeks
    players_data = []
    all_weeks = set()

    for player in sorted(players, key=lambda p: (p.get("gender", ""), p.get("rank", 9999))):
        player_key = f"{player['name']}|{player.get('gender', '')}"
        entries = player_entry_map.get(player_key, [])
        gender_label = "Men" if player.get("gender") == "M" else "Women"

        # Deduplicate entries by normalized (tournament, section, week)
        # This merges "ATP DOHA" (Spazio) + "Doha" (TickTock) into one entry
        seen = set()
        deduped = []
        for entry in entries:
            week_val = entry.get("week", "")
            # Clean up emoji/question marks from ITF week labels
            week_val = re.sub(r"\s*\u2754\s*$", "", week_val)
            week_val = re.sub(r"\s*\?\s*$", "", week_val).strip()
            # Normalize + merge close weeks
            week_val = _normalize_week(week_val)
            week_val = week_merge_map.get(week_val, week_val)

            tourn_name = _normalize_tournament_name(entry.get("tournament", ""))
            section = entry.get("section", "")

            dedup_key = (tourn_name, section, week_val)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            if week_val:
                all_weeks.add(week_val)
            deduped.append({
                "tournament": tourn_name,
                "tier": entry.get("tier", ""),
                "section": section,
                "week": week_val,
                "source": entry.get("source", ""),
                "withdrawn": bool(entry.get("withdrawn")),
            })

        # Sort entries by week
        deduped.sort(key=lambda e: _week_sort_key(e["week"]))

        players_data.append({
            "rank": player.get("rank", 9999),
            "name": player["name"],
            "gender": gender_label,
            "country": player.get("country_code", ""),
            "entries": deduped,
        })

    # Sort weeks chronologically
    sorted_weeks = sorted(all_weeks, key=_week_sort_key)

    # Compute stats
    total_players = len(players_data)
    players_with_entries = sum(1 for p in players_data if p["entries"])
    total_entries = sum(len(p["entries"]) for p in players_data)
    unique_tournaments = len(set(
        e["tournament"] for p in players_data for e in p["entries"]
    ))

    stats = {
        "totalPlayers": total_players,
        "playersWithEntries": players_with_entries,
        "totalEntries": total_entries,
        "uniqueTournaments": unique_tournaments,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    json_data = json.dumps(players_data, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)
    weeks_json = json.dumps(sorted_weeks, ensure_ascii=False)

    html_content = HTML_TEMPLATE.replace("__PLAYERS_JSON__", json_data)
    html_content = html_content.replace("__STATS_JSON__", stats_json)
    html_content = html_content.replace("__WEEKS_JSON__", weeks_json)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\nHTML dashboard written to: {filepath}")
    print(f"  Total players: {total_players}")
    print(f"  Players with entries: {players_with_entries}/{total_players}")
    print(f"  Total tournament entries: {total_entries}")
    print(f"  Unique tournaments: {unique_tournaments}")

    return filepath


# ---------------------------------------------------------------------------
# HTML Template — self-contained with inline CSS and JS
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tennis Entry List Tracker</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg-primary: #0f1923;
    --bg-secondary: #1a2634;
    --bg-tertiary: #243447;
    --bg-hover: #2a3e55;
    --text-primary: #e8edf2;
    --text-secondary: #8899aa;
    --text-muted: #5a6d7f;
    --border-color: #2a3e55;
    --accent-blue: #4da6ff;
    --accent-pink: #ff6b9d;
    --accent-green: #36d399;
    --accent-yellow: #f7c948;
    --accent-red: #ef4444;
    --header-bg: #0a1118;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.5;
    min-height: 100vh;
}

/* Header */
header {
    background: var(--header-bg);
    padding: 20px 24px 16px;
    position: sticky;
    top: 0;
    z-index: 100;
    border-bottom: 1px solid var(--border-color);
}

.header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 8px;
}

header h1 {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: var(--text-primary);
}

header h1 .subtle {
    font-weight: 400;
    opacity: 0.4;
    font-size: 13px;
    margin-left: 10px;
}

.stats-bar {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}

.stat-pill {
    background: var(--bg-tertiary);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;
}

.stat-pill strong {
    color: var(--text-primary);
    font-weight: 700;
    margin-right: 4px;
}

.controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.search-wrapper {
    flex: 1;
    min-width: 220px;
    position: relative;
}

.search-wrapper svg {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    color: var(--text-muted);
    pointer-events: none;
}

#searchInput {
    width: 100%;
    padding: 9px 14px 9px 38px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-size: 14px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    outline: none;
    transition: border-color 0.2s;
}

#searchInput::placeholder { color: var(--text-muted); }
#searchInput:focus { border-color: var(--accent-blue); }

.filter-group { display: flex; gap: 4px; }

.filter-group button {
    padding: 7px 16px;
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--text-secondary);
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.15s;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.filter-group button:hover { background: var(--bg-tertiary); color: var(--text-primary); }

.filter-group button.active {
    background: var(--accent-blue);
    color: #fff;
    border-color: var(--accent-blue);
}

.filter-group.view-toggle button.active {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--text-muted);
}

/* View toggle */
.view-toggle { margin-left: auto; }

/* Entries-only filter */
.toggle-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}

.toggle-label input { display: none; }

.toggle-switch {
    width: 32px;
    height: 18px;
    border-radius: 9px;
    background: var(--bg-tertiary);
    position: relative;
    transition: background 0.2s;
}

.toggle-switch::after {
    content: "";
    position: absolute;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--text-muted);
    top: 2px;
    left: 2px;
    transition: all 0.2s;
}

.toggle-label input:checked + .toggle-switch {
    background: var(--accent-blue);
}

.toggle-label input:checked + .toggle-switch::after {
    left: 16px;
    background: #fff;
}

/* Main content */
main {
    padding: 0;
    overflow-x: auto;
}

#resultsCount {
    font-size: 12px;
    color: var(--text-muted);
    padding: 10px 24px;
}

/* ===== TABLE VIEW ===== */
.table-container {
    width: 100%;
    overflow-x: auto;
}

.player-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    table-layout: auto;
}

.player-table thead {
    position: sticky;
    top: 0;
    z-index: 10;
}

.player-table th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 2px solid var(--border-color);
    white-space: nowrap;
    position: sticky;
    top: 0;
}

.player-table th.week-col {
    text-align: center;
    min-width: 140px;
}

.player-table th.rk-col { width: 55px; text-align: center; }
.player-table th.player-col { min-width: 180px; }
.player-table th.ctry-col { width: 55px; text-align: center; }

.player-table tbody tr {
    border-bottom: 1px solid var(--border-color);
    transition: background 0.1s;
}

.player-table tbody tr:hover { background: var(--bg-hover); }
.player-table tbody tr.gender-men { border-left: 3px solid var(--accent-blue); }
.player-table tbody tr.gender-women { border-left: 3px solid var(--accent-pink); }
.player-table tbody tr.no-entries { opacity: 0.4; }
.player-table tbody tr.no-entries:hover { opacity: 0.65; }

.player-table td {
    padding: 8px 12px;
    vertical-align: middle;
}

.player-table td.rk-cell {
    text-align: center;
    font-weight: 700;
    color: var(--text-muted);
    font-size: 12px;
}

.player-table td.player-cell {
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
}

.player-table td.ctry-cell {
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: 0.5px;
}

.player-table td.week-cell {
    text-align: center;
    padding: 6px 8px;
}

.week-cell .empty-dash {
    color: var(--text-muted);
    opacity: 0.25;
    font-size: 16px;
}

/* Tournament badges */
.tournament-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 4px;
    margin: 2px 2px;
    white-space: nowrap;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
}

/* Tier colors — inspired by TickTock style */
.badge-1000 {
    background: #7c3aed;
    color: #f5f3ff;
}

.badge-500 {
    background: #dc2626;
    color: #fef2f2;
}

.badge-250 {
    background: #2563eb;
    color: #eff6ff;
}

.badge-challenger {
    background: #059669;
    color: #ecfdf5;
}

.badge-125 {
    background: #d97706;
    color: #fffbeb;
}

.badge-itf {
    background: #64748b;
    color: #f1f5f9;
}

.badge-other {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
}

/* Withdrawn badge overlay */
.tournament-badge.withdrawn {
    opacity: 0.5;
    text-decoration: line-through;
    position: relative;
}

.wd-tag {
    display: inline-block;
    background: var(--accent-red);
    color: #fff;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
    vertical-align: middle;
    text-decoration: none;
    letter-spacing: 0.5px;
}

/* Section indicator */
.section-indicator {
    font-size: 9px;
    opacity: 0.7;
    display: block;
    margin-top: 1px;
    letter-spacing: 0.3px;
}

/* ===== CARD VIEW ===== */
.cards-container {
    padding: 0 24px 40px;
}

.player-card {
    background: var(--bg-secondary);
    border-radius: 8px;
    margin-bottom: 6px;
    border-left: 3px solid var(--text-muted);
    overflow: hidden;
    transition: all 0.15s;
}

.player-card:hover { background: var(--bg-tertiary); }
.player-card[data-gender="Men"] { border-left-color: var(--accent-blue); }
.player-card[data-gender="Women"] { border-left-color: var(--accent-pink); }
.player-card.no-entries-card { opacity: 0.35; }
.player-card.no-entries-card:hover { opacity: 0.55; }

.card-header {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    cursor: pointer;
    user-select: none;
    gap: 8px;
}

.card-rank {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-muted);
    min-width: 44px;
}

.card-name {
    font-size: 14px;
    font-weight: 600;
    flex: 1;
    color: var(--text-primary);
}

.card-country {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}

.card-entry-count {
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
}

.card-entry-count.has { color: var(--accent-green); font-weight: 600; }

.card-expand {
    font-size: 10px;
    color: var(--text-muted);
    transition: transform 0.2s;
    margin-left: 4px;
}

.player-card.expanded .card-expand { transform: rotate(180deg); }

.card-entries {
    display: none;
    border-top: 1px solid var(--border-color);
    padding: 0 14px 14px;
}

.player-card.expanded .card-entries { display: block; }

.card-week-group { margin-top: 10px; }

.card-week-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 4px 0;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 6px;
}

.card-entry-row {
    display: flex;
    align-items: center;
    padding: 5px 0;
    gap: 8px;
    font-size: 13px;
    border-bottom: 1px solid rgba(42, 62, 85, 0.3);
}

.card-entry-row:last-child { border-bottom: none; }

.card-entry-row .tournament-badge { margin: 0; }

.card-entry-row .entry-section {
    font-size: 11px;
    color: var(--text-muted);
}

.card-entry-row .entry-source {
    font-size: 11px;
    color: var(--text-muted);
    margin-left: auto;
    opacity: 0.6;
}

.card-no-entries {
    padding: 14px 0;
    color: var(--text-muted);
    font-size: 13px;
    text-align: center;
    font-style: italic;
}

/* No results */
.no-results {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
    font-size: 15px;
}

/* Footer */
footer {
    text-align: center;
    padding: 24px;
    color: var(--text-muted);
    font-size: 11px;
    border-top: 1px solid var(--border-color);
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* Responsive */
@media (max-width: 768px) {
    header { padding: 14px 16px 12px; }
    .header-top { flex-direction: column; align-items: flex-start; }
    .stats-bar { width: 100%; }
    .controls { flex-direction: column; }
    .search-wrapper { width: 100%; }
    .filter-group { width: 100%; justify-content: stretch; }
    .filter-group button { flex: 1; }
    .view-toggle { margin-left: 0; width: 100%; }
    .view-toggle button { flex: 1; }
    #resultsCount { padding: 10px 16px; }
    .cards-container { padding: 0 16px 40px; }
}
</style>
</head>
<body>

<header>
    <div class="header-top">
        <h1>Tennis Entry List Tracker <span class="subtle" id="genDate"></span></h1>
        <div class="stats-bar">
            <div class="stat-pill"><strong id="statPlayers">-</strong> Players</div>
            <div class="stat-pill"><strong id="statMatched">-</strong> With Entries</div>
            <div class="stat-pill"><strong id="statEntries">-</strong> Entries</div>
            <div class="stat-pill"><strong id="statTournaments">-</strong> Tournaments</div>
        </div>
    </div>
    <div class="controls">
        <div class="search-wrapper">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>
            <input type="text" id="searchInput" placeholder="Search player or tournament..." autocomplete="off">
        </div>
        <div class="filter-group gender-tabs">
            <button class="active" data-gender="all">All</button>
            <button data-gender="Men">ATP</button>
            <button data-gender="Women">WTA</button>
        </div>
        <label class="toggle-label">
            <input type="checkbox" id="entriesOnly">
            <span class="toggle-switch"></span>
            With entries only
        </label>
        <div class="filter-group view-toggle">
            <button class="active" data-view="table">Table</button>
            <button data-view="cards">Cards</button>
        </div>
    </div>
</header>

<main>
    <div id="resultsCount"></div>
    <div id="playerList"></div>
</main>

<footer>
    Tennis Entry List Tracker &mdash; Data from TickTock Tennis, Spazio Tennis, ITF Entries
</footer>

<script>
var PLAYERS = __PLAYERS_JSON__;
var STATS = __STATS_JSON__;
var WEEKS = __WEEKS_JSON__;

var currentGender = "all";
var currentSearch = "";
var currentView = "table";
var entriesOnly = false;
var debounceTimer = null;

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("statPlayers").textContent = STATS.totalPlayers.toLocaleString();
    document.getElementById("statMatched").textContent = STATS.playersWithEntries.toLocaleString();
    document.getElementById("statEntries").textContent = STATS.totalEntries.toLocaleString();
    document.getElementById("statTournaments").textContent = STATS.uniqueTournaments.toLocaleString();
    document.getElementById("genDate").textContent = STATS.generatedAt;

    document.getElementById("searchInput").addEventListener("input", function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function() {
            currentSearch = e.target.value.trim();
            applyFilters();
        }, 150);
    });

    document.getElementById("searchInput").addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            this.value = "";
            currentSearch = "";
            applyFilters();
        }
    });

    document.querySelectorAll(".gender-tabs button").forEach(function(btn) {
        btn.addEventListener("click", function() {
            document.querySelectorAll(".gender-tabs button").forEach(function(b) { b.classList.remove("active"); });
            this.classList.add("active");
            currentGender = this.getAttribute("data-gender");
            applyFilters();
        });
    });

    document.querySelectorAll(".view-toggle button").forEach(function(btn) {
        btn.addEventListener("click", function() {
            document.querySelectorAll(".view-toggle button").forEach(function(b) { b.classList.remove("active"); });
            this.classList.add("active");
            currentView = this.getAttribute("data-view");
            applyFilters();
        });
    });

    document.getElementById("entriesOnly").addEventListener("change", function() {
        entriesOnly = this.checked;
        applyFilters();
    });

    applyFilters();
});

function applyFilters() {
    var searchLower = currentSearch.toLowerCase();
    var filtered = PLAYERS.filter(function(p) {
        var genderMatch = currentGender === "all" || p.gender === currentGender;
        if (!genderMatch) return false;
        if (entriesOnly && p.entries.length === 0) return false;
        if (!searchLower) return true;
        // Search in player name and tournament names
        if (p.name.toLowerCase().indexOf(searchLower) !== -1) return true;
        for (var i = 0; i < p.entries.length; i++) {
            if (p.entries[i].tournament.toLowerCase().indexOf(searchLower) !== -1) return true;
        }
        return false;
    });
    if (currentView === "table") {
        renderTable(filtered);
    } else {
        renderCards(filtered);
    }
}

function esc(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function getBadgeClass(tier) {
    if (!tier) return "badge-other";
    var t = tier.toLowerCase();
    if (t.indexOf("1000") !== -1) return "badge-1000";
    if (t.indexOf("500") !== -1) return "badge-500";
    if (t.indexOf("250") !== -1) return "badge-250";
    if (t.indexOf("challenger") !== -1) return "badge-challenger";
    if (t.indexOf("125") !== -1) return "badge-125";
    if (t.indexOf("itf") !== -1) return "badge-itf";
    return "badge-other";
}

function shortSection(section) {
    if (!section) return "";
    var s = section.toLowerCase();
    if (s.indexOf("main") !== -1) return "MD";
    if (s === "qualifying") return "Q";
    if (s.indexOf("qualifying") !== -1 && s.indexOf("alt") !== -1) return "QA";
    if (s.indexOf("qualifying") !== -1 && s.indexOf("wc") !== -1) return "QWC";
    if (s.indexOf("alternate") !== -1) return "ALT";
    if (s.indexOf("wild") !== -1) return "WC";
    return section.substring(0, 3).toUpperCase();
}

function normalizeWeek(w) {
    if (!w) return "";
    return w.replace(/\s*\u2754\s*$/,"").replace(/\s*\?\s*$/,"").trim();
}

// Group a player's entries by normalized week
function entriesByWeek(entries) {
    var map = {};
    for (var i = 0; i < entries.length; i++) {
        var w = normalizeWeek(entries[i].week) || "__none__";
        if (!map[w]) map[w] = [];
        map[w].push(entries[i]);
    }
    return map;
}

/* ==================== TABLE VIEW ==================== */
function renderTable(players) {
    var container = document.getElementById("playerList");
    var countEl = document.getElementById("resultsCount");
    countEl.textContent = "Showing " + players.length + " player" + (players.length !== 1 ? "s" : "");

    if (players.length === 0) {
        container.innerHTML = '<div class="no-results">No players found.</div>';
        return;
    }

    var html = ['<div class="table-container"><table class="player-table"><thead><tr>'];
    html.push('<th class="rk-col">RK</th>');
    html.push('<th class="player-col">Player</th>');
    html.push('<th class="ctry-col">CTRY</th>');

    for (var wi = 0; wi < WEEKS.length; wi++) {
        var weekLabel = WEEKS[wi];
        // Shorten for display: "Feb 9-15" -> "FEB 9", "Feb 16" -> "FEB 16"
        var shortWeek = weekLabel.replace(/(\w{3})\s+(\d{1,2}).*/, function(m, mon, day) {
            return mon.toUpperCase() + " " + day;
        });
        // Handle ITF format "09 Feb to 15 Feb 2026"
        shortWeek = shortWeek.replace(/(\d{1,2})\s+(\w{3})\s+to.*/, function(m, day, mon) {
            return mon.toUpperCase() + " " + day;
        });
        html.push('<th class="week-col">' + esc(shortWeek) + '</th>');
    }
    html.push('</tr></thead><tbody>');

    for (var pi = 0; pi < players.length; pi++) {
        var p = players[pi];
        var hasEntries = p.entries.length > 0;
        var genderClass = p.gender === "Men" ? "gender-men" : "gender-women";
        var rowClass = genderClass + (hasEntries ? "" : " no-entries");

        html.push('<tr class="' + rowClass + '">');
        html.push('<td class="rk-cell">' + p.rank + '</td>');
        html.push('<td class="player-cell">' + esc(p.name) + '</td>');
        html.push('<td class="ctry-cell">' + esc(p.country) + '</td>');

        var byWeek = entriesByWeek(p.entries);

        for (var wi = 0; wi < WEEKS.length; wi++) {
            var wk = WEEKS[wi];
            var wEntries = byWeek[wk];

            html.push('<td class="week-cell">');
            if (wEntries && wEntries.length > 0) {
                for (var ei = 0; ei < wEntries.length; ei++) {
                    var e = wEntries[ei];
                    var badgeCls = getBadgeClass(e.tier);
                    var wdCls = e.withdrawn ? " withdrawn" : "";
                    var sec = shortSection(e.section);
                    var secHtml = (sec && sec !== "MD") ? '<span class="section-indicator">' + sec + '</span>' : "";
                    html.push('<span class="tournament-badge ' + badgeCls + wdCls + '" title="' +
                        esc(e.tournament) + ' | ' + esc(e.tier) + ' | ' + esc(e.section) + ' | ' + esc(e.source) + '">' +
                        esc(e.tournament) +
                        (e.withdrawn ? ' <span class="wd-tag">WD</span>' : '') +
                        secHtml +
                        '</span>');
                }
            } else {
                html.push('<span class="empty-dash">&mdash;</span>');
            }
            html.push('</td>');
        }

        // Entries with no matching week column
        var noWeek = byWeek["__none__"];
        // We don't add an extra column; these are rare edge cases

        html.push('</tr>');
    }

    html.push('</tbody></table></div>');
    container.innerHTML = html.join("");
}

/* ==================== CARD VIEW ==================== */
function renderCards(players) {
    var container = document.getElementById("playerList");
    var countEl = document.getElementById("resultsCount");
    countEl.textContent = "Showing " + players.length + " player" + (players.length !== 1 ? "s" : "");

    if (players.length === 0) {
        container.innerHTML = '<div class="no-results">No players found.</div>';
        return;
    }

    var html = ['<div class="cards-container">'];

    for (var i = 0; i < players.length; i++) {
        var p = players[i];
        var entryCount = p.entries.length;
        var hasEntries = entryCount > 0;
        var active = p.entries.filter(function(e) { return !e.withdrawn; }).length;
        var wd = entryCount - active;

        var countText = "";
        if (hasEntries) {
            countText = active + " tournament" + (active !== 1 ? "s" : "");
            if (wd > 0) countText += " + " + wd + " WD";
        } else {
            countText = "No entries";
        }

        html.push('<div class="player-card ' + (!hasEntries ? 'no-entries-card' : '') +
            '" data-gender="' + esc(p.gender) + '">');
        html.push('<div class="card-header" onclick="toggleCard(this.parentNode)">');
        html.push('<span class="card-rank">#' + p.rank + '</span>');
        html.push('<span class="card-name">' + esc(p.name) + '</span>');
        html.push('<span class="card-country">' + esc(p.country) + '</span>');
        html.push('<span class="card-entry-count ' + (hasEntries ? 'has' : '') + '">' + countText + '</span>');
        html.push('<span class="card-expand">&#9660;</span>');
        html.push('</div>');

        html.push('<div class="card-entries">');
        if (hasEntries) {
            // Group by week
            var groups = {};
            var order = [];
            for (var j = 0; j < p.entries.length; j++) {
                var w = normalizeWeek(p.entries[j].week) || "Upcoming";
                if (!groups[w]) { groups[w] = []; order.push(w); }
                groups[w].push(p.entries[j]);
            }
            for (var gi = 0; gi < order.length; gi++) {
                var wLabel = order[gi];
                var wEntries = groups[wLabel];
                html.push('<div class="card-week-group">');
                html.push('<div class="card-week-label">' + esc(wLabel) + '</div>');
                for (var ei = 0; ei < wEntries.length; ei++) {
                    var e = wEntries[ei];
                    var badgeCls = getBadgeClass(e.tier);
                    var wdCls = e.withdrawn ? " withdrawn" : "";
                    html.push('<div class="card-entry-row">');
                    html.push('<span class="tournament-badge ' + badgeCls + wdCls + '">' +
                        esc(e.tournament) + (e.withdrawn ? ' <span class="wd-tag">WD</span>' : '') + '</span>');
                    html.push('<span class="entry-section">' + esc(e.section) + '</span>');
                    html.push('<span class="entry-source">' + esc(e.source) + '</span>');
                    html.push('</div>');
                }
                html.push('</div>');
            }
        } else {
            html.push('<div class="card-no-entries">No upcoming tournament entries found</div>');
        }
        html.push('</div></div>');
    }

    html.push('</div>');
    container.innerHTML = html.join("");
}

function toggleCard(card) {
    card.classList.toggle("expanded");
}
</script>

</body>
</html>
"""
