import logging
from neo4j import GraphDatabase
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class SharedBrain:
    def __init__(self):
        self._driver = None

    def connect(self):
        self._driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        self._driver.verify_connectivity()
        logger.info("Connected to Neo4j")

    def close(self):
        if self._driver:
            self._driver.close()

    def create_or_update_user(self, user_id: str, name: str, **profile_fields) -> dict:
        with self._driver.session() as session:
            result = session.run(
                """
                MERGE (u:User {user_id: $user_id})
                SET u.name = $name
                RETURN u
                """,
                user_id=user_id,
                name=name,
            )
            record = result.single()

            dob = profile_fields.get("date_of_birth")
            tob = profile_fields.get("time_of_birth")
            birth_place = profile_fields.get("birth_place")
            language = profile_fields.get("preferred_language")
            zodiac = profile_fields.get("zodiac_sign")

            if any([dob, tob, birth_place, language, zodiac]):
                session.run(
                    """
                    MATCH (u:User {user_id: $user_id})
                    MERGE (u)-[:HAS_PROFILE]->(p:Profile)
                    SET p.date_of_birth = coalesce($dob, p.date_of_birth),
                        p.time_of_birth = coalesce($tob, p.time_of_birth),
                        p.birth_place = coalesce($birth_place, p.birth_place),
                        p.preferred_language = coalesce($language, p.preferred_language),
                        p.zodiac_sign = coalesce($zodiac, p.zodiac_sign)
                    """,
                    user_id=user_id,
                    dob=dob,
                    tob=tob,
                    birth_place=birth_place,
                    language=language,
                    zodiac=zodiac,
                )

            return {"user_id": user_id, "name": name}

    def get_user_profile(self, user_id: str) -> dict | None:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {user_id: $user_id})
                OPTIONAL MATCH (u)-[:HAS_PROFILE]->(p:Profile)
                RETURN u.name AS name, u.user_id AS user_id,
                       p.date_of_birth AS date_of_birth,
                       p.time_of_birth AS time_of_birth,
                       p.birth_place AS birth_place,
                       p.preferred_language AS preferred_language,
                       p.zodiac_sign AS zodiac_sign
                """,
                user_id=user_id,
            )
            record = result.single()
            if not record:
                return None
            return dict(record)

    def store_memory(self, user_id: str, category: str, content: str, **properties):
        rel_type = self._category_to_relationship(category)

        with self._driver.session() as session:
            existing = session.run(
                f"""
                MATCH (u:User {{user_id: $user_id}})-[:{rel_type}]->(m)
                WHERE toLower(m.content) = toLower($content)
                RETURN m
                """,
                user_id=user_id,
                content=content,
            ).single()

            if existing:
                props_set = ", ".join(
                    f"m.{k} = ${k}" for k in properties if k != "content"
                )
                if props_set:
                    session.run(
                        f"""
                        MATCH (u:User {{user_id: $user_id}})-[:{rel_type}]->(m)
                        WHERE toLower(m.content) = toLower($content)
                        SET {props_set}
                        """,
                        user_id=user_id,
                        content=content,
                        **properties,
                    )
                return

            props_clause = ", ".join(
                f"{k}: ${k}" for k in ["content", *properties.keys()]
            )
            session.run(
                f"""
                MATCH (u:User {{user_id: $user_id}})
                CREATE (u)-[:{rel_type}]->(m:Memory {{category: $category, {props_clause}}})
                """,
                user_id=user_id,
                category=category,
                content=content,
                **properties,
            )

    def update_memory(self, user_id: str, category: str, old_content: str, new_content: str):
        rel_type = self._category_to_relationship(category)
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (u:User {{user_id: $user_id}})-[:{rel_type}]->(m:Memory)
                WHERE toLower(m.content) = toLower($old_content)
                SET m.content = $new_content
                """,
                user_id=user_id,
                old_content=old_content,
                new_content=new_content,
            )

    def get_relevant_context(self, user_id: str, categories: list[str] | None = None) -> list[dict]:
        with self._driver.session() as session:
            if categories:
                result = session.run(
                    """
                    MATCH (u:User {user_id: $user_id})-[r]->(m:Memory)
                    WHERE m.category IN $categories
                    RETURN m.category AS category, m.content AS content,
                           type(r) AS relationship, properties(m) AS properties
                    ORDER BY m.category
                    """,
                    user_id=user_id,
                    categories=categories,
                )
            else:
                result = session.run(
                    """
                    MATCH (u:User {user_id: $user_id})-[r]->(m:Memory)
                    RETURN m.category AS category, m.content AS content,
                           type(r) AS relationship, properties(m) AS properties
                    ORDER BY m.category
                    """,
                    user_id=user_id,
                )

            return [dict(record) for record in result]

    def get_full_brain(self, user_id: str) -> dict:
        profile = self.get_user_profile(user_id)
        memories = self.get_relevant_context(user_id)
        return {
            "profile": profile,
            "memories": memories,
        }

    def list_all_users(self) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (u:User)
                OPTIONAL MATCH (u)-[:HAS_PROFILE]->(p:Profile)
                RETURN u.user_id AS user_id, u.name AS name,
                       p.zodiac_sign AS zodiac_sign
                ORDER BY u.name
                """
            )
            return [dict(r) for r in result]

    def _category_to_relationship(self, category: str) -> str:
        mapping = {
            "goal": "HAS_GOAL",
            "interest": "INTERESTED_IN",
            "preference": "PREFERS",
            "life_event": "HAS_LIFE_EVENT",
            "relationship": "HAS_RELATIONSHIP",
            "astrology": "HAS_ASTROLOGY",
            "career": "HAS_GOAL",
            "health": "HAS_HEALTH",
            "family": "HAS_FAMILY",
        }
        return mapping.get(category.lower(), "HAS_MEMORY")


shared_brain = SharedBrain()
