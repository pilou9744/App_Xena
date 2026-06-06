from database import connexion, initialiser_base


def existe(conn, table, conditions):
    clause = " AND ".join(f"{colonne} = ?" for colonne in conditions)
    valeurs = tuple(conditions.values())
    requete = f"SELECT 1 FROM {table} WHERE {clause} LIMIT 1"
    return conn.execute(requete, valeurs).fetchone() is not None


def ajouter_si_absent(conn, table, donnees, conditions):
    if existe(conn, table, conditions):
        return False

    colonnes = ", ".join(donnees.keys())
    marqueurs = ", ".join("?" for _ in donnees)
    requete = f"INSERT INTO {table} ({colonnes}) VALUES ({marqueurs})"
    conn.execute(requete, tuple(donnees.values()))
    return True


def ajouter_ou_mettre_a_jour_boite(conn, boite):
    existante = conn.execute(
        "SELECT 1 FROM insectes_boites WHERE nom = ?",
        (boite["nom"],),
    ).fetchone()
    if existante:
        conn.execute(
            """
            UPDATE insectes_boites
            SET type_insecte = ?,
                nombre_individus = ?,
                notes = ?
            WHERE nom = ?
            """,
            (
                boite["type_insecte"],
                boite["nombre_individus"],
                boite["notes"],
                boite["nom"],
            ),
        )
        return False

    conn.execute(
        """
        INSERT INTO insectes_boites (nom, type_insecte, nombre_individus, notes)
        VALUES (?, ?, ?, ?)
        """,
        (
            boite["nom"],
            boite["type_insecte"],
            boite["nombre_individus"],
            boite["notes"],
        ),
    )
    return True


