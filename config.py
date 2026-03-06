import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7445971784")

# Concurrents directs (chaines FR dev perso / motivation / mindset)
COMPETITORS = {
    "David Laroche": "UCDz1naOEbcMak8s8_xO8DJg",
    "Franck Nicolas": "UC4Jd9BKlnEORSXKwsCNJcfg",
    "Emilio": "UC0-KaiZFXaPlcGFNuX1B4nQ",
    "S'enrichir": "UCYzMYq_jlTm3KxYbEB9bFZw",
    "Mylene Muller": "UC1tbpKQPikainYPlnrt_HLXQ",
    "Jean Laval": "UCa7JA7kiNY31NnCXzCLHGYw",
    "Yomi Denzel": "UCkGwDJDsKMq4DZlSvpSNYnA",
    "Les Sherpas": "UCzN5iJg17EDiV1qIuZMiYRg",
    "Motivation du Jour": "UCOxcT3Kj80dqmCGxvgkSFTw",
    "Mental Puissant": "UCL8fKxLEPlBHG3-nEvyJgJQ",
}

# Mots-cles de recherche pour la niche
SEARCH_QUERIES = [
    "développement personnel",
    "motivation française",
    "confiance en soi",
    "discipline habitudes",
    "mentalité de guerrier",
    "mindset entrepreneur français",
    "changer de vie motivation",
    "routine du matin productivité",
    "force mentale résilience",
    "dépassement de soi",
    "stoïcisme français",
    "devenir meilleur version",
]

# Nombre de resultats par requete
MAX_RESULTS_PER_QUERY = 20

# Planification du cron (tous les jours a 8h)
CRON_HOUR = 8
CRON_MINUTE = 0

# Port du serveur
PORT = int(os.getenv("PORT", "3000"))
