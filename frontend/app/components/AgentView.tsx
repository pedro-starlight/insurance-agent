'use client';

import { useState, useEffect, useRef } from 'react';
import ClaimInterface from './ClaimInterface';
import SystemLogs from './SystemLogs';
import { api } from '../api/routes';

interface TranscriptionMessage {
  type: string;
  speaker: 'user' | 'agent';
  text: string;
  timestamp: string;
}

export default function AgentView() {
  const [currentClaimId, setCurrentClaimId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [transcriptions, setTranscriptions] = useState<TranscriptionMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const keepAliveIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptionsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Poll for new claims (in production, use WebSocket)
    const interval = setInterval(async () => {
      try {
        // In a real app, you'd have an endpoint to get the latest claim
        // For now, we'll rely on the claim being set from the policyholder view
        // This is a simplified version
      } catch (error) {
        // Silently fail - no claims yet
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleClaimApproved = () => {
    // Claim approved, could show success message
    console.log('Claim approved');
  };

  // Get claim ID and conversation ID from localStorage and listen for updates
  useEffect(() => {
    const checkForClaim = () => {
      const storedClaimId = localStorage.getItem('currentClaimId');
      if (storedClaimId && storedClaimId !== currentClaimId) {
        setCurrentClaimId(storedClaimId);
      }
    };

    const checkForConversation = async () => {
      const storedConversationId = localStorage.getItem('currentConversationId');
      console.log('AgentView: Checking localStorage for conversationId:', storedConversationId, 'current:', conversationId);
      
      if (storedConversationId) {
        if (storedConversationId !== conversationId) {
          console.log('AgentView: Found new conversationId in localStorage:', storedConversationId);
          setConversationId(storedConversationId);
          connectToWebSocket(storedConversationId);
        }
      } else {
        console.log('AgentView: No conversationId in localStorage, checking backend...');
        // Check backend for latest conversation
        try {
          const latest = await api.getLatestConversation();
          if (latest && latest.conversation_id && latest.conversation_id !== conversationId) {
            console.log('AgentView: Found latest conversation from backend:', latest.conversation_id);
            setConversationId(latest.conversation_id);
            localStorage.setItem('currentConversationId', latest.conversation_id);
          }
        } catch (error: any) {
          // No conversation yet - this is expected
          if (error.response?.status !== 404) {
            console.error('AgentView: Error fetching latest conversation:', error);
          }
        }
      }
    };

    // Check immediately
    checkForClaim();
    checkForConversation();

    // Listen for storage changes (cross-tab communication)
    const handleStorageChange = (e: StorageEvent) => {
      console.log('AgentView: Storage event:', e.key, e.newValue);
      if (e.key === 'currentClaimId') {
        setCurrentClaimId(e.newValue);
      } else if (e.key === 'currentConversationId') {
        console.log('AgentView: Storage event - conversationId changed to:', e.newValue);
        if (e.newValue) {
          setConversationId(e.newValue);
          connectToWebSocket(e.newValue);
        }
      } else if (e.key === 'latestTranscription') {
        // Handle real-time transcription updates from PolicyholderView
        if (e.newValue) {
          try {
            const transcript: TranscriptionMessage = JSON.parse(e.newValue);
            setTranscriptions((prev) => {
              // Avoid duplicates
              const exists = prev.some(t => 
                t.text === transcript.text && 
                t.timestamp === transcript.timestamp
              );
              return exists ? prev : [...prev, transcript];
            });
          } catch (error) {
            console.error('Error parsing transcription:', error);
          }
        }
      }
    };

    // Also poll localStorage in case storage event doesn't fire (same tab)
    // Poll more frequently initially, then slow down
    const interval = setInterval(() => {
      checkForClaim();
      checkForConversation();
    }, 500); // Check every 500ms for faster detection

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentClaimId, conversationId]);

  // Connect to ElevenLabs WebSocket to receive transcription events
  const connectToWebSocket = (convId: string) => {
    // Don't reconnect if already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID || '';
    const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY || '';

    if (!agentId || !apiKey || !convId) {
      return;
    }

    try {
      // Connect to the same conversation using conversation_id
      const wsUrl = `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=${agentId}&conversation_id=${convId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('AgentView: Connected to ElevenLabs WebSocket');
        // Send authentication
        ws.send(JSON.stringify({
          type: 'authentication',
          api_key: apiKey,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('AgentView: WebSocket message received:', data.type, data);
          
          // Handle transcription events
          if (data.type === 'user_transcript' || data.type === 'user_transcription_event') {
            console.log('AgentView: User transcript received:', data);
            const transcriptText = data.text || data.transcript || data.user_transcript || 
                                 (data.user_transcription_event?.user_transcript) || '';
            
            if (transcriptText) {
              const transcript: TranscriptionMessage = {
                type: 'transcription',
                speaker: 'user',
                text: transcriptText,
                timestamp: new Date().toISOString(),
              };
              console.log('AgentView: Adding user transcript:', transcript);
              setTranscriptions((prev) => {
                const exists = prev.some(t => 
                  t.text === transcript.text && 
                  t.timestamp === transcript.timestamp
                );
                return exists ? prev : [...prev, transcript];
              });
            }
          } else if (data.type === 'agent_transcript' || data.type === 'assistant_transcript' || 
                     data.type === 'agent_transcription_event') {
            console.log('AgentView: Agent transcript received:', data);
            const transcriptText = data.text || data.transcript || data.agent_transcript || 
                                 (data.agent_transcription_event?.agent_transcript) || '';
            
            if (transcriptText) {
              const transcript: TranscriptionMessage = {
                type: 'transcription',
                speaker: 'agent',
                text: transcriptText,
                timestamp: new Date().toISOString(),
              };
              console.log('AgentView: Adding agent transcript:', transcript);
              setTranscriptions((prev) => {
                const exists = prev.some(t => 
                  t.text === transcript.text && 
                  t.timestamp === transcript.timestamp
                );
                return exists ? prev : [...prev, transcript];
              });
            }
          } else {
            console.log('AgentView: Unknown event type:', data.type, data);
          }
        } catch (error) {
          console.error('AgentView: Error parsing WebSocket message:', error, event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('AgentView: WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('AgentView: WebSocket closed');
        wsRef.current = null;
      };

      wsRef.current = ws;

      // Keep connection alive
      keepAliveIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(' ');
        }
      }, 20000);

    } catch (error) {
      console.error('AgentView: Error connecting to WebSocket:', error);
    }
  };

  // Poll for post-call transcription from webhook
  useEffect(() => {
    if (!conversationId) {
      console.log('AgentView: No conversationId, skipping transcription polling');
      return;
    }

    console.log('AgentView: Starting transcription polling for conversationId:', conversationId);

    const pollForTranscription = async () => {
      try {
        console.log('AgentView: Polling for transcription, conversationId:', conversationId);
        const transcriptionData = await api.getConversationTranscription(conversationId);
        console.log('AgentView: Transcription data received:', transcriptionData);
        
        if (transcriptionData && transcriptionData.transcription) {
          console.log('AgentView: Post-call transcription received, length:', transcriptionData.transcription.length);
          
          // Parse the transcription text (format: "Agent: message\nUser: message")
          const fullTranscription = transcriptionData.transcription;
          console.log('AgentView: Full transcription text:', fullTranscription.substring(0, 200) + '...');
          
          // Split by lines and parse speaker labels
          const lines = fullTranscription.split('\n').filter(line => line.trim());
          console.log('AgentView: Parsed', lines.length, 'transcription lines');
          
          const newTranscriptions: TranscriptionMessage[] = lines.map((line: string) => {
            // Parse format: "Agent: message" or "User: message"
            const agentMatch = line.match(/^Agent:\s*(.+)$/);
            const userMatch = line.match(/^User:\s*(.+)$/);
            
            if (agentMatch) {
              return {
                type: 'transcription',
                speaker: 'agent',
                text: agentMatch[1],
                timestamp: new Date().toISOString(),
              };
            } else if (userMatch) {
              return {
                type: 'transcription',
                speaker: 'user',
                text: userMatch[1],
                timestamp: new Date().toISOString(),
              };
            } else {
              // Fallback: treat as user message if no label found
              return {
                type: 'transcription',
                speaker: 'user',
                text: line,
                timestamp: new Date().toISOString(),
              };
            }
          });
          
          console.log('AgentView: Created', newTranscriptions.length, 'transcription messages');
          
          // Replace all transcriptions with the new ones (webhook has complete transcript)
          setTranscriptions((prev) => {
            // Check if we already have the same transcriptions
            if (prev.length === newTranscriptions.length && 
                prev.every((p, i) => p.text === newTranscriptions[i]?.text)) {
              console.log('AgentView: Transcriptions already up to date');
              return prev;
            }
            
            console.log('AgentView: Updating transcriptions, new count:', newTranscriptions.length);
            return newTranscriptions;
          });
        }
      } catch (error: any) {
        // Transcription not available yet - this is expected until webhook is received
        if (error.response?.status === 404) {
          console.log('AgentView: Transcription not found yet (404), will keep polling...');
        } else {
          console.error('AgentView: Error fetching transcription:', error);
          if (error.response) {
            console.error('AgentView: Error response:', error.response.status, error.response.data);
          }
        }
      }
    };

    // Poll every 5 seconds for transcription (webhook might arrive after call ends)
    const interval = setInterval(pollForTranscription, 5000);
    
    // Also check immediately
    pollForTranscription();

    return () => {
      console.log('AgentView: Cleaning up transcription polling');
      clearInterval(interval);
    };
  }, [conversationId]);

  // Auto-scroll to bottom of transcriptions
  useEffect(() => {
    if (transcriptionsEndRef.current) {
      transcriptionsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcriptions]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (keepAliveIntervalRef.current) {
        clearInterval(keepAliveIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return (
    <div style={{ padding: '20px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ marginBottom: '20px', color: '#333' }}>Insurance Agent View</h1>
      {conversationId && (
        <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px', fontSize: '12px', color: '#1976d2' }}>
          📞 Active Conversation ID: {conversationId} | Transcriptions: {transcriptions.length}
        </div>
      )}
      <div style={{ display: 'flex', gap: '20px', flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
            <ClaimInterface claimId={currentClaimId} onClaimApproved={handleClaimApproved} />
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '20px', borderTop: '1px solid #eee' }}>
            <h2 style={{ marginBottom: '15px', color: '#333', fontSize: '18px' }}>Real-Time Conversation</h2>
            <div style={{ 
              backgroundColor: '#f9f9f9', 
              borderRadius: '4px', 
              padding: '15px', 
              maxHeight: '400px', 
              overflowY: 'auto',
              border: '1px solid #e0e0e0',
              fontFamily: 'monospace',
              fontSize: '14px'
            }}>
              {transcriptions.length === 0 ? (
                <div style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
                  {conversationId ? (
                    <>
                      <div>📝 Waiting for post-call transcription...</div>
                      <div style={{ fontSize: '11px', marginTop: '8px', color: '#999' }}>
                        Conversation ID: {conversationId.substring(0, 20)}...
                      </div>
                      <div style={{ fontSize: '11px', marginTop: '4px', color: '#999' }}>
                        Polling backend every 5 seconds for webhook data...
                      </div>
                      <div style={{ fontSize: '11px', marginTop: '4px', color: '#666', fontStyle: 'normal' }}>
                        💡 Transcription will appear here after the call ends
                      </div>
                    </>
                  ) : (
                    'No active conversation. Waiting for call to start...'
                  )}
                </div>
              ) : (
                transcriptions.map((transcript, index) => (
                  <div 
                    key={index} 
                    style={{ 
                      marginBottom: '12px',
                      padding: '10px',
                      backgroundColor: transcript.speaker === 'user' ? '#e3f2fd' : '#f1f8e9',
                      borderRadius: '6px',
                      borderLeft: `4px solid ${transcript.speaker === 'user' ? '#2196f3' : '#4caf50'}`
                    }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '6px', color: transcript.speaker === 'user' ? '#1976d2' : '#388e3c', fontSize: '12px' }}>
                      {transcript.speaker === 'user' ? '👤 Policyholder' : '🤖 Agent'}
                    </div>
                    <div style={{ color: '#333', lineHeight: '1.5' }}>{transcript.text}</div>
                    <div style={{ fontSize: '11px', color: '#999', marginTop: '6px' }}>
                      {new Date(transcript.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))
              )}
              <div ref={transcriptionsEndRef} />
            </div>
          </div>
        </div>
        <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <SystemLogs claimId={currentClaimId} />
        </div>
      </div>
    </div>
  );
}

