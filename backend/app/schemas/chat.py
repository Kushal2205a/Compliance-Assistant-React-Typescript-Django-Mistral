from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatEvent(BaseModel):
    token: str | None = None
    done: bool = False
    error: str | None = None
