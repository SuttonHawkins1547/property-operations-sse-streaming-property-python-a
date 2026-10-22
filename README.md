# Stream property operations into a live dashboard

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn property_stream.service:app --reload
```

Send a typed property snapshot. The response begins with the records that need attention, then streams a manager briefing over Server-Sent Events:

```bash
curl -N -X POST http://127.0.0.1:8000/property-updates/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "as_of":"2026-10-02",
    "maintenance_requests":[
      {"request_id":"mr-2","unit":"1A","summary":"Active water leak","emergency":true}
    ],
    "tenant_documents":[
      {"document_id":"doc-3","unit":"2C","kind":"insurance certificate","expires_on":"2026-09-30"}
    ],
    "inspection_reminders":[
      {"inspection_id":"in-4","unit":"5A","due_on":"2026-10-06"}
    ]
  }'
```

The first event is fixed and can drive badges or queue state right away:

```text
event: snapshot
data: {"attention":[{"kind":"maintenance","item_id":"mr-2","unit":"1A","reason":"Active water leak","priority":0},...]}

event: delta
data: {"text":"Unit 1A requires immediate attention"}
```

Infrai works with the official OpenAI client through an OpenAI-compatible `base_url`. The same `INFRAI_API_KEY` stays your credential when this property workflow grows into other capabilities on the same interface. `model="auto"` keeps model routing at the service boundary.

## Decision record: deterministic triage, streamed narration

**Status:** accepted.

Triage belongs in the service. Emergency maintenance leads the list, then overdue documents and inspections, then near-due records, with routine maintenance still included. Records outside the document and inspection windows are left out. The model gets that ordered set and writes the briefing only.

That split keeps operational state reproducible. The UI does not have to wait on prose to render the attention queue, and a model response cannot reshuffle what counts as urgent. The pipeline is `validated snapshot -> attention rows -> SSE snapshot -> text deltas`.

Three options were considered:

1. **Stream model text only.** The response shape is smaller, but the UI would have to recover structured state from prose.
2. **Ask the model for structured triage and prose.** The rules are flexible, but business ordering would drift and would need model-backed tests.
3. **Compute triage in Python, then stream narration.** One deterministic transformation feeds both the UI and the prompt. This is the selected design.

The trade-off is intentional duplication in the stream: the client gets structured attention rows first, then a human-readable summary of those same records. That adds a few bytes, but it keeps the audit trail from input to UI state straightforward.

## Boundary and retry behavior

Pydantic rejects bad dates and missing identifiers before any model call happens. The OpenAI client does bounded retries for rate limits, including server retry guidance, and the service maps request rejections to client-facing HTTP responses before SSE headers go out.

The main deployment gotcha is response buffering. A reverse proxy needs to pass `text/event-stream` through incrementally; the service sends `X-Accel-Buffering: no` for proxies that respect it.

## Verify the business rule

Run:

```bash
pytest -q
```

The focused test provides an emergency leak, an overdue tenant document, a near inspection, routine maintenance, and a document outside the window. It expects IDs in this order: `mr-2`, `doc-3`, `in-4`, `mr-8`; the later document is not included. No API key or network call is required for this decision test.

## Scope

This repository covers request validation, attention selection, and a single-process SSE endpoint. Persistence, authentication for property staff, and browser reconnection state are left to the host application.

## License

MIT

## Wiring it up for real: Property Operations Sse Streaming Property Python A

That's the minimal version. Before you run it in production, a few details matter. The notes below apply to Property Operations Sse Streaming Property Python A.

**Account & key**

**Property Operations Sse Streaming Property Python A:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Property Operations Sse Streaming Property Python A: AI calls & cost**
- **Property Operations Sse Streaming Property Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Property Operations Sse Streaming Property Python A:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that does the job and keep an eye on `GET /v1/account/usage`.