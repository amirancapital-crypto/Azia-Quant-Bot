#!/usr/bin/env python3
"""
Azia Quant Bot — Keyboards Module
Barcha inline va reply tugmalar
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import SIGNAL_PRICES, SCREENER_PRICES, CRYPTO_EDU_PRICE, STOCK_EDU_PRICE, PREMIUM_PRICE


# ===================== REPLY KEYBOARD =====================

def main_reply_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Pastki asosiy menyu"""
    if is_admin:
        buttons = [[KeyboardButton("👨‍💼 Admin Panel")]]
    else:
        buttons = [
            [KeyboardButton("👤 Mening Obunalarim"), KeyboardButton("💼 Mening Portfelim")],
            [KeyboardButton("🎟 Promokodlar"),        KeyboardButton("👥 Referral")],
            [KeyboardButton("💬 Admin bilan aloqa")],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)


# ===================== BOSH MENYU =====================

def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Bosh menyu — asosiy bo'limlar"""
    buttons = [
        [InlineKeyboardButton("📊 Signals",               callback_data="sec_signals")],
        [InlineKeyboardButton("🔗 Onchain + Screener",    callback_data="sec_onchain")],
        [InlineKeyboardButton("📚 Crypto Darslar",        callback_data="sec_crypto_edu")],
        [InlineKeyboardButton("📈 Fond Bozori Darslar",   callback_data="sec_stock_edu")],
        [InlineKeyboardButton("🤖 Quant Trading",         callback_data="sec_quant")],
        [InlineKeyboardButton("🧠 AI Moliyaviy Yordamchi",callback_data="sec_ai")],
        [InlineKeyboardButton("💎 Premium To'liq Paket",  callback_data="sec_premium")],
        [InlineKeyboardButton("🆓 Bepul Xizmatlar",       callback_data="sec_free")],
    ]
    return InlineKeyboardMarkup(buttons)


# ===================== NAVIGATSIYA =====================

def back_menu() -> InlineKeyboardMarkup:
    """Ortga + Bosh menyu"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Ortga",      callback_data="back"),
        InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
    ]])


def home_menu() -> InlineKeyboardMarkup:
    """Faqat bosh menyu"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")
    ]])


def section_back_menu(back_cb: str) -> InlineKeyboardMarkup:
    """Ortga (belgilangan) + Bosh menyu"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Ortga",      callback_data=back_cb),
        InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
    ]])


# ===================== OBUNA =====================

def confirm_menu(section: str) -> InlineKeyboardMarkup:
    """Obuna tasdiqlash"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, obuna bo'laman", callback_data=f"confirm_{section}")],
        [InlineKeyboardButton("❌ Yo'q, ortga",        callback_data="back")],
    ])


def signals_duration_menu() -> InlineKeyboardMarkup:
    """Signals muddat tanlash"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗓 6 oylik — ${SIGNAL_PRICES[6]}",   callback_data="sig_dur_6")],
        [InlineKeyboardButton(f"📅 1 yillik — ${SIGNAL_PRICES[12]}", callback_data="sig_dur_12")],
        [InlineKeyboardButton(f"♾ Doimiy — ${SIGNAL_PRICES[0]}",    callback_data="sig_dur_0")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
    ])


def screener_duration_menu() -> InlineKeyboardMarkup:
    """Screener muddat tanlash"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗓 6 oylik — ${SCREENER_PRICES[6]}",   callback_data="scr_dur_6")],
        [InlineKeyboardButton(f"📅 1 yillik — ${SCREENER_PRICES[12]}", callback_data="scr_dur_12")],
        [InlineKeyboardButton(f"♾ Doimiy — ${SCREENER_PRICES[0]}",    callback_data="scr_dur_0")],
        [InlineKeyboardButton("⬅️ Ortga", callback_data="back")],
    ])


# ===================== SCREENER =====================

def screener_action_menu(ticker: str, ticker_type: str) -> InlineKeyboardMarkup:
    """Screener natijasidan keyin amallar"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Ogohlantirish",   callback_data=f"alert_set_{ticker_type}_{ticker}"),
            InlineKeyboardButton("📌 Portfelga",        callback_data=f"portfolio_add_{ticker_type}_{ticker}"),
        ],
        [
            InlineKeyboardButton("👁 Watchlist",        callback_data=f"watchlist_add_{ticker_type}_{ticker}"),
            InlineKeyboardButton("🔄 Yangilash",        callback_data=f"refresh_{ticker_type}_{ticker}"),
        ],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
    ])


def free_screener_result_menu() -> InlineKeyboardMarkup:
    """Bepul screener natijasi"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 To'liq tahlil uchun obuna oling", callback_data="sec_onchain")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back")],
    ])


# ===================== OGOHLANTIRISH =====================

def alert_type_menu(ticker: str, ticker_type: str) -> InlineKeyboardMarkup:
    """Ogohlantirish turi"""
    back_cb = f"use_{ticker_type}_screener"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Narx chegarasi",  callback_data=f"alert_price_{ticker_type}_{ticker}")],
        [InlineKeyboardButton("📊 RSI chegarasi",   callback_data=f"alert_rsi_{ticker_type}_{ticker}")],
        [InlineKeyboardButton("📈 Foiz o'zgarish",  callback_data=f"alert_pct_{ticker_type}_{ticker}")],
        [
            InlineKeyboardButton("⬅️ Ortga",      callback_data=back_cb),
            InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
        ],
    ])


