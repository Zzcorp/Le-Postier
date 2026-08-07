/* ==========================================================================
   Ambiance aquatique — Collection Samathey
   --------------------------------------------------------------------------
   Script différé (defer). Trouve le conteneur .ambiance posé par
   templates/partials/ambiance.html et construit les couches sous-marines :
   fond, rayons de lumière, algues, vagues, poissons, bulles, particules.

   - Densité pilotée par data-ambiance : 'riche' | 'douce' | 'calme'.
   - Comptes réduits de moitié sous 768px, minimaux sous 480px.
   - prefers-reduced-motion : couches statiques uniquement, aucun mouvement.
   - Onglet masqué : classe .amb-pause (les animations CSS se figent).
   - Aucun émoji, aucune bibliothèque : SVG inline encodés en data URI.
   - Budget DOM : ~55 nœuds maximum toutes couches confondues (plafond : 70).
   ========================================================================== */
(function () {
    'use strict';

    var racine = document.querySelector('.ambiance');
    if (!racine || racine.dataset.ambInit === '1') {
        return; /* absent, ou déjà construit (le partial doit rester idempotent) */
    }
    racine.dataset.ambInit = '1';

    /* ---------------------------------------------------------------------
       Réglages
       --------------------------------------------------------------------- */
    var mode = racine.getAttribute('data-ambiance') || 'douce';
    var mouvementReduit = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var largeur = window.innerWidth || document.documentElement.clientWidth;

    /* Facteur de densité selon la taille d'écran. */
    var facteur = 1;
    if (largeur < 480) {
        facteur = 0.25; /* minimal sur très petits écrans */
    } else if (largeur < 768) {
        facteur = 0.5;  /* moitié sur tablettes / petits écrans */
    }

    /* Comptes de base par mode ('douce' = 'riche' moins ~30 %). */
    var comptes;
    if (mode === 'riche') {
        comptes = { rayons: 3, poissons: 5, bulles: 16, particules: 14, algues: 6 };
    } else if (mode === 'calme') {
        /* calme : vagues + algues + quelques bulles + lumière, pas de poisson */
        comptes = { rayons: 2, poissons: 0, bulles: 6, particules: 0, algues: 2 };
    } else {
        comptes = { rayons: 2, poissons: 3, bulles: 12, particules: 10, algues: 4 };
    }

    /* ---------------------------------------------------------------------
       Petits utilitaires
       --------------------------------------------------------------------- */
    function alea(min, max) {
        return min + Math.random() * (max - min);
    }

    function nb(base) {
        return Math.max(0, Math.round(base * facteur));
    }

    function couche(classe) {
        var d = document.createElement('div');
        d.className = classe;
        racine.appendChild(d);
        return d;
    }

    function element(classe, parent, styles) {
        var d = document.createElement('div');
        d.className = classe;
        for (var cle in styles) {
            if (cle.indexOf('--') === 0) {
                d.style.setProperty(cle, styles[cle]);
            } else {
                d.style[cle] = styles[cle];
            }
        }
        parent.appendChild(d);
        return d;
    }

    /* ---------------------------------------------------------------------
       Silhouettes SVG (data URI, aucune ressource externe)
       --------------------------------------------------------------------- */

    /* Poisson de rivière fuselé : corps effilé, nageoire dorsale discrète,
       queue fourchue. Teinte "verre d'eau" pâle : sur les fonds sombres du
       site, une ombre noire serait invisible — une silhouette légèrement
       lumineuse se lit comme un poisson en profondeur. */
    var SVG_POISSON = 'data:image/svg+xml,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 70">' +
        '<path fill="#9fc4b8" d="' +
        'M6 36 C24 18 62 9 104 10 C136 11 162 20 180 32 ' +
        'L208 14 C200 26 200 44 208 58 L180 40 ' +
        'C162 51 136 59 104 59 C62 60 24 52 6 36 Z ' +
        'M78 12 C88 1 104 0 116 8 L80 13 Z ' +
        'M118 57 C124 66 134 68 142 61 L120 56 Z' +
        '"/></svg>'
    );

    /* Nappe d'eau profonde : deux bosses symétriques, tangentes égales aux
       deux bords => la tuile se répète sans couture (repeat-x). */
    var SVG_VAGUE = 'data:image/svg+xml,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" preserveAspectRatio="none">' +
        '<path fill="#2a4a42" d="M0 64 C100 24 200 24 300 64 C400 104 500 104 600 64 L600 120 L0 120 Z"/>' +
        '</svg>'
    );

    /* Algue "ruban" : trois longues lanières de kelp effilées, enracinées au
       bas de la tuile, chacune montant à sa propre hauteur. Vert-sarcelle
       profond, même famille que la nappe d'eau. */
    var SVG_ALGUE_RUBAN = 'data:image/svg+xml,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 260">' +
        '<path fill="#2a4a42" d="' +
        'M18 260 C26 208 6 168 20 122 C30 88 14 52 26 8 ' +
        'C31 50 44 90 34 126 C22 168 40 210 30 260 Z ' +
        'M58 260 C50 200 72 160 60 112 C52 76 70 40 62 2 ' +
        'C74 44 58 80 70 116 C80 162 58 202 70 260 Z ' +
        'M96 260 C104 214 86 180 98 140 C106 112 92 84 102 48 ' +
        'C108 86 118 116 108 146 C98 182 112 218 104 260 Z' +
        '"/></svg>'
    );

    /* Algue "touffe" : buisson branchu plus trapu, cinq frondes rayonnant
       depuis le pied et tendues vers la surface. */
    var SVG_ALGUE_TOUFFE = 'data:image/svg+xml,' + encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 180">' +
        '<path fill="#264540" d="' +
        'M52 180 C44 140 34 110 24 78 C20 64 12 56 8 44 ' +
        'C22 60 34 88 44 116 C50 134 54 158 58 180 Z ' +
        'M64 180 C58 146 48 120 40 94 C36 82 28 72 26 60 ' +
        'C36 78 48 102 56 128 C60 146 62 162 64 180 Z ' +
        'M66 180 C64 130 70 90 68 44 C66 30 72 16 70 6 ' +
        'C76 40 74 90 76 132 C77 150 74 166 74 180 Z ' +
        'M76 180 C82 144 92 118 100 92 C104 80 112 70 114 58 ' +
        'C104 76 92 100 84 126 C80 144 78 162 76 180 Z ' +
        'M88 180 C96 140 106 110 116 78 C120 64 128 56 132 44 ' +
        'C118 60 106 88 96 116 C90 134 86 158 82 180 Z' +
        '"/></svg>'
    );

    /* ---------------------------------------------------------------------
       1. Fond — voile d'eau (purement statique, stylé en CSS)
       --------------------------------------------------------------------- */
    couche('amb-fond');

    /* ---------------------------------------------------------------------
       2. Rayons de lumière diagonaux
       --------------------------------------------------------------------- */
    var rayons = couche('amb-rayons');
    var nbRayons = Math.max(1, nb(comptes.rayons));
    for (var r = 0; r < nbRayons; r++) {
        element('amb-rayon', rayons, {
            left: alea(8 + r * 30, 22 + r * 30) + 'vw',
            width: alea(7, 15) + 'vw',
            opacity: alea(0.10, 0.18).toFixed(3),
            '--angle': alea(12, 22).toFixed(1) + 'deg',
            '--duree': alea(60, 90).toFixed(1) + 's'
        });
    }

    /* ---------------------------------------------------------------------
       3. Algues — touffes ancrées au bord bas, tendues vers la surface.
       Couche construite AVANT les vagues : dans l'ordre d'empilement, les
       nappes de houle passent devant les algues et les voilent légèrement
       (illusion de profondeur). Toujours construite, y compris en mouvement
       réduit : la classe d'ondulation amb-algue--onde n'est alors pas posée
       et les silhouettes restent statiques.
       --------------------------------------------------------------------- */
    var algues = couche('amb-algues');
    var nbAlgues = nb(comptes.algues);
    for (var a = 0; a < nbAlgues; a++) {
        var hauteurAlgue = alea(8, 20);                 /* hauteur en vh */
        var ruban = (a % 2 === 0);                      /* alternance stricte des deux silhouettes */
        var ratioAlgue = ruban ? (120 / 260) : (140 / 180);
        var dureeAlgue = alea(6, 12);
        var amplitude = alea(2, 5);                     /* inclinaison max en degrés */
        element(
            'amb-algue' + (mouvementReduit ? '' : ' amb-algue--onde'),
            algues,
            {
                /* un créneau par touffe + jitter : réparties sur toute la largeur */
                left: ((a + alea(0.12, 0.88)) * (100 / nbAlgues)).toFixed(1) + 'vw',
                height: hauteurAlgue.toFixed(1) + 'vh',
                width: (hauteurAlgue * ratioAlgue).toFixed(1) + 'vh',
                backgroundImage: 'url("' + (ruban ? SVG_ALGUE_RUBAN : SVG_ALGUE_TOUFFE) + '")',
                opacity: alea(0.10, 0.20).toFixed(3),
                /* petites touffes = plus lointaines = plus floues (3px -> 1px) */
                '--flou': (3 - (hauteurAlgue - 8) / 6).toFixed(1) + 'px',
                '--duree': dureeAlgue.toFixed(1) + 's',
                '--retard': (-alea(0, dureeAlgue)).toFixed(1) + 's',
                '--pencheA': (-amplitude).toFixed(2) + 'deg',
                '--pencheB': (amplitude * alea(0.55, 1)).toFixed(2) + 'deg',
                '--skewA': (-alea(1, 3)).toFixed(2) + 'deg',
                '--skewB': alea(1, 3).toFixed(2) + 'deg'
            }
        );
    }

    /* ---------------------------------------------------------------------
       4. Vagues de fond (deux nappes, sens opposés)
       --------------------------------------------------------------------- */
    var vagues = couche('amb-vagues');
    element('amb-vague amb-vague--arriere', vagues, {
        backgroundImage: 'url("' + SVG_VAGUE + '")'
    });
    element('amb-vague amb-vague--avant', vagues, {
        backgroundImage: 'url("' + SVG_VAGUE + '")'
    });

    /* ---------------------------------------------------------------------
       Couches animées — ignorées si l'utilisateur préfère moins de mouvement
       (le CSS immobilise de toute façon tout via prefers-reduced-motion).
       --------------------------------------------------------------------- */
    if (!mouvementReduit) {

        /* -----------------------------------------------------------------
           5. Poissons — de l'alevin (40 px) au grand poisson (200 px)
           Les plus proches sont grands, plus présents, plus nets et un peu
           plus vifs ; les plus lointains petits, pâles, flous et lents.
           Traversée : 40 à 95 s.
           ----------------------------------------------------------------- */
        var poissons = couche('amb-poissons');
        var nbPoissons = nb(comptes.poissons);
        for (var p = 0; p < nbPoissons; p++) {
            var taille = alea(40, 200);              /* largeur en px */
            var proche = (taille - 40) / 160;        /* 0 = lointain, 1 = proche */
            var duree = alea(60, 95) - proche * 20;  /* grands : 40-75 s, petits : 60-95 s */
            var versLaDroite = Math.random() < 0.5;
            element(
                'amb-poisson ' + (versLaDroite ? 'amb-poisson--droite' : 'amb-poisson--gauche'),
                poissons,
                {
                    top: alea(10, 68) + 'vh',
                    width: taille.toFixed(0) + 'px',
                    height: (taille * 70 / 220).toFixed(0) + 'px',
                    backgroundImage: 'url("' + SVG_POISSON + '")',
                    opacity: (0.12 + proche * 0.14).toFixed(3),
                    '--flou': (9 - proche * 5).toFixed(1) + 'px',
                    '--duree': duree.toFixed(1) + 's',
                    /* retard négatif : certains poissons sont déjà en traversée */
                    animationDelay: (-alea(0, duree)).toFixed(1) + 's'
                }
            );
        }

        /* -----------------------------------------------------------------
           6. Bulles — remontée pleine hauteur, ondulation sinusoïdale
           ----------------------------------------------------------------- */
        var bulles = couche('amb-bulles');
        var nbBulles = nb(comptes.bulles);
        for (var b = 0; b < nbBulles; b++) {
            var diametre = alea(4, 14);
            var dureeBulle = alea(16, 30);
            var ondulation = alea(1, 3.2).toFixed(2);
            element('amb-bulle', bulles, {
                left: alea(2, 96) + 'vw',
                width: diametre.toFixed(1) + 'px',
                height: diametre.toFixed(1) + 'px',
                '--op': alea(0.12, 0.22).toFixed(3),
                '--sx': ondulation + 'vw',
                '--sxn': '-' + ondulation + 'vw',
                '--duree': dureeBulle.toFixed(1) + 's',
                /* retard négatif : la colonne de bulles est peuplée dès l'arrivée */
                '--retard': (-alea(0, dureeBulle)).toFixed(1) + 's'
            });
        }

        /* -----------------------------------------------------------------
           7. Particules — poussières d'eau en dérive diagonale montante
           ----------------------------------------------------------------- */
        var particules = couche('amb-particules');
        var nbParticules = nb(comptes.particules);
        for (var m = 0; m < nbParticules; m++) {
            var grain = alea(1, 3);
            var dureeGrain = alea(40, 75);
            element('amb-particule', particules, {
                left: alea(0, 96) + 'vw',
                top: alea(15, 98) + 'vh',
                width: grain.toFixed(1) + 'px',
                height: grain.toFixed(1) + 'px',
                '--op': alea(0.09, 0.16).toFixed(3),
                '--dx': alea(3, 8).toFixed(1) + 'vw',
                '--duree': dureeGrain.toFixed(1) + 's',
                '--retard': (-alea(0, dureeGrain)).toFixed(1) + 's'
            });
        }
    }

    /* ---------------------------------------------------------------------
       Pause quand l'onglet est masqué — économie de batterie et de GPU.
       --------------------------------------------------------------------- */
    document.addEventListener('visibilitychange', function () {
        racine.classList.toggle('amb-pause', document.hidden);
    });
})();
