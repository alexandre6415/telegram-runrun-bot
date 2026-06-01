import os
import time
import datetime
import threading
import telebot
from telebot import types
import requests
from dotenv import load_dotenv


load_dotenv()
API_TOKEN             = os.getenv("TELEGRAM_API_TOKEN")
RUNRUN_APP_KEY        = os.getenv("RUNRUN_APP_KEY")
RUNRUN_USER_TOKEN     = os.getenv("RUNRUN_USER_TOKEN")
RUNRUN_RESPONSIBLE_ID = os.getenv("RUNRUN_RESPONSIBLE_ID")
RUNRUN_BASE_URL       = "https://runrun.it/api/v1.0"

for _var, _nome in [
    (API_TOKEN,             "TELEGRAM_API_TOKEN"),
    (RUNRUN_APP_KEY,        "RUNRUN_APP_KEY"),
    (RUNRUN_USER_TOKEN,     "RUNRUN_USER_TOKEN"),
    (RUNRUN_RESPONSIBLE_ID, "RUNRUN_RESPONSIBLE_ID"),
]:
    if not _var:
        raise ValueError(f"Variável obrigatória não configurada no .env: {_nome}")

ALLOWED_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
]

# Timeout em segundos para confirmações pendentes (5 minutos)
CONFIRMATION_TIMEOUT = 300

bot = telebot.TeleBot(API_TOKEN)


# ─────────────────────────────────────────────────────────────────────────────
# Estado em memória
#
# draft_tasks:     { chat_id: { "text": str, "msg_id": int, "expires_at": float } }
#                  Tarefa aguardando confirmação do usuário.
#
# pending_hours:   { chat_id: { "task_id": int, "msg_id": int } }
#                  Tarefa criada, aguardando escolha de horas.
#
# selected_tasks:  { (chat_id, task_id): dict }  +  { (chat_id, "list"): [dict] }
#                  Tarefas listadas / selecionadas para ação.
#
# pending_comments:{ chat_id: { "task_id": int, "bot_msg_id": int } }
#                  Aguardando texto do comentário.
#
# processing:      { chat_id: bool }
#                  Trava contra duplo clique — descarta callbacks enquanto True.
# ─────────────────────────────────────────────────────────────────────────────

draft_tasks      = {}
pending_hours    = {}
selected_tasks   = {}
pending_comments = {}
processing       = {}


# ─────────────────────────────────────────────────────────────────────────────
# Limpeza automática de drafts expirados
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup_expired_drafts():
    while True:
        time.sleep(60)
        now = time.time()
        expired = [cid for cid, d in list(draft_tasks.items()) if d["expires_at"] < now]
        for cid in expired:
            draft = draft_tasks.pop(cid, None)
            if draft:
                try:
                    bot.edit_message_text(
                        "⏰ Criação cancelada por inatividade.",
                        cid,
                        draft["msg_id"],
                    )
                except Exception:
                    pass

