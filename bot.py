#!/usr/bin/env python3
"""
Azia Quant Bot — Main Bot Module
Barcha handlerlar va asosiy bot logikasi
"""

import os
import asyncio
import random
import string
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PicklePersistence
)
from telegram.error import TelegramError

from config import (
    BOT_TOKEN, ADMIN_USERNAME, CARD_NUMBER, CARD_OWNER,
    CHANNEL_IDS, SECTION_NAMES, CHANNEL_SECTIONS,
    SIGNAL_PRICES, SCREENER_PRICES, CRYPTO_EDU_PRICE,
    STOCK_EDU_PRICE, PREMIUM_PRICE,
    REFERRAL_PERCENT, AFFILIATE_PERCENT,
    FREE_DAILY_LIMIT, WELCOME_TEXT
)
from database import (
    init_db, save_admin_id, get_admin_ids,
    save_subscription, get_subscription,
    approve_subscription, reject_subscription,
    check_channel_access, get_expired_subscriptions, mark_expired,
    save_screener_sub, get_screener_sub,
    approve_screener_sub, reject_screener_sub,
    check_screener_access, get_expired_screener_subs, mark_screener_expired,
    save_premium_sub, get_premium_sub,
    approve_premium_sub, reject_premium_sub, check_premium_access,
    save_alert, get_active_alerts, get_user_alerts,
    deactivate_alert, delete_alert,
    add_portfolio, get_portfolio, delete_portfolio_item,
    save_referral, get_referral_stats, update_referral_reward,
    save_affiliate, get_affiliate, get_affiliate_by_code,
    approve_affiliate, add_affiliate_earning, get_all_affiliates,
    check_free_usage, increment_free_usage,
    check_promo_code, use_promo_code, create_promo_code,
    save_onchain_signal, mark_signal_sent,
    add_watchlist, get_watchlist, remove_watchlist,
    save_search, get_search_history,
    get_stats, get_all_users, cancel_subscription,
    cancel_screener_subscription, cancel_premium_subscription,
    save_user, get_non_subscribers, get_all_bot_users,
    get_all_promos, delete_promo_code,
)
from keyboards import (
    main_menu, back_menu, home_menu, confirm_menu, section_back_menu,
    signals_duration_menu, screener_duration_menu,
    admin_approve_menu, onchain_signal_menu,
    free_menu, calculator_menu,
    screener_action_menu, free_screener_result_menu,
    alert_type_menu, alert_condition_menu, my_alerts_menu,
    portfolio_menu, referral_menu,
    admin_main_menu, main_reply_menu,
)
from screener_stock import get_stock_data
from screener_crypto import get_crypto_data, get_coin_id
from onchain import format_onchain_report, format_market_status
from ai_module import ask_ai


# ===================== YORDAMCHI FUNKSIYALAR =====================

def generate_code(length=8):
    """Tasodifiy kod generatsiya"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def duration_label(duration):
    """Muddat yorlig'ini to'g'ri formatlash"""
    if duration == 0:
        return "♾ Doimiy"
    elif duration == 12:
        return "1 yil"
    elif duration == 6:
        return "6 oy"
    else:
        return f"{duration} oy"


async def is_admin(user) -> bool:
    """Admin ekanligini tekshirish"""
    if user.username and user.username.lstrip('@') == ADMIN_USERNAME:
        return True
    admin_ids = await get_admin_ids()
    return user.id in admin_ids


async def send_payment_info(query, section_name, price, dur_label, sub_id, sub_type, discount=0):
    """To'lov ma'lumotlarini yuborish"""
    final_price = price * (1 - discount / 100) if discount > 0 else price

    price_txt = f"${final_price:.0f}"
    if discount > 0:
        price_txt = f"~~${price}~~ → <b>${final_price:.0f}</b> ({discount}% chegirma 🎉)"

    txt = (
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📦 Bo'lim: <b>{section_name}</b>\n"
        f"⏱ Muddat: <b>{dur_label}</b>\n"
        f"💰 Summa: {price_txt}\n\n"
        f"🏦 <b>Karta raqami:</b>\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
        f"✅ To'lovni amalga oshirgach, "
        f"<b>to'lov cheki rasmini</b> shu chatga yuboring. 👇"
    )

    # Promo kod tugmasi
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Promo kod bormi?", callback_data=f"promo_{sub_type}_{sub_id}_{int(price)}")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
    ]) if discount == 0 else back_menu()

    await query.edit_message_text(txt, parse_mode="HTML", reply_markup=markup)


# ===================== SHOW SECTION (Reply Keyboard uchun) =====================

