# obmen_bot_full_aiogram3.py
# -*- coding: utf-8 -*-
import os
import json
import time
import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import Router

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# --------------------
# Sozlamalar
# --------------------
os.environ["TZ"] = "Asia/Tashkent"
API_TOKEN = "7644659937:AAHnvt01ZKVtjQAb649QKQheWXPQQJVsitQ"
ADMIN_ID = 7973934849
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

storage = MemoryStorage()
router = Router()

# --------------------
# JSON helpers
# --------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --------------------
# Data stores (RAM mirrors)
# --------------------
currencies = load_json(CURRENCIES_FILE, {})
users = load_json(USERS_FILE, {})
orders = load_json(ORDERS_FILE, {})
sessions = {}

# --------------------
# FSM
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
def is_admin(uid):
    try:
        return int(uid) == int(ADMIN_ID)
    except:
        return False

def ensure_user(uid, tg_user=None):
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

def main_menu_kb(uid=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("ð² Sotib olish"), KeyboardButton("ð° Sotish"))
    if uid and is_admin(uid):
        kb.add(KeyboardButton("âï¸ Admin Panel"))
    return kb

def back_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))
    return kb

def new_order_id():
    return str(int(time.time() * 1000))

# --------------------
# Start
# --------------------
@router.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    user = ensure_user(uid, message.from_user)
    await message.answer(
        f"Assalomu alaykum, {user['name']}! ð\nXush kelibsiz botimizga. Pastdagi tugma orqali curupto valuta sotib olishingiz va sotishingiz mumkin.",
        reply_markup=main_menu_kb(uid)
    )

# --------------------
# Sotib olish (Buy)
# --------------------
@router.message(lambda message: message.text and message.text == "ð² Sotib olish")
async def buy_start(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row_buttons = []
    for i, cur in enumerate(currencies.keys(), 1):
        row_buttons.append(KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row_buttons)
            row_buttons = []
    if row_buttons:
        kb.row(*row_buttons)
    kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))

    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await BuyFSM.choose_currency.set()

@router.message(BuyFSM.choose_currency)
async def choose_currency_buy(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.set_data({"currency": message.text})
    await message.answer(f"{message.text} bo'yicha qancha miqdorda olmoqchisiz?")
    await BuyFSM.amount.set()

@router.message(BuyFSM.amount)
async def amount_handler_buy(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    data = await state.get_data()
    data["amount"] = amt
    await state.set_data(data)
    await message.answer("Hamyon raqamingizni kiriting:")
    await BuyFSM.wallet.set()

@router.message(BuyFSM.wallet)
async def wallet_handler_buy(message: types.Message, state: FSMContext):
    # This handler is triggered for wallet input
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    data = await state.get_data()
    # update wallet
    data["wallet"] = message.text
    await state.set_data(data)

    currency = data["currency"]
    amt = data["amount"]
    rate = currencies[currency].get("buy_rate", 0)
    card = currencies[currency].get("buy_card", "5614 6818 7267 2690")
    total = amt * rate

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Chek yuborish"))
    kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))

    await message.answer(
        f"{amt} {currency} uchun to'lovni quyidagi karta raqamiga qiling:\n{card}\n\nJami to'lov: {total} UZS",
        reply_markup=kb
    )
    await BuyFSM.confirm.set()

@router.message(BuyFSM.confirm)
async def confirm_handler_buy(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "â¹ï¸ Bekor qilish":
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
        "rate": currencies[data["currency"]].get("buy_rate")
    }
    orders[order_id] = order
    user_orders = users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []})
    user_orders.setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("â Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(InlineKeyboardButton("â Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    # notify admin
    try:
        await bot.send_message(
            ADMIN_ID,
            f"Yangi buyurtma!\nFoydalanuvchi: {message.from_user.full_name}\nID: {message.from_user.id}\nValyuta: {data['currency']}\nMiqdor: {data['amount']}\nHamyon: {data['wallet']}\nBuyurtma ID: {order_id}",
            reply_markup=kb
        )
    except Exception as e:
        logger.exception("Adminga xabar yuborishda xato:")

    await message.answer("â Buyurtma adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# Sotish (Sell)
# --------------------
@router.message(lambda message: message.text and message.text == "ð° Sotish")
async def sell_start(message: types.Message):
    uid = message.from_user.id
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row_buttons = []
    for i, cur in enumerate(currencies.keys(), 1):
        row_buttons.append(KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row_buttons)
            row_buttons = []
    if row_buttons:
        kb.row(*row_buttons)
    kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))

    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await SellFSM.choose_currency.set()

