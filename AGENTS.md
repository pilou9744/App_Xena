# AGENTS.md — Projet GeckoCare Xena

## Objectif du projet

Créer une application web simple pour gérer le suivi quotidien d’un gecko à crête nommé Xena.

L’application doit permettre de remplacer un carnet papier / Excel par une interface web simple avec :
- Python
- SQLite
- HTML
- CSS
- JavaScript vanilla
- Aucun framework web lourd
- Interface claire, simple et locale

Le but principal est d’aider à maintenir le gecko dans de bonnes conditions :
- température
- humidité
- brumisation
- eau disponible
- alimentation
- supplémentation calcium / vitamine D3
- suivi du matériel
- suivi des plantes
- suivi des insectes servant à nourrir le gecko
- alertes simples quand certains paramètres sont mauvais ou à vérifier

## Contraintes techniques

Utiliser uniquement :
- Python 3
- SQLite
- HTML
- CSS
- JavaScript vanilla

Ne pas utiliser :
- React
- Angular
- Vue
- Bootstrap
- Django
- Flask lourd avec architecture complexe
- ORM complexe

Flask peut être utilisé uniquement comme micro-serveur si nécessaire, mais garder le projet très simple.

## Architecture attendue

Structure recommandée :

```txt
gecko-care-xena/
│
├── app.py
├── database.py
├── schema.sql
├── seed.py
├── requirements.txt
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── observations.html
│   ├── feedings.html
│   ├── insects.html
│   ├── equipment.html
│   └── plants.html
│
├── data/
│   └── gecko.db
│
└── README.md

Règles de développement
-----------------------

1.  Le code doit rester simple et lisible.
    
2.  Chaque fonctionnalité doit être testable manuellement depuis l’interface.
    
3.  Les noms doivent être en français autant que possible.
    
4.  Les commentaires doivent expliquer les parties importantes.
    
5.  L’application doit fonctionner en local.
    
6.  La base SQLite doit être créée automatiquement si elle n’existe pas.
    
7.  Ne jamais supprimer les anciennes données sans confirmation.
    
8.  Prévoir une navigation simple entre les pages.
    
9.  Les alertes doivent être visibles dans le tableau de bord.
    
10.  L’interface doit être utilisable par une personne non développeuse.
    

Données métier principales
--------------------------

### Animal

Le gecko s’appelle Xena.

Date importante :

*   Xena fête ses 2 ans et 6 mois le 15/05/2026.
    

Il faut pouvoir stocker :

*   nom
    
*   espèce
    
*   date de naissance estimée ou âge
    
*   notes générales
    

### Température et humidité

Deux relevés par jour :

*   matin : température de la nuit
    
*   soir : température de la journée
    

Température de nuit :

*   idéal : 20 à 22 °C
    
*   minimum toléré : 17 °C
    
*   sous 17 °C : alerte
    

Température de jour :

*   idéal : 22 à 25 °C
    
*   proche de 28 °C : dangereux
    
*   au-dessus de 30 °C : critique
    

Humidité :

*   idéal : 50 à 60 %
    
*   après brumisation : 70 à 90 %
    
*   avant brumisation : 45 à 50 %
    
*   trop bas ou trop haut de manière prolongée : alerte
    

### Eau et brumisation

Il faut pouvoir indiquer :

*   brumisation faite ou non
    
*   eau de la gamelle changée ou non
    

Règle :

*   Si la gamelle n’est pas changée mais que la brumisation est faite, c’est acceptable.
    
*   Si la brumisation n’est pas faite mais que l’eau est changée, c’est acceptable.
    
*   Le but est que Xena puisse boire.
    

Si aucune des deux actions n’est faite sur une journée, afficher une alerte.

### Alimentation

Types de nourriture :

*   insectes
    
*   grillons
    
*   red runner
    
*   vers de farine
    
*   Repashy
    
*   compote humaine sans sucre ajouté
    
*   fruits
    

Fréquence :

*   Xena doit manger 2 à 3 fois par semaine.
    
*   Au moins une fois par semaine avec insectes.
    
*   Les insectes doivent être supplémentés avec calcium sans D3.
    
*   Vitamine D3 : une fois par mois.
    

Il faut pouvoir enregistrer :

*   date
    
*   type de nourriture
    
*   quantité
    
*   supplément calcium sans D3 oui/non
    
*   supplément vitamine D3 oui/non
    
*   notes
    

Alertes :

*   moins de 2 repas dans la semaine
    
*   aucun insecte dans la semaine
    
*   vitamine D3 non donnée depuis plus d’un mois
    

### Matériel

Il faut pouvoir enregistrer le matériel utilisé :

*   terrarium
    
*   lampe LED
    
*   lampe chauffante été
    
*   lampe chauffante hiver
    
*   autre matériel ajouté manuellement
    

Pour le terrarium :

*   taille actuelle : 45x45x60
    
*   possibilité d’indiquer lequel est actif
    
*   possibilité de changer de terrarium dans le temps
    

Le matériel est important pour comprendre les tendances de température et d’humidité.

Champs :

*   nom
    
*   type
    
*   description
    
*   date de début d’utilisation
    
*   date de fin d’utilisation
    
*   actif oui/non
    
*   notes
    

### Plantes

Il faut pouvoir enregistrer :

*   nom
    
*   espèce
    
*   type : naturelle ou plastique
    
*   état : excellent, moyen, mauvais, décédé
    
*   date d’ajout
    
*   notes
    

### Insectes

Les insectes servent à nourrir le gecko. Il faut aussi suivre leur entretien.

#### Grillons

Alimentation possible :

*   carotte
    
*   courgette
    
*   pomme
    
*   flocons d’avoine
    
*   céréales
    
*   nourriture sèche spéciale insectes
    

Fréquence :

*   nourrir tous les 2 jours
    
*   brumiser tous les 2 jours
    

#### Red runner

Alimentation possible :

*   légumes
    
*   fruits
    
*   avoine
    
*   nourriture sèche spéciale insectes
    

Fréquence :

*   brumiser une fois par semaine
    

#### Vers de farine

Alimentation :

*   blé
    
*   flocons d’avoine
    
*   carotte
    
*   pomme
    
*   pomme de terre
    

Fréquence :

*   pas de brumisation
    

Il faut pouvoir enregistrer :

*   type d’insecte
    
*   date de nourrissage
    
*   type de nourriture donnée
    
*   brumisation faite oui/non
    
*   notes
    

Alertes :

*   grillons non nourris depuis plus de 2 jours
    
*   grillons non brumisés depuis plus de 2 jours
    
*   red runner non brumisés depuis plus de 7 jours
    

Pages attendues
---------------

### Tableau de bord

Afficher :

*   dernières températures
    
*   dernière humidité
    
*   alertes actives
    
*   dernier repas de Xena
    
*   prochaine action conseillée
    
*   état rapide des insectes
    
*   matériel actif
    
*   plantes avec état mauvais ou décédé
    

### Relevés

Formulaire pour ajouter :

*   date
    
*   moment : matin ou soir
    
*   température
    
*   humidité
    
*   brumisation oui/non
    
*   eau changée oui/non
    
*   notes
    

Liste des derniers relevés.

### Alimentation

Formulaire pour ajouter un repas :

*   date
    
*   aliment
    
*   quantité
    
*   calcium sans D3 oui/non
    
*   vitamine D3 oui/non
    
*   notes
    

Liste des repas.

### Insectes

Formulaire pour ajouter une action :

*   type d’insecte
    
*   nourrissage oui/non
    
*   nourriture donnée
    
*   brumisation oui/non
    
*   notes
    

Liste des actions.

### Matériel

CRUD simple :

*   ajouter matériel
    
*   modifier matériel
    
*   marquer actif/inactif
    

### Plantes

CRUD simple :

*   ajouter plante
    
*   modifier état
    
*   notes
    

Alertes
-------

Créer une fonction Python simple qui calcule les alertes.

Exemples :

*   Température nuit sous 17 °C
    
*   Température jour supérieure ou égale à 28 °C
    
*   Température jour supérieure à 30 °C : critique
    
*   Humidité trop basse
    
*   Aucun accès à l’eau aujourd’hui
    
*   Pas assez de repas cette semaine
    
*   Aucun insecte cette semaine
    
*   Vitamine D3 non donnée depuis plus d’un mois
    
*   Grillons à nourrir
    
*   Grillons à brumiser
    
*   Red runner à brumiser
    

Chaque alerte doit avoir :

*   niveau : info, attention, danger, critique
    
*   message
    
*   date
    
*   source
    

Style interface
---------------

Interface simple :

*   fond clair
    
*   cartes
    
*   tableaux lisibles
    
*   boutons simples
    
*   couleurs d’alerte visibles
    

Pas besoin de design complexe.

Important
---------

Ne pas tout faire d’un coup sans validation.

Travailler étape par étape selon TASK.md.


## Style CSS attendu

Créer une interface simple, douce et tropicale, inspirée d’un terrarium pour gecko à crête.

---

## Ambiance visuelle

Le site doit donner une impression :

- naturelle
- tropicale
- calme
- propre
- facile à lire

Utiliser une palette de couleurs inspirée de :

- vert feuillage
- vert mousse
- beige sable
- brun naturel
- orange doux / corail pour rappeler le gecko
- blanc cassé pour les fonds

---

## Palette conseillée

```css
:root {
  --color-bg: #f6f3e8;
  --color-surface: #ffffff;

  --color-primary: #4f7f52;
  --color-primary-dark: #2f5233;

  --color-secondary: #d98c45;
  --color-accent: #f2c078;

  --color-text: #263524;
  --color-muted: #6f7f68;
  --color-border: #d8d0b8;

  --color-info: #4a90a4;
  --color-success: #5f9f5f;
  --color-warning: #e0a100;
  --color-danger: #d96b4c;
  --color-critical: #b83232;
}
```

---

## Règles de design

- Fond général blanc cassé / beige clair
- Cartes blanches avec bordure douce et coins arrondis
- Menu simple en haut ou sur le côté
- Titres en vert foncé
- Boutons petits, arrondis, sobres
- Bouton principal vert
- Bouton secondaire orange doux
- Tableaux lisibles avec lignes alternées très légères
- Espacement confortable
- Pas de design chargé

---

## Alertes

Les alertes doivent être très visibles :

- info : bleu doux
- attention : jaune/orange
- danger : orange/rouge
- critique : rouge foncé

Chaque alerte doit être affichée dans une carte ou un bandeau avec :

- couleur de fond claire
- bordure gauche colorée
- texte lisible
- niveau visible

### Exemple CSS

```css
.alert {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  margin-bottom: 0.75rem;
  border-left: 6px solid;
  background: #fff;
}

