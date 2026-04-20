<script lang="ts">
	import { onMount } from 'svelte';
	import { mrdApi, type MrdExportJob, type MrdHealthResponse } from '$lib/api/mrd';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { Download, RefreshCw, Clock, AlertTriangle, FileText, Plus } from 'lucide-svelte';

	let health = $state<MrdHealthResponse | null>(null);
	let jobs = $state<MrdExportJob[]>([]);
	let loading = $state(false);
	let createLoading = $state(false);

	// New export form
	let showForm = $state(false);
	let exportType = $state('records');
	let fromDate = $state('');
	let toDate = $state('');

	const exportTypes = [
		{ value: 'records', label: 'Medical Records' },
		{ value: 'prescriptions', label: 'Prescriptions' },
		{ value: 'admissions', label: 'Admissions' },
	];

	function getDefaultDates() {
		const now = new Date();
		const to = now.toISOString().split('T')[0];
		const from = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate()).toISOString().split('T')[0];
		return { from, to };
	}

	async function loadHealth() {
		try {
			health = await mrdApi.getHealth();
		} catch {
			health = null;
		}
	}

	async function loadJobs() {
		loading = true;
		try {
			const res = await mrdApi.listExports();
			jobs = res.jobs;
		} catch {
			toastStore.addToast('Failed to load exports', 'error');
		} finally {
			loading = false;
		}
	}

	async function createExport() {
		if (!fromDate || !toDate) {
			toastStore.addToast('Date range is required', 'error');
			return;
		}

		const from = new Date(fromDate);
		const to = new Date(toDate);
		const span = Math.abs((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24));
		if (span > 366) {
			toastStore.addToast('Date range cannot exceed 366 days', 'error');
			return;
		}

		createLoading = true;
		try {
			await mrdApi.createExport({
				export_type: exportType,
				from_date: fromDate,
				to_date: toDate,
			});
			toastStore.addToast('Export job started', 'success');
			showForm = false;
			await loadJobs();
		} catch (err: any) {
			const msg = err?.response?.data?.detail || 'Failed to create export';
			toastStore.addToast(msg, 'error');
		} finally {
			createLoading = false;
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['MRD'])) return;
		const defaults = getDefaultDates();
		fromDate = defaults.from;
		toDate = defaults.to;
		await Promise.all([loadHealth(), loadJobs()]);
	});
</script>

<div class="px-4 py-4 space-y-4">
	<!-- Snapshot banner -->
	{#if health}
		<div class="rounded-xl px-4 py-2 flex items-center gap-2 text-xs"
			style="background: linear-gradient(to right, #eff6ff, #dbeafe); border: 1px solid #93c5fd;">
			<Clock class="w-3.5 h-3.5 text-blue-600 shrink-0" />
			{#if health.snapshot_age_hours !== null}
				<span class="text-blue-800">
					Snapshot: <strong>{health.snapshot_age_hours.toFixed(1)}h ago</strong>
					{#if health.snapshot_age_hours > 36}
						<AlertTriangle class="inline w-3 h-3 text-amber-500 ml-1" />
						<span class="text-amber-600">(stale)</span>
					{/if}
				</span>
			{:else}
				<span class="text-blue-800">Snapshot status: {health.status}</span>
			{/if}
		</div>
	{/if}

	<!-- Header -->
	<div class="flex items-center justify-between">
		<h2 class="text-lg font-bold text-gray-900">Data Exports</h2>
		<div class="flex gap-2">
			<AquaButton variant="secondary" onclick={loadJobs} loading={loading} size="sm">
				<RefreshCw class="w-3.5 h-3.5" />
			</AquaButton>
			<AquaButton onclick={() => showForm = !showForm} size="sm">
				<Plus class="w-3.5 h-3.5 mr-1 inline" />
				New Export
			</AquaButton>
		</div>
	</div>

	<!-- New export form -->
	{#if showForm}
		<AquaCard>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<Download class="w-4 h-4 text-blue-600" />
					<span class="font-semibold text-sm">Create Export</span>
				</div>
			{/snippet}

			<div class="space-y-3">
				<div>
					<label for="mrd-export-type" class="block text-[11px] font-medium text-gray-500 mb-1">Export Type</label>
					<select id="mrd-export-type" bind:value={exportType}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;">
						{#each exportTypes as t}
							<option value={t.value}>{t.label}</option>
						{/each}
					</select>
				</div>

				<div class="grid grid-cols-2 gap-2">
					<div>
						<label for="mrd-export-from-date" class="block text-[11px] font-medium text-gray-500 mb-1">From Date *</label>
						<input id="mrd-export-from-date" type="date" bind:value={fromDate}
							class="w-full rounded-lg px-3 py-2 text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
					</div>
					<div>
						<label for="mrd-export-to-date" class="block text-[11px] font-medium text-gray-500 mb-1">To Date *</label>
						<input id="mrd-export-to-date" type="date" bind:value={toDate}
							class="w-full rounded-lg px-3 py-2 text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
					</div>
				</div>

				<AquaButton onclick={createExport} loading={createLoading} fullWidth>
					<Download class="w-4 h-4 mr-1 inline" />
					Start Export
				</AquaButton>
			</div>
		</AquaCard>
	{/if}

	<!-- Jobs list -->
	{#if loading && jobs.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">Loading exports...</div>
	{:else if jobs.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">
			<FileText class="w-8 h-8 text-gray-300 mx-auto mb-2" />
			No exports yet. Create one to get started.
		</div>
	{:else}
		<div class="space-y-2">
			{#each jobs as job}
				<div class="rounded-xl px-4 py-3"
					style="background: #fff; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
					<div class="flex items-center justify-between">
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<span class="text-sm font-semibold text-gray-900 capitalize">{job.export_type}</span>
								<span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold"
									style={job.status === 'complete' ? 'background: linear-gradient(to bottom, #a7f3d0, #6ee7b7); color: #065f46;' :
										job.status === 'running' ? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;' :
										job.status === 'failed' ? 'background: linear-gradient(to bottom, #ff5a5a, #cc0000); color: white;' :
										'background: linear-gradient(to bottom, #e5e7eb, #d1d5db); color: #374151;'}>
									{job.status}
								</span>
							</div>
							<p class="text-xs text-gray-500 mt-0.5">
								{new Date(job.created_at).toLocaleString()}
								{#if job.row_count && job.row_count !== '0'}
									· {job.row_count} rows
								{/if}
							</p>
							{#if job.error}
								<p class="text-xs text-red-500 mt-0.5 truncate">{job.error}</p>
							{/if}
						</div>
						{#if job.status === 'complete' && job.file_path}
							<Download class="w-4 h-4 text-blue-500 shrink-0" />
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
