from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import stripe
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import aiohttp
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajout d'un handler pour écrire les logs dans un fichier
file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

logger.info('Application de paiement démarrée')

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
public_key = os.getenv("STRIPE_PUBLIC_KEY")
base_url = os.getenv("BASE_URL")

class PaymentRequest(BaseModel):
    paymentType: str
    montant: Optional[float] = None
    devise: str = "eur"
    id_client: str
    description: str

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "public_key": public_key})

@app.post("/api/create-payment")
async def create_payment(payment: PaymentRequest):
    logger.info(f"Nouvelle demande de paiement reçue: {payment.dict()}")
    try:
        if payment.paymentType == "estimated":
            montant = 1000
            logger.info(f"Paiement estimé: montant fixé à {montant} centimes")
        elif payment.paymentType == "fixed":
            if not payment.montant:
                logger.error("Montant manquant pour le paiement fixe")
                raise ValueError("Montant requis pour le paiement fixe")
            montant = int(payment.montant * 100)
            logger.info(f"Paiement fixe: montant de {montant} centimes")
        elif payment.paymentType == "dynamic":
            montant = 5000
            logger.info(f"Paiement dynamique: montant maximum fixé à {montant} centimes")
        else:
            logger.error(f"Type de paiement non valide: {payment.paymentType}")
            raise ValueError("Type de paiement non valide")

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': payment.devise,
                    'product_data': {
                        'name': payment.description,
                    },
                    'unit_amount': montant,
                },
                'quantity': 1,
            }],
            mode='payment' if payment.paymentType != "dynamic" else 'setup',
            success_url=f'{base_url}/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{base_url}/cancel',
            client_reference_id=payment.id_client,
            metadata={"payment_type": payment.paymentType},
        )
        logger.info(f"Session de paiement créée avec succès: {session.id}")
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

async def notify_csms(event_type: str, data: dict):
    logger.info(f"Début de la notification CSMS - Type d'événement : {event_type}")
    csms_url = os.getenv("CSMS_NOTIFICATION_URL")
    if not csms_url:
        logger.error("URL de notification CSMS non définie dans les variables d'environnement")
        return

    try:
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Envoi de la requête POST au CSMS : {csms_url}")
            logger.debug(f"Données envoyées : {data}")
            async with session.post(csms_url, json={
                "event_type": event_type,
                "data": data
            }) as response:
                if response.status == 200:
                    logger.info(f"Notification CSMS réussie - Type d'événement : {event_type}")
                    logger.debug(f"Réponse du CSMS : {await response.text()}")
                else:
                    logger.warning(f"Le CSMS a répondu avec un statut non-200 : {response.status}")
                    logger.debug(f"Contenu de la réponse : {await response.text()}")
                    raise Exception(f"CSMS a répondu avec le statut {response.status}")
    except aiohttp.ClientError as ce:
        logger.error(f"Erreur de connexion au CSMS : {ce}")
        logger.exception("Détails de l'erreur de connexion :")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la notification du CSMS : {e}")
        logger.exception("Détails de l'erreur inattendue :")
    finally:
        logger.info(f"Fin de la tentative de notification CSMS - Type d'événement : {event_type}")

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

#Endpoint factice pour simuler le csms
@app.post("/csms-notification")
async def csms_notification(request: Request):
    data = await request.json()
    print(f"CSMS Notification reçue : {data}")
    return {"status": "success"}

@app.get("/success")
async def success(request: Request, session_id: str):
    session = stripe.checkout.Session.retrieve(session_id)
    payment_type = session.metadata.get("payment_type", "N/A")
    amount = session.amount_total / 100  # Convertir les centimes en euros
    
    if payment_type == "dynamic":
        return templates.TemplateResponse("charging.html", {
            "request": request, 
            "session_id": session_id
        })
    
    # Notifier le CSMS pour les paiements réussis non dynamiques
    await notify_csms("payment_succeeded", {
        "session_id": session_id,
        "amount": amount,
        "payment_type": payment_type,
        "client_id": session.client_reference_id
    })
    
    return templates.TemplateResponse("success.html", {
        "request": request,
        "amount": amount,
        "payment_type": payment_type,
        "transaction_id": session_id
    })

@app.get("/cancel")
async def cancel(request: Request):
    return templates.TemplateResponse("cancel.html", {"request": request})

@app.get("/finish-dynamic-charge/{session_id}")
async def finish_dynamic_charge(session_id: str):
    logger.info(f"Début de la finalisation de la charge dynamique pour la session : {session_id}")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Session Stripe récupérée : {session.id}")
        setup_intent = stripe.SetupIntent.retrieve(session.setup_intent)
        logger.info(f"SetupIntent récupéré : {setup_intent.id}")

        final_amount = 1500  # 15.00 EUR
        logger.info(f"Montant final calculé : {final_amount / 100} EUR")

        payment_intent = stripe.PaymentIntent.create(
            amount=final_amount,
            currency='eur',
            customer=setup_intent.metadata.get('client_id'),
            payment_method=setup_intent.payment_method,
            off_session=True,
            confirm=True,
        )
        logger.info(f"PaymentIntent créé et confirmé : {payment_intent.id}")

        await notify_csms("charge_completed", {
            "session_id": session_id,
            "payment_intent_id": payment_intent.id,
            "amount_paid": final_amount / 100,
            "client_id": setup_intent.metadata.get('client_id')
        })
        logger.info(f"Notification CSMS envoyée pour la charge complétée : {session_id}")

        return {
            "status": "success", 
            "amount_paid": final_amount / 100,
            "payment_intent_id": payment_intent.id
        }
    except stripe.error.CardError as e:
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
    
@app.post("/api/start-charging-session")
async def start_charging_session(request: Request):
    data = await request.json()
    client_id = data.get("client_id")
    payment_token = data.get("payment_token")

    try:
        # Créer une méthode de paiement à partir du token
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={"token": payment_token},
        )

        # Attacher la méthode de paiement au client
        stripe.PaymentMethod.attach(
            payment_method.id,
            customer=client_id,
        )

        # Créer un SetupIntent
        setup_intent = stripe.SetupIntent.create(
            customer=client_id,
            payment_method=payment_method.id,
            metadata={
                'client_id': client_id,
            }
        )

        return {"setup_intent_id": setup_intent.id, "client_secret": setup_intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/end-charging-session")
async def end_charging_session(request: Request):
    data = await request.json()
    setup_intent_id = data.get("setup_intent_id")
    final_amount = data.get("final_amount")

    try:
        setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
        
        # Créer et confirmer le PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=final_amount,
            currency='eur',
            customer=setup_intent.metadata.get('client_id'),
            payment_method=setup_intent.payment_method,
            off_session=True,
            confirm=True,
        )

        # Notifier le CSMS
        await notify_csms("charge_completed", {
            "setup_intent_id": setup_intent_id,
            "payment_intent_id": payment_intent.id,
            "amount_paid": final_amount / 100,
            "client_id": setup_intent.metadata.get('client_id')
        })

        return {"status": "success", "payment_intent_id": payment_intent.id}
    except stripe.error.StripeError as e:
        await notify_csms("charge_failed", {
            "setup_intent_id": setup_intent_id,
            "error": str(e)
        })
        raise HTTPException(status_code=400, detail=str(e))