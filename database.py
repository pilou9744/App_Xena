from pathlib import Path
from datetime import date
import os
import shutil
import sqlite3
import sys


BASE_DIR = Path(__file__).resolve().parent
RESSOURCES_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))


def dossier_donnees():
    """Retourne le dossier data stable, meme quand l'application est lancee depuis dist."""
    dossier_env = os.environ.get("GECKOCARE_DATA_DIR")
    if dossier_env:
        return Path(dossier_env).expanduser().resolve()

    if not getattr(sys, "frozen", False):
        return BASE_DIR / "data"

    # En mode executable, la base doit rester a cote de l'application et non
    # dans le dossier temporaire PyInstaller. Si l'exe est lance depuis dist,
    # on privilegie donc le dossier data du projet parent
    exe_dir = Path(sys.executable).resolve().parent
    candidats = [
        exe_dir.parent / "data" if exe_dir.name.lower() == "dist" else None,
        exe_dir / "data",
    ]
    for candidat in candidats:
        if candidat and (candidat / "gecko.db").exists():
            return candidat

    return (exe_dir.parent / "data") if exe_dir.name.lower() == "dist" else (exe_dir / "data")


DATA_DIR = dossier_donnees()
DB_PATH = DATA_DIR / "gecko.db"
BACKUP_DIR = DATA_DIR / "sauvegardes"
SCHEMA_PATH = RESSOURCES_DIR / "schema.sql"
DB_SOURCE_PATH = RESSOURCES_DIR / "data" / "gecko.db"


def preparer_fichier_base():
    DATA_DIR.mkdir(exist_ok=True)
    # Lors du premier lancement de l'executable, on copie la base embarquee
    # vers le dossier data stable. Les lancements suivants gardent les donnees
    # utilisateur deja presentes.
    if not DB_PATH.exists() and DB_SOURCE_PATH.exists() and DB_SOURCE_PATH != DB_PATH:
        shutil.copy2(DB_SOURCE_PATH, DB_PATH)


def sauvegarder_base_quotidienne():
    if not DB_PATH.exists():
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    destination = BACKUP_DIR / f"gecko-auto-{date.today().isoformat()}.db"
    if not destination.exists():
        shutil.copy2(DB_PATH, destination)


def connexion():
    preparer_fichier_base()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialiser_base():
    preparer_fichier_base()
    sauvegarder_base_quotidienne()
    with connexion() as conn:
        if SCHEMA_PATH.exists():
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Les migrations gardent les anciennes bases compatibles quand
        # l'application gagne de nouvelles fonctionnalites.
        appliquer_migrations(conn)
        conn.commit()


