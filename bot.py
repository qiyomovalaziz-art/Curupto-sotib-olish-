# obmen_bot_full.py
# -*- coding: utf-8 -*-
import os, json, time, logging, asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

# --------------------
# Sozlamalar
# --------------------
API_TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"  # 🔹 bu yerga o'z bot tokeningni qo'y
ADMIN_ID = 7973934849
CHANNELS = ["@Qiyomov_Azizbek", "@tlovchek"]
INSTAGRAM_URL = "https://www.instagram.com/azizku__2008"
DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
CURRENCIES_FILE = os.path.join(DATA_DIR, "currencies.json")

# --------------------
# Logging & Bot init
# --------------------
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --------------------
# JSON helpers
# --------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_json(USERS_FILE, {})
orders = load_json(ORDERS_FILE, {})
currencies = load_json(CURRENCIES_FILE, {})

# --------------------
# FSM holatlar
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

class MessageAdminFSM(StatesGroup):
    wait_message = State()

class SettingsFSM(StatesGroup):
    choose = State()
    change_name = State()
    add_wallet = State()
    delete_wallet = State()

# --------------------
# Asosiy menyu
# --------------------
def main_menu_kb(uid=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("💲 Sotib olish", "💰 Sotish")
    kb.row("📦 Buyurtma holati", "✉️ Adminga yozish")
    kb.row("⚙️ Sozlamalar", "📸 Instagram")
    if uid == ADMIN_ID:
        kb.add("👮‍♂️ Admin panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Orqaga")
    return kb

# --------------------
# Majburiy obuna tekshirish
# --------------------
async def check_subscription(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                return False
        except:
            return False
    return True

async def subscription_message(message):
    text = (
        "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
        "1️⃣ [@Qiyomov_Azizbek](https://t.me/Qiyomov_Azizbek)\n"
        "2️⃣ [@tlovchek](https://t.me/tlovchek)\n\n"
        "✅ Obuna bo‘lgach /start buyrug‘ini bosing."
    )
    await message.answer(text, parse_mode="Markdown")

# --------------------
# Start komandasi
# --------------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return

    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {
            "id": message.from_user.id,
            "name": message.from_user.full_name,
            "wallets": [],
            "orders": []
        }
        save_json(USERS_FILE, users)

    await message.answer(
        f"👋 Salom, {message.from_user.full_name}!\n"
        "Botimizga xush kelibsiz.\nQuyidagi menyudan kerakli bo‘limni tanlang.",
        reply_markup=main_menu_kb(message.from_user.id)
    )
    # --------------------
# 2-qism: Sotib olish / Sotish va chek yuborish
# --------------------

# Yordamchi: yangi buyurtma id
def new_order_id():
    return str(int(time.time() * 1000))

# Sotib olish start
@dp.message_handler(lambda m: m.text == "💲 Sotib olish")
async def buy_start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.", reply_markup=main_menu_kb(message.from_user.id))
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for i, cur in enumerate(currencies.keys(), 1):
        row.append(types.KeyboardButton(cur))
        if i % 2 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(types.KeyboardButton("⬅️ Orqaga"))
    await message.answer("Qaysi valyutani sotib olmoqchisiz?", reply_markup=kb)
    await BuyFSM.choose_currency.set()

@dp.message_handler(state=BuyFSM.choose_currency)
async def buy_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qayta tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda olmoqchisiz? (faqat raqam)")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.amount)
async def buy_amount(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos faqat raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon yoki karta raqamingizni kiriting:")
    await BuyFSM.next()

@dp.message_handler(state=BuyFSM.wallet)
async def buy_wallet(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    await state.update_data(wallet=message.text)
    data = await state.get_data()
    cur = data["currency"]
    amt = data["amount"]
    rate = currencies[cur]["buy_rate"]
    total = amt * rate
    card = currencies[cur].get("buy_card", "5614 6818 7267 2690")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Chek yuborish"))
    kb.add(types.KeyboardButton("⬅️ Orqaga"))

    await message.answer(
        f"{amt} {cur} uchun to‘lovni quyidagi karta raqamiga yuboring:\n{card}\n\n"
        f"Jami to‘lov: {total} UZS\n\n"
        "To'lovni amalga oshirib, chek (rasm) yuboring (Chek yuborish tugmasi yoki rasm yuboring).",
        reply_markup=kb
    )
    await BuyFSM.wait_check.set()

# qabul cheki (rasm) - buy
@dp.message_handler(content_types=['photo'], state=BuyFSM.wait_check)
async def buy_receive_check_photo(message: types.Message, state: FSMContext):
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
        "rate": currencies[data["currency"]]["buy_rate"],
        "check_photo": file_id
    }
    orders[order_id] = order
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "name": message.from_user.full_name, "wallets": [], "orders": []})
    users[str(message.from_user.id)].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    # adminga rasm va ma'lumot
    await bot.send_photo(
        ADMIN_ID, file_id,
        caption=(f"🆕 Yangi BUY buyurtma!\n\n"
                 f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
                 f"ID: {message.from_user.id}\n"
                 f"Valyuta: {data['currency']}\n"
                 f"Miqdor: {data['amount']}\n"
                 f"Hamyon: {data['wallet']}\n"
                 f"Buyurtma ID: {order_id}"),
        reply_markup=kb
    )
    await message.answer("✅ Chekingiz adminga yuborildi. Tasdiqlash kuting.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(lambda m: m.text == "Chek yuborish", state=BuyFSM.wait_check)
async def buy_wait_check_text(message: types.Message, state: FSMContext):
    await message.answer("Iltimos rasm shaklida chek yuboring.", reply_markup=back_kb())

# --------------------
# Sotish jarayoni
# --------------------
@dp.message_handler(lambda m: m.text == "💰 Sotish")
async def sell_start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return
    if not currencies:
        await message.answer("Hozircha valyuta mavjud emas. Iltimos admin bilan bog'laning.", reply_markup=main_menu_kb(message.from_user.id))
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for i, cur in enumerate(currencies.keys(), 1):
        kb.add(types.KeyboardButton(cur))
    kb.add(types.KeyboardButton("⬅️ Orqaga"))
    await message.answer("Qaysi valyutani sotmoqchisiz?", reply_markup=kb)
    await SellFSM.choose_currency.set()

@dp.message_handler(state=SellFSM.choose_currency)
async def sell_choose_currency(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    if message.text not in currencies:
        await message.answer("Valyuta topilmadi. Qaytadan tanlang.")
        return
    await state.update_data(currency=message.text)
    await message.answer(f"{message.text} bo‘yicha qancha miqdorda sotmoqchisiz?")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.amount)
async def sell_amount(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    try:
        amt = float(message.text.replace(",", "."))
    except:
        await message.answer("Iltimos faqat raqam kiriting.")
        return
    await state.update_data(amount=amt)
    await message.answer("Hamyon yoki karta raqamingizni kiriting:")
    await SellFSM.next()

@dp.message_handler(state=SellFSM.wallet)
async def sell_wallet(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
        return
    await state.update_data(wallet=message.text)
    data = await state.get_data()
    cur = data["currency"]
    amt = data["amount"]
    rate = currencies[cur]["sell_rate"]
    total = amt * rate
    card = currencies[cur].get("sell_card", "5614 6818 7267 2690")

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Chek yuborish"))
    kb.add(types.KeyboardButton("⬅️ Orqaga"))

    await message.answer(
        f"{amt} {cur} ni quyidagi karta raqamiga yuboring:\n{card}\n\n"
        f"Jami to'lov: {total} UZS\n\n"
        "To'lovni amalga oshirib, chek (rasm) yuboring.",
        reply_markup=kb
    )
    await SellFSM.wait_check.set()

@dp.message_handler(content_types=['photo'], state=SellFSM.wait_check)
async def sell_receive_check_photo(message: types.Message, state: FSMContext):
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
        "rate": currencies[data["currency"]]["sell_rate"],
        "check_photo": file_id
    }
    orders[order_id] = order
    users.setdefault(str(message.from_user.id), {"id": message.from_user.id, "name": message.from_user.full_name, "wallets": [], "orders": []})
    users[str(message.from_user.id)].setdefault("orders", []).append(order_id)
    save_json(ORDERS_FILE, orders)
    save_json(USERS_FILE, users)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_order|confirm|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_order|reject|{order_id}"))

    await bot.send_photo(ADMIN_ID, file_id, caption=f"🆕 SELL Buyurtma!\n👤 {message.from_user.full_name}\nID:{message.from_user.id}\nValyuta:{data['currency']}\nMiqdor:{data['amount']}", reply_markup=kb)
    await message.answer("✅ Buyurtma adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(lambda m: m.text == "Chek yuborish", state=SellFSM.wait_check)
async def sell_wait_check_text(message: types.Message, state: FSMContext):
    await message.answer("Iltimos rasm shaklida chek yuboring.", reply_markup=back_kb())

# --------------------
# Admin tasdiqlash/bekor qilish callback
# --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("admin_order"))
async def admin_order_cb(call: types.CallbackQuery):
    parts = call.data.split("|")
    if len(parts) != 3:
        return await call.answer("Xato callback")
    action, order_id = parts[1], parts[2]
    order = orders.get(order_id)
    if not order:
        return await call.answer("Buyurtma topilmadi")
    if action == "confirm":
        order["status"] = "confirmed"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], f"✅ Sizning buyurtmangiz ({order_id}) tasdiqlandi.")
        await call.answer("Tasdiqlandi")
    elif action == "reject":
        order["status"] = "rejected"
        save_json(ORDERS_FILE, orders)
        await bot.send_message(order["user_id"], f"❌ Sizning buyurtmangiz ({order_id}) bekor qilindi.")
        await call.answer("Bekor qilindi")
        # --------------------
# Buyurtma holatini ko‘rish
# --------------------
@dp.message_handler(lambda m: m.text == "📦 Buyurtma holati")
async def show_orders(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return
    user_id = str(message.from_user.id)
    user_orders = users.get(user_id, {}).get("orders", [])
    if not user_orders:
        await message.answer("Sizda buyurtmalar mavjud emas.", reply_markup=main_menu_kb(message.from_user.id))
        return
    text = "📋 Buyurtmalaringiz:\n\n"
    for oid in user_orders[-10:]:
        o = orders.get(oid)
        if not o:
            continue
        status = o.get("status", "noma’lum")
        text += f"🆔 ID: {oid}\n💱 {o['currency']} | {o['type']}\n💰 Miqdor: {o['amount']}\n📊 Status: {status}\n\n"
    await message.answer(text, reply_markup=main_menu_kb(message.from_user.id))

# --------------------
# Adminga yozish
# --------------------
@dp.message_handler(lambda m: m.text == "✉️ Adminga yozish")
async def contact_admin_start(message: types.Message, state: FSMContext):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return
    await message.answer("Admin uchun xabar matnini yuboring:", reply_markup=back_kb())
    await MessageAdminFSM.wait_message.set()

@dp.message_handler(state=MessageAdminFSM.wait_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb(message.from_user.id))
        return
    text = f"📩 Yangi xabar:\n\n👤 {message.from_user.full_name}\n🆔 {message.from_user.id}\n\n💬 {message.text}"
    await bot.send_message(ADMIN_ID, text)
    await message.answer("✅ Xabaringiz adminga yuborildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# --------------------
# Sozlamalar bo‘limi
# --------------------
@dp.message_handler(lambda m: m.text == "⚙️ Sozlamalar")
async def settings_start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await subscription_message(message)
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("👤 Ismni o‘zgartirish", "💳 Hamyon qo‘shish")
    kb.row("🗑 Hamyonni o‘chirish", "⬅️ Orqaga")
    await message.answer("⚙️ Sozlamalar menyusi:", reply_markup=kb)
    await SettingsFSM.choose.set()

@dp.message_handler(state=SettingsFSM.choose)
async def settings_choose(message: types.Message, state: FSMContext):
    uid = str(message.from_user.id)
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await message.answer("Bosh menyu:", reply_markup=main_menu_kb(message.from_user.id))
    elif message.text == "👤 Ismni o‘zgartirish":
        await message.answer("Yangi ismingizni kiriting:", reply_markup=back_kb())
        await SettingsFSM.change_name.set()
    elif message.text == "💳 Hamyon qo‘shish":
        await message.answer("Yangi hamyon raqamini kiriting:", reply_markup=back_kb())
        await SettingsFSM.add_wallet.set()
    elif message.text == "🗑 Hamyonni o‘chirish":
        user_wallets = users.get(uid, {}).get("wallets", [])
        if not user_wallets:
            await message.answer("Sizda saqlangan hamyon yo‘q.", reply_markup=main_menu_kb(message.from_user.id))
            await state.finish()
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for w in user_wallets:
            kb.add(types.KeyboardButton(w))
        kb.add("⬅️ Orqaga")
        await message.answer("Qaysi hamyonni o‘chirmoqchisiz?", reply_markup=kb)
        await SettingsFSM.delete_wallet.set()
    else:
        await message.answer("Noto‘g‘ri buyruq. Qayta urinib ko‘ring.")

@dp.message_handler(state=SettingsFSM.change_name)
async def change_name(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await settings_start(message)
        return
    users[str(message.from_user.id)]["name"] = message.text
    save_json(USERS_FILE, users)
    await message.answer("✅ Ismingiz yangilandi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(state=SettingsFSM.add_wallet)
async def add_wallet(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await settings_start(message)
        return
    users[str(message.from_user.id)].setdefault("wallets", []).append(message.text)
    save_json(USERS_FILE, users)
    await message.answer("✅ Hamyon raqami qo‘shildi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

@dp.message_handler(state=SettingsFSM.delete_wallet)
async def delete_wallet(message: types.Message, state: FSMContext):
    uid = str(message.from_user.id)
    if message.text == "⬅️ Orqaga":
        await state.finish()
        await settings_start(message)
        return
    if message.text in users[uid].get("wallets", []):
        users[uid]["wallets"].remove(message.text)
        save_json(USERS_FILE, users)
        await message.answer("🗑 Hamyon o‘chirildi.", reply_markup=main_menu_kb(message.from_user.id))
    else:
        await message.answer("Bunday hamyon topilmadi.", reply_markup=main_menu_kb(message.from_user.id))
    await state.finish()

# --------------------
# Instagram havolasi
# --------------------
@dp.message_handler(lambda m: m.text == "📸 Instagram")
async def show_instagram(message: types.Message):
    await message.answer(f"📸 Bizni Instagramda kuzating:\n{INSTAGRAM_URL}", disable_web_page_preview=False)

# --------------------
# Admin panel (soddalashtirilgan versiya)
# --------------------
@dp.message_handler(lambda m: m.text == "👮‍♂️ Admin panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Siz admin emassiz.")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📈 Statistika", "💬 Foydalanuvchilarga xabar yuborish")
    kb.row("⬅️ Orqaga")
    await message.answer("👮‍♂️ Admin panel:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📈 Statistika")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = len(users)
    total_orders = len(orders)
    await message.answer(f"📊 Umumiy foydalanuvchilar: {total_users}\n📦 Buyurtmalar soni: {total_orders}")

@dp.message_handler(lambda m: m.text == "💬 Foydalanuvchilarga xabar yuborish")
async def admin_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Yuboriladigan xabar matnini kiriting:", reply_markup=back_kb())
    await SettingsFSM.change_name.set()

# --------------------
# Botni ishga tushirish
# --------------------
if __name__ == "__main__":
    print("🤖 Bot ishga tushmoqda...")
    executor.start_polling(dp, skip_updates=True)
