# Running ED Gateway on your own machine

For a colleague who wants to try ED Gateway and send feedback. Everything runs locally in Docker.

ED Gateway is a research demo. It does not diagnose and does not give a triage level.
**Use fake data only. Never type real patient information.**

## You need

- Docker Desktop, running
- About 2 GB of free disk
- No Python or Node.js

## 1. Offline demo (no key needed)

```bash
git clone https://github.com/shin13/ed-gateway.git
cd ed-gateway
docker compose up --build -d
docker compose ps
```

All three services should say `healthy`. Open <http://127.0.0.1:8000>.

The first build takes a few minutes. After that it starts in seconds.

In this mode the app only matches a fixed list of Chinese keywords. It does not understand free text
or other languages. The chat tells you this on the first screen. Everything else is real: the
questions, the warnings, and the nurse draft.

Check which mode you are in:

```bash
curl -fsS http://127.0.0.1:8001/health/ready
# {"status":"ready","database":"available","llm":"mock"}
```

## 2. Full mode (your own key)

Use this if your feedback is about how well the system understands answers.

```bash
cp .env.example .env
```

Set these four values in `.env`:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_MODEL=<model name>
LLM_BASE_URL=<OpenAI-compatible endpoint>
LLM_API_KEY=<your own key>
```

Use your own key. Keys are personal. They are not in this repository and are not shared with it.
Ask the project owner which endpoint to request access to.

Then rebuild and check:

```bash
docker compose up --build -d
curl -fsS http://127.0.0.1:8001/health/ready
# {"status":"ready","database":"available","llm":"openai_compatible"}
```

If a value is missing, the `api` container stops with a config error. It does not fall back quietly.

## 3. Sending feedback

After a chat, press **「匯出本次對話」**. You get one Markdown file. Send it back.

The file holds the session id, which model was used, the rule version, the full chat with the source
of each answer, any warnings, and the nurse draft. It also shows which mode you were in, so mock and
full-mode feedback never get mixed up.

## Things that catch people out

**`POSTGRES_PASSWORD` only works the first time.** Postgres reads it when the volume is created.
Change it later and `api` will crash-loop with `InvalidPasswordError`. Either keep the old value, or
run `docker compose down --volumes` on purpose. That deletes the demo data.

**The ports are on `127.0.0.1` on purpose.** Only your machine can reach the app. There is no login,
so do not open these ports to a network.

**Stopping is safe. Resetting is not.**

```bash
docker compose down              # stops, keeps your sessions
docker compose down --volumes    # also deletes every session and draft
```

**A build can fail on a slow network.** `uv` may time out while downloading a package. Run the build
again, or use `UV_HTTP_TIMEOUT=120 docker compose up --build -d`.

## Image version

Both app containers are tagged `ed-gateway:0.1.0`. To keep two builds or roll back:

```bash
ED_GATEWAY_VERSION=0.1.1 docker compose up --build -d
```

## More

Developer commands, tests and migrations are in [README.md](README.md). Clinical limits are in
[docs/open-clinical-decisions.md](docs/open-clinical-decisions.md) and
[docs/source-authority.md](docs/source-authority.md).
