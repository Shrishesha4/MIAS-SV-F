<script lang="ts">
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import type { DiagnosisSuggestion } from '$lib/api/autocomplete';
	import type { FormFieldDefinition } from '$lib/types/forms';

	interface Props {
		fields: FormFieldDefinition[];
		values?: Record<string, any>;
		idPrefix?: string;
		diagnosisSuggestions?: DiagnosisSuggestion[];
		diagnosisLoading?: boolean;
		onDiagnosisInput?: (query: string) => void;
		onDiagnosisSelect?: (item: DiagnosisSuggestion) => void;
		onDiagnosisClear?: () => void;
	}

	let {
		fields,
		values = $bindable({}),
		idPrefix = 'dynamic',
		diagnosisSuggestions = [],
		diagnosisLoading = false,
		onDiagnosisInput,
		onDiagnosisSelect,
		onDiagnosisClear,
	}: Props = $props();

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
		if (!value) {
			return '';
		}
		if (Array.isArray(value)) {
			return value.map((file) => file?.name ?? '').filter(Boolean).join(', ');
		}
		return value.name ?? '';
	}
</script>

{#each fields as field (field.key)}
	<div>
		{#if field.type === 'diagnosis'}
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<Autocomplete
				placeholder={field.placeholder ?? 'Search diagnosis...'}
				bind:value={values[field.key]}
				items={diagnosisSuggestions}
				labelKey="text"
				sublabelKey="icd_description"
				badgeKey="icd_code"
				onInput={onDiagnosisInput}
				onSelect={onDiagnosisSelect}
				onClear={onDiagnosisClear}
				loading={diagnosisLoading}
				minChars={2}
			/>
		{:else if field.type === 'select'}
			<label for={inputId(field.key)} class="block text-sm font-medium text-gray-700 mb-1">
				{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
			</label>
			<select
				id={inputId(field.key)}
				bind:value={values[field.key]}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
			>
				<option value="">Select {field.label}</option>
				{#each field.options ?? [] as option}
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
