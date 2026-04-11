import client from './client';

export interface LabInfo {
	id: string;
	name: string;
	block?: string;
	lab_type: string;
	department: string;
	location?: string;
	contact_phone?: string;
	operating_hours?: string;
	is_active: boolean;
	test_count?: number;
	group_count?: number;
}

export interface CreateLabRequest {
	name: string;
	block?: string;
	lab_type: string;
	department: string;
	location?: string;
	contact_phone?: string;
	operating_hours?: string;
	is_active?: boolean;
}

export interface UpdateLabRequest {
	name?: string;
	block?: string;
	lab_type?: string;
	department?: string;
	location?: string;
	contact_phone?: string;
	operating_hours?: string;
	is_active?: boolean;
}

// Lab Tests
export interface LabTest {
	id: string;
	lab_id: string;
	name: string;
	code: string;
	category: string;
	description?: string;
	sample_type?: string;
	turnaround_time?: string;
	is_active: boolean;
}

export interface CreateLabTestRequest {
	name: string;
	code: string;
	category: string;
	description?: string;
	sample_type?: string;
	turnaround_time?: string;
	is_active?: boolean;
}

export interface UpdateLabTestRequest {
	name?: string;
	code?: string;
	category?: string;
	description?: string;
	sample_type?: string;
	turnaround_time?: string;
	is_active?: boolean;
}

// Lab Test Groups
export interface LabTestGroup {
	id: string;
	lab_id: string;
	name: string;
	description?: string;
	is_active: boolean;
	tests: { id: string; name: string; code: string; category: string }[];
}

export interface CreateLabTestGroupRequest {
	name: string;
	description?: string;
	test_ids?: string[];
	is_active?: boolean;
}

export interface UpdateLabTestGroupRequest {
	name?: string;
	description?: string;
	test_ids?: string[];
	is_active?: boolean;
}

// Charge Master
export type ChargeCategory = 'CLINICAL' | 'LABS' | 'ADMIN';
export type ChargeTier = string;

export interface ChargeItem {
	id: string;
	item_code: string;
	name: string;
	category: ChargeCategory;
	description?: string;
	source_type?: string;
	source_id?: string;
	is_active: boolean;
	prices: Record<string, number>;
}

export interface CreateChargeItemRequest {
	item_code: string;
	name: string;
	category: ChargeCategory;
	description?: string;
	source_type?: string;
	source_id?: string;
	prices?: Record<string, number>;
	is_active?: boolean;
}

export interface UpdateChargeItemRequest {
	item_code?: string;
	name?: string;
	category?: ChargeCategory;
	description?: string;
	source_type?: string;
	source_id?: string;
	prices?: Record<string, number>;
	is_active?: boolean;
}

export const labsApi = {
	// Labs
	async getAll(): Promise<LabInfo[]> {
		const response = await client.get('/labs');
		return response.data;
	},

	async getById(id: string): Promise<LabInfo> {
		const response = await client.get(`/labs/${id}`);
		return response.data;
	},

	async create(data: CreateLabRequest): Promise<LabInfo> {
		const response = await client.post('/labs', data);
		return response.data;
	},

	async update(id: string, data: UpdateLabRequest): Promise<LabInfo> {
		const response = await client.put(`/labs/${id}`, data);
		return response.data;
	},

	async delete(id: string): Promise<void> {
		await client.delete(`/labs/${id}`);
	},

	// Lab Tests
	async getTests(labId: string): Promise<LabTest[]> {
		const response = await client.get(`/labs/${labId}/tests`);
		return response.data;
	},

	async createTest(labId: string, data: CreateLabTestRequest): Promise<LabTest> {
		const response = await client.post(`/labs/${labId}/tests`, data);
		return response.data;
	},

	async updateTest(labId: string, testId: string, data: UpdateLabTestRequest): Promise<LabTest> {
		const response = await client.put(`/labs/${labId}/tests/${testId}`, data);
		return response.data;
	},

	async deleteTest(labId: string, testId: string): Promise<void> {
		await client.delete(`/labs/${labId}/tests/${testId}`);
	},

	// Lab Test Groups
	async getGroups(labId: string): Promise<LabTestGroup[]> {
		const response = await client.get(`/labs/${labId}/groups`);
		return response.data;
	},

	async createGroup(labId: string, data: CreateLabTestGroupRequest): Promise<LabTestGroup> {
		const response = await client.post(`/labs/${labId}/groups`, data);
		return response.data;
	},

	async updateGroup(labId: string, groupId: string, data: UpdateLabTestGroupRequest): Promise<LabTestGroup> {
		const response = await client.put(`/labs/${labId}/groups/${groupId}`, data);
		return response.data;
	},

	async deleteGroup(labId: string, groupId: string): Promise<void> {
		await client.delete(`/labs/${labId}/groups/${groupId}`);
	}
};

export const chargesApi = {
	async getAll(category?: ChargeCategory): Promise<ChargeItem[]> {
		const params = category ? { category } : {};
		const response = await client.get('/charges', { params });
		return response.data;
	},

	async create(data: CreateChargeItemRequest): Promise<ChargeItem> {
		const response = await client.post('/charges', data);
		return response.data;
	},

	async update(id: string, data: UpdateChargeItemRequest): Promise<ChargeItem> {
		const response = await client.put(`/charges/${id}`, data);
		return response.data;
	},

	async delete(id: string): Promise<void> {
		await client.delete(`/charges/${id}`);
	}
};
