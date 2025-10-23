# -*- coding: utf-8 -*-
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# === Sozlamalar ===
API_TOKEN = "8245974811:AAEkryr5_vYZ4m_1M8D56tIrViMe3Iwhmpc"  # Tokenni bu yerga yoz
ADMIN_ID = 7973934849  # Azizbekning admin ID

# === Log va botni ishga tushirish ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# === FSM: Adminga xabar yuborish uchun holat ===
class ContactAdminFSM(StatesGroup):
    waiting_message = State()

# === Asosiy menyu tugmalari ===
def main_keyboard():
    buttons = [
        ["🪙 Sotib olish", "💵 Sotish"],
        ["📩 Adminga xabar yuborish"]
    ]
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add(*[types.KeyboardButton(b) for row in buttons for b in row])

# === /start buyrug‘i ===
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer(
        "Salom! Bu bot orqali siz valyuta almashishingiz yoki adminga xabar yuborishingiz mumkin👇",
        reply_markup=main_keyboard()
    )

# === Sotish va sotib olish ===
@dp.message_handler(lambda message: message.text == "🪙 Sotib olish")
async def buy_currency(message: types.Message):
    await message.answer("Sotib olish uchun valyutani tanlang yoki operator bilan bog‘laning.")

@dp.message_handler(lambda message: message.text == "💵 Sotish")
async def sell_currency(message: types.Message):
    await message.answer("Sotish uchun valyutani tanlang yoki operator bilan bog‘laning.")

# === Adminga xabar yuborish ===
@dp.message_handler(lambda message: message.text == "📩 Adminga xabar yuborish")
async def contact_admin(message: types.Message):
    await message.answer("Adminga yubormoqchi bo‘lgan xabaringizni kiriting:")
    await ContactAdminFSM.waiting_message.set()

# === Foydalanuvchi xabar yuborganda ===
@dp.message_handler(state=ContactAdminFSM.waiting_message)
async def send_to_admin(message: types.Message, state: FSMContext):
    text = f"📩 <b>Yangi xabar!</b>\n\n👤 Foydalanuvchi: @{message.from_user.username or message.from_user.full_name}\n🆔 ID: {message.from_user.id}\n\n💬 Xabar:\n{message.text}"
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    await message.answer("✅ Xabaringiz adminga yuborildi!", reply_markup=main_keyboard())
    await state.finish()

# === Xatoliklar uchun fallback ===
@dp.message_handler()
async def fallback(message: types.Message):
    await message.answer("Iltimos, menyudagi tugmalardan birini tanlang.", reply_markup=main_keyboard())

# === Botni ishga tushirish ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

# --------------------
# 💲 Sotib olish funksiyasi
# --------------------
@dp.message_handler(lambda m: m.text == "💲 Sotib olish")
async def buy_start(msg: types.Message):
    await msg.answer("💰 Sotib olish summasini kiriting:", reply_markup=cancel_kb())
    await BuyFSM.amount.set()

@dp.message_handler(state=BuyFSM.amount)
async def buy_amount(msg: types.Message, state: FSMContext):
    if msg.text == "⏹️ Bekor qilish":
        await state.finish()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_menu(msg.from_user.id))
        return
    await state.update_data(amount=msg.text)
    await msg.answer("💳 Hamyon yoki karta raqamingizni kiriting:")
    await BuyFSM.wallet.set()

@dp.message_handler(state=BuyFSM.wallet)
async def buy_wallet(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = str(int(time.time() * 1000))
    order = {
        "type": "buy",
        "user_id": msg.from_user.id,
        "amount": data["amount"],
        "wallet": msg.text,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    orders[order_id] = order
    save_json(ORDERS_FILE, orders)
    await msg.answer("✅ Buyurtmangiz qabul qilindi!", reply_markup=main_menu(msg.from_user.id))
    await bot.send_message(ADMIN_ID, f"🟢 Yangi <b>SOTIB OLISH</b> buyurtma:\n\n{order}", parse_mode="HTML")
    await state.finish()

# --------------------
# 💰 Sotish funksiyasi
# --------------------
@dp.message_handler(lambda m: m.text == "💰 Sotish")
async def sell_start(msg: types.Message):
    await msg.answer("💸 Sotish summasini kiriting:", reply_markup=cancel_kb())
    await SellFSM.amount.set()

@dp.message_handler(state=SellFSM.amount)
async def sell_amount(msg: types.Message, state: FSMContext):
    if msg.text == "⏹️ Bekor qilish":
        await state.finish()
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_menu(msg.from_user.id))
        return
    await state.update_data(amount=msg.text)
    await msg.answer("💳 Hamyon yoki karta raqamingizni kiriting:")
    await SellFSM.wallet.set()

@dp.message_handler(state=SellFSM.wallet)
async def sell_wallet(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = str(int(time.time() * 1000))
    order = {
        "type": "sell",
        "user_id": msg.from_user.id,
        "amount": data["amount"],
        "wallet": msg.text,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    orders[order_id] = order
    save_json(ORDERS_FILE, orders)
    await msg.answer("✅ Buyurtmangiz qabul qilindi!", reply_markup=main_menu(msg.from_user.id))
    await bot.send_message(ADMIN_ID, f"🔴 Yangi <b>SOTISH</b> buyurtma:\n\n{order}", parse_mode="HTML")
    await state.finish()

# --------------------
# ⚙️ Admin panel
# --------------------
@dp.message_handler(lambda m: m.text == "⚙️ Admin panel")
async def admin_panel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Siz admin emassiz.")
        return
    await msg.answer("⚙️ Admin panel:\n1️⃣ Buyurtmalar soni: {}\n2️⃣ Foydalanuvchilar soni: {}".format(
        len(orders), len(users)
    ))


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
