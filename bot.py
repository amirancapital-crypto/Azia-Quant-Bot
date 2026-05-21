#!/usr/bin/env python3
"""
Azia Quant Bot — Obuna boshqaruv boti
Refactored and Debugged version
"""

import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PicklePersistence
)
from telegram.error import TelegramError

# Custom simple env loader to avoid external dependencies
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()
        except Exception as e:
            print(f"[WARNING] .env faylini o'qishda xatolik yuz berdi: {e}")

load_env()

# ===================== SOZLAMALAR =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8692951194:AAHdeM3za7Rodmc9h3sOnW1NerhHIuHVWfU")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "The_M_Maker").lstrip("@")

# Admin Telegram Raqamli ID (t.me/userinfobot orqali olinadi)
# Bir nechta bo'lsa, vergul bilan ajratib yoziladi (masalan: 6470780254,8539763294)
ADMIN_IDS = []
_admin_id_env = os.environ.get("ADMIN_ID")
if _admin_id_env:
    for x in _admin_id_env.split(","):
        try:
            ADMIN_IDS.append(int(x.strip()))
        except ValueError:
            continue

CARD_NUMBER = os.environ.get("CARD_NUMBER", "9860 1201 3287 1324")
CARD_OWNER = os.environ.get("CARD_OWNER", "G A")

# Yopiq kanallar ID lari — botni har kanalga admin qilib qo'shing
CHANNEL_IDS = {
    "signals": int(os.environ.get("CHANNEL_SIGNALS_ID", -1003859590519)),
    "onchain": int(os.environ.get("CHANNEL_ONCHAIN_ID", -1003797469259)),
}

PRICES = {3: 30, 6: 50, 0: 200}  # 0 = doimiy obuna

SECTION_NAMES = {
    "signals": "📊 Crypto va Aksiya Signallar",
    "onchain": "🔗 Onchain Trading",
}

