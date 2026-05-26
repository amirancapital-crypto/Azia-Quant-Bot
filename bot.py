#!/usr/bin/env python3
"""
Azia Quant Bot — Main Bot Module
Toza, professional arxitektura
"""

import os
import asyncio
import logging
import string
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PicklePersistence
)
from telegram.error import TelegramError

# Config
from config import (
    BOT_TOKEN, ADMIN_IDS, ADMIN_USERNAME,
    CARD_NUMBER, CARD_OWNER,
    SIGNAL_PRICES, SCREENER_PRICES, CRYPTO_EDU_PRICE, STOCK_EDU_PRICE, PREMIUM_PRICE,
    SECTION_NAMES, CHANNEL_SECTIONS, CHANNEL_IDS,
    WELCOME_TEXT, ACTIVE_PROMO_CODES,
    FREE_DAILY_SCREENER_LIMIT, FREE_DAILY_AI_LIMIT,
)

# Database
from database import (
    init_db, save_user,
    get_all_users, get_all_bot_users, get_non_subscribers,
    check_channel_access, check_screener_access, check_premium_access,
    save_subscription, approve_subscription, reject_subscription,
    save_screener_sub, approve_screener_sub, reject_screener_sub,
    save_premium_sub, approve_premium_sub, reject_premium_sub,
    get_portfolio, add_portfolio, delete_portfolio,
    get_user_alerts, save_alert, delete_alert, get_all_active_alerts,
    check_promo, use_promo, create_promo, get_all_promos,
    save_referral, get_referral_stats, update_referral_reward,
    save_affiliate, get_pending_affiliates, approve_affiliate,
    get_stats, cancel_user_subscription,
    get_expired_subscriptions, mark_expired,
    get_expired_screener_subs, mark_screener_expired,
    check_daily_limit, increment_daily_limit,
)

# Services
from services.crypto_service import crypto_service
from services.stock_service import stock_service
from services.ai_service import ai_service
from services.onchain_service import onchain_service
from services.news_service import news_service
from services.sentiment_service import sentiment_service

# Workers
from workers.briefing_worker import send_daily_briefing
from workers.alert_worker import check_alerts
from workers.news_worker import check_portfolio_news

# Keyboards
from keyboards import (
    main_menu, main_reply_menu, back_menu, home_menu,
    section_back_menu, confirm_menu,
    signals_duration_menu, screener_duration_menu,
    screener_action_menu, free_screener_result_menu,
    alert_type_menu, alert_condition_menu, my_alerts_menu,
    portfolio_menu, referral_menu,
    free_menu, calculator_menu,
    admin_main_menu, admin_approve_menu,
)

# Logging
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ===================== YORDAMCHI FUNKSIYALAR =====================

async def is_admin(user) -> bool:
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lstrip("@") == ADMIN_USERNAME:
        return True
    return False


def duration_label(months: int) -> str:
    if months == 0:  return "Doimiy ♾"
    if months == 6:  return "6 oylik"
    if months == 12: return "1 yillik"
    return f"{months} oylik"


def fmt_big(n) -> str:
    if not n: return "N/A"
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9:  return f"${n/1e9:.2f}B"
    if n >= 1e6:  return f"${n/1e6:.2f}M"
    return f"${n:,.0f}"


async def check_subscription(user_id: int) -> dict:
    return {
        "signals":  await check_channel_access(user_id, "signals"),
        "screener": await check_screener_access(user_id),
        "premium":  await check_premium_access(user_id),
    }


async def has_any_paid_sub(user_id: int) -> bool:
    subs = await check_subscription(user_id)
    return any(subs.values())


async def send_payment_info(query_or_msg, section_name: str, price: int,
                             duration: str, sub_id: int, sub_type: str):
    promo_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Promo kod bormi?", callback_data=f"promo_{sub_type}_{sub_id}_{price}")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
    ])
    text = (
        f"💳 <b>TO'LOV MA'LUMOTI</b>\n\n"
        f"📦 Xizmat: <b>{section_name}</b>\n"
        f"⏱ Muddat: <b>{duration}</b>\n"
        f"💰 Narx: <b>${price}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 Karta: <code>{CARD_NUMBER}</code>\n"
        f"👤 Egasi: <b>{CARD_OWNER}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 To'lov chekini yuboring\n"
        f"⏰ Admin 24 soat ichida tasdiqlaydi"
    )
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(text, parse_mode="HTML", reply_markup=promo_btn)
    else:
        await query_or_msg.reply_text(text, parse_mode="HTML", reply_markup=promo_btn)


# ===================== START =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await save_user(user.id, user.username or "", user.full_name or "")

    keys_to_clear = [
        'waiting_payment', 'sub_type', 'sub_id', 'scr_sub_id', 'premium_sub_id',
        'screener_mode', 'ai_mode', 'ai_history', 'calc_mode',
        'portfolio_watch', 'portfolio_new', 'admin_broadcast',
        'admin_broadcast_nonsub', 'admin_promo', 'admin_cancel_sub',
    ]
    for key in keys_to_clear:
        context.user_data.pop(key, None)

    args = context.args
    if args:
        code = args[0]
        if code.startswith("ref_"):
            try:
                referrer_id = int(code[4:])
                if referrer_id != user.id:
                    await save_referral(referrer_id, user.id)
            except ValueError:
                pass
        elif code.startswith("aff_"):
            context.user_data["affiliate_code"] = code[4:]
        else:
            ticker = code.upper()
            admin = await is_admin(user)
            await update.message.reply_text(
                "👇 Pastdagi tugmalardan foydalaning:",
                reply_markup=main_reply_menu(is_admin=admin)
            )
            await _handle_screener_deeplink(update, context, ticker)
            return

    admin = await is_admin(user)
    await update.message.reply_text(
        "👇 Tez kirish uchun pastdagi tugmalardan foydalaning:",
        reply_markup=main_reply_menu(is_admin=admin)
    )
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu(is_admin=admin)
    )


async def _handle_screener_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE, ticker: str):
    user  = update.effective_user
    admin = await is_admin(user)
    await update.message.reply_text(f"🔍 <b>{ticker}</b> bo'yicha tahlil olinmoqda...", parse_mode="HTML")
    try:
        from config import CRYPTO_TICKER_MAP
        if ticker in CRYPTO_TICKER_MAP:
            result = crypto_service.get_screener_result(ticker, is_free=True)
        else:
            result = stock_service.get_screener_result(ticker, is_free=True)
        if result:
            await update.message.reply_text(result, parse_mode="HTML",
                reply_markup=main_menu(is_admin=admin), disable_web_page_preview=True)
        else:
            await update.message.reply_text(f"❌ <b>{ticker}</b> bo'yicha ma'lumot topilmadi.",
                parse_mode="HTML", reply_markup=main_menu(is_admin=admin))
    except Exception as e:
        logger.error(f"Deep link screener xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi.", reply_markup=main_menu(is_admin=admin))


# ===================== REPLY KEYBOARD HANDLER =====================

