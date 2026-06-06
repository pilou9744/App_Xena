import json
import sys
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from flask import Flask, abort, redirect, render_template, request, url_for

from database import BACKUP_DIR, DB_PATH, connexion, initialiser_base


RESSOURCES_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
app = Flask(
    __name__,
    template_folder=str(RESSOURCES_DIR / "templates"),
    static_folder=str(RESSOURCES_DIR / "static"),
)
SCHEDULER_DISCORD_DEMARRE = False


@app.context_processor
def filtres_templates():
    return {
        "libelle_statut_materiel": libelle_statut_materiel,
        "libelle_statut_contenant": libelle_statut_contenant,
        "format_nombre": format_nombre,
    }


@app.before_request
def preparer_application():
    # L'application est locale et doit rester autonome : chaque requete verifie
    # que la base existe et que les migrations recentes ont ete appliquees.
    initialiser_base()
    demarrer_scheduler_discord()


@app.route("/")
def accueil():
    return render_template("index.html", titre="GeckoCare Xena")


@app.route("/dashboard")
def tableau_de_bord():
    date_selectionnee = request.args.get("date") or date.today().isoformat()
    animal_id = entier_ou_none(request.args.get("animal_id"))
    donnees = charger_tableau_de_bord(date_selectionnee, animal_id)
    return render_template("dashboard.html", titre="Tableau de bord", **donnees)


@app.route("/poids", methods=["POST"])
def ajouter_poids():
    animal_id = entier_ou_none(request.form.get("animal_id"))
    date_selectionnee = request.form.get("date_selectionnee") or date.today().isoformat()
    try:
        enregistrer_mesure_poids(request.form)
    except ValueError:
        pass
    return redirect(url_for("tableau_de_bord", animal_id=animal_id, date=date_selectionnee))


@app.route("/tailles", methods=["POST"])
def ajouter_taille():
    animal_id = entier_ou_none(request.form.get("animal_id"))
    date_selectionnee = request.form.get("date_selectionnee") or date.today().isoformat()
    try:
        enregistrer_mesure_taille(request.form)
    except ValueError:
        pass
    return redirect(url_for("tableau_de_bord", animal_id=animal_id, date=date_selectionnee))


@app.route("/animaux", methods=["GET", "POST"])
def animaux():
    if request.method == "POST":
        ajouter_animal(request.form)
        return redirect(url_for("animaux"))

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)

    return render_template(
        "animaux.html",
        titre="Animaux",
        animaux=animaux_liste,
        aujourd_hui=date.today().isoformat(),
    )


@app.route("/animaux/<int:animal_id>/modifier", methods=["GET", "POST"])
def modifier_animal(animal_id):
    if request.method == "POST":
        mettre_a_jour_animal(animal_id, request.form)
        return redirect(url_for("animaux"))

    animal = trouver_ligne("gecko", animal_id)
    with connexion() as conn:
        peut_supprimer = conn.execute(
            "SELECT 1 FROM gecko WHERE id != ? LIMIT 1",
            (animal_id,),
        ).fetchone() is not None
    return render_template(
        "modifier_animal.html",
        titre="Modifier un animal",
        animal=animal,
        peut_supprimer=peut_supprimer,
    )


@app.route("/animaux/<int:animal_id>/supprimer", methods=["POST"])
def supprimer_animal(animal_id):
    with connexion() as conn:
        animal = conn.execute("SELECT id FROM gecko WHERE id = ?", (animal_id,)).fetchone()
        autre_animal = conn.execute(
            "SELECT id FROM gecko WHERE id != ? LIMIT 1",
            (animal_id,),
        ).fetchone()
        if animal is None or autre_animal is None:
            return redirect(url_for("animaux"))

        conn.execute("DELETE FROM alertes_config WHERE animal_id = ?", (animal_id,))
        conn.execute(
            """
            DELETE FROM materiel_journalier
            WHERE materiel_id IN (
                SELECT id FROM materiel WHERE animal_id = ?
            )
            """,
            (animal_id,),
        )
        conn.execute("DELETE FROM materiel WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM plantes WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM poids_mesures WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM taille_mesures WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM releves WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM repas WHERE animal_id = ?", (animal_id,))
        conn.execute("DELETE FROM gecko WHERE id = ?", (animal_id,))
        conn.commit()

    return redirect(url_for("animaux"))


@app.route("/reglages", methods=["GET"])
def reglages():
    with connexion() as conn:
        alertes_config = lister_alertes_config(conn)
        sources = sources_alertes()
        return render_template(
            "reglages.html",
            titre="Reglages",
            reglages=charger_reglages(conn),
            alertes_config=alertes_config,
            alertes_config_groupes=groupes_alertes_config(alertes_config),
            animaux=lister_animaux(conn),
            sources_alertes=sources,
            sources_alertes_valeurs={source[0] for source in sources},
            chemin_base=DB_PATH,
            chemin_sauvegardes=BACKUP_DIR,
            discord_message=request.args.get("discord_message"),
        )


@app.route("/reglages/discord", methods=["POST"])
def modifier_reglages_discord():
    with connexion() as conn:
        enregistrer_reglage(conn, "discord_mode", mode_discord_valide(request.form.get("discord_mode")))
        enregistrer_reglage(conn, "discord_webhook_url", request.form.get("discord_webhook_url", "").strip())
        enregistrer_reglage(conn, "discord_bot_token", request.form.get("discord_bot_token", "").strip())
        enregistrer_reglage(conn, "discord_channel_id", request.form.get("discord_channel_id", "").strip())
        enregistrer_reglage(conn, "discord_alertes_actives", "1" if request.form.get("discord_alertes_actives") == "on" else "0")
        enregistrer_reglage(conn, "discord_alertes_preventives", "1" if request.form.get("discord_alertes_preventives") == "on" else "0")
        enregistrer_reglage(conn, "discord_auto_actif", "1" if request.form.get("discord_auto_actif") == "on" else "0")
        enregistrer_reglage(conn, "discord_resume_quotidien", "1" if request.form.get("discord_resume_quotidien") == "on" else "0")
        enregistrer_reglage(conn, "discord_resume_heure", heure_valide(request.form.get("discord_resume_heure"), "18:00"))
        enregistrer_reglage(conn, "discord_temps_reel", "1" if request.form.get("discord_temps_reel") == "on" else "0")
        enregistrer_reglage(conn, "discord_niveaux", niveaux_discord_depuis_formulaire(request.form))
        conn.commit()
    return redirect(url_for("reglages", discord_message="Reglages Discord enregistres."))


@app.route("/discord/alertes/envoyer", methods=["POST"])
def envoyer_alertes_discord():
    with connexion() as conn:
        if request.form.get("discord_webhook_url") is not None:
            enregistrer_reglage(conn, "discord_mode", mode_discord_valide(request.form.get("discord_mode")))
            enregistrer_reglage(conn, "discord_webhook_url", request.form.get("discord_webhook_url", "").strip())
            enregistrer_reglage(conn, "discord_bot_token", request.form.get("discord_bot_token", "").strip())
            enregistrer_reglage(conn, "discord_channel_id", request.form.get("discord_channel_id", "").strip())
            enregistrer_reglage(conn, "discord_alertes_actives", "1" if request.form.get("discord_alertes_actives") == "on" else "0")
            enregistrer_reglage(conn, "discord_alertes_preventives", "1" if request.form.get("discord_alertes_preventives") == "on" else "0")
            enregistrer_reglage(conn, "discord_auto_actif", "1" if request.form.get("discord_auto_actif") == "on" else "0")
            enregistrer_reglage(conn, "discord_resume_quotidien", "1" if request.form.get("discord_resume_quotidien") == "on" else "0")
            enregistrer_reglage(conn, "discord_resume_heure", heure_valide(request.form.get("discord_resume_heure"), "18:00"))
            enregistrer_reglage(conn, "discord_temps_reel", "1" if request.form.get("discord_temps_reel") == "on" else "0")
            enregistrer_reglage(conn, "discord_niveaux", niveaux_discord_depuis_formulaire(request.form))
            conn.commit()
        reglages_app = charger_reglages(conn)
        try:
            envoyer_resume_alertes_discord(conn, reglages_app)
            message = "Alertes envoyees sur Discord."
        except ValueError as erreur:
            message = str(erreur)
        except HTTPError as erreur:
            message = message_erreur_discord_http(erreur)
        except URLError as erreur:
            message = f"Impossible de joindre Discord : {erreur.reason}."
        except OSError as erreur:
            message = f"Impossible de joindre Discord : {erreur}."
    return redirect(url_for("reglages", discord_message=message))


@app.route("/alertes-config", methods=["POST"])
def ajouter_alerte_config():
    with connexion() as conn:
        enregistrer_alerte_config(conn, request.form)
        conn.commit()
    return redirect(url_for("reglages"))


@app.route("/alertes-config/<int:config_id>", methods=["POST"])
def modifier_alerte_config(config_id):
    with connexion() as conn:
        enregistrer_alerte_config(conn, request.form, config_id)
        conn.commit()
    return redirect(url_for("reglages"))


@app.route("/alertes-config/<int:config_id>/supprimer", methods=["POST"])
def supprimer_alerte_config(config_id):
    with connexion() as conn:
        conn.execute("DELETE FROM alertes_config WHERE id = ?", (config_id,))
        conn.commit()
    return redirect(url_for("reglages"))


@app.route("/alertes-config/options", methods=["POST"])
def modifier_options_alertes():
    valeur = "1" if request.form.get("alertes_info_preventives") == "on" else "0"
    with connexion() as conn:
        enregistrer_reglage(conn, "alertes_info_preventives", valeur)
        conn.commit()
    return redirect(url_for("reglages"))


@app.route("/releves", methods=["GET", "POST"])
def releves():
    erreur = None
    animal_id = entier_ou_none(request.args.get("animal_id"))

    if request.method == "POST":
        try:
            ajouter_releve(request.form)
            return redirect(url_for("releves", animal_id=request.form.get("animal_id")))
        except ValueError:
            erreur = "La temperature et l'humidite doivent etre des nombres valides."

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        derniers_releves = conn.execute(
            """
            SELECT * FROM releves
            WHERE animal_id = ?
            ORDER BY date_releve DESC, created_at DESC
            LIMIT 30
            """,
            (animal_id,),
        ).fetchall()

    return render_template(
        "releves.html",
        titre="Releves",
        aujourd_hui=date.today().isoformat(),
        animal_id=animal_id,
        animaux=animaux_liste,
        derniers_releves=derniers_releves,
        erreur=erreur,
    )


@app.route("/repas", methods=["GET", "POST"])
def repas():
    animal_id = entier_ou_none(request.args.get("animal_id"))
    if request.method == "POST":
        if request.form.get("formulaire") == "aliment":
            ajouter_aliment(request.form)
        else:
            ajouter_repas(request.form)
        return redirect(url_for("repas", animal_id=request.form.get("animal_id")))

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        aliments = lister_aliments(conn)
        derniers_repas = conn.execute(
            """
            SELECT * FROM repas
            WHERE animal_id = ?
            ORDER BY date_repas DESC, heure_repas DESC, created_at DESC
            LIMIT 30
            """,
            (animal_id,),
        ).fetchall()

    return render_template(
        "repas.html",
        titre="Repas",
        aujourd_hui=date.today().isoformat(),
        animal_id=animal_id,
        animaux=animaux_liste,
        aliments=aliments,
        derniers_repas=derniers_repas,
    )


@app.route("/observations", methods=["GET", "POST"])
def observations():
    animal_id = entier_ou_none(request.args.get("animal_id"))
    if request.method == "POST":
        ajouter_observation(request.form)
        return redirect(url_for("observations", animal_id=request.form.get("animal_id")))

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        observations_liste = conn.execute(
            """
            SELECT * FROM observations
            WHERE animal_id = ?
            ORDER BY date_observation DESC, heure_observation DESC, created_at DESC
            LIMIT 60
            """,
            (animal_id,),
        ).fetchall()

    return render_template(
        "observations.html",
        titre="Observations",
        aujourd_hui=date.today().isoformat(),
        animal_id=animal_id,
        animaux=animaux_liste,
        observations=observations_liste,
        categories_observation=categories_observation(),
        niveaux_observation=niveaux_observation(),
    )


@app.route("/insectes", methods=["GET", "POST"])
def insectes():
    if request.method == "POST":
        ajouter_action_insectes(request.form)
        return redirect(url_for("insectes"))

    with connexion() as conn:
        boites_insectes = lister_boites_insectes(conn)
        actions_insectes = conn.execute(
            """
            SELECT * FROM insectes_actions
            ORDER BY date_action DESC, created_at DESC
            LIMIT 30
            """
        ).fetchall()

    return render_template(
        "insectes.html",
        titre="Insectes",
        aujourd_hui=date.today().isoformat(),
        boites_insectes=boites_insectes,
        actions_insectes=actions_insectes,
    )


@app.route("/boites-insectes", methods=["GET", "POST"])
def boites_insectes():
    erreur = None

    if request.method == "POST":
        try:
            ajouter_boite_insectes(request.form)
            return redirect(url_for("boites_insectes"))
        except ValueError:
            erreur = "Le nombre d'individus doit etre un nombre entier positif."

    with connexion() as conn:
        boites = lister_boites_insectes(conn)
        boites_vides = lister_boites_insectes(conn, inclure_vides=True, seulement_vides=True)
        comptages_recents = conn.execute(
            """
            SELECT c.*, b.nom AS boite, b.type_insecte
            FROM insectes_comptages c
            JOIN insectes_boites b ON b.id = c.boite_id
            ORDER BY c.date_comptage DESC, c.created_at DESC
            LIMIT 30
            """
        ).fetchall()

    return render_template(
        "boites_insectes.html",
        titre="Boites d'insectes",
        boites=boites,
        boites_vides=boites_vides,
        comptages_recents=comptages_recents,
        aujourd_hui=date.today().isoformat(),
        erreur=erreur,
    )


