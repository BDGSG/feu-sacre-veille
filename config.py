import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7445971784")

# Concurrents directs (chaines FR dev perso / motivation / mindset)
# Format: nom -> handle YouTube (sans @) OU channel ID (UC...)
COMPETITORS = {
    "David Laroche": "@davidlaraborche",
    "Franck Nicolas": "UCOPYmqe_bNzjYErvNEGJ5og",
    "Emilio": "@EmilioSpeaks",
    "Jean Laval": "@jeanlaval",
    "Yomi Denzel": "UChgE6R4QauGAJAlYiJOcCGw",
    "Les Sherpas": "@les_sherpas",
    "Pensees Profondes": "@PenseesProfondes",
    "Motivation du Jour": "@MotivationduJourOfficiel",
    "the Stoic Mode": "@theStoicMode",
    "Mental Puissant": "@MentalPuissant",
}

# Mots-cles de recherche pour la niche
SEARCH_QUERIES = [
    "développement personnel français",
    "motivation française",
    "confiance en soi français",
    "discipline habitudes français",
    "mentalité de guerrier",
    "mindset entrepreneur français",
    "changer de vie motivation français",
    "routine du matin productivité",
    "force mentale résilience",
    "dépassement de soi",
    "stoïcisme français",
    "devenir meilleur version de soi",
]

# Nombre de resultats par requete
MAX_RESULTS_PER_QUERY = 20

# Planification du cron (tous les jours a 8h)
CRON_HOUR = 8
CRON_MINUTE = 0

# Port du serveur
PORT = int(os.getenv("PORT", "3000"))
