import re
from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LEN = 400
MAX_HISTORY_TURNS = 15
MAX_HISTORY_CONTENT_LEN = 4000

_INJECTION_PATTERNS = re.compile(
    r"(ignore (previous|prior|all) instructions?|"
    r"forget (everything|all)|"
    r"new (role|persona|instructions?)|"
    r"you are now|act as (a |an )?(?!tanay|the)|"
    r"<\|im_start\||<\|im_end\||"
    r"\[INST\]|\[\/INST\]|"
    r"system\s*:|<system>|"
    r"jailbreak|dan mode|dev mode|"
    r"pretend (you are|to be)|"
    r"disregard (your|all)|"
    r"override (your|the) (instructions?|prompt|system))",
    re.IGNORECASE,
)


class HistoryMessage(BaseModel):
    role: str
    content: str = Field(max_length=MAX_HISTORY_CONTENT_LEN)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v

    @field_validator("content")
    @classmethod
    def no_injection_in_history(cls, v: str) -> str:
        if _INJECTION_PATTERNS.search(v):
            raise ValueError("Content contains disallowed patterns.")
        return v.strip()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LEN)
    history: list[HistoryMessage] = Field(default=[], max_length=MAX_HISTORY_TURNS)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty.")
        if _INJECTION_PATTERNS.search(stripped):
            raise ValueError("Message contains disallowed patterns.")
        return stripped


class ChatResponse(BaseModel):
    response: str
