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

export interface FacultyItem {
  id: string;
  faculty_id: string;
  name: string;
  department: string;
  specialty: string;
  availability_status: string;
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

export interface AIProviderConfig {
  provider: AIProviderType;
  model: string;
  base_url: string | null;
  system_prompt: string | null;
  temperature: number;
  is_enabled: boolean;
  has_api_key: boolean;
  masked_api_key: string | null;
  last_tested_at: string | null;
  last_test_status: string | null;
  last_error: string | null;
  provider_defaults: Record<string, string>;
}

export interface AIProviderTestResult {
  message: string;
  provider: AIProviderType;
  model: string;
  preview: {
    findings: string;
    diagnosis: string;
    treatment: string;
  };
}

// ── API ──────────────────────────────────────────────────────────────

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

  async createUser(data: {
    username: string;
    email: string;
    password: string;
    role: string;
    name?: string;
    date_of_birth?: string;
    gender?: string;
    blood_group?: string;
    phone?: string;
    year?: number;
    semester?: number;
    program?: string;
    department?: string;
    specialty?: string;
  }) {
    const r = await client.post('/admin/users', data);
    return r.data;
  },

  // Departments
  async getDepartments(): Promise<Department[]> {
    const r = await client.get('/admin/departments');
    return r.data;
  },

  async createDepartment(data: { name: string; code: string; description?: string; head_faculty_id?: string }) {
    const r = await client.post('/admin/departments', data);
    return r.data;
  },

  async updateDepartment(deptId: string, data: Partial<{ name: string; code: string; description: string; head_faculty_id: string; is_active: boolean }>) {
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

  // Faculty list
  async getFaculty(department?: string): Promise<FacultyItem[]> {
    const r = await client.get('/admin/faculty', { params: department ? { department } : {} });
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

  async getAIProviderConfig(): Promise<AIProviderConfig> {
    const r = await client.get('/admin/ai-provider');
    return r.data;
  },

  async updateAIProviderConfig(data: {
    provider: AIProviderType;
    model: string;
    api_key?: string;
    base_url?: string;
    system_prompt?: string;
    temperature: number;
    is_enabled: boolean;
  }): Promise<AIProviderConfig & { message: string }> {
    const r = await client.put('/admin/ai-provider', data);
    return r.data;
  },

  async testAIProviderConnection(): Promise<AIProviderTestResult> {
    const r = await client.post('/admin/ai-provider/test');
    return r.data;
  },
};
