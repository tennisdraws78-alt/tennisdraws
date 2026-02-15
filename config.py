import os
from dotenv import load_dotenv

load_dotenv()

# RapidAPI Tennis Live Data
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "tennisapi1.p.rapidapi.com")

# API Endpoints
ATP_RANKINGS_URL = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/atp"
WTA_RANKINGS_URL = "https://tennisapi1.p.rapidapi.com/api/tennis/rankings/wta"

# Scraper URLs
TICKTOCK_ATP_URL = "https://entries.ticktocktennis.com/atp.html"
TICKTOCK_WTA_URL = "https://entries.ticktocktennis.com/wta.html"
SPAZIOTENNIS_HUB_URL = "https://www.spaziotennis.com/trn/ent/tennis-entry-list-2026-atp-e-wta-aggiornate-tutti-i-partecipanti-e-gli-italiani-torneo-per-torneo/117667"
ITF_ENTRIES_URL = "https://itf-entries.netlify.app/"
WTA_API_URL = "https://api.wtatennis.com/tennis/tournaments/"
WTA_PLAYER_LIST_URL = "https://www.wtatennis.com/tournaments/{id}/{slug}/{year}/player-list"
WTA125_TOMIST_URL = "https://tomistgg.github.io/tenis-fem-arg/"

# Draw PDF URLs (official draw sheets with withdrawal sections)
ATP_DRAW_PDF_URL = "https://www.protennislive.com/posting/{year}/{tournament_id}/mds.pdf"
WTA_DRAW_PDF_URL = "https://wtafiles.wtatennis.com/pdf/draws/{year}/{tournament_id}/MDS.pdf"

# Scraping settings
REQUEST_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
PLAYWRIGHT_TIMEOUT = 30000  # ms

# Name matching
FUZZY_MATCH_THRESHOLD = 85
FUZZY_MATCH_STRICT_THRESHOLD = 95

# Output
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_MAX_RANK = 1500