@router.message(SellFSM.choose_currency)
async def choose_currency_sell(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.set_data({"currency": message.text})
    await message.answer(f"{message.text} bo'yicha qancha miqdorda sotmoqchisiz?")
    await SellFSM.amount.set()

@router.message(SellFSM.amount)
async def amount_handler_sell(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    data = await state.get_data()
    data["amount"] = amt
    await state.set_data(data)
    await message.answer("Hamyon raqamingizni kiriting:")
    await SellFSM.wallet.set()

@router.message(SellFSM.wallet)
async def wallet_handler_sell(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    data = await state.get_data()
    data["wallet"] = message.text
    await state.set_data(data)

    currency = data["currency"]
    amt = data["amount"]
    rate = currencies[currency].get("sell_rate", 0)
    card = currencies[currency].get("sell_card", "5614 6818 7267 2690")
    total = amt * rate

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Chek yuborish"))
    kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))

    await message.answer(
        f"{amt} {currency} sotish uchun to'lovni quyidagi karta raqamiga qiling:\n{card}\n\nJami to'lov: {total} UZS",
        reply_markup=kb
    )
    await SellFSM.confirm.set()

@router.message(SellFSM.confirm)
async def confirm_handler_sell(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "â¹ï¸ Bekor qilish":
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
        "rate": currencies[data["currency"]].get("sell_rate")
    }
    orders[order_id] = order
    user_orders = users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "orders": []})
    user_orders.setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("â Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(InlineKeyboardButton("â Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    try:
        await bot.send_message(
            ADMIN_ID,
            f"Yangi sell buyurtma!\nFoydalanuvchi: {message.from_user.full_name}\nID: {message.from_user.id}\nValyuta: {data['currency']}\nMiqdor: {data['amount']}\nHamyon: {data['wallet']}\nBuyurtma ID: {order_id}",
            reply_markup=kb
        )
    except Exception:
        logger.exception("Adminga sell buyurtma xabari yuborishda xato:")

    await message.answer("â Buyurtma adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.clear()

# --------------------
# Admin order callback (confirm/reject)
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
            await bot.send_message(order["user_id"], f"Sizning buyurtmangiz tasdiqlandi â")
        except Exception:
            logger.exception("Foydalanuvchiga confirm xabari yuborishda xato:")
        await callback.answer("Tasdiqlandi")
    elif action == "reject":
        order["status"] = "rejected"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(order["user_id"], f"Sizning buyurtmangiz bekor qilindi â")
        except Exception:
            logger.exception("Foydalanuvchiga reject xabari yuborishda xato:")
        await callback.answer("Bekor qilindi")

# --------------------
# Admin panel start
# --------------------
@router.message(lambda message: message.text and message.text == "âï¸ Admin Panel")
async def admin_panel_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("â Valyuta qoâshish"), KeyboardButton("âï¸ Valyuta nomini oâzgartirish"))
    kb.add(KeyboardButton("ð° Valyuta kursini oâzgartirish"), KeyboardButton("ð³ Valyuta karta raqamini oâzgartirish"))
    kb.add(KeyboardButton("ðï¸ Valyuta oâchirish"))
    kb.add(KeyboardButton("ð¢ Xabar yuborish"))
    kb.add(KeyboardButton("â¹ï¸ Orqaga"))
    await message.answer("Admin panel:", reply_markup=kb)
    await AdminFSM.main.set()

# --------------------
# Broadcast (admin)
# --------------------
@router.message(lambda message: message.text and message.text == "ð¢ Xabar yuborish", AdminFSM.main)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
    await BroadcastFSM.waiting_message.set()

@router.message(BroadcastFSM.waiting_message)
async def send_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        # return to admin panel
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

    await message.answer(f"â Xabar {count} ta foydalanuvchiga yuborildi.\nâ {failed} ta foydalanuvchiga yuborilmadi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# --------------------
# Admin main FSM handlers (menu actions)
# --------------------
@router.message(AdminFSM.main)
async def admin_main(message: types.Message, state: FSMContext):
    text = message.text
    if text == "â Valyuta qoâshish":
        await message.answer("Valyuta nomini kiriting:", reply_markup=back_kb())
        await AdminFSM.add_name.set()
    elif text == "âï¸ Valyuta nomini oâzgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))
        await message.answer("Qaysi valyuta nomini oâzgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_choose.set()
    elif text == "ð° Valyuta kursini oâzgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))
        await message.answer("Qaysi valyuta kursini oâzgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_rate_choose.set()
    elif text == "ð³ Valyuta karta raqamini oâzgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))
        await message.answer("Qaysi valyuta karta raqamini oâzgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_card_choose.set()
    elif text == "ðï¸ Valyuta oâchirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(KeyboardButton(cur))
        kb.add(KeyboardButton("â¹ï¸ Bekor qilish"))
        await message.answer("Qaysi valyutani oâchirmoqchisiz?", reply_markup=kb)
        await AdminFSM.delete_choose.set()
    elif text == "â¹ï¸ Orqaga":
        await state.clear()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("Notoâgâri tugma. Qaytadan tanlang.")

# --------------------
# Valyuta qoâshish
# --------------------
@router.message(AdminFSM.add_name)
async def add_currency_name(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    await state.update_data(new_name=message.text)
    await message.answer("Valyuta sotib olish kursini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_buy_rate.set()

@router.message(AdminFSM.add_buy_rate)
async def add_currency_buy_rate(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos toâgâri raqam kiriting.")
        return
    await state.update_data(buy_rate=rate)
    await message.answer("Valyuta sotish kursini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_sell_rate.set()

@router.message(AdminFSM.add_sell_rate)
async def add_currency_sell_rate(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos toâgâri raqam kiriting.")
        return
    await state.update_data(sell_rate=rate)
    await message.answer("Sotib olish karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_buy_card.set()

@router.message(AdminFSM.add_buy_card)
async def add_currency_buy_card(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    await state.update_data(buy_card=message.text)
    await message.answer("Sotish karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_sell_card.set()

@router.message(AdminFSM.add_sell_card)
async def add_currency_sell_card(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    data = await state.get_data()
    currencies[data["new_name"]] = {
        "buy_rate": data["buy_rate"],
        "sell_rate": data["sell_rate"],
        "buy_card": data["buy_card"],
        "sell_card": message.text
    }
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['new_name']} qoâshildi! Buy: {data['buy_rate']} ({data['buy_card']}), Sell: {data['sell_rate']} ({message.text})", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# --------------------
# Valyuta nomini oâzgartirish
# --------------------
@router.message(AdminFSM.edit_choose)
async def edit_currency_choose(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(edit_name_old=message.text)
    await message.answer("Yangi nom kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_name.set()

@router.message(AdminFSM.edit_name)
async def edit_currency_name(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    data = await state.get_data()
    currencies[message.text] = currencies.pop(data["edit_name_old"])
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['edit_name_old']} nomi {message.text} ga oâzgartirildi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# --------------------
# Valyuta kursini oâzgartirish
# --------------------
@router.message(AdminFSM.edit_rate_choose)
async def edit_currency_rate_choose(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(rate_name=message.text)
    await message.answer(f"{message.text} uchun yangi kursni kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_rate_set.set()

@router.message(AdminFSM.edit_rate_set)
async def edit_currency_rate_set(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    data = await state.get_data()
    # here we set both buy and sell to same value (same as original code)
    currencies[data["rate_name"]]["buy_rate"] = rate
    currencies[data["rate_name"]]["sell_rate"] = rate
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['rate_name']} kursi yangilandi: {rate}", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# --------------------
# Valyuta karta raqamini oâzgartirish (Buy/Sell)
# --------------------
@router.message(AdminFSM.edit_card_choose)
async def edit_currency_card_choose(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(card_name=message.text)
    await message.answer("Sotib olish (Buy) karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_card_set.set()

@router.message(AdminFSM.edit_card_set)
async def edit_currency_card_set(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
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

# --------------------
# Valyuta oâchirish
# --------------------
@router.message(AdminFSM.delete_choose)
async def delete_currency(message: types.Message, state: FSMContext):
    if message.text == "â¹ï¸ Bekor qilish":
        await state.clear()
        await admin_panel_start(message, state)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    removed = currencies.pop(message.text)
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{message.text} oâchirildi.", reply_markup=back_kb())
    await state.clear()
    await admin_panel_start(message, state)

# --------------------
# Fallback: any text not handled - show main menu
# --------------------
@router.message()
async def fallback(message: types.Message):
    # basic fallback to show main menu (prevents silent failures)
    await message.answer("Quyidagi tugmalardan tanlang:", reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# Main (start polling)
# --------------------
async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    print("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
if __name__ == "__main__":
    asyncio.run(main())
