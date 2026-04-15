import client from './client';
import type { InsurancePolicy } from './types';

export interface StudentForAssignment {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  department: string;
  assigned_patient_count: number;
}

export interface UnassignedPatient {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  blood_group: string;
  photo: string;
  primary_diagnosis: string;
  category?: string | null;
  category_color_primary?: string | null;
  category_color_secondary?: string | null;
  insurance_policies?: InsurancePolicy[];
}

export interface PatientAssignment {
  id: string;
  patient_id: string;
  patient_name: string;
  student_id: string;
  student_name: string;
  assigned_at: string;
}

export interface FacultyClinicSession {
  id: string;
  clinic_id: string;
  clinic_name: string;
  department: string;
  date: string | null;
  display_date: string | null;
  status: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
}

export const facultyApi = {
  async getMe() {
    const response = await client.get('/faculty/me');
    return response.data;
  },

  async getFaculty(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}`);
    return response.data;
  },

  async updateAvailabilityStatus(status: 'Available' | 'Busy' | 'Unavailable') {
    const response = await client.put('/faculty/me/availability-status', {
      availability_status: status,
    });
    return response.data;
  },

  async getApprovals(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}/approvals`);
    return response.data;
  },

  async processApproval(facultyId: string, approvalId: string, data: { status: string; comments?: string; score?: number }) {
    const response = await client.put(`/faculty/${facultyId}/approvals/${approvalId}`, data);
    return response.data;
  },

  async getSchedule(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}/schedule`);
    return response.data;
  },

  async getNotifications(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}/notifications`);
    return response.data;
  },

  async getStudents(facultyId: string): Promise<StudentForAssignment[]> {
    const response = await client.get(`/faculty/${facultyId}/students`);
    return response.data;
  },

  async getUnassignedPatients(facultyId: string): Promise<UnassignedPatient[]> {
    const response = await client.get(`/faculty/${facultyId}/patients-unassigned`);
    return response.data;
  },

  async assignPatient(facultyId: string, studentId: string, patientId: string): Promise<PatientAssignment> {
    const response = await client.post(`/faculty/${facultyId}/assign-patient`, {
      student_id: studentId,
      patient_id: patientId,
    });
    return response.data;
  },

  async removeAssignment(facultyId: string, assignmentId: string): Promise<void> {
    await client.delete(`/faculty/${facultyId}/assignments/${assignmentId}`);
  },

  async uploadPhoto(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/faculty/me/upload-photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async getAdmittedPatients(status: string = 'Active') {
    const response = await client.get('/admissions/', {
      params: { status },
    });
    return response.data;
  },

  async getFacultyClinics(facultyId: string) {
    const response = await client.get(`/clinics/faculty/${facultyId}/clinics`);
    return response.data;
  },

  async getClinicSessions(facultyId: string): Promise<FacultyClinicSession[]> {
    const response = await client.get(`/faculty/${facultyId}/clinic-sessions`);
    return response.data;
  },

  async checkInToClinic(facultyId: string, clinicId: string) {
    const response = await client.post(`/faculty/${facultyId}/clinic-sessions/check-in`, { clinic_id: clinicId });
    return response.data;
  },

  async checkOutFromClinic(facultyId: string, sessionId: string) {
    const response = await client.post(`/faculty/${facultyId}/clinic-sessions/${sessionId}/check-out`);
    return response.data;
  },

  async getClinicPatients(clinicId: string) {
    const response = await client.get(`/clinics/${clinicId}/patients`);
    return response.data;
  },

  async uploadSignature(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/faculty/me/upload-signature', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async markNotificationsRead(facultyId: string) {
    const response = await client.put(`/faculty/${facultyId}/notifications/read`);
    return response.data;
  },

  async getTodaySchedule(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}/today-schedule`);
    return response.data;
  },

  async createScheduleItem(facultyId: string, data: Record<string, unknown>) {
    const response = await client.post(`/faculty/${facultyId}/schedule`, data);
    return response.data;
  },

  async updateScheduleItem(facultyId: string, itemId: string, data: Record<string, unknown>) {
    const response = await client.put(`/faculty/${facultyId}/schedule/${itemId}`, data);
    return response.data;
  },

  async deleteScheduleItem(facultyId: string, itemId: string) {
    const response = await client.delete(`/faculty/${facultyId}/schedule/${itemId}`);
    return response.data;
  },
};
