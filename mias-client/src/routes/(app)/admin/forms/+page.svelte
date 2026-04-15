<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { formsApi, type FormDefinitionPayload } from '$lib/api/forms';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import type { FormCategory, FormDefinition, FormFieldDefinition, FormRule, FormSection, FormFieldType, FieldCondition } from '$lib/types/forms';
	import { toastStore } from '$lib/stores/toast';
	import { FileText, Loader2, Pencil, Plus, Power, Trash2 } from 'lucide-svelte';

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
	let formEditorDescription = $state('');
	let formEditorDepartment = $state('');
	let formEditorProcedure = $state('');
	let formEditorSortOrder = $state(0);
	let formEditorIsActive = $state(true);
	let formEditorFields: FormFieldDefinition[] = $state([]);
	let formEditorRules: FormRule[] = $state([]);
	let savingForm = $state(false);
	let formSaveError = $state('');
	let showCategoryEditor = $state(false);
	let categoryName = $state('');
	let savingCategory = $state(false);
	let categorySaveError = $state('');
	let categoryMenu = $state<{ x: number; y: number; category: FormCategory } | null>(null);

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
		if (normalized === 'diagnosis') {
			return 'text';
		}
		return fieldTypes.includes(normalized as FormFieldType) ? (normalized as FormFieldType) : 'text';
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
		formEditorDescription = '';
		formEditorDepartment = '';
		formEditorProcedure = '';
		formEditorSortOrder = 0;
		formEditorIsActive = true;
		formEditorFields = [];
		formEditorRules = [];
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
		formEditorDescription = form.description || '';
		formEditorDepartment = form.department || '';
		formEditorProcedure = form.procedure_name || '';
		formEditorSortOrder = form.sort_order || 0;
		formEditorIsActive = form.is_active;
		formEditorFields = form.fields.map((field) => ({
			...field,
			type: normalizeFieldType(field.type)
		}));
		formEditorRules = form.rules ? [...form.rules] : [];
		activeSection = formEditorSection;
		showFormEditor = true;
	}

	function addFormField() {
		formEditorFields = [
			...formEditorFields,
			{
				key: '',
				label: '',
				type: 'text',
				required: false,
				placeholder: ''
			}
		];
	}

	function removeFormField(index: number) {
		const nextFields = formEditorFields.filter((_, fieldIndex) => fieldIndex !== index);
		formEditorFields = nextFields.length > 0 ? nextFields : [{ key: '', label: '', type: 'text', required: false, placeholder: '' }];
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
		if (type !== 'select') {
			nextField.options = [];
		}
		patchField(index, nextField);
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

	function serializeFields() {
		const finalKeys = formEditorFields.map((field, index) => field.key?.trim() || slugify(field.label) || `field_${index + 1}`);

		const keyMap = new Map<string, string>();
		formEditorFields.forEach((field, index) => {
			const finalKey = finalKeys[index];
			const rawKey = field.key?.trim();
			const autoKey = slugify(field.label || '');
			if (rawKey) keyMap.set(rawKey, finalKey);
			if (autoKey) keyMap.set(autoKey, finalKey);
			keyMap.set(`field_${index + 1}`, finalKey);
		});

		return formEditorFields.map((field, index) => {
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

		const payload: FormDefinitionPayload = {
			name: formEditorName.trim(),
			description: formEditorDescription || undefined,
			section: formEditorSection,
			fields: nextFields,
			rules: formEditorRules.length > 0 ? formEditorRules : undefined,
			sort_order: formEditorSortOrder,
			is_active: formEditorIsActive,
		};

		if (formEditorType) {
			payload.form_type = formEditorType;
		}
		if (formEditorDepartment) {
			payload.department = formEditorDepartment;
		}
		if (formEditorProcedure) {
			payload.procedure_name = formEditorProcedure;
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
	<div class="flex items-center gap-3">
		<h3 class="text-sm font-bold text-slate-900">Form Configuration</h3>
		<span class="rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
			{formEditorSection}
		</span>
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
			New Configuration
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
						{#if form.department}<p>Department: {form.department}</p>{/if}
						{#if form.procedure_name}<p>Context: {form.procedure_name}</p>{/if}
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
		panelClass="sm:max-w-[760px]"
		contentClass="p-0"
	>
		<div class="px-3.5 py-3.5 md:px-4 md:py-4" style="background: linear-gradient(to bottom, #ffffff, #f4f7fb); max-height: calc(100vh - 12rem);">
			{#if formSaveError}
				<div class="mb-4 rounded-[12px] border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{formSaveError}</div>
			{/if}

			<div class="space-y-4">
				<div>
					<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Form Name</p>
					<input
						type="text"
						placeholder="e.g. Initial Assessment"
						class="w-full rounded-[14px] border border-slate-300 px-3.5 py-2.5 text-sm font-semibold text-slate-800 outline-none md:px-4"
						style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
						bind:value={formEditorName}
					/>
				</div>

				<div>
					<div class="mb-2.5 flex items-center justify-between gap-4">
						<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Form Fields</p>
						<!-- {#if editingFormId && (formEditorDepartment || formEditorProcedure)}
							<p class="text-xs text-slate-400">Legacy context stays attached behind the scenes.</p>
						{/if} -->
					</div>

					<div class="rounded-lg border border-slate-300 p-1.5" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
						<div class="space-y-1">
							{#each formEditorFields as field, index (index)}
								{@const availableFields = getAvailableConditionFields(index)}
								<div class="rounded border border-slate-200 p-1.5" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
									<!-- Compact field row -->
									<div class="grid gap-1.5 items-center" style="grid-template-columns: minmax(0, 1fr) 90px 76px 28px;">
										<input
											type="text"
											placeholder="Label"
											class="w-full rounded border border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-700 outline-none"
											value={field.label}
											oninput={(event) => updateFieldLabel(index, (event.currentTarget as HTMLInputElement).value)}
										/>
										<select
											class="w-full rounded border border-slate-300 px-1.5 py-1.5 text-[10px] font-bold text-blue-700 outline-none cursor-pointer"
											value={field.type}
											onchange={(event) => updateFieldType(index, (event.currentTarget as HTMLSelectElement).value)}
										>
											{#each fieldTypes as fieldType}
												<option value={fieldType}>{fieldType.toUpperCase()}</option>
											{/each}
										</select>
										<button
											type="button"
											class="flex items-center justify-center rounded border px-1.5 py-1 text-[9px] font-bold transition-colors cursor-pointer"
											style="border-color: {field.required ? '#3b82f6' : '#d1d5db'}; background: {field.required ? '#eff6ff' : '#f9fafb'}; color: {field.required ? '#1d4ed8' : '#6b7280'};"
											onclick={() => updateFieldRequired(index, !field.required)}
										>
											{field.required ? 'REQ' : 'OPT'}
										</button>
										<button
											type="button"
											class="flex h-7 w-7 items-center justify-center rounded text-red-500 cursor-pointer hover:bg-red-50"
											onclick={() => removeFormField(index)}
											aria-label="Delete field"
										>
											<Trash2 class="h-3 w-3" />
										</button>
									</div>

									<!-- Select options -->
									{#if field.type === 'select'}
										<input
											type="text"
											placeholder="Options: a,b,c"
											class="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-[11px] text-slate-700 outline-none"
											value={field.options?.join(', ') ?? ''}
											oninput={(event) => updateFormFieldOptions(index, (event.currentTarget as HTMLInputElement).value)}
										/>
									{/if}

									<!-- Conditional logic controls -->
									{#if availableFields.length > 0}
										<div class="mt-1.5 pt-1.5 border-t border-slate-100">
											<div class="flex items-center gap-1.5 flex-wrap">
												<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wide">Show when</span>
												<select
													class="rounded border border-slate-300 px-1.5 py-0.5 text-[10px] text-slate-700 outline-none cursor-pointer"
													value={field.condition?.field ?? ''}
													onchange={(e) => {
														const val = (e.currentTarget as HTMLSelectElement).value;
														if (!val) clearFieldCondition(index);
														else updateFieldConditionField(index, val);
													}}
												>
													<option value="">— always show —</option>
													{#each availableFields as f}
														<option value={f.key}>{f.label}</option>
													{/each}
												</select>

												{#if field.condition?.field}
													{@const ctrlField = availableFields.find(f => f.key === field.condition?.field)}
													<select
														class="rounded border border-slate-300 px-1.5 py-0.5 text-[10px] text-slate-700 outline-none cursor-pointer"
														value={field.condition.operator}
														onchange={(e) => updateFieldConditionOperator(index, (e.currentTarget as HTMLSelectElement).value as FieldCondition['operator'])}
													>
														<option value="not_empty">is filled</option>
														<option value="empty">is empty</option>
														<option value="eq">equals</option>
														<option value="ne">not equals</option>
													</select>

													{#if field.condition.operator === 'eq' || field.condition.operator === 'ne'}
														{#if ctrlField && ctrlField.options.length > 0}
															<select
																class="rounded border border-slate-300 px-1.5 py-0.5 text-[10px] text-slate-700 outline-none cursor-pointer"
																value={String(field.condition.value ?? '')}
																onchange={(e) => updateFieldConditionValue(index, (e.currentTarget as HTMLSelectElement).value)}
															>
																<option value="">pick…</option>
																{#each ctrlField.options as opt}
																	<option value={opt}>{opt}</option>
																{/each}
															</select>
														{:else}
															<input
																type="text"
																placeholder="value…"
																class="w-20 rounded border border-slate-300 px-1.5 py-0.5 text-[10px] text-slate-700 outline-none"
																value={String(field.condition.value ?? '')}
																oninput={(e) => updateFieldConditionValue(index, (e.currentTarget as HTMLInputElement).value)}
															/>
														{/if}
													{/if}
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/each}

							<button
								onclick={addFormField}
								class="w-full rounded border border-dashed border-slate-300 px-3 py-2 text-xs font-semibold text-slate-400 cursor-pointer hover:border-slate-400 hover:text-slate-500"
								style="background: rgba(255,255,255,0.5);"
							>
								<Plus class="mr-1.5 inline-block h-3.5 w-3.5" />
								Add Field
							</button>
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
