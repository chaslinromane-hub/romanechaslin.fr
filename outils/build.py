"""
Génère le site (français + anglais) dans le dossier `site/` à partir de :
  - contenu/site.json      tous les textes en français
  - contenu/site.en.json   les textes traduits en anglais (le reste vient de site.json)
  - contenu/galeries.json  ordre des photos de chaque galerie
  - contenu/photos.json    infos des photos (favori, texte alternatif, dimensions…)
  - statique/              CSS, JS, polices, photos optimisées

Utilisation :
    python outils/build.py           génère le site
    python outils/build.py --serve   génère puis ouvre un aperçu sur http://localhost:8000
"""

from __future__ import annotations

import copy
import datetime as dt
import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CONTENU = RACINE / "contenu"
STATIQUE = RACINE / "statique"
SORTIE = RACINE / "site"


def lire(nom: str) -> dict:
    return json.loads((CONTENU / nom).read_text(encoding="utf-8"))


def fusionner(base, ajout):
    """Fusionne la traduction dans le contenu français (listes d'objets fusionnées par slug, cle ou photo)."""
    if isinstance(base, dict) and isinstance(ajout, dict):
        res = dict(base)
        for k, v in ajout.items():
            res[k] = fusionner(base[k], v) if k in base else v
        return res
    if isinstance(base, list) and isinstance(ajout, list) and base and all(isinstance(x, dict) for x in base + ajout):
        for cle in ("slug", "cle", "photo"):
            if all(cle in x for x in base + ajout):
                trad = {x[cle]: x for x in ajout}
                return [fusionner(x, trad[x[cle]]) if x[cle] in trad else x for x in base]
    return copy.deepcopy(ajout)


FR = lire("site.json")
EN = fusionner(FR, {k: v for k, v in lire("site.en.json").items() if not k.startswith("_")})
CONTENUS = {"fr": FR, "en": EN}
LANGUES = ("fr", "en")
PHOTOS = lire("photos.json")
GALERIES = lire("galeries.json")

# ---------------------------------------------------------------------------
# NOMS DES ARTISTES (page Concert) — affichés au survol des photos.
# Ils se complètent à la main dans : contenu/artistes-concert.json
# (chercher « À COMPLÉTER » : une ligne par photo, dans l'ordre de la galerie).
# ---------------------------------------------------------------------------
GALERIE_ARTISTES = "concert"
A_COMPLETER_NOM = "À COMPLÉTER"
ARTISTES = lire("artistes-concert.json") if (CONTENU / "artistes-concert.json").exists() else {}


def nom_artiste(pid: str) -> str:
    """Nom de l'artiste d'une photo de concert, ou "" s'il n'est pas encore renseigné."""
    nom = str(ARTISTES.get(pid, "")).strip()
    return "" if nom.upper() == A_COMPLETER_NOM else nom
SITE_URL = FR["url"]
NOM = FR["nom"]
ANNEE = dt.date.today().year
VERSION = dt.datetime.now().strftime("%Y%m%d%H%M")
AVERTISSEMENTS: list[str] = []

# Anciennes adresses de l'ancien site → nouvelle adresse (vide = accueil).
REDIRECTIONS = {"home/": ""}

CHEMINS = {
    "fr": {"accueil": "", "portfolio": "portfolio/", "about": "about/", "contact": "contact/",
           "mentions": "mentions-legales/", "404": "404.html"},
    "en": {"accueil": "en/", "portfolio": "en/portfolio/", "about": "en/about/", "contact": "en/contact/",
           "mentions": "en/legal-notice/", "404": "404.html"},
}


# ---------------------------------------------------------------------------
# Petits outils
# ---------------------------------------------------------------------------

def e(texte: str) -> str:
    """Échappe un texte pour le HTML (avec espace insécable avant ? ! : ; à la française)."""
    texte = re.sub(r" ([?!:;»])", "\u202f\\1", str(texte))
    texte = re.sub(r"(«) ", "\\1\u202f", texte)
    return html.escape(texte, quote=True)


def md(texte: str) -> str:
    """Échappe un texte et transforme *mot* en <em>mot</em> (mot en italique rose)."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(texte))


def slug(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", texte).strip("-")


def autre(lang: str) -> str:
    return "en" if lang == "fr" else "fr"


def galerie(slug_fr: str, lang: str) -> dict:
    return next(g for g in CONTENUS[lang]["galeries"] if g["slug"] == slug_fr)


def chemin(cle: str, lang: str) -> str:
    if cle.startswith("galerie:"):
        g = galerie(cle[8:], lang)
        return ("" if lang == "fr" else "en/") + g.get("url", g["slug"]) + "/"
    return CHEMINS[lang][cle]


class Ctx:
    """Contexte d'une page : langue, textes, et chemin relatif vers la racine du site."""

    def __init__(self, lang: str, cle: str):
        self.lang, self.cle = lang, cle
        self.S = CONTENUS[lang]
        self.T = self.S["interface"]
        self.chemin = chemin(cle, lang)
        self.r = "/" if cle == "404" else "../" * self.chemin.count("/")

    def lien(self, cle: str) -> str:
        return self.r + chemin(cle, self.lang)

    def nb(self, n: int) -> str:
        return f"{n} {self.T['photo'] if n == 1 else self.T['photos']}"


def photo(pid: str) -> dict:
    if pid not in PHOTOS:
        raise SystemExit(f"Photo inconnue dans contenu/photos.json : « {pid} »")
    return PHOTOS[pid]


def alt_photo(pid: str, lang: str) -> str:
    p = photo(pid)
    return p.get("alt_en", "") if lang == "en" else p.get("alt", "")


def srcset(pid: str, r: str, tailles: str = "sml") -> str:
    p = photo(pid)
    vus, morceaux = set(), []
    for s in tailles:
        if p[s] not in vus:
            vus.add(p[s])
            morceaux.append(f"{r}assets/photos/{pid}-{s}.webp {p[s]}w")
    return ", ".join(morceaux)


