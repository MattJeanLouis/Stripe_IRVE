# 1. Introduction

## Objectif du projet

Le projet d'Intégration Stripe pour IRVE (Infrastructure de Recharge de Véhicules Électriques) vise à mettre en place un système de paiement robuste et flexible pour les bornes de recharge de véhicules électriques. L'objectif principal est de fournir une solution de paiement sécurisée et facile à utiliser pour les utilisateurs de véhicules électriques, tout en offrant une gestion efficace des transactions pour les opérateurs de bornes de recharge.

Les principaux objectifs du projet sont :

1. Intégrer Stripe comme solution de paiement principale.
2. Offrir plusieurs options de paiement : fixe, estimé et dynamique.
3. Une expérience utilisateur fluide et intuitive.
4. Garantir la sécurité des transactions.
5. Fournir une solution facilement déployable et maintenable.

## Technologies utilisées

1. **Backend** :
    - FastAPI
    - Uvicorn
    - Python 3.11
2. **Frontend** :
    - HTML5
    - Tailwind CSS
    - JavaScript
3. **Paiement** :
    - Stripe API : Pour gérer les transactions de paiement de manière sécurisée.
    - Stripe CLI : Pour le développement local et les tests des webhooks.
4. **Conteneurisation et déploiement** :
    - Docker
    - Docker Compose
5. **Autres outils et bibliothèques** :
    - python-dotenv
    - Jinja2 : Comme moteur de template pour générer du HTML dynamiquement.
    - aiohttp : Une bibliothèque HTTP asynchrone pour Python, utilisée pour les requêtes HTTP asynchrones.

# 2. Architecture du Projet

## Structure des fichiers

Le projet est organisé selon la structure suivante :

```
.
├── app/
│   ├── templates/
│   │   ├── index.html
│   │   ├── success.html
│   │   ├── cancel.html
│   │   └── charging.html
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── test_fixed_payment.py
│   ├── test_estimated_payment.py
│   └── test_dynamic_payment.py
├── .env
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── start.sh

```

## Composants principaux

### Backend (FastAPI)

Le cœur de l'application est le fichier `main.py`, qui contient toute la logique de l'API FastAPI. Voici les principales sections :

- L'application FastAPI est initialisée, le logging est configuré, et les variables d'environnement sont chargées au début du fichier.
- Le modèle de données pour les requêtes de paiement est défini pour structurer les informations nécessaires aux transactions.
- Une route est définie pour gérer l'affichage de la page d'accueil, permettant aux utilisateurs d'accéder à l'interface de base.
- Une autre route gère la création des sessions de paiement, permettant de traiter les paiements de différents types (fixe, estimé, dynamique).
- Enfin, une fonction asynchrone est mise en place pour notifier le CSMS (Charging Station Management System) des différents événements liés aux stations de recharge.

### Frontend (Templates HTML)

Les templates HTML se trouvent dans le dossier `app/templates/`. Ils utilisent Tailwind CSS pour le style et incluent du JavaScript pour la gestion des interactions côté client.

- `index.html` : Page d'accueil avec les options de paiement.
- `success.html` : Page de confirmation après un paiement réussi.
- `cancel.html` : Page affichée en cas d'annulation du paiement.
- `charging.html` : Page de suivi pour les paiements dynamiques.

### Tests

Trois fichiers de test sont inclus pour vérifier le bon fonctionnement des différents scénarios de paiement :

1. `test_fixed_payment.py` : Teste le scénario de paiement fixe.
2. `test_estimated_payment.py` : Teste le scénario de paiement estimé.
3. `test_dynamic_payment.py` : Teste le scénario de paiement dynamique.

Ces tests utilisent la bibliothèque `requests` pour envoyer des requêtes HTTP à l'API et vérifier les réponses.

### Configuration Docker

Le projet utilise Docker pour la conteneurisation, avec les fichiers suivants :

- `Dockerfile` : Définit l'image Docker pour l'application.
- `docker-compose.yml` : Configure les services Docker, y compris l'application web et les ports exposés.
- `start.sh` : Script de démarrage qui initialise le listener Stripe et lance l'application FastAPI.

### Dépendances

Les dépendances du projet sont listées dans le fichier `requirements.txt`

# 3. Configuration

## Variables d'environnement

Le projet utilise des variables d'environnement pour gérer les configurations sensibles. Ces variables sont stockées dans un fichier .env.

Voici les principales variables d'environnement utilisées :

- [STRIPE_SECRET_KEY] Clé secrète Stripe pour l'authentification côté serveur.
- [STRIPE_PUBLIC_KEY] Clé publique Stripe utilisée côté client.
- [STRIPE_WEBHOOK_SECRET] Clé secrète pour vérifier les signatures des webhooks Stripe.
- [BASE_URL] URL de base de l'application.
- [CSMS_NOTIFICATION_URL] URL pour notifier le système de gestion des bornes de recharge (CSMS).

