import { getProcedureFields } from '$lib/config/procedure-fields';
import type { FormDefinition, FormFieldDefinition } from '$lib/types/forms';

const CASE_RECORD_STANDARD_KEYS = new Set(['findings', 'diagnosis', 'treatment', 'notes']);

export function buildCaseRecordProcedureMap(forms: FormDefinition[]): Record<string, string[]> {
	const map: Record<string, string[]> = {};

	for (const form of forms) {
		if (form.form_type !== 'CASE_RECORD' || !form.is_active || !form.department || !form.procedure_name) {
			continue;
		}
		if (!map[form.department]) {
			map[form.department] = [];
		}
		if (!map[form.department].includes(form.procedure_name)) {
			map[form.department].push(form.procedure_name);
		}
	}

	return map;
}

export function mergeProcedureMaps(
	baseMap: Record<string, string[]>,
	formMap: Record<string, string[]>
): Record<string, string[]> {
	const merged: Record<string, string[]> = {};
	for (const [department, procedures] of Object.entries(baseMap)) {
		merged[department] = [...procedures];
	}

	for (const [department, procedures] of Object.entries(formMap)) {
		if (!merged[department]) {
			merged[department] = [];
		}
		for (const procedure of procedures) {
			if (!merged[department].includes(procedure)) {
				merged[department].push(procedure);
			}
		}
	}

	return merged;
}

export function resolveCaseRecordFields(
	forms: FormDefinition[],
	department: string,
	procedure: string
): FormFieldDefinition[] | null {
	const form = forms.find(
		(item) =>
			item.form_type === 'CASE_RECORD' &&
			item.is_active &&
			item.department === department &&
			item.procedure_name === procedure
	);

	if (form?.fields?.length) {
		return form.fields;
	}

	return getProcedureFields(department, procedure);
}

export function stringifyFormValue(value: any): string {
	if (value == null || value === '') {
		return '';
	}
	if (Array.isArray(value)) {
		return value.map((item) => stringifyFormValue(item)).filter(Boolean).join(', ');
	}
	if (typeof File !== 'undefined' && value instanceof File) {
		return value.name;
	}
	if (typeof FileList !== 'undefined' && value instanceof FileList) {
		return Array.from(value).map((file) => file.name).join(', ');
	}
	if (typeof value === 'object') {
		return JSON.stringify(value);
	}
	return String(value);
}

export function buildCaseRecordDescription(
	fields: FormFieldDefinition[] | null,
	values: Record<string, any>
): string {
	if (!fields) {
		return '';
	}

	const parts: string[] = [];
	for (const field of fields) {
		if (CASE_RECORD_STANDARD_KEYS.has(field.key)) {
			continue;
		}
		const rendered = stringifyFormValue(values[field.key]);
		if (rendered) {
			parts.push(`${field.label}: ${rendered}`);
		}
	}

	return parts.join('; ');
}
