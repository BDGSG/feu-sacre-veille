import os

# Load .env if present
from dotenv import load_dotenv
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

# ── API Keys ──────────────────────────────────────────────────────────────

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7445971784")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Concurrents ───────────────────────────────────────────────────────────

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

MAX_RESULTS_PER_QUERY = 20

# ── Scheduling ────────────────────────────────────────────────────────────

CRON_HOUR = 8
CRON_MINUTE = 0
PORT = int(os.getenv("PORT", "3000"))

# ── TTS Voice ─────────────────────────────────────────────────────────────

VOICE = "fr-FR-HenriNeural"
VOICE_RATE = "-5%"
VOICE_PITCH = "-2Hz"

# ── Video Production ──────────────────────────────────────────────────────

FPS = 25
ZOOM_MAX = 1.10
XFADE_DUR = 0.8
WORDS_PER_GROUP = 5

# Identite visuelle Feu Sacre
CHARACTER_BIBLE = (
    "A powerful warrior silhouette, dark anime illustration style, "
    "mysterious hooded figure with angular features, intense glowing orange eyes, "
    "wearing a dark flowing cloak with orange fire ember particles, "
    "athletic build, standing against dramatic dark background with flame accents"
)
IMAGE_STYLE = (
    ", dark cinematic anime illustration, dramatic lighting, deep shadows "
    "with orange and red flame accents, warrior phoenix fire aesthetic, "
    "inspired by Vinland Saga and dark fantasy anime, 4k ultra detailed, "
    "no text no watermark no logos, 16:9 landscape composition"
)
IMAGE_STYLE_VERT = (
    ", dark cinematic anime illustration, dramatic lighting, deep shadows "
    "with orange and red flame accents, warrior phoenix fire aesthetic, "
    "inspired by Vinland Saga and dark fantasy anime, 4k ultra detailed, "
    "no text no watermark no logos, 9:16 portrait vertical composition"
)

# ── Subtitle Style (modern: shadow on words, no black background) ─────────

SUBTITLE_FONT = "Montserrat ExtraBold"
SUBTITLE_FONTSIZE = 90          # bigger than before (was 72)
SUBTITLE_FONTSIZE_VERT = 110    # vertical/shorts
SUBTITLE_PRIMARY = "&H00FFFFFF"  # white text
SUBTITLE_OUTLINE_COLOR = "&H00000000"  # black outline
SUBTITLE_SHADOW_COLOR = "&H40000000"   # 25% opacity shadow (subtle, no box)
SUBTITLE_OUTLINE = 5            # thick outline for readability
SUBTITLE_SHADOW = 3             # drop shadow offset (depth, not background)
SUBTITLE_BORDER_STYLE = 1       # 1=outline+shadow, NOT 3=opaque box
SUBTITLE_HIGHLIGHT = "&H0066CCFF"  # orange flame for active word
SUBTITLE_MARGIN_V = 50          # bottom margin

# ── LLM Script Generation ────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"
SCRIPT_SECTIONS_COUNT = 7
SCRIPT_WORDS_TARGET = 2500      # ~18 min at 140 wpm

# ── Music ─────────────────────────────────────────────────────────────────

MUSIC_VOLUME = 0.12
VOICE_VOLUME = 2.5
