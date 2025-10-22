# obmen_bot_full_aiogram3_complete.py
# -*- coding: utf-8 -*-
import os
import json
import time
import logging
import asyncio
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# --------------------
# Sozlamalar
# --------------------
API_TOKEN = "7644659937:AAHnvt01ZKVtjQAb649QKQheWXPQQJVsitQ"  # <-- TOKENINGNI shu yerga yoz
ADMIN_ID = 7973934849             # <-- ADMIN_ID ni shu yerga yoz

if not API_TOKEN:
    raise RuntimeError("BOT_TOKEN kerak — environment variable sifatida qo'shing yoki kodga yozing.")

DATA_DIR = "bot_data"
CURRENCIES_FILE = os.path.join(DATA_DIR, "currencies.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
os.makedirs(DATA_DIR, exist_ok=True)

# --------------------
# Logging
# --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------
# FSM va Router
# --------------------
storage = MemoryStorage()
router = Router()

# --------------------
# JSON helpers
# --------------------
def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default

def save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --------------------
# Data stores (RAM)
# --------------------
currencies: Dict[str, Dict[str, Any]] = load_json(CURRENCIES_FILE, {})
users: Dict[str, Dict[str, Any]] = load_json(USERS_FILE, {})
orders: Dict[str, Dict[str, Any]] = load_json(ORDERS_FILE, {})

# --------------------
# States
# --------------------
class BuyFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()
    upload_check = State()   # ✅ yangi holat

class SellFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    confirm = State()
    upload_check = State()   # ✅ yangi holat

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
# Utils
# --------------------
def is_admin(uid: int) -> bool:
    try:
        return int(uid) == int(ADMIN_ID)
    except:
        return False

def ensure_user(uid: int, tg_user: types.User = None) -> Dict[str, Any]:
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

def new_order_id() -> str:
    return str(int(time.time() * 1000))

def make_keyboard(rows):
    safe_rows = []
    for row in rows:
        safe_rows.append([KeyboardButton(text=str(b)) for b in row])
    return ReplyKeyboardMarkup(keyboard=safe_rows, resize_keyboard=True)

def main_menu_kb(uid=None):
    rows = [["💲 Sotib olish", "💰 Sotish"]]
    if uid and is_admin(uid):
        rows.append(["⚙️ Admin Panel"])
    return make_keyboard(rows)

def back_kb():
    return make_keyboard([["⏹️ Bekor qilish"]])

# --------------------
# START
# --------------------
@router.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    ensure_user(uid, message.from_user)
    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\nXush kelibsiz botimizga.",
        reply_markup=main_menu_kb(uid)
    )

# --------------------
# BUY FLOW
# --------------------
@router.message(lambda m: m.text == "💲 Sotib olish")
async def buy_start(message: types.Message, state: FSMContext):
    if not currencies:
        await message.answer("Valyuta mavjud emas. Iltimos, admin bilan bog‘laning.")
        return
    cur_keys = list(currencies.keys())
    rows = [cur_keys[i:i+2] for i in range(0, len(cur_keys), 2)]
    rows.append(["⏹️ Bekor qilish"])
    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=make_keyboard(rows))
    await state.set_state(BuyFSM.choose_currency)

@router.message(BuyFSM.choose_currency)
async def buy_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda olmoqchisiz?")
    await state.set_state(BuyFSM.amount)