async def show_section(update: Update, context: ContextTypes.DEFAULT_TYPE, section: str):
    """Reply Keyboard tugmasi bosilganda bo'limni ko'rsatish"""
    user  = update.effective_user
    admin = await is_admin(user)

    if section == "sec_signals":
        txt = (
            "📊 <b>Crypto va Aksiya Signallar</b>\n\n"
            "Professional savdo signallari.\n\n"
            f"💰 <b>Narxlar:</b>\n"
            f"• 6 oylik — ${SIGNAL_PRICES[6]}\n"
            f"• 1 yillik — ${SIGNAL_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SIGNAL_PRICES[0]}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=signals_duration_menu())

    elif section == "sec_onchain":
        txt = (
            "🔗 <b>Onchain + Screener</b>\n\n"
            "Professional screener va onchain tahlil.\n\n"
            f"💰 <b>Narxlar:</b>\n"
            f"• 6 oylik — ${SCREENER_PRICES[6]}\n"
            f"• 1 yillik — ${SCREENER_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SCREENER_PRICES[0]}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=screener_duration_menu())

    elif section == "sec_crypto_edu":
        txt = (
            "📚 <b>Crypto Darslar</b>\n\n"
            "Crypto bozorini noldan professional\n"
            "darajagacha o'rganing!\n\n"
            f"💰 <b>Narx:</b> ${CRYPTO_EDU_PRICE}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=confirm_menu("crypto_edu"))

    elif section == "sec_stock_edu":
        txt = (
            "📈 <b>Fond Bozori Darslar</b>\n\n"
            "Aksiya bozorini professional\n"
            "darajada o'rganing!\n\n"
            f"💰 <b>Narx:</b> ${STOCK_EDU_PRICE}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=confirm_menu("stock_edu"))

    elif section == "sec_quant":
        txt = (
            "🤖 <b>Quant Trading</b>\n\n"
            "Algoritmik trading va kvant\n"
            "strategiyalarini o'rganing!\n\n"
            f"💰 <b>Narx:</b> ${SIGNAL_PRICES[0]}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=confirm_menu("quant"))

    elif section == "sec_ai":
        context.user_data['ai_mode'] = True
        await update.message.reply_text(
            "🧠 <b>AI Moliyaviy Yordamchi</b>\n\n"
            "Savolingizni yozing — javob beraman!\n\n"
            "Chiqish uchun /start bosing.",
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    elif section == "sec_premium":
        txt = (
            "💎 <b>Premium To'liq Paket</b>\n\n"
            "Barcha bo'limlarga to'liq kirish!\n\n"
            f"💰 <b>Narx:</b> ${PREMIUM_PRICE}\n"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=confirm_menu("premium"))

    elif section == "sec_free":
        await update.message.reply_text(
            "🆓 <b>Bepul Xizmatlar</b>\n\nQuyidagilardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=free_menu()
        )

    elif section == "sec_admin":
        await update.message.reply_text(
            f"💬 <b>Admin bilan aloqa</b>\n\n"
            f"Savolingizni yuboring!\n\n"
            f"📞 Admin: @{ADMIN_USERNAME}",
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    elif section == "my_subs":
        has_signals  = await check_channel_access(user.id, "signals")
        has_onchain  = await check_channel_access(user.id, "onchain")
        has_screener = await check_screener_access(user.id)
        has_premium  = await check_premium_access(user.id)

        if not any([has_signals, has_onchain, has_screener, has_premium]):
            await update.message.reply_text(
                "📋 <b>Mening Obunalarim</b>\n\nSizda hozircha faol obuna yo'q.",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        else:
            txt = "📋 <b>Mening Obunalarim</b>\n\n"
            if has_signals:  txt += "✅ Signals\n"
            if has_onchain:  txt += "✅ Onchain\n"
            if has_screener: txt += "✅ Screener\n"
            if has_premium:  txt += "✅ Premium\n"
            await update.message.reply_text(txt, parse_mode="HTML", reply_markup=home_menu())

    elif section == "my_portfolio":
        has_signals  = await check_channel_access(user.id, "signals")
        has_screener = await check_screener_access(user.id)
        has_premium  = await check_premium_access(user.id)
        if not (has_signals or has_screener or has_premium):
            await update.message.reply_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>\n\n"
                "Istalgan obunani sotib oling.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")],
                ])
            )
            return
        items = await get_portfolio(user.id)
        await update.message.reply_text(
            "💼 <b>Mening Portfelim</b>",
            parse_mode="HTML",
            reply_markup=portfolio_menu(items)
        )

    elif section == "referral_menu":
        await update.message.reply_text(
            "👥 <b>Referral tizimi</b>",
            parse_mode="HTML",
            reply_markup=referral_menu()
        )

    elif section == "open_admin":
        if not admin:
            await update.message.reply_text("❌ Ruxsat yo'q!")
            return
        await update.message.reply_text(
            "👨‍💼 <b>Admin Panel</b>",
            parse_mode="HTML",
            reply_markup=admin_main_menu()
        )



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Admin tekshirish
    if user.username and user.username.lstrip('@') == ADMIN_USERNAME:
        await save_admin_id(user.id)

    # Foydalanuvchini saqlash
    await save_user(user.id, user.username, user.full_name)

    # Referral tekshirish
    args = context.args
    if args:
        code = args[0]
        if code.startswith('ref_'):
            referral_code = code[4:]
            context.user_data['referral_code'] = referral_code
        elif code.startswith('aff_'):
            affiliate_code = code[4:]
            context.user_data['affiliate_code'] = affiliate_code

    # Faqat kerakli holatlarni tozalash (ai_mode saqlansin)
    keys_to_clear = ['screener_mode', 'waiting_payment', 'sub_id', 'scr_sub_id',
                     'premium_sub_id', 'sub_type', 'calc_mode', 'alert_pending',
                     'portfolio_pending', 'portfolio_new', 'admin_broadcast',
                     'admin_broadcast_nonsub', 'admin_promo', 'admin_cancel_sub',
                     'aff_apply', 'aff_code', 'promo_pending', 'editing_signal']
    for key in keys_to_clear:
        context.user_data.pop(key, None)

    admin = await is_admin(user)
    # Pastki Reply Keyboard
    await update.message.reply_text(
        "👇 Tez kirish uchun pastdagi tugmalardan foydalaning:",
        reply_markup=main_reply_menu(is_admin=admin)
    )
    # Inline menyu bilan Welcome xabar
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu(is_admin=admin)
    )


# ===================== ADMIN BUYRUG'I =====================

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return
    await save_admin_id(user.id)
    await update.message.reply_text(
        "👨‍💼 <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_main_menu()
    )


# ===================== BUTTON HANDLER =====================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    data = q.data
    user = q.from_user

    # Admin tekshirish
    if user.username and user.username.lstrip('@') == ADMIN_USERNAME:
        await save_admin_id(user.id)

    # Separator (bosilmaydi)
    if data == "sep":
        return

    # ── BOSH MENYU ──
    if data == "back":
        context.user_data.clear()
        admin = await is_admin(user)
        try:
            await q.edit_message_text(
                WELCOME_TEXT, parse_mode="HTML",
                reply_markup=main_menu(is_admin=admin)
            )
        except:
            await q.message.reply_text(
                WELCOME_TEXT, parse_mode="HTML",
                reply_markup=main_menu(is_admin=admin)
            )

    # ── ADMIN PANEL (bosh menyudan) ──
    elif data == "open_admin":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        await q.edit_message_text(
            "👨‍💼 <b>Admin Panel</b>",
            parse_mode="HTML",
            reply_markup=admin_main_menu()
        )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── SIGNALS ──
    elif data == "sec_signals":
        txt = (
            "📊 <b>Crypto va Aksiya Signallar</b>\n\n"
            "Azia Quant jamoasi murakkab Kvant\n"
            "algoritmlari va Onchain tahlil\n"
            "metodlari asosida professional savdo\n"
            "signallarini taqdim etadi.\n\n"
            "🎯 <b>Nimalar olasiz:</b>\n"
            "• Crypto va Aksiya signallari\n"
            "• Aniq kirish nuqtalari\n"
            "• Take Profit darajalari\n"
            "• Stop Loss tavsiyalari\n"
            "• Risk menejment ko'rsatmalari\n"
            "• Bozor tahlili va sharhlar\n\n"
            "📈 Har bir signal jamoa tomonidan\n"
            "tasdiqlanadi va murakkab screenerlar\n"
            "orqali tekshiriladi.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            f"• 6 oylik — ${SIGNAL_PRICES[6]}\n"
            f"• 1 yillik — ${SIGNAL_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SIGNAL_PRICES[0]}\n\n"
            "💡 Signallar professional tahlil\n"
            "natijasidir. Eng yaxshi natija uchun\n"
            "ularni o'z risk menejmentingiz bilan\n"
            "birga qo'llang.\n\n"
            "<b>Obuna bo'lasizmi?</b>"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("signals"))

    elif data == "confirm_signals":
        await q.edit_message_text(
            "📊 <b>Signals — Muddatni tanlang:</b>\n\n"
            f"• 6 oylik — ${SIGNAL_PRICES[6]}\n"
            f"• 1 yillik — ${SIGNAL_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SIGNAL_PRICES[0]}",
            parse_mode="HTML",
            reply_markup=signals_duration_menu()
        )

    elif data.startswith("sig_dur_"):
        duration = int(data.split("_")[2])
        price    = SIGNAL_PRICES[duration]
        dur_label = duration_label(duration)
        sub_id   = await save_subscription(
            user.id, user.username, user.full_name, "signals", duration
        )
        context.user_data['waiting_payment'] = True
        context.user_data['sub_id']          = sub_id
        context.user_data['sub_type']        = 'channel'
        await send_payment_info(q, SECTION_NAMES['signals'], price, dur_label, sub_id, 'channel')

    # ━━━━━━━━━━━━━━━━━━━━
    # ── ONCHAIN + SCREENER ──
    elif data == "sec_onchain":
        # Obuna bormi tekshirish
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if has_access:
            # Obunachi — screener menyusi
            await q.edit_message_text(
                "🔗 <b>Onchain + Screener</b>\n\n"
                "✅ Obunangiz faol!\n\n"
                "Quyidagilardan birini tanlang:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔎 Aksiya Screener",  callback_data="use_stock_screener")],
                    [InlineKeyboardButton("🔍 Crypto Screener",  callback_data="use_crypto_screener")],
                    [InlineKeyboardButton("🔗 Onchain Tahlil",   callback_data="use_onchain_report")],
                    [InlineKeyboardButton("🏠 Bosh menyu",       callback_data="back")],
                ])
            )
            return
        txt = (
            "🔗 <b>Onchain + Aksiya + Crypto Screener</b>\n\n"
            "Eng kuchli paket! Uch xizmat bir joyda.\n\n"
            "🔗 <b>Onchain Trading Kanali:</b>\n"
            "Blockchain ma'lumotlari asosida\n"
            "professional tahlillar. Whale\n"
            "harakatlari, exchange oqimlari,\n"
            "DeFi ko'rsatkichlari.\n\n"
            "🔎 <b>Aksiya Screener:</b>\n"
            "Istalgan AQSh aksiyasini bir tugma\n"
            "bilan to'liq tahlil qiling — 15+\n"
            "moliyaviy ko'rsatkich, insider\n"
            "tranzaksiyalar, choraklik hisobotlar.\n\n"
            "🔍 <b>Crypto Screener:</b>\n"
            "Istalgan coin haqida to'liq ma'lumot —\n"
            "Token Unlock, Fear & Greed, texnik\n"
            "ko'rsatkichlar, developer faolligi.\n\n"
            "💡 Yahoo Finance, CoinGecko va boshqa\n"
            "ishonchli manbalardan real vaqtda\n"
            "ma'lumot olasiz.\n\n"
            "💰 <b>Obuna narxlari:</b>\n"
            f"• 6 oylik — ${SCREENER_PRICES[6]}\n"
            f"• 1 yillik — ${SCREENER_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SCREENER_PRICES[0]}\n\n"
            "<b>Obuna bo'lasizmi?</b>"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("onchain"))

    # ── Screener tanlash (obunachilar uchun) ──
    elif data == "use_stock_screener":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return
        context.user_data['screener_mode'] = 'stock'
        await q.edit_message_text(
            "🔎 <b>Aksiya Screener</b>\n\n"
            "Aksiya ticker yuboring.\n"
            "Masalan: <code>AAPL</code>, <code>TSLA</code>, <code>MSFT</code>\n\n"
            "Ticker kiriting:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Ortga", callback_data="sec_onchain")],
            ])
        )

    elif data == "use_crypto_screener":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return
        context.user_data['screener_mode'] = 'crypto'
        await q.edit_message_text(
            "🔍 <b>Crypto Screener</b>\n\n"
            "Coin ticker yuboring.\n"
            "Masalan: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>\n\n"
            "Ticker kiriting:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Ortga", callback_data="sec_onchain")],
            ])
        )

    elif data == "use_onchain_report":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return
        await q.edit_message_text("⏳ Onchain ma'lumotlar olinmoqda...", parse_mode="HTML")
        report = await asyncio.to_thread(format_onchain_report)
        await q.edit_message_text(
            report, parse_mode="HTML",
            reply_markup=home_menu(),
            disable_web_page_preview=True
        )

    elif data == "confirm_onchain":
        await q.edit_message_text(
            "🔗 <b>Onchain + Screener — Muddatni tanlang:</b>\n\n"
            f"• 6 oylik — ${SCREENER_PRICES[6]}\n"
            f"• 1 yillik — ${SCREENER_PRICES[12]}\n"
            f"• ♾ Doimiy — ${SCREENER_PRICES[0]}",
            parse_mode="HTML",
            reply_markup=screener_duration_menu()
        )

    elif data.startswith("scr_dur_"):
        duration  = int(data.split("_")[2])
        price     = SCREENER_PRICES[duration]
        dur_label = duration_label(duration)

        # Kanala ham, screener ham
        sub_id = await save_subscription(
            user.id, user.username, user.full_name, "onchain", duration
        )
        scr_id = await save_screener_sub(
            user.id, user.username, user.full_name, duration
        )
        context.user_data['waiting_payment'] = True
        context.user_data['sub_id']          = sub_id
        context.user_data['scr_sub_id']      = scr_id
        context.user_data['sub_type']        = 'onchain_screener'
        await send_payment_info(q, SECTION_NAMES['screener'], price, dur_label, sub_id, 'onchain_screener')

    # ━━━━━━━━━━━━━━━━━━━━
    # ── CRYPTO DARSLAR ──
    elif data == "sec_crypto_edu":
        txt = (
            "📚 <b>Crypto Darslar</b>\n\n"
            "Crypto bozorini noldan professional\n"
            "darajagacha o'rganing!\n\n"
            "📖 <b>Kurs dasturi:</b>\n"
            "• Blockchain texnologiyasi asoslari\n"
            "• Kripto hamyon va xavfsizlik\n"
            "• Texnik tahlil (grafik, indikatorlar)\n"
            "• Fundamental tahlil\n"
            "• DeFi, NFT va Web3 dunyosi\n"
            "• Risk menejment va psixologiya\n"
            "• Amaliy savdo strategiyalari\n\n"
            "🎓 Doimiy kirish — bir marta to'lab,\n"
            "umrbod foydalaning. Yangi darslar\n"
            "muntazam qo'shilib boriladi.\n\n"
            f"💰 <b>Doimiy obuna: ${CRYPTO_EDU_PRICE}</b>\n\n"
            "<b>Obuna bo'lasizmi?</b>"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("crypto_edu"))

    elif data == "confirm_crypto_edu":
        sub_id = await save_subscription(
            user.id, user.username, user.full_name, "crypto_edu", 0
        )
        context.user_data['waiting_payment'] = True
        context.user_data['sub_id']          = sub_id
        context.user_data['sub_type']        = 'channel'
        await send_payment_info(q, SECTION_NAMES['crypto_edu'], CRYPTO_EDU_PRICE, "♾ Doimiy", sub_id, 'channel')

    # ━━━━━━━━━━━━━━━━━━━━
    # ── FOND BOZORI DARSLAR ──
    elif data == "sec_stock_edu":
        await q.edit_message_text(
            "⏳ <b>Fond Bozori Darslar</b>\n\n"
            "Bu bo'lim hali tayyorlanmoqda.\n"
            "Tez kunda ishga tushiriladi! 🚀",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── QUANT TRADING ──
    elif data == "sec_quant":
        await q.edit_message_text(
            "⏳ <b>Quant Trading</b>\n\n"
            "Bu bo'lim hali tayyorlanmoqda.\n"
            "Tez kunda ishga tushiriladi! 🚀",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── AI YORDAMCHI ──
    elif data == "sec_ai":
        await q.edit_message_text(
            "🧠 <b>AI Moliyaviy Yordamchi</b>\n\n"
            "Bu bo'lim tez kunda ishga tushiriladi! 🚀\n\n"
            "Kuchli AI modeli ulangandan so'ng:\n"
            "• Aksiya va crypto tahlili\n"
            "• Trading strategiyalari\n"
            "• Risk menejment maslahati\n"
            "• Portfolio diversifikatsiya\n\n"
            "Kuzatib boring! 📡",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    elif data == "ai_start":
        context.user_data['ai_mode'] = True
        context.user_data['ai_history'] = []
        await q.edit_message_text(
            "🤖 <b>AI Yordamchi</b>\n\n"
            "Savolingizni yozing!\n\n"
            "Misol:\n"
            "• <i>AAPL ni tahlil qil</i>\n"
            "• <i>BTC ga hozir kirsa bo'ladimi?</i>\n"
            "• <i>Risk menejment nima?</i>\n"
            "• <i>Portfolio qanday tuzish kerak?</i>\n\n"
            "💡 Suhbat davomli — oldingi savollar esda saqlanadi!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Suhbatni tozalash", callback_data="ai_clear")],
                [InlineKeyboardButton("⬅️ Chiqish",           callback_data="ai_exit")],
            ])
        )

    elif data == "ai_exit":
        context.user_data.pop('ai_mode', None)
        context.user_data.pop('ai_history', None)
        await q.edit_message_text(
            "🤖 <b>AI Moliyaviy Yordamchi</b>\n\n"
            "Professional moliyaviy maslahatchi!\n\n"
            "💬 <b>Nima so'rasangiz bo'ladi:</b>\n"
            "• Aksiya va crypto tahlili\n"
            "• Trading strategiyalari\n"
            "• Risk menejment maslahati\n"
            "• Moliyaviy atamalar tushuntirish\n"
            "• Portfolio diversifikatsiya\n"
            "• DeFi va Web3 haqida\n\n"
            "⚡ Savolingizni yozing!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Suhbatni boshlash", callback_data="ai_start")],
                [InlineKeyboardButton("⬅️ Ortga",             callback_data="back")],
            ])
        )

    elif data == "ai_clear":
        context.user_data['ai_mode'] = True
        context.user_data['ai_history'] = []
        await q.edit_message_text(
            "🤖 <b>AI Yordamchi</b>\n\n"
            "✅ Suhbat tozalandi!\n\n"
            "Yangi savol yozing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Ortga", callback_data="sec_ai")],
            ])
        )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── PREMIUM PAKET ──
    elif data == "sec_premium":
        savings = SIGNAL_PRICES[0] + SCREENER_PRICES[0] + CRYPTO_EDU_PRICE + STOCK_EDU_PRICE
        txt = (
            "💎 <b>Premium To'liq Paket</b>\n\n"
            "Azia Quant ning BARCHA xizmatlari\n"
            "bitta paketda — eng tejamkor variant!\n\n"
            "✅ 📊 Signals kanali\n"
            "✅ 🔗 Onchain Trading kanali\n"
            "✅ 🔎 Aksiya Screener\n"
            "✅ 🔍 Crypto Screener\n"
            "✅ 📚 Crypto Darslar kanali\n"
            "✅ 📈 Fond Bozori Darslar kanali\n\n"
            f"💰 Alohida olganda: ${savings}\n"
            f"💎 Premium paket: ${PREMIUM_PRICE}\n"
            f"🎁 Tejaysiz: ${savings - PREMIUM_PRICE}!\n\n"
            "♾ Doimiy kirish — barcha bo'limlarga\n"
            "umrbod foydalanish huquqi.\n\n"
            "<b>Obuna bo'lasizmi?</b>"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("premium"))

    elif data == "confirm_premium":
        sub_id = await save_premium_sub(user.id, user.username, user.full_name)
        context.user_data['waiting_payment']  = True
        context.user_data['premium_sub_id']   = sub_id
        context.user_data['sub_type']         = 'premium'
        await send_payment_info(q, SECTION_NAMES['premium'], PREMIUM_PRICE, "♾ Doimiy", sub_id, 'premium')

    # ━━━━━━━━━━━━━━━━━━━━
    # ── BEPUL XIZMATLAR ──
    elif data == "sec_free":
        await q.edit_message_text(
            "🆓 <b>Bepul Xizmatlar</b>\n\n"
            "Ro'yxatdan xizmatni tanlang:",
            parse_mode="HTML",
            reply_markup=free_menu()
        )

    elif data == "free_market":
        await q.edit_message_text("⏳ Ma'lumot olinmoqda...", parse_mode="HTML")
        report = await asyncio.to_thread(format_market_status)
        await q.edit_message_text(report, parse_mode="HTML", reply_markup=home_menu(), disable_web_page_preview=True)

    elif data == "free_screener":
        context.user_data['screener_mode'] = 'free'
        await q.edit_message_text(
            "🔍 <b>Bepul Screener</b>\n\n"
            f"Kuniga {FREE_DAILY_LIMIT} ta bepul screener!\n\n"
            "Aksiya ticker yoki crypto nomi yozing:\n"
            "• Aksiya: <code>AAPL</code>, <code>TSLA</code>, <code>MSFT</code>\n"
            "• Crypto: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    elif data == "free_news":
        await q.edit_message_text("⏳ Yangiliklar olinmoqda...", parse_mode="HTML")
        try:
            import feedparser
            news_txt = "📰 <b>Moliyaviy Yangiliklar</b>\n\n"

            feeds = [
                ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
                ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
                ("CoinTelegraph", "https://cointelegraph.com/rss"),
            ]
            count = 0
            for src_name, feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:2]:
                        title = (entry.get('title') or '')[:65]
                        link  = entry.get('link') or ''
                        if title and link:
                            news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {src_name}\n\n"
                            count += 1
                except: continue
                if count >= 6: break

            if count == 0:
                news_txt += "• Yangilik topilmadi"
        except:
            news_txt = "📰 <b>Yangiliklar</b>\n\n• Hozircha ma'lumot yo'q"

        await q.edit_message_text(
            news_txt,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yangilash", callback_data="free_news")],
                [InlineKeyboardButton("⬅️ Ortga", callback_data="sec_free")],
            ]),
            disable_web_page_preview=True
        )

    elif data == "free_calc":
        await q.edit_message_text(
            "🔢 <b>Kalkulyatorlar</b>\n\n"
            "Kerakli kalkulyatorni tanlang:",
            parse_mode="HTML",
            reply_markup=calculator_menu()
        )

    elif data == "free_calc_back":
        await q.edit_message_text(
            "🔢 <b>Kalkulyatorlar</b>\n\n"
            "Kerakli kalkulyatorni tanlang:",
            parse_mode="HTML",
            reply_markup=calculator_menu()
        )

    elif data == "calc_rr":
        context.user_data['calc_mode'] = 'rr'
        await q.edit_message_text(
            "⚖️ <b>Risk/Reward Kalkulyatori</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>kirish_narxi stop_narxi maqsad_narxi</code>\n\n"
            "Misol: <code>100 90 130</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('free_calc')
        )

    elif data == "calc_position":
        context.user_data['calc_mode'] = 'position'
        await q.edit_message_text(
            "📏 <b>Pozitsiya Hajmi Kalkulyatori</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>kapital risk_foizi kirish_narxi stop_narxi</code>\n\n"
            "Misol: <code>10000 2 100 90</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('free_calc')
        )

    elif data == "calc_compound":
        context.user_data['calc_mode'] = 'compound'
        await q.edit_message_text(
            "📈 <b>Compound Foiz Kalkulyatori</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>boshlang'ich_summa oylik_foiz oylar</code>\n\n"
            "Misol: <code>1000 5 12</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('free_calc')
        )

    elif data == "calc_breakeven":
        context.user_data['calc_mode'] = 'breakeven'
        await q.edit_message_text(
            "🎯 <b>Break-Even Kalkulyatori</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>sotib_olish_narxi komissiya_foizi</code>\n\n"
            "Misol: <code>100 0.1</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('free_calc')
        )

    elif data == "free_glossary":
        # Glossariy olib tashlandi — IPO ga yo'naltirish
        await q.edit_message_text(
            "📅 <b>IPO Tracker</b>\n\nYuklash...",
            parse_mode="HTML"
        )
        await q.edit_message_text(
            await get_ipo_data(context),
            parse_mode="HTML",
            reply_markup=back_menu(),
            disable_web_page_preview=True
        )

    elif data == "free_ipo":
        await q.edit_message_text("⏳ IPO ma'lumotlari olinmoqda...", parse_mode="HTML")
        await q.edit_message_text(
            await get_ipo_data(context),
            parse_mode="HTML",
            reply_markup=section_back_menu('sec_free'),
            disable_web_page_preview=True
        )

    elif data == "free_lesson":
        lesson = get_daily_lesson()
        await q.edit_message_text(
            lesson,
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    elif data == "free_calendar":
        await q.edit_message_text("⏳ Ekonomik kalendar olinmoqda...", parse_mode="HTML")
        try:
            import feedparser
            cal_txt = "📅 <b>Ekonomik Kalendar</b>\n"
            cal_txt += "━━━━━━━━━━━━━━━━━━━━\n\n"

            # Investing.com RSS
            try:
                feed = feedparser.parse("https://www.investing.com/rss/news_25.rss")
                count = 0
                for entry in feed.entries[:5]:
                    title = (entry.get('title') or '')[:65]
                    link  = entry.get('link') or ''
                    if title and link:
                        cal_txt += f"• <a href='{link}'>{title}</a>\n\n"
                        count += 1
                if count == 0:
                    raise Exception("No entries")
            except:
                cal_txt += (
                    "📌 <b>Muhim voqealar:</b>\n\n"
                    "• Fed yig'ilishi — har 6 haftada\n"
                    "• NFP — har oy 1-juma\n"
                    "• CPI (Inflyatsiya) — har oy o'rtasida\n"
                    "• GDP — har chorak\n"
                    "• PPI — har oy\n"
                    "• Retail Sales — har oy\n\n"
                )

            cal_txt += (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📎 <a href='https://www.investing.com/economic-calendar/'>To'liq kalendar</a>"
            )
        except Exception as e:
            print(f"[ERROR] Calendar: {e}")
            cal_txt = (
                "📅 <b>Ekonomik Kalendar</b>\n\n"
                "📌 <b>Muhim voqealar:</b>\n\n"
                "• Fed yig'ilishi — har 6 haftada\n"
                "• NFP — har oy 1-juma\n"
                "• CPI — har oy o'rtasida\n"
                "• GDP — har chorak\n\n"
                "📎 <a href='https://www.investing.com/economic-calendar/'>To'liq kalendar</a>"
            )

        await q.edit_message_text(
            cal_txt,
            parse_mode="HTML",
            reply_markup=back_menu(),
            disable_web_page_preview=True
        )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── MENING OBUNALARIM ──
    elif data == "my_subs":
        access_signals = await check_channel_access(user.id, "signals")
        access_onchain = await check_channel_access(user.id, "onchain")
        access_screener = await check_screener_access(user.id)
        access_crypto_edu = await check_channel_access(user.id, "crypto_edu")
        access_premium = await check_premium_access(user.id)

        txt = "👤 <b>Mening Obunalarim</b>\n\n"

        if access_premium:
            txt += "💎 Premium paket: ✅ Faol (Doimiy)\n"
        else:
            if access_signals:
                end = access_signals.get('end_date', '')
                end_txt = "Doimiy ♾" if not end else end[:10]
                txt += f"📊 Signals: ✅ {end_txt}\n"
            else:
                txt += "📊 Signals: ❌ Yo'q\n"

            if access_onchain:
                end = access_onchain.get('end_date', '')
                end_txt = "Doimiy ♾" if not end else end[:10]
                txt += f"🔗 Onchain: ✅ {end_txt}\n"
            else:
                txt += "🔗 Onchain: ❌ Yo'q\n"

            if access_screener:
                end = access_screener.get('end_date', '')
                end_txt = "Doimiy ♾" if not end else end[:10]
                txt += f"🔎 Screener: ✅ {end_txt}\n"
            else:
                txt += "🔎 Screener: ❌ Yo'q\n"

            if access_crypto_edu:
                txt += "📚 Crypto Darslar: ✅ Doimiy ♾\n"
            else:
                txt += "📚 Crypto Darslar: ❌ Yo'q\n"

        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=home_menu())

    # ── MENING PORTFELIM ──
    elif data == "my_portfolio":
        # Pullik obuna tekshiruvi
        has_signals  = await check_channel_access(user.id, "signals")
        has_screener = await check_screener_access(user.id)
        has_premium  = await check_premium_access(user.id)
        if not (has_signals or has_screener or has_premium):
            await q.edit_message_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>\n\n"
                "Portfel va yangiliklar xizmati uchun "
                "istalgan obunani sotib oling.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
            return
        items = await get_portfolio(user.id)
        if not items:
            await q.edit_message_text(
                "💼 <b>Mening Portfelim</b>\n\n"
                "Portfelingiz bo'sh!\n\n"
                "Aktivlaringizni qo'shing — bot yangiliklar\n"
                "chiqsa darhol xabar beradi! 🔔\n\n"
                "Qo'shish uchun ticker yozing:\n"
                "Masalan: <code>BTC</code>, <code>AAPL</code>, <code>ETH</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Aktiv qo'shish", callback_data="portfolio_watch_new")],
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="back"), 
                     InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
        else:
            txt = "💼 <b>Mening Portfelim</b>\n\n"
            txt += "📋 <b>Kuzatilayotgan aktivlar:</b>\n"
            for item in items:
                ticker = item.get('ticker', '')
                t_type = item.get('ticker_type', '')
                icon = "₿" if t_type == 'crypto' else "📈"
                txt += f"{icon} <code>{ticker}</code>\n"
            txt += f"\n🔔 Jami: {len(items)} ta aktiv kuzatilmoqda\n"
            txt += "\n💡 Yangi muhim yangilik chiqsa — darhol xabar beraman!"

            buttons = []
            for item in items:
                buttons.append([InlineKeyboardButton(
                    f"❌ {item['ticker']} o'chirish",
                    callback_data=f"portfolio_del_{item['id']}"
                )])
            buttons.append([InlineKeyboardButton("➕ Aktiv qo'shish", callback_data="portfolio_watch_new")])
            buttons.append([InlineKeyboardButton("📰 Hozir yangiliklar", callback_data="portfolio_news")])
            buttons.append([
                InlineKeyboardButton("⬅️ Ortga", callback_data="back"),
                InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
            ])
            await q.edit_message_text(
                txt, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    elif data == "portfolio_watch_new":
        # Pullik obuna tekshiruvi
        has_signals  = await check_channel_access(user.id, "signals")
        has_screener = await check_screener_access(user.id)
        has_premium  = await check_premium_access(user.id)
        if not (has_signals or has_screener or has_premium):
            await q.edit_message_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>\n\n"
                "Portfelga aktiv qo'shish va yangiliklar olish uchun "
                "istalgan obunani sotib oling.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
            return
        context.user_data['portfolio_watch'] = True
        await q.edit_message_text(
            "💼 <b>Aktiv qo'shish</b>\n\n"
            "Kuzatmoqchi bo'lgan ticker yozing:\n\n"
            "• Crypto: <code>BTC</code>, <code>ETH</code>, <code>SOL</code>\n"
            "• Aksiya: <code>AAPL</code>, <code>TSLA</code>, <code>NVDA</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('my_portfolio')
        )

    elif data == "portfolio_watch_done":
        await q.edit_message_text(
            "🎉 <b>Rahmat!</b>\n\n"
            "Aktivingiz qo'shildi. Portfelingizdagi aktivlar doim kuzatib boriladi.\n\n"
            "🔔 Agar biron bir yangilik chiqsa darhol sizga xabar beramiz!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Bosh menyuga qaytish", callback_data="back")],
            ])
        )

    elif data == "portfolio_news":
        await q.edit_message_text("⏳ Portfelingizdagi aktivlar bo'yicha yangiliklar olinmoqda...", parse_mode="HTML")
        items = await get_portfolio(user.id)
        if not items:
            await q.edit_message_text(
                "💼 Portfelingiz bo'sh!",
                parse_mode="HTML",
                reply_markup=section_back_menu('my_portfolio')
            )
            return

        news_txt = await asyncio.to_thread(get_portfolio_news, items)
        await q.edit_message_text(
            news_txt,
            parse_mode="HTML",
            reply_markup=section_back_menu('my_portfolio'),
            disable_web_page_preview=True
        )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── SCREENER (PULLIK) ──
    elif data.startswith("refresh_"):
        parts       = data.split("_")
        ticker_type = parts[1]
        ticker      = parts[2]

        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return

        await q.edit_message_text("⏳ Yangilanmoqda...", parse_mode="HTML")
        if ticker_type == 'stock':
            result = await asyncio.to_thread(get_stock_data, ticker, False)
        else:
            result = await asyncio.to_thread(get_crypto_data, ticker, False)

        if result:
            await q.edit_message_text(
                result, parse_mode="HTML",
                reply_markup=screener_action_menu(ticker, ticker_type),
                disable_web_page_preview=True
            )
        else:
            await q.edit_message_text("❌ Ma'lumot topilmadi.", parse_mode="HTML", reply_markup=back_menu())

    # ━━━━━━━━━━━━━━━━━━━━
    # ── OGOHLANTIRISH ──
    elif data.startswith("alert_set_"):
        parts       = data.split("_")
        ticker_type = parts[2]
        ticker      = parts[3]
        await q.edit_message_text(
            f"🔔 <b>{ticker} — Ogohlantirish</b>\n\nQanday ogohlantirish o'rnatmoqchisiz?",
            parse_mode="HTML",
            reply_markup=alert_type_menu(ticker, ticker_type)
        )

    elif data.startswith("alert_price_") or data.startswith("alert_rsi_") or data.startswith("alert_pct_"):
        parts       = data.split("_")
        alert_type  = parts[1]
        ticker_type = parts[2]
        ticker      = parts[3]
        await q.edit_message_text(
            f"📊 Chegara qaysi tomonda bo'lsin?",
            parse_mode="HTML",
            reply_markup=alert_condition_menu(alert_type, ticker, ticker_type)
        )

    elif data.startswith("alert_cond_"):
        parts       = data.split("_")
        condition   = parts[2]  # above yoki below
        alert_type  = parts[3]
        ticker_type = parts[4]
        ticker      = parts[5]
        context.user_data['alert_pending'] = {
            'ticker': ticker,
            'ticker_type': ticker_type,
            'alert_type': alert_type,
            'condition': condition,
        }
        type_labels = {'price': 'narx', 'rsi': 'RSI', 'pct': 'foiz o\'zgarish'}
        cond_labels = {'above': 'yuqori', 'below': 'past'}
        await q.edit_message_text(
            f"🔔 <b>{ticker}</b> — {type_labels.get(alert_type, alert_type)} "
            f"{cond_labels.get(condition, condition)} bo'lsa\n\n"
            f"Chegara qiymatini yozing:\n"
            f"Masalan: <code>{'150' if alert_type == 'price' else '30'}</code>",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    elif data.startswith("alert_del_"):
        alert_id = int(data.split("_")[2])
        await delete_alert(alert_id, user.id)
        alerts = await get_user_alerts(user.id)
        if alerts:
            await q.edit_message_text(
                "🔔 <b>Ogohlantirishlar</b>",
                parse_mode="HTML",
                reply_markup=my_alerts_menu(alerts)
            )
        else:
            await q.edit_message_text(
                "✅ O'chirildi!\n\n🔔 Ogohlantirishlar yo'q.",
                parse_mode="HTML",
                reply_markup=home_menu()
            )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── PORTFEL ──
    elif data.startswith("portfolio_add_"):
        parts       = data.split("_")
        ticker_type = parts[2]
        ticker      = parts[3]
        context.user_data['portfolio_pending'] = {
            'ticker': ticker,
            'ticker_type': ticker_type,
        }
        await q.edit_message_text(
            f"📌 <b>{ticker}</b> portfelga qo'shish\n\n"
            f"Quyidagi formatda yozing:\n"
            f"<code>miqdor sotib_olish_narxi</code>\n\n"
            f"Misol: <code>10 150.50</code>",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    elif data == "portfolio_add_new":
        context.user_data['portfolio_new'] = True
        await q.edit_message_text(
            "📌 <b>Portfelga qo'shish</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>TICKER miqdor sotib_olish_narxi tur</code>\n\n"
            "Misol (aksiya): <code>AAPL 10 150.50 stock</code>\n"
            "Misol (crypto): <code>BTC 0.5 45000 crypto</code>",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    elif data.startswith("portfolio_del_"):
        item_id = int(data.split("_")[2])
        await delete_portfolio_item(item_id, user.id)
        items = await get_portfolio(user.id)
        if items:
            await q.edit_message_text(
                "✅ O'chirildi!\n\n💼 <b>Portfeling:</b>",
                parse_mode="HTML",
                reply_markup=portfolio_menu(items)
            )
        else:
            await q.edit_message_text(
                "✅ O'chirildi!\n\n💼 Portfeling bo'sh.",
                parse_mode="HTML",
                reply_markup=home_menu()
            )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── WATCHLIST ──
    elif data.startswith("watchlist_add_"):
        parts       = data.split("_")
        ticker_type = parts[2]
        ticker      = parts[3]
        await add_watchlist(user.id, ticker, ticker_type)
        await q.answer(f"✅ {ticker} watchlistga qo'shildi!", show_alert=True)

    # ━━━━━━━━━━━━━━━━━━━━
    # ── REFERRAL ──
    elif data == "referral_menu":
        await q.edit_message_text(
            "👥 <b>Referral Tizimi</b>",
            parse_mode="HTML",
            reply_markup=referral_menu()
        )

    elif data == "ref_stats":
        ref_code = f"ref_{user.id}"
        stats    = await get_referral_stats(user.id)
        total    = stats.get('total', 0) or 0
        earned   = stats.get('total_reward', 0) or 0
        paid     = stats.get('paid_reward', 0) or 0
        pending  = earned - paid

        txt = (
            f"👥 <b>Referral Statistikasi</b>\n\n"
            f"🔗 Sizning havolangiz:\n"
            f"<code>https://t.me/{(await get_bot_username(context))}?start={ref_code}</code>\n\n"
            f"📊 Jami taklif qilganlar: {total} ta\n"
            f"💰 Jami daromad: ${earned:.0f}\n"
            f"✅ To'langan: ${paid:.0f}\n"
            f"⏳ Kutilayotgan: ${pending:.0f}\n\n"
            f"💡 Har bir obunachidan {REFERRAL_PERCENT}% olasiz!"
        )
        await q.edit_message_text(
            txt, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Ortga", callback_data="referral_menu")]
            ])
        )

    elif data == "ref_affiliate":
        aff = await get_affiliate(user.id)
        if aff:
            status = aff.get('status', 'pending')
            if status == 'approved':
                aff_code = aff.get('affiliate_code', '')
                txt = (
                    f"🤝 <b>Affiliate Hisobingiz</b>\n\n"
                    f"🔗 Sizning havolangiz:\n"
                    f"<code>https://t.me/{(await get_bot_username(context))}?start=aff_{aff_code}</code>\n\n"
                    f"📊 Jami obunachlar: {aff.get('total_referrals', 0)}\n"
                    f"💰 Jami daromad: ${aff.get('total_earned', 0):.0f}\n"
                    f"⏳ Kutilayotgan: ${aff.get('pending_amount', 0):.0f}\n\n"
                    f"💡 Pul olish uchun adminga murojaat qiling:\n"
                    f"@{ADMIN_USERNAME}"
                )
            else:
                txt = (
                    f"🤝 <b>Affiliate So'rovingiz</b>\n\n"
                    f"⏳ Admin tasdiqlashi kutilmoqda.\n\n"
                    f"Savollar uchun: @{ADMIN_USERNAME}"
                )
            await q.edit_message_text(
                txt, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="referral_menu")]
                ])
            )
        else:
            aff_code = generate_code(10)
            context.user_data['aff_apply'] = True
            context.user_data['aff_code']  = aff_code
            await q.edit_message_text(
                "🤝 <b>Affiliate Bo'lish</b>\n\n"
                "Blogger yoki influencer bo'lsangiz,\n"
                "har bir obunachidan 20% komissiya olasiz!\n\n"
                "Kanal/blog havolangizni yozing:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="referral_menu")]
                ])
            )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── ADMIN PANEL ──
    elif data == "admin_stats":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        stats    = await get_stats()
        all_users = await get_all_bot_users()
        non_subs  = await get_non_subscribers()
        txt = (
            f"📊 <b>Statistika</b>\n\n"
            f"👤 Jami /start bosganlar: {len(all_users)}\n"
            f"🆓 Obuna bo'lmaganlar: {len(non_subs)}\n\n"
            f"👥 Kanal obunachlar: {stats.get('channel_subs', 0)}\n"
            f"🔍 Screener obunachlar: {stats.get('screener_subs', 0)}\n"
            f"💎 Premium obunachlar: {stats.get('premium_subs', 0)}\n"
            f"📅 Bu oy yangilar: {stats.get('new_this_month', 0)}\n"
            f"⏳ Kutilayotgan: {stats.get('pending', 0)}\n"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=admin_main_menu())

    elif data == "admin_broadcast":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        context.user_data['admin_broadcast'] = True
        await q.edit_message_text(
            "📢 <b>Barchaga Xabar</b>\n\n"
            "Yubormoqchi bo'lgan xabarni yozing:",
            parse_mode="HTML",
            reply_markup=section_back_menu('open_admin')
        )

    elif data == "admin_promo":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        context.user_data['admin_promo'] = True
        await q.edit_message_text(
            "🎟 <b>Promo Kod Yaratish</b>\n\n"
            "Quyidagi formatda yozing:\n"
            "<code>KOD chegirma_foizi max_foydalanish</code>\n\n"
            "Misol: <code>QURBON50 50 1000</code>",
            parse_mode="HTML",
            reply_markup=section_back_menu('open_admin')
        )

    elif data == "admin_broadcast_nonsub":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        nonsubs = await get_non_subscribers()
        context.user_data['admin_broadcast_nonsub'] = True
        await q.edit_message_text(
            f"📣 <b>Obuna Bo'lmaganlarga Xabar</b>\n\n"
            f"Hozirda obuna bo'lmagan: <b>{len(nonsubs)} ta</b> foydalanuvchi\n\n"
            f"Yubormoqchi bo'lgan xabarni yozing:",
            parse_mode="HTML",
            reply_markup=section_back_menu('open_admin')
        )

    elif data == "admin_promo_list":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        promos = await get_all_promos()
        if not promos:
            await q.edit_message_text(
                "🎟 Hozircha promo kod yo'q.",
                parse_mode="HTML",
                reply_markup=admin_main_menu()
            )
            return
        txt = "🎟 <b>Promo Kodlar:</b>\n\n"
        buttons = []
        for p in promos:
            txt += (
                f"• <code>{p['code']}</code> — {p['discount_pct']}% "
                f"({p['used_count']}/{p['max_uses']})\n"
            )
            buttons.append([InlineKeyboardButton(
                f"❌ {p['code']} o'chirish",
                callback_data=f"admin_promo_del_{p['code']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Ortga", callback_data="admin_stats")])
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("admin_promo_del_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        code = data.replace("admin_promo_del_", "")
        await delete_promo_code(code)
        await q.answer(f"✅ {code} o'chirildi!", show_alert=True)
        await q.edit_message_text(
            "✅ Promo kod o'chirildi!",
            parse_mode="HTML",
            reply_markup=admin_main_menu()
        )

    elif data == "admin_affiliates":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        affiliates = await get_all_affiliates()
        if affiliates:
            txt = "🤝 <b>Affiliate Ro'yxati</b>\n\n"
            for aff in affiliates:
                txt += (
                    f"👤 {aff.get('full_name', '')} (@{aff.get('username', '')})\n"
                    f"   Obunachlar: {aff.get('total_referrals', 0)} | "
                    f"Kutilayotgan: ${aff.get('pending_amount', 0):.0f}\n\n"
                )
        else:
            txt = "🤝 Hozircha affiliate yo'q."
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=admin_main_menu())

    # ── Affiliate tasdiqlash/rad etish ──
    elif data.startswith("aff_approve_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        target_id = int(data.split("_")[2])
        await approve_affiliate(target_id)
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    "✅ <b>Affiliate so'rovingiz tasdiqlandi!</b>\n\n"
                    "Endi havolangizni ulashishingiz mumkin.\n"
                    "Botga /start yozing va Referral bo'limini oching."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except: pass
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text("✅ Affiliate tasdiqlandi!")

    elif data.startswith("aff_reject_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        target_id = int(data.split("_")[2])
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="❌ <b>Affiliate so'rovingiz rad etildi.</b>",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except: pass
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text("❌ Affiliate rad etildi.")

    elif data == "admin_all_users":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        all_users = await get_all_bot_users()
        non_subs  = await get_non_subscribers()
        non_sub_ids = {u['user_id'] for u in non_subs}

        txt = f"👤 <b>Barcha foydalanuvchilar ({len(all_users)} ta)</b>\n\n"
        for u in all_users[:30]:
            uid    = u.get('user_id', '')
            uname  = f"@{u.get('username')}" if u.get('username') else "—"
            fname  = u.get('full_name', '') or ''
            status = "🆓" if uid in non_sub_ids else "✅"
            txt   += f"{status} {fname} {uname}\n"

        if len(all_users) > 30:
            txt += f"\n... va yana {len(all_users) - 30} ta"

        txt += f"\n\n✅ Obunachi | 🆓 Obuna bo'lmagan"

        await q.edit_message_text(
            txt, parse_mode="HTML",
            reply_markup=section_back_menu('admin_stats')
        )

    elif data == "admin_users":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        users = await get_all_users()
        txt = f"👥 <b>Obunachlar ({len(users)} ta)</b>\n\n"
        for u in users[:20]:
            uname = f"@{u.get('username', '')}" if u.get('username') else "—"
            created = u.get('created_at', '')[:16] if u.get('created_at') else "—"
            has_sub = "✅" if await check_channel_access(u.get('user_id'), "signals") or \
                              await check_screener_access(u.get('user_id')) or \
                              await check_premium_access(u.get('user_id')) else "🆓"
            txt += f"{has_sub} {u.get('full_name', '')} {uname}\n"
            txt += f"   🆔 {u.get('user_id', '—')} | 📅 {created}\n"
        if len(users) > 20:
            txt += f"\n... va yana {len(users) - 20} ta"
        txt += f"\n\n✅ Obunachi | 🆓 Obuna bo'lmagan"
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=admin_main_menu())

    elif data == "admin_cancel_sub":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        context.user_data['admin_cancel_sub'] = True
        await q.edit_message_text(
            "❌ <b>Obunani Bekor Qilish</b>\n\n"
            "Foydalanuvchi ID sini yozing:",
            parse_mode="HTML",
            reply_markup=section_back_menu('open_admin')
        )

    # ━━━━━━━━━━━━━━━━━━━━
    # ── ADMIN TASDIQLASH ──
    elif data.startswith("approve_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        parts    = data.split("_")
        sub_type = parts[1]
        sub_id   = int(parts[2])
        await handle_approve(context, q, sub_id, sub_type)

    elif data.startswith("reject_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        parts    = data.split("_")
        sub_type = parts[1]
        sub_id   = int(parts[2])
        await handle_reject(context, q, sub_id, sub_type)

    # ── ONCHAIN SIGNAL YUBORISH ──
    elif data.startswith("signal_send_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        signal_id = int(data.split("_")[2])
        # Signal matnini olish va kanalga yuborish
        txt = context.user_data.get(f'signal_{signal_id}', '')
        if txt:
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_IDS['onchain'],
                    text=txt,
                    parse_mode="HTML"
                )
                await mark_signal_sent(signal_id)
                await q.edit_message_reply_markup(reply_markup=None)
                await q.message.reply_text("✅ Signal kanalga yuborildi!")
            except TelegramError as e:
                await q.answer(f"❌ Xato: {e}", show_alert=True)

    elif data.startswith("signal_cancel_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text("❌ Signal bekor qilindi.")

    elif data.startswith("signal_edit_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        signal_id = int(data.split("_")[2])
        context.user_data['editing_signal'] = signal_id
        await q.message.reply_text(
            "✏️ <b>Signal tahrirlash</b>\n\n"
            "Yangi signal matnini yozing.\n"
            "U kanalga shu ko'rinishda yuboriladi:",
            parse_mode="HTML"
        )

    # ── ADMIN ALOQA ──
    elif data == "sec_admin":
        await q.edit_message_text(
            f"💬 <b>Admin bilan aloqa</b>\n\n"
            f"Savol va murojaatlar uchun:\n"
            f"👤 @{ADMIN_USERNAME}",
            parse_mode="HTML",
            reply_markup=back_menu()
        )

    # ── PROMO KOD ──
    elif data.startswith("promo_"):
        # Format: promo_{sub_type}_{sub_id}_{price}
        # sub_type: channel, screener, onchain_screener, premium
        # Oxirgi 2 ta qism: sub_id va price
        parts     = data.split("_")
        price     = int(float(parts[-1]))
        sub_id    = int(parts[-2])
        # sub_type qolgan qismlar
        sub_type  = "_".join(parts[1:-2])

        if sub_type == "skip":
            # promo_skip_{sub_type}_{sub_id}_{price}
            price    = int(float(parts[-1]))
            sub_id   = int(parts[-2])
            sub_type = "_".join(parts[2:-2])
            context.user_data['waiting_payment'] = True
            context.user_data['sub_id']          = sub_id
            context.user_data['sub_type']        = sub_type
            await q.edit_message_text(
                f"💳 <b>To'lov ma'lumotlari</b>\n\n"
                f"💰 Summa: <b>${price}</b>\n\n"
                f"🏦 <b>Karta raqami:</b>\n"
                f"<code>{CARD_NUMBER}</code>\n"
                f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
                f"✅ To'lovni amalga oshirgach, "
                f"<b>to'lov cheki rasmini</b> shu chatga yuboring. 👇",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
        else:
            context.user_data['promo_pending'] = {
                'sub_type': sub_type,
                'sub_id':   sub_id,
                'price':    price,
            }
            await q.edit_message_text(
                "🎟 <b>Promo Kod</b>\n\n"
                "Promo kodingizni yozing:\n"
                "Masalan: <code>QURBON50</code>",
                parse_mode="HTML",
                reply_markup=back_menu()
            )


# ===================== TASDIQLASH/RAD ETISH =====================

async def handle_approve(context, q, sub_id, sub_type):
    """Obunani tasdiqlash"""
    try:
        if sub_type == "channel":
            sub = await get_subscription(sub_id)
            if not sub:
                await q.answer("Obuna topilmadi!", show_alert=True)
                return
            if sub['status'] != 'pending':
                await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
                await q.edit_message_reply_markup(reply_markup=None)
                return

            duration       = sub['duration_months']
            section        = sub['section']
            section_name   = SECTION_NAMES.get(section, section)
            dur_label      = duration_label(duration)
            channel_id     = CHANNEL_IDS.get(section)

            await approve_subscription(sub_id, duration)

            if channel_id:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id, member_limit=1
                )
                await context.bot.send_message(
                    chat_id=sub['user_id'],
                    text=(
                        f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                        f"📦 <b>Bo'lim:</b> {section_name}\n"
                        f"⏱ <b>Muddat:</b> {dur_label}\n\n"
                        f"🔗 <b>Kanal havolasi:</b>\n{link_obj.invite_link}\n\n"
                        f"⚠️ Havola <b>bir martalik</b> — faqat siz uchun."
                    ),
                    parse_mode="HTML",
                    reply_markup=home_menu()
                )
            else:
                await context.bot.send_message(
                    chat_id=sub['user_id'],
                    text=f"✅ <b>{section_name}</b> obunangiz tasdiqlandi!",
                    parse_mode="HTML",
                    reply_markup=home_menu()
                )

            await q.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"✅ <b>#{sub_id} — TASDIQLANDI.</b>",
                parse_mode="HTML"
            )

            # Referral mukofoti
            await process_referral_reward(sub['user_id'], section_name, context)

        elif sub_type == "screener":
            sub = await get_screener_sub(sub_id)
            if not sub:
                await q.answer("Obuna topilmadi!", show_alert=True)
                return
            if sub['status'] != 'pending':
                await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
                await q.edit_message_reply_markup(reply_markup=None)
                return

            duration  = sub['duration_months']
            dur_label = duration_label(duration)

            await approve_screener_sub(sub_id, duration)

            # Onchain kanal havolasi ham yuboriladi
            channel_id = CHANNEL_IDS.get('onchain')
            if channel_id:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel_id, member_limit=1
                )
                await context.bot.send_message(
                    chat_id=sub['user_id'],
                    text=(
                        f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                        f"📦 <b>Bo'lim:</b> {SECTION_NAMES['screener']}\n"
                        f"⏱ <b>Muddat:</b> {dur_label}\n\n"
                        f"🔗 <b>Onchain kanal havolasi:</b>\n{link_obj.invite_link}\n\n"
                        f"⚠️ Havola <b>bir martalik</b> — faqat siz uchun.\n\n"
                        f"🔎 Screener ishlatish uchun /start bosing va "
                        f"'Onchain + Screener' bo'limini tanlang."
                    ),
                    parse_mode="HTML",
                    reply_markup=home_menu()
                )
            else:
                await context.bot.send_message(
                    chat_id=sub['user_id'],
                    text=(
                        f"✅ <b>Screener obunangiz tasdiqlandi!</b>\n\n"
                        f"🔎 Screener ishlatish uchun /start bosing."
                    ),
                    parse_mode="HTML",
                    reply_markup=home_menu()
                )

            await q.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"✅ <b>Screener #{sub_id} — TASDIQLANDI.</b>",
                parse_mode="HTML"
            )

        elif sub_type == "premium":
            sub = await get_premium_sub(sub_id)
            if not sub:
                await q.answer("Obuna topilmadi!", show_alert=True)
                return
            if sub['status'] != 'pending':
                await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
                await q.edit_message_reply_markup(reply_markup=None)
                return

            await approve_premium_sub(sub_id)

            # Barcha kanallarga havola
            links_txt = ""
            for sec, ch_id in CHANNEL_IDS.items():
                try:
                    link_obj  = await context.bot.create_chat_invite_link(
                        chat_id=ch_id, member_limit=1
                    )
                    sec_name  = SECTION_NAMES.get(sec, sec)
                    links_txt += f"• {sec_name}:\n{link_obj.invite_link}\n\n"
                except:
                    pass

            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"✅ <b>Premium Paket tasdiqlandi!</b>\n\n"
                    f"💎 Barcha bo'limlarga kirish huquqi berildi!\n\n"
                    f"🔗 <b>Kanal havolalari:</b>\n{links_txt}"
                    f"⚠️ Havolalar bir martalik!\n\n"
                    f"🔎 Screener uchun /start bosing."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )

            await q.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(
                chat_id=q.message.chat_id,
                text=f"✅ <b>Premium #{sub_id} — TASDIQLANDI.</b>",
                parse_mode="HTML"
            )

    except TelegramError as e:
        await q.answer(f"❌ Xato: {e}", show_alert=True)


async def handle_reject(context, q, sub_id, sub_type):
    """Obunani rad etish"""
    try:
        if sub_type == "channel":
            sub = await get_subscription(sub_id)
        elif sub_type == "screener":
            sub = await get_screener_sub(sub_id)
        elif sub_type == "premium":
            sub = await get_premium_sub(sub_id)
        else:
            return

        if not sub:
            await q.answer("Obuna topilmadi!", show_alert=True)
            return
        if sub['status'] != 'pending':
            await q.answer("Allaqachon qayta ishlangan!", show_alert=True)
            await q.edit_message_reply_markup(reply_markup=None)
            return

        if sub_type == "channel":
            await reject_subscription(sub_id)
        elif sub_type == "screener":
            await reject_screener_sub(sub_id)
        elif sub_type == "premium":
            await reject_premium_sub(sub_id)

        await context.bot.send_message(
            chat_id=sub['user_id'],
            text=(
                f"❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                f"Murojaat uchun: @{ADMIN_USERNAME}"
            ),
            parse_mode="HTML",
            reply_markup=home_menu()
        )
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=f"❌ <b>#{sub_id} — RAD ETILDI.</b>",
            parse_mode="HTML"
        )
    except TelegramError as e:
        await q.answer(f"❌ Xato: {e}", show_alert=True)