@app.route("/boites-insectes/<int:boite_id>/comptages", methods=["POST"])
def ajouter_comptage_insectes(boite_id):
    try:
        enregistrer_comptage_insectes(boite_id, request.form)
    except ValueError:
        pass
    return redirect(url_for("boites_insectes"))


@app.route("/boites-insectes/<int:boite_id>/modifier", methods=["GET", "POST"])
def modifier_boite_insectes(boite_id):
    erreur = None

    if request.method == "POST":
        try:
            mettre_a_jour_boite_insectes(boite_id, request.form)
            return redirect(url_for("boites_insectes"))
        except ValueError:
            erreur = "Le nombre d'individus doit etre un nombre entier positif."

    boite = trouver_ligne("insectes_boites", boite_id)
    return render_template(
        "modifier_boite_insectes.html",
        titre="Modifier une boite",
        boite=boite,
        erreur=erreur,
    )


@app.route("/boites-insectes/<int:boite_id>/supprimer", methods=["POST"])
def supprimer_boite_insectes(boite_id):
    supprimer_ligne("insectes_boites", boite_id)
    return redirect(url_for("boites_insectes"))


@app.route("/materiel", methods=["GET", "POST"])
def materiel():
    date_selectionnee = request.args.get("date") or date.today().isoformat()
    animal_id = entier_ou_none(request.args.get("animal_id"))

    if request.method == "POST":
        if request.form.get("formulaire") == "journal":
            enregistrer_materiel_journalier(request.form)
        elif request.form.get("formulaire") == "type_materiel":
            ajouter_type_materiel(request.form)
        else:
            ajouter_materiel(request.form)
        return redirect(url_for("materiel", animal_id=request.form.get("animal_id")))

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        types_materiel = lister_types_materiel(conn)
        materiels = conn.execute(
            """
            SELECT * FROM materiel
            WHERE animal_id = ?
            ORDER BY actif DESC, statut, type, nom
            """,
            (animal_id,),
        ).fetchall()
        materiel_du_jour = ids_materiel_utilises(conn, date_selectionnee, animal_id)

    return render_template(
        "materiel.html",
        titre="Materiel",
        aujourd_hui=date.today().isoformat(),
        date_selectionnee=date_selectionnee,
        animal_id=animal_id,
        animaux=animaux_liste,
        types_materiel=types_materiel,
        statuts_materiel=statuts_materiel(),
        materiels=materiels,
        materiel_du_jour=materiel_du_jour,
    )


@app.route("/materiel/<int:materiel_id>/modifier", methods=["GET", "POST"])
def modifier_materiel(materiel_id):
    if request.method == "POST":
        mettre_a_jour_materiel(materiel_id, request.form)
        return redirect(url_for("materiel", animal_id=request.form.get("animal_id")))

    materiel_ligne = trouver_ligne("materiel", materiel_id)
    with connexion() as conn:
        types_materiel = lister_types_materiel(conn)
        animaux_liste = lister_animaux(conn)
    return render_template(
        "modifier_materiel.html",
        titre="Modifier un materiel",
        materiel=materiel_ligne,
        animaux=animaux_liste,
        types_materiel=types_materiel,
        statuts_materiel=statuts_materiel(),
    )


@app.route("/materiel/<int:materiel_id>/actif", methods=["POST"])
def basculer_materiel_actif(materiel_id):
    with connexion() as conn:
        ligne = conn.execute(
            "SELECT actif, statut, est_consommable FROM materiel WHERE id = ?",
            (materiel_id,),
        ).fetchone()
        if ligne is None:
            abort(404)
        if ligne["est_consommable"] or (not ligne["actif"] and materiel_est_inutilisable(ligne["statut"])):
            return redirect(url_for("materiel"))

        conn.execute(
            "UPDATE materiel SET actif = ? WHERE id = ?",
            (0 if ligne["actif"] else 1, materiel_id),
        )
        conn.commit()

    return redirect(url_for("materiel"))


@app.route("/materiel/<int:materiel_id>/mesures", methods=["POST"])
def ajouter_mesure_materiel(materiel_id):
    try:
        enregistrer_mesure_materiel(materiel_id, request.form)
    except ValueError:
        pass
    return redirect(url_for("materiel", animal_id=request.form.get("animal_id")))


@app.route("/materiel/<int:materiel_id>/supprimer", methods=["POST"])
def supprimer_materiel(materiel_id):
    supprimer_ligne("materiel", materiel_id)
    return redirect(url_for("materiel"))


@app.route("/types-materiel/<int:type_id>/supprimer", methods=["POST"])
def supprimer_type_materiel(type_id):
    masquer_ligne("types_materiel", type_id)
    return redirect(url_for("materiel"))


@app.route("/plantes", methods=["GET", "POST"])
def plantes():
    animal_id = entier_ou_none(request.args.get("animal_id"))
    if request.method == "POST":
        ajouter_plante(request.form)
        return redirect(url_for("plantes", animal_id=request.form.get("animal_id")))

    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        plantes_liste = conn.execute(
            """
            SELECT * FROM plantes
            WHERE animal_id = ?
            ORDER BY
                CASE etat
                    WHEN 'mauvais' THEN 0
                    WHEN 'decede' THEN 1
                    WHEN 'moyen' THEN 2
                    ELSE 3
                END,
                nom
            """,
            (animal_id,),
        ).fetchall()

    return render_template(
        "plantes.html",
        titre="Plantes",
        aujourd_hui=date.today().isoformat(),
        animal_id=animal_id,
        animaux=animaux_liste,
        plantes=plantes_liste,
    )


@app.route("/plantes/<int:plante_id>/modifier", methods=["GET", "POST"])
def modifier_plante(plante_id):
    if request.method == "POST":
        mettre_a_jour_plante(plante_id, request.form)
        return redirect(url_for("plantes", animal_id=request.form.get("animal_id")))

    plante = trouver_ligne("plantes", plante_id)
    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
    return render_template("modifier_plante.html", titre="Modifier une plante", plante=plante, animaux=animaux_liste)


@app.route("/plantes/<int:plante_id>/supprimer", methods=["POST"])
def supprimer_plante(plante_id):
    supprimer_ligne("plantes", plante_id)
    return redirect(url_for("plantes"))


@app.route("/observations/<int:observation_id>/supprimer", methods=["POST"])
def supprimer_observation(observation_id):
    supprimer_ligne("observations", observation_id)
    return redirect(url_for("observations"))


@app.route("/insectes/actions/<int:action_id>/modifier", methods=["GET", "POST"])
def modifier_action_insectes(action_id):
    if request.method == "POST":
        mettre_a_jour_action_insectes(action_id, request.form)
        return redirect(url_for("insectes"))

    action = trouver_ligne("insectes_actions", action_id)
    with connexion() as conn:
        boites_insectes = lister_boites_insectes(conn)

    return render_template(
        "modifier_action_insectes.html",
        titre="Modifier une action insectes",
        action=action,
        boites_insectes=boites_insectes,
    )


@app.route("/insectes/actions/<int:action_id>/supprimer", methods=["POST"])
def supprimer_action_insectes(action_id):
    supprimer_ligne("insectes_actions", action_id)
    return redirect(url_for("insectes"))


@app.route("/releves/<int:releve_id>/modifier", methods=["GET", "POST"])
def modifier_releve(releve_id):
    erreur = None

    if request.method == "POST":
        try:
            mettre_a_jour_releve(releve_id, request.form)
            return redirect(url_for("releves", animal_id=request.form.get("animal_id")))
        except ValueError:
            erreur = "La temperature et l'humidite doivent etre des nombres valides."

    releve = trouver_ligne("releves", releve_id)
    with connexion() as conn:
        animaux_liste = lister_animaux(conn)
    return render_template("modifier_releve.html", titre="Modifier un releve", releve=releve, animaux=animaux_liste, erreur=erreur)


@app.route("/releves/<int:releve_id>/supprimer", methods=["POST"])
def supprimer_releve(releve_id):
    supprimer_ligne("releves", releve_id)
    return redirect(url_for("releves"))


@app.route("/repas/<int:repas_id>/modifier", methods=["GET", "POST"])
def modifier_repas(repas_id):
    if request.method == "POST":
        mettre_a_jour_repas(repas_id, request.form)
        return redirect(url_for("repas", animal_id=request.form.get("animal_id")))

    repas_ligne = trouver_ligne("repas", repas_id)
    with connexion() as conn:
        aliments = lister_aliments(conn)
        animaux_liste = lister_animaux(conn)
    return render_template(
        "modifier_repas.html",
        titre="Modifier un repas",
        repas=repas_ligne,
        animaux=animaux_liste,
        aliments=aliments,
    )


@app.route("/repas/<int:repas_id>/supprimer", methods=["POST"])
def supprimer_repas(repas_id):
    supprimer_ligne("repas", repas_id)
    return redirect(url_for("repas"))


@app.route("/aliments/<int:aliment_id>/modifier", methods=["GET", "POST"])
def modifier_aliment(aliment_id):
    if request.method == "POST":
        mettre_a_jour_aliment(aliment_id, request.form)
        return redirect(url_for("repas"))

    aliment = trouver_ligne("aliments", aliment_id)
    return render_template(
        "modifier_aliment.html",
        titre="Modifier un aliment",
        aliment=aliment,
        categories=categories_aliments(),
    )


@app.route("/aliments/<int:aliment_id>/supprimer", methods=["POST"])
def supprimer_aliment(aliment_id):
    masquer_ligne("aliments", aliment_id)
    return redirect(url_for("repas"))


def ajouter_releve(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_releve = formulaire.get("date_releve") or date.today().isoformat()
    heure_releve = heure_valide(formulaire.get("heure_releve"), heure_actuelle())
    moment = periode_observee_valide(formulaire.get("moment"))

    temperature = float(formulaire.get("temperature", "").replace(",", "."))
    humidite = int(formulaire.get("humidite", ""))
    brumisation = 1 if formulaire.get("brumisation") == "on" else 0
    eau_changee = 1 if formulaire.get("eau_changee") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO releves (
                animal_id,
                date_releve,
                heure_releve,
                moment,
                temperature,
                humidite,
                brumisation,
                eau_changee,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                animal_id,
                date_releve,
                heure_releve,
                moment,
                temperature,
                humidite,
                brumisation,
                eau_changee,
                notes,
            ),
        )
        conn.commit()


def mettre_a_jour_releve(releve_id, formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_releve = formulaire.get("date_releve") or date.today().isoformat()
    heure_releve = heure_valide(formulaire.get("heure_releve"), heure_actuelle())
    moment = periode_observee_valide(formulaire.get("moment"))

    temperature = float(formulaire.get("temperature", "").replace(",", "."))
    humidite = int(formulaire.get("humidite", ""))
    brumisation = 1 if formulaire.get("brumisation") == "on" else 0
    eau_changee = 1 if formulaire.get("eau_changee") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            UPDATE releves
            SET animal_id = ?,
                date_releve = ?,
                heure_releve = ?,
                moment = ?,
                temperature = ?,
                humidite = ?,
                brumisation = ?,
                eau_changee = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                animal_id,
                date_releve,
                heure_releve,
                moment,
                temperature,
                humidite,
                brumisation,
                eau_changee,
                notes,
                releve_id,
            ),
        )
        conn.commit()


