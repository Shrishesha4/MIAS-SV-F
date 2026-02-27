<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { Chart, registerables } from 'chart.js';
	import {
		AlertTriangle, FileText, HeartPulse, Pill, Clock, Plus,
		CheckCircle2, ChevronDown, Link2, User, Users,
		Thermometer, Droplet, Activity, Scale, Wind, CircleDot
	} from 'lucide-svelte';

	Chart.register(...registerables);

	let patient: any = $state(null);
	let caseRecords: any[] = $state([]);
	let vitals: any[] = $state([]);
	let medications: any[] = $state([]);
	let prescriptionRequests: any[] = $state([]);
	let loading = $state(true);

	let activeTab = $state('case-records');
	const tabs = [
		{ id: 'case-records', label: 'Case Records', icon: FileText },
		{ id: 'vitals', label: 'Vitals', icon: HeartPulse },
		{ id: 'medications', label: 'Medications', icon: Link2 },
	];

	// Vitals state
	let selectedParameter = $state('bp');
	let selectedTimeRange = $state('30');
	let chartCanvas: HTMLCanvasElement;
	let chartInstance: Chart | null = null;

	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	const vitalCards = $derived(latestVital ? [
		{ icon: HeartPulse, label: 'Blood\nPressure', value: `${latestVital.systolic_bp}/${latestVital.diastolic_bp}`, unit: 'mmHg', color: '#3b82f6' },
		{ icon: Activity, label: 'Heart\nRate', value: `${latestVital.heart_rate}`, unit: 'bpm', color: '#3b82f6' },
		{ icon: Thermometer, label: 'Temperature', value: `${latestVital.temperature?.toFixed(0)}`, unit: '°F', color: '#ef4444' },
		{ icon: Droplet, label: 'Oxygen\nSaturation', value: `${latestVital.oxygen_saturation}`, unit: '%', color: '#3b82f6' },
		{ icon: Wind, label: 'Respiratory\nRate', value: `${latestVital.respiratory_rate}`, unit: 'breaths/min', color: '#22c55e' },
		{ icon: Scale, label: 'Weight', value: `${latestVital.weight?.toFixed(0)}`, unit: 'lbs', color: '#6366f1' },
		{ icon: CircleDot, label: 'Blood\nGlucose', value: `${latestVital.blood_glucose?.toFixed(1)}`, unit: 'mg/dL', color: '#3b82f6' },
	] : []);

	function buildChart() {
		if (!chartCanvas || vitals.length === 0) return;
		chartInstance?.destroy();

		const vitalsSlice = vitals.slice(0, parseInt(selectedTimeRange)).reverse();
		const labels = vitalsSlice.map(v => {
			const d = new Date(v.recorded_at);
			return `${d.getMonth() + 1}/${d.getDate()}`;
		});

		const datasets = selectedParameter === 'bp' ? [
			{ label: 'Systolic', data: vitalsSlice.map(v => v.systolic_bp ?? 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
			{ label: 'Diastolic', data: vitalsSlice.map(v => v.diastolic_bp ?? 0), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
		] : selectedParameter === 'hr' ? [
			{ label: 'Heart Rate', data: vitalsSlice.map(v => v.heart_rate ?? 0), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
		] : [
			{ label: 'SpO₂', data: vitalsSlice.map(v => v.oxygen_saturation ?? 0), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: false, pointRadius: 2 },
		];

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
			selectedParameter; selectedTimeRange;
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

	onMount(async () => {
		try {
			const patientId = page.params.id;
			if (!patientId) return;
			const studentData = await studentApi.getMe();
			const [patientData, caseData, vitalData, rxData] = await Promise.all([
				patientApi.getPatient(patientId),
				studentApi.getCaseRecords(studentData.id),
				patientApi.getVitals(patientId, 30).catch(() => [] as any[]),
				patientApi.getPrescriptions(patientId).catch(() => [] as any[]),
			]);
			patient = patientData;
			caseRecords = caseData;
			vitals = vitalData;
			medications = rxData.flatMap((rx: any) => rx.medications || []);
		} catch (err) {
			console.error('Failed to load patient detail', err);
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
	{:else if !patient}
		<div class="text-center py-12 text-gray-400">
			<p class="text-sm">Patient not found</p>
		</div>
	{:else}
	<!-- Patient Header Card -->
	<AquaCard>
		<div class="flex items-start gap-3">
			<Avatar name={patient.name} size="lg" />
			<div class="flex-1">
				<div class="flex items-center justify-between">
					<h2 class="text-xl font-bold text-gray-800">{patient.name}</h2>
					<span class="text-xs text-gray-400 font-mono">ID: {patient.patient_id}</span>
				</div>
				<p class="text-sm text-gray-500">
					{patient.age}, {patient.gender === 'MALE' ? 'Male' : 'Female'}, Blood: {patient.blood_group}
				</p>
				<p class="text-sm text-gray-500">Contact: {patient.phone}</p>
			</div>
		</div>
	</AquaCard>

	<!-- Medical Alerts -->
	{#if patient.medical_alerts.length > 0}
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
						style="background: rgba(0,0,0,0.08);">
						<Clock class="w-3.5 h-3.5 text-gray-600" />
					</button>
					<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
						style="background: rgba(0,0,0,0.08);">
						<Plus class="w-3.5 h-3.5 text-gray-600" />
					</button>
				</div>
			</div>
			<div class="px-4 pb-2.5 flex flex-wrap gap-2">
				{#each patient.medical_alerts as alert}
					<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-red-700" style="background: rgba(255,255,255,0.5);">
						{alert.title} <span class="text-red-400 cursor-pointer">×</span>
					</span>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Primary Diagnosis -->
	<AquaCard>
		<div class="flex items-center justify-between mb-1">
			<div class="flex items-center gap-2">
				<FileText class="w-4 h-4 text-blue-600" />
				<span class="font-bold text-gray-800">Primary Diagnosis</span>
			</div>
			<div class="flex gap-1.5">
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.06);">
					<Clock class="w-3.5 h-3.5 text-gray-500" />
				</button>
				<button class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
					style="background: rgba(0,0,0,0.06);">
					<Plus class="w-3.5 h-3.5 text-gray-500" />
				</button>
			</div>
		</div>
		<p class="text-sm text-gray-700 mt-1">{patient.primary_diagnosis}</p>
		<p class="text-xs text-gray-400 mt-1">
			Last updated by {patient.diagnosis_doctor} · {patient.diagnosis_date} {patient.diagnosis_time}
		</p>
	</AquaCard>

	<!-- Tabs -->
	<TabBar {tabs} {activeTab} onchange={(id) => activeTab = id} />

	<!-- Tab Content -->
	{#if activeTab === 'case-records'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<FileText class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Case Records</h3>
				</div>
				<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;
					       border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 3px rgba(0,102,204,0.3);">
					<Plus class="w-3 h-3" /> Add Entry
				</button>
			</div>

			<div class="space-y-5">
				{#each caseRecords as record}
					<div class="pb-5 border-b border-gray-100 last:border-0 last:pb-0">
						<!-- Record Header -->
						<div class="flex items-center gap-3 mb-2">
							<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
								style="background: {record.status === 'APPROVED' ? '#22c55e' : '#f97316'};">
								<CheckCircle2 class="w-5 h-5 text-white" />
							</div>
							<div class="flex-1">
								<div class="flex items-center gap-2 flex-wrap">
									<span class="font-semibold text-gray-800">Physical Examination</span>
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

						<!-- Findings Box -->
						<div class="ml-12 p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
							<p class="text-sm text-gray-700"><strong>Findings:</strong> {record.examination}</p>
							<p class="text-sm text-gray-700 mt-1"><strong>Diagnosis:</strong> {record.diagnosis}</p>
							<p class="text-sm text-gray-700 mt-1"><strong>Treatment:</strong> {record.treatment_plan}</p>
						</div>

						<!-- Provider Info -->
						<div class="ml-12 mt-2 flex items-center justify-between text-xs">
							<div class="text-gray-500">
								<div class="flex items-center gap-1">
									<User class="w-3 h-3" /> Provider: {record.provider}
								</div>
								<div class="flex items-center gap-1 mt-0.5">
									<Users class="w-3 h-3" /> Approver: {record.approver}
								</div>
							</div>
							{#if record.approved_at}
								<div class="text-right text-green-600 font-medium">
									<p>{record.date}</p>
									<p>{record.approved_at.split(' ').slice(-2).join(' ')}</p>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</AquaCard>

	{:else if activeTab === 'vitals'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<HeartPulse class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Vitals Tracker</h3>
				</div>
				<div class="flex gap-2">
					<button class="px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #6b7280, #4b5563); color: white;
						       border: 1px solid rgba(0,0,0,0.15);">
						Group View
					</button>
					<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;
						       border: 1px solid rgba(0,0,0,0.15);">
						<Plus class="w-3 h-3" /> Add Reading
					</button>
				</div>
			</div>

			<!-- Selectors -->
			<div class="grid grid-cols-2 gap-3 mb-4">
				<div>
					<label class="text-xs text-gray-500 mb-1 block font-medium">Select Vital Parameter</label>
					<select bind:value={selectedParameter}
						class="w-full px-3 py-2 rounded-lg text-sm bg-white cursor-pointer"
						style="border: 1px solid rgba(0,0,0,0.15);">
						<option value="bp">Blood Pressure (mmHg)</option>
						<option value="hr">Heart Rate (bpm)</option>
						<option value="spo2">SpO₂ (%)</option>
					</select>
				</div>
				<div>
					<label class="text-xs text-gray-500 mb-1 block font-medium">Time Range</label>
					<select bind:value={selectedTimeRange}
						class="w-full px-3 py-2 rounded-lg text-sm bg-white cursor-pointer"
						style="border: 1px solid rgba(0,0,0,0.15);">
						<option value="7">Last 7 days</option>
						<option value="14">Last 14 days</option>
						<option value="30">Last 30 days</option>
					</select>
				</div>
			</div>

			<!-- Chart -->
			<div class="rounded-xl p-3 mb-4" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<HeartPulse class="w-4 h-4 text-blue-600" />
						<div>
							<p class="text-sm font-semibold text-gray-800">
								{selectedParameter === 'bp' ? 'Blood Pressure' : selectedParameter === 'hr' ? 'Heart Rate' : 'SpO₂'}
							</p>
							<p class="text-xs text-gray-400">
								{selectedParameter === 'bp' ? 'Normal range: 120/80 mmHg' : selectedParameter === 'hr' ? 'Normal range: 60-100 bpm' : 'Normal range: 95-100%'}
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

	{:else if activeTab === 'medications'}
		<AquaCard>
			<div class="flex items-center justify-between mb-4">
				<div class="flex items-center gap-2">
					<Link2 class="w-5 h-5 text-blue-600" />
					<h3 class="font-bold text-gray-800">Medications</h3>
				</div>
				<button class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;
					       border: 1px solid rgba(0,0,0,0.15);">
					<Plus class="w-3 h-3" /> Add Prescription
				</button>
			</div>

			<h4 class="text-sm font-semibold text-gray-600 mb-3">Current Medications</h4>
			<div class="space-y-3 mb-6">
				{#each medications as med}
					<div class="p-4 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-start justify-between mb-2">
							<div class="flex items-center gap-2">
								<Link2 class="w-4 h-4 text-gray-500" />
								<span class="font-semibold text-gray-800">{med.name}</span>
							</div>
							<span class="text-xs font-bold px-2 py-0.5 rounded"
								style="background: rgba(34,197,94,0.1); color: #16a34a; border: 1px solid rgba(34,197,94,0.2);">
								{med.status}
							</span>
						</div>
						<div class="grid grid-cols-2 gap-y-1 text-xs ml-6">
							<div>
								<span class="text-gray-500">Frequency:</span>
								<span class="text-gray-700 font-medium"> {med.frequency}</span>
							</div>
							<div class="text-right">
								<span class="text-gray-500">Prescribed by:</span>
								<span class="text-gray-700 font-medium"> {med.prescribed_by}</span>
							</div>
							<div>
								<span class="text-gray-500">Duration:</span>
								<span class="text-gray-700"> {med.start_date} to {med.end_date}</span>
							</div>
							<div class="text-right">
								<span class="text-gray-700 font-medium">{med.department}</span>
							</div>
						</div>
						{#if med.instructions}
							<p class="text-xs text-gray-500 mt-2 ml-6">
								<strong>Instructions:</strong> {med.instructions}
							</p>
						{/if}
					</div>
				{/each}
			</div>

			<h4 class="text-sm font-semibold text-gray-600 mb-3">Prescription Requests</h4>
			<div class="space-y-3">
				{#each prescriptionRequests as req}
					<div class="p-4 rounded-xl" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
						<div class="flex items-start justify-between">
							<div>
								<div class="flex items-center gap-2">
									<Clock class="w-4 h-4 text-orange-500" />
									<span class="font-semibold text-gray-800">Request for {req.medication}</span>
								</div>
								<p class="text-xs text-gray-500 ml-6 mt-1">Requested: {req.requested_date}</p>
								<p class="text-xs text-gray-500 ml-6">Notes: {req.notes}</p>
							</div>
							<div class="text-right shrink-0">
								<span class="text-xs font-bold text-orange-500">{req.status}</span>
								<button class="block mt-1 px-3 py-1 rounded text-xs font-medium cursor-pointer"
									style="background: linear-gradient(to bottom, #1e40af, #1e3a8a); color: white;
									       border: 1px solid rgba(0,0,0,0.15);">
									Respond
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</AquaCard>
	{/if}
	{/if}
</div>
