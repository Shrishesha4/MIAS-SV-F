import client from './client';

export interface ClinicInfo {
  id: string;
  name: string;
  block?: string;
  clinic_type: string;
  department: string;
  location?: string;
  faculty_id?: string;
  faculty_name?: string;
  is_active: boolean;
}

export interface ClinicPatientInfo {
  id: string;
  patient_id: string;
  patient_db_id: string;
  patient_name: string;
  appointment_time: string;
  provider_name: string;
  status: 'Scheduled' | 'Checked In' | 'In Progress' | 'Completed';
}

export interface PatientAppointmentInfo {
  id: string;
  clinic_name: string;
  clinic_location: string;
  clinic_department: string;
  doctor_name: string;
  appointment_date: string;
  appointment_time: string;
  provider_name: string;
  status: string;
}

export const clinicsApi = {
  async listClinics(): Promise<ClinicInfo[]> {
    const response = await client.get('/clinics');
    return response.data;
  },

  async getClinic(clinicId: string): Promise<ClinicInfo> {
    const response = await client.get(`/clinics/${clinicId}`);
    return response.data;
  },

  async getClinicPatients(clinicId: string): Promise<ClinicPatientInfo[]> {
    const response = await client.get(`/clinics/${clinicId}/patients`);
    return response.data;
  },

  async updateAppointmentStatus(clinicId: string, appointmentId: string, status: string) {
    const response = await client.put(`/clinics/${clinicId}/appointments/${appointmentId}/status`, { status });
    return response.data;
  },

  async getFacultyClinics(facultyId: string): Promise<ClinicInfo[]> {
    const response = await client.get(`/clinics/faculty/${facultyId}/clinics`);
    return response.data;
  },

  async getPatientAppointments(patientId: string): Promise<PatientAppointmentInfo[]> {
    const response = await client.get(`/clinics/patient/${patientId}/appointments`);
    return response.data;
  },

  async searchPatient(clinicId: string, query: string) {
    const response = await client.get(`/clinics/${clinicId}/search-patient`, { params: { q: query } });
    return response.data;
  },

  async checkInPatient(clinicId: string, data: { patient_id: string; provider_name?: string }) {
    const response = await client.post(`/clinics/${clinicId}/check-in`, data);
    return response.data;
  },

  async createAppointment(clinicId: string, data: { patient_id: string; date?: string; time?: string; provider_name?: string; status?: string }) {
    const response = await client.post(`/clinics/${clinicId}/appointments`, data);
    return response.data;
  },

  // Admin CRUD operations
  async createClinic(data: {
    name: string;
    block?: string;
    clinic_type?: string;
    department?: string;
    location?: string;
    faculty_id?: string;
    is_active?: boolean;
  }): Promise<ClinicInfo> {
    const response = await client.post('/clinics', data);
    return response.data;
  },

  async updateClinic(clinicId: string, data: {
    name?: string;
    block?: string;
    clinic_type?: string;
    department?: string;
    location?: string;
    faculty_id?: string;
    is_active?: boolean;
  }): Promise<ClinicInfo> {
    const response = await client.put(`/clinics/${clinicId}`, data);
    return response.data;
  },

  async deleteClinic(clinicId: string): Promise<void> {
    await client.delete(`/clinics/${clinicId}`);
  },
};
