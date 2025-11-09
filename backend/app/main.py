from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import AudioRequest, Claim, CoverageDecision, ActionRecommendation, Message, ClaimStatus, ConversationTranscription, UnifiedAgentOutput
from app.services import claim_service, coverage_service, action_service
from app.services.agent_service import process_claim_with_agent
from typing import Dict, Optional
from datetime import datetime
from asyncio import Queue
import asyncio
import os
import json
import hmac
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env file
try:
    load_dotenv()
except PermissionError as e:
    print(f"Warning: Could not load .env file due to permission error: {e}")
    print("Attempting to manually load environment variables...")
    # Fallback: manually load .env if dotenv fails
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print("✓ Successfully loaded .env manually")
    except Exception as e2:
        print(f"Warning: Could not manually load .env: {e2}")

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

# Store for SSE log queues (claim_id -> Queue)
log_queues: Dict[str, Queue] = {}

# Store for agent outputs per claim (claim_id -> UnifiedAgentOutput)
agent_outputs: Dict[str, UnifiedAgentOutput] = {}

# Store mapping from conversation_id to claim_id
conversation_to_claim: Dict[str, str] = {}


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
    """Add a log entry and push to SSE stream if active"""
    if claim_id not in system_logs:
        system_logs[claim_id] = []
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "message": message
    }
    system_logs[claim_id].append(log_entry)
    
    # Push to SSE queue if exists
    if claim_id in log_queues:
        try:
            log_queues[claim_id].put_nowait(log_entry)
        except:
            pass


@app.get("/claim/stream/{claim_id}")
async def stream_logs(claim_id: str):
    """Stream agent execution logs via Server-Sent Events"""
    
    # Create queue for this claim if not exists
    if claim_id not in log_queues:
        log_queues[claim_id] = Queue()
    
    async def event_generator():
        queue = log_queues[claim_id]
        try:
            # Send existing logs first
            if claim_id in system_logs:
                for log in system_logs[claim_id]:
                    yield f"data: {json.dumps(log)}\n\n"
            
            # Send a keepalive message to establish connection
            yield f": keepalive\n\n"
            
            # Then stream new logs
            while True:
                try:
                    # Use asyncio.wait_for to allow periodic keepalive messages
                    log = await asyncio.wait_for(queue.get(), timeout=30.0)
                    if log is None:  # Sentinel to close stream
                        break
                    yield f"data: {json.dumps(log)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive to prevent connection timeout
                    yield f": keepalive\n\n"
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in SSE stream for claim {claim_id}: {e}")
        finally:
            # Don't delete queue on disconnect - allow reconnection
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )




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
    
    # Get agent output if available
    agent_output = agent_outputs.get(claim_id)
    
    if agent_output:
        # Use agent output for coverage decision
        return {
            "claim_id": claim_id,
            "claim_details": {
                # Structured fields
                "full_name": agent_output.full_name,
                "car_model": {
                    "make": agent_output.car_make,
                    "model": agent_output.car_model,
                    "year": agent_output.car_year
                } if agent_output.car_make else None,
                "location_data": {
                    "free_text": agent_output.location,
                    "components": {
                        "city": agent_output.city,
                        "road_or_street": "",
                        "direction": "",
                        "landmark_or_exit": ""
                    }
                } if agent_output.location else None,
                "assistance_type": agent_output.assistance_type,
                "safety_status": agent_output.safety_status,
                "confirmation": "confirmed",
                # Legacy fields (for backward compatibility)
                "policyholder_name": agent_output.full_name,
                "car_info": f"{agent_output.car_year} {agent_output.car_make} {agent_output.car_model}",
                "location": agent_output.location,
                "damage_type": agent_output.assistance_type,
                "situation": agent_output.safety_status
            },
            "coverage_decision": {
                "covered": agent_output.coverage_covered,
                "reasoning": agent_output.coverage_reasoning,
                "policy_section": agent_output.coverage_policy_section,
                "confidence": agent_output.coverage_confidence
            }
        }
    else:
        # Fallback to claim data if agent hasn't processed yet
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
                "policyholder_name": getattr(claim, 'policyholder_name', claim.full_name),
                "car_info": getattr(claim, 'car_info', ''),
                "location": getattr(claim, 'location', ''),
                "damage_type": getattr(claim, 'damage_type', ''),
                "situation": getattr(claim, 'situation', '')
            },
            "coverage_decision": {
                "covered": False,
                "reasoning": "Agent is still processing this claim",
                "policy_section": None,
                "confidence": 0.0
            }
        }


