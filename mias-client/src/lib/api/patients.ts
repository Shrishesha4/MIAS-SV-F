import client from './client';
import type { Patient, Vital, MedicalRecord, Prescription, WalletTransaction, Admission, Report, Notification } from './types';

export interface Appointment {
  id: string;
  patient_id?: string;
  date: string;
  time: string;
  doctor: string;
  department: string;
  status: string;
  notes?: string;
}

export interface ActiveMedication {
  id: string;
  prescription_id: string;
  name: string;
  dosage: string;
  frequency: string;
  instructions?: string;
  doctor?: string;
}

export interface PatientDashboard {
  next_appointment: Appointment | null;
  active_medications: ActiveMedication[];
  hospital_balance: number;
  pharmacy_balance: number;
  last_visit: string | null;
}

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

  async getAppointments(patientId: string): Promise<Appointment[]> {
    const response = await client.get(`/patients/${patientId}/appointments`);
    return response.data;
  },

  async getNextAppointment(patientId: string): Promise<Appointment | null> {
    const response = await client.get(`/patients/${patientId}/next-appointment`);
    return response.data;
  },

  async getActiveMedications(patientId: string): Promise<ActiveMedication[]> {
    const response = await client.get(`/patients/${patientId}/active-medications`);
    return response.data;
  },

  async getDashboard(patientId: string): Promise<PatientDashboard> {
    const response = await client.get(`/patients/${patientId}/dashboard`);
    return response.data;
  },

  async getWalletBalance(patientId: string, walletType: 'hospital' | 'pharmacy'): Promise<{ balance: number }> {
    const response = await client.get(`/wallet/balance/${patientId}/${walletType}`);
    return response.data;
  },
};
