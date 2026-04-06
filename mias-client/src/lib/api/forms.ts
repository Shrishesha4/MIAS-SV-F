import client from './client';
import type { FormDefinition, FormFieldDefinition, FormType } from '$lib/types/forms';

export interface FormDefinitionPayload {
	name: string;
	description?: string;
	form_type: FormType | string;
	department?: string;
	procedure_name?: string;
	fields: FormFieldDefinition[];
	sort_order?: number;
	is_active?: boolean;
}

export const formsApi = {
	async getForms(params?: {
		form_type?: string;
		department?: string;
		procedure_name?: string;
		include_inactive?: boolean;
	}): Promise<FormDefinition[]> {
		const response = await client.get('/forms', { params });
		return response.data;
	},

	async createForm(data: FormDefinitionPayload): Promise<FormDefinition> {
		const response = await client.post('/forms', data);
		return response.data;
	},

	async updateForm(formId: string, data: FormDefinitionPayload): Promise<FormDefinition> {
		const response = await client.put(`/forms/${formId}`, data);
		return response.data;
	},
};
