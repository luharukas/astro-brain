import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.models import UserProfile, ChatRequest, ChatResponse, UserProfileResponse
from app.brain.graph import shared_brain
from app.memory.chat_store import chat_store
from app.profile.service import get_zodiac_sign
from app.chat.service import handle_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        shared_brain.connect()
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
    try:
        chat_store.connect()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
    yield
    shared_brain.close()
    chat_store.close()


app = FastAPI(title="MyNaksh Astrology Chat", lifespan=lifespan)


@app.post("/users", response_model=UserProfileResponse)
def create_user(profile: UserProfile):
    zodiac = None
    if profile.date_of_birth:
        zodiac = get_zodiac_sign(profile.date_of_birth)

    try:
        shared_brain.create_or_update_user(
            user_id=profile.user_id,
            name=profile.name,
            date_of_birth=profile.date_of_birth,
            time_of_birth=profile.time_of_birth,
            birth_place=profile.birth_place,
            preferred_language=profile.preferred_language,
            zodiac_sign=zodiac,
        )
    except Exception as e:
        logger.error(f"Failed to save user: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user profile")

    return UserProfileResponse(
        user_id=profile.user_id,
        name=profile.name,
        date_of_birth=profile.date_of_birth,
        time_of_birth=profile.time_of_birth,
        birth_place=profile.birth_place,
        preferred_language=profile.preferred_language,
        zodiac_sign=zodiac,
    )


@app.get("/users/{user_id}", response_model=UserProfileResponse)
def get_user(user_id: str):
    try:
        profile = shared_brain.get_user_profile(user_id)
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(**profile)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = handle_chat(
        user_id=request.user_id,
        session_id=request.session_id,
        message=request.message,
    )
    return ChatResponse(**result)


@app.get("/users/{user_id}/brain")
def get_brain(user_id: str):
    try:
        brain = shared_brain.get_full_brain(user_id)
    except Exception as e:
        logger.error(f"Failed to get brain: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    return brain


@app.get("/users")
def list_users():
    try:
        users = shared_brain.list_all_users()
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return users


@app.get("/users/{user_id}/sessions")
def get_user_sessions(user_id: str):
    try:
        sessions = chat_store.get_user_sessions(user_id)
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return sessions


@app.get("/sessions/{session_id}/history")
def get_session_history(session_id: str):
    try:
        history = chat_store.get_session_history(session_id)
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return history


@app.get("/health")
def health():
    return {"status": "ok"}
