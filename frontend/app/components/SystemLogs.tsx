'use client';

import { useEffect, useRef } from 'react';

export interface SystemLog {
  timestamp: string;
  type: string;
  message: string;
}

interface SystemLogsProps {
  claimId: string | null;
  logs: SystemLog[];
}

export default function SystemLogs({ claimId, logs }: SystemLogsProps) {
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const getLogColor = (type: string) => {
    switch (type) {
      case 'info':
        return '#007bff';
      case 'success':
        return '#28a745';
      case 'warning':
        return '#ffc107';
      case 'error':
        return '#dc3545';
      default:
        return '#666';
    }
  };

  if (!claimId) {
    return (
      <div style={{ padding: '20px' }}>
        <h2 style={{ marginBottom: '15px', color: '#333' }}>Agent Execution Logs</h2>
        <div
          style={{
            padding: '20px',
            border: '2px dashed #ccc',
            borderRadius: '8px',
            textAlign: 'center',
            color: '#999',
          }}
        >
          No active claim. Logs will appear here when processing starts.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ marginBottom: '15px', color: '#333' }}>Agent Execution Logs</h2>
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          backgroundColor: '#1e1e1e',
          borderRadius: '8px',
          padding: '15px',
          fontFamily: 'monospace',
          fontSize: '12px',
        }}
      >
        {logs.length > 0 ? (
          <>
            {logs.map((log, index) => (
              <div
                key={index}
                style={{
                  marginBottom: '8px',
                  padding: '8px',
                  borderLeft: `3px solid ${getLogColor(log.type)}`,
                  backgroundColor: '#2d2d2d',
                  borderRadius: '4px',
                }}
              >
                <div style={{ color: '#7f8c8d', fontSize: '10px', marginBottom: '4px' }}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </div>
                <div
                  style={{
                    color: log.type === 'error' ? '#e74c3c' : log.type === 'success' ? '#2ecc71' : '#ecf0f1',
                  }}
                >
                  {log.message}
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </>
        ) : (
          <div style={{ color: '#7f8c8d', textAlign: 'center', padding: '20px' }}>
            <div style={{ marginBottom: '8px' }}>🔄 Waiting for agent to start processing...</div>
            <div style={{ fontSize: '10px' }}>Logs will stream in real-time via SSE</div>
          </div>
        )}
      </div>
    </div>
  );
}