threading.Thread(target=_cleanup_expired_drafts, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers gerais
# ─────────────────────────────────────────────────────────────────────────────

def is_authorized(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        print("AVISO: Nenhum usuário autorizado configurado no .env")
        return False
    return user_id in ALLOWED_USER_IDS


def runrun_headers() -> dict:
    return {
        "App-Key": RUNRUN_APP_KEY,
        "User-Token": RUNRUN_USER_TOKEN,
        "Content-Type": "application/json",
    }


def _deny(message):
    bot.reply_to(
        message,
        f"⛔ Você não tem permissão para usar este bot.\nSeu ID: `{message.from_user.id}`",
        parse_mode="Markdown",
    )
    print(f"Acesso negado: {message.from_user.id} ({message.from_user.username})")


def _seconds_label(seconds: int) -> str:
    if seconds < 3600:
        return f"{seconds // 60}min"
    return f"{seconds // 3600}h"


def _lock(chat_id: int) -> bool:
    """Retorna True se conseguiu travar. False se já estava travado (duplo clique)."""
    if processing.get(chat_id):
        return False
    processing[chat_id] = True
    return True


def _unlock(chat_id: int):
    processing.pop(chat_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Runrun.it API
# ─────────────────────────────────────────────────────────────────────────────

def criar_tarefa_runrun(texto: str):
    url = f"{RUNRUN_BASE_URL}/tasks"
    payload = {
        "task": {
            "title": texto[:80],
            "description": texto,
            "project_id": 2757553,
            "board_id": 407293,
            "responsible_id": RUNRUN_RESPONSIBLE_ID,
            "type_id": 1889240,
        }
    }
    resp = requests.post(url, json=payload, headers=runrun_headers())
    print("TASK CREATE:", resp.status_code)
    return resp


def listar_tarefas_abertas(responsible_id: str) -> list:
    url = f"{RUNRUN_BASE_URL}/tasks"
    params = {
        "responsible_id": responsible_id,
        "is_closed": "false",
        "limit": 50,
        "sort": "desired_date",
        "sort_dir": "asc",
    }
    resp = requests.get(url, params=params, headers=runrun_headers())
    print("TASKS LIST:", resp.status_code)
    return resp.json() if resp.status_code == 200 else []


def entregar_tarefa(task_id: int):
    resp = requests.post(f"{RUNRUN_BASE_URL}/tasks/{task_id}/deliver", headers=runrun_headers())
    print("DELIVER:", resp.status_code)
    return resp


def marcar_urgente(task_id: int, urgente: bool):
    action = "mark_as_urgent" if urgente else "unmark_as_urgent"
    resp = requests.post(f"{RUNRUN_BASE_URL}/tasks/{task_id}/{action}", headers=runrun_headers())
    print("URGENT:", resp.status_code)
    return resp


def adicionar_comentario(task_id: int, texto: str):
    url = f"{RUNRUN_BASE_URL}/tasks/{task_id}/comments"
    resp = requests.post(url, json={"comment": {"text": texto}}, headers=runrun_headers())
    print("COMMENT:", resp.status_code)
    return resp


def adicionar_tempo(task_id: int, seconds: int):
    url = f"{RUNRUN_BASE_URL}/manual_work_periods"
    payload = {
        "manual_work_period": {
            "task_id": task_id,
            "seconds": seconds,
            "date_to_apply": datetime.date.today().isoformat(),
        }
    }
    resp = requests.post(url, json=payload, headers=runrun_headers())
    print("WORK:", resp.status_code)
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Teclados
# ─────────────────────────────────────────────────────────────────────────────

def build_confirm_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("✅ Confirmar", callback_data="confirm_create"),
        types.InlineKeyboardButton("✏️ Editar",    callback_data="confirm_edit"),
        types.InlineKeyboardButton("❌ Cancelar",  callback_data="confirm_cancel"),
    )
    return markup


def build_hours_keyboard(task_id: int):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("30min", callback_data=f"h_{task_id}_1800"),
        types.InlineKeyboardButton("1h",    callback_data=f"h_{task_id}_3600"),
        types.InlineKeyboardButton("2h",    callback_data=f"h_{task_id}_7200"),
        types.InlineKeyboardButton("3h",    callback_data=f"h_{task_id}_10800"),
        types.InlineKeyboardButton("4h",    callback_data=f"h_{task_id}_14400"),
        types.InlineKeyboardButton("Nenhuma", callback_data=f"h_{task_id}_0"),
    )
    return markup


def build_tasks_keyboard(tasks: list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for task in tasks[:10]:
        title = task.get("title", "Sem título")
        label = title[:50] + ("…" if len(title) > 50 else "")
        markup.add(types.InlineKeyboardButton(label, callback_data=f"task_{task['id']}"))
    markup.add(types.InlineKeyboardButton("❌ Fechar", callback_data="cancel"))
    return markup


def build_task_actions_keyboard(task_id: int, is_urgent: bool):
    urgent_label = "🔕 Desmarcar urgente" if is_urgent else "🚨 Marcar urgente"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Entregar",        callback_data=f"action_deliver_{task_id}"),
        types.InlineKeyboardButton("💬 Comentar",        callback_data=f"action_comment_{task_id}"),
        types.InlineKeyboardButton("⏱ Registrar tempo",  callback_data=f"action_time_{task_id}"),
        types.InlineKeyboardButton(urgent_label,          callback_data=f"action_urgent_{task_id}"),
    )
    markup.add(types.InlineKeyboardButton("🔙 Voltar", callback_data="back_to_list"))
    return markup


def build_hours_for_task_keyboard(task_id: int):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("30min", callback_data=f"time_{task_id}_1800"),
        types.InlineKeyboardButton("1h",    callback_data=f"time_{task_id}_3600"),
        types.InlineKeyboardButton("2h",    callback_data=f"time_{task_id}_7200"),
        types.InlineKeyboardButton("3h",    callback_data=f"time_{task_id}_10800"),
        types.InlineKeyboardButton("4h",    callback_data=f"time_{task_id}_14400"),
        types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel_inline"),
    )
    return markup


