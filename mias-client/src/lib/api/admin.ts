import client from './client';

// ── Types ────────────────────────────────────────────────────────────

export interface AdminDashboard {
  total_patients: number;
  total_students: number;
  total_faculty: number;
  total_departments: number;
  total_users: number;
  active_users: number;
  blocked_users: number;
  active_admissions: number;
  total_prescriptions: number;
  pending_approvals: number;
  patient_categories: Record<string, number>;
  recent_registrations: number;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: string;
  name: string;
  is_active: boolean;
  created_at: string | null;
  last_login: string | null;
}

export interface UserListResponse {
  items: AdminUser[];
  total: number;
  page: number;
  limit: number;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description: string | null;
  head_faculty_id: string | null;
  head_faculty_name: string | null;
  is_active: boolean;
  faculty_count: number;
  created_at: string | null;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface TrendData {
  period_days: number;
  registrations: TrendPoint[];
  admissions: TrendPoint[];
  prescriptions: TrendPoint[];
  vitals: TrendPoint[];
}

export interface StudentItem {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  program: string;
  gpa: number;
  academic_standing: string;
}

export interface Programme {
  id: string;
  name: string;
  code: string;
  description: string | null;
  degree_type: string | null;
  duration_years: string | null;
  is_active: boolean;
  student_count: number;
  group_count?: number;
  created_at: string | null;
}

export interface AcademicGroup {
  id: string;
  programme_id: string;
  programme_name: string | null;
  name: string;
  description: string | null;
  is_active: boolean;
  student_count: number;
  target_count: number;
  student_ids: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface AcademicTarget {
  id: string;
  group_id: string;
  group_name: string | null;
  programme_id: string | null;
  programme_name: string | null;
  form_definition_id: string | null;
  form_name: string | null;
  metric_name: string;
  metric_key: string;
  category: string;
  target_value: number;
  sort_order: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface AcademicWeightageItem {
  form_definition_id: string;
  slug: string | null;
  name: string | null;
  department: string | null;
  procedure_name: string | null;
  section: string | null;
  points: number;
  has_weightage: boolean;
  updated_at: string | null;
}

export interface AcademicOverviewStudent {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  program: string;
  gpa: number;
  academic_standing: string;
  academic_group_id: string | null;
  academic_group_name: string | null;
}

export interface AcademicOverviewResponse {
  programmes: Programme[];
  groups: AcademicGroup[];
  targets: AcademicTarget[];
  weightages: AcademicWeightageItem[];
  students: AcademicOverviewStudent[];
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

export interface AcademicManagerGroupStudent {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  program: string;
  gpa: number;
  academic_standing: string;
  attendance_overall: number | null;
  approved_case_records: number;
  pending_approvals: number;
  overall_percent: number;
  total_earned_points: number;
  total_possible_points: number;
}

export interface AcademicManagerGroupSummary {
  student_count: number;
  target_count: number;
  avg_gpa: number;
  avg_attendance_overall: number;
  approved_case_records: number;
  pending_approvals: number;
  standing_breakdown: Record<string, number>;
}

export interface AcademicManagerGroupDetail {
  group: AcademicGroup;
  students: AcademicManagerGroupStudent[];
  targets: AcademicTarget[];
  summary: AcademicManagerGroupSummary;
}

export interface AcademicManagerPerformanceItem {
  student_id: string;
  student_name: string;
  programme: string;
  group_id: string | null;
  group_name: string | null;
  year: number;
  semester: number;
  gpa: number;
  attendance_overall: number | null;
  approved_case_records: number;
  pending_case_records: number;
  completed_targets: number;
  total_targets: number;
  overall_percent: number;
  total_earned_points: number;
  avg_approval_score: number | null;
}

export interface AcademicManagerPerformanceSummary {
  student_count: number;
  avg_overall_percent: number;
  avg_gpa: number;
  avg_attendance_overall: number;
  total_approved_case_records: number;
}

export interface AcademicManagerPerformanceResponse {
  items: AcademicManagerPerformanceItem[];
  total: number;
  page: number;
  limit: number;
  summary: AcademicManagerPerformanceSummary;
}

export interface AcademicManagerFeedbackItem {
  approval_id: string;
  student_id: string | null;
  student_name: string | null;
  group_id: string | null;
  group_name: string | null;
  case_record_id: string | null;
  form_name: string | null;
  department: string | null;
  procedure_name: string | null;
  status: string;
  score: number | null;
  grade: string | null;
  comments: string | null;
  faculty_id: string | null;
  faculty_name: string | null;
  created_at: string | null;
  processed_at: string | null;
}

export interface AcademicManagerFeedbackSummary {
  total_feedback_items: number;
  approved_with_comments: number;
  rejected_with_comments: number;
  avg_score: number | null;
  department_breakdown: Record<string, number>;
}

export interface AcademicManagerFeedbackResponse {
  items: AcademicManagerFeedbackItem[];
  total: number;
  page: number;
  limit: number;
  summary: AcademicManagerFeedbackSummary;
}

export interface AcademicManagerActivityTimelineItem {
  period: string;
  case_records_created: number;
  approvals_processed: number;
  approved_count: number;
  rejected_count: number;
  earned_points: number;
}

export interface AcademicManagerRecentActivityItem {
  type: 'CASE_RECORD_SUBMITTED' | 'CASE_RECORD_APPROVED' | 'CASE_RECORD_REJECTED';
  student_id: string | null;
  student_name: string | null;
  group_name: string | null;
  case_record_id: string;
  form_name: string | null;
  department: string | null;
  procedure_name: string | null;
  score: number | null;
  comments: string | null;
  timestamp: string | null;
}

export interface AcademicManagerActivitySummary {
  total_case_records_created: number;
  total_approvals_processed: number;
  total_approved: number;
  total_rejected: number;
  total_earned_points: number;
}

export interface AcademicManagerActivityResponse {
  timeline: AcademicManagerActivityTimelineItem[];
  recent_activity: AcademicManagerRecentActivityItem[];
  summary: AcademicManagerActivitySummary;
}

export interface AcademicManagerTargetCompletionItem {
  target_id: string | null;
  metric_name: string;
  group_id: string | null;
  group_name: string | null;
  target_value_total: number;
  completed_value_total: number;
  completion_percent: number;
}

export interface AcademicManagerDepartmentDistributionItem {
  department: string;
  approved_count: number;
  earned_points: number;
}

export interface AcademicManagerFormDistributionItem {
  form_definition_id: string | null;
  form_name: string;
  approved_count: number;
  earned_points: number;
}

export interface AcademicManagerScoreDistributionItem {
  bucket: string;
  count: number;
}

export interface AcademicManagerGroupComparisonItem {
  group_id: string | null;
  group_name: string | null;
  student_count: number;
  avg_progress_percent: number;
  avg_gpa: number;
  approved_case_records: number;
  total_earned_points: number;
}

export interface AcademicManagerAnalyticsOverview {
  student_count: number;
  group_count: number;
  approved_case_records: number;
  pending_approvals: number;
  avg_gpa: number;
  avg_attendance_overall: number;
  avg_overall_progress_percent: number;
  total_earned_points: number;
}

export interface AcademicManagerAnalyticsResponse {
  overview: AcademicManagerAnalyticsOverview;
  target_completion: AcademicManagerTargetCompletionItem[];
  department_distribution: AcademicManagerDepartmentDistributionItem[];
  form_distribution: AcademicManagerFormDistributionItem[];
  score_distribution: AcademicManagerScoreDistributionItem[];
  group_comparison: AcademicManagerGroupComparisonItem[];
}

export type AIProviderType = 'OPENAI' | 'ANTHROPIC' | 'GEMINI' | 'OPENAI_COMPATIBLE';

export interface PatientCategoryConfig {
  id: string;
  name: string;
  description: string | null;
  color_primary: string;
  color_secondary: string;
  is_active: boolean;
  sort_order: number;
  registration_fee: number;
  patient_count: number;
  created_at: string | null;
}

export interface AIProviderConfigRow {
  id: string;
  display_name: string;
  provider: AIProviderType;
  model: string;
  base_url: string | null;
  system_prompt: string | null;
  temperature: number;
  batch_size: number;
  is_enabled: boolean;
  has_api_key: boolean;
  masked_api_key: string | null;
  last_tested_at: string | null;
  last_test_status: string | null;
  last_error: string | null;
}

export interface AIProviderConfigResponse {
  items: AIProviderConfigRow[];
  provider_defaults: Record<string, string>;
}

export interface AIProviderTestResult {
  message: string;
  id: string;
  provider: AIProviderType;
  model: string;
  preview: {
    findings: string;
    diagnosis: string;
    treatment: string;
  };
}

export interface VitalParameter {
  id: string;
  name: string;
  display_name: string;
  category: string;
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  value_style: 'single' | 'slash';
  is_active: boolean;
  sort_order: number;
}

export interface ICDCodeRecord {
  id: string;
  code: string;
  description: string;
  category: string;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface ICDCodeCreate {
  code: string;
  description: string;
  category?: string;
  is_active?: boolean;
}

export interface VitalParameterCreate {
  name: string;
  display_name: string;
  category?: string;
  unit: string;
  min_value?: number;
  max_value?: number;
  value_style?: 'single' | 'slash';
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminCreateUserPayload {
  username: string;
  email: string;
  password: string;
  role:
    | 'PATIENT'
    | 'STUDENT'
    | 'FACULTY'
    | 'ACADEMIC_MANAGER'
    | 'ADMIN'
    | 'RECEPTION'
    | 'NURSE'
    | 'NURSE_SUPERINTENDENT'
    | 'NUTRITIONIST'
    | 'LAB_TECHNICIAN'
    | 'BILLING'
    | 'ACCOUNTS'
    | 'PHARMACY'
    | 'OT_MANAGER'
    | 'MRD';
  name?: string;
  photo?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  phone?: string;
  address?: string;
  category?: string;
  aadhaar_id?: string;
  abha_id?: string;
  primary_diagnosis?: string;
  diagnosis_doctor?: string;
  diagnosis_date?: string;
  diagnosis_time?: string;
  year?: number;
  semester?: number;
  program?: string;
  degree?: string;
  gpa?: number;
  academic_standing?: string;
  academic_advisor?: string;
  department?: string;
  specialty?: string;
  availability?: string;
  clinic_id?: string;
  hospital?: string;
  ward?: string;
  shift?: string;
  counter_name?: string;
}

// ── API ──────────────────────────────────────────────────────────────

export interface BulkImportRowResult {
  row: number;
  username: string;
  status: 'created' | 'failed';
  error?: string;
}

export interface BulkImportResponse {
  created: number;
  failed: number;
  total: number;
  results: BulkImportRowResult[];
}

export const adminApi = {
  // Dashboard
  async getDashboard(): Promise<AdminDashboard> {
    const r = await client.get('/admin/dashboard');
    return r.data;
  },

  // Users
  async getUsers(params?: {
    role?: string;
    search?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<UserListResponse> {
    const r = await client.get('/admin/users', { params });
    return r.data;
  },

  async blockUser(userId: string) {
    const r = await client.put(`/admin/users/${userId}/block`);
    return r.data;
  },

  async unblockUser(userId: string) {
    const r = await client.put(`/admin/users/${userId}/unblock`);
    return r.data;
  },

  async deleteUser(userId: string) {
    const r = await client.delete(`/admin/users/${userId}`);
    return r.data;
  },

  async createUser(data: AdminCreateUserPayload) {
    const r = await client.post('/admin/users', data);
    return r.data;
  },

  async bulkImportUsers(file: File): Promise<BulkImportResponse> {
    const form = new FormData();
    form.append('file', file);
    const r = await client.post('/admin/users/bulk-import', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return r.data;
  },

  // Departments
  async getDepartments(): Promise<Department[]> {
    const r = await client.get('/admin/departments');
    return r.data;
  },

  async createDepartment(data: { name: string; code: string; description?: string }) {
    const r = await client.post('/admin/departments', data);
    return r.data;
  },

  async updateDepartment(deptId: string, data: Partial<{ name: string; code: string; description: string; is_active: boolean }>) {
    const r = await client.put(`/admin/departments/${deptId}`, data);
    return r.data;
  },

  async deleteDepartment(deptId: string) {
    const r = await client.delete(`/admin/departments/${deptId}`);
    return r.data;
  },

  // Analytics
  async getTrends(days = 30): Promise<TrendData> {
    const r = await client.get('/admin/analytics/trends', { params: { days } });
    return r.data;
  },

  async getDepartmentStats() {
    const r = await client.get('/admin/analytics/department-stats');
    return r.data;
  },

  async getRoleDistribution(): Promise<Record<string, number>> {
    const r = await client.get('/admin/analytics/role-distribution');
    return r.data;
  },

  // Students list
  async getStudents(params?: { year?: number; program?: string }): Promise<StudentItem[]> {
    const r = await client.get('/admin/students', { params });
    return r.data;
  },

  // System info
  async getSystemInfo() {
    const r = await client.get('/admin/system-info');
    return r.data;
  },

  // Programmes
  async getProgrammes(): Promise<Programme[]> {
    const r = await client.get('/admin/programmes');
    return r.data;
  },

  async createProgramme(data: { name: string; code: string; description?: string; degree_type?: string; duration_years?: string }) {
    const r = await client.post('/admin/programmes', data);
    return r.data;
  },

  async updateProgramme(progId: string, data: Partial<{ name: string; code: string; description: string; degree_type: string; duration_years: string; is_active: boolean }>) {
    const r = await client.put(`/admin/programmes/${progId}`, data);
    return r.data;
  },

  async deleteProgramme(progId: string) {
    const r = await client.delete(`/admin/programmes/${progId}`);
    return r.data;
  },

  async getAcademicsOverview(): Promise<AcademicOverviewResponse> {
    const r = await client.get('/admin/programmes/academics/overview');
    return r.data;
  },

  async getAcademicGroups(programmeId?: string): Promise<AcademicGroup[]> {
    const r = await client.get('/admin/programmes/academic-groups', {
      params: programmeId ? { programme_id: programmeId } : undefined,
    });
    return r.data;
  },

  async createAcademicGroup(data: {
    programme_id: string;
    name: string;
    description?: string;
    is_active?: boolean;
    student_ids?: string[];
  }): Promise<AcademicGroup> {
    const r = await client.post('/admin/programmes/academic-groups', data);
    return r.data;
  },

  async updateAcademicGroup(groupId: string, data: {
    programme_id: string;
    name: string;
    description?: string;
    is_active?: boolean;
    student_ids?: string[];
  }): Promise<AcademicGroup> {
    const r = await client.put(`/admin/programmes/academic-groups/${groupId}`, data);
    return r.data;
  },

  async deleteAcademicGroup(groupId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/programmes/academic-groups/${groupId}`);
    return r.data;
  },

  async getAcademicTargets(groupId?: string): Promise<AcademicTarget[]> {
    const r = await client.get('/admin/programmes/academic-targets', {
      params: groupId ? { group_id: groupId } : undefined,
    });
    return r.data;
  },

  async createAcademicTarget(data: {
    group_id: string;
    form_definition_id?: string;
    metric_name: string;
    category?: string;
    target_value?: number;
    sort_order?: number;
  }): Promise<AcademicTarget> {
    const r = await client.post('/admin/programmes/academic-targets', data);
    return r.data;
  },

  async updateAcademicTarget(targetId: string, data: {
    group_id: string;
    form_definition_id?: string;
    metric_name: string;
    category?: string;
    target_value?: number;
    sort_order?: number;
  }): Promise<AcademicTarget> {
    const r = await client.put(`/admin/programmes/academic-targets/${targetId}`, data);
    return r.data;
  },

  async deleteAcademicTarget(targetId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/programmes/academic-targets/${targetId}`);
    return r.data;
  },

  async getAcademicWeightages(): Promise<AcademicWeightageItem[]> {
    const r = await client.get('/admin/programmes/academic-weightages');
    return r.data;
  },

  async updateAcademicWeightage(formDefinitionId: string, data: {
    points: number;
  }): Promise<AcademicWeightageItem> {
    const r = await client.put(`/admin/programmes/academic-weightages/${formDefinitionId}`, data);
    return r.data;
  },

  async getStudentAcademicProgress(studentId: string): Promise<StudentAcademicProgress> {
    const r = await client.get(`/admin/programmes/students/${studentId}/academic-progress`);
    return r.data;
  },

  async getAcademicManagerGroupSummary(groupId: string): Promise<AcademicManagerGroupDetail> {
    const r = await client.get(`/admin/programmes/academic-groups/${groupId}/summary`);
    return r.data;
  },

  async getAcademicManagerPerformance(params?: {
    programme_id?: string;
    group_id?: string;
    year?: number;
    semester?: number;
    search?: string;
    sort_by?: 'progress' | 'points' | 'approved_records' | 'gpa' | 'attendance';
    page?: number;
    limit?: number;
  }): Promise<AcademicManagerPerformanceResponse> {
    const r = await client.get('/admin/programmes/academic-performance', { params });
    return r.data;
  },

  async getAcademicManagerFeedback(params?: {
    programme_id?: string;
    group_id?: string;
    student_id?: string;
    status?: 'APPROVED' | 'REJECTED';
    department?: string;
    has_comments?: boolean;
    from_date?: string;
    to_date?: string;
    page?: number;
    limit?: number;
  }): Promise<AcademicManagerFeedbackResponse> {
    const r = await client.get('/admin/programmes/academic-feedback', { params });
    return r.data;
  },

  async getAcademicManagerActivity(params?: {
    programme_id?: string;
    group_id?: string;
    student_id?: string;
    from_date?: string;
    to_date?: string;
    granularity?: 'day' | 'week' | 'month';
  }): Promise<AcademicManagerActivityResponse> {
    const r = await client.get('/admin/programmes/academic-activity', { params });
    return r.data;
  },

  async getAcademicManagerAnalytics(params?: {
    programme_id?: string;
    group_id?: string;
    year?: number;
    semester?: number;
    from_date?: string;
    to_date?: string;
  }): Promise<AcademicManagerAnalyticsResponse> {
    const r = await client.get('/admin/programmes/academic-analytics', { params });
    return r.data;
  },

  async getPatientCategories(): Promise<PatientCategoryConfig[]> {
    const r = await client.get('/admin/patient-categories');
    return r.data;
  },

  async getPublicPatientCategories(): Promise<{ id: string; name: string; description: string | null; color_primary: string; color_secondary: string; registration_fee: number }[]> {
    const r = await client.get('/admin/patient-categories/public');
    return r.data;
  },

  async createPatientCategory(data: {
    name: string;
    description?: string;
    color_primary?: string;
    color_secondary?: string;
    is_active?: boolean;
    is_default?: boolean;
    sort_order?: number;
    registration_fee?: number;
  }): Promise<PatientCategoryConfig> {
    const r = await client.post('/admin/patient-categories', data);
    return r.data;
  },

  async updatePatientCategory(categoryId: string, data: Partial<{
    name: string;
    description: string;
    color_primary: string;
    color_secondary: string;
    is_active: boolean;
    is_default: boolean;
    sort_order: number;
    registration_fee: number;
  }>): Promise<PatientCategoryConfig> {
    const r = await client.patch(`/admin/patient-categories/${categoryId}`, data);
    return r.data;
  },

  async deletePatientCategory(categoryId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/patient-categories/${categoryId}`);
    return r.data;
  },

  async getICDCodes(params?: { search?: string; include_inactive?: boolean }): Promise<ICDCodeRecord[]> {
    const r = await client.get('/admin/icd-codes', { params });
    return r.data;
  },

  async createICDCode(data: ICDCodeCreate): Promise<ICDCodeRecord> {
    const r = await client.post('/admin/icd-codes', data);
    return r.data;
  },

  async updateICDCode(icdId: string, data: Partial<ICDCodeCreate>): Promise<ICDCodeRecord> {
    const r = await client.patch(`/admin/icd-codes/${icdId}`, data);
    return r.data;
  },

  async deleteICDCode(icdId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/icd-codes/${icdId}`);
    return r.data;
  },

  async getAIProviderConfigs(): Promise<AIProviderConfigResponse> {
    const r = await client.get('/admin/ai-provider');
    return r.data;
  },

  async createAIProviderConfig(data: {
    display_name?: string;
    provider?: AIProviderType;
    model?: string;
    api_key?: string;
    base_url?: string;
    system_prompt?: string;
    temperature?: number;
    batch_size?: number;
    is_enabled?: boolean;
  }): Promise<AIProviderConfigRow & { message: string }> {
    const r = await client.post('/admin/ai-provider', data);
    return r.data;
  },

  async updateAIProviderConfig(configId: string, data: Partial<{
    display_name: string;
    provider: AIProviderType;
    model: string;
    api_key: string;
    base_url: string;
    system_prompt: string;
    temperature: number;
    batch_size: number;
    is_enabled: boolean;
  }>): Promise<AIProviderConfigRow & { message: string }> {
    const r = await client.patch(`/admin/ai-provider/${configId}`, data);
    return r.data;
  },

  async activateAIProviderConfig(configId: string): Promise<AIProviderConfigRow & { message: string }> {
    const r = await client.post(`/admin/ai-provider/${configId}/activate`);
    return r.data;
  },

  async deleteAIProviderConfig(configId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/ai-provider/${configId}`);
    return r.data;
  },

  async testAIProviderConnection(configId: string): Promise<AIProviderTestResult> {
    const r = await client.post(`/admin/ai-provider/${configId}/test`);
    return r.data;
  },

  // Vital Parameters
  async getVitalParameters(activeOnly = false): Promise<VitalParameter[]> {
    const r = await client.get('/admin/vital-parameters', { params: { active_only: activeOnly } });
    return r.data;
  },

  async createVitalParameter(data: VitalParameterCreate): Promise<VitalParameter> {
    const r = await client.post('/admin/vital-parameters', data);
    return r.data;
  },

  async updateVitalParameter(paramId: string, data: Partial<VitalParameterCreate>): Promise<VitalParameter> {
    const r = await client.patch(`/admin/vital-parameters/${paramId}`, data);
    return r.data;
  },

  async deleteVitalParameter(paramId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/vital-parameters/${paramId}`);
    return r.data;
  },
};
