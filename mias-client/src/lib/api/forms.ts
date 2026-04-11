import client from './client';
import type { FormCategory, FormDefinition, FormFieldDefinition, FormSection, FormType, UploadedFormFile } from '$lib/types/forms';

type ApiFormFieldDefinition = FormFieldDefinition & {
	id?: string;
};

type ApiFormDefinition = Omit<FormDefinition, 'fields'> & {
	fields: ApiFormFieldDefinition[];
};

function normalizeFormField(field: ApiFormFieldDefinition): FormFieldDefinition {
	return {
		key: field.key ?? field.id ?? '',
		label: field.label,
		type: field.type,
		required: field.required,
		placeholder: field.placeholder,
		options: field.options,
		rows: field.rows,
		accept: field.accept,
		multiple: field.multiple,
		help_text: field.help_text,
	};
}

function normalizeFormDefinition(form: ApiFormDefinition): FormDefinition {
	return {
		...form,
		fields: (form.fields ?? []).map(normalizeFormField),
	};
}

export interface FormDefinitionPayload {
	name: string;
	description?: string;
	form_type?: FormType | string;
	section?: FormSection | string;
	department?: string;
	procedure_name?: string;
	fields: FormFieldDefinition[];
	sort_order?: number;
	is_active?: boolean;
}

export interface FormCategoryPayload {
	name: string;
	sort_order?: number;
	is_active?: boolean;
}

export const formsApi = {
	async getFormCategories(): Promise<FormCategory[]> {
		const response = await client.get<FormCategory[]>('/forms/categories');
		return response.data;
	},

	async createFormCategory(data: FormCategoryPayload): Promise<FormCategory> {
		const response = await client.post<FormCategory>('/forms/categories', data);
		return response.data;
	},

	async getForms(params?: {
		form_type?: string;
		section?: string;
		department?: string;
		procedure_name?: string;
		include_inactive?: boolean;
	}): Promise<FormDefinition[]> {
		const response = await client.get<ApiFormDefinition[]>('/forms', { params });
		return response.data.map(normalizeFormDefinition);
	},

	async createForm(data: FormDefinitionPayload): Promise<FormDefinition> {
		const response = await client.post<ApiFormDefinition>('/forms', data);
		return normalizeFormDefinition(response.data);
	},

	async updateForm(formId: string, data: FormDefinitionPayload): Promise<FormDefinition> {
		const response = await client.put<ApiFormDefinition>(`/forms/${formId}`, data);
		return normalizeFormDefinition(response.data);
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
