import logging
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from app.config import MONGO_URI, MONGO_DB

logger = logging.getLogger(__name__)


class ChatStore:
    def __init__(self):
        self._client = None
        self._db = None

    def connect(self):
        self._client = MongoClient(MONGO_URI)
        self._db = self._client[MONGO_DB]
        self._db.messages.create_index([("session_id", ASCENDING), ("timestamp", ASCENDING)])
        self._db.messages.create_index([("user_id", ASCENDING)])
        logger.info("Connected to MongoDB")

    def close(self):
        if self._client:
            self._client.close()

    def save_message(self, user_id: str, session_id: str, role: str, content: str):
        self._db.messages.insert_one({
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc),
        })

    def get_session_history(self, session_id: str) -> list[dict]:
        cursor = self._db.messages.find(
            {"session_id": session_id},
            {"_id": 0, "role": 1, "content": 1, "timestamp": 1},
        ).sort("timestamp", ASCENDING)
        return [
            {**doc, "timestamp": doc["timestamp"].isoformat()}
            for doc in cursor
        ]

    def get_user_sessions(self, user_id: str) -> list[dict]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"timestamp": 1}},
            {"$group": {
                "_id": "$session_id",
                "preview": {"$first": "$content"},
                "message_count": {"$sum": 1},
                "last_activity": {"$max": "$timestamp"},
            }},
            {"$sort": {"last_activity": -1}},
        ]
        results = list(self._db.messages.aggregate(pipeline))
        return [
            {
                "session_id": r["_id"],
                "preview": r["preview"],
                "message_count": r["message_count"],
            }
            for r in results
        ]


chat_store = ChatStore()
