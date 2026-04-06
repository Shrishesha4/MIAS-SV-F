<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { formsApi } from '$lib/api/forms';
	import { facultyApi } from '$lib/api/faculty';
	import { autocompleteApi, type DiagnosisSuggestion } from '$lib/api/autocomplete';
	import type { FormDefinition, FormFieldDefinition } from '$lib/types/forms';
	import { buildCaseRecordDescription, buildCaseRecordProcedureMap, mergeProcedureMaps, resolveCaseRecordFields, stringifyFormValue } from '$lib/utils/forms';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { Chart, registerables } from 'chart.js';
	import {
		AlertTriangle, FileText, HeartPulse, Pill, Clock, Plus,
		CheckCircle2, ChevronDown, Link2, User, Users,
		Thermometer, Droplet, Activity, Scale, Wind, CircleDot,
		Phone, Mail, MapPin, Shield, Edit, X,
		Trash2, CheckCircle, Send, History
	} from 'lucide-svelte';

	Chart.register(...registerables);

	interface Props { patientId: string; }
	let { patientId: pid }: Props = $props();

	const auth = get(authStore);
	const role = auth.role;

	// ── Core data (reactive) ──────────────────────────────────────
	let patient: any = $state(null);
	let caseRecords: any[] = $state([]);
	let vitals: any[] = $state([]);
	let medications: any[] = $state([]);
	let prescriptions: any[] = $state([]);
	let prescriptionRequests: any[] = $state([]);
	let alertHistory: any[] = $state([]);
	let loading = $state(true);

	// Reference data
	let facultyApprovers: { id: string; name: string; department: string }[] = $state([]);
	let procedureMap: Record<string, string[]> = $state({});
	let caseRecordForms: FormDefinition[] = $state([]);
	let departments: string[] = $state([]);
	let studentData: any = $state(null);
	let facultyData: any = $state(null);

	// ── UI State ──────────────────────────────────────────────────
	let activeTab = $state('case-records');
	const tabs = [
		{ id: 'case-records', label: 'Case Records', icon: FileText },
		{ id: 'vitals', label: 'Vitals', icon: HeartPulse },
		{ id: 'medications', label: 'Medications', icon: Pill },
	];

	// Modals
	let showAddRecordModal = $state(false);
	let showAddVitalModal = $state(false);
	let showAddPrescriptionModal = $state(false);
	let showRequestPrescriptionModal = $state(false);
	let showEditEmergencyModal = $state(false);
	let showAddInsuranceModal = $state(false);

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
	let crFormData: Record<string, any> = $state({});
	let crDiagnosisSuggestions: DiagnosisSuggestion[] = $state([]);
	let crDiagnosisLoading = $state(false);
	let crIcdCode = $state('');
	let crIcdDescription = $state('');
	let allowedDepartments: string[] = $state([]);

	const mergedProcedureMap = $derived(
		mergeProcedureMaps(procedureMap, buildCaseRecordProcedureMap(caseRecordForms))
	);

	const hasPermission = $derived(
		role !== 'STUDENT' || !crDepartment || allowedDepartments.includes(crDepartment)
	);
	const availableProcedures = $derived(
		crDepartment && hasPermission ? (mergedProcedureMap[crDepartment] || []) : []
	);
	const crFields: FormFieldDefinition[] | null = $derived(
		crDepartment && crProcedure ? resolveCaseRecordFields(caseRecordForms, crDepartment, crProcedure) : null
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
	let vSubmitting = $state(false);

	// ── Add Prescription form ─────────────────────────────────────
	let rxName = $state('');
	let rxDosage = $state('');
	let rxFrequency = $state('');
	let rxStartDate = $state(new Date().toISOString().split('T')[0]);
	let rxEndDate = $state('');
	let rxInstructions = $state('');
	let rxSubmitting = $state(false);

	// ── Patient Prescription Request form ─────────────────────────
	let prMedication = $state('');
	let prDosage = $state('');
	let prNotes = $state('');
	let prSubmitting = $state(false);

	// ── Edit Prescription ─────────────────────────────────────────
	let showEditPrescriptionModal = $state(false);
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

	// ── Vitals Chart ──────────────────────────────────────────────
	let selectedParameter = $state('bp');
	let selectedTimeRange = $state('30');
	let groupViewMode = $state(false);
	let chartCanvas: HTMLCanvasElement = $state(undefined as any);
	let chartInstance: Chart | null = null;

	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	const activeAlerts = $derived(
		patient?.medical_alerts?.filter((a: any) => a.is_active !== false) ?? []
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
			datasets = [
				{ label: 'Heart Rate', data: vitalsSlice.map((v: any) => v.heart_rate ?? 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
			];
		} else {
			datasets = [
				{ label: 'SpO₂', data: vitalsSlice.map((v: any) => v.oxygen_saturation ?? 0), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
			];
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
		const diff = Date.now() - dob.getTime();
		return Math.floor(diff / (365.25 * 24 * 60 * 60 * 1000));
	}

	// ── Data loading ──────────────────────────────────────────────
	async function loadAllData() {
		const patientId = pid;
		if (!patientId) return;
		try {
			if (role === 'STUDENT') {
				if (!studentData) {
					studentData = await studentApi.getMe();
				}
				const [patientData, caseData, vitalData, rxData, depts, procs, approvers, rxReqs, perms, forms] =
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
						formsApi.getForms({ form_type: 'CASE_RECORD' }).catch(() => []),
					]);
				const merged = mergeProcedureMaps(procs, buildCaseRecordProcedureMap(forms));
				patient = patientData;
				caseRecords = caseData;
				vitals = vitalData;
				prescriptions = rxData;
				medications = rxData.flatMap((rx: any) => rx.medications || []);
				departments = Array.from(new Set([...depts, ...Object.keys(merged)])).sort();
				procedureMap = merged;
				caseRecordForms = forms;
				facultyApprovers = approvers;
				prescriptionRequests = rxReqs;
				allowedDepartments = perms.map((p: any) => p.department);
			} else {
				// FACULTY / ADMIN / PATIENT viewing a patient detail
				if (role === 'FACULTY' && !facultyData) {
					facultyData = await facultyApi.getMe();
				}
				const fetchList: Promise<any>[] = [
					patientApi.getPatient(patientId),
					patientApi.getCaseRecords(patientId).catch(() => []),
					patientApi.getVitals(patientId, 30).catch(() => []),
					patientApi.getPrescriptions(patientId).catch(() => []),
					patientApi.getPrescriptionRequests(patientId).catch(() => []),
				];
				if (role === 'FACULTY') {
					fetchList.push(
						studentApi.getDepartments().catch(() => []),
						studentApi.getProcedures().catch(() => ({})),
						formsApi.getForms({ form_type: 'CASE_RECORD' }).catch(() => []),
					);
				}
				const results = await Promise.all(fetchList);
				patient = results[0];
				caseRecords = results[1];
				vitals = results[2];
				prescriptions = results[3];
				medications = results[3].flatMap((rx: any) => rx.medications || []);
				prescriptionRequests = results[4];
				if (role === 'FACULTY') {
					const merged = mergeProcedureMaps(results[6] || {}, buildCaseRecordProcedureMap(results[7] || []));
					departments = Array.from(new Set([...(results[5] || []), ...Object.keys(merged)])).sort();
					procedureMap = merged;
					caseRecordForms = results[7] || [];
				}
			}
		} catch (err) {
			toastStore.addToast('Failed to load patient detail', 'error');
		}
	}

	let loadedPid = '';
	onMount(async () => {
		loadedPid = pid;
		try {
			await loadAllData();
		} finally {
			loading = false;
		}
	});

	// Re-load when patientId prop changes
	$effect(() => {
		if (loadedPid && pid !== loadedPid) {
			loadedPid = pid;
			loading = true;
			patient = null;
			caseRecords = [];
			vitals = [];
			medications = [];
			prescriptions = [];
			prescriptionRequests = [];
			loadAllData().finally(() => { loading = false; });
		}
	});

	// Auto-refresh patient data every 30 seconds
	$effect(() => {
		if (loading) return;
		const interval = setInterval(async () => {
			try {
				const patientId = pid;
				if (!patientId) return;
				const [patientData, vitalData, rxData, rxReqs] = await Promise.all([
					patientApi.getPatient(patientId),
					patientApi.getVitals(patientId, 30).catch(() => []),
					patientApi.getPrescriptions(patientId).catch(() => []),
					patientApi.getPrescriptionRequests(patientId).catch(() => []),
				]);
				patient = patientData;
				vitals = vitalData;
				prescriptions = rxData;
				medications = rxData.flatMap((rx: any) => rx.medications || []);
				prescriptionRequests = rxReqs;
			} catch (err) {
				// Silently fail on auto-refresh
			}
		}, 30000);
		return () => clearInterval(interval);
	});

	// ── Case Record Submit ────────────────────────────────────────
	function resetCaseRecordForm() {
		crDepartment = ''; crProcedure = ''; crFacultyId = '';
		crFormData = {}; crDiagnosisSuggestions = [];
		crIcdCode = ''; crIcdDescription = '';
	}

	async function submitCaseRecord() {
		if (!patient || crSubmitting) return;
		if (role === 'STUDENT' && !studentData) return;
		crSubmitting = true;
		try {
			const now = new Date();
			const payload: Record<string, unknown> = {
				patient_id: patient.id,
				department: crDepartment,
				procedure: crProcedure,
				findings: stringifyFormValue(crFormData['findings']) || '',
				diagnosis: stringifyFormValue(crFormData['diagnosis']) || '',
				treatment: stringifyFormValue(crFormData['treatment']) || '',
				notes: stringifyFormValue(crFormData['notes']) || '',
				description: buildCaseRecordDescription(crFields, crFormData),
				icd_code: crIcdCode || undefined,
				icd_description: crIcdDescription || undefined,
				time: now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
			};
			if (role === 'STUDENT') {
				if (crFacultyId) payload.faculty_id = crFacultyId;
				await studentApi.submitCaseRecord(studentData.id, payload);
				caseRecords = await studentApi.getCaseRecords(studentData.id, patient.id);
			} else {
				await patientApi.createCaseRecord(patient.id, payload);
				caseRecords = await patientApi.getCaseRecords(patient.id);
			}
			showAddRecordModal = false;
			resetCaseRecordForm();
		} catch (err) { console.error('Failed to submit case record', err); }
		finally { crSubmitting = false; }
	}

	// ── Vital Submit ──────────────────────────────────────────────
	function resetVitalForm() {
		vSystolic = ''; vDiastolic = ''; vHeartRate = ''; vSpO2 = '';
		vTemp = ''; vWeight = ''; vRespRate = ''; vGlucose = '';
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
				recorded_by: studentData?.name || 'Student',
			});
			vitals = await patientApi.getVitals(patient.id, 30);
			showAddVitalModal = false;
			resetVitalForm();
		} catch (err) { console.error('Failed to save vital', err); }
		finally { vSubmitting = false; }
	}

	// ── Prescription Submit ───────────────────────────────────────
	function resetPrescriptionForm() {
		rxName = ''; rxDosage = ''; rxFrequency = ''; rxStartDate = new Date().toISOString().split('T')[0];
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
					name: rxName,
					dosage: rxDosage,
					frequency: rxFrequency,
					start_date: rxStartDate,
					end_date: rxEndDate,
					instructions: rxInstructions,
				}],
			});
			prescriptions = await patientApi.getPrescriptions(patient.id);
			medications = prescriptions.flatMap((rx: any) => rx.medications || []);
			showAddPrescriptionModal = false;
			resetPrescriptionForm();
		} catch (err) { console.error('Failed to create prescription', err); }
		finally { rxSubmitting = false; }
	}

	// ── Prescription Request Submit ───────────────────────────────
	function resetRequestForm() {
		prMedication = ''; prDosage = ''; prNotes = '';
	}

	// ── Edit Prescription ─────────────────────────────────────────
	function openEditPrescription(rx: any) {
		editRxId = rx.id;
		editRxStatus = rx.status || 'ACTIVE';
		const med = rx.medications?.[0];
		editRxMedId = med?.id || '';
		editRxName = med?.name || '';
		editRxDosage = med?.dosage || '';
		editRxFrequency = med?.frequency || '';
		editRxStartDate = med?.start_date || '';
		editRxEndDate = med?.end_date || '';
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
					name: editRxName,
					dosage: editRxDosage,
					frequency: editRxFrequency,
					start_date: editRxStartDate,
					end_date: editRxEndDate,
					instructions: editRxInstructions,
				}],
			});
			prescriptions = await patientApi.getPrescriptions(patient.id);
			medications = prescriptions.flatMap((rx: any) => rx.medications || []);
			showEditPrescriptionModal = false;
			resetEditForm();
		} catch (err) { console.error('Failed to update prescription', err); }
		finally { editRxSubmitting = false; }
	}

	async function submitPrescriptionRequest() {
		if (!patient || prSubmitting) return;
		prSubmitting = true;
		try {
			await patientApi.createPrescriptionRequest(patient.id, {
				medication: prMedication,
				dosage: prDosage,
				notes: prNotes,
			});
			prescriptionRequests = await patientApi.getPrescriptionRequests(patient.id);
			showRequestPrescriptionModal = false;
			resetRequestForm();
		} catch (err) { console.error('Failed to create request', err); }
		finally { prSubmitting = false; }
	}

	async function respondToRequest(requestId: string, status: string) {
		if (!patient) return;
		try {
			await patientApi.respondToPrescriptionRequest(patient.id, requestId, {
				status,
				responded_by: studentData?.name || '',
			});
			prescriptionRequests = await patientApi.getPrescriptionRequests(patient.id);
		} catch (err) { console.error('Failed to respond', err); }
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
			// Refresh patient to get updated alerts
			patient = await patientApi.getPatient(patient.id);
			newAlertTitle = '';
			showAlertInput = false;
		} catch (err) { console.error('Failed to add alert', err); }
		finally { alertSubmitting = false; }
	}

	async function removeAlert(alertId: string) {
		if (!patient) return;
		// Optimistic update: immediately mark alert inactive locally
		patient.medical_alerts = patient.medical_alerts.map((a: any) =>
			a.id === alertId ? { ...a, is_active: false } : a
		);
		try {
			await patientApi.removeMedicalAlert(patient.id, alertId);
		} catch (err) {
			console.error('Failed to remove alert', err);
			// Revert on failure
			patient = await patientApi.getPatient(patient.id);
		}
	}

	async function loadAlertHistory() {
		if (!patient) return;
		try {
			alertHistory = await patientApi.getMedicalAlertHistory(patient.id);
			showAlertHistory = true;
		} catch (err) { console.error('Failed to load history', err); }
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
				time: now.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
			});
			patient = await patientApi.getPatient(patient.id);
			newDiagnosis = '';
			showDiagnosisInput = false;
		} catch (err) { console.error('Failed to update diagnosis', err); }
		finally { diagnosisSubmitting = false; }
	}
