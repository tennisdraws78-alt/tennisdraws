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

# ── 2026 WTA Tour Calendar Metadata ──
# Keyed by canonical city name (must match TOURNAMENT_ALIASES values in html_writer.py)
# Format: (city, country, surface, dates, tier)
# Note: Grand Slams are in ATP_CALENDAR already; WTA-only entries here
WTA_CALENDAR = {
    # ── WTA 1000 ──
    "Doha": ("Doha", "Qatar", "Hard", "9 Feb - 15 Feb", "WTA 1000"),
    "Dubai": ("Dubai", "United Arab Emirates", "Hard", "16 Feb - 22 Feb", "WTA 1000"),
    "Indian Wells": ("Indian Wells", "United States", "Hard", "2 Mar - 15 Mar", "WTA 1000"),
    "Miami": ("Miami", "United States", "Hard", "16 Mar - 29 Mar", "WTA 1000"),
    "Madrid": ("Madrid", "Spain", "Clay", "20 Apr - 3 May", "WTA 1000"),
    "Rome": ("Rome", "Italy", "Clay", "4 May - 17 May", "WTA 1000"),
    "Montreal": ("Montreal", "Canada", "Hard", "3 Aug - 16 Aug", "WTA 1000"),
    "Cincinnati": ("Cincinnati", "United States", "Hard", "10 Aug - 23 Aug", "WTA 1000"),
    "Beijing": ("Beijing", "China", "Hard", "28 Sep - 11 Oct", "WTA 1000"),
    "Wuhan": ("Wuhan", "China", "Hard", "12 Oct - 18 Oct", "WTA 1000"),
    # ── WTA 500 ──
    "Brisbane": ("Brisbane", "Australia", "Hard", "5 Jan - 12 Jan", "WTA 500"),
    "Adelaide": ("Adelaide", "Australia", "Hard", "12 Jan - 19 Jan", "WTA 500"),
    "Abu Dhabi": ("Abu Dhabi", "United Arab Emirates", "Hard", "1 Feb - 8 Feb", "WTA 500"),
    "Charleston": ("Charleston", "United States", "Clay", "30 Mar - 5 Apr", "WTA 500"),
    "Linz": ("Linz", "Austria", "Clay", "6 Apr - 12 Apr", "WTA 500"),
    "Stuttgart": ("Stuttgart", "Germany", "Clay", "13 Apr - 19 Apr", "WTA 500"),
    "London": ("London", "Great Britain", "Grass", "8 Jun - 14 Jun", "WTA 500"),
    "Berlin": ("Berlin", "Germany", "Grass", "15 Jun - 21 Jun", "WTA 500"),
    "Bad Homburg": ("Bad Homburg", "Germany", "Grass", "22 Jun - 28 Jun", "WTA 500"),
    "Hamburg": ("Hamburg", "Germany", "Clay", "20 Jul - 26 Jul", "WTA 500"),
    "Washington": ("Washington", "United States", "Hard", "27 Jul - 2 Aug", "WTA 500"),
    "Singapore": ("Singapore", "Singapore", "Hard", "21 Sep - 27 Sep", "WTA 500"),
    "Ningbo": ("Ningbo", "China", "Hard", "19 Oct - 25 Oct", "WTA 500"),
    "Tokyo": ("Tokyo", "Japan", "Hard", "26 Oct - 1 Nov", "WTA 500"),
    # ── WTA 250 ──
    "Auckland": ("Auckland", "New Zealand", "Hard", "5 Jan - 12 Jan", "WTA 250"),
    "Hobart": ("Hobart", "Australia", "Hard", "12 Jan - 19 Jan", "WTA 250"),
    "Cluj-Napoca": ("Cluj-Napoca", "Romania", "Hard", "1 Feb - 8 Feb", "WTA 250"),
    "Ostrava": ("Ostrava", "Czech Republic", "Hard", "1 Feb - 8 Feb", "WTA 250"),
    "Merida": ("Merida", "Mexico", "Hard", "23 Feb - 1 Mar", "WTA 250"),
    "Austin": ("Austin", "United States", "Hard", "23 Feb - 1 Mar", "WTA 250"),
    "Bogota": ("Bogota", "Colombia", "Clay", "30 Mar - 5 Apr", "WTA 250"),
    "Rouen": ("Rouen", "France", "Clay", "13 Apr - 19 Apr", "WTA 250"),
    "Strasbourg": ("Strasbourg", "France", "Clay", "18 May - 24 May", "WTA 250"),
    "Rabat": ("Rabat", "Morocco", "Clay", "18 May - 24 May", "WTA 250"),
    "'s-Hertogenbosch": ("'s-Hertogenbosch", "Netherlands", "Grass", "8 Jun - 14 Jun", "WTA 250"),
    "Nottingham": ("Nottingham", "Great Britain", "Grass", "15 Jun - 21 Jun", "WTA 250"),
    "Eastbourne": ("Eastbourne", "Great Britain", "Grass", "22 Jun - 28 Jun", "WTA 250"),
    "Iasi": ("Iasi", "Romania", "Clay", "13 Jul - 19 Jul", "WTA 250"),
    "Prague": ("Prague", "Czech Republic", "Hard", "20 Jul - 26 Jul", "WTA 250"),
    "Monterrey": ("Monterrey", "Mexico", "Hard", "24 Aug - 30 Aug", "WTA 250"),
    "Cleveland": ("Cleveland", "United States", "Hard", "24 Aug - 30 Aug", "WTA 250"),
    "Guadalajara": ("Guadalajara", "Mexico", "Hard", "14 Sep - 20 Sep", "WTA 1000"),
    "Sao Paulo": ("Sao Paulo", "Brazil", "Hard", "14 Sep - 20 Sep", "WTA 250"),
    "Seoul": ("Seoul", "South Korea", "Hard", "21 Sep - 27 Sep", "WTA 250"),
    "Osaka": ("Osaka", "Japan", "Hard", "19 Oct - 25 Oct", "WTA 250"),
    "Guangzhou": ("Guangzhou", "China", "Hard", "26 Oct - 1 Nov", "WTA 250"),
    "Chennai": ("Chennai", "India", "Hard", "2 Nov - 8 Nov", "WTA 250"),
    "Hong Kong": ("Hong Kong", "Hong Kong", "Hard", "2 Nov - 8 Nov", "WTA 250"),
    "Jiujiang": ("Jiujiang", "China", "Hard", "2 Nov - 8 Nov", "WTA 250"),
    "WTA Finals": ("Riyadh", "Saudi Arabia", "Hard", "9 Nov - 15 Nov", "WTA Finals"),
}

