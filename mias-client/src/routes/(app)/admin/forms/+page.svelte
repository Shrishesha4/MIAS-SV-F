<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { formsApi, type FormDefinitionPayload } from '$lib/api/forms';
	import type { FormDefinition, FormFieldDefinition } from '$lib/types/forms';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import { Plus, Loader2, FileText } from 'lucide-svelte';

	const auth = get(authStore);
	let loadingForms = $state(true);
	let formDefinitions: FormDefinition[] = $state([]);

	// Form editor state
	let showFormEditor = $state(false);
	let editingFormId: string | null = $state(null);
	let formEditorName = $state('');
	let formEditorType = $state('CASE_RECORD');
	let formEditorDescription = $state('');
	let formEditorDepartment = $state('');
	let formEditorProcedure = $state('');
	let formEditorSortOrder = $state(0);
	let formEditorIsActive = $state(true);
	let formEditorFields: FormFieldDefinition[] = $state([]);
	let formPreviewValues: Record<string, any> = $state({});
	let savingForm = $state(false);
	let formSaveError = $state('');

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		loadForms();
	});

	async function loadForms() {
		loadingForms = true;
		try {
			formDefinitions = await formsApi.getForms({ include_inactive: true });
		} catch (e: any) {
			toastStore.addToast('Failed to load forms', 'error');
		} finally {
			loadingForms = false;
		}
	}

	function resetFormEditor() {
		showFormEditor = false;
		editingFormId = null;
		formEditorName = '';
		formEditorType = 'CASE_RECORD';
		formEditorDescription = '';
		formEditorDepartment = '';
		formEditorProcedure = '';
		formEditorSortOrder = 0;
		formEditorIsActive = true;
		formEditorFields = [];
		formPreviewValues = {};
		formSaveError = '';
	}

	function openCreateFormEditor() {
		resetFormEditor();
		showFormEditor = true;
	}

	function openEditFormEditor(form: FormDefinition) {
		editingFormId = form.id;
		formEditorName = form.name;
		formEditorType = form.form_type;
		formEditorDescription = form.description || '';
		formEditorDepartment = form.department || '';
		formEditorProcedure = form.procedure_name || '';
		formEditorSortOrder = form.sort_order || 0;
		formEditorIsActive = form.is_active;
		formEditorFields = form.fields.map(f => ({ ...f }));
		formPreviewValues = {};
		formSaveError = '';
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
		formEditorFields = formEditorFields.filter((_, i) => i !== index);
	}

	function updateFormFieldOptions(index: number, value: string) {
		const options = value.split(',').map(s => s.trim()).filter(Boolean);
		formEditorFields[index].options = options;
	}

	async function saveFormDefinition() {
		if (!formEditorName.trim()) {
			formSaveError = 'Form name is required';
			return;
		}

		if (formEditorFields.length === 0) {
			formSaveError = 'At least one field is required';
			return;
		}

		const invalidField = formEditorFields.find(f => !f.key || !f.label);
		if (invalidField) {
			formSaveError = 'All fields must have a key and label';
			return;
		}

		const payload: FormDefinitionPayload = {
			name: formEditorName,
			description: formEditorDescription || undefined,
			form_type: formEditorType,
			department: formEditorDepartment || undefined,
			procedure_name: formEditorProcedure || undefined,
			fields: formEditorFields,
			sort_order: formEditorSortOrder,
			is_active: formEditorIsActive
		};

		savingForm = true;
		formSaveError = '';
		try {
			if (editingFormId) {
				await formsApi.updateForm(editingFormId, payload);
				toastStore.addToast('Form updated successfully', 'success');
			} else {
				await formsApi.createForm(payload);
				toastStore.addToast('Form created successfully', 'success');
			}
			resetFormEditor();
			await loadForms();
		} catch (e: any) {
			formSaveError = e.response?.data?.detail || 'Failed to save form';
		} finally {
			savingForm = false;
		}
	}

	async function toggleFormActive(form: FormDefinition) {
		try {
			await formsApi.updateForm(form.id, {
				name: form.name,
				form_type: form.form_type,
				fields: form.fields,
				is_active: !form.is_active
			});
			toastStore.addToast(form.is_active ? 'Form deactivated' : 'Form activated', 'success');
			await loadForms();
		} catch (e: any) {
			toastStore.addToast('Failed to update form', 'error');
		}
	}
</script>