Ces variables sont chargées dans l'application à l'aide de la bibliothèque python-dotenv

## Configuration de Stripe

La configuration de Stripe est effectuée dans le fichier principal de l'application. Les clés API sont récupérées à partir des variables d'environnement :

```
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
public_key = os.getenv("STRIPE_PUBLIC_KEY")
base_url = os.getenv("BASE_URL")
```

### Webhook Stripe

Le webhook Stripe est configuré pour recevoir des événements de paiement. La route pour le webhook est définie comme suit :

```
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await notify_csms("session_completed", {
            "session_id": session["id"],
            "client_id": session["client_reference_id"],
            "setup_intent_id": session["setup_intent"]
        })
    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        await notify_csms("payment_succeeded", {
            "payment_intent_id": payment_intent["id"],
            "amount": payment_intent["amount"],
            "client_id": payment_intent["customer"]
        })

```

Le script start.sh configure automatiquement le webhook Stripe lors du démarrage de l'application.

## Tests

Trois fichiers de test sont inclus pour vérifier le bon fonctionnement des différents scénarios de paiement :

### Test de paiement fixe

Le fichier test_fixed_payment.py teste le scénario de paiement fixe. Il envoie une requête à l'API avec un montant prédéfini et vérifie la réponse.

### Test de paiement estimé

Le fichier test_estimated_payment.py teste le scénario de paiement estimé. Il envoie une requête à l'API sans montant spécifié et vérifie la réponse.

### Test de paiement dynamique

Le fichier test_dynamic_payment.py teste le scénario de paiement dynamique. Il simule le début d'une session de charge, attend un certain temps, puis termine la session avec un montant final.

## Docker

Le projet utilise Docker pour la conteneurisation. Le `Dockerfile` définit l'environnement de l'application :

Le fichier docker-compose.yml configure les services Docker, y compris l'application web et les ports exposés.

## Logging

La configuration du logging est effectuée dans le fichier principal de l'application. Les logs sont écrits dans un fichier app.log avec rotation :

```
# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajout d'un handler pour écrire les logs dans un fichier
file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

logger.info('Application de paiement démarrée')
```

# 4. Scénarios de Paiement

Le projet IRVE intègre trois scénarios de paiement principaux pour répondre aux différents besoins des utilisateurs et des opérateurs de bornes de recharge. Chaque scénario est conçu pour offrir une flexibilité maximale tout en assurant une expérience utilisateur fluide.

## Paiement fixe

Le scénario de paiement fixe permet aux utilisateurs de payer un montant prédéfini pour leur recharge.

### Fonctionnement :

1. L'utilisateur sélectionne l'option "Entrer un montant fixe" sur la page d'accueil.
2. Il entre le montant souhaité.
3. Une session Stripe est créée avec ce montant.
4. L'utilisateur est redirigé vers la page de paiement Stripe.
5. Après le paiement, l'utilisateur est redirigé vers la page de succès.

### Implémentation :

Le paiement fixe est géré dans la fonction create_payment du fichier main.py :

## Paiement estimé

Le paiement estimé offre une estimation du coût de la recharge basée sur une durée ou une quantité d'énergie prédéfinie.

### Fonctionnement :

1. L'utilisateur choisit l'option "Paiement estimé par le système" sur la page d'accueil.
2. Le système calcule un montant estimé (dans cet exemple, fixé à 10 euros).
3. Une session Stripe est créée avec ce montant estimé.
4. L'utilisateur procède au paiement via Stripe.
5. Après le paiement, l'utilisateur est redirigé vers la page de succès.

### Implémentation :

Le paiement estimé est également géré dans la fonction create_payment du fichier main.py :

## Paiement dynamique

Le paiement dynamique permet de facturer l'utilisateur en fonction de la quantité réelle d'énergie consommée.

### Fonctionnement :

1. L'utilisateur sélectionne "Paiement selon la charge réelle" sur la page d'accueil.
2. Une session Stripe en mode "setup" est créée pour autoriser les paiements futurs.
3. L'utilisateur est redirigé vers une page de charge en cours.
4. À la fin de la charge, le montant final est calculé et le paiement est effectué.
5. L'utilisateur est redirigé vers la page de succès avec les détails du paiement.

### Implémentation :

Le paiement dynamique implique plusieurs étapes et fonctions :

1. Création de la session initiale :