async def process_referral_reward(user_id, section_name, context):
    """Referral mukofotini hisoblash"""
    try:
        import sqlite3
        conn = sqlite3.connect("azia_quant.db", timeout=30)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM referrals WHERE referred_id=? AND reward_amount=0", (user_id,))
        ref = c.fetchone()
        conn.close()

        if ref:
            ref = dict(ref)
            # To'langan summaga qarab hisoblash
            # Bu yerda to'liq hisob kerak bo'ladi
            await update_referral_reward(ref['referrer_id'], user_id, 10)
    except:
        pass


# ===================== MATN HANDLERLARI =====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarini qabul qilish"""
    user    = update.effective_user
    text    = (update.message.text or update.message.caption or "").strip()
    udata   = context.user_data

    # ── Reply Keyboard tugmalari ──
    reply_sections = {
        "👤 Mening Obunalarim":  "my_subs",
        "💼 Mening Portfelim":   "my_portfolio",
        "👥 Referral":           "referral_menu",
        "💬 Admin bilan aloqa":  "sec_admin",
        "👨‍💼 Admin Panel":        "open_admin",
    }
    if text in reply_sections:
        udata['_pending_section'] = reply_sections[text]
        context.user_data.update(udata)
        await show_section(update, context, reply_sections[text])
        return

    # ── AI Yordamchi ──
    if udata.get('ai_mode'):
        history = udata.get('ai_history', [])

        # Typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # AI ga yuborish
        response = await asyncio.to_thread(ask_ai, text, history)

        # Tarixga qo'shish (OpenRouter formati)
        history.append({"role": "user",      "content": text})
        history.append({"role": "assistant", "content": response})

        # Oxirgi 10 ta xabar saqlash
        if len(history) > 10:
            history = history[-10:]

        # ai_mode saqlanib qolsin!
        udata['ai_mode']    = True
        udata['ai_history'] = history

        await update.message.reply_text(
            f"🤖 {response}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Suhbatni tozalash", callback_data="ai_clear")],
                [InlineKeyboardButton("🚪 Chiqish",           callback_data="ai_exit")],
            ])
        )
        return

    # ── Portfolio Watch (yangi aktiv qo'shish) ──
    if udata.get('portfolio_watch'):
        udata.pop('portfolio_watch', None)
        ticker = text.upper().strip()

        # Crypto yoki aksiya aniqlash
        crypto_list = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE',
                       'AVAX', 'DOT', 'MATIC', 'LINK', 'UNI', 'ATOM', 'LTC']
        t_type = 'crypto' if ticker in crypto_list else 'stock'

        # Portfelga qo'shish (soni va narx 0 — faqat kuzatuv)
        await add_portfolio(user.id, ticker, t_type, 0, 0)

        await update.message.reply_text(
            f"✅ <b>{ticker}</b> qabul qilindi!\n\n"
            f"Yana aktiv qo'shmoqchimisiz?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Ha", callback_data="portfolio_watch_new"),
                    InlineKeyboardButton("❌ Yo'q", callback_data="portfolio_watch_done"),
                ],
            ])
        )
        return

    # ── Promo kod tekshirish ──
    if udata.get('promo_pending'):
        info     = udata.pop('promo_pending')
        promo    = await check_promo_code(text.upper())
        if not promo:
            await update.message.reply_text(
                "❌ <b>Promo kod noto'g'ri yoki muddati tugagan!</b>\n\n"
                "Qaytadan urinib ko'ring yoki to'lovni davom ettiring:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Promodsiz to'lash", callback_data=f"promo_skip_{info['sub_type']}_{info['sub_id']}_{info['price']}")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
            udata['promo_pending'] = info  # qayta saqlash
            return

        await use_promo_code(text.upper())
        discount    = promo['discount_pct']
        discount    = min(discount, 100)
        final_price = max(0, info['price'] * (1 - discount / 100))

        section_map = {
            'channel':          SECTION_NAMES.get('signals', 'Signals'),
            'screener':         SECTION_NAMES.get('screener', 'Screener'),
            'onchain_screener': SECTION_NAMES.get('screener', 'Onchain + Screener'),
            'premium':          SECTION_NAMES.get('premium', 'Premium'),
        }
        section_name = section_map.get(info['sub_type'], 'Obuna')

        # waiting_payment o'rnatish — chek kelganda admin ga ketsin
        udata['waiting_payment'] = True
        udata['sub_id']          = info['sub_id']
        udata['sub_type']        = info['sub_type']
        if info['sub_type'] == 'onchain_screener':
            udata['scr_sub_id'] = info.get('scr_sub_id', info['sub_id'])
        if info['sub_type'] == 'premium':
            udata['premium_sub_id'] = info['sub_id']

        await update.message.reply_text(
            f"✅ <b>Promo kod qabul qilindi!</b>\n\n"
            f"🎟 Kod: <code>{text.upper()}</code>\n"
            f"🎉 Chegirma: {discount}%\n"
            f"💰 Asl narx: ${info['price']}\n"
            f"💰 <b>Chegirmali narx: ${final_price:.0f}</b>\n\n"
            f"📦 Bo'lim: {section_name}\n\n"
            f"🏦 <b>Karta raqami:</b>\n"
            f"<code>{CARD_NUMBER}</code>\n"
            f"👤 <b>Karta egasi:</b> {CARD_OWNER}\n\n"
            f"✅ To'lovni amalga oshirgach, "
            f"<b>to'lov cheki rasmini</b> shu chatga yuboring. 👇",
            parse_mode="HTML",
            reply_markup=back_menu()
        )
        return

    # ── Signal tahrirlash (admin) ──
    if udata.get('editing_signal') and await is_admin(user):
        signal_id = udata.pop('editing_signal')
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_IDS['onchain'],
                text=text,
                parse_mode="HTML"
            )
            await mark_signal_sent(signal_id)
            await update.message.reply_text("✅ Tahrirlangan signal kanalga yuborildi!")
        except TelegramError as e:
            await update.message.reply_text(f"❌ Xato: {e}")
        return

    # ── Admin broadcast ──
    if udata.get('admin_broadcast') and await is_admin(user):
        udata.pop('admin_broadcast', None)
        users   = await get_all_users()
        success = 0
        failed  = 0
        await update.message.reply_text(f"📢 Yuborilmoqda... ({len(users)} ta obunachi)")
        for u in users:
            try:
                if update.message.photo:
                    photo = update.message.photo[-1].file_id
                    await context.bot.send_photo(
                        chat_id=u['user_id'],
                        photo=photo,
                        caption=text,
                        parse_mode="HTML"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=u['user_id'],
                        text=text,
                        parse_mode="HTML"
                    )
                success += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1
        await update.message.reply_text(
            f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta",
            reply_markup=admin_main_menu()
        )
        return

    # ── Obuna bo'lmaganlarga xabar ──
    if udata.get('admin_broadcast_nonsub') and await is_admin(user):
        udata.pop('admin_broadcast_nonsub', None)
        nonsubs = await get_non_subscribers()
        success = 0
        failed  = 0
        await update.message.reply_text(f"📣 Yuborilmoqda... ({len(nonsubs)} ta foydalanuvchi)")
        for u in nonsubs:
            try:
                if update.message.photo:
                    photo = update.message.photo[-1].file_id
                    await context.bot.send_photo(
                        chat_id=u['user_id'],
                        photo=photo,
                        caption=text,
                        parse_mode="HTML"
                    )
                else:
                    await context.bot.send_message(
                        chat_id=u['user_id'],
                        text=text,
                        parse_mode="HTML"
                    )
                success += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1
        await update.message.reply_text(
            f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta",
            reply_markup=admin_main_menu()
        )
        return

    # ── Admin promo kod ──
    if udata.get('admin_promo') and await is_admin(user):
        udata.pop('admin_promo', None)
        try:
            parts      = text.split()
            code       = parts[0].upper()
            discount   = int(parts[1])
            max_uses   = int(parts[2]) if len(parts) > 2 else 1
            await create_promo_code(code, discount, max_uses, None, None)
            await update.message.reply_text(
                f"✅ Promo kod yaratildi!\n\n"
                f"Kod: <code>{code}</code>\n"
                f"Chegirma: {discount}%\n"
                f"Max foydalanish: {max_uses} marta",
                parse_mode="HTML",
                reply_markup=admin_main_menu()
            )
        except:
            await update.message.reply_text("❌ Format noto'g'ri.", reply_markup=admin_main_menu())
        return

    # ── Admin obunani bekor qilish ──
    if udata.get('admin_cancel_sub') and await is_admin(user):
        udata.pop('admin_cancel_sub', None)
        try:
            target_user_id = int(text)

            # Barcha obuna turlarini bekor qilish
            await cancel_subscription(target_user_id, "signals")
            await cancel_subscription(target_user_id, "onchain")
            await cancel_subscription(target_user_id, "crypto_edu")
            await cancel_subscription(target_user_id, "stock_edu")
            await cancel_screener_subscription(target_user_id)
            await cancel_premium_subscription(target_user_id)

            # Kanallardan chiqarish
            for section, channel_id in CHANNEL_IDS.items():
                try:
                    await context.bot.ban_chat_member(channel_id, target_user_id)
                    await context.bot.unban_chat_member(channel_id, target_user_id)
                except:
                    pass

            # Foydalanuvchiga xabar
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "❌ <b>Obunangiz bekor qilindi.</b>\n\n"
                        "Savollar uchun: @" + ADMIN_USERNAME
                    ),
                    parse_mode="HTML"
                )
            except:
                pass

            await update.message.reply_text(
                f"✅ Foydalanuvchi <code>{target_user_id}</code> barcha obunalari bekor qilindi.",
                parse_mode="HTML",
                reply_markup=admin_main_menu()
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Xato: {e}",
                reply_markup=admin_main_menu()
            )
        return

    # ── Affiliate ariza ──
    if udata.get('aff_apply'):
        udata.pop('aff_apply', None)
        aff_code = udata.pop('aff_code', generate_code(10))
        await save_affiliate(user.id, user.username, user.full_name, aff_code)

        # Adminga xabar
        admin_ids = await get_admin_ids()
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🤝 <b>Yangi Affiliate So'rovi</b>\n\n"
                        f"👤 {user.full_name} (@{user.username or 'yo\'q'})\n"
                        f"🆔 ID: <code>{user.id}</code>\n"
                        f"📝 Kanal: {text}\n"
                        f"🔑 Kod: <code>{aff_code}</code>"
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"aff_approve_{user.id}"),
                        InlineKeyboardButton("❌ Rad etish",  callback_data=f"aff_reject_{user.id}"),
                    ]])
                )
            except:
                pass

        await update.message.reply_text(
            "✅ So'rovingiz yuborildi!\n\nAdmin tasdiqlashini kuting.",
            reply_markup=home_menu()
        )
        return

    # ── Ogohlantirish qiymati ──
    if udata.get('alert_pending'):
        alert_info = udata.pop('alert_pending')
        try:
            value = float(text)
            await save_alert(
                user.id,
                alert_info['ticker'],
                alert_info['ticker_type'],
                alert_info['alert_type'],
                alert_info['condition'],
                value
            )
            cond_txt = "yuqori" if alert_info['condition'] == 'above' else "past"
            type_txt = {'price': 'Narx', 'rsi': 'RSI', 'pct': 'Foiz'}
            await update.message.reply_text(
                f"✅ <b>Ogohlantirish o'rnatildi!</b>\n\n"
                f"📊 {alert_info['ticker']} — {type_txt.get(alert_info['alert_type'], '')}\n"
                f"📌 Chegara: {value} dan {cond_txt}",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except ValueError:
            await update.message.reply_text("❌ Raqam kiriting.", reply_markup=back_menu())
        return

    # ── Portfel qo'shish (screenerdan) ──
    if udata.get('portfolio_pending'):
        info = udata.pop('portfolio_pending')
        try:
            parts    = text.split()
            quantity = float(parts[0])
            price_v  = float(parts[1])
            await add_portfolio(user.id, info['ticker'], info['ticker_type'], quantity, price_v)
            await update.message.reply_text(
                f"✅ <b>{info['ticker']}</b> portfelga qo'shildi!\n\n"
                f"📦 Miqdor: {quantity}\n"
                f"💰 Sotib olish narxi: ${price_v}",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except:
            await update.message.reply_text("❌ Format noto'g'ri.", reply_markup=back_menu())
        return

    # ── Portfel yangi qo'shish ──
    if udata.get('portfolio_new'):
        udata.pop('portfolio_new', None)
        try:
            parts    = text.split()
            ticker   = parts[0].upper()
            quantity = float(parts[1])
            price_v  = float(parts[2])
            t_type   = parts[3].lower() if len(parts) > 3 else 'stock'
            await add_portfolio(user.id, ticker, t_type, quantity, price_v)
            await update.message.reply_text(
                f"✅ <b>{ticker}</b> portfelga qo'shildi!",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except:
            await update.message.reply_text(
                "❌ Format noto'g'ri.\nMisol: <code>AAPL 10 150.50 stock</code>",
                parse_mode="HTML",
                reply_markup=back_menu()
            )
        return

    # ── Kalkulyatorlar ──
    if udata.get('calc_mode'):
        calc_mode = udata.pop('calc_mode')
        result    = calculate(calc_mode, text)
        await update.message.reply_text(result, parse_mode="HTML", reply_markup=calculator_menu())
        return

    # ── Glossariy ──
    if udata.get('glossary_mode'):
        result = get_glossary(text)
        await update.message.reply_text(result, parse_mode="HTML", reply_markup=back_menu())
        return

    # ── SCREENER (BEPUL) ──
    if udata.get('screener_mode') == 'free':
        udata.pop('screener_mode', None)
        can_use = await check_free_usage(user.id)
        if not can_use:
            await update.message.reply_text(
                f"❌ <b>Kunlik limit tugadi!</b>\n\n"
                f"Kuniga {FREE_DAILY_LIMIT} ta bepul screener.\n\n"
                f"💎 Cheksiz foydalanish uchun obuna oling:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Onchain + Screener", callback_data="sec_onchain")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
            return

        ticker = text.upper()
        await update.message.reply_text(f"⏳ {ticker} tahlil qilinmoqda...")
        await increment_free_usage(user.id)

        # Aksiya yoki crypto aniqlash
        if len(ticker) <= 5 and ticker.isalpha():
            # Avval aksiya sifatida tekshir
            result = await asyncio.to_thread(get_stock_data, ticker, True)
            if not result:
                result = await asyncio.to_thread(get_crypto_data, ticker, True)
        else:
            result = await asyncio.to_thread(get_crypto_data, ticker, True)

        if result:
            await save_search(user.id, ticker, 'unknown')
            await update.message.reply_text(
                result,
                parse_mode="HTML",
                reply_markup=free_screener_result_menu(ticker, 'unknown'),
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                f"❌ <b>{ticker}</b> topilmadi.\n\nTicker to'g'ri ekanligini tekshiring.",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        return

    # ── SCREENER (PULLIK) ──
    if udata.get('screener_mode') in ('stock', 'crypto'):
        mode = udata.pop('screener_mode')  # O'chiriladi — chat to'lmasin

        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            udata.clear()
            await update.message.reply_text(
                "❌ Screener uchun obuna kerak!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Onchain + Screener", callback_data="sec_onchain")],
                    [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                ])
            )
            return

        ticker = text.upper()
        msg = await update.message.reply_text(
            f"⏳ <b>{ticker}</b> tahlil qilinmoqda...", parse_mode="HTML"
        )

        if mode == 'stock':
            result = await asyncio.to_thread(get_stock_data, ticker, False)
            t_type = 'stock'
            again_cb = "use_stock_screener"
        else:
            result = await asyncio.to_thread(get_crypto_data, ticker, False)
            t_type = 'crypto'
            again_cb = "use_crypto_screener"

        if result:
            await save_search(user.id, ticker, t_type)
            await msg.delete()
            await update.message.reply_text(
                result,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🔔 Ogohlantirish", callback_data=f"alert_set_{t_type}_{ticker}"),
                        InlineKeyboardButton("📌 Portfelga",      callback_data=f"portfolio_add_{t_type}_{ticker}"),
                    ],
                    [InlineKeyboardButton("🔄 Yana qidirish", callback_data=again_cb)],
                    [
                        InlineKeyboardButton("⬅️ Ortga",      callback_data=again_cb),
                        InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
                    ],
                ]),
                disable_web_page_preview=True
            )
        else:
            # Xato bo'lsa mode qayta tiklansin
            context.user_data['screener_mode'] = mode
            await msg.delete()
            await update.message.reply_text(
                f"❌ <b>{ticker}</b> topilmadi.\n\n"
                f"{'Ticker' if mode == 'stock' else 'Ticker yoki CoinGecko ID'}ni to'g'ri kiriting.\n"
                f"Misol: {'AAPL, TSLA, MSFT' if mode == 'stock' else 'BTC, ETH, SOL'}\n\n"
                f"💡 Boshqa ticker kiriting:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Ortga", callback_data=again_cb)],
                ])
            )
        return

    # ── Hech qanday holat yo'q — bosh menyu ko'rsat ──
    # (screener yoki AI mode bo'lmasa)
    if not udata.get('screener_mode') and not udata.get('ai_mode'):
        await update.message.reply_text(
            WELCOME_TEXT,
            parse_mode="HTML"
        )


