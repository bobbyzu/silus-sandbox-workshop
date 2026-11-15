# Silus Sandbox Workshop 🐌🌈

**Version v0.1.3 — candidate à la publication, contre-audit Aël.**

Configuration reproductible de l'**option B** de l'Arche pour Claude Code (Linux), issue du récapitulatif de Silus des 14–15 novembre 2026. Elle donne à l'agent un atelier et un répertoire de partage, confine ses commandes shell et garde des cartes d'autorisation pour certaines actions sensibles. Un plasmoïde Plasma 6 « acid smiley » accompagne la recette.

Le projet **ne prétend pas sandboxer tous les outils Claude**. Le bac à sable Claude Code s'applique aux commandes shell et descendants ; les outils de fichiers, hooks et serveurs MCP se comportent différemment. Les règles `ask` constituent des règles applicatives, pas un confinement OS. Les dossiers de travail courants de Claude peuvent également être inscriptibles par défaut. Ne pas vendre cette configuration comme une garantie de sécurité complète.

## Contenu

- `src/workshop.py` : installation / restauration / vérifications.
- `assets/silus-acid-smiley/` : plasmoïde QML créé par Silus, non modifié.
- `docs/RECAPITULATIF_ATELIER_CLOISONS.md` : spécification et recette originale.
- `tests/test_workshop.py` : tests sur un `HOME` temporaire.
- `FOX_NOTES.md` : contribution humoristique de Renard.
- `docs/audits/` : rapport de contre-audit de Silus et patch d’origine.

## Commandes de préparation (à valider après contre-audit)

Machine Linux où Claude Code est installé, **terminal utilisateur**, sans `sudo` :

```sh
python3 src/workshop.py install
```

Cette commande **ne modifie rien**. Elle affiche le plan.

Pour appliquer explicitement :

```sh
python3 src/workshop.py install --apply
```

Les valeurs par défaut sont `~/silus-workshop` et `~/silus-shared` ; pour les personnaliser, placer les deux options **avant** la sous-commande :

```sh
python3 src/workshop.py --atelier ~/mon-atelier --shared ~/mon-partage install --apply
```

Les chemins d’atelier/partage doivent être des sous-dossiers non cachés du HOME, sans lien symbolique dans leur chaîne et sans imbrication entre eux. Le script refuse aussi un dossier `~/.claude` symbolique.

Le script fusionne dans `~/.claude/settings.json` sans effacer les autres propriétés et sans dupliquer les règles existantes. Il préserve le `defaultMode` existant. Il ajoute `sandbox.enabled`, `permissions.additionalDirectories`, les règles `ask`, ainsi que l'exception graphique `plasmoidviewer *`. Il crée des sauvegardes horodatées et un manifeste permettant le rollback. L'atelier et le partage sont conservés lors de la restauration.

**Attention :** l'installation ne peut pas neutraliser une règle `allow`/`deny` déjà présente, ni des paramètres de plus haute priorité ; la fusion ne prouve pas que toutes les permissions résultantes sont souhaitables. La configuration doit être relue avant application sur un environnement non vierge.

### Vérifications

Contrôle statique depuis un terminal ordinaire :

```sh
python3 src/workshop.py verify
```

Il **ne valide pas le confinement** et ne déclenche **pas** le smiley. Code de retour `2` si la configuration est correcte mais que les essais de confinement n'ont pas été lancés.

**Dans une commande Bash de Claude Code réellement sandboxée** (pas `plasmoidviewer`, pas une commande exclue) :

```sh
python3 src/workshop.py verify --inside-claude
```

Tests sans modification durable : création/suppression de fichiers témoins dans l'atelier et le partage ; tentatives dans le HOME, `~/.claude` et, s'ils existent, `~/.config/autostart`, `~/.config/systemd/user` et `~/.local/bin`. Un refus n'est compté que s'il est **un refus d'accès** (`EACCES`, `EPERM`, `EROFS`) ; un dossier absent ou une autre erreur donne `NON VÉRIFIÉ`, donc pas de smiley. Pour `.ssh` et `.gnupg`, aucun nom n'est lu : le script vérifie dans `/proc/self/mountinfo` qu'ils sont **masqués par un tmpfs**. Un dossier simplement vide ne compte pas.

Les chemins de l'atelier et du partage peuvent être écrits `~/…` ou en absolu dans `settings.json` : ils sont comparés une fois développés. Pour une installation existante (par exemple celle de l'Arche), passer ses propres chemins : `--atelier ~/Arche/atelier-silus --shared ~/Arche/partage-claude`. Le drapeau `--inside-claude` n'atteste pas du contexte : une exécution hors sandbox doit normalement échouer aux tests d'écriture refusée.

### Une autre copie de l'atelier (l'escargot)