# ── 2026 ATP Tour Calendar Metadata ──
# Keyed by canonical city name (must match TOURNAMENT_ALIASES values in html_writer.py)
# Format: (city, country, surface, dates)
ATP_CALENDAR = {
    "United Cup": ("Perth and Sydney", "Australia", "Hard", "2 Jan - 11 Jan"),
    "Brisbane": ("Brisbane", "Australia", "Hard", "5 Jan - 11 Jan"),
    "Hong Kong": ("Hong Kong", "Hong Kong", "Hard", "5 Jan - 11 Jan"),
    "Adelaide": ("Adelaide", "Australia", "Hard", "12 Jan - 17 Jan"),
    "Auckland": ("Auckland", "New Zealand", "Hard", "12 Jan - 17 Jan"),
    "Australian Open": ("Melbourne", "Australia", "Hard", "18 Jan - 1 Feb"),
    "Montpellier": ("Montpellier", "France", "Hard", "2 Feb - 8 Feb"),
    "Dallas": ("Dallas", "United States", "Hard", "9 Feb - 15 Feb"),
    "Rotterdam": ("Rotterdam", "Netherlands", "Hard", "9 Feb - 15 Feb"),
    "Buenos Aires": ("Buenos Aires", "Argentina", "Clay", "9 Feb - 15 Feb"),
    "Doha": ("Doha", "Qatar", "Hard", "16 Feb - 22 Feb"),
    "Rio de Janeiro": ("Rio de Janeiro", "Brazil", "Clay", "16 Feb - 22 Feb"),
    "Delray Beach": ("Delray Beach", "United States", "Hard", "16 Feb - 22 Feb"),
    "Acapulco": ("Acapulco", "Mexico", "Hard", "23 Feb - 28 Feb"),
    "Dubai": ("Dubai", "United Arab Emirates", "Hard", "23 Feb - 1 Mar"),
    "Santiago": ("Santiago", "Chile", "Clay", "23 Feb - 1 Mar"),
    "Indian Wells": ("Indian Wells", "United States", "Hard", "4 Mar - 15 Mar"),
    "Miami": ("Miami", "United States", "Hard", "18 Mar - 29 Mar"),
    "Bucharest": ("Bucharest", "Romania", "Clay", "30 Mar - 5 Apr"),
    "Houston": ("Houston", "United States", "Clay", "30 Mar - 5 Apr"),
    "Marrakech": ("Marrakech", "Morocco", "Clay", "30 Mar - 5 Apr"),
    "Monte Carlo": ("Monte-Carlo", "Monaco", "Clay", "5 Apr - 12 Apr"),
    "Barcelona": ("Barcelona", "Spain", "Clay", "13 Apr - 19 Apr"),
    "Munich": ("Munich", "Germany", "Clay", "13 Apr - 19 Apr"),
    "Madrid": ("Madrid", "Spain", "Clay", "22 Apr - 3 May"),
    "Rome": ("Rome", "Italy", "Clay", "6 May - 17 May"),
    "Hamburg": ("Hamburg", "Germany", "Clay", "17 May - 23 May"),
    "Geneva": ("Geneva", "Switzerland", "Clay", "17 May - 23 May"),
    "Roland Garros": ("Paris", "France", "Clay", "24 May - 7 Jun"),
    "Stuttgart": ("Stuttgart", "Germany", "Grass", "8 Jun - 14 Jun"),
    "'s-Hertogenbosch": ("'s-Hertogenbosch", "Netherlands", "Grass", "8 Jun - 14 Jun"),
    "Halle": ("Halle", "Germany", "Grass", "15 Jun - 21 Jun"),
    "London": ("London", "Great Britain", "Grass", "15 Jun - 21 Jun"),
    "Mallorca": ("Mallorca", "Spain", "Grass", "21 Jun - 27 Jun"),
    "Eastbourne": ("Eastbourne", "Great Britain", "Grass", "22 Jun - 27 Jun"),
    "Wimbledon": ("London", "Great Britain", "Grass", "29 Jun - 12 Jul"),
    "Bastad": ("Bastad", "Sweden", "Clay", "13 Jul - 19 Jul"),
    "Gstaad": ("Gstaad", "Switzerland", "Clay", "13 Jul - 19 Jul"),
    "Umag": ("Umag", "Croatia", "Clay", "13 Jul - 19 Jul"),
    "Kitzbuhel": ("Kitzbuhel", "Austria", "Clay", "20 Jul - 26 Jul"),
    "Estoril": ("Estoril", "Portugal", "Clay", "20 Jul - 26 Jul"),
    "Washington": ("Washington", "United States", "Hard", "27 Jul - 2 Aug"),
    "Los Cabos": ("Los Cabos", "Mexico", "Hard", "27 Jul - 2 Aug"),
    "Montreal": ("Montreal", "Canada", "Hard", "2 Aug - 12 Aug"),
    "Cincinnati": ("Cincinnati", "United States", "Hard", "13 Aug - 23 Aug"),
    "Winston-Salem": ("Winston-Salem", "United States", "Hard", "23 Aug - 29 Aug"),
    "US Open": ("New York", "United States", "Hard", "31 Aug - 13 Sep"),
    "Chengdu": ("Chengdu", "China", "Hard", "23 Sep - 29 Sep"),
    "Hangzhou": ("Hangzhou", "China", "Hard", "23 Sep - 29 Sep"),
    "Laver Cup": ("London", "Great Britain", "Hard", "25 Sep - 27 Sep"),
    "Tokyo": ("Tokyo", "Japan", "Hard", "30 Sep - 6 Oct"),
    "Beijing": ("Beijing", "China", "Hard", "30 Sep - 6 Oct"),
    "Shanghai": ("Shanghai", "China", "Hard", "7 Oct - 18 Oct"),
    "Almaty": ("Almaty", "Kazakhstan", "Hard", "19 Oct - 25 Oct"),
    "Brussels": ("Brussels", "Belgium", "Hard", "19 Oct - 25 Oct"),
    "Lyon": ("Lyon", "France", "Hard", "19 Oct - 25 Oct"),
    "Basel": ("Basel", "Switzerland", "Hard", "26 Oct - 1 Nov"),
    "Vienna": ("Vienna", "Austria", "Hard", "26 Oct - 1 Nov"),
    "Paris": ("Paris", "France", "Hard", "2 Nov - 8 Nov"),
    "Stockholm": ("Stockholm", "Sweden", "Hard", "8 Nov - 14 Nov"),
    "ATP Finals": ("Turin", "Italy", "Hard", "15 Nov - 22 Nov"),
}
