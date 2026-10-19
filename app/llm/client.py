import json
import logging
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._client = OpenAI(api_key=OPENAI_API_KEY)
        self._model = OPENAI_MODEL

    def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        brain_context: str,
        user_profile: str,
    ) -> str:
        system_prompt = self._build_system_prompt(brain_context, user_profile)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=512,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "I'm having trouble generating a response right now. Please try again."

    def extract_memories(self, user_message: str, assistant_response: str) -> list[dict]:
        prompt = f"""Analyze this conversation turn and extract any personal facts, goals, preferences,
interests, or important life information that would be useful to remember for future conversations.

User said: "{user_message}"
Assistant responded: "{assistant_response}"

Return a JSON array of extracted memories. Each memory should have:
- "category": one of "goal", "interest", "preference", "life_event", "relationship", "career", "health", "family", "astrology"
- "content": a concise description of the fact
- "properties": optional dict with additional details like timeframe, status, etc.

If nothing worth remembering, return an empty array [].
Only extract factual information the user shared about themselves. Do not extract questions or general topics.

Respond with ONLY the JSON array, no other text."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            memories = json.loads(text)
            if isinstance(memories, list):
                return memories
            return []
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []

    def select_relevant_categories(self, user_message: str) -> list[str]:
        prompt = f"""Given this user message, which categories of stored information would be relevant to answer it?

Message: "{user_message}"

Categories: goal, interest, preference, life_event, relationship, career, health, family, astrology

Return a JSON array of relevant category strings. If the message is general/greeting, return [].
Respond with ONLY the JSON array."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            categories = json.loads(text)
            if isinstance(categories, list):
                return categories
            return []
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Category selection failed: {e}")
            return []

    def _build_system_prompt(self, brain_context, user_profile):
        prompt = (
            "You are a personalized astrology assistant for MyNaksh. "
            "You provide insightful, warm responses that incorporate the user's astrological profile "
            "and personal context when relevant. Keep responses concise but helpful."
        )
        if user_profile:
            prompt += f"\n\nUser Profile:\n{user_profile}"
        if brain_context:
            prompt += f"\n\nRelevant information about this user:\n{brain_context}"
        prompt += (
            "\n\nUse the user's context naturally in your responses. "
            "Don't list facts back at them unless asked. "
            "If you don't have enough information, ask follow-up questions."
        )
        return prompt


llm_client = LLMClient()