@app.get("/claim/action/{claim_id}")
async def get_action(claim_id: str):
    """Get action recommendation for a claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get agent output if available
    agent_output = agent_outputs.get(claim_id)
    
    if agent_output:
        # Use agent output for action recommendation
        return {
            "claim_id": claim_id,
            "action": {
                "type": agent_output.action_type,
                "garage_name": agent_output.action_garage_name,
                "garage_location": agent_output.action_garage_location,
                "reasoning": agent_output.action_reasoning,
                "estimated_time": agent_output.action_estimated_time
            }
        }
    else:
        # Fallback: use legacy action service if agent hasn't processed yet
        # Create a minimal coverage decision for the legacy function
        from app.models import CoverageDecision
        coverage = CoverageDecision(
            claim_id=claim_id,
            covered=False,
            reasoning="Agent is still processing this claim",
            confidence=0.0
        )
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
    
    # Get agent output if available
    agent_output = agent_outputs.get(claim_id)
    
    if agent_output:
        # Use agent output for message
        return {
            "claim_id": claim_id,
            "message": {
                "assessment": agent_output.message_assessment,
                "next_actions": agent_output.message_next_actions,
                "sent_at": datetime.now().isoformat()
            }
        }
    else:
        # Fallback: use legacy message generation if agent hasn't processed yet
        from app.models import CoverageDecision
        coverage = CoverageDecision(
            claim_id=claim_id,
            covered=False,
            reasoning="Agent is still processing this claim",
            confidence=0.0
        )
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
    """Get full claim details from unified agent output"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Get agent output
    agent_output = agent_outputs.get(claim_id)
    
    if not agent_output:
        return {
            "claim": claim.dict(),
            "status": "processing",
            "message": "Agent is still processing this claim"
        }
    
    return {
        "claim": claim.dict(),
        "agent_output": agent_output.dict(),
        "status": "completed"
    }


