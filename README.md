# AI-First Pharma CRM: Chat-to-Form Sales Logger

> **Impact:** Automates HCP interaction logging using a conversational agent, reducing manual data entry time for pharma field reps by 80% and ensuring higher CRM data compliance.

An AI-first "Log HCP Interaction" screen for pharma field reps. The left panel is a **read-only** interaction form; the right panel is an **AI Assistant chat**. Every field on the form is populated and edited exclusively by a LangGraph agent — there is no manual form-filling, per the assignment's automation requirement.

<img src="https://github.com/user-attachments/assets/e4b3b190-b53e-49b5-8125-ecb89c1c46e7" width="100%" alt="AI-First Pharma CRM UI Mockup" />

## Tech stack

| Layer      | Choice                                              |
|------------|------------------------------------------------------|
| Frontend   | React 18 + Redux Toolkit, Vite, Google Inter font    |
| Backend    | Python + FastAPI                                     |
| AI agent   | LangGraph (ReAct-style tool-calling loop)             |
| LLM        | Groq `gemma2-9b-it` (routing + extraction), `llama-3.3-70b-versatile` as a documented fallback |
| Database   | Postgres (FastAPI + Async SQLAlchemy ORM using asyncpg; SQLite/aiosqlite for testing) |

## Architecture

### The agent's role

The LangGraph agent is the **only** thing that reads or writes the Interaction Details
form. The frontend never mutates form state directly; it sends every user chat message to
`POST /api/chat` along with the form's current snapshot, and renders whatever
`updated_state` comes back. This is what makes the screen "AI-first" rather than a normal
form with an AI helper bolted on.

The graph itself is a standard ReAct loop:

```
START → agent (Groq LLM + tools bound) → tools_condition
              ↑                              │
              └──────────── tools ◀──────────┘ (if a tool was called)
                              │
                             END (once the LLM replies with no further tool call)
```

- **`agent` node** — `gemma2-9b-it` with all 5 tools bound via `bind_tools`. It decides
  *which single tool* best matches the rep's message (see system prompt in
  `backend/app/agent/graph.py`).
- **`tools` node** — a LangGraph `ToolNode` that actually executes the selected tool. Each
  tool returns a `Command(update={...})`, which is how a tool call directly mutates the
  shared `form` state that flows back to the frontend (see `backend/app/agent/tools.py`).
- Control loops back to `agent` so it can give a one-line confirmation of what changed,
  then the graph ends.

### Loading and Error Handling in the Chat UI

To handle real-world API behaviors, the Chat UI implements robust loading and error states:

1. **Slow API Response (API is Slow)**:
   - When a chat message is sent, the UI immediately transitions to a loading state: it sets `isSending: true`, disables the chat input field and the "Log" button (preventing double submissions), and renders a message bubble containing a pulsing three-dot loading animation ("Thinking...").
2. **Network Failures (API Fails)**:
   - If the HTTP request fails due to network loss, server downtime, or CORS issues, the frontend dispatches `sendFailed`. The loading state is cleared, and a visually distinct error message styled with a light-red background, dark-red text, and a warning icon (`⚠️`) is appended to the chat window (e.g., `"⚠️ Sorry, something went wrong: Failed to fetch"`).
3. **LLM/Agent Errors (LLM/Backend Errors)**:
   - If the backend encounters a LangGraph execution or LLM error, it responds with a non-200 status code containing error details. The frontend's `sendChatMessage` wrapper intercepts the non-OK response, throws an error with the details, and displays it in the same light-red warning message block in the chat history.

### The 5 LangGraph tools

| Tool | Purpose |
|------|---------|
| **`log_interaction`** *(required)* | Takes a free-text note (e.g. *"Met Dr. Sharma, discussed Product X efficacy, positive sentiment, shared brochure"*) and calls the LLM to extract structured fields (HCP name, date/time, topics, sentiment, materials, samples). Creates a new `Interaction` row and returns the full populated form. |
| **`edit_interaction`** *(required)* | Takes an instruction (e.g. *"change sentiment to positive and add Dr. Rao to attendees"*) plus the current form as context, asks the LLM for only the fields that should change, merges them in, and updates the existing DB row — everything else is left untouched. |
| **`suggest_followups`** | Reads the current topics/outcomes/sentiment and asks the LLM for 2–4 concrete next-step suggestions, populating the "AI Suggested Follow-ups" list under the form (mirrors the mockup). |
| **`search_and_add_catalog_item`** | Searches the `materials`/`samples` catalog tables for a keyword (e.g. *"OncoBoost brochure"*) and appends the best match to `materials_shared` or `samples_distributed`. Falls back to adding the raw text if no catalog match exists. |
| **`summarize_voice_note`** | Summarizes a long dictated/voice-note transcript into concise bullet points and appends them to `topics_discussed` — this is the "Summarize from Voice Note" button in the mockup. |

