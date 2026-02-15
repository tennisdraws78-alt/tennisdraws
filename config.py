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
# Format: (city, country, surface, dates, tier)
ATP_CALENDAR = {
    "United Cup": ("Perth and Sydney", "Australia", "Hard", "2 Jan - 11 Jan", "United Cup"),
    "Brisbane": ("Brisbane", "Australia", "Hard", "5 Jan - 11 Jan", "ATP 250"),
    "Hong Kong": ("Hong Kong", "Hong Kong", "Hard", "5 Jan - 11 Jan", "ATP 250"),
    "Adelaide": ("Adelaide", "Australia", "Hard", "12 Jan - 17 Jan", "ATP 250"),
    "Auckland": ("Auckland", "New Zealand", "Hard", "12 Jan - 17 Jan", "ATP 250"),
    "Australian Open": ("Melbourne", "Australia", "Hard", "18 Jan - 1 Feb", "Grand Slam"),
    "Montpellier": ("Montpellier", "France", "Hard", "2 Feb - 8 Feb", "ATP 250"),
    "Dallas": ("Dallas", "United States", "Hard", "9 Feb - 15 Feb", "ATP 500"),
    "Rotterdam": ("Rotterdam", "Netherlands", "Hard", "9 Feb - 15 Feb", "ATP 500"),
    "Buenos Aires": ("Buenos Aires", "Argentina", "Clay", "9 Feb - 15 Feb", "ATP 250"),
    "Doha": ("Doha", "Qatar", "Hard", "16 Feb - 22 Feb", "ATP 500"),
    "Rio de Janeiro": ("Rio de Janeiro", "Brazil", "Clay", "16 Feb - 22 Feb", "ATP 500"),
    "Delray Beach": ("Delray Beach", "United States", "Hard", "16 Feb - 22 Feb", "ATP 250"),
    "Acapulco": ("Acapulco", "Mexico", "Hard", "23 Feb - 28 Feb", "ATP 500"),
    "Dubai": ("Dubai", "United Arab Emirates", "Hard", "23 Feb - 1 Mar", "ATP 500"),
    "Santiago": ("Santiago", "Chile", "Clay", "23 Feb - 1 Mar", "ATP 250"),
    "Indian Wells": ("Indian Wells", "United States", "Hard", "4 Mar - 15 Mar", "ATP 1000"),
    "Miami": ("Miami", "United States", "Hard", "18 Mar - 29 Mar", "ATP 1000"),
    "Bucharest": ("Bucharest", "Romania", "Clay", "30 Mar - 5 Apr", "ATP 250"),
    "Houston": ("Houston", "United States", "Clay", "30 Mar - 5 Apr", "ATP 250"),
    "Marrakech": ("Marrakech", "Morocco", "Clay", "30 Mar - 5 Apr", "ATP 250"),
    "Monte Carlo": ("Monte-Carlo", "Monaco", "Clay", "5 Apr - 12 Apr", "ATP 1000"),
    "Barcelona": ("Barcelona", "Spain", "Clay", "13 Apr - 19 Apr", "ATP 500"),
    "Munich": ("Munich", "Germany", "Clay", "13 Apr - 19 Apr", "ATP 500"),
    "Madrid": ("Madrid", "Spain", "Clay", "22 Apr - 3 May", "ATP 1000"),
    "Rome": ("Rome", "Italy", "Clay", "6 May - 17 May", "ATP 1000"),
    "Hamburg": ("Hamburg", "Germany", "Clay", "17 May - 23 May", "ATP 500"),
    "Geneva": ("Geneva", "Switzerland", "Clay", "17 May - 23 May", "ATP 250"),
    "Roland Garros": ("Paris", "France", "Clay", "24 May - 7 Jun", "Grand Slam"),
    "Stuttgart": ("Stuttgart", "Germany", "Grass", "8 Jun - 14 Jun", "ATP 250"),
    "'s-Hertogenbosch": ("'s-Hertogenbosch", "Netherlands", "Grass", "8 Jun - 14 Jun", "ATP 250"),
    "Halle": ("Halle", "Germany", "Grass", "15 Jun - 21 Jun", "ATP 500"),
    "London": ("London", "Great Britain", "Grass", "15 Jun - 21 Jun", "ATP 500"),
    "Mallorca": ("Mallorca", "Spain", "Grass", "21 Jun - 27 Jun", "ATP 250"),
    "Eastbourne": ("Eastbourne", "Great Britain", "Grass", "22 Jun - 27 Jun", "ATP 250"),
    "Wimbledon": ("London", "Great Britain", "Grass", "29 Jun - 12 Jul", "Grand Slam"),
    "Bastad": ("Bastad", "Sweden", "Clay", "13 Jul - 19 Jul", "ATP 250"),
    "Gstaad": ("Gstaad", "Switzerland", "Clay", "13 Jul - 19 Jul", "ATP 250"),
    "Umag": ("Umag", "Croatia", "Clay", "13 Jul - 19 Jul", "ATP 250"),
    "Kitzbuhel": ("Kitzbuhel", "Austria", "Clay", "20 Jul - 26 Jul", "ATP 250"),
    "Estoril": ("Estoril", "Portugal", "Clay", "20 Jul - 26 Jul", "ATP 250"),
    "Washington": ("Washington", "United States", "Hard", "27 Jul - 2 Aug", "ATP 500"),
    "Los Cabos": ("Los Cabos", "Mexico", "Hard", "27 Jul - 2 Aug", "ATP 250"),
    "Montreal": ("Montreal", "Canada", "Hard", "2 Aug - 12 Aug", "ATP 1000"),
    "Cincinnati": ("Cincinnati", "United States", "Hard", "13 Aug - 23 Aug", "ATP 1000"),
    "Winston-Salem": ("Winston-Salem", "United States", "Hard", "23 Aug - 29 Aug", "ATP 250"),
    "US Open": ("New York", "United States", "Hard", "31 Aug - 13 Sep", "Grand Slam"),
    "Chengdu": ("Chengdu", "China", "Hard", "23 Sep - 29 Sep", "ATP 250"),
    "Hangzhou": ("Hangzhou", "China", "Hard", "23 Sep - 29 Sep", "ATP 250"),
    "Laver Cup": ("London", "Great Britain", "Hard", "25 Sep - 27 Sep", "Laver Cup"),
    "Tokyo": ("Tokyo", "Japan", "Hard", "30 Sep - 6 Oct", "ATP 500"),
    "Beijing": ("Beijing", "China", "Hard", "30 Sep - 6 Oct", "ATP 500"),
    "Shanghai": ("Shanghai", "China", "Hard", "7 Oct - 18 Oct", "ATP 1000"),
    "Almaty": ("Almaty", "Kazakhstan", "Hard", "19 Oct - 25 Oct", "ATP 250"),
    "Brussels": ("Brussels", "Belgium", "Hard", "19 Oct - 25 Oct", "ATP 250"),
    "Lyon": ("Lyon", "France", "Hard", "19 Oct - 25 Oct", "ATP 250"),
    "Basel": ("Basel", "Switzerland", "Hard", "26 Oct - 1 Nov", "ATP 500"),
    "Vienna": ("Vienna", "Austria", "Hard", "26 Oct - 1 Nov", "ATP 500"),
    "Paris": ("Paris", "France", "Hard", "2 Nov - 8 Nov", "ATP 1000"),
    "Stockholm": ("Stockholm", "Sweden", "Hard", "8 Nov - 14 Nov", "ATP 250"),
    "ATP Finals": ("Turin", "Italy", "Hard", "15 Nov - 22 Nov", "ATP Finals"),
}
