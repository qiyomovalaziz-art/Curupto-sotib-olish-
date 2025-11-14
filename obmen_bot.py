# obmen_bot.py
# -*- coding: utf-8 -*-
import os
import json
import time
import logging
from typing import Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# --------------------
# Sozlamalar
# --------------------
os.environ["TZ"] = "Asia/Tashkent"
API_TOKEN = os.getenv("OBMEN_BOT_TOKEN", "7644659937:AAHy_LuhZ8Wi_ba22MRp6Ksy4xV1xXV_6O8")
ADMIN_ID = int(os.getenv("OBMEN_ADMIN_ID", "7973934849"))

DATA_DIR = "bot_data"
CURRENCIES_FILE = os.path.join(DATA_DIR, "currencies.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
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

currencies: Dict[str, Any] = load_json(CURRENCIES_FILE, {})
users: Dict[str, Any] = load_json(USERS_FILE, {})
orders: Dict[str, Any] = load_json(ORDERS_FILE, {})

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

# --- Qo'shimcha: adminga xabar uchun FSM
class ContactAdminFSM(StatesGroup):
    wait_message = State()

# --------------------
# Helpers
# --------------------
def is_admin(user_id):
    try:
        return str(user_id) == str(ADMIN_ID)
    except:
        return False

def ensure_user(uid, user=None):
    """
    uid: int yoki str
    Saqlash uchun kalit sifatida always str(uid) ishlatiladi.
    """
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

def main_menu_kb(uid=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💲 Sotib olish", "💰 Sotish")
    kb.row("📋 Mening buyurtmalarim", "📨 Adminga xabar yuborish")
    if uid and is_admin(uid):
        kb.add("⚙️ Admin Panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⏹️ Bekor qilish")
    return kb

def admin_order_kb(order_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))
    return kb

# --------------------
# START + ✅ New Subscriber Notify Admin
# --------------------
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    uid_str = str(message.from_user.id)
    is_new = uid_str not in users  # yangi foydalanuvchi tekshiruvi

    ensure_user(message.from_user.id, message.from_user)

    if is_new:
        # adminga yangi obunachi haqida xabar
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🎉 *Yangi obunachi qo‘shildi!*\n\n"
                f"👤 Ism: {message.from_user.full_name}\n"
                f"🆔 ID: {message.from_user.id}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.exception("Adminga yangi obunachi xabarini yuborishda xato: %s", e)

    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}! 👋",
        reply_markup=main_menu_kb(message.from_user.id)
    )

# --------------------
# /start (ikkilamchi nusxa olib tashlandi) — tugadi
# --------------------

# --------------------
# /my_orders va boshqa handlerlar (qismlar birlashtirilgan)
# --------------------

@dp.message_handler(text="📋 Mening buyurtmalarim")
async def my_orders(message: types.Message):
    uid = str(message.from_user.id)
    ensure_user(message.from_user.id, message.from_user)

    user_orders = users.get(uid, {}).get("orders", [])

    if not user_orders:
        return await message.answer("📭 Sizda buyurtmalar mavjud emas.", reply_markup=main_menu_kb(uid))

    text = "🧾 *Sizning so‘nggi buyurtmalaringiz:*\n\n"

    for oid in user_orders[-10:][::-1]:
        o = orders.get(oid)
        if not o:
            continue

        # ✅ Toshkent vaqti bilan
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
# Buy (Sotib olish) — boshlash va tanlash
# --------------------
@dp.message_handler(lambda message: message.text == "💲 Sotib olish")
async def buy_start(message: types.Message):
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.")
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

    await message.answer("Qaysi valyutani sotib olmoqchisiz? Tanlang:", reply_markup=kb)
    await BuyFSM.choose_currency.set()

@dp.message_handler(state=BuyFSM.choose_currency)
async def buy_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    if message.text not in currencies:
        await message.answer("Bunday valyuta topilmadi. Iltimos ro'yxatdan tanlang.")
        return

    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} uchun qancha miqdor sotib olmoqchisiz? (raqam kiriting)")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.amount)
