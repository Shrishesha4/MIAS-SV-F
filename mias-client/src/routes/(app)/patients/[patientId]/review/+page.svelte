<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import type { AdmissionIOEvent, AdmissionIOEventSummary, AdmissionSoapNote, AdmissionEquipment, Vital, VitalParameterConfig } from '$lib/api/types';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { nurseApi, type SBARNote } from '$lib/api/nurse';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
	import {
		ArrowLeft, Activity, Droplet, Wind, Thermometer, Scale, HeartPulse,
		Plus, Trash2, Edit, ChevronDown, ChevronUp, Monitor, Cpu, X, Wifi,
		AlertTriangle, Send, ClipboardList, Stethoscope, BarChart3, Table,
		Pill, Utensils, Beaker, Circle, FileText, Clock, User, Zap,
		TestTube, FlaskConical, LayoutList
	} from 'lucide-svelte';

	const patientId = $derived($page.params.patientId);

	// ── Data ──────────────────────────────────────────────────────
	let patient: any = $state(null);
	let admission: any = $state(null);
	let vitals = $state.raw<Vital[]>([]);
	let ioEvents = $state.raw<AdmissionIOEvent[]>([]);
	let ioSummary = $state<AdmissionIOEventSummary | null>(null);
	let soapNotes = $state.raw<AdmissionSoapNote[]>([]);
	let sbarNotes = $state.raw<SBARNote[]>([]);
	let equipment = $state.raw<AdmissionEquipment[]>([]);
	let loading = $state(true);
	let role = $state('');

	// ── Vitals view state ─────────────────────────────────────────
	let vitalsView = $state<'chart' | 'table'>('chart');
	let selectedVitalParams = $state<string[]>(['heart_rate', 'systolic_bp']);
	let vitalsDropdownOpen = $state(false);
	let biochemDropdownOpen = $state(false);
	let haemaDropdownOpen = $state(false);
	// Tooltip state
	let hoveredVitalIndex: number | null = $state(null);
	let hoveredVitalParam: string | null = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	// ── IO Event form ─────────────────────────────────────────────
	let showAddEventModal = $state(false);
	let eventType = $state('IV');
	let eventTime = $state('');
	let eventDesc = $state('');
	let eventAmount = $state('');
	let eventSubmitting = $state(false);

	// ── Record Vitals form ────────────────────────────────────────
	let showVitalModal = $state(false);
	let vitalSubmitting = $state(false);
	let vitalParameterConfigs = $state.raw<VitalParameterConfig[]>([]);
	let vitalFormValues = $state<Record<string, string>>({});

	// ── Connect Equipment form ────────────────────────────────────
	let showEquipModal = $state(false);
	let equipType = $state('Bedside Monitor');
	let equipId = $state('');
	let equipSubmitting = $state(false);

	// ── SOAP Note form ────────────────────────────────────────────
	let showSoapModal = $state(false);
	let showSoapHistoryModal = $state(false);
	let soapSubjective = $state('');
	let soapObjective = $state('');
	let soapAssessment = $state('');
	let soapPlan = $state('');
	let soapSubmitting = $state(false);
	let editSoapId: string | null = $state(null);

	// ── Discharge ─────────────────────────────────────────────────
	let showDischargeModal = $state(false);
	let dischargeSummary = $state('');
	let dischargeInstructions = $state('');
	let dischargeFollowUp = $state('');
	let dischargeSubmitting = $state(false);

	// ── Live equipment data simulation ────────────────────────────
	let liveDataInterval: ReturnType<typeof setInterval> | null = null;
	let liveEquipmentData = $state<Record<string, Record<string, number>>>({});

	// ── Parameter config ──────────────────────────────────────────
	const vitalParamsConfig: Record<string, { label: string; unit: string; color: string; key?: string }> = {
		heart_rate: { label: 'Heart Rate', unit: 'bpm', color: '#ef4444' },
		systolic_bp: { label: 'Blood Pressure', unit: 'mmHg', color: '#3b82f6' },
		respiratory_rate: { label: 'Resp. Rate', unit: '/min', color: '#a855f7' },
		temperature: { label: 'Temperature', unit: '°F', color: '#f97316' },
		oxygen_saturation: { label: 'SpO₂', unit: '%', color: '#14b8a6' },
		weight: { label: 'Weight', unit: 'kg', color: '#22c55e' },
		blood_glucose: { label: 'Blood Glucose', unit: 'mg/dL', color: '#f59e0b' },
	};

	const biochemParams: Record<string, { label: string; unit: string; color: string }> = {
		creatinine: { label: 'Creatinine', unit: 'mg/dL', color: '#8b5cf6' },
		urea: { label: 'Urea', unit: 'mg/dL', color: '#6366f1' },
		sodium: { label: 'Sodium', unit: 'mEq/L', color: '#ec4899' },
		potassium: { label: 'Potassium', unit: 'mEq/L', color: '#f43f5e' },
		sgot: { label: 'SGOT', unit: 'U/L', color: '#84cc16' },
		sgpt: { label: 'SGPT', unit: 'U/L', color: '#22c55e' },
	};

	const haemaParams: Record<string, { label: string; unit: string; color: string }> = {
		hemoglobin: { label: 'Hemoglobin', unit: 'g/dL', color: '#dc2626' },
		wbc: { label: 'WBC', unit: '×10³/µL', color: '#2563eb' },
		platelet: { label: 'Platelet', unit: '×10³/µL', color: '#7c3aed' },
		rbc: { label: 'RBC', unit: '×10⁶/µL', color: '#db2777' },
		hct: { label: 'HCT', unit: '%', color: '#ea580c' },
	};

	// ── IO Event type config ─────────────────────────────────────
	const ioEventTypes: Record<string, { label: string; icon: any; bgColor: string; textColor: string; borderColor: string }> = {
		'IV': { label: 'IV Input', icon: Droplet, bgColor: 'bg-green-50', textColor: 'text-green-700', borderColor: 'border-green-200' },
		'ORAL': { label: 'Oral Intake', icon: Utensils, bgColor: 'bg-amber-50', textColor: 'text-amber-700', borderColor: 'border-amber-200' },
		'URINE': { label: 'Urine', icon: Beaker, bgColor: 'bg-cyan-50', textColor: 'text-cyan-700', borderColor: 'border-cyan-200' },
		'STOOL': { label: 'Stool', icon: Circle, bgColor: 'bg-stone-50', textColor: 'text-stone-600', borderColor: 'border-stone-200' },
		'DRUG': { label: 'Drugs', icon: Pill, bgColor: 'bg-purple-50', textColor: 'text-purple-700', borderColor: 'border-purple-200' },
	};

	// ── Derived ───────────────────────────────────────────────────
	const latestSoap = $derived(soapNotes[0] ?? null);
	const chronologicalSoapNotes = $derived(
		[...soapNotes].sort((a, b) => new Date(a.created_at ?? 0).getTime() - new Date(b.created_at ?? 0).getTime())
	);

	// Group IO events by hour for timeline
	const ioEventsByTime = $derived.by(() => {
		const grouped: Record<string, AdmissionIOEvent[]> = {};
		ioEvents.forEach(e => {
			const t = e.event_time?.slice(0, 5) || '00:00';
			if (!grouped[t]) grouped[t] = [];
			grouped[t].push(e);
		});
		return grouped;
	});

	const timeSlots = $derived(
		Object.keys(ioEventsByTime).sort().slice(0, 8)
	);

	// Get vitals sorted by time for charts
	const sortedVitals = $derived(
		[...vitals].sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()).slice(-8)
	);

	// Selected params by category
	const selectedVitalsCount = $derived(
		selectedVitalParams.filter(p => p in vitalParamsConfig).length
	);
	const configuredVitalFields = $derived.by(() =>
		[...vitalParameterConfigs]
			.sort((a, b) => (a.sort_order ?? Number.MAX_SAFE_INTEGER) - (b.sort_order ?? Number.MAX_SAFE_INTEGER))
			.map((parameter) => ({
				key: parameter.name,
				label: parameter.display_name,
				unit: parameter.unit ?? '',
				valueStyle: parameter.value_style ?? 'single',
				placeholder: parameter.value_style === 'slash' ? 'e.g. 120/80' : 'Enter value',
			}))
	);

	onMount(async () => {
		const auth = get(authStore);
		if (!auth?.accessToken) { goto('/login'); return; }
		role = auth?.role ?? '';

		const pid = get(page).params.patientId!;
		try {
			const [p, admList, vs, configuredVitals] = await Promise.all([
				patientApi.getPatient(pid),
				patientApi.getAdmissions(pid),
				patientApi.getVitals(pid, 30),
				patientApi.getActiveVitalParameters().catch(() => []),
			]);
			patient = p;
			vitalParameterConfigs = configuredVitals;
			vitals = vs.sort((a: any, b: any) =>
				new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
			admission = admList.find((a: any) => a.status === 'Active') ?? admList[0] ?? null;

			if (admission) {
				const [evtsResp, notes, equip, sbar] = await Promise.all([
					patientApi.getIOEvents(admission.id),
					patientApi.getSOAPNotes(admission.id),
					patientApi.getEquipment(admission.id),
					nurseApi.getPatientSBARNotes(patient.id),
				]);
				ioEvents = evtsResp.events;
				ioSummary = evtsResp.summary;
				soapNotes = notes;
				sbarNotes = sbar;
				equipment = equip;

				// Initialize live data from equipment
				equip.forEach((eq: AdmissionEquipment) => {
					if (eq.live_data) {
						liveEquipmentData[eq.id] = eq.live_data as Record<string, number>;
					}
				});

				// Start live data simulation
				startLiveDataSimulation();
			}
		} catch (e) {
			toastStore.addToast('Failed to load admission data', 'error');
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		if (liveDataInterval) clearInterval(liveDataInterval);
	});

	function startLiveDataSimulation() {
		liveDataInterval = setInterval(() => {
			equipment.forEach(eq => {
				if (eq.live_data && eq.status === 'Active') {
					const newData: Record<string, number> = {};
					Object.entries(eq.live_data).forEach(([k, v]) => {
						if (typeof v === 'number') {
							// Small random fluctuation
							newData[k] = Math.round((v + (Math.random() - 0.5) * 2) * 10) / 10;
						}
					});
					liveEquipmentData[eq.id] = { ...liveEquipmentData[eq.id], ...newData };
				}
			});
			liveEquipmentData = { ...liveEquipmentData };
		}, 2000);
	}

	function toggleVitalParam(param: string) {
		if (selectedVitalParams.includes(param)) {
			selectedVitalParams = selectedVitalParams.filter(p => p !== param);
		} else {
			selectedVitalParams = [...selectedVitalParams, param];
		}
	}

	async function addIOEvent() {
		if (!admission || !eventType || !eventTime) return;
		eventSubmitting = true;
		try {
			await patientApi.addIOEvent(admission.id, {
				event_type: eventType,
				event_time: eventTime,
				description: eventDesc || undefined,
				amount_ml: eventAmount ? Number(eventAmount) : undefined,
			});
			const resp = await patientApi.getIOEvents(admission.id);
			ioEvents = resp.events;
			ioSummary = resp.summary;
			showAddEventModal = false;
			eventType = 'IV'; eventTime = ''; eventDesc = ''; eventAmount = '';
			toastStore.addToast('Event recorded', 'success');
		} catch { toastStore.addToast('Failed to add event', 'error'); }
		finally { eventSubmitting = false; }
	}

	async function removeIOEvent(eventId: string) {
		if (!admission) return;
		await patientApi.deleteIOEvent(admission.id, eventId);
		ioEvents = ioEvents.filter((e: any) => e.id !== eventId);
		toastStore.addToast('Event removed', 'success');
	}

	async function submitVital() {
		if (!patient) return;
		if (configuredVitalFields.length === 0) {
			toastStore.addToast('No active vital parameters configured.', 'error');
			return;
		}
		const pid = patient.id;
		vitalSubmitting = true;
		try {
			const payload: Record<string, string | number | undefined> = {};
			for (const field of configuredVitalFields) {
				const rawValue = (vitalFormValues[field.key] ?? '').trim();
				if (!rawValue) continue;

				if (field.valueStyle === 'slash') {
					if (field.key === 'systolic_bp') {
						const [sysRaw, diaRaw] = rawValue.split('/').map((value) => value.trim());
						const sys = Number(sysRaw);
						const dia = Number(diaRaw);
						if (!Number.isNaN(sys)) payload.systolic_bp = sys;
						if (!Number.isNaN(dia)) payload.diastolic_bp = dia;
					} else {
						payload[field.key] = rawValue;
					}
					continue;
				}

				const numericValue = Number(rawValue);
				if (!Number.isNaN(numericValue)) {
					payload[field.key] = numericValue;
				}
			}

			await patientApi.createVital(pid, payload);
			vitals = (await patientApi.getVitals(pid, 30)).sort((a: any, b: any) =>
				new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
			showVitalModal = false;
			vitalFormValues = {};
			toastStore.addToast('Vital recorded', 'success');
		} catch { toastStore.addToast('Failed to record vital', 'error'); }
		finally { vitalSubmitting = false; }
	}

	async function connectEquip() {
		if (!admission || !equipType) return;
		equipSubmitting = true;
		try {
			await patientApi.connectEquipment(admission.id, { equipment_type: equipType, equipment_id: equipId || undefined });
			equipment = await patientApi.getEquipment(admission.id);
			showEquipModal = false; equipType = 'Bedside Monitor'; equipId = '';
			toastStore.addToast('Equipment connected', 'success');
		} catch { toastStore.addToast('Failed to connect equipment', 'error'); }
		finally { equipSubmitting = false; }
	}

	async function disconnectEquip(eid: string) {
		if (!admission) return;
		await patientApi.disconnectEquipment(admission.id, eid);
		equipment = equipment.filter((e: any) => e.id !== eid);
		toastStore.addToast('Equipment disconnected', 'success');
	}

	async function saveSoapNote() {
		if (!admission) return;
		soapSubmitting = true;
		const body = { subjective: soapSubjective, objective: soapObjective, assessment: soapAssessment, plan: soapPlan };
		try {
			if (editSoapId) {
				await patientApi.updateSOAPNote(admission.id, editSoapId, body);
			} else {
				await patientApi.createSOAPNote(admission.id, body);
			}
			soapNotes = await patientApi.getSOAPNotes(admission.id);
			showSoapModal = false;
			soapSubjective = ''; soapObjective = ''; soapAssessment = ''; soapPlan = ''; editSoapId = null;
			toastStore.addToast('SOAP note saved', 'success');
		} catch { toastStore.addToast('Failed to save note', 'error'); }
		finally { soapSubmitting = false; }
	}

	function resetSoapForm() {
		soapSubjective = '';
		soapObjective = '';
		soapAssessment = '';
		soapPlan = '';
		editSoapId = null;
	}

	function closeSoapModal() {
		showSoapModal = false;
		resetSoapForm();
	}

	function openNewSoap() {
		resetSoapForm();
		showSoapModal = true;
	}

	function openEditSoap(note: any) {
		editSoapId = note.id;
		soapSubjective = note.subjective ?? '';
		soapObjective = note.objective ?? '';
		soapAssessment = note.assessment ?? '';
		soapPlan = note.plan ?? '';
		showSoapModal = true;
	}

	async function dischargePatient() {
		if (!admission || !patient) return;
		dischargeSubmitting = true;
		try {
			await patientApi.dischargePatient(patient.id, admission.id, {
				discharge_summary: dischargeSummary,
				discharge_instructions: dischargeInstructions,
				follow_up_date: dischargeFollowUp || undefined,
			});
			toastStore.addToast('Patient discharged', 'success');
			goto('/patients');
		} catch { toastStore.addToast('Failed to discharge patient', 'error'); }
		finally { dischargeSubmitting = false; }
	}

	function fmtDate(d: string | null | undefined) {
		if (!d) return '—';
		return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
	}

	function fmtTime(d: string | null | undefined) {
		if (!d) return '';
		return new Date(d).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
	}

	function fmtTimeShort(d: string | null | undefined) {
		if (!d) return '';
		const date = new Date(d);
		return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
	}

	function getChartX(index: number, total: number): number {
		if (total <= 1) return 50;
		return (index / (total - 1)) * 100;
	}

	function getChartPoints(param: string): Array<{ index: number; value: number }> {
		return sortedVitals
			.map((v, index) => ({ index, value: Number((v as any)[param]) }))
			.filter((point) => Number.isFinite(point.value) && point.value > 0);
	}

	function getChartBounds(values: number[]): { min: number; max: number } {
		if (values.length === 0) {
			return { min: 0, max: 100 };
		}
		const minValue = Math.min(...values);
		const maxValue = Math.max(...values);
		const padding = Math.max((maxValue - minValue) * 0.15, maxValue * 0.1, 1);
		return {
			min: Math.max(0, minValue - padding),
			max: maxValue + padding,
		};
	}

	function getChartY(value: number, min: number, max: number): number {
		const range = max - min || 1;
		return 100 - ((value - min) / range) * 100;
	}

	function getChartLabelIndices(total: number): number[] {
		if (total <= 5) {
			return Array.from({ length: total }, (_, index) => index);
		}
		const indices = new Set<number>([0, total - 1]);
		for (let index = 2; index < total - 1; index += 2) {
			indices.add(index);
		}
		return Array.from(indices).sort((left, right) => left - right);
	}

	// Get IO events at a specific time (within 30 minute window)
	function getEventsAtVitalTime(vitalTime: string): AdmissionIOEvent[] {
		const vitalDate = new Date(vitalTime);
		const vitalHourMin = `${String(vitalDate.getHours()).padStart(2, '0')}:${String(vitalDate.getMinutes()).padStart(2, '0')}`;
		
		return ioEvents.filter(evt => {
			if (!evt.event_time) return false;
			// Compare just the time portion HH:mm
			const evtTime = evt.event_time.slice(0, 5);
			const [evtH, evtM] = evtTime.split(':').map(Number);
			const [vitalH, vitalM] = vitalHourMin.split(':').map(Number);
			
			const evtMinutes = evtH * 60 + evtM;
			const vitalMinutes = vitalH * 60 + vitalM;
			const diffMinutes = Math.abs(evtMinutes - vitalMinutes);
			
			return diffMinutes <= 30; // Events within 30 minutes
		});
	}

	function handleChartPointHover(event: MouseEvent, vitalIndex: number, param: string) {
		const target = event.currentTarget as SVGCircleElement;
		const rect = target.getBoundingClientRect();
		const svgParent = target.closest('svg')?.parentElement;
		if (svgParent) {
			const parentRect = svgParent.getBoundingClientRect();
			tooltipX = rect.left - parentRect.left + rect.width / 2;
			tooltipY = rect.top - parentRect.top - 10;
		}
		hoveredVitalIndex = vitalIndex;
		hoveredVitalParam = param;
	}

	function handleChartPointLeave() {
		hoveredVitalIndex = null;
		hoveredVitalParam = null;
	}
</script>

<!-- ══════════════════════════════════════════════════════════════
     ADMISSION REVIEW & VITALS TREND PAGE
     ══════════════════════════════════════════════════════════════ -->
<div class="min-h-screen" style="background: #f1f5f9;">

{#if loading}
	<div class="flex items-center justify-center h-64">
		<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
	</div>
{:else if patient && admission}

<!-- Max width container for narrower page -->
<div class="mx-auto" style="max-width: 768px;">

<!-- ── Top Header Bar ─────────────────────────────────────────── -->
<div class="sticky top-0 z-30 px-4 py-3 flex items-center gap-3"
	style="background: linear-gradient(to bottom, #1e3a5f, #162d4a); box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
	<button onclick={() => goto('/patients')} class="w-8 h-8 flex items-center justify-center rounded-lg cursor-pointer"
		style="background: rgba(255,255,255,0.1);">
		<ArrowLeft class="w-4 h-4 text-white" />
	</button>
	<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="sm" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
	<div class="flex-1 min-w-0">
		<p class="text-sm font-bold text-white truncate">{patient.name}</p>
		<p class="text-[10px] text-blue-200">{patient.patient_id} · {admission.department} · Bed {admission.bed_number || '—'}</p>
		<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
	</div>
	<div class="flex flex-col items-end">
		<span class="text-[9px] font-bold px-2 py-0.5 rounded-full"
			style="background: rgba(34,197,94,0.25); color: #4ade80; border: 1px solid rgba(34,197,94,0.4);">
			● ADMITTED
		</span>
		<span class="text-[9px] text-blue-300 mt-0.5">Since {fmtDate(admission.admission_date)}</span>
	</div>
</div>

<div class="px-4 py-4 space-y-4">

<!-- ══════════════════════════════════════════════════════════════
     SECTION 1: ADMISSION REVIEW & VITALS TREND
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<!-- Header -->
	<div class="px-4 py-3 flex items-center justify-between" style="background: linear-gradient(to bottom, #fef7ed, #fefce8);">
		<div class="flex items-center gap-2">
			<Activity class="w-5 h-5 text-blue-600" />
			<span class="text-sm font-bold text-gray-800">Admission Review & Vitals Trend</span>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => showVitalModal = true}
				class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #22c55e, #16a34a); box-shadow: 0 2px 4px rgba(22,163,74,0.3);">
				<Zap class="w-3.5 h-3.5" /> Record Vital
			</button>
		{/if}
	</div>

	<!-- Filter Pills -->
	<div class="px-4 py-3 flex flex-wrap items-center gap-2" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<!-- Vitals Dropdown -->
		<div class="relative">
			<button onclick={() => { vitalsDropdownOpen = !vitalsDropdownOpen; biochemDropdownOpen = false; haemaDropdownOpen = false; }}
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
				style="background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;">
				<HeartPulse class="w-3.5 h-3.5" />
				Vitals
				{#if selectedVitalsCount > 0}
					<span class="w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center">
						{selectedVitalsCount}
					</span>
				{/if}
				<ChevronDown class="w-3 h-3" />
			</button>
			{#if vitalsDropdownOpen}
				<div class="absolute top-full left-0 mt-1 w-48 rounded-lg shadow-lg z-20 py-1"
					style="background: white; border: 1px solid rgba(0,0,0,0.1);">
					{#each Object.entries(vitalParamsConfig) as [key, cfg]}
						<button onclick={() => toggleVitalParam(key)}
							class="w-full px-3 py-2 text-left text-xs flex items-center gap-2 cursor-pointer hover:bg-gray-50">
							<div class="w-4 h-4 rounded border flex items-center justify-center"
								style="border-color: {selectedVitalParams.includes(key) ? cfg.color : '#d1d5db'}; background: {selectedVitalParams.includes(key) ? cfg.color : 'transparent'};">
								{#if selectedVitalParams.includes(key)}
									<span class="text-white text-[10px]">✓</span>
								{/if}
							</div>
							<span class="w-2 h-2 rounded-full" style="background: {cfg.color};"></span>
							{cfg.label}
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Biochemistry Dropdown -->
		<div class="relative">
			<button onclick={() => { biochemDropdownOpen = !biochemDropdownOpen; vitalsDropdownOpen = false; haemaDropdownOpen = false; }}
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
				style="background: #f5f3ff; border: 1px solid #e9d5ff; color: #7c3aed;">
				<FlaskConical class="w-3.5 h-3.5" />
				Biochemistry
				<ChevronDown class="w-3 h-3" />
			</button>
			{#if biochemDropdownOpen}
				<div class="absolute top-full left-0 mt-1 w-48 rounded-lg shadow-lg z-20 py-1"
					style="background: white; border: 1px solid rgba(0,0,0,0.1);">
					{#each Object.entries(biochemParams) as [key, cfg]}
						<button onclick={() => toggleVitalParam(key)}
							class="w-full px-3 py-2 text-left text-xs flex items-center gap-2 cursor-pointer hover:bg-gray-50">
							<div class="w-4 h-4 rounded border flex items-center justify-center"
								style="border-color: {selectedVitalParams.includes(key) ? cfg.color : '#d1d5db'}; background: {selectedVitalParams.includes(key) ? cfg.color : 'transparent'};">
								{#if selectedVitalParams.includes(key)}
									<span class="text-white text-[10px]">✓</span>
								{/if}
							</div>
							<span class="w-2 h-2 rounded-full" style="background: {cfg.color};"></span>
							{cfg.label}
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Haematology Dropdown -->
		<div class="relative">
			<button onclick={() => { haemaDropdownOpen = !haemaDropdownOpen; vitalsDropdownOpen = false; biochemDropdownOpen = false; }}
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
				style="background: #fdf2f8; border: 1px solid #fbcfe8; color: #db2777;">
				<TestTube class="w-3.5 h-3.5" />
				Haematology
				<ChevronDown class="w-3 h-3" />
			</button>
			{#if haemaDropdownOpen}
				<div class="absolute top-full left-0 mt-1 w-48 rounded-lg shadow-lg z-20 py-1"
					style="background: white; border: 1px solid rgba(0,0,0,0.1);">
					{#each Object.entries(haemaParams) as [key, cfg]}
						<button onclick={() => toggleVitalParam(key)}
							class="w-full px-3 py-2 text-left text-xs flex items-center gap-2 cursor-pointer hover:bg-gray-50">
							<div class="w-4 h-4 rounded border flex items-center justify-center"
								style="border-color: {selectedVitalParams.includes(key) ? cfg.color : '#d1d5db'}; background: {selectedVitalParams.includes(key) ? cfg.color : 'transparent'};">
								{#if selectedVitalParams.includes(key)}
									<span class="text-white text-[10px]">✓</span>
								{/if}
							</div>
							<span class="w-2 h-2 rounded-full" style="background: {cfg.color};"></span>
							{cfg.label}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Selected Parameter Pills -->
	{#if selectedVitalParams.length > 0}
		<div class="px-4 py-2 flex flex-wrap gap-2" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
			{#each selectedVitalParams as param}
				{@const cfg = vitalParamsConfig[param] || biochemParams[param] || haemaParams[param]}
				{#if cfg}
					<span class="flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-medium"
						style="background: {cfg.color}15; border: 1px solid {cfg.color}40; color: {cfg.color};">
						<span class="w-1.5 h-1.5 rounded-full" style="background: {cfg.color};"></span>
						{cfg.label}
						<button onclick={() => toggleVitalParam(param)} class="ml-0.5 cursor-pointer hover:opacity-70">
							<X class="w-3 h-3" />
						</button>
					</span>
				{/if}
			{/each}
		</div>
	{/if}

	<!-- Chart / Table Toggle -->
	<div class="px-4 py-2 flex justify-end">
		<div class="flex rounded-lg overflow-hidden" style="border: 1px solid rgba(0,0,0,0.12);">
			<button class="flex items-center gap-1 px-3 py-1.5 text-xs font-medium cursor-pointer"
				style="background: {vitalsView === 'chart' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f8faff'}; color: {vitalsView === 'chart' ? 'white' : '#64748b'};"
				onclick={() => vitalsView = 'chart'}>
				<BarChart3 class="w-3.5 h-3.5" /> Chart
			</button>
			<button class="flex items-center gap-1 px-3 py-1.5 text-xs font-medium cursor-pointer"
				style="background: {vitalsView === 'table' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f8faff'}; color: {vitalsView === 'table' ? 'white' : '#64748b'};"
				onclick={() => vitalsView = 'table'}>
				<LayoutList class="w-3.5 h-3.5" /> Table
			</button>
		</div>
	</div>

	<!-- Chart View -->
	{#if vitalsView === 'chart' && sortedVitals.length > 0}
		<div class="p-4 space-y-6">
			{#each selectedVitalParams as param}
				{@const cfg = vitalParamsConfig[param] || biochemParams[param] || haemaParams[param]}
				{@const points = getChartPoints(param)}
				{@const diastolicPoints = param === 'systolic_bp' ? getChartPoints('diastolic_bp') : []}
				{@const bounds = getChartBounds(param === 'systolic_bp' ? [...points.map((point) => point.value), ...diastolicPoints.map((point) => point.value)] : points.map((point) => point.value))}
				{@const labelIndices = getChartLabelIndices(sortedVitals.length)}
				{#if cfg && points.length > 0}
					<div class="rounded-xl p-4" style="background: #fef7ed; border: 1px solid rgba(0,0,0,0.05);">
						<!-- Chart Header -->
						<div class="flex items-center gap-2 mb-3">
							<button class="flex items-center gap-1 text-gray-400 text-xs cursor-pointer">
								<ChevronUp class="w-3 h-3" />
								<ChevronDown class="w-3 h-3" />
							</button>
							<span class="w-2.5 h-2.5 rounded-full" style="background: {cfg.color};"></span>
							<span class="text-sm font-semibold text-gray-800">{cfg.label}</span>
							<span class="text-xs text-gray-500">({cfg.unit})</span>
						</div>

						<!-- Chart Area -->
						<div class="relative h-32">
							<!-- Tooltip -->
							{#if hoveredVitalIndex !== null && hoveredVitalParam === param && sortedVitals[hoveredVitalIndex]}
								{@const hoveredVital = sortedVitals[hoveredVitalIndex]}
								{@const eventsAtTime = getEventsAtVitalTime(hoveredVital.recorded_at)}
								<div 
									class="absolute z-50 rounded-xl shadow-2xl px-4 py-3 min-w-[200px] pointer-events-none"
									style="
										background: white;
										border: 2px solid {cfg.color};
										left: {tooltipX}px;
										top: {tooltipY}px;
										transform: translate(-50%, -100%);
										opacity: 0;
										animation: fadeIn 0.2s ease forwards;
										box-shadow: 0 10px 25px rgba(0,0,0,0.15);
									">
									<!-- Time -->
									<div class="text-xs font-bold text-gray-900 mb-2 pb-2 border-b border-gray-200">
										{fmtTimeShort(hoveredVital.recorded_at)}
									</div>
									<!-- Vital values -->
									<div class="space-y-1.5">
										{#if param === 'systolic_bp' && hoveredVital.systolic_bp}
											<div class="flex items-center gap-2">
												<span class="w-2 h-2 rounded-full" style="background: {cfg.color};"></span>
												<span class="text-[11px] font-medium text-gray-700">Systolic:</span>
												<span class="text-sm font-bold" style="color: {cfg.color};">{hoveredVital.systolic_bp}</span>
											</div>
											{#if hoveredVital.diastolic_bp}
												<div class="flex items-center gap-2">
													<span class="w-2 h-2 rounded-full opacity-50" style="background: {cfg.color};"></span>
													<span class="text-[11px] font-medium text-gray-700">Diastolic:</span>
													<span class="text-sm font-bold" style="color: {cfg.color};">{hoveredVital.diastolic_bp}</span>
												</div>
											{/if}
										{:else}
											{@const value = (hoveredVital as any)[param]}
											{#if value}
												<div class="flex items-center gap-2">
													<span class="w-2 h-2 rounded-full" style="background: {cfg.color};"></span>
													<span class="text-[11px] font-medium text-gray-700">{cfg.label}:</span>
													<span class="text-sm font-bold" style="color: {cfg.color};">{value}</span>
													<span class="text-[10px] text-gray-400">{cfg.unit}</span>
												</div>
											{/if}
										{/if}
									</div>
									<!-- Events at this time -->
									{#if eventsAtTime.length > 0}
										<div class="mt-3 pt-2 border-t border-gray-200">
											<div class="text-[10px] font-semibold text-gray-500 mb-1.5">Events</div>
											<div class="space-y-1">
												{#each eventsAtTime.slice(0, 3) as evt}
													{@const typeKey = evt.event_type?.toUpperCase() || 'IV'}
													{@const eventCfg = ioEventTypes[typeKey] || ioEventTypes['IV']}
													{@const Icon = eventCfg.icon}
													<div class="flex items-center gap-1.5">
														<Icon class="w-3 h-3 shrink-0" style="color: {eventCfg.textColor.replace('text-', '')} === 'green-700' ? '#15803d' : eventCfg.textColor.replace('text-', '') === 'amber-700' ? '#b45309' : eventCfg.textColor.replace('text-', '') === 'cyan-700' ? '#0e7490' : eventCfg.textColor.replace('text-', '') === 'purple-700' ? '#6b21a8' : '#57534e';" />
														<span class="text-[11px] text-gray-700 truncate">{evt.description || eventCfg.label}</span>
													</div>
												{/each}
											</div>
										</div>
									{/if}
									<!-- Pointing arrow -->
									<div class="absolute left-1/2 bottom-0 w-3 h-3 -translate-x-1/2 translate-y-1/2 rotate-45" 
										style="background: white; border-right: 2px solid {cfg.color}; border-bottom: 2px solid {cfg.color};"></div>
								</div>
							{/if}
							<!-- Y-axis labels -->
							<div class="absolute left-0 top-0 bottom-0 w-8 flex flex-col justify-between text-[10px] text-gray-400 pr-2">
								<span>{Math.round(bounds.max)}</span>
								<span>{Math.round((bounds.max + bounds.min) / 2)}</span>
								<span>{Math.round(bounds.min)}</span>
							</div>

							<!-- Chart grid and line -->
							<div class="absolute left-10 right-0 top-0 bottom-6">
								<!-- Grid lines -->
								<div class="absolute inset-0 flex flex-col justify-between">
									<div class="border-b border-gray-200"></div>
									<div class="border-b border-gray-100"></div>
									<div class="border-b border-gray-200"></div>
								</div>

								<!-- Line chart using SVG -->
								<svg class="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
									<!-- Line path -->
									<polyline
										fill="none"
										stroke={cfg.color}
										stroke-width="0.5"
										stroke-linecap="round"
										stroke-linejoin="round"
										points={points.map((point) => `${getChartX(point.index, sortedVitals.length)},${getChartY(point.value, bounds.min, bounds.max)}`).join(' ')}
									/>
									<!-- Data points -->
									{#each points as point}
										{@const x = getChartX(point.index, sortedVitals.length)}
										{@const y = getChartY(point.value, bounds.min, bounds.max)}
										{@const isHovered = hoveredVitalIndex === point.index && hoveredVitalParam === param}
										<circle 
											cx={x}
											cy={y}
											r={isHovered ? "2" : "1.5"} 
											fill={cfg.color}
											role="button"
											tabindex="0"
											aria-label="Data point at {fmtTimeShort(sortedVitals[point.index]?.recorded_at)}"
											style="cursor: pointer; transition: r 0.15s ease;"
											onmouseenter={(e) => handleChartPointHover(e, point.index, param)}
											onmouseleave={handleChartPointLeave}
										/>
									{/each}
								</svg>

								<!-- Diastolic line for BP -->
								{#if param === 'systolic_bp'}
										<svg class="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
											<polyline
												fill="none"
												stroke={cfg.color}
												stroke-width="0.5"
												stroke-dasharray="2 2"
												stroke-linecap="round"
												opacity="0.5"
												points={diastolicPoints.map((point) => `${getChartX(point.index, sortedVitals.length)},${getChartY(point.value, bounds.min, bounds.max)}`).join(' ')}
										/>
									</svg>
								{/if}
							</div>

							<!-- X-axis labels (times) -->
							<div class="absolute left-10 right-0 bottom-0 h-4 text-[10px] text-gray-400">
								{#each labelIndices as index}
									{#if sortedVitals[index]}
										<span class="absolute" style={`left: ${getChartX(index, sortedVitals.length)}%; transform: translateX(-50%);`}>
											{fmtTimeShort(sortedVitals[index].recorded_at)}
										</span>
									{/if}
								{/each}
							</div>
						</div>
					</div>
				{/if}
			{/each}
		</div>
	{:else if vitalsView === 'table'}
		<!-- Table View -->
		<div class="p-4">
			<div class="overflow-x-auto rounded-lg" style="border: 1px solid rgba(0,0,0,0.08);">
				<table class="w-full text-xs">
					<thead>
						<tr style="background: #f8faff;">
							<th class="text-left px-3 py-2 font-semibold text-gray-600">Time</th>
							{#each selectedVitalParams as param}
								{@const cfg = vitalParamsConfig[param] || biochemParams[param] || haemaParams[param]}
								{#if cfg}
									<th class="text-right px-3 py-2 font-semibold" style="color: {cfg.color};">{cfg.label}</th>
								{/if}
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each vitals.slice(0, 10) as v}
							<tr style="border-top: 1px solid rgba(0,0,0,0.04);">
								<td class="px-3 py-2 text-gray-500">{fmtTimeShort(v.recorded_at)}</td>
								{#each selectedVitalParams as param}
									{@const cfg = vitalParamsConfig[param] || biochemParams[param] || haemaParams[param]}
									{@const val = (v as any)[param]}
									{#if cfg}
										<td class="px-3 py-2 text-right font-medium" style="color: {cfg.color};">
											{val ?? '—'}
											{#if param === 'systolic_bp' && v.diastolic_bp}
												/{v.diastolic_bp}
											{/if}
										</td>
									{/if}
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else}
		<div class="p-8 text-center text-xs text-gray-400">
			No vitals recorded yet. Click "Record Vital" to add readings.
		</div>
	{/if}
</div>

<!-- ══════════════════════════════════════════════════════════════
     SECTION 2: I/O & EVENTS TIMELINE
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<!-- Header -->
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-4">
			<span class="text-sm font-bold text-gray-800">I/O & Events Timeline</span>
			<!-- Legend -->
			<div class="flex items-center gap-3 text-[10px]">
				{#each Object.entries(ioEventTypes) as [key, cfg]}
					{@const Icon = cfg.icon}
					<span class="flex items-center gap-1 {cfg.textColor}">
						<Icon class="w-3 h-3" />
						{cfg.label}
					</span>
				{/each}
			</div>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => showAddEventModal = true}
				class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 4px rgba(37,99,235,0.3);">
				<Plus class="w-3.5 h-3.5" /> Add Event
			</button>
		{/if}
	</div>

	<!-- Timeline Grid -->
	{#if timeSlots.length > 0}
		<div class="p-4 overflow-x-auto">
			<div class="flex gap-4 min-w-max">
				{#each timeSlots as time}
					<div class="flex-shrink-0 w-28">
						<!-- Time header -->
						<div class="text-center text-xs font-bold text-gray-700 mb-2">{time}</div>
						<!-- Events for this time -->
						<div class="space-y-1.5">
							{#each ioEventsByTime[time] || [] as event}
								{@const typeKey = event.event_type?.toUpperCase() || 'IV'}
								{@const cfg = ioEventTypes[typeKey] || ioEventTypes['IV']}
								{@const Icon = cfg.icon}
								<div class="px-2 py-1.5 rounded-lg text-[10px] font-medium truncate {cfg.bgColor} {cfg.textColor}"
									style="border: 1px solid"
									class:border-green-200={typeKey === 'IV'}
									class:border-amber-200={typeKey === 'ORAL'}
									class:border-cyan-200={typeKey === 'URINE'}
									class:border-stone-200={typeKey === 'STOOL'}
									class:border-purple-200={typeKey === 'DRUG'}>
									<span class="flex items-center gap-1">
										<Icon class="w-3 h-3 shrink-0" />
										<span class="truncate">{event.description || cfg.label}</span>
									</span>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{:else}
		<div class="p-8 text-center text-xs text-gray-400">No events recorded yet.</div>
	{/if}
</div>

<!-- ══════════════════════════════════════════════════════════════
     SECTION 3: 24-HOUR I/O SUMMARY
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<div class="px-4 py-3 font-bold text-gray-800 text-sm" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		24-Hour I/O Summary
	</div>

	<!-- Summary Cards -->
	<div class="grid grid-cols-4 gap-3 p-4">
		<div class="rounded-xl p-3" style="background: #f0fdf4; border: 2px solid #bbf7d0;">
			<div class="flex items-center gap-1 text-green-700 text-xs font-medium mb-1">
				<Droplet class="w-3.5 h-3.5" /> IV Input
			</div>
			<div class="text-xl font-bold text-green-800">{ioSummary?.iv_input_ml ?? 0} ml</div>
			<div class="text-[10px] text-green-600">{ioEvents.filter(e => e.event_type === 'IV').length} entries</div>
		</div>
		<div class="rounded-xl p-3" style="background: #fffbeb; border: 2px solid #fde68a;">
			<div class="flex items-center gap-1 text-amber-700 text-xs font-medium mb-1">
				<Utensils class="w-3.5 h-3.5" /> Oral Intake
			</div>
			<div class="text-xl font-bold text-amber-800">{ioSummary?.oral_intake_ml ?? 0} ml</div>
			<div class="text-[10px] text-amber-600">{ioEvents.filter(e => e.event_type === 'ORAL').length} entries</div>
		</div>
		<div class="rounded-xl p-3" style="background: #ecfeff; border: 2px solid #a5f3fc;">
			<div class="flex items-center gap-1 text-cyan-700 text-xs font-medium mb-1">
				<Beaker class="w-3.5 h-3.5" /> Urine Output
			</div>
			<div class="text-xl font-bold text-cyan-800">{ioSummary?.urine_output_ml ?? 0} ml</div>
			<div class="text-[10px] text-cyan-600">{ioEvents.filter(e => e.event_type === 'URINE').length} entries</div>
		</div>
		<div class="rounded-xl p-3" style="background: #f5f5f4; border: 2px solid #d6d3d1;">
			<div class="flex items-center gap-1 text-stone-600 text-xs font-medium mb-1">
				<Circle class="w-3.5 h-3.5" /> Stool
			</div>
			<div class="text-xl font-bold text-stone-700">{ioSummary?.stool_count ?? 0}× Normal</div>
			<div class="text-[10px] text-stone-500">{ioSummary?.stool_count ?? 0} entries</div>
		</div>
	</div>

	<!-- I/O Events Log -->
	<div class="px-4 pb-4">
		<div class="flex items-center justify-between mb-2">
			<span class="text-xs font-semibold text-gray-700">I/O Events Log</span>
			<span class="text-[10px] text-gray-400">{ioEvents.length} events</span>
		</div>
		<div class="rounded-lg overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
			{#if ioEvents.length === 0}
				<div class="p-6 text-center text-xs text-gray-400">No events recorded.</div>
			{:else}
				<div class="divide-y divide-gray-100 max-h-64 overflow-y-auto">
					{#each ioEvents.slice(0, 10) as event}
						{@const typeKey = event.event_type?.toUpperCase() || 'IV'}
						{@const cfg = ioEventTypes[typeKey] || ioEventTypes['IV']}
						<div class="flex items-center gap-3 px-3 py-2.5">
							<span class="text-[11px] text-gray-400 w-12 shrink-0">{event.event_time?.slice(0, 5) || '—'}</span>
							<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase {cfg.bgColor} {cfg.textColor}"
								style="border: 1px solid">
								{event.event_type || 'IV'}
							</span>
							<span class="flex-1 text-xs text-gray-700 truncate">{event.description || '—'}</span>
							{#if event.amount_ml}
								<span class="text-sm font-bold text-green-700">{event.amount_ml} ml</span>
							{/if}
							<span class="text-[10px] text-gray-400">{event.recorded_by || 'Staff'}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>

<!-- ══════════════════════════════════════════════════════════════
     SECTION 4: CONNECTED EQUIPMENT
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<!-- Header -->
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<Wifi class="w-4 h-4 text-green-600" />
			<span class="text-sm font-bold text-gray-800">Connected Equipment</span>
			<span class="w-5 h-5 rounded-full bg-green-500 text-white text-[10px] font-bold flex items-center justify-center">
				{equipment.length}
			</span>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => showEquipModal = true}
				class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
				style="background: white; border: 1px solid #d1d5db; color: #374151;">
				<Plus class="w-3.5 h-3.5" /> Connect Equipment
			</button>
		{/if}
	</div>

	<!-- Equipment Cards -->
	{#if equipment.length > 0}
		<div class="p-4 grid grid-cols-2 gap-3">
			{#each equipment as eq}
				<div class="rounded-xl p-3" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08);">
					<div class="flex items-center gap-2 mb-1">
						<span class="w-2 h-2 rounded-full {eq.status === 'Active' ? 'bg-green-500' : 'bg-gray-400'}"></span>
						<span class="text-xs font-bold text-gray-800">{eq.equipment_type}</span>
					</div>
					<div class="text-[10px] text-gray-500">{eq.equipment_id || 'No ID'}</div>
					{#if eq.connected_since}
						<div class="text-[10px] text-gray-400 mt-1">Since {eq.connected_since}</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	<!-- Live Equipment Data -->
	{#if equipment.some(eq => eq.live_data && eq.status === 'Active')}
		<div class="px-4 pb-4">
			<div class="flex items-center gap-2 mb-3">
				<span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
				<span class="text-sm font-semibold text-gray-800">Live Equipment Data</span>
				<span class="text-[10px] text-gray-400">Auto-updating every 2s</span>
			</div>

			<div class="space-y-3">
				{#each equipment.filter(eq => eq.live_data && eq.status === 'Active') as eq}
					{@const liveData = liveEquipmentData[eq.id] || eq.live_data || {}}
					<div class="rounded-xl overflow-hidden" style="background: #1e293b;">
						<div class="px-3 py-2 flex items-center gap-2" style="background: #334155;">
							<Cpu class="w-4 h-4 text-gray-400" />
							<span class="text-xs font-semibold text-white">{eq.equipment_type}</span>
							<span class="text-[10px] text-gray-400">{eq.equipment_id || ''}</span>
						</div>
						<div class="p-3 grid grid-cols-3 gap-3">
							{#if eq.equipment_type === 'Bedside Monitor'}
								{#each [
									['HR', liveData.hr ?? liveData.heart_rate, 'bpm', '#ef4444'],
									['NIBP', `${liveData.bp_sys ?? 120}/${liveData.bp_dia ?? 80}`, 'MAP ' + (liveData.map ?? 93), '#3b82f6'],
									['SpO₂', liveData.spo2 ?? 98, '%', '#14b8a6'],
									['RR', liveData.rr ?? 16, 'br/min', '#a855f7'],
									['TEMP', liveData.temp ?? 98.6, '°F', '#f59e0b'],
									['EtCO₂', liveData.etco2 ?? 35, 'mmHg', '#06b6d4'],
								] as [label, value, unit, color]}
									<div class="text-center">
										<div class="text-[10px] font-medium" style="color: {color};">{label}</div>
										<div class="text-lg font-bold" style="color: {color};">{value}</div>
										<div class="text-[9px] text-gray-400">{unit}</div>
									</div>
								{/each}
							{:else if eq.equipment_type === 'Ventilator'}
								{#each [
									['PIP', liveData.pip ?? 16, 'cmH₂O', '#3b82f6'],
									['PEEP', liveData.peep ?? 5, 'cmH₂O', '#22c55e'],
									['FiO₂', liveData.fio2 ?? 40, '%', '#f59e0b'],
									['Vt', liveData.tidal_vol ?? 500, 'mL', '#8b5cf6'],
								] as [label, value, unit, color]}
									<div class="text-center">
										<div class="text-[10px] font-medium" style="color: {color};">{label}</div>
										<div class="text-lg font-bold" style="color: {color};">{value}</div>
										<div class="text-[9px] text-gray-400">{unit}</div>
									</div>
								{/each}
							{:else if eq.equipment_type === 'ABG Analyzer'}
								{#each [
									['pH', liveData.ph ?? 7.38, 'units', '#3b82f6'],
									['pCO₂', liveData.pco2 ?? 42, 'mmHg', '#22c55e'],
									['pO₂', liveData.po2 ?? 85, 'mmHg', '#f59e0b'],
									['HCO₃', liveData.hco3 ?? 24, 'mEq/L', '#8b5cf6'],
									['LAC', liveData.lactate ?? 1.2, 'mmol/L', '#ef4444'],
								] as [label, value, unit, color]}
									<div class="text-center">
										<div class="text-[10px] font-medium" style="color: {color};">{label}</div>
										<div class="text-lg font-bold" style="color: {color};">{value}</div>
										<div class="text-[9px] text-gray-400">{unit}</div>
									</div>
								{/each}
							{:else}
								<!-- Generic equipment data display -->
								{#each Object.entries(liveData).slice(0, 6) as [key, value]}
									<div class="text-center">
										<div class="text-[10px] font-medium text-gray-400">{key}</div>
										<div class="text-lg font-bold text-white">{value}</div>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{:else if equipment.length === 0}
		<div class="p-6 text-center text-xs text-gray-400">No equipment connected.</div>
	{/if}
</div>

<!-- ══════════════════════════════════════════════════════════════
     SECTION 5: CLINICAL PROGRESS NOTES (SOAP)
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<!-- Header -->
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<FileText class="w-4 h-4 text-blue-600" />
			<span class="text-sm font-bold text-gray-800 uppercase tracking-wide">Clinical Progress Notes (SOAP)</span>
		</div>
		<div class="flex items-center gap-2">
			<button
				onclick={() => showSoapHistoryModal = true}
				class="text-xs font-semibold text-blue-600 cursor-pointer"
			>
				VIEW FULL HISTORY
			</button>
			{#if role === 'STUDENT' || role === 'FACULTY'}
				<button
					onclick={openNewSoap}
					class="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white cursor-pointer flex items-center gap-1"
					style="background: linear-gradient(to bottom, #0d9488, #0f766e);"
				>
					<Plus class="w-3.5 h-3.5" />
					New Note
				</button>
			{/if}
		</div>
	</div>

	{#if latestSoap}
		<div class="p-4 space-y-3">
			<div class="flex items-center justify-between rounded-xl px-3 py-2 text-[11px]" style="background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.12);">
				<div class="text-gray-600">
					Latest entry
					<span class="font-semibold text-gray-800 ml-1">{fmtDate(latestSoap.created_at)} · {fmtTime(latestSoap.created_at) || '—'}</span>
				</div>
				<div class="text-gray-500">{soapNotes.length} entr{soapNotes.length === 1 ? 'y' : 'ies'}</div>
			</div>

			<!-- Subjective -->
			<div class="rounded-xl p-4" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<User class="w-4 h-4 text-orange-500" />
						<span class="text-sm font-bold text-gray-800">Subjective</span>
					</div>
					<div class="flex items-center gap-2">
						<button class="text-[10px] text-gray-400 cursor-pointer"><Clock class="w-3 h-3 inline" /></button>
						{#if role === 'STUDENT' || role === 'FACULTY'}
							<button onclick={() => openEditSoap(latestSoap)} class="text-xs text-blue-600 cursor-pointer flex items-center gap-1">
								<Edit class="w-3 h-3" /> Edit
							</button>
						{/if}
					</div>
				</div>
				<p class="text-xs text-gray-700 leading-relaxed">{latestSoap.subjective || 'No subjective notes recorded.'}</p>
			</div>

			<!-- Objective -->
			<div class="rounded-xl p-4" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<Activity class="w-4 h-4 text-blue-500" />
						<span class="text-sm font-bold text-gray-800">Objective</span>
					</div>
					<div class="flex items-center gap-2">
						<button class="text-[10px] text-gray-400 cursor-pointer"><Clock class="w-3 h-3 inline" /></button>
						{#if role === 'STUDENT' || role === 'FACULTY'}
							<button onclick={() => openEditSoap(latestSoap)} class="text-xs text-blue-600 cursor-pointer flex items-center gap-1">
								<Edit class="w-3 h-3" /> Edit
							</button>
						{/if}
					</div>
				</div>
				<p class="text-xs text-gray-700 leading-relaxed">{latestSoap.objective || 'No objective notes recorded.'}</p>
			</div>

			<!-- Assessment -->
			<div class="rounded-xl p-4" style="background: #fefce8; border: 1px solid rgba(234,179,8,0.2);">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<Stethoscope class="w-4 h-4 text-amber-600" />
						<span class="text-sm font-bold text-gray-800">Assessment</span>
					</div>
					<div class="flex items-center gap-2">
						<button class="text-[10px] text-gray-400 cursor-pointer"><Clock class="w-3 h-3 inline" /></button>
						{#if role === 'STUDENT' || role === 'FACULTY'}
							<button onclick={() => openEditSoap(latestSoap)} class="text-xs text-blue-600 cursor-pointer flex items-center gap-1">
								<Edit class="w-3 h-3" /> Edit
							</button>
						{/if}
					</div>
				</div>
				<p class="text-xs text-gray-700 leading-relaxed">{latestSoap.assessment || 'No assessment recorded.'}</p>
			</div>

			<!-- Plan & Orders -->
			<div class="rounded-xl p-4" style="background: #f0fdf4; border: 1px solid rgba(34,197,94,0.2);">
				<div class="flex items-center justify-between mb-3">
					<div class="flex items-center gap-2">
						<ClipboardList class="w-4 h-4 text-green-600" />
						<span class="text-sm font-bold text-gray-800">Plan & Orders</span>
					</div>
					<div class="flex items-center gap-2">
						<button class="text-[10px] text-gray-400 cursor-pointer"><Clock class="w-3 h-3 inline" /></button>
						{#if role === 'STUDENT' || role === 'FACULTY'}
							<button onclick={() => openEditSoap(latestSoap)} class="text-xs text-blue-600 cursor-pointer flex items-center gap-1">
								<Edit class="w-3 h-3" /> Edit
							</button>
						{/if}
					</div>
				</div>

				<!-- Plan Text -->
				{#if latestSoap.plan}
					<p class="text-xs text-gray-700 leading-relaxed mb-3">{latestSoap.plan}</p>
				{/if}

				<!-- Plan Items (Medication Orders) -->
				{#if latestSoap.plan_items?.drugs?.length}
					<div class="mb-3">
						<div class="flex items-center gap-1 text-xs font-semibold text-purple-700 mb-2">
							<Pill class="w-3.5 h-3.5" /> Medication Orders
						</div>
						<div class="space-y-1.5">
							{#each latestSoap.plan_items.drugs as drug}
								<div class="flex items-center gap-2">
									<span class="w-1.5 h-1.5 rounded-full {drug.status === 'completed' ? 'bg-green-500' : 'bg-amber-500'}"></span>
									<div class="flex-1">
										<span class="text-xs font-semibold text-gray-800">{drug.name}</span>
										<span class="text-[10px] text-gray-500 ml-1">{drug.dose} · {drug.route} · {drug.frequency}</span>
									</div>
									<button class="text-gray-300 hover:text-gray-500 cursor-pointer"><X class="w-3 h-3" /></button>
								</div>
							{/each}
						</div>
						{#if latestSoap.plan_items.drug_notes}
							<div class="mt-2 px-3 py-2 rounded-lg text-[10px] text-gray-500 italic" style="background: rgba(0,0,0,0.03);">
								{latestSoap.plan_items.drug_notes}
							</div>
						{/if}
					</div>
				{/if}

				<!-- Investigations -->
				{#if latestSoap.plan_items?.investigations?.length}
					<div class="mb-3">
						<div class="flex items-center gap-1 text-xs font-semibold text-blue-700 mb-2">
							<FlaskConical class="w-3.5 h-3.5" /> Investigations Ordered
						</div>
						<div class="space-y-1.5">
							{#each latestSoap.plan_items.investigations as inv}
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-2">
										<span class="w-1.5 h-1.5 rounded-full {inv.status === 'completed' ? 'bg-green-500' : 'bg-amber-500'}"></span>
										<span class="text-xs text-gray-700">{inv.name}</span>
									</div>
									<span class="text-[9px] px-1.5 py-0.5 rounded font-medium {inv.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}">
										{inv.status}
									</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Diet Orders -->
				{#if latestSoap.plan_items?.diet?.length}
					<div>
						<div class="flex items-center gap-1 text-xs font-semibold text-amber-700 mb-2">
							<Utensils class="w-3.5 h-3.5" /> Diet Orders
						</div>
						<div class="space-y-1.5">
							{#each latestSoap.plan_items.diet as diet}
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-2">
										<span class="w-1.5 h-1.5 rounded-full {diet.status === 'completed' ? 'bg-green-500' : 'bg-amber-500'}"></span>
										<span class="text-xs text-gray-700">{diet.name}</span>
									</div>
									<span class="text-[9px] px-1.5 py-0.5 rounded font-medium {diet.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}">
										{diet.status}
									</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<!-- Meta info -->
			{#if latestSoap.note_meta}
				<div class="text-[10px] text-gray-400 px-1">
					{#if latestSoap.note_meta.author}
						<span>By: {latestSoap.note_meta.author}</span>
					{/if}
					{#if latestSoap.note_meta.supervisor}
						<span class="ml-2">· Supervisor: {latestSoap.note_meta.supervisor}</span>
					{/if}
					{#if latestSoap.note_meta.next_review}
						<span class="ml-2">· Next Review: {latestSoap.note_meta.next_review}</span>
					{/if}
				</div>
			{/if}
		</div>
	{:else}
		<div class="p-6 text-center">
			<p class="text-xs text-gray-400 mb-3">No SOAP notes recorded yet.</p>
			{#if role === 'STUDENT' || role === 'FACULTY'}
				<button onclick={openNewSoap}
					class="px-4 py-2 rounded-lg text-xs font-semibold text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #0d9488, #0f766e);">
					<Plus class="w-3.5 h-3.5 inline mr-1" /> Create First Note
				</button>
			{/if}
		</div>
	{/if}
</div>

<!-- ══════════════════════════════════════════════════════════════
     SECTION 6: NURSING SBAR NOTES
     ══════════════════════════════════════════════════════════════ -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<!-- Header -->
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<ClipboardList class="w-4 h-4 text-teal-600" />
			<span class="text-sm font-bold text-gray-800 uppercase tracking-wide">Nursing SBAR Notes</span>
			<span class="w-5 h-5 rounded-full bg-teal-500 text-white text-[10px] font-bold flex items-center justify-center">
				{sbarNotes.length}
			</span>
		</div>
	</div>

	{#if sbarNotes.length > 0}
		<div class="p-4 space-y-3">
			{#each sbarNotes.slice(0, 3) as note}
				<div class="rounded-xl overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
					<!-- Note Header -->
					<div class="px-4 py-2 flex items-center justify-between" style="background: #f0fdfa; border-bottom: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-center gap-2">
							<div class="w-8 h-8 rounded-full bg-teal-500 flex items-center justify-center text-white text-xs font-bold">
								{note.nurse_name?.split(' ').map(n => n[0]).join('') || 'N'}
							</div>
							<div>
								<div class="text-xs font-semibold text-gray-800">{note.nurse_name || 'Nurse'}</div>
								<div class="text-[10px] text-gray-500">
									{new Date(note.created_at).toLocaleDateString()} · {new Date(note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
								</div>
							</div>
						</div>
						<span class="text-[10px] font-mono text-gray-400">{note.sbar_id}</span>
					</div>

					<!-- SBAR Content -->
					<div class="p-4 space-y-3">
						<!-- Situation -->
						<div class="rounded-lg p-3" style="background: #fef2f2; border: 1px solid rgba(239,68,68,0.2);">
							<div class="flex items-center gap-2 mb-2">
								<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500 text-white">S</span>
								<span class="text-xs font-bold text-gray-700">Situation</span>
							</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.situation || 'Not documented'}</p>
						</div>

						<!-- Background -->
						<div class="rounded-lg p-3" style="background: #fff7ed; border: 1px solid rgba(249,115,22,0.2);">
							<div class="flex items-center gap-2 mb-2">
								<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500 text-white">B</span>
								<span class="text-xs font-bold text-gray-700">Background</span>
							</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.background || 'Not documented'}</p>
						</div>

						<!-- Assessment -->
						<div class="rounded-lg p-3" style="background: #eff6ff; border: 1px solid rgba(59,130,246,0.2);">
							<div class="flex items-center gap-2 mb-2">
								<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500 text-white">A</span>
								<span class="text-xs font-bold text-gray-700">Assessment</span>
							</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.assessment || 'Not documented'}</p>
						</div>

						<!-- Recommendation -->
						<div class="rounded-lg p-3" style="background: #f0fdf4; border: 1px solid rgba(34,197,94,0.2);">
							<div class="flex items-center gap-2 mb-2">
								<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500 text-white">R</span>
								<span class="text-xs font-bold text-gray-700">Recommendation</span>
							</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.recommendation || 'Not documented'}</p>
						</div>
					</div>
				</div>
			{/each}

			{#if sbarNotes.length > 3}
				<button class="w-full py-2 rounded-lg text-xs font-semibold text-teal-600 cursor-pointer"
					style="background: #f0fdfa; border: 1px solid rgba(20,184,166,0.2);">
					View All {sbarNotes.length} SBAR Notes
				</button>
			{/if}
		</div>
	{:else}
		<div class="p-6 text-center text-xs text-gray-400">
			No SBAR notes recorded yet.
		</div>
	{/if}
</div>

<!-- ══════════════════════════════════════════════════════════════
     DISCHARGE BUTTON
     ══════════════════════════════════════════════════════════════ -->
{#if (role === 'FACULTY' || role === 'STUDENT') && admission.status === 'Active'}
	<button onclick={() => showDischargeModal = true}
		class="w-full py-4 rounded-xl text-sm font-bold text-white cursor-pointer flex items-center justify-center gap-2"
		style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 3px 8px rgba(239,68,68,0.4);">
		<FileText class="w-5 h-5" /> Discharge Patient
	</button>
{/if}

</div> <!-- /px-4 py-4 -->

</div> <!-- /max-width container -->

{:else if !loading}
	<div class="flex flex-col items-center justify-center h-64 gap-3 px-8 text-center">
		<AlertTriangle class="w-10 h-10 text-amber-400" />
		<p class="text-sm font-semibold text-gray-700">No active admission found</p>
		<p class="text-xs text-gray-400">This patient may not have an active admission.</p>
		<button onclick={() => goto('/patients')}
			class="px-4 py-2 rounded-lg text-xs font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
			Back to Patients
		</button>
	</div>
{/if}

</div>

<!-- ════════════════════════════════════════════════════════
     MODALS
     ════════════════════════════════════════════════════════ -->

<!-- Record Vital Modal -->
{#if showVitalModal}
<AquaModal onclose={() => showVitalModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<HeartPulse class="w-5 h-5 text-red-500" />
			<span class="font-semibold text-gray-800">Record Vitals</span>
		</div>
	{/snippet}
	{#if configuredVitalFields.length === 0}
		<div class="rounded-lg px-3 py-3 text-sm text-amber-700"
			style="background: #fffbeb; border: 1px solid rgba(245,158,11,0.3);"
		>
			No active vital parameters are configured by admin.
		</div>
	{:else}
		<div class="grid grid-cols-2 gap-3">
			{#each configuredVitalFields as field (field.key)}
				<div class={field.valueStyle === 'slash' ? 'col-span-2' : ''}>
					<div class="text-xs font-medium text-gray-600 mb-1">{field.label}{field.unit ? ` (${field.unit})` : ''}</div>
					<input
						bind:value={vitalFormValues[field.key]}
						type={field.valueStyle === 'slash' ? 'text' : 'number'}
						step={field.valueStyle === 'slash' ? undefined : 'any'}
						placeholder={field.placeholder}
						class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);"
					/>
				</div>
			{/each}
		</div>
	{/if}
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => showVitalModal = false}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #22c55e, #16a34a); box-shadow: 0 2px 4px rgba(22,163,74,0.3);"
			onclick={submitVital} disabled={vitalSubmitting || configuredVitalFields.length === 0}>
			{vitalSubmitting ? 'Saving...' : 'Save Vitals'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Add I/O Event Modal -->
{#if showAddEventModal}
<AquaModal onclose={() => showAddEventModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Droplet class="w-5 h-5 text-blue-500" />
			<span class="font-semibold text-gray-800">Add I/O Event</span>
		</div>
	{/snippet}
	<div class="space-y-3">
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Event Type *</div>
			<div class="grid grid-cols-3 gap-1.5">
				{#each Object.entries(ioEventTypes) as [key, cfg]}
					{@const Icon = cfg.icon}
					<button class="py-2 rounded-lg text-xs font-medium cursor-pointer flex items-center justify-center gap-1"
						style="background: {eventType === key ? cfg.textColor.replace('text-', '') === 'green-700' ? '#22c55e' : cfg.textColor.replace('text-', '') === 'amber-700' ? '#f59e0b' : cfg.textColor.replace('text-', '') === 'cyan-700' ? '#06b6d4' : cfg.textColor.replace('text-', '') === 'stone-600' ? '#78716c' : '#8b5cf6' : '#f1f5f9'}; color: {eventType === key ? 'white' : '#64748b'};"
						onclick={() => eventType = key}>
						<Icon class="w-3.5 h-3.5" />
						{cfg.label}
					</button>
				{/each}
			</div>
		</div>
		<div class="grid grid-cols-2 gap-3">
			<div>
				<div class="text-xs font-medium text-gray-600 mb-1">Time *</div>
				<input type="time" bind:value={eventTime} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
					style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
			</div>
			<div>
				<div class="text-xs font-medium text-gray-600 mb-1">Amount (mL)</div>
				<input type="number" bind:value={eventAmount} placeholder="e.g. 500" class="w-full px-3 py-2 rounded-lg text-sm outline-none"
					style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
			</div>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Description</div>
			<input bind:value={eventDesc} placeholder="e.g. NS 0.9% 500 mL" class="w-full px-3 py-2 rounded-lg text-sm outline-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => showAddEventModal = false}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 4px rgba(37,99,235,0.3);"
			onclick={addIOEvent} disabled={eventSubmitting || !eventTime}>
			{eventSubmitting ? 'Adding...' : 'Add Event'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Connect Equipment Modal -->
{#if showEquipModal}
<AquaModal onclose={() => showEquipModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Monitor class="w-5 h-5 text-indigo-500" />
			<span class="font-semibold text-gray-800">Connect Equipment</span>
		</div>
	{/snippet}
	<div class="space-y-3">
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Equipment Type *</div>
			<div class="grid grid-cols-2 gap-1.5">
				{#each ['Bedside Monitor', 'Pulse Oximeter', 'Ventilator', 'ECG Monitor', 'IV Pump', 'ABG Analyzer', 'Glucometer', 'Defibrillator'] as t}
					<button class="py-2 px-3 rounded-lg text-xs font-medium cursor-pointer text-left"
						style="background: {equipType === t ? 'linear-gradient(to bottom, #6366f1, #4f46e5)' : '#f1f5f9'}; color: {equipType === t ? 'white' : '#64748b'};"
						onclick={() => equipType = t}>{t}</button>
				{/each}
			</div>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Equipment ID / Serial (optional)</div>
			<input bind:value={equipId} placeholder="e.g. BM-007" class="w-full px-3 py-2 rounded-lg text-sm outline-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => showEquipModal = false}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #6366f1, #4f46e5); box-shadow: 0 2px 4px rgba(99,102,241,0.3);"
			onclick={connectEquip} disabled={equipSubmitting}>
			{equipSubmitting ? 'Connecting...' : 'Connect'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- SOAP History Modal -->
{#if showSoapHistoryModal}
<AquaModal onclose={() => showSoapHistoryModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<LayoutList class="w-5 h-5 text-blue-600" />
			<span class="font-semibold text-gray-800">SOAP Note History</span>
		</div>
	{/snippet}

	<div class="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
		{#if chronologicalSoapNotes.length > 0}
			{#each chronologicalSoapNotes as note (note.id)}
				<div class="rounded-xl overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
					<div class="px-4 py-3 flex items-center justify-between gap-3" style="background: #eff6ff; border-bottom: 1px solid rgba(0,0,0,0.06);">
						<div>
							<div class="text-xs font-semibold text-gray-800">
								{fmtDate(note.created_at)} · {fmtTime(note.created_at) || '—'}
							</div>
							<div class="text-[10px] text-gray-500">
								{note.note_meta?.author || note.created_by || 'Clinical note'}
							</div>
						</div>
						{#if role === 'STUDENT' || role === 'FACULTY'}
							<button
								onclick={() => { showSoapHistoryModal = false; openEditSoap(note); }}
								class="text-xs text-blue-600 cursor-pointer flex items-center gap-1"
							>
								<Edit class="w-3 h-3" /> Edit
							</button>
						{/if}
					</div>

					<div class="p-4 space-y-3">
						<div>
							<div class="text-[11px] font-bold text-orange-600 mb-1">S — Subjective</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.subjective || 'No subjective notes recorded.'}</p>
						</div>
						<div>
							<div class="text-[11px] font-bold text-blue-600 mb-1">O — Objective</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.objective || 'No objective notes recorded.'}</p>
						</div>
						<div>
							<div class="text-[11px] font-bold text-amber-600 mb-1">A — Assessment</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.assessment || 'No assessment recorded.'}</p>
						</div>
						<div>
							<div class="text-[11px] font-bold text-green-600 mb-1">P — Plan</div>
							<p class="text-xs text-gray-700 leading-relaxed">{note.plan || 'No plan recorded.'}</p>
						</div>
					</div>
				</div>
			{/each}
		{:else}
			<div class="p-6 text-center text-xs text-gray-400">No SOAP notes recorded yet.</div>
		{/if}
	</div>
</AquaModal>
{/if}

<!-- SOAP Note Modal -->
{#if showSoapModal}
<AquaModal onclose={closeSoapModal}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ClipboardList class="w-5 h-5 text-teal-600" />
			<span class="font-semibold text-gray-800">{editSoapId ? 'Edit' : 'New'} SOAP Note</span>
		</div>
	{/snippet}
	<div class="space-y-3">
		<div>
			<div class="text-xs font-bold text-teal-700 mb-1">S — Subjective</div>
			<textarea rows={2} placeholder="Patient-reported symptoms, complaints, history…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f0fdf9; border: 1px solid rgba(13,148,136,0.2);"
				bind:value={soapSubjective}></textarea>
		</div>
		<div>
			<div class="text-xs font-bold text-teal-700 mb-1">O — Objective</div>
			<textarea rows={2} placeholder="Examination findings, vitals, investigation results…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f0fdf9; border: 1px solid rgba(13,148,136,0.2);"
				bind:value={soapObjective}></textarea>
		</div>
		<div>
			<div class="text-xs font-bold text-teal-700 mb-1">A — Assessment</div>
			<textarea rows={2} placeholder="Diagnosis, impression, clinical reasoning…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f0fdf9; border: 1px solid rgba(13,148,136,0.2);"
				bind:value={soapAssessment}></textarea>
		</div>
		<div>
			<div class="text-xs font-bold text-teal-700 mb-1">P — Plan</div>
			<textarea rows={3} placeholder="Treatment plan, medications ordered, follow-up…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f0fdf9; border: 1px solid rgba(13,148,136,0.2);"
				bind:value={soapPlan}></textarea>
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={closeSoapModal}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #0d9488, #0f766e); box-shadow: 0 2px 4px rgba(13,148,136,0.3);"
			onclick={saveSoapNote} disabled={soapSubmitting}>
			{soapSubmitting ? 'Saving...' : 'Save Note'}
		</button>
	</div>
</AquaModal>
{/if}

<!-- Discharge Patient Modal -->
{#if showDischargeModal}
<AquaModal onclose={() => showDischargeModal = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<AlertTriangle class="w-5 h-5 text-red-500" />
			<span class="font-semibold text-gray-800">Discharge Patient</span>
		</div>
	{/snippet}
	<div class="space-y-3">
		<div class="p-3 rounded-xl flex items-start gap-2"
			style="background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.2);">
			<AlertTriangle class="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
			<p class="text-xs text-red-700">This will close the active admission for <strong>{patient?.name}</strong>. This action cannot be undone.</p>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Discharge Summary *</div>
			<textarea rows={4} bind:value={dischargeSummary} placeholder="Summary of hospital course, procedures done, final diagnosis…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);">
			</textarea>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Discharge Instructions</div>
			<textarea rows={2} bind:value={dischargeInstructions} placeholder="Medications to continue, activity restrictions, diet…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);">
			</textarea>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-600 mb-1">Follow-up Date</div>
			<input type="date" bind:value={dischargeFollowUp} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
		</div>
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => showDischargeModal = false}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 2px 4px rgba(239,68,68,0.3);"
			onclick={dischargePatient} disabled={dischargeSubmitting || !dischargeSummary}>
			{dischargeSubmitting ? 'Discharging...' : 'Confirm Discharge'}
		</button>
	</div>
</AquaModal>
{/if}

<style>
@keyframes fadeIn {
	from {
		opacity: 0;
		transform: translate(-50%, calc(-100% - 5px));
	}
	to {
		opacity: 1;
		transform: translate(-50%, -100%);
	}
}
</style>
