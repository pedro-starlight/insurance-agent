"""
Webhook service for handling ElevenLabs webhook requests.

Provides signature verification, payload parsing, and transcription building
following ElevenLabs best practices:
https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks
"""
import hmac
import hashlib
import json
import time
from typing import Tuple, Optional, Dict, List
from fastapi import Request, HTTPException


def parse_signature_header(signature_header: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse the elevenlabs-signature header format: t=timestamp,v0=signature
    
    Args:
        signature_header: The elevenlabs-signature header value
        
    Returns:
        Tuple of (signature, timestamp) or (None, None) if parsing fails
    """
    signature = None
    timestamp = None
    
    signature_parts = signature_header.split(",")
    for part in signature_parts:
        if part.startswith("v0="):
            signature = part.split("=", 1)[1]
        elif part.startswith("t="):
            timestamp = part.split("=", 1)[1]
    
    return signature, timestamp


def validate_timestamp(timestamp: str, tolerance_minutes: int = 30) -> bool:
    """
    Validate that the webhook timestamp is within the tolerance window.
    
    Args:
        timestamp: The timestamp from the webhook header
        tolerance_minutes: Maximum age of the timestamp in minutes
        
    Returns:
        True if timestamp is valid, False otherwise
    """
    try:
        tolerance_seconds = tolerance_minutes * 60
        min_valid_timestamp = int(time.time()) - tolerance_seconds
        return int(timestamp) >= min_valid_timestamp
    except (ValueError, TypeError):
        return False


async def verify_webhook_signature(
    request: Request,
    webhook_secret: str
) -> Tuple[bool, Optional[Dict]]:
    """
    Verify HMAC SHA256 signature of webhook request.
    
    Args:
        request: FastAPI request object
        webhook_secret: Secret key for signature verification
        
    Returns:
        Tuple of (is_valid, body_dict)
        
    Raises:
        HTTPException: If signature or timestamp validation fails
    """
    signature_header = request.headers.get("elevenlabs-signature")
    
    if not signature_header:
        # No signature header - read body and return as-is
        body = await request.json()
        return True, body
    
    # Parse signature header
    signature, timestamp = parse_signature_header(signature_header)
    
    if not signature or not timestamp:
        body = await request.json()
        return True, body
    
    # Validate timestamp
    if not validate_timestamp(timestamp, tolerance_minutes=30):
        raise HTTPException(
            status_code=401,
            detail="Webhook timestamp too old"
        )
    
    # Verify signature
    body_bytes = await request.body()
    signed_payload = f"{timestamp}.{body_bytes.decode('utf-8')}"
    
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )
    
    body = json.loads(body_bytes.decode('utf-8'))
    return True, body


def check_webhook_type(body: Dict) -> str:
    """
    Extract and validate webhook type from payload.
    
    Args:
        body: Webhook payload dictionary
        
    Returns:
        The webhook type string
        
    Raises:
        HTTPException: If webhook type is not post_call_transcription
    """
    webhook_type = body.get("type")
    
    if webhook_type != "post_call_transcription":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported webhook type: {webhook_type}"
        )
    
    return webhook_type


def build_transcription_from_webhook(data: Dict) -> Tuple[str, List[str], int]:
    """
    Build transcription text from webhook transcript array.
    
    Per ElevenLabs docs:
    - 'message' field may be truncated for long messages
    - 'original_message' field contains full, untruncated content
    
    Args:
        data: The 'data' section from webhook payload
        
    Returns:
        Tuple of (transcription_text, transcription_parts, entry_count)
    """
    transcript_array = data.get("transcript", [])
    transcription_parts = []
    
    for entry in transcript_array:
        role = entry.get("role", "unknown")
        
        # Use original_message if available (for truncated messages), otherwise use message
        original_msg = entry.get("original_message")
        regular_msg = entry.get("message", "")
        
        # Choose the appropriate message
        message = original_msg if original_msg is not None else regular_msg
        
        if message:
            speaker_label = "Agent" if role == "agent" else "User"
            transcription_parts.append(f"{speaker_label}: {message}")
    
    transcription_text = "\n".join(transcription_parts) if transcription_parts else json.dumps(transcript_array)
    
    return transcription_text, transcription_parts, len(transcript_array)


def extract_conversation_id(body: Dict) -> str:
    """
    Extract conversation_id from webhook payload.
    
    Args:
        body: Webhook payload dictionary
        
    Returns:
        The conversation ID
        
    Raises:
        HTTPException: If conversation_id is not found
    """
    data = body.get("data", {})
    conversation_id = data.get("conversation_id") or body.get("conversation_id")
    
    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="conversation_id is required in webhook payload"
        )
    
    return conversation_id


def should_process_transcript(entry_count: int, min_entries: int = 3) -> bool:
    """
    Determine if a transcript is complete enough to process.
    
    Args:
        entry_count: Number of transcript entries
        min_entries: Minimum required entries for processing
        
    Returns:
        True if transcript should be processed, False otherwise
    """
    return entry_count >= min_entries

