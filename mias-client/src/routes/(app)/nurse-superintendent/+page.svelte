<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { nurseApi, type NurseStationSummary } from '$lib/api/nurse';
	import { staffApi, type PendingPatient } from '$lib/api/staff';
	import { toastStore } from '$lib/stores/toast';
	import { Activity, AlertCircle, ChevronRight, MapPinned, Stethoscope, Users } from 'lucide-svelte';

	let loading = $state(true);
	let stations = $state.raw<NurseStationSummary[]>([]);
	let pendingPatients = $state.raw<PendingPatient[]>([]);

	const stationCards = $derived.by(() => {
		const pendingByClinic = new Map<string, number>();
		for (const patient of pendingPatients) {
			if (!patient.clinic_id) continue;
			if (patient.workflow_status !== 'unchecked' && patient.workflow_status !== 'unassigned') continue;
			pendingByClinic.set(patient.clinic_id, (pendingByClinic.get(patient.clinic_id) ?? 0) + 1);
		}
		return stations.map((station) => ({
			...station,
			pending_count: pendingByClinic.get(station.clinic_id) ?? 0,
		}));
	});

	const totalPending = $derived(
		stationCards.reduce((sum, station) => sum + station.pending_count, 0)
	);

	const totalActivePatients = $derived(
		stationCards.reduce((sum, station) => sum + station.active_patient_count, 0)
	);

	function openStation(station: NurseStationSummary) {
		const params = new URLSearchParams({
			clinicId: station.clinic_id,
			clinicName: station.clinic_name,
		});
		if (station.wards.length === 1) {
			params.set('ward', station.wards[0]);
		}
		goto(`/nurse-station?${params.toString()}`);
	}

	async function loadStations() {
		loading = true;
		try {
			const [stationSummary, queue] = await Promise.all([
				nurseApi.getStations(),
				staffApi.getPendingPatients(),
			]);
			stations = stationSummary;
			pendingPatients = queue;
		} catch (error: any) {
			console.error('Error loading nurse superintendent stations:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to load nurse stations', 'error');
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const auth = get(authStore);
		if (auth.role !== 'NURSE_SUPERINTENDENT') {
			goto('/dashboard');
			return;
		}
		void loadStations();
	});
</script>

<div class="p-4 max-w-screen-2xl mx-auto space-y-4">
	{#if loading}
		<div class="text-center py-12">
			<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
		</div>
	{:else}
		<AquaCard padding={true}>
			{#snippet header()}
				<div class="flex items-center gap-3">
					<div
						class="flex items-center justify-center w-14 h-14 rounded-2xl"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(0,0,0,0.2);"
					>
						<Stethoscope class="w-7 h-7 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<h1 class="text-xl font-bold text-gray-900 truncate">Nurse Superintendent</h1>
						<p class="text-sm text-gray-600 truncate">Clinic-wide nurse station overview</p>
					</div>
				</div>
			{/snippet}

			<div class="grid grid-cols-1 gap-3 mt-4 sm:grid-cols-3">
				<div class="rounded-2xl px-4 py-4" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid #bfdbfe;">
					<div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">
						<MapPinned class="h-4 w-4" /> Active Clinics
					</div>
					<p class="mt-2 text-3xl font-bold text-blue-900">{stationCards.length}</p>
				</div>
				<div class="rounded-2xl px-4 py-4" style="background: linear-gradient(to bottom, #ecfccb, #d9f99d); border: 1px solid #bef264;">
					<div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-lime-700">
						<Activity class="h-4 w-4" /> Active Patients
					</div>
					<p class="mt-2 text-3xl font-bold text-lime-900">{totalActivePatients}</p>
				</div>
				<div class="rounded-2xl px-4 py-4" style="background: linear-gradient(to bottom, #fff7ed, #fed7aa); border: 1px solid #fdba74;">
					<div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-orange-700">
						<AlertCircle class="h-4 w-4" /> Pending Queue
					</div>
					<p class="mt-2 text-3xl font-bold text-orange-900">{totalPending}</p>
				</div>
			</div>
		</AquaCard>

		<AquaCard padding={false}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<Users class="w-5 h-5 text-blue-600" />
					<h2 class="text-base font-bold text-gray-800">Clinic Stations</h2>
				</div>
			{/snippet}

			<div class="space-y-3 px-4 py-4">
				{#if stationCards.length === 0}
					<div class="rounded-2xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
						<p class="text-sm">No active clinics are available yet.</p>
					</div>
				{:else}
					{#each stationCards as station (station.clinic_id)}
						<button
							type="button"
							onclick={() => openStation(station)}
							class="w-full rounded-[24px] px-4 py-4 text-left transition-transform cursor-pointer hover:-translate-y-0.5"
							style="background: linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(248,250,252,0.98)); border: 1px solid rgba(148,163,184,0.18); box-shadow: 0 12px 28px rgba(15,23,42,0.08);"
						>
							<div class="flex items-start gap-4">
								<div
									class="mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 14px rgba(37,99,235,0.3);"
								>
									<Stethoscope class="h-6 w-6 text-white" />
								</div>
								<div class="min-w-0 flex-1">
									<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
										<div class="min-w-0">
											<h3 class="text-xl font-bold text-slate-900 truncate">{station.clinic_name}</h3>
											<p class="mt-1 text-sm text-slate-600">{station.department}{station.location ? ` • ${station.location}` : ''}</p>
											<p class="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
												{station.wards.length > 0 ? station.wards.join(' • ') : 'No ward assignment yet'}
											</p>
										</div>
										<div class="flex items-center gap-2 self-start">
											<div class="rounded-2xl px-4 py-3 text-center" style="background: #eff6ff; border: 1px solid #bfdbfe; min-width: 96px;">
												<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-600">Patients</p>
												<p class="mt-1 text-2xl font-bold text-blue-900">{station.active_patient_count}</p>
											</div>
											<div class="rounded-2xl px-4 py-3 text-center" style="background: #fff7ed; border: 1px solid #fdba74; min-width: 96px;">
												<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-orange-600">Pending</p>
												<p class="mt-1 text-2xl font-bold text-orange-900">{station.pending_count}</p>
											</div>
											<ChevronRight class="hidden h-5 w-5 text-slate-400 md:block" />
										</div>
									</div>

									<div class="mt-4 flex flex-wrap gap-2">
										{#if station.assigned_nurses.length > 0}
											{#each station.assigned_nurses as nurse (nurse.id)}
												<div class="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700" style="background: rgba(37,99,235,0.08); border: 1px solid rgba(37,99,235,0.16);">
													{nurse.name}{nurse.shift ? ` • ${nurse.shift}` : ''}
												</div>
											{/each}
										{:else}
											<div class="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-500" style="background: rgba(148,163,184,0.08); border: 1px solid rgba(148,163,184,0.16);">
												No nurses assigned yet
											</div>
										{/if}
									</div>
								</div>
							</div>
						</button>
					{/each}
				{/if}
			</div>
		</AquaCard>
	{/if}
</div>