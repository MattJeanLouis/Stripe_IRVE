FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Installation de l'outil CLI Stripe
RUN apt-get update && apt-get install -y curl
RUN curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | tee /usr/share/keyrings/stripe.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | tee -a /etc/apt/sources.list.d/stripe.list
RUN apt-get update && apt-get install -y stripe

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app
COPY .env /app/.env

# Script pour démarrer l'application et le listener Stripe
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
