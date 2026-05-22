#!/usr/bin/env python3
"""
Azia Quant Bot — Crypto Screener Module
CoinGecko, DefiLlama, Alternative.me orqali crypto tahlili
"""

import requests
from config import COINGECKO_BASE, ALTERNATIVE_BASE, DEFILLAMA_BASE, CRYPTO_TICKER_MAP


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


def get_coin_id(ticker: str) -> str:
    """Ticker dan CoinGecko ID ni topadi"""
    ticker_upper = ticker.upper()

    # Avval ro'yxatdan qidirish
    if ticker_upper in CRYPTO_TICKER_MAP:
        return CRYPTO_TICKER_MAP[ticker_upper]

    # CoinGecko search
    try:
        resp = requests.get(
            f"{COINGECKO_BASE}/search",
            params={"query": ticker},
            timeout=10
        )
        if resp.status_code == 200:
            data  = resp.json()
            coins = data.get('coins', [])
            if coins:
                # Eng mos natijani qaytarish
                for coin in coins[:5]:
                    if coin.get('symbol', '').upper() == ticker_upper:
                        return coin['id']
                return coins[0]['id']
    except:
        pass
    return ticker.lower()


def _calc_rsi_crypto(prices, period=14):
    """RSI hisoblash (narxlar ro'yxatidan)"""
    try:
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains  = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_g  = sum(gains[-period:]) / period
        avg_l  = sum(losses[-period:]) / period
        if avg_l == 0:
            return 100.0
        rs = avg_g / avg_l
        return 100 - (100 / (1 + rs))
    except:
        return None


def _rsi_label(rsi):
    if rsi is None:
        return "N/A"
    if rsi < 30:
        return f"{rsi:.0f} — Oversold 🟢"
    elif rsi > 70:
        return f"{rsi:.0f} — Overbought 🔴"
    else:
        return f"{rsi:.0f} — Neytral ⚪"


def get_fear_greed():
    """Fear & Greed Index"""
    try:
        resp = requests.get(f"{ALTERNATIVE_BASE}/fng/", timeout=10)
        if resp.status_code == 200:
            data  = resp.json()
            val   = int(data['data'][0]['value'])
            cls   = data['data'][0]['value_classification']
            if val >= 75:   icon = "🔴"
            elif val >= 55: icon = "🟡"
            elif val >= 35: icon = "🟠"
            else:           icon = "🟢"
            return f"{val}/100 — {cls} {icon}"
    except:
        pass
    return "N/A"


def get_crypto_news(coin_name: str):
    """Crypto yangiliklari"""
    try:
        # CoinGecko yangiliklari
        resp = requests.get(
            f"{COINGECKO_BASE}/news",
            timeout=10
        )
        if resp.status_code == 200:
            news_list = resp.json().get('data', [])
            news_txt  = ""
            count     = 0
            for n in news_list:
                if count >= 3:
                    break
                title = (n.get('title') or '')[:65]
                url   = n.get('url') or ''
                src   = n.get('news_site') or ''
                if coin_name.lower() in title.lower() and title and url:
                    news_txt += f"• <a href='{url}'>{title}</a>\n  📰 {src}\n"
                    count += 1
            if news_txt:
                return news_txt
    except:
        pass
    return "• Yangilik topilmadi\n"


def get_token_unlock(coin_id: str):
    """Token Unlock ma'lumotlari (DefiLlama)"""
    try:
        from datetime import datetime
        resp = requests.get(
            f"https://coins.llama.fi/chart/coingecko:{coin_id}",
            timeout=10
        )
        # DefiLlama emissions
        resp2 = requests.get(
            f"{DEFILLAMA_BASE}/emission/{coin_id}",
            timeout=10
        )
        if resp2.status_code == 200:
            data   = resp2.json()
            events = data.get('events', [])
            now_ts = datetime.now().timestamp()
            future = sorted(
                [e for e in events if e.get('timestamp', 0) > now_ts],
                key=lambda x: x.get('timestamp', 0)
            )
            unlock_txt = ""
            for ev in future[:3]:
                ev_date   = datetime.fromtimestamp(ev['timestamp']).strftime("%d-%b %Y")
                ev_amount = ev.get('noOfTokens', [0])
                ev_amount = ev_amount[0] if isinstance(ev_amount, list) else ev_amount
                ev_desc   = ev.get('description', 'Noma\'lum')
                days_left = int((ev['timestamp'] - now_ts) / 86400)
                unlock_txt += f"• {ev_date}: {ev_amount:,.0f} token\n  {ev_desc} ({days_left} kun)\n"
            return unlock_txt or "• BTC/ETH uchun unlock yo'q ✅\n"
        return "• Ma'lumot topilmadi\n"
    except:
        return "• Ma'lumot topilmadi\n"


