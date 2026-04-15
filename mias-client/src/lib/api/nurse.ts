import client from './client';
import type { InsurancePolicy } from './types';

export interface Nurse {
  id: string;
  nurse_id: string;
  user_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  hospital: string | null;
  ward: string | null;
  shift: string | null;
  department: string | null;
  has_selected_station: number;
  photo: string | null;
}

export interface WardPatient {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  gender: string | null;
  ward: string;
  bed_number: string;
  admission_id: string;
  admission_date: string | null;
  primary_diagnosis: string | null;
  pending_tasks: number;
  admission_status: string;
  category?: string | null;
  category_color_primary?: string | null;
  category_color_secondary?: string | null;
  insurance_policies?: InsurancePolicy[];
}

export interface NewlyRegisteredPatient {
  id: string;
  patient_id: string;
  name: string;
  age: number | null;
  gender: string | null;
  phone: string | null;
  registered_at: string;
  has_appointment: boolean;
  has_admission: boolean;
  category?: string | null;
  category_color_primary?: string | null;
  category_color_secondary?: string | null;
  insurance_policies?: InsurancePolicy[];
}

export interface NurseClinic {
  id: string;
  name: string;
  location: string | null;
  department: string;
}

export interface StationSelection {
  hospital: string;
  ward?: string;
  shift?: string;
  department?: string;
}

export interface NurseOrder {
  id: string;
  order_id: string;
  order_type: string; // DRUG, INVESTIGATION, PROCEDURE
  title: string;
  description: string | null;
  scheduled_time: string | null;
  is_completed: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface SBARNote {
  id: string;
  sbar_id: string;
  nurse_name: string;
  situation?: string | null;
  background: string | null;
  assessment: string | null;
  recommendation: string | null;
  created_at: string;
  updated_at: string;
}

export const nurseApi = {
  async getMe(): Promise<Nurse> {
    const response = await client.get('/nurses/me');
    return response.data;
  },

  async getClinics(): Promise<NurseClinic[]> {
    const response = await client.get('/nurses/clinics');
    return response.data;
  },

  async selectStation(data: StationSelection): Promise<Nurse> {
    const response = await client.put('/nurses/me/station', data);
    return response.data;
  },

  async getAvailableWards(): Promise<string[]> {
    const response = await client.get('/nurses/wards');
    return response.data;
  },

  async updateProfile(data: Partial<Nurse>): Promise<Nurse> {
    const response = await client.put('/nurses/me', data);
    return response.data;
  },

  async getWardPatients(): Promise<{ nurse: { name: string; hospital: string; ward: string; shift: string }; patients: WardPatient[]; newly_registered: NewlyRegisteredPatient[] }> {
    const response = await client.get('/nurses/ward-patients');
    return response.data;
  },

  async getNotifications() {
    const response = await client.get('/nurses/notifications');
    return response.data;
  },

  async markNotificationRead(notificationId: string) {
    const response = await client.put(`/nurses/notifications/${notificationId}/read`);
    return response.data;
  },

  async getPatientOrders(patientId: string): Promise<NurseOrder[]> {
    const response = await client.get(`/nurses/patients/${patientId}/orders`);
    return response.data;
  },

  async completeOrder(orderId: string) {
    const response = await client.put(`/nurses/orders/${orderId}/complete`);
    return response.data;
  },

  async getPatientSBARNotes(patientId: string): Promise<SBARNote[]> {
    const response = await client.get(`/nurses/patients/${patientId}/sbar`);
    return response.data;
  },

  async createSBARNote(patientId: string, admissionId: string, data: { situation?: string; background?: string; assessment?: string; recommendation?: string }): Promise<SBARNote> {
    const response = await client.post(`/nurses/patients/${patientId}/sbar?admission_id=${admissionId}`, data);
    return response.data;
  },
};
