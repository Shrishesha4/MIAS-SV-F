<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo, type ClinicPatientInfo, type ClinicPatientSearchResult } from '$lib/api/clinics';
	import { staffApi, type ActiveClinicStudent, type PendingPatient } from '$lib/api/staff';
	import PatientGeofenceModal from '$lib/components/geofence/PatientGeofenceModal.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
	import { formatDateIST, formatDateTimeIST } from '$lib/utils/ist';
	import { toastStore } from '$lib/stores/toast';
	import {
		Users, UserCheck, Clock, Calendar, Building, Search, X,
		AlertCircle, CheckCircle, Loader2, Zap, GraduationCap,
		ChevronDown, UserPlus, RefreshCw, ArrowRight, ClipboardList
	} from 'lucide-svelte';

	function clinicAccessModeLabel(accessMode: ClinicInfo['access_mode']) {
		return accessMode === 'APPOINTMENT_ONLY' ? 'Appointment Only' : 'Walk-In';
	}

	function formatRegisteredAt(value: string) {
		return formatDateTimeIST(value, {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
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

	// Geofence modal state
	let showGeofenceModal = $state(false);
	let gfPatientId = $state('');
	let gfPatientName = $state('');
	let gfClinicId = $state('');
	let pendingGeofenceCallback = $state<((proofId: string) => Promise<void>) | null>(null);

	function openGeofenceGate(
		patientId: string,
		patientName: string,
		clinicId: string,
		callback: (proofId: string) => Promise<void>
	) {
		gfPatientId = patientId;
		gfPatientName = patientName;
		gfClinicId = clinicId;
		pendingGeofenceCallback = callback;
		showGeofenceModal = true;
	}

	async function handleGeofenceVerified(proofId: string) {
		showGeofenceModal = false;
		if (pendingGeofenceCallback) {
			await pendingGeofenceCallback(proofId);
			pendingGeofenceCallback = null;
		}
	}

	// Stats
	const waitingCount = $derived(clinicPatients.filter(p => p.status === 'Scheduled' || p.status === 'Checked In').length);
	const inProgressCount = $derived(clinicPatients.filter(p => p.status === 'In Progress').length);
	const completedCount = $derived(clinicPatients.filter(p => p.status === 'Completed').length);
	const totalCount = $derived(clinicPatients.length);
	const uncheckedPatients = $derived(pendingPatients.filter((patient) => patient.workflow_status === 'unchecked'));
	const unassignedPatients = $derived(pendingPatients.filter((patient) => patient.workflow_status === 'unassigned'));
	const assignedPatients = $derived(pendingPatients.filter((patient) => patient.workflow_status === 'assigned'));
	const admittedPatients = $derived(pendingPatients.filter((patient) => patient.workflow_status === 'admitted'));

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
		if (!selectedClinic) {
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

	async function refreshAll() {
		await Promise.all([
			loadPendingPatients(),
			loadClinicPatients(),
			loadActiveStudents()
		]);
	}

	function showAutoAssignToast(patient: PendingPatient, result: Awaited<ReturnType<typeof staffApi.autoAssignPatient>>) {
		if (result.clinic_only) {
			toastStore.addToast(
				result.message || `${patient.name} checked in to ${result.clinic_name || 'the clinic'} and is waiting for assignment`,
				'warning'
			);
			return;
		}
		toastStore.addToast(`${patient.name} assigned to ${result.student_name}`, 'success');
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
			showAutoAssignToast(patient, result);
			await refreshAll();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'No checked-in students available in the allotted clinic. Choose one manually.', 'warning');
			await openAssignModal(patient);
		} finally {
			assigningPatientId = null;
		}
	}

	async function handleQueueCheckIn(patient: PendingPatient, autoAssignAfterCheckIn = false) {
		if (!patient.clinic_id) {
			toastStore.addToast('Patient has no allocated clinic. Choose a clinic manually first.', 'warning');
			await openAssignModal(patient);
			return;
		}
		openGeofenceGate(patient.id, patient.name, patient.clinic_id, async (proofId) => {
			assigningPatientId = patient.id;
			try {
				const result = await clinicsApi.checkInPatient(patient.clinic_id!, { patient_id: patient.id, geofence_proof_id: proofId });
				toastStore.addToast(result.message || `${patient.name} checked in successfully`, 'success');
				if (autoAssignAfterCheckIn) {
					const assignResult = await staffApi.autoAssignPatient(patient.id, patient.clinic_id!);
					showAutoAssignToast(patient, assignResult);
				}
				await refreshAll();
			} catch (err: any) {
				toastStore.addToast(err?.response?.data?.detail || 'Failed to check in patient', 'error');
			} finally {
				assigningPatientId = null;
			}
		});
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

	async function handleAssignClinicOnly() {
		if (!assignTarget || !assignClinicId) return;
		const target = assignTarget;
		const clinicId = assignClinicId;
		openGeofenceGate(target.id, target.name, clinicId, async (proofId) => {
			isAssigning = true;
			try {
				const result = await clinicsApi.checkInPatient(clinicId, { patient_id: target.id, geofence_proof_id: proofId });
				toastStore.addToast(result.message || `${target.name} checked in and moved to clinic waiting`, 'success');
				showAssignModal = false;
				assignTarget = null;
				await refreshAll();
			} catch (err: any) {
				toastStore.addToast(err?.response?.data?.detail || 'Clinic check-in failed', 'error');
			} finally {
				isAssigning = false;
			}
		});
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
		const patient = searchedPatient;
		openGeofenceGate(patient.id, patient.name, patient.clinic_id!, async (proofId) => {
			isCheckingIn = true;
			try {
				const result = await clinicsApi.checkInPatient(patient.clinic_id!, { patient_id: patient.id, geofence_proof_id: proofId });
				toastStore.addToast(result.message || `${patient.name} checked in to ${patient.clinic_name || 'their clinic'}`, 'success');
				if (autoAssign) {
					try {
						const assignResult = await staffApi.autoAssignPatient(patient.id, patient.clinic_id!);
						if (assignResult.clinic_only) {
							toastStore.addToast(assignResult.message || `${patient.name} is waiting in clinic for assignment`, 'warning');
						} else {
							toastStore.addToast(`Assigned to ${assignResult.student_name}`, 'success');
						}
					} catch (assignErr: any) {
						toastStore.addToast(assignErr?.response?.data?.detail || 'Auto-assign failed', 'warning');
					}
				}
				patientIdInput = '';
				searchedPatient = null;
				lookupError = '';
				await refreshAll();
			} catch (err: any) {
				lookupError = err?.response?.data?.detail || 'Failed to check in patient.';
				toastStore.addToast(lookupError, 'error');
			} finally {
				isCheckingIn = false;
			}
		});
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
			refreshAll();
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
		<div
			class="overflow-hidden rounded-[20px]"
			style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid #93c5fd; box-shadow: 0 2px 8px rgba(0,0,0,0.08);"
		>
			<div class="flex items-start justify-between gap-3 px-4 py-4">
				<div class="flex items-center gap-3">
					<div
						class="flex h-12 w-12 items-center justify-center rounded-2xl shrink-0"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 6px rgba(37,99,235,0.28);"
					>
						<ClipboardList class="w-6 h-6 text-white" />
					</div>
					<div>
						<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-700">Reception console</p>
						<h1 class="text-lg font-bold text-gray-900">Morning intake and clinic flow</h1>
						<p class="text-xs text-gray-600">
							Track unchecked patients, move them into clinic, and hand off assignment without losing anyone in reception.
						</p>
					</div>
				</div>
				<button
					class="rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
					style="background: rgba(255,255,255,0.75); border: 1px solid rgba(37,99,235,0.18); color: #1d4ed8;"
					onclick={refreshAll}
				>
					<RefreshCw class="mr-1 inline h-3.5 w-3.5" /> Refresh
				</button>
			</div>
			<div class="grid grid-cols-2 gap-3 px-4 pb-4 md:grid-cols-4">
				<div class="rounded-2xl px-4 py-3" style="background: white; border: 1px solid rgba(59,130,246,0.14);">
					<p class="text-[10px] uppercase tracking-[0.16em] text-gray-500">Unchecked</p>
					<p class="mt-1 text-2xl font-bold text-amber-600">{uncheckedPatients.length}</p>
				</div>
				<div class="rounded-2xl px-4 py-3" style="background: white; border: 1px solid rgba(59,130,246,0.14);">
					<p class="text-[10px] uppercase tracking-[0.16em] text-gray-500">Waiting for student</p>
					<p class="mt-1 text-2xl font-bold text-blue-700">{unassignedPatients.length}</p>
				</div>
				<div class="rounded-2xl px-4 py-3" style="background: white; border: 1px solid rgba(59,130,246,0.14);">
					<p class="text-[10px] uppercase tracking-[0.16em] text-gray-500">Assigned</p>
					<p class="mt-1 text-2xl font-bold text-emerald-700">{assignedPatients.length}</p>
				</div>
				<div class="rounded-2xl px-4 py-3" style="background: white; border: 1px solid rgba(59,130,246,0.14);">
					<p class="text-[10px] uppercase tracking-[0.16em] text-gray-500">Clinic today</p>
					<p class="mt-1 text-2xl font-bold text-gray-900">{totalCount}</p>
				</div>
			</div>
		</div>

		<div class="grid gap-4 xl:grid-cols-[1.25fr_0.9fr]">
			<div class="space-y-4">
				<div class="overflow-hidden rounded-[18px]" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
					<button
						class="flex w-full items-center justify-between px-4 py-3 cursor-pointer"
						style="background: linear-gradient(to bottom, #f8fafc, #eef2ff); border-bottom: 1px solid rgba(0,0,0,0.06);"
						onclick={() => showPendingSection = !showPendingSection}
					>
						<div class="flex items-center gap-2">
							<UserPlus class="w-4 h-4 text-blue-700" />
							<div>
								<p class="text-sm font-semibold text-gray-900">Action queues</p>
								<p class="text-[11px] text-gray-500">Unchecked, checked-in unassigned, and already assigned handoffs</p>
							</div>
						</div>
						<div class="flex items-center gap-2">
							<span class="rounded-full px-2 py-0.5 text-[10px] font-bold" style="background: #dbeafe; color: #1d4ed8;">
								{pendingPatients.length}
							</span>
							<ChevronDown class="w-4 h-4 text-gray-500 transition-transform" style={`transform: rotate(${showPendingSection ? 180 : 0}deg);`} />
						</div>
					</button>

					{#if showPendingSection}
						<div class="space-y-4 p-4">
							<div class="space-y-2">
								<div class="flex items-center justify-between">
									<p class="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Needs check-in</p>
									<span class="text-[11px] text-gray-500">{uncheckedPatients.length} patients</span>
								</div>
								{#if uncheckedPatients.length === 0}
									<p class="rounded-xl px-3 py-3 text-xs text-gray-400" style="background: #fafafa; border: 1px dashed rgba(0,0,0,0.08);">Everyone recent is already inside a clinic or ward.</p>
								{:else}
									{#each uncheckedPatients as patient (patient.id)}
										<div class="rounded-2xl px-3 py-3" style="background: #fff; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
											<div class="flex items-start gap-3">
												<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
												<div class="min-w-0 flex-1">
													<div class="flex items-center gap-2 flex-wrap">
														<p class="text-sm font-semibold text-gray-900">{patient.name}</p>
														<span class="rounded-full px-2 py-0.5 text-[10px] font-bold" style="background: #fef3c7; color: #b45309;">Unchecked</span>
													</div>
													<p class="text-[11px] text-gray-500">{patient.patient_id} · Registered {formatRegisteredAt(patient.registered_at)}</p>
													<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
													<p class="mt-1 text-[11px] font-medium" style={`color: ${patient.clinic_name ? '#2563eb' : '#d97706'};`}>
														{patient.clinic_name || 'No preferred clinic allocated yet'}
													</p>
												</div>
											</div>
											<div class="mt-3 flex flex-wrap gap-2">
												<button
													class="rounded-xl px-3 py-2 text-[11px] font-semibold text-white cursor-pointer disabled:opacity-60"
													style="background: linear-gradient(to bottom, #10b981, #059669); box-shadow: 0 1px 3px rgba(5,150,105,0.25);"
													onclick={() => handleQueueCheckIn(patient, autoAssign)}
													disabled={assigningPatientId === patient.id}
												>
													{#if assigningPatientId === patient.id}
														<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Working
													{:else}
														<UserCheck class="mr-1 inline h-3.5 w-3.5" /> Check in{autoAssign ? ' & route' : ''}
													{/if}
												</button>
												<button
													class="rounded-xl px-3 py-2 text-[11px] font-semibold cursor-pointer"
													style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08); color: #475569;"
													onclick={() => openAssignModal(patient)}
												>
													<UserPlus class="mr-1 inline h-3.5 w-3.5" /> Manual clinic / student
												</button>
											</div>
										</div>
									{/each}
								{/if}
							</div>

							<div class="space-y-2">
								<div class="flex items-center justify-between">
									<p class="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">Checked in, waiting for student</p>
									<span class="text-[11px] text-gray-500">{unassignedPatients.length} patients</span>
								</div>
								{#if unassignedPatients.length === 0}
									<p class="rounded-xl px-3 py-3 text-xs text-gray-400" style="background: #fafafa; border: 1px dashed rgba(0,0,0,0.08);">No patients are stranded in clinic waiting right now.</p>
								{:else}
									{#each unassignedPatients as patient (patient.id)}
										<div class="rounded-2xl px-3 py-3" style="background: #fff; border: 1px solid #bfdbfe; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
											<div class="flex items-start gap-3">
												<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
												<div class="min-w-0 flex-1">
													<div class="flex items-center gap-2 flex-wrap">
														<p class="text-sm font-semibold text-gray-900">{patient.name}</p>
														<span class="rounded-full px-2 py-0.5 text-[10px] font-bold" style="background: #dbeafe; color: #1d4ed8;">Waiting for student</span>
													</div>
													<p class="text-[11px] text-gray-500">{patient.patient_id} · {patient.clinic_name || 'No clinic'}</p>
													<p class="text-[11px] text-gray-500">Clinic status: {patient.clinic_appointment_status || 'Checked In'}</p>
												</div>
											</div>
											<div class="mt-3 flex flex-wrap gap-2">
												<button
													class="rounded-xl px-3 py-2 text-[11px] font-semibold text-white cursor-pointer disabled:opacity-60"
													style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 1px 3px rgba(29,78,216,0.25);"
													onclick={() => handleAutoAssignPendingPatient(patient)}
													disabled={assigningPatientId === patient.id}
												>
													{#if assigningPatientId === patient.id}
														<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Working
													{:else}
														<Zap class="mr-1 inline h-3.5 w-3.5" /> Auto assign
													{/if}
												</button>
												<button
													class="rounded-xl px-3 py-2 text-[11px] font-semibold cursor-pointer"
													style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08); color: #475569;"
													onclick={() => openAssignModal(patient)}
												>
													<UserPlus class="mr-1 inline h-3.5 w-3.5" /> Assign manually
												</button>
											</div>
										</div>
									{/each}
								{/if}
							</div>

							<div class="space-y-2">
								<div class="flex items-center justify-between">
									<p class="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">Assigned and in flow</p>
									<span class="text-[11px] text-gray-500">{assignedPatients.length} patients</span>
								</div>
								{#if assignedPatients.length === 0}
									<p class="rounded-xl px-3 py-3 text-xs text-gray-400" style="background: #fafafa; border: 1px dashed rgba(0,0,0,0.08);">No active handoffs need reassignment.</p>
								{:else}
									{#each assignedPatients as patient (patient.id)}
										<div class="rounded-2xl px-3 py-3" style="background: #f0fdf4; border: 1px solid #86efac; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
											<div class="flex items-start gap-3">
												<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
												<div class="min-w-0 flex-1">
													<div class="flex items-center gap-2 flex-wrap">
														<p class="text-sm font-semibold text-gray-900">{patient.name}</p>
														<span class="rounded-full px-2 py-0.5 text-[10px] font-bold" style="background: rgba(16,185,129,0.12); color: #047857;">Assigned</span>
													</div>
													<p class="text-[11px] text-gray-500">{patient.patient_id} · {patient.clinic_name || 'No clinic'}</p>
													<p class="text-[11px] text-emerald-700 font-medium">{patient.assigned_student_name || 'Student assigned'}</p>
												</div>
											</div>
											<div class="mt-3">
												<button
													class="rounded-xl px-3 py-2 text-[11px] font-semibold cursor-pointer"
													style="background: white; border: 1px solid rgba(0,0,0,0.08); color: #475569;"
													onclick={() => openReassignModal(patient)}
												>
													<ArrowRight class="mr-1 inline h-3.5 w-3.5" /> Reassign student
												</button>
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<div class="flex gap-2 overflow-x-auto pb-1">
					{#each clinics as clinic (clinic.id)}
						<button
							class="shrink-0 rounded-2xl px-4 py-2.5 text-left cursor-pointer transition-all"
							style={selectedClinic?.id === clinic.id
								? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; border: 1px solid rgba(0,0,0,0.12); box-shadow: 0 2px 6px rgba(37,99,235,0.3);'
								: 'background: white; color: #1f2937; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.06);'}
							onclick={async () => {
								selectedClinic = clinic;
								await refreshAll();
							}}
						>
							<p class="text-xs font-semibold">{clinic.name}</p>
							<p class="text-[10px] opacity-80">{clinicAccessModeLabel(clinic.access_mode)}</p>
						</button>
					{/each}
				</div>

				<div class="overflow-hidden rounded-[18px]" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
					<div class="px-4 py-4" style="background: linear-gradient(to bottom, #f8fafc, #eef2ff); border-bottom: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-start justify-between gap-3">
							<div class="flex items-center gap-3">
								<div class="flex h-11 w-11 items-center justify-center rounded-2xl" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
									<Building class="w-5 h-5 text-white" />
								</div>
								<div>
									<p class="text-sm font-semibold text-gray-900">{selectedClinic?.name || 'No clinic selected'}</p>
									<p class="text-xs text-gray-500">{selectedClinic?.location || selectedClinic?.department || 'Clinic flow board'}</p>
									{#if selectedClinic}
										<p class="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-700">{clinicAccessModeLabel(selectedClinic.access_mode)}</p>
									{/if}
								</div>
							</div>
							<div class="text-right text-xs text-gray-500">
								<p>{formatDateIST(new Date(), { day: 'numeric', month: 'short', year: 'numeric' })}</p>
								<p class="mt-1 font-semibold text-gray-700">{activeStudentsInClinic.length} active students</p>
							</div>
						</div>
						<div class="mt-3 grid grid-cols-3 gap-2">
							<div class="rounded-xl px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
								<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">Waiting</p>
								<p class="text-xl font-bold text-amber-600">{waitingCount}</p>
							</div>
							<div class="rounded-xl px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
								<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">In progress</p>
								<p class="text-xl font-bold text-blue-700">{inProgressCount}</p>
							</div>
							<div class="rounded-xl px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
								<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">Completed</p>
								<p class="text-xl font-bold text-emerald-700">{completedCount}</p>
							</div>
						</div>
					</div>

					<div class="px-4 py-3 space-y-3">
						<div class="flex flex-wrap gap-2">
							{#if loadingActiveStudents}
								<p class="text-xs text-gray-500"><Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Loading active students…</p>
							{:else if activeStudentsInClinic.length === 0}
								<p class="text-xs text-gray-500">No students currently checked in for this clinic.</p>
							{:else}
								{#each activeStudentsInClinic as student (student.id)}
									<span class="rounded-full px-3 py-1 text-[11px] font-medium" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;">
										<GraduationCap class="mr-1 inline h-3 w-3" /> {student.name} · {student.assigned_patient_count}
									</span>
								{/each}
							{/if}
						</div>

						<div class="flex p-1" style="background: rgba(0,0,0,0.05); border-radius: 14px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);">
							{#each [
								{ id: 'waiting', label: 'Waiting', count: waitingCount, activeColor: '#92400e' },
								{ id: 'inprogress', label: 'In Progress', count: inProgressCount, activeColor: '#1e40af' },
								{ id: 'completed', label: 'Completed', count: completedCount, activeColor: '#166534' }
							] as tab (tab.id)}
								<button
									class="flex-1 rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
									style={activeTab === tab.id
										? `background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.08); color: ${tab.activeColor};`
										: 'background: transparent; color: #6b7280; border: 1px solid transparent;'}
									onclick={() => activeTab = tab.id as 'waiting' | 'inprogress' | 'completed'}
								>
									{tab.label} ({tab.count})
								</button>
							{/each}
						</div>

						<div class="flex items-center rounded-xl px-3 py-2" style="background: #fff; border: 1px solid rgba(0,0,0,0.08);">
							<Search class="mr-2 h-3.5 w-3.5 text-gray-400" />
							<input
								type="text"
								placeholder="Filter clinic board by patient name or ID…"
								class="flex-1 bg-transparent text-xs text-gray-700 outline-none"
								bind:value={searchFilter}
							/>
							{#if searchFilter}
								<button class="cursor-pointer" onclick={() => searchFilter = ''}>
									<X class="h-3.5 w-3.5 text-gray-400" />
								</button>
							{/if}
						</div>

						<div class="space-y-2">
							{#each filteredPatients as patient (patient.id)}
								<div class="overflow-hidden rounded-2xl" style="background: #fff; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
									<div class="px-3 py-3">
										<div class="flex items-center gap-3">
											<PatientInsuranceAvatar name={patient.patient_name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
											<div class="min-w-0 flex-1">
												<p class="text-sm font-semibold text-gray-900">{patient.patient_name}</p>
												<p class="text-[11px] text-gray-500">{patient.patient_id} · {patient.appointment_time}</p>
												<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
												{#if patient.provider_name || patient.assigned_student_name}
													<p class="mt-1 text-[11px] text-gray-500">{patient.assigned_student_name || patient.provider_name}</p>
												{/if}
											</div>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold shrink-0"
												style={`background: ${patient.status === 'Completed' ? 'rgba(34,197,94,0.12)' : patient.status === 'In Progress' ? 'rgba(59,130,246,0.12)' : 'rgba(251,191,36,0.12)'}; color: ${patient.status === 'Completed' ? '#16a34a' : patient.status === 'In Progress' ? '#2563eb' : '#d97706'};`}>
												{patient.status}
											</span>
										</div>
									</div>
									<div class="px-3 py-2" style="background: #fafbfc; border-top: 1px solid rgba(0,0,0,0.05);">
										{#if patient.source === 'appointment' && (patient.status === 'Scheduled' || patient.status === 'Checked In')}
											<button
												class="w-full rounded-xl px-3 py-2 text-[11px] font-semibold text-white cursor-pointer"
												style="background: linear-gradient(to bottom, #10b981, #059669); box-shadow: 0 1px 3px rgba(5,150,105,0.25);"
												onclick={() => updateStatus(patient.id, 'In Progress')}
											>
												Start visit
											</button>
										{:else if patient.source === 'appointment' && patient.status === 'In Progress'}
											<button
												class="w-full rounded-xl px-3 py-2 text-[11px] font-semibold text-white cursor-pointer"
												style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 1px 3px rgba(29,78,216,0.25);"
												onclick={() => updateStatus(patient.id, 'Completed')}
											>
												<CheckCircle class="mr-1 inline h-3.5 w-3.5" /> Complete visit
											</button>
										{:else if patient.source === 'assignment'}
											<p class="text-center text-[11px] font-medium text-emerald-600">Following assigned student in clinic</p>
										{:else}
											<p class="text-center text-[11px] text-gray-400">Visit completed</p>
										{/if}
									</div>
								</div>
							{/each}

							{#if filteredPatients.length === 0}
								<div class="rounded-2xl px-4 py-10 text-center" style="background: #fff; border: 1px solid rgba(0,0,0,0.08);">
									{#if activeTab === 'waiting'}
										<CheckCircle class="mx-auto mb-2 h-7 w-7 text-green-400" />
										<p class="text-sm text-gray-400">No patients waiting in this clinic</p>
									{:else if activeTab === 'inprogress'}
										<Clock class="mx-auto mb-2 h-7 w-7 text-blue-400" />
										<p class="text-sm text-gray-400">No patients are in progress right now</p>
									{:else}
										<Users class="mx-auto mb-2 h-7 w-7 text-gray-300" />
										<p class="text-sm text-gray-400">No completed visits yet</p>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<div class="space-y-4">
				<div class="overflow-hidden rounded-[18px]" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
					<div class="px-4 py-3" style="background: linear-gradient(to bottom, #f8fafc, #eef2ff); border-bottom: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="text-sm font-semibold text-gray-900">Quick check-in</p>
								<p class="text-[11px] text-gray-500">Search any patient, confirm their preferred clinic, and move them inside.</p>
							</div>
							{#if autoAssign}
								<span class="rounded-full px-2 py-1 text-[10px] font-bold" style="background: #dcfce7; color: #047857;">AUTO ROUTE ON</span>
							{/if}
						</div>
					</div>
					<div class="space-y-3 p-4">
						<div class="flex gap-2">
							<div class="flex flex-1 items-center rounded-xl px-3 py-2.5" style="background: #fff; border: 1px solid rgba(0,0,0,0.12); box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);">
								<Search class="mr-2 h-3.5 w-3.5 shrink-0 text-gray-400" />
								<input
									type="text"
									id="patient-id-input"
									placeholder="Patient ID or name"
									class="flex-1 bg-transparent text-sm text-gray-700 outline-none"
									bind:value={patientIdInput}
									oninput={() => {
										searchedPatient = null;
										lookupError = '';
									}}
									onkeydown={(event) => {
										if (event.key === 'Enter') handleSearch();
									}}
								/>
								{#if patientIdInput}
									<button class="ml-1 cursor-pointer" onclick={() => {
										patientIdInput = '';
										searchedPatient = null;
										lookupError = '';
									}}>
										<X class="h-3.5 w-3.5 text-gray-400" />
									</button>
								{/if}
							</div>
							<button
								class="rounded-xl px-4 py-2.5 text-xs font-semibold text-white cursor-pointer disabled:opacity-50"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(37,99,235,0.25);"
								disabled={!patientIdInput.trim() || isSearching}
								onclick={handleSearch}
							>
								{#if isSearching}
									<Loader2 class="h-3.5 w-3.5 animate-spin" />
								{:else}
									<Search class="h-3.5 w-3.5" />
								{/if}
							</button>
						</div>

						{#if lookupError}
							<div class="flex items-center rounded-xl px-3 py-2.5" style="background: #fef2f2; border: 1px solid #fecaca;">
								<AlertCircle class="mr-2 h-3.5 w-3.5 shrink-0 text-red-500" />
								<p class="text-xs text-red-700">{lookupError}</p>
							</div>
						{/if}

						{#if searchedPatient}
							<div class="rounded-2xl p-4" style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border: 1px solid #bfdbfe;">
								<div class="flex items-center gap-3">
									<PatientInsuranceAvatar name={searchedPatient.name} src={searchedPatient.photo} size="sm" insurancePolicies={searchedPatient.insurance_policies} patientCategory={searchedPatient.category} patientCategoryColorPrimary={searchedPatient.category_color_primary} patientCategoryColorSecondary={searchedPatient.category_color_secondary} />
									<div class="min-w-0 flex-1">
										<p class="text-sm font-bold text-gray-900">{searchedPatient.name}</p>
										<p class="text-[11px] text-gray-500">{searchedPatient.patient_id}</p>
										<InsuranceTypeBadges insurancePolicies={searchedPatient.insurance_policies} compact maxVisible={2} />
										<p class="mt-1 text-[11px] font-semibold" style={`color: ${searchedPatient.clinic_name ? '#2563eb' : '#d97706'};`}>
											{searchedPatient.clinic_name || 'No clinic allocated'}
										</p>
									</div>
									<CheckCircle class="h-5 w-5 shrink-0 text-blue-400" />
								</div>
								<div class="mt-3">
									<button
										class="w-full rounded-2xl px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-50"
										style="background: linear-gradient(to bottom, #10b981, #059669); box-shadow: 0 2px 6px rgba(5,150,105,0.28);"
										disabled={isCheckingIn}
										onclick={handleCheckIn}
									>
										{#if isCheckingIn}
											<Loader2 class="mr-1 inline h-4 w-4 animate-spin" /> Checking in…
										{:else}
											<UserCheck class="mr-1 inline h-4 w-4" /> Check in{autoAssign ? ' & route' : ''}
										{/if}
									</button>
								</div>
							</div>
						{:else if !isSearching && !lookupError}
							<p class="text-xs text-gray-400">Search by patient ID or name, then confirm the check-in.</p>
						{/if}
					</div>
				</div>

				<div class="rounded-[18px] px-4 py-4" style={`background: ${autoAssign ? 'linear-gradient(to bottom, #ecfdf5, #d1fae5)' : 'white'}; border: 1px solid ${autoAssign ? '#86efac' : 'rgba(0,0,0,0.08)'}; box-shadow: 0 2px 8px rgba(0,0,0,0.06);`}>
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-3">
							<div class="flex h-10 w-10 items-center justify-center rounded-2xl" style={`background: ${autoAssign ? 'linear-gradient(to bottom, #10b981, #059669)' : 'linear-gradient(to bottom, #e5e7eb, #d1d5db)'};`}>
								<Zap class={`h-4 w-4 ${autoAssign ? 'text-white' : 'text-gray-500'}`} />
							</div>
							<div>
								<p class="text-sm font-semibold text-gray-900">Auto-route after check-in</p>
								<p class="text-[11px] text-gray-500">If no student is present, the patient still moves into clinic and waits there unassigned.</p>
							</div>
						</div>
						<button
							aria-label="Toggle auto-assign"
							class="relative h-6 w-11 rounded-full cursor-pointer"
							style={`background: ${autoAssign ? 'linear-gradient(to right, #10b981, #059669)' : '#d1d5db'}; box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);`}
							onclick={() => autoAssign = !autoAssign}
						>
							<div
								class="absolute top-0.5 h-5 w-5 rounded-full transition-all duration-200"
								style={`left: ${autoAssign ? '22px' : '2px'}; background: linear-gradient(to bottom, #fff, #f3f4f6); box-shadow: 0 1px 3px rgba(0,0,0,0.25);`}
							></div>
						</button>
					</div>
				</div>

				{#if admittedPatients.length > 0}
					<div class="overflow-hidden rounded-[18px]" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
						<div class="px-4 py-3" style="background: linear-gradient(to bottom, #f8fafc, #f3f4f6); border-bottom: 1px solid rgba(0,0,0,0.06);">
							<p class="text-sm font-semibold text-gray-900">Already admitted</p>
							<p class="text-[11px] text-gray-500">These patients are already under ward care and do not need reception routing.</p>
						</div>
						<div class="space-y-2 p-4">
							{#each admittedPatients as patient (patient.id)}
								<div class="rounded-2xl px-3 py-3" style="background: #fafafa; border: 1px solid rgba(0,0,0,0.06);">
									<div class="flex items-center gap-3">
										<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
										<div class="min-w-0 flex-1">
											<p class="text-sm font-semibold text-gray-900">{patient.name}</p>
											<p class="text-[11px] text-gray-500">{patient.patient_id} · {patient.clinic_name || 'Ward patient'}</p>
										</div>
										<span class="rounded-full px-2 py-0.5 text-[10px] font-bold" style="background: #dcfce7; color: #166534;">Admitted</span>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
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
				<div class="space-y-3">
					<p class="text-xs text-center text-amber-600">No students are currently checked in to the selected clinic.</p>
					<button
						disabled={isAssigning}
						onclick={handleAssignClinicOnly}
						class="w-full py-2 rounded-lg text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
						style="background: linear-gradient(to bottom, #10b981, #059669);
							   box-shadow: 0 1px 3px rgba(5,150,105,0.3), inset 0 1px 0 rgba(255,255,255,0.25);"
					>
						{#if isAssigning}
							<Loader2 class="w-3 h-3 inline mr-1 animate-spin" /> Checking in…
						{:else}
							Check into clinic without assignment
						{/if}
					</button>
				</div>
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

<PatientGeofenceModal
	open={showGeofenceModal}
	patientId={gfPatientId}
	patientName={gfPatientName}
	onclose={() => { showGeofenceModal = false; pendingGeofenceCallback = null; }}
	onverified={handleGeofenceVerified}
/>