# ===================== DATABASE SYNCHRONOUS HELPERS =====================
def _init_db_sync():
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                section TEXT NOT NULL,
                duration_months INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Database init xatosi: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _save_subscription_sync(user_id, username, full_name, section, duration):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO subscriptions (user_id, username, full_name, section, duration_months)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username or "", full_name or "Noma'lum", section, duration))
        sub_id = c.lastrowid
        conn.commit()
        return sub_id
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription saqlashda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _get_subscription_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription olishda xatolik: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def _approve_subscription_sync(sub_id, duration_months):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        now = datetime.now()
        # Doimiy obunada end_date NULL bo'ladi
        if duration_months == 0:
            end_date = None
        else:
            end_date = (now + timedelta(days=30 * duration_months)).isoformat()
        c.execute("""
            UPDATE subscriptions SET status='approved', start_date=?, end_date=? WHERE id=?
        """, (now.isoformat(), end_date, sub_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription tasdiqlashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _reject_subscription_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status='rejected' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription rad etishda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _mark_expired_sync(sub_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("UPDATE subscriptions SET status='expired' WHERE id=?", (sub_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Subscription expired belgilashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _get_expired_subscriptions_sync():
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        now = datetime.now().isoformat()
        # Doimiy obunachilar (duration_months=0) hech qachon chiqarilmaydi
        c.execute("""
            SELECT * FROM subscriptions
            WHERE status='approved' AND end_date < ? AND duration_months != 0
        """, (now,))
        rows = c.fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as e:
        print(f"[ERROR] Muddati tugaganlarni olishda xatolik: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def _save_admin_id_sync(chat_id):
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO admins (id, chat_id) VALUES (?, ?)", (chat_id, chat_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Admin ID saqlashda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def _get_admin_ids_sync():
    ids = list(ADMIN_IDS)
    try:
        conn = sqlite3.connect("azia_quant.db", timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT chat_id FROM admins")
        rows = c.fetchall()
        for row in rows:
            if row[0] not in ids:
                ids.append(row[0])
    except sqlite3.Error as e:
        print(f"[ERROR] Admin IDlarni olishda xatolik: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    return ids


# ===================== DATABASE ASYNC WRAPPERS =====================
async def init_db():
    await asyncio.to_thread(_init_db_sync)

async def save_subscription(user_id, username, full_name, section, duration):
    return await asyncio.to_thread(_save_subscription_sync, user_id, username, full_name, section, duration)

async def get_subscription(sub_id):
    return await asyncio.to_thread(_get_subscription_sync, sub_id)

async def approve_subscription(sub_id, duration_months):
    await asyncio.to_thread(_approve_subscription_sync, sub_id, duration_months)

async def reject_subscription(sub_id):
    await asyncio.to_thread(_reject_subscription_sync, sub_id)

async def mark_expired(sub_id):
    await asyncio.to_thread(_mark_expired_sync, sub_id)

async def get_expired_subscriptions():
    return await asyncio.to_thread(_get_expired_subscriptions_sync)

async def save_admin_id(chat_id):
    await asyncio.to_thread(_save_admin_id_sync, chat_id)

async def get_admin_ids():
    return await asyncio.to_thread(_get_admin_ids_sync)


# ===================== KLAVIATURALAR =====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Crypto va Aksiya Signallar", callback_data="sec_signals")],
        [InlineKeyboardButton("🔗 Onchain Trading",            callback_data="sec_onchain")],
        [InlineKeyboardButton("📚 Crypto Darslar",             callback_data="sec_crypto_edu")],
        [InlineKeyboardButton("📈 Fond Bozori Darslar",        callback_data="sec_stock_edu")],
        [InlineKeyboardButton("🤖 Quant Trading",              callback_data="sec_quant")],
        [InlineKeyboardButton("🔍 Crypto Screener",            callback_data="sec_crypto_scr")],
        [InlineKeyboardButton("🔎 Aksiya Screener",            callback_data="sec_aksiya_scr")],
        [InlineKeyboardButton("💬 Admin bilan aloqa",          callback_data="sec_admin")],
    ])

def duration_menu(section):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗓 3 oylik — $30",    callback_data=f"dur_{section}_3")],
        [InlineKeyboardButton("🗓 6 oylik — $50",    callback_data=f"dur_{section}_6")],
        [InlineKeyboardButton("♾ Doimiy — $200",    callback_data=f"dur_{section}_0")],
        [InlineKeyboardButton("⬅️ Ortga",            callback_data="back")],
    ])

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Ortga", callback_data="back")]])

def admin_menu(sub_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{sub_id}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{sub_id}"),
    ]])

# ===================== HTML XABARLAR =====================
WELCOME = """<b>Assalomu alaykum! 🤝</b>

Azia-Invest Telegram botiga xush kelibsiz.

Bu bot Azia Invest jamoasiga tegishli bo'lib, bunda siz Moliyaviy bozor tahlillari hamda Moliyaviy bozorlar haqida to'liq ma'lumotlar bilan tanishasiz. Bot mukammal AI bilan avtomatlashtirilgan bo'lib har bir signal yoki savdo tahlili murakkab screenerlar orqali aniqlanadi hamda jamoa tasdiqlagandan so'ng signal tariqasida beriladi.

📌 <b>Risk haqida ogohlantirish:</b>

Berilgan har bir signalga Azia Invest jamoasi javobgarlikni o'z zimmasiga olmaydi. Shunday ekan berilgan savdo g'oyalarni mustaqil tarzda tahlil qiling! Hech qachon bitta aktivga 100% kapitalingizni riskga qo'ymang!

Pastdagi tugmalar orqali bo'limlardan birini tanlang! 👇"""

# ===================== HANDLERLAR =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username == ADMIN_USERNAME:
        await save_admin_id(user.id)
        await update.message.reply_text("✅ Admin sifatida ro'yxatdan o'tdingiz.")
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user = q.from_user

    if user.username == ADMIN_USERNAME:
        await save_admin_id(user.id)

    # ── Bosh menyu ──
    if data == "back":
        context.user_data.clear()
        await q.edit_message_text(WELCOME, parse_mode="HTML", reply_markup=main_menu())

    # ── Faol bo'limlar ──
    elif data == "sec_signals":
        txt = (
            "📊 <b>Crypto va Aksiya Signallar</b>\n\n"
            "Quant Trading va Onchain tahlil metodlaridan foydalanib tayyorlangan "
            "professional savdo signallari.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            "• 3 oylik — $30\n"
            "• 6 oylik — $50\n"
            "• ♾ Doimiy — $200\n\n"
            "Muddatni tanlang:"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=duration_menu("signals"))

    elif data == "sec_onchain":
        txt = (
            "🔗 <b>Onchain Trading</b>\n\n"
            "Blockchain ma'lumotlari va Onchain ko'rsatkichlar asosida "
            "savdo signallari va chuqur tahlillar.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            "• 3 oylik — $30\n"
            "• 6 oylik — $50\n"
            "• ♾ Doimiy — $200\n\n"
            "Muddatni tanlang:"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=duration_menu("onchain"))

    # ── Nofaol bo'limlar ──
    elif data in ("sec_crypto_edu", "sec_stock_edu", "sec_quant", "sec_crypto_scr", "sec_aksiya_scr"):
        await q.edit_message_text(
            "⏳ <b>Bu bo'lim hali faol emas</b>\n\nTez kunda ishga tushiriladi. Kuzatib boring! 🚀",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── Admin aloqa ──
    elif data == "sec_admin":
        await q.edit_message_text(
            f"💬 <b>Admin bilan aloqa</b>\n\nSavol va murojaat uchun:\n👤 @{ADMIN_USERNAME}",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── Muddat tanlash ──
    elif data.startswith("dur_"):
        _, section, months_str = data.split("_")
        duration = int(months_str)
        price = PRICES[duration]
        section_name = SECTION_NAMES[section]
        duration_label = "♾ Doimiy" if duration == 0 else f"{duration} oy"

        sub_id = await save_subscription(user.id, user.username, user.full_name, section, duration)
        context.user_data['sub_id'] = sub_id
        context.user_data['waiting_payment'] = True

        txt = (
            f"💳 <b>To'lov ma'lumotlari</b>\n\n"
            f"📦 Bo'lim: <b>{section_name}</b>\n"
            f"⏱ Muddat: <b>{duration_label}</b>\n"
            f"💰 Summa: <b>${price}</b>\n\n"
            f"🏦 <b>Karta raqami:</b>\n<code>{CARD_NUMBER}</code>\n"
            f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
            f"To'lovni amalga oshirgach, <b>to'lov cheki rasmini</b> shu chatga yuboring. 👇"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=back_menu())

    # ── Admin: Tasdiqlash ──
    elif data.startswith("approve_"):
        sub_id = int(data.split("_")[1])
        sub = await get_subscription(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return

        if sub['status'] != 'pending':
            await q.answer("Ushbu obuna so'rovi allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        channel_id = CHANNEL_IDS.get(sub['section'])
        if not channel_id:
            await q.answer("Kanal ID topilmadi!", show_alert=True)
            return
        duration = sub['duration_months']
        duration_label = "♾ Doimiy" if duration == 0 else f"{duration} oy"

        try:
            # Taklif havolasi 24 soat davomida faol bo'lsin.
            # a'zolik muddati esa ma'lumotlar bazasida saqlanadi.
            link_expire = datetime.now() + timedelta(hours=24)
            if duration == 0:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id,
                    member_limit=1,
                )
            else:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id,
                    member_limit=1,
                    expire_date=link_expire
                )
            await approve_subscription(sub_id, duration)
            section_name = SECTION_NAMES.get(sub['section'], sub['section'])
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"📦 <b>Bo'lim:</b> {section_name}\n"
                    f"⏱ <b>Muddat:</b> {duration_label}\n\n"
                    f"🔗 <b>Kanal havolasi:</b>\n{link_obj.invite_link}\n\n"
                    f"⚠️ Havola <b>bir martalik</b> — faqat siz uchun."
                ),
                parse_mode="HTML"
            )
            # Tugmalarni olib tashlaymiz
            await q.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"✅ <b>#{sub_id} — TASDIQLANDI.</b> Havola yuborildi.",
                parse_mode="HTML"
            )
        except TelegramError as e:
            await q.answer(f"Xato: {e}", show_alert=True)

    # ── Admin: Rad etish ──
    elif data.startswith("reject_"):
        sub_id = int(data.split("_")[1])
        sub = await get_subscription(sub_id)
        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return

        if sub['status'] != 'pending':
            await q.answer("Ushbu obuna so'rovi allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        await reject_subscription(sub_id)
        await context.bot.send_message(
            chat_id=sub['user_id'],
            text=(
                "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                f"Murojaat uchun: @{ADMIN_USERNAME}"
            ),
            parse_mode="HTML"
        )
        # Tugmalarni olib tashlaymiz
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"❌ <b>#{sub_id} — RAD ETILDI.</b>",
            parse_mode="HTML"
        )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi to'lov chekini yuborsa adminga xabar beradi."""
    if not context.user_data.get('waiting_payment'):
        return

    sub_id = context.user_data.get('sub_id')
    if not sub_id:
        return

    sub = await get_subscription(sub_id)
    if not sub or sub['status'] != 'pending':
        return

    admin_ids = await get_admin_ids()
    if not admin_ids:
        print("[WARNING] Birorta ham admin topilmadi! To'lov so'rovini yuborib bo'lmadi.")
        await update.message.reply_text(
            "❌ <b>Hozirda administratorlar ro'yxatdan o'tmagan.</b>\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring yoki administratorlar bilan bog'laning.",
            parse_mode="HTML"
        )
        return

    context.user_data['waiting_payment'] = False
    context.user_data['sub_id'] = None

    await update.message.reply_text(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "Admin tekshirgandan so'ng sizga havola yuboriladi.\n"
        "Odatda <b>5–30 daqiqa</b> ichida.",
        parse_mode="HTML"
    )

    section_name = SECTION_NAMES.get(sub['section'], sub['section'])
    username_display = f"@{sub['username']}" if sub.get('username') else "yo'q"
    duration_label = "♾ Doimiy" if sub['duration_months'] == 0 else f"{sub['duration_months']} oy"
    caption = (
        f"💳 <b>Yangi to'lov so'rovi #{sub_id}</b>\n\n"
        f"👤 Ism: {sub['full_name']}\n"
        f"🔖 Username: {username_display}\n"
        f"🆔 ID: <code>{sub['user_id']}</code>\n"
        f"📦 Bo'lim: {section_name}\n"
        f"⏱ Muddat: {duration_label}\n"
        f"💰 Summa: ${PRICES[sub['duration_months']]}"
    )
    photo = update.message.photo[-1].file_id
    
    success_count = 0
    for admin_id in admin_ids:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=admin_menu(sub_id)
            )
            success_count += 1
        except TelegramError as e:
            print(f"[WARNING] Adminga ({admin_id}) chek yuborishda Telegram xatoligi: {e}")

    if success_count == 0:
        await update.message.reply_text(
            "❌ <b>Chekni administratorga yuborishda xatolik yuz berdi.</b>\n\n"
            "Iltimos, birozdan so'ng qayta urinib ko'ring.",
            parse_mode="HTML"
        )
        # Qayta urinishi uchun holatni tiklaymiz
        context.user_data['waiting_payment'] = True
        context.user_data['sub_id'] = sub_id


