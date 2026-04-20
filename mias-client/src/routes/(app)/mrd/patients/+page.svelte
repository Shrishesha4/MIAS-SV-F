<script lang="ts">
	import { onMount } from 'svelte';
	import { mrdApi, type MrdPatient, type MrdHealthResponse } from '$lib/api/mrd';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { Search, Users, Clock, AlertTriangle } from 'lucide-svelte';

	let health = $state<MrdHealthResponse | null>(null);
	let patients = $state<MrdPatient[]>([]);
	let loading = $state(false);
	let nextCursor = $state<string | null>(null);
	let totalCount = $state(0);
	let hasSearched = $state(false);

	let searchName = $state('');
	let searchPatientId = $state('');
	let searchPhone = $state('');
	let searchDobFrom = $state('');
	let searchDobTo = $state('');

	async function loadHealth() {
		try {
			health = await mrdApi.getHealth();
		} catch {
			health = null;
		}
	}

	async function searchPatients(append = false) {
		if (!searchName && !searchPatientId && !searchPhone && !searchDobFrom) {
			toastStore.addToast('Enter at least one search criterion', 'error');
			return;
		}

		loading = true;
		hasSearched = true;
		try {
			const params: any = { page_size: 50 };
			if (searchName) params.name = searchName;
			if (searchPatientId) params.patient_id = searchPatientId;
			if (searchPhone) params.phone = searchPhone;
			if (searchDobFrom) params.dob_from = searchDobFrom;
			if (searchDobTo) params.dob_to = searchDobTo;
			if (append && nextCursor) params.cursor = nextCursor;

			const res = await mrdApi.searchPatients(params);
			if (append) {
				patients = [...patients, ...res.items];
			} else {
				patients = res.items;
			}
			nextCursor = res.next_cursor;
			totalCount = res.total;
		} catch (err: any) {
			const msg = err?.response?.data?.detail || 'Search failed';
			toastStore.addToast(msg, 'error');
		} finally {
			loading = false;
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['MRD'])) return;
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

	<!-- Search -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<Users class="w-4 h-4 text-blue-600" />
				<span class="font-semibold text-sm">Patient Search</span>
			</div>
		{/snippet}

		<div class="space-y-3">
			<div>
				<label class="block text-[11px] font-medium text-gray-500 mb-1">Patient Name</label>
				<input type="text" bind:value={searchName} placeholder="Search by name..."
					class="w-full rounded-lg px-3 py-2 text-sm outline-none"
					style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
			</div>

			<div class="grid grid-cols-2 gap-2">
				<div>
					<label class="block text-[11px] font-medium text-gray-500 mb-1">Patient ID</label>
					<input type="text" bind:value={searchPatientId} placeholder="PAT-001"
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
				<div>
					<label class="block text-[11px] font-medium text-gray-500 mb-1">Phone</label>
					<input type="text" bind:value={searchPhone} placeholder="9876543210"
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2">
				<div>
					<label class="block text-[11px] font-medium text-gray-500 mb-1">DOB From</label>
					<input type="date" bind:value={searchDobFrom}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
				<div>
					<label class="block text-[11px] font-medium text-gray-500 mb-1">DOB To</label>
					<input type="date" bind:value={searchDobTo}
						class="w-full rounded-lg px-3 py-2 text-sm outline-none"
						style="border: 1px solid rgba(0,0,0,0.15); background: #fff;" />
				</div>
			</div>

			<AquaButton onclick={() => searchPatients()} loading={loading} fullWidth>
				<Search class="w-4 h-4 mr-1 inline" />
				Search Patients
			</AquaButton>
		</div>
	</AquaCard>

	<!-- Results -->
	{#if !hasSearched}
		<div class="text-center py-8 text-sm text-gray-400">
			Enter search criteria to find patients
		</div>
	{:else if loading && patients.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">Loading...</div>
	{:else if patients.length === 0}
		<div class="text-center py-8 text-sm text-gray-400">No patients found</div>
	{:else}
		<div class="text-xs text-gray-500 px-1">
			Showing {patients.length} of {totalCount} patients
		</div>

		<div class="space-y-2">
			{#each patients as patient}
				<div
					class="rounded-xl px-4 py-3"
					style="background: #fff; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.06);"
				>
					<div class="flex items-center justify-between">
						<div class="min-w-0 flex-1">
							<p class="text-sm font-semibold text-gray-900">{patient.name}</p>
							<p class="text-xs text-gray-500 mt-0.5">
								{patient.patient_id}
								{#if patient.phone} · {patient.phone}{/if}
							</p>
							{#if patient.date_of_birth}
								<p class="text-xs text-gray-400 mt-0.5">
									DOB: {new Date(patient.date_of_birth).toLocaleDateString()}
									{#if patient.gender} · {patient.gender}{/if}
								</p>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		{#if nextCursor}
			<div class="flex justify-center pt-2 pb-4">
				<AquaButton variant="secondary" onclick={() => searchPatients(true)} loading={loading}>
					Load More
				</AquaButton>
			</div>
		{/if}
	{/if}
</div>
