export type FormType = 'CASE_RECORD' | 'ADMISSION' | 'PROFILE' | 'PRESCRIPTION' | 'CUSTOM';

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

export interface FormDefinition {
	id: string;
	slug: string;
	name: string;
	description: string | null;
	form_type: FormType | string;
	department: string | null;
	procedure_name: string | null;
	fields: FormFieldDefinition[];
	sort_order: number;
	is_active: boolean;
	created_at: string | null;
	updated_at: string | null;
}
