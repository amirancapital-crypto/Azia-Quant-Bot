#!/usr/bin/env python3
"""
Azia Quant Bot — Config Module
Barcha sozlamalar va API kalitlar
"""

import os

# ===================== ENV LOADER =====================
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()

# ===================== BOT =====================
BOT_TOKEN      = os.environ.get("BOT_TOKEN", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "").lstrip("@")
CARD_NUMBER    = os.environ.get("CARD_NUMBER", "")
CARD_OWNER     = os.environ.get("CARD_OWNER", "")

# Admin IDlar
ADMIN_IDS = []
for x in os.environ.get("ADMIN_ID", "").split(","):
    try:
        ADMIN_IDS.append(int(x.strip()))
    except ValueError:
        pass

# ===================== KANALLAR =====================
CHANNEL_IDS = {
    "signals":    int(os.environ.get("CHANNEL_SIGNALS_ID",    0)),
    "onchain":    int(os.environ.get("CHANNEL_ONCHAIN_ID",    0)),
    "crypto_edu": int(os.environ.get("CHANNEL_CRYPTO_EDU_ID", 0)),
    "stock_edu":  int(os.environ.get("CHANNEL_STOCK_EDU_ID",  0)),
    "public":     int(os.environ.get("CHANNEL_PUBLIC_ID",     0)),  # Bepul screener post kanalasi
}

# ===================== NARXLAR ($) =====================
SIGNAL_PRICES = {6: 100, 12: 200, 0: 300}
SCREENER_PRICES = {6: 100, 12: 200, 0: 300}
CRYPTO_EDU_PRICE = 300
STOCK_EDU_PRICE  = 300
PREMIUM_PRICE    = 600

# ===================== LIMITLAR =====================
FREE_DAILY_SCREENER_LIMIT = 1    # Kuniga 1 ta screener
FREE_DAILY_AI_LIMIT       = 10   # Kuniga 10 ta AI so'rov

# ===================== REFERRAL =====================
REFERRAL_PERCENT  = 10
AFFILIATE_PERCENT = 20

# ===================== API KALITLAR =====================

# 🤖 AI
CLAUDE_API_KEY   = os.environ.get("CLAUDE_API_KEY", "")
CLAUDE_MODEL     = "claude-sonnet-4-20250514"

# 🪙 Crypto
COINGECKO_API_KEY      = os.environ.get("COINGECKO_API_KEY", "")
COINMARKETCAP_API_KEY  = os.environ.get("COINMARKETCAP_API_KEY", "")

# 📈 Aksiya
FINNHUB_API_KEY  = os.environ.get("FINNHUB_API_KEY", "")
POLYGON_API_KEY  = os.environ.get("POLYGON_API_KEY", "")

# 🔗 Onchain
GLASSNODE_API_KEY = os.environ.get("GLASSNODE_API_KEY", "")

# 😊 Sentiment
SANTIMENT_API_KEY  = os.environ.get("SANTIMENT_API_KEY", "")
LUNARCRUSH_API_KEY = os.environ.get("LUNARCRUSH_API_KEY", "")

# 📰 Yangiliklar
CRYPTOPANIC_API_KEY = os.environ.get("CRYPTOPANIC_API_KEY", "")

# 🕌 Shariat
ISLAMICLY_API_KEY   = os.environ.get("ISLAMICLY_API_KEY", "")
CRYPTOISLAM_API_KEY = os.environ.get("CRYPTOISLAM_API_KEY", "")

# 🏦 Makro (bepul)
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# ===================== API BASE URLlar =====================
COINGECKO_BASE    = "https://api.coingecko.com/api/v3"
COINMARKETCAP_BASE = "https://pro-api.coinmarketcap.com/v1"
FINNHUB_BASE      = "https://finnhub.io/api/v1"
POLYGON_BASE      = "https://api.polygon.io/v2"
GLASSNODE_BASE    = "https://api.glassnode.com/v1"
SANTIMENT_BASE    = "https://api.santiment.net/graphql"
CRYPTOPANIC_BASE  = "https://cryptopanic.com/api/v1"
ISLAMICLY_BASE    = "https://api.islamicly.com/v1"
DEFILLAMA_BASE    = "https://api.llama.fi"
ALTERNATIVE_BASE  = "https://api.alternative.me"
FRED_BASE         = "https://api.stlouisfed.org/fred"