# ── ONCHAIN ──
async def handle_onchain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    has_access = (
        await check_channel_access(user.id, "onchain") or
        await check_screener_access(user.id) or
        await check_premium_access(user.id)
    )
    if not has_access:
        await update.message.reply_text(
            "❌ Onchain tahlil uchun obuna kerak!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Onchain + Screener", callback_data="sec_onchain")],
            ])
        )
        return
    msg = await update.message.reply_text("⏳ Onchain ma'lumotlar olinmoqda...")
    report = await asyncio.to_thread(format_onchain_report)
    await msg.edit_text(report, parse_mode="HTML", disable_web_page_preview=True)


# ── SCREENER BUYRUGʻI ──
async def screener_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
    if not has_access:
        await update.message.reply_text(
            "❌ Screener uchun obuna kerak!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Onchain + Screener", callback_data="sec_onchain")],
            ])
        )
        return
    await update.message.reply_text(
        "🔎 <b>Screener</b>\n\nQaysi screenerdan foydalanmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Aksiya Screener", callback_data="use_stock_screener")],
            [InlineKeyboardButton("🔍 Crypto Screener", callback_data="use_crypto_screener")],
            [InlineKeyboardButton("🏠 Bosh menyu",      callback_data="back")],
        ])
    )


# ===================== FOTO HANDLER =====================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov cheki qabul qilish va broadcast"""
    user  = update.effective_user
    udata = context.user_data

    # ── Admin broadcast rasm bilan ──
    if udata.get('admin_broadcast') and await is_admin(user):
        udata.pop('admin_broadcast', None)
        caption = update.message.caption or ""
        users   = await get_all_users()
        success = 0
        failed  = 0
        await update.message.reply_text(f"📢 Yuborilmoqda... ({len(users)} ta obunachi)")
        photo = update.message.photo[-1].file_id
        for u in users:
            try:
                await context.bot.send_photo(
                    chat_id=u['user_id'],
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML"
                )
                success += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1
        await update.message.reply_text(
            f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta",
            reply_markup=admin_main_menu()
        )
        return

    # ── Admin broadcast_nonsub rasm bilan ──
    if udata.get('admin_broadcast_nonsub') and await is_admin(user):
        udata.pop('admin_broadcast_nonsub', None)
        caption = update.message.caption or ""
        nonsubs = await get_non_subscribers()
        success = 0
        failed  = 0
        await update.message.reply_text(f"📣 Yuborilmoqda... ({len(nonsubs)} ta foydalanuvchi)")
        photo = update.message.photo[-1].file_id
        for u in nonsubs:
            try:
                await context.bot.send_photo(
                    chat_id=u['user_id'],
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML"
                )
                success += 1
                await asyncio.sleep(0.1)
            except:
                failed += 1
        await update.message.reply_text(
            f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta",
            reply_markup=admin_main_menu()
        )
        return

    if not udata.get('waiting_payment'):
        return

    sub_type = udata.get('sub_type', 'channel')

    # Sub ID larni olish
    sub_id     = udata.get('sub_id')
    scr_sub_id = udata.get('scr_sub_id')
    prem_sub_id = udata.get('premium_sub_id')

    # Validatsiya
    if sub_type == 'channel' and not sub_id:
        return
    if sub_type == 'onchain_screener' and (not sub_id or not scr_sub_id):
        return
    if sub_type == 'premium' and not prem_sub_id:
        return

    # Admin IDlarini olish
    admin_ids = await get_admin_ids()
    if not admin_ids:
        await update.message.reply_text(
            "❌ Administrator topilmadi. Keyinroq urinib ko'ring."
        )
        return

    # Holat o'zgartirish
    udata['waiting_payment'] = False

    await update.message.reply_text(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "Admin tekshirgandan so'ng sizga havola yuboriladi.\n"
        "Odatda <b>5–30 daqiqa</b> ichida.",
        parse_mode="HTML"
    )

    # Admin ga xabar
    photo = update.message.photo[-1].file_id

    if sub_type == 'channel':
        sub  = await get_subscription(sub_id)
        if not sub:
            return
        dur  = sub['duration_months']
        sec  = sub['section']
        dur_label  = "♾ Doimiy" if dur == 0 else f"{dur} oy" if dur != 12 else "1 yil"
        sec_name   = SECTION_NAMES.get(sec, sec)
        price      = SIGNAL_PRICES.get(dur, CRYPTO_EDU_PRICE) if sec == 'signals' else CRYPTO_EDU_PRICE
        caption    = (
            f"💳 <b>To'lov So'rovi #{sub_id}</b>\n\n"
            f"👤 {sub['full_name']}\n"
            f"🔖 @{sub.get('username') or 'yo\'q'}\n"
            f"🆔 <code>{sub['user_id']}</code>\n"
            f"📦 {sec_name}\n"
            f"⏱ {dur_label}"
        )
        markup = admin_approve_menu(sub_id, 'channel')

    elif sub_type == 'onchain_screener':
        sub  = await get_subscription(sub_id)
        if not sub:
            return
        dur  = sub['duration_months']
        dur_label  = "♾ Doimiy" if dur == 0 else f"{dur} oy" if dur != 12 else "1 yil"
        price      = SCREENER_PRICES.get(dur, 100)
        caption    = (
            f"💳 <b>Onchain+Screener So'rovi</b>\n"
            f"Kanal #{sub_id} | Screener #{scr_sub_id}\n\n"
            f"👤 {sub['full_name']}\n"
            f"🔖 @{sub.get('username') or 'yo\'q'}\n"
            f"🆔 <code>{sub['user_id']}</code>\n"
            f"📦 {SECTION_NAMES['screener']}\n"
            f"⏱ {dur_label}\n"
            f"💰 ${price}"
        )
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_screener_{scr_sub_id}"),
            InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_screener_{scr_sub_id}"),
        ]])

    elif sub_type == 'premium':
        sub  = await get_premium_sub(prem_sub_id)
        if not sub:
            return
        caption = (
            f"💎 <b>Premium Paket So'rovi #{prem_sub_id}</b>\n\n"
            f"👤 {sub['full_name']}\n"
            f"🔖 @{sub.get('username') or 'yo\'q'}\n"
            f"🆔 <code>{sub['user_id']}</code>\n"
            f"📦 Premium To'liq Paket\n"
            f"⏱ Doimiy ♾\n"
            f"💰 ${PREMIUM_PRICE}"
        )
        markup = admin_approve_menu(prem_sub_id, 'premium')
    else:
        return

    # Adminga yuborish
    for admin_id in admin_ids:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        except TelegramError as e:
            print(f"[WARNING] Adminga xabar yuborishda xato ({admin_id}): {e}")


