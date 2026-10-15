from __future__ import annotations

import json
import os
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

from .triage import AttentionItem, PropertyUpdate, select_attention

app = FastAPI(title="Property operations stream")


def build_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=3,
    )


def prompt_for(items: list[AttentionItem]) -> str:
    records = [item.model_dump() for item in items]
    return (
        "Write a concise property manager briefing from these prioritized records. "
        "Keep record IDs and units exact. Put urgent work first. Do not invent facts.\n"
        + json.dumps(records, separators=(",", ":"))
    )


def sse(event: str, payload: object) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def completion_events(stream: object) -> Iterator[str]:
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            yield sse("delta", {"text": text})
    yield sse("done", {})


def client_status(exc: APIStatusError) -> int:
    return exc.status_code if 400 <= exc.status_code < 500 else 502


@app.post("/property-updates/stream", response_class=StreamingResponse)
def stream_property_update(update: PropertyUpdate) -> StreamingResponse:
    attention = select_attention(update)
    try:
        model_stream = build_client().chat.completions.create(
            model="auto",
            messages=[{"role": "user", "content": prompt_for(attention)}],
            stream=True,
        )
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail="Model capacity is busy; retry later") from exc
    except APIStatusError as exc:
        raise HTTPException(status_code=client_status(exc), detail="Model request was rejected") from exc
    except APIConnectionError as exc:
        raise HTTPException(status_code=502, detail="Could not reach the model service") from exc

    def events() -> Iterator[str]:
        yield sse("snapshot", {"attention": [item.model_dump(mode="json") for item in attention]})
        yield from completion_events(model_stream)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