REPLY_SECTIONS = {
    "👤 Mening Obunalarim":  "my_subs",
    "💼 Mening Portfelim":   "my_portfolio",
    "🎟 Promokodlar":        "promo_list",
    "👥 Referral":           "referral_menu",
    "💬 Admin bilan aloqa":  "sec_admin",
    "👨‍💼 Admin Panel":        "open_admin",
}


async def show_section(update: Update, context: ContextTypes.DEFAULT_TYPE, section: str):
    user  = update.effective_user
    admin = await is_admin(user)

    if section == "my_subs":
        subs = await check_subscription(user.id)
        txt = "📋 <b>Mening Obunalarim</b>\n\n"
        if subs["signals"]:  txt += "✅ Signals\n"
        if subs["screener"]: txt += "✅ Onchain + Screener\n"
        if subs["premium"]:  txt += "✅ Premium\n"
        if not any(subs.values()):
            txt += "😔 Hozircha faol obuna yo'q.\n\n💎 Obuna oling!"
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=home_menu())

    elif section == "my_portfolio":
        if not await has_any_paid_sub(user.id):
            await update.message.reply_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")
                ]])
            )
            return
        items = await get_portfolio(user.id)
        await update.message.reply_text("💼 <b>Mening Portfelim</b>",
            parse_mode="HTML", reply_markup=portfolio_menu(items))

    elif section == "promo_list":
        from config import ACTIVE_PROMO_CODES
        if not ACTIVE_PROMO_CODES:
            txt = "🎟 <b>Promokodlar</b>\n\n😔 Hozircha amaldagi promokodlar yo'q.\n\n📢 Yangiliklari uchun: @Azia_Invest"
        else:
            txt = "🎟 <b>Faol Promokodlar</b>\n\n"
            for promo in ACTIVE_PROMO_CODES:
                txt += (
                    f"{promo['emoji']} <b>{promo['description']}</b>\n\n"
                    f"🏷 Kod: <code>{promo['code']}</code>\n"
                    f"💰 Chegirma: <b>{promo['discount']}%</b>\n"
                    f"📅 Muddat: {promo['valid_until']}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📌 Obuna olishda kiriting!\n"
                )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=home_menu())

    elif section == "referral_menu":
        stats = await get_referral_stats(user.id)
        ref_link = f"https://t.me/azia_quant_bot?start=ref_{user.id}"
        txt = (
            f"👥 <b>Referral Tizimi</b>\n\n"
            f"🔗 Sizning havolangiz:\n<code>{ref_link}</code>\n\n"
            f"📊 Statistika:\n"
            f"• Taklif qilinganlar: {stats['count']} ta\n"
            f"• Jami mukofot: ${stats['total_reward']}\n\n"
            f"💡 Har bir taklif qilingan obunachi uchun {10}% mukofot!"
        )
        await update.message.reply_text(txt, parse_mode="HTML", reply_markup=referral_menu())

    elif section == "sec_admin":
        await update.message.reply_text(
            f"💬 <b>Admin bilan aloqa</b>\n\nSavolingizni yuboring!\n\n📞 Admin: @{ADMIN_USERNAME}",
            parse_mode="HTML", reply_markup=home_menu()
        )

    elif section == "open_admin":
        if not admin:
            await update.message.reply_text("❌ Ruxsat yo'q!")
            return
        await update.message.reply_text(
            "👨‍💼 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_main_menu()
        )


