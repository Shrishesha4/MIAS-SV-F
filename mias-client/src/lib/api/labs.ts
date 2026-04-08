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

export const labsApi = {
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
	}
};
