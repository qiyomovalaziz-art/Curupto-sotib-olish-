# obmen_bot.py — to'liq, ishlaydigan versiya
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

def save_json(path: str, data: Any):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Faylga yozishda xato (%s): %s", path, e)

# --------------------
# Ma'lumotlarni yuklash
# --------------------
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
    add_choose_code = State()
    add_choose_name = State()
    add_set_buy_rate = State()
    add_set_sell_rate = State()
    add_set_buy_card = State()
    add_set_sell_card = State()
    edit_choose_currency = State()
    edit_field_choose = State()
    edit_set_value = State()
    delete_choose = State()
    reserves_choose_currency = State()
    reserves_set_amount = State()
    card_set_amount = State()
    broadcast_choose = State()
    broadcast_target = State()
    broadcast_media = State()
    help_video_set_video = State()
    help_video_set_text = State()

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
    kb.row("📤 Sotish kursi 📉", "📱 Sotib olish kursi 📈")
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
# KURSLAR — TO'G'RI
# --------------------
@dp.message_handler(lambda m: "Sotib olish kursi" in m.text)
async def show_buy_rates(message: types.Message):
    if not currencies:
        return await message.answer("⚠️ Hozircha valyuta mavjud emas.")
    text = "✅ Bizning sotishimiz kursimiz:\n"
    for code, info in currencies.items():
        name = info.get("name", code)
        sell_rate = info.get("sell_rate", "—")
        try:
            formatted = f"{float(sell_rate):,}".replace(",", " ")
        except:
            formatted = str(sell_rate)
        text += f"{code} — {name}: {formatted} UZS\n"
    await message.answer(text, reply_markup=main_menu_kb())

@dp.message_handler(lambda m: "Sotish kursi" in m.text)
async def show_sell_rates(message: types.Message):
    if not currencies:
        return await message.answer("⚠️ Hozircha valyuta mavjud emas.")
    text = "✅ Bizga quyidagi narxlarda valyutalaringizni sotishingiz mumkin:\n"
    for code, info in currencies.items():
        name = info.get("name", code)
        buy_rate = info.get("buy_rate", "—")
        try:
            formatted = f"{float(buy_rate):,}".replace(",", " ")
        except:
            formatted = str(buy_rate)
        text += f"{code} — {name}: {formatted} UZS\n"
    await message.answer(text, reply_markup=main_menu_kb())

# --------------------
# Ish vaqti
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

# --------------------
# ZAXIRALAR
# --------------------
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

# --------------------
# QO'LLANMA
# --------------------
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

# --------------------
# START
# --------------------
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
# BUYURTMA TARIXI
# --------------------
@dp.message_handler(text="📋 Mening buyurtmalarim")
async def my_orders(message: types.Message):
    uid = str(message.from_user.id)
    ensure_user(message.from_user.id, message.from_user)
    user_orders = users.get(uid, {}).get("orders", [])
    if not user_orders:
        return await message.answer("📭 Sizda buyurtmalar mavjud emas.", reply_markup=main_menu_kb(uid))
    text = "🧾 *Sizning so‘nggi buyurtmalaringiz:*\n"
    for oid in user_orders[-10:][::-1]:
        o = orders.get(oid)
        if not o:
            continue
        created = o["created_at"] + 5 * 3600
        date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created))
        text += (
            f"ID: `{o['id']}`\n"
            f"Turi: {o['type']}\n"
            f"Valyuta: {o['currency']}\n"
            f"Miqdor: {o['amount']}\n"
            f"Holat: {o.get('status', '—')}\n"
            f"Yaratilgan: {date_str}\n"
            f"———————————————\n"
        )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb(uid))

# --------------------
# SOTIB OLISH (foydalanuvchi sotib oladi → biz sotamiz → sell_rate)
# --------------------
@dp.message_handler(lambda m: m.text == "💲 Sotib olish")
async def buy_start(message: types.Message):
    if not is_working_hours():
        return await message.answer("🕗 Hozir ish vaqti emas.")
    available = [cur for cur in currencies.keys() if reserves.get(cur, 0) > 0]
    if not available:
        return await message.answer("⚠️ Zaxira yetarli emas.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cur in available:
        kb.add(cur)
    kb.add("⏹️ Bekor qilish")
    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await BuyFSM.choose_currency.set()

@dp.message_handler(state=BuyFSM.choose_currency)
async def buy_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    if message.text not in currencies:
        return await message.answer("Bunday valyuta yo'q.")
    await state.update_data(currency=message.text)
    await message.answer("Miqdorni kiriting:")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.amount)
