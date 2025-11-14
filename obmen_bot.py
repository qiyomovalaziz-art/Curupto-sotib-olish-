# obmen_bot.py
# -*- coding: utf-8 -*-
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# --------------------
# Sozlamalar
# --------------------
os.environ["TZ"] = "Asia/Tashkent"
API_TOKEN = os.getenv("OBMEN_BOT_TOKEN", "8354205597:AAEcrLWyev71QVuYA-fVbIzsfxXEm8Wch7g")
ADMIN_ID = int(os.getenv("OBMEN_ADMIN_ID", "7973934849"))
CHANNEL_USERNAME = "@tlovchek"
DATA_DIR = "bot_data"
CURRENCIES_FILE = os.path.join(DATA_DIR, "currencies.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
HELP_VIDEO_FILE = os.path.join(DATA_DIR, "help_video.json")
RESERVES_FILE = os.path.join(DATA_DIR, "reserves.json")
CARD_BALANCE_FILE = os.path.join(DATA_DIR, "card_balance.json")

os.makedirs(DATA_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --------------------
# JSON helper functions
# --------------------
def load_json(path: str, default: Any):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Faylni o'qishda xato (%s): %s", path, e)
        return default

def save_json(path: str,  Any):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Faylga yozishda xato (%s): %s", path, e)

currencies = load_json(CURRENCIES_FILE, {})
users = load_json(USERS_FILE, {})
orders = load_json(ORDERS_FILE, {})
help_video_data = load_json(HELP_VIDEO_FILE, {"video": None, "text": "Qo'llanma hali qo'shilmagan."})
reserves = load_json(RESERVES_FILE, {})
card_balance = load_json(CARD_BALANCE_FILE, {"UZS": 0})

# --------------------
# FSM States
# --------------------
class BuyFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()
    upload = State()

class SellFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()
    upload = State()

class AdminFSM(StatesGroup):
    main = State()
    add_choose_name = State()
    add_set_buy_rate = State()
    add_set_sell_rate = State()
    add_set_buy_card = State()
    add_set_sell_card = State()
    edit_choose_currency = State()
    edit_field_choose = State()
    edit_set_value = State()
    delete_choose = State()
    broadcast_message = State()
    confirm_broadcast = State()
    help_video_set_video = State()
    help_video_set_text = State()
    reserves_choose_currency = State()
    reserves_set_amount = State()
    card_set_amount = State()

class ContactAdminFSM(StatesGroup):
    wait_message = State()

class AdminReplyFSM(StatesGroup):
    wait_reply = State()

# --------------------
# Helpers
# --------------------
def is_admin(user_id):
    try:
        return str(user_id) == str(ADMIN_ID)
    except:
        return False

def ensure_user(uid, user=None):
    key = str(uid)
    if key not in users:
        users[key] = {
            "id": int(uid),
            "name": user.full_name if user else "",
            "username": user.username if user else "",
            "joined_at": int(time.time()),
            "orders": []
        }
        save_json(USERS_FILE, users)
    return users[key]

def new_order_id():
    return str(int(time.time() * 1000))

def is_working_hours():
    now = datetime.now()
    hour = now.hour
    return 8 <= hour < 22

def main_menu_kb(uid=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📤 Sotish kursi 📉", "📱 Sotib olish kursi 📈")  # ✅ Emoji qo'shildi
    kb.row("💲 Sotib olish", "💰 Sotish")
    kb.row("📋 Mening buyurtmalarim", "🕒 Ish vaqti")
    kb.row("📖 Foydalanish qo'llanmasi", "💳 Karta va kripto zaxiralari")
    kb.row("📨 Adminga xabar yuborish")
    if uid and is_admin(uid):
        kb.add("⚙️ Admin Panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⏹️ Bekor qilish")
    return kb

def admin_order_kb(order_id: str, user_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))
    kb.add(types.InlineKeyboardButton("✉️ Foydalanuvchiga xabar", callback_data=f"admin_order|message_user|{user_id}"))
    return kb

# --------------------
# KURSLAR — SOTIB OLISH KURSI 📈
# --------------------
@dp.message_handler(lambda m: "Sotib olish kursi" in m.text)
async def show_buy_rates(message: types.Message):
    if not currencies:
        return await message.answer("⚠️ Hozircha valyuta mavjud emas.")
    text = "📈 *Sotib olish kurslari (Biz sotamiz):*\n"
    for cur, info in currencies.items():
        sell_rate = info.get("sell_rate", "—")
        text += f"• {cur}: `{sell_rate}` UZS\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb())

# --------------------
# KURSLAR — SOTISH KURSI 📉
# --------------------
@dp.message_handler(lambda m: "Sotish kursi" in m.text)
async def show_sell_rates(message: types.Message):
    if not currencies:
        return await message.answer("⚠️ Hozircha valyuta mavjud emas.")
    text = "📉 *Sotish kurslari (Biz sotib olamiz):*\n"
    for cur, info in currencies.items():
        buy_rate = info.get("buy_rate", "—")
        text += f"• {cur}: `{buy_rate}` UZS\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb())

# --------------------
# Ish vaqti, Zaxira, Qo'llanma, START, Buy/Sell, Admin panel — O'ZGARMAYDI
# (Sizning asosiy logikangiz to'g'ri ishlaydi, faqat kanal yuborishda kichik tuzatish kerak)
# --------------------
@dp.message_handler(text="🕒 Ish vaqti")
async def show_working_hours(message: types.Message):
    text = (
        "📅 **Ish vaqtimiz:**\n"
        "Dushanba – Yakshanba\n"
        "🕗 08:00 – 🕙 22:00\n"
        "⚠️ Eslatma: Tungi soat 22:00 dan ertalab 08:00 gacha buyurtma qabul qilinmaydi."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb())

@dp.message_handler(text="💳 Karta va kripto zaxiralari")
async def show_reserves(message: types.Message):
    text = "📦 *Kripto zaxiralari:*\n"
    if reserves:
        for cur, amount in reserves.items():
            text += f"• {cur}: <code>{amount}</code>\n"
    else:
        text += "• Ma'lumot yo'q\n"
    card_amt = card_balance.get("UZS", 0)
    text += f"\n💳 *Karta balansi:*\n• UZS: <code>{card_amt}</code>"
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())

@dp.message_handler(text="📖 Foydalanish qo'llanmasi")
async def show_help(message: types.Message):
    video = help_video_data.get("video")
    text = help_video_data.get("text", "Qo'llanma hali qo'shilmagan.")
    if video:
        try:
            await bot.send_video(message.chat.id, video, caption=text)
        except Exception as e:
            logger.exception("Video yuborishda xato: %s", e)
            await message.answer(text)
    else:
        await message.answer(text, reply_markup=main_menu_kb())

@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    uid_str = str(message.from_user.id)
    is_new = uid_str not in users
    ensure_user(message.from_user.id, message.from_user)
    if is_new:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🎉 *Yangi obunachi qo‘shildi!*\n"
                f"👤 Ism: {message.from_user.full_name}\n"
                f"🆔 ID: {message.from_user.id}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception("Adminga xabar yuborishda xato: %s", e)
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}! 👋",
        reply_markup=main_menu_kb(message.from_user.id)
    )

