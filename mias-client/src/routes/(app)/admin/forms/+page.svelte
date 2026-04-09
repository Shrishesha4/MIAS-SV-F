<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { formsApi, type FormDefinitionPayload } from '$lib/api/forms';
	import type { FormDefinition, FormFieldDefinition, FormSection, FormFieldType } from '$lib/types/forms';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import { FileText, Loader2, Pencil, Plus, Power, Trash2, X } from 'lucide-svelte';

	const auth = get(authStore);
	const sectionTabs: FormSection[] = ['CLINICAL', 'LABORATORY', 'ADMINISTRATIVE'];
	const fieldTypes: FormFieldType[] = ['text', 'textarea', 'number', 'select', 'diagnosis', 'date', 'file', 'email', 'password', 'tel'];
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
	let savingForm = $state(false);
	let formSaveError = $state('');

	const filteredForms = $derived.by(() => {
		return formDefinitions.filter((form) => resolveFormSection(form) === activeSection);
	});

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		loadForms();
	});

	function resolveFormSection(form: Pick<FormDefinition, 'section' | 'form_type'>): FormSection {
		const explicitSection = form.section?.toString().toUpperCase();
		if (explicitSection && sectionTabs.includes(explicitSection as FormSection)) {
			return explicitSection as FormSection;
		}
		return legacyTypeToSection[form.form_type?.toString().toUpperCase() || ''] || 'ADMINISTRATIVE';
	}

	function slugify(value: string) {
		return value
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, '_')
			.replace(/^_+|_+$/g, '');
	}

	async function loadForms() {
		loadingForms = true;
		try {
			formDefinitions = await formsApi.getForms({ include_inactive: true });
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
		formSaveError = '';
	}

	function openCreateFormEditor(section: FormSection = activeSection) {
		resetFormEditor();
		formEditorSection = section;
		activeSection = section;
		showFormEditor = true;
		addFormField();
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
		formEditorFields = form.fields.map((field) => ({ ...field }));
		activeSection = formEditorSection;
		showFormEditor = true;
	}

	function setEditorSection(section: FormSection) {
		formEditorSection = section;
		if (!editingFormId && section !== activeSection) {
			activeSection = section;
		}
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
		const nextField: FormFieldDefinition = { ...field, type: type as FormFieldType };
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

	function serializeFields() {
		return formEditorFields.map((field, index) => ({
			...field,
			key: field.key?.trim() || slugify(field.label) || `field_${index + 1}`,
			label: field.label.trim(),
			options: field.type === 'select' ? field.options ?? [] : field.options,
			placeholder: field.placeholder || undefined,
			help_text: field.help_text || undefined,
			accept: field.accept || undefined,
			rows: field.rows || undefined,
			multiple: field.multiple || false,
			required: field.required || false
		}));
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
			await loadForms();
		} catch (error: any) {
			formSaveError = error?.response?.data?.detail || 'Failed to save configuration';
		} finally {
			savingForm = false;
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
			await loadForms();
		} catch {
			toastStore.addToast('Failed to update configuration', 'error');
		}
	}
</script>

<AdminScaffold navItems={adminPageNavItems} title="System Forms" activeNav="forms" titleIcon={FileText}>
	<div class="space-y-4">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<p class="text-xs font-semibold text-slate-500 tracking-[0.24em] uppercase">Form Studio</p>
				<h2 class="text-2xl font-bold text-slate-900 mt-1">Simple configuration for clinical, laboratory, and administrative forms</h2>
			</div>
			<button
				onclick={() => openCreateFormEditor(activeSection)}
				class="inline-flex items-center gap-2 px-5 py-3 rounded-full text-sm font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 10px 24px rgba(37,99,235,0.28), inset 0 1px 0 rgba(255,255,255,0.25);"
			>
				<Plus class="w-4 h-4" />
				New Configuration
			</button>
		</div>

		<div
			class="p-2 rounded-[24px] flex flex-wrap gap-2"
			style="background: linear-gradient(to bottom, #eef2f8, #e2e8f0); border: 1px solid rgba(148,163,184,0.28); box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);"
		>
			{#each sectionTabs as section}
				<button
					onclick={() => activeSection = section}
					class="px-6 py-3 rounded-[16px] text-sm font-bold tracking-[0.2em] cursor-pointer"
					style={activeSection === section
						? 'background: linear-gradient(to bottom, #ffffff, #f8fafc); color: #2563eb; box-shadow: 0 6px 14px rgba(15,23,42,0.08), inset 0 1px 0 rgba(255,255,255,0.8);'
						: 'background: transparent; color: #5b6473;'}
				>
					{section}
				</button>
			{/each}
		</div>

		{#if loadingForms}
			<div class="flex items-center justify-center py-20">
				<Loader2 class="w-8 h-8 text-blue-500 animate-spin" />
			</div>
		{:else if filteredForms.length === 0}
			<div class="rounded-[28px] border border-slate-200 px-8 py-16 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 16px 40px rgba(15,23,42,0.06);">
				<FileText class="w-10 h-10 mx-auto text-slate-300 mb-4" />
				<p class="text-lg font-semibold text-slate-700">No {activeSection.toLowerCase()} forms configured yet</p>
				<p class="text-sm text-slate-400 mt-2">Create one from the button above and it will appear here.</p>
			</div>
		{:else}
			<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				{#each filteredForms as form}
					<div class="rounded-[26px] border border-slate-200 p-5" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 18px 36px rgba(15,23,42,0.06); opacity: {form.is_active ? 1 : 0.72};">
						<div class="flex items-start justify-between gap-3">
							<div>
								<p class="text-[11px] font-bold tracking-[0.22em] text-blue-600 uppercase">{resolveFormSection(form)}</p>
								<h3 class="text-lg font-bold text-slate-900 mt-2">{form.name}</h3>
							</div>
							<span class="px-3 py-1 rounded-full text-[11px] font-bold" style="background: {form.is_active ? 'rgba(37,99,235,0.1)' : 'rgba(148,163,184,0.12)'}; color: {form.is_active ? '#2563eb' : '#64748b'};">
								{form.is_active ? 'ACTIVE' : 'INACTIVE'}
							</span>
						</div>

						<div class="mt-4 space-y-2 text-sm text-slate-500">
							<p>{form.fields.length} fields configured</p>
							{#if form.department}<p>Department: {form.department}</p>{/if}
							{#if form.procedure_name}<p>Context: {form.procedure_name}</p>{/if}
						</div>

						<div class="mt-5 flex items-center gap-2">
							<button
								onclick={() => openEditFormEditor(form)}
								class="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold cursor-pointer"
								style="background: linear-gradient(to bottom, #ffffff, #eff6ff); color: #2563eb; border: 1px solid rgba(59,130,246,0.18);"
							>
								<Pencil class="w-4 h-4" />
								Edit
							</button>
							<button
								onclick={() => toggleFormActive(form)}
								class="px-4 py-2.5 rounded-full text-sm font-semibold cursor-pointer"
								style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); color: #475569; border: 1px solid rgba(148,163,184,0.24);"
							>
								<Power class="w-4 h-4 inline-block" />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	{#if showFormEditor}
		<div class="fixed inset-0 z-50 flex items-start justify-center px-4 py-6" style="background: rgba(148, 163, 184, 0.42); backdrop-filter: blur(8px);">
			<div class="w-full max-w-[1410px] overflow-hidden rounded-[30px] border border-slate-200" style="background: linear-gradient(to bottom, #ffffff, #f4f7fb); box-shadow: 0 30px 80px rgba(15,23,42,0.28), inset 0 1px 0 rgba(255,255,255,0.7);">
				<div class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-300 px-10 py-6">
					<div class="flex flex-wrap items-center gap-6">
						<h3 class="text-[20px] font-bold text-slate-900">Form Configuration</h3>
						<div class="rounded-[18px] p-1 flex flex-wrap gap-1" style="background: linear-gradient(to bottom, #eef2f7, #e2e8f0); border: 1px solid rgba(148,163,184,0.22);">
							{#each sectionTabs as section}
								<button
									onclick={() => setEditorSection(section)}
									class="px-5 py-2 rounded-[14px] text-sm font-bold tracking-[0.16em] cursor-pointer"
									style={formEditorSection === section
										? 'background: linear-gradient(to bottom, #ffffff, #f8fafc); color: #2563eb; box-shadow: 0 4px 10px rgba(15,23,42,0.08);'
										: 'background: transparent; color: #5b6473;'}
								>
									{section}
								</button>
							{/each}
						</div>
					</div>
					<button onclick={resetFormEditor} class="text-slate-400 hover:text-slate-700 cursor-pointer" aria-label="Close form editor">
						<X class="w-8 h-8" />
					</button>
				</div>

				<div class="px-8 py-10 md:px-10">
					{#if formSaveError}
						<div class="mb-6 rounded-[18px] border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-600">{formSaveError}</div>
					{/if}

					<div class="space-y-10">
						<div>
							<p class="mb-4 text-sm font-bold tracking-[0.22em] text-blue-700 uppercase">Form Name</p>
							<input
								type="text"
								placeholder="e.g. Initial Assessment"
								class="w-full rounded-[18px] border border-slate-300 px-6 py-5 text-2xl font-semibold text-slate-800 outline-none"
								style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
								bind:value={formEditorName}
							/>
						</div>

						<div>
							<div class="mb-4 flex items-center justify-between gap-4">
								<p class="text-sm font-bold tracking-[0.22em] text-blue-700 uppercase">Form Fields</p>
								{#if editingFormId && (formEditorDepartment || formEditorProcedure)}
									<p class="text-xs text-slate-400">Legacy context stays attached behind the scenes.</p>
								{/if}
							</div>

							<div class="rounded-[22px] border border-slate-300 p-4 md:p-5" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);">
								<div class="space-y-4">
									{#each formEditorFields as field, index (index)}
										<div class="rounded-[16px] border border-slate-200 p-4" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 6px 18px rgba(15,23,42,0.05);">
											<div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_168px_190px_44px] lg:items-center">
												<input
													type="text"
													placeholder="Field Label"
													class="w-full rounded-[14px] border border-slate-300 px-5 py-4 text-lg font-medium text-slate-700 outline-none"
													style="background: linear-gradient(to bottom, #ffffff, #fafcff); box-shadow: inset 0 1px 3px rgba(15,23,42,0.03);"
													value={field.label}
													oninput={(event) => updateFieldLabel(index, (event.currentTarget as HTMLInputElement).value)}
												/>
												<select
													class="w-full rounded-[14px] border border-slate-300 px-4 py-4 text-base font-bold text-blue-700 outline-none"
													style="background: linear-gradient(to bottom, #ffffff, #f5f9ff); box-shadow: inset 0 1px 3px rgba(15,23,42,0.03);"
													value={field.type}
													onchange={(event) => updateFieldType(index, (event.currentTarget as HTMLSelectElement).value)}
												>
													{#each fieldTypes as fieldType}
														<option value={fieldType}>{fieldType.toUpperCase()}</option>
													{/each}
												</select>
												<div class="flex items-center justify-between gap-4 rounded-[14px] border border-slate-300 px-5 py-4" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);">
													<span class="text-base font-bold text-slate-500">MANDATORY</span>
													<button
														type="button"
														class="relative h-10 w-[72px] rounded-full cursor-pointer transition-colors"
														style="background: {field.required ? 'linear-gradient(to right, #3b82f6, #1453c4)' : 'linear-gradient(to bottom, #e2e8f0, #cbd5e1)'}; box-shadow: inset 0 1px 3px rgba(15,23,42,0.12);"
														onclick={() => updateFieldRequired(index, !field.required)}
														aria-label="Toggle mandatory"
													>
														<span
															class="absolute top-[4px] h-8 w-8 rounded-full bg-white transition-all"
															style="left: {field.required ? '36px' : '4px'}; box-shadow: 0 4px 10px rgba(15,23,42,0.18);"
														></span>
													</button>
												</div>
												<button
													type="button"
													class="flex h-11 w-11 items-center justify-center rounded-full text-red-500 cursor-pointer"
													style="background: linear-gradient(to bottom, #fff5f5, #ffe4e6); border: 1px solid rgba(248,113,113,0.26);"
													onclick={() => removeFormField(index)}
													aria-label="Delete field"
												>
													<Trash2 class="w-5 h-5" />
												</button>
											</div>

											{#if field.type === 'select'}
												<input
													type="text"
													placeholder="Options separated by commas"
													class="mt-3 w-full rounded-[14px] border border-slate-300 px-5 py-3 text-sm text-slate-700 outline-none"
													style="background: linear-gradient(to bottom, #ffffff, #fafcff);"
													value={field.options?.join(', ') ?? ''}
													oninput={(event) => updateFormFieldOptions(index, (event.currentTarget as HTMLInputElement).value)}
												/>
											{/if}
										</div>
									{/each}

									<button
										onclick={addFormField}
										class="w-full rounded-[18px] border border-dashed border-slate-300 px-6 py-5 text-xl font-semibold text-slate-400 cursor-pointer"
										style="background: linear-gradient(to bottom, rgba(255,255,255,0.7), rgba(248,250,252,0.95));"
									>
										<Plus class="inline-block w-6 h-6 mr-2" />
										Add New Field
									</button>
								</div>
							</div>
						</div>

						<button
							onclick={saveFormDefinition}
							disabled={savingForm}
							class="w-full rounded-[999px] px-8 py-5 text-2xl font-bold text-white cursor-pointer disabled:opacity-60"
							style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 20px 40px rgba(37,99,235,0.28), inset 0 2px 0 rgba(255,255,255,0.24);"
						>
							{#if savingForm}
								<Loader2 class="inline-block w-6 h-6 mr-2 animate-spin" />
								Saving...
							{:else}
								Save Configuration
							{/if}
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</AdminScaffold>