def appliquer_migrations(conn):
    colonnes_gecko = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(gecko)").fetchall()
    }
    colonnes_gecko_attendues = {
        "numero_marquage": "TEXT",
        "procedure_marquage": "TEXT",
        "date_adoption": "TEXT",
        "ordre": "TEXT",
        "sexe": "TEXT",
        "nom_vernaculaire": "TEXT",
        "nom_scientifique": "TEXT",
        "classe": "TEXT",
        "origine": "TEXT",
        "pays_origine": "TEXT",
        "taille": "TEXT",
        "taille_valeur": "REAL",
        "taille_unite": "TEXT DEFAULT 'cm'",
        "poids": "TEXT",
        "poids_unite": "TEXT DEFAULT 'g'",
    }
    for colonne, type_sql in colonnes_gecko_attendues.items():
        if colonne not in colonnes_gecko:
            conn.execute(f"ALTER TABLE gecko ADD COLUMN {colonne} {type_sql}")

    conn.execute(
        """
        INSERT INTO gecko (
            nom, espece, date_naissance_estimee, numero_marquage, procedure_marquage,
            date_adoption, ordre, sexe, nom_vernaculaire, nom_scientifique,
            classe, origine, pays_origine, notes
        )
        SELECT
            'Xena', 'correlophus ciliatus', '2023-10-15', 'PH202312141431285',
            'photographie', '2023-12-12', 'Squamata', 'Femelle',
            'Gecko geant a crete', 'correlophus ciliatus', 'Reptilia',
            'ne en captivite', 'Republique Tcheque',
            'Xena fete ses 2 ans et 6 mois le 15/05/2026.'
        WHERE NOT EXISTS (SELECT 1 FROM gecko WHERE nom = 'Xena')
        """
    )
    conn.execute(
        """
        UPDATE gecko
        SET espece = 'correlophus ciliatus',
            date_naissance_estimee = '2023-10-15',
            numero_marquage = 'PH202312141431285',
            procedure_marquage = 'photographie',
            date_adoption = '2023-12-12',
            ordre = 'Squamata',
            sexe = 'Femelle',
            nom_vernaculaire = 'Gecko geant a crete',
            nom_scientifique = 'correlophus ciliatus',
            classe = 'Reptilia',
            origine = 'ne en captivite',
            pays_origine = 'Republique Tcheque'
        WHERE nom = 'Xena'
        """
    )
    colonnes_releves = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(releves)").fetchall()
    }
    if "animal_id" not in colonnes_releves:
        conn.execute("ALTER TABLE releves ADD COLUMN animal_id INTEGER")
    conn.execute(
        """
        UPDATE releves
        SET animal_id = (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1)
        WHERE animal_id IS NULL
        """
    )
    if "heure_releve" not in colonnes_releves:
        conn.execute("ALTER TABLE releves ADD COLUMN heure_releve TEXT")
        conn.execute(
            """
            UPDATE releves
            SET heure_releve = CASE moment
                WHEN 'matin' THEN '08:00'
                ELSE '20:00'
            END
            WHERE heure_releve IS NULL
            """
        )

    colonnes_repas = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(repas)").fetchall()
    }
    if "animal_id" not in colonnes_repas:
        conn.execute("ALTER TABLE repas ADD COLUMN animal_id INTEGER")
    conn.execute(
        """
        UPDATE repas
        SET animal_id = (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1)
        WHERE animal_id IS NULL
        """
    )
    if "heure_repas" not in colonnes_repas:
        conn.execute("ALTER TABLE repas ADD COLUMN heure_repas TEXT")
        conn.execute("UPDATE repas SET heure_repas = '20:00' WHERE heure_repas IS NULL")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS poids_mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            date_mesure TEXT NOT NULL,
            poids REAL NOT NULL,
            unite TEXT NOT NULL DEFAULT 'g' CHECK (unite IN ('g', 'kg')),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (animal_id) REFERENCES gecko(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS taille_mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            date_mesure TEXT NOT NULL,
            taille REAL NOT NULL,
            unite TEXT NOT NULL DEFAULT 'cm' CHECK (unite IN ('cm', 'mm', 'm')),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (animal_id) REFERENCES gecko(id)
        )
        """
    )
    conn.execute(
        """
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
        )
        """
    )
    conn.execute(
        """
        INSERT INTO taille_mesures (animal_id, date_mesure, taille, unite, notes)
        SELECT id, DATE('now'), taille_valeur, COALESCE(NULLIF(taille_unite, ''), 'cm'), 'Importe depuis la fiche animal.'
        FROM gecko
        WHERE taille_valeur IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM taille_mesures
            WHERE taille_mesures.animal_id = gecko.id
        )
        """
    )
    conn.execute(
        """
        INSERT INTO poids_mesures (animal_id, date_mesure, poids, unite, notes)
        SELECT id, DATE('now'), CAST(REPLACE(poids, ',', '.') AS REAL), COALESCE(NULLIF(poids_unite, ''), 'g'), 'Importe depuis la fiche animal.'
        FROM gecko
        WHERE poids IS NOT NULL
        AND TRIM(poids) != ''
        AND NOT EXISTS (
            SELECT 1 FROM poids_mesures
            WHERE poids_mesures.animal_id = gecko.id
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS aliments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            categorie TEXT NOT NULL,
            notes TEXT,
            masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    colonnes_aliments = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(aliments)").fetchall()
    }
    if "masque" not in colonnes_aliments:
        conn.execute(
            "ALTER TABLE aliments ADD COLUMN masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1))"
        )
    aliments_base = [
        ("grillons", "insectes"),
        ("red runner", "insectes"),
        ("vers de farine", "insectes"),
        ("Repashy", "patee"),
        ("compote humaine sans sucre ajoute", "fruit"),
        ("fruits", "fruit"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO aliments (nom, categorie)
        VALUES (?, ?)
        """,
        aliments_base,
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO aliments (nom, categorie, notes)
        SELECT DISTINCT aliment, categorie, 'Importe depuis les repas existants.'
        FROM repas
        WHERE TRIM(aliment) != ''
        AND LOWER(TRIM(aliment)) != 'insectes'
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS types_materiel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            notes TEXT,
            masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    colonnes_types_materiel = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(types_materiel)").fetchall()
    }
    if "masque" not in colonnes_types_materiel:
        conn.execute(
            "ALTER TABLE types_materiel ADD COLUMN masque INTEGER NOT NULL DEFAULT 0 CHECK (masque IN (0, 1))"
        )
    types_materiel_base = [
        ("terrarium",),
        ("lampe LED",),
        ("lampe chauffante",),
        ("thermometre",),
        ("hygrometre",),
        ("supplement",),
        ("autre",),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO types_materiel (nom) VALUES (?)",
        types_materiel_base,
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO types_materiel (nom, notes)
        SELECT DISTINCT type, 'Importe depuis le materiel existant.'
        FROM materiel
        WHERE TRIM(type) != ''
        """
    )

    colonnes_insectes = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(insectes_actions)").fetchall()
    }
    if "boite" not in colonnes_insectes:
        conn.execute(
            "ALTER TABLE insectes_actions ADD COLUMN boite TEXT NOT NULL DEFAULT 'Boite principale'"
        )
    if "heure_action" not in colonnes_insectes:
        conn.execute("ALTER TABLE insectes_actions ADD COLUMN heure_action TEXT")
        conn.execute(
            "UPDATE insectes_actions SET heure_action = '18:00' WHERE heure_action IS NULL"
        )

    colonnes_boites = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(insectes_boites)").fetchall()
    }
    if "statut" not in colonnes_boites:
        conn.execute(
            "ALTER TABLE insectes_boites ADD COLUMN statut TEXT NOT NULL DEFAULT 'active' CHECK (statut IN ('active', 'vide'))"
        )
    if "date_vide" not in colonnes_boites:
        conn.execute("ALTER TABLE insectes_boites ADD COLUMN date_vide TEXT")
    conn.execute(
        """
        UPDATE insectes_boites
        SET statut = CASE WHEN nombre_individus <= 0 THEN 'vide' ELSE 'active' END,
            date_vide = CASE
                WHEN nombre_individus <= 0 AND date_vide IS NULL THEN DATE('now')
                WHEN nombre_individus > 0 THEN NULL
                ELSE date_vide
            END
        """
    )

    nb_boites = conn.execute("SELECT COUNT(*) FROM insectes_boites").fetchone()[0]
    if nb_boites == 0:
        conn.execute(
            """
            INSERT OR IGNORE INTO insectes_boites (nom, type_insecte, nombre_individus, notes)
            SELECT DISTINCT boite, type_insecte, 0, 'Importe depuis les anciennes actions.'
            FROM insectes_actions
            WHERE boite IS NOT NULL AND TRIM(boite) != ''
            """
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS insectes_comptages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boite_id INTEGER NOT NULL,
            date_comptage TEXT NOT NULL,
            nombre_individus INTEGER NOT NULL CHECK (nombre_individus >= 0),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (boite_id) REFERENCES insectes_boites(id)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO insectes_comptages (boite_id, date_comptage, nombre_individus, notes)
        SELECT id, DATE('now'), nombre_individus, 'Comptage initial importe depuis la boite.'
        FROM insectes_boites
        WHERE NOT EXISTS (
            SELECT 1 FROM insectes_comptages
            WHERE insectes_comptages.boite_id = insectes_boites.id
        )
        """
    )

    colonnes_materiel = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(materiel)").fetchall()
    }
    if "animal_id" not in colonnes_materiel:
        conn.execute("ALTER TABLE materiel ADD COLUMN animal_id INTEGER")
    conn.execute(
        """
        UPDATE materiel
        SET animal_id = (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1)
        WHERE animal_id IS NULL
        """
    )
    if "statut" not in colonnes_materiel:
        conn.execute("ALTER TABLE materiel ADD COLUMN statut TEXT NOT NULL DEFAULT 'ok'")
    colonnes_materiel_consommable = {
        "est_consommable": "INTEGER NOT NULL DEFAULT 0 CHECK (est_consommable IN (0, 1))",
        "quantite_initiale": "REAL",
        "quantite_restante": "REAL",
        "unite_quantite": "TEXT DEFAULT 'g'",
        "statut_contenant": "TEXT NOT NULL DEFAULT 'non_applicable' CHECK (statut_contenant IN ('non_applicable', 'rempli', 'moitie', 'vide'))",
    }
    for colonne, type_sql in colonnes_materiel_consommable.items():
        if colonne not in colonnes_materiel:
            conn.execute(f"ALTER TABLE materiel ADD COLUMN {colonne} {type_sql}")
    conn.execute(
        """
        UPDATE materiel
        SET statut = CASE statut
            WHEN 'ok' THEN 'bien_ok'
            WHEN 'a_verifier' THEN 'maintenance'
            WHEN 'casse' THEN 'obsolete_casse'
            WHEN 'obsolete' THEN 'obsolete_casse'
            ELSE statut
        END
        """
    )
    conn.execute(
        """
        UPDATE materiel
        SET statut_contenant = CASE
            WHEN est_consommable = 0 THEN 'non_applicable'
            WHEN COALESCE(quantite_restante, 0) <= 0 THEN 'vide'
            WHEN quantite_initiale IS NOT NULL AND quantite_initiale > 0
                 AND quantite_restante <= quantite_initiale / 2 THEN 'moitie'
            ELSE 'rempli'
        END
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS materiel_mesures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materiel_id INTEGER NOT NULL,
            date_mesure TEXT NOT NULL,
            quantite_restante REAL NOT NULL CHECK (quantite_restante >= 0),
            unite TEXT NOT NULL DEFAULT 'g',
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (materiel_id) REFERENCES materiel(id)
        )
        """
    )
    supplements_base = [
        ("Poudre de calcium sans D3", "supplement", "Pot de calcium sans D3.", 0, "bien_ok", 1, 100, 100, "g", "rempli", "Pot de 100 g."),
        ("Poudre de calcium avec D3", "supplement", "Pot de calcium avec vitamine D3.", 0, "bien_ok", 1, 85, 85, "g", "rempli", "Pot de 85 g."),
    ]
    conn.executemany(
        """
        INSERT INTO materiel (
            animal_id, nom, type, description, actif, statut,
            est_consommable, quantite_initiale, quantite_restante,
            unite_quantite, statut_contenant, notes
        )
        SELECT (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1),
               ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM materiel
            WHERE nom = ?
            AND type = 'supplement'
        )
        """,
        [(*supplement, supplement[0]) for supplement in supplements_base],
    )
    conn.execute(
        """
        INSERT INTO materiel_mesures (materiel_id, date_mesure, quantite_restante, unite, notes)
        SELECT id, DATE('now'), quantite_restante, COALESCE(NULLIF(unite_quantite, ''), 'g'),
               'Mesure initiale du contenant.'
        FROM materiel
        WHERE est_consommable = 1
        AND quantite_restante IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM materiel_mesures
            WHERE materiel_mesures.materiel_id = materiel.id
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reglages (
            cle TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO reglages (cle, valeur)
        VALUES
            ('heure_allumage', '08:00'),
            ('heure_extinction', '20:00'),
            ('alertes_info_preventives', '0'),
            ('discord_mode', 'webhook'),
            ('discord_webhook_url', ''),
            ('discord_bot_token', ''),
            ('discord_channel_id', ''),
            ('discord_alertes_actives', '1'),
            ('discord_alertes_preventives', '1'),
            ('discord_auto_actif', '0'),
            ('discord_resume_quotidien', '1'),
            ('discord_resume_heure', '18:00'),
            ('discord_temps_reel', '1'),
            ('discord_niveaux', 'attention,danger,critique')
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_alertes_envoyees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signature TEXT NOT NULL UNIQUE,
            type_envoi TEXT NOT NULL,
            date_envoi TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS materiel_journalier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_utilisation TEXT NOT NULL,
            materiel_id INTEGER NOT NULL,
            utilise INTEGER NOT NULL DEFAULT 1 CHECK (utilise IN (0, 1)),
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date_utilisation, materiel_id),
            FOREIGN KEY (materiel_id) REFERENCES materiel(id)
        )
        """
    )
    colonnes_plantes = {
        colonne["name"]
        for colonne in conn.execute("PRAGMA table_info(plantes)").fetchall()
    }
    if "animal_id" not in colonnes_plantes:
        conn.execute("ALTER TABLE plantes ADD COLUMN animal_id INTEGER")
    conn.execute(
        """
        UPDATE plantes
        SET animal_id = (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1)
        WHERE animal_id IS NULL
        """
    )

    conn.execute(
        """
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
        )
        """
    )
    alertes_config_defaut = [
        ("temp_nuit_min", "Temperature matin trop basse", "temperature_matin", "danger", 1, 17, None, None, None, "C", 0, 6, "heures", "Alerte si un releve matin est sous le minimum."),
        ("temp_nuit_attention", "Temperature matin a surveiller", "temperature_matin", "attention", 1, 20, None, None, None, "C", 0, 6, "heures", "Alerte si un releve matin est sous l'ideal."),
        ("temp_jour_min_attention", "Temperature soir sous l'ideal", "temperature_soir", "attention", 1, 22, None, None, None, "C", 0, 6, "heures", "Alerte si un releve soir est sous l'ideal de l'animal."),
        ("temp_jour_max_attention", "Temperature soir au-dessus de l'ideal", "temperature_soir", "attention", 1, None, 24, None, None, "C", 0, 6, "heures", "Alerte si un releve soir depasse l'ideal de l'animal."),
        ("temp_jour_danger", "Temperature soir dangereuse", "temperature_soir", "danger", 1, None, 28, None, None, "C", 0, 6, "heures", "Alerte si un releve atteint le seuil haut."),
        ("temp_jour_critique", "Temperature soir critique", "temperature_soir", "critique", 1, None, 30, None, None, "C", 0, 6, "heures", "Alerte si un releve depasse le seuil critique."),
        ("humidite_min", "Humidite trop basse", "humidite", "attention", 1, 45, None, None, None, "%", 0, 6, "heures", ""),
        ("humidite_max", "Humidite trop haute", "humidite", "attention", 1, None, 90, None, None, "%", 0, 6, "heures", ""),
        ("poids_min", "Poids animal sous le seuil", "poids_animal", "attention", 0, 0, None, None, None, "g", 0, 6, "heures", "A activer par animal et a regler avec l'unite adaptee."),
        ("poids_max", "Poids animal au-dessus du seuil", "poids_animal", "attention", 0, None, 0, None, None, "g", 0, 6, "heures", "A activer par animal et a regler avec l'unite adaptee."),
        ("poids_repeser", "Animal a repeser", "poids_animal", "attention", 1, None, None, 28, "jours", "jours", 1, 3, "jours", "Alerte si aucune pesee recente n'a ete notee."),
        ("taille_min", "Taille animal sous le seuil", "taille_animal", "attention", 0, 0, None, None, None, "cm", 0, 6, "heures", "A activer par animal et a regler avec l'unite adaptee."),
        ("taille_max", "Taille animal au-dessus du seuil", "taille_animal", "attention", 0, None, 0, None, None, "cm", 0, 6, "heures", "A activer par animal et a regler avec l'unite adaptee."),
        ("acces_eau", "Acces a l'eau a verifier", "acces_eau", "danger", 1, None, None, 18, "heures", "h", 1, 6, "heures", "Brumisation ou eau changee."),
        ("repas_semaine_min", "Minimum de repas sur 7 jours", "repas_frequence", "attention", 1, 2, None, 7, "jours", "repas", 1, 2, "jours", ""),
        ("insectes_semaine_min", "Repas insectes hebdomadaire", "repas_insectes", "attention", 1, 1, None, 7, "jours", "repas", 1, 2, "jours", ""),
        ("vitamine_d3_delai", "Vitamine D3 mensuelle", "repas_vitamine_d3", "attention", 1, None, None, 30, "jours", "jours", 1, 5, "jours", ""),
        ("grillons_nourrissage", "Grillons a nourrir", "insectes_nourrissage", "attention", 1, None, None, 2, "jours", "jours", 1, 12, "heures", ""),
        ("grillons_brumisation", "Grillons a brumiser", "insectes_brumisation", "attention", 1, None, None, 2, "jours", "jours", 1, 12, "heures", ""),
        ("red_runner_brumisation", "Red runner a brumiser", "insectes_brumisation", "attention", 1, None, None, 7, "jours", "jours", 1, 1, "jours", ""),
        ("insectes_individus_min", "Nombre minimal d'insectes par boite", "insectes_individus", "attention", 0, 5, None, None, None, "individus", 0, 6, "heures", "Alerte si une boite active passe sous le seuil."),
        ("lumiere_duree", "Duree de lumiere hors plage", "lumiere", "info", 1, 10, 12, None, None, "h", 0, 6, "heures", "Planning heure_allumage / heure_extinction."),
    ]
    conn.executemany(
        """
        INSERT INTO alertes_config (
            cle, libelle, source, niveau, actif, seuil_min, seuil_max,
            delai_valeur, delai_unite, unite, phantome, preavis_valeur,
            preavis_unite, notes
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM alertes_config
            WHERE cle = ? AND animal_id IS NULL
        )
        """,
        [(*alerte_config, alerte_config[0]) for alerte_config in alertes_config_defaut],
    )
    sources_alertes = {alerte[0]: alerte[2] for alerte in alertes_config_defaut}
    conn.executemany(
        "UPDATE alertes_config SET source = ? WHERE cle = ?",
        [(source, cle) for cle, source in sources_alertes.items()],
    )
    conn.execute(
        """
        DELETE FROM alertes_config
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM alertes_config
            GROUP BY cle, COALESCE(animal_id, 0)
        )
        """
    )
    alertes_config_animaux = [
        ("Xena", "temp_jour_min_attention", "Temperature de jour sous l'ideal de Xena", "releves", "attention", 1, 22, None, None, None, "C", 0, 6, "heures", "Ideal Xena : 22 a 24 C."),
        ("Xena", "temp_jour_max_attention", "Temperature de jour au-dessus de l'ideal de Xena", "releves", "attention", 1, None, 24, None, None, "C", 0, 6, "heures", "Ideal Xena : 22 a 24 C."),
        ("Xena", "temp_jour_danger", "Temperature trop chaude pour Xena", "releves", "danger", 1, None, 28, None, None, "C", 0, 6, "heures", ""),
        ("Xena", "temp_jour_critique", "Temperature critique pour Xena", "releves", "critique", 1, None, 30, None, None, "C", 0, 6, "heures", ""),
    ]
    conn.executemany(
        """
        INSERT INTO alertes_config (
            animal_id, cle, libelle, source, niveau, actif, seuil_min,
            seuil_max, delai_valeur, delai_unite, unite, phantome,
            preavis_valeur, preavis_unite, notes
        )
        SELECT g.id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        FROM gecko g
        WHERE g.nom = ?
        AND NOT EXISTS (
            SELECT 1 FROM alertes_config ac
            WHERE ac.cle = ?
            AND ac.animal_id = g.id
        )
        """,
        [
            (
                cle,
                libelle,
                source,
                niveau,
                actif,
                seuil_min,
                seuil_max,
                delai_valeur,
                delai_unite,
                unite,
                phantome,
                preavis_valeur,
                preavis_unite,
                notes,
                animal_nom,
                cle,
            )
            for (
                animal_nom,
                cle,
                libelle,
                source,
                niveau,
                actif,
                seuil_min,
                seuil_max,
                delai_valeur,
                delai_unite,
                unite,
                phantome,
                preavis_valeur,
                preavis_unite,
                notes,
            ) in alertes_config_animaux
        ],
    )
    conn.execute(
        """
        INSERT INTO alertes_config (
            animal_id, cle, libelle, source, niveau, actif, seuil_min,
            seuil_max, delai_valeur, delai_unite, unite, phantome,
            preavis_valeur, preavis_unite, notes
        )
        SELECT g.id, 'poids_repeser', 'Animal a repeser', 'animal', 'attention',
               1, NULL, NULL, 28, 'jours', 'jours', 1, 3, 'jours',
               'Alerte si aucune pesee recente n''a ete notee.'
        FROM gecko g
        WHERE NOT EXISTS (
            SELECT 1 FROM alertes_config ac
            WHERE ac.cle = 'poids_repeser'
            AND ac.animal_id = g.id
        )
        """
    )
    conn.executemany(
        "UPDATE alertes_config SET source = ? WHERE cle = ?",
        [(source, cle) for cle, source in sources_alertes.items()],
    )
    conn.execute(
        """
        DELETE FROM alertes_config
        WHERE animal_id IS NULL
        AND source NOT LIKE 'insectes%'
        AND EXISTS (
            SELECT 1
            FROM alertes_config specifique
            JOIN gecko xena ON xena.id = specifique.animal_id
            WHERE specifique.cle = alertes_config.cle
            AND xena.nom = 'Xena'
        )
        """
    )
    conn.execute(
        """
        UPDATE alertes_config
        SET animal_id = (SELECT id FROM gecko WHERE nom = 'Xena' LIMIT 1)
        WHERE animal_id IS NULL
        AND source NOT LIKE 'insectes%'
        AND NOT EXISTS (
            SELECT 1
            FROM alertes_config specifique
            JOIN gecko xena ON xena.id = specifique.animal_id
            WHERE specifique.cle = alertes_config.cle
            AND xena.nom = 'Xena'
        )
        """
    )
