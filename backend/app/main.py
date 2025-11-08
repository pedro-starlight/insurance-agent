from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.models import AudioRequest, Claim, CoverageDecision, ActionRecommendation, Message, ClaimStatus, ConversationTranscription
from app.services import claim_service, coverage_service, action_service, voice_service
from typing import Dict, Optional
from datetime import datetime
import os
import json
import hmac
import hashlib

app = FastAPI(title="Insurance Agent API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for system logs (for observability)
system_logs: Dict[str, list] = {}

# Store for conversation transcriptions (conversation_id -> transcription)
conversation_transcriptions: Dict[str, ConversationTranscription] = {}


# Middleware to log all requests to webhook endpoint
@app.middleware("http")
async def log_webhook_requests(request: Request, call_next):
    """Log all requests, especially to webhook endpoints"""
    if "/webhook" in str(request.url):
        print(f"\n{'='*80}")
        print(f"INCOMING REQUEST TO WEBHOOK: {request.method} {request.url}")
        print(f"Headers: {dict(request.headers)}")
        print(f"{'='*80}\n")
    
    response = await call_next(request)
    return response


def add_log(claim_id: str, message: str, log_type: str = "info"):
    """Add a log entry for observability"""
    if claim_id not in system_logs:
        system_logs[claim_id] = []
    
    from datetime import datetime
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message
    }
    system_logs[claim_id].append(log_entry)


@app.post("/claim/audio")
async def create_claim_from_audio(audio_request: AudioRequest):
    """
    Create a claim from audio URL
    Returns claim_id
    """
    try:
        # Create new claim
        claim_id = claim_service.create_claim()
        add_log(claim_id, f"Claim created: {claim_id}", "info")
        
        # Process audio and get transcription
        add_log(claim_id, "Processing audio transcription...", "info")
        
        # Download and transcribe audio from ElevenLabs conversation
        if not audio_request.conversation_id:
            raise HTTPException(status_code=400, detail="'conversation_id' is required")
        
        add_log(claim_id, f"Downloading audio from conversation: {audio_request.conversation_id}", "info")
        transcription = await voice_service.download_and_transcribe_conversation(audio_request.conversation_id)
        
        if transcription:
            # Update claim with transcription
            claim_service.update_claim(claim_id, transcription=transcription)
            add_log(claim_id, f"Transcription received: {transcription[:100]}...", "info")
            
            # Extract claim fields using OpenAI
            add_log(claim_id, "Extracting claim fields using AI...", "info")
            extracted_fields = await claim_service.extract_claim_fields(transcription)
            
            # Update claim with extracted fields (both new structured and legacy fields)
            claim_service.update_claim(
                claim_id,
                # New structured fields
                full_name=extracted_fields.full_name if extracted_fields.full_name != "unknown" else None,
                car_model=extracted_fields.car_model,
                location_data=extracted_fields.location,
                assistance_type=extracted_fields.assistance_type if extracted_fields.assistance_type != "unknown" else None,
                safety_status=extracted_fields.safety_status if extracted_fields.safety_status != "unknown" else None,
                confirmation=extracted_fields.confirmation,
                # Legacy fields for backward compatibility
                policyholder_name=extracted_fields.full_name if extracted_fields.full_name != "unknown" else None,
                car_info=f"{extracted_fields.car_model.year} {extracted_fields.car_model.make} {extracted_fields.car_model.model}".strip() if all(v != "unknown" for v in [extracted_fields.car_model.make, extracted_fields.car_model.model, extracted_fields.car_model.year]) else None,
                location=extracted_fields.location.free_text,
                damage_type=extracted_fields.assistance_type if extracted_fields.assistance_type != "unknown" else "breakdown",
                situation=extracted_fields.location.free_text,
                status=ClaimStatus.PROCESSING
            )
            add_log(claim_id, "Claim fields extracted successfully", "info")
            
            # Check coverage
            add_log(claim_id, "Checking coverage against policy...", "info")
            claim = claim_service.get_claim(claim_id)
            if claim:
                coverage = coverage_service.check_coverage(claim)
                add_log(claim_id, f"Coverage decision: {'COVERED' if coverage.covered else 'NOT COVERED'}", "info")
                
                # Get action recommendation
                add_log(claim_id, "Generating action recommendation...", "info")
                action = action_service.recommend_action(claim, coverage)
                add_log(claim_id, f"Action recommended: {action.action.value}", "info")
                
                # Generate message
                message = generate_message(claim, coverage, action)
                add_log(claim_id, "Message generated for policyholder", "info")
        
        return {"claim_id": claim_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def generate_message(claim: Claim, coverage: CoverageDecision, action: ActionRecommendation) -> Message:
    """Generate message for policyholder"""
    assessment = f"Your claim has been reviewed. {'Coverage confirmed' if coverage.covered else 'Coverage not confirmed'}."
    next_actions = f"Next steps: {action.reasoning}"
    if action.garage_name:
        next_actions += f" Garage: {action.garage_name}"
    if action.estimated_time:
        next_actions += f" Estimated time: {action.estimated_time}"
    
    return Message(
        claim_id=claim.id,
        assessment=assessment,
        next_actions=next_actions
    )


@app.get("/claim/coverage/{claim_id}")
async def get_coverage(claim_id: str):
    """Get coverage decision for a claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    coverage = coverage_service.check_coverage(claim)
    return {
        "claim_id": claim_id,
        "claim_details": {
            # Structured fields
            "full_name": claim.full_name,
            "car_model": claim.car_model.dict() if claim.car_model else None,
            "location_data": claim.location_data.dict() if claim.location_data else None,
            "assistance_type": claim.assistance_type,
            "safety_status": claim.safety_status,
            "confirmation": claim.confirmation,
            # Legacy fields (for backward compatibility)
            "policyholder_name": claim.policyholder_name,
            "car_info": claim.car_info,
            "location": claim.location,
            "damage_type": claim.damage_type,
            "situation": claim.situation
        },
        "coverage_decision": {
            "covered": coverage.covered,
            "reasoning": coverage.reasoning,
            "policy_section": coverage.policy_section,
            "confidence": coverage.confidence
        }
    }


@app.get("/claim/action/{claim_id}")
async def get_action(claim_id: str):
    """Get action recommendation for a claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    coverage = coverage_service.check_coverage(claim)
    action = action_service.recommend_action(claim, coverage)
    
    return {
        "claim_id": claim_id,
        "action": {
            "type": action.action.value,
            "garage_name": action.garage_name,
            "garage_location": action.garage_location,
            "reasoning": action.reasoning,
            "estimated_time": action.estimated_time
        }
    }


@app.get("/claim/message/{claim_id}")
async def get_message(claim_id: str):
    """Get message for policyholder"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    coverage = coverage_service.check_coverage(claim)
    action = action_service.recommend_action(claim, coverage)
    message = generate_message(claim, coverage, action)
    
    return {
        "claim_id": claim_id,
        "message": {
            "assessment": message.assessment,
            "next_actions": message.next_actions,
            "sent_at": message.sent_at.isoformat()
        }
    }


@app.get("/claim/logs/{claim_id}")
async def get_logs(claim_id: str):
    """Get system logs for a claim (for observability)"""
    return {
        "claim_id": claim_id,
        "logs": system_logs.get(claim_id, [])
    }


@app.get("/claim/{claim_id}")
async def get_claim(claim_id: str):
    """Get full claim details"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return {
        "claim": claim.dict(),
        "coverage": coverage_service.check_coverage(claim).dict(),
        "action": action_service.recommend_action(
            claim, 
            coverage_service.check_coverage(claim)
        ).dict(),
        "message": generate_message(
            claim,
            coverage_service.check_coverage(claim),
            action_service.recommend_action(
                claim,
                coverage_service.check_coverage(claim)
            )
        ).dict()
    }


