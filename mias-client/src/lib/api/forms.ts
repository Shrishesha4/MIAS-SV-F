import client from './client';
import type { FormDefinition, FormFieldDefinition, FormType, UploadedFormFile } from '$lib/types/forms';

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

	async uploadFile(file: File, options?: { context?: string; fieldKey?: string }): Promise<UploadedFormFile> {
		const formData = new FormData();
		formData.append('file', file);
		if (options?.context) {
			formData.append('context', options.context);
		}
		if (options?.fieldKey) {
			formData.append('field_key', options.fieldKey);
		}
		const response = await client.post('/forms/uploads', formData, {
			headers: { 'Content-Type': 'multipart/form-data' },
		});
		return response.data;
	},
};
