<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { authApi } from '$lib/api/auth';
	import type { Admission } from '$lib/api/types';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { 
		Bed, Calendar, User, Building, ChevronDown, ChevronUp, ChevronLeft,
		Clock, Link, FileText, CheckCircle, Circle, ArrowRightCircle, X,
		Plus, Search, LogOut, ArrowRight, Filter
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;
	const isFacultyOrAdmin = role === 'FACULTY' || role === 'ADMIN';

	// Shared state
	let admissions: any[] = $state([]);
	let admissionsMap = $state<Record<string, any>>({});
	let loading = $state(true);
	let expandedId = $state<string | null>(null);
	let showDischargeSummary = $state(false);
	let selectedAdmission = $state<any>(null);

	// Faculty/Admin state
	let filterStatus = $state('');
	let showAdmitModal = $state(false);
	let showDischargeModal = $state(false);
	let showTransferModal = $state(false);
	let actionAdmission = $state<any>(null);
	let submitting = $state(false);
	let actionError = $state('');

	// Admit form fields
	let searchQuery = $state('');
	let searchResults: any[] = $state([]);
	let searching = $state(false);
	let selectedPatient = $state<any>(null);
	let admitDepartment = $state('');
	let admitWard = $state('');
	let admitBed = $state('');
	let admitReason = $state('');
	let admitDiagnosis = $state('');
	let admitNotes = $state('');
	let dbDepartments: { id: string; name: string; code: string }[] = $state([]);

	// Discharge form fields
	let dischargeSummary = $state('');
	let dischargeInstructions = $state('');
	let dischargeDiagnosis = $state('');
	let followUpDate = $state('');

	// Transfer form fields
	let transferDepartment = $state('');
	let transferWard = $state('');
	let transferBed = $state('');
	let transferDoctor = $state('');
	let transferNotes = $state('');

	const filteredAdmissions = $derived(
		filterStatus
			? admissions.filter((a: any) => a.status === filterStatus)
			: admissions
	);

	function getStatusIcon(status: string) {
		if (status === 'Discharged') return { color: '#22c55e', icon: CheckCircle };
		if (status === 'Transferred') return { color: '#3b82f6', icon: ArrowRightCircle };
		return { color: '#f59e0b', icon: Circle }; // Active
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', { 
			month: 'short', day: 'numeric', year: 'numeric' 
		});
	}

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	function openDischargeSummary(admission: any) {
		selectedAdmission = admission;
		showDischargeSummary = true;
	}

	function closeDischargeSummary() {
		showDischargeSummary = false;
		selectedAdmission = null;
	}

	function getRelatedAdmission(id: string | undefined): any | undefined {
		if (!id) return undefined;
		return admissionsMap[id];
	}

	// Faculty actions
	async function searchPatients() {
		if (!searchQuery.trim()) { searchResults = []; return; }
		searching = true;
		try {
			searchResults = await patientApi.searchPatientsForAdmission(searchQuery);
		} catch { searchResults = []; }
		finally { searching = false; }
	}

	function selectPatient(p: any) {
		selectedPatient = p;
		searchQuery = p.name;
		searchResults = [];
	}

	function openAdmitModal() {
		selectedPatient = null;
		searchQuery = '';
		searchResults = [];
		admitDepartment = '';
		admitWard = '';
		admitBed = '';
		admitReason = '';
		admitDiagnosis = '';
		admitNotes = '';
		actionError = '';
		showAdmitModal = true;
	}

	async function submitAdmit() {
		if (!selectedPatient) { actionError = 'Please select a patient'; return; }
		if (!admitDepartment) { actionError = 'Please select a department'; return; }
		if (!admitWard) { actionError = 'Ward is required'; return; }
		if (!admitBed) { actionError = 'Bed number is required'; return; }
		submitting = true;
		actionError = '';
		try {
			await patientApi.createAdmission(selectedPatient.id, {
				department: admitDepartment,
				ward: admitWard,
				bed_number: admitBed,
				reason: admitReason,
				diagnosis: admitDiagnosis,
				notes: admitNotes,
			});
			showAdmitModal = false;
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to create admission';
		} finally { submitting = false; }
	}

	function openDischargeModal(admission: any) {
		actionAdmission = admission;
		dischargeSummary = '';
		dischargeInstructions = '';
		dischargeDiagnosis = admission.diagnosis || '';
		followUpDate = '';
		actionError = '';
		showDischargeModal = true;
	}

	async function submitDischarge() {
		if (!dischargeSummary) { actionError = 'Discharge summary is required'; return; }
		submitting = true;
		actionError = '';
		try {
			await patientApi.dischargePatient(actionAdmission.patient_id, actionAdmission.id, {
				discharge_summary: dischargeSummary,
				discharge_instructions: dischargeInstructions,
				diagnosis: dischargeDiagnosis,
				follow_up_date: followUpDate || null,
			});
			showDischargeModal = false;
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to discharge';
		} finally { submitting = false; }
	}

	function openTransferModal(admission: any) {
		actionAdmission = admission;
		transferDepartment = '';
		transferWard = '';
		transferBed = '';
		transferDoctor = '';
		transferNotes = '';
		actionError = '';
		showTransferModal = true;
	}

	async function submitTransfer() {
		if (!transferDepartment) { actionError = 'Please select target department'; return; }
		if (!transferWard) { actionError = 'Ward is required'; return; }
		if (!transferBed) { actionError = 'Bed number is required'; return; }
		submitting = true;
		actionError = '';
		try {
			await patientApi.transferPatient(actionAdmission.patient_id, actionAdmission.id, {
				new_department: transferDepartment,
				new_ward: transferWard,
				new_bed_number: transferBed,
				new_attending_doctor: transferDoctor || undefined,
				notes: transferNotes || undefined,
			});
			showTransferModal = false;
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to transfer';
		} finally { submitting = false; }
	}

	async function loadAdmissions() {
		loading = true;
		try {
			if (isFacultyOrAdmin) {
				admissions = await patientApi.getAllAdmissions();
			} else {
				const patient = await patientApi.getCurrentPatient();
				admissions = await patientApi.getAdmissions(patient.id);
			}
			admissionsMap = {};
			admissions.forEach((a: any) => { admissionsMap[a.id] = a; });
		} catch (err) {
			console.error('Failed to load admissions', err);
		} finally { loading = false; }
	}

	onMount(async () => {
		if (isFacultyOrAdmin) {
			try {
				const depts = await authApi.getDepartments();
				dbDepartments = depts;
			} catch {}
		}
		await loadAdmissions();
	});
