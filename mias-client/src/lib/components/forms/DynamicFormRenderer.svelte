<script lang="ts">
	import { onMount } from 'svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import DiagnosisSuggestions from './DiagnosisSuggestions.svelte';
	import type { DiagnosisSuggestion as AIDiagnosisSuggestion } from '$lib/api/ai';
	import type { DiagnosisSuggestion as AutocompleteDiagnosisSuggestion } from '$lib/api/autocomplete';
	import type { FormFieldDefinition, FormRule } from '$lib/types/forms';
	import { createFormEngine } from '$lib/utils/formEngine';
	import { formsApi } from '$lib/api/forms';

	const DYNAMIC_SOURCES: Record<string, string> = {
		department_select: 'departments',
		faculty_select: 'faculty',
		clinic_select: 'clinics',
	};

	interface Props {
		fields: FormFieldDefinition[];
		rules?: FormRule[];
		values?: Record<string, any>;
		idPrefix?: string;
		diagnosisSuggestions?: AutocompleteDiagnosisSuggestion[];
		diagnosisLoading?: boolean;
		onDiagnosisInput?: (query: string) => void;
		onDiagnosisSelect?: (item: AutocompleteDiagnosisSuggestion) => void;
		onDiagnosisClear?: () => void;
		// AI Diagnosis props
		aiPatientId?: string;
		aiDepartment?: string | null;
		aiFormName?: string | null;
		aiPriorDiagnoses?: Array<Record<string, any>> | null;
		aiTopN?: number;
		aiAutoAnalyze?: boolean;
		onAISuggestionSelect?: (suggestion: AIDiagnosisSuggestion) => void;
	}

	let {
		fields,
		rules = [],
		values = $bindable({}),
		idPrefix = 'dynamic',
		diagnosisSuggestions = [],
		diagnosisLoading = false,
		onDiagnosisInput,
		onDiagnosisSelect,
		onDiagnosisClear,
		aiPatientId,
		aiDepartment,
		aiFormName,
		aiPriorDiagnoses,
		aiTopN = 5,
		aiAutoAnalyze = true,
		onAISuggestionSelect,
	}: Props = $props();

	// Lookup options cache for dynamic selects
	let lookupOptions: Record<string, { value: string; label: string }[]> = $state({});

	onMount(() => {
		const sources = new Set<string>();
		for (const f of fields) {
			const src = DYNAMIC_SOURCES[f.type];
			if (src) sources.add(src);
		}
		for (const src of sources) {
			formsApi.getLookupOptions(src).then((opts) => {
				lookupOptions[src] = opts;
				lookupOptions = { ...lookupOptions };
			}).catch(() => {});
		}
	});

	// Engine is recreated only when rules change
	const engine = $derived(createFormEngine(rules));

	// Snapshot all field values individually so $derived tracks per-property changes
	const formState = $derived.by(() => {
		const snapshot: Record<string, any> = {};
		for (const f of fields) {
			snapshot[f.key] = values[f.key];
		}
		return engine.evaluate(fields, snapshot);
	});

	function inputId(key: string) {
		return `${idPrefix}-${key}`;
	}

	function setFileValue(key: string, files: FileList | null, multiple = false) {
		if (!files || files.length === 0) {
			values[key] = multiple ? [] : null;
			return;
		}
		values[key] = multiple ? Array.from(files) : files[0];
	}

	function fileNames(value: any): string {
		if (!value) return '';
		if (Array.isArray(value)) return value.map((f) => f?.name ?? '').filter(Boolean).join(', ');
		return value.name ?? '';
	}

	function fieldOptions(field: FormFieldDefinition): string[] {
		return formState.options[field.key] ?? field.options ?? [];
	}

	const visibleFields = $derived(fields.filter((f) => formState.visibility[f.key] !== false));

	function normalizeFieldToken(value: string | null | undefined): string {
		return (value ?? '').trim().toLowerCase();
	}

	function findFieldKeyByHint(
		predicate: (field: FormFieldDefinition, normalizedKey: string, normalizedLabel: string) => boolean,
	): string | null {
		const match = fields.find((field) =>
			predicate(field, normalizeFieldToken(field.key), normalizeFieldToken(field.label))
		);
		return match?.key ?? null;
	}

	const aiDiagnosisFieldKey = $derived.by(() =>
		findFieldKeyByHint((_, normalizedKey, normalizedLabel) =>
			['diagnosis', 'primary_diagnosis', 'provisional_diagnosis', 'final_diagnosis'].includes(normalizedKey)
				|| normalizedLabel.includes('diagnosis')
		)
	);

	const aiIcdCodeFieldKey = $derived.by(() =>
		findFieldKeyByHint((_, normalizedKey, normalizedLabel) =>
			normalizedKey === 'icd_code'
				|| normalizedKey === 'diagnosis_code'
				|| (normalizedLabel.includes('icd') && normalizedLabel.includes('code'))
		)
	);

	function handleAISuggestionSelect(suggestion: AIDiagnosisSuggestion): void {
		if (aiDiagnosisFieldKey) {
			values[aiDiagnosisFieldKey] = suggestion.disease;
		}

		if (aiIcdCodeFieldKey && suggestion.icd_code) {
			values[aiIcdCodeFieldKey] = suggestion.icd_code;
		}

		if (onAISuggestionSelect) {
			onAISuggestionSelect(suggestion);
		}
	}
