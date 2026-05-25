#!/usr/bin/env python3
"""
Azia Quant Bot — Onchain Module
Blockchain.info, Etherscan, DefiLlama orqali onchain ma'lumotlar
"""

import requests
import json
from datetime import datetime
from config import (
    BLOCKCHAIN_BASE, DEFILLAMA_BASE, ALTERNATIVE_BASE,
    BLOCKCHAIR_BASE, ETHERSCAN_BASE, ETHERSCAN_KEY,
    ONCHAIN_FILTERS, COINGECKO_BASE
)


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


# ===================== BTC ONCHAIN =====================

def get_btc_onchain():
    """BTC onchain ma'lumotlari (Blockchain.info)"""
    try:
        result = {}

        # BTC statistika
        resp = requests.get(f"{BLOCKCHAIN_BASE}/stats", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            result['hash_rate']      = data.get('hash_rate', 0) / 1e18  # EH/s
            result['difficulty']     = data.get('difficulty', 0)
            result['mempool_size']   = data.get('mempool_size', 0)
            result['n_tx']           = data.get('n_tx', 0)
            result['total_btc']      = data.get('totalbc', 0) / 1e8
            result['minutes_btw']    = data.get('minutes_between_blocks', 0)
            result['avg_fee']        = data.get('cost_per_transaction', 0)

        # BTC narx
        price_resp = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        )
        if price_resp.status_code == 200:
            result['price'] = price_resp.json().get('bitcoin', {}).get('usd', 0)

        return result
    except Exception as e:
        print(f"[ERROR] BTC onchain: {e}")
        return {}


def get_eth_onchain():
    """ETH onchain ma'lumotlari"""
    try:
        result = {}

        # Gas narxi (Etherscan yoki bepul endpoint)
        try:
            if ETHERSCAN_KEY:
                resp = requests.get(
                    ETHERSCAN_BASE,
                    params={
                        "module": "gastracker",
                        "action": "gasoracle",
                        "apikey": ETHERSCAN_KEY
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json().get('result', {})
                    result['gas_safe']    = data.get('SafeGasPrice', 'N/A')
                    result['gas_average'] = data.get('ProposeGasPrice', 'N/A')
                    result['gas_fast']    = data.get('FastGasPrice', 'N/A')
            else:
                # Bepul gas API
                resp = requests.get("https://api.ethgasstation.info/api/fee-estimate", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    result['gas_average'] = data.get('regular', {}).get('maxFee', 'N/A')
        except:
            result['gas_average'] = 'N/A'

        # ETH narx va ma'lumotlar
        price_resp = requests.get(
            f"{COINGECKO_BASE}/coins/ethereum",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
            },
            timeout=15
        )
        if price_resp.status_code == 200:
            eth_data  = price_resp.json()
            md        = eth_data.get('market_data', {})
            result['price']           = md.get('current_price', {}).get('usd', 0)
            result['staking_apy']     = 3.5  # Taxminiy
            result['total_staked']    = 32_000_000  # Taxminiy

        # DeFi TVL
        defi_resp = requests.get(f"{DEFILLAMA_BASE}/v2/chains", timeout=10)
        if defi_resp.status_code == 200:
            chains = defi_resp.json()
            eth_chain = next((c for c in chains if c.get('name') == 'Ethereum'), None)
            if eth_chain:
                result['tvl'] = eth_chain.get('tvl', 0)

        return result
    except Exception as e:
        print(f"[ERROR] ETH onchain: {e}")
        return {}


def get_sol_onchain():
    """SOL onchain ma'lumotlari"""
    try:
        result = {}

        # SOL TPS — Solana rasmiy RPC dan
        try:
            rpc_resp = requests.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1, "method": "getRecentPerformanceSamples", "params": [1]},
                timeout=10
            )
            if rpc_resp.status_code == 200:
                samples = rpc_resp.json().get('result', [])
                if samples:
                    sample = samples[0]
                    num_tx = sample.get('numTransactions', 0)
                    period = sample.get('samplePeriodSecs', 60)
                    result['tps'] = round(num_tx / period) if period > 0 else 0
        except:
            result['tps'] = 0

        # SOL narx
        price_resp = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": "solana", "vs_currencies": "usd"},
            timeout=10
        )
        if price_resp.status_code == 200:
            result['price'] = price_resp.json().get('solana', {}).get('usd', 0)

        # SOL DeFi TVL
        defi_resp = requests.get(f"{DEFILLAMA_BASE}/v2/chains", timeout=10)
        if defi_resp.status_code == 200:
            chains = defi_resp.json()
            sol_chain = next((c for c in chains if c.get('name') == 'Solana'), None)
            if sol_chain:
                result['tvl'] = sol_chain.get('tvl', 0)

        return result
    except Exception as e:
        print(f"[ERROR] SOL onchain: {e}")
        return {}


