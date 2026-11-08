const THEME_STORAGE_KEY = "geckocare-theme";

// Fonctionnalite ajoutee le 2026-07-26 : le profil animal est choisi une fois
// dans cette barre puis conserve par l'application sur toutes les pages.
async function ajouterSelecteurAnimal() {
    const navigation = document.querySelector(".navigation");
    if (!navigation) return;
    let donnees;
    try {
        const reponse = await fetch("/profil-actif/donnees");
        donnees = await reponse.json();
    } catch (erreur) {
        return;
    }
    const animaux = donnees.animaux || [];
    const actif = animaux.find((animal) => animal.id === donnees.animal_actif_id);
    if (actif && actif.profil === "chat") {
        ["Releves", "Insectes", "Boites", "Plantes"].forEach((libelle) => {
            [...navigation.querySelectorAll("a")].filter((lien) => lien.textContent.trim() === libelle).forEach((lien) => lien.remove());
        });
        if (![...navigation.querySelectorAll("a")].some((lien) => lien.textContent.trim() === "Sante")) {
            const lienSante = document.createElement("a");
            lienSante.href = "/sante";
            lienSante.textContent = "Sante";
            navigation.append(lienSante);
        }
        document.querySelectorAll(".gecko-only").forEach((element) => element.remove());
        const titresGecko = ["Dernier bilan de nuit", "Dernier bilan de journee", "Mesure recente", "Temperature", "Humidite", "Actions insectes", "Nombre d'insectes", "Statut des insectes"];
        document.querySelectorAll(".carte, article").forEach((element) => {
            const titre = element.querySelector("h3");
            if (titre && titresGecko.includes(titre.textContent.trim())) element.remove();
        });
    }
}

function appliquerTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
}

function themeInitial() {
    const themeSauvegarde = localStorage.getItem(THEME_STORAGE_KEY);
    if (themeSauvegarde) {
        return themeSauvegarde;
    }

    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "sombre" : "clair";
}

function ajouterBoutonTheme() {
    const navigation = document.querySelector(".navigation");
    if (!navigation) {
        return;
    }

    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = "theme-toggle";
    bouton.setAttribute("aria-label", "Changer le theme clair ou sombre");

    function rafraichirLibelle() {
        const theme = document.documentElement.dataset.theme || "clair";
        bouton.textContent = theme === "sombre" ? "Mode clair" : "Mode sombre";
    }

    bouton.addEventListener("click", () => {
        const themeActuel = document.documentElement.dataset.theme || "clair";
        appliquerTheme(themeActuel === "sombre" ? "clair" : "sombre");
        rafraichirLibelle();
    });

    navigation.appendChild(bouton);
    rafraichirLibelle();
}

function definirHeureCourante() {
    const maintenant = new Date();
    const heure = String(maintenant.getHours()).padStart(2, "0");
    const minute = String(maintenant.getMinutes()).padStart(2, "0");
    document.querySelectorAll('input[type="time"][required]').forEach((champ) => {
        if (!champ.value) {
            champ.value = `${heure}:${minute}`;
        }
    });
}

function dessinerGraphique(canvas) {
    const donnees = JSON.parse(canvas.dataset.chart || "[]");
    const contexte = canvas.getContext("2d");
    const ratio = window.devicePixelRatio || 1;
    const largeur = canvas.clientWidth || 320;
    const hauteur = 190;
    canvas.width = largeur * ratio;
    canvas.height = hauteur * ratio;
    contexte.setTransform(ratio, 0, 0, ratio, 0, 0);
    contexte.clearRect(0, 0, largeur, hauteur);

    contexte.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--color-muted");
    contexte.font = "12px Arial";

    if (!donnees.length) {
        contexte.fillText("Pas assez de donnees", 18, 92);
        return;
    }

    const marge = { haut: 18, droite: 16, bas: 34, gauche: 36 };
    const valeurs = donnees.map((point) => Number(point.valeur));
    const min = Math.min(...valeurs);
    const max = Math.max(...valeurs);
    const amplitude = max - min || 1;
    const couleur = canvas.dataset.color || "#4f7f52";

    contexte.strokeStyle = "rgba(111, 127, 104, 0.35)";
    contexte.lineWidth = 1;
    for (let i = 0; i < 4; i += 1) {
        const y = marge.haut + ((hauteur - marge.haut - marge.bas) / 3) * i;
        contexte.beginPath();
        contexte.moveTo(marge.gauche, y);
        contexte.lineTo(largeur - marge.droite, y);
        contexte.stroke();
    }

    function x(index) {
        if (donnees.length === 1) {
            return marge.gauche;
        }
        return marge.gauche + ((largeur - marge.gauche - marge.droite) * index) / (donnees.length - 1);
    }

    function y(valeur) {
        return hauteur - marge.bas - ((valeur - min) / amplitude) * (hauteur - marge.haut - marge.bas);
    }

    contexte.strokeStyle = couleur;
    contexte.lineWidth = 2.5;
    contexte.beginPath();
    donnees.forEach((point, index) => {
        const px = x(index);
        const py = y(Number(point.valeur));
        if (index === 0) {
            contexte.moveTo(px, py);
        } else {
            contexte.lineTo(px, py);
        }
    });
    contexte.stroke();

    contexte.fillStyle = couleur;
    donnees.forEach((point, index) => {
        contexte.beginPath();
        contexte.arc(x(index), y(Number(point.valeur)), 3, 0, Math.PI * 2);
        contexte.fill();
    });

    contexte.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--color-muted");
    contexte.fillText(String(max), 6, marge.haut + 4);
    contexte.fillText(String(min), 6, hauteur - marge.bas + 4);
    contexte.fillText(donnees[0].label, marge.gauche, hauteur - 10);
    contexte.textAlign = "right";
    contexte.fillText(donnees[donnees.length - 1].label, largeur - marge.droite, hauteur - 10);
    contexte.textAlign = "left";
}

function initialiserGraphiques() {
    const graphiques = document.querySelectorAll(".graphique");
    graphiques.forEach(dessinerGraphique);
    if (graphiques.length) {
        window.addEventListener("resize", () => graphiques.forEach(dessinerGraphique));
    }
}

appliquerTheme(themeInitial());
document.addEventListener("DOMContentLoaded", () => {
    ajouterSelecteurAnimal();
    ajouterBoutonTheme();
    definirHeureCourante();
    initialiserGraphiques();
});
