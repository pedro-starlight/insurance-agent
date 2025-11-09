from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import Claim, ClaimStatus, UnifiedAgentOutput
from app.services import claim_service
from app.services.agent_service import process_claim_with_agent
from app.services import webhook_service, conversation_service, response_builder_service
from typing import Dict
from datetime import datetime
from asyncio import Queue
import asyncio
import os
import json
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


async def process_and_store_claim(claim_id: str, transcription: str, log_callback):
    """Process claim with unified agent and store results"""
    try:
        agent_output = await process_claim_with_agent(
            transcription=transcription,
            claim_id=claim_id,
            log_callback=log_callback
        )
        
        agent_outputs[claim_id] = agent_output
        claim_service.update_claim(
            claim_id,
            full_name=agent_output.full_name,
            status=ClaimStatus.PROCESSING
        )
        
        log_callback("✅ Agent processing completed successfully", "success")
        
        # Send sentinel to close SSE stream
        if claim_id in log_queues:
            try:
                await log_queues[claim_id].put(None)
            except:
                pass
        
        print(f"✓ ✓ ✓ Claim {claim_id} processed successfully ✓ ✓ ✓")
        
    except Exception as e:
        log_callback(f"❌ Agent processing failed: {str(e)}", "error")
        print(f"Error processing claim with agent: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# SSE Streaming Endpoints
# =============================================================================

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


# =============================================================================
# Claim Endpoints
# =============================================================================

@app.get("/claim/coverage/{claim_id}")
async def get_coverage(claim_id: str):
    """Get coverage decision for a claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    agent_output = agent_outputs.get(claim_id)
    return response_builder_service.build_coverage_response(claim_id, claim, agent_output)


@app.get("/claim/action/{claim_id}")
async def get_action(claim_id: str):
    """Get action recommendation for a claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    agent_output = agent_outputs.get(claim_id)
    return response_builder_service.build_action_response(claim_id, agent_output)


@app.get("/claim/message/{claim_id}")
async def get_message(claim_id: str, preview: bool = False):
    """
    Get message for policyholder.
    
    - If preview=True: Return drafted message for agent review (no status check)
    - If preview=False: Only return message after claim is approved/rejected (for policyholder)
    """
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # For agent preview, return the drafted message regardless of status
    if not preview:
        # Check if claim has been approved or denied (for policyholder view)
        if claim.status not in [ClaimStatus.APPROVED, ClaimStatus.DENIED]:
            raise HTTPException(
                status_code=404, 
                detail="Message not available - claim must be approved or rejected first"
            )
    
    agent_output = agent_outputs.get(claim_id)
    return response_builder_service.build_message_response(claim_id, agent_output)


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
    
    agent_output = agent_outputs.get(claim_id)
    return response_builder_service.build_claim_response(claim, agent_output)


@app.post("/claim/{claim_id}/approve")
async def approve_claim(claim_id: str):
    """Approve and initiate claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim_service.update_claim_status(claim_id, ClaimStatus.APPROVED)
    add_log(claim_id, "✅ Claim approved and initiated by human agent", "success")
    
    return {"status": "approved", "claim_id": claim_id}


@app.post("/claim/{claim_id}/reject")
async def reject_claim(claim_id: str):
    """Reject claim"""
    claim = claim_service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim_service.update_claim_status(claim_id, ClaimStatus.DENIED)
    add_log(claim_id, "❌ Claim rejected by human agent", "warning")
    
    return {"status": "rejected", "claim_id": claim_id}


# =============================================================================
# Webhook Endpoints
# =============================================================================

@app.get("/webhook/elevenlabs/transcription")
async def verify_webhook():
    """Webhook verification endpoint (some services use GET for verification)"""
    print("Webhook verification request received (GET)")
    return {"status": "ok", "message": "Webhook endpoint is active"}


@app.post("/webhook/elevenlabs/transcription")
async def receive_transcription_webhook(request: Request):
    """
    Receive post-call transcription webhook from ElevenLabs.
    Triggers unified agent processing.
    
    Implements best practices from ElevenLabs documentation.
    """
    print("=" * 80)
    print("WEBHOOK REQUEST RECEIVED")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print("=" * 80)
    
    try:
        # Verify webhook signature if secret is configured
        webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
        _, body = await webhook_service.verify_webhook_signature(request, webhook_secret)
        
        # Check webhook type
        webhook_type = webhook_service.check_webhook_type(body)
        print(f"📥 Webhook type: {webhook_type}")
        
        # Extract conversation ID
        conversation_id = webhook_service.extract_conversation_id(body)
        print(f"✓ Extracted conversation_id: {conversation_id}")
        
        # Build transcription from webhook data
        data = body.get("data", {})
        transcription_text, transcription_parts, entry_count = \
            webhook_service.build_transcription_from_webhook(data)
        
        print(f"✅ Built transcription: {len(transcription_parts)} parts, "
              f"{len(transcription_text)} chars total")
        print(f"   Preview: {transcription_text[:150]}...")
        
        if entry_count < 3:
            print(f"⚠️ WARNING: Short transcript ({entry_count} entries) - "
                  "conversation may have been interrupted")
        
        # Store conversation in memory and file
        conversation_service.store_conversation_in_memory(
            conversation_id,
            transcription_text
        )
        
        conversation_service.save_conversation_to_file(
            conversation_id,
            transcription_text,
            {
                "raw_transcript": data.get("transcript", []),
                "transcript_entry_count": entry_count,
                "transcription_parts_count": len(transcription_parts),
                "webhook_type": webhook_type,
                "full_webhook_data": data
            }
        )
        
        # Check if claim already exists for this conversation
        existing_claim_id = conversation_to_claim.get(conversation_id)
        
        if existing_claim_id:
            print(f"⚠️ Updating existing claim {existing_claim_id} for conversation {conversation_id}")
            claim_id = existing_claim_id
            claim_service.update_claim(
                claim_id,
                transcription=transcription_text,
                status=ClaimStatus.PROCESSING
            )
            add_log(claim_id, f"Claim updated with new transcription ({entry_count} entries)", "info")
        else:
            # Create new claim
            claim_id = claim_service.create_claim_from_conversation(
                conversation_id,
                transcription_text
            )
            claim_service.update_claim(claim_id, status=ClaimStatus.PROCESSING)
            add_log(claim_id, f"Claim created for conversation: {conversation_id}", "info")
            conversation_to_claim[conversation_id] = claim_id
        
        # Check if transcript is complete enough to process
        if not webhook_service.should_process_transcript(entry_count):
            print(f"⏸️ Skipping agent processing - incomplete transcript.")
            add_log(claim_id, f"Waiting for complete transcript (currently {entry_count} entries)", "info")
            return {
                "status": "received",
                "conversation_id": conversation_id,
                "claim_id": claim_id,
                "processed": False
            }
        
        # Process claim with unified agent
        add_log(claim_id, "Starting unified agent processing...", "info")
        
        def log_callback(message: str, log_type: str = "info"):
            add_log(claim_id, message, log_type)
        
        await process_and_store_claim(claim_id, transcription_text, log_callback)
        
        return {
            "status": "received",
            "conversation_id": conversation_id,
            "claim_id": claim_id,
            "processed": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error processing transcription webhook: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Conversation Endpoints
# =============================================================================

@app.get("/conversation/latest")
async def get_latest_conversation():
    """Get the most recent conversation that has a transcription"""
    return conversation_service.get_latest_conversation()


@app.get("/conversation/{conversation_id}/transcription")
async def get_conversation_transcription(conversation_id: str):
    """Get transcription for a conversation (from memory or file)"""
    return conversation_service.get_conversation(conversation_id)


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
    claim = claim_service.get_claim_by_conversation_id(conversation_id)
    if claim:
        conversation_to_claim[conversation_id] = claim.id
        return {
            "conversation_id": conversation_id,
            "claim_id": claim.id
        }
    
    # Fallback: Check if conversation file exists and create claim on-demand
    # This handles cases where server restarted or webhook failed to create claim
    conversation_data = conversation_service.load_conversation_from_file(conversation_id)
    
    if conversation_data:
        print(f"⚠️ No claim found for {conversation_id}, creating from saved file...")
        try:
            transcription_text = conversation_data.get("transcription", "")
            
            if transcription_text:
                new_claim_id = claim_service.create_claim_from_conversation(
                    conversation_id,
                    transcription_text
                )
                conversation_to_claim[conversation_id] = new_claim_id
                
                print(f"✅ Created claim {new_claim_id} for conversation {conversation_id}")
                add_log(new_claim_id, "Claim created on-demand from saved conversation file", "info")
                
                # Trigger agent processing for this claim
                add_log(new_claim_id, "Starting unified agent processing...", "info")
                
                def log_callback(message: str, log_type: str = "info"):
                    add_log(new_claim_id, message, log_type)
                
                # Process claim with agent in background
                asyncio.create_task(process_and_store_claim(new_claim_id, transcription_text, log_callback))
                
                return {
                    "conversation_id": conversation_id,
                    "claim_id": new_claim_id
                }
        except Exception as e:
            print(f"❌ Error creating claim from conversation file: {e}")
            import traceback
            traceback.print_exc()
    
    raise HTTPException(status_code=404, detail="No claim found for this conversation")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

