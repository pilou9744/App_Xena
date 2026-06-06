# GeckoCare Xena

Application web locale pour suivre les soins quotidiens de Xena, un gecko a crete.

GeckoCare Xena remplace un carnet papier ou un fichier Excel par une interface simple pour noter les releves, les repas, les insectes, le materiel, les plantes et les alertes importantes.

## Fonctionnalites

- Tableau de bord avec les dernieres donnees et les alertes actives.
- Suivi des temperatures, de l'humidite, de la brumisation et de l'eau disponible.
- Suivi des repas, du calcium sans D3 et de la vitamine D3.
- Suivi des boites d'insectes et des actions d'entretien.
- Gestion du materiel utilise dans le temps.
- Gestion des plantes du terrarium et de leur etat.
- Reglages locaux, dont l'envoi optionnel d'alertes Discord.
- Sauvegardes SQLite locales.
- Lanceur Windows et generation optionnelle d'un executable.

## Apercu

Le projet est prevu pour un usage local, simple et lisible, sans framework lourd :

- Python 3
- Flask comme micro-serveur local
- SQLite
- HTML
- CSS
- JavaScript vanilla

## Installation

Prerequis :

- Python 3.10 ou plus recent
- Git, si tu veux cloner ou versionner le projet

Installer les dependances :

```bash
pip install -r requirements.txt
```

## Initialisation

Creer la base SQLite et inserer les donnees de depart :

```bash
python seed.py
```

Le script peut etre relance sans dupliquer les donnees initiales.

## Lancement

```bash
python app.py
```

Puis ouvrir :

```txt
http://127.0.0.1:5000/
```

## Application Windows autonome

Pour lancer GeckoCare sans Visual Studio Code :

```bash
python desktop_launcher.py
```

Ce lanceur initialise la base, demarre les notifications Discord automatiques, lance le serveur local et ouvre le tableau de bord.

Pour creer un executable Windows :

```bat
build_windows.bat
```

L'executable sera cree dans `dist\GeckoCareXena.exe`. Les donnees SQLite restent conservees dans le dossier `data` place a cote de l'executable.

## Pages principales

- `/dashboard` : vue d'ensemble et alertes.
- `/releves` : temperatures, humidite, brumisation et eau.
- `/repas` : alimentation, calcium sans D3 et vitamine D3.
- `/insectes` : actions de nourrissage et brumisation.
- `/boites-insectes` : boites d'insectes et nombre d'individus.
- `/materiel` : materiel actif ou historique.
- `/plantes` : plantes et etat de sante.
- `/reglages` : preferences de l'application et notifications Discord.

## Alertes suivies

Le tableau de bord signale notamment :

- Temperature de nuit trop basse.
- Temperature de jour dangereuse ou critique.
- Humidite trop basse ou trop haute.
- Absence d'acces a l'eau note aujourd'hui.
- Moins de deux repas sur sept jours.
- Absence d'insectes sur sept jours.
- Vitamine D3 absente depuis plus de trente jours.
- Grillons a nourrir ou brumiser.
- Red runner a brumiser.
- Plantes en mauvais etat.
- Materiel ou actions importantes a verifier.

## Structure du projet

```txt
App_Xena_V5/
|-- app.py
|-- database.py
|-- schema.sql
|-- seed.py
|-- requirements.txt
|-- static/
|   |-- css/
|   |-- img/
|   `-- js/
|-- templates/
|-- data/
`-- README.md
```

## Donnees locales et confidentialite

Le dossier `data/` contient la base SQLite et les sauvegardes locales. Ces fichiers ne doivent pas etre envoyes sur GitHub, car ils peuvent contenir :

- les observations de Xena ;
- les reglages de l'application ;
- une URL de webhook Discord ou un token si l'option Discord est configuree.

Le fichier `.gitignore` exclut donc les bases `.db`, les sauvegardes, les builds, les caches Python et les fichiers temporaires.

## Nom et description GitHub conseilles

Nom du depot :

```txt
geckocare-xena
```

Description courte :

```txt
Application web locale pour suivre les soins, repas, releves et alertes d'un gecko a crete.
```

Topics GitHub possibles :

```txt
python, flask, sqlite, vanilla-js, pet-care, gecko, local-first
```

## Limites actuelles

- Application prevue pour un usage local.
- Pas de comptes utilisateurs.
- Pas de graphiques de tendance avances pour le moment.
- Suppressions definitives apres confirmation.
- L'executable Windows reste une application locale : il lance un mini serveur sur `127.0.0.1`.

## Ameliorations possibles

- Export CSV.
- Sauvegarde automatique configurable.
- Graphiques de tendance temperature / humidite.
- Interface de bureau integree sans navigateur.
- Mode multi-animaux plus complet.

## Licence

A definir avant publication publique. Pour un projet personnel visible sur GitHub, une licence simple comme MIT peut convenir si tu veux autoriser la reutilisation du code.
