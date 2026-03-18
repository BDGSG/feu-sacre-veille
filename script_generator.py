"""
Feu Sacre - Script Generator
Generates video scripts from veille data using LLM (Groq).
Auto-applies trending insights: tags, topics, title patterns.
"""

import json
import logging
import urllib.request

from config import GROQ_API_KEY, GROQ_MODEL, SCRIPT_SECTIONS_COUNT, SCRIPT_WORDS_TARGET

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es le scriptwriter de la chaine YouTube "Feu Sacre".
La chaine produit des videos de developpement personnel, motivation et mindset
avec une esthetique dark anime / guerrier / phoenix.

Ton style:
- Phrases courtes et percutantes, rythmees comme un discours de guerre
- Metaphores martiales et mythologiques (Spartiates, Samourai, Phoenix, forge, feu)
- Tutoiement du spectateur, ton direct et visceral
- References au stoicisme, a la discipline, au depassement de soi
- Pas de jargon corporate, pas de positivite toxique, du vrai

Structure d'une video (~{words} mots total, {sections} sections):
1. HOOK (pas de titre) - accroche choc, stat ou question provocante
2-6. PHASES numerotees avec titres epiques (ex: "PHASE 1: TUE TON CONFORT")
7. CTA (pas de titre) - appel a l'action, abonnement, commentaire

Chaque section doit avoir:
- "titre": titre de la phase (vide pour hook et CTA)
- "narration": le texte a lire (300-500 mots par section)
- "images": liste de 2-4 prompts pour generer des images AI
  Format image: description visuelle en anglais pour FLUX.1
  Style: dark anime, hooded warrior, glowing orange eyes, fire embers

IMPORTANT: Reponds UNIQUEMENT en JSON valide, sans texte avant ou apres.
""".format(words=SCRIPT_WORDS_TARGET, sections=SCRIPT_SECTIONS_COUNT)


def _call_groq(messages: list[dict], temperature: float = 0.8) -> str:
    """Call Groq LLM API."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 8000,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


def _extract_insights(report: dict) -> str:
    """Extract actionable insights from veille report for script generation."""
    insights = []

    # Top trending topics from tags
    top_tags = report.get("top_tags", [])[:15]
    if top_tags:
        tags_str = ", ".join(f"{t[0]} ({t[1]}x)" for t in top_tags)
        insights.append(f"Tags trending cette semaine: {tags_str}")

    # Best performing titles (patterns to emulate)
    best = report.get("best_titles", [])[:10]
    if best:
        titles = "\n".join(f"  - {t['title']} ({t['views']:,} vues)" for t in best)
        insights.append(f"Titres les plus performants:\n{titles}")

    # Competitor analysis
    competitors = report.get("competitors", [])[:5]
    if competitors:
        comp_str = "\n".join(
            f"  - {c['title']}: {c['subscribers']:,} abos"
            for c in competitors
        )
        insights.append(f"Top concurrents:\n{comp_str}")

    # Trending video themes
    trending = report.get("trending_videos", [])[:10]
    if trending:
        themes = set()
        for v in trending:
            for tag in v.get("tags", [])[:3]:
                themes.add(tag.lower())
        if themes:
            insights.append(f"Themes recurrents: {', '.join(list(themes)[:20])}")

    return "\n\n".join(insights) if insights else "Pas de donnees de veille disponibles."


def generate_script_from_veille(report: dict) -> list[dict]:
    """
    Generate a complete video script based on veille intelligence.
    Returns list of sections with titre, narration, images.
    """
    insights = _extract_insights(report)

    user_prompt = f"""Voici les resultats de la veille concurrentielle de cette semaine:

{insights}

Genere un script video complet pour Feu Sacre qui:
1. S'inspire des tendances detectees (tags, themes populaires)
2. Se demarque des concurrents avec un angle unique et percutant
3. Utilise le vocabulaire et les themes qui performent dans la niche
4. Reste fidele a l'identite Feu Sacre (guerrier, feu, phoenix, discipline)

Format de reponse (JSON array):
[
  {{
    "titre": "",
    "narration": "texte du hook...",
    "images": ["prompt1 en anglais", "prompt2"]
  }},
  {{
    "titre": "PHASE 1: TITRE EPIQUE",
    "narration": "texte de la section...",
    "images": ["prompt1", "prompt2", "prompt3"]
  }},
  ...
]"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    log.info("Generating script from veille insights...")
    raw = _call_groq(messages, temperature=0.85)

    # Parse JSON from response (handle markdown code blocks)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    sections = json.loads(raw)

    # Validate structure
    for i, sec in enumerate(sections):
        if "narration" not in sec:
            raise ValueError(f"Section {i} missing 'narration'")
        if "images" not in sec:
            sec["images"] = []
        if "titre" not in sec:
            sec["titre"] = ""

    total_words = sum(len(s["narration"].split()) for s in sections)
    total_images = sum(len(s["images"]) for s in sections)
    log.info("Script generated: %d sections, %d words, %d images",
             len(sections), total_words, total_images)

    return sections


def generate_title_and_metadata(sections: list[dict], report: dict) -> dict:
    """Generate video title, description, and tags from script + veille."""
    narration_preview = " ".join(s["narration"][:100] for s in sections[:3])
    top_tags = [t[0] for t in report.get("top_tags", [])[:20]]

    prompt = f"""Pour cette video Feu Sacre dont voici un apercu:
{narration_preview}...

Tags trending: {', '.join(top_tags[:15])}

Genere en JSON:
{{
  "title": "titre YouTube accrocheur (max 70 chars, majuscules strategiques)",
  "description": "description YouTube (200-300 mots, avec emojis feu/epee, liens, CTA)",
  "tags": ["tag1", "tag2", ...] (20-30 tags SEO pertinents)
}}"""

    messages = [
        {"role": "system", "content": "Tu es un expert SEO YouTube specialise dans le developpement personnel. Reponds uniquement en JSON."},
        {"role": "user", "content": prompt},
    ]

    raw = _call_groq(messages, temperature=0.7)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    metadata = json.loads(raw)
    log.info("Metadata generated: '%s'", metadata.get("title", "?"))
    return metadata


def generate_default_script() -> list[dict]:
    """Generate a script without veille data (standalone mode)."""
    return generate_script_from_veille({
        "top_tags": [],
        "best_titles": [],
        "competitors": [],
        "trending_videos": [],
    })