# ===================== BUTTON HANDLER =====================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    user = update.effective_user
    data = q.data
    await q.answer()

    if data == "back":
        context.user_data.clear()
        admin = await is_admin(user)
        try:
            await q.edit_message_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu(is_admin=admin))
        except:
            await q.message.reply_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu(is_admin=admin))

    elif data == "sep":
        pass

    # ── SIGNALS ──
    elif data == "sec_signals":
        txt = (
            "📊 <b>SIGNAL XIZMATI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Biz bozorda 'taxmin' bilan ishlamaymiz. "
            "Signallarimiz faqat <b>uchta filtrdan o'tgan</b> aktivlar uchun shakllanadi:\n\n"
            "📈 <b>Texnik tahlil:</b> Trend va zonalar aniqligi.\n"
            "⛓ <b>Onchain:</b> 'Smart money' harakatlari va hajmlar.\n"
            "🤖 <b>AI Screener:</b> Volatillik va risk parametrlari.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📦 <b>Sizga nima yetib keladi?</b>\n\n"
            "Har bir signalda:\n\n"
            "📍 Kirish nuqtasi\n"
            "🎯 TP1 · TP2 · TP3 darajalari\n"
            "🛡 Stop Loss chegarasi\n"
            "⚖️ Risk/Reward nisbati\n\n"
            "Tahlilni o'zingiz qilib o'tirmaysiz — "
            "biz buni algoritmlar yordamida qilamiz.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 <b>OBUNA SHARTLARI:</b>\n\n"
            f"🗓 6 oylik — <b>${SIGNAL_PRICES[6]}</b>\n"
            f"📅 1 yillik — <b>${SIGNAL_PRICES[12]}</b>\n"
            f"♾️ Doimiy — <b>${SIGNAL_PRICES[0]}</b>\n\n"
            "🎟 <i>Birinchi marta obuna bo'layotganlar uchun:</i>\n"
            "<code>WELCOME30</code> kodi bilan <b>30% chegirma!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>👇 Quyidagi tugmalardan birini tanlang "
            "va obuna jarayonini boshlang.</i>"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=signals_duration_menu())

    elif data.startswith("sig_dur_"):
        duration = int(data.split("_")[2])
        price    = SIGNAL_PRICES.get(duration, 0)
        dur_lbl  = duration_label(duration)
        sub_id   = await save_subscription(user.id, user.username, user.full_name, "signals", duration)
        context.user_data.update({"waiting_payment": True, "sub_id": sub_id, "sub_type": "channel"})
        await send_payment_info(q, SECTION_NAMES["signals"], price, dur_lbl, sub_id, "channel")

    # ── ONCHAIN + SCREENER ──
    elif data == "sec_onchain":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if has_access:
            await q.edit_message_text(
                "🔗 <b>Onchain + Screener</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Professional tahlil vositalari:\n\n"
                "🔎 Aksiya Screener — AAPL, TSLA...\n"
                "🔍 Crypto Screener — BTC, ETH...\n"
                "⛓ Onchain Tahlil — zanjir ma'lumotlari\n"
                "😊 Sentiment — bozor kayfiyati\n\n"
                "Qaysi bo'limni tanlaysiz?",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔎 Aksiya Screener",  callback_data="use_stock_screener")],
                    [InlineKeyboardButton("🔍 Crypto Screener",  callback_data="use_crypto_screener")],
                    [InlineKeyboardButton("⛓ Onchain Tahlil",   callback_data="use_onchain_report")],
                    [InlineKeyboardButton("😊 Sentiment Tahlil", callback_data="use_sentiment")],
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
                ])
            )
        else:
            txt = (
                "🔗 <b>Onchain + Screener</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔎 Aksiya + Crypto Screener\n"
                "⛓ Onchain tahlil (BTC, ETH, SOL)\n"
                "🤖 AI tahlil har screener natijasida\n"
                "😊 Sentiment tahlil\n"
                "💼 Portfel kuzatuv\n"
                "🔔 Narx ogohlantirishlari\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💰 <b>Narxlar:</b>\n"
                f"• 🗓 6 oylik — <b>${SCREENER_PRICES[6]}</b>\n"
                f"• 📅 1 yillik — <b>${SCREENER_PRICES[12]}</b>\n"
                f"• ♾ Doimiy — <b>${SCREENER_PRICES[0]}</b>"
            )
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=screener_duration_menu())

    elif data.startswith("scr_dur_"):
        duration = int(data.split("_")[2])
        price    = SCREENER_PRICES.get(duration, 0)
        dur_lbl  = duration_label(duration)
        sub_id   = await save_screener_sub(user.id, user.username, user.full_name, duration)
        context.user_data.update({"waiting_payment": True, "scr_sub_id": sub_id, "sub_type": "onchain_screener"})
        await send_payment_info(q, SECTION_NAMES["onchain"], price, dur_lbl, sub_id, "screener")

    # ── SCREENER ──
    elif data == "use_stock_screener":
        context.user_data["screener_mode"] = "stock"
        await q.edit_message_text(
            "🔎 <b>Aksiya Screener</b>\n\nTicker yozing:\n<code>AAPL, TSLA, NVDA, MSFT</code>",
            parse_mode="HTML", reply_markup=section_back_menu("sec_onchain")
        )

    elif data == "use_crypto_screener":
        context.user_data["screener_mode"] = "crypto"
        await q.edit_message_text(
            "🔍 <b>Crypto Screener</b>\n\nTicker yozing:\n<code>BTC, ETH, SOL, BNB</code>",
            parse_mode="HTML", reply_markup=section_back_menu("sec_onchain")
        )

    elif data.startswith("refresh_"):
        parts  = data.split("_")
        t_type = parts[1]
        ticker = parts[2]
        await q.edit_message_text(f"🔄 <b>{ticker}</b> yangilanmoqda...", parse_mode="HTML")
        if t_type == "crypto":
            result = crypto_service.get_screener_result(ticker)
        else:
            result = stock_service.get_screener_result(ticker)
        if result:
            await q.edit_message_text(result, parse_mode="HTML",
                reply_markup=screener_action_menu(ticker, t_type), disable_web_page_preview=True)

    # ── ONCHAIN REPORT ──
    elif data == "use_onchain_report":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return
        await q.edit_message_text("⏳ Onchain ma'lumotlar olinmoqda...", parse_mode="HTML")
        report = onchain_service.get_full_report()
        await q.edit_message_text(report, parse_mode="HTML",
            reply_markup=section_back_menu("sec_onchain"), disable_web_page_preview=True)

    # ── SENTIMENT ──
    elif data == "use_sentiment":
        has_access = await check_screener_access(user.id) or await check_premium_access(user.id)
        if not has_access:
            await q.answer("❌ Obuna kerak!", show_alert=True)
            return
        await q.edit_message_text(
            "😊 <b>Sentiment Tahlil</b>\n\nTicker yozing:\n<code>BTC, ETH, SOL</code>",
            parse_mode="HTML", reply_markup=section_back_menu("sec_onchain")
        )
        context.user_data["screener_mode"] = "sentiment"

    # ── TA'LIM ──
    elif data == "sec_crypto_edu":
        has_access = await check_channel_access(user.id, "crypto_edu") or await check_premium_access(user.id)
        if has_access:
            await q.edit_message_text(
                "📚 <b>Crypto Darslar</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Kirish huquqi faol!\n\n"
                "Darslar kanaliga o'ting 👇",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 Darslar kanaliga o'tish", url="https://t.me/+example")],
                    [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
                ])
            )
        else:
            txt = (
                "📚 <b>Crypto Darslar</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "₿ Blockchain asoslari\n"
                "📈 Texnik tahlil\n"
                "⚖️ Risk menejment\n"
                "🏦 DeFi va NFT\n"
                "🎯 Trading strategiyalari\n"
                "🔐 Kriptovalyuta xavfsizligi\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Narx: ${CRYPTO_EDU_PRICE} (Doimiy)</b>"
            )
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("crypto_edu"))

    elif data == "sec_stock_edu":
        await q.edit_message_text(
            "📈 <b>Fond Bozori Darslar</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏳ <b>Bu bo'lim hali faol emas</b>\n\n"
            "Tez kunda ishga tushadi! 🚀\n\n"
            "📢 Yangiliklar uchun: @AziaQuantBot",
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    elif data == "sec_quant":
        await q.edit_message_text(
            "🤖 <b>Quant Trading</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏳ <b>Bu bo'lim hali faol emas</b>\n\n"
            "Tez kunda ishga tushadi! 🚀\n\n"
            "📢 Yangiliklar uchun: @AziaQuantBot",
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    elif data == "sec_ai":
        await q.edit_message_text(
            "🧠 <b>AI Moliyaviy Yordamchi</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏳ <b>Bu bo'lim hali faol emas</b>\n\n"
            "Tez kunda ishga tushadi! 🚀\n\n"
            "📢 Yangiliklar uchun: @AziaQuantBot",
            parse_mode="HTML",
            reply_markup=home_menu()
        )

    # ── PREMIUM ──
    elif data == "sec_premium":
        has_access = await check_premium_access(user.id)
        if has_access:
            await q.edit_message_text(
                "💎 <b>Premium To'liq Paket</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Siz Premium obunachisiz!\n\n"
                "Barcha funksiyalar faol 🚀",
                parse_mode="HTML",
                reply_markup=home_menu()
            )
        else:
            txt = (
                "💎 <b>Premium To'liq Paket</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔥 Barcha bo'limlar bir paketda!\n\n"
                "📊 Signals — professional signallar\n"
                "🔎 Aksiya + Crypto Screener\n"
                "⛓ Onchain + Sentiment tahlil\n"
                "📚 Crypto Darslar\n"
                "🤖 AI Yordamchi (cheksiz)\n"
                "💼 Portfel kuzatuv\n"
                "🔔 Ogohlantirishlar tizimi\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 <b>Narx: ${PREMIUM_PRICE} (Doimiy)</b>"
            )
            await q.edit_message_text(txt, parse_mode="HTML", reply_markup=confirm_menu("premium"))

    # ── CONFIRM ──
    elif data.startswith("confirm_"):
        section = data[8:]
        if section == "crypto_edu":
            sub_id = await save_subscription(user.id, user.username, user.full_name, "crypto_edu", 0)
            context.user_data.update({"waiting_payment": True, "sub_id": sub_id, "sub_type": "channel"})
            await send_payment_info(q, "📚 Crypto Darslar", CRYPTO_EDU_PRICE, "Doimiy ♾", sub_id, "channel")
        elif section == "premium":
            sub_id = await save_premium_sub(user.id, user.username, user.full_name)
            context.user_data.update({"waiting_payment": True, "premium_sub_id": sub_id, "sub_type": "premium"})
            await send_payment_info(q, "💎 Premium To'liq Paket", PREMIUM_PRICE, "Doimiy ♾", sub_id, "premium")

    # ── PROMO KOD ──
    elif data.startswith("promo_"):
        parts    = data.split("_")
        sub_type = parts[1]
        sub_id   = int(parts[2])
        price    = int(parts[3])
        context.user_data["promo_sub_type"] = sub_type
        context.user_data["promo_sub_id"]   = sub_id
        context.user_data["promo_price"]    = price
        context.user_data["promo_input"]    = True
        await q.edit_message_text("🎟 <b>Promo kod kiriting:</b>", parse_mode="HTML", reply_markup=home_menu())

    # ── BEPUL XIZMATLAR ──
    elif data == "sec_free":
        await q.edit_message_text(
            "🆓 <b>Bepul Xizmatlar</b>\n\nQuyidagilardan birini tanlang:",
            parse_mode="HTML", reply_markup=free_menu()
        )

    elif data == "free_market":
        await q.edit_message_text("⏳ Ma'lumot olinmoqda...", parse_mode="HTML")
        report = onchain_service.get_full_report()
        await q.edit_message_text(report, parse_mode="HTML",
            reply_markup=section_back_menu("sec_free"), disable_web_page_preview=True)

    elif data == "free_screener":
        context.user_data["screener_mode"] = "free"
        await q.edit_message_text(
            "🔍 <b>Bepul Screener</b>\n\nTicker yozing:\n<code>BTC, ETH, AAPL, TSLA</code>",
            parse_mode="HTML", reply_markup=section_back_menu("sec_free")
        )

    elif data == "free_news":
        await q.edit_message_text("⏳ Yangiliklar olinmoqda...", parse_mode="HTML")
        news_list = news_service.get_market_news(limit=5)
        if news_list:
            txt = "📰 <b>So'nggi Yangiliklar</b>\n\n"
            for n in news_list:
                txt += f"• <a href='{n['url']}'>{n['title']}</a>\n"
                if n.get("source"):
                    txt += f"  📰 {n['source']}\n"
                txt += "\n"
        else:
            txt = "📰 Yangiliklar topilmadi"
        await q.edit_message_text(txt, parse_mode="HTML",
            reply_markup=section_back_menu("sec_free"), disable_web_page_preview=True)

    elif data == "free_calc":
        await q.edit_message_text(
            "🔢 <b>Kalkulyatorlar</b>\n\nKerakli kalkulyatorni tanlang:",
            parse_mode="HTML", reply_markup=calculator_menu()
        )

    elif data == "free_calc_back":
        await q.edit_message_text(
            "🔢 <b>Kalkulyatorlar</b>\n\nKerakli kalkulyatorni tanlang:",
            parse_mode="HTML", reply_markup=calculator_menu()
        )

    elif data == "free_lesson":
        await q.edit_message_text(_get_daily_lesson(), parse_mode="HTML",
            reply_markup=section_back_menu("sec_free"))

    elif data == "free_calendar":
        await q.edit_message_text(
            "📅 <b>Ekonomik Kalendar</b>\n\nBu hafta muhim voqealar:\n\n"
            "• <a href='https://www.forexfactory.com/calendar'>Forex Factory</a>\n"
            "• <a href='https://coinmarketcal.com'>CoinMarketCal</a>",
            parse_mode="HTML", reply_markup=section_back_menu("sec_free"), disable_web_page_preview=True)

    elif data == "free_ipo":
        await q.edit_message_text("⏳ IPO ma'lumotlari olinmoqda...", parse_mode="HTML")
        try:
            import feedparser
            feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=IPO&region=US&lang=en-US")
            ipo_txt = "🏢 <b>IPO Tracker</b>\n\n"
            count = 0
            for entry in feed.entries[:5]:
                title = (entry.get("title") or "")[:70]
                link  = entry.get("link") or ""
                if title and link:
                    ipo_txt += f"• <a href='{link}'>{title}</a>\n\n"
                    count += 1
            if not count:
                ipo_txt += "Ma'lumot topilmadi"
        except:
            ipo_txt = "🏢 <b>IPO Tracker</b>\n\nMa'lumot olinmadi."
        await q.edit_message_text(ipo_txt, parse_mode="HTML",
            reply_markup=section_back_menu("sec_free"), disable_web_page_preview=True)

    # ── KALKULYATORLAR ──
    elif data == "calc_rr":
        context.user_data["calc_mode"] = "rr"
        await q.edit_message_text(
            "⚖️ <b>Risk/Reward Kalkulyatori</b>\n\nFormat: <code>kirish stop maqsad</code>\nMisol: <code>100 90 130</code>",
            parse_mode="HTML", reply_markup=section_back_menu("free_calc"))

    elif data == "calc_position":
        context.user_data["calc_mode"] = "position"
        await q.edit_message_text(
            "📏 <b>Pozitsiya Hajmi</b>\n\nFormat: <code>kapital risk% stop%</code>\nMisol: <code>10000 2 5</code>",
            parse_mode="HTML", reply_markup=section_back_menu("free_calc"))

    elif data == "calc_compound":
        context.user_data["calc_mode"] = "compound"
        await q.edit_message_text(
            "📈 <b>Compound Foiz</b>\n\nFormat: <code>kapital foiz% oy</code>\nMisol: <code>1000 5 12</code>",
            parse_mode="HTML", reply_markup=section_back_menu("free_calc"))

    elif data == "calc_breakeven":
        context.user_data["calc_mode"] = "breakeven"
        await q.edit_message_text(
            "🎯 <b>Break-even</b>\n\nFormat: <code>narx komissiya%</code>\nMisol: <code>100 0.1</code>",
            parse_mode="HTML", reply_markup=section_back_menu("free_calc"))

    # ── PORTFEL ──
    elif data == "my_portfolio":
        if not await has_any_paid_sub(user.id):
            await q.edit_message_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")
                ]])
            )
            return
        items = await get_portfolio(user.id)
        await q.edit_message_text("💼 <b>Mening Portfelim</b>",
            parse_mode="HTML", reply_markup=portfolio_menu(items))

    elif data == "portfolio_back":
        admin = await is_admin(user)
        try:
            await q.message.reply_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu(is_admin=admin))
            await q.delete_message()
        except:
            pass

    elif data == "portfolio_watch_new":
        if not await has_any_paid_sub(user.id):
            await q.edit_message_text(
                "🔒 <b>Bu funksiya faqat pullik obuna uchun!</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")
                ]])
            )
            return
        context.user_data["portfolio_watch"] = True
        await q.edit_message_text(
            "💼 <b>Aktiv qo'shish</b>\n\nTicker yozing:\n• 🪙 Crypto: <code>BTC, ETH, SOL</code>\n• 📈 Aksiya: <code>AAPL, TSLA, NVDA</code>",
            parse_mode="HTML", reply_markup=section_back_menu("my_portfolio"))

    elif data == "portfolio_watch_done":
        await q.edit_message_text(
            "🎉 <b>Rahmat!</b>\n\nAktivingiz qo'shildi.\n\n🔔 Muhim yangilik chiqsa darhol xabar beramiz!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Bosh menyuga qaytish", callback_data="back")
            ]])
        )

    elif data.startswith("portfolio_del_"):
        item_id = int(data.split("_")[2])
        await delete_portfolio(item_id, user.id)
        items = await get_portfolio(user.id)
        await q.edit_message_text("💼 <b>Mening Portfelim</b>",
            parse_mode="HTML", reply_markup=portfolio_menu(items))

    elif data == "portfolio_news":
        await q.edit_message_text("⏳ Yangiliklar olinmoqda...", parse_mode="HTML")
        items = await get_portfolio(user.id)
        if not items:
            await q.edit_message_text("Portfelingiz bo'sh!", reply_markup=home_menu())
            return
        txt = "📰 <b>Portfel Yangiliklari</b>\n\n"
        for item in items[:5]:
            ticker = item["ticker"]
            n_list = news_service.get_crypto_news(ticker, limit=2)
            if n_list:
                txt += f"<b>{ticker}:</b>\n"
                for n in n_list:
                    txt += f"• <a href='{n['url']}'>{n['title'][:60]}</a>\n"
                txt += "\n"
        if txt == "📰 <b>Portfel Yangiliklari</b>\n\n":
            txt += "Yangiliklar topilmadi"
        await q.edit_message_text(txt, parse_mode="HTML",
            reply_markup=section_back_menu("my_portfolio"), disable_web_page_preview=True)

    # ── OGOHLANTIRISH ──
    elif data.startswith("alert_set_"):
        parts  = data.split("_")
        t_type = parts[2]
        ticker = parts[3]
        await q.edit_message_text(
            f"🔔 <b>{ticker} uchun ogohlantirish</b>\n\nTurini tanlang:",
            parse_mode="HTML", reply_markup=alert_type_menu(ticker, t_type))

    elif data.startswith("alert_price_") or data.startswith("alert_rsi_") or data.startswith("alert_pct_"):
        parts  = data.split("_")
        a_type = parts[1]
        t_type = parts[2]
        ticker = parts[3]
        context.user_data["alert_type"]        = a_type
        context.user_data["alert_ticker"]      = ticker
        context.user_data["alert_ticker_type"] = t_type
        await q.edit_message_text("📊 Shart tanlang:", parse_mode="HTML",
            reply_markup=alert_condition_menu(a_type, ticker, t_type))

    elif data.startswith("alert_cond_"):
        parts     = data.split("_")
        condition = parts[2]
        a_type    = parts[3]
        t_type    = parts[4]
        ticker    = parts[5]
        context.user_data["alert_condition"]   = condition
        context.user_data["alert_type"]        = a_type
        context.user_data["alert_ticker"]      = ticker
        context.user_data["alert_ticker_type"] = t_type
        context.user_data["alert_input"]       = True
        labels = {"price": "narx", "rsi": "RSI", "pct": "foiz o'zgarish"}
        await q.edit_message_text(
            f"🔔 {labels.get(a_type, a_type)} qiymatini kiriting:\nMisol: <code>50000</code>",
            parse_mode="HTML", reply_markup=home_menu())

    elif data.startswith("alert_del_"):
        alert_id = int(data.split("_")[2])
        await delete_alert(alert_id, user.id)
        alerts = await get_user_alerts(user.id)
        if alerts:
            await q.edit_message_text("🔔 <b>Ogohlantirishlar</b>",
                parse_mode="HTML", reply_markup=my_alerts_menu(alerts))
        else:
            await q.edit_message_text("🔔 Ogohlantirishlar yo'q", reply_markup=home_menu())

    # ── REFERRAL ──
    elif data == "referral_menu":
        stats    = await get_referral_stats(user.id)
        ref_link = f"https://t.me/azia_quant_bot?start=ref_{user.id}"
        txt = (
            f"👥 <b>Referral Tizimi</b>\n\n"
            f"🔗 Sizning havolangiz:\n<code>{ref_link}</code>\n\n"
            f"📊 Statistika:\n"
            f"• Taklif qilinganlar: {stats['count']} ta\n"
            f"• Jami mukofot: ${stats['total_reward']}\n\n"
            f"💡 Har bir to'lovdan {10}% mukofot!"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=referral_menu())

    elif data == "ref_stats":
        stats = await get_referral_stats(user.id)
        await q.edit_message_text(
            f"📊 <b>Referral Statistika</b>\n\n• Taklif qilinganlar: {stats['count']} ta\n• Jami mukofot: ${stats['total_reward']}",
            parse_mode="HTML", reply_markup=section_back_menu("referral_menu"))

    elif data == "ref_affiliate":
        await save_affiliate(user.id, user.username or "")
        await q.edit_message_text(
            "🤝 <b>Affiliate so'rovingiz yuborildi!</b>\n\nAdmin tez orada ko'rib chiqadi.",
            parse_mode="HTML", reply_markup=home_menu())

    # ── ADMIN ──
    elif data == "open_admin":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        await q.edit_message_text("👨‍💼 <b>Admin Panel</b>", parse_mode="HTML", reply_markup=admin_main_menu())

    elif data == "admin_stats":
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        stats = await get_stats()
        txt = (
            f"📊 <b>Statistika</b>\n\n"
            f"👤 Jami foydalanuvchilar: {stats.get('total_users', 0)}\n"
            f"✅ Faol obunalar: {stats.get('active_subs', 0)}\n"
            f"📊 Jami obunalar: {stats.get('total_subscriptions', 0)}\n"
        )
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=admin_main_menu())

    elif data == "admin_users" or data.startswith("admin_users_page_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        page       = int(data.split("_")[-1]) if data.startswith("admin_users_page_") else 0
        per_page   = 10
        users_list = await get_all_users()
        total      = len(users_list)
        start      = page * per_page
        end        = start + per_page
        page_users = users_list[start:end]
        txt = f"👥 <b>Foydalanuvchilar ({total} ta)</b> | Sahifa {page+1}/{max(1,(total-1)//per_page+1)}\n\n"
        for u in page_users:
            uname   = f"@{u.get('username')}" if u.get("username") else "—"
            created = str(u.get("created_at", ""))[:16]
            has_sub = await has_any_paid_sub(u.get("user_id"))
            icon    = "✅" if has_sub else "🆓"
            txt += f"{icon} {u.get('full_name', '')} {uname}\n   🆔 {u.get('user_id')} | 📅 {created}\n"
        txt += "\n✅ Obunachi | 🆓 Bepul"
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_users_page_{page-1}"))
        if end < total:
            nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin_users_page_{page+1}"))
        keyboard = []
        if nav: keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data="open_admin")])
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_all_users" or data.startswith("admin_all_users_page_"):
        if not await is_admin(user):
            await q.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        page           = int(data.split("_")[-1]) if data.startswith("admin_all_users_page_") else 0
        per_page       = 10
        all_users_list = await get_all_bot_users()
        non_subs       = await get_non_subscribers()
        non_ids        = {u["user_id"] for u in non_subs}
        total          = len(all_users_list)
        start          = page * per_page
        end            = start + per_page
        page_u         = all_users_list[start:end]
        txt = f"👤 <b>Barcha foydalanuvchilar ({total} ta)</b> | Sahifa {page+1}/{max(1,(total-1)//per_page+1)}\n\n"
        for u in page_u:
            uid     = u.get("user_id")
            uname   = f"@{u.get('username')}" if u.get("username") else "—"
            created = str(u.get("created_at", ""))[:16]
            icon    = "🆓" if uid in non_ids else "✅"
            txt += f"{icon} {u.get('full_name', '')} {uname}\n   🆔 {uid} | 📅 {created}\n"
        txt += "\n✅ Obunachi | 🆓 Bepul"
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_all_users_page_{page-1}"))
        if end < total:
            nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin_all_users_page_{page+1}"))
        keyboard = []
        if nav: keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("⬅️ Ortga", callback_data="open_admin")])
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_broadcast":
        if not await is_admin(user): return
        context.user_data["admin_broadcast"] = True
        await q.edit_message_text("📢 <b>Barchaga xabar</b>\n\nXabar yozing yoki rasm+matn yuboring:",
            parse_mode="HTML", reply_markup=home_menu())

    elif data == "admin_broadcast_nonsub":
        if not await is_admin(user): return
        context.user_data["admin_broadcast_nonsub"] = True
        await q.edit_message_text("📣 <b>Obuna bo'lmaganlarga xabar</b>\n\nXabar yozing:",
            parse_mode="HTML", reply_markup=home_menu())

    elif data == "admin_cancel_sub":
        if not await is_admin(user): return
        context.user_data["admin_cancel_sub"] = True
        await q.edit_message_text("❌ <b>Obunani bekor qilish</b>\n\nFoydalanuvchi ID ni yozing:",
            parse_mode="HTML", reply_markup=home_menu())

    elif data == "admin_promo":
        if not await is_admin(user): return
        context.user_data["admin_promo"] = True
        await q.edit_message_text(
            "🎟 <b>Promo kod yaratish</b>\n\nFormat: <code>KOD chegirma% max_foydalanish</code>\nMisol: <code>SUMMER30 30 100</code>",
            parse_mode="HTML", reply_markup=home_menu())

    elif data == "admin_promo_list":
        if not await is_admin(user): return
        promos = await get_all_promos()
        if not promos:
            await q.edit_message_text("Promo kodlar yo'q", reply_markup=admin_main_menu())
            return
        txt = "📋 <b>Promo Kodlar</b>\n\n"
        for p in promos[:10]:
            active = "✅" if p.get("is_active") else "❌"
            txt += f"{active} <code>{p['code']}</code> — {p['discount']}% | {p['used_count']}/{p['max_uses']}\n"
        await q.edit_message_text(txt, parse_mode="HTML", reply_markup=admin_main_menu())

    elif data == "admin_affiliates":
        if not await is_admin(user): return
        affiliates = await get_pending_affiliates()
        if not affiliates:
            await q.edit_message_text("Kutayotgan affiliate yo'q", reply_markup=admin_main_menu())
            return
        for aff in affiliates[:5]:
            await q.message.reply_text(
                f"🤝 Affiliate so'rovi:\n👤 {aff.get('username', '—')}\n🆔 {aff.get('user_id')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"aff_approve_{aff['user_id']}"),
                    InlineKeyboardButton("❌ Rad etish",  callback_data=f"aff_reject_{aff['user_id']}"),
                ]])
            )

    elif data.startswith("aff_approve_"):
        aff_uid = int(data.split("_")[2])
        await approve_affiliate(aff_uid)
        await q.edit_message_text("✅ Affiliate tasdiqlandi!")

    # ── APPROVE/REJECT ──
    elif data.startswith("approve_"):
        if not await is_admin(user): return
        parts    = data.split("_")
        sub_type = parts[1]
        sub_id   = int(parts[2])
        if sub_type == "channel":
            await approve_subscription(sub_id, 0)
        elif sub_type == "screener":
            await approve_screener_sub(sub_id, 0)
        elif sub_type == "premium":
            await approve_premium_sub(sub_id)
        await q.edit_message_text(f"✅ #{sub_id} tasdiqlandi!", reply_markup=admin_main_menu())

    elif data.startswith("reject_"):
        if not await is_admin(user): return
        parts    = data.split("_")
        sub_type = parts[1]
        sub_id   = int(parts[2])
        if sub_type == "channel":
            await reject_subscription(sub_id)
        elif sub_type == "screener":
            await reject_screener_sub(sub_id)
        elif sub_type == "premium":
            await reject_premium_sub(sub_id)
        await q.edit_message_text(f"❌ #{sub_id} rad etildi!", reply_markup=admin_main_menu())