# ===================== YORDAMCHI FUNKSIYALAR =====================

def get_portfolio_news(items: list) -> str:
    """Portfolio aktivlari bo'yicha yangiliklar RSS dan olish"""
    import feedparser

    tickers = [item.get('ticker', '').upper() for item in items]
    if not tickers:
        return "💼 Portfelingiz bo'sh!"

    feeds = [
        ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("CoinTelegraph",  "https://cointelegraph.com/rss"),
        ("Reuters",        "https://feeds.reuters.com/reuters/businessNews"),
        ("Yahoo Finance",  "https://finance.yahoo.com/news/rssindex"),
        ("Seeking Alpha",  "https://seekingalpha.com/market_currents.xml"),
    ]

    found_news = []

    # Salbiy kalit so'zlar
    negative_words = [
        'crash', 'fall', 'drop', 'decline', 'down', 'loss', 'sell', 'bear',
        'hack', 'breach', 'ban', 'lawsuit', 'fraud', 'bankrupt', 'delist',
        'warning', 'risk', 'concern', 'problem', 'issue', 'fail', 'collapse',
        'tushdi', 'pasaydi', 'muammo', 'xavf', 'zarar', 'taqiq'
    ]

    # Ijobiy kalit so'zlar
    positive_words = [
        'surge', 'rise', 'gain', 'up', 'bull', 'buy', 'growth', 'profit',
        'partnership', 'launch', 'upgrade', 'approval', 'record', 'high',
        'ko\'tarildi', 'o\'sdi', 'yangi', 'yuqori', 'rekord'
    ]

    for src, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = (entry.get('title') or '').strip()
                link  = entry.get('link') or ''
                if not title:
                    continue

                title_upper = title.upper()

                # Portfolio aktivlaridan biri bor?
                matched_ticker = None
                for ticker in tickers:
                    if ticker in title_upper:
                        matched_ticker = ticker
                        break

                if not matched_ticker:
                    continue

                # Salbiy yoki ijobiy?
                title_lower = title.lower()
                is_negative = any(w in title_lower for w in negative_words)
                is_positive = any(w in title_lower for w in positive_words)

                sentiment = "⚠️" if is_negative else ("📈" if is_positive else "📰")
                alert     = "🚨 <b>SALBIY YANGILIK!</b>\n" if is_negative else ""

                found_news.append({
                    'ticker':    matched_ticker,
                    'title':     title,
                    'link':      link,
                    'sentiment': sentiment,
                    'alert':     alert,
                    'negative':  is_negative,
                })
        except:
            continue

    if not found_news:
        tickers_str = ', '.join(tickers)
        return (
            f"💼 <b>Portfel Yangiliklari</b>\n\n"
            f"📋 Kuzatilayotgan: {tickers_str}\n\n"
            f"📰 Hozircha yangilik topilmadi.\n"
            f"Bot har 30 daqiqada tekshirib turadi!"
        )

    # Salbiylarni oldin ko'rsat
    found_news.sort(key=lambda x: x['negative'], reverse=True)

    txt = f"💼 <b>Portfel Yangiliklari</b>\n\n"
    txt += f"📋 Kuzatilayotgan: {', '.join(tickers)}\n"
    txt += "━━━━━━━━━━━━━━━━━━━━\n\n"

    for news in found_news[:8]:
        txt += f"{news['alert']}"
        txt += f"{news['sentiment']} <b>{news['ticker']}</b>\n"
        txt += f"<a href='{news['link']}'>{news['title'][:70]}</a>\n\n"

    return txt