def img(pid: str, ctx: Ctx, sizes: str, alt: str = "", classe: str = "", eager: bool = False,
        position: str | None = None, attrs: str = "") -> str:
    p = photo(pid)
    r = ctx.r
    style = f' style="object-position:{e(position)}"' if position else ""
    chargement = 'fetchpriority="high"' if eager else 'loading="lazy"'
    cls = f' class="{classe}"' if classe else ""
    texte_alt = (alt or alt_photo(pid, ctx.lang)).strip()
    return (
        f'<img{cls} src="{r}assets/photos/{pid}-m.webp" srcset="{srcset(pid, r)}" sizes="{sizes}" '
        f'width="{p["w"]}" height="{p["h"]}" alt="{e(texte_alt)}" {chargement} decoding="async" draggable="false"{style}{attrs}>'
    )


# ---------------------------------------------------------------------------
# Icônes
# ---------------------------------------------------------------------------

ICONES = {
    "Instagram": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.8.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.9.9 1.4.2.4.4 1.1.4 2.2.1 1.3.1 1.6.1 4.8s0 3.6-.1 4.8c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.9.7-1.4.9-.4.2-1.1.4-2.2.4-1.3.1-1.6.1-4.8.1s-3.6 0-4.8-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.9-.9-1.4-.2-.4-.4-1.1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.8c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.9-.7 1.4-.9.4-.2 1.1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 1.8c-3.1 0-3.5 0-4.7.1-1.1.1-1.7.2-2.1.4-.5.2-.9.4-1.2.8-.4.4-.6.7-.8 1.2-.2.4-.3 1-.4 2.1-.1 1.2-.1 1.6-.1 4.7s0 3.5.1 4.7c.1 1.1.2 1.7.4 2.1.2.5.4.9.8 1.2.4.4.7.6 1.2.8.4.2 1 .3 2.1.4 1.2.1 1.6.1 4.7.1s3.5 0 4.7-.1c1.1-.1 1.7-.2 2.1-.4.5-.2.9-.4 1.2-.8.4-.4.6-.7.8-1.2.2-.4.3-1 .4-2.1.1-1.2.1-1.6.1-4.7s0-3.5-.1-4.7c-.1-1.1-.2-1.7-.4-2.1-.2-.5-.4-.9-.8-1.2-.4-.4-.7-.6-1.2-.8-.4-.2-1-.3-2.1-.4-1.2-.1-1.6-.1-4.7-.1zm0 3.1a4.9 4.9 0 1 1 0 9.8 4.9 4.9 0 0 1 0-9.8zm0 8a3.1 3.1 0 1 0 0-6.2 3.1 3.1 0 0 0 0 6.2zm6.2-8.2a1.1 1.1 0 1 1-2.3 0 1.1 1.1 0 0 1 2.3 0z"/></svg>',
    "Pinterest": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.08 3.16 9.42 7.62 11.17-.1-.95-.2-2.4.04-3.44l1.41-5.96s-.36-.72-.36-1.78c0-1.66.97-2.9 2.17-2.9 1.02 0 1.52.77 1.52 1.69 0 1.03-.66 2.57-.99 3.99-.29 1.19.6 2.17 1.77 2.17 2.13 0 3.77-2.25 3.77-5.49 0-2.86-2.06-4.87-5.01-4.87-3.41 0-5.41 2.56-5.41 5.2 0 1.03.39 2.14.89 2.74.1.12.11.22.08.35l-.33 1.36c-.05.22-.17.27-.4.16-1.5-.69-2.43-2.88-2.43-4.65 0-3.78 2.75-7.25 7.92-7.25 4.16 0 7.39 2.97 7.39 6.92 0 4.13-2.61 7.46-6.23 7.46-1.21 0-2.36-.63-2.75-1.38l-.75 2.85c-.27 1.04-1 2.35-1.5 3.15 1.13.35 2.31.53 3.55.53 6.63 0 12-5.37 12-12S18.63 0 12 0z"/></svg>',
    "TikTok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.6 2h-3.3v13.2a2.9 2.9 0 1 1-2.9-2.9c.3 0 .6 0 .9.1V9a6.3 6.3 0 1 0 5.3 6.2V8.6a7.9 7.9 0 0 0 4.6 1.5V6.8a4.6 4.6 0 0 1-4.6-4.6z"/></svg>',
    "LinkedIn": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9.75h4v11H3v-11zm6.5 0h3.8v1.5h.1c.5-1 1.8-2 3.8-2 4 0 4.8 2.6 4.8 6v5.5h-4v-4.9c0-1.2 0-2.7-1.6-2.7-1.7 0-1.9 1.3-1.9 2.6v5h-4v-11z"/></svg>',
}
FLECHE = '<svg class="fleche" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M1 8h13M9 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
EPINGLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>'
ICONE_GRILLE = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2 3h9v6H2zM13 3h5v6h-5zM2 11h5v6H2zM9 11h9v6H9z" fill="currentColor"/></svg>'
ICONE_FILM = '<svg viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" d="M1 3h18v14H1zM3 4.5h1.5v1.5H3zm3.5 0H8v1.5H6.5zm3.5 0h1.5v1.5H10zm3.5 0H15v1.5h-1.5zM3 14h1.5v1.5H3zm3.5 0H8v1.5H6.5zm3.5 0h1.5v1.5H10zm3.5 0H15v1.5h-1.5zM3 7.5h14v5H3z"/></svg>'
ICONE_AMPOULE = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2a5.5 5.5 0 0 0-3.3 9.9c.5.4.8 1 .8 1.6V14h5v-.5c0-.6.3-1.2.8-1.6A5.5 5.5 0 0 0 10 2zM7.5 15.5h5M8.5 17.5h3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>'
CERCLES = [
    "M55 5C82 4 97 21 96 49 95 79 74 96 47 95 19 94 3 75 4 47 5 22 24 6 61 9",
    "M46 6C73 3 96 18 97 47 98 77 77 95 50 96 22 97 4 79 3 51 2 26 18 8 52 4",
]


def reseaux(ctx: Ctx) -> str:
    items = "".join(
        f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener" aria-label="{e(x["nom"])} ({e(ctx.T["nouvel_onglet"])})">{ICONES.get(x["nom"], "")}</a></li>'
        for x in FR["reseaux"]
    )
    return f'<ul class="reseaux">{items}</ul>'


