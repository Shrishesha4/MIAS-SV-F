<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { mrdApi, type MrdRecord, type MrdHealthResponse } from '$lib/api/mrd';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { Search, FileText, ChevronRight, AlertTriangle, Download, Clock } from 'lucide-svelte';

	let health = $state<MrdHealthResponse | null>(null);
	let records = $state<MrdRecord[]>([]);
	let loading = $state(false);
	let nextCursor = $state<string | null>(null);
	let totalCount = $state(0);
	let hasSearched = $state(false);

	// Filters — date range mandatory
	let fromDate = $state('');
	let toDate = $state('');
	let filterType = $state('');
	let filterDepartment = $state('');
	let filterPatientId = $state('');
	let filterPerformedBy = $state('');

	const recordTypes = ['CONSULTATION', 'LABORATORY', 'PROCEDURE', 'MEDICATION'];

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

	async function searchRecords(append = false) {
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

		loading = true;
		hasSearched = true;
		try {
			const params: any = {
				from_date: fromDate,
				to_date: toDate,
				page_size: 50,
			};
			if (filterType) params.type = filterType;
			if (filterDepartment) params.department = filterDepartment;
			if (filterPatientId) params.patient_id = filterPatientId;
			if (filterPerformedBy) params.performed_by = filterPerformedBy;
			if (append && nextCursor) params.cursor = nextCursor;

			const res = await mrdApi.getRecords(params);
			if (append) {
				records = [...records, ...res.items];
			} else {
				records = res.items;
			}
			nextCursor = res.next_cursor;
			totalCount = res.total;
		} catch (err: any) {
			const msg = err?.response?.data?.detail || 'Failed to load records';
			toastStore.addToast(msg, 'error');
		} finally {
			loading = false;
		}
	}

	function handleExport() {
		if (!fromDate || !toDate) return;
		mrdApi.createExport({ export_type: 'records', from_date: fromDate, to_date: toDate })
			.then(() => toastStore.addToast('Export job started', 'success'))
			.catch(() => toastStore.addToast('Export failed', 'error'));
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['MRD'])) return;
		const defaults = getDefaultDates();
		fromDate = defaults.from;
		toDate = defaults.to;
		await loadHealth();
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

	<!-- Search filters -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<FileText class="w-4 h-4 text-blue-600" />
				<span class="font-semibold text-sm">Medical Records</span>
			</div>
		{/snippet}

		<div class="space-y-3">
			<div class="grid grid-cols-2 gap-2">
				<div>
					<label for="mrd-records-from-date" class="block text-[11px] font-medium text-gray-500 mb-1">From Date *</label>
					<input id="mrd-records-from-date" type="date" bind:value={fromDate}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
				<div>
					<label for="mrd-records-to-date" class="block text-[11px] font-medium text-gray-500 mb-1">To Date *</label>
					<input id="mrd-records-to-date" type="date" bind:value={toDate}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2">
				<div>
					<label for="mrd-records-type" class="block text-[11px] font-medium text-gray-500 mb-1">Type</label>
					<select id="mrd-records-type" bind:value={filterType}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;">
						<option value="">All types</option>
						{#each recordTypes as t}
							<option value={t}>{t}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="mrd-records-department" class="block text-[11px] font-medium text-gray-500 mb-1">Department</label>
					<input id="mrd-records-department" type="text" bind:value={filterDepartment} placeholder="e.g. Cardiology"
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2">
				<div>
					<label for="mrd-records-patient-id" class="block text-[11px] font-medium text-gray-500 mb-1">Patient ID</label>
					<input id="mrd-records-patient-id" type="text" bind:value={filterPatientId} placeholder="PAT-001"
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
				<div>
					<label for="mrd-records-performed-by" class="block text-[11px] font-medium text-gray-500 mb-1">Performed By</label>
					<input id="mrd-records-performed-by" type="text" bind:value={filterPerformedBy} placeholder="Doctor name"
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
			</div>

			<div class="flex gap-2">
				<AquaButton onclick={() => searchRecords()} loading={loading} fullWidth>
					<Search class="w-4 h-4 mr-1 inline" />
					Search Records
				</AquaButton>
				{#if hasSearched && records.length > 0}
					<AquaButton variant="secondary" onclick={handleExport}>
						<Download class="w-4 h-4" />
					</AquaButton>
				{/if}
			</div>
		</div>
	</AquaCard>

	<!-- Results -->
	{#if !hasSearched}
		<div class="text-center py-8 text-sm text-gray-400">
			Set date range and search to view records
		</div>
	{:else if loading && records.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">Loading...</div>
	{:else if records.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">No records found for this date range</div>
	{:else}
		<div class="text-xs text-gray-500 px-1">
			Showing {records.length} of {totalCount} records
		</div>

		<div class="space-y-2">
			{#each records as record}
				<button
					class="w-full text-left rounded-xl px-4 py-3 cursor-pointer active:scale-[0.98] transition-transform"
					style="background: #fff; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.06);"
				>
					<div class="flex items-center justify-between">
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-2">
								<span class="text-sm font-semibold text-gray-900 truncate">{record.patient_name || record.patient_id}</span>
								<span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold"
									style="background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;">
									{record.type}
								</span>
							</div>
							<p class="text-xs text-gray-500 mt-0.5 truncate">
								{record.department || 'N/A'} · {record.performed_by || 'N/A'}
							</p>
							<p class="text-xs text-gray-400 mt-0.5">
								{new Date(record.date).toLocaleDateString()}
								{#if record.diagnosis}
									· {record.diagnosis}
								{/if}
							</p>
						</div>
						<ChevronRight class="w-4 h-4 text-gray-300 shrink-0" />
					</div>
				</button>
			{/each}
		</div>

		{#if nextCursor}
			<div class="flex justify-center pt-2 pb-4">
				<AquaButton variant="secondary" onclick={() => searchRecords(true)} loading={loading}>
					Load More
				</AquaButton>
			</div>
		{/if}
	{/if}
</div>