def inserer_donnees_initiales():
    initialiser_base()

    ajouts = 0
    with connexion() as conn:
        ajouts += ajouter_si_absent(
            conn,
            "gecko",
            {
                "nom": "Xena",
                "espece": "Gecko a crete",
                "date_naissance_estimee": "2023-11-15",
                "notes": "Xena fete ses 2 ans et 6 mois le 15/05/2026.",
            },
            {"nom": "Xena"},
        )

        materiels = [
            {
                "nom": "Terrarium 45x45x60",
                "type": "terrarium",
                "description": "Terrarium principal actuel.",
                "date_debut": "2025-01-01",
                "date_fin": None,
                "actif": 1,
                "notes": "Taille actuelle indiquee pour suivre les tendances.",
            },
            {
                "nom": "Lampe LED plantes",
                "type": "lampe LED",
                "description": "Eclairage pour les plantes du terrarium.",
                "date_debut": "2025-01-01",
                "date_fin": None,
                "actif": 1,
                "notes": "Aide a maintenir les plantes naturelles.",
            },
            {
                "nom": "Lampe chauffante ete",
                "type": "lampe chauffante",
                "description": "Lampe qui chauffe beaucoup, a surveiller en ete.",
                "date_debut": "2025-06-01",
                "date_fin": None,
                "actif": 0,
                "notes": "Peut expliquer des temperatures hautes.",
            },
            {
                "nom": "Lampe chauffante hiver",
                "type": "lampe chauffante",
                "description": "Lampe plus douce pour la periode froide.",
                "date_debut": "2025-11-01",
                "date_fin": None,
                "actif": 1,
                "notes": "Utilisee quand les nuits sont fraiches.",
            },
        ]
        for materiel in materiels:
            ajouts += ajouter_si_absent(conn, "materiel", materiel, {"nom": materiel["nom"]})

        plantes = [
            {
                "nom": "Pothos",
                "espece": "Epipremnum aureum",
                "type_plante": "naturelle",
                "etat": "excellent",
                "date_ajout": "2025-02-10",
                "notes": "Bonne croissance.",
            },
            {
                "nom": "Fougere",
                "espece": "Nephrolepis",
                "type_plante": "naturelle",
                "etat": "moyen",
                "date_ajout": "2025-03-15",
                "notes": "A surveiller, quelques feuilles seches.",
            },
            {
                "nom": "Liane artificielle",
                "espece": "",
                "type_plante": "plastique",
                "etat": "excellent",
                "date_ajout": "2025-01-01",
                "notes": "Cachette et support de deplacement.",
            },
            {
                "nom": "Fittonia",
                "espece": "Fittonia albivenis",
                "type_plante": "naturelle",
                "etat": "mauvais",
                "date_ajout": "2025-04-20",
                "notes": "Feuilles fatiguees, visible sur le tableau de bord plus tard.",
            },
        ]
        for plante in plantes:
            ajouts += ajouter_si_absent(conn, "plantes", plante, {"nom": plante["nom"]})

        releves = [
            {
                "date_releve": "2026-05-10",
                "moment": "matin",
                "temperature": 20.8,
                "humidite": 58,
                "brumisation": 0,
                "eau_changee": 1,
                "notes": "Nuit stable.",
            },
            {
                "date_releve": "2026-05-10",
                "moment": "soir",
                "temperature": 24.1,
                "humidite": 72,
                "brumisation": 1,
                "eau_changee": 0,
                "notes": "Brumisation du soir.",
            },
            {
                "date_releve": "2026-05-11",
                "moment": "matin",
                "temperature": 19.7,
                "humidite": 52,
                "brumisation": 0,
                "eau_changee": 1,
                "notes": "Legerement frais.",
            },
            {
                "date_releve": "2026-05-11",
                "moment": "soir",
                "temperature": 25.4,
                "humidite": 68,
                "brumisation": 1,
                "eau_changee": 0,
                "notes": "Journee correcte.",
            },
            {
                "date_releve": "2026-05-12",
                "moment": "matin",
                "temperature": 20.2,
                "humidite": 55,
                "brumisation": 0,
                "eau_changee": 1,
                "notes": "Parametres confortables.",
            },
            {
                "date_releve": "2026-05-12",
                "moment": "soir",
                "temperature": 26.8,
                "humidite": 76,
                "brumisation": 1,
                "eau_changee": 0,
                "notes": "Un peu chaud, a surveiller.",
            },
        ]
        for releve in releves:
            ajouts += ajouter_si_absent(
                conn,
                "releves",
                releve,
                {"date_releve": releve["date_releve"], "moment": releve["moment"]},
            )

        repas = [
            {
                "date_repas": "2026-05-06",
                "aliment": "Repashy",
                "categorie": "patee",
                "quantite": "petite coupelle",
                "calcium_sans_d3": 0,
                "vitamine_d3": 0,
                "notes": "Bien accepte.",
            },
            {
                "date_repas": "2026-05-09",
                "aliment": "grillons",
                "categorie": "insectes",
                "quantite": "4 grillons",
                "calcium_sans_d3": 1,
                "vitamine_d3": 0,
                "notes": "Grillons saupoudres au calcium sans D3.",
            },
            {
                "date_repas": "2026-05-12",
                "aliment": "compote humaine sans sucre ajoute",
                "categorie": "fruit",
                "quantite": "quelques lechees",
                "calcium_sans_d3": 0,
                "vitamine_d3": 1,
                "notes": "Dose mensuelle de D3 notee.",
            },
        ]
        for repas_item in repas:
            ajouts += ajouter_si_absent(
                conn,
                "repas",
                repas_item,
                {"date_repas": repas_item["date_repas"], "aliment": repas_item["aliment"]},
            )

        boites = [
            {
                "nom": "Boite grillons 1",
                "type_insecte": "grillons",
                "nombre_individus": 12,
                "notes": "Boite principale de grillons.",
            },
            {
                "nom": "Boite red runner 1",
                "type_insecte": "red runner",
                "nombre_individus": 20,
                "notes": "Colonie de red runner.",
            },
            {
                "nom": "Boite vers 1",
                "type_insecte": "vers de farine",
                "nombre_individus": 25,
                "notes": "Boite de vers de farine.",
            },
        ]
        for boite in boites:
            ajouts += ajouter_ou_mettre_a_jour_boite(conn, boite)

        insectes_actions = [
            {
                "date_action": "2026-05-10",
                "type_insecte": "grillons",
                "boite": "Boite grillons 1",
                "nourrissage": 1,
                "nourriture_donnee": "carotte et flocons d'avoine",
                "brumisation": 1,
                "notes": "Colonie active.",
            },
            {
                "date_action": "2026-05-11",
                "type_insecte": "red runner",
                "boite": "Boite red runner 1",
                "nourrissage": 1,
                "nourriture_donnee": "legumes et avoine",
                "brumisation": 1,
                "notes": "Brumisation hebdomadaire faite.",
            },
            {
                "date_action": "2026-05-12",
                "type_insecte": "vers de farine",
                "boite": "Boite vers 1",
                "nourrissage": 1,
                "nourriture_donnee": "pomme de terre et flocons d'avoine",
                "brumisation": 0,
                "notes": "Pas de brumisation necessaire.",
            },
        ]
        for action in insectes_actions:
            ajouts += ajouter_si_absent(
                conn,
                "insectes_actions",
                action,
                {
                    "date_action": action["date_action"],
                    "type_insecte": action["type_insecte"],
                    "boite": action["boite"],
                },
            )

        conn.commit()

    return ajouts


if __name__ == "__main__":
    total = inserer_donnees_initiales()
    print(f"Base initialisee. {total} nouvelle(s) ligne(s) ajoutee(s).")