def instagram_url() -> str:
    return next((x["url"] for x in FR["reseaux"] if x["nom"] == "Instagram"), "#")


# ---------------------------------------------------------------------------
# Gabarit commun
# ---------------------------------------------------------------------------

def page(ctx: Ctx, *, titre: str, description: str, contenu: str, actif: str = "", sombre: bool = False,
         image_partage: str | None = None, extra_head: str = "", visionneuse: bool = False,
         type_page: str = "") -> str:
    T, S, r, lang = ctx.T, ctx.S, ctx.r, ctx.lang
    url = f"{SITE_URL}/{ctx.chemin}"
    image_url = f"{SITE_URL}/assets/partage/{image_partage or FR['image_partage']}.jpg"
    locale = {"fr": "fr_FR", "en": "en_GB"}

    alternates = ""
    if ctx.cle != "404":
        alternates = "".join(
            f'\n<link rel="alternate" hreflang="{l}" href="{SITE_URL}/{chemin(ctx.cle, l)}">' for l in LANGUES
        ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{chemin(ctx.cle, "fr")}">'

    def lien_nav(cle):
        courant = ' aria-current="page"' if actif == cle else ""
        return f'<a href="{ctx.lien(cle)}"{courant}>{e(T[cle])}</a>'

    nav = "".join(lien_nav(c) for c in ("portfolio", "about", "contact"))
    lien_langue = ctx.r + chemin(ctx.cle if ctx.cle != "404" else "accueil", autre(lang))
    langue = (f'<a class="langue" href="{lien_langue}" hreflang="{autre(lang)}" lang="{autre(lang)}" '
              f'aria-label="{e(T["autre_langue_aria"])}">{e(T["autre_langue_court"])}</a>')
    themes_pied = "".join(f'<li><a href="{ctx.lien("galerie:" + g["slug"])}">{e(g["nom"])}</a></li>' for g in S["galeries"])
    reseaux_pied = "".join(f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["nom"])}</a></li>' for x in FR["reseaux"])

    lb = ""
    if visionneuse:
        lb = f"""
<dialog class="visionneuse" aria-label="{e(T['visionneuse'])}">
  <div class="visionneuse__haut">
    <p class="visionneuse__compteur" aria-live="polite"><b data-lb-index>1</b> / <span data-lb-total>1</span><span class="visionneuse__titre" data-lb-titre></span></p>
    <button class="visionneuse__fermer" type="button" data-lb-fermer>{e(T['fermer'])} <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.5"/></svg></button>
  </div>
  <div class="visionneuse__scene" data-lb-scene>
    <img alt="" data-lb-img draggable="false">
    <button class="visionneuse__nav visionneuse__nav--prec" type="button" data-lb-prec aria-label="{e(T['precedente'])}"><span><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M13 3l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span></button>
    <button class="visionneuse__nav visionneuse__nav--suiv" type="button" data-lb-suiv aria-label="{e(T['suivante'])}"><span><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 3l7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span></button>
  </div>
</dialog>"""

    data_page = f' data-page="{type_page}"' if type_page else ""
    return f"""<!doctype html>
<html lang="{lang}"{data_page}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titre)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="index, follow, max-image-preview:large, noai, noimageai">
<meta name="tdm-reservation" content="1">
<link rel="canonical" href="{e(url)}">{alternates}
<meta property="og:type" content="website">
<meta property="og:locale" content="{locale[lang]}">
<meta property="og:locale:alternate" content="{locale[autre(lang)]}">
<meta property="og:site_name" content="{e(NOM)}">
<meta property="og:title" content="{e(titre)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(image_url)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#feefdd">
<link rel="icon" href="{r}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{r}assets/apple-touch-icon.png">
<link rel="preload" href="{r}assets/polices/instrument-serif.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{r}assets/polices/inter-tight-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{r}assets/css/style.css?v={VERSION}">
<script>(function(d){{d.classList.add('js');try{{if(d.dataset.page==='galerie'&&localStorage.getItem('rc-lumiere')==='eteinte')d.classList.add('lumiere-eteinte')}}catch(x){{}}}})(document.documentElement)</script>
<script src="{r}assets/js/main.js?v={VERSION}" defer></script>{extra_head}
</head>
<body class="{'page-sombre' if sombre else ''}">
<a class="lien-evitement" href="#contenu">{e(T['aller_contenu'])}</a>
<header class="entete">
  <div class="conteneur entete__inner">
    <a class="entete__nom" href="{ctx.lien('accueil')}" aria-label="{e(NOM)}, {e(T['accueil_aria'])}">{e(NOM)}</a>
    <nav class="entete__nav" aria-label="{e(T['nav_principale'])}">{nav}</nav>
    <div class="entete__droite">{reseaux(ctx)}{langue}</div>
    <button class="menu-bouton" type="button" aria-expanded="false" aria-controls="menu-mobile" aria-label="{e(T['ouvrir_menu'])}" data-ouvrir="{e(T['ouvrir_menu'])}" data-fermer="{e(T['fermer_menu'])}"><span></span><span></span></button>
  </div>
</header>
<div class="menu-mobile" id="menu-mobile">
  <nav aria-label="{e(T['nav_mobile'])}"><a href="{ctx.lien('accueil')}"{' aria-current="page"' if actif == 'accueil' else ''}>{e(T['accueil'])}</a>{nav}</nav>
  <div class="menu-mobile__bas">{reseaux(ctx)}<a class="langue langue--long" href="{lien_langue}" hreflang="{autre(lang)}" lang="{autre(lang)}">{e(T['autre_langue'])}</a></div>
</div>
<main id="contenu">
{contenu}
</main>
<footer class="pied">
  <div class="conteneur">
    <div class="pied__haut">
      <div class="pied__marque">
        <a class="pied__nom" href="{ctx.lien('accueil')}">{e(NOM)}</a>
        <p class="pied__baseline">{e(S['accueil']['heros']['accroche_titre'])}. {e(S['accueil']['heros']['accroche'])}</p>
      </div>
      <div><h2>{e(T['le_site'])}</h2><ul><li><a href="{ctx.lien('accueil')}">{e(T['accueil'])}</a></li><li><a href="{ctx.lien('portfolio')}">{e(T['portfolio'])}</a></li><li><a href="{ctx.lien('about')}">{e(T['about'])}</a></li><li><a href="{ctx.lien('contact')}">{e(T['contact'])}</a></li></ul></div>
      <div><h2>{e(T['thematiques'])}</h2><ul>{themes_pied}</ul></div>
      <div><h2>{e(T['me_suivre'])}</h2><ul>{reseaux_pied}</ul></div>
    </div>
    <div class="pied__bas">
      <p>© {ANNEE} {e(NOM)}. {e(T['droits'])}</p>
      <p><a href="{ctx.lien('mentions')}">{e(T['mentions'])}</a> · <a href="{lien_langue}" hreflang="{autre(lang)}" lang="{autre(lang)}">{e(T['autre_langue'])}</a></p>
    </div>
  </div>
</footer>{lb}
</body>
</html>
"""


