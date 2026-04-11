<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo, type ClinicPatientInfo } from '$lib/api/clinics';
	import { staffApi, type PendingPatient } from '$lib/api/staff';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import { toastStore } from '$lib/stores/toast';
	import {
		Users, UserCheck, Clock, Calendar, Building, Search, X,
		AlertCircle, CheckCircle, Loader2, Zap, GraduationCap,
		Crown, ChevronDown, Square, CheckSquare, UserPlus
	} from 'lucide-svelte';

	function clinicAccessModeLabel(accessMode: ClinicInfo['access_mode']) {
		return accessMode === 'APPOINTMENT_ONLY' ? 'Appointment Only' : 'Walk-In';
	}

	function clinicAllowsWalkIn(clinic: ClinicInfo | null) {
		return clinic?.access_mode !== 'APPOINTMENT_ONLY';
	}

	const auth = get(authStore);
	let loading = $state(true);

	// Clinic data
	let clinics: ClinicInfo[] = $state([]);
	let selectedClinic: ClinicInfo | null = $state(null);
	let clinicPatients: ClinicPatientInfo[] = $state([]);

	// Pending patients
	let pendingPatients: PendingPatient[] = $state([]);
	let showPendingSection = $state(true);

	// Assignment modal
	let showAssignModal = $state(false);
	let selectedPatientForAssign: PendingPatient | null = $state(null);
	let assignClinicId = $state('');
	let assignDate = $state('');
	let assignNotes = $state('');
	let isAssigning = $state(false);

	// Check-in state
	let patientIdInput = $state('');
	let lookupError = $state('');
	let isSearching = $state(false);

	// Tabs & filtering
	let activeTab = $state<'waiting' | 'inprogress' | 'completed'>('waiting');
	let searchFilter = $state('');
	let autoAssign = $state(false);

	// Stats
	const waitingCount = $derived(clinicPatients.filter(p => p.status === 'Scheduled' || p.status === 'Checked In').length);
	const inProgressCount = $derived(clinicPatients.filter(p => p.status === 'In Progress').length);
	const completedCount = $derived(clinicPatients.filter(p => p.status === 'Completed').length);
	const totalCount = $derived(clinicPatients.length);
	const selectedClinicAllowsWalkIn = $derived(clinicAllowsWalkIn(selectedClinic));

	const filteredPatients = $derived.by(() => {
		let list = clinicPatients;
		if (activeTab === 'waiting') list = list.filter(p => p.status === 'Scheduled' || p.status === 'Checked In');
		else if (activeTab === 'inprogress') list = list.filter(p => p.status === 'In Progress');
		else list = list.filter(p => p.status === 'Completed');

		if (searchFilter.trim()) {
			const q = searchFilter.toLowerCase();
			list = list.filter(p =>
				p.patient_name.toLowerCase().includes(q) ||
				p.patient_id.toLowerCase().includes(q)
			);
		}
		return list;
	});

	async function loadClinicPatients() {
		if (!selectedClinic) return;
		try {
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			console.error('Failed to load clinic patients', err);
		}
	}

	async function loadPendingPatients() {
		try {
			pendingPatients = await staffApi.getPendingPatients();
		} catch (err) {
			console.error('Failed to load pending patients', err);
		}
	}

	function openAssignModal(patient: PendingPatient) {
		selectedPatientForAssign = patient;
		assignClinicId = selectedClinic?.id || '';
		assignDate = new Date().toISOString().split('T')[0];
		assignNotes = '';
		showAssignModal = true;
	}

	async function handleAssignToClinic() {
		if (!selectedPatientForAssign || !assignClinicId || !assignDate) return;
		isAssigning = true;
		try {
			await staffApi.assignToClinic({
				patient_id: selectedPatientForAssign.id,
				clinic_id: assignClinicId,
				scheduled_date: assignDate,
				notes: assignNotes || undefined
			});
			toastStore.addToast(`${selectedPatientForAssign.name} assigned to clinic`, 'success');
			showAssignModal = false;
			await loadPendingPatients();
			await loadClinicPatients();
		} catch (err: any) {
			console.error('Failed to assign patient', err);
			toastStore.addToast(err?.response?.data?.detail || 'Failed to assign patient', 'error');
		} finally {
			isAssigning = false;
		}
	}

	async function updateStatus(appointmentId: string, status: string) {
		if (!selectedClinic) return;
		try {
			await clinicsApi.updateAppointmentStatus(selectedClinic.id, appointmentId, status);
			await loadClinicPatients();
			toastStore.addToast(`Status updated to ${status}`, 'success');
		} catch (err) {
			console.error('Failed to update status', err);
			toastStore.addToast('Failed to update status', 'error');
		}
	}

	async function handleCheckIn() {
		if (!selectedClinic || !patientIdInput.trim()) return;
		if (selectedClinic.access_mode === 'APPOINTMENT_ONLY') {
			lookupError = 'This clinic accepts appointments only.';
			toastStore.addToast(lookupError, 'warning');
			return;
		}
		isSearching = true;
		lookupError = '';
		try {
			const results = await clinicsApi.searchPatient(selectedClinic.id, patientIdInput.trim());
			if (results.length === 0) {
				lookupError = 'No patient found with that ID or name.';
				isSearching = false;
				return;
			}
			const patient = results[0];
			const result = await clinicsApi.checkInPatient(selectedClinic.id, { patient_id: patient.id });
			toastStore.addToast(result.message || `${patient.name} checked in successfully`, 'success');
			
			// Auto-assign to student if toggle is enabled
			if (autoAssign) {
				try {
					const assignResult = await staffApi.autoAssignPatient(patient.id, selectedClinic.id);
					toastStore.addToast(`Assigned to ${assignResult.student_name}`, 'success');
				} catch (assignErr: any) {
					// Don't fail the check-in, just warn about auto-assign failure
					const detail = assignErr?.response?.data?.detail || 'Auto-assign failed';
					toastStore.addToast(detail, 'warning');
				}
			}
			
			patientIdInput = '';
			lookupError = '';
			await loadClinicPatients();
		} catch (err: any) {
			lookupError = err?.response?.data?.detail || 'Failed to check in patient.';
			toastStore.addToast(lookupError, 'error');
		} finally {
			isSearching = false;
		}
	}

	onMount(async () => {
		if (auth.role !== 'RECEPTION' && auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		try {
			clinics = await clinicsApi.listClinics();
			if (clinics.length > 0) {
				selectedClinic = clinics[0];
				await loadClinicPatients();
			}
			await loadPendingPatients();
		} catch (err) {
			console.error('Failed to load clinics', err);
		} finally {
			loading = false;
		}
	});

	// Auto-refresh every 15s
	$effect(() => {
		if (loading || !selectedClinic) return;
		const interval = setInterval(() => {
			loadClinicPatients();
			loadPendingPatients();
		}, 15000);
		return () => clearInterval(interval);
	});

	$effect(() => {
		if (selectedClinic?.access_mode === 'APPOINTMENT_ONLY' && autoAssign) {
			autoAssign = false;
		}
	});
</script>

<div class="px-3 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Clinic Info Header -->
		<div class="overflow-hidden"
			style="background-color: white; border-radius: 10px;
				   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24), 0 0 0 1px rgba(0,0,0,0.05);
				   border: 1px solid rgba(0,0,0,0.1);">
			<div class="px-4 py-3"
				style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
					   box-shadow: inset 0 1px 0 rgba(255,255,255,0.3);">
				<div class="flex items-center justify-between">
					<div class="flex items-center">
						<div class="w-10 h-10 rounded-full flex items-center justify-center mr-3"
							style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);">
							<Building class="w-5 h-5 text-white" />
						</div>
						<div>
							<h2 class="text-white font-semibold text-sm">{selectedClinic?.name || 'No Clinic'}</h2>
							<p class="text-blue-100 text-xs">{selectedClinic?.location || ''}</p>
							{#if selectedClinic}
								<p class="mt-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-blue-100">{clinicAccessModeLabel(selectedClinic.access_mode)}</p>
							{/if}
						</div>
					</div>
					<div class="text-right">
						<p class="text-blue-100 text-xs">Today</p>
						<p class="text-white text-xs font-medium">9:00 AM – 1:00 PM</p>
					</div>
				</div>
			</div>
			<div class="px-4 py-2.5 flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="text-center">
						<p class="text-lg font-bold text-blue-600">{totalCount}</p>
						<p class="text-[10px] text-gray-500 uppercase tracking-wide">Total</p>
					</div>
					<div class="w-px h-8 bg-gray-200"></div>
					<div class="text-center">
						<p class="text-lg font-bold text-amber-600">{waitingCount}</p>
						<p class="text-[10px] text-gray-500 uppercase tracking-wide">Waiting</p>
					</div>
					<div class="w-px h-8 bg-gray-200"></div>
					<div class="text-center">
						<p class="text-lg font-bold text-green-600">{completedCount}</p>
						<p class="text-[10px] text-gray-500 uppercase tracking-wide">Done</p>
					</div>
				</div>
				<div class="flex items-center text-xs text-gray-500">
					<Calendar class="w-3 h-3 mr-1" />
					{new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
				</div>
			</div>
		</div>

		<!-- Clinic Selector (if multiple) -->
		{#if clinics.length > 1}
			<div class="flex gap-2 overflow-x-auto pb-1">
				{#each clinics as clinic}
					<button
						class="shrink-0 px-4 py-2 rounded-full text-xs font-medium cursor-pointer transition-all"
						style="background: {selectedClinic?.id === clinic.id ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : 'linear-gradient(to bottom, #f8fafc, #f1f5f9)'};
							   color: {selectedClinic?.id === clinic.id ? 'white' : '#475569'};
							   border: 1px solid {selectedClinic?.id === clinic.id ? '#2563eb' : '#e2e8f0'};
							   box-shadow: {selectedClinic?.id === clinic.id ? '0 2px 4px rgba(37,99,235,0.3)' : 'none'};"
						onclick={async () => { selectedClinic = clinic; await loadClinicPatients(); }}
					>
						<div class="flex flex-col items-start gap-0.5">
							<span>{clinic.name}</span>
							<span class="text-[9px] uppercase tracking-[0.14em] opacity-80">{clinicAccessModeLabel(clinic.access_mode)}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}

		<!-- Pending Patients Section -->
		{#if pendingPatients.length > 0}
			<div class="overflow-hidden"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<button
					class="w-full px-4 py-2.5 flex items-center justify-between cursor-pointer"
					style="background-image: linear-gradient(to bottom, #fef3c7, #fde68a);
						   box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
						   border-bottom: 1px solid rgba(0,0,0,0.08);"
					onclick={() => showPendingSection = !showPendingSection}
				>
					<div class="flex items-center">
						<UserPlus class="w-3.5 h-3.5 text-amber-700 mr-2" />
						<h3 class="text-sm font-semibold text-gray-800" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
							Pending Patients
						</h3>
						<span class="ml-2 text-[10px] font-bold px-2 py-0.5 rounded-full text-amber-800"
							style="background-color: rgba(251,191,36,0.2); border: 1px solid rgba(251,191,36,0.4);">
							{pendingPatients.length}
						</span>
					</div>
					<ChevronDown class="w-4 h-4 text-gray-600 transition-transform" style="transform: rotate({showPendingSection ? 180 : 0}deg);" />
				</button>

				{#if showPendingSection}
					<div class="p-3 space-y-2">
						{#each pendingPatients as patient}
							<div class="overflow-hidden"
								style="background-color: {patient.has_appointment || patient.has_admission ? '#f0fdf4' : 'white'};
									   border-radius: 8px;
									   box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
									   border: 1px solid {patient.has_appointment || patient.has_admission ? '#86efac' : 'rgba(0,0,0,0.07)'};">
								<div class="px-3 py-2.5">
									<div class="flex items-center gap-2">
										<Avatar name={patient.name} size="sm" />
										<div class="min-w-0 flex-1">
											<p class="text-xs font-semibold text-gray-900 truncate">{patient.name}</p>
											<p class="text-[10px] text-gray-400 truncate">
												ID: {patient.patient_id}
												{#if patient.age}
													· Age: {patient.age}
												{/if}
											</p>
											<p class="text-[9px] text-gray-400">
												Registered: {new Date(patient.registered_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
											</p>
										</div>
										{#if patient.has_appointment}
											<span class="px-2 py-0.5 text-[9px] font-bold rounded-full shrink-0"
												style="background: rgba(34,197,94,0.1); color: #16a34a;">
												✓ Clinic
											</span>
										{:else if patient.has_admission}
											<span class="px-2 py-0.5 text-[9px] font-bold rounded-full shrink-0"
												style="background: rgba(59,130,246,0.1); color: #2563eb;">
												✓ Ward
											</span>
										{:else}
											<span class="px-2 py-0.5 text-[9px] font-bold rounded-full shrink-0"
												style="background: rgba(251,191,36,0.1); color: #d97706;">
												Unassigned
											</span>
										{/if}
									</div>
								</div>
								{#if !patient.has_appointment && !patient.has_admission}
									<div class="px-3 py-1.5"
										style="border-top: 1px solid rgba(0,0,0,0.05); background-color: #fafbfc;">
										<button
											class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
												   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
												   border: 1px solid rgba(0,0,0,0.12);"
											onclick={() => openAssignModal(patient)}
										>
											<Building class="w-2.5 h-2.5 mr-1" /> Assign to Clinic
										</button>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Auto-Assign Toggle -->
		<div class="px-4 py-3 flex items-center justify-between"
			style="background-color: {autoAssign ? '#f0fdf4' : selectedClinicAllowsWalkIn ? 'white' : '#f8fafc'};
				   border-radius: 10px;
				   border: 1px solid {autoAssign ? '#86efac' : selectedClinicAllowsWalkIn ? 'rgba(0,0,0,0.1)' : '#cbd5e1'};
				   box-shadow: 0 1px 3px rgba(0,0,0,0.08);
				   transition: all 0.2s ease;">
			<div class="flex items-center">
				<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3"
					style="background: {autoAssign ? 'linear-gradient(to bottom, #10b981, #059669)' : selectedClinicAllowsWalkIn ? 'linear-gradient(to bottom, #e5e7eb, #d1d5db)' : 'linear-gradient(to bottom, #e2e8f0, #cbd5e1)'};
						   box-shadow: 0 1px 2px rgba(0,0,0,0.15); transition: all 0.2s ease;">
					<Zap class="w-3.5 h-3.5 {autoAssign ? 'text-white' : 'text-gray-500'}" />
				</div>
				<div>
					<p class="text-xs font-semibold text-gray-800">Auto-Assign on Check-In</p>
					<p class="text-[10px] text-gray-500">
						{#if !selectedClinicAllowsWalkIn}
							Unavailable for appointment-only clinics
						{:else if autoAssign}
							New patients will be auto-assigned
						{:else}
							Manual assignment required
						{/if}
					</p>
				</div>
			</div>
			<button
				aria-label="Toggle auto-assign"
				class="relative w-11 h-6 rounded-full transition-all duration-200 cursor-pointer"
				style="background: {autoAssign ? 'linear-gradient(to right, #10b981, #059669)' : selectedClinicAllowsWalkIn ? '#d1d5db' : '#cbd5e1'};
					   box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);"
				disabled={!selectedClinicAllowsWalkIn}
				onclick={() => autoAssign = !autoAssign}
			>
				<div class="absolute top-0.5 w-5 h-5 rounded-full transition-all duration-200"
					style="left: {autoAssign ? '22px' : '2px'};
						   background: linear-gradient(to bottom, #ffffff, #f3f4f6);
						   box-shadow: 0 1px 3px rgba(0,0,0,0.3);">
				</div>
			</button>
		</div>

		<!-- Check In Section -->
		<div class="overflow-hidden"
			style="background-color: white; border-radius: 10px;
				   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				   border: 1px solid rgba(0,0,0,0.1);">
			<div class="px-4 py-2.5 flex items-center justify-between"
				style="background-image: linear-gradient(to bottom, #f8f9fb, #e9eef5);
					   box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
					   border-bottom: 1px solid rgba(0,0,0,0.08);">
				<div class="flex items-center">
					<UserCheck class="w-3.5 h-3.5 text-blue-700 mr-2" />
					<h3 class="text-sm font-semibold text-gray-800" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
						Check In Patient
					</h3>
				</div>
				{#if autoAssign}
					<span class="text-[9px] font-bold px-2 py-0.5 rounded-full text-green-700"
						style="background-color: #dcfce7; border: 1px solid #86efac;">
						<Zap class="w-2 h-2 inline mr-0.5" /> AUTO
					</span>
				{/if}
			</div>
			<div class="p-4">
				{#if selectedClinicAllowsWalkIn}
					<label for="patient-id-input" class="block text-xs font-medium text-gray-600 mb-1.5">Patient ID</label>
					<div class="flex gap-2">
						<div class="flex-1 flex items-center px-3 py-2.5"
							style="border: 1px solid rgba(0,0,0,0.2); border-radius: 8px;
								   background-color: rgba(255,255,255,0.8);
								   box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);">
							<Search class="w-3.5 h-3.5 text-gray-400 mr-2" />
							<input type="text"
								id="patient-id-input"
								placeholder="Enter Patient ID (e.g. PAT-001)"
								class="flex-1 outline-none text-sm text-gray-700 bg-transparent"
								bind:value={patientIdInput}
								onkeydown={(e) => { if (e.key === 'Enter') handleCheckIn(); }}
							/>
							{#if patientIdInput}
								<button class="cursor-pointer" onclick={() => { patientIdInput = ''; lookupError = ''; }}>
									<X class="w-3.5 h-3.5 text-gray-400" />
								</button>
							{/if}
						</div>
						<button
							class="px-4 py-2.5 rounded-lg flex items-center justify-center text-xs font-medium text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
								   box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);
								   border: 1px solid rgba(0,0,0,0.15);"
							disabled={!patientIdInput.trim() || isSearching}
							onclick={handleCheckIn}
						>
							{#if isSearching}
								<Loader2 class="w-3.5 h-3.5 animate-spin" />
							{:else}
								<Search class="w-3.5 h-3.5" />
							{/if}
						</button>
					</div>
				{:else}
					<div class="flex items-start gap-3 rounded-lg px-3 py-3"
						style="background-color: #eff6ff; border: 1px solid #bfdbfe;">
						<Calendar class="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
						<div>
							<p class="text-xs font-semibold text-blue-900">This clinic accepts appointments only.</p>
							<p class="mt-1 text-[11px] text-blue-700">Walk-in check-in is disabled here. Schedule or assign an appointment instead.</p>
						</div>
					</div>
				{/if}
				{#if lookupError}
					<div class="flex items-center px-3 py-2.5 rounded-lg mt-3"
						style="background-color: #fef2f2; border: 1px solid #fecaca;">
						<AlertCircle class="w-3.5 h-3.5 text-red-500 mr-2 shrink-0" />
						<p class="text-xs text-red-700">{lookupError}</p>
					</div>
				{/if}
				{#if !lookupError && !isSearching}
					<p class="text-xs text-gray-400 text-center mt-2">{selectedClinicAllowsWalkIn ? 'Enter a registered patient ID to check them in.' : 'Use the clinic assignment flow for appointment-only clinics.'}</p>
				{/if}
			</div>
		</div>

		<!-- Tabs -->
		<div class="flex p-1"
			style="background-color: rgba(0,0,0,0.06); border-radius: 10px;
				   box-shadow: inset 0 1px 2px rgba(0,0,0,0.08);">
			{#each [
				{ id: 'waiting', label: 'Waiting', count: waitingCount, activeColor: '#92400e' },
				{ id: 'inprogress', label: 'In Progress', count: inProgressCount, activeColor: '#1e40af' },
				{ id: 'completed', label: 'Completed', count: completedCount, activeColor: '#166534' },
			] as tab (tab.id)}
				<button
					class="flex-1 py-2.5 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1 cursor-pointer"
					style="{activeTab === tab.id
						? `background: linear-gradient(to bottom, #ffffff, #f5f5f5); box-shadow: 0 1px 3px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.08); color: ${tab.activeColor};`
						: 'background: transparent; border: 1px solid transparent; color: #6b7280;'}"
					onclick={() => activeTab = tab.id as 'waiting' | 'inprogress' | 'completed'}
				>
					{tab.label} ({tab.count})
				</button>
			{/each}
		</div>

		<!-- Search Bar -->
		<div class="flex items-center px-3 py-2"
			style="border: 1px solid rgba(0,0,0,0.12); border-radius: 8px;
				   background-color: white; box-shadow: inset 0 1px 2px rgba(0,0,0,0.04);">
			<Search class="w-3.5 h-3.5 text-gray-400 mr-2" />
			<input type="text" placeholder="Filter by name or ID..."
				class="flex-1 outline-none text-xs text-gray-600 bg-transparent"
				bind:value={searchFilter}
			/>
			{#if searchFilter}
				<button class="cursor-pointer" onclick={() => searchFilter = ''}>
					<X class="w-3 h-3 text-gray-400" />
				</button>
			{/if}
		</div>

		<!-- Patient List -->
		<div class="space-y-2">
			{#each filteredPatients as patient}
				<div class="overflow-hidden"
					style="background-color: white; border-radius: 8px;
						   box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
						   border: 1px solid rgba(0,0,0,0.07);">
					<div class="px-3 py-2.5">
						<div class="flex items-center gap-2 mb-1">
							<Avatar name={patient.patient_name} size="sm" />
							<div class="min-w-0 flex-1">
								<p class="text-xs font-semibold text-gray-900 truncate">{patient.patient_name}</p>
								<p class="text-[10px] text-gray-400 truncate">
									ID: {patient.patient_id} · {patient.appointment_time}
								</p>
							</div>
							<span class="px-2 py-0.5 text-[10px] font-bold rounded-full shrink-0"
								style="background: {patient.status === 'Completed' ? 'rgba(34,197,94,0.1)' : patient.status === 'In Progress' ? 'rgba(59,130,246,0.1)' : 'rgba(251,191,36,0.1)'};
									   color: {patient.status === 'Completed' ? '#16a34a' : patient.status === 'In Progress' ? '#2563eb' : '#d97706'};">
								{patient.status}
							</span>
						</div>
						{#if patient.provider_name}
							<div class="flex items-center gap-1 ml-9 text-[10px] text-gray-500">
								<GraduationCap class="w-2.5 h-2.5 text-green-600" />
								<span class="text-green-700 font-medium">{patient.provider_name}</span>
							</div>
						{/if}
					</div>
					<div class="px-3 py-1.5"
						style="border-top: 1px solid rgba(0,0,0,0.05); background-color: #fafbfc;">
						{#if patient.status === 'Scheduled' || patient.status === 'Checked In'}
							<button
								class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer"
								style="background: linear-gradient(to bottom, #10b981, #059669);
									   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
									   border: 1px solid rgba(0,0,0,0.12);"
								onclick={() => updateStatus(patient.id, 'In Progress')}
							>
								Start Visit
							</button>
						{:else if patient.status === 'In Progress'}
							<button
								class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer"
								style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
									   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
									   border: 1px solid rgba(0,0,0,0.12);"
								onclick={() => updateStatus(patient.id, 'Completed')}
							>
								<CheckCircle class="w-2.5 h-2.5 mr-1" /> Complete
							</button>
						{:else}
							<p class="text-[10px] text-center text-gray-400 py-0.5">Visit completed</p>
						{/if}
					</div>
				</div>
			{/each}

			{#if filteredPatients.length === 0}
				<div class="text-center py-10"
					style="background-color: white; border-radius: 10px; border: 1px solid rgba(0,0,0,0.08);">
					{#if activeTab === 'waiting'}
						<CheckCircle class="w-7 h-7 mx-auto text-green-400 mb-2" />
						<p class="text-sm text-gray-400">No patients waiting</p>
					{:else if activeTab === 'inprogress'}
						<Clock class="w-7 h-7 mx-auto text-blue-400 mb-2" />
						<p class="text-sm text-gray-400">No patients in progress</p>
					{:else}
						<Users class="w-7 h-7 mx-auto text-gray-300 mb-2" />
						<p class="text-sm text-gray-400">No completed visits yet</p>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Assign to Clinic Modal -->
{#if showAssignModal && selectedPatientForAssign}
	<AquaModal title="Assign Patient to Clinic" onclose={() => showAssignModal = false}>
		<div class="space-y-4">
			<div>
				<p class="text-sm font-semibold text-gray-800 mb-1">{selectedPatientForAssign.name}</p>
				<p class="text-xs text-gray-500">ID: {selectedPatientForAssign.patient_id}</p>
			</div>

			<div>
				<label for="assign-clinic" class="block text-xs font-medium text-gray-600 mb-1.5">Select Clinic</label>
				<div class="relative">
					<select
						id="assign-clinic"
						class="w-full px-3 py-2 text-sm outline-none border rounded-lg bg-white"
						style="border: 1px solid rgba(0,0,0,0.2); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);"
						bind:value={assignClinicId}
					>
						<option value="">-- Select Clinic --</option>
						{#each clinics as clinic}
							<option value={clinic.id}>{clinic.name} ({clinicAccessModeLabel(clinic.access_mode)})</option>
						{/each}
					</select>
				</div>
			</div>

			<div>
				<label for="assign-date" class="block text-xs font-medium text-gray-600 mb-1.5">Appointment Date</label>
				<input
					id="assign-date"
					type="date"
					class="w-full px-3 py-2 text-sm outline-none border rounded-lg"
					style="border: 1px solid rgba(0,0,0,0.2); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);"
					bind:value={assignDate}
				/>
			</div>

			<div>
				<label for="assign-notes" class="block text-xs font-medium text-gray-600 mb-1.5">Notes (optional)</label>
				<textarea
					id="assign-notes"
					rows="3"
					class="w-full px-3 py-2 text-sm outline-none border rounded-lg resize-none"
					style="border: 1px solid rgba(0,0,0,0.2); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);"
					placeholder="Add any notes about the appointment..."
					bind:value={assignNotes}
				></textarea>
			</div>

			<div class="flex gap-2">
				<button
					class="flex-1 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #f3f4f6, #e5e7eb);
						   color: #4b5563; border: 1px solid rgba(0,0,0,0.1);
						   box-shadow: 0 1px 2px rgba(0,0,0,0.1);"
					onclick={() => showAssignModal = false}
					disabled={isAssigning}
				>
					Cancel
				</button>
				<button
					class="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white cursor-pointer flex items-center justify-center"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
						   border: 1px solid rgba(0,0,0,0.12);
						   box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);"
					disabled={!assignClinicId || !assignDate || isAssigning}
					onclick={handleAssignToClinic}
				>
					{#if isAssigning}
						<Loader2 class="w-3.5 h-3.5 animate-spin mr-1" />
						Assigning...
					{:else}
						Assign to Clinic
					{/if}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}
