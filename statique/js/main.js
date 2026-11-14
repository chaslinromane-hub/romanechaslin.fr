/* Romane Chaslin — interactions du site (sans dépendance). */
(() => {
  "use strict";

  const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
  const memoire = {
    lire: (cle) => { try { return localStorage.getItem(cle); } catch { return null; } },
    ecrire: (cle, val) => { try { localStorage.setItem(cle, val); } catch { /* navigation privée */ } },
  };

  /* ---------- Protection des photos : clic droit, glisser-déposer, appui long ---------- */
  function protection() {
    const estPhoto = (cible) => cible instanceof Element &&
      (cible.tagName === "IMG" || cible.closest(".galerie__item, .planche__vue, [data-lb-scene], .heros__cadre"));
    document.addEventListener("contextmenu", (ev) => { if (estPhoto(ev.target)) ev.preventDefault(); });
    document.addEventListener("dragstart", (ev) => { if (estPhoto(ev.target)) ev.preventDefault(); });
  }

  /* ---------- En-tête : fond au défilement, masqué en descendant ---------- */
  function entete() {
    const el = $(".entete");
    if (!el) return;
    let dernier = window.scrollY;
    let attente = false;
    const maj = () => {
      const y = window.scrollY;
      el.classList.toggle("est-defile", y > 8);
      const menuOuvert = document.documentElement.classList.contains("menu-ouvert");
      const delta = y - dernier;
      if (Math.abs(delta) > 4) {
        if (delta > 0 && y > 320 && !menuOuvert) el.classList.add("est-cache");
        else if (delta < 0) el.classList.remove("est-cache");
        dernier = y;
      }
      if (y < 320) el.classList.remove("est-cache");
      attente = false;
    };
    window.addEventListener("scroll", () => {
      if (!attente) { attente = true; requestAnimationFrame(maj); }
    }, { passive: true });
    maj();
  }

  /* ---------- Menu mobile ---------- */
  function menu() {
    const bouton = $(".menu-bouton");
    const panneau = $("#menu-mobile");
    if (!bouton || !panneau) return;
    const racine = document.documentElement;
    const basculer = (ouvrir) => {
      racine.classList.toggle("menu-ouvert", ouvrir);
      bouton.setAttribute("aria-expanded", String(ouvrir));
      bouton.setAttribute("aria-label", ouvrir ? bouton.dataset.fermer : bouton.dataset.ouvrir);
      document.body.style.overflow = ouvrir ? "hidden" : "";
      if (ouvrir) $("a", panneau)?.focus({ preventScroll: true });
    };
    bouton.addEventListener("click", () => basculer(!racine.classList.contains("menu-ouvert")));
    panneau.addEventListener("click", (ev) => { if (ev.target.closest("a")) basculer(false); });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && racine.classList.contains("menu-ouvert")) { basculer(false); bouton.focus(); }
    });
    window.matchMedia("(min-width: 761px)").addEventListener("change", (m) => { if (m.matches) basculer(false); });
  }

  /* ---------- Diaporama de l'accueil ---------- */
  function diaporama() {
    const heros = $(".heros");
    if (!heros) return;
    const diapos = $$("[data-diapo]", heros);
    const boutons = $$("[data-diapo-bouton]", heros);
    if (diapos.length < 2) return;
    const DUREE = 6000;
    heros.style.setProperty("--duree", DUREE + "ms");
    let courant = 0;
    let minuteur = null;

    const afficher = (i) => {
      courant = (i + diapos.length) % diapos.length;
      diapos.forEach((d, k) => d.classList.toggle("est-active", k === courant));
      boutons.forEach((b) => b.setAttribute("aria-pressed", "false"));
      // Relance l'animation de la barre de progression du bouton actif.
      const actif = boutons[courant];
      if (actif) { void actif.offsetWidth; actif.setAttribute("aria-pressed", "true"); }
    };
    const lancer = () => {
      clearInterval(minuteur);
      if (reduit) return;
      minuteur = setInterval(() => afficher(courant + 1), DUREE);
    };
    boutons.forEach((b, k) => b.addEventListener("click", () => { afficher(k); lancer(); }));
    document.addEventListener("visibilitychange", () => (document.hidden ? clearInterval(minuteur) : lancer()));
    if (reduit) heros.classList.add("est-en-pause");
    lancer();
  }

  /* ---------- Texte ondulé qui défile ---------- */
  function vagues() {
    const svgs = $$("[data-vague]");
    if (!svgs.length) return;
    const NS = "http://www.w3.org/2000/svg";
    let vitesseDefilement = 0;
    let dernierY = window.scrollY;
    window.addEventListener("scroll", () => {
      const y = window.scrollY;
      vitesseDefilement += (y - dernierY) * 0.9;
      dernierY = y;
    }, { passive: true });

    const etats = svgs.map((svg) => {
      const chemin = svg.querySelector("path");
      const tp = svg.querySelector("textPath");
      const texte = tp.dataset.texte;
      const etat = { svg, chemin, tp, texte, unite: 0, offset: 0, visible: true };

      const construire = () => {
        const W = Math.max(svg.clientWidth || svg.parentElement.clientWidth, 320);
        const taille = Math.min(Math.max(W * 0.062, 44), 96);
        const amp = taille * 0.42;
        const lambda = Math.max(W * 0.55, 520);
        const H = taille * 1.25 + amp * 2;
        svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
        svg.setAttribute("height", H);
        svg.querySelector("text").setAttribute("font-size", taille);
        const milieu = H / 2 + taille * 0.32;
        let d = `M ${-lambda} ${milieu} q ${lambda / 4} ${-amp * 2} ${lambda / 2} 0`;
        for (let x = lambda / 2; x < W + lambda * 2; x += lambda / 2) d += ` t ${lambda / 2} 0`;
        chemin.setAttribute("d", d);

        // Une unité = le texte en romain + le texte en italique rose.
        tp.textContent = "";
        const ajouterUnite = () => {
          const a = document.createElementNS(NS, "tspan");
          a.textContent = texte + "  ";
          const b = document.createElementNS(NS, "tspan");
          b.setAttribute("class", "accent");
          b.textContent = texte + "  ";
          tp.append(a, b);
        };
        ajouterUnite();
        etat.unite = tp.getComputedTextLength() || 1200;
        const n = Math.ceil(chemin.getTotalLength() / etat.unite) + 1;
        for (let i = 0; i < n; i++) ajouterUnite();
      };
      construire();
      etat.construire = construire;
      return etat;
    });

    let largeur = window.innerWidth;
    window.addEventListener("resize", () => {
      if (Math.abs(window.innerWidth - largeur) < 40) return;
      largeur = window.innerWidth;
      etats.forEach((s) => s.construire());
    });
    if (document.fonts?.ready) document.fonts.ready.then(() => etats.forEach((s) => s.construire()));

    if (reduit) {
      etats.forEach((s) => s.tp.setAttribute("startOffset", -s.unite * 0.3));
      return;
    }

    const io = new IntersectionObserver((entrees) => {
      entrees.forEach((en) => { const s = etats.find((x) => x.svg === en.target); if (s) s.visible = en.isIntersecting; });
    });
    etats.forEach((s) => io.observe(s.svg));

    let t0 = performance.now();
    const boucle = (t) => {
      const dt = Math.min((t - t0) / 1000, 0.05);
      t0 = t;
      vitesseDefilement *= 0.9;
      const v = 55 + Math.max(Math.min(vitesseDefilement * 12, 900), -900);
      etats.forEach((s, i) => {
        if (!s.visible) return;
        const sens = i % 2 ? -1 : 1;
        s.offset = (s.offset - v * dt * sens) % s.unite;
        if (s.offset > 0) s.offset -= s.unite;
        s.tp.setAttribute("startOffset", s.offset.toFixed(1));
      });
      requestAnimationFrame(boucle);
    };
    requestAnimationFrame(boucle);
  }

  /* ---------- Index des thématiques (aperçu au survol) ---------- */
  function themes() {
    const liste = $("[data-themes]");
    if (!liste) return;
    const apercus = $$("[data-apercu]");
    const liens = $$("[data-theme]", liste);
    const activer = (i) => {
      apercus.forEach((img) => img.classList.toggle("est-active", img.dataset.apercu === String(i)));
      liens.forEach((a) => a.classList.toggle("est-active", a.dataset.theme === String(i)));
    };
    liens.forEach((a) => {
      a.addEventListener("mouseenter", () => activer(a.dataset.theme));
      a.addEventListener("focus", () => activer(a.dataset.theme));
    });
  }

  /* ---------- Apparitions au défilement ---------- */
  function apparitions() {
    const els = $$(".apparait");
    if (!els.length) return;
    if (reduit || !("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("est-visible")); return; }
    const io = new IntersectionObserver((entrees) => {
      entrees.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("est-visible"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    els.forEach((el) => io.observe(el));
  }

  /* ---------- Fondu des photos au chargement ---------- */
  function fondus() {
    $$(".galerie__item img, .planche__image img").forEach((img) => {
      if (img.complete) return;
      img.classList.add("charge-en-cours");
      const fin = () => img.classList.remove("charge-en-cours");
      img.addEventListener("load", fin, { once: true });
      img.addEventListener("error", fin, { once: true });
    });
  }

  /* ---------- Lumière éteinte (fond sombre sur les galeries) ---------- */
  function lumiere() {
    const bouton = $("[data-lumiere]");
    if (!bouton) return;
    const racine = document.documentElement;
    const theme = $('meta[name="theme-color"]');
    const appliquer = (eteinte) => {
      racine.classList.toggle("lumiere-eteinte", eteinte);
      bouton.setAttribute("aria-pressed", String(eteinte));
      $("span", bouton).textContent = eteinte ? bouton.dataset.rallumer : bouton.dataset.eteindre;
      if (theme) theme.content = eteinte ? "#1d2422" : "#feefdd";
    };
    appliquer(racine.classList.contains("lumiere-eteinte"));
    bouton.addEventListener("click", () => {
      const eteinte = !racine.classList.contains("lumiere-eteinte");
      appliquer(eteinte);
      memoire.ecrire("rc-lumiere", eteinte ? "eteinte" : "allumee");
    });
  }

  /* ---------- Galerie : affichage (grille / planche contact), visionneuse ---------- */
  function galerie() {
    const grille = $("[data-galerie]");
    if (!grille) return;
    const items = $$(".galerie__item", grille);
    const planche = $("[data-planche]");
    const vues = planche ? $$(".planche__vue", planche) : [];
    const boutonsVue = $$("[data-vue]");

    /* Affichage : grille ou planche contact */
    const choisirVue = (vue, memoriser = true) => {
      if (!planche) return;
      grille.hidden = vue === "planche";
      planche.hidden = vue !== "planche";
      boutonsVue.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.vue === vue)));
      if (memoriser) memoire.ecrire("rc-vue", vue);
      fondus();
    };
    boutonsVue.forEach((b) => b.addEventListener("click", () => choisirVue(b.dataset.vue)));
    if (planche && memoire.lire("rc-vue") === "planche") choisirVue("planche", false);

    /* Visionneuse plein écran */
    const dlg = $(".visionneuse");
    if (!dlg || typeof dlg.showModal !== "function") return;
    const image = $("[data-lb-img]", dlg);
    const scene = $("[data-lb-scene]", dlg);
    const numero = $("[data-lb-index]", dlg);
    const total = $("[data-lb-total]", dlg);
    const titre = $("[data-lb-titre]", dlg);
    const liste = items;
    let pos = 0;
    let ouverte = false;

    const source = (a) => {
      const r = parseFloat(a.dataset.ratio) || 1.5;
      return { srcset: a.dataset.srcset, src: a.dataset.src, sizes: `min(92vw, calc((100svh - 7rem) * ${r.toFixed(3)}))`, alt: $("img", a).alt };
    };
    const precharger = (i) => {
      const s = source(liste[(i + liste.length) % liste.length]);
      const im = new Image();
      im.sizes = s.sizes; im.srcset = s.srcset; im.src = s.src;
    };
    const afficher = (i, sens = 0) => {
      pos = (i + liste.length) % liste.length;
      const s = source(liste[pos]);
      const poser = () => {
        image.sizes = s.sizes; image.srcset = s.srcset; image.src = s.src; image.alt = s.alt;
        image.classList.remove("sort-gauche", "sort-droite");
      };
      if (sens && !reduit) {
        image.classList.add(sens > 0 ? "sort-gauche" : "sort-droite");
        setTimeout(poser, 180);
      } else poser();
      numero.textContent = pos + 1;
      // Nom de l'artiste (page Concert) à côté du titre de la galerie, s'il est renseigné.
      const nom = liste[pos].dataset.legende;
      titre.textContent = nom ? `${grille.dataset.titre} · ${nom}` : grille.dataset.titre || "";
      total.textContent = liste.length;
      if (liste.length > 1) { precharger(pos + 1); precharger(pos - 1); }
      if (ouverte) history.replaceState({ visionneuse: true }, "", `#photo-${+liste[pos].dataset.index + 1}`);
    };
    const ouvrir = (index) => {
      const debut = Math.min(Math.max(index, 0), liste.length - 1);
      if (!dlg.open) dlg.showModal();
      document.body.classList.add("visionneuse-ouverte");
      // Une entrée d'historique : le bouton « retour » du téléphone ferme la visionneuse.
      history.pushState({ visionneuse: true }, "", `#photo-${index + 1}`);
      ouverte = true;
      afficher(debut);
    };
    // Nettoyage immédiat (sans attendre l'événement « close », parfois différé).
    const fermer = (depuisHistorique = false) => {
      if (dlg.open) dlg.close();
      if (!ouverte) return;
      ouverte = false;
      document.body.classList.remove("visionneuse-ouverte");
      if (!depuisHistorique && history.state?.visionneuse) history.back();
      const index = +liste[pos].dataset.index;
      const cible = (planche && !planche.hidden ? vues : items)[index];
      cible?.focus({ preventScroll: true });
    };

    [...items, ...vues].forEach((a) => a.addEventListener("click", (ev) => {
      ev.preventDefault();
      ouvrir(+a.dataset.index);
    }));
    dlg.addEventListener("close", () => fermer());
    dlg.addEventListener("cancel", (ev) => { ev.preventDefault(); fermer(); });
    window.addEventListener("popstate", () => { if (ouverte) fermer(true); });
    $("[data-lb-fermer]", dlg).addEventListener("click", () => fermer());
    $("[data-lb-prec]", dlg).addEventListener("click", () => afficher(pos - 1, -1));
    $("[data-lb-suiv]", dlg).addEventListener("click", () => afficher(pos + 1, 1));
    dlg.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowRight") { ev.preventDefault(); afficher(pos + 1, 1); }
      if (ev.key === "ArrowLeft") { ev.preventDefault(); afficher(pos - 1, -1); }
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); }
    });
    // Glisser du doigt sur mobile.
    let x0 = null, y0 = null;
    scene.addEventListener("pointerdown", (ev) => { x0 = ev.clientX; y0 = ev.clientY; });
    scene.addEventListener("pointerup", (ev) => {
      if (x0 === null) return;
      const dx = ev.clientX - x0, dy = ev.clientY - y0;
      x0 = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) afficher(pos + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
      else if (dy > 90 && Math.abs(dy) > Math.abs(dx)) fermer();
    });
    // Ouverture directe via un lien du type …/concert/#photo-12
    const m = location.hash.match(/^#photo-(\d+)$/);
    if (m) {
      const i = Math.min(Math.max(parseInt(m[1], 10) - 1, 0), items.length - 1);
      history.replaceState(null, "", location.pathname);
      ouvrir(i);
    }
  }

  /* ---------- Formulaire de contact (FormSubmit) ---------- */
  function formulaire() {
    const form = $("[data-formulaire]");
    if (!form) return;
    const statut = $("[data-statut]", form);
    const bouton = $("button[type=submit]", form);
    const params = new URLSearchParams(location.search);
    const dire = (texte, etat) => {
      statut.textContent = texte;
      statut.className = "formulaire__statut" + (etat ? " est-" + etat : "");
    };
    // Pré-sélection du type de projet via l'adresse (ex. contact/?type=portrait).
    const type = params.get("type");
    if (type) {
      const option = $$("option", form).find((o) => o.dataset.cle === type);
      if (option) option.selected = true;
    }
    // Retour après un envoi sans JavaScript (FormSubmit redirige vers …/contact/?envoye=1).
    if (params.get("envoye") === "1") dire(form.dataset.succes, "ok");

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const cible = form.dataset.cible;
      if (!cible) { dire(form.dataset.nonConfigure, "erreur"); return; }
      // Piège à robots rempli : on fait comme si de rien n'était.
      if (form.elements._honey?.value) { form.reset(); dire(form.dataset.succes, "ok"); return; }
      bouton.disabled = true;
      dire(form.dataset.envoi);
      // Champs envoyés avec des intitulés lisibles (« Prénom », « Message »…) dans l'e-mail reçu.
      const donnees = {};
      for (const el of form.elements) {
        if (!el.name || el.name === "_next") continue;
        donnees[el.name.startsWith("_") || el.name === "email" ? el.name : (el.dataset.libelle || el.name)] = el.value;
      }
      donnees._replyto = form.elements.email.value; // « Répondre » renvoie directement au visiteur
      try {
        const rep = await fetch(`https://formsubmit.co/ajax/${cible}`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(donnees),
        });
        const json = await rep.json().catch(() => ({}));
        if (rep.ok && String(json.success) === "true") { form.reset(); dire(form.dataset.succes, "ok"); }
        else if (/activat/i.test(json.message || "")) dire(form.dataset.activation, "erreur");
        else dire(form.dataset.erreur, "erreur");
      } catch {
        dire(form.dataset.erreur, "erreur");
      } finally {
        bouton.disabled = false;
      }
    });
  }

  const demarrer = () => {
    protection(); entete(); menu(); diaporama(); vagues(); themes(); apparitions(); fondus();
    lumiere(); galerie(); formulaire();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer);
  else demarrer();
})();
