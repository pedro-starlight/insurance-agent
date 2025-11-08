'use client';

import { useState, useEffect } from 'react';
import { api, ClaimDetails, ActionDetails } from '../api/routes';

interface ClaimInterfaceProps {
  claimId: string | null;
  onClaimApproved: () => void;
}

export default function ClaimInterface({ claimId, onClaimApproved }: ClaimInterfaceProps) {
  const [claimDetails, setClaimDetails] = useState<ClaimDetails | null>(null);
  const [actionDetails, setActionDetails] = useState<ActionDetails | null>(null);
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
      const [coverage, action] = await Promise.all([
        api.getCoverage(claimId),
        api.getAction(claimId),
      ]);
      setClaimDetails(coverage);
      setActionDetails(action);
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

  if (!claimDetails || !actionDetails) {
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

  return (
    <div style={{ padding: '20px' }}>
      <h2 style={{ marginBottom: '20px', color: '#333' }}>Claim Details</h2>

      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
        <h3 style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>Policyholder</h3>
        <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>{claim?.full_name || 'N/A'}</p>

        <h3 style={{ marginTop: '15px', marginBottom: '10px', fontSize: '14px', color: '#666' }}>Vehicle</h3>
        {claim?.car_make && claim?.car_model && claim?.car_year ? (
          <p>{claim.car_year} {claim.car_make} {claim.car_model}</p>
        ) : (
          <p>N/A</p>
        )}

        <h3 style={{ marginTop: '15px', marginBottom: '10px', fontSize: '14px', color: '#666' }}>Location</h3>
        <p>{claim?.location || 'N/A'}</p>
        {claim?.city && (
          <p style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>City: {claim.city}</p>
        )}

        <h3 style={{ marginTop: '15px', marginBottom: '10px', fontSize: '14px', color: '#666' }}>Assistance Type</h3>
        <p style={{ textTransform: 'capitalize' }}>{claim?.assistance_type?.replace('_', ' ') || 'N/A'}</p>

        <h3 style={{ marginTop: '15px', marginBottom: '10px', fontSize: '14px', color: '#666' }}>Safety Status</h3>
        <p style={{ 
          textTransform: 'capitalize',
          color: claim?.safety_status === 'safe' ? '#2ecc71' : claim?.safety_status === 'unsafe' ? '#e74c3c' : '#666'
        }}>
          {claim?.safety_status || 'unknown'}
        </p>
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

