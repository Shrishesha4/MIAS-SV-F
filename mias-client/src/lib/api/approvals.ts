import client from './client';

export interface ApprovalItem {
  id: string;
  type: 'CASE_RECORD' | 'DISCHARGE_SUMMARY' | 'ADMISSION' | 'PRESCRIPTION';
  status: string;
  score?: number;
  comments?: string;
  created_at: string;
  processed_at?: string;
  patient: {
    id: string;
    patient_id: string;
    name: string;
    age: number;
    gender: string;
    blood_group: string;
    photo?: string;
    allergies?: { allergen: string; severity: string }[];
    primary_diagnosis?: string;
  };
  case_record?: {
    id: string;
    type: string;
    description: string;
    procedure_name: string;
    procedure_description: string;
    doctor_name: string;
    date: string;
    time: string;
  };
  submitted_by?: string;
  submitted_at?: string;
}

export interface ApprovalStats {
  case_records: number;
  discharge_summaries: number;
  admissions: number;
  prescriptions: number;
  total: number;
}

export interface ScheduleItem {
  id: string;
  time_start: string;
  time_end: string;
  title: string;
  type: 'consultation' | 'meeting' | 'review';
  location?: string;
}

export const approvalsApi = {
  async getApprovalStats(facultyId: string): Promise<ApprovalStats> {
    try {
      const response = await client.get(`/faculty/${facultyId}/approval-stats`);
      return response.data;
    } catch {
      // Return empty stats if endpoint doesn't exist
      return {
        case_records: 0,
        discharge_summaries: 0,
        admissions: 0,
        prescriptions: 0,
        total: 0,
      };
    }
  },

  async getPendingApprovals(facultyId: string, type?: string): Promise<ApprovalItem[]> {
    try {
      const response = await client.get(`/faculty/${facultyId}/approvals`, {
        params: { status: 'PENDING', type },
      });
      return response.data;
    } catch {
      return [];
    }
  },

  async getApprovalHistory(facultyId: string): Promise<ApprovalItem[]> {
    try {
      const response = await client.get(`/faculty/${facultyId}/approval-history`);
      return response.data;
    } catch {
      return [];
    }
  },

  async processApproval(
    facultyId: string,
    approvalId: string,
    data: { status: 'APPROVED' | 'REJECTED'; score?: number; comments?: string }
  ): Promise<void> {
    await client.put(`/faculty/${facultyId}/approvals/${approvalId}`, data);
  },

  async getTodaySchedule(facultyId: string): Promise<ScheduleItem[]> {
    try {
      const response = await client.get(`/faculty/${facultyId}/today-schedule`);
      return response.data;
    } catch {
      // Return empty schedule if endpoint doesn't exist
      return [];
    }
  },
};
