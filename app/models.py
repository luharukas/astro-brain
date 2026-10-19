from pydantic import BaseModel
from typing import Optional


class UserProfile(BaseModel):
    user_id: str
    name: str
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    birth_place: Optional[str] = None
    preferred_language: Optional[str] = "English"


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str
    context_used: list[str]


class UserProfileResponse(BaseModel):
    user_id: str
    name: str
    date_of_birth: Optional[str] = None
    time_of_birth: Optional[str] = None
    birth_place: Optional[str] = None
    preferred_language: Optional[str] = None
    zodiac_sign: Optional[str] = None
