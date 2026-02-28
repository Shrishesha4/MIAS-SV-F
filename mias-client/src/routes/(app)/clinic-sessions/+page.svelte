<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo, type ClinicPatientInfo, type PatientAppointmentInfo } from '$lib/api/clinics';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		Building, MapPin, ChevronRight, Users,
		Clock, RefreshCw, User, ArrowRight, Calendar,
		Stethoscope
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;

	let loading = $state(true);
	let clinics: ClinicInfo[] = $state([]);
	let selectedClinic: ClinicInfo | null = $state(null);
	let clinicPatients: ClinicPatientInfo[] = $state([]);
	let showClinicSelector = $state(false);

	// Patient-specific
	let patient: any = $state(null);
	let patientAppointments: PatientAppointmentInfo[] = $state([]);

	// Faculty-specific
	let faculty: any = $state(null);

	// Student-specific
	let student: any = $state(null);

	function statusColor(status: string) {
		switch (status) {
			case 'Checked In': return { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' };
			case 'In Progress': return { bg: 'rgba(249, 115, 22, 0.1)', text: '#ea580c' };
			case 'Completed': return { bg: 'rgba(34, 197, 94, 0.1)', text: '#16a34a' };
			case 'Waiting': return { bg: 'rgba(251, 191, 36, 0.1)', text: '#d97706' };
			default: return { bg: 'rgba(107, 114, 128, 0.1)', text: '#6b7280' };
		}
	}

	async function selectClinic(clinic: ClinicInfo) {
		selectedClinic = clinic;
		showClinicSelector = false;
		try {
			clinicPatients = await clinicsApi.getClinicPatients(clinic.id);
		} catch (err) {
			console.error('Failed to load clinic patients', err);
			clinicPatients = [];
		}
	}

	async function refreshPatients() {
		if (!selectedClinic) return;
		try {
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			console.error('Failed to refresh', err);
		}
	}

	async function updateStatus(appointmentId: string, status: string) {
		if (!selectedClinic) return;
		try {
			await clinicsApi.updateAppointmentStatus(selectedClinic.id, appointmentId, status);
			clinicPatients = await clinicsApi.getClinicPatients(selectedClinic.id);
		} catch (err) {
			console.error('Failed to update status', err);
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
			console.error('Failed to load clinic data', err);
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

<div class="px-4 py-4 space-y-4">
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
						<p class="text-sm font-semibold text-gray-800">{clinic.name}</p>
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
							{/if}
						</div>
					</div>
					<button class="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
						       color: #1e40af; border: 1px solid rgba(0,0,0,0.15);"
						onclick={() => showClinicSelector = !showClinicSelector}>
						Change Clinic
					</button>
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
							<p class="text-sm font-semibold text-gray-800">{clinic.name}</p>
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