# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import urllib.parse
import urllib.request
from typing import Optional


# Known benchmark fallbacks in case network/rate-limiting blocks an external call
FALLBACK_PRICES = {
    "AAPL": {"price": 225.00, "name": "Apple Inc.", "currency": "USD", "type": "stock"},
    "MSFT": {"price": 435.20, "name": "Microsoft Corp.", "currency": "USD", "type": "stock"},
    "NVDA": {"price": 128.50, "name": "NVIDIA Corp.", "currency": "USD", "type": "stock"},
    "GOOGL": {"price": 178.90, "name": "Alphabet Inc.", "currency": "USD", "type": "stock"},
    "VTI": {"price": 280.40, "name": "Vanguard Total Stock Market ETF", "currency": "USD", "type": "mutual_fund"},
    "VOO": {"price": 515.00, "name": "Vanguard S&P 500 ETF", "currency": "USD", "type": "mutual_fund"},
    "GLD": {"price": 242.10, "name": "SPDR Gold Shares ETF", "currency": "USD", "type": "gold"},
    "GOLD": {"price": 2650.00, "name": "Spot Gold (1 Troy Oz)", "currency": "USD", "type": "gold"},
    "BND": {"price": 74.50, "name": "Vanguard Total Bond Market ETF", "currency": "USD", "type": "debt"},
    "AGG": {"price": 99.80, "name": "iShares Core U.S. Aggregate Bond ETF", "currency": "USD", "type": "debt"},
}


def fetch_live_asset_quote(symbol: str, asset_type: Optional[str] = None) -> str:
    """Fetch live or recent market pricing and daily change for stocks, mutual funds/ETFs, gold, and debt instruments.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL', 'MSFT', 'VTI', 'GLD', 'GOLD', 'BND').
        asset_type: Optional asset type ('stock', 'mutual_fund', 'gold', 'debt').

    Returns:
        JSON string containing the current price, currency, daily change, and metadata.
    """
    clean_sym = symbol.strip().upper()
    lookup_sym = clean_sym

    # Handle spot gold alias
    if clean_sym in ("GOLD", "SPOT_GOLD", "XAU"):
        lookup_sym = "GC=F"

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(lookup_sym)}?interval=1d&range=1d"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode())
                results = raw_data.get("chart", {}).get("result")
                if results and len(results) > 0:
                    meta = results[0].get("meta", {})
                    current_price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose", current_price)
                    currency = meta.get("currency", "USD")
                    exchange = meta.get("exchangeName", "")
                    instrument = meta.get("instrumentType", asset_type or "EQUITY")

                    if current_price is not None:
                        change = round(current_price - prev_close, 2) if prev_close else 0.0
                        change_pct = round((change / prev_close) * 100, 2) if prev_close and prev_close != 0 else 0.0

                        return json.dumps({
                            "status": "success",
                            "symbol": clean_sym,
                            "current_price": round(float(current_price), 2),
                            "previous_close": round(float(prev_close), 2) if prev_close else None,
                            "change": change,
                            "change_percent": f"{change_pct:+.2f}%",
                            "currency": currency,
                            "exchange": exchange,
                            "instrument_type": instrument,
                            "source": "live_market_data"
                        }, indent=2)
    except Exception:
        pass

    # Resilient fallback
    if clean_sym in FALLBACK_PRICES:
        fallback = FALLBACK_PRICES[clean_sym]
        return json.dumps({
            "status": "success",
            "symbol": clean_sym,
            "name": fallback["name"],
            "current_price": fallback["price"],
            "currency": fallback["currency"],
            "instrument_type": fallback["type"],
            "source": "reference_benchmark"
        }, indent=2)

    return json.dumps({
        "status": "error",
        "symbol": clean_sym,
        "message": f"Unable to fetch market price for '{clean_sym}'. Please verify the symbol."
    }, indent=2)