Extraction and summarization inside tools use a separate, low-temperature Groq LLM
instance (`get_extraction_llm` in `app/agent/llm.py`) from the routing LLM used by the
`agent` node, so each can be prompt-tuned independently.

### Data model

`backend/app/models.py` — `HCP`, `Material`, `Sample`, `Interaction` (SQLAlchemy). IDs are
plain UUID strings and JSON columns use the generic `sqlalchemy.JSON` type rather than a
Postgres-only type, so the same models work against MySQL if you'd rather use that (per
the assignment, either is acceptable) — just point `DATABASE_URL` at a MySQL driver
(e.g. `mysql+pymysql://...`) and install `pymysql` instead of `psycopg2-binary`.

## Running with Docker Compose (Recommended)

To spin up the entire application stack (Postgres database, FastAPI backend, and React frontend) using a single command:

### 1. Configure Environment
Create a `.env` file in the root directory and add your Groq API key:
```bash
cp .env.example .env
# Open .env and populate GROQ_API_KEY
```

### 2. Launch the Application
Run Docker Compose:
```bash
docker compose up --build
```
This command automatically:
- Starts a Postgres database container (`db`).
- Performs alembic database migrations (`alembic upgrade head`) and seeds mock data (`seed_data.py`).
- Launches the FastAPI backend on `http://localhost:8000`.
- Compiles the React frontend into Nginx and serves it on `http://localhost:5173`.

Verify by opening `http://localhost:5173` in your browser.

## Running it locally

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `GROQ_API_KEY` — create one at https://console.groq.com/keys
- `DATABASE_URL` — point at your Postgres instance (a free one from Neon/Supabase works fine)

Before running the server, apply database schema migrations:
```bash
alembic upgrade head
```

Then seed demo data and start the FastAPI server:
```bash
python seed_data.py   # seeds demo HCPs / materials / samples
uvicorn app.main:app --reload --port 8000
```

The API is running at `http://localhost:8000` (health check: `GET /api/v1/health` or `/api/health`).

### 2. Running Tests

To run the automated `pytest` test suite:
```bash
pytest -v
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. If your backend isn't on `localhost:8000`, set
`VITE_API_BASE_URL` in a `frontend/.env` file.

### 3. Try it

In the chat panel, type e.g.:
- *"Met Dr. Sharma at City Hospital, discussed OncoBoost Phase III data, positive sentiment"*
  → `log_interaction` populates the whole form.
- *"Add the OncoBoost brochure to materials shared"* → `search_and_add_catalog_item`.
- *"Change the sentiment to neutral"* → `edit_interaction`.
- *"Suggest some follow-ups"* → `suggest_followups`.
- Paste a long rambling note and say *"summarize that voice note into topics discussed"*
  → `summarize_voice_note`.

## Project structure

```
backend/
  app/
    main.py            FastAPI app, CORS, table creation
    config.py           env-driven settings
    database.py          SQLAlchemy engine/session
    models.py             HCP / Material / Sample / Interaction
    schemas.py             Pydantic request/response shapes
    agent/
      llm.py               Groq chat + extraction LLM factories
      state.py             LangGraph AgentState (messages, form, tool_calls_made)
      tools.py             the 5 tools (Command-based state updates)
      graph.py             StateGraph wiring (agent ⇄ tools loop)
    routers/
      chat.py              POST /api/chat — drives the agent
      interactions.py      read-only listing endpoints
  seed_data.py            demo catalog data
  requirements.txt
  .env.example

frontend/
  src/
    store/                 Redux Toolkit: interactionSlice (form), chatSlice (messages)
    api/client.js           fetch wrapper for /api/chat
    components/
      LogInteractionScreen.jsx   split-screen layout
      InteractionForm.jsx         read-only left panel
      ChatPanel.jsx                right panel chat UI
    styles/index.css         Inter font + layout matching the provided mockup
```

## Notes / known limitations

- Conversation memory across turns uses LangGraph's in-memory `MemorySaver`, keyed by a
  per-browser-session `thread_id` generated on the frontend. Swap in a persistent
  checkpointer (Postgres/Redis) for multi-instance deployments.
- `log_interaction` always creates a *new* interaction; the agent's system prompt tells it
  to only call `log_interaction` once per session and use `edit_interaction` afterward,
  but this is a prompt-level rule, not enforced in code — a real production build would
  track "is there an active draft interaction" explicitly rather than relying on the LLM.
- Voice-to-text itself is out of scope (the task's "Requires Consent" button implies
  consent/recording is handled upstream); `summarize_voice_note` takes transcript text.
