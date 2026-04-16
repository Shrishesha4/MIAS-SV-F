<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo, type ClinicPatientInfo, type ClinicPatientSearchResult } from '$lib/api/clinics';
	import { staffApi, type ActiveClinicStudent, type PendingPatient } from '$lib/api/staff';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
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
	let activeStudentsInClinic: ActiveClinicStudent[] = $state([]);
	let loadingActiveStudents = $state(false);

	// Assignment state
	let assigningPatientId = $state<string | null>(null);
	let showAssignModal = $state(false);
	let assignTarget = $state<PendingPatient | null>(null);
	let assignClinicId = $state('');
	let assignStudents = $state<ActiveClinicStudent[]>([]);
	let assignStudentId = $state('');
	let loadingAssignStudents = $state(false);
	let isAssigning = $state(false);

	// Reassign modal state
	let showReassignModal = $state(false);
	let reassignTarget = $state<PendingPatient | null>(null);
	let reassignStudents = $state<ActiveClinicStudent[]>([]);
	let reassignStudentId = $state('');
	let loadingReassignStudents = $state(false);
	let isReassigning = $state(false);

	// Check-in state
	let patientIdInput = $state('');
	let lookupError = $state('');
	let isSearching = $state(false);

	// Tabs & filtering
	let activeTab = $state<'waiting' | 'inprogress' | 'completed'>('waiting');
	let searchFilter = $state('');
	// Initialize from localStorage synchronously so $effect never overwrites a saved 'true'
	let autoAssign = $state(browser ? localStorage.getItem('reception_autoAssign') === 'true' : false);

	// Check-in two-step: search result preview
	let searchedPatient = $state<ClinicPatientSearchResult | null>(null);
	let isCheckingIn = $state(false);

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

	async function loadActiveStudents() {
		if (!selectedClinic || !selectedClinicAllowsWalkIn) {
			activeStudentsInClinic = [];
			return;
		}
		loadingActiveStudents = true;
		try {
			activeStudentsInClinic = await staffApi.getActiveStudents(selectedClinic.id);
		} catch (err) {
			console.error('Failed to load active students', err);
			activeStudentsInClinic = [];
		} finally {
			loadingActiveStudents = false;
		}
	}

	async function handleAutoAssignPendingPatient(patient: PendingPatient) {
		if (!patient.clinic_id) {
			toastStore.addToast('Patient has no allocated clinic. Choose a clinic and student manually.', 'warning');
			await openAssignModal(patient);
			return;
		}
		assigningPatientId = patient.id;
		try {
			const result = await staffApi.autoAssignPatient(patient.id, patient.clinic_id);
			toastStore.addToast(`${patient.name} assigned to ${result.student_name}`, 'success');
			await loadPendingPatients();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'No checked-in students available in the allotted clinic. Choose one manually.', 'warning');
			await openAssignModal(patient);
		} finally {
			assigningPatientId = null;
		}
	}

	async function loadAssignStudentsForClinic(clinicId: string) {
		if (!clinicId) {
			assignStudents = [];
			assignStudentId = '';
			return;
		}
		loadingAssignStudents = true;
		try {
			assignStudents = await staffApi.getActiveStudents(clinicId);
			assignStudentId = assignStudents[0]?.id || '';
		} catch (err) {
			assignStudents = [];
			assignStudentId = '';
			toastStore.addToast('Could not load active students for the selected clinic', 'error');
		} finally {
			loadingAssignStudents = false;
		}
	}

	async function openAssignModal(patient: PendingPatient) {
		assignTarget = patient;
		assignClinicId = patient.clinic_id || selectedClinic?.id || clinics[0]?.id || '';
		assignStudents = [];
		assignStudentId = '';
		showAssignModal = true;
		if (!assignClinicId) {
			toastStore.addToast('No clinic is available for assignment', 'error');
			return;
		}
		await loadAssignStudentsForClinic(assignClinicId);
	}

	async function handleAssignPatient() {
		if (!assignTarget || !assignClinicId || !assignStudentId) {
			return;
		}
		isAssigning = true;
		try {
			const result = await staffApi.assignToStudent({
				patient_id: assignTarget.id,
				student_id: assignStudentId,
				clinic_id: assignClinicId,
			});
			toastStore.addToast(`${assignTarget.name} assigned to ${result.student_name}`, 'success');
			showAssignModal = false;
			assignTarget = null;
			await loadPendingPatients();
			await loadClinicPatients();
			await loadActiveStudents();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Assignment failed', 'error');
		} finally {
			isAssigning = false;
		}
	}

	async function openReassignModal(patient: PendingPatient) {
		if (!patient.clinic_id) {
			toastStore.addToast('Patient has no allocated clinic — cannot reassign', 'error');
			return;
		}
		reassignTarget = patient;
		reassignStudentId = patient.assigned_student_id || '';
		reassignStudents = [];
		showReassignModal = true;
		loadingReassignStudents = true;
		try {
			reassignStudents = await staffApi.getActiveStudents(patient.clinic_id);
			if (!reassignStudentId && reassignStudents.length > 0) {
				reassignStudentId = reassignStudents[0].id;
			}
		} catch (err) {
			toastStore.addToast('Could not load active students for this clinic', 'error');
		} finally {
			loadingReassignStudents = false;
		}
	}

	async function handleReassign() {
		if (!reassignTarget || !reassignStudentId) return;
		isReassigning = true;
		try {
			const result = await staffApi.reassignPatient(reassignTarget.id, reassignStudentId);
			toastStore.addToast(`${reassignTarget.name} reassigned to ${result.student_name}`, 'success');
			showReassignModal = false;
			reassignTarget = null;
			await loadPendingPatients();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Reassignment failed', 'error');
		} finally {
			isReassigning = false;
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

	async function handleSearch() {
		if (!patientIdInput.trim()) return;
		if (clinics.length === 0) { lookupError = 'No clinics available.'; return; }
		isSearching = true;
		lookupError = '';
		searchedPatient = null;
		try {
			const results = await clinicsApi.searchPatient(clinics[0].id, patientIdInput.trim());
			if (results.length === 0) {
				lookupError = 'No patient found with that ID or name.';
			} else {
				const p = results[0];
				if (!p.clinic_id) {
					lookupError = 'Patient has no allocated clinic. Please assign one first.';
				} else {
					searchedPatient = p;
				}
			}
		} catch (err: any) {
			lookupError = err?.response?.data?.detail || 'Search failed.';
		} finally {
			isSearching = false;
		}
	}

	async function handleCheckIn() {
		if (!searchedPatient) return;
		isCheckingIn = true;
		try {
			const result = await clinicsApi.checkInPatient(searchedPatient.clinic_id!, { patient_id: searchedPatient.id });
			toastStore.addToast(result.message || `${searchedPatient.name} checked in to ${searchedPatient.clinic_name || 'their clinic'}`, 'success');
			if (autoAssign) {
				try {
					const assignResult = await staffApi.autoAssignPatient(searchedPatient.id, searchedPatient.clinic_id!);
					toastStore.addToast(`Assigned to ${assignResult.student_name}`, 'success');
				} catch (assignErr: any) {
					toastStore.addToast(assignErr?.response?.data?.detail || 'Auto-assign failed', 'warning');
				}
			}
			patientIdInput = '';
			searchedPatient = null;
			lookupError = '';
			await loadClinicPatients();
			await loadPendingPatients();
			await loadActiveStudents();
		} catch (err: any) {
			lookupError = err?.response?.data?.detail || 'Failed to check in patient.';
			toastStore.addToast(lookupError, 'error');
		} finally {
			isCheckingIn = false;
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
				await loadActiveStudents();
			}
			await loadPendingPatients();
		} catch (err) {
			console.error('Failed to load clinics', err);
		} finally {
			loading = false;
		}
	});

	// Persist autoAssign to localStorage
	$effect(() => {
		localStorage.setItem('reception_autoAssign', String(autoAssign));
	});

	// Auto-refresh every 15s
	$effect(() => {
		if (loading || !selectedClinic) return;
		const interval = setInterval(() => {
			loadClinicPatients();
			loadPendingPatients();
			loadActiveStudents();
		}, 15000);
		return () => clearInterval(interval);
	});

	// Note: autoAssign now uses patient's allocated clinic, not selected chip,
	// so we don't disable it based on selectedClinic.access_mode anymore
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

		<!-- Pending Patients Section -->
		{#if pendingPatients.length > 0}
			{@const unassigned = pendingPatients.filter(p => !p.has_student_assignment && !p.has_appointment && !p.has_admission)}
			{@const assigned = pendingPatients.filter(p => p.has_student_assignment)}
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
						{#if unassigned.length === 0 && assigned.length === 0}
							<p class="text-xs text-gray-400 text-center py-2">No pending patients</p>
						{/if}

						{#each unassigned as patient}
							<div class="overflow-hidden"
								style="background-color: white;
									   border-radius: 8px;
									   box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
									   border: 1px solid rgba(0,0,0,0.07);">
								<div class="px-3 py-2.5">
									<div class="flex items-center gap-2">
										<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
										<div class="min-w-0 flex-1">
											<p class="text-xs font-semibold text-gray-900 truncate">{patient.name}</p>
											<p class="text-[10px] text-gray-400 truncate">
												ID: {patient.patient_id}
												{#if patient.age} · Age: {patient.age}{/if}
											</p>
											<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
											<p class="text-[9px] text-gray-400">
												Registered: {new Date(patient.registered_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
											</p>
											{#if patient.clinic_name}
												<p class="text-[9px] font-medium" style="color: #2563eb;">{patient.clinic_name}</p>
											{:else}
												<p class="text-[9px] font-medium text-amber-600">No clinic allocated yet</p>
											{/if}
										</div>
										<span class="px-2 py-0.5 text-[9px] font-bold rounded-full shrink-0"
											style="background: rgba(251,191,36,0.1); color: #d97706;">
											Unassigned
										</span>
									</div>
								</div>
								<div class="px-3 py-1.5"
									style="border-top: 1px solid rgba(0,0,0,0.05); background-color: #fafbfc;">
									<div class="flex gap-2">
										<button
											disabled={assigningPatientId === patient.id}
											class="flex-1 py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer disabled:opacity-60"
											style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
												   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
												   border: 1px solid rgba(0,0,0,0.12);"
											onclick={() => handleAutoAssignPendingPatient(patient)}
										>
											{#if assigningPatientId === patient.id}
												<Loader2 class="w-2.5 h-2.5 mr-1 animate-spin" /> Assigning…
											{:else}
												<Zap class="w-2.5 h-2.5 mr-1" /> Auto Assign
											{/if}
										</button>
										<button
											class="flex-1 py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium cursor-pointer"
											style="background: linear-gradient(to bottom, #f8fafc, #f1f5f9);
												   box-shadow: 0 1px 2px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.8);
												   border: 1px solid rgba(0,0,0,0.1); color: #475569;"
											onclick={() => openAssignModal(patient)}
										>
											<UserPlus class="w-2.5 h-2.5 mr-1" /> Assign Manually
										</button>
									</div>
								</div>
							</div>
						{/each}

						{#if assigned.length > 0}
							<p class="text-[10px] font-semibold text-gray-500 px-1 pt-1">Assigned</p>
							{#each assigned as patient}
								<div class="overflow-hidden"
									style="background-color: #f0fdf4;
										   border-radius: 8px;
										   box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
										   border: 1px solid #86efac;">
									<div class="px-3 py-2.5">
										<div class="flex items-center gap-2">
											<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
											<div class="min-w-0 flex-1">
												<p class="text-xs font-semibold text-gray-900 truncate">{patient.name}</p>
												<p class="text-[10px] text-gray-400 truncate">
													ID: {patient.patient_id}
													{#if patient.age} · Age: {patient.age}{/if}
												</p>
												<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
												{#if patient.clinic_name}
													<p class="text-[9px] font-medium" style="color: #2563eb;">{patient.clinic_name}</p>
												{/if}
											</div>
											<span class="px-2 py-0.5 text-[9px] font-bold rounded-full shrink-0"
												style="background: rgba(16,185,129,0.1); color: #047857;">
												{patient.assigned_student_name ? `→ ${patient.assigned_student_name}` : '✓ Assigned'}
											</span>
										</div>
									</div>
									<div class="px-3 py-1.5"
										style="border-top: 1px solid rgba(0,0,0,0.05); background-color: #f0fdf4;">
										<button
											class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium cursor-pointer"
											style="background: linear-gradient(to bottom, #f8fafc, #f1f5f9);
												   box-shadow: 0 1px 2px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.8);
												   border: 1px solid rgba(0,0,0,0.1); color: #475569;"
											onclick={() => openReassignModal(patient)}
										>
											<UserPlus class="w-2.5 h-2.5 mr-1" /> Reassign
										</button>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Auto-Assign Toggle -->
		<div class="px-4 py-3 flex items-center justify-between"
			style="background-color: {autoAssign ? '#f0fdf4' : 'white'};
				   border-radius: 10px;
				   border: 1px solid {autoAssign ? '#86efac' : 'rgba(0,0,0,0.1)'};
				   box-shadow: 0 1px 3px rgba(0,0,0,0.08);
				   transition: all 0.2s ease;">
			<div class="flex items-center">
				<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3"
					style="background: {autoAssign ? 'linear-gradient(to bottom, #10b981, #059669)' : 'linear-gradient(to bottom, #e5e7eb, #d1d5db)'};
						   box-shadow: 0 1px 2px rgba(0,0,0,0.15); transition: all 0.2s ease;">
					<Zap class="w-3.5 h-3.5 {autoAssign ? 'text-white' : 'text-gray-500'}" />
				</div>
				<div>
					<p class="text-xs font-semibold text-gray-800">Auto-Assign on Check-In</p>
					<p class="text-[10px] text-gray-500">
						{#if autoAssign}
							Patients will be auto-assigned to their clinic's students
						{:else}
							Manual assignment required
						{/if}
					</p>
				</div>
			</div>
			<button
				aria-label="Toggle auto-assign"
				class="relative w-11 h-6 rounded-full transition-all duration-200 cursor-pointer"
				style="background: {autoAssign ? 'linear-gradient(to right, #10b981, #059669)' : '#d1d5db'};
					   box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);"
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
					<span class="text-[9px] font-bold px-2 py-0.5 rounded-full text-green-700 flex items-center gap-0.5"
						style="background-color: #dcfce7; border: 1px solid #86efac;">
						<Zap class="w-2 h-2" /> AUTO-ASSIGN ON
					</span>
				{/if}
			</div>
			<div class="p-4 space-y-3">
				<!-- Step 1: Search -->
				<div class="flex gap-2">
					<div class="flex-1 flex items-center px-3 py-2.5"
						style="border: 1px solid rgba(0,0,0,0.2); border-radius: 8px;
							   background-color: rgba(255,255,255,0.8);
							   box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);">
						<Search class="w-3.5 h-3.5 text-gray-400 mr-2 shrink-0" />
						<input type="text"
							id="patient-id-input"
							placeholder="Patient ID or name (e.g. PT20260413…)"
							class="flex-1 outline-none text-sm text-gray-700 bg-transparent"
							bind:value={patientIdInput}
							oninput={() => { searchedPatient = null; lookupError = ''; }}
							onkeydown={(e) => { if (e.key === 'Enter') handleSearch(); }}
						/>
						{#if patientIdInput}
							<button class="cursor-pointer ml-1" onclick={() => { patientIdInput = ''; searchedPatient = null; lookupError = ''; }}>
								<X class="w-3.5 h-3.5 text-gray-400" />
							</button>
						{/if}
					</div>
					<button
						class="px-4 py-2.5 rounded-lg flex items-center justify-center text-xs font-semibold text-white cursor-pointer disabled:opacity-50"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
							   box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);
							   border: 1px solid rgba(0,0,0,0.15); min-width: 44px;"
						disabled={!patientIdInput.trim() || isSearching}
						onclick={handleSearch}
					>
						{#if isSearching}
							<Loader2 class="w-3.5 h-3.5 animate-spin" />
						{:else}
							<Search class="w-3.5 h-3.5" />
						{/if}
					</button>
				</div>

				<!-- Error -->
				{#if lookupError}
					<div class="flex items-center px-3 py-2.5 rounded-lg"
						style="background-color: #fef2f2; border: 1px solid #fecaca;">
						<AlertCircle class="w-3.5 h-3.5 text-red-500 mr-2 shrink-0" />
						<p class="text-xs text-red-700">{lookupError}</p>
					</div>
				{/if}

				<!-- Step 2: Patient preview card + Check In button -->
				{#if searchedPatient}
					<div class="rounded-xl overflow-hidden"
						style="border: 1.5px solid #bfdbfe; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);">
						<div class="px-4 py-3 flex items-center gap-3">
							<PatientInsuranceAvatar name={searchedPatient.name} src={searchedPatient.photo} size="sm" insurancePolicies={searchedPatient.insurance_policies} patientCategory={searchedPatient.category} patientCategoryColorPrimary={searchedPatient.category_color_primary} patientCategoryColorSecondary={searchedPatient.category_color_secondary} />
							<div class="flex-1 min-w-0">
								<p class="text-sm font-bold text-gray-900 truncate">{searchedPatient.name}</p>
								<p class="text-[11px] text-gray-500 truncate">{searchedPatient.patient_id}</p>
								<InsuranceTypeBadges insurancePolicies={searchedPatient.insurance_policies} compact maxVisible={2} />
								{#if searchedPatient.clinic_name}
									<p class="text-[11px] font-semibold mt-0.5" style="color: #2563eb;">
										<Building class="w-2.5 h-2.5 inline mr-0.5" />{searchedPatient.clinic_name}
									</p>
								{/if}
							</div>
							<CheckCircle class="w-5 h-5 text-blue-400 shrink-0" />
						</div>
						<div class="px-4 pb-3">
							<button
								class="w-full py-2.5 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold text-white cursor-pointer disabled:opacity-50"
								style="background: linear-gradient(to bottom, #10b981, #059669);
									   box-shadow: 0 2px 6px rgba(5,150,105,0.35), inset 0 1px 0 rgba(255,255,255,0.25);
									   border: 1px solid rgba(0,0,0,0.12);"
								disabled={isCheckingIn}
								onclick={handleCheckIn}
							>
								{#if isCheckingIn}
									<Loader2 class="w-4 h-4 animate-spin" /> Checking in…
								{:else}
									<UserCheck class="w-4 h-4" /> Check In{autoAssign ? ' & Auto-Assign' : ''}
								{/if}
							</button>
						</div>
					</div>
				{:else if !isSearching && !lookupError}
					<p class="text-xs text-gray-400 text-center">Search by patient ID or name, then confirm check-in.</p>
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
							<PatientInsuranceAvatar name={patient.patient_name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
							<div class="min-w-0 flex-1">
								<p class="text-xs font-semibold text-gray-900 truncate">{patient.patient_name}</p>
								<p class="text-[10px] text-gray-400 truncate">
									ID: {patient.patient_id} · {patient.appointment_time}
								</p>
								<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
							</div>
							<span class="px-2 py-0.5 text-[10px] font-bold rounded-full shrink-0"
								style="background: {patient.status === 'Completed' ? 'rgba(34,197,94,0.1)' : patient.status === 'In Progress' ? 'rgba(59,130,246,0.1)' : 'rgba(251,191,36,0.1)'};
									   color: {patient.status === 'Completed' ? '#16a34a' : patient.status === 'In Progress' ? '#2563eb' : '#d97706'};">
								{patient.status}
							</span>
						</div>
						{#if patient.provider_name || patient.assigned_student_name}
							<div class="flex items-center gap-1 ml-9 text-[10px] text-gray-500">
								<GraduationCap class="w-2.5 h-2.5 text-green-600" />
								<span class="text-green-700 font-medium">{patient.assigned_student_name || patient.provider_name}</span>
							</div>
						{/if}
					</div>
					<div class="px-3 py-1.5"
						style="border-top: 1px solid rgba(0,0,0,0.05); background-color: #fafbfc;">
						{#if patient.source === 'appointment' && (patient.status === 'Scheduled' || patient.status === 'Checked In')}
							<button
								class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer"
								style="background: linear-gradient(to bottom, #10b981, #059669);
									   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
									   border: 1px solid rgba(0,0,0,0.12);"
								onclick={() => updateStatus(patient.id, 'In Progress')}
							>
								Start Visit
							</button>
						{:else if patient.source === 'appointment' && patient.status === 'In Progress'}
							<button
								class="w-full py-1.5 rounded-md flex items-center justify-center text-[10px] font-medium text-white cursor-pointer"
								style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
									   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
									   border: 1px solid rgba(0,0,0,0.12);"
								onclick={() => updateStatus(patient.id, 'Completed')}
							>
								<CheckCircle class="w-2.5 h-2.5 mr-1" /> Complete
							</button>
						{:else if patient.source === 'assignment'}
							<p class="text-[10px] text-center text-emerald-600 py-0.5 font-medium">Following assigned student in clinic</p>
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

<!-- Reassign Patient Modal -->
{#if showReassignModal && reassignTarget}
	<AquaModal title="Reassign Patient" onclose={() => { showReassignModal = false; reassignTarget = null; }}>
		<div class="space-y-3 px-1">
			<div>
				<p class="text-xs font-semibold text-gray-800">{reassignTarget.name}</p>
				<p class="text-[10px] text-gray-500">{reassignTarget.patient_id} · {reassignTarget.clinic_name || 'Unknown Clinic'}</p>
				{#if reassignTarget.assigned_student_name}
					<p class="text-[10px] text-gray-500 mt-0.5">Currently: <span class="font-medium text-green-700">{reassignTarget.assigned_student_name}</span></p>
				{/if}
			</div>

			{#if loadingReassignStudents}
				<div class="flex items-center justify-center py-4">
					<div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if reassignStudents.length === 0}
				<p class="text-xs text-red-500 text-center py-2">No students currently checked in to {reassignTarget.clinic_name || 'this clinic'}.</p>
			{:else}
				<div>
					<p class="text-[10px] font-medium text-gray-600 mb-1">Select Student</p>
					<select
						bind:value={reassignStudentId}
						class="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-white"
						style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
					>
						{#each reassignStudents as s}
							<option value={s.id}>{s.name} ({s.assigned_patient_count} patients)</option>
						{/each}
					</select>
				</div>
				<button
					disabled={isReassigning || !reassignStudentId}
					onclick={handleReassign}
					class="w-full py-2 rounded-lg text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
						   box-shadow: 0 1px 3px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.25);"
				>
					{#if isReassigning}
						<Loader2 class="w-3 h-3 inline mr-1 animate-spin" /> Reassigning…
					{:else}
						Confirm Reassignment
					{/if}
				</button>
			{/if}
		</div>
	</AquaModal>
{/if}

{#if showAssignModal && assignTarget}
	<AquaModal title="Assign Patient" onclose={() => { showAssignModal = false; assignTarget = null; }}>
		<div class="space-y-3 px-1">
			<div>
				<p class="text-xs font-semibold text-gray-800">{assignTarget.name}</p>
				<p class="text-[10px] text-gray-500">{assignTarget.patient_id}</p>
			</div>

			<div>
				<p class="text-[10px] font-medium text-gray-600 mb-1">Clinic</p>
				<select
					bind:value={assignClinicId}
					onchange={(event) => loadAssignStudentsForClinic((event.currentTarget as HTMLSelectElement).value)}
					class="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-white"
					style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
				>
					{#each clinics as clinic}
						<option value={clinic.id}>{clinic.name}</option>
					{/each}
				</select>
			</div>

			{#if loadingAssignStudents}
				<div class="flex items-center justify-center py-4">
					<div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if assignStudents.length === 0}
				<p class="text-xs text-red-500 text-center py-2">No students are currently checked in to the selected clinic.</p>
			{:else}
				<div>
					<p class="text-[10px] font-medium text-gray-600 mb-1">Student</p>
					<select
						bind:value={assignStudentId}
						class="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-white"
						style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
					>
						{#each assignStudents as student}
							<option value={student.id}>{student.name} ({student.assigned_patient_count} patients)</option>
						{/each}
					</select>
				</div>
				<button
					disabled={isAssigning || !assignStudentId}
					onclick={handleAssignPatient}
					class="w-full py-2 rounded-lg text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
						   box-shadow: 0 1px 3px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.25);"
				>
					{#if isAssigning}
						<Loader2 class="w-3 h-3 inline mr-1 animate-spin" /> Assigning…
					{:else}
						Confirm Assignment
					{/if}
				</button>
			{/if}
		</div>
	</AquaModal>
{/if}