.alert.info {
  border-left-color: var(--color-info);
  background: #eef7fa;
}

.alert.attention {
  border-left-color: var(--color-warning);
  background: #fff7df;
}

.alert.danger {
  border-left-color: var(--color-danger);
  background: #fff0e8;
}

.alert.critique {
  border-left-color: var(--color-critical);
  background: #fdeaea;
  font-weight: 600;
}
```

---

## Boutons

Les boutons doivent être petits, propres et cohérents.

### Exemple CSS

```css
.btn {
  display: inline-block;
  padding: 0.35rem 0.7rem;
  border-radius: 8px;
  border: none;
  font-size: 0.9rem;
  cursor: pointer;
  text-decoration: none;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-secondary {
  background: var(--color-secondary);
  color: white;
}

.btn-danger {
  background: var(--color-danger);
  color: white;
}
```

---

## Tableaux

Les tableaux doivent être harmonieux et faciles à lire.

### Exemple CSS

```css
.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border-radius: 12px;
  overflow: hidden;
}

.table th {
  background: var(--color-primary-dark);
  color: white;
  text-align: left;
  padding: 0.7rem;
}

.table td {
  padding: 0.65rem;
  border-bottom: 1px solid var(--color-border);
}

.table tr:nth-child(even) {
  background: #faf7ee;
}
```

---

## Cartes

### Exemple CSS

```css
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(38, 53, 36, 0.08);
}
```

---

## Important

- Ne pas utiliser Bootstrap
- Ne pas utiliser de framework CSS
- Créer un fichier unique :

```txt
static/css/style.css
```

Le CSS doit être :
- clair
- organisé
- réutilisable
- cohérent

---

## Phrase courte à ajouter au prompt principal

```txt
Je veux un style tropical doux inspiré d’un terrarium de gecko : vert feuillage, beige sable, brun naturel, orange/corail doux. Les alertes doivent être très visibles, les tableaux harmonieux, et les boutons petits, arrondis et cohérents. Ne pas utiliser Bootstrap.
```
