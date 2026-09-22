from typing import Literal

from pydantic import BaseModel


class Hit(BaseModel):
    kind: Literal["report", "event"]
    id: str
    score: float
    snippet: str