@router.message(BuyFSM.amount)
async def buy_amount(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Faqat raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await state.set_state(BuyFSM.wallet)

@router.message(BuyFSM.wallet)
async def buy_wallet(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    data = await state.get_data()
    data["wallet"] = message.text
    await state.update_data(wallet=message.text)

    currency = data["currency"]
    amt = data["amount"]
    rate = currencies.get(currency, {}).get("buy_rate", 0)
    card = currencies.get(currency, {}).get("buy_card", "5614 0000 0000 0000")
    total = amt * rate

    kb = make_keyboard([["Chek yuborish"], ["⏹️ Bekor qilish"]])
    await message.answer(
        f"{amt} {currency} uchun quyidagi karta raqamiga to‘lov qiling:\n💳 {card}\n\nTo‘lov summasi: {total} UZS",
        reply_markup=kb
    )
    await state.set_state(BuyFSM.confirm)

# ✅ Yangi chek so‘rashi uchun joy
@router.message(BuyFSM.confirm)
async def buy_confirm(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text != "Chek yuborish":
        await message.answer("Iltimos, 'Chek yuborish' tugmasini bosing.")
        return

    await message.answer("📸 Iltimos, to‘lov chekini rasm yoki fayl sifatida yuboring.")
    await state.set_state(BuyFSM.upload_check)

# ✅ Foydalanuvchi chek yuborganda
@router.message(BuyFSM.upload_check)
async def buy_upload_check(message: types.Message, state: FSMContext, bot: Bot):
    if not (message.photo or message.document):
        await message.answer("📎 Iltimos, chekni rasm yoki fayl sifatida yuboring.")
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
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []}).setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    caption = (
        f"🆕 Yangi BUY buyurtma!\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"💰 Valyuta: {data['currency']}\n"
        f"💵 Miqdor: {data['amount']}\n"
        f"👛 Hamyon: {data['wallet']}\n"
        f"🆔 ID: {order_id}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"),
             InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}")]
        ]
    )

    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        elif message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception:
        logger.exception("Adminga chek yuborishda xato (buy).")

    await message.answer("✅ Chek yuborildi va adminga jo‘natildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# SELL FLOW
# --------------------
@router.message(lambda m: m.text == "💰 Sotish")
async def sell_start(message: types.Message, state: FSMContext):
    if not currencies:
        await message.answer("Valyuta mavjud emas.")
        return
    cur_keys = list(currencies.keys())
    rows = [cur_keys[i:i+2] for i in range(0, len(cur_keys), 2)]
    rows.append(["⏹️ Bekor qilish"])
    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=make_keyboard(rows))
    await state.set_state(SellFSM.choose_currency)

@router.message(SellFSM.choose_currency)
async def sell_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda sotmoqchisiz?")
    await state.set_state(SellFSM.amount)

