#!/usr/bin/env python3
"""
Azia Quant Bot — Config Module
Barcha sozlamalar va konstantalar
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

# ===================== BOT SOZLAMALARI =====================
BOT_TOKEN      = os.environ.get("BOT_TOKEN", "8692951194:AAG-4O63hvg_CahVM9U-7J3wNd7FgffEGfQ")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "Kvantium_Trader").lstrip("@")
CARD_NUMBER    = os.environ.get("CARD_NUMBER", "9860 1201 3287 1324")
CARD_OWNER     = os.environ.get("CARD_OWNER", "G A")

# Admin IDlar (.env da vergul bilan yoziladi)
ADMIN_IDS = []
_admin_id_env = os.environ.get("ADMIN_ID", "")
if _admin_id_env:
    for x in _admin_id_env.split(","):
        try:
            ADMIN_IDS.append(int(x.strip()))
        except ValueError:
            pass

# ===================== KANAL IDlar =====================
CHANNEL_IDS = {
    "signals":    int(os.environ.get("CHANNEL_SIGNALS_ID",    -1003859590519)),
    "onchain":    int(os.environ.get("CHANNEL_ONCHAIN_ID",    -1003797469259)),
    "crypto_edu": int(os.environ.get("CHANNEL_CRYPTO_EDU_ID", -1003951825296)),
    "stock_edu":  int(os.environ.get("CHANNEL_STOCK_EDU_ID",  -1003745532785)),
}

# ===================== BO'LIM NOMLARI =====================
SECTION_NAMES = {
    "signals":    "📊 Signals",
    "onchain":    "🔗 Onchain + Screener",
    "crypto_edu": "📚 Crypto Darslar",
    "stock_edu":  "📈 Fond Bozori Darslar",
    "screener":   "🔎 Onchain + Aksiya + Crypto Screener",
    "premium":    "💎 Premium To'liq Paket",
}

# Kanal bo'limlari (havola yuboriladi)
CHANNEL_SECTIONS = {"signals", "crypto_edu", "stock_edu"}

# Onchain va Screener birgalikda
ONCHAIN_SCREENER_SECTION = "onchain"

# ===================== NARXLAR =====================

# Signals (kanal)
SIGNAL_PRICES = {
    6:  100,   # 6 oylik
    12: 200,   # 1 yillik
    0:  300,   # Doimiy
}

# Onchain + Aksiya Screener + Crypto Screener (birga)
SCREENER_PRICES = {
    6:  100,   # 6 oylik
    12: 200,   # 1 yillik
    0:  300,   # Doimiy
}

# Crypto Darslar
CRYPTO_EDU_PRICE = 300  # Doimiy

# Fond Bozori Darslar
STOCK_EDU_PRICE = 300   # Doimiy

# Premium paket (hammasi)
PREMIUM_PRICE = 600     # Doimiy

# ===================== REFERRAL =====================
REFERRAL_PERCENT  = 10  # Oddiy obunachi %
AFFILIATE_PERCENT = 20  # Blogger/Influencer %

# ===================== BEPUL LIMIT =====================
FREE_DAILY_LIMIT = 1    # Kuniga 1 ta bepul screener

# ===================== ONCHAIN FILTRLAR =====================
ONCHAIN_FILTERS = {
    "whale_usd":       10_000_000,  # $10M dan yuqori
    "btc_exchange":    5_000,       # 5000 BTC dan yuqori
    "eth_exchange":    50_000,      # 50,000 ETH dan yuqori
    "alt_whale_usd":   5_000_000,   # $5M dan yuqori (altcoinlar)
    "fear_greed_low":  20,          # 20 dan past
    "fear_greed_high": 80,          # 80 dan yuqori
    "liquidation_usd": 100_000_000, # $100M dan yuqori
    "funding_rate_low":  -0.05,     # -0.05% dan past
    "funding_rate_high":  0.05,     # +0.05% dan yuqori
}

# ===================== CRYPTO TICKER MAP =====================
# Mashhur coinlar uchun CoinGecko ID
CRYPTO_TICKER_MAP = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "BNB":   "binancecoin",
    "XRP":   "ripple",
    "ADA":   "cardano",
    "DOGE":  "dogecoin",
    "TRX":   "tron",
    "TON":   "the-open-network",
    "AVAX":  "avalanche-2",
    "MATIC": "matic-network",
    "DOT":   "polkadot",
    "LINK":  "chainlink",
    "UNI":   "uniswap",
    "ATOM":  "cosmos",
    "LTC":   "litecoin",
    "BCH":   "bitcoin-cash",
    "NEAR":  "near",
    "APT":   "aptos",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "SUI":   "sui",
    "INJ":   "injective-protocol",
    "PHB":   "phoenix-global",
    "PEPE":  "pepe",
    "SHIB":  "shiba-inu",
    "FIL":   "filecoin",
    "ICP":   "internet-computer",
    "VET":   "vechain",
    "ALGO":  "algorand",
    "XLM":   "stellar",
    "HBAR":  "hedera-hashgraph",
    "ETC":   "ethereum-classic",
    "MKR":   "maker",
    "AAVE":  "aave",
    "CRV":   "curve-dao-token",
    "SNX":   "synthetix-network-token",
    "COMP":  "compound-governance-token",
    "STX":   "blockstack",
    "IMX":   "immutable-x",
    "RNDR":  "render-token",
    "WLD":   "worldcoin-wld",
    "SEI":   "sei-network",
    "TIA":   "celestia",
    "PYTH":  "pyth-network",
    "JUP":   "jupiter-exchange-solana",
    "PENGU": "pudgy-penguins",
    "TRUMP": "maga",
    "BONK":  "bonk",
    "WIF":   "dogwifcoin",
    "FLOKI": "floki",
    "NOT":   "notcoin",
    "HMSTR": "hamster-kombat",
    "DOGS":  "dogs-2",
}

# ===================== API SOZLAMALARI =====================
COINGECKO_BASE    = "https://api.coingecko.com/api/v3"
BLOCKCHAIN_BASE   = "https://blockchain.info"
DEFILLAMA_BASE    = "https://api.llama.fi"
ALTERNATIVE_BASE  = "https://api.alternative.me"
BLOCKCHAIR_BASE   = "https://api.blockchair.com"
CRYPTOPANIC_BASE  = "https://cryptopanic.com/api/v1"
ETHERSCAN_BASE    = "https://api.etherscan.io/api"

# API Kalitlar (.env dan olinadi)
CRYPTOPANIC_KEY = os.environ.get("CRYPTOPANIC_KEY", "")
ETHERSCAN_KEY   = os.environ.get("ETHERSCAN_KEY", "")
CLAUDE_API_KEY    = os.environ.get("CLAUDE_API_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
OPENROUTER_KEY    = os.environ.get("OPENROUTER_API_KEY", "")
HALAL_API_KEY   = os.environ.get("HALAL_TERMINAL_KEY", "")
FMP_API_KEY     = os.environ.get("FMP_API_KEY", "oXP5gpgNVIZpzRyDSNXLoVwRnACXmptw")
FMP_BASE        = "https://financialmodelingprep.com/api/v3"

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

⚡ <b>Azia Quant Bot</b> — bu shunchaki
ma'lumotlar bazasi emas, balki kuchli
Kvant algoritmlari asosida Moliyaviy
bozorlarni tahlil qilish uchun
yaratilgan professional platforma.

━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Risk haqida ogohlantirish!</b>

Botning har qanday funksiyasidan
foydalanganingizda:

🛡 Savdo intizomiga amal qiling
📉 Risk menejmentni unutmang
💡 Har bir qarorni mustaqil tahlil qiling
🚫 Hech qachon 100% kapitalingizni
   bitta aktivga riskga qo'ymang!

━━━━━━━━━━━━━━━━━━━━

👇 Bo'limlardan birini tanlang:"""