async def buy_amount(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    try:
        amt = float(message.text.replace(",", "."))
        if amt <= 0: raise ValueError()
    except:
        return await message.answer("Iltimos, to'g'ri miqdor kiriting.")
    data = await state.get_data()
    currency = data.get("currency")
    if not currency:
        await state.finish()
        return await message.answer("Xatolik.")
    if amt > reserves.get(currency, 0):
        return await message.answer(f"Zaxira yetarli emas. Mavjud: {reserves.get(currency, 0)}")
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:", reply_markup=back_kb())
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.wallet)
async def buy_wallet(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    await state.update_data(wallet=message.text.strip())
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]
    info = currencies[currency]
    rate = info.get("sell_rate")
    if not rate:
        await state.finish()
        return await message.answer("Narx ma'lum emas.")
    total = round(amt * float(rate), 2)
    card = info.get("sell_card", "5614 6818 7267 2690")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("Chek yuborish")
    kb.add("⏹️ Bekor qilish")
    await message.answer(
        f"🔔 To'lov tafsilotlari:\nKarta: {card}\nValyuta: {currency}\nMiqdor: {amt}\nNarx: {rate}\nJami: {total} UZS",
        reply_markup=kb
    )
    await BuyFSM.confirm.set()

@dp.message_handler(state=BuyFSM.confirm)
async def buy_confirm(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    if message.text != "Chek yuborish":
        return await message.answer("‘Chek yuborish’ tugmasini bosing.")
    await message.answer("✅ Chekni yuboring:", reply_markup=back_kb())
    await BuyFSM.upload.set()

@dp.message_handler(content_types=['photo', 'document'], state=BuyFSM.upload)
async def buy_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = new_order_id()
    order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "currency": data["currency"],
        "amount": data["amount"],
        "wallet": data["wallet"],
        "type": "buy",
        "status": "waiting_admin",
        "created_at": int(time.time()),
        "rate": currencies[data["currency"]]["sell_rate"],
        "photo_file_id": message.photo[-1].file_id if message.photo else None,
        "document_file_id": message.document.file_id if message.document else None,
    }
    orders[order_id] = order
    uid = str(message.from_user.id)
    users.setdefault(uid, ensure_user(message.from_user.id, message.from_user))
    users[uid].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)
    caption = (
        f"🆕 Yangi BUY buyurtma\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Valyuta: {data['currency']}\n"
        f"Miqdor: {data['amount']}\n"
        f"Hamyon: {data['wallet']}\n"
        f"Buyurtma ID: {order_id}"
    )
    kb = admin_order_kb(order_id, message.from_user.id)
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        else:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.exception("Adminga yuborishda xato: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")
        await state.finish()
        return
    await message.answer("✅ Chek adminga yuborildi.", reply_markup=main_menu_kb())
    await state.finish()

# --------------------
# SOTISH (foydalanuvchi sotadi → biz sotib olamiz → buy_rate)
# --------------------
@dp.message_handler(lambda m: m.text == "💰 Sotish")
async def sell_start(message: types.Message):
    if not is_working_hours():
        return await message.answer("🕗 Hozir ish vaqti emas.")
    if not currencies:
        return await message.answer("Valyuta yo'q.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cur in currencies:
        kb.add(cur)
    kb.add("⏹️ Bekor qilish")
    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await SellFSM.choose_currency.set()

@dp.message_handler(state=SellFSM.choose_currency)
async def sell_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    if message.text not in currencies:
        return await message.answer("Bunday valyuta yo'q.")
    await state.update_data(currency=message.text)
    await message.answer("Miqdorni kiriting:")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.amount)
