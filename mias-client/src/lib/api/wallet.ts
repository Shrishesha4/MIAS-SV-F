import client from './client';

export const walletApi = {
  async getBalance(patientId: string, walletType: 'hospital' | 'pharmacy') {
    const response = await client.get(`/wallet/balance/${patientId}/${walletType}`);
    return response.data;
  },

  async getPatientSummary(patientId: string) {
    const response = await client.get(`/wallet/patient/${patientId}/summary`);
    return response.data;
  },

  async searchPatients(q: string) {
    const response = await client.get('/wallet/patients/search', { params: { q } });
    return response.data as Array<{
      id: string; patient_id: string; name: string;
      phone: string; email: string; photo: string | null; category: string;
    }>;
  },

  async topup(data: {
    patient_id: string;
    wallet_type: 'HOSPITAL' | 'PHARMACY';
    amount: number;
    transaction_type?: string;
    reference_id?: string;
    description?: string;
    payment_method?: string;
  }) {
    const response = await client.post('/wallet/topup', data);
    return response.data;
  },

  async selfTopup(data: {
    wallet_type: 'HOSPITAL' | 'PHARMACY';
    amount: number;
    payment_method?: string;
    reference_id?: string;
  }) {
    const response = await client.post('/wallet/self-topup', data);
    return response.data;
  },
};
