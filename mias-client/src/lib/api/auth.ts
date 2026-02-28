import client from './client';
import type { LoginResponse } from './types';

export interface RegisterData {
  username: string;
  password: string;
  email: string;
  role: 'PATIENT' | 'STUDENT' | 'FACULTY';
  patient_data?: {
    name: string;
    date_of_birth: string;
    gender: string;
    blood_group: string;
    phone: string;
    email: string;
    address?: string;
    aadhaar_id?: string;
    abha_id?: string;
    emergency_contact?: {
      name: string;
      phone: string;
      relationship: string;
    };
  };
  student_data?: {
    name: string;
    program: string;
    year: number;
    semester: number;
    gpa?: number;
    academic_advisor?: string;
  };
  faculty_data?: {
    name: string;
    department: string;
    specialty?: string;
    phone?: string;
    email?: string;
  };
}

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await client.post('/auth/login', { username, password });
    return response.data;
  },

  async signup(data: RegisterData): Promise<{ message: string; user_id: string }> {
    const response = await client.post('/auth/register', data);
    return response.data;
  },

  async refresh(refreshToken: string): Promise<LoginResponse> {
    const response = await client.post('/auth/refresh', { refresh_token: refreshToken });
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
