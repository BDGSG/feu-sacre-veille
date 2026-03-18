"""
Feu Sacre - Corrections de prononciation pour Edge-TTS
Corrige les mots mal prononces par le TTS francais (HenriNeural).
"""

import re
import logging

log = logging.getLogger(__name__)

# ── Mots francais mal prononces par edge-tts ──────────────────────────────
# Le TTS HenriNeural a des problemes avec certains mots francais rares,
# noms propres, et termes philosophiques.

FRENCH_FIXES = {
    # Philosophie / Stoicisme (thematique Feu Sacre)
    "stoïcisme": "sto-issisme",
    "stoïcien": "sto-issien",
    "stoïciens": "sto-issiens",
    "stoïque": "sto-ique",
    "stoïques": "sto-iques",
    "Nietzsche": "Nitche",
    "nietzschéen": "nitchéen",
    "nietzschéenne": "nitchéenne",
    "Schopenhauer": "Chopennaweur",
    "Épictète": "Épictète",
    "Sénèque": "Sénèque",
    "Marc Aurèle": "Marc Aurèle",
    "Marcus Aurelius": "Marcusse Auréliusse",
    "Aurelius": "Auréliusse",
    "Socrate": "Socrate",
    "Héraclite": "Éraclite",
    "Miyamoto Musashi": "Miyamoto Moussachi",
    "Musashi": "Moussachi",
    "Sun Tzu": "Soune Dzou",
    "Bushido": "Bouchido",
    "bushido": "bouchido",

    # Termes grecs/latins
    "Memento mori": "Méménto mori",
    "memento mori": "méménto mori",
    "Amor fati": "Amor fati",
    "Carpe diem": "Carpé diemme",
    "carpe diem": "carpé diemme",
    "Premeditatio malorum": "Prémédita-tsio malorume",
    "hubris": "ubrice",
    "ethos": "étoss",
    "pathos": "patoss",
    "logos": "logoss",
    "kairos": "kaïross",
    "eudaimonia": "eudaïmonia",
    "ataraxie": "ataraxie",
    "apatheia": "apatéïa",

    # Termes japonais (Samourai / Guerrier)
    "samouraï": "samouraï",
    "samouraïs": "samouraïs",
    "Samouraï": "Samouraï",
    "Samouraïs": "Samouraïs",
    "katana": "katana",
    "dojo": "dojo",
    "sensei": "sennseï",
    "seppuku": "sépokou",
    "harakiri": "arakiri",
    "ronin": "ronine",
    "shogun": "chogoune",
    "Shogun": "Chogoune",
    "kendo": "kenndo",
    "karate": "karaté",
    "judo": "joudo",
    "zen": "zenne",
    "Zen": "Zenne",

    # Termes spartiates / grecs
    "Spartiate": "Spartiate",
    "Spartiates": "Spartiates",
    "hoplite": "oplite",
    "hoplites": "oplites",
    "phalanx": "falanxe",
    "phalange": "falange",
    "Thermopyles": "Termopile",
    "Léonidas": "Léonidasse",
    "Xerxès": "Zèrxèss",
    "Achille": "Achile",
    "Ulysse": "Ulisse",
    "Odyssée": "Odissée",
    "Iliade": "Iliade",

    # Mots francais problematiques pour le TTS
    "pourcent": "pour-cent",
    "aujourd'hui": "aujourd'hui",
    "quelqu'un": "quelqu'un",
    "jusqu'au": "jusqu'au",
    "résilience": "rézilience",
    "paradigme": "paradig-me",
    "paradigmes": "paradig-mes",
    "psyché": "psiké",
    "psychologie": "psikologie",
    "chrysalide": "krizalide",
    "phénix": "fénix",
    "Phénix": "Fénix",
    "phoenix": "fénix",
    "Phoenix": "Fénix",
    "inébranlable": "inébranlable",
    "quintessence": "kuintéssence",
    "catharsis": "katarsiss",

    # Nombres ecrits souvent mal lus
    "95%": "quatre-vingt-quinze pour cent",
    "99%": "quatre-vingt-dix-neuf pour cent",
    "100%": "cent pour cent",
    "1000": "mille",
    "4h": "quatre heures",
    "5h": "cinq heures",
    "6h": "six heures",
    "4h du matin": "quatre heures du matin",
    "5h du matin": "cinq heures du matin",
}

# ── Mots anglais utilises dans le dev perso FR ────────────────────────────