async def sell_amount(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    try:
        amt = float(message.text.replace(",", "."))
        if amt <= 0: raise ValueError()
    except:
        return await message.answer("Iltimos, to'g'ri miqdor kiriting.")
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:", reply_markup=back_kb())
    await SellFSM.next()

@dp.message_handler(state=SellFSM.wallet)
async def sell_wallet(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    await state.update_data(wallet=message.text.strip())
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]
    info = currencies[currency]
    rate = info.get("buy_rate")
    if not rate:
        await state.finish()
        return await message.answer("Narx ma'lum emas.")
    total = round(amt * float(rate), 2)
    card = info.get("buy_card", "5614 6818 7267 2690")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("Chek yuborish")
    kb.add("⏹️ Bekor qilish")
    await message.answer(
        f"🔔 To'lov tafsilotlari:\nKarta: {card}\nValyuta: {currency}\nMiqdor: {amt}\nNarx: {rate}\nJami: {total} UZS",
        reply_markup=kb
    )
    await SellFSM.confirm.set()

@dp.message_handler(state=SellFSM.confirm)
async def sell_confirm(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    if message.text != "Chek yuborish":
        return await message.answer("‘Chek yuborish’ tugmasini bosing.")
    await message.answer("✅ Chekni yuboring:", reply_markup=back_kb())
    await SellFSM.upload.set()

@dp.message_handler(content_types=['photo', 'document'], state=SellFSM.upload)
async def sell_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = new_order_id()
    order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "currency": data["currency"],
        "amount": data["amount"],
        "wallet": data["wallet"],
        "type": "sell",
        "status": "waiting_admin",
        "created_at": int(time.time()),
        "rate": currencies[data["currency"]]["buy_rate"],
        "photo_file_id": message.photo[-1].file_id if message.photo else None,
        "document_file_id": message.document.file_id if message.document else None,
    }
    orders[order_id] = order
    uid = str(message.from_user.id)
    users.setdefault(uid, ensure_user(message.from_user.id, message.from_user))
    users[uid].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)
    caption = (
        f"🆕 Yangi SELL buyurtma\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Valyuta: {data['currency']}\n"
        f"Miqdor: {data['amount']}\n"
        f"Hamyon: {data['wallet']}\n"
        f"Buyurtma ID: {order_id}"
    )
    kb = admin_order_kb(order_id, message.from_user.id)
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        else:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.exception("Adminga yuborishda xato: %s", e)
        await message.answer("❌ Xatolik yuz berdi.")
        await state.finish()
        return
    await message.answer("✅ Chek adminga yuborildi.", reply_markup=main_menu_kb())
    await state.finish()

# --------------------
# ADMIN CALLBACK — TO'LIQ ISHLOVCHI
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_callback(call: types.CallbackQuery):
    parts = call.data.split("|")
    if len(parts) < 3:
        return await call.answer("Xato.")
    action = parts[1]
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
        if order["type"] == "buy":
            try:
                user = await bot.get_chat(uid)
                full_name = user.full_name or f"Foydalanuvchi {uid}"
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
                if order.get("photo_file_id"):
                    await bot.send_photo(CHANNEL_USERNAME, order["photo_file_id"], caption=caption, parse_mode="HTML", reply_markup=channel_kb)
                elif order.get("document_file_id"):
                    await bot.send_document(CHANNEL_USERNAME, order["document_file_id"], caption=caption, parse_mode="HTML", reply_markup=channel_kb)
                else:
                    await bot.send_message(CHANNEL_USERNAME, caption, parse_mode="HTML", reply_markup=channel_kb)
            except Exception as e:
                logger.exception("Kanalga yuborishda xato: %s", e)
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
    elif action == "message_user":
        user_id = int(parts[2])
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Javob yuborish", callback_data=f"reply_to_user|{user_id}"))
        await call.message.answer("Javob yuborish uchun tugmani bosing:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("reply_to_user"))
async def admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("Siz admin emassiz.")
    user_id = int(call.data.split("|")[1])
    await state.update_data(reply_user_id=user_id)
    await call.message.answer("Javobingizni yuboring:", reply_markup=back_kb())
    await AdminReplyFSM.wait_reply.set()

@dp.message_handler(content_types=types.ContentTypes.ANY, state=AdminReplyFSM.wait_reply)
async def admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reply_user_id")
    if not user_id:
        await state.finish()
        return await message.answer("Xatolik.")
    try:
        if message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption or "")
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=message.caption or "")
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption or "")
        else:
            await bot.send_message(user_id, message.text)
        await message.answer("✅ Javob yuborildi.", reply_markup=main_menu_kb())
    except:
        await message.answer("❌ Yuborilmadi.")
    await state.finish()

