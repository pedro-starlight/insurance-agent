# Insurance Agent Prototype

An AI-powered insurance copilot system that automates roadside assistance claim processing using voice AI, automated coverage checking, and action recommendations.

## Architecture

- **Frontend**: Next.js/React with TypeScript
- **Backend**: FastAPI (Python)
- **Voice AI**: ElevenLabs Conversational AI
- **AI Processing**: OpenAI for claim extraction, coverage analysis, and action recommendations

## Features

### Policyholder View
- Initiate voice calls with AI agent
- Receive automated assessment and next actions via SMS simulation
- Real-time call status

### Insurance Agent View
- View claim details and coverage decisions
- See recommended actions (repair/tow/dispatch taxi)
- System logs for observability
- Approve and initiate claims

## Setup

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Add your API keys to `.env`:
```
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_AGENT_ID=your_agent_id_here
OPENAI_API_KEY=your_key_here
```

6. Run the backend:
```bash
uvicorn app.main:app --reload
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local` file from `.env.local.example`:
```bash
cp .env.local.example .env.local
```

4. Add your configuration to `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ELEVENLABS_API_KEY=your_key_here
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=your_agent_id_here
```

5. Run the frontend:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## API Endpoints

### POST `/claim/audio`
Create a claim from audio URL
- Request: `{ "url": "https://ngrok_audio_file.mp3" }`
- Response: `{ "claim_id": "uuid" }`

### GET `/claim/coverage/{claim_id}`
Get coverage decision for a claim
- Response: Coverage decision with reasoning

### GET `/claim/action/{claim_id}`
Get action recommendation for a claim
- Response: Recommended action (repair/tow/dispatch_taxi)

### GET `/claim/message/{claim_id}`
Get message for policyholder
- Response: Assessment and next actions

### GET `/claim/logs/{claim_id}`
Get system logs for observability
- Response: Array of log entries

### POST `/claim/{claim_id}/approve`
Approve and initiate a claim
- Response: Approval status

## Usage Flow

1. **Policyholder initiates call**: Click "Start Call" in Policyholder View
2. **Voice conversation**: Policyholder talks to AI agent (or mock mode if ElevenLabs not configured)
3. **Automated processing**: 
   - Audio transcribed
   - Claim fields extracted using OpenAI
   - Coverage checked against policy
   - Action recommended
4. **Agent review**: Insurance agent sees claim details, coverage decision, and recommended action
5. **Approval**: Agent approves and initiates claim
6. **Policyholder notification**: Policyholder receives message with assessment and next steps

## Mock Mode

If ElevenLabs credentials are not configured, the system will run in mock mode:
- Simulates a voice call
- Creates a sample claim
- Processes it through the full pipeline
- Useful for testing without voice API setup

## Data

Sample policy data is stored in `backend/app/data/sample_policies.json`:
- Three policy types: Comprehensive, Standard, Premium
- Coverage rules and exclusions
- Garage locations and services

## Development Notes

- Backend uses in-memory storage (claims reset on restart)
- Frontend polls for updates (can be upgraded to WebSocket)
- OpenAI integration has fallback to rule-based logic if API key not provided
- ElevenLabs WebSocket integration ready but requires agent setup

## Next Steps

- Add database persistence
- Implement WebSocket for real-time updates
- Add authentication
- Enhance OpenAI vector store for policy RAG
- Add audio file processing from ngrok URLs
- Implement proper audio playback for voice responses