# ── 2026 WTA 125 Calendar Metadata ──
WTA125_CALENDAR = {
    "Canberra": ("Canberra", "Australia", "Hard", "5 Jan - 11 Jan", "WTA 125"),
    "Manila": ("Manila", "Philippines", "Hard", "26 Jan - 31 Jan", "WTA 125"),
    "Mumbai": ("Mumbai", "India", "Hard", "2 Feb - 8 Feb", "WTA 125"),
    "Oeiras": ("Oeiras", "Portugal", "Hard", "9 Feb - 15 Feb", "WTA 125"),
    "Les Sables d'Olonne": ("Les Sables d'Olonne", "France", "Hard", "16 Feb - 22 Feb", "WTA 125"),
    "Midland": ("Midland", "United States", "Hard", "16 Feb - 22 Feb", "WTA 125"),
    "Oeiras 2": ("Oeiras", "Portugal", "Hard", "16 Feb - 22 Feb", "WTA 125"),
    "Antalya": ("Antalya", "Turkey", "Clay", "23 Feb - 1 Mar", "WTA 125"),
    "Antalya 2": ("Antalya", "Turkey", "Clay", "2 Mar - 8 Mar", "WTA 125"),
    "Austin 125": ("Austin", "United States", "Hard", "9 Mar - 15 Mar", "WTA 125"),
    "Antalya 3": ("Antalya", "Turkey", "Clay", "9 Mar - 15 Mar", "WTA 125"),
    "Puerto Vallarta": ("Puerto Vallarta", "Mexico", "Hard", "23 Mar - 29 Mar", "WTA 125"),
    "Dubrovnik": ("Dubrovnik", "Croatia", "Clay", "23 Mar - 29 Mar", "WTA 125"),
    "Oeiras 3": ("Oeiras", "Portugal", "Clay", "13 Apr - 19 Apr", "WTA 125"),
    "Oeiras 4": ("Oeiras", "Portugal", "Clay", "20 Apr - 26 Apr", "WTA 125"),
    "Saint Malo": ("Saint Malo", "France", "Clay", "27 Apr - 3 May", "WTA 125"),
    "La Bisbal d'Emporda": ("La Bisbal d'Emporda", "Spain", "Clay", "27 Apr - 3 May", "WTA 125"),
    "Istanbul": ("Istanbul", "Turkey", "Clay", "4 May - 10 May", "WTA 125"),
    "Paris 125": ("Paris", "France", "Clay", "11 May - 17 May", "WTA 125"),
    "Parma": ("Parma", "Italy", "Clay", "11 May - 17 May", "WTA 125"),
    "Birmingham": ("Birmingham", "Great Britain", "Grass", "1 Jun - 7 Jun", "WTA 125"),
    "Foggia": ("Foggia", "Italy", "Clay", "1 Jun - 7 Jun", "WTA 125"),
    "Makarska": ("Makarska", "Croatia", "Clay", "1 Jun - 7 Jun", "WTA 125"),
}

