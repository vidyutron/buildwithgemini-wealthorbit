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

import asyncio
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.memory.base_memory_service import MemoryEntry
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-03-c10839d3f1ce"
LOCATION = "us-central1"
MEMORY_BANK_ID = "2326574850711224320"

APP_NAME = "app"
USER_ID = "hh_sharma"

# Scenario 2: Household Structure, Roles & Beneficiaries
# Scenario 5: Advisor Context & Past Action Items
MEMORIES = [
    # Scenario 2
    "Household Members & Roles: Rahul Sharma is the primary household account manager. Spouse is Anita Sharma (has a conservative risk profile and focuses on debt/fixed-income funds). Daughter is Ananya Sharma, aged 10 (education target milestone in 2034).",
    "Asset Allocation & Household Beneficiary Rules: Vanguard index funds (VTI) and fixed-income assets (BND) are designated towards Ananya's college education fund. Gold ETF (GLD) is held as an emergency reserve for the entire household.",
    
    # Scenario 5
    "Advisor Context: Primary assigned wealth advisor is Priya Patel (WealthOrbit Senior Advisor). Regular portfolio review cadence is scheduled quarterly (March, June, September, December).",
    "Agreed Advisor Action Item: In the last quarterly consultation with advisor Priya, Rahul agreed to rebalance and trim AAPL equity holdings if AAPL exceeds 25% of total household equity allocation, shifting proceeds into BND fixed income."
]


async def seed_memories():
    service = VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )

    memory_entries = [
        MemoryEntry(
            content=types.Content(
                parts=[types.Part.from_text(text=mem)],
                role="user"
            )
        )
        for mem in MEMORIES
    ]

    print(f"Seeding {len(memory_entries)} memories for user '{USER_ID}' into Memory Bank {MEMORY_BANK_ID}...")
    await service.add_memory(
        app_name=APP_NAME,
        user_id=USER_ID,
        memories=memory_entries,
    )
    print("Memories successfully seeded!")

    # Verify search_memory
    print("\nVerifying memory retrieval for 'household members'...")
    search_res = await service.search_memory(
        app_name=APP_NAME,
        user_id=USER_ID,
        query="Who are the household members and what are their investment roles?",
    )
    print(f"Retrieved {len(search_res.memories)} memories for query 1:")
    for m in search_res.memories:
        print(f" - {m.content.parts[0].text if m.content and m.content.parts else m}")

    print("\nVerifying memory retrieval for 'advisor action items'...")
    search_res2 = await service.search_memory(
        app_name=APP_NAME,
        user_id=USER_ID,
        query="What is the advisor cadence and agreed action items for AAPL?",
    )
    print(f"Retrieved {len(search_res2.memories)} memories for query 2:")
    for m in search_res2.memories:
        print(f" - {m.content.parts[0].text if m.content and m.content.parts else m}")


if __name__ == "__main__":
    asyncio.run(seed_memories())