async def get_bot_username(context):
    """Bot username ni olish"""
    try:
        bot = await context.bot.get_me()
        return bot.username
    except:
        return "AziaQuantBot"


async def get_ipo_data(context=None) -> str:
    """RSS Feed orqali IPO ma'lumotlari"""
    try:
        import feedparser
        import requests as req

        txt = "🏢 <b>IPO Tracker</b>\n"
        txt += "📆 Yaqinda kutilayotgan IPOlar\n"
        txt += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # NASDAQ IPO RSS
        feeds = [
            "https://www.renaissancecapital.com/review/IPOpipeline.html",
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=IPO&region=US&lang=en-US",
        ]

        count = 0
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:6]:
                    title = (entry.get('title') or '')[:65]
                    link  = entry.get('link') or ''
                    date  = entry.get('published', '')[:16]
                    if title and link:
                        txt += f"🏢 <a href='{link}'>{title}</a>\n"
                        if date:
                            txt += f"   📅 {date}\n"
                        txt += "\n"
                        count += 1
                if count >= 4:
                    break
            except:
                continue

        if count == 0:
            txt += (
                "📌 <b>IPO haqida ma'lumot:</b>\n\n"
                "Yaqin orada rejalashtirilgan IPOlar:\n\n"
                "📎 To'liq ro'yxat:\n"
                "• <a href='https://nasdaq.com/market-activity/ipos'>NASDAQ IPO</a>\n"
                "• <a href='https://finance.yahoo.com/calendar/ipo'>Yahoo Finance IPO</a>"
            )

        return txt
    except Exception as e:
        print(f"[ERROR] IPO data: {e}")
        return (
            "🏢 <b>IPO Tracker</b>\n\n"
            "📎 To'liq ro'yxat:\n"
            "• <a href='https://nasdaq.com/market-activity/ipos'>NASDAQ IPO</a>\n"
            "• <a href='https://finance.yahoo.com/calendar/ipo'>Yahoo Finance IPO</a>"
        )


