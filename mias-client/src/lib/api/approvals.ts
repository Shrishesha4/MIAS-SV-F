import client from './client';
import type { InsurancePolicy } from './types';
import type { FormFieldDefinition } from '$lib/types/forms';

export interface ApprovalItem {
  id: string;
  type: 'CASE_RECORD' | 'DISCHARGE_SUMMARY' | 'ADMISSION' | 'PRESCRIPTION';
  status: string;
  score?: number;
  grade?: string;
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
    category?: string | null;
    category_color_primary?: string | null;
    category_color_secondary?: string | null;
    insurance_policies?: InsurancePolicy[];
    allergies?: { allergen: string; severity: string }[];
    primary_diagnosis?: string;
    medical_alerts?: {
      id: string;
      type: string;
      severity: string;
      title: string;
      description?: string;
      is_active: boolean;
    }[];
  };
  case_record?: {
    id: string;
    type: string;
    description: string;
    procedure_name: string;
    procedure_description: string;
    form_name?: string;
    form_description?: string;
    form_fields?: FormFieldDefinition[];
    form_values?: Record<string, unknown>;
    doctor_name: string;
    grade?: string;
    department?: string;
    findings?: string;
    diagnosis?: string;
    treatment?: string;
    notes?: string;
    date: string;
    time: string;
  };
  admission?: {
    id: string;
    department: string;
    ward: string;
    bed_number: string;
    diagnosis: string;
    reason: string;
    attending_doctor: string;
    referring_doctor?: string;
    status: string;
    notes?: string;
    drug_allergy?: string;
    chief_complaints?: string;
    history_of_present_illness?: string;
    medication_history?: string;
    weight_admission?: string | number;
    pain_score?: string | number;
    physical_examination?: string;
    provisional_diagnosis?: string;
    proposed_plan?: string;
    discharge_summary?: string;
    admission_date: string;
  };
  prescription?: {
    id: string;
    prescription_id?: string;
    doctor?: string;
    department?: string;
    date?: string;
    status?: string;
    notes?: string;
    medications?: Array<{
      id: string;
      name: string;
      dosage: string;
      frequency: string;
      duration: string;
      instructions?: string;
      start_date?: string;
      end_date?: string;
    }>;
  };
  submitted_by?: {
    id: string;
    student_id: string;
    name: string;
  };
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
    data: {
      status: 'APPROVED' | 'REJECTED';
      score?: number;
      grade?: string;
      comments?: string;
      case_record_updates?: Record<string, unknown>;
      admission_updates?: Record<string, unknown>;
      prescription_updates?: Record<string, unknown>;
    }
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
