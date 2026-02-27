import client from './client';

export const studentApi = {
  async getMe() {
    const response = await client.get('/students/me');
    return response.data;
  },

  async getStudent(studentId: string) {
    const response = await client.get(`/students/${studentId}`);
    return response.data;
  },

  async getAssignedPatients(studentId: string) {
    const response = await client.get(`/students/${studentId}/patients`);
    return response.data;
  },

  async getCaseRecords(studentId: string) {
    const response = await client.get(`/students/${studentId}/case-records`);
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
};
