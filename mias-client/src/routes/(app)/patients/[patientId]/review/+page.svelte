<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		ArrowLeft, Activity, Droplet, Wind, Thermometer, Scale, HeartPulse,
		Plus, Trash2, Edit, ChevronDown, ChevronUp, Monitor, Cpu, X,
		AlertTriangle, Send, ClipboardList, Stethoscope
	} from 'lucide-svelte';

	const patientId = $derived($page.params.patientId);

	// ── Data ──────────────────────────────────────────────────────
	let patient: any = $state(null);
	let admission: any = $state(null);
	let vitals: any[] = $state([]);
	let ioEvents: any[] = $state([]);
	let soapNotes: any[] = $state([]);
	let equipment: any[] = $state([]);
	let loading = $state(true);
	let role = $state('');

	// ── IO Event form ─────────────────────────────────────────────
	let showAddEventModal = $state(false);
	let eventType = $state('IV Input');
	let eventTime = $state('');
	let eventDesc = $state('');
	let eventAmount = $state('');
	let eventSubmitting = $state(false);

	// ── Record Vitals form ────────────────────────────────────────
	let showVitalModal = $state(false);
	let vitalBP = $state('');
	let vitalHR = $state('');
	let vitalRR = $state('');
	let vitalSpO2 = $state('');
	let vitalTemp = $state('');
	let vitalWeight = $state('');
	let vitalGlucose = $state('');
	let vitalSubmitting = $state(false);

	// ── Connect Equipment form ────────────────────────────────────
	let showEquipModal = $state(false);
	let equipType = $state('Bedside Monitor');
	let equipId = $state('');
	let equipSubmitting = $state(false);

	// ── SOAP Note form ────────────────────────────────────────────
	let showSoapModal = $state(false);
	let soapSubjective = $state('');
	let soapObjective = $state('');
	let soapAssessment = $state('');
	let soapPlan = $state('');
	let soapSubmitting = $state(false);
	let editSoapId: string | null = $state(null);
	let expandedSoap: string | null = $state(null);

	// ── Discharge ─────────────────────────────────────────────────
	let showDischargeModal = $state(false);
	let dischargeSummary = $state('');
	let dischargeInstructions = $state('');
	let dischargeFollowUp = $state('');
	let dischargeSubmitting = $state(false);

	// ── Vitals view mode ──────────────────────────────────────────
	let vitalsView = $state<'chart' | 'table'>('table');

	// ── Derived totals (last 24h) ─────────────────────────────────
	const ioTotals = $derived.by(() => {
		const intake = ioEvents
			.filter((e: any) => ['IV Input', 'Food'].includes(e.event_type) && e.amount_ml)
			.reduce((s: number, e: any) => s + (e.amount_ml || 0), 0);
		const output = ioEvents
			.filter((e: any) => ['Urine', 'Stool', 'Drain'].includes(e.event_type) && e.amount_ml)
			.reduce((s: number, e: any) => s + (e.amount_ml || 0), 0);
		return { intake, output, balance: intake - output };
	});

	const eventTypeColor: Record<string, string> = {
		'IV Input': '#3b82f6',
		'Drugs':    '#8b5cf6',
		'Food':     '#22c55e',
		'Urine':    '#f59e0b',
		'Stool':    '#92400e',
		'Drain':    '#ef4444',
	};

	const latestVitals = $derived(vitals[0] ?? null);

	onMount(async () => {
		const auth = get(authStore);
		if (!auth?.accessToken) { goto('/login'); return; }
		role = auth?.role ?? '';

		const pid = get(page).params.patientId!;
		try {
			const [p, admList, vs] = await Promise.all([
				patientApi.getPatient(pid),
				patientApi.getAdmissions(pid),
				patientApi.getVitals(pid, 30),
			]);
			patient = p;
			vitals = vs.sort((a: any, b: any) =>
				new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
			admission = admList.find((a: any) => a.status === 'Active') ?? admList[0] ?? null;

			if (admission) {
				const [evts, notes, equip] = await Promise.all([
					patientApi.getIOEvents(admission.id),
					patientApi.getSOAPNotes(admission.id),
					patientApi.getEquipment(admission.id),
				]);
				ioEvents = evts;
				soapNotes = notes;
				equipment = equip;
			}
		} catch (e) {
			toastStore.addToast('Failed to load admission data', 'error');
		} finally {
			loading = false;
		}
	});

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
			ioEvents = await patientApi.getIOEvents(admission.id);
			showAddEventModal = false;
			eventType = 'IV Input'; eventTime = ''; eventDesc = ''; eventAmount = '';
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
		const pid = patient.id;
		vitalSubmitting = true;
		try {
			const [sys, dia] = vitalBP.split('/').map(Number);
			await patientApi.createVital(pid, {
				systolic_bp: sys || undefined,
				diastolic_bp: dia || undefined,
				heart_rate: vitalHR ? Number(vitalHR) : undefined,
				respiratory_rate: vitalRR ? Number(vitalRR) : undefined,
				temperature: vitalTemp ? Number(vitalTemp) : undefined,
				oxygen_saturation: vitalSpO2 ? Number(vitalSpO2) : undefined,
				weight: vitalWeight ? Number(vitalWeight) : undefined,
				blood_glucose: vitalGlucose ? Number(vitalGlucose) : undefined,
			});
			vitals = (await patientApi.getVitals(pid, 30)).sort((a: any, b: any) =>
				new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
			showVitalModal = false;
			vitalBP = ''; vitalHR = ''; vitalRR = ''; vitalSpO2 = ''; vitalTemp = ''; vitalWeight = ''; vitalGlucose = '';
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
</script>

<!-- ══════════════════════════════════════════════════════════════
     REVIEW & VITALS PAGE
     ══════════════════════════════════════════════════════════════ -->
<div class="min-h-screen" style="background: #e8edf3;">

{#if loading}
	<div class="flex items-center justify-center h-64">
		<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
	</div>
{:else if patient && admission}

<!-- ── Top Header Bar ─────────────────────────────────────────── -->
<div class="sticky top-0 z-30 px-4 py-3 flex items-center gap-3"
	style="background: linear-gradient(to bottom, #1e3a5f, #162d4a); box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
	<button onclick={() => goto('/patients')} class="w-8 h-8 flex items-center justify-center rounded-lg cursor-pointer"
		style="background: rgba(255,255,255,0.1);">
		<ArrowLeft class="w-4 h-4 text-white" />
	</button>
	<Avatar name={patient.name} size="sm" />
	<div class="flex-1 min-w-0">
		<p class="text-sm font-bold text-white truncate">{patient.name}</p>
		<p class="text-[10px] text-blue-200">{patient.patient_id} · {admission.department} · Bed {admission.bed_number || '—'}</p>
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

<!-- ── Admission Snapshot ────────────────────────────────────── -->
<div class="rounded-xl p-3" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Admission Overview</p>
	<div class="grid grid-cols-3 gap-2 text-center">
		<div class="rounded-lg p-2" style="background: rgba(59,130,246,0.06);">
			<p class="text-[9px] text-gray-500">Ward</p>
			<p class="text-xs font-bold text-blue-700">{admission.ward || '—'}</p>
		</div>
		<div class="rounded-lg p-2" style="background: rgba(59,130,246,0.06);">
			<p class="text-[9px] text-gray-500">Bed</p>
			<p class="text-xs font-bold text-blue-700">{admission.bed_number || '—'}</p>
		</div>
		<div class="rounded-lg p-2" style="background: rgba(59,130,246,0.06);">
			<p class="text-[9px] text-gray-500">Day</p>
			<p class="text-xs font-bold text-blue-700">
				{Math.max(1, Math.floor((Date.now() - new Date(admission.admission_date).getTime()) / 86400000) + 1)}
			</p>
		</div>
	</div>
	{#if admission.provisional_diagnosis || admission.diagnosis}
		<div class="mt-2 px-2 py-1.5 rounded-lg" style="background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.12);">
			<p class="text-[9px] text-gray-500 mb-0.5">Provisional Diagnosis</p>
			<p class="text-xs font-semibold text-red-700">{admission.provisional_diagnosis || admission.diagnosis}</p>
		</div>
	{/if}
	{#if admission.attending_doctor}
		<p class="text-[10px] text-gray-500 mt-2">
			Attending: <span class="font-semibold text-gray-700">{admission.attending_doctor}</span>
		</p>
	{/if}
</div>

<!-- ── Vital Trends ─────────────────────────────────────────── -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<HeartPulse class="w-4 h-4 text-red-500" />
			<span class="text-sm font-bold text-gray-800">Vitals</span>
			{#if vitals.length > 0}
				<span class="text-[10px] text-gray-400">{vitals.length} reading{vitals.length !== 1 ? 's' : ''}</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<!-- Chart / Table toggle -->
			<div class="flex rounded-lg overflow-hidden" style="border: 1px solid rgba(0,0,0,0.12);">
				<button class="px-2 py-1 text-[10px] font-medium cursor-pointer"
					style="background: {vitalsView === 'table' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f8faff'}; color: {vitalsView === 'table' ? 'white' : '#64748b'};"
					onclick={() => vitalsView = 'table'}>Table</button>
				<button class="px-2 py-1 text-[10px] font-medium cursor-pointer"
					style="background: {vitalsView === 'chart' ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f8faff'}; color: {vitalsView === 'chart' ? 'white' : '#64748b'};"
					onclick={() => vitalsView = 'chart'}>Trend</button>
			</div>
			{#if role === 'STUDENT' || role === 'FACULTY'}
				<button onclick={() => showVitalModal = true}
					class="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 4px rgba(37,99,235,0.3);">
					<Plus class="w-3.5 h-3.5" /> Record
				</button>
			{/if}
		</div>
	</div>

	{#if vitals.length === 0}
		<div class="p-6 text-center text-xs text-gray-400">No vitals recorded yet.</div>
	{:else if vitalsView === 'table'}
		<!-- Latest vitals card -->
		{#if latestVitals}
			<div class="p-3">
				<p class="text-[9px] text-gray-400 mb-2">Latest — {fmtDate(latestVitals.recorded_at)} {fmtTime(latestVitals.recorded_at)}</p>
				<div class="grid grid-cols-4 gap-2">
					{#each [
						[latestVitals.systolic_bp ? `${latestVitals.systolic_bp}/${latestVitals.diastolic_bp}` : null, 'BP', 'mmHg', '#ef4444'],
						[latestVitals.heart_rate, 'HR', 'bpm', '#f97316'],
						[latestVitals.oxygen_saturation, 'SpO₂', '%', '#3b82f6'],
						[latestVitals.temperature, 'Temp', '°F', '#8b5cf6'],
						[latestVitals.respiratory_rate, 'RR', '/min', '#06b6d4'],
						[latestVitals.weight, 'Wt', 'kg', '#22c55e'],
						[latestVitals.blood_glucose, 'CBG', 'mg/dL', '#f59e0b'],
					] as [val, lbl, unit, color]}
						{#if val !== null && val !== undefined}
							<div class="rounded-lg p-2 text-center col-span-1"
								style="background: {color}10; border: 1px solid {color}25;">
								<p class="text-[9px] font-medium" style="color: {color};">{lbl}</p>
								<p class="text-sm font-bold" style="color: {color};">{val}</p>
								<p class="text-[8px] text-gray-400">{unit}</p>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		{/if}
		<!-- History table -->
		{#if vitals.length > 1}
			<div class="overflow-x-auto" style="border-top: 1px solid rgba(0,0,0,0.06);">
				<table class="w-full text-[10px]">
					<thead>
						<tr style="background: #f8faff;">
							<th class="text-left px-3 py-2 font-medium text-gray-500">Date</th>
							<th class="text-right px-2 py-2 font-medium text-gray-500">BP</th>
							<th class="text-right px-2 py-2 font-medium text-gray-500">HR</th>
							<th class="text-right px-2 py-2 font-medium text-gray-500">SpO₂</th>
							<th class="text-right px-2 py-2 font-medium text-gray-500">Temp</th>
						</tr>
					</thead>
					<tbody>
						{#each vitals.slice(0, 10) as v}
							<tr style="border-top: 1px solid rgba(0,0,0,0.04);">
								<td class="px-3 py-2 text-gray-500">{fmtDate(v.recorded_at)}</td>
								<td class="px-2 py-2 text-right font-medium text-gray-700">
									{v.systolic_bp ? `${v.systolic_bp}/${v.diastolic_bp}` : '—'}
								</td>
								<td class="px-2 py-2 text-right font-medium text-gray-700">{v.heart_rate ?? '—'}</td>
								<td class="px-2 py-2 text-right font-medium text-gray-700">{v.oxygen_saturation ?? '—'}</td>
								<td class="px-2 py-2 text-right font-medium text-gray-700">{v.temperature ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{:else}
		<!-- Sparkline trend: HR over time -->
		<div class="p-3">
			<p class="text-[10px] text-gray-500 mb-2">Heart Rate trend (last {Math.min(vitals.length, 10)} readings)</p>
			<div class="flex items-end gap-1 h-16">
				{#each vitals.slice(0, 10).reverse() as v, i}
					{@const hr = v.heart_rate ?? 72}
					{@const pct = Math.min(100, Math.max(20, ((hr - 40) / 120) * 100))}
					<div class="flex-1 flex flex-col items-center gap-0.5">
						<div class="w-full rounded-sm"
							style="height: {pct}%; background: linear-gradient(to top, #3b82f6, #93c5fd); min-height: 4px; max-height: 48px;">
						</div>
						<span class="text-[8px] text-gray-400">{hr}</span>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<!-- ── I/O Events ────────────────────────────────────────────── -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<Droplet class="w-4 h-4 text-blue-500" />
			<span class="text-sm font-bold text-gray-800">I/O Events</span>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => showAddEventModal = true}
				class="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 4px rgba(37,99,235,0.3);">
				<Plus class="w-3.5 h-3.5" /> Add
			</button>
		{/if}
	</div>

	<!-- 24-hr totals bar -->
	<div class="grid grid-cols-3 gap-0" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="py-3 text-center" style="border-right: 1px solid rgba(0,0,0,0.06);">
			<p class="text-[9px] text-gray-500">Total Intake</p>
			<p class="text-sm font-bold text-blue-600">{ioTotals.intake} mL</p>
		</div>
		<div class="py-3 text-center" style="border-right: 1px solid rgba(0,0,0,0.06);">
			<p class="text-[9px] text-gray-500">Total Output</p>
			<p class="text-sm font-bold text-amber-600">{ioTotals.output} mL</p>
		</div>
		<div class="py-3 text-center">
			<p class="text-[9px] text-gray-500">Balance</p>
			<p class="text-sm font-bold" style="color: {ioTotals.balance >= 0 ? '#22c55e' : '#ef4444'};">
				{ioTotals.balance > 0 ? '+' : ''}{ioTotals.balance} mL
			</p>
		</div>
	</div>

	{#if ioEvents.length === 0}
		<div class="p-6 text-center text-xs text-gray-400">No events recorded yet.</div>
	{:else}
		<div class="divide-y divide-gray-50 max-h-64 overflow-y-auto">
			{#each ioEvents as ev}
				<div class="flex items-center gap-3 px-4 py-2.5">
					<!-- type indicator -->
					<div class="w-2.5 h-2.5 rounded-full shrink-0"
						style="background: {eventTypeColor[ev.event_type] ?? '#94a3b8'};"></div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-1.5">
							<span class="text-[10px] font-bold" style="color: {eventTypeColor[ev.event_type] ?? '#64748b'};">
								{ev.event_type}
							</span>
							{#if ev.amount_ml}
								<span class="text-[9px] text-gray-400">{ev.amount_ml} mL</span>
							{/if}
						</div>
						<p class="text-xs text-gray-700 truncate">{ev.description || '—'}</p>
						<p class="text-[9px] text-gray-400">{ev.event_time} · {ev.recorded_by || 'Staff'}</p>
					</div>
					{#if role === 'STUDENT' || role === 'FACULTY'}
						<button onclick={() => removeIOEvent(ev.id)} class="p-1 rounded cursor-pointer hover:text-red-500 text-gray-300">
							<Trash2 class="w-3 h-3" />
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- ── Connected Equipment ───────────────────────────────────── -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<Monitor class="w-4 h-4 text-indigo-500" />
			<span class="text-sm font-bold text-gray-800">Equipment</span>
			<span class="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
				style="background: rgba(34,197,94,0.1); color: #16a34a;">{equipment.length} connected</span>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => showEquipModal = true}
				class="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #6366f1, #4f46e5); box-shadow: 0 2px 4px rgba(79,70,229,0.3);">
				<Plus class="w-3.5 h-3.5" /> Connect
			</button>
		{/if}
	</div>

	{#if equipment.length === 0}
		<div class="p-6 text-center text-xs text-gray-400">No equipment connected.</div>
	{:else}
		<div class="p-3 space-y-2">
			{#each equipment as eq}
				<div class="flex items-center gap-3 p-3 rounded-xl"
					style="background: rgba(99,102,241,0.04); border: 1px solid rgba(99,102,241,0.12);">
					<div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
						style="background: linear-gradient(to bottom, #6366f1, #4f46e5);">
						<Cpu class="w-4 h-4 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-1.5">
							<p class="text-xs font-bold text-gray-800">{eq.equipment_type}</p>
							<span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
							<span class="text-[9px] text-green-600 font-medium">Active</span>
						</div>
						{#if eq.equipment_id}
							<p class="text-[10px] text-gray-500">ID: {eq.equipment_id}</p>
						{/if}
						{#if eq.connected_since}
							<p class="text-[9px] text-gray-400">Since {eq.connected_since}</p>
						{/if}
					</div>
					{#if role === 'STUDENT' || role === 'FACULTY'}
						<button onclick={() => disconnectEquip(eq.id)}
							class="text-[10px] font-medium px-2 py-1 rounded-lg cursor-pointer"
							style="background: rgba(239,68,68,0.08); color: #dc2626; border: 1px solid rgba(239,68,68,0.2);">
							Disconnect
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- ── SOAP Notes ────────────────────────────────────────────── -->
<div class="rounded-xl overflow-hidden" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
	<div class="px-4 py-3 flex items-center justify-between" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
		<div class="flex items-center gap-2">
			<ClipboardList class="w-4 h-4 text-teal-600" />
			<span class="text-sm font-bold text-gray-800">SOAP Notes</span>
		</div>
		{#if role === 'STUDENT' || role === 'FACULTY'}
			<button onclick={() => { editSoapId = null; soapSubjective=''; soapObjective=''; soapAssessment=''; soapPlan=''; showSoapModal = true; }}
				class="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #0d9488, #0f766e); box-shadow: 0 2px 4px rgba(13,148,136,0.3);">
				<Plus class="w-3.5 h-3.5" /> New Note
			</button>
		{/if}
	</div>

	{#if soapNotes.length === 0}
		<div class="p-6 text-center text-xs text-gray-400">No SOAP notes yet.</div>
	{:else}
		<div class="divide-y divide-gray-50">
			{#each soapNotes as note}
				<div>
					<!-- Accordion header -->
					<button class="w-full flex items-center gap-3 px-4 py-3 cursor-pointer text-left"
						onclick={() => expandedSoap = expandedSoap === note.id ? null : note.id}>
						<Stethoscope class="w-4 h-4 text-teal-500 shrink-0" />
						<div class="flex-1 min-w-0">
							<p class="text-xs font-semibold text-gray-800 truncate">
								{note.assessment || 'SOAP Note'}
							</p>
							<p class="text-[10px] text-gray-400">{fmtDate(note.created_at)} {fmtTime(note.created_at)}</p>
						</div>
						{#if expandedSoap === note.id}
							<ChevronUp class="w-3.5 h-3.5 text-gray-400 shrink-0" />
						{:else}
							<ChevronDown class="w-3.5 h-3.5 text-gray-400 shrink-0" />
						{/if}
					</button>
					{#if expandedSoap === note.id}
						<div class="px-4 pb-4 space-y-2">
							{#each [['S — Subjective', note.subjective], ['O — Objective', note.objective], ['A — Assessment', note.assessment], ['P — Plan', note.plan]] as [lbl, val]}
								{#if val}
									<div>
										<p class="text-[9px] font-bold text-teal-700 uppercase tracking-wide mb-0.5">{lbl}</p>
										<p class="text-xs text-gray-700 leading-relaxed">{val}</p>
									</div>
								{/if}
							{/each}
							{#if role === 'STUDENT' || role === 'FACULTY'}
								<button onclick={() => openEditSoap(note)}
									class="flex items-center gap-1 text-[10px] font-medium text-blue-600 cursor-pointer mt-1">
									<Edit class="w-3 h-3" /> Edit Note
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- ── Discharge Patient ─────────────────────────────────────── -->
{#if (role === 'FACULTY' || role === 'STUDENT') && admission.status === 'Active'}
	<button onclick={() => showDischargeModal = true}
		class="w-full py-3 rounded-xl text-sm font-bold text-white cursor-pointer"
		style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 3px 8px rgba(239,68,68,0.4);">
		Discharge Patient
	</button>
{/if}

</div> <!-- /px-4 py-4 -->

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
	<div class="grid grid-cols-2 gap-3">
		{#each [
			['BP (mmHg)', vitalBP, 'e.g. 120/80'],
			['Heart Rate (bpm)', vitalHR, 'e.g. 76'],
			['Resp. Rate (/min)', vitalRR, 'e.g. 18'],
			['SpO₂ (%)', vitalSpO2, 'e.g. 98'],
			['Temperature (°F)', vitalTemp, 'e.g. 98.6'],
			['Weight (kg)', vitalWeight, 'e.g. 72'],
			['Blood Glucose (mg/dL)', vitalGlucose, 'e.g. 110'],
		] as [label, val, ph]}
			<div>
				<label class="block text-xs font-medium text-gray-600 mb-1">{label}</label>
				{#if label.startsWith('BP')}
					<input bind:value={vitalBP} placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else if label.startsWith('Heart')}
					<input bind:value={vitalHR} type="number" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else if label.startsWith('Resp')}
					<input bind:value={vitalRR} type="number" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else if label.startsWith('SpO')}
					<input bind:value={vitalSpO2} type="number" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else if label.startsWith('Temp')}
					<input bind:value={vitalTemp} type="number" step="0.1" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else if label.startsWith('Weight')}
					<input bind:value={vitalWeight} type="number" step="0.1" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{:else}
					<input bind:value={vitalGlucose} type="number" placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
						style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
				{/if}
			</div>
		{/each}
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => showVitalModal = false}>Cancel</button>
		<button class="px-5 py-2 rounded-lg text-sm font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 2px 4px rgba(239,68,68,0.3);"
			onclick={submitVital} disabled={vitalSubmitting}>
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
			<label class="block text-xs font-medium text-gray-600 mb-1">Event Type *</label>
			<div class="grid grid-cols-3 gap-1.5">
				{#each ['IV Input', 'Drugs', 'Food', 'Urine', 'Stool', 'Drain'] as t}
					<button class="py-2 rounded-lg text-xs font-medium cursor-pointer"
						style="background: {eventType === t ? eventTypeColor[t] : '#f1f5f9'}; color: {eventType === t ? 'white' : '#64748b'};"
						onclick={() => eventType = t}>{t}</button>
				{/each}
			</div>
		</div>
		<div class="grid grid-cols-2 gap-3">
			<div>
				<label class="block text-xs font-medium text-gray-600 mb-1">Time *</label>
				<input type="time" bind:value={eventTime} class="w-full px-3 py-2 rounded-lg text-sm outline-none"
					style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-600 mb-1">Amount (mL)</label>
				<input type="number" bind:value={eventAmount} placeholder="e.g. 500" class="w-full px-3 py-2 rounded-lg text-sm outline-none"
					style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);" />
			</div>
		</div>
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Description</label>
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
			<label class="block text-xs font-medium text-gray-600 mb-1">Equipment Type *</label>
			<div class="grid grid-cols-2 gap-1.5">
				{#each ['Bedside Monitor', 'Pulse Oximeter', 'Ventilator', 'ECG Monitor', 'IV Pump', 'ABG Analyzer', 'Glucometer', 'Defibrillator'] as t}
					<button class="py-2 px-3 rounded-lg text-xs font-medium cursor-pointer text-left"
						style="background: {equipType === t ? 'linear-gradient(to bottom, #6366f1, #4f46e5)' : '#f1f5f9'}; color: {equipType === t ? 'white' : '#64748b'};"
						onclick={() => equipType = t}>{t}</button>
				{/each}
			</div>
		</div>
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Equipment ID / Serial (optional)</label>
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

<!-- SOAP Note Modal -->
{#if showSoapModal}
<AquaModal onclose={() => { showSoapModal = false; editSoapId = null; }}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ClipboardList class="w-5 h-5 text-teal-600" />
			<span class="font-semibold text-gray-800">{editSoapId ? 'Edit' : 'New'} SOAP Note</span>
		</div>
	{/snippet}
	<div class="space-y-3">
		{#each [
			['S — Subjective', 'soapSubjective', 'Patient-reported symptoms, complaints, history…', 2] as [string, string, string, number],
			['O — Objective', 'soapObjective', 'Examination findings, vitals, investigation results…', 2] as [string, string, string, number],
			['A — Assessment', 'soapAssessment', 'Diagnosis, impression, clinical reasoning…', 2] as [string, string, string, number],
			['P — Plan', 'soapPlan', 'Treatment plan, medications ordered, follow-up…', 3] as [string, string, string, number],
		] as [lbl, field, ph, rows]}
			<div>
				<label class="block text-xs font-bold text-teal-700 mb-1">{lbl}</label>
				<textarea {rows} placeholder={ph} class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
					style="background: #f0fdf9; border: 1px solid rgba(13,148,136,0.2);"
					value={field === 'soapSubjective' ? soapSubjective : field === 'soapObjective' ? soapObjective : field === 'soapAssessment' ? soapAssessment : soapPlan}
					oninput={(e) => {
						const v = (e.target as HTMLTextAreaElement).value;
						if (field === 'soapSubjective') soapSubjective = v;
						else if (field === 'soapObjective') soapObjective = v;
						else if (field === 'soapAssessment') soapAssessment = v;
						else soapPlan = v;
					}}
				></textarea>
			</div>
		{/each}
	</div>
	<div class="flex justify-end gap-2 mt-5">
		<button class="px-4 py-2 rounded-lg text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);"
			onclick={() => { showSoapModal = false; editSoapId = null; }}>Cancel</button>
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
			<label class="block text-xs font-medium text-gray-600 mb-1">Discharge Summary *</label>
			<textarea rows={4} bind:value={dischargeSummary} placeholder="Summary of hospital course, procedures done, final diagnosis…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);">
			</textarea>
		</div>
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Discharge Instructions</label>
			<textarea rows={2} bind:value={dischargeInstructions} placeholder="Medications to continue, activity restrictions, diet…"
				class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-none"
				style="background: #f8faff; border: 1px solid rgba(0,0,0,0.15);">
			</textarea>
		</div>
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Follow-up Date</label>
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
