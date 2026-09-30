#!/usr/bin/env python3
"""Seed Firestore with sample portfolio assets for WealthOrbit."""

from google.cloud import firestore

# CRITICAL: Hardcode project ID string to avoid project number issues on Agent Platform
FIRESTORE_PROJECT = "qwiklabs-gcp-03-c10839d3f1ce"

SEEDED_HOLDINGS = [
    {
        "id": "asset_aapl",
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_type": "stock",
        "category": "Equities",
        "quantity": 50.0,
        "avg_buy_price": 178.50,
        "current_price": 225.00,
        "currency": "USD",
        "owner_id": "client_arjun",
        "owner_name": "Arjun Sharma",
        "household_id": "hh_sharma",
        "notes": "Core tech equity holding in family growth portfolio"
    },
    {
        "id": "asset_vti",
        "symbol": "VTI",
        "name": "Vanguard Total Stock Market ETF",
        "asset_type": "mutual_fund",
        "category": "Equities",
        "quantity": 120.0,
        "avg_buy_price": 235.00,
        "current_price": 280.40,
        "currency": "USD",
        "owner_id": "client_arjun",
        "owner_name": "Arjun Sharma",
        "household_id": "hh_sharma",
        "notes": "Broad market index fund"
    },
    {
        "id": "asset_gld",
        "symbol": "GLD",
        "name": "SPDR Gold Shares ETF",
        "asset_type": "gold",
        "category": "Commodities",
        "quantity": 40.0,
        "avg_buy_price": 190.00,
        "current_price": 242.10,
        "currency": "USD",
        "owner_id": "client_priya",
        "owner_name": "Priya Sharma",
        "household_id": "hh_sharma",
        "notes": "Hedge against inflation / market downturns"
    },
    {
        "id": "asset_bnd",
        "symbol": "BND",
        "name": "Vanguard Total Bond Market ETF",
        "asset_type": "debt",
        "category": "Fixed Income",
        "quantity": 200.0,
        "avg_buy_price": 72.00,
        "current_price": 74.50,
        "currency": "USD",
        "owner_id": "client_priya",
        "owner_name": "Priya Sharma",
        "household_id": "hh_sharma",
        "notes": "Low risk debt allocation for capital preservation"
    },
    {
        "id": "asset_msft",
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "asset_type": "stock",
        "category": "Equities",
        "quantity": 30.0,
        "avg_buy_price": 380.00,
        "current_price": 435.20,
        "currency": "USD",
        "owner_id": "client_arjun",
        "owner_name": "Arjun Sharma",
        "household_id": "hh_sharma",
        "notes": "Cloud & AI enterprise exposure"
    }
]

def seed():
    print(f"Connecting to Firestore for project: '{FIRESTORE_PROJECT}'...")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    collection = db.collection("portfolio_holdings")
    
    print("Seeding initial holdings...")
    for item in SEEDED_HOLDINGS:
        doc_id = item["id"]
        collection.document(doc_id).set(item)
        total_val = item["quantity"] * item["current_price"]
        print(f"  ✓ Seeded {item['symbol']} ({item['asset_type']}) for {item['owner_name']}: ${total_val:,.2f}")

    print("\n✅ Successfully seeded 5 portfolio holdings in 'portfolio_holdings' collection!")

if __name__ == "__main__":
    seed()
