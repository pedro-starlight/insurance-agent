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
  const audioRef = useRef<HTMLAudioElement | null>(null);

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
              localStorage.setItem('currentConversationId', data.conversation_id);
              console.log('PolicyholderView: Conversation ID stored:', data.conversation_id);
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

    // Clear conversation data in localStorage
    localStorage.removeItem('currentConversationId');
  };


  const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID || '';
  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY || '';

  // Clear conversation when starting a new call (widget loads)
  useEffect(() => {
    if (!agentId) return;

    const handleNewCall = () => {
      console.log('PolicyholderView: New call starting, clearing previous conversation');
      // Clear previous conversation data in localStorage
      localStorage.removeItem('currentConversationId');
      // Notify other tabs to clear their conversation
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'clearConversation',
        newValue: Date.now().toString(),
      }));
    };

    // Listen for widget events if it exposes them
    // For now, we'll detect new calls when the widget is clicked
    // This is a simplified approach - in production, you'd use widget events
    const widget = document.querySelector('elevenlabs-convai');
    if (widget) {
      widget.addEventListener('click', handleNewCall);
      return () => widget.removeEventListener('click', handleNewCall);
    }
  }, [agentId]);

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

      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