</script>

<div class="px-4 py-4 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !patient}
		<div class="text-center py-12 text-gray-400">
			<p class="text-sm">Patient not found</p>
		</div>
	{:else}

	<!-- ═══════════════════════════════════════════════════════════════
	     COMPACT PATIENT HEADER (matching screenshot)
	     ═══════════════════════════════════════════════════════════════ -->
	<AquaCard>
		<div class="flex items-start gap-4">
			<!-- Photo -->
			<div class="shrink-0">
				{#if patient.photo}
					<img src={patient.photo} alt={patient.name}
						class="w-16 h-16 rounded-xl object-cover shadow border-2 border-white" />
				{:else}
					<div class="w-16 h-16 rounded-xl flex items-center justify-center bg-gradient-to-br from-blue-400 to-blue-600 shadow border-2 border-white">
						<span class="text-xl font-bold text-white">{patient.name?.charAt(0) || 'P'}</span>
					</div>
				{/if}
			</div>
			<!-- Info -->
			<div class="flex-1 min-w-0">
				<h2 class="text-lg font-bold text-gray-800 leading-tight">{patient.name}</h2>
				<p class="text-xs text-gray-500 mt-0.5">ID: {patient.patient_id}</p>
				<p class="text-sm text-gray-600 mt-1">
					{patientAge()}, {patient.gender || '—'}, Blood: {patient.blood_group || '—'}
				</p>
				<p class="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
					<Phone class="w-3 h-3" /> {patient.phone || '—'}
				</p>
			</div>
		</div>
	</AquaCard>

	<!-- ═══════════════════════════════════════════════════════════════
	     MEDICAL ALERTS (always visible, expandable)
	     ═══════════════════════════════════════════════════════════════ -->
	<div class="rounded-xl overflow-hidden"
		style="background: linear-gradient(to right, rgba(255,200,200,0.6), rgba(255,180,180,0.4));
		       border: 1px solid rgba(220,50,50,0.15);">
		<div class="px-4 py-2.5 flex items-center justify-between">
			<div class="flex items-center gap-2">
				<AlertTriangle class="w-4 h-4 text-red-500" />
				<span class="text-sm font-bold text-red-600">Medical Alerts</span>
			</div>
			<div class="flex gap-1.5">
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.08);"
					onclick={loadAlertHistory}>
					<History class="w-3.5 h-3.5 text-gray-600" />
				</button>
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.08);"
					onclick={() => showAlertInput = !showAlertInput}>
					<Plus class="w-3.5 h-3.5 text-gray-600" />
				</button>
			</div>
		</div>

		<!-- Alert Tags -->
		{#if activeAlerts.length > 0}
			<div class="px-4 pb-2 flex flex-wrap gap-2">
				{#each activeAlerts as alert}
					<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-red-700"
						style="background: rgba(255,255,255,0.5);">
						{alert.title}
						<button class="text-red-400 cursor-pointer hover:text-red-600" onclick={() => removeAlert(alert.id)}>×</button>
					</span>
				{/each}
			</div>
		{:else}
			<p class="px-4 pb-2 text-xs text-red-400">No active alerts</p>
		{/if}

		<!-- Add Alert Input (inline) -->
		{#if showAlertInput}
			<div class="px-4 pb-3">
				<div class="flex gap-2 items-center p-2 rounded-lg bg-white/60">
					<input type="text" bind:value={newAlertTitle}
						class="flex-1 px-3 py-1.5 rounded-lg text-sm bg-white"
						style="border: 1px solid rgba(0,0,0,0.15);"
						placeholder="Enter new medical alert"
						onkeydown={(e) => e.key === 'Enter' && addAlert()} />
					<button class="px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer"
						style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
						onclick={addAlert} disabled={alertSubmitting}>
						Add
					</button>
				</div>
				<div class="flex justify-end mt-1.5">
					<button class="px-2 py-1 text-xs text-gray-500 cursor-pointer rounded hover:bg-white/40"
						onclick={() => { showAlertInput = false; newAlertTitle = ''; }}>
						Cancel
					</button>
				</div>
			</div>
		{/if}

		<!-- Alert History (inline) -->
		{#if showAlertHistory}
			<div class="mx-4 mb-3 p-3 rounded-lg bg-white/60" style="border: 1px solid rgba(220,50,50,0.1);">
				<h4 class="text-sm font-semibold text-gray-700 mb-2">Alert History</h4>
				{#if alertHistory.length === 0}
					<p class="text-xs text-gray-400">No history</p>
				{:else}
					<div class="space-y-2">
						{#each alertHistory as h}
							<div class="flex items-start gap-2 pl-2" style="border-left: 3px solid {h.is_active ? '#ef4444' : '#d1d5db'};">
								<div class="flex-1">
									<p class="text-sm font-medium" style="color: {h.is_active ? '#dc2626' : '#6b7280'};">{h.title}</p>
									<p class="text-xs text-gray-400">
										Added by {h.added_by || 'Unknown'} · {h.added_at ? new Date(h.added_at).toLocaleDateString() + ' ' + new Date(h.added_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : ''}
									</p>
								</div>
								<span class="text-xs font-medium px-2 py-0.5 rounded"
									style="background: {h.is_active ? 'rgba(239,68,68,0.1)' : 'rgba(0,0,0,0.05)'}; color: {h.is_active ? '#dc2626' : '#6b7280'};">
									{h.is_active ? 'Active' : 'Inactive'}
								</span>
							</div>
						{/each}
					</div>
				{/if}
				<div class="flex justify-end mt-2">
					<button class="px-3 py-1 text-xs text-gray-500 cursor-pointer rounded"
						style="background: rgba(0,0,0,0.06);"
						onclick={() => showAlertHistory = false}>Close</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- ═══════════════════════════════════════════════════════════════
	     PRIMARY DIAGNOSIS (inline, like Medical Alerts)
	     ═══════════════════════════════════════════════════════════════ -->
	<div class="rounded-xl overflow-hidden"
		style="background: linear-gradient(to right, rgba(200,220,255,0.6), rgba(180,210,255,0.4));
		       border: 1px solid rgba(50,100,220,0.15);">
		<div class="px-4 py-2.5 flex items-center justify-between">
			<div class="flex items-center gap-2">
				<FileText class="w-4 h-4 text-blue-500" />
				<span class="text-sm font-bold text-blue-600">Primary Diagnosis</span>
			</div>
			<div class="flex gap-1.5">
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.08);"
					onclick={() => showDiagnosisHistory = !showDiagnosisHistory}>
					<History class="w-3.5 h-3.5 text-gray-600" />
				</button>
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.08);"
					onclick={() => showDiagnosisInput = !showDiagnosisInput}>
					<Edit class="w-3.5 h-3.5 text-gray-600" />
				</button>
			</div>
		</div>

		<!-- Current Diagnosis Tag -->
		<div class="px-4 pb-2">
			{#if patient.primary_diagnosis}
				<span class="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-sm font-medium text-blue-800"
					style="background: rgba(255,255,255,0.6);">
					{patient.primary_diagnosis}
				</span>
				{#if patient.diagnosis_doctor}
					<p class="text-xs text-blue-400 mt-1 ml-1">
						Updated by {patient.diagnosis_doctor} · {patient.diagnosis_date || ''} {patient.diagnosis_time || ''}
					</p>
				{/if}
			{:else}
				<p class="text-xs text-blue-400">No diagnosis recorded</p>
			{/if}
		</div>

		<!-- Edit Diagnosis Input (inline) -->
		{#if showDiagnosisInput}
			<div class="px-4 pb-3">
				<div class="flex gap-2 items-center p-2 rounded-lg bg-white/60">
					<input type="text" bind:value={newDiagnosis}
						class="flex-1 px-3 py-1.5 rounded-lg text-sm bg-white"
						style="border: 1px solid rgba(0,0,0,0.15);"
						placeholder="Enter primary diagnosis"
						onkeydown={(e) => e.key === 'Enter' && updateDiagnosis()} />
					<button class="px-3 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
						onclick={updateDiagnosis} disabled={diagnosisSubmitting}>
						Save
					</button>
				</div>
				<div class="flex justify-end mt-1.5">
					<button class="px-2 py-1 text-xs text-gray-500 cursor-pointer rounded hover:bg-white/40"
						onclick={() => { showDiagnosisInput = false; newDiagnosis = ''; }}>
						Cancel
					</button>
				</div>
			</div>
		{/if}

		<!-- Diagnosis History -->
		{#if showDiagnosisHistory}
			<div class="mx-4 mb-3 p-3 rounded-lg bg-white/60" style="border: 1px solid rgba(50,100,220,0.1);">
				<h4 class="text-sm font-semibold text-gray-700 mb-2">Diagnosis History</h4>
				{#if patient.primary_diagnosis}
					<div class="flex items-start gap-2 pl-2" style="border-left: 3px solid #3b82f6;">
						<div class="flex-1">
							<p class="text-sm font-medium text-blue-700">{patient.primary_diagnosis}</p>
							<p class="text-xs text-gray-400">
								Updated by {patient.diagnosis_doctor || 'Unknown'} · {patient.diagnosis_date || ''} {patient.diagnosis_time || ''}
							</p>
						</div>
						<span class="text-xs font-medium px-2 py-0.5 rounded"
							style="background: rgba(59,130,246,0.1); color: #2563eb;">
							Current
						</span>
					</div>
				{:else}
					<p class="text-xs text-gray-400">No diagnosis history</p>
				{/if}
				<div class="flex justify-end mt-2">
					<button class="px-3 py-1 text-xs text-gray-500 cursor-pointer rounded"
						style="background: rgba(0,0,0,0.06);"
						onclick={() => showDiagnosisHistory = false}>Close</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- ═══════════════════════════════════════════════════════════════
	     TABS
	     ═══════════════════════════════════════════════════════════════ -->
	<TabBar {tabs} {activeTab} onchange={(id) => activeTab = id} />

	<!-- ═══════════════════════════════════════════════════════════════
	     CASE RECORDS TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{#if activeTab === 'case-records'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<FileText class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Case Records</h3>
				</div>
				<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;
					       border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 3px rgba(0,102,204,0.3);"
					onclick={() => showAddRecordModal = true}>
					<Plus class="w-3 h-3" /> Add Entry
				</button>
			</div>

			{#if caseRecords.length === 0}
				<p class="text-sm text-gray-400 text-center py-6">No case records yet</p>
			{:else}
				<div class="space-y-5">
					{#each caseRecords as record}
						<div class="pb-5 border-b border-gray-100 last:border-0 last:pb-0">
							<div class="flex items-center gap-3 mb-2">
								<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
									style="background: {record.status === 'APPROVED' ? '#22c55e' : '#f97316'};">
									<CheckCircle2 class="w-5 h-5 text-white" />
								</div>
								<div class="flex-1">
									<div class="flex items-center gap-2 flex-wrap">
										<span class="font-semibold text-gray-800">{record.procedure_name || 'Physical Examination'}</span>
										{#if record.grade}
											<span class="px-2 py-0.5 rounded text-xs font-bold"
												style="background: {getGradeColor(record.grade)}15; color: {getGradeColor(record.grade)}; border: 1px solid {getGradeColor(record.grade)}30;">
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
							<div class="ml-12 mt-2 flex items-center justify-between text-xs">
								<div class="text-gray-500">
									<div class="flex items-center gap-1">
										<User class="w-3 h-3" /> Provider: {record.provider || '—'}
									</div>
									<div class="flex items-center gap-1 mt-0.5">
										<Users class="w-3 h-3" /> Approver: {record.approver || '—'}
									</div>
								</div>
								{#if record.approved_at}
									<div class="text-right text-green-600 font-medium">
										<p>{record.date}</p>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>

	<!-- ═══════════════════════════════════════════════════════════════
	     VITALS TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{:else if activeTab === 'vitals'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<HeartPulse class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Vitals Tracker</h3>
				</div>
				<div class="flex gap-2">
					<button class="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, {groupViewMode ? '#3b82f6' : '#6b7280'}, {groupViewMode ? '#2563eb' : '#4b5563'}); color: white;
						       border: 1px solid rgba(0,0,0,0.15);"
						onclick={() => groupViewMode = !groupViewMode}>
						{groupViewMode ? 'Single View' : 'Group View'}
					</button>
					<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;
						       border: 1px solid rgba(0,0,0,0.15);"
						onclick={() => showAddVitalModal = true}>
						<Plus class="w-3 h-3" /> Add Reading
					</button>
				</div>
			</div>

			<!-- Selectors -->
			{#if !groupViewMode}
				<div class="grid grid-cols-2 gap-3 mb-4">
					<div>
						<label for="vital-param" class="block text-xs font-medium text-gray-600 mb-1">Vital Parameter</label>
						<select id="vital-param" bind:value={selectedParameter}
							class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
							<option value="bp">BP (mmHg)</option>
							<option value="hr">Heart Rate (bpm)</option>
							<option value="spo2">SpO₂ (%)</option>
						</select>
					</div>
					<div>
						<label for="vital-range" class="block text-xs font-medium text-gray-600 mb-1">Time Range</label>
						<select id="vital-range" bind:value={selectedTimeRange}
							class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
							style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
							<option value="7">Last 7 days</option>
							<option value="14">Last 14 days</option>
							<option value="30">Last 30 days</option>
						</select>
					</div>
				</div>
			{:else}
				<div class="mb-4">
					<label for="vital-range-g" class="block text-xs font-medium text-gray-600 mb-1">Time Range</label>
					<select id="vital-range-g" bind:value={selectedTimeRange}
						class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
						style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
						<option value="7">Last 7 days</option>
						<option value="14">Last 14 days</option>
						<option value="30">Last 30 days</option>
					</select>
				</div>
			{/if}

			<!-- Chart -->
			<div class="rounded-xl p-3 mb-4" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<HeartPulse class="w-4 h-4 text-blue-600" />
						<div>
							<p class="text-sm font-semibold text-gray-800">
								{#if groupViewMode}
									All Vitals Overview
								{:else if selectedParameter === 'bp'}
									BP (mmHg)
								{:else if selectedParameter === 'hr'}
									Heart Rate
								{:else}
									SpO₂
								{/if}
							</p>
							<p class="text-xs text-gray-400">
								{#if groupViewMode}
									BP, HR, SpO₂ combined
								{:else if selectedParameter === 'bp'}
									Normal range: 120/80 mmHg
								{:else if selectedParameter === 'hr'}
									Normal range: 60-100 bpm
								{:else}
									Normal range: 95-100%
								{/if}
							</p>
						</div>
					</div>
					<ChevronDown class="w-5 h-5 text-blue-500" />
				</div>
				<div class="h-40">
					<canvas bind:this={chartCanvas}></canvas>
				</div>
			</div>
		</AquaCard>

		<!-- Latest Readings Grid -->
		{#if vitalCards.length > 0}
			<div>
				<h4 class="text-sm font-semibold text-gray-700 mb-3">Latest Readings</h4>
				<div class="grid grid-cols-3 gap-2">
					{#each vitalCards as card}
						<div class="p-3 rounded-xl text-center"
							style="background-color: white; border-radius: 10px;
							       box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
							<div class="w-8 h-8 rounded-full mx-auto mb-1.5 flex items-center justify-center"
								style="background: {card.color}15;">
								<card.icon class="w-4 h-4" style="color: {card.color}" />
							</div>
							<p class="text-[10px] text-gray-500 leading-tight whitespace-pre-line">{card.label}</p>
							<p class="text-base font-bold text-gray-800 mt-0.5">{card.value}</p>
							<p class="text-[10px] text-gray-400">{card.unit}</p>
						</div>
					{/each}
				</div>
			</div>
		{/if}

	<!-- ═══════════════════════════════════════════════════════════════
	     MEDICATIONS TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{:else if activeTab === 'medications'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<Pill class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Medications</h3>
				</div>
				<div class="flex gap-2">
					{#if role === 'PATIENT'}
						<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
							style="background: linear-gradient(to bottom, #f97316, #ea580c); color: white;
							       border: 1px solid rgba(0,0,0,0.15);"
							onclick={() => showRequestPrescriptionModal = true}>
							<Send class="w-3 h-3" /> Request Rx
						</button>
					{/if}
					<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;
						       border: 1px solid rgba(0,0,0,0.15);"
						onclick={() => showAddPrescriptionModal = true}>
						<Plus class="w-3 h-3" /> Add Prescription
					</button>
				</div>
			</div>

			<h4 class="text-sm font-semibold text-gray-600 mb-3">Current Medications</h4>
			{#if prescriptions.length === 0}
				<p class="text-sm text-gray-400 text-center py-4">No prescriptions</p>
			{:else}
				<div class="space-y-3 mb-6">
					{#each prescriptions as rx}
						<div class="p-4 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
							<div class="flex items-start justify-between mb-2">
								<div class="flex items-center gap-2">
									<Pill class="w-4 h-4 text-gray-500" />
									<span class="font-semibold text-gray-800">{rx.medications?.[0]?.name || 'Unnamed'}</span>
								</div>
								<div class="flex items-center gap-2">
									<span class="text-xs font-bold px-2 py-0.5 rounded"
										style="background: {rx.status === 'ACTIVE' ? 'rgba(34,197,94,0.1)' : 'rgba(107,114,128,0.1)'};
										       color: {rx.status === 'ACTIVE' ? '#16a34a' : '#6b7280'};
										       border: 1px solid {rx.status === 'ACTIVE' ? 'rgba(34,197,94,0.2)' : 'rgba(107,114,128,0.2)'};">
										{rx.status || 'Active'}
									</span>
									{#if rx.status === 'COMPLETED' && patient}
										<button class="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium cursor-pointer"
											style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white;
											       box-shadow: 0 1px 3px rgba(37,99,235,0.3);"
											onclick={async () => {
												try {
													await patientApi.renewPrescription(patient.id, rx.id);
													prescriptions = await patientApi.getPrescriptions(patient.id);
												} catch (err) { console.error('Renew failed', err); }
											}}>
											<Send class="w-3 h-3" /> Renew
										</button>
									{/if}
									<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
										style="background: rgba(0,0,0,0.06);"
										onclick={() => openEditPrescription(rx)}>
										<Edit class="w-3 h-3 text-gray-500" />
									</button>
								</div>
							</div>
							{#each (rx.medications || []) as med}
								<div class="grid grid-cols-2 gap-y-1 text-xs ml-6">
									<div>
										<span class="text-gray-500">Dosage:</span>
										<span class="text-gray-700 font-medium"> {med.dosage || '—'}</span>
									</div>
									<div class="text-right">
										<span class="text-gray-500">Frequency:</span>
										<span class="text-gray-700 font-medium"> {med.frequency || '—'}</span>
									</div>
									<div>
										<span class="text-gray-500">Start:</span>
										<span class="text-gray-700"> {med.start_date || '—'}</span>
									</div>
									<div class="text-right">
										<span class="text-gray-500">End:</span>
										<span class="text-gray-700"> {med.end_date || '—'}</span>
									</div>
								</div>
								{#if med.instructions}
									<p class="text-xs text-gray-500 mt-2 ml-6">
										<strong>Instructions:</strong> {med.instructions}
									</p>
								{/if}
							{/each}
							{#if rx.doctor}
								<p class="text-xs text-gray-400 mt-2 ml-6">Prescribed by {rx.doctor} · {rx.date || ''}</p>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<!-- Prescription Requests Section -->
			<h4 class="text-sm font-semibold text-gray-600 mb-3 mt-4">Prescription Requests</h4>
			{#if prescriptionRequests.length === 0}
				<p class="text-sm text-gray-400 text-center py-4">No prescription requests</p>
			{:else}
				<div class="space-y-3">
					{#each prescriptionRequests as req}
						<div class="p-4 rounded-xl" style="background: #fffbeb; border: 1px solid rgba(234,179,8,0.2);">
							<div class="flex items-start justify-between">
								<div>
									<div class="flex items-center gap-2">
										<Clock class="w-4 h-4 text-orange-500" />
										<span class="font-semibold text-gray-800">Request for {req.medication} {req.dosage || ''}</span>
									</div>
									<p class="text-xs text-gray-500 ml-6 mt-1">Requested: {req.requested_date || '—'}</p>
									{#if req.notes}
										<p class="text-xs text-gray-500 ml-6">Notes: {req.notes}</p>
									{/if}
								</div>
								<div class="text-right shrink-0">
									<span class="text-xs font-bold px-2 py-0.5 rounded"
										style="background: {req.status === 'PENDING' ? 'rgba(249,115,22,0.1)' : req.status === 'APPROVED' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)'};
										       color: {req.status === 'PENDING' ? '#ea580c' : req.status === 'APPROVED' ? '#16a34a' : '#dc2626'};">
										{req.status}
									</span>
									{#if req.status === 'PENDING' && role !== 'PATIENT'}
										<button class="block mt-1.5 px-3 py-1 rounded text-xs font-medium cursor-pointer"
											style="background: linear-gradient(to bottom, #1e40af, #1e3a8a); color: white;
											       border: 1px solid rgba(0,0,0,0.15);"
											onclick={() => respondToRequest(req.id, 'APPROVED')}>
											Respond
										</button>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>
	{/if}
	{/if}
</div>

<!-- ═══════════════════════════════════════════════════════════════════
     MODALS
     ═══════════════════════════════════════════════════════════════════ -->

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

		<!-- Dynamic procedure-specific fields -->
		{#if crFields}
			<DynamicFormRenderer
				fields={crFields}
				bind:values={crFormData}
				idPrefix="cr"
				diagnosisSuggestions={crDiagnosisSuggestions}
				diagnosisLoading={crDiagnosisLoading}
				onDiagnosisInput={handleCrDiagnosisSearch}
				onDiagnosisSelect={handleCrDiagnosisSelect}
				onDiagnosisClear={() => { crIcdCode = ''; crIcdDescription = ''; crDiagnosisSuggestions = []; }}
			/>
			{#if crIcdCode}
				<div class="mt-1.5 flex items-center gap-1.5">
					<span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{crIcdCode}</span>
					<span class="text-[10px] text-gray-500 truncate">{crIcdDescription}</span>
				</div>
			{/if}

			{#if role !== 'FACULTY'}
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
			{crSubmitting ? 'Submitting...' : (role === 'FACULTY' ? 'Save Record' : 'Submit for Review')}
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
					placeholder="e.g. 120" />
			</div>
			<div>
				<label for="v-dia" class="block text-sm font-medium text-gray-700 mb-1">Diastolic (mmHg)</label>
				<input id="v-dia" type="number" bind:value={vDiastolic}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 80" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-hr" class="block text-sm font-medium text-gray-700 mb-1">Heart Rate (bpm)</label>
				<input id="v-hr" type="number" bind:value={vHeartRate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 72" />
			</div>
			<div>
				<label for="v-spo2" class="block text-sm font-medium text-gray-700 mb-1">SpO₂ (%)</label>
				<input id="v-spo2" type="number" bind:value={vSpO2}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 98" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-temp" class="block text-sm font-medium text-gray-700 mb-1">Temperature (°F)</label>
				<input id="v-temp" type="number" step="0.1" bind:value={vTemp}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 98.6" />
			</div>
			<div>
				<label for="v-wt" class="block text-sm font-medium text-gray-700 mb-1">Weight (lbs)</label>
				<input id="v-wt" type="number" bind:value={vWeight}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 150" />
			</div>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label for="v-rr" class="block text-sm font-medium text-gray-700 mb-1">Respiratory Rate</label>
				<input id="v-rr" type="number" bind:value={vRespRate}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 16" />
			</div>
			<div>
				<label for="v-glu" class="block text-sm font-medium text-gray-700 mb-1">Blood Glucose</label>
				<input id="v-glu" type="number" bind:value={vGlucose}
					class="block w-full px-3 py-2 rounded-md text-sm"
					style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
					placeholder="e.g. 100" />
			</div>
		</div>
		<div>
			<label for="v-notes" class="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
			<textarea id="v-notes"
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
			<span class="text-blue-900 font-semibold">Medications</span>
		</div>
	{/snippet}

	<div class="space-y-4">
		<div>
			<label for="rx-name" class="block text-sm font-medium text-gray-700 mb-1">
				Medication Name <span class="text-red-500">*</span>
			</label>
			<input id="rx-name" type="text" bind:value={rxName}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. Lisinopril" />
		</div>
		<div>
			<label for="rx-dose" class="block text-sm font-medium text-gray-700 mb-1">
				Dosage <span class="text-red-500">*</span>
			</label>
			<input id="rx-dose" type="text" bind:value={rxDosage}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. 10mg" />
		</div>
		<div>
			<label for="rx-freq" class="block text-sm font-medium text-gray-700 mb-1">
				Frequency <span class="text-red-500">*</span>
			</label>
			<select id="rx-freq" bind:value={rxFrequency}
				class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
				<option value="">Select frequency</option>
				<option value="Once daily">Once daily</option>
				<option value="Twice daily">Twice daily</option>
				<option value="Three times daily">Three times daily</option>
				<option value="Four times daily">Four times daily</option>
				<option value="Every 8 hours">Every 8 hours</option>
				<option value="Every 12 hours">Every 12 hours</option>
				<option value="As needed">As needed</option>
				<option value="Once weekly">Once weekly</option>
			</select>
		</div>
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
		<div>
			<label for="rx-inst" class="block text-sm font-medium text-gray-700 mb-1">Instructions</label>
			<textarea id="rx-inst" bind:value={rxInstructions}
				class="block w-full px-3 py-2 rounded-md text-sm resize-none" rows="3"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="Special instructions for taking this medication"></textarea>
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

<!-- Patient Prescription Request Modal -->
{#if showRequestPrescriptionModal}
<AquaModal onclose={() => { showRequestPrescriptionModal = false; resetRequestForm(); }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Send class="w-5 h-5 text-orange-600" />
			<span class="font-semibold text-gray-800">Request Prescription</span>
		</div>
	{/snippet}

	<p class="text-xs text-gray-500 mb-4">Submit a request for a prescription refill or new medication</p>
	<div class="space-y-4">
		<div>
			<label for="pr-med" class="block text-sm font-medium text-gray-700 mb-1">
				Medication <span class="text-red-500">*</span>
			</label>
			<input id="pr-med" type="text" bind:value={prMedication}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. Metformin" />
		</div>
		<div>
			<label for="pr-dose" class="block text-sm font-medium text-gray-700 mb-1">Dosage</label>
			<input id="pr-dose" type="text" bind:value={prDosage}
				class="block w-full px-3 py-2 rounded-md text-sm"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. 500mg" />
		</div>
		<div>
			<label for="pr-notes" class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
			<textarea id="pr-notes" bind:value={prNotes}
				class="block w-full px-3 py-2 rounded-md text-sm resize-none" rows="3"
				style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
				placeholder="e.g. Running low on medication, need refill"></textarea>
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-6">
		<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={() => { showRequestPrescriptionModal = false; resetRequestForm(); }}
			disabled={prSubmitting}>Cancel</button>
		<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #f97316, #ea580c); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={submitPrescriptionRequest}
			disabled={prSubmitting || !prMedication}>
			{prSubmitting ? 'Submitting...' : 'Submit Request'}
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
		<!-- Status Toggle -->
		<div>
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
			<div class="flex gap-2">
				{#each ['ACTIVE', 'COMPLETED'] as st}
					<button
						class="flex-1 py-2 rounded-md text-sm font-medium cursor-pointer"
						style="background: {editRxStatus === st ? (st === 'ACTIVE' ? 'linear-gradient(to bottom, #4cd964, #2ac845)' : 'linear-gradient(to bottom, #6b7280, #4b5563)') : 'linear-gradient(to bottom, #f0f4fa, #d5dde8)'};
						       color: {editRxStatus === st ? 'white' : '#64748b'};
						       border: 1px solid rgba(0,0,0,0.2);
						       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,{editRxStatus === st ? '0.4' : '0.8'});"
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
				<option value="Once daily">Once daily</option>
				<option value="Twice daily">Twice daily</option>
				<option value="Three times daily">Three times daily</option>
				<option value="Four times daily">Four times daily</option>
				<option value="Every 8 hours">Every 8 hours</option>
				<option value="Every 12 hours">Every 12 hours</option>
				<option value="As needed">As needed</option>
				<option value="Once weekly">Once weekly</option>
			</select>
		</div>
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
