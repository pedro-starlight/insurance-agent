'use client';

import { useState } from 'react';

interface CallControlsProps {
  onStartCall: () => void;
  onEndCall: () => void;
  isCallActive: boolean;
}

export default function CallControls({ onStartCall, onEndCall, isCallActive }: CallControlsProps) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <button
        onClick={isCallActive ? onEndCall : onStartCall}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          fontWeight: 'bold',
          backgroundColor: isCallActive ? '#dc3545' : '#28a745',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          minWidth: '150px',
        }}
      >
        {isCallActive ? 'End Call' : 'Start Call'}
      </button>
      {isCallActive && (
        <div style={{ marginTop: '10px', color: '#28a745', fontWeight: 'bold' }}>
          ● Call Active
        </div>
      )}
    </div>
  );
}