@app.post("/claim/{claim_id}/approve")
async def approve_claim(claim_id: str):
    """Approve and initiate claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim_service.update_claim(claim_id, status=ClaimStatus.APPROVED)
    add_log(claim_id, "Claim approved and initiated by agent", "info")
    
    return {"status": "approved", "claim_id": claim_id}


@app.get("/webhook/elevenlabs/transcription")
async def verify_webhook():
    """
    Webhook verification endpoint (some services use GET for verification)
    """
    print("Webhook verification request received (GET)")
    return {"status": "ok", "message": "Webhook endpoint is active"}


@app.post("/webhook/elevenlabs/transcription")
async def receive_transcription_webhook(request: Request):
    """
    Receive post-call transcription webhook from ElevenLabs
    Expected payload structure based on ElevenLabs documentation:
    {
        "conversation_id": "string",
        "transcription": "string" or structured transcription data
    }
    """
    # Log all incoming request details for debugging
    print("=" * 80)
    print("WEBHOOK REQUEST RECEIVED")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    print("=" * 80)
    
    try:
        # Verify webhook signature if secret is configured
        webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
        body = None
        
        if webhook_secret:
            # Get signature from headers (ElevenLabs uses 'elevenlabs-signature' header)
            signature_header = request.headers.get("elevenlabs-signature")
            
            if signature_header:
                # Parse signature header format: "t=timestamp,v0=signature"
                # Extract the v0 signature value
                signature_parts = signature_header.split(",")
                signature = None
                timestamp = None
                
                for part in signature_parts:
                    if part.startswith("v0="):
                        signature = part.split("=", 1)[1]
                    elif part.startswith("t="):
                        timestamp = part.split("=", 1)[1]
                
                if signature:
                    # Get raw body for signature verification
                    body_bytes = await request.body()
                    
                    # Create signed payload: timestamp + "." + body
                    signed_payload = f"{timestamp}.{body_bytes.decode('utf-8')}"
                    
                    # Verify signature using HMAC SHA256
                    expected_signature = hmac.new(
                        webhook_secret.encode('utf-8'),
                        signed_payload.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    # Compare signatures securely
                    if not hmac.compare_digest(signature, expected_signature):
                        print("ERROR: Webhook signature verification failed!")
                        print(f"Received signature: {signature}")
                        print(f"Expected signature: {expected_signature}")
                        raise HTTPException(status_code=401, detail="Invalid webhook signature")
                    
                    print("✓ Webhook signature verified successfully")
                    # Parse body after verification
                    body = json.loads(body_bytes.decode('utf-8'))
                else:
                    print("WARNING: Could not parse signature from header")
                    body = await request.json()
            else:
                print("WARNING: Webhook secret configured but no signature header found")
                print("Available headers:", list(request.headers.keys()))
                # Still process the request but log the warning
                body = await request.json()
        else:
            # No secret configured, skip verification (for development)
            print("INFO: No webhook secret configured, skipping signature verification")
            body = await request.json()
        
        print(f"Received transcription webhook body type: {body.get('type')}")
        
        # Extract conversation_id from nested data structure
        # ElevenLabs sends: { "type": "post_call_transcription", "data": { "conversation_id": "...", "transcript": [...] } }
        data = body.get("data", {})
        conversation_id = data.get("conversation_id")
        
        if not conversation_id:
            # Try top-level as fallback
            conversation_id = body.get("conversation_id")
        
        if not conversation_id:
            print(f"ERROR: No conversation_id found in payload. Body keys: {list(body.keys())}")
            if data:
                print(f"Data keys: {list(data.keys())}")
            raise HTTPException(status_code=400, detail="conversation_id is required in webhook payload")
        
        print(f"✓ Extracted conversation_id: {conversation_id}")
        
        # Extract transcript from data.transcript array
        transcript_array = data.get("transcript", [])
        print(f"Found {len(transcript_array)} transcript entries")
        
        # Build transcription text from transcript array
        transcription_parts = []
        for entry in transcript_array:
            role = entry.get("role", "unknown")
            message = entry.get("message", "")
            if message:
                speaker_label = "Agent" if role == "agent" else "User"
                transcription_parts.append(f"{speaker_label}: {message}")
        
        transcription_text = "\n".join(transcription_parts) if transcription_parts else json.dumps(transcript_array)
        
        print(f"Built transcription text ({len(transcription_text)} chars): {transcription_text[:100]}...")
        
        # Store transcription
        conversation_transcriptions[conversation_id] = ConversationTranscription(
            conversation_id=conversation_id,
            transcription=transcription_text,
            received_at=datetime.now()
        )
        
        add_log(conversation_id, f"Transcription received via webhook for conversation: {conversation_id}", "info")
        
        print(f"✓ ✓ ✓ Stored transcription for conversation_id: {conversation_id} ✓ ✓ ✓")
        print(f"Frontend can now fetch it at: GET /conversation/{conversation_id}/transcription")
        
        return {"status": "received", "conversation_id": conversation_id}
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        # Try to get raw body for debugging
        try:
            body_bytes = await request.body()
            print(f"Raw body: {body_bytes.decode('utf-8', errors='ignore')}")
        except:
            pass
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        import traceback
        print(f"Error processing transcription webhook: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/latest")
async def get_latest_conversation():
    """Get the most recent conversation that has a transcription"""
    if not conversation_transcriptions:
        raise HTTPException(status_code=404, detail="No conversations found")
    
    # Get the most recent conversation (sorted by received_at)
    latest = max(conversation_transcriptions.values(), key=lambda x: x.received_at)
    
    return {
        "conversation_id": latest.conversation_id,
        "transcription": latest.transcription,
        "received_at": latest.received_at.isoformat()
    }


@app.get("/conversation/{conversation_id}/transcription")
async def get_conversation_transcription(conversation_id: str):
    """Get transcription for a conversation"""
    transcription = conversation_transcriptions.get(conversation_id)
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return {
        "conversation_id": conversation_id,
        "transcription": transcription.transcription,
        "received_at": transcription.received_at.isoformat()
    }


@app.post("/webhook/elevenlabs/transcription/test")
async def test_webhook_endpoint():
    """
    Test endpoint to simulate webhook call
    Useful for testing webhook functionality without waiting for ElevenLabs
    """
    test_conversation_id = "test-conv-123"
    test_transcription = "This is a test transcription. User: Hello, I need help. Agent: How can I assist you today?"
    
    # Store test transcription
    conversation_transcriptions[test_conversation_id] = ConversationTranscription(
        conversation_id=test_conversation_id,
        transcription=test_transcription,
        received_at=datetime.now()
    )
    
    print(f"Test transcription stored for conversation_id: {test_conversation_id}")
    
    return {
        "status": "test_complete",
        "conversation_id": test_conversation_id,
        "message": "Test transcription stored. Use this conversation_id to test frontend polling."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

