"""
Optimisation des photos du site.

Chaque photo est convertie en WebP en trois tailles (petite, moyenne, grande),
convertie en sRGB, débarrassée de ses métadonnées d'origine (EXIF, GPS…),
puis signée (auteur, copyright) et enregistrée dans `statique/photos/`.
Ses dimensions et sa couleur moyenne (affichée pendant le chargement)
sont notées dans `contenu/photos.json`.

Ajouter des photos à une galerie :

    python outils/photos.py ajouter concert chemin/vers/photo1.jpg chemin/vers/dossier/

Les nouvelles photos sont ajoutées à la fin de la galerie dans
`contenu/galeries.json`, où l'on peut ensuite les réordonner.

Retraiter toutes les photos (après un changement de taille, de signature…),
à partir d'un dossier contenant les originaux nommés comme leur identifiant :

    python outils/photos.py regenerer chemin/vers/originaux/

Dépendance : Pillow (pip install Pillow).
"""

from __future__ import annotations

import io
import json
import re
import sys
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_PHOTOS = RACINE / "statique" / "photos"
FICHIER_PHOTOS = RACINE / "contenu" / "photos.json"
FICHIER_GALERIES = RACINE / "contenu" / "galeries.json"

# Taille du plus grand côté pour chaque variante.
TAILLES = {"s": 720, "m": 1440, "l": 2200}
QUALITE = 80
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic"}

SRGB = ImageCms.createProfile("sRGB")

_SITE = json.loads((RACINE / "contenu" / "site.json").read_text(encoding="utf-8"))
AUTEUR = _SITE["nom"]
URL_DROITS = _SITE["url"] + "/mentions-legales/"


def signature() -> tuple[bytes, bytes]:
    """Métadonnées ajoutées à chaque photo : EXIF (auteur, copyright) et XMP/IPTC (lus par Google Images)."""
    exif = Image.Exif()
    exif[0x013B] = AUTEUR  # Artist
    exif[0x8298] = f"Copyright {AUTEUR}. All rights reserved."  # Copyright
    xmp = f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"
    photoshop:Credit="{AUTEUR}"
    xmpRights:Marked="True"
    xmpRights:WebStatement="{URL_DROITS}">
   <dc:creator><rdf:Seq><rdf:li>{AUTEUR}</rdf:li></rdf:Seq></dc:creator>
   <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">© {AUTEUR}. Tous droits réservés. All rights reserved.</rdf:li></rdf:Alt></dc:rights>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""
    return exif.tobytes(), xmp.encode("utf-8")


def identifiant(nom_fichier: str) -> str:
    """Transforme un nom de fichier en identifiant propre : 'DSC_0100-Enhanced-NR.jpg' -> 'dsc-0100'."""
    nom = Path(nom_fichier).stem
    nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    nom = nom.lower()
    nom = re.sub(r"-?enhanced-nr", "", nom)
    nom = re.sub(r"[^a-z0-9]+", "-", nom).strip("-")
    return nom or "photo"


def _vers_srgb(img: Image.Image) -> Image.Image:
    icc = img.info.get("icc_profile")
    if icc:
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            mode = "RGB" if img.mode not in ("RGB", "RGBA") else img.mode
            img = ImageCms.profileToProfile(img.convert(mode), source, SRGB, outputMode=mode)
        except Exception:
            pass
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fond = Image.new("RGB", img.size, (254, 239, 221))
        fond.paste(img, mask=img.split()[-1])
        img = fond
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


def optimiser(source: Path, pid: str) -> dict:
    """Crée les variantes WebP d'une photo et renvoie ses métadonnées."""
    DOSSIER_PHOTOS.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        img = _vers_srgb(img)
        largeur, hauteur = img.size
        meta = {"w": largeur, "h": hauteur}
        exif, xmp = signature()
        for suffixe, cote in TAILLES.items():
            echelle = min(1.0, cote / max(largeur, hauteur))
            taille = (round(largeur * echelle), round(hauteur * echelle))
            variante = img if echelle == 1.0 else img.resize(taille, Image.LANCZOS)
            variante.save(DOSSIER_PHOTOS / f"{pid}-{suffixe}.webp", "WEBP", quality=QUALITE, method=5, exif=exif, xmp=xmp)
            meta[suffixe] = taille[0]
        r, g, b = img.resize((1, 1), Image.BOX).getpixel((0, 0))
        meta["c"] = f"#{r:02x}{g:02x}{b:02x}"
    return meta