def vague(texte: str, ident: str) -> str:
    """Texte ondulé qui défile (repris du site d'origine)."""
    return (
        f'<svg class="vague" data-vague aria-hidden="true" focusable="false">'
        f'<defs><path id="{ident}" d=""/></defs>'
        f'<text><textPath href="#{ident}" data-texte="{e(texte)}">{e(texte)}</textPath></text></svg>'
    )


def appel(ctx: Ctx) -> str:
    C = ctx.S["galerie_commun"]
    return f"""
<section class="sombre appel" aria-labelledby="titre-appel">
  <div class="conteneur">
    <h2 id="titre-appel" class="apparait">{md(C['appel_titre'])}</h2>
    <a class="bouton" href="{ctx.lien('contact')}">{e(C['appel_bouton'])} {FLECHE}</a>
  </div>
</section>"""


def carte(g: dict, ctx: Ctx, sizes: str, champ: str = "vignette", accroche: bool = False) -> str:
    pos = g.get("couverture_position") if champ == "couverture" else None
    texte_accroche = f'<span class="carte__accroche">{e(g["titre"])}</span>' if accroche else ""
    return (
        f'<a class="carte apparait" href="{ctx.lien("galerie:" + g["slug"])}">{img(g[champ], ctx, sizes, alt=" ", position=pos)}'
        f'<span class="carte__texte"><span><span class="carte__nom">{e(g["nom"])}</span>{texte_accroche}</span>'
        f'<span class="carte__compte">{ctx.nb(len(GALERIES.get(g["slug"], [])))}</span></span></a>'
    )


# ---------------------------------------------------------------------------
# Galeries : grille justifiée, planche contact, barre d'outils
# ---------------------------------------------------------------------------

def legende(nom: str) -> str:
    """Nom de l'artiste révélé mot à mot au survol (chaque mot monte depuis un masque)."""
    mots = " ".join(f'<span class="mot"><span style="--i:{i}">{e(m)}</span></span>' for i, m in enumerate(nom.split()))
    return f'<span class="galerie__legende" aria-hidden="true"><span class="galerie__nom">{mots}</span></span>'


def items_galerie(ids: list[str], ctx: Ctx, alt_base: str, avec_artistes: bool = False) -> str:
    r, T = ctx.r, ctx.T
    items = []
    for n, pid in enumerate(ids):
        p = photo(pid)
        ratio = p["w"] / p["h"]
        sizes = f"(max-width: 560px) {round(ratio * 195)}px, (max-width: 1540px) {ratio * 34:.1f}vw, {round(ratio * 520)}px"
        alt = alt_photo(pid, ctx.lang) or f"{alt_base} — {n + 1} {T['sur']} {len(ids)}"
        nom = nom_artiste(pid) if avec_artistes else ""
        if nom:
            alt = f"{nom} — {alt}"
        lb_srcset = ", ".join(f"{r}assets/photos/{pid}-{s}.webp {p[s]}w" for s in "ml" if s == "m" or p["l"] != p["m"])
        attr_nom = f' data-legende="{e(nom)}"' if nom else ""
        items.append(
            f'<a class="galerie__item" href="#photo-{n + 1}" data-index="{n}" style="--r:{ratio:.4f};--c:{p["c"]}" '
            f'data-src="{r}assets/photos/{pid}-l.webp" data-srcset="{lb_srcset}" data-ratio="{ratio:.4f}"{attr_nom}>'
            f'{img(pid, ctx, sizes, alt=alt)}{legende(nom) if nom else ""}</a>'
        )
    return "".join(items)


def planche(ids: list[str], ctx: Ctx, alt_base: str) -> str:
    """Planche contact façon argentique : bandes de film, numéros de vue, favoris entourés au crayon gras."""
    vues = []
    for n, pid in enumerate(ids):
        p = photo(pid)
        num = n + 1
        marque = f"<span>{e(NOM.upper())}</span>" if num % 6 == 1 else ""
        bord = f'<span class="planche__bord" aria-hidden="true"><span>› {num}</span>{marque}<span>{num}A</span></span>'
        cercle = ""
        if p.get("favori"):
            rot = (n * 37) % 15 - 7
            cercle = (f'<svg class="planche__cercle" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" '
                      f'style="--rot:{rot}deg"><path pathLength="1" d="{CERCLES[n % 2]}"/></svg>')
        alt = alt_photo(pid, ctx.lang) or f"{alt_base} — {num} {ctx.T['sur']} {len(ids)}"
        vignette = img(pid, ctx, "(max-width: 760px) 34vw, 220px", alt=alt)
        vues.append(
            f'<a class="planche__vue{" est-favori" if p.get("favori") else ""}" href="#photo-{num}" data-index="{n}">'
            f'<span class="planche__image">{vignette}</span>{bord}{cercle}</a>'
        )
    return f'<div class="planche" data-planche hidden>{"".join(vues)}</div>'