```
@app.post("/api/create-payment")
async def create_payment(payment: PaymentRequest):
        logger.info(f"Session de paiement créée avec succès: {session.id}")
        ...
        return {"session_id": session.id, "url": session.url}
    except ValueError as ve:
        logger.error(f"Erreur de validation: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except stripe.error.StripeError as se:
        logger.error(f"Erreur Stripe: {str(se)}")
        raise HTTPException(status_code=500, detail=f"Erreur Stripe : {str(se)}")
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)}")

```

1. Gestion de la charge en cours :

```
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Charge en cours - IRVE</title>
    <link href="<https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css>" rel="stylesheet">
</head>
<body class="bg-gray-100 h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
        <h1 class="text-2xl font-bold mb-6 text-blue-600">Charge en cours</h1>
        <p class="text-gray-600 mb-4">Votre session de charge a commencé. Le paiement sera effectué à la fin de la charge.</p>
        <div class="mb-4">
            <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                <div id="progress-bar" class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div>
            </div>
        </div>
        <p id="charge-status" class="text-lg font-semibold text-gray-700 mb-4">0% chargé</p>
        <p class="text-sm text-gray-500 mb-4">Session ID: <span id="sessionId">{{ session_id }}</span></p>

```

1. Finalisation de la charge et du paiement :

```
@app.get("/finish-dynamic-charge/{session_id}")
async def finish_dynamic_charge(session_id: str):
    except stripe.error.CardError as e:
    ...
        error_msg = f"Erreur de carte : {e.error.message}"
        logger.error(f"Erreur de carte lors de la finalisation de la charge : {error_msg}")
        await notify_csms("charge_failed", {"session_id": session_id, "error": error_msg})
        raise HTTPException(status_code=400, detail=error_msg)
    except stripe.error.StripeError as e:
        error_msg = f"Erreur Stripe : {str(e)}"
        logger.error(f"Erreur Stripe lors de la finalisation de la charge : {error_msg}")
        await notify_csms("charge_failed", {"session_id": session_id, "error": error_msg})
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Erreur interne du serveur : {str(e)}"
        logger.error(f"Erreur inattendue lors de la finalisation de la charge : {error_msg}", exc_info=True)
        await notify_csms("charge_failed", {"session_id": session_id, "error": error_msg})
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        logger.info(f"Fin du traitement de la finalisation de la charge pour la session : {session_id}")

```

## Gestion des webhooks

Pour tous les scénarios de paiement, les webhooks Stripe sont utilisés pour gérer les événements de paiement et notifier le système de gestion des bornes de recharge (CSMS).

### Implémentation :

```
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await notify_csms("session_completed", {
            "session_id": session["id"],
            "client_id": session["client_reference_id"],
            "setup_intent_id": session["setup_intent"]
        })
    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        await notify_csms("payment_succeeded", {
            "payment_intent_id": payment_intent["id"],
            "amount": payment_intent["amount"],
            "client_id": payment_intent["customer"]
        })

    return {"success": True}

```

# 5. Logique de l'Application

## Création de session de paiement

La création de session de paiement est gérée par la fonction create_payment dans le fichier `main.py`. Cette fonction traite les trois types de paiement : fixe, estimé et dynamique.

### Processus de création de session :

1. Réception de la requête de paiement
2. Validation du type de paiement
3. Calcul du montant selon le type de paiement
4. Création de la session Stripe
5. Retour de l'ID de session et de l'URL de paiement

## Gestion des webhooks Stripe

Les webhooks Stripe sont gérés par la route /webhook dans `main.py`. Cette fonction traite les événements envoyés par Stripe, notamment :

- `checkout.session.completed` : Lorsqu'une session de paiement est complétée
- `payment_intent.succeeded` : Lorsqu'un paiement est réussi

Pour chaque événement, une notification est envoyée au CSMS (Charging Station Management System).

## Processus de charge dynamique

Le processus de charge dynamique est plus complexe et implique plusieurs étapes :

### Démarrage de la session de charge

La fonction start_charging_session gère le début d'une session de charge dynamique :

1. Création d'une méthode de paiement à partir du token fourni
2. Attachement de la méthode de paiement au client
3. Création d'un SetupIntent Stripe

### Suivi de la charge

Le suivi de la charge est géré côté client dans le fichier `charging.html`. Un script JavaScript simule la progression de la charge et permet à l'utilisateur de terminer la charge quand il le souhaite.

### Finalisation de la charge

La finalisation de la charge est gérée par deux fonctions :

1. finish_dynamic_charge : Appelée lorsque l'utilisateur termine la charge manuellement
2. end_charging_session : Appelée par l'API pour finaliser le paiement

Ces fonctions effectuent les actions suivantes :

- Récupération des informations de la session
- Création et confirmation d'un PaymentIntent Stripe
- Notification au CSMS de la fin de la charge

## Gestion des erreurs

