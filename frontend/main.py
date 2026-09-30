"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import json
import logging
import os
import uuid

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.protobuf.json_format import MessageToDict
import httpx
from a2a.client import ClientConfig, create_client
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import PROTOCOL_VERSION_1_0, VERSION_HEADER, TransportProtocol
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/91004390898/locations/us-central1/reasoningEngines/5804479662948089856",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP passthrough.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(GoogleAuthRequest())
    return {
        "Authorization": f"Bearer {_creds.token}",
        VERSION_HEADER: PROTOCOL_VERSION_1_0,
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    logging.exception("Error in /chat proxy")
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}


def _extract_part(part: Part) -> list[dict]:
    """Turn an A2A response part into structured parts for the chat UI."""
    out: list[dict] = []
    if part.text:
        out.append({"kind": "text", "text": part.text})
    elif part.url:
        out.append({"kind": "text", "text": part.url})
    elif part.HasField("data"):
        data_dict = MessageToDict(part.data)
        if isinstance(data_dict, dict):
            if data_dict.get("metadata", {}).get("mimeType") == _A2UI_MIME:
                inner_data = data_dict.get("data")
                if inner_data:
                    out.append({"kind": "a2ui", "data": inner_data})
                else:
                    out.append({"kind": "a2ui", "data": data_dict})
            elif "beginRendering" in data_dict or "surfaceUpdate" in data_dict or "deleteSurface" in data_dict:
                out.append({"kind": "a2ui", "data": data_dict})
            else:
                out.append({"kind": "text", "text": json.dumps(data_dict, indent=2)})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    headers = _auth_headers()

    async with httpx.AsyncClient(headers=headers, timeout=120) as http_client:
        config = ClientConfig(
            httpx_client=http_client,
            supported_protocol_bindings=[
                TransportProtocol.JSONRPC,
                TransportProtocol.HTTP_JSON,
            ],
        )
        a2a_client = await create_client(A2A_BASE, config)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_USER,
            parts=[Part(text=message)],
            context_id=_contexts.get(user_id, ""),
        )

        async for chunk in a2a_client.send_message(SendMessageRequest(message=msg)):
            which = chunk.WhichOneof("payload")
            if which == "artifact_update":
                if chunk.artifact_update.context_id:
                    _contexts[user_id] = chunk.artifact_update.context_id
                for p in chunk.artifact_update.artifact.parts:
                    parts.extend(_extract_part(p))
            elif which == "task":
                if chunk.task.context_id:
                    _contexts[user_id] = chunk.task.context_id
                for artifact in chunk.task.artifacts:
                    for p in artifact.parts:
                        parts.extend(_extract_part(p))
            elif which == "message":
                for p in chunk.message.parts:
                    parts.extend(_extract_part(p))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))
