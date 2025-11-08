'use client';

interface MessageBoxProps {
  assessment?: string;
  nextActions?: string;
  sentAt?: string;
}

export default function MessageBox({ assessment, nextActions, sentAt }: MessageBoxProps) {
  if (!assessment && !nextActions) {
    return (
      <div
        style={{
          border: '2px dashed #ccc',
          borderRadius: '8px',
          padding: '20px',
          backgroundColor: '#f9f9f9',
          minHeight: '150px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#999',
        }}
      >
        No messages yet. Complete a call to receive assessment.
      </div>
    );
  }

  return (
    <div
      style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '20px',
        backgroundColor: 'white',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <div style={{ marginBottom: '15px' }}>
        <h3 style={{ marginBottom: '10px', color: '#333' }}>Assessment</h3>
        <p style={{ color: '#666', lineHeight: '1.6' }}>{assessment || 'Processing...'}</p>
      </div>
      <div style={{ marginBottom: '15px' }}>
        <h3 style={{ marginBottom: '10px', color: '#333' }}>Next Actions</h3>
        <p style={{ color: '#666', lineHeight: '1.6' }}>{nextActions || 'Processing...'}</p>
      </div>
      {sentAt && (
        <div style={{ fontSize: '12px', color: '#999', marginTop: '10px' }}>
          Sent: {new Date(sentAt).toLocaleString()}
        </div>
      )}
    </div>
  );
}

