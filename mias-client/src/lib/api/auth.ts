import client from './client';
import type { LoginResponse } from './types';

export interface RegisterData {
  username?: string;
  password: string;
  email: string;
  role: 'PATIENT';
  preferred_clinic_id?: string;
  patient_data?: {
    name: string;
    date_of_birth: string;
    gender: string;
    blood_group: string;
    phone: string;
    email: string;
    address?: string;
    photo?: string;
    aadhaar_id?: string;
    abha_id?: string;
    category?: string;
    patient_category_id?: string;
    insurance_category_id?: string;
    emergency_contact?: {
      name: string;
      phone: string;
      relationship: string;
    };
  };
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await client.post('/auth/login', { username, password });
    return response.data;
  },

  async signup(data: RegisterData): Promise<{ message: string; user_id: string; patient_id: string }> {
    const response = await client.post('/auth/register', data);
    return response.data;
  },

  async refresh(): Promise<LoginResponse> {
    // No body — the httpOnly refresh_token cookie is sent automatically.
    const response = await client.post('/auth/refresh', null, { withCredentials: true });
    return response.data;
  },

  async logout(): Promise<void> {
    await client.post('/auth/logout');
  },

  // Public endpoints (no auth needed) for registration form
  async getDepartments(): Promise<{ id: string; name: string; code: string }[]> {
    const response = await client.get('/auth/departments');
    return response.data;
  },

  async getProgrammes(): Promise<{ id: string; name: string; code: string; degree_type: string | null }[]> {
    const response = await client.get('/auth/programmes');
    return response.data;
  },
};
