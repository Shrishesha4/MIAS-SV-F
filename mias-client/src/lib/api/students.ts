import client from './client';
import type { InsurancePolicy } from './types';

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
  clinic_type: string;
  access_mode: 'WALK_IN' | 'APPOINTMENT_ONLY';
  department: string;
  location: string;
  faculty_name: string;
}

export interface ClinicPatient {
  id: string;
  patient_id: string;
  patient_db_id: string | null;
  patient_name: string;
  photo?: string | null;
  appointment_time: string;
  provider_name: string | null;
  status: 'Waiting' | 'In Progress' | 'Completed';
  is_assigned: boolean;
  source: 'appointment' | 'assignment';
  category?: string | null;
  category_color_primary?: string | null;
  category_color_secondary?: string | null;
  insurance_policies?: InsurancePolicy[];
}

export interface ClinicSession {
  id: string;
  clinic_id: string | null;
  clinic_name: string;
  department: string;
  date: string | null;
  display_date: string | null;
  session_date: string | null;
  time_start: string | null;
  time_end: string | null;
  start_time: string | null;
  end_time: string | null;
  status: string;
  is_selected: boolean;
  checked_in_at: string | null;
  checked_out_at: string | null;
  doctor_name: string | null;
  location: string | null;
}

export interface AssignedPatient {
  id: string;
  patient_db_id?: string;
  assignment_id?: string;
  admission_id?: string | null;
  admission_date?: string | null;
  discharge_date?: string | null;
  patient_id: string;
  name: string;
  age: number;
  gender: string;
  blood_group: string;
  photo: string;
  primary_diagnosis: string;
  department?: string | null;
  status: string;
  assigned_date?: string | null;
  category?: string | null;
  category_color_primary?: string | null;
  category_color_secondary?: string | null;
  insurance_policies?: InsurancePolicy[];
}

export interface AttendanceCalendarSession {
  id: string;
  date: string;
  clinic_name: string;
  department: string | null;
  time_start: string | null;
  time_end: string | null;
  status: string;
  checked_in_at: string | null;
  checked_out_at: string | null;
  duration_minutes: number | null;
}

export interface StudentAcademicGroupSummary {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  programme_id: string;
}

export interface StudentAcademicProgressSummary {
  overall_percent: number;
  completed_targets: number;
  total_targets: number;
  approved_case_records: number;
  total_earned_points: number;
  total_possible_points: number;
}

export interface StudentAcademicProgressTarget {
  id: string;
  sort_order: number;
  metric_name: string;
  metric_key: string;
  category: string;
  target_value: number;
  completed_value: number;
  remaining_value: number;
  percent: number;
  is_complete: boolean;
  form_definition_id: string | null;
  form_name: string | null;
}

export interface StudentAcademicProgressWeightageRecord {
  id: string;
  form_name: string | null;
  department: string | null;
  procedure_name: string | null;
  date: string | null;
  status: string;
}

export interface StudentAcademicProgressWeightageItem {
  form_definition_id: string;
  slug: string | null;
  name: string | null;
  department: string | null;
  procedure_name: string | null;
  section: string | null;
  points: number;
  approved_count: number;
  earned_points: number;
  has_weightage: boolean;
}

export interface StudentAcademicProgressWeightages {
  total_approved_forms: number;
  total_configured_forms: number;
  total_possible_points: number;
  total_earned_points: number;
  average_points_per_approved_form: number;
  items: StudentAcademicProgressWeightageItem[];
  unmatched_records: StudentAcademicProgressWeightageRecord[];
}

export interface StudentAcademicProgress {
  student_id: string;
  student_name: string;
  programme_name: string;
  academic_group: StudentAcademicGroupSummary | null;
  summary: StudentAcademicProgressSummary;
  targets: StudentAcademicProgressTarget[];
  weightages: StudentAcademicProgressWeightages;
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

  async getProgress(studentId: string): Promise<{
    gpa: number;
    academic_standing: string;
    attendance: {
      overall?: number;
      clinical?: number;
      lecture?: number;
      lab?: number;
    };
    academic_group_id?: string | null;
    academic_group_name?: string | null;
    academic_progress?: StudentAcademicProgress | null;
    summary?: StudentAcademicProgressSummary | null;
    targets?: StudentAcademicProgressTarget[];
    weightages?: StudentAcademicProgressWeightages | null;
  }> {
    const response = await client.get(`/students/${studentId}/progress`);
    return response.data;
  },

  async getAcademicProgress(studentId: string): Promise<StudentAcademicProgress | null> {
    const response = await client.get(`/students/${studentId}/progress`);
    return response.data?.academic_progress ?? null;
  },

  async getClinicSessions(studentId: string): Promise<ClinicSession[]> {
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

  async getClinicPatients(studentId: string, clinicId: string): Promise<ClinicPatient[]> {
    const response = await client.get(`/students/${studentId}/clinic/${clinicId}/patients`);
    return response.data;
  },

  async selectClinicSession(studentId: string, sessionId: string) {
    const response = await client.post(`/students/${studentId}/clinic-sessions/${sessionId}/select`);
    return response.data;
  },

  async checkInToClinic(studentId: string, clinicId: string, coords?: { lat: number; lng: number; accuracy: number }) {
    const response = await client.post(`/students/${studentId}/clinic-sessions/check-in`, {
      clinic_id: clinicId,
      ...(coords ?? {}),
    });
    return response.data;
  },

  async checkOutClinic(studentId: string, sessionId: string) {
    const response = await client.post(`/students/${studentId}/clinic-sessions/${sessionId}/check-out`);
    return response.data;
  },

  async getAttendanceCalendar(studentId: string, month?: number, year?: number): Promise<AttendanceCalendarSession[]> {
    const params = new URLSearchParams();
    if (month) params.append('month', month.toString());
    if (year) params.append('year', year.toString());
    const query = params.toString() ? `?${params.toString()}` : '';
    const response = await client.get(`/students/${studentId}/attendance-calendar${query}`);
    const payload = response.data;

    if (Array.isArray(payload)) {
      return payload;
    }

    if (Array.isArray(payload?.sessions)) {
      return payload.sessions;
    }

    return [];
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

  async submitAdmissionRequest(studentId: string, data: {
    patient_id: string;
    faculty_id: string;
    insurance_category_id?: string;
    department?: string;
    ward?: string;
    bed_number?: string;
    reason: string;
    diagnosis?: string;
    notes?: string;
    referring_doctor?: string;
  }) {
    const response = await client.post(`/students/${studentId}/admission-requests`, data);
    return response.data;
  },

  async getAdmissionRequests(studentId: string) {
    const response = await client.get(`/students/${studentId}/admission-requests`);
    return response.data;
  },

  async markNotificationsRead(studentId: string) {
    const response = await client.put(`/students/${studentId}/notifications/read`);
    return response.data;
  },

  async getPreviousPatients(studentId: string): Promise<AssignedPatient[]> {
    const response = await client.get(`/students/${studentId}/previous-patients`);
    return response.data;
  },

  async submitPrescription(studentId: string, data: {
    patient_id: string;
    faculty_id: string;
    department?: string;
    notes?: string;
    diagnosis?: string;
    medications: Array<{
      name: string;
      dosage: string;
      frequency: string;
      duration: string;
      timing?: string;
      instructions?: string;
      start_date: string;
      end_date: string;
    }>;
  }) {
    const response = await client.post(`/students/${studentId}/prescriptions/submit`, data);
    return response.data;
  },
};
