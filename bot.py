import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo, InputMediaDocument

# ===== CONFIG =====
TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"
ADMIN_ID = 7973934849  # Admin ID

bot = Bot(TOKEN)
dp = Dispatcher(bot)

# ===== DATABASE =====
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
    sql.execute("SELECT kanal FROM settings WHERE id=1")
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
        sql.execute("SELECT kanal FROM settings WHERE id=1")
        kanal = sql.fetchone()[0]
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{kanal[1:]}"))
        kb.add(InlineKeyboardButton("🔄 Tekshirish", callback_data="check_sub"))
        return await msg.answer("⚠ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=kb)

    name = msg.from_user.first_name
    text = f"Assalomu alaykum, *{name}!* ❤️\n\n" \
           "Siz bu bot orqali:\n" \
           "📷 Romantik rasmlar\n" \
           "🎥 Romantik videolar\n" \
           "📁 Fayllar va Dramalar topishingiz mumkin.\n\n" \
           "Quyidagi bo‘limlardan birini tanlang 👇"

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("📷 Rasmlar", callback_data="rasm"),
        InlineKeyboardButton("📁 Fayllar", callback_data="fayl"),
        InlineKeyboardButton("🎥 Videolar", callback_data="video")
    )
    if msg.from_user.id == ADMIN_ID:
        kb.add(InlineKeyboardButton("🔐 Admin Panel", callback_data="admin"))

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# ===== NEXT / BACK =====
async def show_item(msg, items, index, cat):
    item = items[index]
    sql.execute("SELECT nom, file_id FROM files WHERE id=?", (item,))
    nom, fid = sql.fetchone()

    caption = f"{nom}\n\n{index+1} / {len(items)}"
    kb = InlineKeyboardMarkup()

    if index > 0:
        kb.insert(InlineKeyboardButton("⟵ Back", callback_data=f"back_{cat}_{index}"))
    if index < len(items) - 1:
        kb.insert(InlineKeyboardButton("Next ⟶", callback_data=f"next_{cat}_{index}"))

    if cat == "rasm":
        media = InputMediaPhoto(fid, caption)
    elif cat == "fayl":
        media = InputMediaDocument(fid, caption)
    else:
        media = InputMediaVideo(fid, caption)

    try:
        await msg.edit_media(media, reply_markup=kb)
    except:
        if cat == "rasm": await msg.answer_photo(fid, caption=caption, reply_markup=kb)
        elif cat == "fayl": await msg.answer_document(fid, caption=caption, reply_markup=kb)
        else: await msg.answer_video(fid, caption=caption, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data in ["rasm","fayl","video"])
async def open_cat(call):
    cat = call.data
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    items = [i[0] for i in sql.fetchall()]
    if not items:
        return await call.message.answer("📭 Bo‘lim bo‘sh")
    await show_item(call.message, items, 0, cat)


@dp.callback_query_handler(lambda c: c.data.startswith("next_"))
async def nxt(call):
    _, cat, i = call.data.split("_")
    i = int(i) + 1
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    await show_item(call.message, [x[0] for x in sql.fetchall()], i, cat)


@dp.callback_query_handler(lambda c: c.data.startswith("back_"))
async def back(call):
    _, cat, i = call.data.split("_")
    i = int(i) - 1
    sql.execute("SELECT id FROM files WHERE kategoriya=?", (cat,))
    await show_item(call.message, [x[0] for x in sql.fetchall()], i, cat)


# ===== ADMIN PANEL =====
@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin(call):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Rasm", callback_data="add_img"),
        InlineKeyboardButton("➕ Fayl", callback_data="add_fayl"),
        InlineKeyboardButton("➕ Video", callback_data="add_vid")
    )
    kb.add(
        InlineKeyboardButton("📡 Kanal qo‘shish", callback_data="set_channel"),
        InlineKeyboardButton("❌ Kanalni o‘chirish", callback_data="remove_channel")
    )
    kb.add(InlineKeyboardButton("🗑 Fayl / Video / Rasm o‘chirish", callback_data="del_file"))
    kb.add(InlineKeyboardButton("❌ Hammasini tozalash", callback_data="del_all"))

    await call.message.answer("🔐 Admin Panel", reply_markup=kb)


# ===== KANAL QO‘SHISH =====
@dp.callback_query_handler(lambda c: c.data == "set_channel")
async def ask_channel(call):
    await call.message.answer("📡 Kanal username kiriting (masalan: @RomantikKanal):")
    dp.register_message_handler(save_channel, chat_id=call.from_user.id)

async def save_channel(msg):
    sql.execute("UPDATE settings SET kanal=? WHERE id=1", (msg.text.strip(),))
    db.commit()
    await msg.answer("✅ Kanal qo‘shildi!")


# ===== KANAL O‘CHIRISH =====
@dp.callback_query_handler(lambda c: c.data == "remove_channel")
async def remove_channel(call):
    sql.execute("UPDATE settings SET kanal=NULL WHERE id=1")
    db.commit()
    await call.message.answer("❌ Kanal o‘chirildi!")


# ===== FAYL / RASM / VIDEO QO‘SHISH =====
@dp.callback_query_handler(lambda c: c.data == "add_img")
async def add_img(call):
    await call.message.answer("📥 Rasm yuboring:")
    dp.register_message_handler(save_img, content_types=["photo"], chat_id=call.from_user.id)

async def save_img(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",
                ("Romantic Rasm", msg.photo[-1].file_id, "rasm"))
    db.commit()
    await msg.answer("✅ Rasm saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_fayl")
async def add_fayl(call):
    await call.message.answer("📥 Fayl yuboring:")
    dp.register_message_handler(save_fayl, content_types=["document"], chat_id=call.from_user.id)

async def save_fayl(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",
                (msg.document.file_name, msg.document.file_id, "fayl"))
    db.commit()
    await msg.answer("✅ Fayl saqlandi!")


@dp.callback_query_handler(lambda c: c.data == "add_vid")
async def add_vid(call):
    await call.message.answer("📥 Video yuboring:")
    dp.register_message_handler(save_vid, content_types=["video"], chat_id=call.from_user.id)

async def save_vid(msg):
    sql.execute("INSERT INTO files (nom,file_id,kategoriya) VALUES (?,?,?)",
                (msg.video.file_name or "Video", msg.video.file_id, "video"))
    db.commit()
    await msg.answer("✅ Video saqlandi!")


# ===== FAYL O‘CHIRISH =====
@dp.callback_query_handler(lambda c: c.data == "del_file")
async def del_file(call):
    sql.execute("SELECT id, nom FROM files")
    rows = sql.fetchall()
    kb = InlineKeyboardMarkup()
    for r in rows:
        kb.add(InlineKeyboardButton(f"🗑 {r[1]}", callback_data=f"delete_{r[0]}"))
    await call.message.answer("Qaysi faylni o‘chiramiz?", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_one(call):
    sql.execute("DELETE FROM files WHERE id=?", (call.data.split("_")[1],))
    db.commit()
    await call.message.answer("✅ O‘chirildi!")


# ===== HAMMASINI TOZALASH =====
@dp.callback_query_handler(lambda c: c.data == "del_all")
async def del_all(call):
    sql.execute("DELETE FROM files")
    db.commit()
    await call.message.answer("🗑 Hammasi tozalandi!")


# ===== RUN =====
executor.start_polling(dp, skip_updates=True)
