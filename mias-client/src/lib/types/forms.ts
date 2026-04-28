// ─── Field & form types ──────────────────────────────────────────────────────

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
	| 'date'
	| 'file'
	| 'email'
	| 'password'
	| 'tel'
	| 'diagnosis'
	| 'department_select'
	| 'faculty_select'
	| 'clinic_select'
	| 'db_select';

export type FormSection = string;

// ─── Condition engine types ──────────────────────────────────────────────────

export type ConditionOperator =
	| 'equals'
	| 'not_equals'
	| 'greater_than'
	| 'less_than'
	| 'greater_than_or_equal'
	| 'less_than_or_equal'
	| 'contains'
	| 'includes'
	| 'empty'
	| 'not_empty';

/** A single field comparison predicate */
export interface RuleCondition {
	field: string;
	operator: ConditionOperator;
	value?: any;
}

/** Compound predicate: all / any of sub-conditions must pass */
export interface CompoundCondition {
	and?: RuleCondition[];
	or?: RuleCondition[];
}

export type AnyCondition = RuleCondition | CompoundCondition;

export type RuleActionType = 'show' | 'hide' | 'enable' | 'disable' | 'set_value' | 'set_options';

/** A single side-effect triggered by a rule */
export interface FormAction {
	action: RuleActionType;
	target: string;
	/** Used by set_value and set_options */
	value?: any;
}

/**
 * Declarative rule: if condition met → apply `then` actions, else apply `else` actions.
 * Rules are stored at form level and evaluated against current values.
 */
export interface FormRule {
	if: AnyCondition;
	then: FormAction[];
	else?: FormAction[];
}

/** Normalized runtime state produced by the engine */
export interface FormState {
	values: Record<string, any>;
	visibility: Record<string, boolean>;
	enabled: Record<string, boolean>;
	/** Dynamically overridden options per field key */
	options: Record<string, string[]>;
	errors: Record<string, string>;
}

// ─── Legacy field-level condition (simple yes/no shorthand) ──────────────────

/** @deprecated Use FormRule at form level instead. Kept for backward compatibility. */
export interface FieldCondition {
	field: string;
	operator: 'eq' | 'ne' | 'contains' | 'gt' | 'lt' | 'gte' | 'lte' | 'empty' | 'not_empty';
	value?: string | number | boolean;
}

// ─── Field & form definitions ────────────────────────────────────────────────

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
	/** Legacy per-field visibility shorthand. Prefer FormRule at form level. */
	condition?: FieldCondition;
	/** For db_select: which backend source to query (e.g. 'patients', 'labs') */
	db_source?: string;
	/** For db_select: static key=value filters applied to the lookup query */
	db_filters?: Record<string, string>;
}

export interface FormCategory {
	id: string;
	name: string;
	sort_order: number;
	is_active: boolean;
	is_system: boolean;
	created_at: string | null;
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
	/** Declarative conditional logic rules evaluated at runtime */
	rules?: FormRule[];
	sort_order: number;
	is_active: boolean;
	icon?: string | null;
	color?: string | null;
	allowed_roles?: string[] | null;
	created_at: string | null;
	updated_at: string | null;
}
