<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { autocompleteApi, type DiagnosisSuggestion } from '$lib/api/autocomplete';
	import { getProcedureFields, type ProcedureField } from '$lib/config/procedure-fields';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import { Chart, registerables } from 'chart.js';
	import {
		Search, ChevronRight, Users, FileText, HeartPulse, Pill, Clock, Plus,
		CheckCircle2, User, Thermometer, Droplet, Activity, Scale, Wind, CircleDot,
		Phone, Edit, X, Trash2, CheckCircle, Send, History, AlertTriangle,
		ClipboardList, ArrowLeft
	} from 'lucide-svelte';

	Chart.register(...registerables);

	// ── List state ────────────────────────────────────────────────
	let listSearch = $state('');
	let listTab = $state<'clinic' | 'today' | 'previous'>('clinic');
	let assignedPatients: any[] = $state([]);
	let loading = $state(true);
	let studentData: any = $state(null);

	// ── Selected patient ──────────────────────────────────────────
	let selectedPatientId: string | null = $state(null);
	let mobileShowDetail = $state(false);
	let loadingDetail = $state(false);

	// ── Patient detail state ──────────────────────────────────────
	let patient: any = $state(null);
	let caseRecords: any[] = $state([]);
	let vitals: any[] = $state([]);
	let prescriptions: any[] = $state([]);
	let prescriptionRequests: any[] = $state([]);
	let admissions: any[] = $state([]);
	let alertHistory: any[] = $state([]);

	// Reference data
	let facultyApprovers: { id: string; name: string; department: string }[] = $state([]);
	let procedureMap: Record<string, string[]> = $state({});
	let departments: string[] = $state([]);
	let allowedDepartments: string[] = $state([]);

	// ── UI state (detail) ─────────────────────────────────────────
	let activeTab = $state('case-records');
	const detailTabs = [
		{ id: 'case-records', label: 'Case Records', icon: FileText },
		{ id: 'vitals', label: 'Vitals', icon: HeartPulse },
		{ id: 'medications', label: 'Medications', icon: Pill },
	];

	// Modals
	let showAddRecordModal = $state(false);
	let showAddVitalModal = $state(false);
	let showAddPrescriptionModal = $state(false);
	let showEditPrescriptionModal = $state(false);

	// Medical Alerts UI
	let showAlertInput = $state(false);
	let showAlertHistory = $state(false);
	let newAlertTitle = $state('');
	let alertSubmitting = $state(false);

	// Primary Diagnosis UI
	let showDiagnosisInput = $state(false);
	let showDiagnosisHistory = $state(false);
	let newDiagnosis = $state('');
	let diagnosisSubmitting = $state(false);

	// ── Case Record form ──────────────────────────────────────────
	let crDepartment = $state('');
	let crProcedure = $state('');
	let crFacultyId = $state('');
	let crSubmitting = $state(false);
	let crFormData: Record<string, string> = $state({});
	let crDiagnosisSuggestions: DiagnosisSuggestion[] = $state([]);
	let crDiagnosisLoading = $state(false);
	let crIcdCode = $state('');
	let crIcdDescription = $state('');

	const hasPermission = $derived(
		!crDepartment || allowedDepartments.includes(crDepartment)
	);
	const availableProcedures = $derived(
		crDepartment && hasPermission ? (procedureMap[crDepartment] || []) : []
	);
	const crFields: ProcedureField[] | null = $derived(
		crDepartment && crProcedure ? getProcedureFields(crDepartment, crProcedure) : null
	);

	async function handleCrDiagnosisSearch(query: string) {
		if (query.length < 2) { crDiagnosisSuggestions = []; return; }
		crDiagnosisLoading = true;
		try {
			crDiagnosisSuggestions = await autocompleteApi.searchDiagnoses(query);
		} catch { crDiagnosisSuggestions = []; }
		finally { crDiagnosisLoading = false; }
	}
	function handleCrDiagnosisSelect(item: DiagnosisSuggestion) {
		crFormData['diagnosis'] = item.text;
		crIcdCode = item.icd_code || '';
		crIcdDescription = item.icd_description || item.text;
	}

	// ── Add Vital form ────────────────────────────────────────────
	let vSystolic = $state('');
	let vDiastolic = $state('');
	let vHeartRate = $state('');
	let vSpO2 = $state('');
	let vTemp = $state('');
	let vWeight = $state('');
	let vRespRate = $state('');
	let vGlucose = $state('');
	let vNotes = $state('');
	let vSubmitting = $state(false);

	// ── Add Prescription form ─────────────────────────────────────
	let rxName = $state('');
	let rxDosage = $state('');
	let rxFrequency = $state('');
	let rxStartDate = $state(new Date().toISOString().split('T')[0]);
	let rxEndDate = $state('');
	let rxInstructions = $state('');
	let rxSubmitting = $state(false);

	// ── Edit Prescription form ────────────────────────────────────
	let editRxId = $state('');
	let editRxName = $state('');
	let editRxDosage = $state('');
	let editRxFrequency = $state('');
	let editRxStartDate = $state('');
	let editRxEndDate = $state('');
	let editRxInstructions = $state('');
	let editRxStatus = $state('ACTIVE');
	let editRxMedId = $state('');
	let editRxSubmitting = $state(false);

	// ── Vitals chart ──────────────────────────────────────────────
	let selectedParameter = $state('bp');
	let selectedTimeRange = $state('30');
	let groupViewMode = $state(false);
	let chartCanvas: HTMLCanvasElement = $state(undefined as any);
	let chartInstance: Chart | null = null;

	// ── Derived ───────────────────────────────────────────────────
	const today = new Date().toISOString().split('T')[0];

	const filteredPatients = $derived(
		assignedPatients.filter(p => {
			const q = listSearch.toLowerCase();
			const matchesSearch = !q ||
				(p.name || '').toLowerCase().includes(q) ||
				(p.patient_id || '').toLowerCase().includes(q) ||
				(p.primary_diagnosis || '').toLowerCase().includes(q);
			if (!matchesSearch) return false;
			if (listTab === 'today') {
				const d = (p.created_at || '').split('T')[0];
				return d === today;
			}
			if (listTab === 'previous') {
				const d = (p.created_at || '').split('T')[0];
				return d !== today;
			}
			return true;
		})
	);

	const activeAlerts = $derived(
		patient?.medical_alerts?.filter((a: any) => a.is_active !== false) ?? []
	);

	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	const currentAdmission = $derived(
		admissions.find((a: any) => a.status === 'Active') ?? null
	);

	const vitalCards = $derived(latestVital ? [
		{ icon: HeartPulse, label: 'Blood\nPressure', value: `${latestVital.systolic_bp ?? '—'}/${latestVital.diastolic_bp ?? '—'}`, unit: 'mmHg', color: '#3b82f6' },
		{ icon: Activity, label: 'Heart\nRate', value: `${latestVital.heart_rate ?? '—'}`, unit: 'bpm', color: '#3b82f6' },
		{ icon: Thermometer, label: 'Temp', value: `${latestVital.temperature?.toFixed(1) ?? '—'}`, unit: '°F', color: '#ef4444' },
		{ icon: Droplet, label: 'SpO₂', value: `${latestVital.oxygen_saturation ?? '—'}`, unit: '%', color: '#3b82f6' },
		{ icon: Wind, label: 'Resp\nRate', value: `${latestVital.respiratory_rate ?? '—'}`, unit: '/min', color: '#22c55e' },
		{ icon: Scale, label: 'Weight', value: `${latestVital.weight?.toFixed(0) ?? '—'}`, unit: 'lbs', color: '#6366f1' },
		{ icon: CircleDot, label: 'Glucose', value: `${latestVital.blood_glucose ?? '—'}`, unit: 'mg/dL', color: '#f97316' },
	] : []);

	function getGradeColor(grade: string | undefined) {
		if (!grade) return '#6b7280';
		if (grade.startsWith('A')) return '#22c55e';
		if (grade.startsWith('B')) return '#3b82f6';
		if (grade.startsWith('C')) return '#f97316';
		return '#ef4444';
	}

	function patientAge(): number {
		if (!patient?.date_of_birth) return 0;
		const dob = new Date(patient.date_of_birth);
		return Math.floor((Date.now() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000));
	}

	function buildChart() {
		if (!chartCanvas || vitals.length === 0) return;
		chartInstance?.destroy();
		const vitalsSlice = vitals.slice(0, parseInt(selectedTimeRange)).reverse();
		const labels = vitalsSlice.map((v: any) => {
			const d = new Date(v.recorded_at);
			return `${d.getMonth() + 1}/${d.getDate()}`;
		});
		let datasets: any[];
		if (groupViewMode) {
			datasets = [
				{ label: 'Systolic', data: vitalsSlice.map((v: any) => v.systolic_bp ?? null), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
				{ label: 'Diastolic', data: vitalsSlice.map((v: any) => v.diastolic_bp ?? null), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
				{ label: 'Heart Rate', data: vitalsSlice.map((v: any) => v.heart_rate ?? null), borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
				{ label: 'SpO₂', data: vitalsSlice.map((v: any) => v.oxygen_saturation ?? null), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
			];
		} else if (selectedParameter === 'bp') {
			datasets = [
				{ label: 'Systolic', data: vitalsSlice.map((v: any) => v.systolic_bp ?? 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
				{ label: 'Diastolic', data: vitalsSlice.map((v: any) => v.diastolic_bp ?? 0), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
			];
		} else if (selectedParameter === 'hr') {
			datasets = [{ label: 'Heart Rate', data: vitalsSlice.map((v: any) => v.heart_rate ?? 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 }];
		} else {
			datasets = [{ label: 'SpO₂', data: vitalsSlice.map((v: any) => v.oxygen_saturation ?? 0), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: false, pointRadius: 2 }];
		}
		chartInstance = new Chart(chartCanvas, {
			type: 'line',
			data: { labels, datasets },
			options: {
				responsive: true, maintainAspectRatio: false,
				plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
				scales: {
					y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { font: { size: 9 } } },
					x: { grid: { display: false }, ticks: { font: { size: 9 }, maxTicksLimit: 10 } },
				},
			},
		});
	}

	$effect(() => {
		if (activeTab === 'vitals') {
			selectedParameter; selectedTimeRange; groupViewMode; vitals;
			setTimeout(buildChart, 50);
		}
	});

	// ── Data loading ──────────────────────────────────────────────
	async function selectPatient(patientId: string) {
		if (selectedPatientId === patientId) return;
		selectedPatientId = patientId;
		mobileShowDetail = true;
		activeTab = 'case-records';
		await loadPatientDetail(patientId);
	}

	async function loadPatientDetail(patientId: string) {
		loadingDetail = true;
		patient = null; caseRecords = []; vitals = []; prescriptions = [];
		prescriptionRequests = []; admissions = [];
		try {
			const [patientData, caseData, vitalData, rxData, depts, procs, approvers, rxReqs, perms, admData] =
				await Promise.all([
					patientApi.getPatient(patientId),
					studentApi.getCaseRecords(studentData.id, patientId),
					patientApi.getVitals(patientId, 30).catch(() => []),
					patientApi.getPrescriptions(patientId).catch(() => []),
					studentApi.getDepartments().catch(() => []),
					studentApi.getProcedures().catch(() => ({})),
					studentApi.getFacultyApprovers().catch(() => []),
					patientApi.getPrescriptionRequests(patientId).catch(() => []),
					studentApi.getPermissions(studentData.id).catch(() => []),
					patientApi.getAdmissions(patientId).catch(() => []),
				]);
			patient = patientData;
			caseRecords = caseData;
			vitals = vitalData;
			prescriptions = rxData;
			departments = depts;
			procedureMap = procs;
			facultyApprovers = approvers;
			prescriptionRequests = rxReqs;
			allowedDepartments = perms.map((p: any) => p.department);
			admissions = admData;
		} catch (err) {
			toastStore.addToast('Failed to load patient detail', 'error');
		} finally {
			loadingDetail = false;
		}
	}

	onMount(async () => {
		try {
			studentData = await studentApi.getMe();
			assignedPatients = await studentApi.getAssignedPatients(studentData.id);
		} catch (err) {
			toastStore.addToast('Failed to load patients', 'error');
		} finally {
			loading = false;
		}
	});

	// ── Case Record submit ────────────────────────────────────────
	function resetCaseRecordForm() {
		crDepartment = ''; crProcedure = ''; crFacultyId = '';
		crFormData = {}; crDiagnosisSuggestions = [];
		crIcdCode = ''; crIcdDescription = '';
	}

	async function submitCaseRecord() {
		if (!patient || crSubmitting || !studentData) return;
		crSubmitting = true;
		try {
			const now = new Date();
			const descParts: string[] = [];
			if (crFields) {
				for (const field of crFields) {
					const val = crFormData[field.key];
					if (val && field.key !== 'findings' && field.key !== 'diagnosis' && field.key !== 'treatment' && field.key !== 'notes') {
						descParts.push(`${field.label}: ${val}`);
					}
				}
			}
			const payload: Record<string, unknown> = {
				patient_id: patient.id,
				department: crDepartment,
				procedure: crProcedure,
				findings: crFormData['findings'] || '',
				diagnosis: crFormData['diagnosis'] || '',
				treatment: crFormData['treatment'] || '',
				notes: crFormData['notes'] || '',
				description: descParts.join(', '),
				icd_code: crIcdCode || undefined,
				icd_description: crIcdDescription || undefined,
				time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
			};
			if (crFacultyId) payload.faculty_id = crFacultyId;
			await studentApi.submitCaseRecord(studentData.id, payload);
			caseRecords = await studentApi.getCaseRecords(studentData.id, patient.id);
			showAddRecordModal = false;
			resetCaseRecordForm();
		} catch (err) { toastStore.addToast('Failed to submit case record', 'error'); }
		finally { crSubmitting = false; }
	}

	// ── Vital submit ──────────────────────────────────────────────
	function resetVitalForm() {
		vSystolic = ''; vDiastolic = ''; vHeartRate = ''; vSpO2 = '';
		vTemp = ''; vWeight = ''; vRespRate = ''; vGlucose = '';
		vNotes = '';
	}

	async function submitVital() {
		if (!patient || vSubmitting) return;
		vSubmitting = true;
		try {
			await patientApi.createVital(patient.id, {
				systolic_bp: vSystolic ? parseInt(vSystolic) : undefined,
				diastolic_bp: vDiastolic ? parseInt(vDiastolic) : undefined,
				heart_rate: vHeartRate ? parseInt(vHeartRate) : undefined,
				oxygen_saturation: vSpO2 ? parseInt(vSpO2) : undefined,
				temperature: vTemp ? parseFloat(vTemp) : undefined,
				weight: vWeight ? parseFloat(vWeight) : undefined,
				respiratory_rate: vRespRate ? parseInt(vRespRate) : undefined,
				blood_glucose: vGlucose ? parseInt(vGlucose) : undefined,
				notes: vNotes || undefined,
				recorded_by: studentData?.name || 'Student',
			});
			vitals = await patientApi.getVitals(patient.id, 30);
			showAddVitalModal = false;
			resetVitalForm();
		} catch (err) { toastStore.addToast('Failed to save vital', 'error'); }
		finally { vSubmitting = false; }
	}

	// ── Prescription submit ───────────────────────────────────────
	function resetPrescriptionForm() {
		rxName = ''; rxDosage = ''; rxFrequency = '';
		rxStartDate = new Date().toISOString().split('T')[0];
		rxEndDate = ''; rxInstructions = '';
	}

	async function submitPrescription() {
		if (!patient || rxSubmitting) return;
		rxSubmitting = true;
		try {
			await patientApi.createPrescription(patient.id, {
				doctor: studentData?.name || '',
				department: '',
				medications: [{
					name: rxName, dosage: rxDosage, frequency: rxFrequency,
					start_date: rxStartDate, end_date: rxEndDate, instructions: rxInstructions,
				}],
			});
			prescriptions = await patientApi.getPrescriptions(patient.id);
			showAddPrescriptionModal = false;
			resetPrescriptionForm();
		} catch (err) { toastStore.addToast('Failed to create prescription', 'error'); }
		finally { rxSubmitting = false; }
	}

	// ── Edit Prescription ─────────────────────────────────────────
	function openEditPrescription(rx: any) {
		editRxId = rx.id; editRxStatus = rx.status || 'ACTIVE';
		const med = rx.medications?.[0];
		editRxMedId = med?.id || ''; editRxName = med?.name || '';
		editRxDosage = med?.dosage || ''; editRxFrequency = med?.frequency || '';
		editRxStartDate = med?.start_date || ''; editRxEndDate = med?.end_date || '';
		editRxInstructions = med?.instructions || '';
		showEditPrescriptionModal = true;
	}

	function resetEditForm() {
		editRxId = ''; editRxName = ''; editRxDosage = ''; editRxFrequency = '';
		editRxStartDate = ''; editRxEndDate = ''; editRxInstructions = '';
		editRxStatus = 'ACTIVE'; editRxMedId = '';
	}

	async function submitEditPrescription() {
		if (!patient || editRxSubmitting) return;
		editRxSubmitting = true;
		try {
			await patientApi.updatePrescription(patient.id, editRxId, {
				status: editRxStatus,
				medications: [{
					id: editRxMedId || undefined,
					name: editRxName, dosage: editRxDosage, frequency: editRxFrequency,
					start_date: editRxStartDate, end_date: editRxEndDate, instructions: editRxInstructions,
				}],
			});
			prescriptions = await patientApi.getPrescriptions(patient.id);
			showEditPrescriptionModal = false;
			resetEditForm();
		} catch (err) { toastStore.addToast('Failed to update prescription', 'error'); }
		finally { editRxSubmitting = false; }
	}

	// ── Admit Patient ─────────────────────────────────────────────
	let admitSubmitting = $state(false);

	async function admitPatient() {
		if (!patient || admitSubmitting) return;
		admitSubmitting = true;
		try {
			await patientApi.createAdmission(patient.id, {
				department: departments[0] || 'General',
				ward: 'General Ward',
				bed_number: '',
				attending_doctor: studentData?.name || '',
				reason: patient.primary_diagnosis || '',
			});
			admissions = await patientApi.getAdmissions(patient.id);
		} catch (err) { toastStore.addToast('Failed to admit patient', 'error'); }
		finally { admitSubmitting = false; }
	}

	// ── Medical Alerts ────────────────────────────────────────────
	async function addAlert() {
		if (!patient || !newAlertTitle.trim() || alertSubmitting) return;
		alertSubmitting = true;
		try {
			await patientApi.addMedicalAlert(patient.id, {
				title: newAlertTitle.trim(),
				added_by: studentData?.name || '',
			});
			patient = await patientApi.getPatient(patient.id);
			newAlertTitle = '';
			showAlertInput = false;
		} catch (err) { toastStore.addToast('Failed to add alert', 'error'); }
		finally { alertSubmitting = false; }
	}

	async function removeAlert(alertId: string) {
		if (!patient) return;
		patient.medical_alerts = patient.medical_alerts.map((a: any) =>
			a.id === alertId ? { ...a, is_active: false } : a
		);
		try {
			await patientApi.removeMedicalAlert(patient.id, alertId);
		} catch {
			patient = await patientApi.getPatient(patient.id);
		}
	}

	async function loadAlertHistory() {
		if (!patient) return;
		try {
			alertHistory = await patientApi.getMedicalAlertHistory(patient.id);
			showAlertHistory = true;
		} catch { /* ignore */ }
	}

	// ── Primary Diagnosis ─────────────────────────────────────────
	async function updateDiagnosis() {
		if (!patient || !newDiagnosis.trim() || diagnosisSubmitting) return;
		diagnosisSubmitting = true;
		try {
			const now = new Date();
			await patientApi.updatePrimaryDiagnosis(patient.id, {
				diagnosis: newDiagnosis.trim(),
				doctor: studentData?.name || '',
				date: now.toLocaleDateString(),
				time: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
			});
			patient = await patientApi.getPatient(patient.id);
			newDiagnosis = ''; showDiagnosisInput = false;
		} catch (err) { toastStore.addToast('Failed to update diagnosis', 'error'); }
		finally { diagnosisSubmitting = false; }
	}
</script>

<!-- ══════════════════════════════════════════════════════════
     MASTER-DETAIL PATIENT VIEW
     Left: patient list panel  |  Right: patient detail panel
     ══════════════════════════════════════════════════════════ -->
<div class="flex overflow-hidden" style="height: calc(100vh - 48px); margin: -16px;">

	<!-- ─── LEFT PANEL: Patient List ───────────────────────────── -->
	<div
		class="flex flex-col flex-shrink-0 overflow-hidden"
		class:hidden={mobileShowDetail}
		style="width: 280px; background: #dce3ed;
		       border-right: 1px solid rgba(0,0,0,0.12);
		       display: {mobileShowDetail ? 'none' : 'flex'};"
	>
		<!-- Tab bar: Clinic / Today / Previous -->
		<div class="flex px-3 pt-3 gap-1" style="border-bottom: 1px solid rgba(0,0,0,0.1);">
			{#each ([['clinic','Clinic'],['today','Today'],['previous','Previous']] as const) as [tab, label]}
				<button
					class="flex-1 py-2 text-xs font-semibold rounded-t-lg cursor-pointer transition-all"
					style="background: {listTab === tab ? 'white' : 'transparent'};
					       color: {listTab === tab ? '#1e40af' : '#64748b'};
					       border: {listTab === tab ? '1px solid rgba(0,0,0,0.1)' : '1px solid transparent'};
					       border-bottom-color: {listTab === tab ? 'white' : 'transparent'};
					       margin-bottom: {listTab === tab ? '-1px' : '0'};
					       box-shadow: {listTab === tab ? '0 -1px 3px rgba(0,0,0,0.06)' : 'none'};"
					onclick={() => listTab = tab}
				>
					{label}
				</button>
			{/each}
		</div>

		<!-- Search -->
		<div class="px-3 py-2.5">
			<div class="relative">
				<Search class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
				<input
					type="text"
					placeholder="Search patients..."
					bind:value={listSearch}
					class="w-full pl-8 pr-3 py-2 text-xs rounded-lg outline-none"
					style="background: rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.15);
					       box-shadow: inset 0 1px 2px rgba(0,0,0,0.08);"
				/>
			</div>
		</div>

		<!-- Patient count label -->
		<div class="px-3 pb-1.5 flex items-center gap-1.5">
			<Users class="w-3.5 h-3.5 text-blue-700" />
			<span class="text-[11px] font-semibold text-blue-800">
				{filteredPatients.length} Patient{filteredPatients.length !== 1 ? 's' : ''}
			</span>
		</div>

		<!-- Patient list (scrollable) -->
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex items-center justify-center py-8">
					<div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if filteredPatients.length === 0}
				<div class="text-center py-10 px-4">
					<Users class="w-8 h-8 text-gray-300 mx-auto mb-2" />
					<p class="text-xs text-gray-400">No patients found</p>
				</div>
			{:else}
				{#each filteredPatients as p}
					{@const isSelected = selectedPatientId === p.id}
					<button
						class="w-full flex items-center gap-2.5 px-3 py-3 cursor-pointer transition-colors text-left"
						style="background: {isSelected ? 'linear-gradient(to right, #3b82f6, #2563eb)' : 'transparent'};
						       border-bottom: 1px solid rgba(0,0,0,0.06);"
						onclick={() => selectPatient(p.id)}
					>
						<div class="shrink-0 w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm"
							style="background: {isSelected ? 'rgba(255,255,255,0.25)' : 'linear-gradient(to bottom, #4d90fe, #3b7aed)'};
							       color: white; border: 1px solid rgba(0,0,0,0.1);">
							{(p.name || '?').charAt(0).toUpperCase()}
						</div>
						<div class="flex-1 min-w-0">
							<p class="text-xs font-semibold truncate"
								style="color: {isSelected ? 'white' : '#1e293b'};">
								{p.name}
							</p>
							<p class="text-[10px] mt-0.5 truncate"
								style="color: {isSelected ? 'rgba(255,255,255,0.75)' : '#64748b'};">
								{p.patient_id} · {p.primary_diagnosis || p.condition || 'No diagnosis'}
							</p>
						</div>
						<ChevronRight class="w-3.5 h-3.5 shrink-0"
							style="color: {isSelected ? 'rgba(255,255,255,0.7)' : '#cbd5e1'};" />
					</button>
				{/each}
			{/if}
		</div>
	</div>

	<!-- ─── RIGHT PANEL: Patient Detail ─────────────────────────── -->
	<div
		class="flex-1 overflow-y-auto"
		style="background: #eef2f8; display: {(!mobileShowDetail && !selectedPatientId) ? 'none' : 'block'};"
		class:hidden={!mobileShowDetail && !selectedPatientId}
	>
		{#if !selectedPatientId}
			<!-- Empty state (desktop) -->
			<div class="hidden md:flex flex-col items-center justify-center h-full text-center p-8">
				<div class="w-16 h-16 rounded-full flex items-center justify-center mb-4"
					style="background: linear-gradient(to bottom, #e0e8f4, #c8d6ea);">
					<Users class="w-8 h-8 text-blue-400" />
				</div>
				<p class="text-gray-600 font-medium">Select a patient</p>
				<p class="text-sm text-gray-400 mt-1">Choose a patient from the list to view details</p>
			</div>

		{:else if loadingDetail}
			<div class="flex items-center justify-center py-20">
				<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
			</div>

		{:else if patient}
		<div class="p-4 space-y-3">

			<!-- Mobile: back button -->
			<button
				class="flex md:hidden items-center gap-1.5 text-sm font-medium text-blue-700 cursor-pointer py-1"
				onclick={() => { mobileShowDetail = false; selectedPatientId = null; }}
			>
				<ArrowLeft class="w-4 h-4" /> Back to patients
			</button>

			<!-- ── PATIENT HEADER ──────────────────────────────── -->
			<div class="rounded-xl p-4 flex items-start gap-4"
				style="background: white; border: 1px solid rgba(0,0,0,0.08);
				       box-shadow: 0 1px 4px rgba(0,0,0,0.08);">
				<!-- Photo/Avatar -->
				{#if patient.photo}
					<img src={patient.photo} alt={patient.name}
						class="w-16 h-16 rounded-xl object-cover border-2 border-white shadow-md shrink-0" />
				{:else}
					<div class="w-16 h-16 rounded-xl flex items-center justify-center shrink-0 font-bold text-2xl text-white"
						style="background: linear-gradient(135deg, #4d90fe, #2563eb); border: 2px solid white; box-shadow: 0 2px 8px rgba(59,130,246,0.4);">
						{(patient.name || 'P').charAt(0)}
					</div>
				{/if}
				<!-- Info -->
				<div class="flex-1 min-w-0">
					<h2 class="text-lg font-bold text-gray-800 leading-tight">{patient.name}</h2>
					<p class="text-xs text-gray-500 mt-0.5">ID: {patient.patient_id}</p>
					<p class="text-sm text-gray-600 mt-1.5">
						{patientAge()} years, {patient.gender || '—'}, Blood: {patient.blood_group || '—'}
					</p>
					<p class="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
						<Phone class="w-3 h-3" /> {patient.phone || '—'}
					</p>
				</div>
			</div>

			<!-- ── MEDICAL ALERTS + PRIMARY DIAGNOSIS (2-col on desktop) ── -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-3">

				<!-- Medical Alerts -->
				<div class="rounded-xl overflow-hidden"
					style="background: linear-gradient(to right, rgba(255,200,200,0.7), rgba(255,180,180,0.5));
					       border: 1px solid rgba(220,50,50,0.2);">
					<div class="px-4 py-2.5 flex items-center justify-between">
						<div class="flex items-center gap-2">
							<AlertTriangle class="w-4 h-4 text-red-500" />
							<span class="text-sm font-bold text-red-700">Medical Alerts</span>
						</div>
						<div class="flex gap-1">
							<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
								style="background: rgba(0,0,0,0.08);"
								onclick={loadAlertHistory} title="View history">
								<History class="w-3 h-3 text-gray-600" />
							</button>
							<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
								style="background: rgba(0,0,0,0.08);"
								onclick={() => showAlertInput = !showAlertInput} title="Add alert">
								<Plus class="w-3 h-3 text-gray-600" />
							</button>
						</div>
					</div>
					{#if activeAlerts.length > 0}
						<div class="px-4 pb-2 flex flex-wrap gap-1.5">
							{#each activeAlerts as alert}
								<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-red-700"
									style="background: rgba(255,255,255,0.55);">
									{alert.title}
									<button class="text-red-400 cursor-pointer hover:text-red-600 leading-none"
										onclick={() => removeAlert(alert.id)}>×</button>
								</span>
							{/each}
						</div>
					{:else}
						<p class="px-4 pb-2 text-xs text-red-400">No active alerts</p>
					{/if}
					{#if showAlertInput}
						<div class="px-4 pb-3">
							<div class="flex gap-2 items-center p-2 rounded-lg bg-white/60">
								<input type="text" bind:value={newAlertTitle}
									class="flex-1 px-2.5 py-1.5 rounded text-xs bg-white outline-none"
									style="border: 1px solid rgba(0,0,0,0.15);"
									placeholder="Enter alert..."
									onkeydown={(e) => e.key === 'Enter' && addAlert()} />
								<button class="px-2.5 py-1.5 rounded text-xs font-medium text-white cursor-pointer"
									style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
									onclick={addAlert} disabled={alertSubmitting}>Add</button>
								<button class="text-gray-400 cursor-pointer text-xs hover:text-gray-600"
									onclick={() => { showAlertInput = false; newAlertTitle = ''; }}>✕</button>
							</div>
						</div>
					{/if}
					{#if showAlertHistory}
						<div class="mx-3 mb-3 p-3 rounded-lg bg-white/60">
							<h4 class="text-xs font-semibold text-gray-700 mb-2">Alert History</h4>
							<div class="space-y-1.5 max-h-32 overflow-y-auto">
								{#each alertHistory as h}
									<div class="flex items-center gap-2 pl-2" style="border-left: 2px solid {h.is_active ? '#ef4444' : '#d1d5db'};">
										<p class="text-xs flex-1" style="color: {h.is_active ? '#dc2626' : '#6b7280'};">{h.title}</p>
										<span class="text-[10px] px-1.5 py-0.5 rounded"
											style="background: {h.is_active ? 'rgba(239,68,68,0.1)' : 'rgba(0,0,0,0.05)'}; color: {h.is_active ? '#dc2626' : '#6b7280'};">
											{h.is_active ? 'Active' : 'Removed'}
										</span>
									</div>
								{/each}
							</div>
							<button class="mt-2 text-xs text-gray-400 cursor-pointer hover:text-gray-600"
								onclick={() => showAlertHistory = false}>Close</button>
						</div>
					{/if}
				</div>

				<!-- Primary Diagnosis -->
				<div class="rounded-xl overflow-hidden"
					style="background: linear-gradient(to right, rgba(200,220,255,0.7), rgba(180,210,255,0.5));
					       border: 1px solid rgba(50,100,220,0.2);">
					<div class="px-4 py-2.5 flex items-center justify-between">
						<div class="flex items-center gap-2">
							<FileText class="w-4 h-4 text-blue-500" />
							<span class="text-sm font-bold text-blue-700">Primary Diagnosis</span>
						</div>
						<div class="flex gap-1">
							<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
								style="background: rgba(0,0,0,0.08);"
								onclick={() => showDiagnosisHistory = !showDiagnosisHistory} title="History">
								<History class="w-3 h-3 text-gray-600" />
							</button>
							<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
								style="background: rgba(0,0,0,0.08);"
								onclick={() => showDiagnosisInput = !showDiagnosisInput} title="Edit">
								<Edit class="w-3 h-3 text-gray-600" />
							</button>
						</div>
					</div>
					<div class="px-4 pb-2">
						{#if patient.primary_diagnosis}
							<span class="inline-flex items-center px-2.5 py-1 rounded-lg text-sm font-medium text-blue-800"
								style="background: rgba(255,255,255,0.6);">
								{patient.primary_diagnosis}
							</span>
							{#if patient.diagnosis_doctor}
								<p class="text-[10px] text-blue-400 mt-1 ml-0.5">
									{patient.diagnosis_doctor} · {patient.diagnosis_date || ''}
								</p>
							{/if}
						{:else}
							<p class="text-xs text-blue-400">No diagnosis recorded</p>
						{/if}
					</div>
					{#if showDiagnosisInput}
						<div class="px-4 pb-3">
							<div class="flex gap-2 items-center p-2 rounded-lg bg-white/60">
								<input type="text" bind:value={newDiagnosis}
									class="flex-1 px-2.5 py-1.5 rounded text-xs bg-white outline-none"
									style="border: 1px solid rgba(0,0,0,0.15);"
									placeholder="Enter diagnosis..."
									onkeydown={(e) => e.key === 'Enter' && updateDiagnosis()} />
								<button class="px-2.5 py-1.5 rounded text-xs font-medium text-white cursor-pointer"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
									onclick={updateDiagnosis} disabled={diagnosisSubmitting}>Save</button>
								<button class="text-gray-400 cursor-pointer text-xs hover:text-gray-600"
									onclick={() => { showDiagnosisInput = false; newDiagnosis = ''; }}>✕</button>
							</div>
						</div>
					{/if}
					{#if showDiagnosisHistory}
						<div class="mx-3 mb-3 p-3 rounded-lg bg-white/60">
							<h4 class="text-xs font-semibold text-gray-700 mb-2">Diagnosis History</h4>
							{#if patient.primary_diagnosis}
								<div class="flex items-center gap-2 pl-2" style="border-left: 2px solid #3b82f6;">
									<p class="text-xs text-blue-700 flex-1">{patient.primary_diagnosis}</p>
									<span class="text-[10px] px-1.5 py-0.5 rounded"
										style="background: rgba(59,130,246,0.1); color: #2563eb;">Current</span>
								</div>
							{:else}
								<p class="text-xs text-gray-400">No history</p>
							{/if}
							<button class="mt-2 text-xs text-gray-400 cursor-pointer hover:text-gray-600"
								onclick={() => showDiagnosisHistory = false}>Close</button>
						</div>
					{/if}
				</div>
			</div>

			<!-- ── ADMISSION STATUS BAR ────────────────────────── -->
			<div class="rounded-xl px-4 py-3 flex items-center justify-between"
				style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
				<div class="flex items-center gap-2.5 min-w-0">
					<ClipboardList class="w-4 h-4 text-gray-500 shrink-0" />
					<span class="text-sm font-semibold text-gray-700">Admission Status</span>
					{#if currentAdmission}
						<span class="text-xs font-bold px-2 py-0.5 rounded shrink-0"
							style="background: rgba(34,197,94,0.12); color: #15803d;">
							{currentAdmission.status} — {currentAdmission.ward || 'Ward'}
						</span>
					{:else}
						<Clock class="w-3.5 h-3.5 text-gray-400 shrink-0" />
						<span class="text-xs text-gray-400 truncate">Not currently admitted</span>
					{/if}
				</div>
				{#if !currentAdmission}
					<button
						class="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer flex items-center gap-1.5"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.2);
						       box-shadow: 0 1px 3px rgba(22,163,74,0.4);"
						onclick={admitPatient} disabled={admitSubmitting}
					>
						{#if admitSubmitting}
							<div class="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
						{/if}
						Admit Patient
					</button>
				{:else}
					<span class="text-xs text-gray-400 shrink-0">Since {currentAdmission.admission_date}</span>
				{/if}
			</div>

			<!-- ── TAB BAR ─────────────────────────────────────── -->
			<TabBar tabs={detailTabs} {activeTab} onchange={(id) => activeTab = id} />

			<!-- ── CASE RECORDS TAB ────────────────────────────── -->
			{#if activeTab === 'case-records'}
			<AquaCard>
				<div class="flex items-center justify-between mb-4 flex-wrap gap-2">
					<div class="flex items-center gap-2">
						<FileText class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Case Records</h3>
					</div>
					<div class="flex items-center gap-2">
						<select class="px-2 py-1.5 rounded text-xs cursor-pointer outline-none"
							style="border: 1px solid rgba(0,0,0,0.15); background: rgba(255,255,255,0.9);">
							<option>All</option>
							{#each departments as dept}
								<option>{dept}</option>
							{/each}
						</select>
						<button class="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
							style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.15);
							       color: #334155;">
							View Gallery
						</button>
						<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer text-white"
							style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.15);
							       box-shadow: 0 1px 3px rgba(0,102,204,0.3);"
							onclick={() => showAddRecordModal = true}>
							<Plus class="w-3 h-3" /> Add Entry
						</button>
					</div>
				</div>

				{#if caseRecords.length === 0}
					<p class="text-sm text-gray-400 text-center py-8">No case records yet</p>
				{:else}
					<div class="space-y-5">
						{#each caseRecords as record}
							<div class="pb-5 border-b border-gray-100 last:border-0 last:pb-0">
								<div class="flex items-center gap-3 mb-2">
									<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
										style="background: {record.status === 'APPROVED' ? '#22c55e' : '#f97316'};">
										<CheckCircle2 class="w-5 h-5 text-white" />
									</div>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 flex-wrap">
											<span class="font-semibold text-gray-800 text-sm">{record.procedure_name || 'Physical Examination'}</span>
											{#if record.grade}
												<span class="px-2 py-0.5 rounded text-xs font-bold"
													style="background: {getGradeColor(record.grade)}20; color: {getGradeColor(record.grade)}; border: 1px solid {getGradeColor(record.grade)}40;">
													Approved: {record.grade}
												</span>
											{/if}
										</div>
										<p class="text-xs text-gray-500">{record.date} · {record.time} · {record.department}</p>
									</div>
								</div>
								<div class="ml-12 p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
									<p class="text-sm text-gray-700"><strong>Findings:</strong> {record.examination || record.findings || '—'}</p>
									<p class="text-sm text-gray-700 mt-1"><strong>Diagnosis:</strong> {record.diagnosis || '—'}</p>
									<p class="text-sm text-gray-700 mt-1"><strong>Treatment:</strong> {record.treatment_plan || record.treatment || '—'}</p>
								</div>
								<div class="ml-12 mt-2 flex items-start justify-between text-xs text-gray-500">
									<div>
										<div class="flex items-center gap-1"><User class="w-3 h-3" /> Provider: {record.provider || '—'}</div>
										<div class="flex items-center gap-1 mt-0.5"><Users class="w-3 h-3" /> Approver: {record.approver || '—'}</div>
									</div>
									{#if record.approved_at || record.date}
										<span class="text-green-600 font-medium">{record.date}</span>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</AquaCard>

			<!-- ── VITALS TAB ──────────────────────────────────── -->
			{:else if activeTab === 'vitals'}
			<AquaCard>
				<div class="flex items-center justify-between mb-4 flex-wrap gap-2">
					<div class="flex items-center gap-2">
						<HeartPulse class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Vitals Tracker</h3>
					</div>
					<div class="flex gap-2 flex-wrap">
						<button class="px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer"
							style="background: linear-gradient(to bottom, {groupViewMode ? '#3b82f6' : '#6b7280'}, {groupViewMode ? '#2563eb' : '#4b5563'});
							       border: 1px solid rgba(0,0,0,0.15);"
							onclick={() => groupViewMode = !groupViewMode}>
							{groupViewMode ? 'Single View' : 'Group View'}
						</button>
						<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.15);"
							onclick={() => showAddVitalModal = true}>
							<Plus class="w-3 h-3" /> Add Reading
						</button>
					</div>
				</div>

				{#if vitals.length === 0}
					<p class="text-sm text-gray-400 text-center py-8">No vitals recorded yet</p>
				{:else}
					<!-- Parameter + time range selectors -->
					{#if !groupViewMode}
						<div class="flex gap-2 mb-3 flex-wrap">
							{#each [['bp','Blood Pressure'],['hr','Heart Rate'],['spo2','SpO₂']] as [key, label]}
								<button class="px-3 py-1 rounded-full text-xs font-medium cursor-pointer"
									style="background: {selectedParameter === key ? '#3b82f6' : 'rgba(0,0,0,0.06)'};
									       color: {selectedParameter === key ? 'white' : '#374151'};"
									onclick={() => selectedParameter = key}>{label}</button>
							{/each}
						</div>
					{/if}
					<div class="flex gap-2 mb-3 flex-wrap">
						{#each [['7','7 days'],['14','14 days'],['30','30 days']] as [val, label]}
							<button class="px-3 py-1 rounded-full text-xs font-medium cursor-pointer"
								style="background: {selectedTimeRange === val ? '#1e40af' : 'rgba(0,0,0,0.06)'};
								       color: {selectedTimeRange === val ? 'white' : '#374151'};"
								onclick={() => selectedTimeRange = val}>{label}</button>
						{/each}
					</div>
					<!-- Chart -->
					<div class="rounded-lg overflow-hidden mb-4" style="height: 180px; border: 1px solid rgba(0,0,0,0.07);">
						<canvas bind:this={chartCanvas} style="width:100%;height:100%;"></canvas>
					</div>
					<!-- Latest readings grid -->
					{#if vitalCards.length > 0}
						<p class="text-xs font-semibold text-gray-500 mb-2">Latest Readings</p>
						<div class="grid grid-cols-3 gap-2">
							{#each vitalCards as card}
								{@const CardIcon = card.icon}
								<div class="p-2.5 rounded-lg text-center"
									style="background: white; border: 1px solid rgba(0,0,0,0.07);">
									<CardIcon class="w-4 h-4 mx-auto mb-1" style="color: {card.color};" />
									<p class="text-base font-bold" style="color: {card.color};">{card.value}</p>
									<p class="text-[9px] text-gray-400 leading-tight">{card.unit}</p>
									<p class="text-[9px] text-gray-500 mt-0.5 leading-tight">{card.label}</p>
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			</AquaCard>

			<!-- ── MEDICATIONS TAB ─────────────────────────────── -->
			{:else if activeTab === 'medications'}
			<AquaCard>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-2">
						<Pill class="w-5 h-5 text-blue-600" />
						<h3 class="font-bold text-gray-800">Medications</h3>
					</div>
					<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.15);
						       box-shadow: 0 1px 3px rgba(0,102,204,0.3);"
						onclick={() => showAddPrescriptionModal = true}>
						<Plus class="w-3 h-3" /> Add Prescription
					</button>
				</div>

				{#if prescriptions.length === 0}
					<p class="text-sm text-gray-400 text-center py-8">No prescriptions recorded</p>
				{:else}
					<div class="space-y-4">
						{#each prescriptions as rx}
							<div class="p-4 rounded-xl" style="background: #f8faff; border: 1px solid rgba(59,130,246,0.1);">
								<div class="flex items-start justify-between mb-2">
									<div class="flex items-center gap-2">
										<div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
											style="background: {rx.status === 'ACTIVE' ? 'rgba(34,197,94,0.15)' : 'rgba(107,114,128,0.15)'};">
											<Pill class="w-3.5 h-3.5" style="color: {rx.status === 'ACTIVE' ? '#16a34a' : '#6b7280'};" />
										</div>
										<div>
											<span class="text-xs font-bold px-2 py-0.5 rounded"
												style="background: {rx.status === 'ACTIVE' ? 'rgba(34,197,94,0.1)' : 'rgba(107,114,128,0.1)'};
												       color: {rx.status === 'ACTIVE' ? '#15803d' : '#6b7280'};">
												{rx.status || 'ACTIVE'}
											</span>
										</div>
									</div>
									<button class="text-xs text-gray-400 cursor-pointer hover:text-blue-600 px-2 py-1 rounded"
										style="background: rgba(0,0,0,0.05);"
										onclick={() => openEditPrescription(rx)}>
										<Edit class="w-3 h-3" />
									</button>
								</div>
								{#each rx.medications || [] as med}
									<div class="flex items-start gap-2 mt-2">
										<div class="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0"></div>
										<div class="flex-1">
											<span class="text-sm font-semibold text-gray-800">{med.name}</span>
											<span class="ml-2 text-xs text-gray-500">{med.dosage} · {med.frequency}</span>
											{#if med.start_date || med.end_date}
												<p class="text-[10px] text-gray-400 mt-0.5">
													{med.start_date || ''}{med.end_date ? ` → ${med.end_date}` : ''}
												</p>
											{/if}
											{#if med.instructions}
												<p class="text-xs text-gray-500 mt-0.5"><strong>Instructions:</strong> {med.instructions}</p>
											{/if}
										</div>
									</div>
								{/each}
								{#if rx.doctor}
									<p class="text-[10px] text-gray-400 mt-2">Prescribed by {rx.doctor} · {rx.date || ''}</p>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				{#if prescriptionRequests.length > 0}
					<h4 class="text-sm font-semibold text-gray-600 mt-5 mb-3">Prescription Requests</h4>
					<div class="space-y-3">
						{#each prescriptionRequests as req}
							<div class="p-3 rounded-xl" style="background: #fffbeb; border: 1px solid rgba(234,179,8,0.2);">
								<div class="flex items-start justify-between">
									<div>
										<div class="flex items-center gap-2">
											<Clock class="w-3.5 h-3.5 text-orange-500" />
											<span class="text-sm font-semibold text-gray-800">{req.medication} {req.dosage || ''}</span>
										</div>
										<p class="text-xs text-gray-400 ml-5 mt-0.5">{req.requested_date || '—'}</p>
									</div>
									<span class="text-xs font-bold px-2 py-0.5 rounded"
										style="background: {req.status === 'PENDING' ? 'rgba(249,115,22,0.1)' : 'rgba(34,197,94,0.1)'};
										       color: {req.status === 'PENDING' ? '#ea580c' : '#16a34a'};">
										{req.status}
									</span>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</AquaCard>
			{/if}

		</div>
		{/if}
	</div>
</div>

<!-- ══════════════════════════════════════════════════════════
     MODALS
     ══════════════════════════════════════════════════════════ -->

<!-- Add Case Record Modal -->
{#if showAddRecordModal}
<AquaModal onclose={() => { showAddRecordModal = false; resetCaseRecordForm(); }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<FileText class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">Add New Case Record Entry</span>
		</div>
	{/snippet}
	<div class="space-y-4">
		<div>
			<label for="cr-dept" class="block text-sm font-medium text-gray-700 mb-1">
				Department <span class="text-red-500">*</span>
			</label>
			<select id="cr-dept" bind:value={crDepartment}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				onchange={() => { crProcedure = ''; crFormData = {}; crIcdCode = ''; crIcdDescription = ''; }}>
				<option value="">Select Department</option>
				{#each departments as dept}
					<option value={dept}>{dept}</option>
				{/each}
			</select>
		</div>
		{#if crDepartment && hasPermission}
		<div>
			<label for="cr-proc" class="block text-sm font-medium text-gray-700 mb-1">
				Procedure <span class="text-red-500">*</span>
			</label>
			<select id="cr-proc" bind:value={crProcedure}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				onchange={() => { crFormData = {}; crIcdCode = ''; crIcdDescription = ''; }}>
				<option value="">Select Procedure</option>
				{#each availableProcedures as proc}
					<option value={proc}>{proc}</option>
				{/each}
			</select>
		</div>
		{:else if crDepartment && !hasPermission}
		<div class="rounded-lg p-4 text-center" style="background-color: rgba(254,226,226,0.5); border: 1px solid rgba(239,68,68,0.2);">
			<p class="text-sm font-medium text-red-700">You don't have permission to perform procedures in {crDepartment}.</p>
			<p class="text-xs text-red-500 mt-1">Contact your faculty advisor to request access.</p>
		</div>
		{/if}
		{#if crFields}
			{#each crFields as field (field.key)}
				<div>
					{#if field.type === 'diagnosis'}
						<!-- svelte-ignore a11y_label_has_associated_control -->
						<label class="block text-sm font-medium text-gray-700 mb-1">
							{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
						</label>
						<Autocomplete
							placeholder="Search ICD-10 code or diagnosis..."
							bind:value={crFormData[field.key]}
							items={crDiagnosisSuggestions}
							labelKey="text"
							sublabelKey="icd_description"
							badgeKey="icd_code"
							onInput={handleCrDiagnosisSearch}
							onSelect={handleCrDiagnosisSelect}
							onClear={() => { crIcdCode = ''; crIcdDescription = ''; crDiagnosisSuggestions = []; }}
							loading={crDiagnosisLoading}
							minChars={2}
						/>
						{#if crIcdCode}
							<div class="mt-1.5 flex items-center gap-1.5">
								<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{crIcdCode}</span>
								<span class="text-[10px] text-gray-500 truncate">{crIcdDescription}</span>
							</div>
						{/if}
					{:else if field.type === 'select'}
						<label for="cr-{field.key}" class="block text-sm font-medium text-gray-700 mb-1">
							{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
						</label>
						<select id="cr-{field.key}" bind:value={crFormData[field.key]}
							class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
							<option value="">Select {field.label}</option>
							{#each field.options ?? [] as opt}
								<option value={opt}>{opt}</option>
							{/each}
						</select>
					{:else if field.type === 'textarea'}
						<label for="cr-{field.key}" class="block text-sm font-medium text-gray-700 mb-1">
							{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
						</label>
						<textarea id="cr-{field.key}" bind:value={crFormData[field.key]}
							class="block w-full px-3 py-2 rounded-md text-sm resize-y" rows={field.rows ?? 3}
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
							placeholder={field.placeholder ?? ''}></textarea>
					{:else}
						<label for="cr-{field.key}" class="block text-sm font-medium text-gray-700 mb-1">
							{field.label} {#if field.required}<span class="text-red-500">*</span>{/if}
						</label>
						<input id="cr-{field.key}" type={field.type} bind:value={crFormData[field.key]}
							class="block w-full px-3 py-2 rounded-md text-sm"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
							placeholder={field.placeholder ?? ''} />
					{/if}
				</div>
			{/each}
			<div>
				<label for="cr-fac" class="block text-sm font-medium text-gray-700 mb-1">
					Faculty for Approval <span class="text-red-500">*</span>
				</label>
				<select id="cr-fac" bind:value={crFacultyId}
					class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
					<option value="">Select Approver</option>
					{#each facultyApprovers as fac}
						<option value={fac.id}>{fac.name} — {fac.department}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>
	{#if crFields}
	<div class="flex justify-end gap-2 mt-6">
		<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={() => { showAddRecordModal = false; resetCaseRecordForm(); }}
			disabled={crSubmitting}>Cancel</button>
		<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={submitCaseRecord}
			disabled={crSubmitting || !crDepartment || !crProcedure}>
			{crSubmitting ? 'Submitting...' : 'Submit for Review'}
		</button>
	</div>
	{/if}
</AquaModal>
{/if}

<!-- Add Vital Modal -->
{#if showAddVitalModal}
<AquaModal onclose={() => { showAddVitalModal = false; resetVitalForm(); }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<HeartPulse class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">Add New Vital Reading</span>
		</div>
	{/snippet}
	<div class="space-y-4">
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-sys" class="block text-sm font-medium text-gray-700 mb-1">Systolic (mmHg)</label>
				<input id="v-sys" type="number" bind:value={vSystolic}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="120" />
			</div>
			<div>
				<label for="v-dia" class="block text-sm font-medium text-gray-700 mb-1">Diastolic (mmHg)</label>
				<input id="v-dia" type="number" bind:value={vDiastolic}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="80" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-hr" class="block text-sm font-medium text-gray-700 mb-1">Heart Rate (bpm)</label>
				<input id="v-hr" type="number" bind:value={vHeartRate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="72" />
			</div>
			<div>
				<label for="v-spo2" class="block text-sm font-medium text-gray-700 mb-1">SpO₂ (%)</label>
				<input id="v-spo2" type="number" bind:value={vSpO2}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="98" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-temp" class="block text-sm font-medium text-gray-700 mb-1">Temperature (°F)</label>
				<input id="v-temp" type="number" step="0.1" bind:value={vTemp}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="98.6" />
			</div>
			<div>
				<label for="v-wt" class="block text-sm font-medium text-gray-700 mb-1">Weight (lbs)</label>
				<input id="v-wt" type="number" bind:value={vWeight}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="150" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-rr" class="block text-sm font-medium text-gray-700 mb-1">Respiratory Rate</label>
				<input id="v-rr" type="number" bind:value={vRespRate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="16" />
			</div>
			<div>
				<label for="v-glu" class="block text-sm font-medium text-gray-700 mb-1">Blood Glucose</label>
				<input id="v-glu" type="number" bind:value={vGlucose}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="100" />
			</div>
		</div>
		<div>
			<label for="v-notes" class="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
			<textarea id="v-notes" bind:value={vNotes}
				class="block w-full px-3 py-2 rounded-md text-sm resize-none" rows="2"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="Add any relevant notes about this reading"></textarea>
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-6">
		<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={() => { showAddVitalModal = false; resetVitalForm(); }}
			disabled={vSubmitting}>Cancel</button>
		<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={submitVital}
			disabled={vSubmitting}>
			{vSubmitting ? 'Saving...' : 'Save Vital'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Add Prescription Modal -->
{#if showAddPrescriptionModal}
<AquaModal onclose={() => { showAddPrescriptionModal = false; resetPrescriptionForm(); }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Pill class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">Add Prescription</span>
		</div>
	{/snippet}
	<div class="space-y-4">
		<div>
			<label for="rx-name" class="block text-sm font-medium text-gray-700 mb-1">Medication Name <span class="text-red-500">*</span></label>
			<input id="rx-name" type="text" bind:value={rxName}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. Lisinopril" />
		</div>
		<div>
			<label for="rx-dose" class="block text-sm font-medium text-gray-700 mb-1">Dosage <span class="text-red-500">*</span></label>
			<input id="rx-dose" type="text" bind:value={rxDosage}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. 10mg" />
		</div>
		<div>
			<label for="rx-freq" class="block text-sm font-medium text-gray-700 mb-1">Frequency <span class="text-red-500">*</span></label>
			<select id="rx-freq" bind:value={rxFrequency}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
				<option value="">Select frequency</option>
				<option>Once daily</option>
				<option>Twice daily</option>
				<option>Three times daily</option>
				<option>Four times daily</option>
				<option>Every 8 hours</option>
				<option>Every 12 hours</option>
				<option>As needed</option>
				<option>Once weekly</option>
			</select>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="rx-start" class="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
				<input id="rx-start" type="date" bind:value={rxStartDate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
			</div>
			<div>
				<label for="rx-end" class="block text-sm font-medium text-gray-700 mb-1">End Date</label>
				<input id="rx-end" type="date" bind:value={rxEndDate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
			</div>
		</div>
		<div>
			<label for="rx-inst" class="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
			<textarea id="rx-inst" bind:value={rxInstructions}
				class="block w-full px-3 py-2 rounded-md text-sm resize-none" rows="3"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="Special instructions"></textarea>
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-6">
		<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={() => { showAddPrescriptionModal = false; resetPrescriptionForm(); }}>Cancel</button>
		<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={submitPrescription}
			disabled={rxSubmitting || !rxName || !rxDosage || !rxFrequency}>
			{rxSubmitting ? 'Adding...' : 'Add Prescription'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Edit Prescription Modal -->
{#if showEditPrescriptionModal}
<AquaModal onclose={() => { showEditPrescriptionModal = false; resetEditForm(); }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Edit class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">Edit Prescription</span>
		</div>
	{/snippet}
	<div class="space-y-4">
		<div>
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
			<div class="flex gap-2">
				{#each ['ACTIVE', 'COMPLETED'] as st}
					<button class="flex-1 py-2 rounded-md text-sm font-medium cursor-pointer"
						style="background: {editRxStatus === st ? (st === 'ACTIVE' ? 'linear-gradient(to bottom, #4cd964, #2ac845)' : 'linear-gradient(to bottom, #6b7280, #4b5563)') : 'linear-gradient(to bottom, #f0f4fa, #d5dde8)'};
						       color: {editRxStatus === st ? 'white' : '#64748b'};
						       border: 1px solid rgba(0,0,0,0.2);"
						onclick={() => editRxStatus = st}>
						{st === 'ACTIVE' ? 'Active' : 'Inactive'}
					</button>
				{/each}
			</div>
		</div>
		<div>
			<label for="erx-name" class="block text-sm font-medium text-gray-700 mb-1">Medication Name</label>
			<input id="erx-name" type="text" bind:value={editRxName}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
		</div>
		<div>
			<label for="erx-dose" class="block text-sm font-medium text-gray-700 mb-1">Dosage</label>
			<input id="erx-dose" type="text" bind:value={editRxDosage}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
		</div>
		<div>
			<label for="erx-freq" class="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
			<select id="erx-freq" bind:value={editRxFrequency}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
				<option value="">Select frequency</option>
				<option>Once daily</option>
				<option>Twice daily</option>
				<option>Three times daily</option>
				<option>Four times daily</option>
				<option>Every 8 hours</option>
				<option>Every 12 hours</option>
				<option>As needed</option>
				<option>Once weekly</option>
			</select>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="erx-start" class="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
				<input id="erx-start" type="date" bind:value={editRxStartDate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
			</div>
			<div>
				<label for="erx-end" class="block text-sm font-medium text-gray-700 mb-1">End Date</label>
				<input id="erx-end" type="date" bind:value={editRxEndDate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);" />
			</div>
		</div>
		<div>
			<label for="erx-inst" class="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
			<textarea id="erx-inst" bind:value={editRxInstructions}
				class="block w-full px-3 py-2 rounded-md text-sm resize-none" rows="3"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"></textarea>
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-6">
		<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={() => { showEditPrescriptionModal = false; resetEditForm(); }}
			disabled={editRxSubmitting}>Cancel</button>
		<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={submitEditPrescription}
			disabled={editRxSubmitting}>
			{editRxSubmitting ? 'Saving...' : 'Save Changes'}
		</button>
	</div>
</AquaModal>
{/if}
