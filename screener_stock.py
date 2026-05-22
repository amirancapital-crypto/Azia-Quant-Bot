#!/usr/bin/env python3
"""
Azia Quant Bot — Stock Screener Module
Yahoo Finance + FMP API orqali aksiya tahlili
"""

import yfinance as yf
import requests
import feedparser
from config import FMP_API_KEY, FMP_BASE


def _fmt_big(n):
    if not n or n == 0: return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12: return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:  return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:  return f"${n/1e6:.2f}M"
        return f"${n:,.2f}"
    except: return "N/A"


def _fmt_pct(n):
    if n is None: return "N/A"
    try: return f"{float(n)*100:.1f}%"
    except: return "N/A"


def _calc_rsi(hist, period=14):
    try:
        if hist is None or len(hist) < period + 1: return None
        delta = hist['Close'].diff()
        gain  = delta.where(delta > 0, 0).rolling(period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs    = gain / loss
        return float(100 - (100 / (1 + rs.iloc[-1])))
    except: return None


def _rsi_label(rsi):
    if rsi is None: return "N/A"
    if rsi < 30:  return f"{rsi:.0f} — Oversold 🟢"
    elif rsi > 70: return f"{rsi:.0f} — Overbought 🔴"
    else:          return f"{rsi:.0f} — Neytral ⚪"


def get_stock_news_rss(ticker, company_name):
    """RSS Feed orqali aksiya yangiliklari"""
    try:
        feeds = [
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
            f"https://www.investing.com/rss/news_25.rss",
        ]
        news_txt = ""
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            count = 0
            for entry in feed.entries[:5]:
                title = (entry.get('title') or '')[:65]
                link  = entry.get('link') or ''
                src   = entry.get('source', {}).get('title') or feed.feed.get('title', '')
                if title and link:
                    news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {src}\n"
                    count += 1
                    if count >= 2: break
            if news_txt: break

        if not news_txt:
            # Google News RSS
            query = f"{ticker} stock"
            gfeed = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en")
            count = 0
            for entry in gfeed.entries[:5]:
                title = (entry.get('title') or '')[:65]
                link  = entry.get('link') or ''
                if title and link:
                    news_txt += f"• <a href='{link}'>{title}</a>\n"
                    count += 1
                    if count >= 3: break

        return news_txt or "• Yangilik topilmadi\n"
    except Exception as e:
        print(f"[ERROR] Stock news RSS: {e}")
        return "• Yangilik topilmadi\n"


def get_fmp_institutional(ticker):
    """FMP API — Institutional Ownership"""
    try:
        url = f"{FMP_BASE}/institutional-holder/{ticker}?apikey={FMP_API_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None
        data = resp.json()
        if not data or not isinstance(data, list): return None

        total_shares = sum(h.get('shares', 0) for h in data)
        top_holders  = data[:5]
        return {
            'total_holders': len(data),
            'top_holders':   top_holders,
            'total_shares':  total_shares,
        }
    except Exception as e:
        print(f"[ERROR] FMP institutional: {e}")
        return None


def get_fmp_earnings(ticker):
    """FMP API — Choraklik hisobotlar"""
    try:
        url = f"{FMP_BASE}/earnings-surprises/{ticker}?apikey={FMP_API_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None
        data = resp.json()
        if not data or not isinstance(data, list): return None
        return data[:4]
    except Exception as e:
        print(f"[ERROR] FMP earnings: {e}")
        return None


def get_fmp_insider(ticker):
    """FMP API — Insider tranzaksiyalar"""
    try:
        url = f"{FMP_BASE}/insider-trading?symbol={ticker}&limit=5&apikey={FMP_API_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None
        data = resp.json()
        if not data or not isinstance(data, list): return None
        return data[:3]
    except Exception as e:
        print(f"[ERROR] FMP insider: {e}")
        return None


def get_fmp_next_earnings(ticker):
    """FMP API — Keyingi hisobot sanasi"""
    try:
        url = f"{FMP_BASE}/earning_calendar?symbol={ticker}&apikey={FMP_API_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200: return None
        data = resp.json()
        if not data: return None
        return data[0].get('date', '')
    except: return None


def get_stock_data(ticker: str, is_free: bool = False) -> str:
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        if not info or not (info.get('regularMarketPrice') or info.get('currentPrice')):
            hist = stock.history(period="1d")
            if hist is None or hist.empty: return None

        name     = info.get('longName') or info.get('shortName') or ticker
        price    = info.get('regularMarketPrice') or info.get('currentPrice') or 0
        change   = info.get('regularMarketChangePercent') or 0
        mkt_cap  = info.get('marketCap') or 0
        w52_high = info.get('fiftyTwoWeekHigh') or 0
        w52_low  = info.get('fiftyTwoWeekLow') or 0
        sector   = info.get('sector') or "N/A"
        exchange = info.get('exchange') or ""

        change_icon = "📈" if change >= 0 else "📉"
        change_sign = "+" if change >= 0 else ""

        # ── BEPUL VERSIYA ──
        if is_free:
            return (
                f"🔎 <b>{ticker.upper()} — {name}</b>\n"
                f"📍 {sector} | {exchange}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>ASOSIY:</b>\n"
                f"• Narx: <b>${price:,.2f}</b> ({change_sign}{change:.2f}% {change_icon})\n"
                f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
                f"• 52 hafta: ${w52_low:,.2f} — ${w52_high:,.2f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💎 <b>To'liq tahlil uchun obuna oling!</b>"
            )

        # ── TO'LIQ VERSIYA ──
        pe_ratio   = info.get('trailingPE') or 0
        pb_ratio   = info.get('priceToBook') or 0
        ps_ratio   = info.get('priceToSalesTrailing12Months') or 0
        ev_ebitda  = info.get('enterpriseToEbitda') or 0
        eps        = info.get('trailingEps') or 0
        eps_growth = info.get('earningsGrowth') or 0
        revenue    = info.get('totalRevenue') or 0
        net_income = info.get('netIncomeToCommon') or 0
        gross_m    = info.get('grossMargins') or 0
        net_m      = info.get('profitMargins') or 0
        roe        = info.get('returnOnEquity') or 0
        roa        = info.get('returnOnAssets') or 0
        debt_eq    = info.get('debtToEquity') or 0
        fcf        = info.get('freeCashflow') or 0
        dividend   = info.get('dividendRate') or 0
        div_yield  = info.get('dividendYield') or 0

        # Dividend yield to'g'ri foiz
        if div_yield > 1:
            div_yield = div_yield / 100

        beta   = info.get('beta') or 0
        ma50   = info.get('fiftyDayAverage') or 0
        ma200  = info.get('twoHundredDayAverage') or 0
        short_pct = info.get('shortPercentOfFloat') or 0

        # RSI
        hist    = stock.history(period="1mo")
        rsi_val = _calc_rsi(hist)
        rsi_txt = _rsi_label(rsi_val)

        ma50_txt  = f"${ma50:,.2f} {'✅' if price > ma50 else '❌'}"  if ma50 else "N/A"
        ma200_txt = f"${ma200:,.2f} {'✅' if price > ma200 else '❌'}" if ma200 else "N/A"

        if w52_high and w52_low and (w52_high - w52_low) > 0:
            w52_pos = ((price - w52_low) / (w52_high - w52_low)) * 100
            w52_pos_txt = f"{w52_pos:.0f}% (pastdan)"
        else:
            w52_pos_txt = "N/A"

        # Analyst
        rec          = (info.get('recommendationKey') or 'N/A').upper()
        target_price = info.get('targetMeanPrice') or 0
        analyst_num  = info.get('numberOfAnalystOpinions') or 0
        rec_map = {
            'STRONG_BUY': 'KUCHLI SOTIB OL 🟢',
            'BUY':        'SOTIB OL ✅',
            'HOLD':       'KUTING ⚪',
            'SELL':       'SOTMA ❌',
            'STRONG_SELL':'KUCHLI SOTMA 🔴',
        }
        rec_txt = rec_map.get(rec, rec)

        # ── FMP: Institutional ──
        inst_data = get_fmp_institutional(ticker)
        if inst_data and inst_data['top_holders']:
            inst_txt = f"• Jami institutlar: {inst_data['total_holders']} ta\n"
            for h in inst_data['top_holders'][:3]:
                hname   = h.get('holder', 'N/A')
                hshares = h.get('shares', 0)
                inst_txt += f"• {hname}: {hshares:,} aksiya\n"
        else:
            inst_pct  = info.get('institutionPercentHeld') or 0
            inst_txt  = f"• Fondlar ulushi: {inst_pct*100:.1f}%\n" if inst_pct else "• Ma'lumot topilmadi\n"

        # ── FMP: Insider ──
        fmp_insider = get_fmp_insider(ticker)
        if fmp_insider:
            insider_txt = ""
            for t in fmp_insider:
                iname  = t.get('reportingName') or t.get('transactionType') or 'N/A'
                itype  = t.get('transactionType') or ''
                ishares= abs(t.get('securitiesTransacted') or 0)
                ival   = abs(t.get('transactionPrice') or 0) * ishares
                idate  = (t.get('transactionDate') or '')[:10]
                icon   = "OLDI ✅" if 'P' in itype.upper() or 'BUY' in itype.upper() else "SOTDI ⚠️"
                insider_txt += f"• {iname}: {ishares:,.0f} aksiya {icon}\n  {_fmt_big(ival)} | {idate}\n"
        else:
            # yfinance fallback
            try:
                idf = stock.insider_transactions
                insider_txt = ""
                if idf is not None and not idf.empty:
                    for _, row in idf.head(3).iterrows():
                        iname   = row.get('Name') or row.get('Insider') or "Noma'lum"
                        ishares = row.get('Shares') or 0
                        ival    = row.get('Value') or 0
                        idate   = str(row.get('Start Date') or '')[:10]
                        icon    = "SOTDI ⚠️" if float(ishares) < 0 else "OLDI ✅"
                        insider_txt += f"• {iname}: {abs(float(ishares)):,.0f} aksiya {icon}\n  {_fmt_big(abs(float(ival)))} | {idate}\n"
                if not insider_txt:
                    insider_txt = "• Ma'lumot topilmadi\n"
            except:
                insider_txt = "• Ma'lumot topilmadi\n"

        # ── FMP: Choraklik hisobotlar ──
        fmp_earnings = get_fmp_earnings(ticker)
        if fmp_earnings:
            earnings_txt = ""
            for e in fmp_earnings[:4]:
                date_str = (e.get('date') or '')[:10]
                eps_est  = e.get('estimatedEps') or 0
                eps_act  = e.get('actualEarningResult') or 0
                if eps_est and eps_act:
                    diff = ((float(eps_act) - float(eps_est)) / abs(float(eps_est))) * 100 if eps_est else 0
                    icon = "✅" if diff >= 0 else "❌"
                    earnings_txt += f"• {date_str}: ${float(eps_act):.2f} (kutilgan ${float(eps_est):.2f}) {diff:+.1f}% {icon}\n"
        else:
            earnings_txt = "• Ma'lumot topilmadi\n"

        # Keyingi hisobot
        next_earn = get_fmp_next_earnings(ticker)
        if next_earn:
            earnings_txt += f"\n📅 Keyingi hisobot: {next_earn}"

        # ── Yangiliklar (RSS) ──
        news_txt = get_stock_news_rss(ticker, name)

        short_txt = f"{short_pct*100:.1f}% ({'Yuqori ⚠️' if short_pct > 0.1 else 'Normal ✅'})" if short_pct else "N/A"

        return (
            f"🔎 <b>{ticker.upper()} — {name}</b>\n"
            f"📍 {sector} | {exchange}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>ASOSIY:</b>\n"
            f"• Narx: <b>${price:,.2f}</b> ({change_sign}{change:.2f}% {change_icon})\n"
            f"• Bozor kap: {_fmt_big(mkt_cap)}\n"
            f"• 52 hafta: ${w52_low:,.2f} — ${w52_high:,.2f}\n"
            f"• 52 hafta pozitsiyasi: {w52_pos_txt}\n\n"

            f"📊 <b>FUNDAMENTAL:</b>\n"
            f"• P/E: {pe_ratio:.1f}\n"
            f"• P/B: {pb_ratio:.1f}\n"
            f"• P/S: {ps_ratio:.1f}\n"
            f"• EV/EBITDA: {ev_ebitda:.1f}\n"
            f"• EPS: ${eps:.2f} ({'+' if eps_growth >= 0 else ''}{eps_growth*100:.1f}%)\n"
            f"• Daromad: {_fmt_big(revenue)}\n"
            f"• Sof foyda: {_fmt_big(net_income)}\n"
            f"• Gross Margin: {_fmt_pct(gross_m)}\n"
            f"• Net Margin: {_fmt_pct(net_m)}\n"
            f"• ROE: {_fmt_pct(roe)}\n"
            f"• ROA: {_fmt_pct(roa)}\n"
            f"• Qarz/Kapital: {debt_eq:.2f}\n"
            f"• Free Cash Flow: {_fmt_big(fcf)}\n"
            f"• Dividend: ${dividend:.2f} ({div_yield*100:.2f}%)\n\n"

            f"📈 <b>TEXNIK:</b>\n"
            f"• RSI (14): {rsi_txt}\n"
            f"• MA50: {ma50_txt}\n"
            f"• MA200: {ma200_txt}\n"
            f"• Beta: {beta:.2f}\n"
            f"• Short Interest: {short_txt}\n\n"

            f"🏦 <b>ANALYST REYTINGI:</b>\n"
            f"• Xulosa: <b>{rec_txt}</b>\n"
            f"• Maqsad narx: ${target_price:,.2f}\n"
            f"• Analitiklar soni: {analyst_num}\n\n"

            f"🏛 <b>INSTITUTIONAL:</b>\n"
            f"{inst_txt}\n"

            f"👤 <b>INSIDER TRANZAKSIYALAR:</b>\n"
            f"{insider_txt}\n"

            f"📋 <b>CHORAKLIK HISOBOTLAR:</b>\n"
            f"{earnings_txt}\n\n"

            f"📰 <b>YANGILIKLAR:</b>\n"
            f"{news_txt}\n"

            f"🕌 <b>ISLOMIY MUVOFIQLIK:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"🤖 <b>AI TAHLILI:</b>\n"
            f"• Tez kunda qo'shiladi ⏳\n\n"

            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Bu tahlil faqat ma'lumot uchun.\n"
            f"Investitsiya qarori faqat sizga bog'liq.\n"
            f"Azia Invest javobgar emas."
        )

    except Exception as e:
        print(f"[ERROR] Stock data ({ticker}): {e}")
        return None