# ── 2026 ATP Challenger Calendar Metadata ──
# Same 5-tuple format as ATP/WTA calendars: (city, country, surface, dates, tier)
# Surface suffixed with " (i)" for indoor events
CHALLENGER_CALENDAR = {
    # ── January ──
    "Bengaluru": ("Bengaluru", "India", "Hard", "5 Jan - 10 Jan", "ATP Challenger 125"),
    "Canberra": ("Canberra", "Australia", "Hard", "5 Jan - 10 Jan", "ATP Challenger 125"),
    "Noumea": ("Noumea", "New Caledonia", "Hard", "5 Jan - 10 Jan", "ATP Challenger 75"),
    "Nonthaburi": ("Nonthaburi", "Thailand", "Hard", "5 Jan - 10 Jan", "ATP Challenger 50"),
    "Nottingham": ("Nottingham", "Great Britain", "Hard (i)", "5 Jan - 10 Jan", "ATP Challenger 50"),
    "Nonthaburi 2": ("Nonthaburi", "Thailand", "Hard", "12 Jan - 17 Jan", "ATP Challenger 75"),
    "Buenos Aires CH": ("Buenos Aires", "Argentina", "Clay", "12 Jan - 17 Jan", "ATP Challenger 50"),
    "Glasgow": ("Glasgow", "Great Britain", "Hard (i)", "12 Jan - 17 Jan", "ATP Challenger 50"),
    "Oeiras": ("Oeiras", "Portugal", "Hard (i)", "19 Jan - 25 Jan", "ATP Challenger 100"),
    "Itajai": ("Itajai", "Brazil", "Clay", "19 Jan - 25 Jan", "ATP Challenger 75"),
    "Soma Bay": ("Soma Bay", "Egypt", "Hard", "19 Jan - 26 Jan", "ATP Challenger 75"),
    "Phan Thiet": ("Phan Thiet", "Vietnam", "Hard", "19 Jan - 25 Jan", "ATP Challenger 50"),
    "Phan Thiet 2": ("Phan Thiet", "Vietnam", "Hard", "26 Jan - 1 Feb", "ATP Challenger 50"),
    "Bahrain": ("Manama", "Bahrain", "Hard", "27 Jan - 1 Feb", "ATP Challenger 125"),
    # ── February ──
    "Rosario": ("Rosario", "Argentina", "Clay", "2 Feb - 8 Feb", "ATP Challenger 125"),
    "Brisbane": ("Brisbane", "Australia", "Hard", "2 Feb - 8 Feb", "ATP Challenger 75"),
    "Cleveland": ("Cleveland", "United States", "Hard (i)", "2 Feb - 8 Feb", "ATP Challenger 75"),
    "Tenerife": ("Tenerife", "Spain", "Hard", "2 Feb - 8 Feb", "ATP Challenger 75"),
    "Koblenz": ("Koblenz", "Germany", "Hard (i)", "2 Feb - 8 Feb", "ATP Challenger 50"),
    "Cesenatico": ("Cesenatico", "Italy", "Hard (i)", "2 Feb - 8 Feb", "ATP Challenger 50"),
    "Pau": ("Pau", "France", "Hard (i)", "9 Feb - 15 Feb", "ATP Challenger 125"),
    "Brisbane 2": ("Brisbane", "Australia", "Hard", "9 Feb - 15 Feb", "ATP Challenger 75"),
    "Tenerife 2": ("Tenerife", "Spain", "Hard", "9 Feb - 15 Feb", "ATP Challenger 75"),
    "Chennai": ("Chennai", "India", "Hard", "9 Feb - 15 Feb", "ATP Challenger 50"),
    "Baton Rouge": ("Baton Rouge", "United States", "Hard (i)", "9 Feb - 15 Feb", "ATP Challenger 50"),
    "Lille": ("Lille", "France", "Hard (i)", "16 Feb - 22 Feb", "ATP Challenger 125"),
    "Metepec": ("Metepec", "Mexico", "Hard", "16 Feb - 22 Feb", "ATP Challenger 75"),
    "New Delhi": ("New Delhi", "India", "Hard", "16 Feb - 22 Feb", "ATP Challenger 75"),
    "Tigre": ("Tigre", "Argentina", "Clay", "16 Feb - 22 Feb", "ATP Challenger 50"),
    "St. Brieuc": ("St. Brieuc", "France", "Hard (i)", "23 Feb - 1 Mar", "ATP Challenger 100"),
    "Pune": ("Pune", "India", "Hard", "23 Feb - 1 Mar", "ATP Challenger 75"),
    "Lugano": ("Lugano", "Switzerland", "Hard (i)", "23 Feb - 1 Mar", "ATP Challenger 75"),
    # ── March ──
    "Thionville": ("Thionville", "France", "Hard (i)", "2 Mar - 8 Mar", "ATP Challenger 100"),
    "Brasilia": ("Brasilia", "Brazil", "Clay", "2 Mar - 8 Mar", "ATP Challenger 75"),
    "Kigali": ("Kigali", "Rwanda", "Clay", "2 Mar - 8 Mar", "ATP Challenger 75"),
    "Fujairah": ("Fujairah", "United Arab Emirates", "Hard", "2 Mar - 8 Mar", "ATP Challenger 50"),
    "Hersonissos": ("Hersonissos", "Greece", "Hard", "2 Mar - 8 Mar", "ATP Challenger 50"),
    "Kigali 2": ("Kigali", "Rwanda", "Clay", "9 Mar - 15 Mar", "ATP Challenger 100"),
    "Santiago": ("Santiago", "Chile", "Clay", "9 Mar - 15 Mar", "ATP Challenger 75"),
    "Cherbourg": ("Cherbourg", "France", "Hard (i)", "9 Mar - 15 Mar", "ATP Challenger 75"),
    "Fujairah 2": ("Fujairah", "United Arab Emirates", "Hard", "9 Mar - 15 Mar", "ATP Challenger 50"),
    "Hersonissos 2": ("Hersonissos", "Greece", "Hard", "9 Mar - 15 Mar", "ATP Challenger 50"),
    "Phoenix": ("Phoenix", "United States", "Hard", "10 Mar - 15 Mar", "ATP Challenger 175"),
    "Cap Cana": ("Cap Cana", "Dominican Republic", "Hard", "10 Mar - 15 Mar", "ATP Challenger 175"),
    "Morelos": ("Morelos", "Mexico", "Hard", "16 Mar - 22 Mar", "ATP Challenger 75"),
    "Asuncion": ("Asuncion", "Paraguay", "Clay", "16 Mar - 22 Mar", "ATP Challenger 75"),
    "Murcia": ("Murcia", "Spain", "Clay", "16 Mar - 22 Mar", "ATP Challenger 75"),
    "Morelia": ("Morelia", "Mexico", "Hard", "23 Mar - 28 Mar", "ATP Challenger 125"),
    "Naples": ("Naples", "Italy", "Clay", "23 Mar - 29 Mar", "ATP Challenger 125"),
    "Sao Paulo": ("Sao Paulo", "Brazil", "Clay", "23 Mar - 29 Mar", "ATP Challenger 100"),
    "Montemar": ("Montemar", "Spain", "Clay", "23 Mar - 29 Mar", "ATP Challenger 100"),
    "Bucaramanga": ("Bucaramanga", "Colombia", "Clay", "23 Mar - 29 Mar", "ATP Challenger 50"),
    "Yokkaichi": ("Yokkaichi", "Japan", "Hard", "23 Mar - 29 Mar", "ATP Challenger 50"),
    "Split": ("Split", "Croatia", "Clay", "23 Mar - 29 Mar", "ATP Challenger 50"),
    # ── April ──
    "Mexico City": ("Mexico City", "Mexico", "Clay", "6 Apr - 12 Apr", "ATP Challenger 125"),
    "Monza": ("Monza", "Italy", "Clay", "6 Apr - 12 Apr", "ATP Challenger 125"),
    "Campinas": ("Campinas", "Brazil", "Clay", "6 Apr - 12 Apr", "ATP Challenger 75"),
    "Sarasota": ("Sarasota", "United States", "Clay", "6 Apr - 12 Apr", "ATP Challenger 75"),
    "Madrid": ("Madrid", "Spain", "Clay", "6 Apr - 12 Apr", "ATP Challenger 75"),
    "Wuning": ("Wuning", "China", "Hard", "6 Apr - 12 Apr", "ATP Challenger 50"),
    "Busan": ("Busan", "South Korea", "Hard", "13 Apr - 19 Apr", "ATP Challenger 125"),
    "Oeiras 2": ("Oeiras", "Portugal", "Clay", "13 Apr - 19 Apr", "ATP Challenger 125"),
    "Tallahassee": ("Tallahassee", "United States", "Clay", "13 Apr - 19 Apr", "ATP Challenger 75"),
    "Merida": ("Merida", "Mexico", "Clay", "13 Apr - 19 Apr", "ATP Challenger 75"),
    "Wuning 2": ("Wuning", "China", "Hard", "13 Apr - 19 Apr", "ATP Challenger 50"),
    "Gwangju": ("Gwangju", "South Korea", "Hard", "20 Apr - 26 Apr", "ATP Challenger 75"),
    "Savannah": ("Savannah", "United States", "Clay", "20 Apr - 26 Apr", "ATP Challenger 75"),
    "Rome": ("Rome", "Italy", "Clay", "20 Apr - 26 Apr", "ATP Challenger 75"),
    "Shymkent": ("Shymkent", "Kazakhstan", "Clay", "20 Apr - 26 Apr", "ATP Challenger 50"),
    "Abidjan": ("Abidjan", "Ivory Coast", "Hard", "20 Apr - 26 Apr", "ATP Challenger 50"),
    "Cagliari": ("Cagliari", "Italy", "Clay", "28 Apr - 3 May", "ATP Challenger 175"),
    "Aix-en-Provence": ("Aix-en-Provence", "France", "Clay", "28 Apr - 3 May", "ATP Challenger 175"),
    # ── May ──
    "Wuxi": ("Wuxi", "China", "Hard", "4 May - 10 May", "ATP Challenger 100"),
    "Francavilla al Mare": ("Francavilla al Mare", "Italy", "Clay", "4 May - 10 May", "ATP Challenger 75"),
    "Prague": ("Prague", "Czechia", "Clay", "4 May - 10 May", "ATP Challenger 75"),
    "Brazzaville": ("Brazzaville", "Republic of Congo", "Clay", "4 May - 10 May", "ATP Challenger 50"),
    "Santos": ("Santos", "Brazil", "Clay", "4 May - 10 May", "ATP Challenger 50"),
    "Oeiras 3": ("Oeiras", "Portugal", "Clay", "11 May - 16 May", "ATP Challenger 100"),
    "Tunis": ("Tunis", "Tunisia", "Clay", "11 May - 16 May", "ATP Challenger 75"),
    "Zagreb": ("Zagreb", "Croatia", "Clay", "11 May - 16 May", "ATP Challenger 75"),
    "Cordoba": ("Cordoba", "Argentina", "Clay", "11 May - 16 May", "ATP Challenger 50"),
    "Bordeaux": ("Bordeaux", "France", "Clay", "12 May - 17 May", "ATP Challenger 175"),
    "Valencia": ("Valencia", "Spain", "Clay", "12 May - 17 May", "ATP Challenger 175"),
    "Istanbul": ("Istanbul", "Turkey", "Clay", "18 May - 23 May", "ATP Challenger 75"),
    "Cervia": ("Cervia", "Italy", "Clay", "18 May - 23 May", "ATP Challenger 50"),
    "Chisinau": ("Chisinau", "Moldova", "Clay", "25 May - 31 May", "ATP Challenger 100"),
    "Little Rock": ("Little Rock", "United States", "Hard", "25 May - 31 May", "ATP Challenger 75"),
    "Vicenza": ("Vicenza", "Italy", "Clay", "25 May - 31 May", "ATP Challenger 75"),
    "Centurion": ("Centurion", "South Africa", "Hard", "25 May - 31 May", "ATP Challenger 50"),
    "Kosice": ("Kosice", "Slovakia", "Clay", "25 May - 31 May", "ATP Challenger 50"),
    # ── June ──
    "Perugia": ("Perugia", "Italy", "Clay", "1 Jun - 7 Jun", "ATP Challenger 125"),
    "Birmingham": ("Birmingham", "Great Britain", "Grass", "1 Jun - 7 Jun", "ATP Challenger 125"),
    "Heilbronn": ("Heilbronn", "Germany", "Clay", "1 Jun - 7 Jun", "ATP Challenger 100"),
    "Prostejov": ("Prostejov", "Czechia", "Clay", "1 Jun - 7 Jun", "ATP Challenger 100"),
    "Tyler": ("Tyler", "United States", "Hard", "1 Jun - 7 Jun", "ATP Challenger 75"),
    "Centurion 2": ("Centurion", "South Africa", "Hard", "1 Jun - 7 Jun", "ATP Challenger 50"),
    "Bratislava": ("Bratislava", "Slovakia", "Clay", "7 Jun - 8 Jun", "ATP Challenger 100"),
    "Ilkley": ("Ilkley", "Great Britain", "Grass", "8 Jun - 14 Jun", "ATP Challenger 125"),
    "Lyon": ("Lyon", "France", "Clay", "8 Jun - 14 Jun", "ATP Challenger 100"),
    "Nottingham 2": ("Nottingham", "Great Britain", "Grass", "15 Jun - 21 Jun", "ATP Challenger 125"),
    "Poznan": ("Poznan", "Poland", "Clay", "15 Jun - 20 Jun", "ATP Challenger 100"),
    "Royan": ("Royan", "France", "Clay", "15 Jun - 20 Jun", "ATP Challenger 50"),
    "Targu Mures": ("Targu Mures", "Romania", "Clay", "22 Jun - 27 Jun", "ATP Challenger 75"),
    "Durham": ("Durham", "United States", "Hard", "22 Jun - 27 Jun", "ATP Challenger 75"),
    "Cary": ("Cary", "United States", "Hard", "29 Jun - 5 Jul", "ATP Challenger 75"),
    # ── July ──
    "Newport": ("Newport", "United States", "Grass", "6 Jul - 12 Jul", "ATP Challenger 125"),
    "Braunschweig": ("Braunschweig", "Germany", "Clay", "6 Jul - 12 Jul", "ATP Challenger 125"),
    "Trieste": ("Trieste", "Italy", "Clay", "6 Jul - 12 Jul", "ATP Challenger 75"),
    "Huy": ("Huy", "Belgium", "Clay", "6 Jul - 12 Jul", "ATP Challenger 50"),
    "Granby": ("Granby", "Canada", "Hard", "13 Jul - 19 Jul", "ATP Challenger 75"),
    "Lincoln": ("Lincoln", "United States", "Hard", "13 Jul - 19 Jul", "ATP Challenger 75"),
    "Cordenons": ("Cordenons", "Italy", "Clay", "13 Jul - 19 Jul", "ATP Challenger 75"),
    "Pozoblanco": ("Pozoblanco", "Spain", "Hard", "13 Jul - 19 Jul", "ATP Challenger 75"),
    "Bloomfield Hills": ("Bloomfield Hills", "United States", "Hard", "20 Jul - 26 Jul", "ATP Challenger 100"),
    "Winnipeg": ("Winnipeg", "Canada", "Hard", "20 Jul - 26 Jul", "ATP Challenger 75"),
    "Segovia": ("Segovia", "Spain", "Hard", "20 Jul - 26 Jul", "ATP Challenger 75"),
    "Vancouver": ("Vancouver", "Canada", "Hard", "27 Jul - 2 Aug", "ATP Challenger 125"),
    "San Marino": ("San Marino", "San Marino", "Clay", "27 Jul - 2 Aug", "ATP Challenger 125"),
    # ── Aliases for scraper name variations ──
    "Bangkok": ("Nonthaburi", "Thailand", "Hard", "5 Jan - 10 Jan", "ATP Challenger 50"),
    "Bangkok 2": ("Nonthaburi", "Thailand", "Hard", "12 Jan - 17 Jan", "ATP Challenger 75"),
    "New Dehli": ("New Delhi", "India", "Hard", "16 Feb - 22 Feb", "ATP Challenger 75"),
    "Brasília": ("Brasilia", "Brazil", "Clay", "2 Mar - 8 Mar", "ATP Challenger 75"),
    "Tigre 2": ("Tigre", "Argentina", "Clay", "23 Feb - 1 Mar", "ATP Challenger 50"),
}
