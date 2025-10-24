import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, InputMediaDocument

# ====== CONFIG ======
TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"
ADMIN_ID = 7973934849 # O'zingizni Telegram ID raqamingizni kiriting

bot = Bot(TOKEN)
dp = Dispatcher(bot)

# ====== DATABASE ======
db = sqlite3.connect("data.db", check_same_thread=False)
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS files (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 nom TEXT,
 file_id TEXT,
 kategoriya TEXT
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS settings (
 id INTEGER PRIMARY KEY,
 kanal TEXT
)
""")

sql.execute("INSERT OR IGNORE INTO settings (id, kanal) VALUES (1, NULL)")
db.commit()

# ====== OBUNA TEKSHIRISH ======
async def check_sub(user_id):
    sql.execute("SELECT kanal FROM settings WHERE id=1")
    kanal = sql.fetchone()[0]
    if kanal is None:
        return True
    try:
        member = await bot.get_chat_member(kanal, user_id)
        return member.status in ["member","administrator","creator"]
    except:
        return False

# ====== START ======
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    if not await check_sub(msg.from_user.id):
        sql.execute("SELECT kanal FROM settings WHERE id=1")
        kanal = sql.fetchone()[0]

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{kanal[1:]}"))
        kb.add(InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        return await msg.answer("⚠ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=kb)

    user = msg.from_user.first_name
    text = f"Assalomu alaykum, *{user}!* 👋\n\n" \
           "Siz bu bot orqali:\n" \
           "📷 *Romantik rasmlar*\n" \
           "🎥 *Romantik videolar*\n" \
           "📁 *Fayllar* va *Dramalar* topishingiz mumkin.\n\n" \
           "Quyidagi bo‘limlardan birini tanlang 👇"

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📷 Rasmlar", callback_data="rasm"),
        InlineKeyboardButton("📁 Fayllar", callback_data="fayl"),
        InlineKeyboardButton("🎥 Videolar", callback_data="video")
    )
    if msg.from_user.id == ADMIN_ID:
        kb.add(InlineKeyboardButton("🔐 Admin Panel", callback_data="admin"))

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def retry(call):
    await start(call.message)

# ====== NEXT / BACK ======
async def show_item(msg, items, index, cat):
    item = items[index]
    sql.execute("SELECT nom, file_id FROM files WHERE id=?", (item,))
    nom, fid = sql.fetchone()

    caption = f"{nom}\n\n{index+1} / {len(items)}"
    kb = InlineKeyboardMarkup()
    if index > 0: kb.insert(InlineKeyboardButton("⟵ Back", callback_data=f"back_{cat}_{index}"))
    if index < len(items)-1: kb.insert(InlineKeyboardButton("Next ⟶", callback_data=f"next_{cat}_{index}"))

    media = InputMediaPhoto(fid, caption) if cat=="rasm" else \
            InputMediaDocument(fid, caption) if cat=="fayl" else \
            InputMediaVideo(fid, caption)

    try:
        await msg.edit_media(media, reply_markup=kb)
    except:
        if cat=="rasm": await msg.answer_photo(fid, caption=caption, reply_markup=kb)
        elif cat=="fayl": await msg.answer_document(fid, caption=caption, reply_markup=kb)
        else: await msg.answer_video(fid, caption=caption, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data in ["rasm","fayl","video"])
async def open_cat(call):
    cat = call.data
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    items = [i[0] for i in sql.fetchall()]
    if not items: return await call.message.answer("📭 Hali yuklanmagan")
    await show_item(call.message, items, 0, cat)

@dp.callback_query_handler(lambda c: c.data.startswith("next_"))
async def nxt(call):
    _, cat, i = call.data.split("_"); i = int(i)+1
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    await show_item(call.message, [i[0] for i in sql.fetchall()], i, cat)

@dp.callback_query_handler(lambda c: c.data.startswith("back_"))
async def bck(call):
    _, cat, i = call.data.split("_"); i = int(i)-1
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    await show_item(call.message, [i[0] for i in sql.fetchall()], i, cat)

# ====== ADMIN PANEL ======
@dp.callback_query_handler(lambda c: c.data=="admin")
async def admin(call):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Rasm", callback_data="add_img"),
        InlineKeyboardButton("➕ Fayl", callback_data="add_fayl"),
        InlineKeyboardButton("➕ Video", callback_data="add_vid"),
    )
    kb.add(InlineKeyboardButton("🗑 Hammasini o‘chirish", callback_data="del_all"))
    kb.add(InlineKeyboardButton("📡 Kanal sozlash", callback_data="set_channel"))
    await call.message.answer("🔐 Admin Panel", reply_markup=kb)

# ====== KANAL SOZLASH ======
@dp.callback_query_handler(lambda c: c.data=="set_channel")
async def ask_ch(call):
    await call.message.answer("📡 Kanal username kiriting (masalan: @RomantikKanal):")
    dp.register_message_handler(save_ch, chat_id=call.from_user.id)

async def save_ch(msg):
    sql.execute("UPDATE settings SET kanal=? WHERE id=1",(msg.text.strip(),))
    db.commit()
    await msg.answer("✅ Kanal o‘rnatildi!")

# ====== CONTET QO‘SHISH ======
@dp.callback_query_handler(lambda c: c.data=="add_img")
async def add_img(call):
    await call.message.answer("📥 Rasm yuboring:")
    dp.register_message_handler(save_img, content_types=["photo"], chat_id=call.from_user.id)

async def save_img(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",("Romantic", msg.photo[-1].file_id,"rasm"))
    db.commit(); await msg.answer("✅ Rasm yuklandi!")

@dp.callback_query_handler(lambda c: c.data=="add_fayl")
async def add_f(call):
    await call.message.answer("📥 Fayl yuboring:")
    dp.register_message_handler(save_f, content_types=["document"], chat_id=call.from_user.id)

async def save_f(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",(msg.document.file_name,msg.document.file_id,"fayl"))
    db.commit(); await msg.answer("✅ Fayl yuklandi!")

@dp.callback_query_handler(lambda c: c.data=="add_vid")
async def add_v(call):
    await call.message.answer("📥 Video yuboring:")
    dp.register_message_handler(save_v, content_types=["video"], chat_id=call.from_user.id)

async def save_v(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",
                (msg.video.file_name or "video", msg.video.file_id,"video"))
    db.commit(); await msg.answer("✅ Video yuklandi!")

# ====== DELETE ALL ======
@dp.callback_query_handler(lambda c: c.data=="del_all")
async def del_all(call):
    sql.execute("DELETE FROM files"); db.commit()
    await call.message.answer("🗑 Hammasi o‘chirildi!")

# ====== RUN BOT ======
executor.start_polling(dp, skip_updates=True)