def get_daily_lesson():
    """Kunlik moliyaviy dars"""
    lessons = [
        (
            "📚 <b>Bugungi Dars: P/E Nisbati</b>\n\n"
            "P/E (Price-to-Earnings) — aksiya narxini yillik foydaga nisbatan ko'rsatadi.\n\n"
            "Misol: Narx $100, EPS $5 → P/E = 20\n\n"
            "✅ P/E pastroq = arzonroq\n"
            "⚠️ P/E yuqori = qimmat yoki tez o'sayotgan kompaniya\n\n"
            "💡 Bir xil sektordagi kompaniyalar bilan taqqoslang!"
        ),
        (
            "📚 <b>Bugungi Dars: RSI Indikatori</b>\n\n"
            "RSI (Relative Strength Index) — 0 dan 100 gacha bo'lgan ko'rsatkich.\n\n"
            "• RSI < 30 → Oversold (Sotib olish imkoniyati)\n"
            "• RSI > 70 → Overbought (Ehtiyot bo'lish kerak)\n"
            "• RSI 30-70 → Neytral zona\n\n"
            "💡 RSI faqat bitta signal, boshqa ko'rsatkichlar bilan birga ishlating!"
        ),
        (
            "📚 <b>Bugungi Dars: Diversifikatsiya</b>\n\n"
            "Diversifikatsiya — riskni kamaytirish uchun turli aktivlarga sarmoya kiritish.\n\n"
            "✅ Bir kompaniyaga 100% sarmoya kiritma!\n"
            "✅ Turli sektorlarga taqsimla\n"
            "✅ Crypto + Aksiya + Boshqa aktivlar\n\n"
            "💡 'Tuxumlarni bitta savatchaga qo'yma!'"
        ),
        (
            "📚 <b>Bugungi Dars: Stop Loss</b>\n\n"
            "Stop Loss — zararni cheklash uchun oldindan belgilangan chiqish narxi.\n\n"
            "Misol: $100 ga sotib oldingiz → Stop Loss $90 (10% risk)\n\n"
            "✅ Har doim Stop Loss qo'ying!\n"
            "✅ Kapitalingizning 1-2% dan ko'p riskga qo'ymang\n\n"
            "💡 Stop Loss — professionallarning asosiy quroli!"
        ),
        (
            "📚 <b>Bugungi Dars: Market Cap</b>\n\n"
            "Market Cap = Narx × Muomaladagi miqdor\n\n"
            "• Large Cap (>$10B) — barqaror, kam risk\n"
            "• Mid Cap ($1B-$10B) — o'rtacha risk\n"
            "• Small Cap (<$1B) — yuqori risk, yuqori potensial\n"
            "• Micro Cap (<$100M) — juda yuqori risk\n\n"
            "💡 Yangi investorlar Large Cap dan boshlashlari yaxshi!"
        ),
    ]
    import random
    return random.choice(lessons)


