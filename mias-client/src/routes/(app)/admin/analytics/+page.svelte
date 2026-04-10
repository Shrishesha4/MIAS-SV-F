<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type TrendData, type TrendPoint } from '$lib/api/admin';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import {
		BarChart3, TrendingUp, Activity, Pill, Bed, Users
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let trends: TrendData | null = $state(null);
	let deptStats: any[] = $state([]);
	let periodDays = $state(30);
	let activeChart = $state('registrations');

	onMount(async () => {
		if (auth.role !== 'ADMIN') { window.location.href = '/dashboard'; return; }
		await loadData();
	});

	async function loadData() {
		loading = true;
		error = '';
		try {
			const [t, d] = await Promise.all([
				adminApi.getTrends(periodDays),
				adminApi.getDepartmentStats(),
			]);
			trends = t;
			deptStats = d;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load analytics';
		} finally {
			loading = false;
		}
	}

	function changePeriod(d: number) {
		periodDays = d;
		loadData();
	}

	const chartOptions = [
		{ id: 'registrations', label: 'Registrations', icon: Users, color: '#3b82f6' },
		{ id: 'admissions', label: 'Admissions', icon: Bed, color: '#10b981' },
		{ id: 'prescriptions', label: 'Prescriptions', icon: Pill, color: '#8b5cf6' },
		{ id: 'vitals', label: 'Vitals', icon: Activity, color: '#f59e0b' },
	];

	const activeData = $derived<TrendPoint[]>(
		trends
			? (trends as any)[activeChart] || []
			: []
	);

	const maxCount = $derived(
		activeData.length > 0
			? Math.max(...activeData.map((d: TrendPoint) => d.count), 1)
			: 1
	);

	const totalInPeriod = $derived(
		activeData.reduce((sum: number, d: TrendPoint) => sum + d.count, 0)
	);
</script>

	<div class="space-y-4">
		<div>
			<h2 class="text-sm font-bold uppercase tracking-[0.18em] text-slate-600">Analytics</h2>
			<p class="mt-1 text-xs text-slate-500">Hospital performance overview</p>
		</div>

		<div class="flex gap-2 overflow-x-auto">
		{#each [{ d: 7, l: '7 days' }, { d: 30, l: '30 days' }, { d: 90, l: '90 days' }, { d: 365, l: '1 year' }] as p}
			<button
				class="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-all"
				style={periodDays === p.d
					? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);'
					: 'background: white; color: #4b5563; border: 1px solid #e5e7eb;'}
				onclick={() => changePeriod(p.d)}
			>
				{p.l}
			</button>
		{/each}
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<AquaCard>
			<p class="text-red-500 text-center py-4">{error}</p>
		</AquaCard>
	{:else if trends}
		<!-- Chart Type Toggle -->
		<div class="grid grid-cols-4 gap-2">
			{#each chartOptions as opt}
				{@const Icon = opt.icon}
				{@const data = (trends as any)[opt.id] || []}
				{@const sum = data.reduce((s: number, d: any) => s + d.count, 0)}
				<button
					class="text-center p-2 rounded-xl cursor-pointer transition-all"
					style={activeChart === opt.id
						? `background: ${opt.color}15; border: 2px solid ${opt.color}; box-shadow: 0 0 0 1px ${opt.color}40;`
						: 'background: white; border: 2px solid transparent; box-shadow: 0 1px 3px rgba(0,0,0,0.08);'}
					onclick={() => activeChart = opt.id}
				>
					<Icon class="w-4 h-4 mx-auto mb-1" style="color: {opt.color};" />
					<p class="text-lg font-bold" style="color: {opt.color};">{sum}</p>
					<p class="text-[9px] text-gray-500">{opt.label}</p>
				</button>
			{/each}
		</div>

		<!-- Bar Chart -->
		<AquaCard>
			{#snippet header()}
				{@const opt = chartOptions.find(c => c.id === activeChart)!}
				<TrendingUp class="w-4 h-4 mr-2" style="color: {opt.color};" />
				<span class="text-sm font-semibold text-blue-900">{opt.label} Trend</span>
				<span class="ml-auto text-xs text-gray-400">{totalInPeriod} total</span>
			{/snippet}

			{#if activeData.length === 0}
				<div class="text-center py-8 text-gray-400 text-sm">No data for this period</div>
			{:else}
				<div class="space-y-1.5 max-h-64 overflow-y-auto">
					{#each activeData as point}
						{@const pct = maxCount > 0 ? (point.count / maxCount) * 100 : 0}
						{@const opt = chartOptions.find(c => c.id === activeChart)!}
						<div class="flex items-center gap-2">
							<span class="text-[10px] text-gray-400 w-16 shrink-0 text-right">
								{new Date(point.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
							</span>
							<div class="flex-1 h-4 bg-gray-50 rounded-full overflow-hidden">
								<div
									class="h-full rounded-full transition-all"
									style="width: {Math.max(pct, 2)}%; background: linear-gradient(90deg, {opt.color}80, {opt.color});"
								></div>
							</div>
							<span class="text-xs font-medium text-gray-700 w-8 text-right">{point.count}</span>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>

		<!-- Department Stats -->
		{#if deptStats.length > 0}
			<AquaCard>
				{#snippet header()}
					<BarChart3 class="w-4 h-4 text-blue-700 mr-2" />
					<span class="text-sm font-semibold text-blue-900">Faculty by Department</span>
				{/snippet}
				<div class="space-y-3">
					{#each deptStats as ds}
						{@const maxFac = Math.max(...deptStats.map((d: any) => d.faculty_count), 1)}
						{@const dpct = (ds.faculty_count / maxFac) * 100}
						<div>
							<div class="flex items-center justify-between text-xs mb-1">
								<span class="font-medium text-gray-700">{ds.department}</span>
								<span class="text-gray-500">{ds.faculty_count} faculty</span>
							</div>
							<div class="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
								<div
									class="h-full rounded-full"
									style="width: {dpct}%; background: linear-gradient(90deg, #8b5cf680, #8b5cf6);"
								></div>
							</div>
						</div>
					{/each}
				</div>
			</AquaCard>
		{/if}
	{/if}
	</div>
