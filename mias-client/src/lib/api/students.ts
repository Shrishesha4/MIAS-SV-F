import client from './client';

export interface EmergencyContact {
  id: string;
  name: string;
  department: string;
  specialty: string;
  phone: string;
  email: string;
  photo: string;
  availability: string;
  availability_status: 'Available' | 'Busy' | 'Unavailable';
}

export interface Clinic {
  id: string;
  name: string;
  department: string;
  location: string;
  faculty_name: string;
}

export interface ClinicPatient {
  id: string;
  patient_id: string;
  patient_name: string;
  appointment_time: string;
  provider_name: string;
  status: 'Waiting' | 'In Progress' | 'Completed';
}

export interface AssignedPatient {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  blood_group: string;
  photo: string;
  primary_diagnosis: string;
  status: string;
}

export const studentApi = {
  async getMe() {
    const response = await client.get('/students/me');
    return response.data;
  },

  async getStudent(studentId: string) {
    const response = await client.get(`/students/${studentId}`);
    return response.data;
  },

  async getAssignedPatients(studentId: string): Promise<AssignedPatient[]> {
    const response = await client.get(`/students/${studentId}/patients`);
    return response.data;
  },

  async getCaseRecords(studentId: string, patientId?: string) {
    const params = patientId ? { patient_id: patientId } : {};
    const response = await client.get(`/students/${studentId}/case-records`, { params });
    return response.data;
  },

  async createCaseRecord(studentId: string, data: Record<string, unknown>) {
    const response = await client.post(`/students/${studentId}/case-records`, data);
    return response.data;
  },

  async getProgress(studentId: string) {
    const response = await client.get(`/students/${studentId}/progress`);
    return response.data;
  },

  async getClinicSessions(studentId: string) {
    const response = await client.get(`/students/${studentId}/clinic-sessions`);
    return response.data;
  },

  async getNotifications(studentId: string) {
    const response = await client.get(`/students/${studentId}/notifications`);
    return response.data;
  },

  async getEmergencyContacts(): Promise<EmergencyContact[]> {
    const response = await client.get('/students/emergency-contacts');
    return response.data;
  },

  async getClinics(): Promise<Clinic[]> {
    const response = await client.get('/students/clinics');
    return response.data;
  },

  async getClinicPatients(clinicId: string): Promise<ClinicPatient[]> {
    const response = await client.get(`/students/clinic/${clinicId}/patients`);
    return response.data;
  },

  async selectClinicSession(studentId: string, sessionId: string) {
    const response = await client.post(`/students/${studentId}/clinic-sessions/${sessionId}/select`);
    return response.data;
  },

  async getDepartments(): Promise<string[]> {
    const response = await client.get('/students/departments');
    return response.data;
  },

  async getProcedures(): Promise<Record<string, string[]>> {
    const response = await client.get('/students/procedures');
    return response.data;
  },

  async getFacultyApprovers(): Promise<{ id: string; name: string; department: string }[]> {
    const response = await client.get('/students/faculty-approvers');
    return response.data;
  },

  async submitCaseRecord(studentId: string, data: Record<string, unknown>) {
    const response = await client.post(`/students/${studentId}/case-records/submit`, data);
    return response.data;
  },
};