def barre_outils(ctx: Ctx) -> str:
    T = ctx.T
    return f"""
  <div class="outils">
    <div class="vues" role="group" aria-label="{e(T['affichage'])}">
      <button type="button" data-vue="galerie" aria-pressed="true">{ICONE_GRILLE}<span>{e(T['vue_galerie'])}</span></button>
      <button type="button" data-vue="planche" aria-pressed="false">{ICONE_FILM}<span>{e(T['vue_planche'])}</span></button>
    </div>
    <button type="button" class="lumiere" data-lumiere aria-pressed="false" data-eteindre="{e(T['eteindre'])}" data-rallumer="{e(T['rallumer'])}">{ICONE_AMPOULE}<span>{e(T['eteindre'])}</span></button>
  </div>"""


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_accueil(lang: str) -> str:
    ctx = Ctx(lang, "accueil")
    S, T = ctx.S, ctx.T
    A = S["accueil"]
    H = A["heros"]

    lettres = "".join(f'<span class="lettre" style="--i:{i}">{e(c)}</span>' for i, c in enumerate(H["titre"]))
    diapos, boutons = [], []
    for i, d in enumerate(H["diapos"]):
        g = galerie(d["galerie"], lang)
        diapos.append(
            f'<figure class="heros__diapo{" est-active" if i == 0 else ""}" data-diapo>'
            f'{img(d["photo"], ctx, "100vw", alt=g["alt"], eager=i == 0, position=d.get("position"))}</figure>'
        )
        boutons.append(
            f'<li><button type="button" data-diapo-bouton aria-pressed="{"true" if i == 0 else "false"}">{e(d.get("libelle", g["nom"]))}</button></li>'
        )

    RG, TH, P, I = A["regard"], A["themes"], A["passion"], A["instagram"]
    liste, apercus = [], []
    for i, g in enumerate(S["galeries"]):
        liste.append(
            f'<li><a href="{ctx.lien("galerie:" + g["slug"])}" data-theme="{i}">'
            f'<span class="themes__vignette">{img(g["vignette"], ctx, "64px", alt=" ")}</span>'
            f'<span class="themes__nom">{e(g["nom"])}</span>'
            f'<span class="themes__compte">{ctx.nb(len(GALERIES.get(g["slug"], [])))}</span></a></li>'
        )
        apercus.append(img(g["vignette"], ctx, "(max-width: 860px) 1px, 40vw", alt=" ", classe="est-active" if i == 0 else "",
                           attrs=f' data-apercu="{i}"'))
    insta = "".join(
        f'<a href="{e(instagram_url())}" target="_blank" rel="noopener" aria-label="{e(T["voir_instagram"])}">{img(pid, ctx, "260px", alt=" ")}</a>'
        for pid in I["photos"]
    )
    paragraphes = "".join(f"<p>{e(x)}</p>" for x in P["paragraphes"])

    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": f"{NOM} — {S['metier']}",
        "url": f"{SITE_URL}/{ctx.chemin}",
        "image": f"{SITE_URL}/assets/partage/{FR['image_partage']}.jpg",
        "description": S["description"],
        "address": {"@type": "PostalAddress", "addressLocality": FR["ville"], "addressRegion": S["region"], "addressCountry": "FR"},
        "areaServed": FR["ville"],
        "founder": {"@type": "Person", "name": NOM, "jobTitle": S["metier"]},
        "sameAs": [x["url"] for x in FR["reseaux"]],
    }, ensure_ascii=False)

    contenu = f"""
<section class="heros" aria-label="{e(H['titre'])}">
  <div class="heros__cadre">
    {''.join(diapos)}
    <h1 class="heros__titre"><span class="visuellement-cache">{e(NOM)}, {e(H['accroche_titre'])} — </span><span aria-hidden="true">{lettres}</span><span class="visuellement-cache">{e(H['titre'])}</span></h1>
    <div class="heros__bas">
      <p class="heros__accroche"><strong>{e(H['accroche_titre'])}</strong>{e(H['accroche'])}</p>
      <ul class="heros__themes" aria-label="{e(T['choisir_diapo'])}">{''.join(boutons)}</ul>
    </div>
  </div>
</section>

<section class="regard" aria-labelledby="titre-regard">
  <h2 class="visuellement-cache" id="titre-regard">{e(RG['vague'])}</h2>
  {vague(RG['vague'], 'vague-regard')}
  <div class="conteneur regard__grille">
    <div class="regard__photo apparait">{img(RG['photo'], ctx, "(max-width: 760px) 100vw, 40vw", alt=T['musicien_alt'])}</div>
    <div class="regard__texte apparait">
      <p>{e(RG['texte'])}</p>
      <a class="bouton" href="{ctx.lien('portfolio')}">{e(RG['bouton'])} {FLECHE}</a>
    </div>
  </div>
</section>

<section class="section themes" aria-labelledby="titre-themes">
  <div class="conteneur">
    <div class="themes__tete apparait">
      <h2 id="titre-themes">{e(TH['titre'])}</h2>
      <a href="{ctx.lien('portfolio')}">{e(TH['lien'])}</a>
    </div>
    <div class="themes__grille">
      <ul class="themes__liste" data-themes>{''.join(liste)}</ul>
      <div class="themes__apercu" aria-hidden="true">{''.join(apercus)}</div>
    </div>
  </div>
</section>

<section class="section passion" aria-labelledby="titre-passion" style="padding-top:0">
  <div class="conteneur">
    <div class="passion__photo apparait">{img(P['photo'], ctx, "100vw", alt=T['passion_alt'])}</div>
    <div class="passion__texte apparait">
      <h2 id="titre-passion">{e(P['titre'])}</h2>
      <div>
        <span class="etiquette">{e(P['etiquette'])}</span>
        {paragraphes}
        <p style="margin-top:1.5rem"><a class="bouton bouton--contour" href="{ctx.lien('about')}">{e(P['lien'])} {FLECHE}</a></p>
      </div>
    </div>
  </div>
</section>

<section class="sombre insta" aria-labelledby="titre-insta">
  <h2 class="visuellement-cache" id="titre-insta">{e(I['vague'])}</h2>
  {vague(I['vague'], 'vague-insta')}
  <div class="insta__photos">{insta}</div>
  <a class="bouton bouton--contour" href="{e(instagram_url())}" target="_blank" rel="noopener">{e(I['bouton'])} {FLECHE}</a>
</section>
"""
    return page(ctx, titre=A["titre_seo"], description=S["description"], contenu=contenu, actif="accueil",
                extra_head=f'\n<script type="application/ld+json">{json_ld}</script>')


