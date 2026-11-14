# romanechaslin.fr

Site de Romane Chaslin, photographe à Rennes. Site statique (HTML, CSS, JavaScript) en français et en anglais, sans Squarespace ni abonnement, hébergé gratuitement sur GitHub Pages.

Palette : crème `#FEEFDD` (fond), ardoise `#36413E` (texte, bandeaux), pervenche `#7F7EFF` (accent, grands titres sur fond sombre), bois de rose `#885053` (boutons, liens). Les couleurs se changent en haut de `statique/css/style.css`.

## Organisation

```
contenu/
  site.json        tous les textes du site en français (accueil, galeries, à propos, contact…)
  site.en.json     les mêmes textes traduits en anglais
  galeries.json    la liste et l'ordre des photos de chaque galerie
  photos.json      infos de chaque photo : favori, texte alternatif (dimensions remplies automatiquement)
  artistes-concert.json  noms des artistes affichés au survol des photos de concert (À COMPLÉTER)
statique/
  css/ js/ polices/  style et interactions
  photos/          photos optimisées et signées (WebP, 3 tailles chacune)
outils/
  build.py         génère le site dans le dossier site/
  photos.py        optimise, signe et ajoute de nouvelles photos
  importer_squarespace.py  import unique depuis l'ancien site (déjà fait)
.github/workflows/deploy.yml   mise en ligne automatique
```

Prérequis : Python 3.10 ou plus, et Pillow (`pip install Pillow`).

## Voir le site sur son ordinateur

```bash
python outils/build.py --serve
```

Puis ouvrir http://localhost:8000 (version anglaise : http://localhost:8000/en/). Relancer la commande après chaque modification. À la fin, la commande liste ce qu'il reste à compléter avant la mise en ligne.

## Modifier un texte

- Français : `contenu/site.json`. Anglais : `contenu/site.en.json` (ne contient que les textes ; photos et liens viennent de `site.json`).
- Entourer un mot d'astérisques (`*mot*`) l'affiche en italique (bois de rose sur fond clair, pervenche sur fond sombre) dans les titres.
- Penser à mettre à jour les deux langues.

## Ajouter des photos à une galerie

```bash
python outils/photos.py ajouter concert "C:/chemin/vers/mes photos/"
```

Les galeries s'appellent : `concert`, `corporate`, `reportage`, `portrait`, `portrait-professionnel`, `tourisme`.
Les photos sont converties, allégées, débarrassées de leurs données EXIF/GPS, signées au nom de Romane, puis ajoutées à la fin de la galerie.

- **Changer l'ordre** ou **retirer une photo** : modifier la liste dans `contenu/galeries.json`.
- **Changer une couverture, le diaporama d'accueil…** : indiquer l'identifiant de la photo (ex. `dsc-1117`) dans `contenu/site.json`.

Dans `contenu/photos.json`, chaque photo peut recevoir :

| Champ | Effet |
|---|---|
| `"favori": true` | entoure la photo au **crayon pervenche** dans la planche contact |
| `"alt"` / `"alt_en"` | description de la photo en français / anglais (accessibilité, Google Images) |

## Noms des artistes (page Concert)

Au survol d'une photo de concert, le nom de l'artiste apparaît en bas de l'image. Sur téléphone (pas de survol), il s'affiche dans la visionneuse.

Les noms se remplissent à la main dans `contenu/artistes-concert.json` : une ligne par photo, dans l'ordre de la galerie. Cherchez « À COMPLÉTER » et remplacez-le par le nom (laisser `""` pour ne rien afficher). Pour savoir quelle photo correspond à une ligne, ouvrez `statique/photos/<identifiant>-s.webp` (ex. `dsc-0100-s.webp`).

```json
"dsc-0100": "À COMPLÉTER",   ← à remplacer, ex. "Nom de l'artiste"
"gazo-12": "Gazo",
```

Les nouvelles photos ajoutées à la galerie concert avec `outils/photos.py` reçoivent automatiquement une ligne « À COMPLÉTER ». La commande `python outils/build.py` indique combien de noms restent à compléter.

## Protection des photos

- Clic droit, glisser-déposer et appui long (mobile) bloqués sur les photos.
- Les liens des galeries ne pointent plus vers les fichiers images.
- Chaque fichier est signé (auteur, copyright, lien vers les mentions légales), crédit affiché par Google Images.
- Les robots d'entraînement d'IA sont refusés (`robots.txt`), avec opposition à la fouille de données au sens de la loi française (`.well-known/tdmrep.json` et mentions légales). Les moteurs de recherche restent autorisés.

Rien n'empêche totalement une capture d'écran : ces mesures découragent la copie et prouvent l'origine des images.

Pour retraiter toutes les photos (nouvelle signature, autre taille…) depuis les originaux nommés comme leur identifiant :

```bash
python outils/photos.py regenerer "C:/chemin/vers/originaux/"
```

## Formulaire de contact

