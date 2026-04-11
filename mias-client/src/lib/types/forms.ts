export type FormType =
	| 'CASE_RECORD'
	| 'CLINICAL'
	| 'LABORATORY'
	| 'ADMINISTRATIVE'
	| 'ADMISSION'
	| 'ADMISSION_REQUEST'
	| 'ADMISSION_INTAKE'
	| 'ADMISSION_DISCHARGE'
	| 'ADMISSION_TRANSFER'
	| 'PROFILE'
	| 'PROFILE_EDIT'
	| 'PRESCRIPTION'
	| 'PRESCRIPTION_CREATE'
	| 'PRESCRIPTION_EDIT'
	| 'PRESCRIPTION_REQUEST'
	| 'VITAL_ENTRY'
	| 'CUSTOM';

export type FormFieldType =
	| 'text'
	| 'textarea'
	| 'number'
	| 'select'
	| 'diagnosis'
	| 'date'
	| 'file'
	| 'email'
	| 'password'
	| 'tel';

export type FormSection = string;

export interface FormCategory {
	id: string;
	name: string;
	sort_order: number;
	is_active: boolean;
	is_system: boolean;
	created_at: string | null;
}

export interface FormFieldDefinition {
	key: string;
	label: string;
	type: FormFieldType;
	required?: boolean;
	placeholder?: string;
	options?: string[];
	rows?: number;
	accept?: string;
	multiple?: boolean;
	help_text?: string;
}

export interface UploadedFormFile {
	name: string;
	url: string;
	content_type?: string | null;
	size?: number | null;
	uploaded_at?: string | null;
}

export interface FormDefinition {
	id: string;
	slug: string;
	name: string;
	description: string | null;
	form_type: FormType | string;
	section?: FormSection | string;
	department: string | null;
	procedure_name: string | null;
	fields: FormFieldDefinition[];
	sort_order: number;
	is_active: boolean;
	created_at: string | null;
	updated_at: string | null;
}
