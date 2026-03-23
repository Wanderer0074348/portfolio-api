import tomllib
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────────

_root = Path(__file__).parent

_config_path = _root / "config.toml"
with open(_config_path, "rb") as _f:
    config = tomllib.load(_f)

# ── System prompt ─────────────────────────────────────────────────────────────

_prompt_path = _root / config["terminal"]["system_prompt_file"]
system_prompt = _prompt_path.read_text(encoding="utf-8")

# ── OpenAI client ─────────────────────────────────────────────────────────────

api_key = config["openai"]["api_key"]
if not api_key:
    raise RuntimeError("openai.api_key is not set in config.toml")

client = OpenAI(api_key=api_key)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Portfolio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config["server"]["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class HistoryMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []

class ChatResponse(BaseModel):
    response: str

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": config["openai"]["model"]}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    messages: list[dict] = [
        {"role": "system", "content": system_prompt}
    ]

    for msg in req.history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": req.message})

    try:
        completion = client.chat.completions.create(
            model=config["openai"]["model"],
            messages=messages,
            max_tokens=config["terminal"]["max_tokens"],
            temperature=config["terminal"]["temperature"],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    reply = completion.choices[0].message.content or ""
    return ChatResponse(response=reply)
