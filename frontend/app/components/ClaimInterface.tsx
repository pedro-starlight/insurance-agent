'use client';

import { useState, useEffect } from 'react';
import { api, ClaimDetails, ActionDetails, MessageDetails } from '../api/routes';

interface ClaimInterfaceProps {
  claimId: string | null;
  onClaimApproved: () => void;
}

export default function ClaimInterface({ claimId, onClaimApproved }: ClaimInterfaceProps) {
  const [claimDetails, setClaimDetails] = useState<ClaimDetails | null>(null);
  const [actionDetails, setActionDetails] = useState<ActionDetails | null>(null);
  const [messageDetails, setMessageDetails] = useState<MessageDetails | null>(null);
  const [isApproving, setIsApproving] = useState(false);

  useEffect(() => {
    if (claimId) {
      fetchClaimData();
      // Poll for updates
      const interval = setInterval(fetchClaimData, 2000);
      return () => clearInterval(interval);
    }
  }, [claimId]);

  const fetchClaimData = async () => {
    if (!claimId) return;

    try {
      const [coverage, action, message] = await Promise.all([
        api.getCoverage(claimId),
        api.getAction(claimId),
        api.getMessage(claimId),
      ]);
      setClaimDetails(coverage);
      setActionDetails(action);
      setMessageDetails(message);
    } catch (error) {
      console.error('Error fetching claim data:', error);
    }
  };

  const handleApprove = async () => {
    if (!claimId) return;

    setIsApproving(true);
    try {
      await api.approveClaim(claimId);
      onClaimApproved();
    } catch (error) {
      console.error('Error approving claim:', error);
    } finally {
      setIsApproving(false);
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
        }}
      >
        No active claim. Waiting for policyholder to initiate a call...
      </div>
    );
  }

  if (!claimDetails || !actionDetails || !messageDetails) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <div style={{ marginBottom: '15px', color: '#666' }}>Loading claim details...</div>
        <div style={{ fontSize: '12px', color: '#999' }}>Waiting for agent to process claim...</div>
      </div>
    );
  }

  const coverage = claimDetails.coverage_decision;
  const action = actionDetails.action;
  const claim = claimDetails.claim_details;

  const carModel = claim?.car_model || claim?.carModel;
  const carMake = carModel?.make || claim?.car_make;
  const carModelName = carModel?.model || claim?.car_model;
  const carYear = carModel?.year || claim?.car_year;
  const locationText =
    claim?.location_data?.free_text ||
    claim?.locationData?.free_text ||
    claim?.location ||
    claim?.location_text;
  const city =
    claim?.location_data?.components?.city ||
    claim?.locationData?.components?.city ||
    claim?.city;
  const assistanceType = claim?.assistance_type || claim?.assistanceType;
  const safetyStatus = claim?.safety_status || claim?.safetyStatus;

  return (
    <div style={{ padding: '20px' }}>
      <h2 style={{ marginBottom: '20px', color: '#333' }}>Claim Details</h2>

      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Full Name</h3>
            <p style={{ fontWeight: 'bold', margin: 0 }}>{claim?.full_name || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Car Make</h3>
            <p style={{ margin: 0 }}>{carMake || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Car Model</h3>
            <p style={{ margin: 0 }}>{carModelName || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Car Year</h3>
            <p style={{ margin: 0 }}>{carYear || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Location</h3>
            <p style={{ margin: 0 }}>{locationText || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>City</h3>
            <p style={{ margin: 0 }}>{city || 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Assistance Type</h3>
            <p style={{ margin: 0, textTransform: 'capitalize' }}>{assistanceType ? assistanceType.replace(/_/g, ' ') : 'N/A'}</p>
          </div>
          <div>
            <h3 style={{ marginBottom: '8px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Safety Status</h3>
            <p
              style={{
                margin: 0,
                textTransform: 'capitalize',
                color:
                  safetyStatus === 'safe'
                    ? '#2ecc71'
                    : safetyStatus === 'unsafe'
                    ? '#e74c3c'
                    : '#666',
              }}
            >
              {safetyStatus || 'unknown'}
            </p>
          </div>
        </div>
      </div>

      <div
        style={{
          marginBottom: '20px',
          padding: '15px',
          backgroundColor: coverage?.covered ? '#d4edda' : '#f8d7da',
          borderRadius: '8px',
          border: `1px solid ${coverage?.covered ? '#c3e6cb' : '#f5c6cb'}`,
        }}
      >
        <h3 style={{ marginBottom: '10px', color: coverage?.covered ? '#155724' : '#721c24' }}>
          Coverage Decision: {coverage?.covered ? 'COVERED' : 'NOT COVERED'}
        </h3>
        <p style={{ color: coverage?.covered ? '#155724' : '#721c24', lineHeight: '1.6' }}>
          {coverage?.reasoning}
        </p>
        {coverage?.confidence && (
          <p style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
            Confidence: {(coverage.confidence * 100).toFixed(0)}%
          </p>
        )}
      </div>

      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#e7f3ff', borderRadius: '8px' }}>
        <h3 style={{ marginBottom: '10px', color: '#004085' }}>Recommended Action</h3>
        <p style={{ fontWeight: 'bold', color: '#004085', marginBottom: '10px' }}>
          {action.type.toUpperCase().replace('_', ' ')}
        </p>
        <p style={{ color: '#004085', lineHeight: '1.6', marginBottom: '10px' }}>
          {action.reasoning}
        </p>
        {action.garage_name && (
          <div style={{ marginTop: '10px' }}>
            <p style={{ fontSize: '14px', color: '#004085' }}>
              <strong>Garage:</strong> {action.garage_name}
            </p>
            {action.garage_location && (
              <p style={{ fontSize: '14px', color: '#004085' }}>
                <strong>Location:</strong> {action.garage_location}
              </p>
            )}
          </div>
        )}
        {action.estimated_time && (
          <p style={{ marginTop: '10px', fontSize: '14px', color: '#004085' }}>
            <strong>Estimated Time:</strong> {action.estimated_time}
          </p>
        )}
      </div>

      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f3f0ff', borderRadius: '8px', border: '1px solid #d4c5f9' }}>
        <h3 style={{ marginBottom: '12px', color: '#5a2d82', fontWeight: 'bold' }}>Policyholder Message</h3>
        <div style={{ marginBottom: '12px' }}>
          <h4 style={{ fontSize: '13px', color: '#7c4dff', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Assessment</h4>
          <p style={{ color: '#5a2d82', lineHeight: '1.6', margin: 0 }}>
            {messageDetails.message.assessment}
          </p>
        </div>
        <div>
          <h4 style={{ fontSize: '13px', color: '#7c4dff', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Next Actions</h4>
          <p style={{ color: '#5a2d82', lineHeight: '1.6', margin: 0 }}>
            {messageDetails.message.next_actions}
          </p>
        </div>
      </div>

      <button
        onClick={handleApprove}
        disabled={isApproving}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          fontWeight: 'bold',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: isApproving ? 'not-allowed' : 'pointer',
          opacity: isApproving ? 0.6 : 1,
        }}
      >
        {isApproving ? 'Approving...' : 'Approve & Initiate Claim'}
      </button>
    </div>
  );
}

