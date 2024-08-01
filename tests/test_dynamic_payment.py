import requests
import json
import time
import stripe
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

BASE_URL = "http://localhost:8000"

def test_dynamic_payment():
    # Créer un client de test
    customer = stripe.Customer.create(
        email="test@example.com",
        name="Client de Test Dynamique"
    )
    client_id = customer.id
    print(f"Client de test créé avec l'ID : {client_id}")

    try:
        # Utiliser un jeton de test au lieu de créer une méthode de paiement
        test_token = "tok_visa"  # Jeton de test pour une carte Visa

        # Étape 1 : Démarrer une session de charge
        start_url = f"{BASE_URL}/api/start-charging-session"
        start_payload = {
            "client_id": client_id,
            "payment_token": test_token
        }
        headers = {'Content-Type': 'application/json'}

        start_response = requests.post(start_url, data=json.dumps(start_payload), headers=headers)
        assert start_response.status_code == 200, f"Erreur au démarrage de la session : {start_response.text}"
        start_data = start_response.json()
        setup_intent_id = start_data["setup_intent_id"]

        print("Session de charge démarrée :")
        print(f"ID du SetupIntent : {setup_intent_id}")

        assert "setup_intent_id" in start_data, "La réponse ne contient pas de setup_intent_id"
        assert "client_secret" in start_data, "La réponse ne contient pas de client_secret"

        # Simuler une charge en cours
        time.sleep(5)

        # Étape 2 : Terminer la session de charge
        end_url = f"{BASE_URL}/api/end-charging-session"
        end_payload = {
            "setup_intent_id": setup_intent_id,
            "final_amount": 3500  # 35,00 EUR
        }

        end_response = requests.post(end_url, data=json.dumps(end_payload), headers=headers)
        assert end_response.status_code == 200, f"Erreur à la fin de la session : {end_response.text}"
        end_data = end_response.json()

        assert "status" in end_data, "La réponse ne contient pas de statut"
        assert "payment_intent_id" in end_data, "La réponse ne contient pas d'ID d'intention de paiement"

        print("Session de charge terminée :")
        print(f"Statut : {end_data['status']}")
        print(f"ID de l'intention de paiement : {end_data['payment_intent_id']}")

        # Vérifier le statut du paiement
        payment_intent = stripe.PaymentIntent.retrieve(end_data['payment_intent_id'])
        assert payment_intent.status == 'succeeded', f"Le paiement n'a pas réussi. Statut : {payment_intent.status}"

        print("Test de paiement dynamique réussi.")

    except Exception as e:
        print(f"Erreur lors du test : {str(e)}")
        raise

    finally:
        # Supprimer le client de test
        stripe.Customer.delete(client_id)
        print(f"Client de test avec l'ID {client_id} supprimé.")

if __name__ == "__main__":
    test_dynamic_payment()