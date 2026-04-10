<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { patientApi, type PatientDashboard, type ActiveMedication, type Appointment } from '$lib/api/patients';
	import { studentApi, type EmergencyContact, type Clinic, type ClinicPatient, type AssignedPatient } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import { approvalsApi, type ApprovalStats, type ScheduleItem } from '$lib/api/approvals';
	import { autocompleteApi } from '$lib/api/autocomplete';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import PatientProfile from '$lib/components/PatientProfile.svelte';
	import {
		HeartPulse, FileText, Pill, Activity, TestTube, Wallet,
		Bed, Calendar, Crown, Shield, AlertTriangle, ChevronRight,
		GraduationCap, Users, CheckCircle, Clipboard, User,
		Award, BarChart3, RefreshCw, ArrowRight, Building,
		Phone, Mail, MessageSquare, CheckCircle2, Clock, CircleDot,
		PhoneCall, Hospital, ClipboardList, FileCheck, Save,
		Eye, X
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;

	// Shared state
	let loading = $state(true);
	let error = $state('');

	// Patient state
	let patient: any = $state(null);
	let dashboard: PatientDashboard | null = $state(null);
	let showAppointment = $state(true);
	let showMedicationReminder = $state(true);

	// Student state
	let student: any = $state(null);
	let assignedPatients: AssignedPatient[] = $state([]);
	let clinicSessions: any[] = $state([]);
	let studentTab = $state('today');
	let selectedPatient: AssignedPatient | null = $state(null);
	let emergencyContacts: EmergencyContact[] = $state([]);
	let clinics: Clinic[] = $state([]);
	let selectedClinic: Clinic | null = $state(null);
	let clinicPatients: ClinicPatient[] = $state([]);
	let showAllPatients = $state(false);
	let previousPatients: any[] = $state([]);
	let previousPatientsLoading = $state(false);

	// Faculty state
	let faculty: any = $state(null);
	let approvals: any[] = $state([]);
	let approvalStats: ApprovalStats = $state({
		case_records: 0,
		discharge_summaries: 0,
		admissions: 0,
		prescriptions: 0,
		total: 0,
	});
	let todaySchedule: ScheduleItem[] = $state([]);

	const studentTabs = [
		{ id: 'clinic', label: 'Clinic' },
		{ id: 'today', label: 'Today' },
		{ id: 'previous', label: 'Previous' },
	];

	// Faculty approval cards config
	const approvalCards = $derived([
		{
			icon: ClipboardList,
			label: 'Case Record Approvals',
			count: approvalStats.case_records,
			path: '/approvals?type=case-records',
			color: '#3b82f6',
		},
		{
			icon: FileCheck,
			label: 'Discharge Approvals',
			count: approvalStats.discharge_summaries,
			path: '/approvals?type=discharge',
			color: '#8b5cf6',
		},
		{
			icon: Save,
			label: 'Admission Approvals',
			count: approvalStats.admissions,
			path: '/approvals?type=admissions',
			color: '#3b82f6',
		},
		{
			icon: Pill,
			label: 'Prescription Approvals',
			count: approvalStats.prescriptions,
			path: '/approvals?type=prescriptions',
			color: '#3b82f6',
		},
	]);

	// Derived medical alerts string
	const medicalAlertsText = $derived.by(() => {
		if (!patient?.allergies?.length && !patient?.medical_alerts?.length) return '';
		const alerts: string[] = [];
		patient?.allergies?.forEach((a: any) => alerts.push(`${a.allergen} Allergy`));
		patient?.medical_alerts?.forEach((a: any) => alerts.push(a.title));
		return alerts.join(', ');
	});

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		const d = new Date(dateStr);
		return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
	}

	function formatAppointmentDate(dateStr: string | null, time: string | null): string {
		if (!dateStr) return '';
		const d = new Date(dateStr);
		const dateFormatted = d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
		return time ? `${dateFormatted}, ${time}` : dateFormatted;
	}

	function getScheduleColor(type: string) {
		switch (type) {
			case 'consultation': return { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' };
			case 'meeting': return { bg: 'rgba(236, 72, 153, 0.1)', text: '#db2777' };
			case 'review': return { bg: 'rgba(34, 197, 94, 0.1)', text: '#16a34a' };
			default: return { bg: 'rgba(107, 114, 128, 0.1)', text: '#4b5563' };
		}
	}

	let medicationTakenSuccess = $state(false);

	async function handleMedicationTaken() {
		if (!dashboard?.active_medications?.[0] || !patient) return;
		const med = dashboard.active_medications[0];
		try {
			const result = await patientApi.logMedicationDose(patient.id, med.id, { status: 'TAKEN', scheduled_time: new Date().toISOString() });
			if (result && result.id) {
				medicationTakenSuccess = true;
				dashboard = await patientApi.getDashboard(patient.id);
				setTimeout(() => {
					showMedicationReminder = false;
					medicationTakenSuccess = false;
				}, 1500);
			}
		} catch (err) {
			toastStore.addToast('Failed to log medication dose. Please try again.', 'error');
		}
	}


	onMount(async () => {
		try {
			if (role === 'PATIENT') {
				patient = await patientApi.getCurrentPatient();
				dashboard = await patientApi.getDashboard(patient.id);
			} else if (role === 'STUDENT') {
				student = await studentApi.getMe();
				assignedPatients = await studentApi.getAssignedPatients(student.id);
				clinicSessions = await studentApi.getClinicSessions(student.id);
				emergencyContacts = await studentApi.getEmergencyContacts();
				clinics = await studentApi.getClinics();
				if (clinics.length > 0) {
					selectedClinic = clinics[0];
					clinicPatients = await studentApi.getClinicPatients(clinics[0].id);
				}
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
				approvals = await facultyApi.getApprovals(faculty.id);
				approvalStats = await approvalsApi.getApprovalStats(faculty.id);
				todaySchedule = await approvalsApi.getTodaySchedule(faculty.id);
			}
		} catch (err: any) {
			error = 'Failed to load dashboard data';
			toastStore.addToast('Failed to load dashboard data', 'error');
		} finally {
			loading = false;
		}
	});

	// Auto-refresh dashboard data every 30 seconds
	$effect(() => {
		if (loading) return;
		const interval = setInterval(async () => {
			try {
				if (role === 'PATIENT' && patient) {
					dashboard = await patientApi.getDashboard(patient.id);
				} else if (role === 'STUDENT' && student) {
					assignedPatients = await studentApi.getAssignedPatients(student.id);
				} else if (role === 'FACULTY' && faculty) {
					approvals = await facultyApi.getApprovals(faculty.id);
					approvalStats = await approvalsApi.getApprovalStats(faculty.id);
				}
			} catch (err) {
				toastStore.addToast('Auto-refresh failed', 'error');
			}
		}, 30000);
		return () => clearInterval(interval);
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<AquaCard>
			<p class="text-center text-red-600 text-sm py-4">{error}</p>
		</AquaCard>
	{:else if role === 'PATIENT' && patient}
		<!-- Patient Welcome Card -->
		<AquaCard padding={false}>
			<div class="p-4">
				<div class="flex items-center gap-3">
					<div class="relative">
						{#if patient.photo}
							<img src={patient.photo} alt={patient.name} class="w-14 h-14 rounded-full object-cover border-2 border-white shadow-md" />
						{:else}
							<Avatar name={patient.name} size="lg" />
						{/if}
						{#if patient.category === 'ELITE' || patient.category === 'VIP'}
							<div class="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center"
								style="background: linear-gradient(to bottom, #fbbf24, #f59e0b); border: 2px solid white;">
								<Crown class="w-2.5 h-2.5 text-white" />
							</div>
						{/if}
					</div>
					<div class="flex-1 min-w-0">
						<h2 class="text-lg font-bold text-gray-800">Welcome, {patient.name}</h2>
						<p class="text-sm text-gray-500">
							ID: {patient.patient_id}
							{#if dashboard?.last_visit}
								<span class="mx-1">·</span> Last visit: {formatDate(dashboard.last_visit)}
							{/if}
						</p>
					</div>
				</div>
			</div>
			
			<!-- Medical Alerts Bar -->
			{#if medicalAlertsText}
				<div class="px-4 py-2.5 flex items-center gap-2"
					style="background: linear-gradient(to bottom, #fef2f2, #fee2e2); border-top: 1px solid #fecaca;">
					<AlertTriangle class="w-4 h-4 text-red-500 shrink-0" />
					<p class="text-sm text-red-700 font-medium truncate">{medicalAlertsText}</p>
				</div>
			{/if}
		</AquaCard>

		<!-- Next Appointment Card -->
		{#if dashboard?.next_appointment && showAppointment}
			<AquaCard padding={false}>
				<div class="p-4 flex items-center gap-3">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<Calendar class="w-5 h-5 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-xs text-gray-500 font-medium">Next Appointment</p>
						<p class="text-sm font-semibold text-gray-800">
							{dashboard.next_appointment.doctor} - {formatAppointmentDate(dashboard.next_appointment.date, dashboard.next_appointment.time)}
						</p>
					</div>
					<button
						class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 cursor-pointer"
						style="background: linear-gradient(to bottom, #fee2e2, #fecaca);"
						onclick={() => showAppointment = false}
					>
						<X class="w-4 h-4 text-red-500" />
					</button>
				</div>
			</AquaCard>
		{/if}

		<!-- Medication Reminder Card -->
		{#if dashboard && dashboard.active_medications && dashboard.active_medications.length > 0 && showMedicationReminder}
			{@const med = dashboard.active_medications[0]}
			<AquaCard padding={false}>
				<div class="p-4 flex items-center gap-3">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<Pill class="w-5 h-5 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<p class="text-xs text-gray-500 font-medium">Medication Reminder</p>
							<span class="px-1.5 py-0.5 text-[10px] font-bold text-white rounded"
								style="background: linear-gradient(to bottom, #ef4444, #dc2626);">Now</span>
						</div>
						<p class="text-sm font-semibold text-gray-800 truncate">
							{med.name} {med.dosage} - {med.instructions || `Take as directed`}
						</p>
					</div>
					<button
						class="px-4 py-1.5 rounded-full text-sm font-semibold text-white cursor-pointer shrink-0"
						style="background: linear-gradient(to bottom, {medicationTakenSuccess ? '#22c55e' : '#3b82f6'}, {medicationTakenSuccess ? '#16a34a' : '#2563eb'});
						       box-shadow: 0 2px 4px {medicationTakenSuccess ? 'rgba(22,163,74,0.3)' : 'rgba(37, 99, 235, 0.3)'};"
						onclick={handleMedicationTaken}
						disabled={medicationTakenSuccess}
					>
						{medicationTakenSuccess ? '✓ Logged!' : 'Taken'}
					</button>
				</div>
			</AquaCard>
		{/if}

		<!-- PATIENT SERVICES Section -->
		<div>
			<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 px-1">Patient Services</p>
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
				<button
					class="flex items-center gap-3 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/records')}
				>
					<div class="w-10 h-10 rounded-lg flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<FileText class="w-5 h-5 text-white" />
					</div>
					<span class="text-sm font-semibold text-gray-800">Health Records</span>
				</button>

				<button
					class="flex items-center gap-3 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/admissions')}
				>
					<div class="w-10 h-10 rounded-lg flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<Bed class="w-5 h-5 text-white" />
					</div>
					<span class="text-sm font-semibold text-gray-800">Admissions</span>
				</button>

				<button
					class="flex flex-col gap-1 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/wallet/hospital')}
				>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
							<Wallet class="w-5 h-5 text-white" />
						</div>
						<span class="text-sm font-semibold text-gray-800">Hospital Wallet</span>
					</div>
					<p class="text-base font-bold text-blue-600 ml-13">₹{(dashboard?.hospital_balance ?? 0).toFixed(2)}</p>
				</button>

				<button
					class="flex flex-col gap-1 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/wallet/pharmacy')}
				>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
							<Pill class="w-5 h-5 text-white" />
						</div>
						<span class="text-sm font-semibold text-gray-800">Pharmacy Wallet</span>
					</div>
					<p class="text-base font-bold text-blue-600 ml-13">₹{(dashboard?.pharmacy_balance ?? 0).toFixed(2)}</p>
				</button>
			</div>
		</div>

		<!-- MEDICAL SERVICES Section -->
		<div>
			<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 px-1">Medical Services</p>
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
				<button
					class="flex items-center gap-3 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/reports')}
				>
					<div class="w-10 h-10 rounded-lg flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<TestTube class="w-5 h-5 text-white" />
					</div>
					<span class="text-sm font-semibold text-gray-800 truncate">Investigation Rep...</span>
				</button>

				<button
					class="flex items-center gap-3 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/prescriptions')}
				>
					<div class="w-10 h-10 rounded-lg flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<Pill class="w-5 h-5 text-white" />
					</div>
					<span class="text-sm font-semibold text-gray-800">Prescriptions</span>
				</button>

				<button
					class="flex items-center gap-3 p-4 rounded-xl cursor-pointer text-left"
					style="background-color: white; border-radius: 12px;
					       box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05);"
					onclick={() => goto('/vitals')}
				>
					<div class="w-10 h-10 rounded-lg flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6cc, #3b82f6);">
						<HeartPulse class="w-5 h-5 text-white" />
					</div>
					<span class="text-sm font-semibold text-gray-800">Vitals</span>
				</button>
			</div>
		</div>

	{:else if role === 'STUDENT' && student}
		<!-- Student Dashboard - Master Detail -->
		<div class="flex gap-0 md:gap-4" style="min-height: calc(100vh - 7rem);">
			<!-- Left Panel: Patient List -->
			<div class="w-full md:w-80 lg:w-96 flex flex-col shrink-0 rounded-xl overflow-hidden"
				style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
				<!-- Tabs -->
				<div class="p-2">
					<TabBar tabs={studentTabs} activeTab={studentTab} onchange={async (id) => {
						studentTab = id;
						selectedPatient = null;
						if (id === 'previous' && previousPatients.length === 0 && student) {
							previousPatientsLoading = true;
							try {
								previousPatients = await studentApi.getPreviousPatients(student.id);
							} catch (err) {
								toastStore.addToast('Failed to load previous patients', 'error');
							} finally {
								previousPatientsLoading = false;
							}
						}
					}} />
				</div>

				<!-- Patient List -->
				<div class="flex-1 overflow-y-auto">
					{#if studentTab === 'today'}
						{#each assignedPatients as ap}
							<button
								class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer border-b border-gray-50 hover:bg-gray-50"
								class:bg-blue-50={selectedPatient?.id === ap.id}
								onclick={() => {
									if (window.innerWidth < 768) {
										goto(`/patients/${ap.id}`);
									} else {
										selectedPatient = ap;
									}
								}}
							>
								<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
									style="background: linear-gradient(to bottom, #60a5fa, #3b82f6);">
									<User class="w-5 h-5 text-white" />
								</div>
								<div class="flex-1 min-w-0">
									<p class="font-semibold text-gray-800 text-sm">{ap.name}</p>
									<p class="text-xs text-gray-500 truncate">{ap.patient_id} · {ap.primary_diagnosis || 'No diagnosis'}</p>
								</div>
								<ChevronRight class="w-4 h-4 text-gray-400 shrink-0" />
							</button>
						{/each}
						{#if assignedPatients.length === 0}
							<div class="flex flex-col items-center justify-center py-16 text-center px-4">
								<Users class="w-8 h-8 text-gray-300 mb-2" />
								<p class="text-sm text-gray-400">No patients assigned today</p>
							</div>
						{/if}

					{:else if studentTab === 'clinic'}
						<!-- Clinic Selector -->
						{#if clinics.length > 0}
							<div class="flex gap-2 overflow-x-auto p-3 border-b border-gray-100">
								{#each clinics as clinic}
									<button
										class="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-all"
										style="background: {selectedClinic?.id === clinic.id ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f1f5f9'};
											   color: {selectedClinic?.id === clinic.id ? 'white' : '#475569'};
											   border: 1px solid {selectedClinic?.id === clinic.id ? '#2563eb' : '#e2e8f0'};"
										onclick={async () => {
											selectedClinic = clinic;
											clinicPatients = await studentApi.getClinicPatients(clinic.id);
										}}
									>
										{clinic.name}
									</button>
								{/each}
							</div>
						{/if}
						{#each clinicPatients as cp}
							<div class="flex items-center gap-3 px-4 py-3 border-b border-gray-50">
								<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
									style="background: linear-gradient(to bottom, #60a5fa, #3b82f6);">
									<User class="w-5 h-5 text-white" />
								</div>
								<div class="flex-1 min-w-0">
									<p class="font-semibold text-gray-800 text-sm">{cp.patient_name}</p>
									<p class="text-xs text-gray-500 truncate">{cp.appointment_time} · {cp.provider_name}</p>
								</div>
								<span
									class="px-2 py-0.5 text-[10px] font-medium rounded-full shrink-0"
									style="background: {cp.status === 'Completed' ? 'rgba(34, 197, 94, 0.1)' : cp.status === 'In Progress' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(251, 191, 36, 0.1)'};
										   color: {cp.status === 'Completed' ? '#16a34a' : cp.status === 'In Progress' ? '#2563eb' : '#d97706'};"
								>
									{cp.status}
								</span>
							</div>
						{/each}
						{#if clinicPatients.length === 0}
							<div class="flex flex-col items-center justify-center py-16 text-center px-4">
								<Building class="w-8 h-8 text-gray-300 mb-2" />
								<p class="text-sm text-gray-400">No patients in this clinic</p>
							</div>
						{/if}

					{:else if studentTab === 'previous'}
						{#if previousPatientsLoading}
							<div class="flex items-center justify-center py-16">
								<div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
							</div>
						{:else}
							{#each previousPatients as ap}
								<button
									class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer border-b border-gray-50 hover:bg-gray-50"
									class:bg-blue-50={selectedPatient?.id === ap.id}
									onclick={() => {
										if (window.innerWidth < 768) {
											goto(`/patients/${ap.id}`);
										} else {
											selectedPatient = ap;
										}
									}}
								>
									<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
										style="background: linear-gradient(to bottom, #60a5fa, #3b82f6);">
										<User class="w-5 h-5 text-white" />
									</div>
									<div class="flex-1 min-w-0">
										<p class="font-semibold text-gray-800 text-sm">{ap.name}</p>
										<p class="text-xs text-gray-500 truncate">{ap.patient_id} · {ap.primary_diagnosis || 'No diagnosis'}</p>
									</div>
									<ChevronRight class="w-4 h-4 text-gray-400 shrink-0" />
								</button>
							{/each}
							{#if previousPatients.length === 0}
								<div class="flex flex-col items-center justify-center py-16 text-center px-4">
									<Clock class="w-8 h-8 text-gray-300 mb-2" />
									<p class="text-sm text-gray-400">No previous patients</p>
								</div>
							{/if}
						{/if}
					{/if}
				</div>
			</div>

			<!-- Right Panel: Detail (Desktop only) -->
			<div class="hidden md:flex flex-1 rounded-xl overflow-hidden flex-col"
				style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
				{#if selectedPatient}
					<div class="flex-1 overflow-y-auto relative">
						<button class="absolute top-3 right-3 z-10 w-8 h-8 rounded-full flex items-center justify-center cursor-pointer"
							style="background: rgba(255,255,255,0.9); box-shadow: 0 1px 4px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.08);"
							onclick={() => selectedPatient = null}>
							<X class="w-4 h-4 text-gray-500" />
						</button>
						<PatientProfile patientId={selectedPatient.id} />
					</div>
				{:else}
					<!-- Empty State -->
					<div class="flex-1 flex flex-col items-center justify-center text-center p-8">
						<div class="w-20 h-20 rounded-full flex items-center justify-center mb-4"
							style="background: linear-gradient(to bottom, #f0f4fa, #e2e8f0);">
							<Users class="w-10 h-10 text-gray-400" />
						</div>
						<h3 class="text-lg font-semibold text-gray-700 mb-1">Select a Patient</h3>
						<p class="text-sm text-gray-400 max-w-xs">
							Choose a patient from the sidebar to view their detailed profile, medical history, and active treatments.
						</p>
					</div>
				{/if}
			</div>
		</div>

	{:else if role === 'FACULTY' && faculty}
		<!-- Faculty Welcome Card (Matching Design) -->
		<AquaCard>
			<div class="flex items-center gap-4">
				<div class="relative shrink-0">
					{#if faculty.photo}
						<img src={faculty.photo} alt={faculty.name} class="w-16 h-16 rounded-full object-cover border-2 border-white shadow-md" />
					{:else}
						<Avatar name={faculty.name} size="lg" />
					{/if}
					<div class="absolute -bottom-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 2px solid white;">
						<GraduationCap class="w-3 h-3 text-white" />
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<h2 class="text-lg font-bold text-gray-800">Welcome, {faculty.name}</h2>
					<p class="text-sm text-gray-500">ID: {faculty.faculty_id} · Department: {faculty.department}</p>
				</div>
			</div>
		</AquaCard>

		

		<!-- Approval Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
			{#each approvalCards as card}
				<button
					class="w-full text-left cursor-pointer"
					onclick={() => goto(card.path)}
				>
					<AquaCard padding={false}>
						<div class="px-4 py-4 flex items-center gap-4">
							<div class="w-12 h-12 rounded-full flex items-center justify-center shrink-0"
								style="background: linear-gradient(to bottom, {card.color}20, {card.color}10); border: 1px solid {card.color}30;">
								<card.icon class="w-6 h-6" style="color: {card.color}" />
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-base font-semibold text-gray-800">{card.label}</p>
								<p class="text-sm text-gray-500">{card.count} pending approvals</p>
							</div>
							<ChevronRight class="w-5 h-5 text-gray-300 shrink-0" />
						</div>
					</AquaCard>
				</button>
			{/each}
		</div>

		<!-- Today's Schedule -->
		<AquaCard>
			{#snippet header()}
				<Calendar class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Today's Schedule</span>
			{/snippet}
			<div class="space-y-3">
				{#each todaySchedule as item}
					{@const colors = getScheduleColor(item.type)}
					<div class="p-3 rounded-lg" style="background: {colors.bg}; border-left: 3px solid {colors.text};">
						<p class="text-sm font-bold" style="color: {colors.text};">
							{item.time_start} - {item.time_end}
						</p>
						<p class="text-sm font-medium" style="color: {colors.text};">{item.title}</p>
					</div>
				{/each}

				{#if todaySchedule.length === 0}
					<p class="text-sm text-gray-400 text-center py-4">No scheduled items for today</p>
				{/if}
			</div>
		</AquaCard>
	{/if}
</div>
