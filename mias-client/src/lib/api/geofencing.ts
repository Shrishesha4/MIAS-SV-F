import client from './client';

export interface PatientProofResponse {
  proof_id: string;
  short_code: string;
  is_valid: boolean;
  expires_at: string;
  message: string;
}

export interface ProofStatusResponse {
  proof_id: string;
  short_code: string;
  is_valid: boolean;
  is_consumed: boolean;
  is_expired: boolean;
  expires_at: string;
}

export const geofencingApi = {
  /** Admin: list all zones */
  async listZones() {
    return (await client.get('/geofencing/zones')).data;
  },

  /** Admin: create a zone */
  async createZone(data: { name: string; polygon: { lat: number; lng: number }[]; is_active?: boolean }) {
    return (await client.post('/geofencing/zones', data)).data;
  },

  /** Admin: update a zone */
  async updateZone(zoneId: string, data: { name?: string; polygon?: { lat: number; lng: number }[]; is_active?: boolean }) {
    return (await client.patch(`/geofencing/zones/${zoneId}`, data)).data;
  },

  /** Admin: delete a zone */
  async deleteZone(zoneId: string) {
    return (await client.delete(`/geofencing/zones/${zoneId}`)).data;
  },

  /** Public: active zones for patient map */
  async listActiveZones() {
    return (await client.get('/geofencing/zones/public')).data;
  },

  /** Patient device: submit location proof */
  async submitPatientProof(data: { lat: number; lng: number; accuracy?: number; patient_id?: string }): Promise<PatientProofResponse> {
    return (await client.post('/geofencing/patient-proof', data)).data;
  },

  /** Staff: check proof status before check-in (accepts UUID or short_code) */
  async getProofStatus(proofId: string): Promise<ProofStatusResponse> {
    return (await client.get(`/geofencing/patient-proof/${proofId}/status`)).data;
  },
};
