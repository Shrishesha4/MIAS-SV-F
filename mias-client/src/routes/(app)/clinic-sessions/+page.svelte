<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { clinicsApi, type ClinicInfo, type ClinicPatientInfo, type PatientAppointmentInfo } from '$lib/api/clinics';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		Building, MapPin, ChevronRight, Users,
		Clock, RefreshCw, User, ArrowRight, Calendar,
		Stethoscope, Plus
	} from 'lucide-svelte';

	function clinicAccessModeLabel(accessMode: ClinicInfo['access_mode']) {
		return accessMode === 'APPOINTMENT_ONLY' ? 'Appointment Only' : 'Walk-In';
	}

	const auth = get(authStore);
	const role = auth.role;

	let loading = $state(true);
	let clinics: ClinicInfo[] = $state([]);
	let selectedClinic: ClinicInfo | null = $state(null);
	let clinicPatients: ClinicPatientInfo[] = $state([]);
	let showClinicSelector = $state(false);

	// Appointment creation
	let showAddApptModal = $state(false);
	let apptPatientSearch = $state('');
	let apptPatientResults: any[] = $state([]);
	let selectedApptPatient: any = $state(null);
	let apptDate = $state('');
	let apptTime = $state('09:00 AM');
	let addingAppt = $state(false);
	let searchingPatient = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	// Patient-specific
	let patient: any = $state(null);
	let patientAppointments: PatientAppointmentInfo[] = $state([]);

	// Faculty-specific
	let faculty: any = $state(null);

	// Student-specific
	let student: any = $state(null);
	let studentSessions: any[] = $state([]);
	let activeSession: any = $state(null);
	let checkingIn = $state(false);
	let checkingOut = $state(false);

	// Get the active session the student is checked into
	const currentCheckedInSession = $derived(
		studentSessions.find(s => s.checked_in_at && !s.checked_out_at)
	);

	async function loadStudentSessions() {
		if (!student?.id) return;
		try {
			const sessions = await studentApi.getClinicSessions(student.id);
			studentSessions = sessions;
		} catch (err) {
			console.error('Failed to load clinic sessions', err);
		}
	}

	async function handleStudentCheckIn(session: any) {
		if (!student?.id) return;
		checkingIn = true;
		try {
			const result = await studentApi.checkInClinic(student.id, session.id);
			toastStore.addToast(`Checked in to ${result.clinic_name}`, 'success');
			await loadStudentSessions();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to check in', 'error');
		} finally {
			checkingIn = false;
		}
	}

	async function handleStudentCheckOut(session: any) {
		if (!student?.id) return;
		checkingOut = true;
		try {
			const result = await studentApi.checkOutClinic(student.id, session.id);
			const hours = Math.floor(result.duration_minutes / 60);
			const mins = result.duration_minutes % 60;
			toastStore.addToast(`Checked out. Duration: ${hours}h ${mins}m`, 'success');
			await loadStudentSessions();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to check out', 'error');
		} finally {
			checkingOut = false;
		}
	}

	function formatTime(isoString: string | null) {
		if (!isoString) return '';
		return new Date(isoString).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
	}

	function statusColor(status: string) {
		switch (status) {
			case 'Checked In': return { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' };
			case 'In Progress': return { bg: 'rgba(249, 115, 22, 0.1)', text: '#ea580c' };
			case 'Completed': return { bg: 'rgba(34, 197, 94, 0.1)', text: '#16a34a' };
			case 'Waiting': return { bg: 'rgba(251, 191, 36, 0.1)', text: '#d97706' };
			default: return { bg: 'rgba(107, 114, 128, 0.1)', text: '#6b7280' };
		}
	}

	function handlePatientSearch(query: string) {
		apptPatientSearch = query;
		if (searchTimeout) clearTimeout(searchTimeout);
		if (!query.trim() || !selectedClinic) {
			apptPatientResults = [];
			return;
		}
		searchTimeout = setTimeout(async () => {
			searchingPatient = true;
			try {
				apptPatientResults = await clinicsApi.searchPatient(selectedClinic!.id, query.trim());
			} catch (err) {
				toastStore.addToast('Failed to search patients', 'error');
				apptPatientResults = [];
			} finally {
				searchingPatient = false;
			}
		}, 400);
	}

	function resetApptModal() {
		apptPatientSearch = '';
		apptPatientResults = [];
		selectedApptPatient = null;
		apptDate = '';
		apptTime = '09:00 AM';
		addingAppt = false;
	}

	async function handleCreateAppointment() {
		if (!selectedClinic || !selectedApptPatient) return;
		addingAppt = true;
		try {
			await clinicsApi.createAppointment(selectedClinic.id, {
				patient_id: selectedApptPatient.id,
				date: apptDate || undefined,
				time: apptTime || undefined
			});
			toastStore.addToast('Appointment created successfully', 'success');
			showAddApptModal = false;
			resetApptModal();
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			toastStore.addToast('Failed to create appointment', 'error');
		} finally {
			addingAppt = false;
		}
	}

	async function selectClinic(clinic: ClinicInfo) {
		selectedClinic = clinic;
		showClinicSelector = false;
		try {
			clinicPatients = await clinicsApi.getClinicPatients(clinic.id);
		} catch (err) {
			toastStore.addToast('Failed to load clinic patients', 'error');
			clinicPatients = [];
		}
	}

	async function refreshPatients() {
		if (!selectedClinic) return;
		try {
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			toastStore.addToast('Failed to refresh patients', 'error');
		}
	}

	async function updateStatus(appointmentId: string, status: string) {
		if (!selectedClinic) return;
		try {
			await clinicsApi.updateAppointmentStatus(selectedClinic.id, appointmentId, status);
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			toastStore.addToast('Failed to update status', 'error');
		}
	}

	onMount(async () => {
		try {
			if (role === 'PATIENT') {
				patient = await patientApi.getCurrentPatient();
				patientAppointments = await clinicsApi.getPatientAppointments(patient.id);
				clinics = await clinicsApi.listClinics();
			} else if (role === 'STUDENT') {
				student = await studentApi.getMe();
				clinics = await clinicsApi.listClinics();
				await loadStudentSessions();
				if (clinics.length > 0) {
					await selectClinic(clinics[0]);
				}
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
				clinics = await clinicsApi.listClinics();
				const myClinic = clinics.find(c => c.faculty_id === faculty.id);
				if (myClinic) {
					await selectClinic(myClinic);
				} else if (clinics.length > 0) {
					await selectClinic(clinics[0]);
				}
			} else {
				clinics = await clinicsApi.listClinics();
				if (clinics.length > 0) {
					await selectClinic(clinics[0]);
				}
			}
		} catch (err) {
			toastStore.addToast('Failed to load clinic data', 'error');
		} finally {
			loading = false;
		}
	});

	$effect(() => {
		if (selectedClinic && (role === 'STUDENT' || role === 'FACULTY' || role === 'ADMIN')) {
			const interval = setInterval(refreshPatients, 30000);
			return () => clearInterval(interval);
		}
	});

	const waitingCount = $derived(clinicPatients.filter(p => p.status === 'Scheduled' || p.status === 'Checked In').length);
	const inProgressCount = $derived(clinicPatients.filter(p => p.status === 'In Progress').length);
	const completedCount = $derived(clinicPatients.filter(p => p.status === 'Completed').length);
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>

	{:else if role === 'PATIENT'}
		<AquaCard>
			<div class="flex items-center gap-2 mb-4">
				<Calendar class="w-5 h-5 text-blue-600" />
				<h3 class="font-bold text-gray-800">My Clinic Appointments</h3>
			</div>
			{#if patientAppointments.length === 0}
				<p class="text-sm text-center text-gray-400 py-6">No clinic appointments scheduled</p>
			{:else}
				<div class="space-y-3">
					{#each patientAppointments as appt}
						{@const sc = statusColor(appt.status)}
						<div class="p-4 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
							<div class="flex items-start justify-between">
								<div>
									<p class="font-semibold text-gray-800">{appt.clinic_name}</p>
									<div class="flex items-center gap-1 text-xs text-gray-500 mt-1">
										<MapPin class="w-3 h-3" /> {appt.clinic_location}
									</div>
									<div class="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
										<Stethoscope class="w-3 h-3" /> {appt.doctor_name || appt.provider_name}
									</div>
									<div class="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
										<Clock class="w-3 h-3" /> {appt.appointment_time} · {appt.appointment_date ? new Date(appt.appointment_date).toLocaleDateString() : ''}
									</div>
								</div>
								<span class="px-2 py-1 text-xs font-medium rounded-full" style="background: {sc.bg}; color: {sc.text};">
									{appt.status}
								</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>
		<AquaCard>
			<div class="flex items-center gap-2 mb-3">
				<Building class="w-5 h-5 text-blue-600" />
				<h3 class="font-bold text-gray-800">Available Clinics</h3>
			</div>
			<div class="space-y-2">
				{#each clinics as clinic}
					<div class="p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-center gap-2">
							<p class="text-sm font-semibold text-gray-800">{clinic.name}</p>
							<span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600">{clinicAccessModeLabel(clinic.access_mode)}</span>
						</div>
						<p class="text-xs text-gray-500">{clinic.department} · {clinic.location}</p>
						{#if clinic.faculty_name}
							<p class="text-xs text-gray-400">Managed by {clinic.faculty_name}</p>
						{/if}
					</div>
				{/each}
				{#if clinics.length === 0}
					<p class="text-sm text-gray-400 text-center py-4">No clinics available</p>
				{/if}
			</div>
		</AquaCard>

	{:else}
		<!-- Student Attendance Check-in/out -->
		{#if role === 'STUDENT'}
			<AquaCard>
				<div class="flex items-center gap-2 mb-4">
					<Clock class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">My Attendance</h3>
				</div>

				{#if currentCheckedInSession}
					<!-- Currently checked in -->
					<div class="p-4 rounded-xl" style="background: linear-gradient(to bottom, #dcfce7, #bbf7d0); border: 1px solid #86efac;">
						<div class="flex items-center justify-between">
							<div>
								<p class="font-semibold text-green-800">Checked In</p>
								<p class="text-sm text-green-700">{currentCheckedInSession.clinic_name}</p>
								<p class="text-xs text-green-600 mt-1">
									Since {formatTime(currentCheckedInSession.checked_in_at)}
								</p>
							</div>
							<AquaButton
								variant="danger"
								size="sm"
								loading={checkingOut}
								onclick={() => handleStudentCheckOut(currentCheckedInSession.id)}
							>
								Check Out
							</AquaButton>
						</div>
					</div>
				{:else if studentSessions.length > 0}
					<!-- Sessions available to check into -->
					<div class="space-y-2">
						{#each studentSessions as session}
							<div class="p-3 rounded-xl flex items-center justify-between" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
								<div>
									<p class="font-medium text-gray-800">{session.clinic_name}</p>
									<p class="text-xs text-gray-500">
										{new Date(session.session_date).toLocaleDateString()} · {session.start_time} - {session.end_time}
									</p>
									{#if session.checked_out_at}
										<p class="text-xs text-gray-400 mt-1">
											Attended: {formatTime(session.checked_in_at)} - {formatTime(session.checked_out_at)}
										</p>
									{/if}
								</div>
								{#if !session.checked_in_at}
									<AquaButton
										variant="primary"
										size="sm"
										loading={checkingIn}
										onclick={() => handleStudentCheckIn(session.id)}
									>
										Check In
									</AquaButton>
								{:else if session.checked_out_at}
									<span class="px-2 py-1 text-xs font-medium rounded-full" style="background: #dcfce7; color: #166534;">
										Completed
									</span>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-center text-gray-400 py-4">No clinic sessions assigned today</p>
				{/if}
			</AquaCard>
		{/if}

		<!-- Student / Faculty / Admin Clinic View -->
		<AquaCard padding={false}>
			<div class="p-4">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
							<Building class="w-5 h-5 text-white" />
						</div>
						<div>
							<h2 class="text-lg font-bold text-gray-800">{selectedClinic?.name || 'Select Clinic'}</h2>
							{#if selectedClinic}
								<p class="text-xs text-gray-500 flex items-center gap-1">
									<MapPin class="w-3 h-3" /> {selectedClinic.location} · {selectedClinic.department}
								</p>
								<p class="mt-1 text-[11px] text-gray-500">{clinicAccessModeLabel(selectedClinic.access_mode)} clinic</p>
							{/if}
						</div>
					</div>
					<div class="flex items-center gap-2">
						{#if role === 'FACULTY' || role === 'ADMIN' || role === 'STUDENT' || role === 'RECEPTION'}
							<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
								       color: white; border: 1px solid rgba(0,0,0,0.15);
								       box-shadow: 0 1px 2px rgba(0,0,0,0.1);"
								onclick={() => showAddApptModal = true}>
								<Plus class="w-3 h-3" /> {selectedClinic?.access_mode === 'APPOINTMENT_ONLY' ? 'Schedule Appointment' : 'Add Appointment'}
							</button>
						{/if}
						<button class="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
							style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
							       color: #1e40af; border: 1px solid rgba(0,0,0,0.15);"
							onclick={() => showClinicSelector = !showClinicSelector}>
							Change Clinic
						</button>
					</div>
				</div>
				{#if selectedClinic?.faculty_name}
					<div class="mt-2 flex items-center gap-1 text-xs text-gray-500">
						<Stethoscope class="w-3 h-3" />
						<span>Managed by <strong>{selectedClinic.faculty_name}</strong></span>
					</div>
				{/if}
			</div>
			{#if showClinicSelector}
				<div class="border-t border-gray-100 p-3 space-y-2">
					{#each clinics as clinic}
						<button class="w-full text-left p-3 rounded-lg cursor-pointer"
							style="background: {selectedClinic?.id === clinic.id ? 'rgba(59,130,246,0.1)' : '#f8f9fb'};
							       border: 1px solid {selectedClinic?.id === clinic.id ? 'rgba(59,130,246,0.3)' : 'rgba(0,0,0,0.06)'};"
							onclick={() => selectClinic(clinic)}>
							<div class="flex items-center gap-2">
								<p class="text-sm font-semibold text-gray-800">{clinic.name}</p>
								<span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600">{clinicAccessModeLabel(clinic.access_mode)}</span>
							</div>
							<p class="text-xs text-gray-500">{clinic.department} · {clinic.location}</p>
							{#if clinic.faculty_name}
								<p class="text-xs text-gray-400">Dr. {clinic.faculty_name}</p>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		</AquaCard>

		{#if selectedClinic}
			<div class="grid grid-cols-3 gap-2">
				<div class="p-3 rounded-xl text-center" style="background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.2);">
					<p class="text-lg font-bold text-amber-600">{waitingCount}</p>
					<p class="text-[10px] text-amber-600 font-medium">Waiting</p>
				</div>
				<div class="p-3 rounded-xl text-center" style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2);">
					<p class="text-lg font-bold text-blue-600">{inProgressCount}</p>
					<p class="text-[10px] text-blue-600 font-medium">In Progress</p>
				</div>
				<div class="p-3 rounded-xl text-center" style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2);">
					<p class="text-lg font-bold text-green-600">{completedCount}</p>
					<p class="text-[10px] text-green-600 font-medium">Completed</p>
				</div>
			</div>

			<AquaCard>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<Users class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Patients in Clinic Today</h3>
					</div>
					<button class="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer"
						style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
						       color: #1e40af; border: 1px solid rgba(0,0,0,0.15);"
						onclick={refreshPatients}>
						<RefreshCw class="w-3 h-3" /> Refresh
					</button>
				</div>
				{#if clinicPatients.length === 0}
					<p class="text-sm text-gray-400 text-center py-6">No patients scheduled for today</p>
				{:else}
					<div class="space-y-3">
						{#each clinicPatients as cp}
							{@const sc = statusColor(cp.status)}
							<div class="flex items-center gap-3 p-3 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
								<Avatar name={cp.patient_name || 'Patient'} size="md" />
								<div class="flex-1 min-w-0">
									<p class="text-sm font-semibold text-gray-800 truncate">{cp.patient_name}</p>
									<p class="text-xs text-gray-500">{cp.patient_id}</p>
									<div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
										<span class="flex items-center gap-1"><Clock class="w-3 h-3" /> {cp.appointment_time}</span>
										<span class="flex items-center gap-1"><User class="w-3 h-3" /> {cp.provider_name}</span>
									</div>
								</div>
								<div class="flex flex-col items-end gap-1.5 shrink-0">
									<span class="px-2 py-1 text-xs font-medium rounded-full" style="background: {sc.bg}; color: {sc.text};">
										{cp.status}
									</span>
									{#if role !== 'PATIENT'}
										<div class="flex gap-1">
											{#if cp.status === 'Scheduled' || cp.status === 'Checked In'}
												<button class="px-2 py-0.5 text-[10px] font-medium rounded cursor-pointer"
													style="background: rgba(59,130,246,0.1); color: #2563eb; border: 1px solid rgba(59,130,246,0.2);"
													onclick={() => updateStatus(cp.id, 'In Progress')}>Start</button>
											{/if}
											{#if cp.status === 'In Progress'}
												<button class="px-2 py-0.5 text-[10px] font-medium rounded cursor-pointer"
													style="background: rgba(34,197,94,0.1); color: #16a34a; border: 1px solid rgba(34,197,94,0.2);"
													onclick={() => updateStatus(cp.id, 'Completed')}>Complete</button>
											{/if}
										</div>
									{/if}
								</div>
								{#if cp.patient_db_id && role !== 'PATIENT'}
									<button class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 cursor-pointer"
										style="background: linear-gradient(to bottom, #e8edf5, #d5dde8); border: 1px solid rgba(0,0,0,0.1);"
										onclick={() => goto(`/patients/${cp.patient_db_id}`)}>
										<ArrowRight class="w-4 h-4 text-blue-600" />
									</button>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</AquaCard>
		{/if}
	{/if}
</div>

<!-- Add Appointment Modal -->
<AquaModal open={showAddApptModal} title="Add Appointment" onclose={() => { showAddApptModal = false; resetApptModal(); }}>
	<div class="space-y-4">
		<!-- Patient Search -->
		<div>
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-xs font-medium text-gray-600 mb-1">Search Patient</label>
			{#if selectedApptPatient}
				<div class="flex items-center justify-between p-3 rounded-xl" style="background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.2);">
					<div>
						<p class="text-sm font-semibold text-gray-800">{selectedApptPatient.name || selectedApptPatient.full_name}</p>
						<p class="text-xs text-gray-500">{selectedApptPatient.patient_id || selectedApptPatient.id}</p>
					</div>
					<button class="text-xs text-blue-600 font-medium cursor-pointer" onclick={() => { selectedApptPatient = null; apptPatientSearch = ''; apptPatientResults = []; }}>
						Change
					</button>
				</div>
			{:else}
				<input
					type="text"
					class="w-full px-3 py-2 text-sm rounded-lg"
					style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.1); outline: none;"
					placeholder="Type patient name or ID..."
					value={apptPatientSearch}
					oninput={(e) => handlePatientSearch(e.currentTarget.value)}
				/>
				{#if searchingPatient}
					<p class="text-xs text-gray-400 mt-1">Searching...</p>
				{/if}
				{#if apptPatientResults.length > 0}
					<div class="mt-2 space-y-1 max-h-40 overflow-y-auto">
						{#each apptPatientResults as pt}
							<button class="w-full text-left p-2 rounded-lg text-sm cursor-pointer"
								style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);"
								onclick={() => { selectedApptPatient = pt; apptPatientResults = []; apptPatientSearch = ''; }}>
								<p class="font-medium text-gray-800">{pt.name || pt.full_name}</p>
								<p class="text-xs text-gray-500">{pt.patient_id || pt.id}</p>
							</button>
						{/each}
					</div>
				{:else if apptPatientSearch.trim() && !searchingPatient}
					<p class="text-xs text-gray-400 mt-1">No patients found</p>
				{/if}
			{/if}
		</div>

		<!-- Date -->
		<div>
			<label for="appt-date" class="block text-xs font-medium text-gray-600 mb-1">Appointment Date</label>
			<input
				id="appt-date"
				type="date"
				class="w-full px-3 py-2 text-sm rounded-lg"
				style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.1); outline: none;"
				bind:value={apptDate}
			/>
		</div>

		<!-- Time -->
		<div>
			<label for="appt-time" class="block text-xs font-medium text-gray-600 mb-1">Appointment Time</label>
			<input
				id="appt-time"
				type="text"
				class="w-full px-3 py-2 text-sm rounded-lg"
				style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.1); outline: none;"
				placeholder="e.g. 09:00 AM"
				bind:value={apptTime}
			/>
		</div>

		<!-- Submit -->
		<button
			class="w-full py-2.5 rounded-xl text-sm font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
			       color: white; border: 1px solid rgba(0,0,0,0.15);
			       box-shadow: 0 2px 4px rgba(37,99,235,0.3);"
			disabled={!selectedApptPatient || addingAppt}
			onclick={handleCreateAppointment}>
			{#if addingAppt}
				Creating...
			{:else}
				Create Appointment
			{/if}
		</button>
	</div>
</AquaModal>