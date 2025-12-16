import os
import datetime
import telebot
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
RUNRUN_APP_KEY = os.getenv("RUNRUN_APP_KEY")
RUNRUN_USER_TOKEN = os.getenv("RUNRUN_USER_TOKEN")
RUNRUN_BASE_URL = "https://runrun.it/api/v1.0"

bot = telebot.TeleBot(API_TOKEN)

def criar_tarefa_runrun(texto):
    url = f"{RUNRUN_BASE_URL}/tasks"
    headers = {
        "App-Key": RUNRUN_APP_KEY,
        "User-Token": RUNRUN_USER_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {
        "task": {
            "title": texto[:80],
            "description": texto,
            "project_id": 2757553,  # inteiro, ex: 123456
            "board_id": 407293,   # ou o nome de campo que a doc indicar
            "responsible_id": "alexandre-rosendo-passos-filho",
            "type_id": 1889240, #id do tipo Analise de Infra
#            "current_estimate_seconds": 3600 # tempo pre definido de 1h
            "time_worked": 7200
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.status_code, response.text)
    return response
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, "Bot online. Envie uma mensagem que vou abrir um ticket no Runrun.it.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    texto = message.text or ""
    resp = criar_tarefa_runrun(texto)

    if resp.status_code == 201 or resp.status_code == 200:
        bot.reply_to(message, "Ticket criado no Runrun.it com sucesso.")
    else:
        bot.reply_to(
            message,
            f"Erro ao criar ticket no Runrun.it (status {resp.status_code})."
        )

bot.infinity_polling()