async def buy_amount_handler(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    try:
        amt = float(txt.replace(",", "."))
        if amt <= 0:
            raise ValueError()
    except:
        await message.answer("Iltimos to'g'ri miqdor kiriting (masalan: 10 yoki 0.5).")
        return

    await state.update_data(amount=amt)
    await message.answer("Hamyoningiz (wallet) raqamini kiriting (masalan: TRC20 address yoki hamyon id):", reply_markup=back_kb())
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.wallet)
async def buy_wallet_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    await state.update_data(wallet=message.text.strip())
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]
    cur_info = currencies.get(currency, {})
    buy_rate = cur_info.get("buy_rate")
    if buy_rate is None:
        await message.answer("Kechirasiz, bu valyuta uchun narx ma'lum emas. Admin bilan bog'laning.")
        await state.finish()
        return

    total = round(amt * float(buy_rate), 2)
    card = cur_info.get("buy_card", "5614 6818 7267 2690")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Chek yuborish"))
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))

    await message.answer(
        f"🔔 Toʻlov tafsilotlari:\n\n"
        f"Karta/Hisob: {card}\n"
        f"Valyuta: {currency}\n"
        f"Miqdor: {amt}\n"
        f"Narx: {buy_rate}\n"
        f"Jami: {total} UZS\n\n"
        f"Toʻlovni amalga oshirib, pastdagi 'Chek yuborish' tugmasi orqali toʻlov chekini (rasm yoki hujjat) yuboring.",
        reply_markup=kb
    )
    await BuyFSM.confirm.set()

# --------------------
# Buy FSM – Chek yuborish (photo yoki document)
# --------------------
@dp.message_handler(state=BuyFSM.confirm)
async def buy_confirm_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    if message.text != "Chek yuborish":
        await message.answer("Iltimos pastdagi 'Chek yuborish' tugmasini bosing.")
        return

    await message.answer("✅ Iltimos, to‘lov chekini rasm yoki fayl ko‘rinishida yuboring.", reply_markup=back_kb())
    await BuyFSM.upload.set()

@dp.message_handler(content_types=['photo', 'document'], state=BuyFSM.upload)
async def buy_upload_handler(message: types.Message, state: FSMContext):
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
        "rate": currencies[data["currency"]]["buy_rate"]
    }

    orders[order_id] = order
    uid = str(message.from_user.id)
    # ensure_user returns and creates users[uid_str] if missing
    users.setdefault(uid, ensure_user(message.from_user.id, message.from_user))
    users[uid].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    caption = (
        f"🆕 Yangi BUY buyurtma\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Valyuta: {data['currency']}\n"
        f"Miqdor: {data['amount']}\n"
        f"Hamyon: {data['wallet']}\n"
        f"Buyurtma ID: {order_id}"
    )

    kb = admin_order_kb(order_id)

    try:
        if message.content_type == 'photo':
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        else:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.exception("Adminga yuborishda xato: %s", e)
        await message.answer("❌ Xatolik yuz berdi. Keyinroq urinib ko‘ring.")
        await state.finish()
        return

    await message.answer("✅ Chek adminga yuborildi. Tez orada tasdiqlanadi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# --------------------
# Sell (Sotish) — Boshlang‘ich bosqich
# --------------------
@dp.message_handler(lambda message: message.text == "💰 Sotish")
async def sell_start(message: types.Message):
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog‘laning.")
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

@dp.message_handler(state=SellFSM.choose_currency)
async def sell_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    if message.text not in currencies:
        await message.answer("Bunday valyuta topilmadi. Iltimos ro‘yhatdan tanlang.")
        return

    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdor sotmoqchisiz? (raqam kiriting)")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.amount)
async def sell_amount_handler(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if txt == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    try:
        amt = float(txt.replace(",", "."))
        if amt <= 0:
            raise ValueError()
    except:
        await message.answer("Iltimos to‘g‘ri raqam kiriting (masalan: 5 yoki 0.5).")
        return

    await state.update_data(amount=amt)
    await message.answer("Hamyon raqamingizni kiriting:", reply_markup=back_kb())
    await SellFSM.next()

@dp.message_handler(state=SellFSM.wallet)
async def sell_wallet_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    await state.update_data(wallet=message.text.strip())
    data = await state.get_data()
    currency = data["currency"]
    amt = data["amount"]

    cur_info = currencies.get(currency, {})
    sell_rate = cur_info.get("sell_rate")
    if sell_rate is None:
        await message.answer("Kechirasiz, bu valyuta uchun narx ma'lum emas. Admin bilan bog‘laning.")
        await state.finish()
        return

    total = round(amt * float(sell_rate), 2)
    card = cur_info.get("sell_card", "5614 6818 7267 2690")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Chek yuborish"))
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))

    await message.answer(
        f"🔔 To‘lov tafsilotlari:\n\n"
        f"Karta/Hisob: {card}\n"
        f"Valyuta: {currency}\n"
        f"Miqdor: {amt}\n"
        f"Narx: {sell_rate}\n"
        f"Jami: {total} UZS\n\n"
        f"To‘lovni amalga oshirib, pastdagi 'Chek yuborish' tugmasini bosib to‘lov chekini yuboring.",
        reply_markup=kb
    )
    await SellFSM.confirm.set()