def get_global_market():
    """Umumiy bozor ma'lumotlari"""
    try:
        result = {}

        # CoinGecko global
        resp = requests.get(f"{COINGECKO_BASE}/global", timeout=10)
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            result['total_market_cap'] = data.get('total_market_cap', {}).get('usd', 0)
            result['total_volume']     = data.get('total_volume', {}).get('usd', 0)
            result['btc_dominance']    = data.get('market_cap_percentage', {}).get('btc', 0)
            result['eth_dominance']    = data.get('market_cap_percentage', {}).get('eth', 0)
            result['market_cap_change']= data.get('market_cap_change_percentage_24h_usd', 0)

        # Fear & Greed
        fg_resp = requests.get(f"{ALTERNATIVE_BASE}/fng/", timeout=10)
        if fg_resp.status_code == 200:
            fg_data = fg_resp.json()
            result['fear_greed']     = int(fg_data['data'][0]['value'])
            result['fear_greed_cls'] = fg_data['data'][0]['value_classification']

        return result
    except Exception as e:
        print(f"[ERROR] Global market: {e}")
        return {}


def get_defi_stats():
    """DeFi statistikasi"""
    try:
        result = {}

        # Total TVL
        resp = requests.get(f"{DEFILLAMA_BASE}/v2/globalCharts", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                last = data[-1]
                if isinstance(last, list) and len(last) > 1:
                    result['total_tvl'] = last[1]
                elif isinstance(last, dict):
                    result['total_tvl'] = last.get('totalLiquidityUSD', 0)

        # Agar hali ham yo'q bo'lsa — alohida endpoint
        if not result.get('total_tvl'):
            tvl_resp = requests.get(f"{DEFILLAMA_BASE}/v2/chains", timeout=10)
            if tvl_resp.status_code == 200:
                chains = tvl_resp.json()
                result['total_tvl'] = sum(c.get('tvl', 0) for c in chains)

        # Top protokollar
        proto_resp = requests.get(f"{DEFILLAMA_BASE}/protocols", timeout=10)
        if proto_resp.status_code == 200:
            protocols = proto_resp.json()[:5]
            result['top_protocols'] = [
                {
                    'name': p.get('name', ''),
                    'tvl':  p.get('tvl', 0),
                    'chain': p.get('chain', ''),
                }
                for p in protocols
            ]

        return result
    except Exception as e:
        print(f"[ERROR] DeFi stats: {e}")
        return {}


def format_onchain_report():
    """To'liq onchain hisobot formatlash"""
    try:
        btc    = get_btc_onchain()
        eth    = get_eth_onchain()
        sol    = get_sol_onchain()
        global_m = get_global_market()
        defi   = get_defi_stats()

        fg_val = global_m.get('fear_greed', 0)
        fg_cls = global_m.get('fear_greed_cls', 'N/A')
        if fg_val >= 75:   fg_icon = "🔴"
        elif fg_val >= 55: fg_icon = "🟡"
        elif fg_val >= 35: fg_icon = "🟠"
        else:              fg_icon = "🟢"

        mkt_chg = global_m.get('market_cap_change', 0)
        mkt_icon = "📈" if mkt_chg >= 0 else "📉"

        report = (
            f"🔗 <b>ONCHAIN TAHLIL</b>\n"
            f"🕐 {datetime.now().strftime('%d-%b %Y %H:%M')} UTC\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"🌍 <b>BOZOR HOLATI:</b>\n"
            f"• Jami bozor kap: {_fmt_big(global_m.get('total_market_cap', 0))}\n"
            f"  {'+' if mkt_chg >= 0 else ''}{mkt_chg:.1f}% (24s) {mkt_icon}\n"
            f"• BTC Dominance: {global_m.get('btc_dominance', 0):.1f}%\n"
            f"• ETH Dominance: {global_m.get('eth_dominance', 0):.1f}%\n"
            f"• 24s Hajm: {_fmt_big(global_m.get('total_volume', 0))}\n"
            f"• Fear & Greed: {fg_val}/100 — {fg_cls} {fg_icon}\n\n"

            f"₿ <b>BTC ONCHAIN:</b>\n"
            f"• Narx: ${btc.get('price', 0):,.0f}\n"
            f"• Hash Rate: {btc.get('hash_rate', 0):.0f} EH/s\n"
            f"• Mempool: {btc.get('mempool_size', 0):,} tx\n"
            f"• O'rtacha to'lov: ${btc.get('avg_fee', 0):.2f}\n"
            f"• Qazilgan: {btc.get('total_btc', 0):,.0f} BTC\n\n"

            f"⟠ <b>ETH ONCHAIN:</b>\n"
            f"• Narx: ${eth.get('price', 0):,.0f}\n"
            f"• Gas (o'rtacha): {eth.get('gas_average', 'N/A')} Gwei\n"
            f"• Staking APY: ~{eth.get('staking_apy', 0):.1f}%\n"
            f"• ETH TVL: {_fmt_big(eth.get('tvl', 0))}\n\n"

            f"◎ <b>SOL ONCHAIN:</b>\n"
            f"• Narx: ${sol.get('price', 0):,.2f}\n"
            f"• TPS: {sol.get('tps', 0):,.0f}\n"
            f"• SOL TVL: {_fmt_big(sol.get('tvl', 0))}\n\n"

            f"🏦 <b>DEFI:</b>\n"
            f"• Jami TVL: {_fmt_big(defi.get('total_tvl', 0))}\n"
        )

        # Top DeFi protokollar
        top_proto = defi.get('top_protocols', [])
        if top_proto:
            report += "• Top protokollar:\n"
            for p in top_proto[:3]:
                report += f"  — {p['name']}: {_fmt_big(p['tvl'])}\n"

        # 🐋 WHALE TRACKER
        report += "\n🐋 <b>WHALE TRACKER:</b>\n• Tez kunda qo'shiladi ⏳\n\n"

        # 📊 FUNDING RATE (Binance)
        try:
            import requests as req
            from config import BINANCE_API_KEY
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
            funding_txt = ""
            for symbol in symbols:
                resp = req.get(
                    "https://fapi.binance.com/fapi/v1/premiumIndex",
                    params={"symbol": symbol},
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rate = float(data.get('lastFundingRate', 0)) * 100
                    name = symbol.replace("USDT", "")
                    if rate > 0.05:
                        signal = "🔴 Yuqori (Short signal)"
                    elif rate < -0.05:
                        signal = "🟢 Manfiy (Long signal)"
                    else:
                        signal = "⚪ Normal"
                    funding_txt += f"  • {name}: {rate:.4f}% — {signal}\n"
            if funding_txt:
                report += f"📊 <b>FUNDING RATE:</b>\n{funding_txt}\n"
            else:
                report += "📊 <b>FUNDING RATE:</b>\n• Ma'lumot olinmadi\n\n"
        except:
            report += "📊 <b>FUNDING RATE:</b>\n• Tez kunda qo'shiladi ⏳\n\n"

        # 💥 LIKVIDATSIYALAR
        report += "💥 <b>LIKVIDATSIYALAR:</b>\n• Tez kunda qo'shiladi ⏳\n\n"

        report += (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ Bu ma'lumot faqat tahlil uchun."
        )

        return report

    except Exception as e:
        print(f"[ERROR] Onchain report: {e}")
        return "❌ Ma'lumot olishda xatolik. Qayta urinib ko'ring."


def check_whale_alert(data: dict) -> bool:
    """Whale alert filtri"""
    try:
        amount_usd = float(data.get('amount_usd', 0))
        return amount_usd >= ONCHAIN_FILTERS['whale_usd']
    except:
        return False


def check_exchange_flow(coin: str, amount: float) -> bool:
    """Exchange oqim filtri"""
    try:
        if coin.upper() == 'BTC':
            return abs(amount) >= ONCHAIN_FILTERS['btc_exchange']
        elif coin.upper() == 'ETH':
            return abs(amount) >= ONCHAIN_FILTERS['eth_exchange']
        else:
            return False
    except:
        return False


def format_market_status():
    """Bozor holati (bepul foydalanuvchilar uchun)"""
    try:
        global_m = get_global_market()
        btc_resp = requests.get(
            f"{COINGECKO_BASE}/simple/price",
            params={
                "ids": "bitcoin,ethereum,solana,binancecoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            },
            timeout=10
        )

        prices = {}
        if btc_resp.status_code == 200:
            prices = btc_resp.json()

        btc_price  = prices.get('bitcoin', {}).get('usd', 0)
        btc_chg    = prices.get('bitcoin', {}).get('usd_24h_change', 0)
        eth_price  = prices.get('ethereum', {}).get('usd', 0)
        eth_chg    = prices.get('ethereum', {}).get('usd_24h_change', 0)
        sol_price  = prices.get('solana', {}).get('usd', 0)
        sol_chg    = prices.get('solana', {}).get('usd_24h_change', 0)
        bnb_price  = prices.get('binancecoin', {}).get('usd', 0)
        bnb_chg    = prices.get('binancecoin', {}).get('usd_24h_change', 0)

        def coin_line(name, price, chg):
            icon = "📈" if chg >= 0 else "📉"
            sign = "+" if chg >= 0 else ""
            return f"• {name}: ${price:,.2f} ({sign}{chg:.2f}%) {icon}\n"

        fg_val = global_m.get('fear_greed', 0)
        fg_cls = global_m.get('fear_greed_cls', 'N/A')
        if fg_val >= 75:   fg_icon = "🔴 Ochko'zlik"
        elif fg_val >= 55: fg_icon = "🟡 Yuqori"
        elif fg_val >= 35: fg_icon = "🟠 Qo'rquv"
        else:              fg_icon = "🟢 Juda qo'rquv"

        report = (
            f"📊 <b>BOZOR HOLATI</b>\n"
            f"🕐 {datetime.now().strftime('%d-%b %Y %H:%M')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"

            f"💰 <b>NARXLAR:</b>\n"
            f"{coin_line('BTC', btc_price, btc_chg)}"
            f"{coin_line('ETH', eth_price, eth_chg)}"
            f"{coin_line('SOL', sol_price, sol_chg)}"
            f"{coin_line('BNB', bnb_price, bnb_chg)}\n"

            f"🌍 <b>BOZOR:</b>\n"
            f"• Jami kap: {_fmt_big(global_m.get('total_market_cap', 0))}\n"
            f"• BTC Dominance: {global_m.get('btc_dominance', 0):.1f}%\n\n"

            f"😨 <b>FEAR & GREED:</b>\n"
            f"• {fg_val}/100 — {fg_icon}\n"
        )
        return report

    except Exception as e:
        print(f"[ERROR] Market status: {e}")
        return "❌ Ma'lumot olishda xatolik."x
