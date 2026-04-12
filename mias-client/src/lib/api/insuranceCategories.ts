import client from './client';

export interface WalkInType {
  value: string;
  label: string;
}

export interface PatientCategory {
  id: string;
  name: string;
  description: string | null;
}

export interface ClinicConfig {
  id: string;
  clinic_id: string;
  clinic_name: string;
  walk_in_type: string;
  walk_in_label: string;
  registration_fee: number;
  is_enabled: boolean;
}

export interface InsuranceCategory {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  patient_categories: PatientCategory[];
  clinic_configs: ClinicConfig[];
}

export interface InsuranceCategoryCreate {
  name: string;
  description?: string;
  is_active?: boolean;
  sort_order?: number;
  patient_category_ids?: string[];
}

export interface InsuranceCategoryUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  sort_order?: number;
  patient_category_ids?: string[];
}

export interface ClinicConfigUpdate {
  walk_in_type?: string;
  registration_fee?: number;
  is_enabled?: boolean;
}

export interface PublicInsuranceCategory {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
}

export interface PublicClinicInfo {
  config_id: string;
  clinic_id: string;
  clinic_name: string;
  clinic_type: string | null;
  department: string | null;
  location: string | null;
  walk_in_type: string;
  walk_in_label: string;
  registration_fee: number;
}

export const insuranceCategoriesApi = {
  // Walk-in types
  async getWalkInTypes(): Promise<WalkInType[]> {
    const response = await client.get('/insurance-categories/walk-in-types');
    return response.data;
  },

  // Admin CRUD operations
  async listCategories(): Promise<InsuranceCategory[]> {
    const response = await client.get('/insurance-categories');
    return response.data;
  },

  async createCategory(data: InsuranceCategoryCreate): Promise<InsuranceCategory & { message: string }> {
    const response = await client.post('/insurance-categories', data);
    return response.data;
  },

  async updateCategory(categoryId: string, data: InsuranceCategoryUpdate): Promise<InsuranceCategory & { message: string }> {
    const response = await client.patch(`/insurance-categories/${categoryId}`, data);
    return response.data;
  },

  async deleteCategory(categoryId: string): Promise<{ message: string }> {
    const response = await client.delete(`/insurance-categories/${categoryId}`);
    return response.data;
  },

  // Clinic configuration (by config ID)
  async updateClinicConfig(
    categoryId: string,
    configId: string,
    data: ClinicConfigUpdate
  ): Promise<ClinicConfig & { message: string }> {
    const response = await client.patch(`/insurance-categories/${categoryId}/clinics/${configId}`, data);
    return response.data;
  },

  // Clinic configuration by category + clinic ID (for admin panel)
  async getClinicConfigByClinic(
    categoryId: string,
    clinicId: string
  ): Promise<ClinicConfig & { exists: boolean }> {
    const response = await client.get('/insurance-categories/clinic-config', {
      params: { category_id: categoryId, clinic_id: clinicId }
    });
    return response.data;
  },

  async saveClinicConfigByClinic(
    categoryId: string,
    clinicId: string,
    data: ClinicConfigUpdate
  ): Promise<ClinicConfig & { message: string }> {
    const response = await client.patch('/insurance-categories/clinic-config', data, {
      params: { category_id: categoryId, clinic_id: clinicId }
    });
    return response.data;
  },

  // Public endpoints (no auth required)
  async listPublicCategories(): Promise<PublicInsuranceCategory[]> {
    const response = await client.get('/insurance-categories/public/list');
    return response.data;
  },

  async getCategoryClinics(categoryId: string): Promise<PublicClinicInfo[]> {
    const response = await client.get(`/insurance-categories/public/${categoryId}/clinics`);
    return response.data;
  },
};
