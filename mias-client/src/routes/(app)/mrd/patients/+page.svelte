<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { mrdApi, type MrdPatient, type MrdHealthResponse } from '$lib/api/mrd';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import PatientCaseSheet from '$lib/components/mrd/PatientCaseSheet.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		Search, Users, Clock, AlertTriangle, ChevronRight, Activity
	} from 'lucide-svelte';

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

	// Case sheet
	let caseSheetOpen = $state(false);
	let selectedPatient = $state<{
		id: string; patient_id: string; name: string;
		phone?: string | null; date_of_birth?: string | null; gender?: string | null;
	} | null>(null);

	async function loadHealth() {
		try { health = await mrdApi.getHealth(); } catch { health = null; }
	}

	async function searchPatientsQuery(append = false) {
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
			toastStore.addToast(err?.response?.data?.detail || 'Search failed', 'error');
		} finally {
			loading = false;
		}
	}

	function openPatientSheet(p: MrdPatient) {
		selectedPatient = {
			id: p.id,
			patient_id: p.patient_id,
			name: p.name,
			phone: p.phone,
			date_of_birth: p.date_of_birth,
			gender: p.gender,
		};
		caseSheetOpen = true;
	}

	// Handle ?id= query param from dashboard/census navigation
	async function handleQueryParam() {
		const idParam = page.url.searchParams.get('id');
		if (idParam) {
			// Try to find patient by internal ID - search by name won't work, 
			// so we open the case sheet directly with what we know
			selectedPatient = {
				id: idParam,
				patient_id: '',
				name: 'Patient',
			};
			caseSheetOpen = true;
			// Clear the query param from URL without reload
			goto('/mrd/patients', { replaceState: true });
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['MRD'])) return;
		await loadHealth();
		handleQueryParam();
	});
</script>

<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
		<div>
			<h1 class="text-xl font-bold text-slate-800">Patient Search</h1>
			<p class="text-sm text-slate-500 mt-0.5">Find and view patient records</p>
		</div>
		{#if health}
			<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
				style="background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;">
				<Clock size={12} />
				{#if health.snapshot_age_hours !== null}
					<span>
						Snapshot: {health.snapshot_age_hours.toFixed(1)}h ago
						{#if health.snapshot_age_hours > 36}
							<AlertTriangle class="inline w-3 h-3 text-amber-500 ml-0.5" />
						{/if}
					</span>
				{:else}
					<span>{health.status}</span>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Search Form -->
	<div class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"
		style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
		<div class="flex items-center gap-2 mb-4">
			<Users size={16} class="text-blue-600" />
			<span class="text-sm font-semibold text-slate-700">Search Criteria</span>
		</div>

		<div class="space-y-3">
			<div>
				<label for="mrd-patient-name" class="block text-[11px] font-medium text-slate-500 mb-1">Patient Name</label>
				<input id="mrd-patient-name" type="text" bind:value={searchName} placeholder="Search by name..."
					class="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
					style="border: 1px solid #e2e8f0; background: #f8fafc;" />
			</div>

			<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
				<div>
					<label for="mrd-patient-id" class="block text-[11px] font-medium text-slate-500 mb-1">Patient ID</label>
					<input id="mrd-patient-id" type="text" bind:value={searchPatientId} placeholder="PAT-001"
						class="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border: 1px solid #e2e8f0; background: #f8fafc;" />
				</div>
				<div>
					<label for="mrd-patient-phone" class="block text-[11px] font-medium text-slate-500 mb-1">Phone</label>
					<input id="mrd-patient-phone" type="text" bind:value={searchPhone} placeholder="9876543210"
						class="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border: 1px solid #e2e8f0; background: #f8fafc;" />
				</div>
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label for="mrd-dob-from" class="block text-[11px] font-medium text-slate-500 mb-1">DOB From</label>
						<input id="mrd-dob-from" type="date" bind:value={searchDobFrom}
							class="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
							style="border: 1px solid #e2e8f0; background: #f8fafc;" />
					</div>
					<div>
						<label for="mrd-dob-to" class="block text-[11px] font-medium text-slate-500 mb-1">DOB To</label>
						<input id="mrd-dob-to" type="date" bind:value={searchDobTo}
							class="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-200"
							style="border: 1px solid #e2e8f0; background: #f8fafc;" />
					</div>
				</div>
			</div>

			<AquaButton onclick={() => searchPatientsQuery()} {loading} fullWidth>
				<div class="flex items-center justify-center gap-2">
					<Search size={16} />
					Search Patients
				</div>
			</AquaButton>
		</div>
	</div>

	<!-- Results -->
	{#if !hasSearched}
		<div class="text-center py-12 text-sm text-slate-400">
			<Users size={36} class="mx-auto mb-3 text-slate-200" />
			Enter search criteria to find patients
		</div>
	{:else if loading && patients.length === 0}
		<div class="flex items-center justify-center py-12">
			<Activity size={24} class="animate-spin text-blue-500" />
		</div>
	{:else if patients.length === 0}
		<div class="text-center py-12 text-sm text-slate-400">
			No patients found
		</div>
	{:else}
		<div class="flex items-center justify-between px-1">
			<p class="text-xs text-slate-500">
				Showing {patients.length} of {totalCount} patients
			</p>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			{#each patients as patient, i}
				<button
					class="patient-card flex items-center gap-3 p-4 rounded-2xl border border-slate-200 bg-white text-left cursor-pointer"
					style="box-shadow: 0 1px 3px rgba(0,0,0,0.04); animation: cardIn 0.3s ease-out backwards; animation-delay: {i * 40}ms;"
					onclick={() => openPatientSheet(patient)}
				>
					<Avatar name={patient.name} size="sm" />
					<div class="flex-1 min-w-0">
						<p class="text-sm font-semibold text-slate-800 truncate">{patient.name}</p>
						<p class="text-xs text-slate-500 mt-0.5">
							{patient.patient_id}
							{#if patient.phone} · {patient.phone}{/if}
						</p>
						{#if patient.date_of_birth}
							<p class="text-xs text-slate-400 mt-0.5">
								DOB: {new Date(patient.date_of_birth).toLocaleDateString()}
								{#if patient.gender} · {patient.gender}{/if}
							</p>
						{/if}
					</div>
					<ChevronRight size={16} class="text-slate-300 shrink-0" />
				</button>
			{/each}
		</div>

		{#if nextCursor}
			<div class="flex justify-center pt-2 pb-4">
				<AquaButton variant="secondary" onclick={() => searchPatientsQuery(true)} {loading}>
					Load More
				</AquaButton>
			</div>
		{/if}
	{/if}
</div>

<!-- Patient Case Sheet -->
<PatientCaseSheet
	open={caseSheetOpen}
	patient={selectedPatient}
	onclose={() => (caseSheetOpen = false)}
/>

<style>
	@keyframes cardIn {
		from { opacity: 0; transform: translateY(8px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.patient-card {
		transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
	}

	@media (hover: hover) {
		.patient-card:hover {
			transform: translateY(-1px);
			box-shadow: 0 4px 16px rgba(0,0,0,0.08);
			border-color: #bfdbfe;
		}
	}

	.patient-card:active {
		transform: scale(0.98);
	}

	@media (prefers-reduced-motion: reduce) {
		.patient-card { animation: none !important; transition: none !important; }
	}
</style>
