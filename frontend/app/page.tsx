'use client';

import { useState } from 'react';
import PolicyholderView from './components/PolicyholderView';
import AgentView from './components/AgentView';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'policyholder' | 'agent'>('policyholder');

  const handleResetDemo = () => {
    console.log('🔄 Resetting demo...');
    
    // Clear all localStorage data
    localStorage.clear();
    
    // Set a flag to prevent auto-loading after reset
    localStorage.setItem('demoReset', 'true');
    
    // Dispatch clearConversation event to notify all components
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'clearConversation',
      newValue: Date.now().toString(),
    }));
    
    // Show confirmation and reload page after a short delay
    console.log('✅ Demo reset complete - reloading page...');
    
    // Force page reload to clear all React state
    setTimeout(() => {
      window.location.reload();
    }, 500);
  };

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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
          
          {/* Reset Demo Button */}
          <button
            onClick={handleResetDemo}
            style={{
              padding: '10px 20px',
              border: '1px solid #dc3545',
              backgroundColor: 'white',
              borderRadius: '6px',
              color: '#dc3545',
              fontWeight: '500',
              cursor: 'pointer',
              fontSize: '14px',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = '#dc3545';
              e.currentTarget.style.color = 'white';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'white';
              e.currentTarget.style.color = '#dc3545';
            }}
          >
            <span>🔄</span>
            <span>Reset Demo</span>
          </button>
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {activeTab === 'policyholder' ? <PolicyholderView /> : <AgentView />}
      </div>
    </div>
  );
}

