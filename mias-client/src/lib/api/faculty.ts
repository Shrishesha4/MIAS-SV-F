import client from './client';

export const facultyApi = {
  async getMe() {
    const response = await client.get('/faculty/me');
    return response.data;
  },

  async getFaculty(facultyId: string) {
    const response = await client.get(`/faculty/${facultyId}`);
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
};
