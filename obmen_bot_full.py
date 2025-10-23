# obmen_bot_full.py
# -*- coding: utf-8 -*-
import os, json, time, logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# --------------------
# Sozlamalar
# --------------------
os.environ["TZ"] = "Asia/Tashkent"
API_TOKEN = "YOUR_BOT_TOKEN"
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
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --------------------
# JSON helpers
# --------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path,"w",encoding="utf-8") as f:
            json.dump(default,f,ensure_ascii=False,indent=2)
        return default
    with open(path,"r",encoding="utf-8") as f:
        try: 
            return json.load(f)
        except: 
            return default

def save_json(path, data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

# --------------------
# Data stores
# --------------------
currencies = load_json(CURRENCIES_FILE, {})
users = load_json(USERS_FILE, {})
orders = load_json(ORDERS_FILE, {})

# --------------------
# FSM
# --------------------
class BuyFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    wait_check = State()

class SellFSM(StatesGroup):
    choose_currency = State()
    amount = State()
    wallet = State()
    wait_check = State()

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
    return int(uid)==int(ADMIN_ID)

def ensure_user(uid,tg_user=None):
    key = str(uid)
    if key not in users:
        users[key]={"id":uid,"name":tg_user.full_name if tg_user else "",
                    "username":tg_user.username if tg_user else "",
                    "orders":[]}
        save_json(USERS_FILE,users)
    return users[key]

def main_menu_kb(uid=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💲 Sotib olish", "💰 Sotish")
    if uid and is_admin(uid):
        kb.add("⚙️ Admin Panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⏹️ Bekor qilish")
    return kb

def new_order_id():
    return str(int(time.time()*1000))

# --------------------
# Start
# --------------------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    user = ensure_user(uid, message.from_user)
    await message.answer(
        f"Assalomu alaykum, {user['name']}! 👋\n"
        "Xush kelibsiz botimizga. Quyidagi tugmalar orqali valuta sotib olishingiz yoki sotishingiz mumkin.",
        reply_markup=main_menu_kb(uid)
    )

# --------------------
# Sotib olish
# --------------------
@dp.message_handler(lambda message: message.text=="💲 Sotib olish")
async def buy_start(message: types.Message):
    uid = message.from_user.id
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cur in currencies.keys():
        kb.add(cur)
    kb.add("⏹️ Bekor qilish")

    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await BuyFSM.choose_currency.set()

@dp.message_handler(state=BuyFSM.choose_currency)
async def choose_currency_buy(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda olmoqchisiz?")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.amount)
async def amount_handler_buy(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",","."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.wallet)
async def wallet_handler_buy(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]
    rate = currencies[currency]["buy_rate"]
    total = amt * rate
    card = currencies[currency].get("buy_card","5614 6818 7267 2690")

    await message.answer(
        f"{amt} {currency} uchun to‘lovni quyidagi karta raqamiga amalga oshiring:\n"
        f"{card}\n\n"
        f"Jami: {total} UZS\n\n"
        "✅ To‘lovni amalga oshirgach, *chek rasmini yuboring*.",
        parse_mode="Markdown"
    )
    await BuyFSM.wait_check.set()

@dp.message_handler(content_types=['photo'], state=BuyFSM.wait_check)
async def handle_buy_check_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = new_order_id()
    file_id = message.photo[-1].file_id

    order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "currency": data["currency"],
        "amount": data["amount"],
        "wallet": data["wallet"],
        "type": "buy",
        "status": "waiting_admin",
        "created_at": int(time.time()),
        "check_photo": file_id
    }
    orders[order_id] = order
    user = ensure_user(message.from_user.id, message.from_user)
    user["orders"].append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    await bot.send_photo(
        ADMIN_ID, file_id,
        caption=(
            f"🆕 Yangi BUY buyurtma!\n\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"💱 Valyuta: {data['currency']}\n"
            f"💰 Miqdor: {data['amount']}\n"
            f"🏦 Hamyon: {data['wallet']}\n"
            f"📄 Buyurtma ID: {order_id}"
        ),
        reply_markup=kb
    )
    await message.answer("✅ Chekingiz adminga yuborildi. Tasdiqlashni kuting.", reply_markup=main_menu_kb())
    await state.finish()

# --------------------
# Sotish
# --------------------
@dp.message_handler(lambda message: message.text=="💰 Sotish")
async def sell_start(message: types.Message):
    uid = message.from_user.id
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for cur in currencies.keys():
        kb.add(cur)
    kb.add("⏹️ Bekor qilish")

    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await SellFSM.choose_currency.set()

@dp.message_handler(state=SellFSM.choose_currency)
async def choose_currency_sell(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda sotmoqchisiz?")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.amount)
async def amount_handler_sell(message: types.Message, state: FSMContext):
    try:
        amt = float(message.text.replace(",","."))
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.wallet)
async def sell_wallet_handler(message: types.Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]
    rate = currencies[currency]["sell_rate"]
    total = amt * rate
    card = currencies[currency].get("sell_card","5614 6818 7267 2690")

    await message.answer(
        f"{amt} {currency} ni quyidagi karta raqamiga yuboring:\n"
        f"{card}\n\n"
        f"Jami: {total} UZS\n\n"
        "✅ To‘lovni amalga oshirgach, *chek rasmini yuboring*.",
        parse_mode="Markdown"
    )
    await SellFSM.wait_check.set()

@dp.message_handler(content_types=['photo'], state=SellFSM.wait_check)
async def handle_sell_check_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = new_order_id()
    file_id = message.photo[-1].file_id

    order = {
        "id": order_id,
        "user_id": message.from_user.id,
        "currency": data["currency"],
        "amount": data["amount"],
        "wallet": data["wallet"],
        "type": "sell",
        "status": "waiting_admin",
        "created_at": int(time.time()),
        "check_photo": file_id
    }
    orders[order_id] = order
    user = ensure_user(message.from_user.id, message.from_user)
    user["orders"].append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    await bot.send_photo(
        ADMIN_ID, file_id,
        caption=(
            f"🆕 Yangi SELL buyurtma!\n\n"
            f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"💱 Valyuta: {data['currency']}\n"
            f"💰 Miqdor: {data['amount']}\n"
            f"🏦 Hamyon: {data['wallet']}\n"
            f"📄 Buyurtma ID: {order_id}"
        ),
        reply_markup=kb
    )
    await message.answer("✅ Chekingiz adminga yuborildi. Tasdiqlashni kuting.", reply_markup=main_menu_kb())
    await state.finish()

# --------------------
# Admin buyurtma tasdiqlash
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_cb(call: types.CallbackQuery):
    parts = call.data.split("|")
    if len(parts)!=3:
        return await call.answer("Xato callback")
    action, order_id = parts[1], parts[2]
    order = orders.get(order_id)
    if not order:
        return await call.answer("Buyurtma topilmadi")
    if action=="confirm":
        order["status"]="confirmed"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], "✅ Buyurtmangiz tasdiqlandi!")
        await call.answer("Tasdiqlandi")
    elif action=="reject":
        order["status"]="rejected"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], "❌ Buyurtmangiz bekor qilindi.")
        await call.answer("Bekor qilindi")

