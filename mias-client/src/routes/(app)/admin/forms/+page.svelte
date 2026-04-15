<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { formsApi, type FormDefinitionPayload } from '$lib/api/forms';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import type { FormCategory, FormDefinition, FormFieldDefinition, FormRule, FormSection, FormFieldType, FieldCondition } from '$lib/types/forms';
	import { toastStore } from '$lib/stores/toast';
	import { ArrowDown, ArrowUp, FileText, Loader2, Pencil, Plus, Power, Trash2 } from 'lucide-svelte';

	const auth = get(authStore);
	const defaultSections: FormSection[] = ['CLINICAL', 'LABORATORY', 'ADMINISTRATIVE'];
	const fieldTypes: FormFieldType[] = ['text', 'textarea', 'number', 'select', 'date', 'file', 'email', 'password', 'tel', 'diagnosis'];
	const legacyTypeToSection: Record<string, FormSection> = {
		CASE_RECORD: 'CLINICAL',
		ADMISSION: 'CLINICAL',
		ADMISSION_REQUEST: 'CLINICAL',
		ADMISSION_INTAKE: 'CLINICAL',
		ADMISSION_DISCHARGE: 'CLINICAL',
		ADMISSION_TRANSFER: 'CLINICAL',
		PRESCRIPTION: 'CLINICAL',
		PRESCRIPTION_CREATE: 'CLINICAL',
		PRESCRIPTION_EDIT: 'CLINICAL',
		PRESCRIPTION_REQUEST: 'CLINICAL',
		VITAL_ENTRY: 'CLINICAL',
		LABORATORY: 'LABORATORY',
		LAB: 'LABORATORY',
		LABS: 'LABORATORY',
		PROFILE: 'ADMINISTRATIVE',
		PROFILE_EDIT: 'ADMINISTRATIVE',
		CUSTOM: 'ADMINISTRATIVE',
		ADMINISTRATIVE: 'ADMINISTRATIVE'
	};

	let loadingForms = $state(true);
	let formDefinitions: FormDefinition[] = $state([]);
	let formCategories: FormCategory[] = $state([]);
	let activeSection = $state<FormSection>('CLINICAL');

	let showFormEditor = $state(false);
	let editingFormId: string | null = $state(null);
	let formEditorSection = $state<FormSection>('CLINICAL');
	let formEditorType = $state('');
	let formEditorName = $state('');
	let formEditorSortOrder = $state(0);
	let formEditorIsActive = $state(true);
	let formEditorFields: FormFieldDefinition[] = $state([]);
	let formEditorRules: FormRule[] = $state([]);
	let selectedFieldIndex = $state(0);
	let previewValues = $state<Record<string, any>>({});
	let isEditingFormName = $state(false);
	let formNameInput = $state<HTMLInputElement | null>(null);
	let savingForm = $state(false);
	let formSaveError = $state('');
	let showCategoryEditor = $state(false);
	let categoryName = $state('');
	let savingCategory = $state(false);
	let categorySaveError = $state('');
	let categoryMenu = $state<{ x: number; y: number; category: FormCategory } | null>(null);

	const selectedField = $derived(formEditorFields[selectedFieldIndex] ?? null);
	const previewSchema = $derived.by(() => {
		const serializedFields = serializeFields(formEditorFields);
		const duplicateKeys = new Set<string>();
		const seenKeys = new Set<string>();
		const previewKeyCounts = new Map<string, number>();
		const firstPreviewKeyBySerializedKey = new Map<string, string>();

		const previewKeys = serializedFields.map((field, index) => {
			const baseKey = field.key || `field_${index + 1}`;
			if (seenKeys.has(baseKey)) {
				duplicateKeys.add(baseKey);
			} else {
				seenKeys.add(baseKey);
			}

			const currentCount = previewKeyCounts.get(baseKey) ?? 0;
			const previewKey = currentCount === 0 ? baseKey : `${baseKey}_${currentCount + 1}`;
			previewKeyCounts.set(baseKey, currentCount + 1);
			if (!firstPreviewKeyBySerializedKey.has(baseKey)) {
				firstPreviewKeyBySerializedKey.set(baseKey, previewKey);
			}
			return previewKey;
		});

		return {
			duplicates: [...duplicateKeys],
			fields: serializedFields.map((field, index) => ({
				...field,
				key: previewKeys[index],
				label: field.label || `Untitled field ${index + 1}`,
				condition: field.condition
					? {
						...field.condition,
						field: firstPreviewKeyBySerializedKey.get(field.condition.field) ?? field.condition.field,
					}
					: undefined,
			})),
		};
	});

	const sectionTabs = $derived.by(() => {
		const activeCategories = [...formCategories]
			.filter((category) => category.is_active)
			.sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
		return activeCategories.length > 0 ? activeCategories.map((category) => category.name) : defaultSections;
	});

	const filteredForms = $derived.by(() => {
		return formDefinitions.filter((form) => resolveFormSection(form) === activeSection);
	});

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		loadFormStudio();
	});

	function openCategoryContextMenu(event: MouseEvent, section: FormSection) {
		event.preventDefault();
		const category = formCategories.find((item) => item.name === section);
		if (!category || category.is_system) {
			categoryMenu = null;
			return;
		}
		categoryMenu = { x: event.clientX, y: event.clientY, category };
	}

	async function deleteCategoryFromMenu() {
		if (!categoryMenu) return;
		const target = categoryMenu.category;
		categoryMenu = null;
		try {
			await formsApi.deleteFormCategory(target.id);
			formCategories = sortFormCategories(formCategories.filter((item) => item.id !== target.id));
			syncActiveSection(formCategories);
			await loadFormStudio();
			toastStore.addToast('Form category deleted', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete form category', 'error');
		}
	}

	function resolveFormSection(form: Pick<FormDefinition, 'section' | 'form_type'>): FormSection {
		const explicitSection = form.section?.toString().toUpperCase();
		if (explicitSection) {
			return explicitSection;
		}
		return legacyTypeToSection[form.form_type?.toString().toUpperCase() || ''] || 'ADMINISTRATIVE';
	}

	function sortFormCategories(categories: FormCategory[]): FormCategory[] {
		return [...categories].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
	}

	function syncActiveSection(categories: FormCategory[]) {
		const activeCategories = sortFormCategories(categories).filter((category) => category.is_active);
		if (activeCategories.length === 0) {
			activeSection = defaultSections[0];
			return;
		}
		if (!activeCategories.some((category) => category.name === activeSection)) {
			activeSection = activeCategories[0].name;
		}
	}

	function slugify(value: string) {
		return value
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, '_')
			.replace(/^_+|_+$/g, '');
	}

	function normalizeFieldType(type: string | undefined): FormFieldType {
		const normalized = (type || '').toLowerCase();
		return fieldTypes.includes(normalized as FormFieldType) ? (normalized as FormFieldType) : 'text';
	}

	function createEmptyField(): FormFieldDefinition {
		return {
			key: '',
			label: '',
			type: 'text',
			required: false,
			placeholder: ''
		};
	}

	async function loadFormStudio() {
		loadingForms = true;
		try {
			const [forms, categories] = await Promise.all([
				formsApi.getForms({ include_inactive: true }),
				formsApi.getFormCategories(),
			]);
			formDefinitions = forms;
			formCategories = sortFormCategories(categories);
			syncActiveSection(categories);
		} catch {
			toastStore.addToast('Failed to load forms', 'error');
		} finally {
			loadingForms = false;
		}
	}

	function resetFormEditor() {
		showFormEditor = false;
		editingFormId = null;
		formEditorSection = activeSection;
		formEditorType = '';
		formEditorName = '';
		formEditorSortOrder = 0;
		formEditorIsActive = true;
		formEditorFields = [];
		formEditorRules = [];
		selectedFieldIndex = 0;
		previewValues = {};
		isEditingFormName = false;
		formSaveError = '';
	}

	function resetCategoryEditor() {
		showCategoryEditor = false;
		categoryName = '';
		categorySaveError = '';
	}

	function openCreateFormEditor(section: FormSection = activeSection) {
		resetFormEditor();
		formEditorSection = section;
		activeSection = section;
		showFormEditor = true;
		addFormField();
	}

	function openCategoryEditor() {
		resetCategoryEditor();
		showCategoryEditor = true;
	}

	function openEditFormEditor(form: FormDefinition) {
		resetFormEditor();
		editingFormId = form.id;
		formEditorSection = resolveFormSection(form);
		formEditorType = form.form_type;
		formEditorName = form.name;
		formEditorSortOrder = form.sort_order || 0;
		formEditorIsActive = form.is_active;
		formEditorFields = (form.fields.length > 0 ? form.fields : [createEmptyField()]).map((field) => ({
			...field,
			type: normalizeFieldType(field.type)
		}));
		formEditorRules = form.rules ? [...form.rules] : [];
		selectedFieldIndex = 0;
		previewValues = {};
		activeSection = formEditorSection;
		showFormEditor = true;
	}

	function addFormField() {
		const nextFields = [...formEditorFields, createEmptyField()];
		formEditorFields = nextFields;
		selectedFieldIndex = nextFields.length - 1;
	}

	function removeFormField(index: number) {
		const nextFields = formEditorFields.filter((_, fieldIndex) => fieldIndex !== index);
		if (nextFields.length === 0) {
			formEditorFields = [createEmptyField()];
			selectedFieldIndex = 0;
			return;
		}

		formEditorFields = nextFields;
		if (selectedFieldIndex > index) {
			selectedFieldIndex -= 1;
		} else if (selectedFieldIndex === index) {
			selectedFieldIndex = Math.max(0, index - 1);
		}
	}

	function moveFormField(fromIndex: number, toIndex: number) {
		if (
			fromIndex === toIndex ||
			fromIndex < 0 ||
			toIndex < 0 ||
			fromIndex >= formEditorFields.length ||
			toIndex >= formEditorFields.length
		) {
			return;
		}

		const nextFields = [...formEditorFields];
		const [movedField] = nextFields.splice(fromIndex, 1);
		nextFields.splice(toIndex, 0, movedField);
		formEditorFields = nextFields;

		if (selectedFieldIndex === fromIndex) {
			selectedFieldIndex = toIndex;
			return;
		}

		if (fromIndex < selectedFieldIndex && toIndex >= selectedFieldIndex) {
			selectedFieldIndex -= 1;
			return;
		}

		if (fromIndex > selectedFieldIndex && toIndex <= selectedFieldIndex) {
			selectedFieldIndex += 1;
		}
	}

	function setFormFieldOrder(index: number, nextOrder: number) {
		const normalizedOrder = Math.min(Math.max(nextOrder, 1), formEditorFields.length) - 1;
		moveFormField(index, normalizedOrder);
	}

	function canMoveFieldUp(index: number) {
		return index > 0;
	}

	function canMoveFieldDown(index: number) {
		return index < formEditorFields.length - 1;
	}

	function patchField(index: number, nextField: FormFieldDefinition) {
		formEditorFields = formEditorFields.map((field, fieldIndex) => (fieldIndex === index ? nextField : field));
	}

	function updateFieldLabel(index: number, label: string) {
		const field = formEditorFields[index];
		const previousAutoKey = slugify(field.label || '');
		const nextField = { ...field, label };
		if (!field.key || field.key === previousAutoKey) {
			nextField.key = slugify(label);
		}
		patchField(index, nextField);
	}

	function updateFieldType(index: number, type: string) {
		const field = formEditorFields[index];
		const nextField: FormFieldDefinition = { ...field, type: normalizeFieldType(type) };
		if (nextField.type !== 'select') {
			nextField.options = [];
		}
		if (nextField.type !== 'textarea') {
			nextField.rows = undefined;
		}
		if (nextField.type !== 'file') {
			nextField.accept = undefined;
			nextField.multiple = false;
		}
		patchField(index, nextField);
	}

	function updateFieldKey(index: number, key: string) {
		patchField(index, { ...formEditorFields[index], key: slugify(key) });
	}

	function updateFieldProperty<K extends keyof FormFieldDefinition>(index: number, property: K, value: FormFieldDefinition[K]) {
		patchField(index, { ...formEditorFields[index], [property]: value } as FormFieldDefinition);
	}

	function getEditorFieldId(field: FormFieldDefinition, index: number): string {
		return `${getEffectiveKey(field, index)}__${index}`;
	}

	function updateFieldRequired(index: number, required: boolean) {
		patchField(index, { ...formEditorFields[index], required });
	}

	function updateFormFieldOptions(index: number, value: string) {
		const options = value.split(',').map((item) => item.trim()).filter(Boolean);
		patchField(index, { ...formEditorFields[index], options });
	}

	function updateFieldCondition(index: number, condition: FormFieldDefinition['condition']) {
		patchField(index, { ...formEditorFields[index], condition });
	}

	function getEffectiveKey(field: FormFieldDefinition, idx: number): string {
		return field.key?.trim() || slugify(field.label) || `field_${idx + 1}`;
	}

	function getAvailableConditionFields(currentIndex: number) {
		return formEditorFields.slice(0, currentIndex).map((f, idx) => ({
			key: f.key || getEffectiveKey(f, idx),
			label: f.label || f.key || `Field ${idx + 1}`,
			type: f.type,
			options: f.type === 'select' ? (f.options ?? []) : []
		}));
	}

	function updateFieldConditionField(index: number, fieldKey: string) {
		const field = formEditorFields[index];
		updateFieldCondition(index, { field: fieldKey, operator: field.condition?.operator || 'not_empty' });
	}

	function updateFieldConditionOperator(index: number, operator: FieldCondition['operator']) {
		const field = formEditorFields[index];
		const next: FieldCondition = { field: field.condition?.field || '', operator };
		if (operator !== 'empty' && operator !== 'not_empty') next.value = field.condition?.value ?? '';
		updateFieldCondition(index, next);
	}

	function updateFieldConditionValue(index: number, value: string) {
		const field = formEditorFields[index];
		updateFieldCondition(index, { ...field.condition, field: field.condition?.field || '', operator: field.condition?.operator || 'not_empty', value });
	}

	function clearFieldCondition(index: number) {
		const nextField = { ...formEditorFields[index] };
		delete nextField.condition;
		patchField(index, nextField);
	}

	function serializeFields(fields: FormFieldDefinition[] = formEditorFields) {
		const finalKeys = fields.map((field, index) => field.key?.trim() || slugify(field.label) || `field_${index + 1}`);

		const keyMap = new Map<string, string>();
		fields.forEach((field, index) => {
			const finalKey = finalKeys[index];
			const rawKey = field.key?.trim();
			const autoKey = slugify(field.label || '');
			if (rawKey) keyMap.set(rawKey, finalKey);
			if (autoKey) keyMap.set(autoKey, finalKey);
			keyMap.set(`field_${index + 1}`, finalKey);
		});

		return fields.map((field, index) => {
			const condition = field.condition
				? {
					...field.condition,
					field: keyMap.get(field.condition.field) ?? field.condition.field,
				  }
				: undefined;

			return {
				...field,
				type: normalizeFieldType(field.type),
				key: finalKeys[index],
				label: field.label.trim(),
				options: field.type === 'select' ? field.options ?? [] : field.options,
				placeholder: field.placeholder || undefined,
				help_text: field.help_text || undefined,
				accept: field.accept || undefined,
				rows: field.rows || undefined,
				multiple: field.multiple || false,
				required: field.required || false,
				condition,
			};
		});
	}

	async function saveFormDefinition() {
		if (!formEditorName.trim()) {
			formSaveError = 'Form name is required';
			return;
		}

		const nextFields = serializeFields();
		if (nextFields.length === 0) {
			formSaveError = 'At least one field is required';
			return;
		}

		const invalidField = nextFields.find((field) => !field.label || !field.key);
		if (invalidField) {
			formSaveError = 'Every field needs a label';
			return;
		}

		const seenKeys = new Set<string>();
		const duplicateKeys = new Set<string>();
		for (const field of nextFields) {
			if (seenKeys.has(field.key)) {
				duplicateKeys.add(field.key);
			} else {
				seenKeys.add(field.key);
			}
		}
		if (duplicateKeys.size > 0) {
			formSaveError = `Field keys must be unique: ${[...duplicateKeys].join(', ')}`;
			return;
		}

		const payload: FormDefinitionPayload = {
			name: formEditorName.trim(),
			section: formEditorSection,
			fields: nextFields,
			rules: formEditorRules.length > 0 ? formEditorRules : undefined,
			sort_order: formEditorSortOrder,
			is_active: formEditorIsActive,
		};

		if (formEditorType) {
			payload.form_type = formEditorType;
		}

		savingForm = true;
		formSaveError = '';
		try {
			if (editingFormId) {
				await formsApi.updateForm(editingFormId, payload);
				toastStore.addToast('Configuration updated', 'success');
			} else {
				await formsApi.createForm(payload);
				toastStore.addToast('Configuration created', 'success');
			}
			resetFormEditor();
			await loadFormStudio();
		} catch (error: any) {
			formSaveError = error?.response?.data?.detail || 'Failed to save configuration';
		} finally {
			savingForm = false;
		}
	}

	async function saveFormCategory() {
		if (!categoryName.trim()) {
			categorySaveError = 'Category name is required';
			return;
		}

		savingCategory = true;
		categorySaveError = '';
		try {
			const created = await formsApi.createFormCategory({
				name: categoryName.trim(),
				sort_order: formCategories.length,
				is_active: true,
			});
			const categories = sortFormCategories([...formCategories, created]);
			formCategories = categories;
			activeSection = created.name;
			resetCategoryEditor();
			toastStore.addToast('Form category created', 'success');
		} catch (error: any) {
			categorySaveError = error?.response?.data?.detail || 'Failed to create form category';
		} finally {
			savingCategory = false;
		}
	}

	async function toggleFormActive(form: FormDefinition) {
		try {
			await formsApi.updateForm(form.id, {
				name: form.name,
				description: form.description || undefined,
				form_type: form.form_type,
				section: resolveFormSection(form),
				department: form.department || undefined,
				procedure_name: form.procedure_name || undefined,
				fields: form.fields,
				sort_order: form.sort_order,
				is_active: !form.is_active
			});
			toastStore.addToast(form.is_active ? 'Configuration deactivated' : 'Configuration activated', 'success');
			await loadFormStudio();
		} catch {
			toastStore.addToast('Failed to update configuration', 'error');
		}
	}

	async function startEditingFormName() {
		isEditingFormName = true;
		await tick();
		formNameInput?.focus();
		formNameInput?.select();
	}

	function stopEditingFormName() {
		formEditorName = formEditorName.trim();
		isEditingFormName = false;
	}
