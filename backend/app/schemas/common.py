from pydantic import BaseModel
from typing import Optional, List


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List