def ajouter_repas(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_repas = formulaire.get("date_repas") or date.today().isoformat()
    heure_repas = heure_valide(formulaire.get("heure_repas"), heure_actuelle())
    quantite = formulaire.get("quantite", "").strip()
    calcium_sans_d3 = 1 if formulaire.get("calcium_sans_d3") == "on" else 0
    vitamine_d3 = 1 if formulaire.get("vitamine_d3") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        aliment_ligne = aliment_depuis_formulaire(conn, formulaire)
        conn.execute(
            """
            INSERT INTO repas (
                animal_id,
                date_repas,
                heure_repas,
                aliment,
                categorie,
                quantite,
                calcium_sans_d3,
                vitamine_d3,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                animal_id,
                date_repas,
                heure_repas,
                aliment_ligne["nom"],
                aliment_ligne["categorie"],
                quantite,
                calcium_sans_d3,
                vitamine_d3,
                notes,
            ),
        )
        conn.commit()


def ajouter_aliment(formulaire):
    nom = formulaire.get("nom", "").strip()
    categorie = categorie_aliment_valide(formulaire.get("categorie"))
    notes = formulaire.get("notes", "").strip()
    if not nom:
        return

    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO aliments (nom, categorie, notes, masque)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(nom) DO UPDATE SET
                categorie = excluded.categorie,
                notes = excluded.notes,
                masque = 0
            """,
            (nom, categorie, notes),
        )
        conn.commit()


def ajouter_observation(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_observation = formulaire.get("date_observation") or date.today().isoformat()
    heure_observation = heure_valide(formulaire.get("heure_observation"), heure_actuelle())
    categorie = categorie_observation_valide(formulaire.get("categorie"))
    niveau = niveau_observation_valide(formulaire.get("niveau"))
    description = formulaire.get("description", "").strip()
    photo = formulaire.get("photo", "").strip()
    if not animal_id or not description:
        return

    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO observations (
                animal_id,
                date_observation,
                heure_observation,
                categorie,
                niveau,
                description,
                photo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (animal_id, date_observation, heure_observation, categorie, niveau, description, photo),
        )
        conn.commit()


def ajouter_action_insectes(formulaire):
    date_action = formulaire.get("date_action") or date.today().isoformat()
    heure_action = heure_valide(formulaire.get("heure_action"), heure_actuelle())
    boite_id = int(formulaire.get("boite_id", "0"))
    nourrissage = 1 if formulaire.get("nourrissage") == "on" else 0
    nourriture_donnee = formulaire.get("nourriture_donnee", "").strip()
    brumisation = 1 if formulaire.get("brumisation") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        boite_ligne = conn.execute(
            "SELECT * FROM insectes_boites WHERE id = ?",
            (boite_id,),
        ).fetchone()
        if boite_ligne is None:
            abort(400)

        conn.execute(
            """
            INSERT INTO insectes_actions (
                date_action,
                heure_action,
                type_insecte,
                boite,
                nourrissage,
                nourriture_donnee,
                brumisation,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_action,
                heure_action,
                boite_ligne["type_insecte"],
                boite_ligne["nom"],
                nourrissage,
                nourriture_donnee,
                brumisation,
                notes,
            ),
        )
        conn.commit()


def mettre_a_jour_action_insectes(action_id, formulaire):
    date_action = formulaire.get("date_action") or date.today().isoformat()
    heure_action = heure_valide(formulaire.get("heure_action"), heure_actuelle())
    boite_id = int(formulaire.get("boite_id", "0"))
    nourrissage = 1 if formulaire.get("nourrissage") == "on" else 0
    nourriture_donnee = formulaire.get("nourriture_donnee", "").strip()
    brumisation = 1 if formulaire.get("brumisation") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        boite_ligne = conn.execute(
            "SELECT * FROM insectes_boites WHERE id = ?",
            (boite_id,),
        ).fetchone()
        if boite_ligne is None:
            abort(400)

        conn.execute(
            """
            UPDATE insectes_actions
            SET date_action = ?,
                heure_action = ?,
                type_insecte = ?,
                boite = ?,
                nourrissage = ?,
                nourriture_donnee = ?,
                brumisation = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                date_action,
                heure_action,
                boite_ligne["type_insecte"],
                boite_ligne["nom"],
                nourrissage,
                nourriture_donnee,
                brumisation,
                notes,
                action_id,
            ),
        )
        conn.commit()


def ajouter_boite_insectes(formulaire):
    nom = formulaire.get("nom", "").strip()
    type_insecte = formulaire.get("type_insecte", "").strip()
    nombre_individus = int(formulaire.get("nombre_individus", "0"))
    if nombre_individus < 0:
        raise ValueError
    statut = statut_boite_depuis_nombre(nombre_individus)
    date_vide = date.today().isoformat() if statut == "vide" else None
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        curseur = conn.execute(
            """
            INSERT INTO insectes_boites (nom, type_insecte, nombre_individus, statut, date_vide, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (nom, type_insecte, nombre_individus, statut, date_vide, notes),
        )
        conn.execute(
            """
            INSERT INTO insectes_comptages (boite_id, date_comptage, nombre_individus, notes)
            VALUES (?, ?, ?, ?)
            """,
            (curseur.lastrowid, date.today().isoformat(), nombre_individus, "Comptage initial."),
        )
        conn.commit()


def mettre_a_jour_boite_insectes(boite_id, formulaire):
    nom = formulaire.get("nom", "").strip()
    ancien_nom = trouver_ligne("insectes_boites", boite_id)["nom"]
    type_insecte = formulaire.get("type_insecte", "").strip()
    nombre_individus = int(formulaire.get("nombre_individus", "0"))
    if nombre_individus < 0:
        raise ValueError
    statut = statut_boite_depuis_nombre(nombre_individus)
    date_vide = date.today().isoformat() if statut == "vide" else None
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            UPDATE insectes_boites
            SET nom = ?,
                type_insecte = ?,
                nombre_individus = ?,
                statut = ?,
                date_vide = ?,
                notes = ?
            WHERE id = ?
            """,
            (nom, type_insecte, nombre_individus, statut, date_vide, notes, boite_id),
        )
        conn.execute(
            """
            UPDATE insectes_actions
            SET boite = ?,
                type_insecte = ?
            WHERE boite = ?
            """,
            (nom, type_insecte, ancien_nom),
        )
        conn.execute(
            """
            INSERT INTO insectes_comptages (boite_id, date_comptage, nombre_individus, notes)
            VALUES (?, ?, ?, ?)
            """,
            (boite_id, date.today().isoformat(), nombre_individus, "Mise a jour depuis la fiche boite."),
        )
        conn.commit()


def enregistrer_comptage_insectes(boite_id, formulaire):
    date_comptage = date_depuis_chaine(formulaire.get("date_comptage") or date.today().isoformat()).isoformat()
    nombre_individus = int(formulaire.get("nombre_individus", "0"))
    if nombre_individus < 0:
        raise ValueError
    statut = statut_boite_depuis_nombre(nombre_individus)
    date_vide = date_comptage if statut == "vide" else None
    notes = formulaire.get("notes", "").strip()
    with connexion() as conn:
        if conn.execute("SELECT 1 FROM insectes_boites WHERE id = ?", (boite_id,)).fetchone() is None:
            abort(404)
        conn.execute(
            """
            INSERT INTO insectes_comptages (boite_id, date_comptage, nombre_individus, notes)
            VALUES (?, ?, ?, ?)
            """,
            (boite_id, date_comptage, nombre_individus, notes),
        )
        conn.execute(
            """
            UPDATE insectes_boites
            SET nombre_individus = ?,
                statut = ?,
                date_vide = ?
            WHERE id = ?
            """,
            (nombre_individus, statut, date_vide, boite_id),
        )
        conn.commit()


def statut_boite_depuis_nombre(nombre_individus):
    return "vide" if nombre_individus <= 0 else "active"


def ajouter_materiel(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    nom = formulaire.get("nom", "").strip()
    type_materiel = formulaire.get("type", "").strip()
    description = formulaire.get("description", "").strip()
    date_debut = formulaire.get("date_debut", "").strip()
    date_fin = formulaire.get("date_fin", "").strip()
    statut = statut_materiel_valide(formulaire.get("statut"))
    est_consommable = 1 if formulaire.get("est_consommable") == "on" else 0
    quantite_initiale = nombre_ou_none(formulaire.get("quantite_initiale"))
    quantite_restante = nombre_ou_none(formulaire.get("quantite_restante"))
    unite_quantite = unite_quantite_valide(formulaire.get("unite_quantite"))
    statut_contenant = statut_contenant_depuis_quantites(
        est_consommable, quantite_initiale, quantite_restante
    )
    actif = 0 if est_consommable else 1 if formulaire.get("actif") == "on" and not materiel_est_inutilisable(statut) else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        curseur = conn.execute(
            """
            INSERT INTO materiel (
                animal_id,
                nom,
                type,
                description,
                date_debut,
                date_fin,
                statut,
                actif,
                est_consommable,
                quantite_initiale,
                quantite_restante,
                unite_quantite,
                statut_contenant,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                animal_id,
                nom,
                type_materiel,
                description,
                date_debut,
                date_fin,
                statut,
                actif,
                est_consommable,
                quantite_initiale,
                quantite_restante,
                unite_quantite,
                statut_contenant,
                notes,
            ),
        )
        if est_consommable and quantite_restante is not None:
            conn.execute(
                """
                INSERT INTO materiel_mesures (materiel_id, date_mesure, quantite_restante, unite, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (curseur.lastrowid, date.today().isoformat(), quantite_restante, unite_quantite, "Mesure initiale."),
            )
        conn.commit()


def mettre_a_jour_materiel(materiel_id, formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    nom = formulaire.get("nom", "").strip()
    type_materiel = formulaire.get("type", "").strip()
    description = formulaire.get("description", "").strip()
    date_debut = formulaire.get("date_debut", "").strip()
    date_fin = formulaire.get("date_fin", "").strip()
    statut = statut_materiel_valide(formulaire.get("statut"))
    est_consommable = 1 if formulaire.get("est_consommable") == "on" else 0
    quantite_initiale = nombre_ou_none(formulaire.get("quantite_initiale"))
    quantite_restante = nombre_ou_none(formulaire.get("quantite_restante"))
    unite_quantite = unite_quantite_valide(formulaire.get("unite_quantite"))
    statut_contenant = statut_contenant_depuis_quantites(
        est_consommable, quantite_initiale, quantite_restante
    )
    actif = 0 if est_consommable else 1 if formulaire.get("actif") == "on" and not materiel_est_inutilisable(statut) else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            UPDATE materiel
            SET animal_id = ?,
                nom = ?,
                type = ?,
                description = ?,
                date_debut = ?,
                date_fin = ?,
                statut = ?,
                actif = ?,
                est_consommable = ?,
                quantite_initiale = ?,
                quantite_restante = ?,
                unite_quantite = ?,
                statut_contenant = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                animal_id,
                nom,
                type_materiel,
                description,
                date_debut,
                date_fin,
                statut,
                actif,
                est_consommable,
                quantite_initiale,
                quantite_restante,
                unite_quantite,
                statut_contenant,
                notes,
                materiel_id,
            ),
        )
        conn.commit()


def enregistrer_mesure_materiel(materiel_id, formulaire):
    date_mesure = date_depuis_chaine(formulaire.get("date_mesure") or date.today().isoformat()).isoformat()
    quantite_restante = nombre_ou_none(formulaire.get("quantite_restante"))
    if quantite_restante is None or quantite_restante < 0:
        raise ValueError
    unite = unite_quantite_valide(formulaire.get("unite"))
    notes = formulaire.get("notes", "").strip()
    with connexion() as conn:
        materiel_ligne = conn.execute(
            "SELECT quantite_initiale FROM materiel WHERE id = ? AND est_consommable = 1",
            (materiel_id,),
        ).fetchone()
        if materiel_ligne is None:
            abort(404)
        statut_contenant = statut_contenant_depuis_quantites(
            1, materiel_ligne["quantite_initiale"], quantite_restante
        )
        conn.execute(
            """
            INSERT INTO materiel_mesures (materiel_id, date_mesure, quantite_restante, unite, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (materiel_id, date_mesure, quantite_restante, unite, notes),
        )
        conn.execute(
            """
            UPDATE materiel
            SET quantite_restante = ?,
                unite_quantite = ?,
                statut_contenant = ?
            WHERE id = ?
            """,
            (quantite_restante, unite, statut_contenant, materiel_id),
        )
        conn.commit()


def ajouter_type_materiel(formulaire):
    nom = formulaire.get("nom", "").strip()
    notes = formulaire.get("notes", "").strip()
    if not nom:
        return

    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO types_materiel (nom, notes, masque)
            VALUES (?, ?, 0)
            ON CONFLICT(nom) DO UPDATE SET
                notes = excluded.notes,
                masque = 0
            """,
            (nom, notes),
        )
        conn.commit()


def ajouter_plante(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    nom = formulaire.get("nom", "").strip()
    espece = formulaire.get("espece", "").strip()
    type_plante = formulaire.get("type_plante", "").strip()
    etat = formulaire.get("etat", "").strip()
    date_ajout = formulaire.get("date_ajout", "").strip()
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO plantes (
                animal_id,
                nom,
                espece,
                type_plante,
                etat,
                date_ajout,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (animal_id, nom, espece, type_plante, etat, date_ajout, notes),
        )
        conn.commit()


def mettre_a_jour_plante(plante_id, formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    nom = formulaire.get("nom", "").strip()
    espece = formulaire.get("espece", "").strip()
    type_plante = formulaire.get("type_plante", "").strip()
    etat = formulaire.get("etat", "").strip()
    date_ajout = formulaire.get("date_ajout", "").strip()
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        conn.execute(
            """
            UPDATE plantes
            SET animal_id = ?,
                nom = ?,
                espece = ?,
                type_plante = ?,
                etat = ?,
                date_ajout = ?,
                notes = ?
            WHERE id = ?
            """,
            (animal_id, nom, espece, type_plante, etat, date_ajout, notes, plante_id),
        )
        conn.commit()


def mettre_a_jour_repas(repas_id, formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_repas = formulaire.get("date_repas") or date.today().isoformat()
    heure_repas = heure_valide(formulaire.get("heure_repas"), heure_actuelle())
    quantite = formulaire.get("quantite", "").strip()
    calcium_sans_d3 = 1 if formulaire.get("calcium_sans_d3") == "on" else 0
    vitamine_d3 = 1 if formulaire.get("vitamine_d3") == "on" else 0
    notes = formulaire.get("notes", "").strip()

    with connexion() as conn:
        aliment_ligne = aliment_depuis_formulaire(conn, formulaire)
        conn.execute(
            """
            UPDATE repas
            SET animal_id = ?,
                date_repas = ?,
                heure_repas = ?,
                aliment = ?,
                categorie = ?,
                quantite = ?,
                calcium_sans_d3 = ?,
                vitamine_d3 = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                animal_id,
                date_repas,
                heure_repas,
                aliment_ligne["nom"],
                aliment_ligne["categorie"],
                quantite,
                calcium_sans_d3,
                vitamine_d3,
                notes,
                repas_id,
            ),
        )
        conn.commit()


def mettre_a_jour_aliment(aliment_id, formulaire):
    nom = formulaire.get("nom", "").strip()
    categorie = categorie_aliment_valide(formulaire.get("categorie"))
    notes = formulaire.get("notes", "").strip()
    if not nom:
        return

    with connexion() as conn:
        conn.execute(
            """
            UPDATE OR IGNORE aliments
            SET nom = ?,
                categorie = ?,
                notes = ?
            WHERE id = ?
            """,
            (nom, categorie, notes, aliment_id),
        )
        conn.commit()


def trouver_ligne(table, ligne_id):
    # Helper reserve aux routes internes : les noms de tables ne viennent pas
    # directement d'une saisie utilisateur.
    with connexion() as conn:
        ligne = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (ligne_id,)).fetchone()

    if ligne is None:
        abort(404)
    return ligne


def supprimer_ligne(table, ligne_id):
    with connexion() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (ligne_id,))
        conn.commit()


def masquer_ligne(table, ligne_id):
    with connexion() as conn:
        conn.execute(f"UPDATE {table} SET masque = 1 WHERE id = ?", (ligne_id,))
        conn.commit()


def ajouter_animal(formulaire):
    donnees = donnees_animal_depuis_formulaire(formulaire)
    if not donnees["nom"]:
        return
    with connexion() as conn:
        colonnes = ", ".join(donnees.keys())
        marqueurs = ", ".join("?" for _ in donnees)
        conn.execute(
            f"INSERT INTO gecko ({colonnes}) VALUES ({marqueurs})",
            tuple(donnees.values()),
        )
        conn.commit()


def mettre_a_jour_animal(animal_id, formulaire):
    donnees = donnees_animal_depuis_formulaire(formulaire)
    if not donnees["nom"]:
        return
    affectations = ", ".join(f"{colonne} = ?" for colonne in donnees)
    with connexion() as conn:
        conn.execute(
            f"UPDATE gecko SET {affectations} WHERE id = ?",
            (*donnees.values(), animal_id),
        )
        conn.commit()


def donnees_animal_depuis_formulaire(formulaire):
    champs = [
        "nom",
        "espece",
        "date_naissance_estimee",
        "numero_marquage",
        "procedure_marquage",
        "date_adoption",
        "ordre",
        "sexe",
        "nom_vernaculaire",
        "nom_scientifique",
        "classe",
        "origine",
        "pays_origine",
        "taille",
        "taille_valeur",
        "taille_unite",
        "poids",
        "poids_unite",
        "notes",
    ]
    donnees = {champ: formulaire.get(champ, "").strip() for champ in champs}
    donnees["poids_unite"] = unite_poids_valide(donnees["poids_unite"])
    taille_valeur = nombre_ou_none(donnees["taille_valeur"])
    donnees["taille_valeur"] = taille_valeur
    donnees["taille_unite"] = unite_taille_valide(donnees["taille_unite"])
    if taille_valeur is not None:
        donnees["taille"] = f"{format_nombre(taille_valeur)} {donnees['taille_unite']}"
    return donnees


def enregistrer_alerte_config(conn, formulaire, config_id=None):
    cle = formulaire.get("cle", "").strip()
    libelle = formulaire.get("libelle", "").strip()
    source = formulaire.get("source", "").strip() or "general"
    niveau = niveau_alerte_valide(formulaire.get("niveau"))
    if not cle or not libelle:
        return

    valeurs = (
        cle,
        libelle,
        source,
        niveau,
        1 if formulaire.get("actif") == "on" else 0,
        animal_id_alerte_valide(conn, source, entier_ou_none(formulaire.get("animal_id"))),
        nombre_ou_none(formulaire.get("seuil_min")),
        nombre_ou_none(formulaire.get("seuil_max")),
        nombre_ou_none(formulaire.get("delai_valeur")),
        unite_delai_valide(formulaire.get("delai_unite")),
        formulaire.get("unite", "").strip(),
        1 if formulaire.get("phantome") == "on" else 0,
        nombre_ou_none(formulaire.get("preavis_valeur")) or 6,
        unite_delai_valide(formulaire.get("preavis_unite")) or "heures",
        formulaire.get("notes", "").strip(),
    )
    if config_id is None:
        existante = conn.execute(
            """
            SELECT id FROM alertes_config
            WHERE cle = ?
            AND (animal_id = ? OR (animal_id IS NULL AND ? IS NULL))
            LIMIT 1
            """,
            (cle, valeurs[5], valeurs[5]),
        ).fetchone()
        if existante:
            enregistrer_alerte_config(conn, formulaire, existante["id"])
        else:
            conn.execute(
                """
                INSERT INTO alertes_config (
                    cle, libelle, source, niveau, actif, animal_id, seuil_min,
                    seuil_max, delai_valeur, delai_unite, unite, phantome,
                    preavis_valeur, preavis_unite, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                valeurs,
            )
    else:
        conn.execute(
            """
            UPDATE alertes_config
            SET cle = ?,
                libelle = ?,
                source = ?,
                niveau = ?,
                actif = ?,
                animal_id = ?,
                seuil_min = ?,
                seuil_max = ?,
                delai_valeur = ?,
                delai_unite = ?,
                unite = ?,
                phantome = ?,
                preavis_valeur = ?,
                preavis_unite = ?,
                notes = ?
            WHERE id = ?
            """,
            (*valeurs, config_id),
        )


def lister_alertes_config(conn):
    return conn.execute(
        """
        SELECT ac.*, g.nom AS animal_nom
        FROM alertes_config ac
        LEFT JOIN gecko g ON g.id = ac.animal_id
        ORDER BY ac.source, ac.cle, ac.animal_id IS NULL DESC, g.nom
        """
    ).fetchall()


def groupes_alertes_config(alertes_config):
    groupes = []
    index_groupes = {}
    for config in alertes_config:
        cle = config["cle"]
        if cle not in index_groupes:
            groupe = {
                "cle": cle,
                "source": config["source"],
                "configs": [],
            }
            index_groupes[cle] = groupe
            groupes.append(groupe)
        index_groupes[cle]["configs"].append(config)
    return groupes


def charger_alertes_config(conn, animal_id=None):
    lignes = conn.execute(
        """
        SELECT * FROM alertes_config
        WHERE animal_id IS NULL
        OR (
            animal_id = ?
            AND source NOT LIKE 'insectes%'
        )
        ORDER BY animal_id IS NULL DESC
        """,
        (animal_id,),
    ).fetchall()
    return {ligne["cle"]: ligne for ligne in lignes}


def niveau_alerte_valide(valeur):
    return valeur if valeur in {"info", "attention", "danger", "critique"} else "attention"


def sources_alertes():
    return [
        ("temperature_matin", "Temperature matin"),
        ("temperature_soir", "Temperature soir"),
        ("humidite_matin", "Humidite matin"),
        ("humidite_soir", "Humidite soir"),
        ("poids_animal", "Poids animal"),
        ("taille_animal", "Taille animal"),
        ("acces_eau", "Acces a l'eau"),
        ("brumisation", "Brumisation"),
        ("eau_changee", "Changement d'eau"),
        ("repas_frequence", "Minimum de repas animal"),
        ("repas_insectes", "Repas insectes animal"),
        ("repas_calcium_sans_d3", "Calcium sans D3 animal"),
        ("repas_vitamine_d3", "Vitamine D3 animal"),
        ("insectes_nourrissage", "Nourrissage insectes"),
        ("insectes_brumisation", "Brumisation insectes"),
        ("insectes_individus", "Nombre d'insectes"),
        ("lumiere", "Lumiere"),
        ("general", "General"),
    ]


def unite_delai_valide(valeur):
    return valeur if valeur in {"heures", "jours"} else None


def nombre_ou_none(valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    return float(str(valeur).replace(",", "."))


def entier_ou_none(valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    return int(valeur)


def config_active(config):
    return config is not None and config["actif"] == 1


def seuil_min(config, defaut):
    return config["seuil_min"] if config and config["seuil_min"] is not None else defaut


def seuil_max(config, defaut):
    return config["seuil_max"] if config and config["seuil_max"] is not None else defaut


def delai_config_heures(config, defaut):
    if not config or config["delai_valeur"] is None:
        return defaut
    multiplicateur = 24 if config["delai_unite"] == "jours" else 1
    return float(config["delai_valeur"]) * multiplicateur


def preavis_config_heures(config):
    if not config or config["preavis_valeur"] is None:
        return 6
    multiplicateur = 24 if config["preavis_unite"] == "jours" else 1
    return float(config["preavis_valeur"]) * multiplicateur


def format_nombre(valeur):
    if valeur is None:
        return ""
    nombre = float(valeur)
    return str(int(nombre)) if nombre.is_integer() else f"{nombre:.1f}"


def format_duree(heures):
    return f"{format_nombre(heures / 24)} j" if heures >= 24 and heures % 24 == 0 else f"{format_nombre(heures)} h"


def unite_poids_valide(valeur):
    return valeur if valeur in {"g", "kg"} else "g"


def unite_taille_valide(valeur):
    return valeur if valeur in {"cm", "mm", "m"} else "cm"


def valeur_poids(valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    try:
        return float(str(valeur).replace(",", ".").split()[0])
    except ValueError:
        return None


def poids_animal_dans_unite(animal, unite_cible=None):
    if not animal:
        return None
    poids = valeur_poids(animal.get("poids"))
    if poids is None:
        return None
    unite_source = unite_poids_valide(animal.get("poids_unite"))
    unite_cible = unite_poids_valide(unite_cible or unite_source)
    if unite_source == unite_cible:
        return poids
    if unite_source == "kg" and unite_cible == "g":
        return poids * 1000
    if unite_source == "g" and unite_cible == "kg":
        return poids / 1000
    return poids


def formater_poids_animal(animal):
    poids = valeur_poids(animal.get("poids") if animal else None)
    if poids is None:
        return None
    return f"{format_nombre(poids)} {unite_poids_valide(animal.get('poids_unite'))}"


def poids_dans_unite(poids, unite_source, unite_cible):
    poids = valeur_poids(poids)
    if poids is None:
        return None
    unite_source = unite_poids_valide(unite_source)
    unite_cible = unite_poids_valide(unite_cible)
    if unite_source == unite_cible:
        return poids
    if unite_source == "kg" and unite_cible == "g":
        return poids * 1000
    if unite_source == "g" and unite_cible == "kg":
        return poids / 1000
    return poids


def taille_dans_unite(taille, unite_source, unite_cible):
    taille = nombre_ou_none(taille)
    if taille is None:
        return None
    unite_source = unite_taille_valide(unite_source)
    unite_cible = unite_taille_valide(unite_cible)
    facteurs_cm = {"mm": 0.1, "cm": 1, "m": 100}
    return taille * facteurs_cm[unite_source] / facteurs_cm[unite_cible]


def enregistrer_mesure_poids(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_mesure = date_depuis_chaine(formulaire.get("date_mesure") or date.today().isoformat()).isoformat()
    poids = nombre_ou_none(formulaire.get("poids"))
    unite = unite_poids_valide(formulaire.get("unite"))
    notes = formulaire.get("notes", "").strip()
    if animal_id is None or poids is None:
        raise ValueError("animal_id et poids sont obligatoires")
    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO poids_mesures (animal_id, date_mesure, poids, unite, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (animal_id, date_mesure, poids, unite, notes),
        )
        conn.execute(
            """
            UPDATE gecko
            SET poids = ?, poids_unite = ?
            WHERE id = ?
            """,
            (format_nombre(poids), unite, animal_id),
        )
        conn.commit()


def enregistrer_mesure_taille(formulaire):
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    date_mesure = date_depuis_chaine(formulaire.get("date_mesure") or date.today().isoformat()).isoformat()
    taille = nombre_ou_none(formulaire.get("taille"))
    unite = unite_taille_valide(formulaire.get("unite"))
    notes = formulaire.get("notes", "").strip()
    if animal_id is None or taille is None:
        raise ValueError("animal_id et taille sont obligatoires")
    with connexion() as conn:
        conn.execute(
            """
            INSERT INTO taille_mesures (animal_id, date_mesure, taille, unite, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (animal_id, date_mesure, taille, unite, notes),
        )
        conn.execute(
            """
            UPDATE gecko
            SET taille = ?, taille_valeur = ?, taille_unite = ?
            WHERE id = ?
            """,
            (f"{format_nombre(taille)} {unite}", taille, unite, animal_id),
        )
        conn.commit()


def alerte_preventive_autorisee(config, infos_preventives):
    return (
        config_active(config)
        and config["phantome"] == 1
        and (config["niveau"] != "info" or infos_preventives)
    )


def ajouter_alerte_preventive(alertes, config, ligne, champ_date, champ_heure, reference, message, infos_preventives):
    if not ligne:
        return
    ajouter_alerte_preventive_iso(
        alertes,
        config,
        f"{ligne[champ_date]} {ligne[champ_heure] or '00:00'}",
        reference,
        message,
        infos_preventives,
    )


def ajouter_alerte_preventive_date(alertes, config, date_iso, reference, message, infos_preventives):
    if not date_iso:
        return
    ajouter_alerte_preventive_iso(alertes, config, f"{date_iso} 00:00", reference, message, infos_preventives)


def ajouter_alerte_preventive_iso(alertes, config, date_heure_iso, reference, message, infos_preventives):
    if not alerte_preventive_autorisee(config, infos_preventives) or not date_heure_iso:
        return
    derniere_date = datetime.strptime(date_heure_iso, "%Y-%m-%d %H:%M")
    echeance = derniere_date + timedelta(hours=delai_config_heures(config, 24))
    heures_restantes = (echeance - reference).total_seconds() / 3600
    if 0 < heures_restantes <= preavis_config_heures(config):
        alertes.append(
            alerte(
                config["niveau"],
                message.format(reste=format_duree(round(heures_restantes, 1))),
                config["source"],
                echeance.strftime("%Y-%m-%d %H:%M"),
            )
        )


def charger_animal(conn, animal_id=None):
    if animal_id is None:
        animal = conn.execute("SELECT * FROM gecko ORDER BY id LIMIT 1").fetchone()
    else:
        animal = conn.execute("SELECT * FROM gecko WHERE id = ?", (animal_id,)).fetchone()
    if not animal:
        return None
    donnees = dict(animal)
    donnees["age"] = calculer_age(donnees.get("date_naissance_estimee"))
    donnees["poids_affiche"] = formater_poids_animal(donnees)
    return donnees


def calculer_age(date_naissance):
    naissance = date_depuis_chaine(date_naissance)
    aujourd_hui = date.today()
    mois = (aujourd_hui.year - naissance.year) * 12 + aujourd_hui.month - naissance.month
    if aujourd_hui.day < naissance.day:
        mois -= 1
    annees = mois // 12
    reste_mois = mois % 12
    if annees and reste_mois:
        return f"{annees} ans et {reste_mois} mois"
    if annees:
        return f"{annees} ans"
    return f"{reste_mois} mois"


def charger_tableau_de_bord(date_selectionnee, animal_id=None):
    maintenant = datetime.now()
    try:
        jour_selectionne = datetime.strptime(date_selectionnee, "%Y-%m-%d").date()
    except ValueError:
        jour_selectionne = date.today()
        date_selectionnee = jour_selectionne.isoformat()

    with connexion() as conn:
        reglages = charger_reglages(conn)
        moment_actuel = periode_lumiere(maintenant.strftime("%H:%M"), reglages)
        animaux_liste = lister_animaux(conn)
        animal_id = animal_id_selectionne(animaux_liste, animal_id)
        animal = charger_animal(conn, animal_id)
        dernier_matin = dernier_releve_observe(conn, "matin", date_selectionnee, animal_id)
        dernier_soir = dernier_releve_observe(conn, "soir", date_selectionnee, animal_id)
        dernier_releve = conn.execute(
            """
            SELECT * FROM releves
            WHERE animal_id = ?
            ORDER BY date_releve DESC, heure_releve DESC, created_at DESC
            LIMIT 1
            """,
            (animal_id,),
        ).fetchone()
        dernier_repas = conn.execute(
            """
            SELECT * FROM repas
            WHERE animal_id = ?
            ORDER BY date_repas DESC, heure_repas DESC, created_at DESC
            LIMIT 1
            """,
            (animal_id,),
        ).fetchone()
        dernier_poids = conn.execute(
            """
            SELECT * FROM poids_mesures
            WHERE animal_id = ?
            ORDER BY date_mesure DESC, created_at DESC
            LIMIT 1
            """,
            (animal_id,),
        ).fetchone()
        derniere_taille = conn.execute(
            """
            SELECT * FROM taille_mesures
            WHERE animal_id = ?
            ORDER BY date_mesure DESC, created_at DESC
            LIMIT 1
            """,
            (animal_id,),
        ).fetchone()
        dernieres_observations = conn.execute(
            """
            SELECT * FROM observations
            WHERE animal_id = ?
            ORDER BY date_observation DESC, heure_observation DESC, created_at DESC
            LIMIT 5
            """,
            (animal_id,),
        ).fetchall()
        observations_a_surveiller = conn.execute(
            """
            SELECT * FROM observations
            WHERE animal_id = ?
            AND niveau IN ('a_surveiller', 'inquietant')
            ORDER BY date_observation DESC, heure_observation DESC, created_at DESC
            LIMIT 5
            """,
            (animal_id,),
        ).fetchall()
        materiels_actifs = conn.execute(
            """
            SELECT * FROM materiel
            WHERE animal_id = ?
            AND actif = 1
            AND statut != 'obsolete_casse'
            ORDER BY type, nom
            """,
            (animal_id,),
        ).fetchall()
        materiels_jour = materiel_utilise_pour_date(conn, date_selectionnee, animal_id)
        plantes_a_surveiller = conn.execute(
            """
            SELECT * FROM plantes
            WHERE animal_id = ?
            AND etat IN ('mauvais', 'decede')
            ORDER BY etat DESC, nom
            """,
            (animal_id,),
        ).fetchall()
        derniers_insectes = conn.execute(
            """
            SELECT
                b.type_insecte,
                b.nom AS boite,
                b.nombre_individus,
                MAX(a.date_action || ' ' || COALESCE(a.heure_action, '00:00')) AS derniere_action
            FROM insectes_boites b
            LEFT JOIN insectes_actions a ON a.boite = b.nom
            WHERE b.statut = 'active'
            AND b.nombre_individus > 0
            GROUP BY b.id
            ORDER BY b.type_insecte, b.nom
            """
        ).fetchall()
        releves_jour = conn.execute(
            """
            SELECT * FROM releves
            WHERE animal_id = ?
            AND date_releve = ?
            ORDER BY heure_releve, created_at
            """,
            (animal_id, date_selectionnee),
        ).fetchall()
        repas_jour = conn.execute(
            """
            SELECT * FROM repas
            WHERE animal_id = ?
            AND date_repas = ?
            ORDER BY heure_repas, created_at
            """,
            (animal_id, date_selectionnee),
        ).fetchall()
        observations_jour = conn.execute(
            """
            SELECT * FROM observations
            WHERE animal_id = ?
            AND date_observation = ?
            ORDER BY heure_observation, created_at
            """,
            (animal_id, date_selectionnee),
        ).fetchall()
        insectes_jour = conn.execute(
            """
            SELECT * FROM insectes_actions
            WHERE date_action = ?
            ORDER BY heure_action, created_at
            """,
            (date_selectionnee,),
        ).fetchall()
        historique_jour = construire_historique_jour(
            releves_jour, repas_jour, insectes_jour, materiels_jour, observations_jour
        )
        graphiques = donnees_graphiques(conn, animal_id)
        resultats_alertes = calculer_alertes(conn, maintenant, reglages, date_selectionnee, animal_id)
        alertes_config = lister_alertes_config(conn)

    return {
        "date_selectionnee": date_selectionnee,
        "maintenant": maintenant.strftime("%Y-%m-%d %H:%M"),
        "reglages": reglages,
        "moment_actuel": moment_actuel,
        "animaux": animaux_liste,
        "animal_id": animal_id,
        "animal": animal,
        "dernier_matin": dernier_matin,
        "dernier_soir": dernier_soir,
        "dernier_releve": dernier_releve,
        "dernier_releve_periode": dernier_releve["moment"] if dernier_releve else None,
        "dernier_repas": dernier_repas,
        "dernier_poids": dernier_poids,
        "derniere_taille": derniere_taille,
        "dernieres_observations": dernieres_observations,
        "observations_a_surveiller": observations_a_surveiller,
        "materiels_actifs": materiels_actifs,
        "materiels_jour": materiels_jour,
        "plantes_a_surveiller": plantes_a_surveiller,
        "derniers_insectes": derniers_insectes,
        "releves_jour": releves_jour,
        "repas_jour": repas_jour,
        "observations_jour": observations_jour,
        "insectes_jour": insectes_jour,
        "historique_jour": historique_jour,
        "graphiques": graphiques,
        "alertes": resultats_alertes["alertes_actuelles"],
        "alertes_actuelles": resultats_alertes["alertes_actuelles"],
        "alertes_a_venir": resultats_alertes["alertes_a_venir"],
        "alertes_config": alertes_config,
    }


def calculer_alertes(conn, maintenant=None, reglages=None, date_selectionnee=None, animal_id=None):
    # Point central de la logique metier : cette fonction lit les donnees
    # recentes, applique les seuils configurables et separe les alertes
    # actives des alertes preventives.
    maintenant = maintenant or datetime.now()
    reglages = reglages or charger_reglages(conn)
    aujourd_hui = date_depuis_chaine(date_selectionnee) if date_selectionnee else maintenant.date()
    reference = maintenant if aujourd_hui == maintenant.date() else datetime.combine(aujourd_hui, datetime.max.time()).replace(microsecond=0)
    config = charger_alertes_config(conn, animal_id)
    infos_preventives = reglages.get("alertes_info_preventives") == "1"
    alertes = []
    alertes_a_venir = []

    derniers_releves = conn.execute(
        """
        SELECT * FROM releves
        WHERE animal_id = ?
        AND date_releve = ?
        ORDER BY heure_releve, created_at
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchall()
    for releve in derniers_releves:
        periode = releve["moment"]
        quand = f"{releve['date_releve']} {releve['heure_releve'] or ''}".strip()
        temperature = releve["temperature"]

        temp_critique = config.get("temp_jour_critique")
        temp_danger = config.get("temp_jour_danger")
        temp_jour_min_attention = config.get("temp_jour_min_attention")
        temp_jour_max_attention = config.get("temp_jour_max_attention")
        temp_nuit_min = config.get("temp_nuit_min")
        temp_nuit_attention = config.get("temp_nuit_attention")
        alerte_temperature_haute = False
        if config_active(temp_critique) and temperature > seuil_max(temp_critique, 30):
            alertes.append(
                alerte(temp_critique["niveau"], f"Temperature critique au-dessus de {format_nombre(seuil_max(temp_critique, 30))} degres.", temp_critique["source"], quand)
            )
            alerte_temperature_haute = True
        elif config_active(temp_danger) and temperature >= seuil_max(temp_danger, 28):
            alertes.append(
                alerte(temp_danger["niveau"], f"Temperature dangereuse proche de {format_nombre(seuil_max(temp_danger, 28))} degres.", temp_danger["source"], quand)
            )
            alerte_temperature_haute = True

        if periode == "soir" and config_active(temp_jour_min_attention) and temperature < seuil_min(temp_jour_min_attention, 22):
            alertes.append(
                alerte(temp_jour_min_attention["niveau"], f"Temperature de jour sous l'ideal de {format_nombre(seuil_min(temp_jour_min_attention, 22))} degres.", temp_jour_min_attention["source"], quand)
            )
        elif (
            periode == "soir"
            and not alerte_temperature_haute
            and config_active(temp_jour_max_attention)
            and temperature > seuil_max(temp_jour_max_attention, 24)
        ):
            alertes.append(
                alerte(temp_jour_max_attention["niveau"], f"Temperature de jour au-dessus de l'ideal de {format_nombre(seuil_max(temp_jour_max_attention, 24))} degres.", temp_jour_max_attention["source"], quand)
            )

        if periode == "matin" and config_active(temp_nuit_min) and temperature < seuil_min(temp_nuit_min, 17):
            alertes.append(
                alerte(temp_nuit_min["niveau"], f"Temperature de nuit sous {format_nombre(seuil_min(temp_nuit_min, 17))} degres.", temp_nuit_min["source"], quand)
            )
        elif periode == "matin" and config_active(temp_nuit_attention) and temperature < seuil_min(temp_nuit_attention, 20):
            alertes.append(
                alerte(temp_nuit_attention["niveau"], f"Temperature de nuit sous {format_nombre(seuil_min(temp_nuit_attention, 20))} degres.", temp_nuit_attention["source"], quand)
            )

        humidite = releve["humidite"]
        humidite_min = config.get("humidite_min")
        humidite_max = config.get("humidite_max")
        if config_active(humidite_min) and humidite < seuil_min(humidite_min, 45):
            alertes.append(
                alerte(humidite_min["niveau"], f"Humidite trop basse sous {format_nombre(seuil_min(humidite_min, 45))} %.", f"humidite_{periode}", quand)
            )
        elif config_active(humidite_max) and humidite > seuil_max(humidite_max, 90):
            alertes.append(
                alerte(humidite_max["niveau"], f"Humidite au-dessus de {format_nombre(seuil_max(humidite_max, 90))} %.", f"humidite_{periode}", quand)
            )
        elif humidite > 70 and not releve["brumisation"]:
            alertes.append(
                alerte("info", "Humidite haute sans brumisation notee.", f"humidite_{periode}", quand)
            )

    animal = charger_animal(conn, animal_id)
    config_poids_min = config.get("poids_min")
    config_poids_max = config.get("poids_max")
    if animal and poids_animal_dans_unite(animal, None) is not None and config_active(config_poids_min):
        unite = unite_poids_valide(config_poids_min["unite"] or animal.get("poids_unite"))
        poids_converti = poids_animal_dans_unite(animal, unite)
        limite = seuil_min(config_poids_min, None)
        if limite is not None and poids_converti is not None and poids_converti < limite:
            alertes.append(
                alerte(
                    config_poids_min["niveau"],
                    f"Poids sous {format_nombre(limite)} {unite}.",
                    config_poids_min["source"],
                    reference.strftime("%Y-%m-%d %H:%M"),
                )
            )
    if animal and poids_animal_dans_unite(animal, None) is not None and config_active(config_poids_max):
        unite = unite_poids_valide(config_poids_max["unite"] or animal.get("poids_unite"))
        poids_converti = poids_animal_dans_unite(animal, unite)
        limite = seuil_max(config_poids_max, None)
        if limite is not None and poids_converti is not None and poids_converti > limite:
            alertes.append(
                alerte(
                    config_poids_max["niveau"],
                    f"Poids au-dessus de {format_nombre(limite)} {unite}.",
                    config_poids_max["source"],
                    reference.strftime("%Y-%m-%d %H:%M"),
                )
            )

    config_poids_repeser = config.get("poids_repeser")
    dernier_poids = conn.execute(
        """
        SELECT date_mesure FROM poids_mesures
        WHERE animal_id = ?
        AND date_mesure <= ?
        ORDER BY date_mesure DESC, created_at DESC
        LIMIT 1
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchone()
    delai_pesee = delai_config_heures(config_poids_repeser, 28 * 24)
    if config_active(config_poids_repeser):
        if dernier_poids is None:
            alertes.append(
                alerte(
                        config_poids_repeser["niveau"],
                        "Aucune pesee notee pour cet animal.",
                        config_poids_repeser["source"],
                    reference.strftime("%Y-%m-%d %H:%M"),
                )
            )
        else:
            derniere_pesee = datetime.strptime(dernier_poids["date_mesure"], "%Y-%m-%d")
            heures_depuis_pesee = (reference - derniere_pesee).total_seconds() / 3600
            if heures_depuis_pesee > delai_pesee:
                alertes.append(
                    alerte(
                        config_poids_repeser["niveau"],
                        f"Derniere pesee il y a plus de {format_duree(delai_pesee)}.",
                        config_poids_repeser["source"],
                        reference.strftime("%Y-%m-%d %H:%M"),
                    )
                )
    ajouter_alerte_preventive_date(
        alertes_a_venir,
        config_poids_repeser,
        dernier_poids["date_mesure"] if dernier_poids else None,
        reference,
        "Pesee a refaire dans {reste}.",
        infos_preventives,
    )

    derniere_taille = conn.execute(
        """
        SELECT date_mesure, taille, unite FROM taille_mesures
        WHERE animal_id = ?
        AND date_mesure <= ?
        ORDER BY date_mesure DESC, created_at DESC
        LIMIT 1
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchone()
    for cle, sens in (("taille_min", "min"), ("taille_max", "max")):
        config_taille = config.get(cle)
        if not config_active(config_taille) or derniere_taille is None:
            continue
        unite = unite_taille_valide(config_taille["unite"] or derniere_taille["unite"])
        taille_convertie = taille_dans_unite(derniere_taille["taille"], derniere_taille["unite"], unite)
        limite = seuil_min(config_taille, None) if sens == "min" else seuil_max(config_taille, None)
        if limite is None or taille_convertie is None:
            continue
        if (sens == "min" and taille_convertie < limite) or (sens == "max" and taille_convertie > limite):
            comparaison = "sous" if sens == "min" else "au-dessus de"
            alertes.append(
                alerte(
                    config_taille["niveau"],
                    f"Taille {comparaison} {format_nombre(limite)} {unite}.",
                    config_taille["source"],
                    reference.strftime("%Y-%m-%d %H:%M"),
                )
            )

    derniere_eau = conn.execute(
        """
        SELECT date_releve, heure_releve FROM releves
        WHERE animal_id = ?
        AND date_releve <= ?
        AND (brumisation = 1 OR eau_changee = 1)
        ORDER BY date_releve DESC, heure_releve DESC, created_at DESC
        LIMIT 1
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchone()
    eau_du_jour = conn.execute(
        """
        SELECT 1 FROM releves
        WHERE animal_id = ?
        AND date_releve = ?
        AND (brumisation = 1 OR eau_changee = 1)
        LIMIT 1
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchone()

    config_eau = config.get("acces_eau")
    delai_eau = delai_config_heures(config_eau, 18)
    if aujourd_hui == maintenant.date():
        manque_eau = derniere_eau is None or heures_depuis_ligne(
            derniere_eau, "date_releve", "heure_releve", maintenant
        ) > delai_eau
        message_eau = f"Aucune brumisation ou eau changee notee depuis plus de {format_duree(delai_eau)}."
    else:
        manque_eau = eau_du_jour is None
        message_eau = "Aucune brumisation ou eau changee notee ce jour-la."

    if config_active(config_eau) and manque_eau:
        alertes.append(
            alerte(config_eau["niveau"], message_eau, config_eau["source"], reference.strftime("%Y-%m-%d %H:%M"))
        )
    ajouter_alerte_preventive(
        alertes_a_venir,
        config_eau,
        derniere_eau,
        "date_releve",
        "heure_releve",
        reference,
        f"Acces a l'eau a verifier dans {{reste}}.",
        infos_preventives,
    )

    config_repas_min = config.get("repas_semaine_min")
    jours_repas = int(delai_config_heures(config_repas_min, 168) / 24)
    limite_7_jours = (aujourd_hui - timedelta(days=jours_repas)).isoformat()
    nb_repas = conn.execute(
        """
        SELECT COUNT(*) FROM repas
        WHERE animal_id = ?
        AND date_repas >= ?
        AND date_repas <= ?
        """,
        (animal_id, limite_7_jours, aujourd_hui.isoformat()),
    ).fetchone()[0]
    repas_min = seuil_min(config_repas_min, 2)
    if config_active(config_repas_min) and nb_repas < repas_min:
        alertes.append(
            alerte(config_repas_min["niveau"], f"Moins de {format_nombre(repas_min)} repas notes sur les {jours_repas} derniers jours.", config_repas_min["source"], reference.strftime("%Y-%m-%d %H:%M"))
        )

    config_insectes_min = config.get("insectes_semaine_min")
    nb_insectes = conn.execute(
        """
        SELECT COUNT(*) FROM repas
        WHERE animal_id = ?
        AND date_repas >= ?
        AND date_repas <= ?
        AND categorie = 'insectes'
        """,
        (animal_id, limite_7_jours, aujourd_hui.isoformat()),
    ).fetchone()[0]
    insectes_min = seuil_min(config_insectes_min, 1)
    if config_active(config_insectes_min) and nb_insectes < insectes_min:
        alertes.append(
            alerte(config_insectes_min["niveau"], f"Moins de {format_nombre(insectes_min)} repas avec insectes sur les {jours_repas} derniers jours.", config_insectes_min["source"], reference.strftime("%Y-%m-%d %H:%M"))
        )

    config_d3 = config.get("vitamine_d3_delai")
    dernier_d3 = conn.execute(
        """
        SELECT date_repas FROM repas
        WHERE animal_id = ?
        AND vitamine_d3 = 1
        AND date_repas <= ?
        ORDER BY date_repas DESC
        LIMIT 1
        """,
        (animal_id, aujourd_hui.isoformat()),
    ).fetchone()
    delai_d3 = delai_config_heures(config_d3, 720)
    if config_active(config_d3) and (dernier_d3 is None or jours_depuis(dernier_d3["date_repas"], aujourd_hui) * 24 > delai_d3):
        alertes.append(
            alerte(config_d3["niveau"], f"Vitamine D3 non donnee depuis plus de {format_duree(delai_d3)}.", config_d3["source"], reference.strftime("%Y-%m-%d %H:%M"))
        )
    ajouter_alerte_preventive_date(
        alertes_a_venir,
        config_d3,
        dernier_d3["date_repas"] if dernier_d3 else None,
        reference,
        "Vitamine D3 a prevoir dans {reste}.",
        infos_preventives,
    )

    boites_grillons = boites_par_type(conn, "grillons")
    for boite in boites_grillons:
        config_grillons_nourrissage = config.get("grillons_nourrissage")
        dernier_nourrissage = derniere_action_insectes(conn, "grillons", boite, "nourrissage", reference)
        delai_grillons_nourrissage = delai_config_heures(config_grillons_nourrissage, 48)
        if config_active(config_grillons_nourrissage) and (dernier_nourrissage is None or heures_depuis_iso(dernier_nourrissage, reference) > delai_grillons_nourrissage):
            alertes.append(
                alerte(config_grillons_nourrissage["niveau"], f"{boite} : grillons a nourrir.", config_grillons_nourrissage["source"], reference.strftime("%Y-%m-%d %H:%M"))
            )
        ajouter_alerte_preventive_iso(alertes_a_venir, config_grillons_nourrissage, dernier_nourrissage, reference, f"{boite} : grillons a nourrir dans {{reste}}.", infos_preventives)

        config_grillons_brumisation = config.get("grillons_brumisation")
        derniere_brumisation = derniere_action_insectes(conn, "grillons", boite, "brumisation", reference)
        delai_grillons_brumisation = delai_config_heures(config_grillons_brumisation, 48)
        if config_active(config_grillons_brumisation) and (derniere_brumisation is None or heures_depuis_iso(derniere_brumisation, reference) > delai_grillons_brumisation):
            alertes.append(
                alerte(config_grillons_brumisation["niveau"], f"{boite} : grillons a brumiser.", config_grillons_brumisation["source"], reference.strftime("%Y-%m-%d %H:%M"))
            )
        ajouter_alerte_preventive_iso(alertes_a_venir, config_grillons_brumisation, derniere_brumisation, reference, f"{boite} : grillons a brumiser dans {{reste}}.", infos_preventives)

    boites_red_runner = boites_par_type(conn, "red runner")
    for boite in boites_red_runner:
        config_red_runner = config.get("red_runner_brumisation")
        derniere_brumisation = derniere_action_insectes(conn, "red runner", boite, "brumisation", reference)
        delai_red_runner = delai_config_heures(config_red_runner, 168)
        if config_active(config_red_runner) and (derniere_brumisation is None or heures_depuis_iso(derniere_brumisation, reference) > delai_red_runner):
            alertes.append(
                alerte(config_red_runner["niveau"], f"{boite} : red runner a brumiser.", config_red_runner["source"], reference.strftime("%Y-%m-%d %H:%M"))
            )
        ajouter_alerte_preventive_iso(alertes_a_venir, config_red_runner, derniere_brumisation, reference, f"{boite} : red runner a brumiser dans {{reste}}.", infos_preventives)

    config_insectes_individus = config.get("insectes_individus_min")
    minimum_individus = seuil_min(config_insectes_individus, None)
    if config_active(config_insectes_individus) and minimum_individus is not None:
        boites = conn.execute(
            """
            SELECT nom, type_insecte, nombre_individus
            FROM insectes_boites
            WHERE nombre_individus < ?
            ORDER BY type_insecte, nom
            """,
            (minimum_individus,),
        ).fetchall()
        for boite in boites:
            alertes.append(
                alerte(
                    config_insectes_individus["niveau"],
                    f"{boite['nom']} : {boite['nombre_individus']} individu(s), sous le seuil de {format_nombre(minimum_individus)}.",
                    config_insectes_individus["source"],
                    reference.strftime("%Y-%m-%d %H:%M"),
                )
            )

    config_lumiere = config.get("lumiere_duree")
    duree_lumiere = duree_lumiere_heures(reglages)
    if config_active(config_lumiere) and (
        duree_lumiere < seuil_min(config_lumiere, 10)
        or duree_lumiere > seuil_max(config_lumiere, 12)
    ):
        alertes.append(
            alerte(config_lumiere["niveau"], f"La plage de lumiere devrait rester autour de {format_nombre(seuil_min(config_lumiere, 10))} a {format_nombre(seuil_max(config_lumiere, 12))} h.", "lumiere", reference.strftime("%Y-%m-%d %H:%M"))
        )

    return {
        "alertes_actuelles": regrouper_alertes(alertes),
        "alertes_a_venir": regrouper_alertes(alertes_a_venir),
    }


def boites_par_type(conn, type_insecte):
    lignes = conn.execute(
        """
        SELECT nom AS boite FROM insectes_boites
        WHERE type_insecte = ?
        AND nombre_individus > 0
        ORDER BY boite
        """,
        (type_insecte,),
    ).fetchall()
    return [ligne["boite"] for ligne in lignes]


def derniere_action_insectes(conn, type_insecte, boite, action, reference=None):
    # Le parametre action est controle par le code appelant et correspond aux
    # colonnes booleennes connues : nourrissage ou brumisation.
    reference = reference or datetime.now()
    ligne = conn.execute(
        f"""
        SELECT date_action, heure_action FROM insectes_actions
        WHERE type_insecte = ?
        AND boite = ?
        AND {action} = 1
        AND (date_action || ' ' || COALESCE(heure_action, '00:00')) <= ?
        ORDER BY date_action DESC, heure_action DESC, created_at DESC
        LIMIT 1
        """,
        (type_insecte, boite, reference.strftime("%Y-%m-%d %H:%M")),
    ).fetchone()
    if not ligne:
        return None
    return f"{ligne['date_action']} {ligne['heure_action'] or '00:00'}"


def lister_boites_insectes(conn, inclure_vides=False, seulement_vides=False):
    filtre = ""
    if seulement_vides:
        filtre = "WHERE statut = 'vide' OR nombre_individus <= 0"
    elif not inclure_vides:
        filtre = "WHERE statut = 'active' AND nombre_individus > 0"
    return conn.execute(
        f"""
        SELECT * FROM insectes_boites
        {filtre}
        ORDER BY type_insecte, nom
        """
    ).fetchall()


def lister_aliments(conn):
    return conn.execute(
        """
        SELECT * FROM aliments
        WHERE masque = 0
        ORDER BY categorie, nom
        """
    ).fetchall()


def lister_types_materiel(conn):
    return conn.execute(
        """
        SELECT * FROM types_materiel
        WHERE masque = 0
        ORDER BY nom
        """
    ).fetchall()


def lister_animaux(conn):
    return conn.execute(
        """
        SELECT *,
               nom || COALESCE(' - ' || nom_vernaculaire, '') AS libelle
        FROM gecko
        ORDER BY nom
        """
    ).fetchall()


def animal_id_alerte_valide(conn, source, animal_id):
    if source.startswith("insectes"):
        return None
    if animal_id is not None:
        return animal_id
    animal = conn.execute(
        """
        SELECT id FROM gecko
        ORDER BY CASE WHEN nom = 'Xena' THEN 0 ELSE 1 END, id
        LIMIT 1
        """
    ).fetchone()
    return animal["id"] if animal else None


def animal_id_selectionne(animaux_liste, animal_id=None):
    ids = {animal["id"] for animal in animaux_liste}
    if animal_id in ids:
        return animal_id
    for animal in animaux_liste:
        if animal["nom"] == "Xena":
            return animal["id"]
    return animaux_liste[0]["id"] if animaux_liste else None


def aliment_depuis_formulaire(conn, formulaire):
    aliment_id = formulaire.get("aliment_id", "")
    if aliment_id.isdigit():
        aliment_ligne = conn.execute(
            "SELECT * FROM aliments WHERE id = ?",
            (int(aliment_id),),
        ).fetchone()
        if aliment_ligne:
            return aliment_ligne

    ancien_nom = formulaire.get("aliment", "").strip()
    if ancien_nom:
        aliment_ligne = conn.execute(
            "SELECT * FROM aliments WHERE nom = ?",
            (ancien_nom,),
        ).fetchone()
        if aliment_ligne:
            return aliment_ligne
        return {"nom": ancien_nom, "categorie": categorie_aliment_valide(formulaire.get("categorie"))}

    abort(400)


def categories_aliments():
    return ["insectes", "patee", "fruit", "autre"]


def categorie_aliment_valide(valeur):
    return valeur if valeur in categories_aliments() else "autre"


def categories_observation():
    return [
        ("comportement", "Comportement"),
        ("mue", "Mue"),
        ("selles", "Selles"),
        ("sante", "Sante"),
        ("reproduction", "Reproduction"),
        ("entretien", "Entretien / nettoyage"),
        ("autre", "Autre"),
    ]


def categorie_observation_valide(valeur):
    valeurs = {categorie[0] for categorie in categories_observation()}
    return valeur if valeur in valeurs else "comportement"


def niveaux_observation():
    return [
        ("normal", "Normal"),
        ("a_surveiller", "A surveiller"),
        ("inquietant", "Inquietant"),
    ]


def niveau_observation_valide(valeur):
    valeurs = {niveau[0] for niveau in niveaux_observation()}
    return valeur if valeur in valeurs else "normal"


def statuts_materiel():
    return [
        ("excellent_neuf", "Excellent/neuf"),
        ("bien_ok", "Bien/ok"),
        ("pas_oof", "Pas oof"),
        ("horrible", "Horrible"),
        ("obsolete_casse", "Obsolète/cassé"),
        ("maintenance", "Maintenance"),
    ]


def statuts_contenant():
    return [
        ("non_applicable", "Non applicable"),
        ("rempli", "Rempli"),
        ("moitie", "A moitie"),
        ("vide", "Vide"),
    ]


def libelle_statut_contenant(valeur):
    return dict(statuts_contenant()).get(valeur, valeur)


def unite_quantite_valide(valeur):
    return valeur if valeur in {"g", "kg", "ml", "l"} else "g"


def statut_contenant_depuis_quantites(est_consommable, quantite_initiale, quantite_restante):
    if not est_consommable:
        return "non_applicable"
    if quantite_restante is None or quantite_restante <= 0:
        return "vide"
    if quantite_initiale and quantite_initiale > 0 and quantite_restante <= quantite_initiale / 2:
        return "moitie"
    return "rempli"


def statut_materiel_valide(valeur):
    valeurs = {statut[0] for statut in statuts_materiel()}
    anciens = {
        "ok": "bien_ok",
        "a_verifier": "maintenance",
        "casse": "obsolete_casse",
        "obsolete": "obsolete_casse",
    }
    valeur = anciens.get(valeur, valeur)
    return valeur if valeur in valeurs else "bien_ok"


def libelle_statut_materiel(valeur):
    libelles = dict(statuts_materiel())
    return libelles.get(valeur, valeur)


def materiel_est_inutilisable(statut):
    return statut_materiel_valide(statut) == "obsolete_casse"


def dernier_releve_observe(conn, periode, date_selectionnee=None, animal_id=None):
    if date_selectionnee:
        return conn.execute(
            """
            SELECT * FROM releves
            WHERE moment = ?
            AND animal_id = ?
            AND date_releve = ?
            ORDER BY heure_releve DESC, created_at DESC
            LIMIT 1
            """,
            (periode, animal_id, date_selectionnee),
        ).fetchone()

    return conn.execute(
        """
        SELECT * FROM releves
        WHERE moment = ?
        AND animal_id = ?
        ORDER BY date_releve DESC, heure_releve DESC, created_at DESC
        LIMIT 1
        """,
        (periode, animal_id),
    ).fetchone()


def charger_reglages(conn):
    lignes = conn.execute("SELECT cle, valeur FROM reglages").fetchall()
    reglages = {ligne["cle"]: ligne["valeur"] for ligne in lignes}
    return {
        "heure_allumage": heure_valide(reglages.get("heure_allumage"), "08:00"),
        "heure_extinction": heure_valide(reglages.get("heure_extinction"), "20:00"),
        "alertes_info_preventives": "1" if reglages.get("alertes_info_preventives") == "1" else "0",
        "discord_mode": mode_discord_valide(reglages.get("discord_mode")),
        "discord_webhook_url": reglages.get("discord_webhook_url", ""),
        "discord_bot_token": reglages.get("discord_bot_token", ""),
        "discord_channel_id": reglages.get("discord_channel_id", ""),
        "discord_alertes_actives": "1" if reglages.get("discord_alertes_actives") != "0" else "0",
        "discord_alertes_preventives": "1" if reglages.get("discord_alertes_preventives") != "0" else "0",
        "discord_auto_actif": "1" if reglages.get("discord_auto_actif") == "1" else "0",
        "discord_resume_quotidien": "1" if reglages.get("discord_resume_quotidien") != "0" else "0",
        "discord_resume_heure": heure_valide(reglages.get("discord_resume_heure"), "18:00"),
        "discord_temps_reel": "1" if reglages.get("discord_temps_reel") != "0" else "0",
        "discord_niveaux": niveaux_discord_valides(reglages.get("discord_niveaux")),
    }


def enregistrer_reglage(conn, cle, valeur):
    conn.execute(
        """
        INSERT INTO reglages (cle, valeur)
        VALUES (?, ?)
        ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur
        """,
        (cle, valeur),
    )


def mode_discord_valide(valeur):
    return valeur if valeur in {"webhook", "bot"} else "webhook"


def niveaux_discord_valides(valeur):
    niveaux = [niveau for niveau in (valeur or "").split(",") if niveau in {"info", "attention", "danger", "critique"}]
    return niveaux or ["attention", "danger", "critique"]


def niveaux_discord_depuis_formulaire(formulaire):
    niveaux = [
        niveau
        for niveau in ["info", "attention", "danger", "critique"]
        if formulaire.get(f"discord_niveau_{niveau}") == "on"
    ]
    return ",".join(niveaux or ["attention", "danger", "critique"])


def envoyer_resume_alertes_discord(conn, reglages_app=None):
    reglages_app = reglages_app or charger_reglages(conn)
    lignes = ["**GeckoCare Xena - alertes**", datetime.now().strftime("%Y-%m-%d %H:%M")]
    blocs_par_animal = alertes_discord_par_animal(conn, reglages_app)
    total = sum(len(blocs) for blocs in blocs_par_animal.values())
    for animal_nom, blocs in blocs_par_animal.items():
        lignes.append("")
        lignes.append(f"__{animal_nom}__")
        for type_alerte, alerte_item in blocs[:8]:
            lignes.append(
                f"- {type_alerte} [{alerte_item['niveau']}] {alerte_item['message']} ({alerte_item['source']})"
            )

    if total == 0:
        lignes.append("")
        lignes.append("Aucune alerte a signaler.")

    contenu = "\n".join(lignes)
    if len(contenu) > 1900:
        contenu = contenu[:1890] + "\n...resume tronque."

    envoyer_message_discord(reglages_app, contenu)


def alertes_discord_par_animal(conn, reglages_app=None):
    reglages_app = reglages_app or charger_reglages(conn)
    niveaux = set(reglages_app.get("discord_niveaux") or ["attention", "danger", "critique"])
    blocs_par_animal = {}
    signatures = set()
    for animal in lister_animaux(conn):
        resultats = calculer_alertes(conn, datetime.now(), reglages_app, date.today().isoformat(), animal["id"])
        blocs = []
        if reglages_app.get("discord_alertes_actives") == "1":
            blocs.extend(("Actuelle", alerte_item) for alerte_item in resultats["alertes_actuelles"])
        if reglages_app.get("discord_alertes_preventives") == "1":
            blocs.extend(("A venir", alerte_item) for alerte_item in resultats["alertes_a_venir"])

        blocs_filtres = []
        for type_alerte, alerte_item in blocs:
            if alerte_item["niveau"] not in niveaux:
                continue
            signature = signature_alerte_discord(animal["id"], type_alerte, alerte_item)
            if signature in signatures:
                continue
            signatures.add(signature)
            blocs_filtres.append((type_alerte, alerte_item))
        if blocs_filtres:
            blocs_par_animal[animal["nom"]] = blocs_filtres
    return blocs_par_animal


def signature_alerte_discord(animal_id, type_alerte, alerte_item):
    animal_signature = "global" if alerte_item["source"].startswith("insectes") else str(animal_id)
    return "|".join(
        [
            animal_signature,
            type_alerte,
            alerte_item["niveau"],
            alerte_item["source"],
            alerte_item["message"],
        ]
    )


def envoyer_message_discord(reglages_app, contenu):
    if mode_discord_valide(reglages_app.get("discord_mode")) == "bot":
        envoyer_message_discord_bot(reglages_app, contenu)
    else:
        envoyer_message_discord_webhook(reglages_app, contenu)


def envoyer_message_discord_webhook(reglages_app, contenu):
    webhook_url = reglages_app.get("discord_webhook_url", "").strip()
    if not webhook_url:
        raise ValueError("Webhook Discord non configure.")
    if not url_webhook_discord_valide(webhook_url):
        raise ValueError("URL Discord invalide : colle l'URL d'un webhook de salon, pas un token de bot ni un lien de salon.")

    requete = urlrequest.Request(
        webhook_url,
        data=json.dumps({"content": contenu, "username": "GeckoCare Xena"}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "GeckoCare-Xena/1.0",
        },
        method="POST",
    )
    with urlrequest.urlopen(requete, timeout=10) as reponse:
        if reponse.status >= 400:
            raise URLError(f"Discord HTTP {reponse.status}")


def envoyer_message_discord_bot(reglages_app, contenu):
    token = reglages_app.get("discord_bot_token", "").strip()
    channel_id = reglages_app.get("discord_channel_id", "").strip()
    if not token or not channel_id:
        raise ValueError("Bot Discord non configure : renseigne le token du bot et l'ID du salon.")
    if not channel_id.isdigit():
        raise ValueError("ID du salon Discord invalide : active le mode developpeur Discord puis copie l'ID du salon.")

    requete = urlrequest.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=json.dumps({"content": contenu}).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "GeckoCare-Xena/1.0",
        },
        method="POST",
    )
    with urlrequest.urlopen(requete, timeout=10) as reponse:
        if reponse.status >= 400:
            raise URLError(f"Discord HTTP {reponse.status}")


def demarrer_scheduler_discord():
    global SCHEDULER_DISCORD_DEMARRE
    if SCHEDULER_DISCORD_DEMARRE:
        return
    # Un seul thread de notifications doit tourner, meme si Flask traite
    # plusieurs requetes pendant la session locale.
    SCHEDULER_DISCORD_DEMARRE = True
    thread = threading.Thread(target=boucle_scheduler_discord, daemon=True)
    thread.start()


def boucle_scheduler_discord():
    while True:
        try:
            executer_notifications_discord_automatiques()
        except Exception as erreur:
            print(f"[Discord] Notification automatique ignoree : {erreur}")
        time.sleep(60)


def executer_notifications_discord_automatiques():
    with connexion() as conn:
        reglages_app = charger_reglages(conn)
        if reglages_app.get("discord_auto_actif") != "1":
            return
        maintenant = datetime.now()
        nettoyer_anciennes_notifications_discord(conn, maintenant)
        if reglages_app.get("discord_resume_quotidien") == "1":
            envoyer_resume_quotidien_si_necessaire(conn, reglages_app, maintenant)
        if reglages_app.get("discord_temps_reel") == "1":
            envoyer_nouvelles_alertes_si_necessaire(conn, reglages_app, maintenant)


def envoyer_resume_quotidien_si_necessaire(conn, reglages_app, maintenant):
    heure_resume = heure_valide(reglages_app.get("discord_resume_heure"), "18:00")
    if maintenant.strftime("%H:%M") < heure_resume:
        return
    signature = f"resume-quotidien|{maintenant.date().isoformat()}"
    if alerte_discord_deja_envoyee(conn, signature):
        return
    envoyer_resume_alertes_discord(conn, reglages_app)
    memoriser_alerte_discord(conn, signature, "resume_quotidien", maintenant)
    memoriser_alertes_courantes_discord(conn, reglages_app, maintenant, "resume_quotidien")


def envoyer_nouvelles_alertes_si_necessaire(conn, reglages_app, maintenant):
    blocs_par_animal = alertes_discord_par_animal(conn, reglages_app)
    for animal_nom, blocs in blocs_par_animal.items():
        for type_alerte, alerte_item in blocs:
            signature = signature_alerte_discord(animal_nom, type_alerte, alerte_item)
            if alerte_discord_deja_envoyee(conn, signature):
                continue
            contenu = "\n".join(
                [
                    "**Nouvelle alerte GeckoCare**",
                    maintenant.strftime("%Y-%m-%d %H:%M"),
                    f"Animal : {animal_nom}",
                    f"Niveau : {alerte_item['niveau']}",
                    f"Type : {type_alerte}",
                    f"Source : {alerte_item['source']}",
                    alerte_item["message"],
                ]
            )
            envoyer_message_discord(reglages_app, contenu)
            memoriser_alerte_discord(conn, signature, "temps_reel", maintenant)


def memoriser_alertes_courantes_discord(conn, reglages_app, maintenant, type_envoi):
    for animal_nom, blocs in alertes_discord_par_animal(conn, reglages_app).items():
        for type_alerte, alerte_item in blocs:
            signature = signature_alerte_discord(animal_nom, type_alerte, alerte_item)
            memoriser_alerte_discord(conn, signature, type_envoi, maintenant)


def alerte_discord_deja_envoyee(conn, signature):
    return conn.execute(
        "SELECT 1 FROM discord_alertes_envoyees WHERE signature = ? LIMIT 1",
        (signature,),
    ).fetchone() is not None


def memoriser_alerte_discord(conn, signature, type_envoi, maintenant):
    conn.execute(
        """
        INSERT OR IGNORE INTO discord_alertes_envoyees (signature, type_envoi, date_envoi)
        VALUES (?, ?, ?)
        """,
        (signature, type_envoi, maintenant.strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()


def nettoyer_anciennes_notifications_discord(conn, maintenant):
    limite = (maintenant - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
    conn.execute(
        """
        DELETE FROM discord_alertes_envoyees
        WHERE date_envoi < ?
        AND type_envoi != 'resume_quotidien'
        """,
        (limite,),
    )
    conn.commit()


def url_webhook_discord_valide(url):
    url = (url or "").strip()
    domaines_valides = (
        "https://discord.com/api/webhooks/",
        "https://discordapp.com/api/webhooks/",
    )
    if not url.startswith(domaines_valides):
        return False
    reste = url.split("/api/webhooks/", 1)[1]
    morceaux = [morceau for morceau in reste.split("/") if morceau]
    return len(morceaux) >= 2


def message_erreur_discord_http(erreur):
    details = ""
    try:
        details = erreur.read().decode("utf-8", errors="replace").strip()
    except OSError:
        details = ""

    if erreur.code in {401, 403, 404}:
        return "Webhook Discord refuse ou introuvable. Supprime-le et recree un nouveau webhook."
    if erreur.code == 429:
        return "Discord limite temporairement les envois. Reessaie dans quelques minutes."
    if details:
        return f"Discord a refuse l'envoi : HTTP {erreur.code} - {details[:180]}"
    return f"Discord a refuse l'envoi : HTTP {erreur.code}."


def heure_valide(valeur, defaut):
    try:
        datetime.strptime(valeur or "", "%H:%M")
        return valeur
    except ValueError:
        return defaut


def heure_actuelle():
    return datetime.now().strftime("%H:%M")


def date_depuis_chaine(valeur):
    try:
        return datetime.strptime(valeur or "", "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def periode_observee_valide(valeur):
    return valeur if valeur in {"matin", "soir"} else "matin"


def minutes_depuis_minuit(heure):
    moment = datetime.strptime(heure, "%H:%M")
    return moment.hour * 60 + moment.minute


def periode_lumiere(heure, reglages):
    valeur = minutes_depuis_minuit(heure_valide(heure, "08:00"))
    allumage = minutes_depuis_minuit(reglages["heure_allumage"])
    extinction = minutes_depuis_minuit(reglages["heure_extinction"])
    if allumage < extinction:
        est_jour = allumage <= valeur < extinction
    else:
        est_jour = valeur >= allumage or valeur < extinction
    return "soir" if est_jour else "matin"


def duree_lumiere_heures(reglages):
    allumage = minutes_depuis_minuit(reglages["heure_allumage"])
    extinction = minutes_depuis_minuit(reglages["heure_extinction"])
    duree = extinction - allumage
    if duree <= 0:
        duree += 24 * 60
    return duree / 60


def dt_depuis(date_iso, heure_iso):
    return datetime.strptime(f"{date_iso} {heure_valide(heure_iso, '00:00')}", "%Y-%m-%d %H:%M")


def heures_depuis_ligne(ligne, champ_date, champ_heure, maintenant):
    return (maintenant - dt_depuis(ligne[champ_date], ligne[champ_heure])).total_seconds() / 3600


def heures_depuis_iso(date_heure_iso, maintenant):
    return (maintenant - datetime.strptime(date_heure_iso, "%Y-%m-%d %H:%M")).total_seconds() / 3600


def ids_materiel_utilises(conn, date_selectionnee, animal_id=None):
    materiels = materiel_utilise_pour_date(conn, date_selectionnee, animal_id)
    return {materiel["id"] for materiel in materiels}


def materiel_utilise_pour_date(conn, date_selectionnee, animal_id=None):
    explicites = conn.execute(
        """
        SELECT m.* FROM materiel_journalier mj
        JOIN materiel m ON m.id = mj.materiel_id
        WHERE mj.date_utilisation = ?
        AND (? IS NULL OR m.animal_id = ?)
        AND mj.utilise = 1
        ORDER BY m.type, m.nom
        """,
        (date_selectionnee, animal_id, animal_id),
    ).fetchall()
    if explicites:
        return explicites

    return conn.execute(
        """
        SELECT * FROM materiel
        WHERE (? IS NULL OR animal_id = ?)
        AND actif = 1
        AND statut != 'obsolete_casse'
        AND (date_debut IS NULL OR date_debut = '' OR date_debut <= ?)
        AND (date_fin IS NULL OR date_fin = '' OR date_fin >= ?)
        ORDER BY type, nom
        """,
        (animal_id, animal_id, date_selectionnee, date_selectionnee),
    ).fetchall()


def enregistrer_materiel_journalier(formulaire):
    date_utilisation = formulaire.get("date_utilisation") or date.today().isoformat()
    animal_id = entier_ou_none(formulaire.get("animal_id"))
    ids_selectionnes = {
        int(valeur) for valeur in formulaire.getlist("materiel_ids") if valeur.isdigit()
    }
    with connexion() as conn:
        materiels = conn.execute(
            "SELECT id, statut FROM materiel WHERE statut != 'obsolete_casse' AND animal_id = ?",
            (animal_id,),
        ).fetchall()
        for materiel in materiels:
            utilise = 1 if materiel["id"] in ids_selectionnes else 0
            conn.execute(
                """
                INSERT INTO materiel_journalier (date_utilisation, materiel_id, utilise)
                VALUES (?, ?, ?)
                ON CONFLICT(date_utilisation, materiel_id)
                DO UPDATE SET utilise = excluded.utilise
                """,
                (date_utilisation, materiel["id"], utilise),
            )
        conn.commit()


def construire_historique_jour(releves, repas, insectes, materiels, observations=None):
    historique = []
    for releve in releves:
        details = [
            f"{releve['temperature']} C",
            f"{releve['humidite']} %",
            "nuit ecoulee" if releve["moment"] == "matin" else "journee ecoulee",
            "brumisation" if releve["brumisation"] else "",
            "eau changee" if releve["eau_changee"] else "",
        ]
        historique.append(
            {
                "heure": releve["heure_releve"] or "--:--",
                "type": "Releve",
                "details": " - ".join([detail for detail in details if detail]),
            }
        )
    for ligne in repas:
        historique.append(
            {
                "heure": ligne["heure_repas"] or "--:--",
                "type": "Repas",
                "details": f"{ligne['aliment']} - {ligne['quantite'] or 'quantite non precisee'}",
            }
        )
    for action in insectes:
        actions = []
        if action["nourrissage"]:
            actions.append("nourrissage")
        if action["brumisation"]:
            actions.append("brumisation")
        historique.append(
            {
                "heure": action["heure_action"] or "--:--",
                "type": "Insectes",
                "details": f"{action['boite']} - {', '.join(actions) or 'note'}",
            }
        )
    for observation in observations or []:
        historique.append(
            {
                "heure": observation["heure_observation"] or "--:--",
                "type": f"Observation {observation['categorie']}",
                "details": f"{observation['niveau']} - {observation['description']}",
            }
        )
    for materiel in materiels:
        historique.append(
            {
                "heure": "journee",
                "type": "Materiel",
                "details": f"{materiel['nom']} ({materiel['type']})",
            }
        )
    return sorted(historique, key=lambda item: item["heure"])


def donnees_graphiques(conn, animal_id=None):
    depuis = (date.today() - timedelta(days=14)).isoformat()
    depuis_poids = (date.today() - timedelta(days=180)).isoformat()
    depuis_croissance = (date.today() - timedelta(days=365)).isoformat()
    debut_semaine = date.today() - timedelta(days=date.today().weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    animal = charger_animal(conn, animal_id)
    unite_poids_graphique = unite_poids_valide(animal.get("poids_unite") if animal else "g")
    releves = conn.execute(
        """
        SELECT date_releve, heure_releve, temperature, humidite, brumisation, eau_changee
        FROM releves
        WHERE animal_id = ?
        AND date_releve >= ?
        ORDER BY date_releve, heure_releve
        """,
        (animal_id, depuis),
    ).fetchall()
    repas_lignes = conn.execute(
        """
        SELECT date_repas, COUNT(*) AS total
        FROM repas
        WHERE animal_id = ?
        AND date_repas >= ?
        AND date_repas <= ?
        GROUP BY date_repas
        ORDER BY date_repas
        """,
        (animal_id, debut_semaine.isoformat(), fin_semaine.isoformat()),
    ).fetchall()
    poids_lignes = conn.execute(
        """
        SELECT date_mesure, poids, unite
        FROM poids_mesures
        WHERE animal_id = ?
        AND date_mesure >= ?
        ORDER BY date_mesure, created_at
        """,
        (animal_id, depuis_poids),
    ).fetchall()
    taille_lignes = conn.execute(
        """
        SELECT date_mesure, taille, unite
        FROM taille_mesures
        WHERE animal_id = ?
        AND date_mesure >= ?
        ORDER BY date_mesure, created_at
        """,
        (animal_id, depuis_croissance),
    ).fetchall()
    repas_par_jour = {ligne["date_repas"]: ligne["total"] for ligne in repas_lignes}
    repas = [
        {
            "label": (debut_semaine + timedelta(days=decalage)).strftime("%d/%m"),
            "valeur": repas_par_jour.get((debut_semaine + timedelta(days=decalage)).isoformat(), 0),
        }
        for decalage in range(7)
    ]
    insectes = conn.execute(
        """
        SELECT date_action,
               SUM(nourrissage) AS nourrissages,
               SUM(brumisation) AS brumisations
        FROM insectes_actions
        WHERE date_action >= ?
        GROUP BY date_action
        ORDER BY date_action
        """,
        (depuis,),
    ).fetchall()
    comptages_insectes = conn.execute(
        """
        SELECT c.date_comptage, b.nom AS boite, c.nombre_individus
        FROM insectes_comptages c
        JOIN insectes_boites b ON b.id = c.boite_id
        WHERE c.date_comptage >= ?
        ORDER BY c.date_comptage, c.created_at
        """,
        (depuis_croissance,),
    ).fetchall()
    return {
        "temperature": [
            {"label": f"{r['date_releve'][5:]} {r['heure_releve'] or ''}", "valeur": r["temperature"]}
            for r in releves
        ],
        "humidite": [
            {"label": f"{r['date_releve'][5:]} {r['heure_releve'] or ''}", "valeur": r["humidite"]}
            for r in releves
        ],
        "repas": repas,
        "poids": [
            {
                "label": ligne["date_mesure"][5:],
                "valeur": round(poids_dans_unite(ligne["poids"], ligne["unite"], unite_poids_graphique), 2),
            }
            for ligne in poids_lignes
            if poids_dans_unite(ligne["poids"], ligne["unite"], unite_poids_graphique) is not None
        ],
        "poids_unite": unite_poids_graphique,
        "taille": [
            {
                "label": ligne["date_mesure"][5:],
                "valeur": round(taille_dans_unite(ligne["taille"], ligne["unite"], "cm"), 2),
            }
            for ligne in taille_lignes
            if taille_dans_unite(ligne["taille"], ligne["unite"], "cm") is not None
        ],
        "taille_unite": "cm",
        "insectes": [
            {
                "label": r["date_action"][5:],
                "valeur": (r["nourrissages"] or 0) + (r["brumisations"] or 0),
            }
            for r in insectes
        ],
        "insectes_comptages": [
            {
                "label": f"{r['date_comptage'][5:]} {r['boite']}",
                "valeur": r["nombre_individus"],
            }
            for r in comptages_insectes
        ],
    }


def regrouper_alertes(alertes):
    poids = {"info": 0, "attention": 1, "danger": 2, "critique": 3}
    groupes = {}
    for item in alertes:
        cle = (item["source"], item["message"])
        actuel = groupes.get(cle)
        if actuel is None or poids[item["niveau"]] > poids[actuel["niveau"]]:
            groupes[cle] = {**item, "nombre": 1}
        else:
            actuel["nombre"] += 1
            if item["date"] > actuel["date"]:
                actuel["date"] = item["date"]
    return sorted(groupes.values(), key=lambda a: (-poids[a["niveau"]], a["source"], a["message"]))


def alerte(niveau, message, source, date_heure=None):
    return {
        "niveau": niveau,
        "message": message,
        "source": source,
        "date": date_heure or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def jours_depuis(date_iso, aujourd_hui):
    return (aujourd_hui - datetime.strptime(date_iso, "%Y-%m-%d").date()).days


if __name__ == "__main__":
    initialiser_base()
    demarrer_scheduler_discord()
    app.run(debug=True, use_reloader=False)
