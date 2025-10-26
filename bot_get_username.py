#!/usr/bin/env python3
# coding: utf-8

import logging
import os
import html
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext

# ---------- SOZLAMALAR ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "<SENING_BOT_TOKEN>"
OWNER_ID = int(os.environ.get("OWNER_ID") or 123456789)  # O'ZGARTIR
# ---------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Salom! Men ID → Username aniqlovchi botman.\n\n"
        "Foydalanish: /get <user_id>\n\n"
        "Bu komanda faqat bot egasiga ruxsat etilgan."
    )


def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("Foydalanish: /get <user_id>")


def get_user(update: Update, context: CallbackContext):
    user = update.effective_user

    if user.id != OWNER_ID:
        update.message.reply_text("❌ Sizda ruxsat yo‘q.")
        return

    if not context.args:
        update.message.reply_text("Iltimos: /get <user_id> shaklida yuboring.")
        return

    target_id = context.args[0]

    try:
        chat = context.bot.get_chat(chat_id=target_id)
    except Exception as e:
        update.message.reply_text(f"Xato yoki ma'lumot topilmadi:\n\n{e}")
        return

    username = chat.username
    first_name = getattr(chat, "first_name", "")
    last_name = getattr(chat, "last_name", "")
    name_display = (first_name + " " + last_name).strip()

    text = (
        f"<b>Natija:</b>\n"
        f"ID: <code>{html.escape(str(chat.id))}</code>\n"
        f"Username: @{html.escape(username) if username else 'yo‘q'}\n"
        f"Ism: {html.escape(name_display) if name_display else 'yo‘q'}\n"
        f"Type: {html.escape(str(chat.type))}\n"
    )

    update.message.reply_text(text, parse_mode=ParseMode.HTML)


def error_handler(update: Update, context: CallbackContext):
    logger.error("Xato yuz berdi:", exc_info=context.error)


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN kiritilmagan!")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("get", get_user, pass_args=True))
    dp.add_error_handler(error_handler)

    print("✅ Bot ishga tushdi... Ctrl+C bilan to‘xtatish mumkin.")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