</script>

<div class="px-4 py-4 space-y-2">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-4">
		<button class="p-2 rounded-full hover:bg-gray-100" onclick={() => history.back()}>
			<ChevronLeft class="w-5 h-5 text-gray-600" />
		</button>
		<h1 class="text-lg font-bold text-gray-800 flex-1">
			{isFacultyOrAdmin ? 'Admission Management' : 'Admission Records'}
		</h1>
		{#if isFacultyOrAdmin}
			<button
				class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-white text-sm font-medium"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={openAdmitModal}
			>
				<Plus class="w-4 h-4" />
				Admit
			</button>
		{/if}
	</div>

	<!-- Faculty: Status Filter -->
	{#if isFacultyOrAdmin}
		<div class="flex gap-2 mb-3 overflow-x-auto pb-1">
			{#each ['', 'Active', 'Discharged', 'Transferred'] as status}
				<button
					class="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors"
					class:bg-blue-500={filterStatus === status}
					class:text-white={filterStatus === status}
					class:bg-gray-100={filterStatus !== status}
					class:text-gray-600={filterStatus !== status}
					onclick={() => filterStatus = status}
				>
					{status || 'All'}
				</button>
			{/each}
		</div>
	{/if}

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Admissions List -->
		{#each filteredAdmissions as admission}
			{@const statusInfo = getStatusIcon(admission.status)}
			{@const StatusIcon = statusInfo.icon}
			{@const isExpanded = expandedId === admission.id}
			
			<AquaCard padding={false}>
				<!-- Collapsed Header -->
				<button 
					class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
					onclick={() => toggleExpand(admission.id)}
				>
					<!-- Status Icon -->
					<div 
						class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
						style="background: {statusInfo.color}20;"
					>
						<StatusIcon class="w-5 h-5" style="color: {statusInfo.color};" />
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						{#if isFacultyOrAdmin && admission.patient_name}
							<p class="text-sm font-bold text-gray-800">{admission.patient_name}</p>
							<p class="text-xs text-gray-500">{admission.patient_display_id} · {formatDate(admission.admission_date)}</p>
						{:else}
							<p class="text-xs text-gray-500">{formatDate(admission.admission_date)}</p>
							<p class="text-sm font-bold text-gray-800">{admission.ward}, {admission.bed_number}</p>
						{/if}
						<p class="text-xs text-gray-600">{admission.attending_doctor} · {admission.department}</p>
					</div>

					<!-- Status + Expand -->
					<div class="flex items-center gap-2">
						<span
							class="px-2 py-0.5 rounded-full text-xs font-medium"
							style="background: {statusInfo.color}15; color: {statusInfo.color};"
						>{admission.status}</span>
						{#if isExpanded}
							<ChevronUp class="w-4 h-4 text-gray-400" />
						{:else}
							<ChevronDown class="w-4 h-4 text-gray-400" />
						{/if}
					</div>
				</button>

				<!-- Expanded Content -->
				{#if isExpanded}
					<div class="px-4 pb-4 space-y-4 border-t border-gray-100">
						<!-- Dates & Location -->
						<div class="grid grid-cols-2 gap-4 pt-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Admission Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">{formatDate(admission.admission_date)}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Discharge Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">
										{admission.discharge_date ? formatDate(admission.discharge_date) : 'Active'}
									</span>
								</div>
							</div>
						</div>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Ward & Bed</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
										<Bed class="w-4 h-4 text-gray-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.ward}, {admission.bed_number}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Admitted Under</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
										<User class="w-4 h-4 text-green-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.attending_doctor}</span>
								</div>
							</div>
						</div>

						<!-- Reason for Admission -->
						{#if admission.reason}
							<div class="p-3 rounded-xl border border-gray-200">
								<p class="text-xs text-gray-500 mb-1">Reason for Admission</p>
								<p class="text-sm text-gray-800">{admission.reason}</p>
							</div>
						{/if}

						<!-- Diagnosis -->
						{#if admission.diagnosis}
							<div class="p-3 rounded-xl bg-gray-50">
								<p class="text-xs text-gray-500 mb-1">Diagnosis</p>
								<p class="text-sm text-gray-800">{admission.diagnosis}</p>
							</div>
						{/if}

						<!-- Related Admission (if transferred) -->
						{#if admission.related_admission_id}
							{@const relatedAdmission = getRelatedAdmission(admission.related_admission_id)}
							{#if relatedAdmission}
								<div class="p-3 rounded-xl bg-blue-50 border border-blue-100">
									<div class="flex items-center gap-2 text-blue-600 mb-2">
										<Link class="w-4 h-4" />
										<span class="text-xs font-medium">Related Admission</span>
									</div>
									<p class="text-sm text-blue-800">
										Transferred from {admission.transferred_from_department} ({admission.referring_doctor})
									</p>
								</div>
							{/if}
						{/if}

						<!-- Transferred From Section -->
						{#if admission.transferred_from_department}
							<div class="p-3 rounded-xl border border-gray-200 space-y-2">
								<div>
									<p class="text-xs text-gray-500">Transferred From</p>
									<p class="text-sm font-semibold text-gray-800">{admission.transferred_from_department}</p>
								</div>
								{#if admission.referring_doctor}
									<div>
										<p class="text-xs text-gray-500">Referring Doctor</p>
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-gray-500" />
											<span class="text-sm text-gray-800">{admission.referring_doctor}</span>
										</div>
									</div>
								{/if}
							</div>
						{/if}

						<!-- View Discharge Summary Button -->
						{#if admission.status === 'Discharged' && admission.discharge_summary}
							<button 
								class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
								onclick={() => openDischargeSummary(admission)}
							>
								<FileText class="w-5 h-5" />
								View Discharge Summary
							</button>
						{/if}

						<!-- Faculty Action Buttons -->
						{#if isFacultyOrAdmin && admission.status === 'Active'}
							<div class="flex gap-2 pt-2">
								<button
									class="flex-1 py-2.5 rounded-xl text-white text-sm font-medium flex items-center justify-center gap-1.5"
									style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
									onclick={() => openDischargeModal(admission)}
								>
									<LogOut class="w-4 h-4" />
									Discharge
								</button>
								<button
									class="flex-1 py-2.5 rounded-xl text-white text-sm font-medium flex items-center justify-center gap-1.5"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
									onclick={() => openTransferModal(admission)}
								>
									<ArrowRight class="w-4 h-4" />
									Transfer
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</AquaCard>
		{/each}

		{#if filteredAdmissions.length === 0}
			<div class="text-center py-12 text-gray-400">
				<Bed class="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p class="text-sm">No admissions found</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Discharge Summary Modal -->
{#if showDischargeSummary && selectedAdmission}
	<AquaModal onClose={closeDischargeSummary}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<FileText class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Discharge Summary</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			<div class="p-4 rounded-xl bg-gray-50">
				<div class="grid grid-cols-2 gap-3 text-sm">
					<div>
						<span class="text-gray-500">Admitted:</span>
						<span class="ml-1 text-gray-800 font-medium">{formatDate(selectedAdmission.admission_date)}</span>
					</div>
					<div>
						<span class="text-gray-500">Discharged:</span>
						<span class="ml-1 text-gray-800 font-medium">{formatDate(selectedAdmission.discharge_date)}</span>
					</div>
					<div>
						<span class="text-gray-500">Department:</span>
						<span class="ml-1 text-gray-800">{selectedAdmission.department}</span>
					</div>
					<div>
						<span class="text-gray-500">Doctor:</span>
						<span class="ml-1 text-gray-800">{selectedAdmission.attending_doctor}</span>
					</div>
				</div>
			</div>

			{#if selectedAdmission.diagnosis}
				<div>
					<h4 class="text-sm font-semibold text-gray-700 mb-2">Diagnosis</h4>
					<p class="text-sm text-gray-800 p-3 rounded-lg bg-gray-50">{selectedAdmission.diagnosis}</p>
				</div>
			{/if}

			<div>
				<h4 class="text-sm font-semibold text-gray-700 mb-2">Summary</h4>
				<p class="text-sm text-gray-800 p-3 rounded-lg bg-gray-50">{selectedAdmission.discharge_summary}</p>
			</div>

			{#if selectedAdmission.discharge_instructions}
				<div>
					<h4 class="text-sm font-semibold text-gray-700 mb-2">Discharge Instructions</h4>
					<p class="text-sm text-gray-800 p-3 rounded-lg bg-blue-50">{selectedAdmission.discharge_instructions}</p>
				</div>
			{/if}

			{#if selectedAdmission.follow_up_date}
				<div class="p-3 rounded-xl border border-green-200 bg-green-50">
					<div class="flex items-center gap-2">
						<Calendar class="w-4 h-4 text-green-600" />
						<span class="text-sm text-green-800">
							Follow-up scheduled: <strong>{formatDate(selectedAdmission.follow_up_date)}</strong>
						</span>
					</div>
				</div>
			{/if}
		</div>
	</AquaModal>
{/if}

<!-- Admit Patient Modal -->
{#if showAdmitModal}
	<AquaModal onClose={() => showAdmitModal = false}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<Plus class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Admit Patient</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<!-- Patient Search -->
			<div>
				<label class="text-xs text-gray-500 mb-1 block">Patient</label>
				<div class="relative">
					<div class="flex items-center px-3 py-2.5 rounded-xl border border-gray-200">
						<Search class="w-4 h-4 text-gray-400 mr-2 shrink-0" />
						<input
							type="text"
							placeholder="Search patient by name or ID..."
							bind:value={searchQuery}
							oninput={searchPatients}
							class="flex-1 outline-none text-sm text-gray-700 bg-transparent"
						/>
					</div>
					{#if searchResults.length > 0}
						<div class="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg z-10 max-h-48 overflow-y-auto">
							{#each searchResults as p}
								<button
									class="w-full px-4 py-2.5 text-left hover:bg-gray-50 flex items-center gap-3 text-sm"
									onclick={() => selectPatient(p)}
								>
									<User class="w-4 h-4 text-gray-400" />
									<div>
										<p class="font-medium text-gray-800">{p.name}</p>
										<p class="text-xs text-gray-500">{p.patient_id} · {p.gender} · {p.blood_group}</p>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
				{#if selectedPatient}
					<div class="mt-2 p-2 rounded-lg bg-blue-50 flex items-center gap-2 text-sm text-blue-700">
						<CheckCircle class="w-4 h-4" />
						<span>{selectedPatient.name} ({selectedPatient.patient_id})</span>
					</div>
				{/if}
			</div>

			<!-- Department -->
			<div>
				<label class="text-xs text-gray-500 mb-1 block">Department</label>
				<select bind:value={admitDepartment}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-700 outline-none">
					<option value="">Select department</option>
					{#each dbDepartments as d}
						<option value={d.name}>{d.name}</option>
					{/each}
				</select>
			</div>

			<!-- Ward & Bed -->
			<div class="grid grid-cols-2 gap-3">
				<div>
					<label class="text-xs text-gray-500 mb-1 block">Ward</label>
					<input type="text" placeholder="e.g., General Ward A" bind:value={admitWard}
						class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
				</div>
				<div>
					<label class="text-xs text-gray-500 mb-1 block">Bed Number</label>
					<input type="text" placeholder="e.g., A-12" bind:value={admitBed}
						class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
				</div>
			</div>

			<!-- Reason -->
			<div>
				<label class="text-xs text-gray-500 mb-1 block">Reason for Admission</label>
				<textarea placeholder="Describe the reason..." bind:value={admitReason} rows="2"
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none resize-none"></textarea>
			</div>

			<!-- Diagnosis -->
			<div>
				<label class="text-xs text-gray-500 mb-1 block">Initial Diagnosis</label>
				<input type="text" placeholder="Diagnosis" bind:value={admitDiagnosis}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
			</div>

			<!-- Notes -->
			<div>
				<label class="text-xs text-gray-500 mb-1 block">Notes (Optional)</label>
				<textarea placeholder="Additional notes..." bind:value={admitNotes} rows="2"
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none resize-none"></textarea>
			</div>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={submitAdmit}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Admit Patient
			</button>
		</div>
	</AquaModal>
{/if}

<!-- Discharge Modal -->
{#if showDischargeModal && actionAdmission}
	<AquaModal onClose={() => showDischargeModal = false}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<LogOut class="w-5 h-5 text-green-600" />
				<span class="font-semibold text-gray-800">Discharge Patient</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<div class="p-3 rounded-xl bg-gray-50 text-sm">
				<p class="text-gray-500">Patient</p>
				<p class="font-semibold text-gray-800">{actionAdmission.patient_name || 'N/A'}</p>
				<p class="text-xs text-gray-500 mt-1">{actionAdmission.department} · {actionAdmission.ward}, {actionAdmission.bed_number}</p>
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Final Diagnosis</label>
				<input type="text" bind:value={dischargeDiagnosis}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Discharge Summary *</label>
				<textarea bind:value={dischargeSummary} rows="3" placeholder="Summary of treatment and outcomes..."
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none resize-none"></textarea>
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Discharge Instructions</label>
				<textarea bind:value={dischargeInstructions} rows="3" placeholder="Post-discharge care instructions..."
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none resize-none"></textarea>
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Follow-up Date</label>
				<input type="date" bind:value={followUpDate}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
			</div>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50"
				style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
				onclick={submitDischarge}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Confirm Discharge
			</button>
		</div>
	</AquaModal>
{/if}

<!-- Transfer Modal -->
{#if showTransferModal && actionAdmission}
	<AquaModal onClose={() => showTransferModal = false}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<ArrowRight class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Transfer Patient</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<div class="p-3 rounded-xl bg-gray-50 text-sm">
				<p class="text-gray-500">Transferring from</p>
				<p class="font-semibold text-gray-800">{actionAdmission.department}</p>
				<p class="text-xs text-gray-500">{actionAdmission.ward}, {actionAdmission.bed_number} · {actionAdmission.attending_doctor}</p>
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Target Department</label>
				<select bind:value={transferDepartment}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-700 outline-none">
					<option value="">Select department</option>
					{#each dbDepartments as d}
						<option value={d.name}>{d.name}</option>
					{/each}
				</select>
			</div>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<label class="text-xs text-gray-500 mb-1 block">New Ward</label>
					<input type="text" placeholder="e.g., ICU" bind:value={transferWard}
						class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
				</div>
				<div>
					<label class="text-xs text-gray-500 mb-1 block">New Bed</label>
					<input type="text" placeholder="e.g., ICU-3" bind:value={transferBed}
						class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
				</div>
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Attending Doctor (Optional)</label>
				<input type="text" placeholder="New attending doctor" bind:value={transferDoctor}
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none" />
			</div>

			<div>
				<label class="text-xs text-gray-500 mb-1 block">Transfer Notes</label>
				<textarea placeholder="Reason for transfer..." bind:value={transferNotes} rows="2"
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm outline-none resize-none"></textarea>
			</div>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={submitTransfer}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Confirm Transfer
			</button>
		</div>
	</AquaModal>
{/if}