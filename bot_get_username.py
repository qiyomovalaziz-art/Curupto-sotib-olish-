#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import json
import html
import time
from pathlib import Path
from telegram import (
    Update, ParseMode, KeyboardButton, ReplyKeyboardMarkup, ChatMember
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)

# --------- SOZLAMALAR ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "<SENING_BOT_TOKEN>"
OWNER_ID = int(os.environ.get("OWNER_ID") or 7973934849)
DATA_FILE = Path("bot_data.json")
# --------------------------------

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Ma'lumot faylini yuklash/saqlash ---
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"users": {}, "chats": {}}
    return {"users": {}, "chats": {}}

def save_data(d):
    DATA_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

data = load_data()

# Struktur:
# data = {
#   "users": {
#       "<user_id>": {
#           "username": "...",
#           "full_name": "...",
#           "phone": "...",
#           "seen_in": { "<chat_id>": first_seen_unix_ts, ... }
#       }, ...
#   },
#   "chats": {
#       "<chat_id>": { "title": "...", "type": "group|supergroup|channel|private" }
#   }
# }

def ensure_user_entry(user_id: int):
    sid = str(user_id)
    if sid not in data["users"]:
        data["users"][sid] = {"username": None, "full_name": None, "phone": None, "seen_in": {}}
    return data["users"][sid]

def ensure_chat_entry(chat):
    cid = str(chat.id)
    if cid not in data["chats"]:
        title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or cid
        data["chats"][cid] = {"title": title, "type": getattr(chat, "type", None)}
    return data["chats"][cid]

# --- Handlers ---
def start(update: Update, context: CallbackContext):
    keyboard = [[KeyboardButton("📱 Raqamimni yuborish", request_contact=True)]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        "Salom! Agar telefon raqamingizni baham ko'rmoqchi bo'lsangiz, tugmani bosing.\n\n"
        "Eslatma: telefon faqat siz yuborgan taqdirda saqlanadi.",
        reply_markup=reply
    )

def contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    if not contact:
        return
    uid = contact.user_id or update.effective_user.id
    u = ensure_user_entry(uid)
    u["phone"] = contact.phone_number
    user = update.effective_user
    u["username"] = user.username
    u["full_name"] = ((user.first_name or "") + " " + (user.last_name or "")).strip()
    save_data(data)
    update.message.reply_text("✅ Telefon raqamingiz saqlandi. Rahmat!")

def record_presence(user, chat):
    if user is None or chat is None:
        return
    u = ensure_user_entry(user.id)
    u["username"] = user.username
    u["full_name"] = ((user.first_name or "") + " " + (user.last_name or "")).strip()
    cid = str(chat.id)
    # agar birinchi marta ko'rilsa, saqlaymiz vaqtni
    if cid not in u["seen_in"]:
        u["seen_in"][cid] = int(time.time())
    ensure_chat_entry(chat)
    save_data(data)

def group_message_handler(update: Update, context: CallbackContext):
    # Guruh yoki kanal ichidagi xabar yozilganda
    user = update.effective_user
    chat = update.effective_chat
    record_presence(user, chat)

def new_members_handler(update: Update, context: CallbackContext):
    chat = update.effective_chat
    for member in update.message.new_chat_members or []:
        record_presence(member, chat)

def left_member_handler(update: Update, context: CallbackContext):
    # agar kerak bo'lsa ketganlarni qayd etish mumkin
    pass

def get_command(update: Update, context: CallbackContext):
    # faqat owner
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ Sizga ruxsat yo'q.")
        return

    if not context.args:
        update.message.reply_text("Foydalanish: /get <user_id yoki @username>")
        return

    q = context.args[0].strip()
    # avval ID bilan qaraymiz
    entry = data["users"].get(str(q))
    if entry is None:
        # username bilan qidiring
        uname = q[1:] if q.startswith("@") else q
        found = None
        for uid, val in data["users"].items():
            if val.get("username") and val["username"].lower() == uname.lower():
                found = (uid, val)
                break
        if found:
            uid, entry = found
        else:
            update.message.reply_text("📭 Saqlangan ma'lumot topilmadi.")
            return
    uid_str = None
    # find key for the entry
    for k, v in data["users"].items():
        if v is entry:
            uid_str = k
            break
    text_lines = [
        "<b>Saqlangan ma'lumot:</b>",
        f"ID: <code>{html.escape(uid_str or q)}</code>",
        f"Username: {html.escape(entry.get('username') or '(yo‘q)')}",
        f"Ism: {html.escape(entry.get('full_name') or '(yo‘q)')}",
        f"Telefon: {html.escape(entry.get('phone') or '(saqlanmagan)')}",
        "",
        "<b>Bot kuzatgan chatlar va birinchi ko‘rish vaqti:</b>"
    ]
    seen = entry.get("seen_in", {})
    if seen:
        for cid, ts in seen.items():
            chat_info = data["chats"].get(cid, {})
            title = chat_info.get("title", cid)
            ctype = chat_info.get("type", "")
            text_lines.append(f"{html.escape(title)} ({html.escape(str(ctype))}) — id {cid} — birinchi ko‘rish: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}")
    else:
        text_lines.append("(Hech qanday chatda uchramagan yoki saqlanmagan.)")

    update.message.reply_text("\n".join(text_lines), parse_mode=ParseMode.HTML)

def check_command(update: Update, context: CallbackContext):
    # /check <user_id> <chat_id1> <chat_id2> ...
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ Sizga ruxsat yo'q.")
        return
    if len(context.args) < 2:
        update.message.reply_text("Foydalanish: /check <user_id> <chat_id1> [chat_id2 ...]\nBot tekshirishi uchun u chatlarda bo‘lishi kerak.")
        return

    user_arg = context.args[0]
    # user_id numeric kerak bo'ladi
    try:
        user_id = int(user_arg) if not user_arg.startswith("@") else None
    except ValueError:
        user_id = None

    result_lines = []
    for chat_arg in context.args[1:]:
        try:
            chat_id = int(chat_arg)
        except ValueError:
            chat_id = chat_arg  # username or @channelusername
        try:
            member = context.bot.get_chat_member(chat_id=chat_id, user_id=int(user_arg) if user_id else user_arg)
            # member.status: "creator", "administrator", "member", "left", "kicked"
            status = getattr(member, "status", str(member))
            result_lines.append(f"Chat {chat_arg}: status = {status}")
        except Exception as e:
            result_lines.append(f"Chat {chat_arg}: xato yoki bot bu chatda emas / ruxsat yo'q ({e})")

    update.message.reply_text("\n".join(result_lines))

def error_handler(update: Update, context: CallbackContext):
    logger.exception("Xato: %s", context.error)

def main():
    if not BOT_TOKEN or "<SENING_BOT_TOKEN>" in BOT_TOKEN:
        print("Iltimos BOT_TOKEN sozlang.")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))
    dp.add_handler(MessageHandler(~Filters.private, group_message_handler))  # private bo'lmagan xabarlarni kuzatadi
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_members_handler))
    dp.add_handler(CommandHandler("get", get_command, pass_args=True))
    dp.add_handler(CommandHandler("check", check_command, pass_args=True))
    dp.add_error_handler(error_handler)

    logger.info("Bot ishga tushmoqda...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
