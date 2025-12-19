import os
import datetime
import telebot
from telebot import types
import requests
from dotenv import load_dotenv


load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
RUNRUN_APP_KEY = os.getenv("RUNRUN_APP_KEY")
RUNRUN_USER_TOKEN = os.getenv("RUNRUN_USER_TOKEN")
RUNRUN_BASE_URL = "https://runrun.it/api/v1.0"

# Carrega IDs autorizados do .env
ALLOWED_USER_IDS = [
    int(user_id.strip()) 
    for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",") 
    if user_id.strip()
]

bot = telebot.TeleBot(API_TOKEN)

# Mapeia mensagem do usuário -> ID da tarefa criada
pending_tasks = {}  # { (chat_id, message_id): task_id }

def is_authorized(user_id):
    """Verifica se o usuário está autorizado a usar o bot"""
    if not ALLOWED_USER_IDS:
        print(f"AVISO: Nenhum usuário autorizado configurado no .env")
        return False
    return user_id in ALLOWED_USER_IDS

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
            "project_id": 2757553, #id do projeto "DEVOPS"
            "board_id": 407293, #id do quadro "INFRA"
            "responsible_id": "alexandre-rosendo-passos-filho",
            "type_id": 1889240 #id do tipo "Analise de Infra"
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    print("TASK:", response.status_code, response.text)
    return response

def adicionar_tempo(task_id, seconds):
    url = f"{RUNRUN_BASE_URL}/manual_work_periods"
    headers = {
        "App-Key": RUNRUN_APP_KEY,
        "User-Token": RUNRUN_USER_TOKEN,
        "Content-Type": "application/json",
    }
    today_str = datetime.date.today().isoformat()  # YYYY-MM-DD
    payload = {
        "manual_work_period": {
            "task_id": task_id,
            "seconds": seconds,
            "date_to_apply": today_str
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    print("WORK:", response.status_code, response.text)
    return response

def build_hours_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_1h = types.InlineKeyboardButton("1h", callback_data="h_3600")
    btn_2h = types.InlineKeyboardButton("2h", callback_data="h_7200")
    btn_3h = types.InlineKeyboardButton("3h", callback_data="h_10800")
    btn_4h = types.InlineKeyboardButton("4h", callback_data="h_14400")
    btn_none = types.InlineKeyboardButton("Nenhuma", callback_data="h_0")
    markup.add(btn_1h, btn_2h, btn_3h, btn_4h)
    markup.add(btn_none)
    return markup

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(
            message,
            "⛔ Você não tem permissão para usar este bot.\n"
            f"Seu ID: {message.from_user.id}"
        )
        print(f"Acesso negado para usuário {message.from_user.id} ({message.from_user.username})")
        return
    
    bot.reply_to(
        message,
        "Bot online. Envie o título/descrição do ticket; em seguida escolha as horas já trabalhadas."
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(
            message,
            "⛔ Você não tem permissão para usar este bot.\n"
            f"Seu ID: {message.from_user.id}"
        )
        print(f"Tentativa de criar ticket negada para usuário {message.from_user.id} ({message.from_user.username})")
        return
    
    texto = message.text or ""
    resp = criar_tarefa_runrun(texto)

    if resp.status_code not in (200, 201):
        bot.reply_to(
            message,
            f"Erro ao criar ticket no Runrun.it (status {resp.status_code})."
        )
        return

    task_data = resp.json()
    task_id = task_data.get("id")

    if not task_id:
        bot.reply_to(message, "Ticket criado, mas não consegui obter o ID da tarefa.")
        return

    # Guarda associação (chat_id, message_id da mensagem do usuário) -> task_id
    pending_tasks[(message.chat.id, message.message_id)] = task_id

    # Envia pergunta com botões
    bot.send_message(
        message.chat.id,
        f"Ticket criado (ID {task_id}).\nQuanto tempo já foi trabalhado?",
        reply_markup=build_hours_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("h_"))
def callback_hours(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ Acesso negado.")
        return
    
    seconds = int(call.data.split("_", 1)[1])

    # Associa a tarefa à última mensagem de texto do usuário nesse chat:
    # usamos o message_id anterior ao da mensagem com os botões.
    chat_id = call.message.chat.id
    related_msg_id = call.message.message_id - 1
    key = (chat_id, related_msg_id)
    task_id = pending_tasks.get(key)

    if not task_id:
        bot.answer_callback_query(call.id, "Não encontrei a tarefa associada.")
        return

    if seconds > 0:
        adicionar_tempo(task_id, seconds)
        bot.answer_callback_query(call.id, "Tempo registrado com sucesso.")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Tempo de {seconds // 3600}h registrado no ticket {task_id}."
        )
    else:
        bot.answer_callback_query(call.id, "Nenhum tempo será registrado.")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Nenhum tempo registrado. Ticket {task_id} criado."
        )

    # Limpa da memória
    pending_tasks.pop(key, None)

bot.infinity_polling()
