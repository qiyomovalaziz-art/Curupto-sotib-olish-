#!/usr/bin/env python3
# coding: utf-8

import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
import os

# ---------- SOZLAMALAR ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "<SENING_BOT_TOKEN>"
OWNER_ID = int(os.environ.get("OWNER_ID") or 123456789)  # o'zgartir: o'z user id'ingni qo'y
# ---------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Salom! Men ID→username tekshirish botiman.\n\n"
        "Foydalanish: /get <user_id>\n\n"
        "Eslatma: Bu buyruq faqat bot egasiga (owner) ochiq."
    )

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("Foydalanish: /get <user_id> — foydalanuvchi haqida ma'lumot beradi (ruxsat bilan).")

def get_user(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Faqat ownerga ruxsat
    if user.id != OWNER_ID:
        update.message.reply_text("Sizga ruxsat yo'q.")
        return

    # Parametr tekshirish
    if not context.args:
        update.message.reply_text("Iltimos: /get <user_id> formatida yuboring.")
        return

    target = context.args[0]
    try:
        # getChat ishlatamiz — foydalanuvchi bot bilan muloqot qilgan yoki bir xil guruhda bo'lsa ishlaydi
        chat = context.bot.get_chat(chat_id=target)
    except Exception as e:
        # Xato bo'lsa, foydali xabar qaytaramiz
        logger.exception("getChat xatosi")
        update.message.reply_text(f"Xato yoki ma'lumot topilmadi: {e}")
        return

    # Ma'lumotni formatlab yuborish
    username = getattr(chat, "username", None)
    first_name = getattr(chat, "first_name", "")
    last_name = getattr(chat, "last_name", "")
    full_name = (first_name + " " + last_name).strip()

    text = f"<b>Natija:</b>\n"
    text += f"ID: <code>{chat.id}</code>\n"
    if username:
        text += f"Username: @{username}\n"
    else:
        text += "Username: (yo'q)\n"
    text += f"Ism: {full_name if full_name else '(ma\'lumot yo\'q)'}\n"
    text += f"Type: {chat.type}\n"

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if update and update.effective_message:
            update.effective_message.reply_text("Ichki xato yuz berdi.")
    except Exception:
        pass

def main():
    if BOT_TOKEN is None or BOT_TOKEN == "" or OWNER_ID is None:
        print("Iltimos BOT_TOKEN va OWNER_ID sozlang (kod ichida yoki environment o'zgaruvchilar orqali).")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("get", get_user, pass_args=True))
    dp.add_error_handler(error_handler)

    print("Bot ishga tushmoqda... Ctrl+C bilan to'xtating.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