@app.post("/claim/{claim_id}/approve")
async def approve_claim(claim_id: str):
    """Approve and initiate claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim_service.update_claim(claim_id, status=ClaimStatus.APPROVED)
    add_log(claim_id, "✅ Claim approved and initiated by human agent", "success")
    
    # Send the message to policyholder by updating the claim status
    # Frontend will poll for message updates
    
    return {"status": "approved", "claim_id": claim_id}


@app.post("/claim/{claim_id}/reject")
async def reject_claim(claim_id: str):
    """Reject claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim_service.update_claim(claim_id, status=ClaimStatus.REJECTED)
    add_log(claim_id, "❌ Claim rejected by human agent", "warning")
    
    # Frontend will poll for message updates
    
    return {"status": "rejected", "claim_id": claim_id}


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
    Triggers unified agent processing
    
    Implements best practices from ElevenLabs documentation:
    https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks#transcription-webhooks-post_call_transcription
    
    - HMAC signature verification with timestamp validation
    - Uses 'original_message' for full transcription (not truncated 'message')
    - Handles webhook type detection (post_call_transcription)
    - Returns 200 status code for successful processing
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
            signature_header = request.headers.get("elevenlabs-signature")
            
            if signature_header:
                signature_parts = signature_header.split(",")
                signature = None
                timestamp = None
                
                for part in signature_parts:
                    if part.startswith("v0="):
                        signature = part.split("=", 1)[1]
                    elif part.startswith("t="):
                        timestamp = part.split("=", 1)[1]
                
                if signature and timestamp:
                    # Validate timestamp (within 30 minutes tolerance as per docs)
                    import time
                    tolerance = int(time.time()) - 30 * 60
                    if int(timestamp) < tolerance:
                        print("ERROR: Webhook timestamp too old")
                        raise HTTPException(status_code=401, detail="Webhook timestamp too old")
                    
                    body_bytes = await request.body()
                    signed_payload = f"{timestamp}.{body_bytes.decode('utf-8')}"
                    
                    expected_signature = hmac.new(
                        webhook_secret.encode('utf-8'),
                        signed_payload.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    if not hmac.compare_digest(signature, expected_signature):
                        print("ERROR: Webhook signature verification failed!")
                        raise HTTPException(status_code=401, detail="Invalid webhook signature")
                    
                    print("✓ Webhook signature and timestamp verified successfully")
                    body = json.loads(body_bytes.decode('utf-8'))
                else:
                    body = await request.json()
            else:
                body = await request.json()
        else:
            body = await request.json()
        
        # Check webhook type as per ElevenLabs documentation
        webhook_type = body.get("type")
        print(f"📥 Webhook type: {webhook_type}")
        
        # We only handle post_call_transcription webhooks
        if webhook_type != "post_call_transcription":
            print(f"⚠️ Ignoring webhook type: {webhook_type}")
            return {"status": "received", "message": f"Webhook type {webhook_type} not handled"}
        
        # Extract conversation_id and transcription
        data = body.get("data", {})
        conversation_id = data.get("conversation_id") or body.get("conversation_id")
        
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversation_id is required in webhook payload")
        
        print(f"✓ Extracted conversation_id: {conversation_id}")
        
        # Build transcription text from transcript array
        # Per ElevenLabs docs: https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks
        # - 'message' field may be truncated for long messages
        # - 'original_message' field contains full, untruncated content (only populated when truncation occurs)
        transcript_array = data.get("transcript", [])
        transcription_parts = []
        
        print(f"📝 Processing {len(transcript_array)} transcript entries...")
        for idx, entry in enumerate(transcript_array):
            role = entry.get("role", "unknown")
            
            # Use original_message if available (for truncated messages), otherwise use message
            original_msg = entry.get("original_message")
            regular_msg = entry.get("message", "")
            
            # Choose the appropriate message
            message = original_msg if original_msg is not None else regular_msg
            
            # Debug logging for first few entries
            if idx < 3:
                print(f"  Entry {idx}: role={role}, has_original={original_msg is not None}, "
                      f"msg_len={len(message) if message else 0}, "
                      f"truncated={'...' in regular_msg if regular_msg else False}")
            
            if message:
                speaker_label = "Agent" if role == "agent" else "User"
                transcription_parts.append(f"{speaker_label}: {message}")
        
        transcription_text = "\n".join(transcription_parts) if transcription_parts else json.dumps(transcript_array)
        print(f"✅ Built transcription: {len(transcription_parts)} parts, {len(transcription_text)} chars total")
        print(f"   Preview: {transcription_text[:150]}...")
        
        # Check for incomplete conversations
        if len(transcript_array) < 3:
            print(f"⚠️ WARNING: Short transcript ({len(transcript_array)} entries) - conversation may have been interrupted")
        
        # Store conversation transcription
        conversation = ConversationTranscription(
            conversation_id=conversation_id,
            transcription=transcription_text,
            received_at=datetime.now()
        )
        conversation_transcriptions[conversation_id] = conversation
        
        # Save to JSON file
        conversations_dir = os.path.join(os.path.dirname(__file__), 'data', 'conversations')
        os.makedirs(conversations_dir, exist_ok=True)
        
        conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
        try:
            with open(conversation_file, 'w') as f:
                json.dump({
                    "conversation_id": conversation_id,
                    "transcription": transcription_text,
                    "received_at": conversation.received_at.isoformat(),
                    "raw_transcript": transcript_array,
                    "transcript_entry_count": len(transcript_array),
                    "transcription_parts_count": len(transcription_parts),
                    "webhook_type": webhook_type,
                    "full_webhook_data": data  # Save complete webhook data for debugging
                }, f, indent=2)
            print(f"✓ Saved conversation to file: {conversation_file}")
            print(f"  - {len(transcript_array)} transcript entries")
            print(f"  - {len(transcription_parts)} processed parts")
            print(f"  - {len(transcription_text)} total characters")
        except Exception as e:
            print(f"Warning: Failed to save conversation to file: {e}")
        
        # Check if claim already exists for this conversation
        existing_claim_id = conversation_to_claim.get(conversation_id)
        
        if existing_claim_id:
            # Update existing claim with new transcription
            print(f"⚠️ Updating existing claim {existing_claim_id} for conversation {conversation_id}")
            claim_id = existing_claim_id
            claim_service.update_claim(
                claim_id,
                transcription=transcription_text,
                status=ClaimStatus.PROCESSING
            )
            add_log(claim_id, f"Claim updated with new transcription ({len(transcript_array)} entries)", "info")
        else:
            # Create new claim
            claim_id = claim_service.create_claim()
            add_log(claim_id, f"Claim created for conversation: {conversation_id}", "info")
            claim_service.update_claim(
                claim_id,
                transcription=transcription_text,
                status=ClaimStatus.PROCESSING,
                conversation_id=conversation_id
            )
            conversation_to_claim[conversation_id] = claim_id
        
        # Define log callback for agent
        def log_callback(message: str, log_type: str = "info"):
            add_log(claim_id, message, log_type)
        
        # Skip agent processing for incomplete transcripts
        should_process_agent = len(transcript_array) >= 3
        
        if not should_process_agent:
            print(f"⏸️ Skipping agent processing - incomplete transcript. Waiting for complete webhook.")
            add_log(claim_id, f"Waiting for complete transcript (currently {len(transcript_array)} entries)", "info")
            return {"status": "received", "conversation_id": conversation_id, "claim_id": claim_id, "processed": False}
        
        # Process claim with unified agent (only for complete transcripts)
        add_log(claim_id, "Starting unified agent processing...", "info")
        try:
            agent_output = await process_claim_with_agent(
                transcription=transcription_text,
                claim_id=claim_id,
                log_callback=log_callback
            )
            
            # Store agent output
            agent_outputs[claim_id] = agent_output
            
            # Update claim with agent results
            claim_service.update_claim(
                claim_id,
                full_name=agent_output.full_name,
                status=ClaimStatus.PROCESSING
            )
            
            add_log(claim_id, "✅ Agent processing completed successfully", "success")
            
            # Send sentinel to close SSE stream
            if claim_id in log_queues:
                try:
                    await log_queues[claim_id].put(None)
                except:
                    pass
            
            print(f"✓ ✓ ✓ Claim {claim_id} processed successfully ✓ ✓ ✓")
            
        except Exception as e:
            add_log(claim_id, f"❌ Agent processing failed: {str(e)}", "error")
            print(f"Error processing claim with agent: {e}")
            import traceback
            traceback.print_exc()
        
        return {"status": "received", "conversation_id": conversation_id, "claim_id": claim_id, "processed": True}
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        import traceback
        print(f"Error processing transcription webhook: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/latest")
async def get_latest_conversation():
    """Get the most recent conversation that has a transcription"""
    # Check in-memory storage first
    if conversation_transcriptions:
        latest = max(conversation_transcriptions.values(), key=lambda x: x.received_at)
        return {
            "conversation_id": latest.conversation_id,
            "transcription": latest.transcription,
            "received_at": latest.received_at.isoformat()
        }
    
    # If nothing in memory, check file system
    conversations_dir = os.path.join(os.path.dirname(__file__), 'data', 'conversations')
    if os.path.exists(conversations_dir):
        files = [f for f in os.listdir(conversations_dir) if f.endswith('.json') and not f.startswith('.')]
        if files:
            # Load all conversations and find the most recent by received_at timestamp
            conversations = []
            for filename in files:
                file_path = os.path.join(conversations_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if 'received_at' in data and 'conversation_id' in data:
                            conversations.append(data)
                except Exception as e:
                    print(f"Warning: Could not load conversation file {filename}: {e}")
                    continue
            
            if conversations:
                # Sort by received_at timestamp (most recent first)
                latest = max(conversations, key=lambda x: x.get('received_at', ''))
                print(f"✓ Found latest conversation: {latest['conversation_id']} (received_at: {latest.get('received_at')})")
                return {
                    "conversation_id": latest["conversation_id"],
                    "transcription": latest["transcription"],
                    "received_at": latest["received_at"]
                }
    
    raise HTTPException(status_code=404, detail="No conversations found")


@app.get("/conversation/{conversation_id}/transcription")
async def get_conversation_transcription(conversation_id: str):
    """Get transcription for a conversation (from memory or file)"""
    # First check in-memory storage
    transcription = conversation_transcriptions.get(conversation_id)
    
    # If not in memory, try loading from file
    if not transcription:
        conversations_dir = os.path.join(os.path.dirname(__file__), 'data', 'conversations')
        conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
        
        if os.path.exists(conversation_file):
            try:
                with open(conversation_file, 'r') as f:
                    data = json.load(f)
                    return {
                        "conversation_id": data["conversation_id"],
                        "transcription": data["transcription"],
                        "received_at": data["received_at"]
                    }
            except Exception as e:
                print(f"Error loading conversation from file: {e}")
        
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return {
        "conversation_id": conversation_id,
        "transcription": transcription.transcription,
        "received_at": transcription.received_at.isoformat()
    }


@app.get("/conversation/{conversation_id}/claim")
async def get_claim_from_conversation(conversation_id: str):
    """Get claim_id associated with a conversation_id"""
    # Check mapping first
    claim_id = conversation_to_claim.get(conversation_id)
    
    if claim_id:
        return {
            "conversation_id": conversation_id,
            "claim_id": claim_id
        }
    
    # If not in mapping, check all claims for this conversation_id
    from app.services.claim_service import claims_store
    for cid, claim in claims_store.items():
        if hasattr(claim, 'conversation_id') and claim.conversation_id == conversation_id:
            conversation_to_claim[conversation_id] = cid
            return {
                "conversation_id": conversation_id,
                "claim_id": cid
            }
    
    # Fallback: Check if conversation file exists and create claim on-demand
    # This handles cases where server restarted or webhook failed to create claim
    conversations_dir = os.path.join(os.path.dirname(__file__), 'data', 'conversations')
    conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
    
    if os.path.exists(conversation_file):
        print(f"⚠️ No claim found for {conversation_id}, creating from saved file...")
        try:
            with open(conversation_file, 'r') as f:
                data = json.load(f)
                transcription_text = data.get("transcription", "")
                
                if transcription_text:
                    # Create a new claim
                    new_claim_id = claim_service.create_claim()
                    claim_service.update_claim(
                        new_claim_id,
                        transcription=transcription_text,
                        conversation_id=conversation_id,
                        status=ClaimStatus.PENDING
                    )
                    
                    # Store mapping
                    conversation_to_claim[conversation_id] = new_claim_id
                    
                    print(f"✅ Created claim {new_claim_id} for conversation {conversation_id}")
                    add_log(new_claim_id, f"Claim created on-demand from saved conversation file", "info")
                    
                    return {
                        "conversation_id": conversation_id,
                        "claim_id": new_claim_id
                    }
        except Exception as e:
            print(f"❌ Error creating claim from conversation file: {e}")
            import traceback
            traceback.print_exc()
    
    raise HTTPException(status_code=404, detail="No claim found for this conversation")


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