La gestion des erreurs est intégrée à chaque étape du processus de paiement. Les erreurs sont capturées, enregistrées dans les logs, et des réponses HTTP appropriées sont renvoyées au client.

## Notification au CSMS

La fonction notify_csms est utilisée pour envoyer des notifications au système de gestion des bornes de recharge (CSMS) à différentes étapes du processus de paiement. Cette fonction utilise des requêtes HTTP asynchrones pour communiquer avec le CSMS.

# 6. Interfaces Utilisateur

L'interface utilisateur de l'application IRVE est simple et réactive Les interfaces sont développées en utilisant HTML et JavaScript, avec Tailwind CSS pour le style.

## Page d'accueil

La page d'accueil index.html est le point d'entrée principal de l'application. Elle présente aux utilisateurs les différentes options de paiement disponibles.

### Caractéristiques principales :

- Design épuré utilisant Tailwind CSS
- Trois options de paiement clairement présentées :
    1. Paiement estimé par le système
    2. Entrer un montant fixe
    3. Paiement selon la charge réelle
- Formulaire dynamique qui s'adapte en fonction de l'option choisie
- Intégration de Stripe.js pour la gestion sécurisée des paiements

### Fonctionnalité :

Lorsqu'un utilisateur sélectionne une option de paiement, un script JavaScript met à jour dynamiquement le formulaire. Pour l'option de montant fixe, un champ de saisie supplémentaire apparaît, permettant à l'utilisateur d'entrer le montant souhaité.

## Page de charge en cours

La page de charge en cours charging.html est affichée lors d'un paiement dynamique, permettant à l'utilisateur de suivre la progression de la charge.

### Fonctionnalité :

Un script JavaScript simule la progression de la charge, mettant à jour la barre de progression et le pourcentage affiché toutes les secondes. Une fois la charge terminée (simulée à 100%), un bouton apparaît permettant à l'utilisateur de finaliser la transaction.

## Page de succès

La page success.html est affichée après un paiement réussi, qu'il soit fixe, estimé ou dynamique.

### Caractéristiques principales :

- Message de confirmation clair
- Affichage des détails de la transaction :
    - Montant payé
    - Type de paiement
    - ID de transaction
- Bouton pour retourner à la page d'accueil

### Fonctionnalité :

Cette page est générée dynamiquement côté serveur, injectant les détails spécifiques de la transaction dans le template HTML avant de l'envoyer au client.

## Page d'annulation

La page d'annulation cancel.html est une page simple affichée si l'utilisateur annule le processus de paiement.

### Caractéristiques principales :

- Message indiquant que le paiement a été annulé
- Suggestion de réessayer

# 7. API Backend

L'API backend de l'application IRVE est construite avec FastAPI.

## Routes principales

### Page d'accueil

**Route** : GET "/"

Cette route affiche la page d'accueil de l'application, présentant les différentes options de paiement aux utilisateurs.

### Création de paiement

**Route** : POST "/api/create-payment"

Cette route gère la création des sessions de paiement pour les trois types de paiement (fixe, estimé, dynamique). Elle accepte un objet PaymentRequest et retourne les détails de la session Stripe créée.

### Démarrage de session de charge

**Route** : POST "/api/start-charging-session"

Cette route est utilisée pour démarrer une session de charge dynamique. Elle crée un SetupIntent Stripe et prépare la session pour un paiement futur.

### Fin de session de charge

**Route** : POST "/api/end-charging-session"

Cette route finalise une session de charge dynamique, calculant le montant final et effectuant le paiement.

### Webhook Stripe

**Route** : POST "/webhook"

Cette route gère les événements webhook envoyés par Stripe, traitant notamment les paiements réussis et les sessions complétées.

## Gestion des requêtes

### Validation des données

L'API utilise Pydantic pour la validation des données entrantes. Le modèle PaymentRequest définit la structure attendue pour les requêtes de paiement.

### Gestion des erreurs

L'API implémente une gestion d'erreurs, capturant et loggant les exceptions, et renvoyant des réponses HTTP appropriées avec des messages d'erreur détaillés.

### Logging

Un système de logging est mis en place pour enregistrer les événements importants, les erreurs et les informations de débogage, facilitant le suivi et la résolution des problèmes.

## Intégration avec Stripe

L'API interagit directement avec l'API Stripe pour :

- Créer des sessions de paiement
- Gérer les SetupIntents pour les paiements dynamiques
- Créer et confirmer des PaymentIntents
- Traiter les webhooks Stripe

## Communication avec le CSMS

L'API inclut une fonction notify_csms qui envoie des notifications asynchrones au système de gestion des bornes de recharge (CSMS) pour différents événements comme le début et la fin des sessions de charge, les paiements réussis, etc.