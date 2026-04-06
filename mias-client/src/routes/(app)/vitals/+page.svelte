<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { Chart, registerables } from 'chart.js';
	import { patientApi } from '$lib/api/patients';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import {
		Activity, HeartPulse, Thermometer, Droplet, Scale,
		Plus, ChevronDown, Download, Wind
	} from 'lucide-svelte';

	Chart.register(...registerables);

	let detailChartCanvas: HTMLCanvasElement | undefined = $state();
	let detailChart: Chart | null = null;

	let vitals: any[] = $state([]);
	let loading = $state(true);
	let patientId = $state('');

	// Selected vital for detail view
	let activeVitalId = $state<string | null>(null);
	let timeRange = $state('30');
	let showRawData = $state(false);
	let showSecondary = $state(false);

	// Add vital modal
	let showAddModal = $state(false);
	let addVitalType = $state('');
	let addVitalValue = $state('');
	let addVitalValue2 = $state(''); // for diastolic BP
	let addingVital = $state(false);

	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	interface VitalDef {
		id: string;
		label: string;
		icon: typeof HeartPulse;
		unit: string;
		normal: string;
		color: string;
		getValue: (v: any) => string;
		getNumeric: (v: any) => number | null;
		isWarning: (v: any) => boolean;
	}

	const primaryVitalDefs: VitalDef[] = [
		{
			id: 'bloodPressure', label: 'Blood Pressure', icon: HeartPulse, unit: 'mmHg',
			normal: '120/80', color: '#8884d8',
			getValue: (v) => `${v.systolic_bp ?? '--'}/${v.diastolic_bp ?? '--'}`,
			getNumeric: (v) => v.systolic_bp,
			isWarning: (v) => (v.systolic_bp ?? 0) > 130 || (v.diastolic_bp ?? 0) > 90,
		},
		{
			id: 'heartRate', label: 'Heart Rate', icon: Activity, unit: 'bpm',
			normal: '60-100', color: '#ff7300',
			getValue: (v) => `${v.heart_rate ?? '--'}`,
			getNumeric: (v) => v.heart_rate,
			isWarning: (v) => (v.heart_rate ?? 0) < 60 || (v.heart_rate ?? 0) > 100,
		},
		{
			id: 'oxygenSaturation', label: 'SpO₂', icon: Droplet, unit: '%',
			normal: '95-100', color: '#0088fe',
			getValue: (v) => `${v.oxygen_saturation ?? '--'}`,
			getNumeric: (v) => v.oxygen_saturation,
			isWarning: (v) => (v.oxygen_saturation ?? 0) < 95,
		},
		{
			id: 'temperature', label: 'Temperature', icon: Thermometer, unit: '°F',
			normal: '97.8-99.1', color: '#ff4d4f',
			getValue: (v) => `${v.temperature?.toFixed(1) ?? '--'}`,
			getNumeric: (v) => v.temperature,
			isWarning: (v) => (v.temperature ?? 0) > 99.1 || (v.temperature ?? 0) < 97.8,
		},
	];

	const secondaryVitalDefs: VitalDef[] = [
		{
			id: 'respiratoryRate', label: 'Respiratory Rate', icon: Wind, unit: 'breaths/min',
			normal: '12-20', color: '#8dd1e1',
			getValue: (v) => `${v.respiratory_rate ?? '--'}`,
			getNumeric: (v) => v.respiratory_rate,
			isWarning: (v) => (v.respiratory_rate ?? 0) < 12 || (v.respiratory_rate ?? 0) > 20,
		},
		{
			id: 'weight', label: 'Weight', icon: Scale, unit: 'lbs',
			normal: 'Varies', color: '#a4de6c',
			getValue: (v) => `${v.weight?.toFixed(1) ?? '--'}`,
			getNumeric: (v) => v.weight,
			isWarning: () => false,
		},
		{
			id: 'bloodGlucose', label: 'Blood Glucose', icon: Droplet, unit: 'mg/dL',
			normal: '70-99', color: '#d0ed57',
			getValue: (v) => `${v.blood_glucose ?? '--'}`,
			getNumeric: (v) => v.blood_glucose,
			isWarning: (v) => (v.blood_glucose ?? 0) > 120 || (v.blood_glucose ?? 0) < 70,
		},
	];

	const allVitalDefs = $derived([...primaryVitalDefs, ...secondaryVitalDefs]);

	const selectedVital = $derived(activeVitalId ? allVitalDefs.find(v => v.id === activeVitalId) ?? null : null);

	const rangeNum = $derived(parseInt(timeRange));
	const filteredVitals = $derived(vitals.slice(0, rangeNum).reverse());

	function buildDetailChart() {
		detailChart?.destroy();
		detailChart = null;
		if (!detailChartCanvas || !selectedVital || filteredVitals.length === 0) return;

		const labels = filteredVitals.map(v => {
			const d = new Date(v.recorded_at);
			if (rangeNum <= 30) return `${d.getMonth() + 1}/${d.getDate()}`;
			if (rangeNum <= 90) return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
			return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
		});

		const datasets: any[] = [];

		if (selectedVital.id === 'bloodPressure') {
			datasets.push(
				{
					label: 'Systolic',
					data: filteredVitals.map(v => v.systolic_bp ?? 0),
					borderColor: '#8884d8',
					backgroundColor: 'rgba(136, 132, 216, 0.1)',
					tension: 0.4, fill: true, pointRadius: rangeNum <= 14 ? 3 : 0,
				},
				{
					label: 'Diastolic',
					data: filteredVitals.map(v => v.diastolic_bp ?? 0),
					borderColor: '#82ca9d',
					backgroundColor: 'rgba(130, 202, 157, 0.1)',
					tension: 0.4, fill: true, pointRadius: rangeNum <= 14 ? 3 : 0,
				}
			);
		} else {
			datasets.push({
				label: selectedVital.label,
				data: filteredVitals.map(v => selectedVital.getNumeric(v) ?? 0),
				borderColor: selectedVital.color,
				backgroundColor: selectedVital.color + '1a',
				tension: 0.4, fill: true, pointRadius: rangeNum <= 14 ? 3 : 0,
			});
		}

		detailChart = new Chart(detailChartCanvas, {
			type: 'line',
			data: { labels, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
				},
				scales: {
					y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' } },
					x: { grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: rangeNum <= 30 ? 7 : 10 } },
				},
			},
		});
	}

	function exportCSV() {
		if (!selectedVital) return;
		let csv = '';
		if (selectedVital.id === 'bloodPressure') {
			csv = 'Date,Systolic (mmHg),Diastolic (mmHg)\n';
			filteredVitals.forEach(v => {
				csv += `${new Date(v.recorded_at).toLocaleDateString()},${v.systolic_bp},${v.diastolic_bp}\n`;
			});
		} else {
			csv = `Date,${selectedVital.label} (${selectedVital.unit})\n`;
			filteredVitals.forEach(v => {
				csv += `${new Date(v.recorded_at).toLocaleDateString()},${selectedVital.getNumeric(v)}\n`;
			});
		}
		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${selectedVital.label}_data.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	async function handleAddVital() {
		if (!addVitalType || !addVitalValue || !patientId) return;
		addingVital = true;
		try {
			const vitalData: any = {};
			const val = parseFloat(addVitalValue);
			switch (addVitalType) {
				case 'bloodPressure':
					vitalData.systolic_bp = val;
					vitalData.diastolic_bp = parseFloat(addVitalValue2) || 80;
					break;
				case 'heartRate': vitalData.heart_rate = val; break;
				case 'oxygenSaturation': vitalData.oxygen_saturation = val; break;
				case 'temperature': vitalData.temperature = val; break;
				case 'respiratoryRate': vitalData.respiratory_rate = val; break;
				case 'weight': vitalData.weight = val; break;
				case 'bloodGlucose': vitalData.blood_glucose = val; break;
			}
			await patientApi.createVital(patientId, vitalData);
			vitals = await patientApi.getVitals(patientId, 365);
			showAddModal = false;
			addVitalType = '';
			addVitalValue = '';
			addVitalValue2 = '';
		} catch (err) {
			toastStore.addToast('Failed to add vital', 'error');
		} finally {
			addingVital = false;
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['PATIENT'])) return;
		try {
			const patient = await patientApi.getCurrentPatient();
			patientId = patient.id;
			vitals = await patientApi.getVitals(patient.id, 365);
		} catch (err) {
			toastStore.addToast('Failed to load vitals', 'error');
		} finally {
			loading = false;
		}
	});

	$effect(() => {
		if (activeVitalId && detailChartCanvas && filteredVitals.length > 0) {
			buildDetailChart();
		}
	});

	// Rebuild chart when timeRange changes
	$effect(() => {
		timeRange;
		if (activeVitalId && detailChartCanvas) {
			buildDetailChart();
		}
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !latestVital}
		<div class="text-center py-12 text-gray-400">
			<HeartPulse class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No vitals data available</p>
		</div>
	{:else}
	<!-- Header -->
	<div class="flex items-center justify-between">
		<h1 class="text-xl font-semibold text-blue-900">Vitals Tracker</h1>
		<button
			onclick={() => showAddModal = true}
			class="flex items-center px-3 py-1.5 text-sm font-medium text-white rounded-lg cursor-pointer"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
			<Plus class="w-4 h-4 mr-1" />
			Add Reading
		</button>
	</div>

	<!-- Primary Vitals Grid -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
		{#each primaryVitalDefs as vital}
			{@const isActive = activeVitalId === vital.id}
			{@const warn = latestVital ? vital.isWarning(latestVital) : false}
			<button
				class="p-3 rounded-xl text-left cursor-pointer transition-all"
				style="background-color: white; background-image: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(245,245,245,0.8));
				       box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				       border: {isActive ? '2px solid #3b82f6' : '1px solid rgba(0,0,0,0.1)'};"
				onclick={() => activeVitalId = activeVitalId === vital.id ? null : vital.id}
			>
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<div class="w-7 h-7 rounded-full flex items-center justify-center"
							style="background: linear-gradient(to bottom, {warn ? '#ff3b30, #d70015' : '#4d90fe, #0066cc'}); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
							<vital.icon class="w-3.5 h-3.5 text-white" />
						</div>
						<span class="font-medium text-gray-800 text-sm">{vital.label}</span>
					</div>
				</div>
				<div class="flex items-baseline justify-between">
					<div>
						<span class="text-xl font-bold text-gray-900">{vital.getValue(latestVital)}</span>
						<span class="text-sm font-normal text-gray-500 ml-1">{vital.unit}</span>
					</div>
					<span class="text-xs text-gray-400">{vital.normal}</span>
				</div>
			</button>
		{/each}
	</div>

	<!-- Secondary Vitals Dropdown -->
	<div class="rounded-xl overflow-hidden"
		style="background-color: white; background-image: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(245,245,245,0.8));
		       box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1);">
		<button
			class="w-full p-4 flex justify-between items-center cursor-pointer"
			style={showSecondary ? 'border-bottom: 1px solid rgba(0,0,0,0.1);' : ''}
			onclick={() => showSecondary = !showSecondary}>
			<span class="font-medium text-gray-800">Other Vital Signs</span>
			<ChevronDown class="w-5 h-5 text-gray-400 transition-transform {showSecondary ? 'rotate-180' : ''}" />
		</button>
		{#if showSecondary}
			<div class="px-4 pb-4 space-y-3 pt-3">
				{#each secondaryVitalDefs as vital}
					{@const isActive = activeVitalId === vital.id}
					{@const warn = latestVital ? vital.isWarning(latestVital) : false}
					<button
						class="w-full rounded-lg p-3 cursor-pointer flex items-center justify-between"
						style="background-color: rgba(245,245,245,0.8); box-shadow: 0 1px 3px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.7);
						       border: {isActive ? '2px solid #3b82f6' : '1px solid rgba(0,0,0,0.1)'};"
						onclick={() => activeVitalId = activeVitalId === vital.id ? null : vital.id}
					>
						<div class="flex items-center gap-2">
							<div class="w-6 h-6 rounded-full flex items-center justify-center"
								style="background: linear-gradient(to bottom, {warn ? '#ff3b30, #d70015' : '#4d90fe, #0066cc'}); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
								<vital.icon class="w-3 h-3 text-white" />
							</div>
							<span class="font-medium text-gray-800 text-sm">{vital.label}</span>
						</div>
						<div>
							<span class="text-lg font-semibold text-gray-900">{vital.getValue(latestVital)}</span>
							<span class="text-xs font-normal text-gray-500 ml-1">{vital.unit}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Detailed Chart Section -->
	{#if selectedVital}
		<div class="rounded-xl overflow-hidden"
			style="background-color: white; background-image: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(245,245,245,0.8));
			       box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1);">
			<!-- Blue Header -->
			<div class="p-4"
				style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: inset 0 1px 0 rgba(255,255,255,0.4); border-bottom: 1px solid rgba(0,0,0,0.2);">
				<div class="flex justify-between items-center">
					<div class="flex items-center gap-3">
						<div class="w-8 h-8 rounded-full flex items-center justify-center"
							style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.3); border: 1px solid rgba(0,0,0,0.2);">
							<selectedVital.icon class="w-4 h-4 text-blue-600" />
						</div>
						<div>
							<h3 class="font-medium text-white">{selectedVital.label}</h3>
							<p class="text-xs text-blue-100">Normal: {selectedVital.normal} {selectedVital.unit}</p>
						</div>
					</div>
					<div class="flex items-center gap-2">
						<div style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem;">
							<select class="text-sm px-2 py-1 bg-transparent outline-none text-gray-700" bind:value={timeRange}>
								<option value="7">7 days</option>
								<option value="14">14 days</option>
								<option value="30">30 days</option>
								<option value="90">3 months</option>
								<option value="180">6 months</option>
								<option value="365">1 year</option>
							</select>
						</div>
						<button
							onclick={exportCSV}
							class="p-1.5 rounded-full cursor-pointer"
							title="Export CSV"
							style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);">
							<Download class="w-4 h-4 text-blue-700" />
						</button>
					</div>
				</div>
			</div>
			<!-- Chart -->
			<div class="p-4">
				<div class="h-56">
					<canvas bind:this={detailChartCanvas}></canvas>
				</div>
				<!-- Toggle Raw Data -->
				<div class="mt-4 flex justify-center">
					<button
						class="text-sm text-blue-600 flex items-center px-3 py-1 rounded-full cursor-pointer"
						onclick={() => showRawData = !showRawData}
						style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);">
						{showRawData ? 'Hide' : 'Show'} Raw Data
						<ChevronDown class="w-4 h-4 ml-1 transition-transform {showRawData ? 'rotate-180' : ''}" />
					</button>
				</div>
				<!-- Raw Data Table -->
				{#if showRawData}
					<div class="mt-3 rounded-lg overflow-hidden" style="border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
						<div class="max-h-64 overflow-y-auto">
							<table class="min-w-full divide-y divide-gray-200">
								<thead class="sticky top-0" style="background-image: linear-gradient(to bottom, #f0f4fa, #d5dde8);">
									<tr>
										<th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
										{#if selectedVital.id === 'bloodPressure'}
											<th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sys</th>
											<th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Dia</th>
										{:else}
											<th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{selectedVital.label}</th>
										{/if}
									</tr>
								</thead>
								<tbody class="divide-y divide-gray-200">
									{#each filteredVitals as row, i}
										<tr style="background-color: {i % 2 === 0 ? 'white' : 'rgba(249,250,251,0.7)'};">
											<td class="px-4 py-2 text-sm text-gray-500">{new Date(row.recorded_at).toLocaleDateString()}</td>
											{#if selectedVital.id === 'bloodPressure'}
												<td class="px-4 py-2 text-sm font-medium text-gray-900">{row.systolic_bp}</td>
												<td class="px-4 py-2 text-sm font-medium text-gray-900">{row.diastolic_bp}</td>
											{:else}
												<td class="px-4 py-2 text-sm font-medium text-gray-900">{selectedVital.getNumeric(row) ?? '--'}</td>
											{/if}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Recent Readings -->
	<AquaCard>
		{#snippet header()}
			<span class="text-blue-900 font-semibold text-sm">Recent Readings</span>
		{/snippet}
		<div class="space-y-2 max-h-64 overflow-y-auto">
			{#each vitals.slice(0, 5) as vital}
				<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
					<div>
						<p class="text-xs text-gray-500">
							{new Date(vital.recorded_at).toLocaleDateString('en-IN', {
								day: 'numeric', month: 'short', year: 'numeric'
							})}
						</p>
						<p class="text-sm text-gray-700">
							BP: {vital.systolic_bp}/{vital.diastolic_bp} · HR: {vital.heart_rate} · SpO₂: {vital.oxygen_saturation}%
						</p>
					</div>
					{#if (vital.systolic_bp ?? 0) > 130}
						<StatusBadge variant="warning">Elevated</StatusBadge>
					{:else}
						<StatusBadge variant="normal">Normal</StatusBadge>
					{/if}
				</div>
			{/each}
		</div>
	</AquaCard>

	<!-- Add Vital Reading Modal -->
	{#if showAddModal}
		<AquaModal title="Add Vital Reading" onclose={() => showAddModal = false}>
			<div class="space-y-4">
				<div>
					<label for="vital-type" class="block text-sm font-medium text-gray-700 mb-1">Vital Sign</label>
					<div style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem;">
						<select id="vital-type" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700" bind:value={addVitalType}>
							<option value="">Select vital sign</option>
							{#each allVitalDefs as v}
								<option value={v.id}>{v.label}</option>
							{/each}
						</select>
					</div>
				</div>
				{#if addVitalType}
					<div>
						<label for="vital-val" class="block text-sm font-medium text-gray-700 mb-1">
							{addVitalType === 'bloodPressure' ? 'Systolic (mmHg)' : (allVitalDefs.find(v => v.id === addVitalType)?.label ?? 'Value')}
						</label>
						<div style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem; background-color: rgba(255,255,255,0.8);">
							<input id="vital-val" type="number" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700"
								placeholder="Enter value" bind:value={addVitalValue} />
						</div>
					</div>
					{#if addVitalType === 'bloodPressure'}
						<div>
							<label for="vital-val2" class="block text-sm font-medium text-gray-700 mb-1">Diastolic (mmHg)</label>
							<div style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem; background-color: rgba(255,255,255,0.8);">
								<input id="vital-val2" type="number" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700"
									placeholder="Enter diastolic" bind:value={addVitalValue2} />
							</div>
						</div>
					{/if}
				{/if}
				<button
					onclick={handleAddVital}
					disabled={addingVital || !addVitalType || !addVitalValue}
					class="w-full py-2.5 rounded-lg text-white text-sm font-medium cursor-pointer disabled:opacity-50"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
					{addingVital ? 'Adding...' : 'Save Reading'}
				</button>
			</div>
		</AquaModal>
	{/if}
	{/if}
</div>
