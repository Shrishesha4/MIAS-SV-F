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
  created_at: string | null;
}

export type AIProviderType = 'OPENAI' | 'ANTHROPIC' | 'GEMINI' | 'OPENAI_COMPATIBLE';

export interface PatientCategoryConfig {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  is_default: boolean;
  sort_order: number;
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
  is_active: boolean;
  sort_order: number;
}

export interface VitalParameterCreate {
  name: string;
  display_name: string;
  category?: string;
  unit?: string;
  min_value?: number;
  max_value?: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdminCreateUserPayload {
  username: string;
  email: string;
  password: string;
  role: string;
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
  hospital?: string;
  ward?: string;
  shift?: string;
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

  async getPatientCategories(): Promise<PatientCategoryConfig[]> {
    const r = await client.get('/admin/patient-categories');
    return r.data;
  },

  async createPatientCategory(data: {
    name: string;
    description?: string;
    is_active?: boolean;
    is_default?: boolean;
    sort_order?: number;
  }): Promise<PatientCategoryConfig> {
    const r = await client.post('/admin/patient-categories', data);
    return r.data;
  },

  async updatePatientCategory(categoryId: string, data: Partial<{
    name: string;
    description: string;
    is_active: boolean;
    is_default: boolean;
    sort_order: number;
  }>): Promise<PatientCategoryConfig> {
    const r = await client.patch(`/admin/patient-categories/${categoryId}`, data);
    return r.data;
  },

  async deletePatientCategory(categoryId: string): Promise<{ message: string }> {
    const r = await client.delete(`/admin/patient-categories/${categoryId}`);
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