def build_retry_keyboard(action: str):
    """Botão de retry genérico — action é o callback_data original."""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔄 Tentar novamente", callback_data=action),
        types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel_inline"),
    )
    return markup


# ─────────────────────────────────────────────────────────────────────────────
# Handlers de comandos
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    if not is_authorized(message.from_user.id):
        return _deny(message)
    bot.reply_to(
        message,
        "👋 *Bot Runrun.it*\n\n"
        "• Envie um texto para *criar um ticket* (com confirmação)\n"
        "• /minhas\\_tarefas — lista e gerencia suas tarefas em aberto\n"
        "• /cancelar — cancela qualquer operação pendente\n"
        "• /help — exibe esta mensagem",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["cancelar"])
def cmd_cancelar(message):
    if not is_authorized(message.from_user.id):
        return _deny(message)
    chat_id = message.chat.id
    draft_tasks.pop(chat_id, None)
    pending_hours.pop(chat_id, None)
    pending_comments.pop(chat_id, None)
    _unlock(chat_id)
    bot.reply_to(message, "🚫 Operação cancelada.")


@bot.message_handler(commands=["minhas_tarefas"])
def cmd_minhas_tarefas(message):
    if not is_authorized(message.from_user.id):
        return _deny(message)

    msg = bot.reply_to(message, "⏳ Buscando suas tarefas…")
    tasks = listar_tarefas_abertas(RUNRUN_RESPONSIBLE_ID)

    if not tasks:
        bot.edit_message_text(
            "✅ Nenhuma tarefa em aberto encontrada.",
            msg.chat.id, msg.message_id,
        )
        return

    selected_tasks[(message.chat.id, "list")] = tasks
    bot.edit_message_text(
        f"📋 *{len(tasks)} tarefa(s) em aberto.* Selecione uma:",
        msg.chat.id, msg.message_id,
        parse_mode="Markdown",
        reply_markup=build_tasks_keyboard(tasks),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Handler de texto livre
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if not is_authorized(message.from_user.id):
        return _deny(message)

    chat_id = message.chat.id
    texto   = message.text or ""

    # ── Aguardando comentário ──
    if chat_id in pending_comments:
        state    = pending_comments.pop(chat_id)
        task_id  = state["task_id"]
        bot_msg  = state["bot_msg_id"]

        resp = adicionar_comentario(task_id, texto)
        if resp.status_code in (200, 201):
            try:
                bot.edit_message_text(
                    f"💬 Comentário adicionado à tarefa *{task_id}*.",
                    chat_id, bot_msg, parse_mode="Markdown",
                )
            except Exception:
                pass
            bot.delete_message(chat_id, message.message_id)
        else:
            bot.reply_to(message, f"❌ Erro ao comentar (status {resp.status_code}). Tente novamente.")
        return

    # ── Aguardando edição do texto do draft ──
    if chat_id in draft_tasks and draft_tasks[chat_id].get("awaiting_edit"):
        draft = draft_tasks[chat_id]
        draft["text"]          = texto
        draft["awaiting_edit"] = False
        draft["expires_at"]    = time.time() + CONFIRMATION_TIMEOUT

        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass

        bot.edit_message_text(
            _preview_text(texto),
            chat_id, draft["msg_id"],
            parse_mode="Markdown",
            reply_markup=build_confirm_keyboard(),
        )
        return

    # ── Novo draft ──
    sent = bot.reply_to(
        message,
        _preview_text(texto),
        parse_mode="Markdown",
        reply_markup=build_confirm_keyboard(),
    )
    draft_tasks[chat_id] = {
        "text":          texto,
        "msg_id":        sent.message_id,
        "expires_at":    time.time() + CONFIRMATION_TIMEOUT,
        "awaiting_edit": False,
    }


def _preview_text(texto: str) -> str:
    titulo = texto[:80] + ("…" if len(texto) > 80 else "")
    return (
        f"📋 *Nova tarefa — confirme antes de criar:*\n\n"
        f"*Título:* {titulo}\n\n"
        f"_Toque em Confirmar para criar ou Editar para corrigir._"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Handler único de callbacks
# ─────────────────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if not is_authorized(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ Acesso negado.")
        return

    data    = call.data
    chat_id = call.message.chat.id
    msg_id  = call.message.message_id

    # ── Confirmação de criação ──────────────────────────────────────────────
    if data == "confirm_create":
        if not _lock(chat_id):
            bot.answer_callback_query(call.id, "⏳ Aguarde…")
            return

        draft = draft_tasks.get(chat_id)
        if not draft:
            bot.answer_callback_query(call.id, "⏰ Sessão expirada. Envie o texto novamente.")
            _unlock(chat_id)
            return

        bot.answer_callback_query(call.id)
        bot.edit_message_text("⏳ Criando tarefa…", chat_id, msg_id)

        resp = criar_tarefa_runrun(draft["text"])
        draft_tasks.pop(chat_id, None)

        if resp.status_code not in (200, 201):
            bot.edit_message_text(
                f"❌ Erro ao criar tarefa (status {resp.status_code}).",
                chat_id, msg_id,
                reply_markup=build_retry_keyboard("confirm_create"),
            )
            _unlock(chat_id)
            return

        task_id = resp.json().get("id")
        _unlock(chat_id)

        pending_hours[chat_id] = {"task_id": task_id, "msg_id": msg_id}

        bot.edit_message_text(
            f"✅ Tarefa *{task_id}* criada!\n\nQuanto tempo já foi trabalhado nela?",
            chat_id, msg_id,
            parse_mode="Markdown",
            reply_markup=build_hours_keyboard(task_id),
        )
        return

    if data == "confirm_edit":
        draft = draft_tasks.get(chat_id)
        if not draft:
            bot.answer_callback_query(call.id, "⏰ Sessão expirada.")
            return
        draft["awaiting_edit"] = True
        draft["expires_at"]    = time.time() + CONFIRMATION_TIMEOUT
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "✏️ Envie o texto corrigido:",
            chat_id, msg_id,
        )
        return

    if data == "confirm_cancel":
        draft_tasks.pop(chat_id, None)
        bot.answer_callback_query(call.id, "Cancelado.")
        bot.edit_message_text("🚫 Criação cancelada.", chat_id, msg_id)
        return

    # ── Escolha de horas após criação ──────────────────────────────────────
    if data.startswith("h_"):
        parts   = data.split("_")           # h_<task_id>_<seconds>
        task_id = int(parts[1])
        seconds = int(parts[2])

        state = pending_hours.get(chat_id)
        if not state or state["task_id"] != task_id:
            bot.answer_callback_query(call.id, "Sessão expirada.")
            return

        pending_hours.pop(chat_id, None)

        if seconds > 0:
            resp = adicionar_tempo(task_id, seconds)
            if resp.status_code not in (200, 201):
                bot.answer_callback_query(call.id, "Erro ao registrar tempo.")
                bot.edit_message_text(
                    f"✅ Tarefa *{task_id}* criada, mas falha ao registrar tempo.",
                    chat_id, msg_id,
                    parse_mode="Markdown",
                    reply_markup=build_retry_keyboard(data),
                )
                return
            label = _seconds_label(seconds)
            bot.answer_callback_query(call.id, "Tempo registrado!")
            bot.edit_message_text(
                f"✅ Tarefa *{task_id}* criada com *{label}* registrado.",
                chat_id, msg_id, parse_mode="Markdown",
            )
        else:
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                f"✅ Tarefa *{task_id}* criada sem registro de tempo.",
                chat_id, msg_id, parse_mode="Markdown",
            )
        return

    # ── Seleção de tarefa da lista ──────────────────────────────────────────
    if data.startswith("task_"):
        task_id = int(data.split("_", 1)[1])
        tasks   = selected_tasks.get((chat_id, "list"), [])
        task    = next((t for t in tasks if t["id"] == task_id), None)

        if not task:
            bot.answer_callback_query(call.id, "Tarefa não encontrada na lista.")
            return

        selected_tasks[(chat_id, task_id)] = task
        _show_task_detail(call, task)
        return

    # ── Ações em tarefa existente ───────────────────────────────────────────
    if data.startswith("action_"):
        parts   = data.split("_")
        action  = parts[1]
        task_id = int(parts[2])

        if not _lock(chat_id):
            bot.answer_callback_query(call.id, "⏳ Aguarde…")
            return

        task = selected_tasks.get((chat_id, task_id), {})

        if action == "deliver":
            bot.answer_callback_query(call.id)
            bot.edit_message_text("⏳ Entregando tarefa…", chat_id, msg_id)
            resp = entregar_tarefa(task_id)
            if resp.status_code in (200, 201):
                bot.edit_message_text(
                    f"✅ Tarefa *{task_id}* entregue com sucesso!",
                    chat_id, msg_id, parse_mode="Markdown",
                )
            else:
                bot.edit_message_text(
                    f"❌ Erro ao entregar (status {resp.status_code}).",
                    chat_id, msg_id,
                    reply_markup=build_retry_keyboard(data),
                )

        elif action == "comment":
            pending_comments[chat_id] = {"task_id": task_id, "bot_msg_id": msg_id}
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                f"💬 Digite o comentário para a tarefa *{task_id}*:\n\n"
                "_Ou envie /cancelar para desistir._",
                chat_id, msg_id, parse_mode="Markdown",
            )

        elif action == "time":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                f"⏱ Quanto tempo registrar na tarefa *{task_id}*?",
                chat_id, msg_id, parse_mode="Markdown",
                reply_markup=build_hours_for_task_keyboard(task_id),
            )

        elif action == "urgent":
            is_urgent = task.get("is_urgent", False)
            bot.answer_callback_query(call.id)
            resp = marcar_urgente(task_id, not is_urgent)
            if resp.status_code in (200, 201):
                novo_estado = not is_urgent
                label = "marcada como urgente 🚨" if novo_estado else "desmarcada como urgente"
                # Atualiza estado local
                task["is_urgent"] = novo_estado
                bot.edit_message_text(
                    f"Tarefa *{task_id}* {label}.",
                    chat_id, msg_id, parse_mode="Markdown",
                )
            else:
                bot.edit_message_text(
                    f"❌ Erro na operação (status {resp.status_code}).",
                    chat_id, msg_id,
                    reply_markup=build_retry_keyboard(data),
                )

        _unlock(chat_id)
        return

    # ── Registro de tempo em tarefa existente ──────────────────────────────
    if data.startswith("time_"):
        parts   = data.split("_")
        task_id = int(parts[1])
        seconds = int(parts[2])

        if not _lock(chat_id):
            bot.answer_callback_query(call.id, "⏳ Aguarde…")
            return

        resp = adicionar_tempo(task_id, seconds)
        if resp.status_code in (200, 201):
            label = _seconds_label(seconds)
            bot.answer_callback_query(call.id, "Tempo registrado!")
            bot.edit_message_text(
                f"⏱ *{label}* registrado na tarefa *{task_id}*.",
                chat_id, msg_id, parse_mode="Markdown",
            )
        else:
            bot.answer_callback_query(call.id, "Erro ao registrar.")
            bot.edit_message_text(
                f"❌ Erro ao registrar tempo (status {resp.status_code}).",
                chat_id, msg_id,
                reply_markup=build_retry_keyboard(data),
            )
        _unlock(chat_id)
        return

    # ── Voltar à lista ─────────────────────────────────────────────────────
    if data == "back_to_list":
        tasks = selected_tasks.get((chat_id, "list"), [])
        if not tasks:
            bot.answer_callback_query(call.id, "Lista expirada. Use /minhas_tarefas novamente.")
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            f"📋 *{len(tasks)} tarefa(s) em aberto.* Selecione uma:",
            chat_id, msg_id,
            parse_mode="Markdown",
            reply_markup=build_tasks_keyboard(tasks),
        )
        return

    # ── Cancelar inline (fecha o menu sem apagar) ──────────────────────────
    if data == "cancel_inline":
        bot.answer_callback_query(call.id, "Cancelado.")
        try:
            bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)
        except Exception:
            pass
        return

    # ── Cancelar (apaga a mensagem) ────────────────────────────────────────
    if data == "cancel":
        bot.answer_callback_query(call.id, "Cancelado.")
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        return


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de exibição
# ─────────────────────────────────────────────────────────────────────────────

def _show_task_detail(call, task: dict):
    chat_id   = call.message.chat.id
    msg_id    = call.message.message_id
    task_id   = task["id"]
    title     = task.get("title", "Sem título")
    is_urgent = task.get("is_urgent", False)
    prazo     = task.get("desired_date") or "—"
    segundos  = task.get("time_worked", 0)

    h = segundos // 3600
    m = (segundos % 3600) // 60
    time_label = f"{h}h{m:02d}min" if h else f"{m}min"

    urgente_badge = " 🚨" if is_urgent else ""
    text = (
        f"📌 *{title}*{urgente_badge}\n"
        f"ID: `{task_id}`\n"
        f"Prazo: {prazo}\n"
        f"Tempo trabalhado: {time_label}"
    )

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        text, chat_id, msg_id,
        parse_mode="Markdown",
        reply_markup=build_task_actions_keyboard(task_id, is_urgent),
    )


bot.infinity_polling()