</script>

{#snippet formCategoryHeader()}
	<div class="flex items-center gap-3">
		<h3 class="text-sm font-bold text-slate-900">New Form Category</h3>
		<span class="rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
			TAB
		</span>
	</div>
{/snippet}

{#snippet formEditorHeader()}
	<div class="flex w-full flex-col gap-3 md:flex-row md:items-center md:justify-between">
		<div class="min-w-0 flex-1">
			<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-700">Form Studio</p>
			{#if isEditingFormName}
				<input
					bind:this={formNameInput}
					bind:value={formEditorName}
					onblur={stopEditingFormName}
					onkeydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							stopEditingFormName();
						}
						if (event.key === 'Escape') {
							event.preventDefault();
							isEditingFormName = false;
						}
					}}
					class="mt-1 w-full rounded-[14px] border border-slate-300 px-3 py-2 text-base font-bold text-slate-900 outline-none md:max-w-[360px]"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
					placeholder="Untitled form"
				/>
			{:else}
				<button
					type="button"
					onclick={startEditingFormName}
					class="mt-1 inline-flex min-w-0 max-w-full flex-col items-start rounded-[14px] px-1 py-1 text-left cursor-pointer"
				>
					<span class="truncate text-base font-bold text-slate-900 md:text-lg">{formEditorName || 'Untitled Form'}</span>
					<span class="text-[11px] text-slate-500">Click to rename</span>
				</button>
			{/if}
		</div>

		<div class="flex flex-wrap items-center gap-2 md:justify-end">
			<div class="rounded-[14px] border border-slate-200 px-2.5 py-2" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
				<p class="mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-700">Type</p>
				<input
					type="text"
					placeholder="CLINICAL"
					class="w-28 bg-transparent text-xs font-bold uppercase text-slate-800 outline-none"
					bind:value={formEditorType}
				/>
			</div>

			<div class="rounded-[14px] border border-slate-200 px-2.5 py-2" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
				<p class="mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-700">Section</p>
				<select
					class="w-28 cursor-pointer bg-transparent text-xs font-bold text-slate-800 outline-none"
					bind:value={formEditorSection}
				>
					{#each sectionTabs as section}
						<option value={section}>{section}</option>
					{/each}
				</select>
			</div>

			<div class="rounded-[14px] border border-slate-200 px-2.5 py-2" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
				<p class="mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-700">Sort</p>
				<input
					type="number"
					min="0"
					class="w-16 bg-transparent text-xs font-bold text-slate-800 outline-none"
					value={formEditorSortOrder}
					oninput={(event) => {
						const value = Number.parseInt((event.currentTarget as HTMLInputElement).value, 10);
						formEditorSortOrder = Number.isFinite(value) && value >= 0 ? value : 0;
					}}
				/>
			</div>

			<button
				type="button"
				onclick={() => (formEditorIsActive = !formEditorIsActive)}
				class="rounded-[14px] border px-4 py-3 text-xs font-bold cursor-pointer"
				style={`border-color: ${formEditorIsActive ? 'rgba(37,99,235,0.22)' : 'rgba(148,163,184,0.28)'}; background: ${formEditorIsActive ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : 'linear-gradient(to bottom, #ffffff, #f8fafc)'}; color: ${formEditorIsActive ? '#1d4ed8' : '#64748b'};`}
			>
				{formEditorIsActive ? 'Active' : 'Inactive'}
			</button>
		</div>
	</div>
{/snippet}

<div class="space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Form Studio</p>
			<h2 class="mt-1 text-lg font-bold text-slate-900 md:text-xl">Forms</h2>
		</div>
		<button
			onclick={() => openCreateFormEditor(activeSection)}
			class="inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 6px 14px rgba(37,99,235,0.2), inset 0 1px 0 rgba(255,255,255,0.25);"
		>
			<Plus class="h-3.5 w-3.5" />
			New Form
		</button>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<div class="form-tab-scroll form-tab-shell">
			<div class="form-tab-row" role="tablist" aria-label="Form category navigation">
				{#each sectionTabs as section}
					<button
						type="button"
						class="form-tab-btn"
						class:is-active={activeSection === section}
						role="tab"
						aria-selected={activeSection === section}
						onclick={() => {
							activeSection = section;
							categoryMenu = null;
						}}
						oncontextmenu={(event) => openCategoryContextMenu(event, section)}
					>
						{section}
					</button>
				{/each}
			</div>
		</div>
		<button
			type="button"
			onclick={openCategoryEditor}
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 8px 18px rgba(37,99,235,0.22), inset 0 1px 0 rgba(255,255,255,0.24);"
			aria-label="Add form category"
			title="Add form category"
		>
			<Plus class="h-4 w-4" />
		</button>
	</div>

	{#if categoryMenu}
		<button
			type="button"
			class="fixed inset-0 z-40 cursor-default"
			onclick={() => (categoryMenu = null)}
			aria-label="Close category context menu"
		></button>
		<div
			class="fixed z-50 rounded-xl border border-slate-200 bg-white p-2 shadow-xl"
			style={`left: ${categoryMenu.x}px; top: ${categoryMenu.y}px;`}
		>
			<button
				type="button"
				onclick={deleteCategoryFromMenu}
				class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 cursor-pointer"
			>
				<Trash2 class="h-3.5 w-3.5" />
				Delete Tab
			</button>
		</div>
	{/if}

	{#if loadingForms}
		<div class="flex items-center justify-center py-20">
			<Loader2 class="h-8 w-8 animate-spin text-blue-500" />
		</div>
	{:else if filteredForms.length === 0}
		<div class="rounded-[18px] border border-slate-200 px-5 py-10 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<FileText class="mx-auto mb-3 h-7 w-7 text-slate-300" />
			<p class="text-sm font-semibold text-slate-700">No {activeSection.toLowerCase()} forms configured yet</p>
			<p class="mt-1.5 text-xs text-slate-400">Create one from the button above and it will appear here.</p>
		</div>
	{:else}
		<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
			{#each filteredForms as form}
				<div class="rounded-[18px] border border-slate-200 p-3.5" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 20px rgba(15,23,42,0.05); opacity: {form.is_active ? 1 : 0.72};">
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-[9px] font-bold uppercase tracking-[0.14em] text-blue-600">{resolveFormSection(form)}</p>
							<h3 class="mt-1 text-sm font-bold text-slate-900">{form.name}</h3>
						</div>
						<span class="rounded-full px-2.5 py-1 text-[10px] font-bold" style="background: {form.is_active ? 'rgba(37,99,235,0.1)' : 'rgba(148,163,184,0.12)'}; color: {form.is_active ? '#2563eb' : '#64748b'};">
							{form.is_active ? 'ACTIVE' : 'INACTIVE'}
						</span>
					</div>

					<div class="mt-2.5 space-y-1 text-xs text-slate-500">
						<p>{form.fields.length} fields configured</p>
						<p>Type: {form.form_type}</p>
					</div>

					<div class="mt-3 flex items-center gap-2">
						<button
							onclick={() => openEditFormEditor(form)}
							class="flex-1 inline-flex items-center justify-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold cursor-pointer"
							style="background: linear-gradient(to bottom, #ffffff, #eff6ff); color: #2563eb; border: 1px solid rgba(59,130,246,0.18);"
						>
							<Pencil class="h-3.5 w-3.5" />
							Edit
						</button>
						<button
							onclick={() => toggleFormActive(form)}
							class="rounded-full px-3 py-1.5 text-xs font-semibold cursor-pointer"
							style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); color: #475569; border: 1px solid rgba(148,163,184,0.24);"
						>
							<Power class="inline-block h-3.5 w-3.5" />
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

{#if showCategoryEditor}
	<AquaModal
		header={formCategoryHeader}
		onclose={resetCategoryEditor}
		panelClass="sm:max-w-[420px]"
		contentClass="p-0"
	>
		<div class="space-y-4 px-4 py-4" style="background: linear-gradient(to bottom, #ffffff, #f4f7fb);">
			{#if categorySaveError}
				<div class="rounded-[12px] border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{categorySaveError}</div>
			{/if}

			<div>
				<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Category Name</p>
				<input
					type="text"
					placeholder="e.g. RADIOLOGY"
					class="w-full rounded-[14px] border border-slate-300 px-3.5 py-2.5 text-sm font-semibold text-slate-800 outline-none"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
					bind:value={categoryName}
				/>
				<p class="mt-2 text-xs text-slate-500">The new tab becomes available immediately in the forms studio and in form creation.</p>
			</div>

			<button
				type="button"
				onclick={saveFormCategory}
				disabled={savingCategory}
				class="w-full rounded-[999px] px-8 py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60"
				style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 10px 20px rgba(37,99,235,0.2), inset 0 2px 0 rgba(255,255,255,0.24);"
			>
				{#if savingCategory}
					<Loader2 class="mr-2 inline-block h-4 w-4 animate-spin" />
					Creating...
				{:else}
					Create Category
				{/if}
			</button>
		</div>
	</AquaModal>
{/if}

<style>
	.form-tab-scroll {
		display: block;
		max-width: 100%;
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: none;
		-ms-overflow-style: none;
	}

	.form-tab-scroll::-webkit-scrollbar {
		display: none;
	}

	.form-tab-shell :global(.tab-bar--jiggle) {
		border-color: rgba(226, 232, 240, 0.9);
		background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
	}

	.form-tab-row {
		display: flex;
		gap: 0.35rem;
		width: max-content;
		padding: 0.28rem;
		border: 1px solid rgba(226, 232, 240, 0.9);
		border-radius: 1.4rem;
		background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
	}

	.form-tab-btn {
		flex: 0 0 auto;
		min-height: 2.7rem;
		padding: 0.62rem 0.88rem;
		border: 1px solid transparent;
		border-radius: 1.1rem;
		background: transparent;
		font-size: 0.84rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		color: #667085;
		cursor: pointer;
		white-space: nowrap;
	}

	.form-tab-btn:hover {
		color: #475467;
		transform: translateY(-1px);
	}

	.form-tab-btn.is-active {
		color: white;
		border-color: rgba(29, 78, 216, 0.2);
		background: linear-gradient(135deg, #3b82f6 0%, #2563eb 60%, #1d4ed8 100%);
		box-shadow:
			0 10px 22px rgba(37, 99, 235, 0.22),
			inset 0 1px 0 rgba(255, 255, 255, 0.32),
			inset 0 -1px 0 rgba(15, 23, 42, 0.12);
	}

	@media (min-width: 768px) {
		.form-tab-scroll {
			max-width: 620px;
		}
	}
</style>

{#if showFormEditor}
	<AquaModal
		header={formEditorHeader}
		onclose={resetFormEditor}
		panelClass="sm:max-w-[1320px]"
		contentClass="p-0"
	>
		<div class="px-3.5 py-3.5 md:px-4 md:py-4" style="background: linear-gradient(to bottom, #ffffff, #f4f7fb); max-height: calc(100vh - 8rem);">
			{#if formSaveError}
				<div class="mb-4 rounded-[12px] border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{formSaveError}</div>
			{/if}

			<div class="space-y-4 overflow-y-auto pr-1">
				<div class="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_minmax(0,1.1fr)]">
					<div class="rounded-[22px] border border-slate-200 p-3.5" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); box-shadow: 0 12px 24px rgba(15,23,42,0.05);">
						<div class="mb-3 flex items-center justify-between gap-3">
							<div>
								<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Fields Overview</p>
								<p class="mt-1 text-xs text-slate-500">Pick a field to configure it in detail.</p>
							</div>
							<span class="rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
								{formEditorFields.length} FIELD{formEditorFields.length === 1 ? '' : 'S'}
							</span>
						</div>

						<div class="space-y-2">
							{#each formEditorFields as field, index (getEditorFieldId(field, index))}
								<div
									class="rounded-[18px] border p-2.5"
									style={`border-color: ${selectedFieldIndex === index ? 'rgba(37,99,235,0.3)' : 'rgba(226,232,240,0.95)'}; background: ${selectedFieldIndex === index ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : 'linear-gradient(to bottom, #ffffff, #f8fafc)'}; box-shadow: ${selectedFieldIndex === index ? '0 10px 20px rgba(37,99,235,0.12)' : '0 8px 16px rgba(15,23,42,0.04)'};`}
								>
									<div class="flex items-start gap-2">
										<button
											type="button"
											class="min-w-0 flex-1 text-left cursor-pointer"
											onclick={() => (selectedFieldIndex = index)}
										>
											<div class="flex items-center gap-2">
												<span class="rounded-full px-2 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(15,23,42,0.06); color: #475569;">
													#{index + 1}
												</span>
												<span class="rounded-full px-2 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
													{field.type.toUpperCase()}
												</span>
												{#if field.required}
													<span class="rounded-full px-2 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(220,38,38,0.1); color: #dc2626;">
														REQUIRED
													</span>
												{/if}
											</div>
											<p class="mt-2 truncate text-sm font-bold text-slate-900">{field.label || `Untitled field ${index + 1}`}</p>
											<p class="mt-1 truncate text-[11px] text-slate-500">{field.key || slugify(field.label) || `field_${index + 1}`}</p>
											{#if field.condition}
												<p class="mt-1.5 text-[11px] text-slate-500">Conditional on {field.condition.field}</p>
											{/if}
										</button>
										<div class="flex shrink-0 flex-col gap-1">
											<button
												type="button"
												class="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 cursor-pointer hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-35"
												onclick={() => moveFormField(index, index - 1)}
												disabled={!canMoveFieldUp(index)}
												aria-label="Move field up"
											>
												<ArrowUp class="h-3.5 w-3.5" />
											</button>
											<button
												type="button"
												class="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 cursor-pointer hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-35"
												onclick={() => moveFormField(index, index + 1)}
												disabled={!canMoveFieldDown(index)}
												aria-label="Move field down"
											>
												<ArrowDown class="h-3.5 w-3.5" />
											</button>
											<button
												type="button"
												class="flex h-8 w-8 items-center justify-center rounded-full text-red-500 cursor-pointer hover:bg-red-50"
												onclick={() => removeFormField(index)}
												aria-label="Delete field"
											>
												<Trash2 class="h-3.5 w-3.5" />
											</button>
										</div>
									</div>
								</div>
							{/each}

							<button
								type="button"
								onclick={addFormField}
								class="w-full rounded-[18px] border border-dashed border-slate-300 px-3 py-3 text-xs font-semibold text-slate-500 cursor-pointer hover:border-slate-400 hover:text-slate-700"
								style="background: rgba(255,255,255,0.55);"
							>
								<Plus class="mr-1.5 inline-block h-3.5 w-3.5" />
								Add Field
							</button>
						</div>
					</div>

					<div class="rounded-[22px] border border-slate-200 p-3.5" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); box-shadow: 0 12px 24px rgba(15,23,42,0.05);">
						{#if selectedField}
							{@const availableFields = getAvailableConditionFields(selectedFieldIndex)}
							<div class="mb-3 flex items-start justify-between gap-3">
								<div>
									<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Selected Field</p>
									<h4 class="mt-1 text-sm font-bold text-slate-900">{selectedField.label || `Field ${selectedFieldIndex + 1}`}</h4>
									<p class="mt-1 text-xs text-slate-500">Adjust the schema for the currently highlighted field.</p>
								</div>
								<button
									type="button"
									onclick={() => removeFormField(selectedFieldIndex)}
									class="rounded-full border border-red-200 px-3 py-1.5 text-[11px] font-bold text-red-600 cursor-pointer"
									style="background: linear-gradient(to bottom, #ffffff, #fff1f2);"
								>
									Remove
								</button>
							</div>

							<div class="space-y-3">
								<div class="rounded-[18px] border border-slate-200 p-3" style="background: linear-gradient(to bottom, rgba(248,250,252,0.95), rgba(241,245,249,0.95));">
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Field Order</p>
											<p class="mt-1 text-xs text-slate-500">Rearrange this field from the detail pane.</p>
										</div>
										<span class="rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
											#{selectedFieldIndex + 1} OF {formEditorFields.length}
										</span>
									</div>

									<div class="mt-3 grid gap-3 md:grid-cols-[120px_minmax(0,1fr)] md:items-end">
										<div>
											<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Position</p>
											<input
												type="number"
												min="1"
												max={formEditorFields.length}
												class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none"
												style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
												value={selectedFieldIndex + 1}
												onchange={(event) => {
													const value = Number.parseInt((event.currentTarget as HTMLInputElement).value, 10);
													if (Number.isFinite(value)) {
														setFormFieldOrder(selectedFieldIndex, value);
													}
												}}
											/>
										</div>

										<div class="grid gap-2 md:grid-cols-2">
											<button
												type="button"
												onclick={() => moveFormField(selectedFieldIndex, selectedFieldIndex - 1)}
												disabled={!canMoveFieldUp(selectedFieldIndex)}
												class="rounded-[14px] border px-3 py-2.5 text-sm font-bold cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
												style="border-color: rgba(226,232,240,0.95); background: linear-gradient(to bottom, #ffffff, #f8fafc); color: #475569;"
											>
												<ArrowUp class="mr-1.5 inline-block h-3.5 w-3.5" />
												Move Earlier
											</button>
											<button
												type="button"
												onclick={() => moveFormField(selectedFieldIndex, selectedFieldIndex + 1)}
												disabled={!canMoveFieldDown(selectedFieldIndex)}
												class="rounded-[14px] border px-3 py-2.5 text-sm font-bold cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
												style="border-color: rgba(226,232,240,0.95); background: linear-gradient(to bottom, #ffffff, #f8fafc); color: #475569;"
											>
												<ArrowDown class="mr-1.5 inline-block h-3.5 w-3.5" />
												Move Later
											</button>
										</div>
									</div>
								</div>

								<div class="grid gap-3 md:grid-cols-2">
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Label</p>
										<input
											type="text"
											class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none"
											style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
											value={selectedField.label}
											oninput={(event) => updateFieldLabel(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)}
										/>
									</div>

									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Key</p>
										<input
											type="text"
											class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none"
											style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
											value={selectedField.key}
											oninput={(event) => updateFieldKey(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)}
										/>
										<p class="mt-1 text-[11px] text-slate-500">Auto-normalized to lowercase underscore format.</p>
									</div>

									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Type</p>
										<select
											class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none cursor-pointer"
											style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
											value={selectedField.type}
											onchange={(event) => updateFieldType(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value)}
										>
											{#each fieldTypes as fieldType}
												<option value={fieldType}>{fieldType.toUpperCase()}</option>
											{/each}
										</select>
									</div>

									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Required</p>
										<button
											type="button"
											onclick={() => updateFieldRequired(selectedFieldIndex, !selectedField.required)}
											class="w-full rounded-[14px] border px-3 py-2.5 text-sm font-bold cursor-pointer"
											style={`border-color: ${selectedField.required ? 'rgba(37,99,235,0.22)' : 'rgba(226,232,240,0.95)'}; background: ${selectedField.required ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : 'linear-gradient(to bottom, #ffffff, #f8fafc)'}; color: ${selectedField.required ? '#1d4ed8' : '#64748b'};`}
										>
											{selectedField.required ? 'Required Field' : 'Optional Field'}
										</button>
									</div>
								</div>

								<div>
									<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Placeholder</p>
									<input
										type="text"
										class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none"
										style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
										value={selectedField.placeholder || ''}
										oninput={(event) => updateFieldProperty(selectedFieldIndex, 'placeholder', (event.currentTarget as HTMLInputElement).value)}
									/>
								</div>

								<div>
									<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Help Text</p>
									<textarea
										rows="2"
										class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none resize-y"
										style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
										value={selectedField.help_text || ''}
										oninput={(event) => updateFieldProperty(selectedFieldIndex, 'help_text', (event.currentTarget as HTMLTextAreaElement).value)}
									></textarea>
								</div>

								{#if selectedField.type === 'select'}
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Options</p>
										<input
											type="text"
											placeholder="comma,separated,values"
											class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none"
											style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
											value={selectedField.options?.join(', ') || ''}
											oninput={(event) => updateFormFieldOptions(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)}
										/>
									</div>
								{/if}

								{#if selectedField.type === 'textarea'}
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Rows</p>
										<input
											type="number"
											min="1"
											class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none"
											style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
											value={selectedField.rows ?? 3}
											oninput={(event) => {
												const parsed = Number.parseInt((event.currentTarget as HTMLInputElement).value, 10);
												updateFieldProperty(selectedFieldIndex, 'rows', Number.isFinite(parsed) && parsed > 0 ? parsed : undefined);
											}}
										/>
									</div>
								{/if}

								{#if selectedField.type === 'file'}
									<div class="grid gap-3 md:grid-cols-2">
										<div>
											<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Accepted Types</p>
											<input
												type="text"
												placeholder=".pdf,.jpg,image/*"
												class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none"
												style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
												value={selectedField.accept || ''}
												oninput={(event) => updateFieldProperty(selectedFieldIndex, 'accept', (event.currentTarget as HTMLInputElement).value)}
											/>
										</div>

										<div>
											<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Upload Mode</p>
											<button
												type="button"
												onclick={() => updateFieldProperty(selectedFieldIndex, 'multiple', !selectedField.multiple)}
												class="w-full rounded-[14px] border px-3 py-2.5 text-sm font-bold cursor-pointer"
												style={`border-color: ${selectedField.multiple ? 'rgba(37,99,235,0.22)' : 'rgba(226,232,240,0.95)'}; background: ${selectedField.multiple ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : 'linear-gradient(to bottom, #ffffff, #f8fafc)'}; color: ${selectedField.multiple ? '#1d4ed8' : '#64748b'};`}
											>
												{selectedField.multiple ? 'Multiple Files' : 'Single File'}
											</button>
										</div>
									</div>
								{/if}

								<div class="rounded-[18px] border border-slate-200 p-3" style="background: linear-gradient(to bottom, rgba(248,250,252,0.95), rgba(241,245,249,0.95));">
									<div class="mb-3">
										<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Visibility Logic</p>
										<p class="mt-1 text-xs text-slate-500">Simple field-level visibility is configured here. Earlier fields can drive later fields.</p>
									</div>

									{#if availableFields.length === 0}
										<p class="rounded-[14px] border border-slate-200 bg-white px-3 py-3 text-xs text-slate-500">Add a field before this one if you want to make it conditional.</p>
									{:else}
										<div class="space-y-3">
											<div>
												<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Show Field When</p>
												<select
													class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer"
													style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
													value={selectedField.condition?.field ?? ''}
													onchange={(event) => {
														const value = (event.currentTarget as HTMLSelectElement).value;
														if (!value) {
															clearFieldCondition(selectedFieldIndex);
															return;
														}
														updateFieldConditionField(selectedFieldIndex, value);
													}}
												>
													<option value="">Always show</option>
													{#each availableFields as fieldOption}
														<option value={fieldOption.key}>{fieldOption.label}</option>
													{/each}
												</select>
											</div>

											{#if selectedField.condition?.field}
												{@const controllingField = availableFields.find((fieldOption) => fieldOption.key === selectedField.condition?.field)}
												<div class="grid gap-3 md:grid-cols-2">
													<div>
														<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Operator</p>
														<select
															class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer"
															style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
															value={selectedField.condition.operator}
															onchange={(event) => updateFieldConditionOperator(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value as FieldCondition['operator'])}
														>
															<option value="not_empty">is filled</option>
															<option value="empty">is empty</option>
															<option value="eq">equals</option>
															<option value="ne">not equals</option>
														</select>
													</div>

													{#if selectedField.condition.operator === 'eq' || selectedField.condition.operator === 'ne'}
														<div>
															<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Value</p>
															{#if controllingField && controllingField.options.length > 0}
																<select
																	class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer"
																	style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
																	value={String(selectedField.condition.value ?? '')}
																	onchange={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value)}
																>
																	<option value="">Pick a value</option>
																	{#each controllingField.options as option}
																		<option value={option}>{option}</option>
																	{/each}
																</select>
															{:else}
																<input
																	type="text"
																	class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none"
																	style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
																	value={String(selectedField.condition.value ?? '')}
																	oninput={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)}
																/>
															{/if}
														</div>
													{/if}
												</div>
											{/if}
										</div>
									{/if}
								</div>
							</div>
						{:else}
							<div class="flex h-full items-center justify-center rounded-[18px] border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500" style="background: rgba(255,255,255,0.55);">
								Select a field from the overview to configure it.
							</div>
						{/if}
					</div>

					<div class="rounded-[22px] border border-slate-200 p-3.5" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); box-shadow: 0 12px 24px rgba(15,23,42,0.05);">
						<div class="mb-3 flex items-center justify-between gap-3">
							<div>
								<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Live Preview</p>
								<p class="mt-1 text-xs text-slate-500">Type into the preview to test placeholders and conditional visibility.</p>
							</div>
							<button
								type="button"
								onclick={() => (previewValues = {})}
								class="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-bold text-slate-600 cursor-pointer"
								style="background: linear-gradient(to bottom, #ffffff, #f8fafc);"
							>
								Reset Preview
							</button>
						</div>

						{#if previewSchema.duplicates.length > 0}
							<div class="mb-3 rounded-[14px] border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
								Duplicate field keys detected: {previewSchema.duplicates.join(', ')}. The preview is still rendered with temporary fallback keys, but saving will be blocked until the keys are unique.
							</div>
						{/if}

						<div class="rounded-[18px] border border-slate-200 p-3" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); min-height: 420px;">
							{#if previewSchema.fields.length > 0}
								<div class="space-y-3">
									<DynamicFormRenderer
										fields={previewSchema.fields}
										rules={formEditorRules}
										bind:values={previewValues}
										idPrefix="form-studio-preview"
									/>
								</div>
							{:else}
								<div class="flex h-full items-center justify-center text-center text-sm text-slate-500">
									Add at least one field to render the preview.
								</div>
							{/if}
						</div>
					</div>
				</div>

				<button
					onclick={saveFormDefinition}
					disabled={savingForm}
					class="w-full rounded-[999px] px-8 py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 10px 20px rgba(37,99,235,0.2), inset 0 2px 0 rgba(255,255,255,0.24);"
				>
					{#if savingForm}
						<Loader2 class="mr-2 inline-block h-4 w-4 animate-spin" />
						Saving...
					{:else}
						Save Configuration
					{/if}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}
