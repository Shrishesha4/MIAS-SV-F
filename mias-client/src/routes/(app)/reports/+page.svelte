<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { TestTube, Download, Eye, ChevronRight } from 'lucide-svelte';

	const statusVariant: Record<string, 'normal' | 'abnormal' | 'critical' | 'pending'> = {
		NORMAL: 'normal',
		ABNORMAL: 'abnormal',
		CRITICAL: 'critical',
		PENDING: 'pending',
	};

	let selectedReport = $state<string | null>(null);
	let reports: any[] = $state([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			reports = await patientApi.getReports(patient.id);
		} catch (err) {
			console.error('Failed to load reports', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	{#each reports as report}
		<AquaCard padding={false}>
			<div class="px-4 py-3 flex items-center gap-3">
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, #f97316cc, #f97316);"
				>
					<TestTube class="w-5 h-5 text-white" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{report.title}</p>
					<p class="text-xs text-gray-500">
						{new Date(report.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						· {report.department}
					</p>
					<p class="text-xs text-gray-500">Ordered by: {report.ordered_by}</p>
				</div>
				<div class="flex flex-col items-end gap-2">
					<StatusBadge variant={statusVariant[report.status]}>{report.status}</StatusBadge>
					<div class="flex gap-1">
						<button
							class="p-1 text-blue-600 cursor-pointer"
							onclick={() => selectedReport = selectedReport === report.id ? null : report.id}
						>
							<Eye class="w-4 h-4" />
						</button>
						<button class="p-1 text-blue-600 cursor-pointer">
							<Download class="w-4 h-4" />
						</button>
					</div>
				</div>
			</div>

			{#if selectedReport === report.id && report.findings}
				<div class="px-4 pb-3 border-t border-gray-100 pt-3">
					<p class="text-xs text-gray-500 mb-1">Findings</p>
					<p class="text-sm text-gray-700">{report.findings}</p>
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if reports.length === 0}
		<div class="text-center py-12 text-gray-400">
			<TestTube class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No reports found</p>
		</div>
	{/if}
	{/if}
</div>
