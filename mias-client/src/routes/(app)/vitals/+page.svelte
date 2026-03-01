<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { Chart, registerables } from 'chart.js';
	import { patientApi } from '$lib/api/patients';
	import { authStore } from '$lib/stores/auth';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Activity, HeartPulse, Thermometer, Droplet, Scale } from 'lucide-svelte';

	Chart.register(...registerables);

	let bpChartCanvas: HTMLCanvasElement | undefined = $state();
	let hrChartCanvas: HTMLCanvasElement | undefined = $state();
	let bpChart: Chart | null = null;
	let hrChart: Chart | null = null;

	let selectedDays = $state(7);
	let vitals: any[] = $state([]);
	let loading = $state(true);
	let patientId = $state('');

	const filteredVitals = $derived(vitals.slice(0, selectedDays).reverse());
	const latestVital = $derived(vitals.length > 0 ? vitals[0] : null);

	const vitalCards = $derived(latestVital ? [
		{
			icon: HeartPulse,
			label: 'Blood Pressure',
			value: `${latestVital.systolic_bp ?? '--'}/${latestVital.diastolic_bp ?? '--'}`,
			unit: 'mmHg',
			status: (latestVital.systolic_bp ?? 0) > 130 ? 'warning' as const : 'normal' as const,
		},
		{
			icon: Activity,
			label: 'Heart Rate',
			value: `${latestVital.heart_rate ?? '--'}`,
			unit: 'bpm',
			status: 'normal' as const,
		},
		{
			icon: Droplet,
			label: 'SpO₂',
			value: `${latestVital.oxygen_saturation ?? '--'}`,
			unit: '%',
			status: (latestVital.oxygen_saturation ?? 0) < 95 ? 'warning' as const : 'normal' as const,
		},
		{
			icon: Thermometer,
			label: 'Temperature',
			value: `${latestVital.temperature?.toFixed(1) ?? '--'}`,
			unit: '°F',
			status: (latestVital.temperature ?? 0) > 99.5 ? 'warning' as const : 'normal' as const,
		},
		{
			icon: Scale,
			label: 'Weight',
			value: `${latestVital.weight?.toFixed(1) ?? '--'}`,
			unit: 'lbs',
			status: 'normal' as const,
		},
		{
			icon: Activity,
			label: 'Blood Glucose',
			value: `${latestVital.blood_glucose ?? '--'}`,
			unit: 'mg/dL',
			status: (latestVital.blood_glucose ?? 0) > 120 ? 'warning' as const : 'normal' as const,
		},
	] : []);

	function buildCharts() {
		const labels = filteredVitals.map(v => {
			const d = new Date(v.recorded_at);
			return `${d.getMonth() + 1}/${d.getDate()}`;
		});

		// Destroy existing charts
		bpChart?.destroy();
		hrChart?.destroy();

		// Blood Pressure Chart
		if (bpChartCanvas) {
			bpChart = new Chart(bpChartCanvas, {
				type: 'line',
				data: {
					labels,
					datasets: [
						{
							label: 'Systolic',
							data: filteredVitals.map(v => v.systolic_bp ?? 0),
							borderColor: '#ef4444',
							backgroundColor: 'rgba(239, 68, 68, 0.1)',
							tension: 0.4,
							fill: true,
						},
						{
							label: 'Diastolic',
							data: filteredVitals.map(v => v.diastolic_bp ?? 0),
							borderColor: '#3b82f6',
							backgroundColor: 'rgba(59, 130, 246, 0.1)',
							tension: 0.4,
							fill: true,
						},
					],
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
					},
					scales: {
						y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' } },
						x: { grid: { display: false }, ticks: { font: { size: 10 } } },
					},
				},
			});
		}

		// Heart Rate Chart
		if (hrChartCanvas) {
			hrChart = new Chart(hrChartCanvas, {
				type: 'line',
				data: {
					labels,
					datasets: [
						{
							label: 'Heart Rate',
							data: filteredVitals.map(v => v.heart_rate ?? 0),
							borderColor: '#ef4444',
							backgroundColor: 'rgba(239, 68, 68, 0.1)',
							tension: 0.4,
							fill: true,
							pointBackgroundColor: '#ef4444',
						},
						{
							label: 'SpO₂',
							data: filteredVitals.map(v => v.oxygen_saturation ?? 0),
							borderColor: '#22c55e',
							backgroundColor: 'rgba(34, 197, 94, 0.1)',
							tension: 0.4,
							fill: true,
							pointBackgroundColor: '#22c55e',
						},
					],
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					plugins: {
						legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
					},
					scales: {
						y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' } },
						x: { grid: { display: false }, ticks: { font: { size: 10 } } },
					},
				},
			});
		}
	}

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			patientId = patient.id;
			vitals = await patientApi.getVitals(patient.id, 30);
		} catch (err) {
			console.error('Failed to load vitals', err);
		} finally {
			loading = false;
		}
		if (!loading && vitals.length > 0) {
			buildCharts();
		}
	});

	$effect(() => {
		// Rebuild when selectedDays changes
		selectedDays;
		if (bpChartCanvas && hrChartCanvas) {
			buildCharts();
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
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
	<!-- Current Vitals Grid -->
	<div class="grid grid-cols-3 gap-2">
		{#each vitalCards as card}
			<div
				class="p-3 rounded-xl text-center"
				style="background-color: white;
				       border-radius: 10px;
				       box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				       border: 1px solid rgba(0,0,0,0.1);"
			>
				<card.icon class="w-5 h-5 mx-auto mb-1 text-blue-600" />
				<p class="text-xs text-gray-500">{card.label}</p>
				<p class="text-lg font-bold text-blue-900">{card.value}</p>
				<p class="text-[10px] text-gray-400">{card.unit}</p>
			</div>
		{/each}
	</div>

	<!-- Period Selector -->
	<div class="flex gap-2 justify-center">
		{#each [7, 14, 30] as days}
			<button
				class="px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer transition-all"
				style={selectedDays === days
					? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 3px rgba(0,0,0,0.3);'
					: 'background: linear-gradient(to bottom, #f0f4fa, #d5dde8); color: #1e40af; border: 1px solid rgba(0,0,0,0.2);'}
				onclick={() => selectedDays = days}
			>
				{days}D
			</button>
		{/each}
	</div>

	<!-- Blood Pressure Chart -->
	<AquaCard>
		{#snippet header()}
			<HeartPulse class="w-4 h-4 text-red-500 mr-2" />
			<span class="text-blue-900 font-semibold text-sm">Blood Pressure Trend</span>
		{/snippet}
		<div class="h-48">
			<canvas bind:this={bpChartCanvas}></canvas>
		</div>
	</AquaCard>

	<!-- Heart Rate & SpO2 Chart -->
	<AquaCard>
		{#snippet header()}
			<Activity class="w-4 h-4 text-red-500 mr-2" />
			<span class="text-blue-900 font-semibold text-sm">Heart Rate & SpO₂</span>
		{/snippet}
		<div class="h-48">
			<canvas bind:this={hrChartCanvas}></canvas>
		</div>
	</AquaCard>

	<!-- Vitals History -->
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
	{/if}
</div>
