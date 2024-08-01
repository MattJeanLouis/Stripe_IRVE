#!/bin/bash

# Démarrer le listener Stripe en arrière-plan
stripe listen --forward-to localhost:80/webhook > stripe_output.log 2>&1 &

# Attendre que le listener Stripe soit prêt
while ! grep -q "Ready!" stripe_output.log; do
    sleep 1
done

# Extraire la clé de webhook
WEBHOOK_SECRET=$(grep "webhook signing secret:" stripe_output.log | awk '{print $NF}')

# Mettre à jour le fichier .env avec la nouvelle clé de webhook
sed -i "s/^STRIPE_WEBHOOK_SECRET=.*/STRIPE_WEBHOOK_SECRET=$WEBHOOK_SECRET/" /app/.env

# Démarrer l'application FastAPI
exec uvicorn main:app --host 0.0.0.0 --port 80