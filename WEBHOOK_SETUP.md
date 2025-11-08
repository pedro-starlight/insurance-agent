# ElevenLabs Webhook Setup Guide

## Overview
This guide explains how to configure the ElevenLabs post-call transcription webhook to receive conversation transcriptions after calls end.

## Webhook Endpoint

**Backend Endpoint:** `POST /webhook/elevenlabs/transcription`

**Full URL (local):** `http://localhost:8000/webhook/elevenlabs/transcription`

## Setup Steps

### 1. Make Your Backend Publicly Accessible

Since ElevenLabs needs to send webhooks to your server, it must be publicly accessible. For local development, use a tunneling service:

#### Option A: Using ngrok (Recommended)
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

This will give you a public URL like: `https://abc123.ngrok.io`

**Webhook URL:** `https://abc123.ngrok.io/webhook/elevenlabs/transcription`

#### Option B: Using localtunnel
```bash
npm install -g localtunnel
lt --port 8000
```

### 2. Configure Webhook in ElevenLabs Dashboard

1. Go to [ElevenLabs Dashboard](https://elevenlabs.io/app)
2. Navigate to your **Agent** settings
3. Go to **Webhooks** or **Post-Call Webhooks** section
4. Add a new webhook:
   - **URL:** Your public webhook URL (e.g., `https://abc123.ngrok.io/webhook/elevenlabs/transcription`)
   - **Event Type:** Select `post_call_transcription` or `Post-Call Transcription`
   - **Method:** POST
   - **Status:** Enabled

### 3. Verify Webhook is Working

1. **Check Backend Logs:**
   - When a call ends, you should see logs like:
     ```
     ================================================================================
     WEBHOOK REQUEST RECEIVED
     Method: POST
     URL: http://localhost:8000/webhook/elevenlabs/transcription
     ================================================================================
     Received transcription webhook body: {...}
     ```

2. **Test the Endpoint Manually:**
   ```bash
   curl -X POST http://localhost:8000/webhook/elevenlabs/transcription \
     -H "Content-Type: application/json" \
     -d '{
       "conversation_id": "test-123",
       "transcription": "Test transcription"
     }'
   ```

3. **Check Frontend:**
   - After a call ends, the transcription should appear in the PolicyholderView conversation transcript panel
   - The frontend polls every 5 seconds for the transcription

## Troubleshooting

### Webhook Not Being Called

1. **Check if webhook is configured in ElevenLabs:**
   - Verify the webhook URL is correct in the dashboard
   - Ensure the webhook is enabled/active

2. **Check if backend is accessible:**
   - Test the webhook URL directly: `curl https://your-url/webhook/elevenlabs/transcription`
   - Verify ngrok/tunnel is running and active

3. **Check backend logs:**
   - Look for any incoming requests to `/webhook` endpoints
   - Check for error messages

4. **Verify HTTPS:**
   - ElevenLabs requires HTTPS for webhooks
   - Make sure your tunnel service provides HTTPS (ngrok does by default)

5. **Check ElevenLabs Call History:**
   - Go to Call History in ElevenLabs dashboard
   - Check if calls are completing successfully
   - Look for any error messages

### Webhook Called But Transcription Not Appearing

1. **Check backend logs:**
   - Verify the webhook payload structure
   - Check if `conversation_id` is being extracted correctly

2. **Check frontend:**
   - Open browser console and look for polling logs
   - Verify `conversationId` is set in localStorage
   - Check for API errors when fetching transcription

3. **Test transcription retrieval:**
   ```bash
   curl http://localhost:8000/conversation/{conversation_id}/transcription
   ```

## Expected Webhook Payload

The webhook should receive a payload like:
```json
{
  "conversation_id": "conv_abc123",
  "transcription": "Full conversation transcription text..."
}
```

Or structured format:
```json
{
  "conversation_id": "conv_abc123",
  "transcription": {
    "text": "Full transcription",
    "messages": [...]
  }
}
```

## Production Deployment

For production:
1. Deploy backend to a server with a public domain
2. Use HTTPS (required by ElevenLabs)
3. Configure webhook URL in ElevenLabs dashboard
4. Consider adding webhook authentication/verification

