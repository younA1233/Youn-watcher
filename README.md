# CROUS Watcher — Alertes logement Grenoble

Surveille automatiquement trouverunlogement.lescrous.fr et t'envoie une
notification push dès qu'un nouveau logement apparaît dans ta zone.
Gratuit, tourne dans le cloud GitHub (aucun PC à laisser allumé).

## Étape 1 — Installer l'appli ntfy sur ton téléphone
- iOS : « ntfy » sur l'App Store
- Android : « ntfy » sur le Play Store

Choisis un nom de "topic" **long et aléatoire** (personne d'autre ne doit
pouvoir le deviner, sinon il pourrait lire ou spammer tes notifs) :
ex. `crous-grenoble-j8f3k92m-x7q1`

Dans l'appli ntfy : bouton **+** → tape exactement ce nom → **Subscribe**.

## Étape 2 — Récupérer ton URL de recherche CROUS
1. Va sur https://trouverunlogement.lescrous.fr
2. Fais une recherche sur Grenoble, déplace/zoome la carte sur ta zone,
   clique sur **« Rechercher dans cette zone »**
3. Ajoute tes filtres (budget, type de logement...)
4. Copie l'URL complète dans la barre d'adresse (elle contient des
   coordonnées `bounds=...`)

## Étape 3 — Créer un dépôt GitHub
1. Sur https://github.com : **New repository** → **Public** (nécessaire
   pour des minutes GitHub Actions gratuites et illimitées)
2. Mets tous les fichiers de ce dossier dedans (garde l'arborescence
   `.github/workflows/check.yml`), puis :
   ```
   git init
   git add .
   git commit -m "Ajout du bot CROUS"
   git branch -M main
   git remote add origin https://github.com/TON_PSEUDO/NOM_DU_REPO.git
   git push -u origin main
   ```

## Étape 4 — Ajouter les 2 secrets
Sur la page du dépôt : **Settings → Secrets and variables → Actions →
New repository secret**

| Nom du secret      | Valeur                        |
|---------------------|-------------------------------|
| `CROUS_SEARCH_URL`  | l'URL copiée à l'étape 2      |
| `NTFY_TOPIC`        | le nom de topic choisi étape 1|

Puis : **Settings → Actions → General → Workflow permissions** →
sélectionne **« Read and write permissions »** (pour que le bot puisse
sauvegarder son état automatiquement).

## Étape 5 — Tester
Onglet **Actions** du dépôt → **« Check CROUS Grenoble »** → **Run
workflow**. Au bout d'~1 minute tu dois recevoir la notif
« ✅ Surveillance active ». Ensuite ça tourne tout seul, toutes les heures.

## Limites à connaître
- Sans être connecté avec ton propre compte (DSE) sur le site, seule une
  partie de l'offre est visible. Le bot sert de **signal d'alerte** — il
  faut ensuite te connecter sur MesServices.etudiant.gouv.fr pour voir
  l'offre complète et réserver.
- Le bot ne réserve rien à ta place, il notifie seulement.
- Si le CROUS change la structure de sa page, le parsing peut casser —
  regarde les logs de l'Action en cas de "0 logement" suspect.