# --------------------
# ADMIN PANEL — TO'LIQ
# --------------------
@dp.message_handler(lambda m: m.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Sizda admin huquqi yo‘q.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Valyuta qo‘shish", "✏️ Valyutani tahrirlash")
    kb.row("🗑️ Valyutani o‘chirish", "📄 Valyutalar ro‘yxati")
    kb.row("📦 Kripto zaxiralari", "💳 Karta balansi")
    kb.row("🎥 Qo'llanma sozlamalari", "📩 Foydalanuvchilarga xabar")
    kb.row("⬅️ Orqaga")
    await message.answer("⚙️ Admin panel:", reply_markup=kb)
    await AdminFSM.main.set()

# VALYUTA QO'SHISH — KOD + NOM
@dp.message_handler(lambda m: m.text == "➕ Valyuta qo‘shish", state=AdminFSM.main)
async def add_currency_code(message: types.Message):
    await message.answer("Valyuta kodini kiriting (masalan: USDT):", reply_markup=back_kb())
    await AdminFSM.add_choose_code.set()

@dp.message_handler(state=AdminFSM.add_choose_code)
async def add_currency_code_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    code = message.text.strip().upper()
    if code in currencies:
        await message.answer("Bu valyuta allaqachon mavjud.")
        return
    await state.update_data(code=code)
    await message.answer(f"{code} uchun to'liq nomini kiriting (masalan: Tether):")
    await AdminFSM.add_choose_name.set()

@dp.message_handler(state=AdminFSM.add_choose_name)
async def add_currency_name_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer(f"**Sotib olish (buy)** kursini kiriting (UZS):")
    await AdminFSM.add_set_buy_rate.set()

@dp.message_handler(state=AdminFSM.add_set_buy_rate)
async def add_buy_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(buy_rate=rate)
    await message.answer("Endi **sotish (sell)** kursini kiriting (UZS):")
    await AdminFSM.add_set_sell_rate.set()

@dp.message_handler(state=AdminFSM.add_set_sell_rate)
async def add_sell_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(sell_rate=rate)
    await message.answer("Valyutani **sotib olish** kartasini kiriting:")
    await AdminFSM.add_set_buy_card.set()

@dp.message_handler(state=AdminFSM.add_set_buy_card)
async def add_buy_card(message: types.Message, state: FSMContext):
    await state.update_data(buy_card=message.text.strip())
    await message.answer("Endi **sotish** kartasini kiriting:")
    await AdminFSM.add_set_sell_card.set()

@dp.message_handler(state=AdminFSM.add_set_sell_card)
async def add_sell_card(message: types.Message, state: FSMContext):
    data = await state.get_data()
    currencies[data["code"]] = {
        "name": data["name"],
        "buy_rate": data["buy_rate"],
        "sell_rate": data["sell_rate"],
        "buy_card": data["buy_card"],
        "sell_card": message.text.strip()
    }
    save_json(CURRENCIES_FILE, currencies)
    if data["code"] not in reserves:
        reserves[data["code"]] = 0
        save_json(RESERVES_FILE, reserves)
    await message.answer(f"✅ {data['code']} — {data['name']} qo'shildi.", reply_markup=main_menu_kb())
    await state.finish()

# VALYUTANI TAHRIRLASH
@dp.message_handler(lambda m: m.text == "✏️ Valyutani tahrirlash", state=AdminFSM.main)
async def admin_edit_currency_start(message: types.Message):
    if not currencies:
        return await message.answer("Hech qanday valyuta mavjud emas.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in currencies.keys():
        kb.add(c)
    kb.add("⏹️ Bekor qilish")
    await message.answer("Tahrirlamoqchi bo‘lgan valyutani tanlang:", reply_markup=kb)
    await AdminFSM.edit_choose_currency.set()

@dp.message_handler(state=AdminFSM.edit_choose_currency)
async def admin_edit_currency_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    name = message.text.strip().upper()
    if name not in currencies:
        return await message.answer("Bunday valyuta topilmadi.")
    await state.update_data(currency=name)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("name", "buy_rate", "sell_rate")
    kb.row("buy_card", "sell_card")
    kb.add("⏹️ Bekor qilish")
    await message.answer("Qaysi maydonni tahrirlamoqchisiz?", reply_markup=kb)
    await AdminFSM.edit_field_choose.set()

@dp.message_handler(state=AdminFSM.edit_field_choose)
async def admin_edit_field_select(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    field = message.text.strip()
    if field not in ["name", "buy_rate", "sell_rate", "buy_card", "sell_card"]:
        return await message.answer("Noto‘g‘ri tanlov.")
    await state.update_data(field=field)
    await message.answer(f"Yangi qiymatni kiriting ({field}):")
    await AdminFSM.edit_set_value.set()

@dp.message_handler(state=AdminFSM.edit_set_value)
async def admin_edit_value_set(message: types.Message, state: FSMContext):
    data = await state.get_data()
    currency = data["currency"]
    field = data["field"]
    val = message.text.strip()
    if field in ["buy_rate", "sell_rate"]:
        try:
            val = float(val.replace(",", "."))
        except:
            return await message.answer("Raqam kiriting.")
    currencies[currency][field] = val
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"✅ {currency} valyutasi yangilandi ({field} = {val}).", reply_markup=main_menu_kb())
    await state.finish()

# VALYUTANI O'CHIRISH
@dp.message_handler(lambda m: m.text == "🗑️ Valyutani o‘chirish", state=AdminFSM.main)
async def admin_delete_currency(message: types.Message):
    if not currencies:
        return await message.answer("Valyutalar yo‘q.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in currencies.keys():
        kb.add(c)
    kb.add("⏹️ Bekor qilish")
    await message.answer("Qaysi valyutani o‘chirmoqchisiz?", reply_markup=kb)
    await AdminFSM.delete_choose.set()

@dp.message_handler(state=AdminFSM.delete_choose)
async def admin_delete_currency_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    name = message.text.strip().upper()
    if name not in currencies:
        return await message.answer("Bunday valyuta topilmadi.")
    currencies.pop(name)
    if name in reserves:
        reserves.pop(name)
        save_json(RESERVES_FILE, reserves)
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"🗑️ {name} o‘chirildi.", reply_markup=main_menu_kb())
    await state.finish()

# VALYUTALAR RO'YXATI
@dp.message_handler(lambda m: m.text == "📄 Valyutalar ro‘yxati", state=AdminFSM.main)
async def admin_list_currencies(message: types.Message):
    if not currencies:
        return await message.answer("Hozircha valyuta mavjud emas.")
    text = "📄 *Valyutalar ro‘yxati:*\n"
    for code, info in currencies.items():
        name = info.get("name", code)
        text += (
            f"💱 {code} — {name}\n"
            f"  💰 Sotish (biz sotamiz): {info.get('sell_rate')}\n"
            f"  💵 Sotib olish (biz sotib olamiz): {info.get('buy_rate')}\n"
            f"  🏦 Sotish karta: {info.get('sell_card')}\n"
            f"  💳 Sotib olish karta: {info.get('buy_card')}\n"
        )
    await message.answer(text, parse_mode="Markdown")

# KRIPTO ZAXIRALARI
@dp.message_handler(lambda m: m.text == "📦 Kripto zaxiralari", state=AdminFSM.main)
async def admin_reserves_start(message: types.Message):
    if not currencies:
        return await message.answer("Avval valyuta qo'shing.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for cur in currencies.keys():
        kb.add(cur)
    kb.add("⏹️ Bekor qilish")
    await message.answer("Qaysi valyutaga zaxira kiriting?", reply_markup=kb)
    await AdminFSM.reserves_choose_currency.set()

@dp.message_handler(state=AdminFSM.reserves_choose_currency)
async def admin_reserves_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    if message.text not in currencies:
        return await message.answer("Bunday valyuta yo'q.")
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} uchun zaxira miqdorini kiriting:")
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
        return await message.answer("Iltimos, to'g'ri miqdor kiriting.")
    data = await state.get_data()
    currency = data["currency"]
    reserves[currency] = amount
    save_json(RESERVES_FILE, reserves)
    await message.answer(f"✅ {currency} zaxirasi: {amount}", reply_markup=main_menu_kb())
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
        return await message.answer("Iltimos, to'g'ri summa kiriting.")
    card_balance["UZS"] = amount
    save_json(CARD_BALANCE_FILE, card_balance)
    await message.answer(f"✅ Karta balansi yangilandi: {amount} UZS", reply_markup=main_menu_kb())
    await state.finish()

# QO'LLANMA
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
    if message.text.lower() == "o‘chirish":
        help_video_data["video"] = None
        help_video_data["text"] = "Qo'llanma hali qo'shilmagan."
        save_json(HELP_VIDEO_FILE, help_video_data)
        await message.answer("✅ Qo'llanma o'chirildi.", reply_markup=main_menu_kb())
        await state.finish()
        return
    if not message.video:
        return await message.answer("Iltimos, video yuboring.")
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
    await message.answer("✅ Qo'llanma yangilandi.", reply_markup=main_menu_kb())
    await state.finish()

# FOYDALANUVCHILARGA XABAR
@dp.message_handler(lambda m: m.text == "📩 Foydalanuvchilarga xabar", state=AdminFSM.main)
async def admin_msg_choose(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👤 Bitta foydalanuvchiga")
    kb.add("🌍 Barchasiga")
    kb.add("⏹️ Bekor qilish")
    await message.answer("Kimga xabar yubormoqchisiz?", reply_markup=kb)
    await AdminFSM.broadcast_choose.set()

@dp.message_handler(state=AdminFSM.broadcast_choose)
async def admin_msg_target_type(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    if message.text == "👤 Bitta foydalanuvchiga":
        await state.update_data(target="single")
        await message.answer("Foydalanuvchi ID sini kiriting:")
        await AdminFSM.broadcast_target.set()
    elif message.text == "🌍 Barchasiga":
        await state.update_data(target="all")
        await message.answer("Xabarni yuboring (matn, rasm, video — emoji, format saqlanadi):")
        await AdminFSM.broadcast_media.set()
    else:
        await message.answer("Noto‘g‘ri tanlov.")

@dp.message_handler(state=AdminFSM.broadcast_target)
async def admin_msg_single_id(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return
    try:
        uid = int(message.text.strip())
        if str(uid) not in users:
            await message.answer("Bunday foydalanuvchi topilmadi.")
            return
        await state.update_data(user_id=uid)
        await message.answer("Xabarni yuboring (matn, rasm, video — emoji, format saqlanadi):")
        await AdminFSM.broadcast_media.set()
    except:
        await message.answer("Iltimos, to'g'ri ID kiriting.")

@dp.message_handler(content_types=types.ContentTypes.ANY, state=AdminFSM.broadcast_media)
async def admin_msg_send_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("target")
    
    async def send_to(uid):
        try:
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(uid, message.video.file_id, caption=message.caption)
            elif message.document:
                await bot.send_document(uid, message.document.file_id, caption=message.caption)
            elif message.text:
                await bot.send_message(uid, message.text)
            return True
        except:
            return False

    success = 0
    if target == "all":
        for uid_str in users.keys():
            if await send_to(int(uid_str)):
                success += 1
        await message.answer(f"✅ Xabar {success} ta foydalanuvchiga yuborildi.", reply_markup=main_menu_kb())
    else:
        uid = data.get("user_id")
        if await send_to(uid):
            await message.answer("✅ Xabar yuborildi.", reply_markup=main_menu_kb())
        else:
            await message.answer("❌ Xabar yuborilmadi.")
    await state.finish()

# ADMINGA XABAR
@dp.message_handler(lambda m: m.text == "📨 Adminga xabar yuborish")
async def contact_admin_start(message: types.Message):
    await message.answer("Xabaringizni yuboring (matn, rasm, video):", reply_markup=back_kb())
    await ContactAdminFSM.wait_message.set()

@dp.message_handler(content_types=types.ContentTypes.ANY, state=ContactAdminFSM.wait_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        return await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
    caption = f"📨 *Foydalanuvchidan xabar:*\n👤 {message.from_user.full_name}\n🆔 {message.from_user.id}"
    user_text = message.caption or message.text or ""
    if user_text:
        caption += f"\n💬 {user_text}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✉️ Javob berish", callback_data=f"reply_to_user|{message.from_user.id}"))
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown", reply_markup=kb)
        elif message.video:
            await bot.send_video(ADMIN_ID, message.video.file_id, caption=caption, parse_mode="Markdown", reply_markup=kb)
        elif message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown", reply_markup=kb)
        else:
            await bot.send_message(ADMIN_ID, caption, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.exception("Xatolik: %s", e)
        await message.answer("❌ Xabar yuborilmadi.")
    await state.finish()
    await message.answer("✅ Xabaringiz adminga yuborildi.", reply_markup=main_menu_kb())

# UNKNOWN
@dp.message_handler()
async def unknown(message: types.Message):
    await message.answer("❓ Noma'lum buyruq.", reply_markup=main_menu_kb())

# --------------------
# ISHGA TUSHIRISH
# --------------------
if __name__ == "__main__":
    print("🤖 Obmen bot ishga tushmoqda...")
    executor.start_polling(dp, skip_updates=True)
