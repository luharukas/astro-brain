import logging
from app.llm.client import llm_client
from app.brain.graph import shared_brain
from app.memory.short_term import session_memory
from app.memory.chat_store import chat_store

logger = logging.getLogger(__name__)


def handle_chat(user_id: str, session_id: str, message: str) -> dict:
    context_used = []

    history = session_memory.get_history(session_id)

    categories = llm_client.select_relevant_categories(message)
    logger.info(f"Selected categories for '{message[:50]}': {categories}")

    brain_context = ""
    try:
        memories = shared_brain.get_relevant_context(user_id, categories if categories else None)
        if memories:
            parts = []
            for mem in memories:
                props = mem.get("properties", {})
                content = props.get("content", mem.get("content", ""))
                category = props.get("category", mem.get("category", ""))
                extra = {k: v for k, v in props.items() if k not in ("content", "category")}
                line = f"- [{category}] {content}"
                if extra:
                    line += f" ({', '.join(f'{k}: {v}' for k, v in extra.items())})"
                parts.append(line)
                context_used.append(category)
            brain_context = "\n".join(parts)
    except Exception as e:
        logger.error(f"Brain retrieval failed: {e}")

    profile_str = ""
    try:
        profile = shared_brain.get_user_profile(user_id)
        if profile:
            pinfo = []
            if profile.get("name"):
                pinfo.append(f"Name: {profile['name']}")
            if profile.get("zodiac_sign"):
                pinfo.append(f"Zodiac: {profile['zodiac_sign']}")
                context_used.append("zodiac")
            if profile.get("date_of_birth"):
                pinfo.append(f"DOB: {profile['date_of_birth']}")
            if profile.get("birth_place"):
                pinfo.append(f"Birth Place: {profile['birth_place']}")
            if profile.get("preferred_language"):
                pinfo.append(f"Language: {profile['preferred_language']}")
            if pinfo:
                profile_str = "\n".join(pinfo)
                if "user_profile" not in context_used:
                    context_used.append("user_profile")
    except Exception as e:
        logger.error(f"Profile retrieval failed: {e}")

    response_text = llm_client.generate_response(
        user_message=message,
        conversation_history=history,
        brain_context=brain_context,
        user_profile=profile_str,
    )

    session_memory.add_message(session_id, "user", message)
    session_memory.add_message(session_id, "assistant", response_text)
    try:
        chat_store.save_message(user_id, session_id, "user", message)
        chat_store.save_message(user_id, session_id, "assistant", response_text)
    except Exception as e:
        logger.error(f"Chat history persistence failed: {e}")

    try:
        extracted = llm_client.extract_memories(message, response_text)
        for mem in extracted:
            category = mem.get("category", "general")
            content = mem.get("content", "")
            properties = mem.get("properties", {})
            if content:
                shared_brain.store_memory(user_id, category, content, **properties)
                logger.info(f"Stored memory: [{category}] {content}")
    except Exception as e:
        logger.error(f"Memory persistence failed: {e}")

    context_used = list(dict.fromkeys(context_used))

    return {
        "response": response_text,
        "user_id": user_id,
        "session_id": session_id,
        "context_used": context_used,
    }
