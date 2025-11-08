'use client';

import { useState, useEffect, useRef } from 'react';
import Script from 'next/script';
import CallControls from './CallControls';
import MessageBox from './MessageBox';
import { api, MessageDetails } from '../api/routes';

interface TranscriptionMessage {
  type: string;
  speaker: 'user' | 'agent';
  text: string;
  timestamp: string;
}

export default function PolicyholderView() {
  const [isCallActive, setIsCallActive] = useState(false);
  const [currentClaimId, setCurrentClaimId] = useState<string | null>(null);
  const [message, setMessage] = useState<MessageDetails | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [transcriptions, setTranscriptions] = useState<TranscriptionMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const keepAliveIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptionsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Poll for message updates if we have a claim
    if (currentClaimId && !isCallActive) {
      const interval = setInterval(async () => {
        try {
          const messageData = await api.getMessage(currentClaimId);
          setMessage(messageData);
        } catch (error) {
          console.error('Error fetching message:', error);
        }
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [currentClaimId, isCallActive]);

  const startCall = async () => {
    setIsCallActive(true);
    setIsLoading(true);

    try {
      // Connect to ElevenLabs WebSocket
      const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID || '';
      const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY || '';

      if (!agentId || !apiKey) {
        console.warn('ElevenLabs credentials not configured. Using mock mode.');
        // Mock call for demo
        setTimeout(() => {
          handleMockCall();
        }, 1000);
        return;
      }

      const wsUrl = `wss://api.elevenlabs.io/v1/convai/conversation?agent_id=${agentId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to ElevenLabs');
        // Send authentication
        ws.send(JSON.stringify({
          type: 'authentication',
          api_key: apiKey,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('PolicyholderView (manual WS): Message received:', data.type, data);
          
          if (data.type === 'audio') {
            // Handle audio response
            playAudio(data.audio);
          } else if (data.type === 'conversation_initiation_metadata') {
            console.log('PolicyholderView: Conversation started', data);
            // Store conversation_id for AgentView to connect
            if (data.conversation_id) {
              setConversationId(data.conversation_id);
              localStorage.setItem('currentConversationId', data.conversation_id);
              console.log('PolicyholderView: Conversation ID stored:', data.conversation_id);
            }
          } else if (data.type === 'user_transcript' || data.type === 'user_transcription_event') {
            console.log('PolicyholderView: User transcript received:', data);
            const transcriptText = data.text || data.transcript || data.user_transcript || 
                                 (data.user_transcription_event?.user_transcript) || '';
            
            if (transcriptText) {
              const transcript: TranscriptionMessage = {
                type: 'transcription',
                speaker: 'user',
                text: transcriptText,
                timestamp: new Date().toISOString(),
              };
              console.log('PolicyholderView: Adding user transcript:', transcript);
              setTranscriptions((prev) => [...prev, transcript]);
              // Share with AgentView via localStorage
              localStorage.setItem('latestTranscription', JSON.stringify(transcript));
              window.dispatchEvent(new StorageEvent('storage', {
                key: 'latestTranscription',
                newValue: JSON.stringify(transcript),
              }));
            }
          } else if (data.type === 'agent_transcript' || data.type === 'assistant_transcript' || 
                     data.type === 'agent_transcription_event') {
            console.log('PolicyholderView: Agent transcript received:', data);
            const transcriptText = data.text || data.transcript || data.agent_transcript || 
                                 (data.agent_transcription_event?.agent_transcript) || '';
            
            if (transcriptText) {
              const transcript: TranscriptionMessage = {
                type: 'transcription',
                speaker: 'agent',
                text: transcriptText,
                timestamp: new Date().toISOString(),
              };
              console.log('PolicyholderView: Adding agent transcript:', transcript);
              setTranscriptions((prev) => [...prev, transcript]);
              // Share with AgentView via localStorage
              localStorage.setItem('latestTranscription', JSON.stringify(transcript));
              window.dispatchEvent(new StorageEvent('storage', {
                key: 'latestTranscription',
                newValue: JSON.stringify(transcript),
              }));
            }
          } else {
            console.log('PolicyholderView: Unknown event type:', data.type, data);
          }
        } catch (error) {
          console.error('PolicyholderView: Error parsing WebSocket message:', error, event.data);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Fallback to mock mode
        handleMockCall();
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        setIsCallActive(false);
      };

      wsRef.current = ws;

      // Keep connection alive (send space every 20 seconds)
      keepAliveIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(' ');
        }
      }, 20000);

      // Start audio capture
      startAudioCapture(ws);

    } catch (error) {
      console.error('Error starting call:', error);
      handleMockCall();
    }
  };

  const startAudioCapture = async (ws: WebSocket) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks: Blob[] = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
          // Send audio to WebSocket
          ws.send(event.data);
        }
      };

      mediaRecorder.start(100); // Send chunks every 100ms

      // Store for cleanup
      (ws as any).mediaRecorder = mediaRecorder;
      (ws as any).stream = stream;

    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };

  const playAudio = (audioData: string) => {
    // Decode and play audio
    // This is simplified - in production, you'd decode the base64 audio
    if (audioRef.current) {
      // audioRef.current.src = `data:audio/wav;base64,${audioData}`;
      // audioRef.current.play();
    }
  };

  const handleMockCall = async () => {
    // Simulate a call for demo purposes
    setIsLoading(true);

    // Simulate audio processing
    setTimeout(async () => {
      try {
        // Create a mock claim
        const mockAudioUrl = 'https://example.com/mock-audio.mp3';
        const response = await api.createClaimFromAudio(mockAudioUrl);
        setCurrentClaimId(response.claim_id);
        // Store in localStorage for AgentView to access
        localStorage.setItem('currentClaimId', response.claim_id);

        // Wait a bit then fetch message
        setTimeout(async () => {
          try {
            const messageData = await api.getMessage(response.claim_id);
            setMessage(messageData);
          } catch (error) {
            console.error('Error fetching message:', error);
          }
          setIsLoading(false);
        }, 3000);
      } catch (error) {
        console.error('Error creating claim:', error);
        setIsLoading(false);
      }
    }, 2000);
  };

  const endCall = () => {
    setIsCallActive(false);
    setIsLoading(false);

    // Clear keep-alive interval
    if (keepAliveIntervalRef.current) {
      clearInterval(keepAliveIntervalRef.current);
      keepAliveIntervalRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      const ws = wsRef.current as any;
      if (ws.mediaRecorder) {
        ws.mediaRecorder.stop();
      }
      if (ws.stream) {
        ws.stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clear conversation data
    setConversationId(null);
    setTranscriptions([]);
    localStorage.removeItem('currentConversationId');
  };

  // Auto-scroll to bottom of transcriptions
  useEffect(() => {
    if (transcriptionsEndRef.current) {
      transcriptionsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcriptions]);

  // Poll for post-call transcription from webhook
  useEffect(() => {
    if (!conversationId) return;

    const pollForTranscription = async () => {
      try {
        const transcriptionData = await api.getConversationTranscription(conversationId);
        if (transcriptionData && transcriptionData.transcription) {
          console.log('PolicyholderView: Post-call transcription received:', transcriptionData);
          
          // Parse the transcription and add to transcriptions
          // The transcription might be a full text or structured data
          const fullTranscription = transcriptionData.transcription;
          
          // If it's a JSON string, try to parse it
          let parsedTranscription: any;
          try {
            parsedTranscription = JSON.parse(fullTranscription);
          } catch {
            // If not JSON, treat as plain text
            parsedTranscription = fullTranscription;
          }
          
          // If it's structured with messages or transcript array, extract them
          if (parsedTranscription && typeof parsedTranscription === 'object') {
            let messages: any[] = [];
            
            // Check for different structures
            if (parsedTranscription.messages) {
              messages = parsedTranscription.messages;
            } else if (Array.isArray(parsedTranscription)) {
              messages = parsedTranscription;
            } else if (parsedTranscription.transcript && Array.isArray(parsedTranscription.transcript)) {
              messages = parsedTranscription.transcript;
            }
            
            if (messages.length > 0) {
              const newTranscriptions: TranscriptionMessage[] = messages.map((msg: any) => ({
                type: 'transcription',
                speaker: msg.role === 'user' || msg.speaker === 'user' ? 'user' : 'agent',
                text: msg.text || msg.content || msg.message || '',
                timestamp: msg.timestamp || msg.time_in_call_secs ? new Date(Date.now() - (msg.time_in_call_secs * 1000)).toISOString() : new Date().toISOString(),
              }));
              
              // Only add if we don't already have these transcriptions
              setTranscriptions((prev) => {
                const existingTexts = new Set(prev.map(t => t.text));
                const toAdd = newTranscriptions.filter(t => t.text && !existingTexts.has(t.text));
                return [...prev, ...toAdd];
              });
            }
          } else if (typeof parsedTranscription === 'string') {
            // If it's a plain string, parse the "Agent: message\nUser: message" format
            const lines = parsedTranscription.split('\n').filter(line => line.trim());
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
                // Fallback: try to detect speaker from line content
                const isUser = line.toLowerCase().includes('user:') || line.toLowerCase().startsWith('you:');
                const isAgent = line.toLowerCase().includes('agent:') || line.toLowerCase().includes('assistant:');
                
                // Remove speaker prefixes
                let text = line.replace(/^(user|agent|assistant|you):\s*/i, '').trim();
                
                return {
                  type: 'transcription',
                  speaker: isUser ? 'user' : (isAgent ? 'agent' : 'user'), // Default to user if unclear
                  text: text || line,
                  timestamp: new Date().toISOString(),
                };
              }
            });
            
            // Replace all transcriptions with the new ones (webhook has complete transcript)
            setTranscriptions((prev) => {
              // Check if we already have the same transcriptions
              if (prev.length === newTranscriptions.length && 
                  prev.every((p, i) => p.text === newTranscriptions[i]?.text)) {
                return prev;
              }
              return newTranscriptions;
            });
          }
        }
      } catch (error: any) {
        // Transcription not available yet - this is expected until webhook is received
        if (error.response?.status !== 404) {
          console.error('PolicyholderView: Error fetching transcription:', error);
        }
      }
    };

    // Poll every 5 seconds for transcription (webhook might arrive after call ends)
    const interval = setInterval(pollForTranscription, 5000);
    
    // Also check immediately
    pollForTranscription();

    return () => clearInterval(interval);
  }, [conversationId]);

  const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID || '';
  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY || '';

  // Poll for the latest conversation from the backend (webhook will provide it)
  useEffect(() => {
    if (!agentId) return;

    console.log('PolicyholderView: Setting up conversation polling');
    
    // Check localStorage for any stored conversation ID first
    const checkStoredConversation = () => {
      const stored = localStorage.getItem('currentConversationId');
      if (stored && !conversationId) {
        console.log('PolicyholderView: Found stored conversationId:', stored);
        setConversationId(stored);
      }
    };

    // Also check backend for latest conversation
    const checkLatestConversation = async () => {
      try {
        const latest = await api.getLatestConversation();
        if (latest && latest.conversation_id && latest.conversation_id !== conversationId) {
          console.log('PolicyholderView: Found latest conversation from backend:', latest.conversation_id);
          setConversationId(latest.conversation_id);
          localStorage.setItem('currentConversationId', latest.conversation_id);
          // Trigger storage event manually for same-tab communication
          window.dispatchEvent(new StorageEvent('storage', {
            key: 'currentConversationId',
            newValue: latest.conversation_id,
            oldValue: null,
          }));
        }
      } catch (error: any) {
        // No conversation yet - this is expected
        if (error.response?.status !== 404) {
          console.error('PolicyholderView: Error fetching latest conversation:', error);
        }
      }
    };

    checkStoredConversation();
    checkLatestConversation();

    // Poll every 3 seconds to check if a new conversation was detected
    const pollInterval = setInterval(() => {
      checkStoredConversation();
      checkLatestConversation();
    }, 3000);

    return () => {
      clearInterval(pollInterval);
    };
  }, [agentId, conversationId]);

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px', color: '#333' }}>Policyholder View</h1>

      {/* ElevenLabs Agent Widget */}
      {agentId && (
        <>
          <Script
            src="https://unpkg.com/@elevenlabs/convai-widget-embed"
            strategy="lazyOnload"
onLoad={() => {
              console.log('PolicyholderView: ElevenLabs widget script loaded');
              
              // The widget handles the conversation internally
              // We'll get the conversation_id from the webhook after the call ends
              console.log('PolicyholderView: Widget will handle conversation. Transcription will be available after call via webhook.');
            }}
          />
          <elevenlabs-convai agent-id={agentId}></elevenlabs-convai>
        </>
      )}

      {/* Legacy Call Controls (kept for fallback) */}
      {!agentId && (
        <CallControls
          onStartCall={startCall}
          onEndCall={endCall}
          isCallActive={isCallActive}
        />
      )}

      {isLoading && (
        <div style={{ marginBottom: '20px', color: '#666' }}>
          Processing your call...
        </div>
      )}

      <div style={{ marginTop: '30px' }}>
        <h2 style={{ marginBottom: '15px', color: '#333' }}>Message</h2>
        <MessageBox
          assessment={message?.message.assessment}
          nextActions={message?.message.next_actions}
          sentAt={message?.message.sent_at}
        />
      </div>

      {/* Conversation Transcription (Post-Call) */}
      <div style={{ marginTop: '30px' }}>
        <h2 style={{ marginBottom: '15px', color: '#333' }}>Conversation Transcript</h2>
        <div style={{ 
          backgroundColor: '#f9f9f9', 
          borderRadius: '8px', 
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
                  <div>📝 Transcription will appear here after the call ends</div>
                  <div style={{ fontSize: '11px', marginTop: '8px', color: '#999' }}>
                    Conversation ID: {conversationId.substring(0, 20)}...
                  </div>
                </>
              ) : (
                'Start a call to see the transcription'
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
                  {transcript.speaker === 'user' ? '👤 You' : '🤖 Agent'}
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

      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

