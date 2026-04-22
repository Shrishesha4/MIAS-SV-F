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
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import PatientProfile from '$lib/components/PatientProfile.svelte';
	import { isHighlightedPatientCategory } from '$lib/utils/patient-category';
	import {
		HeartPulse, FileText, Pill, Activity, TestTube, Wallet,
		Bed, Calendar, Crown, Shield, AlertTriangle, ChevronRight, ChevronDown,
		GraduationCap, Users, CheckCircle, Clipboard, User,
		Award, BarChart3, RefreshCw, ArrowRight, Building,
		Phone, Mail, MessageSquare, CheckCircle2, Clock, CircleDot,
		PhoneCall, Hospital, ClipboardList, FileCheck, Save,
		Eye, X, LogIn, LogOut, Stethoscope, ExternalLink
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;

	type StudentPatientSelection = {
		id: string;
		rowId: string;
		patient_id: string;
		name: string;
		canEdit: boolean;
	};

	// Shared state
	let loading = $state(true);
	let error = $state('');
	let allocatedClinicNotice = $state<{ name: string; location: string } | null>(null);

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
	let selectedPatient: StudentPatientSelection | null = $state(null);
	let emergencyContacts: EmergencyContact[] = $state([]);
	let clinics: Clinic[] = $state([]);
	let selectedClinic: Clinic | null = $state(null);
	let clinicPatients: ClinicPatient[] = $state([]);
	let clinicSearch = $state('');
	let showAllPatients = $state(false);
	let previousPatients: any[] = $state([]);
	let previousPatientsLoading = $state(false);
	let expandedPrevPatient = $state<string | null>(null);
	let prevPatientDetails = $state<Record<string, { admissions: any[]; caseRecords: any[]; loading: boolean }>>({});
	let checkingIn = $state(false);
	let checkingOut = $state(false);

	const activeClinicSession = $derived(
		clinicSessions.find((s) => s.checked_in_at && !s.checked_out_at) ?? null
	);

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
	let admittedPatients: any[] = $state([]);
	let admittedPatientsTotal = $state(0);
	let admittedPatientsOffset = $state(0);
	const ADMITTED_PATIENTS_LIMIT = 50;
	let facultyClinics: any[] = $state([]);
	let facultyClinicSessions: any[] = $state([]);
	let selectedFacultyClinic: any = $state(null);
	let facultyClinicPatients: any[] = $state([]);
	let facultyClinicSearch = $state('');
	let facultyCheckingIn = $state(false);
	let facultyCheckingOut = $state(false);
	let facultyTab = $state('admitted');
	let facultyPatientSearch = $state('');

	const activeFacultyClinicSession = $derived(
		facultyClinicSessions.find((s) => s.checked_in_at && !s.checked_out_at) ?? null
	);

	const studentTabs = [
		{ id: 'clinic', label: 'Clinic' },
		{ id: 'today', label: 'Today' },
		{ id: 'previous', label: 'Previous' },
	];

	const facultyTabs = [
		{ id: 'admitted', label: 'My Admitted Patients' },
		{ id: 'clinic', label: 'Clinic View' },
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

	const assignedPatientIds = $derived(new Set(assignedPatients.map((patient) => patient.id)));

	const searchableClinics = $derived.by(() =>
		clinics.map((clinic) => ({
			...clinic,
			meta: [clinic.department, clinic.location, clinic.faculty_name].filter(Boolean).join(' · '),
		}))
	);

	const filteredClinicOptions = $derived.by(() => {
		const query = clinicSearch.trim().toLowerCase();
		if (!query) return searchableClinics;
		return searchableClinics.filter((clinic) =>
			[clinic.name, clinic.department, clinic.location, clinic.faculty_name]
				.filter(Boolean)
				.some((value) => String(value).toLowerCase().includes(query))
		);
	});

	const searchableFacultyClinics = $derived.by(() =>
		facultyClinics.map((clinic) => ({
			...clinic,
			meta: [clinic.department, clinic.location, clinic.faculty_name].filter(Boolean).join(' · '),
		}))
	);

	const filteredFacultyClinicOptions = $derived.by(() => {
		const query = facultyClinicSearch.trim().toLowerCase();
		if (!query) return searchableFacultyClinics;
		return searchableFacultyClinics.filter((clinic) =>
			[clinic.name, clinic.department, clinic.location, clinic.faculty_name]
				.filter(Boolean)
				.some((value) => String(value).toLowerCase().includes(query))
		);
	});

	const filteredAdmittedPatients = $derived.by(() => {
		if (!facultyPatientSearch.trim()) return admittedPatients;
		const search = facultyPatientSearch.toLowerCase();
		return admittedPatients.filter((p: any) =>
			p.patient_name?.toLowerCase().includes(search) ||
			p.patient_display_id?.toLowerCase().includes(search) ||
			p.diagnosis?.toLowerCase().includes(search)
		);
	});

	const filteredClinicPatients = $derived.by(() => {
		if (!facultyPatientSearch.trim()) return facultyClinicPatients;
		const search = facultyPatientSearch.toLowerCase();
		return facultyClinicPatients.filter((p: any) =>
			p.patient_name?.toLowerCase().includes(search) ||
			p.patient_id?.toLowerCase().includes(search)
		);
	});

	function openPatientCaseLog(patientId?: string | null) {
		if (!patientId) {
			toastStore.addToast('Patient record is not available', 'error');
			return;
		}
		void goto(`/patients/${patientId}`);
	}

	function clinicDisplayLabel(clinic: Clinic) {
		return clinic.name;
	}

	function toAssignedSelection(patient: AssignedPatient): StudentPatientSelection {
		return {
			id: patient.patient_db_id ?? patient.id,
			rowId: patient.assignment_id ?? patient.id,
			patient_id: patient.patient_id,
			name: patient.name,
			canEdit: patient.status === 'Active',
		};
	}

	async function togglePrevPatient(ap: any) {
		const key = ap.assignment_id ?? ap.id;
		if (expandedPrevPatient === key) {
			expandedPrevPatient = null;
			return;
		}
		expandedPrevPatient = key;
		if (!prevPatientDetails[key]) {
			prevPatientDetails[key] = { admissions: [], caseRecords: [], loading: true };
			try {
				const patDbId = ap.patient_db_id ?? ap.id;
				const [admissions, caseRecords] = await Promise.all([
					patientApi.getAdmissions(patDbId).catch(() => []),
					studentApi.getCaseRecords(student.id, patDbId).catch(() => []),
				]);
				prevPatientDetails[key] = { admissions, caseRecords, loading: false };
			} catch {
				prevPatientDetails[key] = { admissions: [], caseRecords: [], loading: false };
			}
		}
	}

	function toClinicSelection(patient: ClinicPatient): StudentPatientSelection | null {
		if (!patient.patient_db_id) return null;
		return {
			id: patient.patient_db_id,
			rowId: patient.patient_db_id,
			patient_id: patient.patient_id,
			name: patient.patient_name,
			canEdit: patient.is_assigned || assignedPatientIds.has(patient.patient_db_id),
		};
	}

	async function loadStudentClinicPatients(clinic: Clinic | null) {
		selectedPatient = null;
		selectedClinic = clinic;
		if (!clinic) {
			clinicPatients = [];
			return;
		}
		clinicSearch = clinicDisplayLabel(clinic);
		clinicPatients = await studentApi.getClinicPatients(student.id, clinic.id);
	}

	async function handleStudentClinicSelection(clinic: Clinic | null) {
		await loadStudentClinicPatients(clinic);
		if (!clinic || !student || activeClinicSession?.clinic_id === clinic.id) return;
		await handleCheckIn();
	}

	async function refreshStudentClinicState(preferredClinicId?: string | null) {
		if (!student) return;
		const sessions = await studentApi.getClinicSessions(student.id);
		clinicSessions = sessions;
		const targetClinicId =
			preferredClinicId ??
			sessions.find((session: any) => session.checked_in_at && !session.checked_out_at)?.clinic_id ??
			selectedClinic?.id ??
			null;
		if (!targetClinicId) {
			clinicPatients = [];
			return;
		}
		const clinic = clinics.find((item) => item.id === targetClinicId) ?? null;
		await loadStudentClinicPatients(clinic);
	}

	function handleClinicSearchInput(query: string) {
		if (selectedClinic && query !== clinicDisplayLabel(selectedClinic)) {
			selectedClinic = null;
			selectedPatient = null;
			clinicPatients = [];
		}
	}

	function clearClinicSelection() {
		clinicSearch = '';
		selectedClinic = null;
		selectedPatient = null;
		clinicPatients = [];
	}

	async function loadFacultyClinicPatients(clinic: any | null) {
		selectedFacultyClinic = clinic;
		if (!clinic) {
			facultyClinicPatients = [];
			return;
		}
		facultyClinicSearch = clinic.name;
		facultyClinicPatients = await facultyApi.getClinicPatients(clinic.id);
	}

	async function handleFacultyClinicSelection(clinic: any | null) {
		await loadFacultyClinicPatients(clinic);
		if (!clinic || !faculty || activeFacultyClinicSession?.clinic_id === clinic.id) return;
		await handleFacultyCheckIn();
	}

	async function refreshFacultyClinicState(preferredClinicId?: string | null) {
		if (!faculty) return;
		const sessions = await facultyApi.getClinicSessions(faculty.id);
		facultyClinicSessions = sessions;
		const targetClinicId =
			preferredClinicId ??
			sessions.find((session: any) => session.checked_in_at && !session.checked_out_at)?.clinic_id ??
			selectedFacultyClinic?.id ??
			null;
		if (!targetClinicId) {
			facultyClinicPatients = [];
			return;
		}
		const clinic = facultyClinics.find((item) => item.id === targetClinicId) ?? null;
		await loadFacultyClinicPatients(clinic);
	}

	function handleFacultyClinicSearchInput(query: string) {
		if (selectedFacultyClinic && query !== selectedFacultyClinic.name) {
			selectedFacultyClinic = null;
			facultyClinicPatients = [];
		}
	}

	function clearFacultyClinicSelection() {
		facultyClinicSearch = '';
		selectedFacultyClinic = null;
		facultyClinicPatients = [];
	}

	async function handleCheckIn() {
		if (!student || !selectedClinic) return;
		checkingIn = true;
		try {
			const result = await studentApi.checkInToClinic(student.id, selectedClinic.id);
			await refreshStudentClinicState(selectedClinic.id);
			if (result?.switched_from_clinic_name) {
				toastStore.addToast(`Switched from ${result.switched_from_clinic_name} to ${selectedClinic.name}`, 'success');
			} else if (result?.status === 'already_checked_in') {
				toastStore.addToast(`Already checked in to ${selectedClinic.name}`, 'success');
			} else {
				toastStore.addToast(`Checked in to ${selectedClinic.name}`, 'success');
			}
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail ?? 'Check-in failed', 'error');
		} finally {
			checkingIn = false;
		}
	}

	async function handleCheckOut() {
		if (!student || !activeClinicSession) return;
		checkingOut = true;
		try {
			await studentApi.checkOutClinic(student.id, activeClinicSession.id);
			await refreshStudentClinicState(selectedClinic?.id ?? activeClinicSession.clinic_id ?? null);
			toastStore.addToast('Checked out successfully', 'success');
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail ?? 'Check-out failed', 'error');
		} finally {
			checkingOut = false;
		}
	}

	async function handleFacultyCheckIn() {
		if (!faculty || !selectedFacultyClinic) return;
		facultyCheckingIn = true;
		try {
			const result = await facultyApi.checkInToClinic(faculty.id, selectedFacultyClinic.id);
			await refreshFacultyClinicState(selectedFacultyClinic.id);
			if (result?.switched_from_clinic_name) {
				toastStore.addToast(`Switched from ${result.switched_from_clinic_name} to ${selectedFacultyClinic.name}`, 'success');
			} else if (result?.status === 'already_checked_in') {
				toastStore.addToast(`Already checked in to ${selectedFacultyClinic.name}`, 'success');
			} else {
				toastStore.addToast(`Checked in to ${selectedFacultyClinic.name}`, 'success');
			}
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail ?? 'Faculty check-in failed', 'error');
		} finally {
			facultyCheckingIn = false;
		}
	}

	async function handleFacultyCheckOut() {
		if (!faculty || !activeFacultyClinicSession) return;
		facultyCheckingOut = true;
		try {
			await facultyApi.checkOutFromClinic(faculty.id, activeFacultyClinicSession.id);
			await refreshFacultyClinicState(selectedFacultyClinic?.id ?? activeFacultyClinicSession.clinic_id ?? null);
			toastStore.addToast('Checked out successfully', 'success');
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail ?? 'Faculty check-out failed', 'error');
		} finally {
			facultyCheckingOut = false;
		}
	}

	function openStudentPatient(selection: StudentPatientSelection | null) {
		if (!selection) {
			toastStore.addToast('Patient details are not available for this clinic appointment', 'error');
			return;
		}

		if (window.innerWidth < 768) {
			goto(selection.canEdit ? `/patients/${selection.id}` : `/patients/${selection.id}?mode=view`);
			return;
		}

		selectedPatient = selection;
	}

	// Handle patient updates from PatientProfile - sync with list
	function handlePatientUpdate(updatedPatient: any) {
		// Update in assignedPatients list
		assignedPatients = assignedPatients.map(p => {
			if (p.patient_db_id === updatedPatient.id || p.id === updatedPatient.id) {
				return {
					...p,
					name: updatedPatient.name,
					primary_diagnosis: updatedPatient.primary_diagnosis,
					diagnosis_entries: updatedPatient.diagnosis_entries,
					medical_alerts: updatedPatient.medical_alerts,
					allergies: updatedPatient.allergies,
				};
			}
			return p;
		});
		// Update in clinicPatients list
		clinicPatients = clinicPatients.map(p => {
			if (p.patient_db_id === updatedPatient.id) {
				return {
					...p,
					patient_name: updatedPatient.name,
				};
			}
			return p;
		});
		// Update in previousPatients list
		previousPatients = previousPatients.map(p => {
			if (p.patient_db_id === updatedPatient.id || p.id === updatedPatient.id) {
				return {
					...p,
					name: updatedPatient.name,
					primary_diagnosis: updatedPatient.primary_diagnosis,
				};
			}
			return p;
		});
		// Update in facultyClinicPatients list
		facultyClinicPatients = facultyClinicPatients.map(p => {
			if (p.patient_db_id === updatedPatient.id) {
				return {
					...p,
					patient_name: updatedPatient.name,
				};
			}
			return p;
		});
		// Update in admittedPatients list
		admittedPatients = admittedPatients.map(p => {
			if (p.patient_db_id === updatedPatient.id || p.id === updatedPatient.id) {
				return {
					...p,
					name: updatedPatient.name,
					primary_diagnosis: updatedPatient.primary_diagnosis,
				};
			}
			return p;
		});
	}

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

	function formatSessionWindow(patient: AssignedPatient): string | null {
		if (!patient.admission_date && !patient.discharge_date) return null;
		const start = patient.admission_date ? formatDate(patient.admission_date) : 'Unknown start';
		const end = patient.discharge_date ? formatDate(patient.discharge_date) : 'Open';
		return `${start} - ${end}`;
	}

	function getScheduleColor(type: string) {
		switch (type) {
			case 'consultation': return { bg: 'rgba(59, 130, 246, 0.1)', text: '#2563eb' };
			case 'meeting': return { bg: 'rgba(236, 72, 153, 0.1)', text: '#db2777' };
			case 'review': return { bg: 'rgba(34, 197, 94, 0.1)', text: '#16a34a' };
			default: return { bg: 'rgba(107, 114, 128, 0.1)', text: '#4b5563' };
		}
	}

	let loadingMoreAdmitted = $state(false);

	async function loadMoreAdmittedPatients() {
		if (loadingMoreAdmitted || admittedPatients.length >= admittedPatientsTotal) return;
		loadingMoreAdmitted = true;
		try {
			const newOffset = admittedPatientsOffset + ADMITTED_PATIENTS_LIMIT;
			const res = await facultyApi.getAdmittedPatients('Active', ADMITTED_PATIENTS_LIMIT, newOffset);
			admittedPatients = [...admittedPatients, ...(res.items || [])];
			admittedPatientsOffset = newOffset;
			admittedPatientsTotal = res.total || admittedPatientsTotal;
		} catch (err) {
			toastStore.addToast('Failed to load more patients', 'error');
		} finally {
			loadingMoreAdmitted = false;
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
		const noticeRaw = sessionStorage.getItem('allocatedClinicNotice');
		if (noticeRaw) {
			try {
				allocatedClinicNotice = JSON.parse(noticeRaw);
			} catch {
				allocatedClinicNotice = null;
			}
			sessionStorage.removeItem('allocatedClinicNotice');
		}

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
				const active = clinicSessions.find((s: any) => s.checked_in_at && !s.checked_out_at);
				if (active && active.clinic_id) {
					const activeClinic = clinics.find((c) => c.id === active.clinic_id) ?? null;
					await loadStudentClinicPatients(activeClinic ?? (clinics[0] || null));
				} else if (clinics.length > 0) {
					await loadStudentClinicPatients(clinics[0]);
				}
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
				approvals = await facultyApi.getApprovals(faculty.id);
				approvalStats = await approvalsApi.getApprovalStats(faculty.id);
				todaySchedule = await approvalsApi.getTodaySchedule(faculty.id);
				const admissionsRes = await facultyApi.getAdmittedPatients('Active', ADMITTED_PATIENTS_LIMIT, 0);
				admittedPatients = admissionsRes.items || [];
				admittedPatientsTotal = admissionsRes.total || 0;
				admittedPatientsOffset = 0;
				const [clinicList, clinicSessionList] = await Promise.all([
					facultyApi.getFacultyClinics(faculty.id),
					facultyApi.getClinicSessions(faculty.id),
				]);
				facultyClinics = clinicList;
				facultyClinicSessions = clinicSessionList;
				const activeFacultyClinicId = clinicSessionList.find((session: any) => session.checked_in_at && !session.checked_out_at)?.clinic_id;
				const initialFacultyClinic =
					clinicList.find((clinic: any) => clinic.id === activeFacultyClinicId) ??
					clinicList[0] ??
					null;
				if (initialFacultyClinic) {
					await loadFacultyClinicPatients(initialFacultyClinic);
				}
			} else if (role === 'LAB_TECHNICIAN') {
				goto('/labs' as string);
				return;
			} else if (role === 'NURSE') {
				// Redirect nurses to their station dashboard
				goto('/nurse-station');
				return;
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
					<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="lg" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<h2 class="text-lg font-bold text-gray-800">Welcome, {patient.name}</h2>
							{#if isHighlightedPatientCategory(patient.category)}
								<Crown class="w-4 h-4 text-yellow-500 shrink-0" />
							{/if}
						</div>
						<p class="text-sm text-gray-500">
							ID: {patient.patient_id}
							{#if dashboard?.last_visit}
								<span class="mx-1">·</span> Last visit: {formatDate(dashboard.last_visit)}
							{/if}
						</p>
						{#if patient.clinic_name}
							<p class="text-xs text-blue-600 flex items-center gap-1 mt-0.5">
								<Building class="w-3 h-3" /> {patient.clinic_name}
							</p>
						{/if}
						<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact />
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
		<div class="flex gap-0 md:gap-4 overflow-hidden" style="height: calc(100dvh - 4rem);">
			<!-- Left Panel: Patient List -->
			<div class="w-full md:w-80 lg:w-96 flex flex-col shrink-0 rounded-xl overflow-hidden"
				style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
				<!-- Tabs -->
				<div class="p-2">
					<TabBar tabs={studentTabs} activeTab={studentTab} variant="jiggle" ariaLabel="Student patient views" onchange={async (id) => {
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
								class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer border-b border-gray-200 hover:bg-gray-50"
								class:bg-blue-50={selectedPatient?.rowId === (ap.assignment_id ?? ap.id)}
								onclick={() => openStudentPatient(toAssignedSelection(ap))}
							>
								<PatientInsuranceAvatar name={ap.name} src={ap.photo} size="sm" insurancePolicies={ap.insurance_policies} patientCategory={ap.category} patientCategoryColorPrimary={ap.category_color_primary} patientCategoryColorSecondary={ap.category_color_secondary} />
								<div class="flex-1 min-w-0">
									<p class="font-semibold text-gray-800 text-sm">{ap.name}</p>
									<p class="text-xs text-gray-500 truncate">{ap.patient_id} · {ap.primary_diagnosis || 'No diagnosis'}</p>
									<InsuranceTypeBadges insurancePolicies={ap.insurance_policies} compact maxVisible={2} />
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
							<div class="p-3 border-b border-gray-100 space-y-2">
								<Autocomplete
									items={filteredClinicOptions}
									labelKey="name"
									sublabelKey="meta"
									minChars={0}
									placeholder="Search and select clinic..."
									bind:value={clinicSearch}
									onInput={handleClinicSearchInput}
									onSelect={(clinic) => void handleStudentClinicSelection(clinic as Clinic)}
									onClear={clearClinicSelection}
								/>
								{#if selectedClinic}
									<p class="text-xs text-gray-500">{selectedClinic.department} · {selectedClinic.location}</p>
								{/if}
								{#if activeClinicSession && activeClinicSession.clinic_id === selectedClinic?.id}
									<!-- Checked In Banner -->
									<div class="flex items-center justify-between px-3 py-2 rounded-lg" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25);">
										<div class="flex items-center gap-2">
											<CheckCircle2 class="w-4 h-4 text-emerald-600 shrink-0" />
											<div>
												<p class="text-xs font-semibold text-emerald-700">Checked In</p>
												<p class="text-[11px] text-emerald-600">Since {new Date(activeClinicSession.checked_in_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</p>
											</div>
										</div>
										<button
											class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-60"
											style="background: linear-gradient(to bottom, #ef4444, #dc2626); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
											disabled={checkingOut}
											onclick={handleCheckOut}
										>
											{#if checkingOut}
												<div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
											{:else}
												<LogOut class="w-3 h-3" />
											{/if}
											Check Out
										</button>
									</div>
								{:else if selectedClinic}
									<div class="flex items-center gap-2 px-3 py-2 rounded-lg" style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2);">
										{#if checkingIn}
											<div class="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin shrink-0"></div>
											<p class="text-xs text-blue-700">Checking in to <span class="font-semibold">{selectedClinic.name}</span>...</p>
										{:else}
											<Building class="w-4 h-4 text-blue-600 shrink-0" />
											<p class="text-xs text-blue-700">
												{#if activeClinicSession && activeClinicSession.clinic_id !== selectedClinic.id}
													Choosing <span class="font-semibold">{selectedClinic.name}</span> above will switch your active clinic immediately.
												{:else}
													Selecting a clinic above checks you in immediately.
												{/if}
											</p>
										{/if}
									</div>
								{/if}
							</div>
						{/if}
						{#each clinicPatients as cp}
							<button
								class="w-full flex items-center gap-3 px-4 py-3 text-left border-b border-gray-50 transition-colors cursor-pointer hover:bg-gray-50"
								class:bg-blue-50={selectedPatient?.rowId === cp.patient_db_id}
								onclick={() => openStudentPatient(toClinicSelection(cp))}
							>
								<PatientInsuranceAvatar name={cp.patient_name} src={cp.photo} size="sm" insurancePolicies={cp.insurance_policies} patientCategory={cp.category} patientCategoryColorPrimary={cp.category_color_primary} patientCategoryColorSecondary={cp.category_color_secondary} />
								<div class="flex-1 min-w-0">
									<p class="font-semibold text-gray-800 text-sm">{cp.patient_name}</p>
									<p class="text-xs text-gray-500 truncate">{cp.appointment_time} · {cp.provider_name}</p>
									<InsuranceTypeBadges insurancePolicies={cp.insurance_policies} compact maxVisible={2} />
									<!-- <p class="mt-1 text-[11px] font-medium {cp.is_assigned || (cp.patient_db_id && assignedPatientIds.has(cp.patient_db_id)) ? 'text-emerald-600' : 'text-amber-600'}">
										{cp.is_assigned || (cp.patient_db_id && assignedPatientIds.has(cp.patient_db_id)) ? 'Assigned to you · edit enabled' : 'View only · not assigned to you'}
									</p> -->
								</div>
								<div class="flex flex-col items-end gap-1 shrink-0">
									<span
										class="px-2 py-0.5 text-[10px] font-medium rounded-full"
										style="background: {cp.status === 'Completed' ? 'rgba(34, 197, 94, 0.1)' : cp.status === 'In Progress' ? 'rgba(59, 130, 246, 0.1)' : 'rgba(251, 191, 36, 0.1)'};
											   color: {cp.status === 'Completed' ? '#16a34a' : cp.status === 'In Progress' ? '#2563eb' : '#d97706'};"
									>
										{cp.status}
									</span>
									<span class="text-[11px] font-semibold text-blue-600">{cp.is_assigned || (cp.patient_db_id && assignedPatientIds.has(cp.patient_db_id)) ? 'Edit' : 'View'}</span>
								</div>
							</button>
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
{@const key = ap.assignment_id ?? ap.id}
{@const isExpanded = expandedPrevPatient === key}
{@const details = prevPatientDetails[key]}
<div class="border-b border-gray-100">
<!-- Card Header — tap to expand -->
<button
class="w-full flex items-start gap-3 px-4 py-3 text-left transition-colors cursor-pointer hover:bg-gray-50"
class:bg-blue-50={isExpanded}
onclick={() => togglePrevPatient(ap)}
>
<PatientInsuranceAvatar name={ap.name} src={ap.photo} size="sm" insurancePolicies={ap.insurance_policies} patientCategory={ap.category} patientCategoryColorPrimary={ap.category_color_primary} patientCategoryColorSecondary={ap.category_color_secondary} />
<div class="flex-1 min-w-0">
<p class="font-semibold text-gray-800 text-sm">{ap.name}</p>
<p class="text-xs text-gray-500">{ap.patient_id}{ap.age ? ` · ${ap.age}y` : ''}{ap.gender ? ` · ${ap.gender}` : ''}{ap.blood_group ? ` · ${ap.blood_group}` : ''}</p>
<p class="text-xs text-gray-500 truncate mt-0.5">{ap.primary_diagnosis || 'No diagnosis recorded'}</p>
<div class="flex items-center gap-1.5 mt-1 flex-wrap">
{#if ap.discharge_date}
<span class="inline-flex items-center gap-0.5 text-[10px] text-gray-400"><Calendar class="w-2.5 h-2.5" /> Discharged {new Date(ap.discharge_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' })}</span>
{:else if ap.assigned_date}
<span class="inline-flex items-center gap-0.5 text-[10px] text-gray-400"><Calendar class="w-2.5 h-2.5" /> {new Date(ap.assigned_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' })}</span>
{/if}
{#if ap.department}
<span class="text-[10px] text-gray-400">· {ap.department}</span>
{/if}
</div>
<div class="flex items-center gap-1.5 mt-1 flex-wrap">
{#if ap.case_record_count > 0}
<span class="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full font-medium" style="background: rgba(59,130,246,0.1); color: #2563eb;">
<FileText class="w-2.5 h-2.5" />{ap.case_record_count} record{ap.case_record_count !== 1 ? 's' : ''}
</span>
{/if}
{#if ap.total_admissions > 0}
<span class="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full font-medium" style="background: rgba(16,185,129,0.1); color: #059669;">
<Bed class="w-2.5 h-2.5" />{ap.total_admissions} admission{ap.total_admissions !== 1 ? 's' : ''}
</span>
{/if}
<InsuranceTypeBadges insurancePolicies={ap.insurance_policies} compact maxVisible={2} />
</div>
</div>
<div class="shrink-0 mt-1 transition-transform duration-200" class:rotate-180={isExpanded}>
<ChevronDown class="w-4 h-4 text-gray-400" />
</div>
</button>

<!-- Expanded Detail Section -->
{#if isExpanded}
<div class="px-4 pb-4 space-y-3" style="background: #f8faff;">
{#if details?.loading}
<div class="flex items-center justify-center py-4">
<div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
</div>
{:else}
<!-- Open Full Profile Button -->
<button
class="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold cursor-pointer mt-1"
style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 1px 3px rgba(37,99,235,0.35);"
onclick={(e) => { e.stopPropagation(); openStudentPatient(toAssignedSelection(ap)); }}
>
<ExternalLink class="w-3.5 h-3.5" /> View Full Profile
</button>

<!-- Admissions -->
{#if details?.admissions?.length}
<div>
<p class="text-[11px] font-bold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
<Bed class="w-3 h-3" /> Admissions ({details.admissions.length})
</p>
<div class="space-y-1.5">
{#each details.admissions as adm}
<div class="rounded-lg px-3 py-2 border" style="background: white; border-color: rgba(0,0,0,0.08);">
<div class="flex items-start justify-between gap-2">
<div class="min-w-0">
<p class="text-xs font-semibold text-gray-700">{adm.ward || adm.department || 'Ward —'}</p>
<p class="text-[11px] text-gray-500 mt-0.5 truncate">{adm.diagnosis || adm.admission_reason || '—'}</p>
<p class="text-[10px] text-gray-400 mt-0.5">
{adm.admission_date ? new Date(adm.admission_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' }) : '—'}
{#if adm.discharge_date}
→ {new Date(adm.discharge_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' })}
{:else}
· Active
{/if}
</p>
</div>
<span class="text-[10px] px-1.5 py-0.5 rounded-full shrink-0 font-medium"
style="{adm.status === 'Discharged' ? 'background:rgba(16,185,129,0.1);color:#059669' : adm.status === 'Active' ? 'background:rgba(59,130,246,0.1);color:#2563eb' : 'background:rgba(156,163,175,0.15);color:#6b7280'}"
>{adm.status}</span>
</div>
</div>
{/each}
</div>
</div>
{:else}
<p class="text-[11px] text-gray-400 text-center py-1 flex items-center justify-center gap-1"><Bed class="w-3 h-3" /> No admissions</p>
{/if}

<!-- Case Records -->
{#if details?.caseRecords?.length}
<div>
<p class="text-[11px] font-bold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
<FileText class="w-3 h-3" /> Case Records ({details.caseRecords.length})
</p>
<div class="space-y-1.5">
{#each details.caseRecords as cr}
<div class="rounded-lg px-3 py-2 border" style="background: white; border-color: rgba(0,0,0,0.08);">
<div class="flex items-start justify-between gap-2">
<div class="min-w-0 flex-1">
<p class="text-xs font-semibold text-gray-700 truncate">{cr.procedure_name || cr.form_name || cr.type || 'Case Record'}</p>
{#if cr.description}
<p class="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{cr.description}</p>
{/if}
{#if cr.findings}
<p class="text-[11px] text-gray-500 mt-0.5"><span class="font-medium">Findings:</span> {cr.findings}</p>
{/if}
{#if cr.diagnosis}
<p class="text-[11px] text-gray-500 mt-0.5"><span class="font-medium">Dx:</span> {cr.diagnosis}</p>
{/if}
{#if cr.treatment}
<p class="text-[11px] text-gray-500 mt-0.5"><span class="font-medium">Tx:</span> {cr.treatment}</p>
{/if}
<p class="text-[10px] text-gray-400 mt-0.5">
{cr.date ? new Date(cr.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' }) : '—'}
{cr.department ? ` · ${cr.department}` : ''}
</p>
</div>
<span class="text-[10px] px-1.5 py-0.5 rounded-full shrink-0 font-medium"
style="{cr.status === 'APPROVED' ? 'background:rgba(16,185,129,0.1);color:#059669' : cr.status === 'PENDING' ? 'background:rgba(245,158,11,0.1);color:#d97706' : 'background:rgba(156,163,175,0.15);color:#6b7280'}"
>{cr.status || 'Draft'}</span>
</div>
</div>
{/each}
</div>
</div>
{:else}
<p class="text-[11px] text-gray-400 text-center py-1 flex items-center justify-center gap-1"><FileText class="w-3 h-3" /> No case records</p>
{/if}
{/if}
</div>
{/if}
</div>
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
						<!-- <button class="absolute top-3 right-3 z-10 w-8 h-8 rounded-full flex items-center justify-center cursor-pointer"
							style="background: rgba(255,255,255,0.9); box-shadow: 0 1px 4px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.08);"
							onclick={() => selectedPatient = null}>
							<X class="w-4 h-4 text-gray-500" />
						</button> -->
						<PatientProfile patientId={selectedPatient.id} canEdit={selectedPatient.canEdit} onpatientupdate={handlePatientUpdate} />
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

		<div class="text-base font-bold text-gray-700 mb-2">Approvals</div>

		<!-- Approval Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
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
								<p class="text-sm font-semibold text-gray-800 leading-tight">{card.label}</p>
								<p class="text-xs text-gray-500 mt-0.5">{card.count} pending approval requests</p>
							</div>
							<ChevronRight class="w-5 h-5 text-gray-300 shrink-0" />
						</div>
					</AquaCard>
				</button>
			{/each}
		</div>

		<!-- Patient List with Tabs -->
		<AquaCard padding={false}>
			<!-- Tabs -->
			<div class="border-b border-gray-200">
				<div class="flex">
					<button
						class="flex-1 px-4 py-3 text-sm font-medium transition-colors"
						class:border-b-2={facultyTab === 'admitted'}
						class:border-blue-500={facultyTab === 'admitted'}
						class:text-blue-600={facultyTab === 'admitted'}
						class:text-gray-500={facultyTab !== 'admitted'}
						onclick={() => { facultyTab = 'admitted'; facultyPatientSearch = ''; }}
						style={facultyTab === 'admitted' ? 'background: rgba(59, 130, 246, 0.03);' : ''}
						type="button"
					>
						<div class="flex items-center justify-center gap-2">
							<Bed class="w-4 h-4" />
							My Admitted Patients
						</div>
					</button>
					<button
						class="flex-1 px-4 py-3 text-sm font-medium transition-colors"
						class:border-b-2={facultyTab === 'clinic'}
						class:border-blue-500={facultyTab === 'clinic'}
						class:text-blue-600={facultyTab === 'clinic'}
						class:text-gray-500={facultyTab !== 'clinic'}
						onclick={() => { facultyTab = 'clinic'; facultyPatientSearch = ''; }}
						style={facultyTab === 'clinic' ? 'background: rgba(59, 130, 246, 0.03);' : ''}
						type="button"
					>
						<div class="flex items-center justify-center gap-2">
							<Building class="w-4 h-4" />
							Clinic View
						</div>
					</button>
				</div>
			</div>

			<!-- Search Bar -->
			<div class="p-3 border-b border-gray-100 space-y-3">
				{#if facultyTab === 'clinic' && facultyClinics.length > 0}
					<div class="space-y-2">
						<Autocomplete
							items={filteredFacultyClinicOptions}
							labelKey="name"
							sublabelKey="meta"
							minChars={0}
							placeholder="Search and select clinic..."
							bind:value={facultyClinicSearch}
							onInput={handleFacultyClinicSearchInput}
							onSelect={(clinic) => void handleFacultyClinicSelection(clinic)}
							onClear={clearFacultyClinicSelection}
						/>
						{#if selectedFacultyClinic}
							<p class="text-xs text-gray-500">{selectedFacultyClinic.department} · {selectedFacultyClinic.location}</p>
							{#if activeFacultyClinicSession && activeFacultyClinicSession.clinic_id === selectedFacultyClinic.id}
								<div class="flex items-center justify-between px-3 py-2 rounded-lg" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.25);">
									<div class="flex items-center gap-2">
										<CheckCircle2 class="w-4 h-4 text-emerald-600 shrink-0" />
										<div>
											<p class="text-xs font-semibold text-emerald-700">Checked In</p>
											<p class="text-[11px] text-emerald-600">Since {new Date(activeFacultyClinicSession.checked_in_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</p>
										</div>
									</div>
									<button
										class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-60"
										style="background: linear-gradient(to bottom, #ef4444, #dc2626); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
										disabled={facultyCheckingOut}
										onclick={handleFacultyCheckOut}
									>
										{#if facultyCheckingOut}
											<div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
										{:else}
											<LogOut class="w-3 h-3" />
										{/if}
										Check Out
									</button>
								</div>
							{:else}
								<div class="flex items-center gap-2 px-3 py-2 rounded-lg" style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2);">
									{#if facultyCheckingIn}
										<div class="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin shrink-0"></div>
										<p class="text-xs text-blue-700">Checking in to <span class="font-semibold">{selectedFacultyClinic.name}</span>...</p>
									{:else}
										<Building class="w-4 h-4 text-blue-600 shrink-0" />
										<p class="text-xs text-blue-700">
											{#if activeFacultyClinicSession && activeFacultyClinicSession.clinic_id !== selectedFacultyClinic.id}
												Choosing <span class="font-semibold">{selectedFacultyClinic.name}</span> above will switch your active clinic immediately.
											{:else}
												Selecting a clinic above checks you in immediately.
											{/if}
										</p>
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
				<div class="relative">
					<input
						type="text"
						bind:value={facultyPatientSearch}
						placeholder={facultyTab === 'admitted' ? 'Search admitted patients...' : 'Search clinic patients...'}
						class="w-full px-4 py-2 pl-10 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-400"
					/>
					<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
						<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.35-4.35"></path></svg>
					</div>
				</div>
			</div>

			<!-- Patient List -->
			<div class="max-h-96 overflow-y-auto">
				{#if facultyTab === 'admitted'}
					{#each filteredAdmittedPatients as patient}
						<button
							class="w-full p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors text-left cursor-pointer"
							onclick={() => openPatientCaseLog(patient.patient_id)}
							type="button"
						>
							<div class="flex items-start gap-3">
								<PatientInsuranceAvatar name={patient.patient_name || 'Patient'} src={patient.photo} size="md" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
								<div class="flex-1 min-w-0">
									<div class="flex items-start justify-between gap-2">
										<div class="flex-1 min-w-0">
											<p class="font-semibold text-gray-800 text-sm">{patient.patient_name}</p>
											<p class="text-xs text-gray-500">45y, Male</p>
											<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
										</div>
										<StatusBadge variant={patient.status === 'Active' ? 'success' : patient.status === 'Critical' ? 'critical' : 'warning'}>
											{patient.status === 'Active' ? 'STABLE' : patient.status === 'Critical' ? 'Critical' : 'Under Observation'}
										</StatusBadge>
									</div>
									<div class="mt-1.5 space-y-0.5">
										<div class="flex items-center gap-1.5 text-xs text-gray-600">
											<Bed class="w-3 h-3" />
											<span>Admitted: {new Date(patient.admission_date).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })}</span>
										</div>
										<div class="flex items-center gap-1.5 text-xs text-gray-600">
											<CircleDot class="w-3 h-3" />
											<span>{patient.reason || patient.diagnosis || 'No diagnosis recorded'}</span>
										</div>
										{#if patient.diagnosis && patient.reason && patient.diagnosis !== patient.reason}
											<div class="flex flex-wrap gap-1 mt-1">
												<span class="px-2 py-0.5 rounded-full text-[10px] font-medium" style="background: rgba(239, 68, 68, 0.1); color: #dc2626;">Penicillin Allergy</span>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</button>
					{/each}
					{#if filteredAdmittedPatients.length === 0}
						<div class="py-12 text-center">
							<Bed class="w-12 h-12 text-gray-300 mx-auto mb-2" />
							<p class="text-sm text-gray-400">{facultyPatientSearch ? 'No patients found' : 'No admitted patients'}</p>
						</div>
					{:else if !facultyPatientSearch && admittedPatients.length < admittedPatientsTotal}
						<div class="p-4 text-center border-t border-gray-100">
							<p class="text-xs text-gray-500 mb-2">Showing {admittedPatients.length} of {admittedPatientsTotal} patients</p>
							<button
								onclick={loadMoreAdmittedPatients}
								disabled={loadingMoreAdmitted}
								class="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
							>
								{loadingMoreAdmitted ? 'Loading...' : 'Load More'}
							</button>
						</div>
					{/if}
				{:else if facultyTab === 'clinic'}
					{#each filteredClinicPatients as patient}
						<button
							class="w-full p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors text-left cursor-pointer"
							onclick={() => openPatientCaseLog(patient.patient_db_id)}
							type="button"
						>
							<div class="flex items-start gap-3">
								<PatientInsuranceAvatar name={patient.patient_name || 'Patient'} src={patient.photo} size="md" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
								<div class="flex-1 min-w-0">
									<p class="font-semibold text-gray-800 text-sm">{patient.patient_name}</p>
									<p class="text-xs text-gray-500">({patient.patient_id})</p>
									<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
									<div class="mt-1.5 space-y-0.5">
										<div class="flex items-center gap-1.5 text-xs text-gray-600">
											<Clock class="w-3 h-3" />
											<span>32y, Female · {patient.appointment_time}</span>
										</div>
										<div class="flex items-center gap-1 mt-1">
											<span class="px-2 py-0.5 rounded text-[10px] font-semibold" style="background: rgba(59, 130, 246, 0.1); color: #2563eb;">{patient.status || 'Scheduled'}</span>
											{#if patient.provider_name}
												<span class="text-[10px] text-gray-500">· {patient.provider_name}</span>
											{/if}
										</div>
									</div>
								</div>
							</div>
						</button>
					{/each}
					{#if filteredClinicPatients.length === 0}
						<div class="py-12 text-center">
							<Building class="w-12 h-12 text-gray-300 mx-auto mb-2" />
							<p class="text-sm text-gray-400">{facultyPatientSearch ? 'No patients found' : 'No clinic appointments today'}</p>
						</div>
					{/if}
				{/if}
			</div>
		</AquaCard>
	{/if}
</div>

{#if allocatedClinicNotice}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
		<div class="bg-white rounded-2xl p-8 max-w-md mx-4 text-center shadow-2xl">
			<div class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
				 style="background: linear-gradient(to bottom, #e8f0fe, #d0e1fd);">
				<Hospital class="w-8 h-8 text-blue-600" />
			</div>
			<h2 class="text-2xl font-bold text-gray-800 mb-2">Clinic Allocated!</h2>
			<p class="text-gray-600 mb-6">Please proceed to your allotted clinic:</p>
			<div class="rounded-xl p-4 mb-6"
				 style="background: linear-gradient(to bottom, #eef4ff, #e0eaff); border: 1.5px solid #93b8f5;">
				<p class="text-lg font-bold text-blue-800">{allocatedClinicNotice.name}</p>
				<p class="text-sm text-gray-600 mt-1">{allocatedClinicNotice.location}</p>
			</div>
			<p class="text-sm text-gray-500 mb-6">Your registration is complete and you are now logged in.</p>
			<button
				class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90"
				style="background: linear-gradient(to bottom, #4d90fe, #3b7aed); box-shadow: 0 2px 8px rgba(59,122,237,0.4); border: 1px solid rgba(0,0,0,0.1);"
				onclick={() => (allocatedClinicNotice = null)}
			>
				I Understand <CheckCircle2 class="w-4 h-4" />
			</button>
		</div>
	</div>
{/if}
