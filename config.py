import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7445971784")

# Concurrents directs (chaines FR dev perso / motivation / mindset)
# Tous en channel ID (UC...) pour economiser le quota API
COMPETITORS = {
    "Yomi Denzel": "UChgE6R4QauGAJAlYiJOcCGw",
    "Franck Nicolas": "UCOPYmqe_bNzjYErvNEGJ5og",
    "Jean Laval": "UC8JMj6-MQMjMhSCxwbMuvPw",
    "Les Sherpas": "UCzk9CKiC5wJrjpzGCfjqIkA",
    "the Stoic Mode": "UCqr2baNgRH9zCKRnb5dLqOA",
    "Pensees Profondes": "UC_PejHrGWKhMX7j-5KBluig",
    "David Laroche": "UCLkP4EU7PLrXnU1cElbYIZA",
    "Oussama Ammar": "UCMrdp10ltViJeGq2T0bGmsg",
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
