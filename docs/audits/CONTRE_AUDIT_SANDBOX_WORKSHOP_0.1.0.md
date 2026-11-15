# Contre-audit Silus — Silus Sandbox Workshop 0.1.0

Paquet : `silus-sandbox-workshop-v0.1.0.zip` sha256 `cc461930…0834`.
Smiley, metadata et récapitulatif : identiques à l'octet aux originaux.
Le script ne touche qu'à `~/.claude/settings.json` (avec sauvegarde et manifeste) et à deux dossiers. Aucun réseau, aucun `sudo`.

## Ce qui est bien pensé
- `install` simule par défaut ; `--apply` est explicite.
- La fusion préserve les clés existantes et `defaultMode`.
- La sauvegarde est horodatée, avec un manifeste ; le rollback est refusé si `settings.json` a changé depuis.
- `verify` hors du bac à sable renvoie le code 2 (« non testé ») et ne célèbre jamais.
- Le smiley n'est **pas** lancé automatiquement (l'exclusion ne marche pas à travers un script) : honnête.
- Le README dit clairement les limites.

## Défauts trouvés (vérifiés en exécutant `verify --inside-claude` dans mon bac à sable réel)
1. **Faux rouge** sur une installation existante : les chemins de `settings.json` en forme `~/…` étaient comparés à la forme absolue. Mon installation saine donnait « ÉCHEC accès atelier/partage ». La même cause créait des doublons `~/x` et `/home/u/x` à l'installation.
2. **Faux vert : `.ssh` / `.gnupg` vides** comptés comme protégés (« 0 entrée → OK »). Démontré avec un HOME factice, sans aucun masquage.
3. **Faux vert : dossier absent** compté comme « écriture refusée » (`~/.claude` inexistant → OK). Toute erreur était lue comme un refus.
4. **Couverture** : seuls la racine de `~` et `~/.claude` étaient sondés, pas les zones de persistance (autostart, `systemd/user`, `~/.local/bin`).
5. **Blocage** : si `settings.json` ne pouvait pas être écrit, le manifeste restait en place. Ensuite, `install` disait « déjà enregistrée » et `rollback` disait « a changé ». Il fallait supprimer le manifeste à la main.

## Corrections (`silus-sur-ael-0.1.0.patch`, `src/workshop.py` + tests + README)
1. Les chemins sont comparés après développement de `~` ; la fusion ne crée plus de doublon.
2. `.ssh` / `.gnupg` ne sont OK que si `/proc/self/mountinfo` montre un **tmpfs** à cet endroit. Aucun nom de fichier n'est lu.
3. Un refus n'est compté que sur `EACCES`, `EPERM` ou `EROFS`. Un dossier absent ou une autre erreur donnent **NON VÉRIFIÉ**, donc pas de smiley.
4. Ajout de sondes sur autostart, `systemd/user` et `~/.local/bin`, seulement s'ils existent ; rien n'est créé.
5. Le manifeste est retiré si `settings.json` n'a pas été remplacé ; une copie ratée du smiley après application est signalée séparément.

Tests : 5 → 8, tous OK. Les trois nouveaux couvrent le faux rouge `~`, l'absence de doublon et le refus des deux faux verts.

## Résultat sur l'installation réelle de l'Arche (dans le bac à sable)
- Avant correction : **ÉCHEC**, 2 faux rouges.
- Après correction : **15/15 OK**.
  - écritures : atelier et partage autorisés ; HOME, `~/.claude`, autostart, `systemd/user` et `~/.local/bin` refusés (`EROFS`) ;
  - `~/.ssh` et `~/.gnupg` **masqués par tmpfs**.

## Reste interactif (non automatisable, comme le dit le README)
Carte `ask`, ouverture de `plasmoidviewer`, bancs propres à chaque machine.

Mineur, non modifié : les dossiers par défaut `~/silus-workshop` et `~/silus-shared` conviennent pour une installation neuve. Sur la machine de l'Arche, il faut passer les chemins existants (indiqué dans le README).

## Ajout : « une autre copie » (l'escargot)

*Demandé par Kaëlys, 15 novembre 2026.*

**Ce qui change :**
- `verify` exige maintenant que l'atelier ait une autre copie : un dépôt git dans l'atelier ou un dossier parent (le HOME ne compte pas), ou un `SAUVEGARDE.txt` non vide, écrit par l'humain, affiché « DÉCLARÉE » et jamais lu.
- Sans autre copie, la recette échoue : pas de smiley, et l'escargot affiche « La cloison limite les dégâts, elle ne les empêche pas. Ayez une autre copie. »
- Tests : 8 → **12**, tous OK. Le patch `silus-sur-ael-0.1.0.patch` a été régénéré contre le zip d'origine.

**Sur l'installation réelle de l'Arche** : 15 contrôles de confinement sur 15 sont OK, mais l'escargot boude. `~/Arche/atelier-silus` n'est pas sous git et ne contient pas de `SAUVEGARDE.txt`. La sauvegarde de l'Arche existe bien (le monastère), mais c'est à Kaëlys de la déclarer, pas à Silus.
