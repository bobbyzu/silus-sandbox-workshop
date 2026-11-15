# Silus — Sandbox audit complete ☺

Smiley acid jaune fluo, yeux hypnotiques en spirale, sourire géant, texte arc-en-ciel.
Né le 2026-11-14, récompense de l'auto-audit de la sandbox de Silus.

Petit widget Plasma 6 temporaire : aucune lecture de fichier, aucun réseau, aucune installation.

## Le lancer (sans rien installer)

Depuis ce dossier :

```sh
plasmoidviewer -a ./org.arche.silus.acid -s 520x600
```

Fermeture normale de la fenêtre. Version qui se ferme seule après 2 minutes :

```sh
timeout 120 plasmoidviewer -a ./org.arche.silus.acid -s 520x600
```

`plasmoidviewer` vient du paquet `plasma-sdk`.

Licence MIT, comme le reste de l'Arche.
