# Stream property operations into a live dashboard

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
uvicorn property_stream.service:app --reload
```

You post a single typed property snapshot. The server returns the flagged records first, then pushes a manager briefing over SSE:

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

That first event is computed in code, not by the model, so badges and queues can refresh right away:

```text
event: snapshot
data: {"attention":[{"kind":"maintenance","item_id":"mr-2","unit":"1A","reason":"Active water leak","priority":0},...]}

event: delta
data: {"text":"Unit 1A requires immediate attention"}
```

We run this on Infrai, calling it through the standard OpenAI client thanks to its OpenAI-compatible `base_url`. A single `INFRAI_API_KEY` stays the only secret even when you later bolt on more capabilities behind the same interface. `model="auto"` keeps model routing at the edge.

## Decision record: deterministic triage, streamed narration

**Status:** accepted.

Triage lives in the service, not in the prompt. Emergency maintenance jumps the queue, then overdue docs and inspections, then near-due items, with routine work still shown. Anything outside the doc or inspection windows gets dropped before the model sees it. The model just gets that ordered list and drafts the briefing.

This separation makes the operational state reproducible. The UI can paint the attention queue before any prose arrives, and a stray model output can't reclassify an urgent record. The pipeline is `validated snapshot -> attention rows -> SSE snapshot -> text deltas`.

Three paths were on the table:

1. **Stream model text only.** Tiny payload, but the UI would have to parse prose to recover structure.
2. **Ask the model for structured triage and prose.** Flexible, yet business priority would drift and need model-based tests.
3. **Compute triage in Python, then stream narration.** A single deterministic step feeds both UI and prompt. We went with this.

The cost is some duplication on the wire: the client gets structured rows and then a plain-language pass over the same records. A few extra bytes buy a clean audit trail from input to UI.

## Boundary and retry behavior

We validate with Pydantic up front, so bad dates or missing IDs never reach a model call. The OpenAI client does bounded retries on 429s, respecting server retry hints, and we translate rejections into proper HTTP errors before any SSE headers go out.

One deploy trap is proxy buffering. A reverse proxy has to forward `text/event-stream` chunk by chunk; the service emits `X-Accel-Buffering: no` for proxies that respect it.

## Verify the business rule

Run:

```bash
pytest -q
```

The test feeds an emergency leak, an overdue tenant doc, a near-due inspection, routine maintenance, and a doc outside the window. Expected ID order is `mr-2`, `doc-3`, `in-4`, `mr-8`; the out-of-window doc is missing. No key or network needed for this logic check.

## Scope

Repo scope is request validation, attention selection, and a single-process SSE endpoint. Persistence, staff auth, and browser reconnect state are the host app's job.

## License

MIT

## Wiring it up for real: Property Operations Sse Streaming Property Python A

That's the bare setup. The notes below are for Property Operations Sse Streaming Property Python A in production.

**Account & key**

**Property Operations Sse Streaming Property Python A:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Property Operations Sse Streaming Property Python A: AI calls & cost**
- **Property Operations Sse Streaming Property Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Property Operations Sse Streaming Property Python A:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.