def charger(fichier: Path) -> dict:
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    return {}


def sauver(fichier: Path, donnees: dict) -> None:
    fichier.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tache(args):
    source, pid = args
    return pid, optimiser(Path(source), pid)


def optimiser_lot(sources: list[tuple[Path, str]]) -> dict:
    """Optimise plusieurs photos en parallèle. `sources` : liste de (chemin, identifiant)."""
    resultats = {}
    with ProcessPoolExecutor() as pool:
        for i, (pid, meta) in enumerate(pool.map(_tache, [(str(s), p) for s, p in sources]), 1):
            resultats[pid] = meta
            print(f"  [{i}/{len(sources)}] {pid}")
    return resultats


def ajouter(galerie: str, chemins: list[str]) -> None:
    galeries = charger(FICHIER_GALERIES)
    photos = charger(FICHIER_PHOTOS)
    if galerie not in galeries:
        print(f"Galerie inconnue : {galerie}. Galeries existantes : {', '.join(galeries)}")
        sys.exit(1)

    fichiers: list[Path] = []
    for c in chemins:
        p = Path(c)
        if p.is_dir():
            fichiers += sorted(f for f in p.iterdir() if f.suffix.lower() in EXTENSIONS)
        elif p.suffix.lower() in EXTENSIONS:
            fichiers.append(p)

    a_traiter = []
    for f in fichiers:
        pid = identifiant(f.name)
        while pid in photos and pid not in galeries[galerie]:
            pid += "-b"
        a_traiter.append((f, pid))

    print(f"Optimisation de {len(a_traiter)} photo(s)…")
    for pid, meta in optimiser_lot(a_traiter).items():
        photos[pid] = {**photos.get(pid, {"alt": ""}), **meta}
        if pid not in galeries[galerie]:
            galeries[galerie].append(pid)

    sauver(FICHIER_PHOTOS, photos)
    sauver(FICHIER_GALERIES, galeries)

    # Page Concert : chaque nouvelle photo reçoit une ligne « À COMPLÉTER » pour le nom de l'artiste.
    if galerie == "concert":
        fichier_noms = RACINE / "contenu" / "artistes-concert.json"
        noms = charger(fichier_noms)
        for _, pid in a_traiter:
            noms.setdefault(pid, "À COMPLÉTER")
        sauver(fichier_noms, noms)
        print("Noms d'artistes à compléter dans contenu/artistes-concert.json")
    print("Terminé. Pensez à relancer : python outils/build.py")


def regenerer(dossier: str) -> None:
    """Retraite toutes les photos connues à partir de leurs originaux (fichiers nommés <identifiant>.<ext>)."""
    photos = charger(FICHIER_PHOTOS)
    sources = {f.stem: f for f in Path(dossier).iterdir() if f.suffix.lower() in EXTENSIONS}
    manquantes = [pid for pid in photos if pid not in sources]
    if manquantes:
        print(f"Originaux introuvables pour : {', '.join(manquantes)}")
    a_traiter = [(sources[pid], pid) for pid in photos if pid in sources]
    print(f"Retraitement de {len(a_traiter)} photo(s)…")
    for pid, meta in optimiser_lot(a_traiter).items():
        photos[pid] = {**photos[pid], **meta}
    sauver(FICHIER_PHOTOS, photos)
    print("Terminé. Pensez à relancer : python outils/build.py")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "ajouter":
        ajouter(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) == 3 and sys.argv[1] == "regenerer":
        regenerer(sys.argv[2])
    else:
        print(__doc__)
