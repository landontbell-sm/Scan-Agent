# Chainlit cheatsheet

Grounded in what's actually installed in this repo: **chainlit 2.11.1** (see
`.chainlit/config.toml`'s `[meta] generated_by`). Chainlit ships two separate
customization surfaces — Python decorators/API (`app.py`) for behavior, and
`.chainlit/config.toml` + `public/` for appearance/branding. Most "customize
Chainlit" questions are one or the other; this sheet is split the same way.

## Running it

```bash
uv run chainlit run app.py -w        # dev server, auto-reload on file save
uv run chainlit run app.py --host 127.0.0.1 --port 8000   # pin host/port
```

`-w` (watch) is what you want during development — it's what `docs/` and
`README.md` already document for this project. Drop it for anything you'd
call "production."

## Lifecycle decorators (app.py)

These are the hooks Chainlit calls into; this app currently only uses the
first two.

| Decorator | Fires when |
|---|---|
| `@cl.on_chat_start` | A new chat session begins (used in `app.py` to send the welcome message) |
| `@cl.on_message` | The user sends a message (used in `app.py` for the whole search→extract→explain pipeline) |
| `@cl.on_chat_end` | The session ends (tab closed, navigated away) |
| `@cl.on_chat_resume` | A persisted thread is reopened (needs a data layer — see below) |
| `@cl.on_stop` | The user clicks the Stop button mid-response |
| `@cl.on_settings_update` | `cl.ChatSettings` widgets changed (see below) |
| `@cl.on_logout` / `@cl.password_auth_callback` / `@cl.oauth_callback` / `@cl.header_auth_callback` | Auth hooks — pick one auth strategy, not several |
| `@cl.on_audio_start` / `@cl.on_audio_chunk` / `@cl.on_audio_end` | Voice input, if `features.audio.enabled = true` |
| `@cl.on_mcp_connect` / `@cl.on_mcp_disconnect` | MCP client connections, if `features.mcp.enabled = true` |
| `@cl.on_app_startup` / `@cl.on_app_shutdown` | Process-level, not per-session (good place for warming a connection pool, not per-user state) |

Only one function per decorator — decorating two functions with
`@cl.on_message` silently means only the last one registered wins.

## Messages, Steps, and Elements

**`cl.Message`** — a chat bubble. `await cl.Message(content="...").send()`.
Update after sending with `msg.content = "..."; await msg.update()`. Stream
plain text token-by-token with `await msg.stream_token(tok)` then
`await msg.send()` once (don't call `.send()` first *and* stream — pick one).

**`cl.Step`** — this app's main addition this session. A collapsible
sub-trace with automatic elapsed-time display, for "here's what I'm doing"
visibility instead of a silent wait:

```python
async with cl.Step(name="Search", type="tool") as step:
    step.input = f"script_id({plugin_id})"
    result = await do_search()
    step.output = result  # shown when the step closes
```

`type` is one of `run | tool | llm | embedding | retrieval | rerank |
undefined` — purely cosmetic/icon selection, no behavioral difference.
`step.stream_token(token)` works exactly like `Message.stream_token` but
inside the step's own box — that's what streams the model's output live in
`utils/llm.py` → `app.py`'s `on_delta` callback in this app. A `Step` that
raises inside the `async with` block is marked failed in the UI automatically
— you don't need to catch-and-set `step.output` yourself just to show an
error state, though doing so gives a nicer message than a stack trace.

**Elements** — attach rich content to a message: `cl.Image`, `cl.Pdf`,
`cl.File`, `cl.Text`, `cl.Audio`, `cl.Video`, `cl.Plotly`, `cl.Pyplot`,
`cl.Dataframe`, `cl.CustomElement`. Pass via
`cl.Message(content="...", elements=[cl.Image(path="./chart.png", name="chart")])`.

**Actions** — clickable buttons on a message:

```python
@cl.action_callback("approve")
async def on_approve(action: cl.Action):
    await cl.Message(content="Approved.").send()

await cl.Message(
    content="Proceed?",
    actions=[cl.Action(name="approve", payload={}, label="Approve")],
).send()
```

**Asking the user something mid-flow** — `cl.AskUserMessage`,
`cl.AskFileMessage`, `cl.AskActionMessage`, `cl.AskElementMessage`. All block
until the user responds (or time out) and return `None` on timeout — always
check for that before using the result.

## Session state

`cl.user_session.set("key", value)` / `cl.user_session.get("key")` — a
per-connection dict, the idiomatic way to stash state across turns in the
same chat (a conversation history list, a loaded model, a user's chosen
mode). Nothing here needs it today since each plugin lookup is
self-contained, but it's the first thing to reach for once a feature needs
"remember something from the last message."

## Sync work in an async handler

`@cl.on_message` handlers are `async def`. Blocking calls (subprocess, file
I/O, a sync SDK) will freeze the whole server for every connected user if
called directly — that's exactly why `tools/search.py` and
`tools/extract.py` are wrapped:

```python
search_async = cl.make_async(plugin_search)   # runs plugin_search() in a thread pool
path = await search_async(plugin_id)
```

If a call is natively async (this app's `utils/llm.py`, via
`AsyncAnthropic`), await it directly — don't wrap it in `make_async`, that
would pointlessly bounce it through a thread.

## Chat settings (a form the user fills out once per session)

```python
from chainlit.input_widget import Select, Switch, Slider

@cl.on_chat_start
async def start():
    await cl.ChatSettings(
        [
            Select(id="model", label="Model", values=["fast", "thorough"], initial_index=0),
            Switch(id="verbose", label="Verbose", initial=False),
        ]
    ).send()

@cl.on_settings_update
async def on_settings(settings):
    cl.user_session.set("settings", settings)
```

## Chat profiles (pick a persona/mode at session start)

```python
@cl.set_chat_profiles
async def profiles():
    return [
        cl.ChatProfile(name="Quick", markdown_description="Fast, no citations"),
        cl.ChatProfile(name="Thorough", markdown_description="Slower, full source review"),
    ]
```

`cl.user_session.get("chat_profile")` reads back which one was picked.

## Persistence (threads, resume, auth)

None of this is wired up in this project (no `on_chat_resume`, no auth
callback, no `@cl.data_layer`) — everything here is in-memory per
session and disappears on reconnect. To persist chat history across
reconnects/logins you need **both** a data layer (`@cl.data_layer`,
typically backed by Postgres via the official `chainlit-datalayer` package or
a custom `BaseDataLayer` subclass) **and** an auth callback — Chainlit won't
persist anonymous sessions. This is a real architectural addition, not a
config flag; don't reach for it unless the tool actually needs
"come back tomorrow and see my old lookups."

## Appearance & config (`.chainlit/config.toml`)

This file already exists in the repo with the defaults commented out. Things
worth knowing:

- **`[UI] name`** — the assistant's display name in the header (currently
  `"Assistant"` — rename this for a SecurityMetrics-branded deployment).
