# Testing Transcription Flow

## Changes Made

### Problem
The background WebSocket was conflicting with the ElevenLabs widget, causing error `1008 Invalid message received`. The conversationId was never being captured.

### Solution
1. **Removed conflicting WebSocket**: The widget handles the conversation internally, so we don't need a separate WebSocket connection.
2. **Post-call transcription**: The system now relies on the webhook to receive transcription AFTER the call ends.
3. **Automatic discovery**: Frontend polls the backend every 3 seconds to check for new conversations.
4. **New backend endpoint**: `GET /conversation/latest` returns the most recent conversation.

## How It Works Now

1. User starts a call through the ElevenLabs widget
2. Call ends
3. ElevenLabs sends webhook to backend: `POST /webhook/elevenlabs/transcription`
4. Backend stores the transcription with conversation_id
5. Frontend polls `GET /conversation/latest` every 3 seconds
6. When found, frontend displays the transcription in both PolicyholderView and AgentView

## Testing Steps

### Test 1: Using Real ElevenLabs Call (Requires ngrok)

1. Start ngrok to expose your backend:
   ```bash
   ngrok http 8000
   ```

2. Configure ElevenLabs webhook in their dashboard:
   - Webhook URL: `https://your-ngrok-url.ngrok.io/webhook/elevenlabs/transcription`
   - Event: `post_call_transcription`

3. Start the backend:
   ```bash
   cd backend
   source venv/bin/activate
   python -m app.main
   ```

4. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

5. Make a call through the widget in PolicyholderView
6. After call ends, wait ~5 seconds for webhook
7. Transcription should appear in both views

### Test 2: Using Test Webhook (No ngrok needed)

1. Start backend and frontend (see Test 1)

2. Simulate a webhook call:
   ```bash
   curl -X POST http://localhost:8000/webhook/elevenlabs/transcription/test
   ```

3. Check response:
   ```json
   {
     "status": "test_complete",
     "conversation_id": "test-conv-123",
     "message": "Test transcription stored..."
   }
   ```

4. Within 3 seconds, you should see the transcription appear in both views
5. Look for console logs:
   - PolicyholderView: `Found latest conversation from backend: test-conv-123`
   - AgentView: `Found latest conversation from backend: test-conv-123`

### Test 3: Manual Webhook Simulation

Send a real webhook payload:

```bash
curl -X POST http://localhost:8000/webhook/elevenlabs/transcription \
  -H "Content-Type: application/json" \
  -d '{
    "type": "post_call_transcription",
    "data": {
      "conversation_id": "conv_test_12345",
      "transcript": [
        {
          "role": "agent",
          "message": "Hello, you'\''ve reached roadside assistance. How can I help you today?"
        },
        {
          "role": "user",
          "message": "Hi, my car broke down on Highway 101."
        },
        {
          "role": "agent",
          "message": "I'\''m sorry to hear that. Can you tell me your exact location?"
        }
      ]
    }
  }'
```

Expected backend logs:
```
✓ Extracted conversation_id: conv_test_12345
Found 3 transcript entries
Built transcription text (...)
✓ ✓ ✓ Stored transcription for conversation_id: conv_test_12345 ✓ ✓ ✓
Frontend can now fetch it at: GET /conversation/conv_test_12345/transcription
```

## Debugging

### Check backend logs
Look for:
- `INCOMING REQUEST TO WEBHOOK`
- `✓ Extracted conversation_id: ...`
- `✓ ✓ ✓ Stored transcription for conversation_id: ...`

### Check frontend console
Look for:
- `PolicyholderView: Found latest conversation from backend: ...`
- `AgentView: Found latest conversation from backend: ...`
- `AgentView: Post-call transcription received: ...`
- `AgentView: Updating transcriptions, new count: ...`

### Check localStorage
Open DevTools → Application → Local Storage:
- Should see `currentConversationId` key with the conversation ID

### Check API directly
```bash
# Get latest conversation
curl http://localhost:8000/conversation/latest

# Get specific conversation
curl http://localhost:8000/conversation/conv_test_12345/transcription
```

## Known Limitations

1. **Post-call only**: Transcription appears after the call ends, not in real-time
2. **Latest conversation**: System shows the most recent conversation, not necessarily the current one
3. **In-memory storage**: Transcriptions are lost when backend restarts

## Future Improvements

1. **Real-time transcription**: Connect to ElevenLabs WebSocket properly to get live transcription
2. **Persistent storage**: Store transcriptions in a database
3. **User session tracking**: Associate conversations with specific user sessions
4. **Widget events**: Listen to widget events if ElevenLabs exposes them in the future

