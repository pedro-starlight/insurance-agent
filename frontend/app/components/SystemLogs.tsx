'use client';

import { useState, useEffect, useRef } from 'react';
import { api, SystemLog } from '../api/routes';

interface SystemLogsProps {
  claimId: string | null;
}

export default function SystemLogs({ claimId }: SystemLogsProps) {
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (claimId) {
      fetchLogs();
      // Poll for new logs
      const interval = setInterval(fetchLogs, 1000);
      return () => clearInterval(interval);
    } else {
      setLogs([]);
    }
  }, [claimId]);

  useEffect(() => {
    // Auto-scroll to bottom
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchLogs = async () => {
    if (!claimId) return;

    try {
      const response = await api.getLogs(claimId);
      setLogs(response.logs);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

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
      <div
        style={{
          padding: '20px',
          border: '2px dashed #ccc',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#999',
          height: '100%',
        }}
      >
        No logs available. Waiting for claim...
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '20px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <h2 style={{ marginBottom: '15px', color: '#333' }}>System Logs</h2>
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          backgroundColor: '#1e1e1e',
          borderRadius: '8px',
          padding: '15px',
          fontFamily: 'monospace',
          fontSize: '12px',
          maxHeight: '600px',
        }}
      >
        {logs.length === 0 ? (
          <div style={{ color: '#999' }}>No logs yet...</div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              style={{
                marginBottom: '10px',
                padding: '8px',
                backgroundColor: '#2d2d2d',
                borderRadius: '4px',
                borderLeft: `3px solid ${getLogColor(log.type)}`,
              }}
            >
              <div style={{ color: '#999', fontSize: '10px', marginBottom: '4px' }}>
                {new Date(log.timestamp).toLocaleTimeString()}
              </div>
              <div style={{ color: '#fff' }}>{log.message}</div>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

