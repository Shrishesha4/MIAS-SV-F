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

export interface MedicationDoseLog {
  id: string;
  medication_id: string;
  medication_name: string;
  medication_dosage: string;
  status: 'TAKEN' | 'MISSED' | 'SKIPPED';
  logged_at: string;
  scheduled_time: string | null;
  notes: string | null;
}

export interface MedicationAdherence {
  total_doses: number;
  taken: number;
  missed: number;
  skipped: number;
  adherence_rate: number;
  period_days: number;
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

  async logMedicationDose(
    patientId: string,
    medicationId: string,
    data: { status: string; scheduled_time?: string; notes?: string }
  ): Promise<{ id: string; status: string; logged_at: string; message: string }> {
    const response = await client.post(`/patients/${patientId}/medications/${medicationId}/log-dose`, data);
    return response.data;
  },

  async getMedicationHistory(patientId: string, days = 7): Promise<MedicationDoseLog[]> {
    const response = await client.get(`/patients/${patientId}/medication-history`, {
      params: { days },
    });
    return response.data;
  },

  async getMedicationAdherence(patientId: string, days = 30): Promise<MedicationAdherence> {
    const response = await client.get(`/patients/${patientId}/medication-adherence`, {
      params: { days },
    });
    return response.data;
  },

  // Primary Diagnosis
  async updatePrimaryDiagnosis(patientId: string, data: { diagnosis: string; doctor?: string; date?: string; time?: string }) {
    const response = await client.put(`/patients/${patientId}/primary-diagnosis`, data);
    return response.data;
  },

  // Medical Alerts
  async addMedicalAlert(patientId: string, data: { title: string; type?: string; severity?: string; added_by?: string }) {
    const response = await client.post(`/patients/${patientId}/medical-alerts`, data);
    return response.data;
  },

  async removeMedicalAlert(patientId: string, alertId: string) {
    const response = await client.delete(`/patients/${patientId}/medical-alerts/${alertId}`);
    return response.data;
  },

  async getMedicalAlertHistory(patientId: string) {
    const response = await client.get(`/patients/${patientId}/medical-alerts/history`);
    return response.data;
  },

  // Prescriptions
  async createPrescription(patientId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/prescriptions`, data);
    return response.data;
  },

  // Prescription Requests
  async getPrescriptionRequests(patientId: string) {
    const response = await client.get(`/patients/${patientId}/prescription-requests`);
    return response.data;
  },

  async createPrescriptionRequest(patientId: string, data: { medication: string; dosage?: string; notes?: string }) {
    const response = await client.post(`/patients/${patientId}/prescription-requests`, data);
    return response.data;
  },

  async respondToPrescriptionRequest(patientId: string, requestId: string, data: { status: string; responded_by?: string; notes?: string }) {
    const response = await client.put(`/patients/${patientId}/prescription-requests/${requestId}/respond`, data);
    return response.data;
  },
};
