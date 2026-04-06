import { getProcedureFields } from '$lib/config/procedure-fields';
import type { FormDefinition, FormFieldDefinition, UploadedFormFile } from '$lib/types/forms';

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
	if (isUploadedFormFile(value)) {
		return value.url ? `${value.name} (${value.url})` : value.name;
	}
	if (typeof value === 'object') {
		return JSON.stringify(value);
	}
	return String(value);
}

export function resolveFormFieldsByType(
	forms: FormDefinition[],
	formType: string,
	fallbackFields: FormFieldDefinition[]
): FormFieldDefinition[] {
	const match = forms.find((form) => form.form_type === formType && form.is_active);
	if (match?.fields?.length) {
		return match.fields;
	}
	return fallbackFields;
}

export function mergeFieldOptions(
	fields: FormFieldDefinition[],
	overrides: Partial<Record<string, string[]>>
): FormFieldDefinition[] {
	return fields.map((field) => {
		const options = overrides[field.key];
		if (!options || field.type !== 'select') {
			return field;
		}
		return { ...field, options };
	});
}

export function isUploadedFormFile(value: any): value is UploadedFormFile {
	return Boolean(value && typeof value === 'object' && typeof value.name === 'string' && typeof value.url === 'string');
}

export function asOptionalString(value: any): string | undefined {
	const rendered = stringifyFormValue(value).trim();
	return rendered || undefined;
}

export function asOptionalNumber(value: any): number | undefined {
	if (value == null || value === '') {
		return undefined;
	}
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : undefined;
}

export function appendSupplementalText(base: string | undefined, extra: string): string | undefined {
	const trimmedBase = base?.trim();
	const trimmedExtra = extra.trim();
	if (!trimmedExtra) {
		return trimmedBase || undefined;
	}
	if (!trimmedBase) {
		return trimmedExtra;
	}
	return `${trimmedBase}\n\n${trimmedExtra}`;
}

export function buildSupplementalFormDescription(
	fields: FormFieldDefinition[],
	values: Record<string, any>,
	consumedKeys: Set<string>
): string {
	const parts: string[] = [];
	for (const field of fields) {
		if (consumedKeys.has(field.key)) {
			continue;
		}
		const rendered = stringifyFormValue(values[field.key]);
		if (rendered) {
			parts.push(`${field.label}: ${rendered}`);
		}
	}
	return parts.join('; ');
}

export async function persistFormFiles(
	fields: FormFieldDefinition[],
	values: Record<string, any>,
	uploadFile: (file: File, options: { context: string; fieldKey: string }) => Promise<UploadedFormFile>,
	context: string
): Promise<Record<string, any>> {
	const nextValues = { ...values };

	for (const field of fields) {
		if (field.type !== 'file') {
			continue;
		}

		const currentValue = nextValues[field.key];
		if (!currentValue) {
			continue;
		}

		if (Array.isArray(currentValue)) {
			const uploaded: any[] = [];
			for (const item of currentValue) {
				if (typeof File !== 'undefined' && item instanceof File) {
					uploaded.push(await uploadFile(item, { context, fieldKey: field.key }));
				} else {
					uploaded.push(item);
				}
			}
			nextValues[field.key] = uploaded;
			continue;
		}

		if (typeof File !== 'undefined' && currentValue instanceof File) {
			nextValues[field.key] = await uploadFile(currentValue, { context, fieldKey: field.key });
		}
	}

	return nextValues;
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