# ===================== MATN HANDLER =====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    text  = (update.message.text or "").strip()
    udata = context.user_data

    if text in REPLY_SECTIONS:
        await show_section(update, context, REPLY_SECTIONS[text])
        return
    if udata.get("ai_mode"):
        await _handle_ai(update, context, text)
        return
    if udata.get("screener_mode"):
        await _handle_screener(update, context, text)
        return
    if udata.get("portfolio_watch"):
        await _handle_portfolio_add(update, context, text)
        return
    if udata.get("alert_input"):
        await _handle_alert_input(update, context, text)
        return
    if udata.get("promo_input"):
        await _handle_promo_input(update, context, text)
        return
    if udata.get("calc_mode"):
        await _handle_calculator(update, context, text)
        return
    if udata.get("admin_broadcast") and await is_admin(user):
        await _handle_broadcast(update, context, text, all_users=True)
        return
    if udata.get("admin_broadcast_nonsub") and await is_admin(user):
        await _handle_broadcast(update, context, text, all_users=False)
        return
    if udata.get("admin_promo") and await is_admin(user):
        await _handle_create_promo(update, context, text)
        return
    if udata.get("admin_cancel_sub") and await is_admin(user):
        await _handle_cancel_sub(update, context, text)
        return

    admin = await is_admin(user)
    await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=main_menu(is_admin=admin))