ENGLISH_FIXES = {
    "mindset": "maïndnsètte",
    "Mindset": "Maïndnsètte",
    "mindsets": "maïndnsèttes",
    "burnout": "beurnaoutte",
    "burn-out": "beurnaoutte",
    "feedback": "fidbaque",
    "coaching": "cotchigne",
    "coach": "cotche",
    "coachs": "cotches",
    "workout": "oueurkaoutte",
    "challenge": "tchalènge",
    "challenges": "tchalènges",
    "flow": "flo",
    "Flow": "Flo",
    "focus": "fokeusse",
    "Focus": "Fokeusse",
    "reset": "ri-sète",
    "Reset": "Ri-sète",
    "level up": "lévèle eupe",
    "grind": "graïnde",
    "hustle": "heuseule",
    "mindfulness": "maïndfouleunesse",
    "self-care": "sèlfe-kère",
    "self care": "sèlfe kère",
    "leadership": "lideur-chipe",
    "framework": "fréïmoueurke",
    "peak performance": "pike perfaurmance",
    "growth": "grosse",
    "Growth": "Grosse",
    "growth mindset": "grosse maïndnsètte",
    "comfort zone": "conforte zone",
    "discipline": "discipline",  # fr OK
    "routine": "routine",  # fr OK
    "stoic": "sto-ique",
    "Stoic": "Sto-ique",
    "warrior": "ouorrieur",
    "legacy": "lègueussi",
    "purpose": "peurpeusse",
    "grindset": "graïndnsètte",
    "accountability": "akaounteubiliti",
    "podcast": "podkaste",
    "podcasts": "podkastes",
    "lifestyle": "laïfstaïle",
    "empowerment": "emmpaoueurement",
    "storytelling": "storitèligne",
}

# ── Expressions multi-mots ────────────────────────────────────────────────

PHRASE_FIXES = {
    "bull run": "boule reune",
    "no pain no gain": "no péïne no guéïne",
    "comfort zone": "comforte zone",
    "never give up": "néveur guive eupe",
    "level up": "lévèle eupe",
    "wake up": "ouéïke eupe",
    "game changer": "guéïme tchéïndjeur",
    "next level": "nèxte lévèle",
    "self made": "sèlfe méïde",
    "self-made": "sèlfe-méïde",
}


def normalize_pronunciation(text: str) -> str:
    """
    Pre-process text before sending to TTS.
    Fixes known pronunciation issues for edge-tts fr-FR-HenriNeural.
    """
    if not text:
        return text

    original = text

    # 1. Fix multi-word phrases first (longest match first)
    for phrase, replacement in sorted(PHRASE_FIXES.items(), key=lambda x: -len(x[0])):
        # Case-insensitive replacement preserving sentence flow
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub(replacement, text)

    # 2. Fix French words
    for word, replacement in FRENCH_FIXES.items():
        if word in text:
            text = text.replace(word, replacement)

    # 3. Fix English words (case-insensitive, word boundaries)
    for word, replacement in ENGLISH_FIXES.items():
        pattern = re.compile(r'\b' + re.escape(word) + r'\b')
        text = pattern.sub(replacement, text)

    # 4. Fix numbers with % not already caught
    text = re.sub(r'(\d+)\s*%', lambda m: f"{m.group(1)} pour cent", text)

    # 5. Fix "Xh" time patterns not already caught
    text = re.sub(r'\b(\d{1,2})h\b', lambda m: f"{m.group(1)} heures", text)

    # 6. Remove emojis (TTS reads them or glitches)
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0001F018-\U0001F270\U000024C2-\U0001F251'
        r'\U0000200D\U00002640\U00002642\U0000FE0F\U00002764]+',
        '', text
    )

    # 7. Add breath pauses on very long sentences (>100 chars without punctuation)
    sentences = text.split('. ')
    fixed_sentences = []
    for sent in sentences:
        if len(sent) > 120 and ',' not in sent:
            # Insert comma at natural break points
            words = sent.split()
            mid = len(words) // 2
            # Find a good break near middle (after liaison words)
            break_words = {'et', 'ou', 'mais', 'donc', 'car', 'puis', 'ainsi', 'alors', 'parce', 'comme', 'quand'}
            best = mid
            for i in range(max(0, mid - 3), min(len(words), mid + 4)):
                if words[i].lower().rstrip('.,;:!?') in break_words:
                    best = i + 1
                    break
            sent = ' '.join(words[:best]) + ', ' + ' '.join(words[best:])
        fixed_sentences.append(sent)
    text = '. '.join(fixed_sentences)

    # 8. Clean up double spaces
    text = re.sub(r'\s+', ' ', text).strip()

    if text != original:
        changes = sum(1 for a, b in zip(text, original) if a != b)
        log.info("Pronunciation: %d character changes applied", changes)

    return text
