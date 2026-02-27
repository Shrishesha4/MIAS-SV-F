import client from './client';

export const walletApi = {
  async getBalance(patientId: string, walletType: 'hospital' | 'pharmacy') {
    const response = await client.get(`/wallet/balance/${patientId}/${walletType}`);
    return response.data;
  },
};