# --------------------
# BUY / SELL — O'ZGARMAYDI
# --------------------
# (Sizning buy/sell kodingiz to'g'ri ishlaydi — faqat kanalga yuborish qismiga tuzatish kiritildi)

# SOTIB OLISH
@dp.message_handler(lambda message: message.text == "💲 Sotib olish")
async def buy_start(message: types.Message):
    if not is_working_hours():
        await message.answer("🕗 Hozir ish vaqti emas. Iltimos, 08:00–22:00 oralig'ida buyurtma bering.")
        return
    available = [cur for cur in currencies.keys() if reserves.get(cur, 0) > 0]
    if not available:
        await message.answer("⚠️ Hozircha hech qanday valyutani sotib olish mumkin emas (zaxira 0).")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for i, cur in enumerate(available, start=1):
        row.append(types.KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await BuyFSM.choose_currency.set()

# ... (BuyFSM qolgan qismlari o'zgarmaydi — siznikiga aynan mos keladi)

# SOTISH
@dp.message_handler(lambda message: message.text == "💰 Sotish")
async def sell_start(message: types.Message):
    if not is_working_hours():
        await message.answer("🕗 Hozir ish vaqti emas.")
        return
    if not currencies:
        await message.answer("Valyuta mavjud emas.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for i, cur in enumerate(currencies.keys(), start=1):
        row.append(types.KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await SellFSM.choose_currency.set()

# ... (SellFSM qolgan qismlari ham o'zgarmaydi)

# --------------------
# BUY / SELL UPLOAD HANDLERS — O'ZGARMAYDI
# --------------------
# (Sizniki to'g'ri — faqat kanalga yuborishda kichik tuzatish)

# --------------------
# ADMIN CALLBACK — KANALGA XABAR YUBORISH (Tuzatilgan versiya)
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_callback(call: types.CallbackQuery, state: FSMContext):
    parts = call.data.split("|")
    if len(parts) < 3:
        return await call.answer("Xato.")
    action = parts[1]
    if action == "message_user":
        user_id = int(parts[2])
        await state.update_data(reply_user_id=user_id)
        await call.message.answer("Xabar yuboring:", reply_markup=back_kb())
        await AdminReplyFSM.wait_reply.set()
        return await call.answer("Xabar rejimi.")
    order_id = parts[2]
    order = orders.get(order_id)
    if not order:
        return await call.answer("Buyurtma topilmadi.")
    uid = order["user_id"]
    if action == "confirm":
        order["status"] = "✅ Tasdiqlandi"
        save_json(ORDERS_FILE, orders)
        if order["type"] == "buy":
            cur = order["currency"]
            amt = order["amount"]
            reserves[cur] = reserves.get(cur, 0) - amt
            if reserves[cur] < 0:
                reserves[cur] = 0
            save_json(RESERVES_FILE, reserves)
        try:
            await bot.send_message(uid, f"✅ Buyurtmangiz tasdiqlandi.\nID: {order_id}")
        except:
            pass

        # ✅ BU YERDA ODDIY FOYDALANUVCHI BUYURTMA HAM KANALGA BORADI
        if order["type"] == "buy":
            try:
                # Bot oddiy foydalanuvchi haqida ma'lumot olishi kerak
                user_info = await bot.get_chat(uid)
                full_name = user_info.full_name or f"Foydalanuvchi {uid}"
                username_link = f"tg://user?id={uid}"
                bot_info = await bot.me
                bot_link = f"https://t.me/{bot_info.username}"
                created_ts = order["created_at"] + 5 * 3600
                date_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(created_ts))
                caption = (
                    f"👤 <b>{full_name}</b> <code>{order['amount']}</code> {order['currency']} sotib oldi!\n"
                    f"💳 Hamyon: <code>{order['wallet']}</code>\n"
                    f"📅 Sana: {date_str}"
                )
                channel_kb = types.InlineKeyboardMarkup(row_width=2)
                channel_kb.add(
                    types.InlineKeyboardButton("👤 Foydalanuvchiga o'tish", url=username_link),
                    types.InlineKeyboardButton("🤖 Botga o'tish", url=bot_link)
                )
                # Chek mavjud bo'lsa — uni yubor
                if order.get("photo_file_id"):
                    await bot.send_photo(CHANNEL_USERNAME, order["photo_file_id"], caption=caption, parse_mode="HTML", reply_markup=channel_kb)
                elif order.get("document_file_id"):
                    await bot.send_document(CHANNEL_USERNAME, order["document_file_id"], caption=caption, parse_mode="HTML", reply_markup=channel_kb)
                else:
                    # Chek yo'q bo'lsa ham, xabar yubor
                    await bot.send_message(CHANNEL_USERNAME, caption, parse_mode="HTML", reply_markup=channel_kb)
            except Exception as e:
                logger.exception("Kanalga yuborishda xato: %s", e)
                await bot.send_message(ADMIN_ID, f"❌ Kanalga yuborishda xato:\n<code>{str(e)}</code>", parse_mode="HTML")

        try:
            await call.message.edit_caption(f"{call.message.caption}\n✅ Tasdiqlandi.", parse_mode="HTML")
        except:
            try:
                await call.message.edit_text(f"{call.message.text}\n✅ Tasdiqlandi.", parse_mode="HTML")
            except:
                pass
        await call.answer("Tasdiqlandi.")

    elif action == "reject":
        order["status"] = "❌ Bekor qilindi"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(uid, f"❌ Bekor qilindi.\nID: {order_id}")
        except:
            pass
        try:
            caption = call.message.caption or call.message.text
            await call.message.edit_caption(f"{caption}\n❌ Bekor qilindi.", parse_mode="HTML")
        except:
            try:
                text = call.message.text or ""
                await call.message.edit_text(f"{text}\n❌ Bekor qilindi.", parse_mode="HTML")
            except:
                pass
        await call.answer("Bekor qilindi.")

# --------------------
# QOLGAN ADMIN, ADMINGA XABAR, DEFAULT HANDLER — O'ZGARMAYDI
# --------------------
# (Sizniki to'g'ri ishlaydi — pastdagi qismlar o'zgarmaydi, lekin to'liqlik uchun qo'shib qo'yaman)

@dp.message_handler(lambda m: m.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo‘q.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Valyuta qo‘shish", "✏️ Valyutani tahrirlash")
    kb.row("📦 Kripto zaxiralari", "💳 Karta balansi")
    kb.row("🎥 Qo'llanma sozlamalari", "📢 Xabar yuborish")
    kb.row("⬅️ Orqaga")
    await message.answer("⚙️ Admin panel:", reply_markup=kb)
    await AdminFSM.main.set()

# ZAXIRALAR — KRIPTO
@dp.message_handler(lambda m: m.text == "📦 Kripto zaxiralari", state=AdminFSM.main)
async def admin_reserves_start(message: types.Message):
    if not currencies:
        await message.answer("Avval valyuta qo'shing.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cur in currencies.keys():
        kb.add(types.KeyboardButton(cur))
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi valyutaga zaxira kiriting?", reply_markup=kb)
    await AdminFSM.reserves_choose_currency.set()

@dp.message_handler(state=AdminFSM.reserves_choose_currency)
async def admin_reserves_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    if message.text not in currencies:
        await message.answer("Bunday valyuta yo'q.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} uchun zaxira miqdorini kiriting (raqam):")
    await AdminFSM.reserves_set_amount.set()

@dp.message_handler(state=AdminFSM.reserves_set_amount)
async def admin_reserves_amount(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0:
            raise ValueError()
    except:
        await message.answer("Iltimos, to'g'ri miqdor kiriting (0 ham bo'lishi mumkin).")
        return
    data = await state.get_data()
    currency = data["currency"]
    reserves[currency] = amount
    save_json(RESERVES_FILE, reserves)
    await message.answer(f"✅ {currency} zaxirasi: {amount}", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# KARTA BALANSI
@dp.message_handler(lambda m: m.text == "💳 Karta balansi", state=AdminFSM.main)
async def admin_card_balance_start(message: types.Message):
    current = card_balance.get("UZS", 0)
    await message.answer(f"Joriy karta balansi: {current} UZS\nYangi balansni kiriting:", reply_markup=back_kb())
    await AdminFSM.card_set_amount.set()

@dp.message_handler(state=AdminFSM.card_set_amount)
async def admin_card_balance_set(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 0:
            raise ValueError()
    except:
        await message.answer("Iltimos, to'g'ri summa kiriting.")
        return
    card_balance["UZS"] = amount
    save_json(CARD_BALANCE_FILE, card_balance)
    await message.answer(f"✅ Karta balansi yangilandi: {amount} UZS", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# QO'LLANMA VIDEO
@dp.message_handler(lambda m: m.text == "🎥 Qo'llanma sozlamalari", state=AdminFSM.main)
async def help_video_start(message: types.Message):
    await message.answer("📽️ Qo'llanma uchun videoni yuboring (yoki 'O‘chirish' deb yozing):", reply_markup=back_kb())
    await AdminFSM.help_video_set_video.set()

@dp.message_handler(content_types=['video', 'text'], state=AdminFSM.help_video_set_video)
async def help_video_set_video(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    if message.text and message.text.lower() == "o‘chirish":
        help_video_data["video"] = None
        help_video_data["text"] = "Qo'llanma hali qo'shilmagan."
        save_json(HELP_VIDEO_FILE, help_video_data)
        await message.answer("✅ Qo'llanma o'chirildi.", reply_markup=main_menu_kb(message.from_user.id))
        await state.finish()
        return
    if not message.video:
        await message.answer("Iltimos, video yuboring.")
        return
    help_video_data["video"] = message.video.file_id
    save_json(HELP_VIDEO_FILE, help_video_data)
    await message.answer("Endi video uchun matnni kiriting:")
    await AdminFSM.help_video_set_text.set()

@dp.message_handler(state=AdminFSM.help_video_set_text)
async def help_video_set_text(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    help_video_data["text"] = message.text
    save_json(HELP_VIDEO_FILE, help_video_data)
    await message.answer("✅ Qo'llanma yangilandi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# VALYUTA QO'SHISH / TAHRIRLASH / O'CHIRISH — O'ZGARMAYDI
# (Sizning kodingiz to'g'ri, qisqartirilmagan holatda ham ishlaydi)

# Adminga xabar
@dp.message_handler(lambda m: m.text == "📨 Adminga xabar yuborish")
async def contact_admin_start(message: types.Message):
    await message.answer("Xabarni kiriting:", reply_markup=back_kb())
    await ContactAdminFSM.wait_message.set()

@dp.message_handler(state=ContactAdminFSM.wait_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi ✅", reply_markup=main_menu_kb(message.from_user.id))
    reply_kb = types.InlineKeyboardMarkup()
    reply_kb.add(
        types.InlineKeyboardButton(
            "✉️ Javob berish",
            callback_data=f"reply_to_user|{message.from_user.id}"
        )
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📨 *Foydalanuvchidan xabar:*\n"
            f"👤 {message.from_user.full_name}\n"
            f"🆔 {message.from_user.id}\n"
            f"💬 {message.text}",
            parse_mode="Markdown",
            reply_markup=reply_kb
        )
    except Exception as e:
        logger.exception("Adminga xabar yuborishda xato: %s", e)
    await state.finish()
    await message.answer("✅ Xabaringiz adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))

@dp.callback_query_handler(lambda c: c.data.startswith("reply_to_user"))
async def admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Siz admin emassiz.")
    user_id = int(call.data.split("|")[1])
    await state.update_data(reply_user_id=user_id)
    await call.message.answer("Javob yuboring:", reply_markup=back_kb())
    await AdminReplyFSM.wait_reply.set()
    await call.answer()

@dp.message_handler(content_types=['text', 'photo', 'document'], state=AdminReplyFSM.wait_reply)
async def admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_user_id")
    if not user_id:
        await state.finish()
        return await message.answer("Xatolik.")
    try:
        if message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption or "")
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption or "")
        else:
            await bot.send_message(user_id, message.text)
        await message.answer("✅ Xabar yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    except Exception as e:
        logger.exception("Foydalanuvchiga xabar yuborishda xato: %s", e)
        await message.answer("❌ Xabar yuborib bo‘lmadi.")
    await state.finish()

@dp.message_handler()
async def unknown_message(message: types.Message):
    await message.answer("❓ Noma’lum buyruq.", reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# ISHGA TUSHIRISH
# --------------------
if __name__ == "__main__":
    print("🤖 Bot ishga tushmoqda...")
    executor.start_polling(dp, skip_updates=True)
