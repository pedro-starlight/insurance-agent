'use client';

import { useState } from 'react';
import PolicyholderView from './components/PolicyholderView';
import AgentView from './components/AgentView';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'policyholder' | 'agent'>('policyholder');

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <div
        style={{
          backgroundColor: 'white',
          borderBottom: '1px solid #ddd',
          padding: '0 20px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ display: 'flex', gap: '20px' }}>
          <button
            onClick={() => setActiveTab('policyholder')}
            style={{
              padding: '15px 20px',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === 'policyholder' ? '3px solid #007bff' : '3px solid transparent',
              color: activeTab === 'policyholder' ? '#007bff' : '#666',
              fontWeight: activeTab === 'policyholder' ? 'bold' : 'normal',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            Policyholder View
          </button>
          <button
            onClick={() => setActiveTab('agent')}
            style={{
              padding: '15px 20px',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: activeTab === 'agent' ? '3px solid #007bff' : '3px solid transparent',
              color: activeTab === 'agent' ? '#007bff' : '#666',
              fontWeight: activeTab === 'agent' ? 'bold' : 'normal',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            Insurance Agent View
          </button>
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {activeTab === 'policyholder' ? <PolicyholderView /> : <AgentView />}
      </div>
    </div>
  );
}

