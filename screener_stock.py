#!/usr/bin/env python3
"""
Azia Quant Bot — Stock Screener Module
Yahoo Finance orqali aksiya tahlili
"""

import yfinance as yf
import requests
from config import CRYPTOPANIC_KEY


def _fmt_big(n):
    """Katta sonlarni formatlash"""
    if not n or n == 0:
        return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e12:
            return f"${n/1e12:.2f}T"
        if abs(n) >= 1e9:
            return f"${n/1e9:.2f}B"
        if abs(n) >= 1e6:
            return f"${n/1e6:.2f}M"
        return f"${n:,.2f}"
    except:
        return "N/A"


def _fmt_pct(n):
    """Foizni formatlash"""
    if n is None:
        return "N/A"
    try:
        return f"{float(n)*100:.1f}%"
    except:
        return "N/A"


def _calc_rsi(hist, period=14):
    """RSI hisoblash"""
    try:
        if hist is None or len(hist) < period + 1:
            return None
        delta = hist['Close'].diff()
        gain  = delta.where(delta > 0, 0).rolling(period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs    = gain / loss
        rsi   = 100 - (100 / (1 + rs.iloc[-1]))
        return float(rsi)
    except:
        return None


def _rsi_label(rsi):
    """RSI belgisi"""
    if rsi is None:
        return "N/A"
    if rsi < 30:
        return f"{rsi:.0f} — Oversold 🟢"
    elif rsi > 70:
        return f"{rsi:.0f} — Overbought 🔴"
    else:
        return f"{rsi:.0f} — Neytral ⚪"


def get_stock_news(ticker):
    """Aksiya yangiliklari"""
    try:
        stock     = yf.Ticker(ticker)
        news_list = stock.news
        if not news_list:
            return "• Yangilik topilmadi\n"
        news_txt = ""
        for n in news_list[:3]:
            title  = (n.get('title', '') or '')[:65]
            source = n.get('publisher', '')
            link   = n.get('link', '')
            if title and link:
                news_txt += f"• <a href='{link}'>{title}</a>\n  📰 {source}\n"
        return news_txt or "• Yangilik topilmadi\n"
    except:
        return "• Yangilik topilmadi\n"


def get_stock_data(ticker: str, is_free: bool = False) -> str:
    """
    Yahoo Finance dan aksiya ma'lumotlarini oladi.
    is_free=True bo'lsa — faqat asosiy ma'lumotlar
    """
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        if not info or not info.get('regularMarketPrice'):
            # Boshqa usul bilan tekshirish
            hist = stock.history(period="1d")
            if hist is None or hist.empty:
                return None

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
                f"💎 <b>To'liq tahlil uchun Onchain + Screener obunasi oling!</b>\n"
                f"• 15+ moliyaviy ko'rsatkich\n"
                f"• Insider tranzaksiyalar\n"
                f"• Choraklik hisobotlar\n"
                f"• AI tahlili (tez kunda)\n"
                f"• Islomiy muvofiqlik (tez kunda)"
            )

        # ── TO'LIQ VERSIYA ──

        # Fundamental
        pe_ratio   = info.get('trailingPE') or info.get('forwardPE') or 0
        pb_ratio   = info.get('priceToBook') or 0
        ps_ratio   = info.get('priceToSalesTrailing12Months') or 0
        ev_ebitda  = info.get('enterpriseToEbitda') or 0
        eps        = info.get('trailingEps') or 0
        eps_growth = info.get('earningsGrowth') or info.get('earningsQuarterlyGrowth') or 0
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

        # Texnik
        beta   = info.get('beta') or 0
        ma50   = info.get('fiftyDayAverage') or 0
        ma200  = info.get('twoHundredDayAverage') or 0

        # RSI
        hist    = stock.history(period="1mo")
        rsi_val = _calc_rsi(hist)
        rsi_txt = _rsi_label(rsi_val)

        # MA taqqoslash
        ma50_txt  = f"${ma50:,.2f} {'✅' if price > ma50  else '❌'}" if ma50  else "N/A"
        ma200_txt = f"${ma200:,.2f} {'✅' if price > ma200 else '❌'}" if ma200 else "N/A"

        # 52 hafta pozitsiyasi
        if w52_high and w52_low:
            w52_pos = ((price - w52_low) / (w52_high - w52_low)) * 100
            w52_pos_txt = f"{w52_pos:.0f}% (pastdan)"
        else:
            w52_pos_txt = "N/A"

        # Analyst
        rec          = (info.get('recommendationKey') or 'N/A').upper()
        target_price = info.get('targetMeanPrice') or 0
        analyst_num  = info.get('numberOfAnalystOpinions') or 0
        analyst_buy  = info.get('recommendationMean') or 0

        rec_map = {
            'STRONG_BUY': 'KUCHLI SOTIB OL 🟢',
            'BUY': 'SOTIB OL ✅',
            'HOLD': 'KUTING ⚪',
            'SELL': 'SOTMA ❌',
            'STRONG_SELL': 'KUCHLI SOTMA 🔴',
        }
        rec_txt = rec_map.get(rec, rec)

        # Institutional
        inst_hold   = info.get('institutionPercentHeld') or 0
        insider_hold = info.get('insiderPercentHeld') or 0
        short_pct   = info.get('shortPercentOfFloat') or 0

        # Insider tranzaksiyalar
        try:
            insider_df  = stock.insider_transactions
            insider_txt = ""
            if insider_df is not None and not insider_df.empty:
                for _, row in insider_df.head(3).iterrows():
                    # Turli ustun nomlarini tekshirish
                    iname = (
                        row.get('Name') or
                        row.get('Insider') or
                        row.get('name') or
                        "Noma'lum"
                    )
                    ishares = row.get('Shares') or row.get('shares') or 0
                    ival    = row.get('Value') or row.get('value') or 0
                    idate   = str(row.get('Start Date') or row.get('date') or '')[:10]
                    itype   = "SOTDI ⚠️" if float(ishares) < 0 else "OLDI ✅"
                    insider_txt += (
                        f"• {iname}: {abs(float(ishares)):,.0f} aksiya {itype}\n"
                        f"  {_fmt_big(abs(float(ival)))} | {idate}\n"
                    )
            if not insider_txt:
                insider_txt = "• Ma'lumot topilmadi\n"
        except Exception:
            insider_txt = "• Ma'lumot topilmadi\n"

        # Choraklik hisobotlar
        try:
            earnings_txt = ""
            # Yangi usul
            cal = stock.calendar
            next_earnings = ""
            if cal is not None and not cal.empty:
                if 'Earnings Date' in cal.index:
                    next_earnings = str(cal.loc['Earnings Date'].values[0])[:10]

            # Earnings history
            earn_hist = stock.earnings_history
            if earn_hist is not None and not earn_hist.empty:
                for _, row in earn_hist.head(4).iterrows():
                    date_str = str(row.name)[:10] if hasattr(row, 'name') else ''
                    eps_est  = row.get('epsEstimate') or row.get('EPS Estimate') or 0
                    eps_act  = row.get('epsActual') or row.get('Reported EPS') or 0
                    if eps_est and eps_act:
                        diff = ((float(eps_act) - float(eps_est)) / abs(float(eps_est))) * 100 if eps_est else 0
                        icon = "✅" if diff >= 0 else "❌"
                        earnings_txt += f"• {date_str}: ${float(eps_act):.2f} (kutilgan ${float(eps_est):.2f}) {diff:+.1f}% {icon}\n"

            if not earnings_txt:
                # earnings_dates dan olish
                earn_dates = stock.earnings_dates
                if earn_dates is not None and not earn_dates.empty:
                    for idx, row in earn_dates.head(4).iterrows():
                        date_str = str(idx)[:10]
                        eps_est  = row.get('EPS Estimate') or 0
                        eps_act  = row.get('Reported EPS') or 0
                        if eps_est and eps_act and float(eps_act) != 0:
                            diff = ((float(eps_act) - float(eps_est)) / abs(float(eps_est))) * 100 if eps_est else 0
                            icon = "✅" if diff >= 0 else "❌"
                            earnings_txt += f"• {date_str}: ${float(eps_act):.2f} (kutilgan ${float(eps_est):.2f}) {diff:+.1f}% {icon}\n"

            if not earnings_txt:
                earnings_txt = "• Ma'lumot topilmadi\n"

            if next_earnings:
                earnings_txt += f"\n📅 Keyingi hisobot: {next_earnings}"

        except Exception:
            earnings_txt = "• Ma'lumot topilmadi\n"

        # Yangiliklar
        news_txt = get_stock_news(ticker)

        # Short Interest
        short_txt = f"{short_pct*100:.1f}% ({'Yuqori ⚠️' if short_pct > 0.1 else 'Normal ✅'})" if short_pct else "N/A"

        result = (
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
            f"• Dividend: ${dividend:.2f} ({_fmt_pct(div_yield)})\n\n"

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
            f"• Fondlar ulushi: {_fmt_pct(inst_hold)}\n"
            f"• Insider ulushi: {_fmt_pct(insider_hold)}\n\n"

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
        return result

    except Exception as e:
        print(f"[ERROR] Stock data ({ticker}): {e}")
        return None
