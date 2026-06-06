CREATE TABLE IF NOT EXISTS gecko (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    espece TEXT,
    date_naissance_estimee TEXT,
    numero_marquage TEXT,
    procedure_marquage TEXT,
    date_adoption TEXT,
    ordre TEXT,
    sexe TEXT,
    nom_vernaculaire TEXT,
    nom_scientifique TEXT,
    classe TEXT,
    origine TEXT,
    pays_origine TEXT,
    taille TEXT,
    taille_valeur REAL,
    taille_unite TEXT DEFAULT 'cm',
    poids TEXT,
    poids_unite TEXT DEFAULT 'g',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS releves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER,
    date_releve TEXT NOT NULL,
    heure_releve TEXT,
    moment TEXT NOT NULL CHECK (moment IN ('matin', 'soir')),
    temperature REAL NOT NULL,
    humidite INTEGER NOT NULL,
    brumisation INTEGER NOT NULL DEFAULT 0 CHECK (brumisation IN (0, 1)),
    eau_changee INTEGER NOT NULL DEFAULT 0 CHECK (eau_changee IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS repas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER,
    date_repas TEXT NOT NULL,
    heure_repas TEXT,
    aliment TEXT NOT NULL,
    categorie TEXT NOT NULL,
    quantite TEXT,
    calcium_sans_d3 INTEGER NOT NULL DEFAULT 0 CHECK (calcium_sans_d3 IN (0, 1)),
    vitamine_d3 INTEGER NOT NULL DEFAULT 0 CHECK (vitamine_d3 IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS poids_mesures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    date_mesure TEXT NOT NULL,
    poids REAL NOT NULL,
    unite TEXT NOT NULL DEFAULT 'g' CHECK (unite IN ('g', 'kg')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS taille_mesures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    date_mesure TEXT NOT NULL,
    taille REAL NOT NULL,
    unite TEXT NOT NULL DEFAULT 'cm' CHECK (unite IN ('cm', 'mm', 'm')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    date_observation TEXT NOT NULL,
    heure_observation TEXT,
    categorie TEXT NOT NULL DEFAULT 'comportement' CHECK (categorie IN ('comportement', 'mue', 'selles', 'sante', 'reproduction', 'entretien', 'autre')),
    niveau TEXT NOT NULL DEFAULT 'normal' CHECK (niveau IN ('normal', 'a_surveiller', 'inquietant')),
    description TEXT NOT NULL,
    photo TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS aliments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    categorie TEXT NOT NULL,
    notes TEXT,
    masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS materiel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER,
    nom TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    date_debut TEXT,
    date_fin TEXT,
    statut TEXT NOT NULL DEFAULT 'ok',
    actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1)),
    est_consommable INTEGER NOT NULL DEFAULT 0 CHECK (est_consommable IN (0, 1)),
    quantite_initiale REAL,
    quantite_restante REAL,
    unite_quantite TEXT DEFAULT 'g',
    statut_contenant TEXT NOT NULL DEFAULT 'non_applicable' CHECK (statut_contenant IN ('non_applicable', 'rempli', 'moitie', 'vide')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS materiel_mesures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    materiel_id INTEGER NOT NULL,
    date_mesure TEXT NOT NULL,
    quantite_restante REAL NOT NULL CHECK (quantite_restante >= 0),
    unite TEXT NOT NULL DEFAULT 'g',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (materiel_id) REFERENCES materiel(id)
);

CREATE TABLE IF NOT EXISTS types_materiel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    notes TEXT,
    masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER,
    nom TEXT NOT NULL,
    espece TEXT,
    type_plante TEXT NOT NULL CHECK (type_plante IN ('naturelle', 'plastique')),
    etat TEXT NOT NULL CHECK (etat IN ('excellent', 'moyen', 'mauvais', 'decede')),
    date_ajout TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES gecko(id)
);

CREATE TABLE IF NOT EXISTS insectes_boites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    type_insecte TEXT NOT NULL,
    nombre_individus INTEGER NOT NULL DEFAULT 0 CHECK (nombre_individus >= 0),
    statut TEXT NOT NULL DEFAULT 'active' CHECK (statut IN ('active', 'vide')),
    date_vide TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insectes_comptages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    boite_id INTEGER NOT NULL,
    date_comptage TEXT NOT NULL,
    nombre_individus INTEGER NOT NULL CHECK (nombre_individus >= 0),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boite_id) REFERENCES insectes_boites(id)
);

CREATE TABLE IF NOT EXISTS insectes_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_action TEXT NOT NULL,
    heure_action TEXT,
    type_insecte TEXT NOT NULL,
    boite TEXT NOT NULL DEFAULT 'Boite principale',
    nourrissage INTEGER NOT NULL DEFAULT 0 CHECK (nourrissage IN (0, 1)),
    nourriture_donnee TEXT,
    brumisation INTEGER NOT NULL DEFAULT 0 CHECK (brumisation IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reglages (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discord_alertes_envoyees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signature TEXT NOT NULL UNIQUE,
    type_envoi TEXT NOT NULL,
    date_envoi TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS materiel_journalier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_utilisation TEXT NOT NULL,
    materiel_id INTEGER NOT NULL,
    utilise INTEGER NOT NULL DEFAULT 1 CHECK (utilise IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date_utilisation, materiel_id),
    FOREIGN KEY (materiel_id) REFERENCES materiel(id)
);

CREATE TABLE IF NOT EXISTS alertes_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cle TEXT NOT NULL,
    libelle TEXT NOT NULL,
    source TEXT NOT NULL,
    niveau TEXT NOT NULL DEFAULT 'attention' CHECK (niveau IN ('info', 'attention', 'danger', 'critique')),
    actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1)),
    animal_id INTEGER,
    seuil_min REAL,
    seuil_max REAL,
    delai_valeur REAL,
    delai_unite TEXT CHECK (delai_unite IN ('heures', 'jours')),
    unite TEXT,
    phantome INTEGER NOT NULL DEFAULT 0 CHECK (phantome IN (0, 1)),
    preavis_valeur REAL NOT NULL DEFAULT 6,
    preavis_unite TEXT NOT NULL DEFAULT 'heures' CHECK (preavis_unite IN ('heures', 'jours')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cle, animal_id)
);
