<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, scale, slide } from 'svelte/transition';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { formsApi } from '$lib/api/forms';
	import { facultyApi } from '$lib/api/faculty';
	import type { VitalParameterConfig } from '$lib/api/types';
	import type { Report } from '$lib/api/types';
	import { autocompleteApi, type DiagnosisSuggestion } from '$lib/api/autocomplete';
	import {
		defaultAdmissionRequestFields,
		defaultPrescriptionCreateFields,
		defaultPrescriptionEditFields,
		defaultPrescriptionRequestFields,
		defaultVitalEntryFields,
	} from '$lib/config/default-form-definitions';
	import type { FormDefinition, FormFieldDefinition } from '$lib/types/forms';
	import {
		appendSupplementalText,
		asOptionalNumber,
		asOptionalString,
		buildCaseRecordDescription,
		buildCaseRecordProcedureMap,
		buildSupplementalFormDescription,
		mergeFieldOptions,
		mergeProcedureMaps,
		persistFormFiles,
		resolveCaseRecordFields,
		resolveFormFieldsByType,
		stringifyFormValue,
	} from '$lib/utils/forms';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import Autocomplete from '$lib/components/ui/Autocomplete.svelte';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import PrescriptionForm from '$lib/components/PrescriptionForm.svelte';
	import { Chart, registerables } from 'chart.js';
	import {
		AlertTriangle, FileText, HeartPulse, Pill, Clock, Plus,
		CheckCircle2, ChevronDown, ChevronRight, User, Users,
		Thermometer, Droplet, Activity, Scale, Wind, CircleDot,
		Phone, Mail, MapPin, Shield, Edit, X,
		Trash2, CheckCircle, Send, History, ClipboardList, TestTube,
		Image as ImageIcon
	} from 'lucide-svelte';

	Chart.register(...registerables);

	interface Props {
		patientId: string;
		canEdit?: boolean;
	}
	const { patientId, canEdit = true }: Props = $props();
	const pid = $derived(patientId);

	const auth = get(authStore);
	const role = auth.role;
	const studentReadOnly = $derived(role === 'STUDENT' && !canEdit);
	const studentEditAllowed = $derived(role !== 'STUDENT' || canEdit);
	const interactiveClinicalAccess = $derived(role !== 'PATIENT' && (role !== 'STUDENT' || canEdit));

	function showReadOnlyToast() {
		toastStore.addToast('This patient is not assigned to you. You can view details, but editing is disabled.', 'info');
	}

	// ── Core data (reactive) ──────────────────────────────────────
	let patient: any = $state(null);
	let caseRecords: any[] = $state([]);
	let vitals: any[] = $state([]);
	let medications: any[] = $state([]);
	let prescriptions: any[] = $state([]);
	let prescriptionRequests: any[] = $state([]);
	let reports: Report[] = $state([]);
	let admissions: any[] = $state([]);
	let alertHistory: any[] = $state([]);
	let loading = $state(true);

	// Reference data
	let facultyApprovers: { id: string; name: string; department: string }[] = $state([]);
	let procedureMap: Record<string, string[]> = $state({});
	let caseRecordForms: FormDefinition[] = $state([]);
	let departments: string[] = $state([]);
	let studentData: any = $state(null);
	let facultyData: any = $state(null);
	let vitalParameterConfigs: VitalParameterConfig[] = $state([]);

	// ── UI State ──────────────────────────────────────────────────
	let activeTab = $state('case-records');
	let trendsView = $state<'charts' | 'table'>('charts');
	const tabs = [
		{ id: 'case-records', label: 'Case Records', icon: FileText },
		{ id: 'trends', label: 'Trends', icon: HeartPulse },
		{ id: 'medications', label: 'Medications', icon: Pill },
		{ id: 'investigations', label: 'Investigations', icon: TestTube },
		{ id: 'radiology', label: 'Radiology', icon: Activity },
		{ id: 'gallery', label: 'Gallery', icon: ImageIcon },
	];

	// Modals
	let showAddRecordModal = $state(false);
	let showAddVitalModal = $state(false);
	let showAddPrescriptionModal = $state(false);
	let showRequestPrescriptionModal = $state(false);
	let showAdmissionRequestModal = $state(false);
	let showEditEmergencyModal = $state(false);
	let showAddInsuranceModal = $state(false);
	let showAdmissionHistoryModal = $state(false);

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
	let selectedCrFormId = $state('');
	let crFormSearch = $state('');
	let crFacultyId = $state('');
	let crSubmitting = $state(false);
	let crFormData: Record<string, any> = $state({});
	let crDiagnosisSuggestions: DiagnosisSuggestion[] = $state([]);
	let crDiagnosisLoading = $state(false);
	let crIcdCode = $state('');
	let crIcdDescription = $state('');
	let selectedVitalFormId = $state('');
	let vitalFormSearch = $state('');

	const defaultVitalForm: FormDefinition = {
		id: '__default_vital_entry__',
		slug: 'default-vital-entry',
		name: 'Quick Vital Entry',
		description: 'Default vital entry template for major parameters.',
		form_type: 'VITAL_ENTRY',
		section: 'CLINICAL',
		department: null,
		procedure_name: null,
		fields: defaultVitalEntryFields,
		sort_order: 0,
		is_active: true,
		created_at: null,
		updated_at: null,
	};

	const supportedVitalKeys = new Set([
		'systolic_bp',
		'diastolic_bp',
		'heart_rate',
		'respiratory_rate',
		'temperature',
		'oxygen_saturation',
		'weight',
		'blood_glucose',
		'cholesterol',
		'bmi',
		'creatinine',
		'urea',
		'sodium',
		'potassium',
		'sgot',
		'sgpt',
		'hemoglobin',
		'wbc',
		'platelet',
		'rbc',
		'hct',
	]);

	const configuredVitalFields = $derived.by<FormFieldDefinition[]>(() =>
		vitalParameterConfigs
			.filter((parameter) => supportedVitalKeys.has(parameter.name))
			.map((parameter) => ({
				key: parameter.name,
				label: parameter.display_name,
				type: 'number' as const,
				placeholder: parameter.unit ? `${parameter.display_name} (${parameter.unit})` : parameter.display_name,
				help_text:
					parameter.min_value !== null && parameter.min_value !== undefined && parameter.max_value !== null && parameter.max_value !== undefined
						? `Reference range: ${parameter.min_value} - ${parameter.max_value}${parameter.unit ? ` ${parameter.unit}` : ''}`
						: parameter.unit ?? undefined,
			}))
	);

	const selectedCrForm = $derived(
		caseRecordForms.find(f => f.id === selectedCrFormId) || null
	);

	const searchableCrForms = $derived.by(() =>
		caseRecordForms.map((form) => ({
			...form,
			meta: [form.department, form.procedure_name, form.description].filter(Boolean).join(' · '),
			badge: form.department || '',
		}))
	);

	const filteredCrForms = $derived.by(() => {
		const query = crFormSearch.trim().toLowerCase();
		if (!query) return searchableCrForms;
		return searchableCrForms.filter((form) =>
			[form.name, form.department, form.procedure_name, form.description]
				.filter(Boolean)
				.some((value) => String(value).toLowerCase().includes(query))
		);
	});

	const crFields: FormFieldDefinition[] | null = $derived(
		selectedCrForm ? selectedCrForm.fields : null
	);
	const vitalFormOptions = $derived.by((): FormDefinition[] => {
		const activeVitalForms = caseRecordForms.filter(
			(form) => form.form_type === 'VITAL_ENTRY' && form.is_active
		);
		return [
			defaultVitalForm,
			...activeVitalForms.filter((form) => form.id !== defaultVitalForm.id),
		];
	});
	const searchableVitalForms = $derived.by(() =>
		vitalFormOptions.map((form) => ({
			...form,
			meta: [form.department, form.procedure_name, form.description].filter(Boolean).join(' · '),
			badge: form.department || 'Vitals',
		}))
	);
	const filteredVitalForms = $derived.by(() => {
		const query = vitalFormSearch.trim().toLowerCase();
		if (!query) return searchableVitalForms;
		return searchableVitalForms.filter((form) =>
			[form.name, form.department, form.procedure_name, form.description]
				.filter(Boolean)
				.some((value) => String(value).toLowerCase().includes(query))
		);
	});
	const selectedVitalForm = $derived(
		vitalFormOptions.find((form) => form.id === selectedVitalFormId) || vitalFormOptions[0] || defaultVitalForm
	);
	const selectedVitalFields: FormFieldDefinition[] = $derived(
		selectedVitalForm?.id === defaultVitalForm.id
			? (configuredVitalFields.length > 0 ? configuredVitalFields : defaultVitalEntryFields)
			: (selectedVitalForm?.fields?.length ? selectedVitalForm.fields : (configuredVitalFields.length > 0 ? configuredVitalFields : defaultVitalEntryFields))
	);
	const majorVitalFieldKeys = new Set([
		'systolic_bp',
		'diastolic_bp',
		'heart_rate',
		'respiratory_rate',
		'blood_glucose',
	]);
	const majorVitalFieldMap = $derived.by(() => {
		const map = new Map<string, FormFieldDefinition>();
		for (const field of selectedVitalFields) {
			if (majorVitalFieldKeys.has(field.key)) {
				map.set(field.key, field);
			}
		}
		return map;
	});
	const supplementalVitalFields = $derived.by(() => {
		return selectedVitalFields.filter((field) => !majorVitalFieldKeys.has(field.key));
	});
	const prescriptionCreateFields = $derived(
		resolveFormFieldsByType(caseRecordForms, 'PRESCRIPTION_CREATE', defaultPrescriptionCreateFields)
	);
	const prescriptionEditFields = $derived(
		resolveFormFieldsByType(caseRecordForms, 'PRESCRIPTION_EDIT', defaultPrescriptionEditFields)
	);
	const prescriptionRequestFields = $derived(
		resolveFormFieldsByType(caseRecordForms, 'PRESCRIPTION_REQUEST', defaultPrescriptionRequestFields)
	);
	const defaultPrescriptionFrequency = $derived.by(() => {
		const frequencyField = prescriptionCreateFields.find(
			(field) => field.key === 'frequency' && field.type === 'select'
		);
		return frequencyField?.options?.[0] ?? '';
	});
	const admissionRequestFields = $derived(
		mergeFieldOptions(
			resolveFormFieldsByType(caseRecordForms, 'ADMISSION_REQUEST', defaultAdmissionRequestFields),
			{ department: departments }
		)
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

	function crFormDisplayLabel(form: FormDefinition) {
		const suffix = [form.department, form.procedure_name].filter(Boolean).join(' · ');
		return suffix ? `${form.name} · ${suffix}` : form.name;
	}

	function handleCrFormSearch(query: string) {
		if (selectedCrFormId && selectedCrForm && query !== crFormDisplayLabel(selectedCrForm)) {
			clearCrFormSelection();
		}
	}

	function handleCrFormSelect(form: FormDefinition) {
		selectedCrFormId = form.id;
		crFormSearch = crFormDisplayLabel(form);
	}

	function handleCrFormClear() {
		crFormSearch = '';
		clearCrFormSelection();
	}

	function clearCrFormSelection() {
		selectedCrFormId = '';
		crFormData = {};
		crIcdCode = '';
		crIcdDescription = '';
		crDiagnosisSuggestions = [];
	}

	function vitalFormDisplayLabel(form: FormDefinition) {
		const suffix = [form.department, form.procedure_name].filter(Boolean).join(' · ');
		return suffix ? `${form.name} · ${suffix}` : form.name;
	}

	function setDefaultVitalFormSelection() {
		const defaultForm = vitalFormOptions.find((form) => form.id === defaultVitalForm.id) || defaultVitalForm;
		selectedVitalFormId = defaultForm.id;
		vitalFormSearch = vitalFormDisplayLabel(defaultForm);
	}

	function handleVitalFormSelect(form: FormDefinition) {
		selectedVitalFormId = form.id;
		vitalFormSearch = vitalFormDisplayLabel(form);
	}

	function handleVitalFormClear() {
		setDefaultVitalFormSelection();
	}

	function openVitalModal() {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}
		resetVitalForm();
		showAddVitalModal = true;
	}

	// ── Add Vital form ────────────────────────────────────────────
	let vitalFormData: Record<string, any> = $state({});
	let vSubmitting = $state(false);

	// ── Add Prescription form ─────────────────────────────────────
	let prescriptionFormData: Record<string, any> = $state({
		start_date: new Date().toISOString().split('T')[0],
	});
	let rxSubmitting = $state(false);

	// ── Patient Prescription Request form ─────────────────────────
	let prescriptionRequestFormData: Record<string, any> = $state({});
	let prSubmitting = $state(false);
	let admissionRequestFormData: Record<string, any> = $state({});
	let admissionFacultyId = $state('');
	let admissionSubmitting = $state(false);
	let admissionError = $state('');

	// ── Edit Prescription ─────────────────────────────────────────
	let showEditPrescriptionModal = $state(false);
	let editRxId = $state('');
	let editPrescriptionFormData: Record<string, any> = $state({});
	let editRxStatus = $state('ACTIVE');
	let editRxMedId = $state('');
	let editRxSubmitting = $state(false);

	// ── Vitals Chart ──────────────────────────────────────────────
	let selectedParameter = $state('bp');
	let selectedTimeRange = $state('30');
	let groupViewMode = $state(true);
	let expandedInvestigationId = $state('');
	let galleryFilter = $state<'clinical' | 'investigations' | 'documents'>('documents');
	let showAllGallery = $state(true);
	let chartCanvas: HTMLCanvasElement = $state(undefined as any);
	let chartInstance: Chart | null = null;

	type GalleryItem = {
		id: string;
		title: string;
		description?: string;
		url: string;
		reportTitle: string;
		reportType: string;
		reportDate: string;
		mediaType?: string;
		category: 'clinical' | 'investigations' | 'documents';
		badge: string;
	};

	type TrendTooltipItem = {
		label: string;
		value: string;
		color: string;
		y: number;
	};

	let trendTooltip = $state({
		visible: false,
		x: 0,
		label: '',
		items: [] as TrendTooltipItem[],
	});

	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	const activeAlerts = $derived(
		patient?.medical_alerts?.filter((a: any) => a.is_active !== false) ?? []
	);
	const alertPanelOpen = $derived(showAlertInput || showAlertHistory);
	const diagnosisPanelOpen = $derived(showDiagnosisInput || showDiagnosisHistory);
	const currentAdmission = $derived(
		admissions.find((a: any) => a.status === 'Active') ?? null
	);
	const pendingAdmission = $derived(
		admissions.find((a: any) => a.status === 'Pending Approval') ?? null
	);
	const investigationReports = $derived.by(() =>
		reports.filter((report) => report.type !== 'Radiology')
	);
	const radiologyReports = $derived.by(() =>
		reports.filter((report) => report.type === 'Radiology')
	);
	const galleryItems = $derived.by<GalleryItem[]>(() =>
		reports.flatMap((report) =>
			(report.images || []).map((image) => ({
				id: image.id,
				title: image.title,
				description: image.description,
				url: image.url,
				reportTitle: report.title,
				reportType: report.type,
				reportDate: report.date,
				mediaType: image.type,
				category: classifyGalleryItem(report.type, image.type, image.title, image.description),
				badge: resolveGalleryBadge(image.type, image.title, image.description),
			}))
		)
	);
	const filteredGalleryItems = $derived.by(() =>
		galleryItems.filter((item) => item.category === galleryFilter)
	);
	const visibleGalleryItems = $derived.by(() =>
		showAllGallery ? filteredGalleryItems : filteredGalleryItems.slice(0, 2)
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
		trendTooltip = { visible: false, x: 0, label: '', items: [] };

		const vitalsSlice = vitals.slice(0, parseInt(selectedTimeRange)).reverse();
		const labels = vitalsSlice.map((v: any) => {
			const d = new Date(v.recorded_at);
			return `${d.getMonth() + 1}/${d.getDate()}`;
		});

		let datasets: any[];

		if (groupViewMode) {
			datasets = [
				{ label: 'Sys', data: vitalsSlice.map((v: any) => v.systolic_bp ?? null), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#ef4444', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#ef4444' },
				{ label: 'Dia', data: vitalsSlice.map((v: any) => v.diastolic_bp ?? null), borderColor: '#fb7185', backgroundColor: 'rgba(251,113,133,0.1)', borderDash: [5, 5], tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#fb7185', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#fb7185' },
				{ label: 'Heart Rate', data: vitalsSlice.map((v: any) => v.heart_rate ?? null), borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.1)', tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#f97316', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#f97316' },
				{ label: 'Temperature', data: vitalsSlice.map((v: any) => v.temperature ?? null), borderColor: '#ff4d5a', backgroundColor: 'rgba(255,77,90,0.1)', tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#ff4d5a', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#ff4d5a' },
				{ label: 'Oxygen Saturation', data: vitalsSlice.map((v: any) => v.oxygen_saturation ?? null), borderColor: '#157efb', backgroundColor: 'rgba(21,126,251,0.1)', tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#157efb', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#157efb' },
				{ label: 'Respiratory Rate', data: vitalsSlice.map((v: any) => v.respiratory_rate ?? null), borderColor: '#7dc9e8', backgroundColor: 'rgba(125,201,232,0.1)', tension: 0.42, fill: false, pointRadius: 2.5, pointHoverRadius: 5, pointHoverBorderWidth: 2, pointBackgroundColor: '#ffffff', pointBorderColor: '#7dc9e8', pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#7dc9e8' },
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

		const hoverGuidePlugin = {
			id: 'hoverGuide',
			afterDatasetsDraw(chart: any) {
				const activeElements = chart.tooltip?.getActiveElements?.() || [];
				if (!activeElements.length) return;
				const x = activeElements[0].element.x;
				const { ctx, chartArea } = chart;
				ctx.save();
				ctx.beginPath();
				ctx.moveTo(x, chartArea.top);
				ctx.lineTo(x, chartArea.bottom);
				ctx.lineWidth = 1.5;
				ctx.strokeStyle = 'rgba(148,163,184,0.7)';
				ctx.stroke();
				ctx.restore();
			},
		};

		chartInstance = new Chart(chartCanvas, {
			type: 'line',
			data: { labels, datasets },
			plugins: [hoverGuidePlugin],
			options: {
				responsive: true, maintainAspectRatio: false,
				interaction: { mode: 'index', intersect: false },
				animation: { duration: 260, easing: 'easeOutQuart' },
				plugins: {
					legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
					tooltip: {
						enabled: false,
						external: (context: any) => {
							const tooltipModel = context.tooltip;
							if (!tooltipModel || tooltipModel.opacity === 0 || !tooltipModel.dataPoints?.length) {
								trendTooltip = { visible: false, x: 0, label: '', items: [] };
								return;
							}

							const chart = context.chart;
							const x = Math.min(tooltipModel.caretX + 20, chart.width - 220);
							trendTooltip = {
								visible: true,
								x,
								label: tooltipModel.title?.[0] || '',
								items: tooltipModel.dataPoints
									.filter((point: any) => point.raw !== null && point.raw !== undefined)
									.map((point: any) => ({
										label: point.dataset.label,
										value: formatTrendTooltipValue(point.dataset.label, point.raw),
										color: point.dataset.borderColor,
										y: point.element.y - 18,
									})),
							};
						},
					},
				},
				scales: {
					y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { font: { size: 9 } } },
					x: { grid: { display: false }, ticks: { font: { size: 9 }, maxTicksLimit: 10 } },
				},
			},
		});
	}

	$effect(() => {
		if (activeTab === 'trends' && trendsView === 'charts') {
			selectedParameter; selectedTimeRange; groupViewMode; vitals;
			setTimeout(buildChart, 50);
		}
	});

	function formatTrendTooltipValue(label: string, value: number) {
		if (label === 'Temperature') return `${Math.round(value)}`;
		return `${Math.round(value)}`;
	}

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

	function formatReportDate(date: string, time?: string): string {
		const formattedDate = new Date(date).toLocaleDateString('en-US', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
		});
		return time ? `${formattedDate} · ${time}` : formattedDate;
	}

	function getReportStatusTone(status: Report['status']) {
		if (status === 'CRITICAL') return { bg: 'rgba(239,68,68,0.12)', text: '#dc2626', border: 'rgba(248,113,113,0.25)' };
		if (status === 'ABNORMAL') return { bg: 'rgba(249,115,22,0.12)', text: '#ea580c', border: 'rgba(251,146,60,0.25)' };
		if (status === 'PENDING') return { bg: 'rgba(148,163,184,0.12)', text: '#475569', border: 'rgba(148,163,184,0.25)' };
		return { bg: 'rgba(34,197,94,0.12)', text: '#15803d', border: 'rgba(74,222,128,0.25)' };
	}

	function classifyGalleryItem(reportType: string, imageType?: string, title?: string, description?: string) {
		const combined = `${reportType} ${imageType || ''} ${title || ''} ${description || ''}`.toLowerCase();
		if (reportType === 'Radiology') return 'investigations';
		if (
			combined.includes('document') ||
			combined.includes('consent') ||
			combined.includes('insurance') ||
			combined.includes('summary') ||
			combined.includes('pdf') ||
			combined.includes('form')
		) {
			return 'documents';
		}
		return 'clinical';
	}

	function resolveGalleryBadge(imageType?: string, title?: string, description?: string) {
		const combined = `${imageType || ''} ${title || ''} ${description || ''}`.toLowerCase();
		if (combined.includes('pdf') || combined.includes('document') || combined.includes('form') || combined.includes('insurance') || combined.includes('consent')) {
			return 'DOCUMENT';
		}
		return 'IMAGE';
	}

	function toggleInvestigationReport(reportId: string) {
		expandedInvestigationId = expandedInvestigationId === reportId ? '' : reportId;
	}

	function getInvestigationIconTone(status: Report['status']) {
		if (status === 'PENDING') {
			return {
				bg: 'linear-gradient(to bottom, #fb923c, #f97316)',
				icon: Clock,
			};
		}
		return {
			bg: 'linear-gradient(to bottom, #22c55e, #16a34a)',
			icon: CheckCircle2,
		};
	}

	function viewInvestigationReport(report: Report) {
		if (report.file_url) {
			window.open(report.file_url, '_blank', 'noopener,noreferrer');
			return;
		}
		toggleInvestigationReport(report.id);
	}

	function requestLabOrder() {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}
		toastStore.addToast('Lab ordering workflow is not available in this view yet', 'info');
	}

	function openRadiologyViewer(reportId?: string) {
		const targetId = reportId ?? radiologyReports[0]?.id;
		if (!targetId) {
			activeTab = 'radiology';
			return;
		}
		void goto(`/patients/${pid}/radiology/${targetId}`);
	}

	function openTab(tabId: string) {
		if (tabId === 'radiology' && radiologyReports.length > 0) {
			openRadiologyViewer();
			return;
		}
		activeTab = tabId;
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
				const [patientData, caseData, vitalData, rxData, depts, procs, approvers, rxReqs, reportData, admissionData, forms, vitalParameters] =
					await Promise.all([
						patientApi.getPatient(patientId),
						studentApi.getCaseRecords(studentData.id, patientId),
						patientApi.getVitals(patientId, 30).catch(() => []),
						patientApi.getPrescriptions(patientId).catch(() => []),
						studentApi.getDepartments().catch(() => []),
						studentApi.getProcedures().catch(() => ({})),
						studentApi.getFacultyApprovers().catch(() => []),
						patientApi.getPrescriptionRequests(patientId).catch(() => []),
						patientApi.getReports(patientId).catch(() => []),
						patientApi.getAdmissions(patientId).catch(() => []),
						formsApi.getForms().catch(() => []),
						patientApi.getActiveVitalParameters().catch(() => []),
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
				vitalParameterConfigs = vitalParameters;
				facultyApprovers = approvers;
				prescriptionRequests = rxReqs;
				reports = reportData;
				admissions = admissionData;
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
					patientApi.getReports(patientId).catch(() => []),
					patientApi.getAdmissions(patientId).catch(() => []),
				];
				if (role === 'FACULTY') {
					fetchList.push(
						studentApi.getDepartments().catch(() => []),
						studentApi.getProcedures().catch(() => ({})),
						formsApi.getForms().catch(() => []),
						patientApi.getActiveVitalParameters().catch(() => []),
					);
				}
				if (role === 'ADMIN') {
					fetchList.push(
						studentApi.getDepartments().catch(() => []),
						studentApi.getProcedures().catch(() => ({})),
						formsApi.getForms().catch(() => []),
						patientApi.getActiveVitalParameters().catch(() => []),
					);
				}
				const results = await Promise.all(fetchList);
				patient = results[0];
				caseRecords = results[1];
				vitals = results[2];
				prescriptions = results[3];
				medications = results[3].flatMap((rx: any) => rx.medications || []);
				prescriptionRequests = results[4];
				reports = results[5];
				admissions = results[6];
				if (role === 'FACULTY' || role === 'ADMIN') {
					const merged = mergeProcedureMaps(results[8] || {}, buildCaseRecordProcedureMap(results[9] || []));
					departments = Array.from(new Set([...(results[7] || []), ...Object.keys(merged)])).sort();
					procedureMap = merged;
					caseRecordForms = results[9] || [];
					vitalParameterConfigs = results[10] || [];
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
			reports = [];
			admissions = [];
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
				const [patientData, vitalData, rxData, rxReqs, reportData, admissionData] = await Promise.all([
					patientApi.getPatient(patientId),
					patientApi.getVitals(patientId, 30).catch(() => []),
					patientApi.getPrescriptions(patientId).catch(() => []),
					patientApi.getPrescriptionRequests(patientId).catch(() => []),
					patientApi.getReports(patientId).catch(() => []),
					patientApi.getAdmissions(patientId).catch(() => []),
				]);
				patient = patientData;
				vitals = vitalData;
				prescriptions = rxData;
				medications = rxData.flatMap((rx: any) => rx.medications || []);
				prescriptionRequests = rxReqs;
				reports = reportData;
				admissions = admissionData;
			} catch (err) {
				// Silently fail on auto-refresh
			}
		}, 30000);
		return () => clearInterval(interval);
	});

	// ── Case Record Submit ────────────────────────────────────────
	function resetCaseRecordForm() {
		selectedCrFormId = ''; crFormSearch = ''; crFacultyId = '';
		crFormData = {}; crDiagnosisSuggestions = [];
		crIcdCode = ''; crIcdDescription = '';
	}

	async function submitCaseRecord() {
		if (!patient || crSubmitting || !selectedCrForm) return;
		if (studentReadOnly) return;
		if (role === 'STUDENT' && !studentData) return;
		crSubmitting = true;
		try {
			const now = new Date();
			const payload: Record<string, unknown> = {
				patient_id: patient.id,
				department: selectedCrForm.department || '',
				procedure: selectedCrForm.procedure_name || '',
				findings: '',
				diagnosis: stringifyFormValue(crFormData['diagnosis']) || '',
				treatment: '',
				notes: stringifyFormValue(crFormData['notes']) || '',
				description: buildCaseRecordDescription(crFields, crFormData),
				icd_code: crIcdCode || undefined,
				icd_description: crIcdDescription || undefined,
				form_values: crFormData,
				form_name: selectedCrForm.name,
				form_description: selectedCrForm.description || undefined,
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
			toastStore.addToast('Case record submitted. summary pending.', 'success');
		} catch (err: any) {
			console.error('Failed to submit case record', err);
			toastStore.addToast(err?.response?.data?.detail || 'Failed to submit case record', 'error');
		}
		finally { crSubmitting = false; }
	}

	// ── Vital Submit ──────────────────────────────────────────────
	function resetVitalForm() {
		vitalFormData = {};
		setDefaultVitalFormSelection();
	}

	async function submitVital() {
		if (!patient || vSubmitting) return;
		if (studentReadOnly) return;
		vSubmitting = true;
		try {
			const submittedValues = await persistFormFiles(
				selectedVitalFields,
				vitalFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'patient-profile-vital'
			);
			const urineOutput = asOptionalNumber(submittedValues.urine_output_ml);
			const vitalPayload = selectedVitalFields.reduce<Record<string, number | string>>((payload, field) => {
				if (!supportedVitalKeys.has(field.key)) {
					return payload;
				}
				const value = asOptionalNumber(submittedValues[field.key]);
				if (value !== undefined) {
					payload[field.key] = value;
				}
				return payload;
			}, {
				recorded_by: studentData?.name || 'Student',
			});
			await patientApi.createVital(patient.id, vitalPayload);
			if (urineOutput) {
				if (currentAdmission?.id) {
					try {
						await patientApi.addIOEvent(currentAdmission.id, {
							event_time: new Date().toISOString(),
							event_type: 'URINE',
							amount_ml: urineOutput,
							description: 'Quick vital entry',
						});
					} catch (error) {
						console.error('Failed to record urine output', error);
						toastStore.addToast('Vital saved, but urine output could not be recorded.', 'error');
					}
				} else {
					toastStore.addToast('Vital saved. Urine output requires an active admission.', 'info');
				}
			}
			vitals = await patientApi.getVitals(patient.id, 30);
			showAddVitalModal = false;
			resetVitalForm();
			toastStore.addToast('Vital entry saved.', 'success');
		} catch (err) { console.error('Failed to save vital', err); }
		finally { vSubmitting = false; }
	}

	// ── Prescription Submit ───────────────────────────────────────
	function resetPrescriptionForm() {
		const today = new Date().toISOString().split('T')[0];
		prescriptionFormData = {
			start_date: today,
			end_date: today,
			frequency: defaultPrescriptionFrequency,
		};
	}

	function getPrescriptionAuthorMeta() {
		const activeAdmission = admissions.find((admission: any) => admission.status === 'Active') ?? admissions[0] ?? null;

		if (role === 'STUDENT') {
			return {
				doctor: studentData?.name || 'Student Clinician',
				department: studentData?.department || activeAdmission?.department || '',
			};
		}

		if (role === 'FACULTY') {
			return {
				doctor: facultyData?.name || 'Faculty Clinician',
				department: facultyData?.department || activeAdmission?.department || '',
			};
		}

		if (role === 'ADMIN') {
			return {
				doctor: 'Administrator',
				department: activeAdmission?.department || '',
			};
		}

		return {
			doctor: patient?.primary_doctor || 'Clinical Staff',
			department: activeAdmission?.department || '',
		};
	}

	async function submitPrescription() {
		if (!patient || rxSubmitting) return;
		if (studentReadOnly) return;
		rxSubmitting = true;
		try {
			const submittedValues = await persistFormFiles(
				prescriptionCreateFields,
				prescriptionFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'patient-profile-prescription'
			);
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.notes),
				buildSupplementalFormDescription(
					prescriptionCreateFields,
					submittedValues,
					new Set(['name', 'dosage', 'frequency', 'start_date', 'end_date', 'instructions', 'notes'])
				)
			);
			const authorMeta = getPrescriptionAuthorMeta();
			await patientApi.createPrescription(patient.id, {
				doctor: authorMeta.doctor,
				department: authorMeta.department,
				notes,
				medications: [{
					name: asOptionalString(submittedValues.name) || '',
					dosage: asOptionalString(submittedValues.dosage) || '',
					frequency: asOptionalString(submittedValues.frequency) || '',
					duration: asOptionalString(submittedValues.duration) || 'As directed',
					start_date: asOptionalString(submittedValues.start_date) || new Date().toISOString().split('T')[0],
					end_date: asOptionalString(submittedValues.end_date) || new Date().toISOString().split('T')[0],
					instructions: asOptionalString(submittedValues.instructions),
				}],
			});
			prescriptions = await patientApi.getPrescriptions(patient.id);
			medications = prescriptions.flatMap((rx: any) => rx.medications || []);
			showAddPrescriptionModal = false;
			resetPrescriptionForm();
			toastStore.addToast('Prescription added successfully', 'success');
		} catch (err) {
			console.error('Failed to create prescription', err);
			toastStore.addToast('Failed to create prescription', 'error');
		}
		finally { rxSubmitting = false; }
	}

	async function submitStudentPrescription(data: {
		diagnosis: string;
		medications: Array<{
			name: string;
			dosage: string;
			duration: string;
			frequency: string;
			timing: string;
			instructions: string;
		}>;
		faculty_id: string;
	}) {
		if (!patient || !studentData) return;
		if (studentReadOnly) return;
		try {
			const today = new Date().toISOString().split('T')[0];
			const medications = data.medications.map(med => ({
				name: med.name,
				dosage: med.dosage,
				frequency: med.frequency,
				duration: med.duration,
				timing: med.timing,
				instructions: med.instructions,
				start_date: today,
				end_date: today,
			}));
			await studentApi.submitPrescription(studentData.id, {
				patient_id: patient.id,
				faculty_id: data.faculty_id,
				department: studentData.department || '',
				diagnosis: data.diagnosis,
				notes: '',
				medications,
			});
			toastStore.addToast('Prescription submitted for approval', 'success');
			showAddPrescriptionModal = false;
		} catch (err) {
			console.error('Failed to submit prescription', err);
			toastStore.addToast('Failed to submit prescription', 'error');
			throw err;
		}
	}

	// ── Prescription Request Submit ───────────────────────────────
	function resetRequestForm() {
		prescriptionRequestFormData = {};
	}

	function resetAdmissionRequestForm() {
		admissionRequestFormData = {};
		admissionFacultyId = facultyApprovers[0]?.id || '';
		admissionError = '';
	}

	function openAdmissionRequestModal() {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}
		resetAdmissionRequestForm();
		showAdmissionRequestModal = true;
	}

	async function submitAdmissionRequest() {
		if (role !== 'STUDENT' || studentReadOnly || !patient || !studentData || admissionSubmitting) return;
		if (!admissionFacultyId) {
			admissionError = 'Please select a faculty approver';
			return;
		}
		if (!admissionRequestFormData.reason) {
			admissionError = 'Reason for admission is required';
			return;
		}

		admissionSubmitting = true;
		admissionError = '';
		try {
			const submittedValues = await persistFormFiles(
				admissionRequestFields,
				admissionRequestFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'patient-profile-admission-request'
			);
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.notes),
				buildSupplementalFormDescription(
					admissionRequestFields,
					submittedValues,
					new Set(['department', 'ward', 'bed_number', 'reason', 'diagnosis', 'notes', 'referring_doctor'])
				)
			);

			await studentApi.submitAdmissionRequest(studentData.id, {
				patient_id: patient.id,
				faculty_id: admissionFacultyId,
				department: asOptionalString(submittedValues.department),
				ward: asOptionalString(submittedValues.ward),
				bed_number: asOptionalString(submittedValues.bed_number),
				reason: asOptionalString(submittedValues.reason) || '',
				diagnosis: asOptionalString(submittedValues.diagnosis),
				notes,
				referring_doctor: asOptionalString(submittedValues.referring_doctor),
			});

			admissions = await patientApi.getAdmissions(patient.id);
			showAdmissionRequestModal = false;
			resetAdmissionRequestForm();
			toastStore.addToast('Admission request submitted successfully', 'success');
		} catch (err: any) {
			admissionError = err?.response?.data?.detail || 'Failed to submit admission request';
			toastStore.addToast(admissionError, 'error');
		} finally {
			admissionSubmitting = false;
		}
	}

	// ── Edit Prescription ─────────────────────────────────────────
	function openEditPrescription(rx: any) {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}
		editRxId = rx.id;
		editRxStatus = rx.status || 'ACTIVE';
		const med = rx.medications?.[0];
		editRxMedId = med?.id || '';
		editPrescriptionFormData = {
			status: rx.status || 'ACTIVE',
			name: med?.name || '',
			dosage: med?.dosage || '',
			frequency: med?.frequency || '',
			start_date: med?.start_date || '',
			end_date: med?.end_date || '',
			instructions: med?.instructions || '',
			notes: rx.notes || '',
		};
		showEditPrescriptionModal = true;
	}

	function resetEditForm() {
		editRxId = '';
		editPrescriptionFormData = {};
		editRxStatus = 'ACTIVE'; editRxMedId = '';
	}

	async function submitEditPrescription() {
		if (!patient || editRxSubmitting) return;
		editRxSubmitting = true;
		try {
			const submittedValues = await persistFormFiles(
				prescriptionEditFields,
				editPrescriptionFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'patient-profile-prescription-edit'
			);
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.notes),
				buildSupplementalFormDescription(
					prescriptionEditFields,
					submittedValues,
					new Set(['status', 'name', 'dosage', 'frequency', 'start_date', 'end_date', 'instructions', 'notes'])
				)
			);
			await patientApi.updatePrescription(patient.id, editRxId, {
				status: asOptionalString(submittedValues.status) || editRxStatus,
				notes,
				medications: [{
					id: editRxMedId || undefined,
					name: asOptionalString(submittedValues.name) || '',
					dosage: asOptionalString(submittedValues.dosage) || '',
					frequency: asOptionalString(submittedValues.frequency) || '',
					start_date: asOptionalString(submittedValues.start_date) || new Date().toISOString().split('T')[0],
					end_date: asOptionalString(submittedValues.end_date) || new Date().toISOString().split('T')[0],
					instructions: asOptionalString(submittedValues.instructions),
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
			const submittedValues = await persistFormFiles(
				prescriptionRequestFields,
				prescriptionRequestFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'patient-profile-prescription-request'
			);
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.notes),
				buildSupplementalFormDescription(
					prescriptionRequestFields,
					submittedValues,
					new Set(['medication', 'dosage', 'notes'])
				)
			);
			await patientApi.createPrescriptionRequest(patient.id, {
				medication: asOptionalString(submittedValues.medication) || '',
				dosage: asOptionalString(submittedValues.dosage),
				notes,
			});
			prescriptionRequests = await patientApi.getPrescriptionRequests(patient.id);
			showRequestPrescriptionModal = false;
			resetRequestForm();
		} catch (err) { console.error('Failed to create request', err); }
		finally { prSubmitting = false; }
	}

	async function respondToRequest(requestId: string, status: string) {
		if (!patient) return;
		if (studentReadOnly) return;
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
		if (studentReadOnly) return;
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
		if (studentReadOnly) return;
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

	async function toggleAlertDetails() {
		if (alertPanelOpen) {
			showAlertInput = false;
			showAlertHistory = false;
			return;
		}

		await loadAlertHistory();
	}

	function toggleAlertComposer() {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}

		const nextState = !showAlertInput;
		showAlertInput = nextState;

		if (nextState) {
			void loadAlertHistory();
		} else if (!showAlertHistory) {
			newAlertTitle = '';
		}
	}

	// ── Primary Diagnosis ─────────────────────────────────────────
	async function updateDiagnosis() {
		if (!patient || !newDiagnosis.trim() || diagnosisSubmitting) return;
		if (studentReadOnly) return;
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

	function toggleDiagnosisDetails() {
		if (diagnosisPanelOpen) {
			showDiagnosisInput = false;
			showDiagnosisHistory = false;
			return;
		}

		showDiagnosisHistory = true;
	}

	function toggleDiagnosisComposer() {
		if (studentReadOnly) {
			showReadOnlyToast();
			return;
		}

		const nextState = !showDiagnosisInput;
		showDiagnosisInput = nextState;
		showDiagnosisHistory = nextState || showDiagnosisHistory;
	}
</script>

<div class="space-y-3 px-3 py-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !patient}
		<div class="text-center py-12 text-gray-400">
			<p class="text-sm">Patient not found</p>
		</div>
	{:else}
	{#if studentReadOnly}
		<div class="rounded-[20px] px-4 py-3 text-sm font-medium text-amber-800"
			style="background: linear-gradient(to bottom, rgba(254,249,195,0.95), rgba(254,240,138,0.78)); border: 1px solid rgba(245,158,11,0.22); box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);">
			View only. This patient is in the selected clinic, but not assigned to you, so editing actions are disabled.
		</div>
	{/if}

	<div class="overflow-hidden rounded-[22px]"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(244,248,255,0.98)); border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 8px 24px rgba(15,23,42,0.08), inset 0 1px 0 rgba(255,255,255,0.85);">
		<div class="grid grid-cols-1 border-b border-slate-200/80 md:grid-cols-[1.05fr_1fr_1fr]">
			<div class="p-4 md:p-5" style="background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(247,250,255,0.92));">
				<div class="flex items-center gap-3">
					{#if patient.photo}
						<img src={patient.photo} alt={patient.name} class="h-14 w-14 rounded-full object-cover border-4 border-white shadow-md shrink-0" />
					{:else}
						<div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-xl font-bold text-white"
							style="background: linear-gradient(135deg, #60a5fa, #2563eb); border: 4px solid white; box-shadow: 0 8px 18px rgba(37,99,235,0.24);">
							{patient.name?.charAt(0) || 'P'}
						</div>
					{/if}
					<div class="min-w-0 flex-1">
						<h2 class="text-2xl font-black leading-none tracking-tight text-slate-900">{patient.name}</h2>
						<p class="mt-1.5 text-[11px] font-semibold tracking-wide text-slate-500">ID: {patient.patient_id}</p>
						<p class="mt-2 text-[13px] font-semibold text-slate-700">{patientAge()}, {patient.gender || '—'}, Blood: {patient.blood_group || '—'}</p>
						<p class="mt-1.5 text-[13px] text-slate-600">{patient.phone || '—'}</p>
					</div>
				</div>
			</div>

			<div class="border-t border-slate-200/80 p-4 md:border-l md:border-t-0 md:p-5"
				style="background: linear-gradient(135deg, rgba(254,242,242,0.95), rgba(254,226,226,0.82));">
				<div class="flex items-center justify-between gap-3">
					<button class="flex min-w-0 items-center gap-2 text-left cursor-pointer transition-transform duration-200 hover:-translate-y-0.5"
						type="button"
						onclick={toggleAlertDetails}>
						<AlertTriangle class="h-4 w-4 text-red-500" />
						<span class="text-[13px] font-black tracking-wide text-red-800">MEDICAL ALERTS</span>
						<ChevronDown class="h-4 w-4 text-red-400 transition-transform duration-300 {alertPanelOpen ? 'rotate-180' : ''}" />
					</button>
					<div class="flex gap-2">
						<button class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer"
							style="background: rgba(255,255,255,0.88); border: 1px solid rgba(59,130,246,0.18); box-shadow: 0 2px 6px rgba(15,23,42,0.1);"
							type="button"
							onclick={toggleAlertDetails}>
							<History class="h-3.5 w-3.5 text-blue-500" />
						</button>
						{#if studentEditAllowed}
						<button class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer"
							style="background: rgba(255,255,255,0.88); border: 1px solid rgba(59,130,246,0.18); box-shadow: 0 2px 6px rgba(15,23,42,0.1);"
							type="button"
							onclick={toggleAlertComposer}>
							<Plus class="h-3.5 w-3.5 text-blue-500" />
						</button>
						{/if}
					</div>
				</div>
				<div class="mt-4 flex flex-wrap gap-2">
					{#if activeAlerts.length > 0}
						{#each activeAlerts as alert (alert.id)}
							<span class="inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-[12px] font-semibold text-red-700"
								in:scale={{ duration: 180, start: 0.9 }}
								out:scale={{ duration: 140, start: 0.92 }}
								style="background: rgba(255,255,255,0.56); border: 1px solid rgba(248,113,113,0.18); box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);">
								{alert.title}
								{#if studentEditAllowed}
									<button class="cursor-pointer text-red-400 hover:text-red-600 leading-none" onclick={() => removeAlert(alert.id)}>×</button>
								{/if}
							</span>
						{/each}
					{:else}
						<p class="text-sm font-medium text-red-300">No active alerts</p>
					{/if}
				</div>
				{#if alertPanelOpen}
					<div class="mt-4 space-y-3 overflow-hidden" transition:slide={{ duration: 260 }}>
						{#if showAlertInput}
							<div class="rounded-2xl p-3" in:fade={{ duration: 180 }} out:fade={{ duration: 120 }} style="background: rgba(255,255,255,0.52); border: 1px solid rgba(248,113,113,0.14);">
								<div class="flex gap-2 items-center">
									<input type="text" bind:value={newAlertTitle} class="flex-1 rounded-xl px-3 py-2 text-sm bg-white outline-none transition-shadow duration-200 focus:shadow-[0_0_0_4px_rgba(239,68,68,0.12)]" style="border: 1px solid rgba(0,0,0,0.12);" placeholder="Enter alert..." onkeydown={(e) => e.key === 'Enter' && addAlert()} />
									<button class="rounded-xl px-3 py-2 text-xs font-bold text-white cursor-pointer transition-transform duration-200 hover:-translate-y-0.5" style="background: linear-gradient(to bottom, #ef4444, #dc2626);" onclick={addAlert} disabled={alertSubmitting}>Add</button>
									<button class="text-xs text-slate-400 cursor-pointer hover:text-slate-600" onclick={() => { showAlertInput = false; newAlertTitle = ''; }}>Close</button>
								</div>
							</div>
						{/if}

						{#if showAlertHistory}
							<div class="rounded-2xl p-3" in:fade={{ duration: 180 }} out:fade={{ duration: 120 }} style="background: rgba(255,255,255,0.52); border: 1px solid rgba(248,113,113,0.14);">
								<h4 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Alert History</h4>
								<div class="space-y-2 max-h-32 overflow-y-auto pr-1">
									{#each alertHistory as h}
										<div class="flex items-center gap-2 pl-2" in:fade={{ duration: 150 }} style="border-left: 2px solid {h.is_active ? '#ef4444' : '#d1d5db'};">
											<p class="text-xs flex-1" style="color: {h.is_active ? '#dc2626' : '#6b7280'};">{h.title}</p>
											<span class="text-[10px] px-1.5 py-0.5 rounded" style="background: {h.is_active ? 'rgba(239,68,68,0.1)' : 'rgba(0,0,0,0.05)'}; color: {h.is_active ? '#dc2626' : '#6b7280'};">{h.is_active ? 'Active' : 'Inactive'}</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<div class="border-t border-slate-200/80 p-4 md:border-l md:border-t-0 md:p-5"
				style="background: linear-gradient(135deg, rgba(219,234,254,0.96), rgba(191,219,254,0.82));">
				<div class="flex items-center justify-between gap-3">
					<button class="flex min-w-0 items-center gap-2 text-left cursor-pointer transition-transform duration-200 hover:-translate-y-0.5"
						type="button"
						onclick={toggleDiagnosisDetails}>
						<FileText class="h-4 w-4 text-blue-600" />
						<span class="text-[13px] font-black tracking-wide text-blue-800">PRIMARY DIAGNOSIS</span>
						<ChevronDown class="h-4 w-4 text-blue-400 transition-transform duration-300 {diagnosisPanelOpen ? 'rotate-180' : ''}" />
					</button>
					<div class="flex gap-2">
						<button class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer"
							style="background: rgba(255,255,255,0.88); border: 1px solid rgba(59,130,246,0.18); box-shadow: 0 2px 6px rgba(15,23,42,0.1);"
							type="button"
							onclick={toggleDiagnosisDetails}>
							<History class="h-3.5 w-3.5 text-blue-500" />
						</button>
						{#if studentEditAllowed}
						<button class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer"
							style="background: rgba(255,255,255,0.88); border: 1px solid rgba(59,130,246,0.18); box-shadow: 0 2px 6px rgba(15,23,42,0.1);"
							type="button"
							onclick={toggleDiagnosisComposer}>
							<Edit class="h-3.5 w-3.5 text-blue-500" />
						</button>
						{/if}
					</div>
				</div>
				<div class="mt-4">
					{#if patient.primary_diagnosis}
						<p class="text-[16px] font-black leading-tight text-slate-800">{patient.primary_diagnosis}</p>
						<p class="mt-2 text-[12px] font-medium text-slate-500">Last updated by {patient.diagnosis_doctor || 'Student'}{patient.diagnosis_date ? ` • ${patient.diagnosis_date}` : ''}{patient.diagnosis_time ? ` ${patient.diagnosis_time}` : ''}</p>
					{:else}
						<p class="text-sm font-medium text-blue-300">No diagnosis recorded</p>
					{/if}
				</div>
				{#if diagnosisPanelOpen}
					<div class="mt-4 space-y-3 overflow-hidden" transition:slide={{ duration: 260 }}>
						{#if showDiagnosisInput}
							<div class="rounded-2xl p-3" in:fade={{ duration: 180 }} out:fade={{ duration: 120 }} style="background: rgba(255,255,255,0.52); border: 1px solid rgba(96,165,250,0.16);">
								<div class="flex gap-2 items-center">
									<input type="text" bind:value={newDiagnosis} class="flex-1 rounded-xl px-3 py-2 text-sm bg-white outline-none transition-shadow duration-200 focus:shadow-[0_0_0_4px_rgba(59,130,246,0.12)]" style="border: 1px solid rgba(0,0,0,0.12);" placeholder="Enter diagnosis..." onkeydown={(e) => e.key === 'Enter' && updateDiagnosis()} />
									<button class="rounded-xl px-3 py-2 text-xs font-bold text-white cursor-pointer transition-transform duration-200 hover:-translate-y-0.5" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={updateDiagnosis} disabled={diagnosisSubmitting}>Save</button>
									<button class="text-xs text-slate-400 cursor-pointer hover:text-slate-600" onclick={() => { showDiagnosisInput = false; newDiagnosis = ''; }}>Close</button>
								</div>
							</div>
						{/if}

						{#if showDiagnosisHistory}
							<div class="rounded-2xl p-3" in:fade={{ duration: 180 }} out:fade={{ duration: 120 }} style="background: rgba(255,255,255,0.52); border: 1px solid rgba(96,165,250,0.16);">
								<h4 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Diagnosis History</h4>
								{#if patient.primary_diagnosis}
									<div class="flex items-center gap-2 pl-2" in:fade={{ duration: 150 }} style="border-left: 2px solid #3b82f6;">
										<p class="text-xs text-blue-700 flex-1">{patient.primary_diagnosis}</p>
										<span class="text-[10px] px-1.5 py-0.5 rounded" style="background: rgba(59,130,246,0.1); color: #2563eb;">Current</span>
									</div>
								{:else}
									<p class="text-xs text-gray-400">No history</p>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		<div class="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:px-5"
			style="background: linear-gradient(to right, rgba(239,246,255,0.98), rgba(226,238,252,0.96));">
			<div class="flex min-w-0 items-center gap-2.5">
				<ClipboardList class="h-5 w-5 shrink-0 text-blue-600" />
				<div class="flex min-w-0 flex-wrap items-center gap-2.5">
					<span class="text-[15px] font-bold text-slate-800">Admission Status</span>
					<button
						class="p-1 rounded-lg hover:bg-blue-100 transition-colors"
						onclick={() => showAdmissionHistoryModal = true}
						title="View Admission History"
					>
						<Clock class="h-4 w-4 text-blue-500" />
					</button>
					{#if currentAdmission}
						<span class="rounded-xl bg-blue-600 px-3 py-1 text-xs font-black tracking-wide text-white">ADMITTED</span>
					{:else if pendingAdmission}
						<span class="text-xs font-semibold text-slate-500">Request pending faculty approval</span>
					{:else}
						<span class="text-xs font-medium text-slate-500">No active admission</span>
					{/if}
				</div>
			</div>

			{#if currentAdmission && interactiveClinicalAccess}
				<a href="/patients/{patient.id}/review" class="shrink-0 flex items-center gap-1.5 text-[13px] font-black tracking-wide text-blue-600">
					REVIEW & VITALS <ChevronRight class="h-4 w-4" />
				</a>
			{:else if pendingAdmission && role === 'STUDENT' && canEdit}
				<button class="shrink-0 flex items-center gap-2 rounded-2xl px-4 py-2.5 text-xs font-bold cursor-not-allowed"
					style="background: rgba(240,253,244,0.9); border: 1px solid rgba(134,239,172,0.95); color: #15803d; box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);" disabled>
					<CheckCircle class="h-4 w-4" /> Sent for Approval
				</button>
			{:else if role === 'STUDENT' && canEdit}
				<button class="shrink-0 rounded-2xl px-5 py-2.5 text-[13px] font-bold text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #4ade80, #16a34a); border: 1px solid rgba(21,128,61,0.45); box-shadow: 0 6px 14px rgba(34,197,94,0.25), inset 0 1px 0 rgba(255,255,255,0.45);"
					onclick={openAdmissionRequestModal}>
					Admit Patient
				</button>
			{/if}
		</div>
	</div>

	{#if showAdmissionRequestModal}
		<AquaModal onclose={() => { showAdmissionRequestModal = false; resetAdmissionRequestForm(); }}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<ClipboardList class="w-5 h-5 text-blue-600" />
					<span class="font-semibold text-gray-800">Admission Request - {patient?.name}</span>
				</div>
			{/snippet}

			<div class="space-y-4">
				{#if admissionError}
					<div class="rounded-xl px-3 py-2 text-sm font-medium text-red-600" style="background: rgba(254,226,226,0.8); border: 1px solid rgba(248,113,113,0.25);">
						{admissionError}
					</div>
				{/if}

				<div class="rounded-2xl p-4" style="background: rgba(239,246,255,0.7); border: 1px solid rgba(147,197,253,0.35);">
					<p class="text-xs font-bold uppercase tracking-wide text-slate-500">Requesting Student</p>
					<p class="mt-1 text-base font-semibold text-slate-800">{studentData?.name || 'Student'}</p>
					<p class="mt-1 text-sm text-slate-500">This request is submitted by the student for faculty approval.</p>
				</div>

				<div>
					<label for="profile-admission-faculty" class="block text-sm font-medium text-gray-700 mb-1">Faculty Approver <span class="text-red-500">*</span></label>
					<select id="profile-admission-faculty" bind:value={admissionFacultyId}
						class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
						style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);">
						<option value="">Select faculty approver</option>
						{#each facultyApprovers as fac}
							<option value={fac.id}>{fac.name} - {fac.department}</option>
						{/each}
					</select>
				</div>

				<DynamicFormRenderer
					fields={admissionRequestFields}
					bind:values={admissionRequestFormData}
					idPrefix="profile-admission-request"
				/>
			</div>

			<div class="flex justify-end gap-2 mt-6">
				<button class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
					onclick={() => { showAdmissionRequestModal = false; resetAdmissionRequestForm(); }}
					disabled={admissionSubmitting}>Cancel</button>
				<button class="px-4 py-2 rounded-md text-sm font-medium text-white cursor-pointer flex items-center gap-1.5"
					style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
					onclick={submitAdmissionRequest}
					disabled={admissionSubmitting || !admissionFacultyId || !admissionRequestFormData.reason}>
					{#if admissionSubmitting}
						<div class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
					{/if}
					Send for Approval
				</button>
			</div>
		</AquaModal>
	{/if}

	{#if showAdmissionHistoryModal}
		<AquaModal onclose={() => showAdmissionHistoryModal = false}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<History class="w-5 h-5 text-blue-600" />
					<span class="font-semibold text-gray-800">Admission History - {patient?.name}</span>
				</div>
			{/snippet}
			<div class="space-y-3">
				{#if admissions.length === 0}
					<p class="text-sm text-gray-400 text-center py-6">No admission history</p>
				{:else}
					{#each admissions as admission}
						<div class="p-4 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
							<div class="flex items-start justify-between mb-2">
								<div>
									<p class="font-semibold text-gray-800">{admission.department || 'General'}</p>
									<p class="text-xs text-gray-500">{admission.ward || 'Not assigned'}</p>
								</div>
								<span class="px-2 py-0.5 rounded-full text-xs font-bold"
									style="background: {admission.status === 'ACTIVE' ? '#dcfce7' : admission.status === 'DISCHARGED' ? '#e0e7ff' : '#fef3c7'};
									       color: {admission.status === 'ACTIVE' ? '#166534' : admission.status === 'DISCHARGED' ? '#4338ca' : '#a16207'};">
									{admission.status}
								</span>
							</div>
							<div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
								<div>
									<span class="text-gray-400">Admitted:</span>
									{admission.admitted_at ? new Date(admission.admitted_at).toLocaleDateString() : '—'}
								</div>
								{#if admission.discharged_at}
									<div>
										<span class="text-gray-400">Discharged:</span>
										{new Date(admission.discharged_at).toLocaleDateString()}
									</div>
								{/if}
							</div>
							{#if admission.attending_doctor}
								<p class="text-xs text-gray-500 mt-2">
									Attending: {admission.attending_doctor}
								</p>
							{/if}
							{#if admission.reason_for_admission}
								<p class="text-sm text-gray-700 mt-2">
									<span class="text-gray-400">Reason:</span> {admission.reason_for_admission}
								</p>
							{/if}
							{#if admission.discharge_summary}
								<p class="text-sm text-gray-700 mt-1">
									<span class="text-gray-400">Discharge Summary:</span> {admission.discharge_summary}
								</p>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</AquaModal>
	{/if}

	<!-- ═══════════════════════════════════════════════════════════════
	     TABS
	     ═══════════════════════════════════════════════════════════════ -->
	<div class="overflow-x-auto pb-1">
		<TabBar tabs={tabs} activeTab={activeTab} onchange={openTab} variant="jiggle" stretch={false} ariaLabel="Patient detail sections" />
	</div>

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
				{#if studentEditAllowed || role !== 'STUDENT'}
					<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;
						       border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 3px rgba(0,102,204,0.3);"
						onclick={() => showAddRecordModal = true}>
						<Plus class="w-3 h-3" /> Add Entry
					</button>
				{/if}
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
								{#if !(record.examination || record.findings || record.diagnosis || record.treatment_plan || record.treatment)}
									<p class="text-sm text-amber-700"><strong>Status:</strong>Pending</p>
								{/if}
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
	{:else if activeTab === 'trends'}
		<AquaCard padding={false}>
			<div class="border-b border-slate-200/80 p-4 md:p-5">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
					<div class="flex items-center gap-2.5">
						<HeartPulse class="h-5 w-5 text-red-500" />
						<div>
							<h3 class="font-bold text-slate-800">Vitals Monitoring Dashboard</h3>
							<p class="text-xs text-slate-500">Trend view for the readings recorded during care.</p>
						</div>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						{#if studentEditAllowed || role !== 'STUDENT'}
							<button class="rounded-xl px-3 py-2 text-xs font-bold cursor-pointer"
							style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); color: #2563eb; border: 1px solid rgba(59,130,246,0.22);"
							onclick={openVitalModal}>
							MANUAL ENTRY
							</button>
						{/if}
						<button class="rounded-xl px-3 py-2 text-xs font-bold cursor-pointer"
							style="background: {trendsView === 'charts' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : 'white'}; color: {trendsView === 'charts' ? 'white' : '#2563eb'}; border: 1px solid rgba(59,130,246,0.24);"
							onclick={() => trendsView = 'charts'}>
							CHARTS
						</button>
						<button class="rounded-xl px-3 py-2 text-xs font-bold cursor-pointer"
							style="background: {trendsView === 'table' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : 'white'}; color: {trendsView === 'table' ? 'white' : '#2563eb'}; border: 1px solid rgba(59,130,246,0.24);"
							onclick={() => trendsView = 'table'}>
							TABLE
						</button>
					</div>
				</div>
			</div>

			<div class="space-y-4 p-4 md:p-5">
				{#if vitalCards.length > 0}
					<div class="grid gap-2 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
						{#each vitalCards as card}
							<div class="rounded-2xl px-4 py-3" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(226,232,240,0.95); box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);">
								<div class="flex items-start gap-3">
									<div class="mt-0.5 h-2.5 w-2.5 rounded-full" style="background: {card.color};"></div>
									<div>
										<p class="text-[10px] font-black uppercase leading-tight tracking-wide text-slate-400 whitespace-pre-line">{card.label}</p>
										<p class="mt-1 text-lg font-black text-slate-800">{card.value} <span class="text-xs font-semibold text-slate-400">{card.unit}</span></p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}

				<div class="flex flex-wrap gap-2">
					{#each ['7', '14', '30'] as range}
						<button class="rounded-full px-3 py-1.5 text-xs font-bold cursor-pointer"
							style="background: {selectedTimeRange === range ? 'rgba(59,130,246,0.12)' : 'white'}; color: {selectedTimeRange === range ? '#2563eb' : '#64748b'}; border: 1px solid {selectedTimeRange === range ? 'rgba(59,130,246,0.26)' : 'rgba(148,163,184,0.22)'};"
							onclick={() => selectedTimeRange = range}>
							Last {range} Days
						</button>
					{/each}
				</div>

				{#if vitals.length === 0}
					<div class="py-12 text-center text-slate-400">
						<HeartPulse class="mx-auto mb-3 h-10 w-10 opacity-50" />
						<p class="text-sm">No vitals recorded yet</p>
					</div>
				{:else if trendsView === 'charts'}
					<div class="rounded-[24px] p-3 md:p-4" style="background: linear-gradient(to bottom, #ffffff, #f8fbff); border: 1px solid rgba(226,232,240,0.95); box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);">
						<div class="mb-3 flex items-center justify-between gap-3">
							<div>
								<p class="text-sm font-bold text-slate-800">Combined Trends</p>
								<p class="text-xs text-slate-400">Blood pressure, heart rate, SpO₂, and respiratory rate</p>
							</div>
							<ChevronDown class="h-5 w-5 text-blue-500" />
						</div>
						<div class="relative h-[320px] md:h-[420px]">
							<canvas bind:this={chartCanvas}></canvas>
							{#if trendTooltip.visible}
								{#each trendTooltip.items as item (item.label)}
									<div
										class="pointer-events-none absolute z-10 rounded-[18px] px-4 py-3 text-sm font-semibold shadow-[0_12px_28px_rgba(15,23,42,0.12)]"
										style="left: {trendTooltip.x}px; top: {item.y}px; background: rgba(255,255,255,0.96); color: {item.color}; min-width: 180px;">
										{item.label} : {item.value}
									</div>
								{/each}
								<div class="pointer-events-none absolute bottom-3 left-0 text-xs font-semibold text-slate-400" style="left: {Math.max(trendTooltip.x - 18, 0)}px;">
									{trendTooltip.label}
								</div>
							{/if}
						</div>
					</div>
				{:else}
					<div class="overflow-hidden rounded-[24px] border border-slate-200/90 bg-white shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
						<div class="overflow-x-auto">
							<table class="min-w-full text-sm">
								<thead style="background: linear-gradient(to bottom, #f8fafc, #eef2f7);">
									<tr>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">Recorded</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">BP</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">HR</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">Temp</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">SpO₂</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">Resp</th>
										<th class="px-4 py-3 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">Weight</th>
									</tr>
								</thead>
								<tbody>
									{#each vitals.slice(0, parseInt(selectedTimeRange)) as vital, index}
										<tr style="background: {index % 2 === 0 ? 'white' : 'rgba(248,250,252,0.84)'}; border-top: 1px solid rgba(226,232,240,0.9);">
											<td class="px-4 py-3 font-medium text-slate-600">{formatReportDate(vital.recorded_at)}</td>
											<td class="px-4 py-3 text-slate-800">{vital.systolic_bp ?? '—'}/{vital.diastolic_bp ?? '—'}</td>
											<td class="px-4 py-3 text-slate-800">{vital.heart_rate ?? '—'}</td>
											<td class="px-4 py-3 text-slate-800">{vital.temperature ?? '—'}</td>
											<td class="px-4 py-3 text-slate-800">{vital.oxygen_saturation ?? '—'}</td>
											<td class="px-4 py-3 text-slate-800">{vital.respiratory_rate ?? '—'}</td>
											<td class="px-4 py-3 text-slate-800">{vital.weight ?? '—'}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>
		</AquaCard>

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
					{#if studentEditAllowed || role !== 'STUDENT'}
						<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
							style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;
							       border: 1px solid rgba(0,0,0,0.15);"
							onclick={() => {
								resetPrescriptionForm();
								showAddPrescriptionModal = true;
							}}>
							<Plus class="w-3 h-3" /> Add Prescription
						</button>
					{/if}
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
									{#if studentEditAllowed || role !== 'STUDENT'}
										<button class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
											style="background: rgba(0,0,0,0.06);"
											onclick={() => openEditPrescription(rx)}>
											<Edit class="w-3 h-3 text-gray-500" />
										</button>
									{/if}
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
									{#if req.status === 'PENDING' && interactiveClinicalAccess}
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

	<!-- ═══════════════════════════════════════════════════════════════
	     INVESTIGATIONS TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{:else if activeTab === 'investigations'}
		<AquaCard padding={false}>
			<div class="border-b border-slate-200/85 px-5 py-5" style="background: linear-gradient(to bottom, #f4f8ff, #e9f0fb);">
				<div class="flex items-center justify-between gap-3">
					<div class="flex items-center gap-3">
						<TestTube class="h-6 w-6 text-emerald-600" />
						<div>
							<h3 class="text-[18px] font-black text-slate-900">Lab Investigations</h3>
							<p class="text-xs text-slate-500">{investigationReports.length} reports recorded for this patient</p>
						</div>
					</div>
					{#if interactiveClinicalAccess}
						<button class="flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-bold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #60a5fa, #2563eb); border: 1px solid rgba(37,99,235,0.34); box-shadow: 0 8px 18px rgba(37,99,235,0.2);"
							onclick={requestLabOrder}>
							<Plus class="h-4 w-4" /> ORDER LAB
						</button>
					{/if}
				</div>
			</div>

			<div class="space-y-4 p-4 md:p-6">
				{#if investigationReports.length === 0}
					<p class="py-8 text-center text-sm text-gray-400">No investigation reports available</p>
				{:else}
					{#each investigationReports as report, index (report.id)}
						{@const iconTone = getInvestigationIconTone(report.status)}
						<div class="overflow-hidden rounded-[22px] border border-slate-200/90 bg-white shadow-[0_10px_24px_rgba(15,23,42,0.07)]">
							<div class="flex items-center gap-4 px-5 py-4">
								<div class="flex h-13 w-13 shrink-0 items-center justify-center rounded-full text-white" style="background: {iconTone.bg};">
									<iconTone.icon class="h-6 w-6" />
								</div>
								<div class="min-w-0 flex-1">
									<p class="truncate text-[18px] font-black text-slate-900">{report.title}</p>
									<p class="mt-1 text-sm text-slate-500">ID: LAB-{String(index + 1).padStart(3, '0')} · Date: {formatReportDate(report.date, report.time)} · Provider: {report.performed_by || report.ordered_by || '—'}</p>
								</div>
								<div class="flex items-center gap-3">
									<button class="rounded-2xl px-4 py-2 text-sm font-bold text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #60a5fa, #2563eb); border: 1px solid rgba(37,99,235,0.34);"
										onclick={() => viewInvestigationReport(report)}>
										VIEW REPORT
									</button>
									<button class="flex h-10 w-10 items-center justify-center rounded-full cursor-pointer text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
										onclick={() => toggleInvestigationReport(report.id)}
										aria-label="Toggle report details">
										<ChevronDown class="h-5 w-5 transition-transform" style="transform: rotate({expandedInvestigationId === report.id ? 180 : 0}deg);" />
									</button>
								</div>
							</div>

							{#if expandedInvestigationId === report.id}
								<div class="border-t border-slate-200/80 bg-slate-50/60 px-5 py-4">
									{#if report.result_summary}
										<p class="text-sm font-semibold text-slate-700">{report.result_summary}</p>
									{/if}
									{#if report.findings && report.findings.length > 0}
										<div class="mt-3 grid gap-3 md:grid-cols-2">
											{#each report.findings.slice(0, 4) as finding}
												<div class="rounded-xl border border-slate-200/85 bg-white px-4 py-3">
													<p class="text-[11px] font-bold uppercase tracking-wide text-slate-400">{finding.parameter}</p>
													<p class="mt-1 text-sm font-semibold text-slate-800">{finding.value}</p>
													{#if finding.reference}
														<p class="mt-1 text-[11px] text-slate-400">Reference: {finding.reference}</p>
													{/if}
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</AquaCard>

	<!-- ═══════════════════════════════════════════════════════════════
	     RADIOLOGY TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{:else if activeTab === 'radiology'}
		<AquaCard>
			<div class="mb-4 flex items-center justify-between gap-3">
				<div class="flex items-center gap-2">
					<Activity class="h-5 w-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Radiology</h3>
				</div>
				<div class="flex items-center gap-2">
					<span class="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">{radiologyReports.length} studies</span>
					{#if radiologyReports.length > 0}
						<button class="rounded-xl px-3 py-1.5 text-xs font-bold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #1d4ed8, #1e40af); border: 1px solid rgba(30,64,175,0.45);"
							onclick={() => openRadiologyViewer()}>
							Open Viewer
						</button>
					{/if}
				</div>
			</div>

			{#if radiologyReports.length === 0}
				<p class="py-8 text-center text-sm text-gray-400">No radiology studies available</p>
			{:else}
				<div class="space-y-3">
					{#each radiologyReports as report}
						{@const tone = getReportStatusTone(report.status)}
						<div class="rounded-[22px] p-4" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(226,232,240,0.95);">
							<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<span class="inline-flex h-9 w-9 items-center justify-center rounded-full" style="background: rgba(249,115,22,0.12); color: #ea580c;">
											<Activity class="h-4 w-4" />
										</span>
										<div>
											<p class="font-bold text-slate-800">{report.title}</p>
											<p class="text-xs text-slate-400">{report.department} · {formatReportDate(report.date, report.time)}</p>
										</div>
									</div>
									{#if report.result_summary}
										<p class="mt-3 text-sm font-semibold text-slate-700">{report.result_summary}</p>
									{/if}
									{#if report.notes}
										<p class="mt-2 text-sm text-slate-500">{report.notes}</p>
									{/if}
								</div>
								<div class="shrink-0 space-y-3 lg:w-60">
									<span class="inline-flex rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide" style="background: {tone.bg}; color: {tone.text}; border: 1px solid {tone.border};">{report.status}</span>
									<button class="w-full rounded-2xl px-3 py-2 text-xs font-bold text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #1d4ed8, #1e40af); border: 1px solid rgba(30,64,175,0.45);"
										onclick={() => openRadiologyViewer(report.id)}>
										View Fullscreen
									</button>
									<div class="rounded-2xl px-3 py-3 text-sm" style="background: rgba(248,250,252,0.9); border: 1px solid rgba(226,232,240,0.9);">
										<p class="text-[11px] font-bold uppercase tracking-wide text-slate-400">Images</p>
										<p class="mt-1 font-semibold text-slate-800">{report.images?.length || 0} attached</p>
									</div>
									{#if report.images && report.images.length > 0}
										<div class="grid grid-cols-3 gap-2">
											{#each report.images.slice(0, 3) as image}
												<a href={image.url} target="_blank" rel="noreferrer" class="block overflow-hidden rounded-xl border border-slate-200/90 bg-slate-100">
													<img src={image.url} alt={image.title} class="h-16 w-full object-cover" />
												</a>
											{/each}
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>

	<!-- ═══════════════════════════════════════════════════════════════
	     GALLERY TAB
	     ═══════════════════════════════════════════════════════════════ -->
	{:else if activeTab === 'gallery'}
		<AquaCard padding={false}>
			<div class="border-b border-slate-200/85 px-5 py-5" style="background: linear-gradient(to bottom, #f4f8ff, #e9f0fb);">
				<div class="flex items-center justify-between gap-3">
					<div class="flex items-center gap-3">
						<ImageIcon class="h-6 w-6 text-blue-600" />
						<div>
							<h3 class="text-[18px] font-black text-slate-900">Patient Gallery</h3>
							<p class="text-xs text-slate-500">Clinical media, investigation images, and patient documents</p>
						</div>
					</div>
					<!-- <button class="rounded-2xl px-4 py-2 text-sm font-bold text-white cursor-pointer"
						style="background: linear-gradient(to bottom, #60a5fa, #2563eb); border: 1px solid rgba(37,99,235,0.34);"
						onclick={() => showAllGallery = !showAllGallery}>
						{showAllGallery ? 'SHOW LESS' : 'VIEW FULL GALLERY'}
					</button> -->
				</div>
			</div>

			<div class="space-y-5 p-4 md:p-6">
				<div class="inline-flex rounded-2xl border border-slate-200/90 bg-slate-100/80 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]">
					<button class="rounded-xl px-7 py-2 text-sm font-bold transition-all"
						style="background: {galleryFilter === 'clinical' ? 'white' : 'transparent'}; color: {galleryFilter === 'clinical' ? '#1f2937' : '#64748b'}; box-shadow: {galleryFilter === 'clinical' ? '0 2px 10px rgba(15,23,42,0.08)' : 'none'};"
						onclick={() => { galleryFilter = 'clinical'; showAllGallery = false; }}>
						Clinical
					</button>
					<button class="rounded-xl px-7 py-2 text-sm font-bold transition-all"
						style="background: {galleryFilter === 'investigations' ? 'white' : 'transparent'}; color: {galleryFilter === 'investigations' ? '#1f2937' : '#64748b'}; box-shadow: {galleryFilter === 'investigations' ? '0 2px 10px rgba(15,23,42,0.08)' : 'none'};"
						onclick={() => { galleryFilter = 'investigations'; showAllGallery = false; }}>
						Investigations
					</button>
					<button class="rounded-xl px-7 py-2 text-sm font-bold transition-all"
						style="background: {galleryFilter === 'documents' ? 'white' : 'transparent'}; color: {galleryFilter === 'documents' ? '#2563eb' : '#64748b'}; box-shadow: {galleryFilter === 'documents' ? '0 2px 10px rgba(15,23,42,0.08)' : 'none'};"
						onclick={() => { galleryFilter = 'documents'; showAllGallery = false; }}>
						Documents
					</button>
				</div>

				{#if filteredGalleryItems.length === 0}
					<p class="py-8 text-center text-sm text-gray-400">No items in this gallery section</p>
				{:else}
					<div class="grid gap-5 md:grid-cols-2">
						{#each visibleGalleryItems as item (item.id)}
							<a href={item.url} target="_blank" rel="noreferrer" class="group overflow-hidden rounded-[22px] border border-slate-200/90 bg-white shadow-[0_10px_24px_rgba(15,23,42,0.07)] transition-transform hover:scale-[1.01]">
								<div class="aspect-[5/4] overflow-hidden bg-slate-100">
									<img src={item.url} alt={item.title} class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]" />
								</div>
								<div class="space-y-2 p-4">
									<div class="flex items-start justify-between gap-3">
										<p class="text-[15px] font-black leading-tight text-slate-900">{item.title}</p>
										<span class="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-black tracking-wide text-slate-700">{item.badge}</span>
									</div>
									<p class="text-sm text-slate-500">{formatReportDate(item.reportDate)}</p>
								</div>
							</a>
						{/each}
					</div>
				{/if}
			</div>
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
			<label for="cr-form" class="block text-sm font-medium text-gray-700 mb-1">
				Case Record Form <span class="text-red-500">*</span>
			</label>
			<Autocomplete
				items={filteredCrForms}
				labelKey="name"
				sublabelKey="meta"
				badgeKey="badge"
				minChars={0}
				placeholder="Search case record forms..."
				bind:value={crFormSearch}
				onInput={handleCrFormSearch}
				onSelect={handleCrFormSelect}
				onClear={handleCrFormClear}
			/>
		</div>

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
			disabled={crSubmitting || !selectedCrFormId}>
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
		<div class="flex items-center gap-3">
			<div class="flex h-12 w-12 items-center justify-center rounded-full"
				style="background: radial-gradient(circle at 30% 30%, #ff5b5b, #d40000 72%); box-shadow: 0 3px 8px rgba(212,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.35);">
				<HeartPulse class="h-6 w-6 text-white" />
			</div>
			<div>
				<h3 class="text-[1.7rem] font-black leading-none text-slate-900">Quick Vital Entry</h3>
				<p class="mt-1 text-[0.72rem] font-black uppercase tracking-[0.24em] text-red-600">Major Parameters</p>
			</div>
		</div>
	{/snippet}

	<div class="space-y-5">
		<div>
			<div class="mb-1.5 block text-sm font-medium text-slate-700">
				Vital Form
			</div>
			<Autocomplete
				items={filteredVitalForms}
				labelKey="name"
				sublabelKey="meta"
				badgeKey="badge"
				minChars={0}
				placeholder="Search available vital forms..."
				bind:value={vitalFormSearch}
				onSelect={handleVitalFormSelect}
				onClear={handleVitalFormClear}
			/>
			{#if selectedVitalForm?.description}
				<p class="mt-1.5 text-xs text-slate-500">{selectedVitalForm.description}</p>
			{/if}
		</div>

		<div class="rounded-[1.75rem] border border-slate-200/80 bg-gradient-to-b from-slate-50 via-white to-slate-50/80 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
			<div class="mb-5 text-[0.76rem] font-black uppercase tracking-[0.24em] text-slate-500">Blood Pressure (mmHg)</div>
			{#if majorVitalFieldMap.has('systolic_bp') || majorVitalFieldMap.has('diastolic_bp')}
			<div class="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
				<input
					bind:value={vitalFormData.systolic_bp}
					type="number"
					placeholder={majorVitalFieldMap.get('systolic_bp')?.label || 'Sys'}
					class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					disabled={!majorVitalFieldMap.has('systolic_bp')}
				/>
				<div class="pb-1 text-4xl font-black text-slate-400">/</div>
				<input
					bind:value={vitalFormData.diastolic_bp}
					type="number"
					placeholder={majorVitalFieldMap.get('diastolic_bp')?.label || 'Dia'}
					class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					disabled={!majorVitalFieldMap.has('diastolic_bp')}
				/>
			</div>
			{/if}

			<div class="mt-6 grid gap-5 sm:grid-cols-2">
				{#if majorVitalFieldMap.has('heart_rate')}
				<div>
					<div class="mb-2 text-[0.76rem] font-black uppercase tracking-[0.24em] text-slate-500">Pulse (bpm)</div>
					<input
						bind:value={vitalFormData.heart_rate}
						type="number"
						placeholder={majorVitalFieldMap.get('heart_rate')?.label || '72'}
						class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					/>
				</div>
				{/if}
				{#if majorVitalFieldMap.has('respiratory_rate')}
				<div>
					<div class="mb-2 text-[0.76rem] font-black uppercase tracking-[0.24em] text-slate-500">Resp. Rate (min)</div>
					<input
						bind:value={vitalFormData.respiratory_rate}
						type="number"
						placeholder={majorVitalFieldMap.get('respiratory_rate')?.label || '16'}
						class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					/>
				</div>
				{/if}
				<div>
					<div class="mb-2 text-[0.76rem] font-black uppercase tracking-[0.24em] text-slate-500">Urine Output (mL)</div>
					<input
						bind:value={vitalFormData.urine_output_ml}
						type="number"
						placeholder="300"
						class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					/>
					{#if !currentAdmission}
						<p class="mt-1.5 text-[11px] text-slate-400">Saved only when the patient has an active admission.</p>
					{/if}
				</div>
				{#if majorVitalFieldMap.has('blood_glucose')}
				<div>
					<div class="mb-2 text-[0.76rem] font-black uppercase tracking-[0.24em] text-slate-500">Glucose (mg/dL)</div>
					<input
						bind:value={vitalFormData.blood_glucose}
						type="number"
						placeholder={majorVitalFieldMap.get('blood_glucose')?.label || '110'}
						class="h-16 w-full rounded-[1.35rem] border border-slate-200 bg-white px-6 text-2xl font-black text-slate-700 outline-none placeholder:font-bold placeholder:text-slate-400 focus:border-red-300 focus:ring-4 focus:ring-red-100"
					/>
				</div>
				{/if}
			</div>
		</div>

		{#if supplementalVitalFields.length > 0}
			<div class="rounded-[1.5rem] border border-slate-200/80 bg-white/90 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
				<div class="mb-3 text-[0.72rem] font-black uppercase tracking-[0.24em] text-slate-500">Additional Fields</div>
				<div class="grid gap-4 sm:grid-cols-2">
					<DynamicFormRenderer
						fields={supplementalVitalFields}
						bind:values={vitalFormData}
						idPrefix="patient-profile-vital"
					/>
				</div>
			</div>
		{/if}
	</div>
	<div class="mt-6 flex justify-end gap-3 border-t border-slate-200 pt-5">
		<button class="min-w-[9.25rem] rounded-2xl px-5 py-3 text-sm font-black tracking-wide text-slate-500 cursor-pointer"
			style="background: linear-gradient(to bottom, #f8fafc, #dfe7f1); border: 1px solid rgba(148,163,184,0.26);
			       box-shadow: 0 4px 10px rgba(148,163,184,0.16), inset 0 1px 0 rgba(255,255,255,0.92);"
			onclick={() => { showAddVitalModal = false; resetVitalForm(); }}
			disabled={vSubmitting}>Cancel</button>
		<button class="min-w-[13rem] rounded-2xl px-6 py-3 text-sm font-black uppercase tracking-[0.08em] text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #ff5b5b, #d40000 72%); border: 1px solid rgba(117,0,0,0.35);
			       box-shadow: 0 8px 18px rgba(212,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.32);"
			onclick={submitVital}
			disabled={vSubmitting}>
			{vSubmitting ? 'Saving...' : 'Save All Entries'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Add Prescription Modal -->
{#if showAddPrescriptionModal}
	{#if role === 'STUDENT'}
		<PrescriptionForm
			patient={{ id: patient.id, patient_id: patient.patient_id, name: patient.name }}
			facultyApprovers={facultyApprovers}
			onClose={() => { showAddPrescriptionModal = false; }}
			onSubmit={submitStudentPrescription}
		/>
	{:else}
		<AquaModal onclose={() => { showAddPrescriptionModal = false; resetPrescriptionForm(); }}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<Pill class="w-5 h-5 text-blue-600" />
					<span class="text-blue-900 font-semibold">Medications</span>
				</div>
			{/snippet}

			<div class="space-y-4">
				<DynamicFormRenderer
					fields={prescriptionCreateFields}
					bind:values={prescriptionFormData}
					idPrefix="patient-profile-prescription"
				/>
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
					disabled={rxSubmitting || !prescriptionFormData.name || !prescriptionFormData.dosage || !prescriptionFormData.frequency}>
					{rxSubmitting ? 'Adding...' : 'Add Prescription'}
				</button>
			</div>
		</AquaModal>
	{/if}
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
		<DynamicFormRenderer
			fields={prescriptionRequestFields}
			bind:values={prescriptionRequestFormData}
			idPrefix="patient-profile-prescription-request"
		/>
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
			disabled={prSubmitting || !prescriptionRequestFormData.medication}>
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
		<DynamicFormRenderer
			fields={prescriptionEditFields}
			bind:values={editPrescriptionFormData}
			idPrefix="patient-profile-prescription-edit"
		/>
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