# --------------------
# Admin buyurtma tasdiqlash / bekor qilish
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_cb(call: types.CallbackQuery):
    parts = call.data.split("|")
    if len(parts)!=3: 
        return await call.answer("Xato callback")
    action, order_id = parts[1], parts[2]
    order = orders.get(order_id)
    if not order: 
        return await call.answer("Buyurtma topilmadi")
    if action=="confirm":
        order["status"]="confirmed"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], f"Sizning buyurtmangiz tasdiqlandi ✅")
        await call.answer("Tasdiqlandi")
    elif action=="reject":
        order["status"]="rejected"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], f"Sizning buyurtmangiz bekor qilindi ❌")
        await call.answer("Bekor qilindi")

# --------------------
# Admin panel funksiyalari
# --------------------
# Bu qism sizning avvalgi kodlaringizdan olindi,
# endi buy/sell kurs va karta raqamlarini qo‘shish imkoniyati bilan ishlaydi.
# --------------------
# Shu yerga AdminFSM.add_* va edit/delete funksiyalarini joylashtiring
# --------------------
# --------------------
# Admin Panel Start
# --------------------
@dp.message_handler(lambda message: message.text=="⚙️ Admin Panel")
async def admin_panel_start(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Valyuta qo‘shish", "✏️ Valyuta nomini o‘zgartirish")
    kb.add("💰 Valyuta kursini o‘zgartirish", "💳 Valyuta karta raqamini o‘zgartirish")
    kb.add("🗑️ Valyuta o‘chirish")
    kb.add("📢 Xabar yuborish")  # <-- shu qatorni qo‘sh
    kb.add("⏹️ Orqaga")
    await message.answer("Admin panel:", reply_markup=kb)
    await AdminFSM.main.set()
# --------------------
# Foydalanuvchilarga xabar yuborish (admin uchun)
# --------------------
class BroadcastFSM(StatesGroup):
    waiting_message = State()

@dp.message_handler(lambda message: message.text == "📢 Xabar yuborish", state=AdminFSM.main)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
    await BroadcastFSM.waiting_message.set()

@dp.message_handler(state=BroadcastFSM.waiting_message)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return

    text = message.text
    count = 0
    failed = 0
    for uid in users.keys():
        try:
            await bot.send_message(int(uid), text)
            count += 1
        except:
            failed += 1
            continue

    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.\n❌ {failed} ta foydalanuvchiga yuborilmadi.", reply_markup=back_kb())
    await state.finish()
    await admin_panel_start(message)
# --------------------
# Admin panel FSM
# --------------------
@dp.message_handler(state=AdminFSM.main)
async def admin_main(message: types.Message, state: FSMContext):
    text = message.text
    if text=="➕ Valyuta qo‘shish":
        await message.answer("Valyuta nomini kiriting:", reply_markup=back_kb())
        await AdminFSM.add_name.set()
    elif text=="✏️ Valyuta nomini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(types.KeyboardButton(cur))
        kb.add("⏹️ Bekor qilish")
        await message.answer("Qaysi valyuta nomini o‘zgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_choose.set()
    elif text=="💰 Valyuta kursini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(types.KeyboardButton(cur))
        kb.add("⏹️ Bekor qilish")
        await message.answer("Qaysi valyuta kursini o‘zgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_rate_choose.set()
    elif text=="💳 Valyuta karta raqamini o‘zgartirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(types.KeyboardButton(cur))
        kb.add("⏹️ Bekor qilish")
        await message.answer("Qaysi valyuta karta raqamini o‘zgartirmoqchisiz?", reply_markup=kb)
        await AdminFSM.edit_card_choose.set()
    elif text=="🗑️ Valyuta o‘chirish":
        if not currencies:
            await message.answer("Hozircha valyuta mavjud emas.", reply_markup=back_kb())
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for cur in currencies.keys():
            kb.add(types.KeyboardButton(cur))
        kb.add("⏹️ Bekor qilish")
        await message.answer("Qaysi valyutani o‘chirmoqchisiz?", reply_markup=kb)
        await AdminFSM.delete_choose.set()
    elif text=="⏹️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("Noto‘g‘ri tugma. Qaytadan tanlang.")

# --------------------
# Valyuta qo‘shish
# --------------------
@dp.message_handler(state=AdminFSM.add_name)
async def add_currency_name(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    await state.update_data(new_name=message.text)
    await message.answer("Valyuta sotib olish kursini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_buy_rate.set()

@dp.message_handler(state=AdminFSM.add_buy_rate)
async def add_currency_buy_rate(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    try:
        rate = float(message.text.replace(",","."))
    except:
        await message.answer("Iltimos to‘g‘ri raqam kiriting.")
        return
    await state.update_data(buy_rate=rate)
    await message.answer("Valyuta sotish kursini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_sell_rate.set()

@dp.message_handler(state=AdminFSM.add_sell_rate)
async def add_currency_sell_rate(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    try:
        rate = float(message.text.replace(",","."))
    except:
        await message.answer("Iltimos to‘g‘ri raqam kiriting.")
        return
    await state.update_data(sell_rate=rate)
    await message.answer("Sotib olish karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_buy_card.set()

@dp.message_handler(state=AdminFSM.add_buy_card)
async def add_currency_buy_card(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    await state.update_data(buy_card=message.text)
    await message.answer("Sotish karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.add_sell_card.set()

@dp.message_handler(state=AdminFSM.add_sell_card)
async def add_currency_sell_card(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    data = await state.get_data()
    currencies[data["new_name"]] = {
        "buy_rate": data["buy_rate"],
        "sell_rate": data["sell_rate"],
        "buy_card": data["buy_card"],
        "sell_card": message.text
    }
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['new_name']} qo‘shildi! Buy: {data['buy_rate']} ({data['buy_card']}), Sell: {data['sell_rate']} ({message.text})", reply_markup=back_kb())
    await state.finish()
    await admin_panel_start(message)

# --------------------
# Valyuta nomini o‘zgartirish
# --------------------
@dp.message_handler(state=AdminFSM.edit_choose)
async def edit_currency_choose(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(edit_name_old=message.text)
    await message.answer("Yangi nom kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_name.set()

@dp.message_handler(state=AdminFSM.edit_name)
async def edit_currency_name(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    data = await state.get_data()
    currencies[message.text] = currencies.pop(data["edit_name_old"])
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['edit_name_old']} nomi {message.text} ga o‘zgartirildi.", reply_markup=back_kb())
    await state.finish()
    await admin_panel_start(message)

# --------------------
# Valyuta kursini o‘zgartirish
# --------------------
@dp.message_handler(state=AdminFSM.edit_rate_choose)
async def edit_currency_rate_choose(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(rate_name=message.text)
    await message.answer(f"{message.text} uchun yangi kursni kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_rate_set.set()

@dp.message_handler(state=AdminFSM.edit_rate_set)
async def edit_currency_rate_set(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    try:
        rate = float(message.text.replace(",",".")) 
    except:
        await message.answer("Iltimos raqam kiriting.")
        return
    data = await state.get_data()
    currencies[data["rate_name"]]["buy_rate"] = rate
    currencies[data["rate_name"]]["sell_rate"] = rate
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{data['rate_name']} kursi yangilandi: {rate}", reply_markup=back_kb())
    await state.finish()
    await admin_panel_start(message)

# --------------------
# Valyuta karta raqamini o‘zgartirish (Buy/Sell)
# --------------------
@dp.message_handler(state=AdminFSM.edit_card_choose)
async def edit_currency_card_choose(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    await state.update_data(card_name=message.text)
    await message.answer("Sotib olish (Buy) karta raqamini kiriting:", reply_markup=back_kb())
    await AdminFSM.edit_card_set.set()

@dp.message_handler(state=AdminFSM.edit_card_set)
async def edit_currency_card_set(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
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
    await state.finish()
    await admin_panel_start(message)

# --------------------
# Valyuta o‘chirish
# --------------------
@dp.message_handler(state=AdminFSM.delete_choose)
async def delete_currency(message: types.Message, state: FSMContext):
    if message.text=="⏹️ Bekor qilish":
        await state.finish()
        await admin_panel_start(message)
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi.")
        return
    removed = currencies.pop(message.text)
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"{message.text} o‘chirildi.", reply_markup=back_kb())
    await state.finish()
    await admin_panel_start(message)
# --------------------
# Run bot
# --------------------
if __name__=="__main__":
    print("Bot ishga tushmoqda...")
executor.start_polling(dp, skip_updates=True)
