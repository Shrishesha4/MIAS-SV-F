<script lang="ts">
	import { onMount } from 'svelte';
	import { studentApi } from '$lib/api/students';
	import { formsApi } from '$lib/api/forms';
	import { autocompleteApi, type DiagnosisSuggestion } from '$lib/api/autocomplete';
	import type { FormDefinition, FormFieldDefinition } from '$lib/types/forms';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import { buildCaseRecordDescription, buildCaseRecordProcedureMap, mergeProcedureMaps, resolveCaseRecordFields, stringifyFormValue } from '$lib/utils/forms';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import { Clipboard, ChevronDown, ChevronUp, Award, User, Calendar, Stethoscope, Plus } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let caseRecords: any[] = $state([]);
	let loading = $state(true);
	let student: any = $state(null);
	let assignedPatients: any[] = $state([]);

	// Modal state
	let showCreateModal = $state(false);
	let departments: string[] = $state([]);
	let procedures: Record<string, string[]> = $state({});
	let caseRecordForms: FormDefinition[] = $state([]);
	let facultyApprovers: { id: string; name: string; department: string }[] = $state([]);
	let submitting = $state(false);

	// Form state
	let selectedFormId = $state('');
	let selectedDepartment = $state('');
	let selectedProcedure = $state('');
	let selectedPatientId = $state('');
	let formData: Record<string, any> = $state({});
	let icdCode = $state('');
	let icdDescription = $state('');
	let diagnosisSuggestions: DiagnosisSuggestion[] = $state([]);
	let diagnosisLoading = $state(false);
	let selectedFacultyId = $state('');
	let allowedDepartments: string[] = $state([]);

	const mergedProcedureMap = $derived(
		mergeProcedureMaps(procedures, buildCaseRecordProcedureMap(caseRecordForms))
	);

	const selectedForm = $derived(
		caseRecordForms.find(f => f.id === selectedFormId) || null
	);

	const crFields: FormFieldDefinition[] | null = $derived(
		selectedForm ? selectedForm.fields : null
	);

	async function handleDiagnosisSearch(query: string) {
		if (query.length < 2) {
			diagnosisSuggestions = [];
			return;
		}
		diagnosisLoading = true;
		try {
			diagnosisSuggestions = await autocompleteApi.searchDiagnoses(query);
		} catch (err) {
			toastStore.addToast('Failed to search diagnoses', 'error');
			diagnosisSuggestions = [];
		} finally {
			diagnosisLoading = false;
		}
	}

	function handleDiagnosisSelect(item: DiagnosisSuggestion) {
		formData['diagnosis'] = item.text;
		icdCode = item.icd_code || '';
		icdDescription = item.icd_description || item.text;
	}

	const hasPermission = $derived(
		!selectedDepartment || allowedDepartments.includes(selectedDepartment)
	);

	function handleFormSelection(formId: string) {
		const form = caseRecordForms.find(f => f.id === formId);
		if (form) {
			selectedFormId = formId;
			selectedDepartment = form.department || '';
			selectedProcedure = form.procedure_name || '';
			formData = {};
			icdCode = '';
			icdDescription = '';
			diagnosisSuggestions = [];
		}
	}

	const availableProcedures = $derived(
		selectedDepartment && hasPermission ? (mergedProcedureMap[selectedDepartment] || []) : []
	);

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		APPROVED: 'success',
		SUBMITTED: 'info',
		DRAFT: 'pending',
		REJECTED: 'error' as any,
	};

	async function openCreateModal() {
		// Load form data + permissions
		const [depts, procs, approvers, perms, forms] = await Promise.all([
			studentApi.getDepartments(),
			studentApi.getProcedures(),
			studentApi.getFacultyApprovers(),
			student ? studentApi.getPermissions(student.id) : Promise.resolve([]),
			formsApi.getForms({ form_type: 'CASE_RECORD' }).catch(() => []),
		]);
		const merged = mergeProcedureMaps(procs, buildCaseRecordProcedureMap(forms));
		departments = Array.from(new Set([...depts, ...Object.keys(merged)])).sort();
		procedures = merged;
		caseRecordForms = forms;
		facultyApprovers = approvers;
		allowedDepartments = perms.map((p: any) => p.department);
		// Reset form
		selectedFormId = '';
		selectedDepartment = '';
		selectedProcedure = '';
		selectedPatientId = '';
		formData = {};
		icdCode = '';
		icdDescription = '';
		diagnosisSuggestions = [];
		selectedFacultyId = '';
		showCreateModal = true;
	}

	async function handleSubmit() {
		if (!selectedPatientId || !selectedDepartment || !selectedProcedure || !selectedFacultyId) {
			return;
		}
		submitting = true;
		try {
			await studentApi.submitCaseRecord(student.id, {
				patient_id: selectedPatientId,
				department: selectedDepartment,
				procedure: selectedProcedure,
				procedure_description: buildCaseRecordDescription(crFields, formData) || undefined,
				notes: stringifyFormValue(formData['notes']) || '',
				findings: stringifyFormValue(formData['findings']) || '',
				diagnosis: stringifyFormValue(formData['diagnosis']) || '',
				treatment: stringifyFormValue(formData['treatment']) || '',
				icd_code: icdCode || undefined,
				icd_description: icdDescription || undefined,
				faculty_id: selectedFacultyId,
				time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
			});
			showCreateModal = false;
			// Refresh case records
			caseRecords = await studentApi.getCaseRecords(student.id);
		} catch (err) {
			toastStore.addToast('Failed to submit case record', 'error');
		} finally {
			submitting = false;
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['STUDENT'])) return;
		try {
			student = await studentApi.getMe();
			[caseRecords, assignedPatients] = await Promise.all([
				studentApi.getCaseRecords(student.id),
				studentApi.getAssignedPatients(student.id),
			]);
		} catch (err) {
			toastStore.addToast('Failed to load case records', 'error');
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	<!-- Header -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2 w-full">
				<Clipboard class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Case Records
				</h2>
				<span class="ml-auto text-xs text-blue-600 font-semibold bg-blue-100 px-2 py-0.5 rounded-full">
					{caseRecords.length}
				</span>
			</div>
		{/snippet}
		<p class="text-xs text-gray-500">Your clinical case documentation and evaluations</p>
	</AquaCard>

	<!-- Case Record List -->
	{#each caseRecords as cr}
		<AquaCard padding={false}>
			<button
				class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
				onclick={() => expandedId = expandedId === cr.id ? null : cr.id}
			>
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, #8b5cf6cc, #8b5cf6);"
				>
					<Clipboard class="w-5 h-5 text-white" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{cr.chief_complaint}</p>
					<p class="text-xs text-gray-500 mt-0.5">
						{new Date(cr.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						{#if cr.time} · {cr.time}{/if}
						{#if cr.department} · {cr.department}{/if}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<StatusBadge variant={statusVariant[cr.status] ?? 'pending'}>{cr.status}</StatusBadge>
					{#if expandedId === cr.id}
						<ChevronUp class="w-4 h-4 text-gray-400" />
					{:else}
						<ChevronDown class="w-4 h-4 text-gray-400" />
					{/if}
				</div>
			</button>

			{#if expandedId === cr.id}
				<div class="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
					<!-- Examination -->
					<div class="p-3 rounded-lg bg-gray-50">
						<p class="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
							<Stethoscope class="w-3 h-3" />
							Examination
						</p>
						<p class="text-xs text-gray-600">{cr.examination}</p>
					</div>

					<!-- Diagnosis -->
					<div class="p-3 rounded-lg bg-blue-50">
						<p class="text-xs font-semibold text-blue-700 mb-1">Diagnosis</p>
						<p class="text-xs text-gray-700">{cr.diagnosis}</p>
						{#if cr.icd_code}
							<span class="inline-block mt-1 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{cr.icd_code}</span>
						{/if}
					</div>

					<!-- Treatment Plan -->
					<div class="p-3 rounded-lg bg-green-50">
						<p class="text-xs font-semibold text-green-700 mb-1">Treatment Plan</p>
						<p class="text-xs text-gray-700">{cr.treatment_plan}</p>
					</div>

					<!-- History -->
					{#if cr.history}
						<div class="p-3 rounded-lg bg-gray-50">
							<p class="text-xs font-semibold text-gray-700 mb-1">History</p>
							<p class="text-xs text-gray-600">{cr.history}</p>
						</div>
					{/if}

					<!-- Footer info -->
					<div class="pt-2 text-[10px] text-gray-400 space-y-1">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3">
								{#if cr.grade}
									<span class="flex items-center gap-1">
										<Award class="w-3 h-3" />
										Grade: <strong class="text-gray-600">{cr.grade}</strong>
									</span>
								{/if}
								{#if cr.created_by_name}
									<span class="flex items-center gap-1">
										<User class="w-3 h-3" />
										Created by: {cr.created_by_name}
										<span class="px-1 py-0.5 rounded text-[9px] font-semibold"
											style="background: {cr.created_by_role === 'FACULTY' ? 'rgba(139,92,246,0.1)' : 'rgba(59,130,246,0.1)'};
											       color: {cr.created_by_role === 'FACULTY' ? '#7c3aed' : '#2563eb'};">
											{cr.created_by_role === 'FACULTY' ? 'Doctor' : 'Student'}
										</span>
									</span>
								{:else if cr.provider}
									<span class="flex items-center gap-1">
										<User class="w-3 h-3" />
										{cr.provider}
									</span>
								{/if}
							</div>
							{#if cr.approver}
								<span>Approved by {cr.approver}</span>
							{/if}
						</div>
						{#if cr.last_modified_by}
							<div class="flex items-center gap-1 text-gray-400">
								Last modified by: {cr.last_modified_by}
								{#if cr.last_modified_at}
									· {new Date(cr.last_modified_at).toLocaleDateString('en-IN', {day: 'numeric', month: 'short'})} {new Date(cr.last_modified_at).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})}
								{/if}
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if caseRecords.length === 0}
		<div class="text-center py-12">
			<Clipboard class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No case records yet</p>
		</div>
	{/if}
	{/if}
</div>

<!-- Floating Action Button -->
<button
	class="fixed bottom-20 right-4 w-14 h-14 rounded-full flex items-center justify-center cursor-pointer shadow-lg z-40"
	style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
	       box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);"
	onclick={openCreateModal}
>
	<Plus class="w-6 h-6 text-white" />
</button>

<!-- Create Case Record Modal -->
<AquaModal open={showCreateModal} onclose={() => showCreateModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Clipboard class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">New Case Record</span>
		</div>
	{/snippet}
	{#snippet children()}
		<div class="space-y-4">
			<!-- Patient Selection -->
			<div>
				<label for="cr-patient" class="block text-sm font-medium text-gray-700 mb-1">
					Patient <span class="text-red-500">*</span>
				</label>
				<select id="cr-patient"
					class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					bind:value={selectedPatientId}
				>
					<option value="">Select a patient</option>
					{#each assignedPatients as patient}
						<option value={patient.id}>{patient.name} ({patient.patient_id})</option>
					{/each}
				</select>
			</div>

			<!-- Form Selection -->
			<div>
				<label for="cr-form" class="block text-sm font-medium text-gray-700 mb-1">
					Case Record Form <span class="text-red-500">*</span>
				</label>
				<select id="cr-form"
					class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					bind:value={selectedFormId}
					onchange={() => handleFormSelection(selectedFormId)}
				>
					<option value="">Search and select a form...</option>
					{#each caseRecordForms as form}
						<option value={form.id}>
							{form.name}
							{#if form.department || form.procedure_name}
								· {form.department || ''} {form.procedure_name ? `— ${form.procedure_name}` : ''}
							{/if}
						</option>
					{/each}
				</select>
				{#if selectedForm && selectedForm.description}
					<p class="text-xs text-gray-500 mt-1.5">{selectedForm.description}</p>
				{/if}
			</div>

			<!-- Display selected department and procedure (read-only) -->
			{#if selectedForm}
			<div class="grid grid-cols-2 gap-3">
				<div>
					<div class="block text-xs font-medium text-gray-600 mb-1">Department</div>
					<div class="px-3 py-2 rounded-md text-sm bg-gray-50 border border-gray-200 text-gray-700">
						{selectedForm.department || 'N/A'}
					</div>
				</div>
				<div>
					<div class="block text-xs font-medium text-gray-600 mb-1">Procedure</div>
					<div class="px-3 py-2 rounded-md text-sm bg-gray-50 border border-gray-200 text-gray-700">
						{selectedForm.procedure_name || 'N/A'}
					</div>
				</div>
			</div>
			{/if}

			<!-- Permission check -->
			{#if selectedDepartment && !hasPermission}
			<div class="rounded-lg p-4 text-center" style="background-color: rgba(254,226,226,0.5); border: 1px solid rgba(239,68,68,0.2);">
				<p class="text-sm font-medium text-red-700">You don't have permission to perform procedures in {selectedDepartment}.</p>
				<p class="text-xs text-red-500 mt-1">Contact your faculty advisor to request access.</p>
			</div>
			{/if}

			<!-- Dynamic procedure-specific fields -->
			{#if crFields}
				<DynamicFormRenderer
					fields={crFields}
					bind:values={formData}
					idPrefix="cr"
					diagnosisSuggestions={diagnosisSuggestions}
					diagnosisLoading={diagnosisLoading}
					onDiagnosisInput={handleDiagnosisSearch}
					onDiagnosisSelect={handleDiagnosisSelect}
					onDiagnosisClear={() => { icdCode = ''; icdDescription = ''; diagnosisSuggestions = []; }}
				/>
				{#if icdCode}
					<div class="mt-1.5 flex items-center gap-1.5">
						<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{icdCode}</span>
						<span class="text-[10px] text-gray-500 truncate">{icdDescription}</span>
					</div>
				{/if}

				<!-- Faculty Approver -->
				<div>
					<label for="cr-faculty" class="block text-sm font-medium text-gray-700 mb-1">
						Request Approval From <span class="text-red-500">*</span>
					</label>
					<select id="cr-faculty"
						class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
						style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
						bind:value={selectedFacultyId}
					>
						<option value="">Select faculty</option>
						{#each facultyApprovers as faculty}
							<option value={faculty.id}>{faculty.name} ({faculty.department})</option>
						{/each}
					</select>
				</div>
			{/if}

			<!-- Buttons -->
			<div class="flex justify-end gap-2 pt-2">
				<button
					class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
					       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
					onclick={() => showCreateModal = false}
				>Cancel</button>
				<button
					class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);
					       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
					onclick={handleSubmit}
					disabled={submitting || !selectedPatientId || !selectedDepartment || !selectedProcedure || !selectedFacultyId}
				>
					{submitting ? 'Submitting...' : 'Submit for Approval'}
				</button>
			</div>
		</div>
	{/snippet}
</AquaModal>
