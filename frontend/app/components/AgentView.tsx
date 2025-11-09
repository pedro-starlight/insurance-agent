'use client';

import { useState, useEffect, useRef } from 'react';
import ClaimInterface from './ClaimInterface';
import SystemLogs, { SystemLog } from './SystemLogs';
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
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [sseConnectionStatus, setSseConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'error'>('disconnected');
  // wsRef and keepAliveIntervalRef removed - no longer using WebSocket for transcription
  const transcriptionsEndRef = useRef<HTMLDivElement | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

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
          // WebSocket connection removed - we now use post-call webhook transcription
          
          // Try to get claim_id from conversation_id
          try {
            const claimData = await api.getClaimFromConversation(storedConversationId);
            if (claimData && claimData.claim_id) {
              console.log('AgentView: Found claim_id from conversation:', claimData.claim_id);
              setCurrentClaimId(claimData.claim_id);
              localStorage.setItem('currentClaimId', claimData.claim_id);
            }
          } catch (error: any) {
            // Claim might not be created yet - this is expected during active calls
            if (error.response?.status !== 404) {
              console.error('AgentView: Error fetching claim from conversation:', error);
            }
          }
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
            
            // Try to get claim_id from conversation_id
            try {
              const claimData = await api.getClaimFromConversation(latest.conversation_id);
              if (claimData && claimData.claim_id) {
                console.log('AgentView: Found claim_id from conversation:', claimData.claim_id);
                setCurrentClaimId(claimData.claim_id);
                localStorage.setItem('currentClaimId', claimData.claim_id);
              }
            } catch (error: any) {
              // Claim might not be created yet
              if (error.response?.status !== 404) {
                console.error('AgentView: Error fetching claim from conversation:', error);
              }
            }
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
          // WebSocket connection removed - we now use post-call webhook transcription
        }
      } else if (e.key === 'clearConversation') {
        // Clear conversation when new call starts
        console.log('AgentView: Clearing conversation for new call');
        setConversationId(null);
        setCurrentClaimId(null);
        setTranscriptions([]);
        setLogs([]);
        localStorage.removeItem('currentClaimId');
        localStorage.removeItem('currentConversationId');
      }
    };

    // Also poll localStorage in case storage event doesn't fire (same tab)
    // Poll more frequently for active calls
    const interval = setInterval(() => {
      checkForClaim();
      checkForConversation();
    }, 1000); // Check every 1 second for active calls

    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentClaimId, conversationId]);

  // WebSocket connection removed - we now rely on post-call webhook transcription
  // The PolicyholderView widget handles the real-time conversation
  // AgentView polls for the complete transcription from the backend after the call ends

  // Poll for transcription - more frequently during active calls
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
          console.log('AgentView: Transcription received, length:', transcriptionData.transcription.length);
          
          // Parse the transcription text (format: "Agent: message\nUser: message")
          const fullTranscription = transcriptionData.transcription;
          console.log('AgentView: Full transcription text:', fullTranscription.substring(0, 200) + '...');
          console.log('AgentView: Transcription length:', fullTranscription.length);
          console.log('AgentView: Contains newlines:', fullTranscription.includes('\n'));
          console.log('AgentView: Newline count:', (fullTranscription.match(/\n/g) || []).length);
          
          // Split by lines and parse speaker labels
          const lines = fullTranscription.split('\n').filter(line => line.trim());
          console.log('AgentView: Parsed', lines.length, 'transcription lines');
          console.log('AgentView: First 3 lines:', lines.slice(0, 3));
          
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
            
            // Detect if this is a more complete transcription
            const isMoreComplete = prev.length > 0 && newTranscriptions.length > prev.length + 5;
            
            if (isMoreComplete && conversationId) {
              console.log('AgentView: Detected more complete transcription, refreshing claim_id');
              // Refresh claim_id asynchronously
              (async () => {
                try {
                  const claimData = await api.getClaimFromConversation(conversationId);
                  if (claimData && claimData.claim_id !== currentClaimId) {
                    console.log('AgentView: Updated to new claim_id:', claimData.claim_id);
                    setCurrentClaimId(claimData.claim_id);
                    localStorage.setItem('currentClaimId', claimData.claim_id);
                  }
                } catch (error) {
                  console.error('Error refreshing claim_id:', error);
                }
              })();
            }
            
            return newTranscriptions;
          });
          
          // Also try to get claim_id if we don't have it yet
          if (!currentClaimId) {
            try {
              const claimData = await api.getClaimFromConversation(conversationId);
              if (claimData && claimData.claim_id) {
                console.log('AgentView: Found claim_id from conversation during transcription poll:', claimData.claim_id);
                setCurrentClaimId(claimData.claim_id);
                localStorage.setItem('currentClaimId', claimData.claim_id);
              }
            } catch (error: any) {
              // Claim might not be created yet
              if (error.response?.status !== 404) {
                console.error('AgentView: Error fetching claim from conversation:', error);
              }
            }
          }
        }
      } catch (error: any) {
        // Transcription not available yet - this is expected until webhook is received
        if (error.response?.status === 404) {
          // During active calls, transcription might not be available yet
          // This is normal, so we'll keep polling
        } else {
          console.error('AgentView: Error fetching transcription:', error);
          if (error.response) {
            console.error('AgentView: Error response:', error.response.status, error.response.data);
          }
        }
      }
    };

    // Poll more frequently during active calls (every 2 seconds)
    // This helps catch transcription updates quickly for active/hanging calls
    const interval = setInterval(pollForTranscription, 2000);
    
    // Also check immediately
    pollForTranscription();

    return () => {
      console.log('AgentView: Cleaning up transcription polling');
      clearInterval(interval);
    };
  }, [conversationId, currentClaimId]);

  // Auto-scroll to bottom of transcriptions
  useEffect(() => {
    if (transcriptionsEndRef.current) {
      transcriptionsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcriptions]);

  // SSE connection for real-time agent logs
  useEffect(() => {
    if (!currentClaimId) {
      setSseConnectionStatus('disconnected');
      setLogs([]);
      return;
    }

    console.log('AgentView: Setting up SSE connection for claim:', currentClaimId);
    setSseConnectionStatus('connecting');
    
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    // Create EventSource for SSE
    const eventSource = new EventSource(`http://localhost:8000/claim/stream/${currentClaimId}`);
    
    eventSource.onopen = () => {
      console.log('AgentView: SSE connection opened');
      setSseConnectionStatus('connected');
    };
    
    eventSource.onmessage = (event) => {
      try {
        // Skip keepalive messages
        if (event.data.trim() === '' || event.data.startsWith(':')) {
          return;
        }
        
        const log: SystemLog = JSON.parse(event.data);
        console.log('AgentView: SSE log received:', log);
        setLogs((prev) => {
          // Avoid duplicates
          const exists = prev.some(l => 
            l.timestamp === log.timestamp && 
            l.message === log.message
          );
          return exists ? prev : [...prev, log];
        });
      } catch (error) {
        console.error('AgentView: Error parsing SSE message:', error, event.data);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('AgentView: SSE error:', error);
      setSseConnectionStatus('error');
      
      // Try to reconnect after a delay
      setTimeout(() => {
        if (currentClaimId && eventSourceRef.current?.readyState === EventSource.CLOSED) {
          console.log('AgentView: Attempting to reconnect SSE...');
          setSseConnectionStatus('connecting');
          // The useEffect will run again and create a new connection
        }
      }, 3000);
    };
    
    eventSourceRef.current = eventSource;
    
    return () => {
      console.log('AgentView: Closing SSE connection');
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setSseConnectionStatus('disconnected');
    };
  }, [currentClaimId]);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      // WebSocket cleanup removed - no longer using WebSocket
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  return (
    <div style={{ padding: '20px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ marginBottom: '20px', color: '#333' }}>Insurance Agent View</h1>
      {(currentClaimId || conversationId) && (
        <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px', fontSize: '12px', color: '#1976d2' }}>
          {conversationId && (
            <span>📞 Conversation: {conversationId.substring(0, 20)}...</span>
          )}
          {conversationId && currentClaimId && <span> | </span>}
          {currentClaimId && (
            <span>📋 Claim: {currentClaimId.substring(0, 20)}...</span>
          )}
          {(currentClaimId || conversationId) && <span> | </span>}
          <span>📝 Logs: {logs.length} | Transcriptions: {transcriptions.length}</span>
        </div>
      )}
      <div style={{ display: 'flex', gap: '20px', flex: 1, minHeight: 0 }}>
        {/* Left Panel - Claim Details (Full Height) */}
        <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', overflow: 'auto' }}>
          <ClaimInterface claimId={currentClaimId} onClaimApproved={handleClaimApproved} />
        </div>

        {/* Right Panel - Call Transcription (Top) and Agent Logs (Bottom) */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Call Transcription - Top Right */}
          <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #eee' }}>
              <h2 style={{ margin: 0, color: '#333', fontSize: '18px' }}>Call Transcription</h2>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
              <div style={{ 
                backgroundColor: '#f9f9f9', 
                borderRadius: '4px', 
                padding: '15px', 
                minHeight: '100%',
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

          {/* Agent Execution Logs - Bottom Right */}
          <div style={{ flex: 1, backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', minHeight: 0 }}>
            <SystemLogs claimId={currentClaimId} logs={logs} connectionStatus={sseConnectionStatus} />
          </div>
        </div>
      </div>
    </div>
  );
}