Les messages sont envoyés par [FormSubmit](https://formsubmit.co) : gratuit, sans inscription. Réglage unique dans `contenu/site.json`, champ `contact.formsubmit`.

1. Mettre l'adresse e-mail de Romane : `"formsubmit": "romane@exemple.fr"`, puis lancer `python outils/build.py --serve`.
2. Envoyer un premier message depuis la page Contact. Le site affiche « Formulaire en attente d'activation » : c'est normal.
3. Romane reçoit un e-mail de FormSubmit (regarder les indésirables) : cliquer sur **Activate Form**.
4. FormSubmit envoie ensuite un **code** (une suite de lettres et chiffres). Le mettre à la place de l'adresse : `"formsubmit": "le-code-recu"`, puis relancer `python outils/build.py`. L'adresse e-mail n'apparaît ainsi plus dans le code du site (protection contre le spam).
5. Renvoyer un message de test : il doit arriver dans la boîte de Romane, sous forme de tableau (Prénom, Nom, E-mail, Type de projet, Message). « Répondre » écrit directement au visiteur.

Anti-spam intégré : un champ piège invisible bloque les robots.

## Avant la mise en ligne

Vérification complète faite le 25/10/2026 : 23 pages, aucun lien cassé, aucune erreur, affichage correct de 360 à 1920 px, contrastes conformes, anciennes adresses conservées.

**Obligatoire**
- [x] Mentions légales : statut (EI, micro-entreprise) et SIRET renseignés (`contenu/site.json` → `mentions`).
- [ ] Mentions légales : la loi (LCEN) demande aussi, pour une professionnelle, une **adresse** et un **numéro de téléphone**. À décider : les ajouter, ou utiliser une adresse de domiciliation pour ne pas publier son adresse personnelle.
- [x] Formulaire de contact : FormSubmit activé, code en place (adresse e-mail masquée), test de réception réussi le 25/10/2026.
- [ ] Juste après la mise en ligne : envoyer un message depuis le vrai site. Si FormSubmit redemande une activation (il peut la lier à l'adresse du site), Romane recliquera sur « Activate Form ».
- [ ] Nom de domaine : il est géré par **Squarespace Domains**. Avant de résilier le site Squarespace, s'assurer que le domaine reste payé et renouvelé (le garder chez Squarespace Domains ou le transférer chez un autre registraire, ex. OVH, Gandi). Aucune messagerie n'est liée au domaine : pas de risque de coupure d'e-mails.

**Contenu à compléter ou relire**
- [ ] Noms d'artistes : 41 « À COMPLÉTER » sur 48 dans `contenu/artistes-concert.json`, et confirmer l'orthographe des 7 déjà remplis (« Jolagreen » ou « Jolagreen23 » ?).
- [ ] Relire tous les textes, et faire relire la traduction anglaise (`contenu/site.en.json`).
- [ ] Photos en basse définition (un peu floues en plein écran) : `dsc-4089` (portrait), `000982620017`, `000982620022`, `voyage-capture-1`, `voyage-capture-2` (Ailleurs sur Terre), et `concert-capture`. À remplacer par les fichiers originaux si possible.
- [ ] Photo importée mais affichée nulle part : `dsc-8552` (grand-mère et enfant à table). L'ajouter à une galerie ou la supprimer.
- [ ] Droit à l'image : vérifier les autorisations des personnes photographiées (portraits, reportage à l'abbaye) et l'accord de Longchamp pour la galerie Corporate, comme pour l'ancien site.

**Recommandé**
- [ ] Décrire les photos principales (`alt` / `alt_en` dans `contenu/photos.json`) : aujourd'hui elles ont une description générique (« Photo de concert — 3 sur 48 »), utile mais peu informative pour Google Images.
- [ ] Après la mise en ligne : déclarer le site dans Google Search Console et y envoyer `https://www.romanechaslin.fr/sitemap.xml` ; vérifier que `https://www.romanechaslin.fr/.well-known/tdmrep.json` s'affiche bien.
- [ ] Tester le site sur un vrai téléphone (iPhone et Android) : animations, visionneuse, appui long sur les photos.

## Mise en ligne sur GitHub Pages

1. Créer un dépôt sur le compte GitHub de Romane (ex. `romanechaslin.fr`) et y envoyer ce dossier :
   ```bash
   git init
   git add .
   git commit -m "Nouveau site"
   git branch -M main
   git remote add origin https://github.com/<compte>/romanechaslin.fr.git
   git push -u origin main
   ```
2. Sur GitHub : **Settings → Pages → Source : GitHub Actions**. Le site se construit et se publie tout seul à chaque `git push` (onglet **Actions** pour suivre).
3. **Nom de domaine** : dans **Settings → Pages → Custom domain**, saisir `www.romanechaslin.fr`, puis chez le gestionnaire du domaine (Squarespace Domains) remplacer les enregistrements DNS par :
   - `CNAME` : `www` → `<compte>.github.io`
   - `A` : `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`

   Une fois le domaine vérifié, cocher **Enforce HTTPS**. Les anciennes adresses (`/concert`, `/about`, `/contact`…) sont conservées, le référencement Google n'est donc pas perdu.
4. Résilier l'abonnement Squarespace seulement après avoir vérifié que le nouveau site s'affiche bien sur le domaine.
