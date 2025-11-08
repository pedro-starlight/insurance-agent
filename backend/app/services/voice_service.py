import requests
import os
from typing import Optional, Dict, Any
from io import BytesIO
from app.models import Claim


async def list_conversations(
    agent_id: Optional[str] = None,
    cursor: Optional[str] = None,
    call_successful: Optional[str] = None,
    call_start_before_unix: Optional[int] = None,
    call_start_after_unix: Optional[int] = None,
    user_id: Optional[str] = None,
    page_size: Optional[int] = None,
    summary_mode: Optional[str] = None,
    search: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    List conversations from ElevenLabs
    
    Args:
        agent_id: Filter by specific agent ID
        cursor: Cursor for pagination (returned in response)
        call_successful: Filter by success result (success/failure/unknown)
        call_start_before_unix: Unix timestamp to filter conversations up to this start date
        call_start_after_unix: Unix timestamp to filter conversations after this start date
        user_id: Filter conversations by the user ID who initiated them
        page_size: How many conversations to return (max 100, defaults to 30)
        summary_mode: Whether to include transcript summaries (exclude/include)
        search: Full-text or fuzzy search over transcript messages
        
    Returns:
        Dictionary with conversations list, has_more flag, and next_cursor, or None if request fails
    """
    from elevenlabs.client import ElevenLabs
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
    
    try:
        # Initialize ElevenLabs client
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # Build parameters dict (only include non-None values)
        params = {}
        if agent_id is not None:
            params["agent_id"] = agent_id
        if cursor is not None:
            params["cursor"] = cursor
        if call_successful is not None:
            params["call_successful"] = call_successful
        if call_start_before_unix is not None:
            params["call_start_before_unix"] = call_start_before_unix
        if call_start_after_unix is not None:
            params["call_start_after_unix"] = call_start_after_unix
        if user_id is not None:
            params["user_id"] = user_id
        if page_size is not None:
            params["page_size"] = page_size
        if summary_mode is not None:
            params["summary_mode"] = summary_mode
        if search is not None:
            params["search"] = search
        
        # List conversations using ElevenLabs SDK
        response = elevenlabs.conversational_ai.conversations.list(**params)
        
        # Convert response to dictionary format
        return {
            "conversations": [
                {
                    "agent_id": conv.agent_id,
                    "branch_id": getattr(conv, "branch_id", None),
                    "agent_name": getattr(conv, "agent_name", None),
                    "conversation_id": conv.conversation_id,
                    "start_time_unix_secs": conv.start_time_unix_secs,
                    "call_duration_secs": conv.call_duration_secs,
                    "message_count": conv.message_count,
                    "status": conv.status,
                    "call_successful": conv.call_successful,
                    "transcript_summary": getattr(conv, "transcript_summary", None),
                    "call_summary_title": getattr(conv, "call_summary_title", None),
                    "direction": getattr(conv, "direction", None),
                }
                for conv in response.conversations
            ],
            "has_more": response.has_more,
            "next_cursor": getattr(response, "next_cursor", None),
        }
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return None


async def download_conversation_audio(conversation_id: str) -> Optional[bytes]:
    """
    Download audio recording from an ElevenLabs conversation
    
    Args:
        conversation_id: The ID of the conversation to download audio from
        
    Returns:
        Audio file bytes, or None if download fails
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
    
    url = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}/audio"
    
    headers = {
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error downloading conversation audio: {e}")
        return None


async def transcribe_audio(audio_data: bytes) -> Optional[str]:
    """
    Transcribe audio using ElevenLabs Speech-to-Text API
    
    Args:
        audio_data: Audio file bytes to transcribe
        
    Returns:
        Transcription text, or None if transcription fails
    """
    from elevenlabs.client import ElevenLabs
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment variables")
    
    try:
        # Initialize ElevenLabs client
        elevenlabs = ElevenLabs(api_key=api_key)
        
        # Convert bytes to BytesIO for the API
        audio_file = BytesIO(audio_data)
        
        # Transcribe using ElevenLabs Speech-to-Text API
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1",  # Model to use, for now only "scribe_v1" is supported
            tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
            language_code="eng",  # Language of the audio file. If set to None, the model will detect the language automatically.
            diarize=True,  # Whether to annotate who is speaking
        )
        
        return transcription
    except Exception as e:
        print(f"Error transcribing audio with ElevenLabs: {e}")
        return None


async def download_and_transcribe_conversation(conversation_id: str) -> Optional[str]:
    """
    Download audio from ElevenLabs conversation and transcribe it
    
    Args:
        conversation_id: The ID of the conversation to process
        
    Returns:
        Transcription text, or None if processing fails
    """
    # Download audio
    audio_data = await download_conversation_audio(conversation_id)
    if not audio_data:
        return None
    
    # Transcribe audio
    transcription = await transcribe_audio(audio_data)
    return transcription

