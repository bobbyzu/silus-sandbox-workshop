# Contre-audit Aël — Silus Sandbox Workshop v0.1.2 → v0.1.3

Date : 15 novembre 2026. Analyse statique de l’archive v0.1.2 et du patch v0.1.1 → v0.1.2, tests en HOME temporaire. Aucun accès à la configuration réelle de Claude Desktop.

## Résultat

**Cinq corrections ciblées intégrées ; 17/17 tests réussis.** Publication possible comme outil expérimental, avec limites clairement annoncées.

## Constats et corrections

1. **IMPORTANT — Extension imprévue des zones inscriptibles.** `checked_path` refusait seulement HOME et `~/.claude`, mais acceptait `~/.ssh/x`, `~/.config/x`, un répertoire extérieur au HOME ou des chemins contenant des liens symboliques. La v0.1.3 impose des sous-dossiers ordinaires du HOME, sans composant caché ni chaîne symbolique. Les ateliers imbriqués sont refusés.
2. **MODÉRÉ — État rollback insuffisamment borné.** Un manifeste modifié pouvait diriger une restauration vers un fichier non prévu. La v0.1.3 refuse les manifestes symboliques/mal formés et les sauvegardes situées hors du répertoire attendu, ou symboliques. Les droits Unix ordinaires restent la frontière de confiance : elle ne résiste pas à un acteur qui contrôle le compte utilisateur.
3. **FAIBLE — Faux dépôt Git.** Un dossier vide `.git` suffisait à passer le test ; `.git/HEAD` est maintenant exigé. Ceci ne prouve toujours ni commit, ni distant, ni autre copie hors de la machine. L’alternative `SAUVEGARDE.txt` reste une simple déclaration humaine.
4. **COMPATIBILITÉ — Refus volontaire** des espaces de travail hors HOME, cachés ou symlinkés ; les installations légitimes de ce type doivent adapter les chemins avant `install`.

## Tests exécutés

`python3 -m unittest discover -s tests -q` : **17 tests, OK** sur HOME temporaires. Installation, merge, restauration, configuration invalide, chemins `~`, erreurs de masquage et sauvegarde, refus de chemins sensibles, liens symboliques, imbrication, manifeste et chemin de sauvegarde manipulés.

## Limites et travaux ultérieurs

- Aucun test en situation réelle de Claude Desktop/Claude Code : confinement, cartes `ask`, serveurs MCP, outils fichiers et comportement du plasmoïde non certifiés ici.
- Les autorisations préexistantes sont fusionnées et ne sont pas auditées exhaustivement. `excludedCommands` autorise `plasmoidviewer *` hors bac à sable ; l’utilisateur doit contrôler cette exception.
- La détection `other_copy` est un indicateur de prudence, **pas une attestation de sauvegarde**.
- Les données de la documentation d’origine proviennent du récapitulatif de Silus ; elles ne sont pas une mesure effectuée dans cet audit.
- Ne jamais publier les paramètres réels `~/.claude/settings.json`, les sauvegardes ni les journaux locaux.

## Avis

**Favorable à une publication expérimentale de v0.1.3**, après validation locale du mainteneur et signalement explicite de ces limites. Ce contre-audit n’est pas une certification de sécurité.