# ===================== SEKCIYALAR =====================
SECTION_NAMES = {
    "signals":    "📊 Signals",
    "onchain":    "🔗 Onchain + Screener",
    "crypto_edu": "📚 Crypto Darslar",
    "stock_edu":  "📈 Fond Bozori Darslar",
    "screener":   "🔎 Screener",
    "premium":    "💎 Premium To'liq Paket",
}

CHANNEL_SECTIONS    = {"signals", "crypto_edu", "stock_edu"}

# ===================== CRYPTO TICKER MAP =====================
CRYPTO_TICKER_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "TRX": "tron", "TON": "the-open-network",
    "AVAX": "avalanche-2", "MATIC": "matic-network", "DOT": "polkadot",
    "LINK": "chainlink", "UNI": "uniswap", "ATOM": "cosmos",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "NEAR": "near",
    "APT": "aptos", "ARB": "arbitrum", "OP": "optimism",
    "SUI": "sui", "INJ": "injective-protocol", "PEPE": "pepe",
    "SHIB": "shiba-inu", "FIL": "filecoin", "ICP": "internet-computer",
    "VET": "vechain", "ALGO": "algorand", "XLM": "stellar",
    "HBAR": "hedera-hashgraph", "ETC": "ethereum-classic",
    "MKR": "maker", "AAVE": "aave", "STX": "blockstack",
    "IMX": "immutable-x", "WLD": "worldcoin-wld", "SEI": "sei-network",
    "TIA": "celestia", "JUP": "jupiter-exchange-solana",
    "BONK": "bonk", "WIF": "dogwifcoin", "FLOKI": "floki",
    "NOT": "notcoin",
}

# ===================== WELCOME MATNI =====================
WELCOME_TEXT = """🌟 <b>Assalomu alaykum!</b>

Azia Invest Quant botiga xush kelibsiz! 🤝

━━━━━━━━━━━━━━━━━━━━

🤖 <b>Bot haqida:</b>

Bu bot murakkab AI algoritmlari asosida
tuzilgan bo'lib foydalanuvchilarga:

📊 Moliyaviy bozorlar tahlili
📈 Aksiya va Crypto signallari
🔍 Professional Screener xizmati
🔗 Onchain tahlil ma'lumotlari
📚 Moliyaviy ta'lim materiallari
📋 Moliyaviy hisobotlar

...kabi xizmatlarni taqdim etadi.

━━━━━━━━━━━━━━━━━━━━

⚡ <b>Azia Quant Bot</b> — kuchli Kvant
algoritmlari asosida professional platforma.

━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Risk haqida ogohlantirish!</b>

🛡 Savdo intizomiga amal qiling
📉 Risk menejmentni unutmang
💡 Har bir qarorni mustaqil tahlil qiling
🚫 100% kapitalingizni bitta aktivga qo'ymang!

━━━━━━━━━━━━━━━━━━━━

📢 <b>Kanalimiz:</b> @azia_invest
📣 <b>Yangiliklar:</b> @aziaquantbot

━━━━━━━━━━━━━━━━━━━━

👇 Bo'limlardan birini tanlang:"""

# ===================== FAOL PROMOKODLAR =====================
ACTIVE_PROMO_CODES = [
    {
        "code": "HAYITLIK50",
        "discount": 50,
        "description": "Qurbon Hayiti munosabati bilan maxsus chegirma!",
        "emoji": "🎉",
        "valid_until": "2026-05-26 soat 23:59 gacha",
    }
]
