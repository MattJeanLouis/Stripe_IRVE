import requests
import json

BASE_URL = "http://localhost:8000"

def test_fixed_payment():
    url = f"{BASE_URL}/api/create-payment"
    payload = {
        "paymentType": "fixed",
        "montant": 1000,  # 10,00 EUR
        "devise": "eur",
        "id_client": "client_789012",
        "description": "Recharge fixe - 10 EUR"
    }
    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, data=json.dumps(payload), headers=headers)
    
    assert response.status_code == 200, f"Erreur : {response.text}"
    data = response.json()
    assert "session_id" in data, "La réponse ne contient pas de session_id"
    assert "url" in data, "La réponse ne contient pas d'URL de paiement"

    print("Test de paiement fixe réussi :")
    print(f"ID de session : {data['session_id']}")
    print(f"URL de paiement : {data['url']}")

if __name__ == "__main__":
    test_fixed_payment()