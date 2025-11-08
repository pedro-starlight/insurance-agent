import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AudioRequest {
  url: string;
}

export interface ClaimDetails {
  claim_id: string;
  claim_details?: {
    policyholder_name?: string;
    car_info?: string;
    location?: string;
    damage_type?: string;
    situation?: string;
  };
  coverage_decision?: {
    covered: boolean;
    reasoning: string;
    policy_section?: string;
    confidence: number;
  };
}

export interface ActionDetails {
  claim_id: string;
  action: {
    type: string;
    garage_name?: string;
    garage_location?: string;
    reasoning: string;
    estimated_time?: string;
  };
}

export interface MessageDetails {
  claim_id: string;
  message: {
    assessment: string;
    next_actions: string;
    sent_at: string;
  };
}

export interface SystemLog {
  timestamp: string;
  type: string;
  message: string;
}

export interface ClaimLogs {
  claim_id: string;
  logs: SystemLog[];
}

export const api = {
  async createClaimFromAudio(audioUrl: string): Promise<{ claim_id: string }> {
    const response = await axios.post(`${API_BASE_URL}/claim/audio`, {
      url: audioUrl,
    });
    return response.data;
  },

  async getCoverage(claimId: string): Promise<ClaimDetails> {
    const response = await axios.get(`${API_BASE_URL}/claim/coverage/${claimId}`);
    return response.data;
  },

  async getAction(claimId: string): Promise<ActionDetails> {
    const response = await axios.get(`${API_BASE_URL}/claim/action/${claimId}`);
    return response.data;
  },

  async getMessage(claimId: string): Promise<MessageDetails> {
    const response = await axios.get(`${API_BASE_URL}/claim/message/${claimId}`);
    return response.data;
  },

  async getClaim(claimId: string): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/claim/${claimId}`);
    return response.data;
  },

  async getLogs(claimId: string): Promise<ClaimLogs> {
    const response = await axios.get(`${API_BASE_URL}/claim/logs/${claimId}`);
    return response.data;
  },

  async approveClaim(claimId: string): Promise<{ status: string; claim_id: string }> {
    const response = await axios.post(`${API_BASE_URL}/claim/${claimId}/approve`);
    return response.data;
  },

  async getConversationTranscription(conversationId: string): Promise<{ conversation_id: string; transcription: string; received_at: string }> {
    const response = await axios.get(`${API_BASE_URL}/conversation/${conversationId}/transcription`);
    return response.data;
  },

  async getLatestConversation(): Promise<{ conversation_id: string; transcription: string; received_at: string }> {
    const response = await axios.get(`${API_BASE_URL}/conversation/latest`);
    return response.data;
  },

  async getClaimFromConversation(conversationId: string): Promise<{ conversation_id: string; claim_id: string }> {
    const response = await axios.get(`${API_BASE_URL}/conversation/${conversationId}/claim`);
    return response.data;
  },
};

