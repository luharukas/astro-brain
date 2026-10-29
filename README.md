# Personalized Astrology Chat with Shared Brain

Conversational AI service with a persistent **Shared Brain** (Neo4j graph) for personalized astrology responses across sessions.

**Stack**: FastAPI, Neo4j (knowledge graph), MongoDB (chat history), OpenAI gpt-4o-mini, Streamlit UI

## How It Works

1. User sends a message
2. LLM picks which memory categories are relevant to the message
3. Matching memories are fetched from Neo4j
4. LLM generates a response using conversation history + brain context + user profile
5. After responding, a second LLM call extracts any new facts and stores them in the graph

**Two databases because each stores what it's good at**: Neo4j for interconnected user knowledge (goals, preferences, relationships), MongoDB for sequential chat logs.

## Graph Schema (Neo4j)

```
(User {user_id, name})
  ├── [:HAS_PROFILE] ──> (Profile {dob, tob, birthplace, zodiac, language})
  ├── [:HAS_GOAL] ──> (Memory {category: "goal", content, ...})
  ├── [:INTERESTED_IN] ──> (Memory {category: "interest", content, ...})
  ├── [:PREFERS] ──> (Memory {category: "preference", content, ...})
  ├── [:HAS_LIFE_EVENT] ──> (Memory {category: "life_event", content, ...})
  ├── [:HAS_RELATIONSHIP] ──> (Memory {category: "relationship", content, ...})
  └── [:HAS_MEMORY] ──> (Memory {category: "...", content, ...})
```

Category-specific relationship types allow targeted retrieval without scanning all memories.

## Setup

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Docker Compose (recommended)

```bash
cp .env.example .env
# set OPENAI_API_KEY in .env

docker-compose up --build
```

Services:
- **FastAPI**: http://localhost:8000
- **Streamlit UI**: http://localhost:8501
- **Neo4j Browser**: http://localhost:7474

### Local Development

```bash
# databases in docker
docker-compose up -d neo4j mongo

# python setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set OPENAI_API_KEY in .env

# terminal 1
uvicorn app.main:app --reload --port 8000

# terminal 2
streamlit run streamlit_app.py
```

## API Examples

### Create User
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "name": "Shubham",
    "date_of_birth": "1995-08-15",
    "birth_place": "Delhi",
    "preferred_language": "English"
  }'
```

### Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "session_id": "session-456",
    "message": "I am planning to switch jobs next year. What should I focus on?"
  }'
```

### Inspect Brain
```bash
curl http://localhost:8000/users/user-123/brain
```

## Project Structure

```
app/
  main.py            # FastAPI routes
  config.py          # Environment config
  models.py          # Pydantic models
  chat/service.py    # Chat orchestration (the main flow)
  llm/client.py      # OpenAI calls (response, memory extraction, category selection)
  brain/graph.py     # Neo4j shared brain
  memory/
    chat_store.py    # MongoDB chat persistence
    short_term.py    # In-memory session history (last 20 messages)
  profile/service.py # Zodiac sign lookup
streamlit_app.py     # Chat UI
```

## Limitations

- Session history is in-memory (lost on restart)
- Memory extraction depends on LLM quality
- No memory conflict resolution (old and new facts coexist)
- No auth on endpoints
- Zodiac calculation uses date ranges only