def page_portfolio(lang: str) -> str:
    ctx = Ctx(lang, "portfolio")
    P = ctx.S["portfolio"]
    cartes = "".join(
        carte(g, ctx, "(max-width: 760px) 100vw, " + ("100vw" if i == 0 else "50vw"), champ="couverture", accroche=True)
        for i, g in enumerate(ctx.S["galeries"])
    )
    contenu = f"""
<section class="sombre bandeau">
  <div class="conteneur">
    <span class="etiquette">{e(P['etiquette'])}</span>
    <h1>{md(P['titre'])}</h1>
  </div>
</section>
<section class="intro conteneur"><p>{e(P['intro'])}</p></section>
<div class="conteneur portfolio-grille">{cartes}</div>
{appel(ctx)}
"""
    return page(ctx, titre=P["titre_seo"], description=P["description"], contenu=contenu, actif="portfolio", sombre=True)


def page_galerie(g: dict, lang: str) -> str:
    ctx = Ctx(lang, "galerie:" + g["slug"])
    S = ctx.S
    C = S["galerie_commun"]
    ids = GALERIES.get(g["slug"], [])
    idx = [x["slug"] for x in S["galeries"]].index(g["slug"])
    autres = [S["galeries"][(idx + k) % len(S["galeries"])] for k in (1, 2, 3)]
    cartes = "".join(carte(a, ctx, "(max-width: 760px) 50vw, 33vw") for a in autres)

    contenu = f"""
<section class="sombre bandeau">
  <div class="conteneur">
    <span class="etiquette">{e(g['nom'])} · {ctx.nb(len(ids))}</span>
    <h1>{md(g['titre'])}</h1>
  </div>
</section>
<section class="intro conteneur">
  <p>{e(g['intro'])}</p>
  <a class="bouton bouton--contour" href="{ctx.lien('contact')}">{e(C['bouton'])} {FLECHE}</a>
</section>
<section class="conteneur galerie-zone" aria-label="{e(ctx.T['galerie_de'])} {e(g['nom'])}">
  {barre_outils(ctx)}
  <div class="galerie" data-galerie data-titre="{e(g['nom'])}">{items_galerie(ids, ctx, g['alt'], avec_artistes=g['slug'] == GALERIE_ARTISTES)}</div>
  {planche(ids, ctx, g['alt'])}
</section>
<section class="autres conteneur" aria-labelledby="titre-autres">
  <h2 id="titre-autres" class="apparait">{e(C['autres_titre'])}</h2>
  <div class="cartes">{cartes}</div>
</section>
{appel(ctx)}
"""
    return page(ctx, titre=g["titre_seo"], description=g["description"], contenu=contenu, actif="portfolio",
                sombre=True, image_partage=g["couverture"], visionneuse=True, type_page="galerie")


def page_about(lang: str) -> str:
    ctx = Ctx(lang, "about")
    A = ctx.S["about"]
    paragraphes = "".join(f"<p>{e(x)}</p>" for x in A["paragraphes"])
    faits = "".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in A["faits"])
    contenu = f"""
<div class="conteneur apropos">
  <div class="apropos__photo">{img(A['photo'], ctx, "(max-width: 760px) 100vw, 40vw", alt=ctx.T['romane_alt'], eager=True)}</div>
  <div class="apropos__texte">
    <h1>{md(A['titre'])}</h1>
    {paragraphes}
    <dl class="faits">{faits}</dl>
    <p>{e(A['conclusion'])}</p>
    <a class="bouton" href="{ctx.lien('contact')}">{e(A['bouton'])} {FLECHE}</a>
  </div>
</div>
"""
    return page(ctx, titre=A["titre_seo"], description=A["description"], contenu=contenu, actif="about",
                image_partage=A["photo"])


def page_contact(lang: str) -> str:
    ctx = Ctx(lang, "contact")
    S, T = ctx.S, ctx.T
    C, K = S["page_contact"], S["contact"]
    # Envoi des messages par FormSubmit : adresse e-mail de réception, puis (après activation)
    # le code fourni par FormSubmit pour la masquer. Réglage : contenu/site.json → contact.formsubmit
    cible = FR["contact"].get("formsubmit", "").strip()
    action = f"https://formsubmit.co/{cible}" if cible else "#"
    oblig = f'<span>({e(T["obligatoire"])})</span>'
    options = "".join(f'<option data-cle="{e(t["cle"])}">{e(t["nom"])}</option>' for t in K["types_projet"])
    contenu = f"""
<div class="conteneur contact">
  <div class="contact__infos">
    <h1>{md(C['titre'])}</h1>
    <p>{e(C['texte'])}</p>
    <p class="contact__lieu">{EPINGLE} {e(C['lieu'])}</p>
    {reseaux(ctx)}
  </div>
  <form class="formulaire" action="{e(action)}" method="post" data-formulaire
        data-cible="{e(cible)}" data-succes="{e(C['succes'])}" data-erreur="{e(C['erreur'])}"
        data-non-configure="{e(C['non_configure'])}" data-activation="{e(C['activation'])}" data-envoi="{e(T['envoi'])}">
    <input type="hidden" name="_subject" value="{e(K['sujet_mail'])}">
    <input type="hidden" name="_template" value="table">
    <input type="hidden" name="_next" value="{SITE_URL}/{ctx.chemin}?envoye=1">
    <div class="champ champ--pot" aria-hidden="true"><label>{e(T['anti_robot'])} <input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></div>
    <div class="champ"><label for="prenom">{e(T['prenom'])} {oblig}</label><input id="prenom" name="prenom" data-libelle="{e(T['prenom'])}" autocomplete="given-name" required></div>
    <div class="champ"><label for="nom">{e(T['nom'])} {oblig}</label><input id="nom" name="nom" data-libelle="{e(T['nom'])}" autocomplete="family-name" required></div>
    <div class="champ"><label for="email">{e(T['email'])} {oblig}</label><input id="email" name="email" type="email" autocomplete="email" required></div>
    <div class="champ"><label for="type">{e(T['type_projet'])}</label><select id="type" name="type_projet" data-libelle="{e(T['type_projet'])}"><option value="">{e(T['choisir'])}</option>{options}</select></div>
    <div class="champ champ--large"><label for="message">{e(T['message'])} {oblig}</label><textarea id="message" name="message" data-libelle="{e(T['message'])}" required></textarea></div>
    <div class="formulaire__envoi">
      <button class="bouton" type="submit">{e(T['envoyer'])} {FLECHE}</button>
      <p class="formulaire__statut" role="status" data-statut></p>
    </div>
  </form>
</div>
"""
    return page(ctx, titre=C["titre_seo"], description=C["description"], contenu=contenu, actif="contact")


