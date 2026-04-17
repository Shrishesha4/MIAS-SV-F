import client from './client';

export interface BillingProfile {
  id: string;
  billing_id: string;
  name: string;
  counter_name: string | null;
  phone: string | null;
  email: string | null;
  username: string;
}

export const billingApi = {
  async getMe(): Promise<BillingProfile> {
    const response = await client.get('/billing/me');
    return response.data;
  },
};
