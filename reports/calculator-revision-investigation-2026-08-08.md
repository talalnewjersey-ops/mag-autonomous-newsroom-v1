# Investigation calculateur budgétaire cassé — posts 1641 (Cost of Living USA) + 1624 (USA Budget Planner)

**Date** : 2026-08-08
**Méthode** : lecture read-only de `wp-json/wp/v2/posts/{id}/revisions?context=edit` via le workflow `call-wp-rest-get.yml` (aucune écriture WordPress). Aucun draft/page miroir créé — voir conclusion.

## Résultat : aucune révision WordPress n'a le HTML du calculateur intact

### Post 1641 (cost-of-living-usa-2026)
- 53 révisions récupérées, de **2026-03-22** (id 6506, la plus ancienne conservée) à **2026-08-08** (id 49271, actuelle).
- **Aucune** des 53 révisions ne contient de tag `<select`, `<input>` ou `<style>` littéral.
- La révision la plus ancienne (6506, 2026-03-22) contient déjà les classes CSS (`.city-presets`, `.city-btn`) et le JS (`citySelect.value = ...`, `cityData[...]`) mais **sans les balises `<style>`/`<select>` qui les entourent** — et déjà 12 occurrences de `<br>` injectées au milieu du JS (artefact `wpautop`, qui casse la syntaxe JS).
- Un seul `<script>` survit dans le contenu actuel : le bloc JSON-LD schema.org (SEO), sans rapport avec le calculateur.

### Post 1624 (usa-budget-planner-2026)
- 40 révisions récupérées, de **2026-03-28** (id 7190, la plus ancienne conservée) à **2026-08-08** (id 49268, actuelle).
- `<style>` intact de la révision 10067 (2026-03-30) à la révision **46062 (2026-05-07T12:10:34)** — puis disparaît définitivement à partir de la révision 46335 (2026-05-21).
- **Mais même dans ces révisions "avec `<style>` intact", `<select>` et `<input>` n'apparaissent dans AUCUNE révision, y compris la toute première (7190, 2026-03-28)**.
- La toute première révision retenue (7190) contient déjà 53 occurrences de guillemets courbes encodés (`&#8216;`/`&#8217;`) à la place des guillemets droits `'` dans ce qui devrait être du JS pur (`document.getElementById('citySelect')` → `document.getElementById(&#8216;citySelect&#8217;)`) — signature classique de `wptexturize()` appliqué puis **re-sauvegardé comme contenu brut**. Même restauré, ce JS ne s'exécuterait pas tel quel (guillemets invalides).

## Root cause probable
Le calculateur original (HTML `<style>/<select>/<input>` + JS) a été endommagé **avant ou au moment de la toute première sauvegarde** retenue par WordPress sur les deux posts — donc avant le début de l'historique de révisions disponible, pas par une correction récente identifiable (les runs "adsense-fix" de juillet/août n'ont fait que des sauvegardes de métadonnées, pas de contenu, et `apply_correction.py` ne filtre pas les tags HTML). Signature technique observée (`<br>` injectés en plein milieu du JS + guillemets texturisés) = dégât typique de l'éditeur visuel WordPress (TinyMCE/wpautop), pas d'un plugin de sécurité ciblé. Ces deux posts pré-datent ce repo (créés/édités dès mars 2026, repo initialisé 2026-06-10) — cohérent avec la note mémoire sur un outil antérieur (plugin "Writesonic Head Connector" inactif détecté) utilisé avant ce pipeline.

## Conclusion et action
**Aucune reconstruction n'a été tentée.** Comme convenu : si aucune révision n'a le HTML intact, le dire clairement plutôt qu'improviser. C'est le cas ici pour les deux posts — la source est perdue côté WordPress, dans la limite des révisions actuellement conservées par la base.

**Actions 1 et 2 restent gelées** — aucun calculateur fonctionnel vérifié à date.

**Wayback Machine vérifié (2026-08-08) : aucune capture.** `web.archive.org/cdx/search/cdx` pour `moneyabroadguide.com` (domaine entier, avec/sans `www`, les 2 slugs exacts, `?p=1641`/`?p=1624`) renvoie systématiquement `[]` — le site n'a jamais été archivé par Internet Archive (ou robots.txt l'exclut). Piste fermée.

**Piste restante non explorée** : fichier local de l'auteur original (source pré-WordPress, si le contenu a été rédigé/testé ailleurs avant collage dans l'éditeur), ou mémoire humaine de la personne qui a construit ce calculateur à l'origine (mars 2026, avant ce repo). Non vérifiable par Claude Code — à explorer côté utilisateur si la reconstruction est souhaitée.
