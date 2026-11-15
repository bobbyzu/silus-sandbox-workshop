# Historique des versions

## v0.1.3 — 15 novembre 2026

Contre-audit Aël de la v0.1.2 : validation des chemins et chaînes symboliques, refus de l’imbrication atelier/partage, durcissement du rollback (manifeste et chemin de backup), rejet des faux dépôts `.git` sans HEAD ; 17 tests réussis. Les mécanismes de sandbox Claude Code restent à valider sur la machine cible.

## v0.1.2 — 15 novembre 2026

L’escargot : contrôle d’une autre copie de l’atelier.

- `verify` cherche d’abord une autre copie : un dépôt `.git` dans l’atelier ou un dossier parent, le HOME lui-même étant exclu (dotfiles), sinon un `SAUVEGARDE.txt` non vide et non symbolique, affiché « DÉCLARÉE » et non vérifiable. Le contenu n’est ni lu ni affiché.
- Sans autre copie : pas de smiley, bannière ANSI de l’escargot boudeur, code de retour non nul.
- Douze tests automatisés (quatre nouveaux : aucune copie, git parent hors HOME, déclaration, déclaration vide).
- Aucun changement des fonctions d’installation et de rollback de la v0.1.1.

## v0.1.1 — 15 novembre 2026

Intégration des corrections et des tests fournis dans le contre-audit de Silus.

- Équivalence des chemins `~/…` et absolus pour les autorisations et la déduplication.
- Masquage de `.ssh` et `.gnupg` vérifié par le montage `tmpfs`, pas par un dossier vide.
- Refus d’écriture reconnu uniquement sur `EACCES`, `EPERM` ou `EROFS`; autres erreurs non validantes.
- Contrôles supplémentaires des zones de persistance déjà présentes.
- Nettoyage du manifeste en cas d’échec d’installation avant remplacement de la configuration.
- Huit tests automatisés réussis dans l’environnement de construction.

Les tests interactifs (règles `ask`, fenêtre graphique, bancs propres à la machine) restent hors de la recette automatisée. Aucun déploiement sur les machines de l’Arche ni publication GitHub.
