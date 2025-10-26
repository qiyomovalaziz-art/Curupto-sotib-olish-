#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import json
import html
from pathlib import Path
from telegram import Update, ParseMode, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)

# ---------- SOZLAMALAR ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "<SENING_BOT_TOKEN>"
OWNER_ID = int(os.environ.get("OWNER_ID") or 7973934849)  # o'zgartir: o'z user id'ingni qo'y
DATA_FILE = Path("bot_data.json")  # oddiy faylga saqlaymiz (SQLite yoki DB ham qo'yish mumkin)
# ---------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data strukturalari ---
# fayl tarkibi: {"users": { "<user_id>": {"username":..., "full_name":..., "phone":..., "seen_in": [chat_id,...]} }, "chats": { "<chat_id>": {"title":..., "type":...} } }
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"users": {}, "chats": {}}
    return {"users": {}, "chats": {}}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

data = load_data()

# --- Yordamchi ---
def ensure_user_entry(user_id: int):
    sid = str(user_id)
    if sid not in data["users"]:
        data["users"][sid] = {"username": None, "full_name": None, "phone": None, "seen_in": []}
    return data["users"][sid]

def ensure_chat_entry(chat):
    cid = str(chat.id)
    if cid not in data["chats"]:
        data["chats"][cid] = {"title": getattr(chat, "title", None) or getattr(chat, "first_name", None) or cid, "type": chat.type}
    return data["chats"][cid]

# --- Handlers ---
def start(update: Update, context: CallbackContext):
    # Taklif: foydalanuvchi telefonini bir martalik yuborishi uchun tugma
    keyboard = [[KeyboardButton("📱 Raqamimni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(
        "Salom! Agar telefon raqamingizni biz bilan bo'lishmoqchi bo'lsangiz, quyidagi tugmaga bosing.\n\n"
        "Eslatma: telefon faqat siz yuborgan taqdirda saqlanadi.",
        reply_markup=reply_markup
    )

def contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    # contact.user_id -> original foydalanuvchi id
    if not contact:
        return
    uid = contact.user_id or update.effective_user.id
    uentry = ensure_user_entry(uid)
    uentry["phone"] = contact.phone_number
    # also update username / name from sender
    user = update.effective_user
    uentry["username"] = user.username
    uentry["full_name"] = (user.first_name or "") + " " + (user.last_name or "")
    save_data(data)
    update.message.reply_text("✅ Rahmat — telefon raqamingiz saqlandi.")

def record_presence_in_chat(user, chat):
    # chat = update.effective_chat, user = update.effective_user
    uentry = ensure_user_entry(user.id)
    # update username / full_name
    uentry["username"] = user.username
    uentry["full_name"] = ((user.first_name or "") + " " + (user.last_name or "")).strip()
    cid = str(chat.id)
    if cid not in uentry["seen_in"]:
        uentry["seen_in"].append(cid)
    ensure_chat_entry(chat)
    save_data(data)

def group_message_handler(update: Update, context: CallbackContext):
    # Agar foydalanuvchi guruh yoki kanal ichida xabar yuborsa — uni "ko‘rgan" deb belgilaymiz
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    record_presence_in_chat(user, chat)
    # bot hech qanday avtomatik javob bermasligni afzal ko'ramiz
    return

def new_members_handler(update: Update, context: CallbackContext):
    # yangi a'zolar qo'shilganda ham ularni belgilash mumkin
    chat = update.effective_chat
    for member in update.message.new_chat_members or []:
        # member is a User
        record_presence_in_chat(member, chat)

def get_user_handler(update: Update, context: CallbackContext):
    # faqat OWNER_IDga ruxsat
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ Sizda ruxsat yo'q.")
        return

    if not context.args:
        update.message.reply_text("Foydalanish: /get <user_id>\nEslatma: faqat bot ma'lumotlar bazasida saqlangan ma'lumotlar ko'rsatiladi.")
        return

    user_id = context.args[0].strip()
    # qidiruv numeric yoki username bilan ham sinash mumkin
    # avval numeric sifatida tekshir
    uentry = data["users"].get(str(user_id))
    if uentry is None:
        # agar username berilgan bo'lsa, qidiring
        if user_id.startswith("@"):
            uname = user_id[1:].lower()
        else:
            uname = user_id.lower()
        # qidiruv
        found = None
        for k, v in data["users"].items():
            if v.get("username") and v["username"].lower() == uname:
                found = (k, v)
                break
        if found:
            uid, uentry = found
        else:
            update.message.reply_text("📭 Bu ID/username bo'yicha saqlangan ma'lumot topilmadi.")
            return

    # tayyorlash
    username = uentry.get("username") or "(yo'q)"
    full_name = uentry.get("full_name") or "(yo'q)"
    phone = uentry.get("phone") or "(saqlanmagan)"
    seen_chats = uentry.get("seen_in", [])

    # chat nomlarini olish
    chat_lines = []
    for cid in seen_chats:
        chat_info = data["chats"].get(cid)
        if chat_info:
            chat_lines.append(f"{chat_info.get('title')} ({chat_info.get('type')}) — id {cid}")
        else:
            chat_lines.append(f"{cid}")

    text = (
        f"<b>Ma'lumot (saqlangan):</b>\n"
        f"ID: <code>{html.escape(str(user_id))}</code>\n"
        f"Username: {html.escape(username)}\n"
        f"Ism: {html.escape(full_name)}\n"
        f"Telefon: {html.escape(phone)}\n\n"
        f"<b>Foydalanuvchining bot kuzatgan chatlari (faqat bot ishtirok etgan va saqlanganlar):</b>\n"
    )
    if chat_lines:
        text += "\n".join(html.escape(line) for line in chat_lines)
    else:
        text += "(Hech qanday chatda uchramagan yoki saqlanmagan.)"

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def error_handler(update: Update, context: CallbackContext):
    logger.exception("Xato yuz berdi: %s", context.error)

def main():
    if not BOT_TOKEN or "<SENING_BOT_TOKEN>" in BOT_TOKEN:
        print("Iltimos: BOT_TOKEN o'rnatilsin (env VAR yoki kod ichida).")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))       # telefon yuborilganda
    dp.add_handler(MessageHandler(Filters.group | Filters.channel, group_message_handler))  # guruhda yozganda
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_members_handler))  # yangi a'zo qo'shilsa
    dp.add_handler(CommandHandler("get", get_user_handler, pass_args=True))
    dp.add_error_handler(error_handler)

    logger.info("Bot ishga tushmoqda...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
