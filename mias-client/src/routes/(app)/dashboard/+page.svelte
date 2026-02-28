<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { patientApi, type PatientDashboard, type ActiveMedication, type Appointment } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import { approvalsApi, type ApprovalStats, type ScheduleItem } from '$lib/api/approvals';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
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
	let assignedPatients: any[] = $state([]);
	let clinicSessions: any[] = $state([]);
	let studentTab = $state('patients');

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
		{ id: 'patients', label: 'My Patients', icon: Users },
		{ id: 'clinic', label: 'Clinic', icon: Hospital },
		{ id: 'emergency', label: 'Emergency', icon: PhoneCall },
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
			label: 'Discharge Summary Approvals',
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
	const medicalAlertsText = $derived(() => {
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

	function handleMedicationTaken() {
		showMedicationReminder = false;
		// TODO: API call to mark medication as taken
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
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
				approvals = await facultyApi.getApprovals(faculty.id);
				approvalStats = await approvalsApi.getApprovalStats(faculty.id);
				todaySchedule = await approvalsApi.getTodaySchedule(faculty.id);
			}
		} catch (err: any) {
			error = 'Failed to load dashboard data';
			console.error(err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
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
			{#if medicalAlertsText()}
				<div class="px-4 py-2.5 flex items-center gap-2"
					style="background: linear-gradient(to bottom, #fef2f2, #fee2e2); border-top: 1px solid #fecaca;">
					<AlertTriangle class="w-4 h-4 text-red-500 shrink-0" />
					<p class="text-sm text-red-700 font-medium truncate">{medicalAlertsText()}</p>
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
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
						       box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);"
						onclick={handleMedicationTaken}
					>
						Taken
					</button>
				</div>
			</AquaCard>
		{/if}

		<!-- PATIENT SERVICES Section -->
		<div>
			<p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 px-1">Patient Services</p>
			<div class="grid grid-cols-2 gap-3">
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
					<span class="text-sm font-semibold text-gray-800 truncate">Admission Recor...</span>
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
			<div class="grid grid-cols-2 gap-3">
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
		<!-- Student Welcome Card -->
		<AquaCard>
			<div class="flex items-center gap-4">
				<div class="relative">
					<Avatar name={student.name} size="lg" />
					<div class="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 2px solid white;">
						<CheckCircle2 class="w-3 h-3 text-white" />
					</div>
				</div>
				<div class="flex-1">
					<h2 class="text-lg font-bold text-gray-800">Welcome, {student.name}</h2>
					<p class="text-sm text-gray-500">
						ID: {student.student_id} · Year: {student.year} · Semester: {student.semester}
					</p>
				</div>
			</div>
			<!-- Stats Row -->
			<div class="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<Award class="w-4 h-4 text-gray-500" />
					<span class="text-sm text-gray-700">Current GPA: <strong>{student.gpa}/4.0</strong></span>
				</div>
				<button class="flex items-center gap-1 text-sm text-blue-600 font-medium cursor-pointer hover:underline"
					onclick={() => goto('/profile')}>
					<BarChart3 class="w-4 h-4" /> Scores
				</button>
			</div>
			<div class="mt-1">
				<span class="text-sm text-gray-500">Attendance: {student.attendance?.overall ?? '--'}%</span>
			</div>
		</AquaCard>

		<!-- Tab Bar -->
		<TabBar tabs={studentTabs} activeTab={studentTab} onchange={(id) => studentTab = id} />

		<!-- Tab Content -->
		{#if studentTab === 'patients'}
			<!-- My Patients Tab -->
			<AquaCard>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<Users class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Patients Assigned to Me</h3>
					</div>
					<button
						class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer"
						style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
						       color: #1e40af; border: 1px solid rgba(0,0,0,0.15);
						       box-shadow: 0 1px 2px rgba(0,0,0,0.08);"
					>
						<RefreshCw class="w-3 h-3" /> Refresh List
					</button>
				</div>

				<div class="space-y-1">
					{#each assignedPatients as patient}
						<button
							class="w-full flex items-center gap-3 p-3 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors text-left"
							onclick={() => goto(`/patients/${patient.id}`)}
						>
							<Avatar name={patient.name} size="md" />
							<div class="flex-1 min-w-0">
								<p class="font-semibold text-gray-800">{patient.name}</p>
								<p class="text-xs text-gray-500">{patient.status}</p>
							</div>
							<div class="text-right shrink-0">
								<p class="text-xs text-gray-400 font-mono">{patient.patient_id}</p>
							</div>
							<div
								class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
								style="background: linear-gradient(to bottom, #e8edf5, #d5dde8);
								       border: 1px solid rgba(0,0,0,0.1);"
							>
								<ArrowRight class="w-3.5 h-3.5 text-blue-600" />
							</div>
						</button>
					{/each}
				</div>

				<div class="mt-4 flex justify-center">
					<button
						class="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
						       color: white; border: 1px solid rgba(0,0,0,0.15);
						       box-shadow: 0 2px 6px rgba(0,102,204,0.3), inset 0 1px 0 rgba(255,255,255,0.3);"
					>
						View All Patients <ChevronRight class="w-4 h-4" />
					</button>
				</div>
			</AquaCard>

		{:else if studentTab === 'clinic'}
			<!-- Clinic Tab -->
			<AquaCard>
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<Building class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Clinic Sessions</h3>
					</div>
				</div>
				{#if clinicSessions.length > 0}
					<div class="space-y-2">
						{#each clinicSessions as session}
							<div class="p-3 rounded-lg bg-gray-50 flex items-center justify-between">
								<div>
									<p class="text-sm font-semibold text-gray-800">{session.clinic_name}</p>
									<p class="text-xs text-gray-500">{session.department} · {session.date}</p>
								</div>
								<StatusBadge variant={session.status === 'Completed' ? 'success' : 'info'}>
									{session.status}
								</StatusBadge>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-400 text-center py-4">No clinic sessions found</p>
				{/if}
			</AquaCard>

			<AquaCard>
				<div class="flex items-center gap-2 mb-3">
					<PhoneCall class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Emergency Contacts</h3>
				</div>
				<p class="text-sm text-gray-500 text-center py-4">Contact your department head for emergency assistance.</p>
			</AquaCard>

		{:else if studentTab === 'emergency'}
			<!-- Emergency Tab -->
			<AquaCard>
				<div class="flex items-center gap-2 mb-3">
					<PhoneCall class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Emergency Contacts</h3>
				</div>
				<p class="text-sm text-gray-500 text-center py-4">Contact desk: +91 44 2345 6789</p>
			</AquaCard>
		{/if}

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
		<div class="space-y-3">
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
