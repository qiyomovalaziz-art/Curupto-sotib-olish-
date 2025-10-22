import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Tokenni Railway environment variables ichidan olish
TOKEN = os.getenv("API_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Bot muvaffaqiyatli ishga tushdi 🚀")

def main():
    if not TOKEN:
        raise Exception("❌ API_TOKEN topilmadi! Railway Settings → Environment Variables → API_TOKEN ni qo‘sh!")
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
from telegram import ReplyKeyboardMarkup

async def start(update: Update, context):
    keyboard = [
        ["💰 Sotib olish", "💸 Sotish"],
        ["⚙️ Admin panel"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Salom! Quyidagilardan birini tanlang:",
        reply_markup=reply_markup
    )