def get_crypto_data(ticker: str, is_free: bool = False) -> str:
    """
    CoinGecko dan crypto ma'lumotlarini oladi.
    is_free=True bo'lsa — faqat asosiy ma'lumotlar
    """
    try:
        # Coin ID ni aniqlash
        coin_id = get_coin_id(ticker)

        # CoinGecko asosiy ma'lumotlar
        resp = requests.get(
            f"{COINGECKO_BASE}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers":      "false",
                "market_data":  "true",
                "community_data": "false",
                "developer_data": "false",
            },
            timeout=15
        )

        if resp.status_code == 429:
            return "⏳ CoinGecko so'rov limiti. Biroz kuting va qayta urinib ko'ring."

        if resp.status_code != 200:
            return None

        data   = resp.json()
        md     = data.get('market_data', {})
        name   = data.get('name', ticker)
        symbol = data.get('symbol', '').upper()

        price      = md.get('current_price', {}).get('usd') or 0
        change_24h = md.get('price_change_percentage_24h') or 0
        mkt_cap    = md.get('market_cap', {}).get('usd') or 0
        volume_24h = md.get('total_volume', {}).get('usd') or 0
        circ_sup   = md.get('circulating_supply') or 0
        max_sup    = md.get('max_supply')
        fdv        = md.get('fully_diluted_valuation', {}).get('usd') or 0
        ath        = md.get('ath', {}).get('usd') or 0
        atl        = md.get('atl', {}).get('usd') or 0
        ath_chg    = md.get('ath_change_percentage', {}).get('usd') or 0

        change_icon = "📈" if change_24h >= 0 else "📉"
        change_sign = "+" if change_24h >= 0 else ""

        # Mined foiz
        if max_sup and circ_sup:
            mined_pct = (circ_sup / max_sup) * 100
            mined_txt = f"{mined_pct:.1f}%"
        else:
            mined_txt = "Cheksiz (Max Supply yo'q)"

        # Market Cap toifasi
        if mkt_cap >= 10e9:
            cap_cat = "Large Cap 🔵"
        elif mkt_cap >= 1e9:
            cap_cat = "Mid Cap 🟡"
        elif mkt_cap >= 100e6:
            cap_cat = "Small Cap 🟠"
        else:
            cap_cat = "Micro Cap 🔴"

        # ── BEPUL VERSIYA ──
        if is_free:
            return (
                f"🔍 <b>{symbol} — {name}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ASOSIY:</b>\n"
                f"• Narx: <b>${price:,.4f}</b> ({change_sign}{change_24h:.2f}% {change_icon})\n"
                f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
                f"• Toifa: {cap_cat}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>To'liq tahlil uchun Onchain + Screener obunasi oling!</b>"
            )

        # ── TO'LIQ VERSIYA ──

        # RSI
        try:
            ohlc_resp = requests.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/ohlc",
                params={"vs_currency": "usd", "days": "30"},
                timeout=10
            )
            if ohlc_resp.status_code == 200:
                ohlc   = ohlc_resp.json()
                closes = [c[4] for c in ohlc]
                rsi_v  = _calc_rsi_crypto(closes)
                rsi_txt = _rsi_label(rsi_v)
            else:
                rsi_txt = "N/A"
        except:
            rsi_txt = "N/A"

        # MA50 va MA200
        try:
            hist_resp = requests.get(
                f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": "200"},
                timeout=10
            )
            if hist_resp.status_code == 200:
                prices  = [p[1] for p in hist_resp.json().get('prices', [])]
                ma50_v  = sum(prices[-50:]) / 50 if len(prices) >= 50 else None
                ma200_v = sum(prices[-200:]) / 200 if len(prices) >= 200 else None
                ma50_txt  = f"${ma50_v:,.4f} {'✅' if price > ma50_v else '❌'}" if ma50_v else "N/A"
                ma200_txt = f"${ma200_v:,.4f} {'✅' if price > ma200_v else '❌'}" if ma200_v else "N/A"
            else:
                ma50_txt = ma200_txt = "N/A"
        except:
            ma50_txt = ma200_txt = "N/A"

        # Fear & Greed
        fg_txt = get_fear_greed()

        # Token Unlock
        unlock_txt = get_token_unlock(coin_id)

        # Yangiliklar
        news_txt = get_crypto_news(name)

        # Developer faolligi
        dev_data = data.get('developer_data', {})
        github_stars = dev_data.get('stars') or 0
        github_commits = dev_data.get('commit_count_4_weeks') or 0
        if github_commits > 100:
            dev_txt = f"Juda faol 🟢 ({github_commits} commit/oy)"
        elif github_commits > 20:
            dev_txt = f"Faol ✅ ({github_commits} commit/oy)"
        elif github_commits > 0:
            dev_txt = f"O'rtacha ⚪ ({github_commits} commit/oy)"
        else:
            dev_txt = "Ma'lumot yo'q"

        result = (
            f"🔍 <b>{symbol} — {name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.4f}</b> ({change_sign}{change_24h:.2f}% {change_icon})\n"
            f"• Bozor kap: {_fmt_big(mkt_cap)} ({cap_cat})\n"
            f"• Hajm (24s): {_fmt_big(volume_24h)}\n\n"

            f"📦 <b>TA'MINOT:</b>\n"
            f"• Muomaladagi: {circ_sup:,.0f} {symbol}\n"
            f"• Max Supply: {f'{max_sup:,.0f}' if max_sup else 'Cheksiz'} {symbol}\n"
            f"• Qazilgan: {mined_txt}\n"
            f"• FDV: {_fmt_big(fdv)}\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI (14): {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• ATH: ${ath:,.4f} ({ath_chg:.1f}%)\n"
            f"• ATL: ${atl:,.8f}\n\n"

            f"🔓 <b>TOKEN UNLOCK:</b>\n"
            f"{unlock_txt}\n"

            f"💻 <b>DEVELOPER FAOLLIGI:</b>\n"
            f"• {dev_txt}\n\n"

            f"😨 <b>FEAR & GREED:</b>\n"
            f"• {fg_txt}\n\n"

            f"🐋 <b>WHALE TRACKER:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"📊 <b>FUNDING RATE:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"💥 <b>LIKVIDATSIYALAR:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"📰 <b>YANGILIKLAR:</b>\n"
            f"{news_txt}\n"

            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Bu ma'lumot faqat tahlil uchun.\n"
            f"Investitsiya qarori faqat sizga bog'liq.\n"
            f"Azia Invest javobgar emas."
        )
        return result

    except Exception as e:
        print(f"[ERROR] Crypto data ({ticker}): {e}")
        return None
