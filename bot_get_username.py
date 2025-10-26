#!/usr/bin/env python3
# coding: utf-8

import logging
import html
from telegram import Update, ParseMode, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN") or "<BU YERGA BOT TOKENNI YOZ>"
OWNER_ID = int(os.environ.get("OWNER_ID") or 7973934849)  # O'zingning ID'ing

logging.basicConfig(level=logging.INFO)

user_phone_numbers = {}  # ID → phone_number saqlash uchun

def start(update: Update, context: CallbackContext):
    keyboard = [[KeyboardButton("📱 Raqamimni yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(
        "Salom! Men ID → Username → (agar mavjud bo'lsa) telefon raqam ko'rsatadigan botman.\n\n"
        "Raqamingizni ulashsangiz — sizning raqamingiz saqlanadi.",
        reply_markup=reply_markup
    )

def contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    user_phone_numbers[contact.user_id] = contact.phone_number
    update.message.reply_text("✅ Telefon raqamingiz saqlandi.")

def get_user(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("❌ Sizga ruxsat yo'q.")
        return

    if not context.args:
        update.message.reply_text("Foydalanish:\n/get <user_id>")
        return

    user_id = context.args[0]

    try:
        chat = context.bot.get_chat(user_id)
    except Exception as e:
        update.message.reply_text(f"❌ Topilmadi yoki xato: {e}")
        return

    full_name = (chat.first_name or "") + " " + (chat.last_name or "")
    full_name = full_name.strip() or "(yo'q)"
    username = f"@{chat.username}" if chat.username else "(yo'q)"

    phone = user_phone_numbers.get(chat.id, "(telefon saqlanmagan)")

    text = f"""
<b>Natija:</b>
ID: <code>{chat.id}</code>
Username: {html.escape(username)}
Ism: {html.escape(full_name)}
Telefon: {html.escape(phone)}
"""

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get", get_user))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
