
---

## 2. `TASK.md`

```md
# TASK.md — Plan de développement GeckoCare Xena

## Étape 1 — Initialisation du projet

Créer la structure du projet :

```txt
gecko-care-xena/
├── app.py
├── database.py
├── schema.sql
├── seed.py
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
└── data/

Créer une application Python locale simple.

Objectif de validation :

*   le projet se lance
    
*   une page d’accueil s’affiche
    
*   la base SQLite peut être créée
    

Ne pas passer à l’étape suivante avant validation.

Étape 2 — Base de données SQLite
--------------------------------

Créer les tables suivantes :

### gecko

Champs :

*   id
    
*   nom
    
*   espece
    
*   date\_naissance\_estimee
    
*   notes
    

### releves

Champs :

*   id
    
*   date\_releve
    
*   moment
    
*   temperature
    
*   humidite
    
*   brumisation
    
*   eau\_changee
    
*   notes
    
*   created\_at
    

### repas

Champs :

*   id
    
*   date\_repas
    
*   aliment
    
*   categorie
    
*   quantite
    
*   calcium\_sans\_d3
    
*   vitamine\_d3
    
*   notes
    
*   created\_at
    

### materiel

Champs :

*   id
    
*   nom
    
*   type
    
*   description
    
*   date\_debut
    
*   date\_fin
    
*   actif
    
*   notes
    
*   created\_at
    

### plantes

Champs :

*   id
    
*   nom
    
*   espece
    
*   type\_plante
    
*   etat
    
*   date\_ajout
    
*   notes
    
*   created\_at
    

### insectes\_actions

Champs :

*   id
    
*   date\_action
    
*   type\_insecte
    
*   nourrissage
    
*   nourriture\_donnee
    
*   brumisation
    
*   notes
    
*   created\_at
    

Objectif de validation :

*   la base est créée automatiquement
    
*   les tables existent
    
*   les données de test peuvent être insérées
    

Ne pas passer à l’étape suivante avant validation.

Étape 3 — Données initiales
---------------------------

Créer un fichier seed.py.

Insérer :

*   Xena
    
*   terrarium actuel 45x45x60
    
*   lampe LED
    
*   lampe chauffante été
    
*   lampe chauffante hiver
    
*   quelques plantes exemples
    
*   quelques relevés exemples
    
*   quelques repas exemples
    
*   quelques actions insectes exemples
    

Objectif de validation :

*   la base contient des données réalistes
    
*   le tableau de bord peut afficher ces données
    

Étape 4 — Tableau de bord
-------------------------

Créer une page tableau de bord.

Afficher :

*   dernier relevé matin
    
*   dernier relevé soir
    
*   dernière température
    
*   dernière humidité
    
*   dernier repas
    
*   matériel actif
    
*   alertes actives
    
*   plantes en mauvais état
    
*   statut des insectes
    

Objectif de validation :

*   les informations principales sont visibles dès l’arrivée sur l’application
    
*   les alertes s’affichent clairement
    

Étape 5 — Gestion des relevés
-----------------------------

Créer une page releves.

Fonctionnalités :

*   formulaire d’ajout
    
*   liste des derniers relevés
    
*   affichage matin / soir
    
*   brumisation oui/non
    
*   eau changée oui/non
    

Objectif de validation :

*   on peut ajouter un relevé
    
*   le relevé apparaît dans la liste
    
*   le tableau de bord se met à jour
    

Étape 6 — Gestion de l’alimentation
-----------------------------------

Créer une page repas.

Fonctionnalités :

*   ajouter un repas
    
*   choisir aliment
    
*   choisir catégorie
    
*   indiquer quantité
    
*   calcium sans D3 oui/non
    
*   vitamine D3 oui/non
    
*   notes
    

Objectif de validation :

*   on peut enregistrer ce que Xena mange
    
*   les alertes hebdomadaires fonctionnent
    

Étape 7 — Gestion des insectes
------------------------------

Créer une page insectes.

Fonctionnalités :

*   ajouter une action
    
*   type d’insecte : grillon, red runner, ver de farine
    
*   nourrissage oui/non
    
*   nourriture donnée
    
*   brumisation oui/non
    
*   notes
    

Règles :

*   grillons : nourrir et brumiser tous les 2 jours
    
*   red runner : brumiser une fois par semaine
    
*   vers de farine : pas de brumisation obligatoire
    

Objectif de validation :

*   on peut suivre l’entretien des insectes
    
*   les alertes insectes fonctionnent
    

Étape 8 — Gestion du matériel
-----------------------------

Créer une page materiel.

Fonctionnalités :

*   ajouter matériel
    
*   lister matériel
    
*   marquer actif/inactif
    
*   indiquer date de début et fin d’utilisation
    

Objectif de validation :

*   on sait quel matériel est utilisé actuellement
    
*   on peut conserver l’historique
    

Étape 9 — Gestion des plantes
-----------------------------

Créer une page plantes.

Fonctionnalités :

*   ajouter plante
    
*   nom
    
*   espèce
    
*   type : naturelle ou plastique
    
*   état : excellent, moyen, mauvais, décédé
    
*   notes
    

Objectif de validation :

*   les plantes sont listées
    
*   les plantes en mauvais état apparaissent sur le tableau de bord
    

Étape 10 — Alertes métier
-------------------------

Créer un module ou une fonction calculer\_alertes.

Alertes à gérer :

### Température

*   nuit < 17 °C : danger
    
*   nuit entre 17 et 20 °C : attention
    
*   nuit entre 20 et 22 °C : bon
    
*   jour entre 22 et 25 °C : bon
    
*   jour proche de 28 °C : danger
    
*   jour > 30 °C : critique
    

### Humidité

*   idéal : 50 à 60 %
    
*   45 à 50 % : acceptable avant brumisation
    
*   70 à 90 % : acceptable après brumisation
    
*   très bas ou très haut sans explication : attention
    

### Eau

*   si aucune brumisation et aucune eau changée aujourd’hui : danger
    

### Repas

*   moins de 2 repas sur 7 jours : attention
    
*   aucun insecte sur 7 jours : attention
    
*   vitamine D3 absente depuis plus de 30 jours : attention
    

### Insectes

*   grillons non nourris depuis plus de 2 jours : attention
    
*   grillons non brumisés depuis plus de 2 jours : attention
    
*   red runner non brumisés depuis plus de 7 jours : attention
    

Objectif de validation :

*   les alertes sont compréhensibles
    
*   les alertes apparaissent sur le tableau de bord
    

Étape 11 — Amélioration visuelle simple
---------------------------------------

Créer une interface agréable mais simple.

À faire :

*   menu de navigation
    
*   cartes de résumé
    
*   couleurs d’alerte
    
*   tableaux propres
    
*   formulaires lisibles
    
*   responsive minimal
    

Objectif de validation :

*   l’application est utilisable facilement sur ordinateur
    
*   pas besoin de design complexe
    

Étape 12 — README
-----------------

Créer un README avec :

*   objectif du projet
    
*   installation
    
*   lancement
    
*   initialisation de la base
    
*   description des pages
    
*   limites actuelles
    
*   améliorations possibles
    

Objectif de validation :

*   une autre personne peut lancer le projet en suivant le README
