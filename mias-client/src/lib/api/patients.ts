import client from './client';
import type { Patient, Vital, MedicalRecord, Prescription, WalletTransaction, Admission, Report, Notification } from './types';

export const patientApi = {
  async getCurrentPatient(): Promise<Patient> {
    const response = await client.get('/patients/me');
    return response.data;
  },

  async getPatient(patientId: string): Promise<Patient> {
    const response = await client.get(`/patients/${patientId}`);
    return response.data;
  },

  async getVitals(patientId: string, days: number = 30): Promise<Vital[]> {
    const response = await client.get(`/patients/${patientId}/vitals`, {
      params: { days },
    });
    return response.data;
  },

  async createVital(patientId: string, vital: Partial<Vital>): Promise<Vital> {
    const response = await client.post(`/patients/${patientId}/vitals`, vital);
    return response.data;
  },

  async getRecords(patientId: string): Promise<MedicalRecord[]> {
    const response = await client.get(`/patients/${patientId}/records`);
    return response.data;
  },

  async getPrescriptions(patientId: string): Promise<Prescription[]> {
    const response = await client.get(`/patients/${patientId}/prescriptions`);
    return response.data;
  },

  async getAdmissions(patientId: string): Promise<Admission[]> {
    const response = await client.get(`/patients/${patientId}/admissions`);
    return response.data;
  },

  async getReports(patientId: string): Promise<Report[]> {
    const response = await client.get(`/patients/${patientId}/reports`);
    return response.data;
  },

  async getNotifications(patientId: string): Promise<Notification[]> {
    const response = await client.get(`/patients/${patientId}/notifications`);
    return response.data;
  },

  async getWalletTransactions(patientId: string, walletType: 'hospital' | 'pharmacy'): Promise<WalletTransaction[]> {
    const response = await client.get(`/patients/${patientId}/wallet/${walletType}/transactions`);
    return response.data;
  },
};
