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
import os
import urllib.request
from typing import Optional


def convert_currency_or_rates(
    base_currency: str = "USD",
    target_currency: Optional[str] = None,
    amount: float = 1.0,
) -> str:
    """Fetch live foreign exchange rates or convert portfolio values across currencies using ExchangeRate-API.

    Args:
        base_currency: Source currency ISO code (e.g., 'USD', 'EUR', 'INR', 'GBP'). Default is 'USD'.
        target_currency: Optional target currency to convert to (e.g. 'INR', 'EUR', 'GBP'). If omitted, returns key global rates.
        amount: Amount to convert (default 1.0).

    Returns:
        JSON string with real-time conversion results or exchange rates.
    """
    base = base_currency.strip().upper()
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")

    if api_key:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    else:
        url = f"https://open.er-api.com/v6/latest/{base}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (WealthOrbit-Agent/1.0)"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

            if data.get("result") != "success":
                return json.dumps({"error": f"Failed to retrieve rates for {base}: {data.get('error-type', 'unknown')}"})

            rates = data.get("rates", {})

            if target_currency:
                tgt = target_currency.strip().upper()
                if tgt not in rates:
                    return json.dumps({"error": f"Currency '{tgt}' not supported."})
                
                rate = rates[tgt]
                converted_value = round(amount * rate, 2)
                return json.dumps({
                    "status": "success",
                    "base_currency": base,
                    "target_currency": tgt,
                    "rate": rate,
                    "original_amount": amount,
                    "converted_amount": converted_value,
                    "last_updated": data.get("time_last_update_utc", ""),
                }, indent=2)

            # Return a curated basket of top global currencies useful for portfolios
            common_currencies = ["EUR", "GBP", "INR", "JPY", "CAD", "AUD", "SGD", "CHF", "CNY"]
            filtered_rates = {k: rates[k] for k in common_currencies if k in rates}
            return json.dumps({
                "status": "success",
                "base_currency": base,
                "rates": filtered_rates,
                "last_updated": data.get("time_last_update_utc", ""),
            }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Error fetching exchange rate data: {str(e)}"})