def get_glossary(term: str) -> str:
    """Moliyaviy atamalar lug'ati"""
    glossary = {
        "RSI": (
            "📖 <b>RSI (Relative Strength Index)</b>\n\n"
            "Texnik tahlil ko'rsatkichi. 0-100 oralig'ida.\n"
            "• <30 = Oversold (Sotib olish imkoniyati)\n"
            "• >70 = Overbought (Ehtiyot)\n"
            "• 30-70 = Neytral"
        ),
        "MACD": (
            "📖 <b>MACD (Moving Average Convergence Divergence)</b>\n\n"
            "Trend ko'rsatkichi. Ikki moving average orasidagi farq.\n"
            "• MACD Signal dan yuqori = Bullish signal\n"
            "• MACD Signal dan past = Bearish signal"
        ),
        "P/E": (
            "📖 <b>P/E (Price-to-Earnings Ratio)</b>\n\n"
            "Aksiya narxini yillik foydaga nisbati.\n"
            "• Past P/E = Arzonroq\n"
            "• Yuqori P/E = Qimmat yoki tez o'sayotgan"
        ),
        "EPS": (
            "📖 <b>EPS (Earnings Per Share)</b>\n\n"
            "Bir aksiyaga to'g'ri keladigan foyda.\n"
            "EPS = Sof foyda / Aksiyalar soni"
        ),
        "ROE": (
            "📖 <b>ROE (Return on Equity)</b>\n\n"
            "Kapital rentabelligi. ROE = Sof foyda / Kapital\n"
            "• >15% = Yaxshi\n"
            "• >25% = Juda yaxshi"
        ),
        "DCA": (
            "📖 <b>DCA (Dollar Cost Averaging)</b>\n\n"
            "Har oy/hafta bir xil miqdorda sotib olish strategiyasi.\n"
            "Narx tushganda ko'proq, ko'tarilganda kamroq olasiz."
        ),
        "ATH": (
            "📖 <b>ATH (All Time High)</b>\n\n"
            "Barcha vaqtlar ichidagi eng yuqori narx."
        ),
        "ATL": (
            "📖 <b>ATL (All Time Low)</b>\n\n"
            "Barcha vaqtlar ichidagi eng past narx."
        ),
        "HODL": (
            "📖 <b>HODL</b>\n\n"
            "'Hold' so'zining xatosi. Uzoq muddatga ushlab turish strategiyasi."
        ),
        "TVL": (
            "📖 <b>TVL (Total Value Locked)</b>\n\n"
            "DeFi protokolida qulflangan jami qiymat.\n"
            "TVL yuqori = Ishonch yuqori"
        ),
        "DEFI": (
            "📖 <b>DeFi (Decentralized Finance)</b>\n\n"
            "Markazlashtirilmagan moliya. Bank va vositachilarsiz xizmatlar."
        ),
        "NFT": (
            "📖 <b>NFT (Non-Fungible Token)</b>\n\n"
            "Noyob raqamli aktiv. Har bir NFT o'ziga xos."
        ),
    }

    term_upper = term.upper().replace(' ', '/')
    for key, val in glossary.items():
        if key.upper() in term_upper or term_upper in key.upper():
            return val

    return (
        f"📖 <b>{term.upper()}</b>\n\n"
        f"Bu atama lug'atimizda hozircha yo'q.\n\n"
        f"Mavjud atamalar: RSI, MACD, P/E, EPS, ROE, DCA, ATH, ATL, HODL, TVL, DeFi, NFT"
    )


def calculate(mode: str, text: str) -> str:
    """Kalkulyatorlar"""
    try:
        parts = [float(x) for x in text.split()]

        if mode == 'rr':
            entry, stop, target = parts[0], parts[1], parts[2]
            risk    = abs(entry - stop)
            reward  = abs(target - entry)
            rr      = reward / risk if risk > 0 else 0
            return (
                f"⚖️ <b>Risk/Reward Natijasi</b>\n\n"
                f"• Kirish: ${entry}\n"
                f"• Stop: ${stop}\n"
                f"• Maqsad: ${target}\n\n"
                f"• Risk: ${risk:.2f}\n"
                f"• Reward: ${reward:.2f}\n"
                f"• R:R = 1:{rr:.2f}\n\n"
                f"{'✅ Yaxshi nisbat!' if rr >= 2 else '⚠️ Risk yuqori!'}"
            )

        elif mode == 'position':
            capital, risk_pct, entry, stop = parts[0], parts[1], parts[2], parts[3]
            risk_usd  = capital * (risk_pct / 100)
            stop_dist = abs(entry - stop)
            qty       = risk_usd / stop_dist if stop_dist > 0 else 0
            pos_size  = qty * entry
            return (
                f"📏 <b>Pozitsiya Hajmi</b>\n\n"
                f"• Kapital: ${capital:,.0f}\n"
                f"• Risk: {risk_pct}% (${risk_usd:,.2f})\n"
                f"• Kirish: ${entry}\n"
                f"• Stop: ${stop}\n\n"
                f"• Miqdor: {qty:.4f} dona\n"
                f"• Pozitsiya: ${pos_size:,.2f}\n"
                f"• Max zarar: ${risk_usd:,.2f}"
            )

        elif mode == 'compound':
            initial, monthly_pct, months = parts[0], parts[1], int(parts[2])
            result = initial
            for _ in range(months):
                result *= (1 + monthly_pct / 100)
            profit = result - initial
            return (
                f"📈 <b>Compound Foiz Natijasi</b>\n\n"
                f"• Boshlang'ich: ${initial:,.2f}\n"
                f"• Oylik foiz: {monthly_pct}%\n"
                f"• Muddat: {months} oy\n\n"
                f"• Yakuniy summa: ${result:,.2f}\n"
                f"• Foyda: ${profit:,.2f}\n"
                f"• O'sish: {(profit/initial*100):.1f}%"
            )

        elif mode == 'breakeven':
            buy_price, commission = parts[0], parts[1]
            breakeven = buy_price * (1 + commission / 100)
            return (
                f"🎯 <b>Break-Even Natijasi</b>\n\n"
                f"• Sotib olish: ${buy_price}\n"
                f"• Komissiya: {commission}%\n\n"
                f"• Break-even: ${breakeven:.4f}\n"
                f"• Komissiya: ${breakeven - buy_price:.4f}"
            )

    except (ValueError, IndexError, ZeroDivisionError):
        pass

    return "❌ Format noto'g'ri. Qayta urinib ko'ring."


# ===================== MUDDATI TUGAGAN OBUNALAR =====================

async def check_portfolio_news(context: ContextTypes.DEFAULT_TYPE):
    """Har 30 daqiqada barcha foydalanuvchilar portfolio yangiliklar tekshiruvi"""
    try:
        import feedparser

        # Barcha foydalanuvchilarni olish
        all_users = await get_all_bot_users()
        if not all_users:
            return

        # Salbiy kalit so'zlar
        negative_words = [
            'crash', 'fall', 'drop', 'decline', 'down', 'loss', 'sell',
            'hack', 'breach', 'ban', 'lawsuit', 'fraud', 'bankrupt', 'delist',
            'warning', 'risk', 'collapse', 'suspend', 'halt', 'plunge',
        ]

        # RSS manbalar
        feeds = [
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss",
            "https://feeds.reuters.com/reuters/businessNews",
            "https://finance.yahoo.com/news/rssindex",
        ]

        # Barcha yangiliklar
        all_news = []
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = (entry.get('title') or '').strip()
                    link  = entry.get('link') or ''
                    if title and link:
                        all_news.append({'title': title, 'link': link})
            except:
                continue

        if not all_news:
            return

        # Har bir foydalanuvchi uchun tekshirish
        for u in all_users:
            uid = u.get('user_id')
            if not uid:
                continue

            # Faqat pullik obuna bor foydalanuvchilarga
            has_signals   = await check_channel_access(uid, "signals")
            has_screener  = await check_screener_access(uid)
            has_premium   = await check_premium_access(uid)
            if not (has_signals or has_screener or has_premium):
                continue

            items = await get_portfolio(uid)
            if not items:
                continue

            tickers = [item.get('ticker', '').upper() for item in items]

            for news in all_news:
                title_upper = news['title'].upper()
                title_lower = news['title'].lower()

                # Ticker bor?
                matched = None
                for ticker in tickers:
                    if ticker in title_upper:
                        matched = ticker
                        break

                if not matched:
                    continue

                # Salbiy?
                is_negative = any(w in title_lower for w in negative_words)
                if not is_negative:
                    continue

                # Xabar yuborish
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=(
                            f"🚨 <b>PORTFEL OGOHLANTIRISHI!</b>\n\n"
                            f"📌 Aktiv: <b>{matched}</b>\n\n"
                            f"⚠️ Salbiy yangilik:\n"
                            f"<a href='{news['link']}'>{news['title'][:100]}</a>\n\n"
                            f"💡 Portfelingizni tekshiring!"
                        ),
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("💼 Portfelni ko'rish", callback_data="my_portfolio")
                        ]])
                    )
                    await asyncio.sleep(0.1)
                except:
                    pass
    except Exception as e:
        print(f"[ERROR] check_portfolio_news: {e}")


async def check_expired(context: ContextTypes.DEFAULT_TYPE):
    """Muddati tugagan obunalarni tekshirish"""
    # Kanal obunalar
    expired = await get_expired_subscriptions()
    for sub in expired:
        channel_id = CHANNEL_IDS.get(sub['section'])
        if channel_id:
            try:
                await context.bot.ban_chat_member(channel_id, sub['user_id'])
                await context.bot.unban_chat_member(channel_id, sub['user_id'])
            except:
                pass
        try:
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"⏰ <b>{SECTION_NAMES.get(sub['section'], '')} obunangiz tugadi.</b>\n\n"
                    f"Yangilash uchun /start yuboring."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except:
            pass
        await mark_expired(sub['id'])

    # Screener obunalar
    expired_scr = await get_expired_screener_subs()
    for sub in expired_scr:
        try:
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text=(
                    f"⏰ <b>Screener obunangiz tugadi.</b>\n\n"
                    f"Yangilash uchun /start yuboring."
                ),
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        except:
            pass
        await mark_screener_expired(sub['id'])


# ===================== ONCHAIN MONITORING =====================

async def monitor_onchain(context: ContextTypes.DEFAULT_TYPE):
    """Onchain ma'lumotlarni monitoring qilish va adminga yuborish"""
    try:
        from onchain import get_global_market
        from config import ONCHAIN_FILTERS

        global_m = await asyncio.to_thread(get_global_market)
        fg_val   = global_m.get('fear_greed', 50)

        # Fear & Greed filtri
        if fg_val <= ONCHAIN_FILTERS['fear_greed_low'] or fg_val >= ONCHAIN_FILTERS['fear_greed_high']:
            fg_cls = global_m.get('fear_greed_cls', '')
            icon   = "🟢" if fg_val <= 20 else "🔴"

            signal_txt = (
                f"⚡ <b>MUHIM SIGNAL: Fear & Greed</b>\n\n"
                f"📊 Ko'rsatkich: {fg_val}/100\n"
                f"📌 Holat: {fg_cls} {icon}\n\n"
                f"🌍 Umumiy bozor:\n"
                f"• Bozor kap: {_fmt_big(global_m.get('total_market_cap', 0))}\n"
                f"• BTC Dominance: {global_m.get('btc_dominance', 0):.1f}%\n\n"
                f"⚠️ Bu ma'lumot faqat tahlil uchun."
            )

            signal_id = await save_onchain_signal("fear_greed", "GLOBAL", signal_txt)
            context.user_data[f'signal_{signal_id}'] = signal_txt

            admin_ids = await get_admin_ids()
            for admin_id in admin_ids:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"🔔 <b>Onchain Signal Tayyorlandi</b>\n\n"
                            f"{signal_txt}\n\n"
                            f"Kanalga yuborasizmi?"
                        ),
                        parse_mode="HTML",
                        reply_markup=onchain_signal_menu(signal_id)
                    )
                except:
                    pass
    except Exception as e:
        print(f"[ERROR] Onchain monitoring: {e}")


def _fmt_big(n):
    if not n or n == 0:
        return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.2f}"
    except:
        return "N/A"


# ===================== OGOHLANTIRISH TEKSHIRUVI =====================

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi ogohlantirishlarini tekshirish"""
    try:
        alerts = await get_active_alerts()
        if not alerts:
            return

        for alert in alerts:
            try:
                ticker      = alert['ticker']
                ticker_type = alert['ticker_type']
                alert_type  = alert['alert_type']
                condition   = alert['condition']
                value       = alert['value']

                # Hozirgi narxni olish
                current = None
                if ticker_type == 'stock':
                    import yfinance as yf
                    stock   = yf.Ticker(ticker)
                    info    = stock.info
                    if alert_type == 'price':
                        current = info.get('regularMarketPrice')
                    elif alert_type == 'rsi':
                        hist    = stock.history(period="1mo")
                        from screener_stock import _calc_rsi
                        current = _calc_rsi(hist)
                elif ticker_type == 'crypto':
                    import requests
                    from screener_crypto import get_coin_id
                    coin_id = get_coin_id(ticker)
                    resp    = requests.get(
                        f"{COINGECKO_BASE}/simple/price",
                        params={"ids": coin_id, "vs_currencies": "usd"},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        current = resp.json().get(coin_id, {}).get('usd')

                if current is None:
                    continue

                # Shart tekshirish
                triggered = False
                if condition == 'above' and current >= value:
                    triggered = True
                elif condition == 'below' and current <= value:
                    triggered = True

                if triggered:
                    await deactivate_alert(alert['id'])
                    cond_txt = "oshdi" if condition == 'above' else "tushdi"
                    type_txt = {'price': 'Narx', 'rsi': 'RSI', 'pct': 'Foiz'}
                    await context.bot.send_message(
                        chat_id=alert['user_id'],
                        text=(
                            f"🔔 <b>OGOHLANTIRISH!</b>\n\n"
                            f"📊 {ticker} — {type_txt.get(alert_type, alert_type)}\n"
                            f"📌 {current:.2f} — {value} dan {cond_txt}!\n\n"
                            f"✅ Ogohlantirish o'chirildi."
                        ),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(
                                f"🔎 {ticker} tahlil qilish",
                                callback_data=f"refresh_{ticker_type}_{ticker}"
                            )],
                            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
                        ])
                    )
            except Exception as e:
                print(f"[ERROR] Alert tekshirishda: {e}")
                continue

    except Exception as e:
        print(f"[ERROR] check_alerts: {e}")


# ===================== MAIN =====================

def main():
    from database import _init_db_sync
    _init_db_sync()

    persistence = PicklePersistence(filepath="bot_persistence.pickle")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .persistence(persistence)
        .build()
    )

    # Handlerlar
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("admin",    admin_cmd))
    app.add_handler(CommandHandler("onchain",  handle_onchain_command))
    app.add_handler(CommandHandler("screener", screener_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Scheduler
    if app.job_queue:
        app.job_queue.run_repeating(check_expired,       interval=3600,  first=60)
        app.job_queue.run_repeating(check_alerts,        interval=300,   first=30)
        app.job_queue.run_repeating(check_portfolio_news, interval=1800, first=120)

    print("[SUCCESS] Azia Quant Bot ishga tushdi! 🚀")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
