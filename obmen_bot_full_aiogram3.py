# main.py
# -*- coding: utf-8 -*-
"""
To'liq bir-fayllik Telegram bot (aiogram 3.x) —
- Start / Help
- Buy / Sell (FSM)
- Admin panel: add/edit/delete currency, broadcast
- Orders save/load (JSON)
- Uses environment variables: API_TOKEN, ADMIN_ID
Save as main.py. requirements.txt: aiogram==3.12.0 (yoki 3.x)
"""

import os
import json
import time
import logging
import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# --------------------
# CONFIG (set these in Railway Variables / .env)
# --------------------
os.environ.setdefault("TZ", "Asia/Tashkent")

API_TOKEN = os.getenv("7644659937:AAHnvt01ZKVtjQAb649QKQheWXPQQJVsitQ")  # required!
ADMIN_ID_ENV = os.getenv("7973934849")  # optional but recommended (just number)

if not API_TOKEN:
    raise RuntimeError("API_TOKEN topilmadi! Railway Variables yoki .env ga API_TOKEN qo'ying.")

try:
    ADMIN_ID: Optional[int] = int(ADMIN_ID_ENV) if ADMIN_ID_ENV else None
except Exception:
    ADMIN_ID = None

DATA_DIR = "bot_data"
CURRENCIES_FILE = os.path.join(DATA_DIR, "currencies.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
os.makedirs(DATA_DIR, exist_ok=True)

# --------------------
# Logging & bot init
# --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# --------------------
# JSON helpers
# --------------------
def load_json(path: str, default):
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Faylga yozishda xato: %s", path)

# --------------------
# In-memory backed stores
# --------------------
currencies = load_json(CURRENCIES_FILE, {})
users = load_json(USERS_FILE, {})
orders = load_json(ORDERS_FILE, {})

# --------------------
# FSM definitions
# --------------------
class BuyFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()

class SellFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()

class AdminFSM(StatesGroup):
    main = State()
    add_name = State()
    add_buy_rate = State()
    add_sell_rate = State()
    add_buy_card = State()
    add_sell_card = State()
    edit_choose = State()
    edit_name = State()
    edit_rate_choose = State()
    edit_rate_set = State()
    edit_card_choose = State()
    edit_card_set = State()
    delete_choose = State()

class BroadcastFSM(StatesGroup):
    waiting_message = State()

# --------------------
# Utilities
# --------------------
def is_admin(uid: int) -> bool:
    try:
        return ADMIN_ID is not None and int(uid) == int(ADMIN_ID)
    except Exception:
        return False

def ensure_user(uid: int, tg_user: Optional[types.User] = None):
    key = str(uid)
    if key not in users:
        users[key] = {
            "id": uid,
            "name": tg_user.full_name if tg_user else "",
            "username": tg_user.username if tg_user else "",
            "orders": []
        }
        save_json(USERS_FILE, users)
    return users[key]

def main_menu_kb(uid: Optional[int] = None) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("💲 Sotib olish"), KeyboardButton("💰 Sotish"))
    if uid and is_admin(uid):
        kb.add(KeyboardButton("⚙️ Admin Panel"))
    return kb

def back_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("⏹️ Bekor qilish"))
    return kb

def new_order_id() -> str:
    return str(int(time.time() * 1000))

