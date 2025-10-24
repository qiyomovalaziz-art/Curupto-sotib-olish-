import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"  # <-- YANGI TOKEN BU YERGA
ADMIN_ID = 7973934849         # <-- ADMIN ID BU YERGA

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ===== BAZA =====
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


# ===== OBUNA TEKSHIRISH =====
async def check_sub(user_id):
    sql.execute("SELECT kanal FROM settings WHERE id = 1")
    kanal = sql.fetchone()[0]

    if kanal is None:
        return True

    try:
        member = await bot.get_chat_member(kanal, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# ===== START =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    if not await check_sub(msg.from_user.id):
        sql.execute("SELECT kanal FROM settings WHERE id = 1")
        kanal = sql.fetchone()[0]

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{kanal[1:]}"))
        kb.add(InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        await msg.answer("⚠ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=kb)
        return

    user = msg.from_user.first_name

    matn = f"Assalomu alaykum, *{user}!* 👋\n\n" \
           "Siz bu bot orqali:\n" \
           "📷 *Romantik rasmlar*\n" \
           "🎥 *Romantik videolar*\n" \
           "📁 *Fayllar* va *Dramalar* topishingiz mumkin.\n\n" \
           "Quyidagi bo‘limlardan birini tanlang 👇"

    menu = InlineKeyboardMarkup()
    menu.add(
        InlineKeyboardButton("📷 Rasmlar", callback_data="rasmlar"),
        InlineKeyboardButton("📁 Fayllar", callback_data="fayllar"),
        InlineKeyboardButton("🎥 Videolar", callback_data="videolar")
    )

    if msg.from_user.id == ADMIN_ID:
        menu.add(InlineKeyboardButton("🔐 Admin Panel", callback_data="admin"))

    await msg.answer(matn, reply_markup=menu, parse_mode="Markdown")


@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def retry(call: types.CallbackQuery):
    await start(call.message)


# ===== FOYDALANUVCHI BO‘LIMLARI =====
@dp.callback_query_handler(lambda c: c.data in ["rasmlar","fayllar","videolar"])
async def show_list(call: types.CallbackQuery):
    cat = {"rasmlar": "rasm", "fayllar": "fayl", "videolar": "video"}[call.data]
    sql.execute("SELECT id, nom FROM files WHERE kategoriya=?", (cat,))
    rows = sql.fetchall()

    if not rows:
        await call.message.answer("📭 Hozircha hech narsa yo‘q.")
        return

    kb = InlineKeyboardMarkup()
    for id, nom in rows:
        kb.add(InlineKeyboardButton(nom, callback_data=f"open_{id}"))

    await call.message.answer("Tanlang:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("open_"))
async def open_file(call: types.CallbackQuery):
    item_id = call.data.split("_")[1]
    sql.execute("SELECT nom, file_id, kategoriya FROM files WHERE id = ?", (item_id,))
    nom, file_id, cat = sql.fetchone()

    if cat == "rasm":
        await call.message.answer_photo(file_id, caption=nom)
    elif cat == "fayl":
        await call.message.answer_document(file_id, caption=nom)
    else:
        await call.message.answer_video(file_id, caption=nom)


# ===== ADMIN PANEL =====
@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Rasm", callback_data="add_img"),
        InlineKeyboardButton("➕ Fayl", callback_data="add_fayl"),
        InlineKeyboardButton("➕ Video", callback_data="add_vid"),
    )
    kb.add(InlineKeyboardButton("🗑 Bittalab o‘chirish", callback_data="del_one"))
    kb.add(InlineKeyboardButton("❌ Hammasini o‘chirish", callback_data="del_all"))
    kb.add(InlineKeyboardButton("📡 Kanalni sozlash", callback_data="set_channel"))
    await call.message.answer("🔐 Admin Panel", reply_markup=kb)


# ===== KANAL SOZLASH =====
@dp.callback_query_handler(lambda c: c.data == "set_channel")
async def ask_channel(call):
    await call.message.answer("📡 Kanal username kiriting (masalan: @MyKanal):")
    dp.register_message_handler(save_channel, chat_id=call.from_user.id)

async def save_channel(msg):
    sql.execute("UPDATE settings SET kanal=? WHERE id=1", (msg.text.strip(),))
    db.commit()
    await msg.answer("✅ Kanal o‘rnatildi!")


# ===== FAYLLARNI SAQLASH =====
@dp.callback_query_handler(lambda c: c.data == "add_img")
async def add_img(call):
    await call.message.answer("📥 Rasm yuboring:")
    dp.register_message_handler(save_img, content_types=['photo'], chat_id=call.from_user.id)

async def save_img(msg):
    file_id = msg.photo[-1].file_id
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)", ("rasm.jpg", file_id, "rasm"))
    db.commit()
    await msg.answer("✅ Rasm saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_fayl")
async def add_fayl(call):
    await call.message.answer("📥 Fayl yuboring:")
    dp.register_message_handler(save_fayl, content_types=['document'], chat_id=call.from_user.id)

async def save_fayl(msg):
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)",
                (msg.document.file_name, msg.document.file_id, "fayl"))
    db.commit()
    await msg.answer("✅ Fayl saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_vid")
