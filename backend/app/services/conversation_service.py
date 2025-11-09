"""
Conversation service for managing conversation transcriptions.

Handles in-memory storage, file persistence, and retrieval of conversation data.
"""
import os
import json
from typing import Dict, Optional, List
from datetime import datetime
from fastapi import HTTPException
from app.models import ConversationTranscription


# In-memory storage for conversation transcriptions
conversation_transcriptions: Dict[str, ConversationTranscription] = {}


def get_conversations_directory() -> str:
    """
    Get the path to the conversations directory.
    
    Returns:
        Absolute path to conversations directory
    """
    current_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(current_dir, 'data', 'conversations')


def save_conversation_to_file(
    conversation_id: str,
    transcription: str,
    metadata: Dict
) -> str:
    """
    Save conversation to a JSON file.
    
    Args:
        conversation_id: Unique conversation identifier
        transcription: Full transcription text
        metadata: Additional metadata (transcript_array, webhook_type, etc.)
        
    Returns:
        Path to the saved file
        
    Raises:
        Exception: If file save fails
    """
    conversations_dir = get_conversations_directory()
    os.makedirs(conversations_dir, exist_ok=True)
    
    conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
    
    data = {
        "conversation_id": conversation_id,
        "transcription": transcription,
        "received_at": datetime.now().isoformat(),
        **metadata  # Include all metadata (raw_transcript, webhook_type, etc.)
    }
    
    with open(conversation_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Saved conversation to file: {conversation_file}")
    print(f"  - {metadata.get('transcript_entry_count', 0)} transcript entries")
    print(f"  - {metadata.get('transcription_parts_count', 0)} processed parts")
    print(f"  - {len(transcription)} total characters")
    
    return conversation_file


def load_conversation_from_file(conversation_id: str) -> Optional[Dict]:
    """
    Load conversation from a JSON file.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        Dictionary with conversation data or None if not found
    """
    conversations_dir = get_conversations_directory()
    conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
    
    if not os.path.exists(conversation_file):
        return None
    
    try:
        with open(conversation_file, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading conversation from file: {e}")
        return None


def get_latest_conversation_from_files() -> Optional[Dict]:
    """
    Find the most recent conversation from filesystem.
    
    Returns:
        Dictionary with latest conversation data or None if not found
    """
    conversations_dir = get_conversations_directory()
    
    if not os.path.exists(conversations_dir):
        return None
    
    files = [f for f in os.listdir(conversations_dir) 
             if f.endswith('.json') and not f.startswith('.')]
    
    if not files:
        return None
    
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
    
    if not conversations:
        return None
    
    # Sort by received_at timestamp (most recent first)
    latest = max(conversations, key=lambda x: x.get('received_at', ''))
    print(f"✓ Found latest conversation: {latest['conversation_id']} "
          f"(received_at: {latest.get('received_at')})")
    
    return latest


def list_all_conversations() -> List[Dict]:
    """
    List all saved conversations.
    
    Returns:
        List of conversation dictionaries, sorted by received_at (newest first)
    """
    conversations_dir = get_conversations_directory()
    
    if not os.path.exists(conversations_dir):
        return []
    
    files = [f for f in os.listdir(conversations_dir) 
             if f.endswith('.json') and not f.startswith('.')]
    
    conversations = []
    for filename in files:
        file_path = os.path.join(conversations_dir, filename)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'conversation_id' in data:
                    conversations.append(data)
        except Exception as e:
            print(f"Warning: Could not load conversation file {filename}: {e}")
            continue
    
    # Sort by received_at timestamp (most recent first)
    conversations.sort(key=lambda x: x.get('received_at', ''), reverse=True)
    
    return conversations


def store_conversation_in_memory(
    conversation_id: str,
    transcription: str,
    received_at: Optional[datetime] = None
) -> ConversationTranscription:
    """
    Store conversation in in-memory cache.
    
    Args:
        conversation_id: Unique conversation identifier
        transcription: Full transcription text
        received_at: Timestamp of when conversation was received
        
    Returns:
        ConversationTranscription object
    """
    conversation = ConversationTranscription(
        conversation_id=conversation_id,
        transcription=transcription,
        received_at=received_at or datetime.now()
    )
    
    conversation_transcriptions[conversation_id] = conversation
    
    return conversation


def get_conversation_from_memory(conversation_id: str) -> Optional[ConversationTranscription]:
    """
    Get conversation from in-memory cache.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        ConversationTranscription object or None if not found
    """
    return conversation_transcriptions.get(conversation_id)


def get_latest_conversation_from_memory() -> Optional[ConversationTranscription]:
    """
    Get the most recent conversation from in-memory cache.
    
    Returns:
        ConversationTranscription object or None if cache is empty
    """
    if not conversation_transcriptions:
        return None
    
    return max(conversation_transcriptions.values(), key=lambda x: x.received_at)


def get_conversation(conversation_id: str) -> Dict:
    """
    Get conversation from memory or file.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        Dictionary with conversation data
        
    Raises:
        HTTPException: If conversation not found
    """
    # First check in-memory storage
    conversation = get_conversation_from_memory(conversation_id)
    
    if conversation:
        return {
            "conversation_id": conversation.conversation_id,
            "transcription": conversation.transcription,
            "received_at": conversation.received_at.isoformat()
        }
    
    # If not in memory, try loading from file
    data = load_conversation_from_file(conversation_id)
    
    if data:
        return {
            "conversation_id": data["conversation_id"],
            "transcription": data["transcription"],
            "received_at": data["received_at"]
        }
    
    raise HTTPException(status_code=404, detail="Transcription not found")


def get_latest_conversation() -> Dict:
    """
    Get the most recent conversation from memory or filesystem.
    
    Returns:
        Dictionary with latest conversation data
        
    Raises:
        HTTPException: If no conversations found
    """
    # Check in-memory storage first
    conversation = get_latest_conversation_from_memory()
    
    if conversation:
        return {
            "conversation_id": conversation.conversation_id,
            "transcription": conversation.transcription,
            "received_at": conversation.received_at.isoformat()
        }
    
    # If nothing in memory, check file system
    data = get_latest_conversation_from_files()
    
    if data:
        return {
            "conversation_id": data["conversation_id"],
            "transcription": data["transcription"],
            "received_at": data["received_at"]
        }
    
    raise HTTPException(status_code=404, detail="No conversations found")

