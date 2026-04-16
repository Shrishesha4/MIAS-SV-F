<script lang="ts">
	import type { FormFieldDefinition, UploadedFormFile } from '$lib/types/forms';
	import { isUploadedFormFile, stringifyFormValue } from '$lib/utils/forms';

	interface DisplayField extends FormFieldDefinition {
		key: string;
		label: string;
	}

	interface DisplayItem {
		field: DisplayField;
		text: string;
		files: UploadedFormFile[];
	}

	interface Props {
		fields?: FormFieldDefinition[] | null;
		values?: Record<string, any> | null;
		title?: string;
		emptyText?: string;
	}

	let {
		fields = null,
		values = null,
		title = 'Original Submitted Form',
		emptyText = 'No original form values were saved for this case record.',
	}: Props = $props();

	function humanizeKey(key: string): string {
		return key
			.replace(/[_-]+/g, ' ')
			.replace(/([a-z0-9])([A-Z])/g, '$1 $2')
			.replace(/\s+/g, ' ')
			.trim()
			.replace(/\b\w/g, (char) => char.toUpperCase());
	}

	function collectUploadedFiles(value: any): UploadedFormFile[] {
		if (!value) return [];
		if (Array.isArray(value)) return value.flatMap((item) => collectUploadedFiles(item));
		return isUploadedFormFile(value) ? [value] : [];
	}

	const displayItems = $derived.by(() => {
		const sourceValues = values ?? {};
		const orderedFields = fields ?? [];
		const usedKeys = new Set<string>();
		const items: DisplayItem[] = [];

		for (const field of orderedFields) {
			const value = sourceValues[field.key];
			const text = stringifyFormValue(value).trim();
			const files = collectUploadedFiles(value);
			if (!text && files.length === 0) continue;
			usedKeys.add(field.key);
			items.push({
				field,
				text,
				files,
			});
		}

		for (const [key, value] of Object.entries(sourceValues)) {
			if (usedKeys.has(key)) continue;
			const text = stringifyFormValue(value).trim();
			const files = collectUploadedFiles(value);
			if (!text && files.length === 0) continue;
			items.push({
				field: {
					key,
					label: humanizeKey(key),
					type: 'textarea',
				},
				text,
				files,
			});
		}

		return items;
	});
</script>

<div class="rounded-lg border border-slate-200/80 bg-slate-50 p-3">
	<div class="mb-2 flex items-center justify-between gap-2">
		<p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-600">{title}</p>
		<span class="text-[10px] font-medium text-slate-400">{displayItems.length} field{displayItems.length === 1 ? '' : 's'}</span>
	</div>

	{#if displayItems.length === 0}
		<p class="text-xs text-slate-500">{emptyText}</p>
	{:else}
		<div class="space-y-3">
			{#each displayItems as item (item.field.key)}
				<div class="rounded-md bg-white px-3 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
					<div class="mb-1 block text-sm font-medium text-gray-700">
						{item.field.label}
						{#if item.field.required}<span class="text-red-500">*</span>{/if}
					</div>
					{#if item.files.length > 0}
						<div class="flex flex-wrap gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2">
							{#each item.files as file, index (`${item.field.key}-${file.url}-${index}`)}
								<a
									href={file.url}
									target="_blank"
									rel="noreferrer"
									class="inline-flex max-w-full items-center rounded-full bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700 hover:bg-blue-100"
								>
									<span class="truncate">{file.name}</span>
								</a>
							{/each}
						</div>
					{:else if item.field.type === 'textarea' || item.field.type === 'diagnosis'}
						<textarea
							rows={item.field.rows ?? 3}
							disabled
							class="block w-full resize-y rounded-md px-3 py-2 text-sm text-gray-700"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.95);"
							value={item.text}
						></textarea>
					{:else if item.field.type === 'select'}
						<select
							disabled
							class="block w-full rounded-md px-3 py-2 text-sm text-gray-700"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.95);"
						>
							<option value={item.text}>{item.text || `Select ${item.field.label}`}</option>
						</select>
					{:else}
						<input
							type={item.field.type === 'number' ? 'number' : item.field.type === 'date' ? 'date' : item.field.type === 'email' ? 'email' : item.field.type === 'password' ? 'text' : item.field.type === 'tel' ? 'tel' : 'text'}
							disabled
							class="block w-full rounded-md px-3 py-2 text-sm text-gray-700"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.95);"
							value={item.text}
						/>
					{/if}
					{#if item.field.help_text}
						<p class="mt-1 text-[11px] text-gray-500">{item.field.help_text}</p>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
