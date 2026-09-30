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
from typing import Optional
from google.cloud import firestore

# CRITICAL: Hardcode project ID string to avoid project number issues on Agent Platform
FIRESTORE_PROJECT = "qwiklabs-gcp-03-c10839d3f1ce"
COLLECTION_NAME = "portfolio_holdings"


def _get_db():
    return firestore.Client(project=FIRESTORE_PROJECT)


def list_portfolio_holdings(
    household_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> str:
    """Retrieve portfolio holdings from Firestore with optional filtering.

    Args:
        household_id: Filter by household ID (e.g. 'hh_sharma').
        owner_id: Filter by owner/client ID (e.g. 'client_arjun').
        asset_type: Filter by asset category ('stock', 'mutual_fund', 'gold', 'debt').

    Returns:
        JSON string containing the list of portfolio holdings and aggregate total value.
    """
    try:
        db = _get_db()
        query = db.collection(COLLECTION_NAME)

        if household_id:
            query = query.where("household_id", "==", household_id)
        if owner_id:
            query = query.where("owner_id", "==", owner_id)
        if asset_type:
            query = query.where("asset_type", "==", asset_type)

        docs = query.stream()
        holdings = []
        total_portfolio_value = 0.0

        for doc in docs:
            data = doc.to_dict()
            qty = float(data.get("quantity", 0.0))
            price = float(data.get("current_price", 0.0))
            current_value = round(qty * price, 2)
            data["current_value"] = current_value
            total_portfolio_value += current_value
            holdings.append(data)

        result = {
            "count": len(holdings),
            "total_portfolio_value_usd": round(total_portfolio_value, 2),
            "holdings": holdings,
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to list holdings: {str(e)}"})


def get_holding_details(symbol_or_id: str) -> str:
    """Get detailed information for a specific asset holding by symbol or document ID.

    Args:
        symbol_or_id: The asset symbol (e.g., 'AAPL', 'GLD') or document ID (e.g., 'asset_aapl').

    Returns:
        JSON string with the holding details or an error message if not found.
    """
    try:
        db = _get_db()
        col = db.collection(COLLECTION_NAME)

        # Try doc id first
        doc = col.document(symbol_or_id).get()
        if doc.exists:
            data = doc.to_dict()
            qty = float(data.get("quantity", 0.0))
            price = float(data.get("current_price", 0.0))
            data["current_value"] = round(qty * price, 2)
            return json.dumps(data, indent=2)

        # Try querying by uppercase symbol
        docs = col.where("symbol", "==", symbol_or_id.upper()).limit(1).stream()
        for d in docs:
            data = d.to_dict()
            qty = float(data.get("quantity", 0.0))
            price = float(data.get("current_price", 0.0))
            data["current_value"] = round(qty * price, 2)
            return json.dumps(data, indent=2)

        return json.dumps({"error": f"Holding '{symbol_or_id}' not found."})
    except Exception as e:
        return json.dumps({"error": f"Failed to get holding: {str(e)}"})


def record_portfolio_holding(
    symbol: str,
    name: str,
    asset_type: str,
    category: str,
    quantity: float,
    avg_buy_price: float,
    current_price: float,
    owner_id: str,
    owner_name: str,
    household_id: str,
    currency: str = "USD",
    notes: str = "",
) -> str:
    """Record or update an asset holding in the client's portfolio.

    Args:
        symbol: Ticker symbol or code (e.g. 'NVDA', 'HDFC_GOLD', 'QQQ').
        name: Full asset or fund name (e.g. 'NVIDIA Corp', 'Invesco QQQ Trust').
        asset_type: Asset type ('stock', 'mutual_fund', 'gold', 'debt').
        category: High-level allocation category ('Equities', 'Commodities', 'Fixed Income').
        quantity: Units/shares held.
        avg_buy_price: Purchase price per unit.
        current_price: Current market price per unit.
        owner_id: Client ID (e.g. 'client_arjun').
        owner_name: Client name (e.g. 'Arjun Sharma').
        household_id: Household identifier (e.g. 'hh_sharma').
        currency: Currency code (default 'USD').
        notes: Context or notes regarding this holding.

    Returns:
        JSON string confirming the saved asset record.
    """
    try:
        db = _get_db()
        doc_id = f"asset_{symbol.lower()}"
        doc_ref = db.collection(COLLECTION_NAME).document(doc_id)

        holding_data = {
            "id": doc_id,
            "symbol": symbol.upper(),
            "name": name,
            "asset_type": asset_type.lower(),
            "category": category,
            "quantity": float(quantity),
            "avg_buy_price": float(avg_buy_price),
            "current_price": float(current_price),
            "currency": currency.upper(),
            "owner_id": owner_id,
            "owner_name": owner_name,
            "household_id": household_id,
            "notes": notes,
        }

        doc_ref.set(holding_data)
        current_value = round(float(quantity) * float(current_price), 2)
        gain_loss = round(current_value - (float(quantity) * float(avg_buy_price)), 2)

        return json.dumps(
            {
                "status": "success",
                "message": f"Recorded {symbol.upper()} successfully for {owner_name}.",
                "holding_id": doc_id,
                "current_value_usd": current_value,
                "unrealized_gain_loss_usd": gain_loss,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": f"Failed to record holding: {str(e)}"})


def update_asset_price(symbol: str, new_price: float) -> str:
    """Update current market price for an existing asset holding in Firestore.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL', 'GLD').
        new_price: Updated market price per unit.

    Returns:
        JSON string confirming updated valuation.
    """
    try:
        db = _get_db()
        col = db.collection(COLLECTION_NAME)
        docs = col.where("symbol", "==", symbol.upper()).stream()
        
        updated_count = 0
        for doc in docs:
            doc.reference.update({"current_price": float(new_price)})
            updated_count += 1

        if updated_count == 0:
            return json.dumps({"error": f"No holdings found with symbol '{symbol}' to update."})

        return json.dumps({
            "status": "success",
            "message": f"Updated price for {symbol.upper()} to ${new_price:.2f} across {updated_count} record(s)."
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to update asset price: {str(e)}"})
