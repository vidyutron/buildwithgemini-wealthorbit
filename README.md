# WealthOrbit

**WealthOrbit** is an intelligent AI Wealth and Portfolio Concierge built with the Google Agent Development Kit (ADK) and Gemini 2.5 Flash on Vertex AI Agent Platform. It assists wealth advisors and client households in managing multi-asset portfolios across equities, mutual funds, spot commodities (gold), and fixed income, complete with automated valuations, cross-currency calculations, long-term memory, and A2UI display surfaces.

---

## What the Agent Does

WealthOrbit implements the following core capabilities wired to Google Cloud and external financial APIs:

1. **Long-Term Memory Bank (Vertex AI Agent Engine)**:
   - **Cross-Session Memory Preloading**: Powered by `PreloadMemoryTool()`, the agent automatically recalls client risk tolerance, household member structures, tax preferences, and advisor meeting notes across conversations.
   - **Automatic Memory Extraction**: An `after_agent_callback` (`generate_memories_callback`) extracts structured entities and updates the managed Memory Bank after each dialogue turn.

2. **Portfolio Data Management (Google Cloud Firestore)**:
   - Queries and persists real household holdings from the `portfolio_holdings` collection:
     - `list_portfolio_holdings`: Lists assets filtered by household, client, or asset class (`stock`, `mutual_fund`, `gold`, `debt`), calculating aggregate net worth.
     - `get_holding_details`: Retrieves cost basis, acquisition dates, purchase currency, and allocations for specific holdings.
     - `record_portfolio_holding`: Adds newly acquired assets or cash deposits to a household.
     - `update_asset_price`: Updates asset valuations in Firestore with latest market marks.

3. **Secure Financial Analytics Sandbox (`AgentEngineSandboxCodeExecutor`)**:
   - Executes Python in an isolated Vertex AI Agent Engine code sandbox.
   - Computes financial mathematics without hallucinations:
     - Portfolio rebalancing targets and percentage allocations.
     - Asset allocation drift analysis (e.g. comparing current weights to a 60/30/10 target).
     - Internal Rate of Return (XIRR) and weighted returns.

4. **Live Market Pricing & Foreign Exchange Tools**:
   - `fetch_live_asset_quote`: Fetches real-time price quotes, daily percentage changes, and market status for stocks, ETFs, debt benchmarks, and spot gold.
   - `convert_currency_or_rates`: Converts asset valuations and portfolio values across global currencies (e.g., USD to INR) via live FX exchange rates.

5. **Milestone Image Generation & Storage (Gemini + Google Cloud Storage)**:
   - `generate_portfolio_milestone_image`: Uses the `gemini-3.1-flash-lite-image` model in Vertex AI to generate visual badges and infographics for portfolio milestones.
   - Saves the generated image bytes directly into the ADK artifact store via `tool_context.save_artifact` and uploads to a public Cloud Storage bucket (`wealthorbit-media-*`), returning an embeddable HTTPS URL.

6. **Agent-to-User Interface (A2UI v0.8)**:
   - System prompts constructed with `A2uiSchemaManager` (v0.8 Basic Catalog).
   - An `after_model_callback` (`a2ui_callback`) catches A2UI JSON structures and emits them as `application/json+a2ui` data parts, rendering rich interactive cards, allocation progress bars, and holdings breakdowns.

7. **A2A Protocol & Conversational Web Frontend**:
   - A standalone FastAPI proxy communicates with the agent using the Agent-to-Agent (A2A) protocol (`a2a-sdk` 1.1+).
   - A responsive concierge frontend featuring dialogue avatars, profile switching, dark/light mode, and tailored prompt suggestions.

---

## Planned / Not Yet Implemented

The following features from the initial concept brief are planned for future milestones:
- *Consolidated Account Statement (CAS) PDF / Excel statement ingestion via Vertex AI Document AI / RAG Engine*.
- *Automated scheduled advisor alert notifications (e.g. Cloud Tasks / Cloud Scheduler trigger for portfolio drift >5%)*.

---

## Project Structure

```
wealthorbit/
├── app/
│   ├── agent.py                 # Root agent definition, callbacks, and tool registry
│   ├── a2ui_prompt.py           # Cached v0.8 A2UI system instructions & schemas
│   ├── a2ui_utils.py            # after_model_callback parser for A2UI data parts
│   ├── firestore_tools.py       # Firestore read/write tools for household portfolios
│   ├── image_tools.py           # gemini-3.1-flash-lite-image + Cloud Storage uploader
│   ├── pricing_tools.py         # Live quote lookups for stocks, ETFs, gold, and bonds
│   ├── currency_tools.py        # Real-time multi-currency FX conversion
│   └── fast_api_app.py          # FastAPI agent application wrapper
├── frontend/
│   ├── main.py                  # A2A FastAPI proxy server for the web interface
│   ├── requirements.txt         # Frontend server dependencies (fastapi, uvicorn, a2a-sdk)
│   └── static/
│       └── index.html           # Concierge UI with A2UI renderer, switcher, and theme
├── agents-cli-manifest.yaml     # Agent deployment manifest (Agent Runtime, us-central1)
├── deployment_metadata.json     # Agent Engine, Sandbox, and Memory Bank resource identifiers
├── pyproject.toml               # Python dependencies and build system configuration
└── README.md                    # Project documentation
```

---

## Getting Started Locally

### Prerequisites

1. **Python 3.10+** and [`uv`](https://docs.astral.sh/uv/) package manager.
2. **Google Cloud SDK (`gcloud`)** authenticated with active project and application default credentials:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project <YOUR_PROJECT_ID>
   ```

### 1. Install Dependencies

From the project root:

```bash
uv pip install -e .
```

### 2. Run the Local ADK Playground

To test the agent locally with Memory Bank integration:

```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri="agentengine://<YOUR_AGENT_ENGINE_ID>"
```

### 3. Run the Chat Frontend Locally

Open a separate terminal, navigate to `frontend/`, and launch the web server:

```bash
cd frontend
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8080

python main.py
```

Open a browser and navigate to the address output by the server (typically port 8080 on localhost) to interact with the concierge.

---

## Deployment Instructions

### Deploying the Agent to Agent Platform (Agent Runtime)

Deploy the ADK container to Google Cloud Agent Platform using `agents-cli`:

```bash
agents-cli deploy
```

Grant the deployed reasoning engine service account (`service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) the required IAM permissions:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud storage buckets add-iam-policy-binding gs://<IMAGE_BUCKET_NAME> \
  --member="serviceAccount:service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Deploying the Frontend to Cloud Run

From the `frontend/` directory, deploy the container to Cloud Run:

```bash
cd frontend
gcloud run deploy wealthorbit-frontend \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<DEPLOYED_AGENT_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```

Ensure the Cloud Run compute service account has `roles/aiplatform.user` to invoke the deployed agent:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
