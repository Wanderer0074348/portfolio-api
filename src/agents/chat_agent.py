import logging
import os
import tomllib
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

logger = logging.getLogger("portfolio.chat")

load_dotenv()

_root = Path(__file__).parent.parent.parent

with open(_root / "config.toml", "rb") as _f:
    _config = tomllib.load(_f)

_instructions = (_root / "prompts" / "instructions.md").read_text(encoding="utf-8")
_data_dir = _root / "prompts" / "data"
_data_sections = "\n\n".join(
    f.read_text(encoding="utf-8") for f in sorted(_data_dir.glob("*.md"))
)
system_prompt = f"{_instructions}\n\n{_data_sections}"

_api_key = os.environ.get("GROQ_API_KEY") or _config["groq"].get("api_key", "")
if not _api_key:
    raise RuntimeError("GROQ_API_KEY env var is not set")

_client = Groq(api_key=_api_key)
_model = _config["groq"]["model"]
_max_tokens = _config["terminal"]["max_tokens"]
_temperature = _config["terminal"]["temperature"]


def run(message: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    completion = _client.chat.completions.create(
        model=_model,
        messages=messages,
        max_tokens=_max_tokens,
        temperature=_temperature,
    )
    logger.debug(f"finish_reason={completion.choices[0].finish_reason}")
    return completion.choices[0].message.content or ""
