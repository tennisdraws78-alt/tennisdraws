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