# ===================== MATN SUB-HANDLER LAR =====================

async def _handle_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user    = update.effective_user
    udata   = context.user_data
    history = udata.get("ai_history", [])
    can_use = await check_daily_limit(user.id, "ai", FREE_DAILY_AI_LIMIT)
    if not can_use and not await has_any_paid_sub(user.id):
        await update.message.reply_text(
            f"⏰ Kunlik AI limitingiz ({FREE_DAILY_AI_LIMIT} ta) tugadi!\n\nErtaga yangilanadi yoki obuna oling.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")]])
        )
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = ai_service.answer_question(text, history)
    if not response:
        response = "Hozircha AI xizmati mavjud emas. Tez orada ulanadi!"
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})
    if len(history) > 10:
        history = history[-10:]
    udata["ai_history"] = history
    udata["ai_mode"]    = True
    if not await has_any_paid_sub(user.id):
        await increment_daily_limit(user.id, "ai")
    await update.message.reply_text(response, parse_mode="HTML", reply_markup=home_menu())


async def _handle_screener(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user   = update.effective_user
    udata  = context.user_data
    mode   = udata.get("screener_mode")
    ticker = text.upper().strip()
    if not ticker or len(ticker) > 10:
        await update.message.reply_text("❌ Noto'g'ri ticker!")
        return
    is_free = mode == "free"
    if is_free:
        can_use = await check_daily_limit(user.id, "screener", FREE_DAILY_SCREENER_LIMIT)
        if not can_use:
            await update.message.reply_text(
                f"⏰ Kunlik screener limitingiz ({FREE_DAILY_SCREENER_LIMIT} ta) tugadi!\n\nErtaga yangilanadi yoki obuna oling.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Obuna olish", callback_data="sec_premium")]])
            )
            return
    await update.message.reply_text(f"🔍 <b>{ticker}</b> tahlil qilinmoqda...", parse_mode="HTML")
    from config import CRYPTO_TICKER_MAP
    is_crypto = ticker in CRYPTO_TICKER_MAP or mode == "crypto"
    if mode == "sentiment":
        result = sentiment_service.get_sentiment_report(ticker)
        udata.pop("screener_mode", None)
        await update.message.reply_text(result, parse_mode="HTML",
            reply_markup=section_back_menu("sec_onchain"), disable_web_page_preview=True)
        return
    if is_crypto:
        result = crypto_service.get_screener_result(ticker, is_free=is_free)
        ticker_type = "crypto"
    else:
        result = stock_service.get_screener_result(ticker, is_free=is_free)
        ticker_type = "stock"
    if not result:
        await update.message.reply_text(
            f"❌ <b>{ticker}</b> topilmadi.\n\nTicker to'g'ri ekanligini tekshiring.", parse_mode="HTML")
        return
    if not is_free and await has_any_paid_sub(user.id):
        ai_analysis = ai_service.analyze_screener(ticker, result, ticker_type)
        if ai_analysis:
            result += f"\n\n{ai_analysis}"
    if is_free:
        await increment_daily_limit(user.id, "screener")
        await update.message.reply_text(result, parse_mode="HTML",
            reply_markup=free_screener_result_menu(), disable_web_page_preview=True)
        public_channel = CHANNEL_IDS.get("public")
        if public_channel:
            try:
                await update.message.bot.send_message(
                    chat_id=public_channel,
                    text=result + f"\n\n📊 <i>@azia_quant_bot orqali tahlil qilindi</i>",
                    parse_mode="HTML", disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Kanalga yuborish xato: {e}")
    else:
        udata.pop("screener_mode", None)
        await update.message.reply_text(result, parse_mode="HTML",
            reply_markup=screener_action_menu(ticker, ticker_type), disable_web_page_preview=True)


async def _handle_portfolio_add(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user   = update.effective_user
    ticker = text.upper().strip()
    if not ticker or len(ticker) > 10:
        await update.message.reply_text("❌ Noto'g'ri ticker!")
        return
    from config import CRYPTO_TICKER_MAP
    t_type = "crypto" if ticker in CRYPTO_TICKER_MAP else "stock"
    await add_portfolio(user.id, ticker, t_type, 0, 0)
    context.user_data.pop("portfolio_watch", None)
    await update.message.reply_text(
        f"✅ <b>{ticker}</b> qabul qilindi!\n\nYana aktiv qo'shmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Ha",   callback_data="portfolio_watch_new"),
            InlineKeyboardButton("❌ Yo'q", callback_data="portfolio_watch_done"),
        ]])
    )