def page_mentions(lang: str) -> str:
    ctx = Ctx(lang, "mentions")
    M = FR["mentions"]
    contact = f'<a href="{ctx.lien("contact")}">'

    def marque(x):
        return f"<mark>{x}</mark>"

    if lang == "fr":
        statut = e(M["statut"]) if M["statut"] else marque("Statut à compléter (ex. : entrepreneur individuel)")
        siret = e(M["siret"]) if M["siret"] else marque("SIRET à compléter")
        corps = f"""
  <h1>Mentions légales</h1>
  <h2>Éditrice du site</h2>
  <p>{e(NOM)}, photographe — {statut}<br>SIRET : {siret}<br>Basée à {e(FR['ville'])}, France<br>Contact : via le {contact}formulaire de contact</a></p>
  <h2>Hébergement</h2>
  <p>{e(M['hebergeur'])}</p>
  <h2>Propriété intellectuelle</h2>
  <p>L’ensemble des photographies présentes sur ce site sont la propriété exclusive de {e(NOM)} et sont protégées par le Code de la propriété intellectuelle. Toute reproduction, diffusion ou utilisation, même partielle, sans autorisation écrite préalable est interdite.</p>
  <h2>Fouille de textes et de données, intelligence artificielle</h2>
  <p>Conformément à l’article L. 122-5-3 du Code de la propriété intellectuelle, l’autrice s’oppose à toute fouille de textes et de données des contenus de ce site, notamment pour l’entraînement de systèmes d’intelligence artificielle. Cette opposition est également exprimée de manière lisible par machine (fichiers robots.txt et tdmrep.json).</p>
  <h2>Données personnelles</h2>
  <p>Les informations envoyées via le formulaire de contact (nom, e-mail, message) servent uniquement à répondre à votre demande. Elles sont transmises par le service FormSubmit et ne sont ni revendues ni utilisées à des fins commerciales. Vous pouvez demander leur suppression à tout moment via le formulaire de contact.</p>
  <h2>Cookies</h2>
  <p>Ce site ne dépose aucun cookie et n’utilise aucun outil de mesure d’audience. Seuls vos choix d’affichage (lumière, planche contact) sont mémorisés dans votre navigateur.</p>"""
        titre, desc = f"Mentions légales — {NOM}", f"Mentions légales du site de {NOM}, photographe à {FR['ville']}."
    else:
        statut_en = M.get("statut_en") or M["statut"]
        statut = e(statut_en) if statut_en else marque("Legal status to be completed")
        siret = e(M["siret"]) if M["siret"] else marque("SIRET number to be completed")
        corps = f"""
  <h1>Legal notice</h1>
  <p><em>This translation is provided for convenience; the French version prevails.</em></p>
  <h2>Publisher</h2>
  <p>{e(NOM)}, photographer — {statut}<br>SIRET: {siret}<br>Based in {e(FR['ville'])}, France<br>Contact: via the {contact}contact form</a></p>
  <h2>Hosting</h2>
  <p>GitHub, Inc. — 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA — pages.github.com</p>
  <h2>Intellectual property</h2>
  <p>All photographs on this website are the exclusive property of {e(NOM)} and are protected by French intellectual property law. Any reproduction, distribution or use, even partial, without prior written permission is prohibited.</p>
  <h2>Text and data mining, artificial intelligence</h2>
  <p>In accordance with Article L. 122-5-3 of the French Intellectual Property Code, the author opts out of any text and data mining of this website’s content, including for training artificial intelligence systems. This reservation is also expressed in machine-readable form (robots.txt and tdmrep.json files).</p>
  <h2>Personal data</h2>
  <p>Information sent through the contact form (name, email, message) is used only to reply to your request. It is transmitted by the FormSubmit service and is never sold or used for marketing. You can ask for it to be deleted at any time through the contact form.</p>
  <h2>Cookies</h2>
  <p>This website sets no cookies and uses no analytics. Only your display choices (lights, contact sheet) are remembered in your browser.</p>"""
        titre, desc = f"Legal notice — {NOM}", f"Legal notice for the website of {NOM}, photographer in {FR['ville']}, France."
    contenu = f'<div class="conteneur page-texte etroit">{corps}\n</div>'
    return page(ctx, titre=titre, description=desc, contenu=contenu)


def page_404() -> str:
    ctx = Ctx("fr", "404")
    contenu = f"""
<div class="conteneur page-404">
  <div>
    <h1>404</h1>
    <p>{e(FR['interface']['titre_404'])}</p>
    <p lang="en">{e(EN['interface']['titre_404'])}</p>
    <p style="margin-top:1.5rem"><a class="bouton" href="/portfolio/">{e(FR['interface']['bouton_404'])} {FLECHE}</a></p>
  </div>
</div>
"""
    return page(ctx, titre=f"Page introuvable — {NOM}", description=FR["description"], contenu=contenu)