@dp.message_handler(state=SellFSM.confirm)
async def sell_confirm_handler(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await state.finish()
        await message.answer("Operatsiya bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return

    if message.text != "Chek yuborish":
        await message.answer("Iltimos pastdagi 'Chek yuborish' tugmasini bosing.")
        return

    await message.answer("✅ Iltimos, to‘lov chekini (rasm yoki fayl) yuboring.", reply_markup=back_kb())
    await SellFSM.upload.set()

@dp.message_handler(content_types=['photo', 'document'], state=SellFSM.upload)
async def sell_upload_handler(message: types.Message, state: FSMContext):
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
        "rate": currencies[data["currency"]]["sell_rate"]
    }

    orders[order_id] = order
    uid = str(message.from_user.id)
    users.setdefault(uid, ensure_user(message.from_user.id, message.from_user))
    users[uid].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    caption = (
        f"🆕 Yangi SELL buyurtma\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
        f"ID: {message.from_user.id}\n"
        f"Valyuta: {data['currency']}\n"
        f"Miqdor: {data['amount']}\n"
        f"Hamyon: {data['wallet']}\n"
        f"Buyurtma ID: {order_id}"
    )

    kb = admin_order_kb(order_id)

    try:
        if message.content_type == 'photo':
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=kb)
        else:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        logger.exception("Adminga yuborishda xato: %s", e)
        await message.answer("❌ Xatolik yuz berdi. Keyinroq urinib ko‘ring.")
        await state.finish()
        return

    await message.answer("✅ Chek adminga yuborildi. Tez orada tasdiqlanadi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# --------------------
# Admin — buyurtmani tasdiqlash / bekor qilish
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_callback(call: types.CallbackQuery):
    parts = call.data.split("|")
    if len(parts) != 3:
        await call.answer("Xato ma’lumot.")
        return

    action, order_id = parts[1], parts[2]
    order = orders.get(order_id)
    if not order:
        await call.answer("Buyurtma topilmadi.")
        return

    uid = order["user_id"]

    if action == "confirm":
        order["status"] = "✅ Tasdiqlandi"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(uid, f"✅ Sizning buyurtmangiz tasdiqlandi.\nBuyurtma ID: {order_id}")
        except:
            # foydalanuvchiga xabar yuborilmasa ham admin xabarni ko'radi
            pass
        # edit caption if message had one
        try:
            await call.message.edit_caption(f"{call.message.caption}\n\n✅ Admin tomonidan tasdiqlandi.")
        except:
            pass
        await call.answer("Tasdiqlandi.")

    elif action == "reject":
        order["status"] = "❌ Bekor qilindi"
        save_json(ORDERS_FILE, orders)
        try:
            await bot.send_message(uid, f"❌ Sizning buyurtmangiz bekor qilindi.\nBuyurtma ID: {order_id}")
        except:
            pass
        try:
            await call.message.edit_caption(f"{call.message.caption}\n\n❌ Admin tomonidan bekor qilindi.")
        except:
            pass
        await call.answer("Bekor qilindi.")

    else:
        await call.answer("Noma’lum amal.")

# --------------------
# ADMIN PANEL BOSHI va qolgan admin funktsiyalari (o'zgarmadi)
# --------------------
@dp.message_handler(lambda m: m.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo‘q.")
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Valyuta qo‘shish", "✏️ Valyutani tahrirlash")
    kb.row("🗑️ Valyutani o‘chirish", "📄 Valyutalar ro‘yxati")
    kb.row("📢 Xabar yuborish")
    kb.row("⬅️ Orqaga")
    await message.answer("⚙️ Admin panel menyusi:", reply_markup=kb)
    await AdminFSM.main.set()

@dp.message_handler(lambda m: m.text == "➕ Valyuta qo‘shish", state=AdminFSM.main)
async def admin_add_currency_start(message: types.Message):
    await message.answer("Yangi valyuta nomini kiriting (masalan: USDT, BTC, ETH):", reply_markup=back_kb())
    await AdminFSM.add_choose_name.set()

@dp.message_handler(state=AdminFSM.add_choose_name)
async def admin_add_currency_name(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return

    name = message.text.strip().upper()
    if name in currencies:
        await message.answer("Bu valyuta allaqachon mavjud. Boshqa nom kiriting.")
        return
    await state.update_data(name=name)
    await message.answer(f"{name} uchun **sotib olish (buy)** kursini kiriting (UZS):")
    await AdminFSM.add_set_buy_rate.set()

@dp.message_handler(state=AdminFSM.add_set_buy_rate)
async def admin_add_currency_buy_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(buy_rate=rate)
    await message.answer("Endi **sotish (sell)** kursini kiriting (UZS):")
    await AdminFSM.add_set_sell_rate.set()

@dp.message_handler(state=AdminFSM.add_set_sell_rate)
async def admin_add_currency_sell_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text.replace(",", "."))
    except:
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(sell_rate=rate)
    await message.answer("Valyutani **sotib olish kartasi** (karta raqami yoki hamyon manzili)ni kiriting:")
    await AdminFSM.add_set_buy_card.set()

@dp.message_handler(state=AdminFSM.add_set_buy_card)
async def admin_add_currency_buy_card(message: types.Message, state: FSMContext):
    await state.update_data(buy_card=message.text.strip())
    await message.answer("Endi **sotish kartasi** (karta raqami yoki hamyon manzili)ni kiriting:")
    await AdminFSM.add_set_sell_card.set()

@dp.message_handler(state=AdminFSM.add_set_sell_card)
async def admin_add_currency_sell_card(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]

    currencies[name] = {
        "buy_rate": data["buy_rate"],
        "sell_rate": data["sell_rate"],
        "buy_card": data["buy_card"],
        "sell_card": message.text.strip()
    }
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"✅ {name} valyutasi qo‘shildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(lambda m: m.text == "✏️ Valyutani tahrirlash", state=AdminFSM.main)
async def admin_edit_currency_start(message: types.Message):
    if not currencies:
        await message.answer("Hech qanday valyuta mavjud emas.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in currencies.keys():
        kb.add(types.KeyboardButton(c))
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
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
        await message.answer("Bunday valyuta topilmadi.")
        return

    await state.update_data(name=name)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row("buy_rate", "sell_rate")
    kb.row("buy_card", "sell_card")
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
    await message.answer("Qaysi maydonni tahrirlamoqchisiz?", reply_markup=kb)
    await AdminFSM.edit_field_choose.set()

@dp.message_handler(state=AdminFSM.edit_field_choose)
async def admin_edit_field_select(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return

    field = message.text.strip()
    if field not in ["buy_rate", "sell_rate", "buy_card", "sell_card"]:
        await message.answer("Noto‘g‘ri tanlov.")
        return
    await state.update_data(field=field)
    await message.answer(f"Yangi qiymatni kiriting ({field}):")
    await AdminFSM.edit_set_value.set()

@dp.message_handler(state=AdminFSM.edit_set_value)
async def admin_edit_value_set(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    field = data["field"]
    val = message.text.strip()
    if field in ["buy_rate", "sell_rate"]:
        try:
            val = float(val.replace(",", "."))
        except:
            await message.answer("Raqam kiriting.")
            return
    currencies[name][field] = val
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"✅ {name} valyutasi yangilandi ({field} = {val}).", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(lambda m: m.text == "🗑️ Valyutani o‘chirish", state=AdminFSM.main)
async def admin_delete_currency(message: types.Message):
    if not currencies:
        await message.answer("Valyutalar yo‘q.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for c in currencies.keys():
        kb.add(types.KeyboardButton(c))
    kb.add(types.KeyboardButton("⏹️ Bekor qilish"))
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
        await message.answer("Bunday valyuta topilmadi.")
        return
    currencies.pop(name)
    save_json(CURRENCIES_FILE, currencies)
    await message.answer(f"🗑️ {name} o‘chirildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(lambda m: m.text == "📄 Valyutalar ro‘yxati", state=AdminFSM.main)
async def admin_list_currencies(message: types.Message):
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas.")
        return
    text = "📄 *Valyutalar ro‘yxati:*\n\n"
    for k, v in currencies.items():
        text += (f"💱 {k}\n"
                 f"  💰 Buy rate: {v.get('buy_rate')}\n"
                 f"  💵 Sell rate: {v.get('sell_rate')}\n"
                 f"  🏦 Buy card: {v.get('buy_card')}\n"
                 f"  💳 Sell card: {v.get('sell_card')}\n\n")
    await message.answer(text, parse_mode="Markdown")

@dp.message_handler(lambda m: m.text == "📢 Xabar yuborish", state=AdminFSM.main)
async def admin_broadcast_start(message: types.Message):
    await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
    await AdminFSM.broadcast_message.set()

@dp.message_handler(state=AdminFSM.broadcast_message)
async def admin_broadcast_confirm(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return

    await state.update_data(text=message.text)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✅ Tasdiqlash", "⏹️ Bekor qilish")
    await message.answer("Ushbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?", reply_markup=kb)
    await AdminFSM.confirm_broadcast.set()

@dp.message_handler(state=AdminFSM.confirm_broadcast)
async def admin_broadcast_send(message: types.Message, state: FSMContext):
    if message.text == "⏹️ Bekor qilish":
        await admin_panel(message)
        await state.finish()
        return

    if message.text != "✅ Tasdiqlash":
        await message.answer("Iltimos, '✅ Tasdiqlash' tugmasini bosing.")
        return

    data = await state.get_data()
    text = data["text"]

    count = 0
    for uid in users.keys():
        try:
            await bot.send_message(uid, f"📢 {text}")
            count += 1
        except:
            continue

    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()


@dp.message_handler(lambda m: m.text == "⬅️ Orqaga", state=AdminFSM.main)
async def admin_back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu_kb(message.from_user.id))


# -------------------------------------------------
# Adminga xabar yuborish (ContactAdminFSM)
# -------------------------------------------------

@dp.message_handler(lambda m: m.text == "📨 Adminga xabar yuborish")
async def contact_admin_start(message: types.Message):
    await message.answer("✍️ Adminga yuboriladigan xabarni kiriting:", reply_markup=back_kb())
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
            f"📨 *Foydalanuvchidan xabar:*\n\n"
            f"👤 {message.from_user.full_name}\n"
            f"🆔 {message.from_user.id}\n\n"
            f"💬 {message.text}",
            parse_mode="Markdown",
            reply_markup=reply_kb
        )
    except Exception as e:
        logger.exception("Adminga xabar yuborishda xato: %s", e)

    await state.finish()
    await message.answer("✅ Xabaringiz adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))


# -------------------------------------------------
# Admindan foydalanuvchiga javob qaytarish (AdminReplyFSM)
# -------------------------------------------------

class AdminReplyFSM(StatesGroup):
    wait_reply = State()


@dp.callback_query_handler(lambda c: c.data.startswith("reply_to_user"))
async def admin_reply_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Siz admin emassiz.")

    user_id = call.data.split("|")[1]
    await state.update_data(reply_user_id=user_id)

    await call.message.answer("✍️ Javob matnini yoki rasmni yuboring:", reply_markup=back_kb())
    await AdminReplyFSM.wait_reply.set()
    await call.answer()


@dp.message_handler(content_types=['text', 'photo', 'document'], state=AdminReplyFSM.wait_reply)
async def admin_reply_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["reply_user_id"]

    try:
        if message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption or "")
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption or "")
        else:
            await bot.send_message(user_id, message.text)

        await message.answer("✅ Javob foydalanuvchiga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    except:
        await message.answer("❌ Xatolik: foydalanuvchi xabarlarni qabul qila olmaydi (bloklagan).")

    await state.finish()


# --------------------
# Default nomalum xabar
# --------------------
@dp.message_handler()
async def unknown_message(message: types.Message):
    await message.answer("❓ Noma’lum buyruq. Pastdagi menyudan foydalaning.", reply_markup=main_menu_kb(message.from_user.id))
# --------------------
# BOTNI ISHGA TUSHIRISH
# --------------------
if __name__ == "__main__":
    print("🤖 Bot ishga tushmoqda...")
    executor.start_polling(dp, skip_updates=True)