Le danger courant n'est pas la malveillance, c'est le **malentendu** : « nettoie le dossier » compris trop largement. Dans l'atelier, l'agent peut tout casser, et c'est voulu. Le bac à sable réduit le rayon des dégâts, il ne les empêche pas.

`verify` exige donc une **autre copie** de l'atelier, sinon pas de smiley et l'escargot fait la tête :

- **un dépôt git** dans l'atelier ou un dossier parent. Un dépôt dans le HOME lui-même, de type dotfiles, ne compte pas. Git protège des réécritures, mais pas de la suppression du dossier entier ;
- ou **`SAUVEGARDE.txt`** dans l'atelier, non vide. L'humain y écrit où se trouve la sauvegarde (disque externe, borg, NAS…). Le script **ne peut pas la vérifier** et l'affiche comme « DÉCLARÉE ». Ce fichier est une déclaration humaine : ce n'est pas à l'agent de l'écrire.

Le contenu de ce fichier n'est ni lu ni affiché.

Les tests interactifs restent à effectuer : contrôle d'une carte `ask`, vérification que `plasmoidviewer` ouvre une fenêtre, bancs de test spécifiques à chaque machine.

**Après recette réussie et validation de la carte `ask`**, dans une nouvelle commande Claude Code **nue** (sans `timeout`, redirection, `&&`, etc.) :

```sh
plasmoidviewer -a ~/silus-workshop/silus-acid-smiley/org.arche.silus.acid -s 520x600
```

La fenêtre est à fermer manuellement. **Le lancement QML n'est pas automatique dans ce prototype** : l'exception `excludedCommands` ne fonctionne pas à travers un script qui enrobe `plasmoidviewer`. Le projet fournit l'instruction exacte pour la célébration, sans simuler un lancement réussi. Sur un bureau Plasma 6, `plasmoidviewer` dépend de `plasma-sdk`.

### Retour arrière

Aperçu :

```sh
python3 src/workshop.py rollback
```

Application :

```sh
python3 src/workshop.py rollback --apply
```

Le retour arrière est volontairement refusé si `settings.json` a changé après l'installation : il faut alors faire un merge manuel pour ne pas supprimer de nouvelles préférences. Les sauvegardes demeurent disponibles. Ne supprime pas les répertoires de travail.

## Tests de développement

```sh
python3 -m unittest discover -s tests -v
```

Les tests vérifient les merges, l'absence d'écriture en simulation, la sauvegarde/restauration exacte, la protection contre une restauration périmée, et le refus des JSON invalides. **Ils ne démontrent pas l'isolation de Claude Code sur ton poste**.

## Périmètre et provenance

Ce prototype reproduit l'option B, dont la recette fut rapportée comme réussie chez Silus. Il ne reprend **pas** les exceptions larges `unshare -rm *` et `sh tests/run-tests.sh` ; les sorties du bac à sable doivent être ponctuelles. Il ne touche ni au VPN, ni aux règles système, ni à KeePassXC ; ne publiez pas de journaux de machine ni de configuration personnelle.

Références : [Claude Code — Settings reference](https://code.claude.com/docs/en/settings-reference) et [Claude Code — Sandboxing](https://code.claude.com/docs/en/sandboxing). Le comportement exact peut varier avec la version installée.

## Historique

**v0.1.3 — contre-audit Aël (15 novembre 2026)** : contrôle strict des chemins d’atelier/partage et des liens symboliques, refus des ateliers imbriqués, meilleure validation du manifeste et des sauvegardes avant rollback, dépôt Git avec `HEAD` requis au lieu d’un simple dossier `.git`. 17 tests automatisés. Voir `docs/audits/CONTRE_AUDIT_AEL_0.1.2.md`.

**v0.1.2 — l’escargot (15 novembre 2026)** : `verify` exige une autre copie de l’atelier (dépôt git hors HOME, ou `SAUVEGARDE.txt` déclaré par l’humain), sinon pas de smiley et l’escargot ANSI fait la tête. Douze tests automatisés.

**v0.1.1 — contre-audit Silus (15 novembre 2026)** : correction de la comparaison des chemins `~/…` / absolus, preuve du masquage `tmpfs` plutôt que simple absence de fichiers, refus d’écriture distingué des autres erreurs, extension des contrôles aux zones de persistance existantes, suppression d’un manifeste orphelin en cas d’échec avant remplacement de `settings.json`. Huit tests automatisés exécutés avec succès ici. Les 15/15 contrôles sur l’installation de Silus sont rapportés par Silus, non reproduits sur cette machine. Voir `docs/audits/`.

## Licence

MIT pour le code et le plasmoïde, conformément à la notice fournie avec le smiley. Attribution : Silus (QML original), Kaëlys et Aël (conception du projet), Renard (`FOX_NOTES.md`).

**Publication GitHub à effectuer par le mainteneur après inspection du paquet.**