# ---------------------------------------------------------------------------
# Fichiers annexes
# ---------------------------------------------------------------------------

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#36413e"/><text x="32" y="46" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-style="italic" font-size="40" fill="#7f7eff">R</text></svg>
"""

# Robots d'entraînement d'IA refusés (les moteurs de recherche, eux, restent bienvenus).
ROBOTS_IA = ["GPTBot", "Google-Extended", "CCBot", "ClaudeBot", "anthropic-ai", "Applebot-Extended",
             "meta-externalagent", "Bytespider", "cohere-ai", "Diffbot", "ImagesiftBot", "Omgilibot", "Timpibot"]


def robots() -> str:
    ia = "\n".join(f"User-agent: {b}" for b in ROBOTS_IA)
    return (f"# Moteurs de recherche : bienvenus\nUser-agent: *\nAllow: /\n\n"
            f"# Robots d'entraînement d'intelligence artificielle : refusés\n{ia}\nDisallow: /\n\n"
            f"Sitemap: {SITE_URL}/sitemap.xml\n")


def sitemap(chemins: list[str]) -> str:
    aujourdhui = dt.date.today().isoformat()
    urls = "".join(f"<url><loc>{SITE_URL}/{c}</loc><lastmod>{aujourdhui}</lastmod></url>" for c in chemins)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'


def copier_statique() -> None:
    """Copie statique/ vers site/assets/ en ne recopiant que ce qui a changé."""
    cible_racine = SORTIE / "assets"
    for source in STATIQUE.rglob("*"):
        if source.is_dir():
            continue
        cible = cible_racine / source.relative_to(STATIQUE)
        if cible.exists() and cible.stat().st_size == source.stat().st_size and cible.stat().st_mtime >= source.stat().st_mtime:
            continue
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, cible)


def images_partage() -> None:
    """Crée les images de partage (réseaux sociaux), signées, en JPEG 1200×630."""
    try:
        from PIL import Image, ImageOps
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from photos import signature
    except ImportError:
        print("  (Pillow absent : images de partage non générées)")
        return
    exif, _ = signature()
    dossier = SORTIE / "assets" / "partage"
    dossier.mkdir(parents=True, exist_ok=True)
    pids = {FR["image_partage"], FR["about"]["photo"], *(g["couverture"] for g in FR["galeries"])}
    for pid in pids:
        source = STATIQUE / "photos" / f"{pid}-l.webp"
        cible = dossier / f"{pid}.jpg"
        if cible.exists() and cible.stat().st_mtime >= source.stat().st_mtime:
            continue
        with Image.open(source) as im:
            ImageOps.fit(im.convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.35)).save(
                cible, "JPEG", quality=84, optimize=True, exif=exif)


def verifier() -> None:
    """Liste ce qui reste à compléter avant la mise en ligne."""
    if not FR["mentions"]["statut"] or not FR["mentions"]["siret"]:
        AVERTISSEMENTS.append("mentions légales : statut et/ou SIRET (contenu/site.json → mentions)")
    cible = FR["contact"].get("formsubmit", "").strip()
    if not cible:
        AVERTISSEMENTS.append("formulaire de contact : adresse de réception FormSubmit (contenu/site.json → contact.formsubmit)")
    elif "@" in cible:
        AVERTISSEMENTS.append("formulaire de contact : après activation, remplacer l'adresse e-mail par le code reçu de "
                              "FormSubmit pour la masquer aux robots (contenu/site.json → contact.formsubmit)")
    manquants = [pid for pid in GALERIES.get(GALERIE_ARTISTES, []) if not nom_artiste(pid)]
    if manquants:
        AVERTISSEMENTS.append(f"noms d'artistes : {len(manquants)} « {A_COMPLETER_NOM} » sur "
                              f"{len(GALERIES[GALERIE_ARTISTES])} photos (contenu/artistes-concert.json)")


# ---------------------------------------------------------------------------

def ecrire(chemin_fichier: str, contenu: str) -> None:
    fichier = SORTIE / chemin_fichier
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(contenu, encoding="utf-8")


def construire() -> None:
    SORTIE.mkdir(exist_ok=True)
    pages = {"404.html": page_404()}
    for lang in LANGUES:
        pages[chemin("accueil", lang) + "index.html"] = page_accueil(lang)
        pages[chemin("portfolio", lang) + "index.html"] = page_portfolio(lang)
        pages[chemin("about", lang) + "index.html"] = page_about(lang)
        pages[chemin("contact", lang) + "index.html"] = page_contact(lang)
        pages[chemin("mentions", lang) + "index.html"] = page_mentions(lang)
        for g in CONTENUS[lang]["galeries"]:
            pages[chemin("galerie:" + g["slug"], lang) + "index.html"] = page_galerie(g, lang)
    for chemin_fichier, contenu in pages.items():
        ecrire(chemin_fichier, contenu)

    # Anciennes adresses Squarespace sans équivalent : petite page qui redirige vers la bonne.
    for ancienne, nouvelle in REDIRECTIONS.items():
        vers = "../" * ancienne.count("/") + nouvelle
        ecrire(ancienne + "index.html", (
            f'<!doctype html>\n<html lang="fr"><head><meta charset="utf-8"><title>{e(NOM)}</title>'
            f'<meta name="robots" content="noindex"><link rel="canonical" href="{SITE_URL}/{nouvelle}">'
            f'<meta http-equiv="refresh" content="0; url={vers}"><script>location.replace("{vers}")</script></head>'
            f'<body><a href="{vers}">{e(NOM)}</a></body></html>\n'))

    exclus = {chemin("mentions", l) + "index.html" for l in LANGUES} | {"404.html"}
    ecrire("sitemap.xml", sitemap([c.replace("index.html", "") for c in pages if c not in exclus]))
    ecrire("robots.txt", robots())
    ecrire(".well-known/tdmrep.json", json.dumps([{"location": "/", "tdm-reservation": 1}], indent=2) + "\n")
    ecrire("favicon.svg", FAVICON)
    ecrire(".nojekyll", "")
    copier_statique()
    images_partage()
    verifier()
    print(f"Site généré dans {SORTIE} ({len(pages)} pages).")
    if AVERTISSEMENTS:
        print("À compléter avant la mise en ligne :")
        for a in AVERTISSEMENTS:
            print(f"  - {a}")


def servir(port: int = 8000) -> None:
    import functools
    import http.server

    gestionnaire = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SORTIE))
    print(f"Aperçu : http://localhost:{port}  (Ctrl+C pour arrêter)")
    http.server.ThreadingHTTPServer(("", port), gestionnaire).serve_forever()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    construire()
    if "--serve" in sys.argv:
        servir()
