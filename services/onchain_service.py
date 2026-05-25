#!/usr/bin/env python3
"""
Azia Quant Bot — Onchain Service
Glassnode + DefiLlama + Alternative.me
"""

import logging
import requests
from typing import Optional, Dict, List

from config import (
    GLASSNODE_API_KEY, GLASSNODE_BASE,
    DEFILLAMA_BASE, ALTERNATIVE_BASE
)
from database import cache_get, cache_set

logger = logging.getLogger(__name__)


class OnchainService:
    """Onchain ma'lumotlari servisi"""

    def __init__(self):
        self.gn_key = GLASSNODE_API_KEY

    # ── Glassnode ────────────────────────────────────────────────

    def _gn_get(self, endpoint: str, params: dict = {}) -> Optional[Dict]:
        """Glassnode API dan ma'lumot olish"""
        try:
            if not self.gn_key:
                return None
            params["api_key"] = self.gn_key
            resp = requests.get(
                f"{GLASSNODE_BASE}/metrics/{endpoint}",
                params=params,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[-1] if isinstance(data, list) else data
        except Exception as e:
            logger.error(f"Glassnode xato: {e}")
        return None

    # ── DefiLlama ────────────────────────────────────────────────

    def _defi_get(self, endpoint: str) -> Optional[any]:
        """DefiLlama dan ma'lumot"""
        try:
            resp = requests.get(f"{DEFILLAMA_BASE}/{endpoint}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"DefiLlama xato: {e}")
        return None

    # ── Fear & Greed ─────────────────────────────────────────────

    def get_fear_greed(self) -> Optional[Dict]:
        """Fear & Greed Index"""
        cached = cache_get("fear_greed")
        if cached is not None:
            return cached
        try:
            resp = requests.get(f"{ALTERNATIVE_BASE}/fng/", timeout=8)
            if resp.status_code == 200:
                d = resp.json().get("data", [{}])[0]
                result = {
                    "value": int(d.get("value", 0)),
                    "label": d.get("value_classification", "")
                }
                cache_set("fear_greed", result, ttl=3600)
                return result
        except Exception as e:
            logger.error(f"Fear&Greed xato: {e}")
        return None

    # ── BTC Onchain ──────────────────────────────────────────────

    def get_btc_onchain(self) -> Dict:
        """BTC onchain ko'rsatkichlar"""
        cached = cache_get("btc_onchain")
        if cached is not None:
            return cached

        result = {}

        # SOPR
        sopr = self._gn_get("indicators/sopr", {"a": "BTC", "i": "24h"})
        if sopr:
            result["sopr"] = sopr.get("v")

        # MVRV
        mvrv = self._gn_get("market/mvrv", {"a": "BTC", "i": "24h"})
        if mvrv:
            result["mvrv"] = mvrv.get("v")

        # Exchange netflow
        netflow = self._gn_get("transactions/transfers_volume_to_exchanges_sum",
                                {"a": "BTC", "i": "24h"})
        if netflow:
            result["exchange_netflow"] = netflow.get("v")

        # Active addresses
        active = self._gn_get("addresses/active_count", {"a": "BTC", "i": "24h"})
        if active:
            result["active_addresses"] = active.get("v")

        if result:
            cache_set("btc_onchain", result, ttl=3600)
        return result

    # ── ETH Onchain ──────────────────────────────────────────────

    def get_eth_onchain(self) -> Dict:
        """ETH onchain ko'rsatkichlar"""
        cached = cache_get("eth_onchain")
        if cached is not None:
            return cached

        result = {}

        # Staking APY
        staking = self._gn_get("staking/volume_sum", {"a": "ETH", "i": "24h"})
        if staking:
            result["staking_volume"] = staking.get("v")

        # TVL (DefiLlama)
        chains = self._defi_get("v2/chains")
        if chains:
            eth_chain = next((c for c in chains if c.get("name") == "Ethereum"), None)
            if eth_chain:
                result["tvl"] = eth_chain.get("tvl", 0)

        if result:
            cache_set("eth_onchain", result, ttl=3600)
        return result

    # ── DeFi Stats ───────────────────────────────────────────────

    def get_defi_stats(self) -> Dict:
        """DeFi umumiy statistika"""
        cached = cache_get("defi_stats")
        if cached is not None:
            return cached

        result = {}

        # Total TVL
        try:
            resp = requests.get(f"{DEFILLAMA_BASE}/v2/globalCharts", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list):
                    last = data[-1]
                    if isinstance(last, list) and len(last) > 1:
                        result["total_tvl"] = last[1]
                    elif isinstance(last, dict):
                        result["total_tvl"] = last.get("totalLiquidityUSD", 0)
        except:
            pass

        # Agar TVL topilmasa chains dan yig'amiz
        if not result.get("total_tvl"):
            chains = self._defi_get("v2/chains")
            if chains:
                result["total_tvl"] = sum(c.get("tvl", 0) for c in chains)

        # Top protokollar
        protocols = self._defi_get("protocols")
        if protocols:
            result["top_protocols"] = [
                {"name": p["name"], "tvl": p.get("tvl", 0)}
                for p in sorted(protocols, key=lambda x: x.get("tvl", 0), reverse=True)[:5]
            ]

        if result:
            cache_set("defi_stats", result, ttl=3600)
        return result

    # ── SOL Onchain ──────────────────────────────────────────────

    def get_sol_onchain(self) -> Dict:
        """SOL onchain ma'lumotlari"""
        cached = cache_get("sol_onchain")
        if cached is not None:
            return cached

        result = {}

        # TPS (Solana RPC)
        try:
            resp = requests.post(
                "https://api.mainnet-beta.solana.com",
                json={"jsonrpc": "2.0", "id": 1,
                      "method": "getRecentPerformanceSamples", "params": [1]},
                timeout=8
            )
            if resp.status_code == 200:
                samples = resp.json().get("result", [])
                if samples:
                    sample = samples[0]
                    num_tx = sample.get("numTransactions", 0)
                    period = sample.get("samplePeriodSecs", 60)
                    result["tps"] = round(num_tx / period) if period > 0 else 0
        except:
            result["tps"] = 0

        # TVL (DefiLlama)
        chains = self._defi_get("v2/chains")
        if chains:
            sol_chain = next((c for c in chains if c.get("name") == "Solana"), None)
            if sol_chain:
                result["tvl"] = sol_chain.get("tvl", 0)

        if result:
            cache_set("sol_onchain", result, ttl=1800)
        return result

    # ── Funding Rate ─────────────────────────────────────────────

    def get_funding_rates(self) -> Dict:
        """Funding Rate (Bybit)"""
        cached = cache_get("funding_rates")
        if cached is not None:
            return cached

        result = {}
        symbols = [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"),
                   ("SOLUSDT", "SOL"), ("BNBUSDT", "BNB")]

        for symbol, name in symbols:
            try:
                resp = requests.get(
                    "https://api.bybit.com/v5/market/tickers",
                    params={"category": "linear", "symbol": symbol},
                    timeout=5
                )
                if resp.status_code == 200:
                    items = resp.json().get("result", {}).get("list", [])
                    if items:
                        rate = float(items[0].get("fundingRate", 0)) * 100
                        if rate > 0.05:
                            signal = "🔴 Yuqori"
                        elif rate < -0.05:
                            signal = "🟢 Manfiy"
                        else:
                            signal = "⚪ Normal"
                        result[name] = {"rate": rate, "signal": signal}
            except:
                continue

        if result:
            cache_set("funding_rates", result, ttl=1800)
        return result

    # ── To'liq Onchain hisobot ───────────────────────────────────

    def get_full_report(self) -> str:
        """To'liq onchain hisobot"""
        btc     = self.get_btc_onchain()
        eth     = self.get_eth_onchain()
        sol     = self.get_sol_onchain()
        defi    = self.get_defi_stats()
        fg      = self.get_fear_greed()
        funding = self.get_funding_rates()

        def fmt_big(n):
            if not n: return "N/A"
            if n >= 1e12: return f"${n/1e12:.2f}T"
            if n >= 1e9:  return f"${n/1e9:.2f}B"
            if n >= 1e6:  return f"${n/1e6:.2f}M"
            return f"${n:,.0f}"

        # Fear & Greed
        if fg:
            v = fg["value"]
            fg_icon = "🟢" if v <= 25 else "🔴" if v >= 75 else "🟡"
            fg_txt = f"{v}/100 — {fg['label']} {fg_icon}"
        else:
            fg_txt = "N/A"

        txt = "🔗 <b>ONCHAIN TAHLIL</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"

        # BTC
        txt += "₿ <b>BTC ONCHAIN:</b>\n"
        if btc.get("sopr"):
            sopr_icon = "🟢" if btc["sopr"] > 1 else "🔴"
            txt += f"• SOPR: {btc['sopr']:.3f} {sopr_icon}\n"
        if btc.get("mvrv"):
            mvrv_icon = "🔴" if btc["mvrv"] > 3 else "🟢" if btc["mvrv"] < 1 else "🟡"
            txt += f"• MVRV: {btc['mvrv']:.2f} {mvrv_icon}\n"
        if btc.get("exchange_netflow"):
            nf = btc["exchange_netflow"]
            nf_icon = "🔴" if nf > 0 else "🟢"
            txt += f"• Exchange Netflow: {fmt_big(abs(nf))} {nf_icon}\n"
        if btc.get("active_addresses"):
            txt += f"• Aktiv manzillar: {btc['active_addresses']:,.0f}\n"
        txt += "\n"

        # ETH
        txt += "Ξ <b>ETH ONCHAIN:</b>\n"
        if eth.get("tvl"):
            txt += f"• ETH TVL: {fmt_big(eth['tvl'])}\n"
        txt += "\n"

        # SOL
        txt += "◎ <b>SOL ONCHAIN:</b>\n"
        txt += f"• TPS: {sol.get('tps', 0):,.0f}\n"
        if sol.get("tvl"):
            txt += f"• SOL TVL: {fmt_big(sol['tvl'])}\n"
        txt += "\n"

        # DeFi
        txt += "🏦 <b>DEFI:</b>\n"
        txt += f"• Jami TVL: {fmt_big(defi.get('total_tvl', 0))}\n"
        if defi.get("top_protocols"):
            txt += "• Top protokollar:\n"
            for p in defi["top_protocols"][:3]:
                txt += f"  — {p['name']}: {fmt_big(p['tvl'])}\n"
        txt += "\n"

        # Fear & Greed
        txt += f"😱 <b>FEAR & GREED:</b>\n• {fg_txt}\n\n"

        # Funding Rate
        if funding:
            txt += "📊 <b>FUNDING RATE:</b>\n"
            for name, data in funding.items():
                txt += f"• {name}: {data['rate']:.4f}% — {data['signal']}\n"
            txt += "\n"
        else:
            txt += "📊 <b>FUNDING RATE:</b>\n• Ma'lumot olinmadi\n\n"

        txt += (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Bu ma'lumot faqat tahlil uchun."
        )

        return txt


# Global instance
onchain_service = OnchainService()
