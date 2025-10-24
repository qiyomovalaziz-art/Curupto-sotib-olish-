import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ====================
#  CONFIG
# ====================
TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"
ADMIN_ID = 7973934849

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ====================
#  DATABASE
# ====================
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


# ====================
#  OBUNA TEKSHIRISH
# ====================
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


# ====================
#  START COMMAND
# ====================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    if not await check_sub(msg.from_user.id):
        sql.execute("SELECT kanal FROM settings WHERE id = 1")
        kanal = sql.fetchone()[0]

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{kanal[1:]}"))
        kb.add(InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        return await msg.answer("⚠ Kanalga obuna bo‘ling!", reply_markup=kb)

    menu = InlineKeyboardMarkup()
    menu.add(
        InlineKeyboardButton("📷 Rasmlar", callback_data="rasmlar"),
        InlineKeyboardButton("📁 Fayllar", callback_data="fayllar"),
        InlineKeyboardButton("🎥 Videolar", callback_data="videolar")
    )

    if msg.from_user.id == ADMIN_ID:
        menu.add(InlineKeyboardButton("🔐 Admin Panel", callback_data="admin"))

    await msg.answer("Kerakli bo‘limni tanlang 👇", reply_markup=menu)


@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def retry(call):
    await start(call.message)


# ====================
#  PAGINATSIYA BILAN KO‘RSATISH
# ====================
async def show_item(msg, items, index, cat):
    item_id = items[index]
    sql.execute("SELECT nom, file_id FROM files WHERE id=?", (item_id,))
    nom, file_id = sql.fetchone()

    kb = InlineKeyboardMarkup()
    if index > 0:
        kb.insert(InlineKeyboardButton("⟵ back", callback_data=f"back_{cat}_{index}"))
    if index < len(items) - 1:
        kb.insert(InlineKeyboardButton("next ⟶", callback_data=f"next_{cat}_{index}"))

    text = f"{nom}\n\n{index+1} / {len(items)}"

    if cat == "rasm":
        await msg.answer_photo(file_id, caption=text, reply_markup=kb)
    elif cat == "fayl":
        await msg.answer_document(file_id, caption=text, reply_markup=kb)
    else:
        await msg.answer_video(file_id, caption=text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data in ["rasmlar","fayllar","videolar"])
async def show_collection(call):
    cat = {"rasmlar": "rasm", "fayllar": "fayl", "videolar": "video"}[call.data]
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    items = [i[0] for i in sql.fetchall()]

    if not items:
        return await call.message.answer("📭 Hozircha fayllar mavjud emas.")

    await show_item(call.message, items, 0, cat)


@dp.callback_query_handler(lambda c: c.data.startswith("next_"))
async def next_item(call):
    _, cat, index = call.data.split("_")
    index = int(index) + 1

    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    items = [i[0] for i in sql.fetchall()]

    await show_item(call.message, items, index, cat)


@dp.callback_query_handler(lambda c: c.data.startswith("back_"))
async def back_item(call):
    _, cat, index = call.data.split("_")
    index = int(index) - 1

    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    items = [i[0] for i in sql.fetchall()]

    await show_item(call.message, items, index, cat)


# ====================
#  ADMIN PANEL
# ====================
@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin(call):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Rasm", callback_data="add_img"),
        InlineKeyboardButton("➕ Fayl", callback_data="add_fayl"),
        InlineKeyboardButton("➕ Video", callback_data="add_vid")
    )
    kb.add(InlineKeyboardButton("🗑 Hammasini o‘chirish", callback_data="del_all"))
    kb.add(InlineKeyboardButton("📡 Kanal sozlash", callback_data="set_channel"))
    await call.message.answer("🔐 Admin panel", reply_markup=kb)


# ===== Kanal Sozlash
@dp.callback_query_handler(lambda c: c.data == "set_channel")
async def ask_channel(call):
    await call.message.answer("Kanal username kiriting (masalan: @MyKanal):")
    dp.register_message_handler(save_channel, chat_id=call.from_user.id)

async def save_channel(msg):
    sql.execute("UPDATE settings SET kanal=? WHERE id=1", (msg.text.strip(),))
    db.commit()
    await msg.answer("✅ Kanal o‘rnatildi!")


# ===== Fayl Saqlash
@dp.callback_query_handler(lambda c: c.data == "add_img")
async def add_img(call):
    await call.message.answer("📥 Rasm yuboring:")
    dp.register_message_handler(save_img, content_types=["photo"], chat_id=call.from_user.id)

async def save_img(msg):
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)",
                ("rasm", msg.photo[-1].file_id, "rasm"))
    db.commit()
    await msg.answer("✅ Rasm saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_fayl")
async def add_fayl(call):
    await call.message.answer("📥 Fayl yuboring:")
    dp.register_message_handler(save_fayl, content_types=["document"], chat_id=call.from_user.id)

async def save_fayl(msg):
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)",
                (msg.document.file_name, msg.document.file_id, "fayl"))
    db.commit()
    await msg.answer("✅ Fayl saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_vid")
async def add_vid(call):
    await call.message.answer("📥 Video yuboring:")
    dp.register_message_handler(save_vid, content_types=["video"], chat_id=call.from_user.id)

async def save_vid(msg):
    nom = msg.video.file_name or "video.mp4"
    sql.execute("INSERT INTO files (nom, file_id, kategoriya) VALUES (?,?,?)",
                (nom, msg.video.file_id, "video"))
    db.commit()
    await msg.answer("✅ Video saqlandi!")


# ===== Hammasini O‘chirish
@dp.callback_query_handler(lambda c: c.data == "del_all")
async def del_all(call):
    sql.execute("DELETE FROM files")
    db.commit()
    await call.message.answer("🗑 Barcha fayllar o‘chirildi!")


# ====================
#  RUN BOT
# ====================
executor.start_polling(dp, skip_updates=True)