@router.message(SellFSM.amount)
async def sell_amount(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Faqat raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await state.set_state(SellFSM.wallet)

@router.message(SellFSM.wallet)
async def sell_wallet(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    data = await state.get_data()
    data["wallet"] = message.text
    await state.update_data(wallet=message.text)

    currency = data["currency"]
    amt = data["amount"]
    rate = currencies.get(currency, {}).get("sell_rate", 0)
    card = currencies.get(currency, {}).get("sell_card", "5614 0000 0000 0000")
    total = amt * rate

    kb = make_keyboard([["Chek yuborish"], ["⏹️ Bekor qilish"]])
    await message.answer(
        f"{amt} {currency} sotish uchun quyidagi karta raqamiga to‘lov qiling:\n💳 {card}\n\nJami: {total} UZS",
        reply_markup=kb
    )
    await state.set_state(SellFSM.confirm)

# ✅ Chek yuborish bosilganda
@router.message(SellFSM.confirm)
async def sell_confirm(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text != "Chek yuborish":
        await message.answer("Iltimos, 'Chek yuborish' tugmasini bosing.")
        return

    await message.answer("📸 Iltimos, to‘lov chekini rasm yoki fayl sifatida yuboring.")
    await state.set_state(SellFSM.upload_check)

# ✅ Chek yuborilganda adminga jo‘natish
@router.message(SellFSM.upload_check)
async def sell_upload_check(message: types.Message, state: FSMContext, bot: Bot):
    if not (message.photo or message.document):
        await message.answer("📎 Iltimos, chekni rasm yoki fayl sifatida yuboring.")
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
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []}).setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    caption = (
        f"🆕 Yangi SELL buyurtma!\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"💰 Valyuta: {data['currency']}\n"
        f"💵 Miqdor: {data['amount']}\n"
        f"👛 Hamyon: {data['wallet']}\n"
        f"🆔 ID: {order_id}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"),
             InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}")]
        ]
    )

    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        elif message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception:
        logger.exception("Adminga chek yuborishda xato (sell).")

    await message.answer("✅ Chek yuborildi va adminga jo‘natildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# ADMIN TASDIQLASH CALLBACK
# --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("admin_order"))
async def admin_order_cb(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("|")
    if len(parts) != 3:
        await callback.answer("Xato callback")
        return
    action, order_id = parts[1], parts[2]
    order = orders.get(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi")
        return
    if action == "confirm":
        order["status"] = "confirmed"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(order["user_id"], f"Sizning buyurtmangiz tasdiqlandi ✅")
        except:
            pass
        await callback.answer("Tasdiqlandi")
    elif action == "reject":
        order["status"] = "rejected"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(order["user_id"], f"Sizning buyurtmangiz bekor qilindi ❌")
        except:
            pass
        await callback.answer("Bekor qilindi")

# --------------------
# FALLBACK
# --------------------
@router.message()
async def fallback(message: types.Message):
    await message.answer("Buyruq topilmadi. /start ni bosing", reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# Admin panel start
# --------------------
@router.message(lambda m: m.text == "⚙️ Admin Panel")
async def admin_panel_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    rows = [
        ["➕ Valyuta qo‘shish", "✏️ Valyuta nomini o‘zgartirish"],
        ["💰 Valyuta kursini o‘zgartirish", "💳 Valyuta karta raqamini o‘zgartirish"],
        ["🗑️ Valyuta o‘chirish", "📢 Xabar yuborish"],
        ["⏹️ Orqaga"]
    ]
    await message.answer("Admin panel:", reply_markup=make_keyboard(rows))
    await state.set_state(AdminFSM.main)

# (Admin FSM handlers: add, edit, delete, broadcast)
@router.message(lambda m: m.text == "📢 Xabar yuborish", AdminFSM.main)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
    await state.set_state(BroadcastFSM.waiting_message)

@router.message(BroadcastFSM.waiting_message)
async def send_broadcast(message: types.Message, state: FSMContext, bot: Bot):
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
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.\n❌ {failed} ta yuborilmadi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Admin menu actions (simplified flow)
@router.message(AdminFSM.main)
async def admin_main(message: types.Message, state: FSMContext):
    text = message.text
    if text == "➕ Valyuta qo‘shish":
        await message.answer("Valyuta nomini kiriting:", reply_markup=back_kb())
        await state.set_state(AdminFSM.add_name)
    elif text == "✏️ Valyuta nomini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        rows = [[c] for c in currencies.keys()] + [["⏹️ Bekor qilish"]]
        await message.answer("Qaysi valyuta nomini o‘zgartirmoqchisiz?", reply_markup=make_keyboard(rows))
        await state.set_state(AdminFSM.edit_choose)
    elif text == "💰 Valyuta kursini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        rows = [[c] for c in currencies.keys()] + [["⏹️ Bekor qilish"]]
        await message.answer("Qaysi valyuta kursini o‘zgartirmoqchisiz?", reply_markup=make_keyboard(rows))
        await state.set_state(AdminFSM.edit_rate_choose)
    elif text == "💳 Valyuta karta raqamini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        rows = [[c] for c in currencies.keys()] + [["⏹️ Bekor qilish"]]
        await message.answer("Qaysi valyuta karta raqamini o‘zgartirmoqchisiz?", reply_markup=make_keyboard(rows))
        await state.set_state(AdminFSM.edit_card_choose)
    elif text == "🗑️ Valyuta o‘chirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        rows = [[c] for c in currencies.keys()] + [["⏹️ Bekor qilish"]]
        await message.answer("Qaysi valyutani o‘chirmoqchisiz?", reply_markup=make_keyboard(rows))
        await state.set_state(AdminFSM.delete_choose)
    elif text == "⏹️ Orqaga":
        await state.clear()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("Noto‘g‘ri tugma. Qaytadan tanlang.")

# Add currency flow
@router.message(AdminFSM.add_name)
async def add_currency_name(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    await state.update_data(new_name=message.text)
    await message.answer("Valyuta sotib olish kursini kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.add_buy_rate)

@router.message(AdminFSM.add_buy_rate)
async def add_currency_buy_rate(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos to‘g‘ri raqam kiriting.")
        return
    await state.update_data(buy_rate=rate)
    await message.answer("Valyuta sotish kursini kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.add_sell_rate)

@router.message(AdminFSM.add_sell_rate)
async def add_currency_sell_rate(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos to‘g‘ri raqam kiriting.")
        return
    await state.update_data(sell_rate=rate)
    await message.answer("Sotib olish karta raqamini kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.add_buy_card)

@router.message(AdminFSM.add_buy_card)
async def add_currency_buy_card(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    await state.update_data(buy_card=message.text)
    await message.answer("Sotish karta raqamini kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.add_sell_card)

@router.message(AdminFSM.add_sell_card)
async def add_currency_sell_card(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    data = await state.get_data()
    name = data["new_name"]
    currencies[name] = {
        "buy_rate": data["buy_rate"],
        "sell_rate": data["sell_rate"],
        "buy_card": data["buy_card"],
        "sell_card": message.text
    }
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{name} qo‘shildi! Buy: {data['buy_rate']} ({data['buy_card']}), Sell: {data['sell_rate']} ({message.text})", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Edit name
@router.message(AdminFSM.edit_choose)
async def edit_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(edit_name_old=message.text)
    await message.answer("Yangi nom kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.edit_name)

@router.message(AdminFSM.edit_name)
async def edit_name(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    data = await state.get_data()
    currencies[message.text] = currencies.pop(data["edit_name_old"])
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['edit_name_old']} nomi {message.text} ga o‘zgartirildi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Edit rate
@router.message(AdminFSM.edit_rate_choose)
async def edit_rate_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(rate_name=message.text)
    await message.answer(f"{message.text} uchun yangi kursni kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.edit_rate_set)

@router.message(AdminFSM.edit_rate_set)
async def edit_rate_set(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    data = await state.get_data()
    currencies[data["rate_name"]]["buy_rate"] = rate
    currencies[data["rate_name"]]["sell_rate"] = rate
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['rate_name']} kursi yangilandi: {rate}", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Edit card
@router.message(AdminFSM.edit_card_choose)
async def edit_card_choose(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(card_name=message.text)
    await message.answer("Sotib olish (Buy) karta raqamini kiriting:", reply_markup=back_kb())
    await state.set_state(AdminFSM.edit_card_set)

@router.message(AdminFSM.edit_card_set)
async def edit_card_set(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    data = await state.get_data()
    if "buy_card_new" not in data:
        await state.update_data(buy_card_new=message.text)
        await message.answer("Sotish (Sell) karta raqamini kiriting:", reply_markup=back_kb())
        return
    currencies[data["card_name"]]["buy_card"] = data["buy_card_new"]
    currencies[data["card_name"]]["sell_card"] = message.text
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['card_name']} karta raqamlari yangilandi.\nBuy: {data['buy_card_new']}, Sell: {message.text}", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Delete currency
@router.message(AdminFSM.delete_choose)
async def delete_currency(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    removed = currencies.pop(message.text)
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{message.text} o‘chirildi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# Fallback
@router.message()
async def fallback(message: types.Message):
    await message.answer("Quyidagi tugmalardan tanlang:", reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# Main
# --------------------
async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    logger.info("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