def alert_condition_menu(alert_type: str, ticker: str, ticker_type: str) -> InlineKeyboardMarkup:
    """Ogohlantirish sharti"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Dan yuqori", callback_data=f"alert_cond_above_{alert_type}_{ticker_type}_{ticker}"),
            InlineKeyboardButton("📉 Dan past",   callback_data=f"alert_cond_below_{alert_type}_{ticker_type}_{ticker}"),
        ],
        [
            InlineKeyboardButton("⬅️ Ortga",      callback_data=f"alert_set_{ticker_type}_{ticker}"),
            InlineKeyboardButton("🏠 Bosh menyu", callback_data="back"),
        ],
    ])


def my_alerts_menu(alerts: list) -> InlineKeyboardMarkup:
    """Foydalanuvchi ogohlantirishlari"""
    buttons = []
    for alert in alerts:
        label = f"{alert['ticker']} — {alert['alert_type']} {alert['condition']} {alert['value']}"
        buttons.append([InlineKeyboardButton(
            f"❌ {label}", callback_data=f"alert_del_{alert['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Ortga", callback_data="back")])
    return InlineKeyboardMarkup(buttons)


# ===================== PORTFEL =====================

def portfolio_menu(items: list) -> InlineKeyboardMarkup:
    """Portfel ko'rinishi"""
    buttons = []
    for item in items:
        label = f"{item['ticker']} — {item['quantity']} dona"
        buttons.append([InlineKeyboardButton(
            f"🗑 {label}", callback_data=f"portfolio_del_{item['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Aktiv qo'shish", callback_data="portfolio_watch_new")])
    if items:
        buttons.append([InlineKeyboardButton("📰 Hozir yangiliklar", callback_data="portfolio_news")])
    buttons.append([InlineKeyboardButton("⬅️ Ortga", callback_data="portfolio_back")])
    return InlineKeyboardMarkup(buttons)


# ===================== REFERRAL =====================

def referral_menu() -> InlineKeyboardMarkup:
    """Referral menyu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Mening statistikam",  callback_data="ref_stats")],
        [InlineKeyboardButton("🤝 Affiliate bo'lish",   callback_data="ref_affiliate")],
        [InlineKeyboardButton("⬅️ Ortga",               callback_data="back")],
    ])


# ===================== BEPUL XIZMATLAR =====================

def free_menu() -> InlineKeyboardMarkup:
    """Bepul xizmatlar"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bozor holati",        callback_data="free_market")],
        [InlineKeyboardButton("🔍 Screener (1 ta/kun)", callback_data="free_screener")],
        [InlineKeyboardButton("📰 Yangiliklar",          callback_data="free_news")],
        [InlineKeyboardButton("🔢 Kalkulyatorlar",       callback_data="free_calc")],
        [InlineKeyboardButton("🏢 IPO Tracker",          callback_data="free_ipo")],
        [InlineKeyboardButton("📚 Kunlik Dars",          callback_data="free_lesson")],
        [InlineKeyboardButton("📅 Ekonomik Kalendar",    callback_data="free_calendar")],
        [InlineKeyboardButton("⬅️ Ortga",                callback_data="back")],
    ])


def calculator_menu() -> InlineKeyboardMarkup:
    """Kalkulyatorlar"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚖️ Risk/Reward",      callback_data="calc_rr")],
        [InlineKeyboardButton("📏 Pozitsiya hajmi",  callback_data="calc_position")],
        [InlineKeyboardButton("📈 Compound foiz",    callback_data="calc_compound")],
        [InlineKeyboardButton("🎯 Break-even",       callback_data="calc_breakeven")],
        [InlineKeyboardButton("⬅️ Ortga",            callback_data="free_calc_back")],
    ])


# ===================== ADMIN =====================

def admin_main_menu() -> InlineKeyboardMarkup:
    """Admin bosh menyu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika",                 callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Obunachlar ro'yxati",        callback_data="admin_users")],
        [InlineKeyboardButton("👤 Barcha foydalanuvchilar",    callback_data="admin_all_users")],
        [InlineKeyboardButton("📢 Barchaga xabar",             callback_data="admin_broadcast")],
        [InlineKeyboardButton("📣 Obuna bo'lmaganlarga xabar", callback_data="admin_broadcast_nonsub")],
        [InlineKeyboardButton("❌ Obunani bekor qilish",       callback_data="admin_cancel_sub")],
        [InlineKeyboardButton("🎟 Promo kod yaratish",         callback_data="admin_promo")],
        [InlineKeyboardButton("📋 Promo kodlar ro'yxati",      callback_data="admin_promo_list")],
        [InlineKeyboardButton("🤝 Affiliate tasdiqlash",       callback_data="admin_affiliates")],
        [InlineKeyboardButton("🏠 Bosh menyu",                 callback_data="back")],
    ])


def admin_approve_menu(sub_id: int, sub_type: str = "channel") -> InlineKeyboardMarkup:
    """Admin tasdiqlash"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{sub_type}_{sub_id}"),
        InlineKeyboardButton("❌ Rad etish",  callback_data=f"reject_{sub_type}_{sub_id}"),
    ]])