- **`[UI] custom_css` / `custom_js`** — point at a file under `public/` to
  override styling or inject client-side behavior. `custom_css_attributes`
  lets you add e.g. `media="print"`.
- **`[UI] logo_file_url` / `default_avatar_file_url`** — swap the logo/avatar
  by URL instead of a local file.
- **`[UI] cot`** — Chain-of-Thought display mode: `"hidden"`, `"tool_call"`,
  or `"full"`. This controls whether `cl.Step` traces are visible at all —
  currently `"full"`, which is why the Search/Extract/Explain steps this
  session added actually render. Setting it to `"hidden"` would silently make
  all of that invisible again.
- **`[UI] default_theme`** — `"dark"` or `"light"` default.
- **`[project] user_env`** — env vars the *user* must supply per-session
  (prompted in the UI) rather than ones the server reads from `.env`. Not
  what `PLUGINS_DIR`/`ANTHROPIC_API_KEY` are — those are server-side and
  loaded via `python-dotenv` in each module, independent of Chainlit.
- **`[features.spontaneous_file_upload]`** — lets users drag-and-drop files
  into the chat; `on_message`'s `message.elements` then carries them.
- **`[features] unsafe_allow_html`** — off by default for a reason (XSS via
  rendered Markdown/HTML) — don't flip this on to solve a formatting problem;
  find a Markdown-safe way instead.

`chainlit.md` (project root) is the welcome-screen content, per its own
header comment — empty file means no welcome screen at all, independent of
whatever `@cl.on_chat_start` sends as the first message.

## The wire protocol, if you ever need to debug below the SDK

Chainlit's browser client talks Socket.IO at `/ws/socket.io`. Worth knowing
this exists if `cl.Step`/`cl.Message` ever seem to not be reaching the UI and
you want to confirm what the server is actually emitting, independent of
frontend rendering:

| Client → server | Server → client |
|---|---|
| `client_message` (send a chat message) | `new_message` (a message/step was created) |
| `stop` (cancel the run) | `update_message` (a message/step was updated — this is how `Step`/`Message` edits after `.send()` propagate) |
| `edit_message` | `stream_token` (`{id, token, isSequence, isInput}` — what `Step.stream_token`/`Message.stream_token` actually emit) |
| `chat_settings_change` | `task_start` / `task_end` (the "agent is working" indicator wrapping a whole `on_message` run) |

This is implementation detail, not a supported integration surface — reach
for the Python API above for anything real. It's here because it's the
fastest way to prove *"is my step/stream actually being sent"* independent of
whatever the frontend does with it (a `python-socketio` `Client()` connecting
with `transports=["polling"]` and an `auth={"sessionId": ..., "userEnv": "{}",
"clientType": "webapp", "chatProfile": None, "threadId": None}` payload is
enough to open a session and watch the raw events).

## Common pitfalls

- **Don't mix `.send()` and `stream_token`** on the same message inconsistently — stream first, `.send()` once at the end, or just `.send()` — don't call `.send()` early then keep streaming into an already-sent message.
- **A `RuntimeError`/exception raised inside `@cl.on_message`** shows the user a generic error toast, not your message text — if you want a specific message on failure, catch it yourself and `await cl.Message(content=...).send()`, which is exactly the pattern already used in `app.py` for search/extract/explain failures.
- **Blocking calls freeze every connected session**, not just the current one — Chainlit runs one asyncio event loop for the whole server. Always `cl.make_async()` sync I/O, or use an async-native client.
- **`cot = "hidden"` or `"tool_call"`** in config.toml can make `cl.Step` output invisible or collapsed even though the server-side code is correct — check this before assuming a Step integration is broken.
- **Env vars in `.chainlit/config.toml`'s `user_env`** are *user-supplied*, not server config — don't confuse them with `.env` (server-side, loaded by your own code via `python-dotenv`, as this project does).
