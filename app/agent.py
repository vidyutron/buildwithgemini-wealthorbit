# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types


from google.adk.code_executors import AgentEngineSandboxCodeExecutor

from app.currency_tools import convert_currency_or_rates
from app.firestore_tools import (
    get_holding_details,
    list_portfolio_holdings,
    record_portfolio_holding,
    update_asset_price,
)
from app.image_tools import generate_portfolio_milestone_image
from app.pricing_tools import fetch_live_asset_quote

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from app.a2ui_utils import a2ui_callback

MODEL = "gemini-3.6-flash"
AGENT_ENGINE_RESOURCE_NAME = (
    "projects/91004390898/locations/us-central1/reasoningEngines/2326574850711224320"
)

try:
    from a2ui.basic_catalog.provider import BasicCatalog
    from a2ui.schema.manager import A2uiSchemaManager

    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )

    instruction = schema_manager.generate_system_prompt(
        role_description=(
            "You are WealthOrbit, an intelligent Portfolio and Wealth Management AI Concierge. "
            "You help advisors and individual/household clients manage their asset portfolios across "
            "stocks, mutual funds, gold, and fixed income. "
            "You remember the client's stated risk tolerance, goals, household structure, and preferences across sessions. "
            "Use your portfolio tools to list holdings, inspect specific assets, record new investments, "
            "fetch live market quotes, update pricing, convert portfolio valuations across currencies, "
            "and generate visual milestone/goal achievement images. "
            "You have a secure Python code execution sandbox to perform precise financial mathematics, "
            "such as XIRR calculations, asset allocation percentages, portfolio variance, and rebalancing math. "
            "When answering questions, calculate accurate valuations and break down allocations by category or household member."
        ),
        workflow_description="Analyze the request and return structured UI when appropriate.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the URL an image tool returns after uploading "
            "to a public bucket). Set the Image url to that exact https link, for example "
            "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
            "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
            "headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )
except ImportError:
    from app.a2ui_prompt import INSTRUCTION as instruction

# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None

# Secure code execution sandbox on Agent Platform
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        list_portfolio_holdings,
        get_holding_details,
        record_portfolio_holding,
        update_asset_price,
        fetch_live_asset_quote,
        convert_currency_or_rates,
        generate_portfolio_milestone_image,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
