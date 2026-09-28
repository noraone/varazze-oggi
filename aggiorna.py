"""Varazze Oggi - raccoglie le notizie su Varazze dai feed RSS e aggiorna news.json.
Gira gratis su GitHub Actions, senza intelligenza artificiale e senza token."""
import json, re, html, urllib.request, datetime as dt
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

# (nome fonte, url feed, serve filtrare per "Varazze"?)
SOURCES = [
    ("IVG", "https://www.ivg.it/notizie-di-citta/varazze/feed/", False),
    ("IVG", "https://www.ivg.it/feed/", True),
    ("Genova24", "https://www.genova24.it/feed/", True),
    ("SavonaNews", "https://www.savonanews.it/rss.xml", True),
    ("Google News", "https://news.google.com/rss/search?q=Varazze+when:7d&hl=it&gl=IT&ceid=IT:it", False),
]
KEYWORDS = ["varazz", "alpicella", "castagnabuona", "invrea", "casanova di varazze", "pero di varazze"]
GIORNI_DA_TENERE = 30
MAX_NOTIZIE = 250

CATEGORIE = [
    ("Cronaca", ["incidente", "arrest", "carabinier", "polizia", "soccors", "furto", "rapina", "ferit", "morto", "morta",
                 "muore", "scompars", "incendio", "denunc", "guardia costiera", "maltempo", "allerta", "tromba",
                 "frana", "schianto", "investit", "truffa", "sequestr", "vigili del fuoco", "pompieri", "malore",
                 "annegat", "aggression", "droga", "lutto", "piange"]),
    ("Sport", ["calcio", "serie d", "eccellenza", "promozione", "partita", "campionato", "basket", "pallavolo",
               "volley", "regata", "nuoto", "allenatore", "gol", "torneo", "celle varazze", "ciclis", "maratona",
               "classifica", "pallanuoto", "tennis", "rugby", "atleti"]),
    ("Politica", ["sindaco", "consiglio comunale", "giunta", "assessor", "consiglier", "elezion", "opposizione",
                  "minoranza", "interrogazione", "partito", " pd", "lega", "fratelli d'italia", "centrodestra",
                  "centrosinistra"]),
    ("Eventi", ["festa", "sagra", "concerto", "mostra", "evento", "spettacolo", "festival", "manifestazione",
                "rassegna", "teatro", "cerimonia", "intitolazion", "fiera", "presentazione", "appuntament", "musica"]),
    ("Ambiente", ["rifiuti", "spiagg", "beigua", "parco", "ambiente", "alberi", "fung", "pulizia", "inquinament",
                  "depurat", "animal", "tartarug", "cinghial", "sentier", "mare "]),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (VarazzeOggi RSS reader)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def categoria(testo):
    t = " " + testo.lower() + " "
    for nome, parole in CATEGORIE:
        if any(p in t for p in parole):
            return nome
    return "Attualità"


def chiave(titolo):
    return re.sub(r"[^a-z0-9]", "", titolo.lower())[:70]


def leggi_feed(nome, url, filtra):
    out = []
    root = ET.fromstring(fetch(url))
    for it in root.iter("item"):
        titolo = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        desc = clean(it.findtext("description"))
        fonte = nome
        if nome == "Google News":
            src = it.find("source")
            if src is not None and src.text:
                fonte = src.text.strip()
                if titolo.endswith(" - " + fonte):
                    titolo = titolo[: -len(" - " + fonte)]
            desc = ""  # la descrizione di Google News ripete solo il titolo
        if not titolo or not link.startswith("http"):
            continue
        if filtra and not any(k in (titolo + " " + desc).lower() for k in KEYWORDS):
            continue
        try:
            quando = parsedate_to_datetime(it.findtext("pubDate")).astimezone(dt.timezone.utc)
        except Exception:
            quando = dt.datetime.now(dt.timezone.utc)
        if len(desc) > 280:
            desc = desc[:277].rsplit(" ", 1)[0] + "…"
        out.append({
            "title": titolo, "summary": desc, "url": link, "source": fonte,
            "category": categoria(titolo + " " + desc), "published": quando.isoformat(),
        })
    return out


def main():
    try:
        with open("news.json", encoding="utf-8") as f:
            vecchie = json.load(f).get("items", [])
    except Exception:
        vecchie = []

    per_chiave = {chiave(n["title"]): n for n in vecchie}
    nuove = 0
    for nome, url, filtra in SOURCES:
        try:
            items = leggi_feed(nome, url, filtra)
            print(f"{nome}: {len(items)} notizie da {url}")
        except Exception as e:
            print(f"{nome}: errore {e} ({url})")
            continue
        for n in items:
            k = chiave(n["title"])
            if k not in per_chiave:
                per_chiave[k] = n
                nuove += 1

    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=GIORNI_DA_TENERE)
    tutte = [n for n in per_chiave.values() if dt.datetime.fromisoformat(n["published"]) >= limite]
    tutte.sort(key=lambda n: n["published"], reverse=True)
    tutte = tutte[:MAX_NOTIZIE]

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump({"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "items": tutte},
                  f, ensure_ascii=False, indent=1)
    print(f"Notizie nuove: {nuove} - totale salvate: {len(tutte)}")


if __name__ == "__main__":
    main()
