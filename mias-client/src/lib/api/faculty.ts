import client from './client';

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
}

export interface PatientAssignment {
  id: string;
  patient_id: string;
  patient_name: string;
  student_id: string;
  student_name: string;
  assigned_at: string;
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

  async uploadSignature(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/faculty/me/upload-signature', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};