async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    """Har soatda obuna muddati tugaganlarni kanaldan chiqaradi."""
    expired = await get_expired_subscriptions()
    for sub in expired:
        channel_id = CHANNEL_IDS.get(sub['section'])
        if not channel_id:
            await mark_expired(sub['id'])
            continue
        try:
            await context.bot.ban_chat_member(channel_id, sub['user_id'])
            await context.bot.unban_chat_member(channel_id, sub['user_id'])
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    "⏰ <b>Obuna muddatingiz tugadi.</b>\n\n"
                    "Davom ettirish uchun /start yuboring."
                ),
                parse_mode="HTML"
            )
            # Faqat muvaffaqiyatli bo'lganda expired deb belgilaymiz
            await mark_expired(sub['id'])
        except TelegramError as e:
            print(f"[WARNING] Foydalanuvchini kanaldan chiqarishda xatolik (User: {sub['user_id']}): {e}")


# ===================== MAIN =====================
def main():
    _init_db_sync()
    
    # PicklePersistence orqali bot holatini saqlash (restart bo'lganda ham o'chib ketmaydi)
    persistence = PicklePersistence(filepath="bot_persistence.pickle")
    
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Har soatda obunalarni tekshiradi
    if app.job_queue:
        app.job_queue.run_repeating(check_expired, interval=3600, first=60)

    print("[SUCCESS] Azia Quant Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()