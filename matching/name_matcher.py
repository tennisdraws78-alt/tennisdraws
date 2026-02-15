"""Fuzzy name matching for cross-referencing players across data sources."""
from __future__ import annotations

from unidecode import unidecode
from rapidfuzz import fuzz, process
import config


def normalize_name(name: str) -> str:
    """Normalize a player name for matching.

    - Strip accents: Djoković -> Djokovic
    - Lowercase
    - Remove hyphens and apostrophes
    - Normalize whitespace
    - Handle "Last, First" -> "first last"
    """
    if not name:
        return ""

    # Handle "LastName, FirstName" format
    if "," in name:
        parts = name.split(",", 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"

    # Strip accents
    name = unidecode(name)

    # Lowercase
    name = name.lower()

    # Remove hyphens and apostrophes
    name = name.replace("-", " ").replace("'", "").replace("'", "")

    # Normalize whitespace
    name = " ".join(name.split())

    return name


def match_player_to_entries(
    player: dict,
    entry_list: list[dict],
    threshold: int = config.FUZZY_MATCH_THRESHOLD,
) -> list[dict]:
    """Find all entry list entries that match a given ranked player.

    Uses fuzzy matching on normalized names, with country as a tiebreaker
    for borderline matches.

    Args:
        player: Dict with keys 'name', 'rank', 'gender', 'country_code'
        entry_list: List of entry dicts with 'player_name', 'player_country', 'gender'
        threshold: Minimum fuzzy match score (0-100)

    Returns:
        List of matching entry dicts (may be empty).
    """
    player_norm = normalize_name(player["name"])
    player_gender = player.get("gender", "")
    player_country = player.get("country_code", "").upper()

    matches = []

    for entry in entry_list:
        # Skip different gender
        if player_gender and entry.get("gender") and player_gender != entry["gender"]:
            continue

        entry_norm = normalize_name(entry["player_name"])

        # Quick exact match check (fast path)
        if player_norm == entry_norm:
            matches.append(entry)
            continue

        # Fuzzy match using token sort ratio (handles word order differences)
        score = fuzz.token_sort_ratio(player_norm, entry_norm)

        if score >= config.FUZZY_MATCH_STRICT_THRESHOLD:
            # High confidence match
            matches.append(entry)
        elif score >= threshold:
            # Borderline match — require country confirmation
            entry_country = entry.get("player_country", "").upper()
            if player_country and entry_country and player_country == entry_country:
                matches.append(entry)

    return matches


def build_player_entry_map(
    players: list[dict],
    entries: list[dict],
) -> dict[str, list[dict]]:
    """Build a mapping from player name to their tournament entries.

    For efficiency, pre-groups entries by gender and builds a name lookup index.

    Args:
        players: List of ranked players from API
        entries: Combined list of entries from all scrapers

    Returns:
        Dict mapping player name -> list of matching entries
    """
    # Pre-group entries by gender
    entries_by_gender = {"M": [], "F": []}
    for e in entries:
        g = e.get("gender", "")
        if g in entries_by_gender:
            entries_by_gender[g].append(e)

    # Build normalized name index for fast lookup
    # Map normalized_name -> list of entries
    name_index = {}
    for e in entries:
        norm = normalize_name(e["player_name"])
        name_index.setdefault(norm, []).append(e)

    result = {}
    total = len(players)

    for i, player in enumerate(players):
        if (i + 1) % 100 == 0:
            print(f"  Matching player {i+1}/{total}...")

        player_norm = normalize_name(player["name"])
        player_key = f"{player['name']}|{player.get('gender', '')}"

        # First try exact normalized match (fast)
        exact_matches = name_index.get(player_norm, [])
        # Filter by gender — skip entries with a known different gender
        gender = player.get("gender", "")
        exact_matches = [
            e for e in exact_matches
            if not (gender and e.get("gender") and gender != e["gender"])
        ]

        if exact_matches:
            result[player_key] = exact_matches
        else:
            # Fall back to fuzzy matching against gender-filtered entries
            gender_entries = entries_by_gender.get(gender, entries)
            fuzzy_matches = match_player_to_entries(player, gender_entries)
            result[player_key] = fuzzy_matches

    return result