async def _handle_alert_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user  = update.effective_user
    udata = context.user_data
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Raqam kiriting!")
        return
    ticker    = udata.get("alert_ticker", "")
    t_type    = udata.get("alert_ticker_type", "crypto")
    a_type    = udata.get("alert_type", "price")
    condition = udata.get("alert_condition", "above")
    await save_alert(user.id, ticker, t_type, a_type, condition, value)
    for key in ["alert_ticker", "alert_ticker_type", "alert_type", "alert_condition", "alert_input"]:
        udata.pop(key, None)
    cond_txt = "dan yuqori" if condition == "above" else "dan past"
    await update.message.reply_text(
        f"✅ <b>Ogohlantirish o'rnatildi!</b>\n\n📌 {ticker} — {a_type} {value} {cond_txt} bo'lganda xabar beraman.",
        parse_mode="HTML", reply_markup=home_menu())


async def _handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user  = update.effective_user
    udata = context.user_data
    promo = await check_promo(text.strip().upper(), user.id)
    if not promo:
        await update.message.reply_text("❌ Promo kod topilmadi yoki allaqachon ishlatilgan!", reply_markup=home_menu())
        udata.pop("promo_input", None)
        return
    discount  = promo["discount"]
    price     = udata.get("promo_price", 0)
    new_price = int(price * (1 - discount / 100))
    await use_promo(text.strip().upper(), user.id)
    udata.pop("promo_input", None)
    await update.message.reply_text(
        f"🎉 <b>Promo kod qabul qilindi!</b>\n\n"
        f"💰 Yangi narx: <b>${new_price}</b> ({discount}% chegirma)\n\n"
        f"💳 Karta: <code>{CARD_NUMBER}</code>\n"
        f"👤 Egasi: <b>{CARD_OWNER}</b>\n\n"
        f"📸 To'lov chekini yuboring!",
        parse_mode="HTML", reply_markup=home_menu())


