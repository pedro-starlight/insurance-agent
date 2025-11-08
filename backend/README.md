# Backend API

FastAPI backend for the Insurance Agent system.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Add your API keys to `.env`:
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `ELEVENLABS_AGENT_ID`: Your ElevenLabs Conversational AI agent ID
- `ELEVENLABS_WEBHOOK_SECRET`: Your ElevenLabs webhook secret (for webhook signature verification)
- `OPENAI_API_KEY`: Your OpenAI API key

4. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Notes

- Claims are stored in-memory (will be lost on restart)
- If OpenAI API key is not provided, the system falls back to rule-based logic
- If ElevenLabs credentials are not provided, mock transcriptions are used