</script>

{#each visibleFields as field (field.key)}
	{@const isDisabled = formState.enabled[field.key] === false}
	<div style={isDisabled ? 'opacity: 0.45; pointer-events: none;' : ''}>

		{#if field.type === 'diagnosis'}
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<Autocomplete
				placeholder={field.placeholder ?? 'Search diagnosis...'}
				bind:value={values[field.key]}
				items={diagnosisSuggestions}
				loading={diagnosisLoading}
				onInput={onDiagnosisInput}
				onSelect={onDiagnosisSelect}
				onClear={onDiagnosisClear}
			/>
		{:else if DYNAMIC_SOURCES[field.type]}
			{@const source = DYNAMIC_SOURCES[field.type]}
			{@const opts = lookupOptions[source] ?? []}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<select
				id={inputId(field.key)}
				bind:value={values[field.key]}
				disabled={isDisabled || opts.length === 0}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
			>
				<option value="">{opts.length === 0 ? 'Loading...' : `Select ${field.label}`}</option>
				{#each opts as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
		{:else if field.type === 'select'}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<select
				id={inputId(field.key)}
				bind:value={values[field.key]}
				disabled={isDisabled}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
			>
				<option value="">Select {field.label}</option>
				{#each fieldOptions(field) as option}
					<option value={option}>{option}</option>
				{/each}
			</select>
		{:else if field.type === 'textarea'}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<textarea
				id={inputId(field.key)}
				bind:value={values[field.key]}
				rows={field.rows ?? 3}
				disabled={isDisabled}
				class="block w-full px-3 py-2 rounded-md text-sm resize-y"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder={field.placeholder ?? ''}
			></textarea>
		{:else if field.type === 'file'}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<input
				id={inputId(field.key)}
				type="file"
				accept={field.accept ?? undefined}
				multiple={field.multiple ?? false}
				disabled={isDisabled}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; background-color: rgba(255,255,255,0.9);"
				onchange={(event) => setFileValue(field.key, event.currentTarget.files, field.multiple)}
			/>
			{#if fileNames(values[field.key])}
				<p class="mt-1 text-[11px] text-gray-500">{fileNames(values[field.key])}</p>
			{/if}
		{:else}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<input
				id={inputId(field.key)}
				type={field.type}
				bind:value={values[field.key]}
				disabled={isDisabled}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder={field.placeholder ?? ''}
			/>
		{/if}

		{#if field.help_text}
			<p class="mt-1 text-[11px] text-gray-500">{field.help_text}</p>
		{/if}
	</div>
{/each}

<!-- AI Diagnosis Suggestions -->
{#if aiPatientId}
	<DiagnosisSuggestions
		patientId={aiPatientId}
		department={aiDepartment}
		formName={aiFormName}
		formValues={values}
		priorDiagnoses={aiPriorDiagnoses}
		topN={aiTopN}
		autoAnalyze={aiAutoAnalyze}
		onSuggestionSelect={handleAISuggestionSelect}
	/>
{/if}
