<script lang="ts">
	import { onMount } from 'svelte';
	import { studentApi } from '$lib/api/students';
	import { autocompleteApi, type DiagnosisSuggestion } from '$lib/api/autocomplete';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import { Clipboard, ChevronDown, ChevronUp, Award, User, Calendar, Stethoscope, Plus, Activity } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let caseRecords: any[] = $state([]);
	let loading = $state(true);
	let student: any = $state(null);
	let assignedPatients: any[] = $state([]);

	// Modal state
	let showCreateModal = $state(false);
	let departments: string[] = $state([]);
	let procedures: Record<string, string[]> = $state({});
	let facultyApprovers: { id: string; name: string; department: string }[] = $state([]);
	let submitting = $state(false);

	// Form state
	let selectedDepartment = $state('');
	let selectedProcedure = $state('');
	let selectedPatientId = $state('');
	let systolic = $state('');
	let diastolic = $state('');
	let patientPosition = $state('Sitting');
	let notes = $state('');
	let findings = $state('');
	let diagnosis = $state('');
	let icdCode = $state('');
	let icdDescription = $state('');
	let diagnosisSuggestions: DiagnosisSuggestion[] = $state([]);
	let diagnosisLoading = $state(false);
	let treatment = $state('');
	let selectedFacultyId = $state('');

	async function handleDiagnosisSearch(query: string) {
		if (query.length < 2) {
			diagnosisSuggestions = [];
			return;
		}
		diagnosisLoading = true;
		try {
			diagnosisSuggestions = await autocompleteApi.searchDiagnoses(query);
		} catch (err) {
			console.error('Failed to search diagnoses', err);
			diagnosisSuggestions = [];
		} finally {
			diagnosisLoading = false;
		}
	}

	function handleDiagnosisSelect(item: DiagnosisSuggestion) {
		diagnosis = item.text;
		icdCode = item.icd_code || '';
		icdDescription = item.icd_description || item.text;
	}

	const availableProcedures = $derived(
		selectedDepartment ? (procedures[selectedDepartment] || []) : []
	);

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		APPROVED: 'success',
		SUBMITTED: 'info',
		DRAFT: 'pending',
		REJECTED: 'error' as any,
	};

	const positionOptions = ['Sitting', 'Standing', 'Supine', 'Prone', 'Left Lateral', 'Right Lateral'];

	async function openCreateModal() {
		// Load form data
		[departments, procedures, facultyApprovers] = await Promise.all([
			studentApi.getDepartments(),
			studentApi.getProcedures(),
			studentApi.getFacultyApprovers(),
		]);
		// Reset form
		selectedDepartment = '';
		selectedProcedure = '';
		selectedPatientId = '';
		systolic = '';
		diastolic = '';
		patientPosition = 'Sitting';
		notes = '';
		findings = '';
		diagnosis = '';
		icdCode = '';
		icdDescription = '';
		diagnosisSuggestions = [];
		treatment = '';
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
				procedure_description: `BP: ${systolic}/${diastolic} mmHg (${patientPosition})`,
				notes,
				findings,
				diagnosis,
				treatment,
				icd_code: icdCode || undefined,
				icd_description: icdDescription || undefined,
				faculty_id: selectedFacultyId,
				time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
			});
			showCreateModal = false;
			// Refresh case records
			caseRecords = await studentApi.getCaseRecords(student.id);
		} catch (err) {
			console.error('Failed to submit case record', err);
		} finally {
			submitting = false;
		}
	}

	onMount(async () => {
		try {
			student = await studentApi.getMe();
			[caseRecords, assignedPatients] = await Promise.all([
				studentApi.getCaseRecords(student.id),
				studentApi.getAssignedPatients(student.id),
			]);
		} catch (err) {
			console.error('Failed to load case records', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-3">
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
<AquaModal open={showCreateModal} title="New Case Record" onclose={() => showCreateModal = false}>
	{#snippet children()}
		<div class="space-y-4">
			<!-- Patient Selection -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Patient</span>
				<select
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={selectedPatientId}
				>
					<option value="">Select a patient</option>
					{#each assignedPatients as patient}
						<option value={patient.id}>{patient.name} ({patient.patient_id})</option>
					{/each}
				</select>
			</div>

			<!-- Department Selection -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Department</span>
				<select
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={selectedDepartment}
					onchange={() => selectedProcedure = ''}
				>
					<option value="">Select department</option>
					{#each departments as dept}
						<option value={dept}>{dept}</option>
					{/each}
				</select>
			</div>

			<!-- Procedure Selection -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Procedure</span>
				<select
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={selectedProcedure}
					disabled={!selectedDepartment}
				>
					<option value="">Select procedure</option>
					{#each availableProcedures as proc}
						<option value={proc}>{proc}</option>
					{/each}
				</select>
			</div>

			<!-- Blood Pressure -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
					<Activity class="w-3 h-3" />
					Blood Pressure
				</span>
				<div class="flex items-center gap-2">
					<input
						type="number"
						placeholder="Systolic"
						class="flex-1 px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
						bind:value={systolic}
					/>
					<span class="text-gray-400">/</span>
					<input
						type="number"
						placeholder="Diastolic"
						class="flex-1 px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
						bind:value={diastolic}
					/>
					<span class="text-xs text-gray-500">mmHg</span>
				</div>
			</div>

			<!-- Patient Position -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Patient Position</span>
				<select
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={patientPosition}
				>
					{#each positionOptions as pos}
						<option value={pos}>{pos}</option>
					{/each}
				</select>
			</div>

			<!-- Notes -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Notes</span>
				<textarea
					placeholder="Additional notes..."
					rows="2"
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
					bind:value={notes}
				></textarea>
			</div>

			<!-- Findings -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Findings</span>
				<textarea
					placeholder="Clinical findings..."
					rows="2"
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
					bind:value={findings}
				></textarea>
			</div>

			<!-- Diagnosis with ICD Autocomplete -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Diagnosis</span>
				<Autocomplete
					placeholder="Search ICD-10 code or diagnosis..."
					bind:value={diagnosis}
					items={diagnosisSuggestions}
					labelKey="text"
					sublabelKey="icd_description"
					badgeKey="icd_code"
					onInput={handleDiagnosisSearch}
					onSelect={handleDiagnosisSelect}
					onClear={() => { icdCode = ''; icdDescription = ''; diagnosisSuggestions = []; }}
					loading={diagnosisLoading}
					minChars={2}
				/>
				{#if icdCode}
					<div class="mt-1.5 flex items-center gap-1.5">
						<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{icdCode}</span>
						<span class="text-[10px] text-gray-500 truncate">{icdDescription}</span>
					</div>
				{/if}
			</div>

			<!-- Treatment -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Treatment</span>
				<textarea
					placeholder="Treatment plan..."
					rows="2"
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
					bind:value={treatment}
				></textarea>
			</div>

			<!-- Faculty Approver -->
			<div>
				<span class="block text-xs font-semibold text-gray-700 mb-1">Request Approval From</span>
				<select
					class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					bind:value={selectedFacultyId}
				>
					<option value="">Select faculty</option>
					{#each facultyApprovers as faculty}
						<option value={faculty.id}>{faculty.name} ({faculty.department})</option>
					{/each}
				</select>
			</div>

			<!-- Submit Button -->
			<button
				class="w-full py-3 rounded-lg text-sm font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white;
				       box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);"
				onclick={handleSubmit}
				disabled={submitting || !selectedPatientId || !selectedDepartment || !selectedProcedure || !selectedFacultyId}
			>
				{submitting ? 'Submitting...' : 'Submit for Approval'}
			</button>
		</div>
	{/snippet}
</AquaModal>
