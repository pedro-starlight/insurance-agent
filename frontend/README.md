# Frontend Application

Next.js frontend for the Insurance Agent system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` file:
```bash
cp .env.local.example .env.local
```

3. Add your configuration to `.env.local`:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `NEXT_PUBLIC_ELEVENLABS_API_KEY`: Your ElevenLabs API key (optional)
- `NEXT_PUBLIC_ELEVENLABS_AGENT_ID`: Your ElevenLabs agent ID (optional)

4. Run the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Features

- **Policyholder View**: Initiate calls and receive messages
- **Agent View**: Review claims, coverage decisions, and approve actions

## Notes

- If ElevenLabs credentials are not configured, the app runs in mock mode
- The app uses localStorage to share claim IDs between views
- Real-time updates use polling (can be upgraded to WebSocket)

