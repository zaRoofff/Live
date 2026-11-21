# Prolonge le Live – overlay TikTok

Chrono de live : **1 pièce = +1 sec**, **1 follow = +10 sec**, ajouté automatiquement via TikFinity.

## Installation
1. Télécharge `prolonge-le-live.html` et mets-le dans un dossier (ex : `C:\Live\`).
2. Ouvre-le avec le Bloc-notes et règle le bloc `REGLAGES` en haut (ton pseudo, temps de départ…).
3. Lance **TikFinity** et connecte-le à ton live (il doit tourner pendant le live).
4. Ajoute l'overlay :
   - **OBS** : Source > Navigateur > coche « Fichier local » > choisis le fichier. Taille 560 x 450.
   - **TikTok LIVE Studio** : Ajouter une source > Lien > colle `file:///C:/Live/prolonge-le-live.html`.

## Commandes chat (toi + tes modos)
- `!temps +5m` / `!temps -30s` : ajouter / enlever
- `!temps 2h` : mettre le chrono à 2h
- `!temps pause` / `!temps go` / `!temps reset`

## Options d'URL (facultatif)
`?depart=1h30&piece=1&follow=10&pseudo=tonpseudo&max=12h&scale=1.2&status=0`
- `demo=1&bg=1` : aperçu avec de faux dons
- `reset=1` : repart de zéro (à enlever ensuite)

Le chrono est sauvegardé : s'il recharge pendant le live, il reprend où il en était.
Un même follower ne compte qu'une fois (anti unfollow/refollow).