async def add_vid(call):
    await call.message.answer("📥 Video yuboring:")
    dp.register_message_handler(save_vid, content_types=['video'], chat_id=call.from_user.id)

async def save_vid(msg):
    nom = msg.video.file_name if msg.video.file_name else "video.mp4"
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)", (nom, msg.video.file_id, "video"))
    db.commit()
    await msg.answer("✅ Video saqlandi!")


# ===== O‘CHIRISH =====
@dp.callback_query_handler(lambda c: c.data == "del_one")
async def del_one(call):
    sql.execute("SELECT id, nom FROM files")
    rows = sql.fetchall()

    kb = InlineKeyboardMarkup()
    for id, nom in rows:
        kb.add(InlineKeyboardButton(f"🗑 {nom}", callback_data=f"delete_{id}"))

    await call.message.answer("Qaysi faylni o‘chiramiz?", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_one(call):
    sql.execute("DELETE FROM files WHERE id=?", (call.data.split("_")[1],))
    db.commit()
    await call.message.answer("✅ O‘chirildi!")


@dp.callback_query_handler(lambda c: c.data == "del_all")
async def del_all(call):
    sql.execute("DELETE FROM files")
    db.commit()
    await call.message.answer("❌ Hammasi o‘chirildi!")


executor.start_polling(dp, skip_updates=True)


# ===== ADMIN PANEL =====
@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Rasm", callback_data="add_img"),
        InlineKeyboardButton("➕ Fayl", callback_data="add_fayl"),
        InlineKeyboardButton("➕ Video", callback_data="add_vid"),
    )
    kb.add(InlineKeyboardButton("🗑 Bittalab o‘chirish", callback_data="del_one"))
    kb.add(InlineKeyboardButton("❌ Hammasini o‘chirish", callback_data="del_all"))
    kb.add(InlineKeyboardButton("📡 Kanalni sozlash", callback_data="set_channel"))
    await call.message.answer("🔐 Admin Panel", reply_markup=kb)


# ===== KANAL SOZLASH =====
@dp.callback_query_handler(lambda c: c.data == "set_channel")
async def ask_channel(call: types.CallbackQuery):
    await call.message.answer("📡 Kanal username kiriting (masalan: @MyKanal):")
    dp.register_message_handler(save_channel, chat_id=call.from_user.id)


async def save_channel(msg: types.Message):
    sql.execute("UPDATE settings SET kanal=? WHERE id=1", (msg.text.strip(),))
    db.commit()
    await msg.answer("✅ Kanal o‘rnatildi!")


# ===== FAYLLARNI SAQLASH =====
@dp.callback_query_handler(lambda c: c.data == "add_img")
async def add_img(call):
    await call.message.answer("📥 Rasm yuboring:")
    dp.register_message_handler(save_img, content_types=['photo'], chat_id=call.from_user.id)

async def save_img(msg):
    file_id = msg.photo[-1].file_id
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)", ("rasm.jpg", file_id, "rasm"))
    db.commit()
    await msg.answer("✅ Rasm saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_fayl")
async def add_fayl(call):
    await call.message.answer("📥 Fayl yuboring:")
    dp.register_message_handler(save_fayl, content_types=['document'], chat_id=call.from_user.id)

async def save_fayl(msg):
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)",
                (msg.document.file_name, msg.document.file_id, "fayl"))
    db.commit()
    await msg.answer("✅ Fayl saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_vid")
async def add_vid(call):
    await call.message.answer("📥 Video yuboring:")
    dp.register_message_handler(save_vid, content_types=['video'], chat_id=call.from_user.id)

async def save_vid(msg):
    nom = msg.video.file_name if msg.video.file_name else "video.mp4"
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)", (nom, msg.video.file_id, "video"))
    db.commit()
    await msg.answer("✅ Video saqlandi!")


# ===== O‘CHIRISH =====
@dp.callback_query_handler(lambda c: c.data == "del_one")
async def del_one(call):
    sql.execute("SELECT id, nom FROM files")
    rows = sql.fetchall()

    kb = InlineKeyboardMarkup()
    for id, nom in rows:
        kb.add(InlineKeyboardButton(f"🗑 {nom}", callback_data=f"delete_{id}"))

    await call.message.answer("Qaysi faylni o‘chiramiz?", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_one(call):
    sql.execute("DELETE FROM files WHERE id=?", (call.data.split("_")[1],))
    db.commit()
    await call.message.answer("✅ O‘chirildi!")


@dp.callback_query_handler(lambda c: c.data == "del_all")
async def del_all(call):
    sql.execute("DELETE FROM files")
    db.commit()
    await call.message.answer("❌ Hammasi o‘chirildi!")


executor.start_polling(dp, skip_updates=True)