<AdminScaffold navItems={adminPageNavItems} title="System Forms" activeNav="forms" titleIcon={FileText}>
	<div class="flex items-center justify-between mb-4">
		<div>
			<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Form Definitions</p>
			<p class="text-xs text-slate-400 mt-1">Case-record definitions go live anywhere the shared renderer is used.</p>
		</div>
		<div class="flex items-center gap-2">
			<span class="text-[10px] text-slate-400">{formDefinitions.length} configured</span>
			{#if !showFormEditor}
				<button
					onclick={openCreateFormEditor}
					class="px-4 py-2 text-sm font-semibold text-white rounded-full"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
				>
					Add New
				</button>
			{/if}
		</div>
	</div>

	{#if showFormEditor}
		<div class="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.9fr)] mb-6">
			<div
				class="p-4 rounded-2xl"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
			>
				<div class="flex items-center justify-between gap-3 mb-4">
					<h4 class="text-sm font-bold text-slate-900">{editingFormId ? 'Edit Form' : 'New Form'}</h4>
					<button class="px-3 py-1.5 text-xs font-bold text-slate-500 cursor-pointer" onclick={resetFormEditor}>Close</button>
				</div>
				{#if formSaveError}
					<p class="text-xs text-red-500 mb-3 px-3 py-2 rounded-lg bg-red-50 border border-red-200">{formSaveError}</p>
				{/if}
				<div class="space-y-3">
					<div class="grid gap-2 sm:grid-cols-2">
						<input
							type="text"
							placeholder="Form Name"
							class="px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
							style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
							bind:value={formEditorName}
						/>
						<select
							class="px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
							style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
							bind:value={formEditorType}
						>
							<option value="CASE_RECORD">CASE_RECORD</option>
							<option value="ADMISSION">ADMISSION</option>
							<option value="ADMISSION_REQUEST">ADMISSION_REQUEST</option>
							<option value="ADMISSION_INTAKE">ADMISSION_INTAKE</option>
							<option value="ADMISSION_DISCHARGE">ADMISSION_DISCHARGE</option>
							<option value="ADMISSION_TRANSFER">ADMISSION_TRANSFER</option>
							<option value="PROFILE">PROFILE</option>
							<option value="PROFILE_EDIT">PROFILE_EDIT</option>
							<option value="PRESCRIPTION">PRESCRIPTION</option>
							<option value="PRESCRIPTION_CREATE">PRESCRIPTION_CREATE</option>
							<option value="PRESCRIPTION_EDIT">PRESCRIPTION_EDIT</option>
							<option value="PRESCRIPTION_REQUEST">PRESCRIPTION_REQUEST</option>
							<option value="VITAL_ENTRY">VITAL_ENTRY</option>
							<option value="CUSTOM">CUSTOM</option>
						</select>
					</div>
					<textarea
						placeholder="Description"
						rows="2"
						class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl resize-y"
						style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
						bind:value={formEditorDescription}
					></textarea>
					{#if formEditorType === 'CASE_RECORD'}
						<div class="grid gap-2 sm:grid-cols-2">
							<input
								type="text"
								placeholder="Department"
								class="px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
								style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
								bind:value={formEditorDepartment}
							/>
							<input
								type="text"
								placeholder="Procedure Name"
								class="px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
								style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
								bind:value={formEditorProcedure}
							/>
						</div>
					{/if}
					<div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
						<input
							type="number"
							min="0"
							placeholder="Sort Order"
							class="px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
							style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
							bind:value={formEditorSortOrder}
						/>
						<label class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-slate-700 border border-blue-200" style="background: rgba(59,130,246,0.05);">
							<input type="checkbox" bind:checked={formEditorIsActive} />
							Active
						</label>
					</div>

					<div class="flex items-center justify-between pt-2">
						<h5 class="text-xs font-bold uppercase tracking-wide text-slate-500">Fields</h5>
						<button
							class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
							onclick={addFormField}
						>
							<Plus class="w-3.5 h-3.5" />
							Add Field
						</button>
					</div>

					<div class="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
						{#each formEditorFields as field, index (index)}
							<div class="p-3 rounded-xl border border-slate-200" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5);">
								<div class="grid gap-2 sm:grid-cols-2">
									<input
										type="text"
										placeholder="Field Key"
										class="px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										bind:value={field.key}
									/>
									<input
										type="text"
										placeholder="Label"
										class="px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										bind:value={field.label}
									/>
								</div>
								<div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] mt-2">
									<select
										class="px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										bind:value={field.type}
									>
										{#each ['text', 'textarea', 'number', 'select', 'diagnosis', 'date', 'file', 'email', 'password', 'tel'] as fieldType}
											<option value={fieldType}>{fieldType}</option>
										{/each}
									</select>
									<input
										type="text"
										placeholder="Placeholder"
										class="px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										bind:value={field.placeholder}
									/>
									<label class="flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-700 border border-slate-200" style="background: white;">
										<input type="checkbox" bind:checked={field.required} />
										Req.
									</label>
								</div>
								{#if field.type === 'select'}
									<input
										type="text"
										value={field.options?.join(', ') ?? ''}
										placeholder="Options (comma separated)"
										class="mt-2 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										oninput={(event) => updateFormFieldOptions(index, event.currentTarget.value)}
									/>
								{:else if field.type === 'textarea'}
									<input
										type="number"
										min="2"
										max="12"
										placeholder="Rows"
										class="mt-2 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
										style="background: white;"
										bind:value={field.rows}
									/>
								{:else if field.type === 'file'}
									<div class="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto] mt-2">
										<input
											type="text"
											placeholder="Accept (e.g. image/*,.pdf)"
											class="px-3 py-2 text-sm border border-slate-200 rounded-lg"
											style="background: white;"
											bind:value={field.accept}
										/>
										<label class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-700 border border-slate-200" style="background: white;">
											<input type="checkbox" bind:checked={field.multiple} />
											Multiple
										</label>
									</div>
								{/if}
								<input
									type="text"
									placeholder="Help text"
									class="mt-2 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg"
									style="background: white;"
									bind:value={field.help_text}
								/>
								<div class="flex justify-end mt-2">
									<button class="px-3 py-1.5 text-xs font-bold text-red-500 cursor-pointer" onclick={() => removeFormField(index)}>Remove</button>
								</div>
							</div>
						{/each}
						{#if formEditorFields.length === 0}
							<div class="text-center py-6 rounded-xl border border-dashed border-slate-300" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5);">
								<p class="text-sm text-slate-400">No fields added yet</p>
							</div>
						{/if}
					</div>

					<div class="flex gap-2 pt-2">
						<button
							class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
							onclick={saveFormDefinition}
							disabled={savingForm}
						>
							{savingForm ? 'Saving...' : editingFormId ? 'Update Form' : 'Create Form'}
						</button>
						<button class="px-4 py-2.5 text-sm font-bold text-slate-500 cursor-pointer" onclick={resetFormEditor}>Cancel</button>
					</div>
				</div>
			</div>

			<div
				class="p-4 rounded-2xl"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
			>
				<h4 class="text-sm font-bold text-slate-900 mb-4">Live Preview</h4>
				{#if formEditorFields.length > 0}
					<div class="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
						<DynamicFormRenderer fields={formEditorFields} bind:values={formPreviewValues} idPrefix="admin-form-preview" />
					</div>
				{:else}
					<div class="text-center py-10 rounded-xl border border-dashed border-slate-300" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5);">
						<p class="text-sm text-slate-400">Add fields to preview this form</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	{#if loadingForms}
		<div class="flex items-center justify-center py-12">
			<Loader2 class="w-8 h-8 text-blue-500 animate-spin" />
		</div>
	{:else}
		<div class="space-y-3">
			{#each formDefinitions as form}
				<div
					class="p-4 rounded-xl flex flex-wrap items-center justify-between gap-3"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 2px rgba(0,0,0,0.06); opacity: {form.is_active ? 1 : 0.65};"
				>
					<div class="min-w-0">
						<p class="text-sm font-semibold text-slate-900 truncate">{form.name}</p>
						<p class="text-[11px] text-slate-500 truncate">
							<span class="font-bold uppercase text-blue-600">{form.form_type}</span>
							{#if form.department}<span> · {form.department}</span>{/if}
							{#if form.procedure_name}<span> · {form.procedure_name}</span>{/if}
							<span> · {form.fields.length} fields</span>
							{#if !form.is_active}<span class="text-red-500 font-bold"> · INACTIVE</span>{/if}
						</p>
						{#if form.description}
							<p class="text-xs text-slate-500 mt-1 line-clamp-2">{form.description}</p>
						{/if}
					</div>
					<div class="flex items-center gap-2 shrink-0">
						<button
							class="px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer text-blue-700 border border-blue-200"
							style="background: rgba(59,130,246,0.08);"
							onclick={() => openEditFormEditor(form)}
						>
							Edit
						</button>
						<button
							class="px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer text-slate-700 border border-slate-300"
							style="background: rgba(148,163,184,0.08);"
							onclick={() => toggleFormActive(form)}
						>
							{form.is_active ? 'Deactivate' : 'Activate'}
						</button>
					</div>
				</div>
			{/each}
			{#if formDefinitions.length === 0}
				<div class="text-center py-12">
					<FileText class="w-10 h-10 mx-auto text-slate-300 mb-3" />
					<p class="text-sm text-slate-400">No form definitions yet</p>
				</div>
			{/if}
		</div>
	{/if}
</AdminScaffold>