# --------------------
# Start / Help
# --------------------
@router.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    user = ensure_user(uid, message.from_user)
    await message.answer(
        f"Assalomu alaykum, {user.get('name','Foydalanuvchi')}! 👋\n"
        "Kripto obmen botiga xush kelibsiz.\n"
        "Quyidagi tugmalardan foydalaning:",
        reply_markup=main_menu_kb(uid)
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Buyruqlar:\n/start - boshlash\n/help - yordam\nAdminlar uchun: Admin Panel")

# --------------------
# BUY flow
# --------------------
@router.message(F.text == "💲 Sotib olish")
async def buy_start(message: Message, state: FSMContext):
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for i, cur in enumerate(currencies.keys(), 1):
        row.append(KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await state.set_state(BuyFSM.choose_currency)

@router.message(BuyFSM.choose_currency)
async def choose_currency_buy(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo'yicha qancha miqdorda olmoqchisiz?")
    await state.set_state(BuyFSM.amount)

@router.message(BuyFSM.amount)
async def amount_handler_buy(message: Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Iltimos raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await state.set_state(BuyFSM.wallet)

@router.message(BuyFSM.wallet)
async def wallet_handler_buy(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    await state.update_data(wallet=message.text)
    data = await state.get_data()
    currency = data.get("currency")
    amt = data.get("amount", 0)
    rate = currencies.get(currency, {}).get("buy_rate", 0)
    card = currencies.get(currency, {}).get("buy_card", "5614 6818 7267 2690")
    total = amt * rate if amt else 0

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Chek yuborish"))
    kb.add(KeyboardButton("⏹️ Bekor qilish"))

    await message.answer(
        f"{amt} {currency} uchun to'lovni quyidagi karta raqamiga qiling:\n{card}\n\nJami to'lov: {total} UZS",
        reply_markup=kb
    )
    await state.set_state(BuyFSM.confirm)

@router.message(BuyFSM.confirm)
async def confirm_handler_buy(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text != "Chek yuborish":
        await message.answer("Iltimos faqat 'Chek yuborish' tugmasini bosing.")
        return

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
        "rate": currencies.get(data["currency"], {}).get("buy_rate")
    }
    orders[order_id] = order
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []})
    users[str(message.from_user.id)].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"Yangi buyurtma!\nFoydalanuvchi: {message.from_user.full_name}\nID: {message.from_user.id}\nValyuta: {data['currency']}\nMiqdor: {data['amount']}\nHamyon: {data['wallet']}\nBuyurtma ID: {order_id}",
                reply_markup=kb
            )
        except Exception:
            logger.exception("Adminga xabar yuborishda xato:")
    else:
        logger.warning("ADMIN_ID o'rnatilmagan - adminga xabar yuborilmadi.")

    await message.answer("✅ Buyurtma adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# SELL flow
# --------------------
@router.message(F.text == "💰 Sotish")
async def sell_start(message: Message, state: FSMContext):
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for i, cur in enumerate(currencies.keys(), 1):
        row.append(KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await state.set_state(SellFSM.choose_currency)

@router.message(SellFSM.choose_currency)
async def choose_currency_sell(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo'yicha qancha miqdorda sotmoqchisiz?")
    await state.set_state(SellFSM.amount)

@router.message(SellFSM.amount)
async def amount_handler_sell(message: Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Iltimos raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await state.set_state(SellFSM.wallet)

@router.message(SellFSM.wallet)
async def wallet_handler_sell(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    await state.update_data(wallet=message.text)
    data = await state.get_data()
    currency = data.get("currency")
    amt = data.get("amount", 0)
    rate = currencies.get(currency, {}).get("sell_rate", 0)
    card = currencies.get(currency, {}).get("sell_card", "5614 6818 7267 2690")
    total = amt * rate if amt else 0

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Chek yuborish"))
    kb.add(KeyboardButton("⏹️ Bekor qilish"))

    await message.answer(
        f"{amt} {currency} sotish uchun to'lovni quyidagi karta raqamiga qiling:\n{card}\n\nJami to'lov: {total} UZS",
        reply_markup=kb
    )
    await state.set_state(SellFSM.confirm)

@router.message(SellFSM.confirm)
async def confirm_handler_sell(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text != "Chek yuborish":
        await message.answer("Iltimos faqat 'Chek yuborish' tugmasini bosing.")
        return

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
        "rate": currencies.get(data["currency"], {}).get("sell_rate")
    }
    orders[order_id] = order
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []})
    users[str(message.from_user.id)].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"Yangi sell buyurtma!\nFoydalanuvchi: {message.from_user.full_name}\nID: {message.from_user.id}\nValyuta: {data['currency']}\nMiqdor: {data['amount']}\nHamyon: {data['wallet']}\nBuyurtma ID: {order_id}",
                reply_markup=kb
            )
        except Exception:
            logger.exception("Adminga sell buyurtma xabari yuborishda xato:")
    else:
        logger.warning("ADMIN_ID o'rnatilmagan - adminga xabar yuborilmadi.")

    await message.answer("✅ Buyurtma adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# Admin callbacks (confirm/reject)
# --------------------
@router.callback_query(F.data.startswith("admin_order"))
async def admin_order_cb(callback: CallbackQuery):
    data = callback.data or ""
    parts = data.split("|")
    if len(parts) != 3:
        await callback.answer("Xato callback")
        return
    _, action, order_id = parts
    order = orders.get(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi")
        return
    if action == "confirm":
        order["status"] = "confirmed"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(order["user_id"], "Sizning buyurtmangiz tasdiqlandi ✅")
        except Exception:
            logger.exception("Foydalanuvchiga confirm xabari yuborishda xato:")
        await callback.answer("Tasdiqlandi")
    elif action == "reject":
        order["status"] = "rejected"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(order["user_id"], "Sizning buyurtmangiz bekor qilindi ❌")
        except Exception:
            logger.exception("Foydalanuvchiga reject xabari yuborishda xato:")
        await callback.answer("Bekor qilindi")

# --------------------
# Admin Panel
# --------------------
@router.message(F.text == "⚙️ Admin Panel")
async def admin_panel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Valyuta qo'shish"), KeyboardButton("✏️ Valyuta nomini o'zgartirish"))
    kb.add(KeyboardButton("💰 Valyuta kursini o'zgartirish"), KeyboardButton("💳 Valyuta karta raqamini o'zgartirish"))
    kb.add(KeyboardButton("🗑️ Valyuta o'chirish"))
    kb.add(KeyboardButton("📢 Xabar yuborish"))
    kb.add(KeyboardButton("⏹️ Orqaga"))
    await message.answer("Admin panel:", reply_markup=kb)
    await state.set_state(AdminFSM.main)

@router.message(AdminFSM.main)
async def admin_main(message: Message, state: FSMContext):
    text = message.text
    if text == "➕ Valyuta qo'shish":
        await message.answer("Valyuta nomini kiriting:", reply_markup=back_kb())
        await state.set_state(AdminFSM.add_name)
    elif text == "✏️ Valyuta nomini o'zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("⏹️ Bekor qilish"))
        await message.answer("Qaysi valyuta nomini o'zgartirmoqchisiz?", reply_markup=kb)
        await state.set_state(AdminFSM.edit_choose)
    elif text == "💰 Valyuta kursini o'zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("⏹️ Bekor qilish"))
        await message.answer("Qaysi valyuta kursini o'zgartirmoqchisiz?", reply_markup=kb)
        await state.set_state(AdminFSM.edit_rate_choose)
    elif text == "💳 Valyuta karta raqamini o'zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("⏹️ Bekor qilish"))
        await message.answer("Qaysi valyuta karta raqamini o'zgartirmoqchisiz?", reply_markup=kb)
        await state.set_state(AdminFSM.edit_card_choose)
    elif text == "🗑️ Valyuta o'chirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("⏹️ Bekor qilish"))
        await message.answer("Qaysi valyutani o'chirmoqchisiz?", reply_markup=kb)
        await state.set_state(AdminFSM.delete_choose)
    elif text == "📢 Xabar yuborish":
        await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
        await state.set_state(BroadcastFSM.waiting_message)
    elif text == "⏹️ Orqaga":
        await state.clear()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("Noto'g'ri tugma. Qaytadan tanlang.")

# Broadcast handlers
@router.message(BroadcastFSM.waiting_message)
async def send_broadcast(message: Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    text = message.text
    count = 0
    failed = 0
    for uid in list(users.keys()):
        try:
            await bot.send_message(int(uid), text)
            count += 1
        except Exception:
            failed += 1
            continue
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.\n❌ {failed} ta foydalanuvchiga yuborilmadi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Admin add/edit/delete flows implemented above (handlers already included)

# --------------------
# Fallback
# --------------------
@router.message()
async def fallback(message: Message):
    await message.answer("Quyidagi tugmalardan tanlang:", reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# STARTUP
# --------------------
async def on_startup():
    logger.info("Bot ishga tushmoqda...")
    # Ensure files exist
    save_json(CURRENCIES_FILE, currencies)
    save_json(USERS_FILE, users)
    save_json(ORDERS_FILE, orders)
    # notify admin that bot started (optional)
    if ADMIN_ID:
        try:
            await bot.send_message(ADMIN_ID, "Bot ishga tushdi ✅")
        except Exception:
            logger.exception("Adminga start xabar yuborishda xato:")

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