async def _handle_calculator(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    udata = context.user_data
    mode  = udata.get("calc_mode")
    try:
        nums = [float(x) for x in text.split()]
        if mode == "rr" and len(nums) >= 3:
            entry, stop, target = nums[0], nums[1], nums[2]
            risk   = abs(entry - stop)
            reward = abs(target - entry)
            rr     = reward / risk if risk > 0 else 0
            result = (f"⚖️ <b>Risk/Reward</b>\n\n• Kirish: ${entry:,.2f}\n• Stop: ${stop:,.2f}\n"
                      f"• Maqsad: ${target:,.2f}\n• Risk: ${risk:,.2f}\n• Reward: ${reward:,.2f}\n• R/R: 1:{rr:.2f}")
        elif mode == "position" and len(nums) >= 3:
            capital, risk_pct, stop_pct = nums[0], nums[1], nums[2]
            risk_amount = capital * risk_pct / 100
            position    = risk_amount / (stop_pct / 100)
            result = (f"📏 <b>Pozitsiya Hajmi</b>\n\n• Kapital: ${capital:,.2f}\n• Risk: {risk_pct}% = ${risk_amount:,.2f}\n"
                      f"• Stop: {stop_pct}%\n• Pozitsiya: ${position:,.2f}")
        elif mode == "compound" and len(nums) >= 3:
            capital, rate, months = nums[0], nums[1], int(nums[2])
            final  = capital * (1 + rate / 100) ** months
            profit = final - capital
            result = (f"📈 <b>Compound Foiz</b>\n\n• Boshlang'ich: ${capital:,.2f}\n• Oylik foiz: {rate}%\n"
                      f"• Muddat: {months} oy\n• Yakuniy: ${final:,.2f}\n• Foyda: ${profit:,.2f}")
        elif mode == "breakeven" and len(nums) >= 2:
            price, commission = nums[0], nums[1]
            buy_price  = price * (1 + commission / 100)
            sell_price = buy_price * (1 + commission / 100)
            result = (f"🎯 <b>Break-even</b>\n\n• Sotib olish: ${price:,.2f}\n• Komissiya: {commission}%\n"
                      f"• Break-even: ${sell_price:,.2f}")
        else:
            await update.message.reply_text("❌ Format noto'g'ri!")
            return
        udata.pop("calc_mode", None)
        await update.message.reply_text(result, parse_mode="HTML", reply_markup=section_back_menu("free_calc"))
    except (ValueError, ZeroDivisionError):
        await update.message.reply_text("❌ Raqamlarni to'g'ri kiriting!")


async def _handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, all_users: bool):
    if all_users:
        users_list = await get_all_users()
        context.user_data.pop("admin_broadcast", None)
    else:
        users_list = await get_non_subscribers()
        context.user_data.pop("admin_broadcast_nonsub", None)
    success = failed = 0
    await update.message.reply_text(f"📢 Yuborilmoqda... ({len(users_list)} ta)")
    for u in users_list:
        try:
            await context.bot.send_message(chat_id=u["user_id"], text=text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await update.message.reply_text(f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta", reply_markup=admin_main_menu())


async def _handle_create_promo(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        parts    = text.split()
        code     = parts[0].upper()
        discount = int(parts[1])
        max_uses = int(parts[2]) if len(parts) > 2 else 100
        await create_promo(code, discount, max_uses)
        context.user_data.pop("admin_promo", None)
        await update.message.reply_text(
            f"✅ Promo kod yaratildi!\n\nKod: <code>{code}</code>\nChegirma: {discount}%\nMax foydalanish: {max_uses}",
            parse_mode="HTML", reply_markup=admin_main_menu())
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: <code>KOD chegirma% max_foydalanish</code>", parse_mode="HTML")


async def _handle_cancel_sub(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        uid = int(text.strip())
        await cancel_user_subscription(uid)
        context.user_data.pop("admin_cancel_sub", None)
        await update.message.reply_text(f"✅ #{uid} obunasi bekor qilindi!", reply_markup=admin_main_menu())
    except ValueError:
        await update.message.reply_text("❌ ID raqam kiriting!")


# ===================== RASM HANDLER =====================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    udata = context.user_data

    if udata.get("admin_broadcast") and await is_admin(user):
        udata.pop("admin_broadcast", None)
        caption    = update.message.caption or ""
        users_list = await get_all_users()
        success = failed = 0
        photo = update.message.photo[-1].file_id
        await update.message.reply_text(f"📢 Yuborilmoqda... ({len(users_list)} ta)")
        for u in users_list:
            try:
                await context.bot.send_photo(chat_id=u["user_id"], photo=photo, caption=caption, parse_mode="HTML")
                success += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        await update.message.reply_text(f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta", reply_markup=admin_main_menu())
        return

    if udata.get("admin_broadcast_nonsub") and await is_admin(user):
        udata.pop("admin_broadcast_nonsub", None)
        caption = update.message.caption or ""
        nonsubs = await get_non_subscribers()
        success = failed = 0
        photo = update.message.photo[-1].file_id
        await update.message.reply_text(f"📣 Yuborilmoqda... ({len(nonsubs)} ta)")
        for u in nonsubs:
            try:
                await context.bot.send_photo(chat_id=u["user_id"], photo=photo, caption=caption, parse_mode="HTML")
                success += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        await update.message.reply_text(f"✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta", reply_markup=admin_main_menu())
        return

    if not udata.get("waiting_payment"):
        return

    sub_type       = udata.get("sub_type", "channel")
    sub_id         = udata.get("sub_id")
    scr_sub_id     = udata.get("scr_sub_id")
    premium_sub_id = udata.get("premium_sub_id")

    if sub_type == "channel" and not sub_id: return
    if sub_type == "onchain_screener" and not scr_sub_id: return
    if sub_type == "premium" and not premium_sub_id: return

    the_sub_id   = sub_id or scr_sub_id or premium_sub_id
    approve_type = sub_type

    for admin_id in set(ADMIN_IDS):
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=update.message.photo[-1].file_id,
                caption=(
                    f"💳 <b>TO'LOV CHEKI</b>\n\n"
                    f"👤 {user.full_name} (@{user.username or '—'})\n"
                    f"🆔 {user.id}\n"
                    f"📦 {SECTION_NAMES.get(sub_type, sub_type)}\n"
                    f"🔑 Sub ID: #{the_sub_id}"
                ),
                parse_mode="HTML",
                reply_markup=admin_approve_menu(the_sub_id, approve_type)
            )
        except Exception as e:
            logger.error(f"Admin ga yuborish xato: {e}")

    udata["waiting_payment"] = False
    await update.message.reply_text(
        "✅ <b>Chek qabul qilindi!</b>\n\nAdmin 24 soat ichida tasdiqlaydi.\nTasdiqlanganda xabar keladi!",
        parse_mode="HTML", reply_markup=home_menu())


# ===================== YORDAMCHI =====================

def _get_daily_lesson() -> str:
    lessons = [
        "📚 <b>Bugungi dars: RSI nima?</b>\n\nRSI (Relative Strength Index) — narx harakatining kuchini o'lchaydigan indikator.\n\n• RSI > 70 = Overbought (qimmat)\n• RSI < 30 = Oversold (arzon)\n• RSI = 50 = Neytral",
        "📚 <b>Bugungi dars: Support va Resistance</b>\n\nSupport — narx tushganda to'xtaydigan daraja.\nResistance — narx ko'tarilganda to'xtaydigan daraja.\n\n💡 Bu darajalar muhim qaror qabul qilish nuqtalari.",
        "📚 <b>Bugungi dars: Market Cap nima?</b>\n\nMarket Cap = Narx × Muomaladagi miqdor\n\n• Large Cap: $10B+\n• Mid Cap: $1B-$10B\n• Small Cap: $100M-$1B",
        "📚 <b>Bugungi dars: Stop Loss</b>\n\nStop Loss — zararni cheklash uchun belgilangan daraja.\n\n💡 Har doim kapitaling 2-3% dan ko'p yo'qotma!\nBu professional treyderlarning asosiy qoidasi.",
    ]
    import datetime
    day = datetime.date.today().timetuple().tm_yday
    return lessons[day % len(lessons)]


# ===================== PERIODIY VAZIFALAR =====================

async def check_expired_subs(context: ContextTypes.DEFAULT_TYPE):
    try:
        expired = await get_expired_subscriptions()
        for sub in expired:
            await mark_expired(sub["user_id"], sub["sub_type"])
            try:
                await context.bot.send_message(
                    chat_id=sub["user_id"],
                    text="⚠️ Obunangiz muddati tugadi!\n\n💎 Yangilash uchun bot ga o'ting.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Yangilash", callback_data="sec_signals")
                    ]])
                )
            except:
                pass
        expired_scr = await get_expired_screener_subs()
        for sub in expired_scr:
            await mark_screener_expired(sub["user_id"])
    except Exception as e:
        logger.error(f"Expired subs xato: {e}")


# ===================== MAIN =====================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    jq = app.job_queue
    jq.run_repeating(check_alerts,          interval=300,  first=60)
    jq.run_repeating(check_portfolio_news,  interval=1800, first=120)
    jq.run_repeating(check_expired_subs,    interval=3600, first=300)
    import datetime
    jq.run_daily(send_daily_briefing, time=datetime.time(hour=8, minute=0))
    logger.info("[SUCCESS] Azia Quant Bot ishga tushdi! 🚀")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
