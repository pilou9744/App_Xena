# Mise en ligne sur GitHub

Ce guide sert a publier GeckoCare Xena sur GitHub proprement.

## 1. Installer Git

Si la commande `git` n'est pas reconnue dans le terminal, installer Git pour Windows :

```txt
https://git-scm.com/download/win
```

Pendant l'installation, garder les options par defaut convient dans la plupart des cas.

Verifier ensuite :

```bash
git --version
```

## 2. Initialiser le depot local

Depuis le dossier du projet :

```bash
git init
git branch -M main
git status
```

Verifier que les fichiers suivants ne sont pas proposes au commit :

- `data/gecko.db`
- `data/*.db`
- `data/sauvegardes/`
- `build/`
- `dist/`
- `__pycache__/`

## 3. Premier commit

```bash
git add .
git commit -m "Initial commit"
```

## 4. Creer le depot sur GitHub

Nom conseille :

```txt
geckocare-xena
```

Description conseillee :

```txt
Application web locale pour suivre les soins, repas, releves et alertes d'un gecko a crete.
```

Options conseillees :

- Public ou prive selon ton choix.
- Ne pas cocher "Add a README file", car il existe deja.
- Ne pas ajouter de `.gitignore`, car il existe deja.
- Ne pas ajouter de licence au moment de la creation si tu veux la choisir plus tard.

Topics possibles :

```txt
python
flask
sqlite
vanilla-js
pet-care
gecko
local-first
```

## 5. Relier le depot local a GitHub

Remplacer `TON_UTILISATEUR` par ton pseudo GitHub :

```bash
git remote add origin https://github.com/TON_UTILISATEUR/geckocare-xena.git
git push -u origin main
```

## 6. Apres publication

Verifier sur GitHub que :

- le README s'affiche correctement ;
- les fichiers `.db` ne sont pas presents ;
- le dossier `dist/` n'est pas present ;
- aucune URL Discord ni token Discord n'est visible ;
- le nom et la description du depot sont clairs.

## Option avec GitHub CLI

Si `gh` est installe et connecte :

```bash
gh repo create geckocare-xena --public --source=. --remote=origin --push --description "Application web locale pour suivre les soins, repas, releves et alertes d'un gecko a crete."
```

Utiliser `--private` a la place de `--public` si le depot doit rester prive.
