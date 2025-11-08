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
  connectionStatus?: 'connected' | 'disconnected' | 'connecting' | 'error';
}

export default function SystemLogs({ claimId, logs, connectionStatus = 'disconnected' }: SystemLogsProps) {
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

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return '#28a745';
      case 'connecting':
        return '#ffc107';
      case 'error':
        return '#dc3545';
      default:
        return '#6c757d';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return '● Connected';
      case 'connecting':
        return '● Connecting...';
      case 'error':
        return '● Connection Error';
      default:
        return '● Disconnected';
    }
  };

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h2 style={{ margin: 0, color: '#333' }}>Agent Execution Logs</h2>
        {claimId && (
          <div style={{ 
            fontSize: '11px', 
            color: getConnectionStatusColor(),
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span>{getConnectionStatusText()}</span>
            <span style={{ color: '#666', fontWeight: 'normal' }}>({logs.length} logs)</span>
          </div>
        )}
      </div>
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
            {claimId ? (
              <>
                <div style={{ marginBottom: '8px' }}>🔄 Waiting for agent to start processing...</div>
                <div style={{ fontSize: '10px', marginBottom: '4px' }}>
                  Connection: <span style={{ color: getConnectionStatusColor() }}>{getConnectionStatusText()}</span>
                </div>
                <div style={{ fontSize: '10px' }}>Logs will stream in real-time</div>
              </>
            ) : (
              <>
                <div style={{ marginBottom: '8px' }}>No active claim</div>
                <div style={{ fontSize: '10px' }}>Logs will appear here when processing starts</div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
