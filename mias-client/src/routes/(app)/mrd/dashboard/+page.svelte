<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { mrdApi, type CensusData, type CensusPatient, type CensusCategory } from '$lib/api/mrd';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		Users, Bed, Scissors, Baby, Skull, TestTube,
		LogOut, Calendar, ChevronRight, Activity, Clock
	} from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let census: CensusData | null = $state(null);
	let snapshotInfo = $state('');

	// Date range — default to today
	let fromDate = $state(new Date().toISOString().split('T')[0]);
	let toDate = $state(new Date().toISOString().split('T')[0]);

	// Modal state
	let modalOpen = $state(false);
	let modalTitle = $state('');
	let modalPatients: CensusPatient[] = $state([]);
	let modalLoading = $state(false);

	const cards: { key: CensusCategory; label: string; icon: any; gradient: string; textColor: string }[] = [
		{ key: 'op', label: 'OP Count', icon: Users, gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', textColor: '#fff' },
		{ key: 'ip', label: 'IP Count', icon: Bed, gradient: 'linear-gradient(135deg, #22c55e, #15803d)', textColor: '#fff' },
		{ key: 'ot', label: 'OT Procedures', icon: Scissors, gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)', textColor: '#fff' },
		{ key: 'births', label: 'Births', icon: Baby, gradient: 'linear-gradient(135deg, #ec4899, #be185d)', textColor: '#fff' },
		{ key: 'deaths', label: 'Deaths', icon: Skull, gradient: 'linear-gradient(135deg, #6b7280, #374151)', textColor: '#fff' },
		{ key: 'investigations', label: 'Investigations', icon: TestTube, gradient: 'linear-gradient(135deg, #f97316, #c2410c)', textColor: '#fff' },
		{ key: 'discharges', label: 'Discharges', icon: LogOut, gradient: 'linear-gradient(135deg, #06b6d4, #0e7490)', textColor: '#fff' },
	];

	function getCount(key: CensusCategory): number {
		if (!census) return 0;
		const map: Record<CensusCategory, number> = {
			op: census.op_count,
			ip: census.ip_count,
			ot: census.ot_procedures,
			births: census.births,
			deaths: census.deaths,
			investigations: census.investigations,
			discharges: census.discharges,
		};
		return map[key];
	}

	async function fetchCensus() {
		loading = true;
		try {
			const [c, health] = await Promise.all([
				mrdApi.getCensus({ from_date: fromDate, to_date: toDate }),
				mrdApi.getHealth(),
			]);
			census = c;
			if (health.snapshot_age_hours !== null) {
				snapshotInfo = `Snapshot as of ${health.snapshot_age_hours}h ago`;
			} else {
				snapshotInfo = 'Live data';
			}
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to load census', 'error');
		} finally {
			loading = false;
		}
	}

	async function openCategoryModal(key: CensusCategory, label: string) {
		modalTitle = `${label} Records`;
		modalOpen = true;
		modalLoading = true;
		modalPatients = [];
		try {
			const res = await mrdApi.getCensusPatients({
				category: key,
				from_date: fromDate,
				to_date: toDate,
				page_size: 50,
			});
			modalPatients = res.items;
		} catch (e: any) {
			toastStore.addToast('Failed to load patients', 'error');
		} finally {
			modalLoading = false;
		}
	}

	function navigateToPatient(patientId: string) {
		modalOpen = false;
		goto(`/mrd/patients?id=${patientId}`);
	}

	onMount(() => {
		if (auth.role !== 'MRD') {
			goto('/dashboard');
			return;
		}
		fetchCensus();
	});
</script>

<div class="max-w-[448px] mx-auto px-4 py-4 space-y-4">
	<!-- Snapshot banner -->
	{#if snapshotInfo}
		<div class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
			style="background: linear-gradient(to right, #fef3c7, #fde68a); color: #92400e;">
			<Clock size={14} />
			<span>{snapshotInfo}</span>
		</div>
	{/if}

	<!-- Census Period Picker -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<Calendar size={18} class="text-blue-600" />
				<span class="font-semibold text-sm">Census Period</span>
			</div>
		{/snippet}
		<div class="flex gap-2 items-end">
			<div class="flex-1">
				<label for="mrd-dashboard-from-date" class="text-xs text-gray-500 block mb-1">From</label>
				<input id="mrd-dashboard-from-date" type="date" bind:value={fromDate}
					class="w-full px-3 py-2 rounded-lg border text-sm"
					style="border-color: #d1d5db; background: #f9fafb;" />
			</div>
			<div class="flex-1">
				<label for="mrd-dashboard-to-date" class="text-xs text-gray-500 block mb-1">To</label>
				<input id="mrd-dashboard-to-date" type="date" bind:value={toDate}
					class="w-full px-3 py-2 rounded-lg border text-sm"
					style="border-color: #d1d5db; background: #f9fafb;" />
			</div>
			<AquaButton variant="primary" size="sm" onclick={fetchCensus} {loading}>
				Update
			</AquaButton>
		</div>
	</AquaCard>

	<!-- MRD Officer Card -->
	<div class="flex items-center gap-3 px-4 py-3 rounded-xl"
		style="background: linear-gradient(to bottom, #f0f9ff, #e0f2fe); border: 1px solid #bae6fd;">
		<Avatar name={'MRD Officer'} size="md" />
		<div>
			<div class="font-semibold text-sm" style="color: #0c4a6e;">MRD Officer</div>
			<div class="text-xs" style="color: #0369a1;">Medical Records Department</div>
		</div>
	</div>

	<!-- Census Stat Cards -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<Activity size={24} class="animate-spin text-blue-500" />
		</div>
	{:else if census}
		<div class="grid grid-cols-2 gap-3">
			{#each cards as card}
				{@const Icon = card.icon}
				<button
					class="flex flex-col items-center justify-center py-4 px-3 rounded-xl cursor-pointer transition-transform active:scale-95"
					style="background: {card.gradient}; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-height: 100px;"
					onclick={() => openCategoryModal(card.key, card.label)}
				>
					<Icon size={24} color={card.textColor} />
					<span class="text-2xl font-bold mt-1" style="color: {card.textColor};">{getCount(card.key)}</span>
					<span class="text-xs font-medium mt-0.5 opacity-90" style="color: {card.textColor};">{card.label}</span>
				</button>
			{/each}

			<!-- Total card spans full width -->
			<div class="col-span-2 flex items-center justify-between py-3 px-4 rounded-xl"
				style="background: linear-gradient(135deg, #1e293b, #0f172a); box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
				<span class="text-sm font-medium text-white opacity-80">Total</span>
				<span class="text-2xl font-bold text-white">{census.total}</span>
			</div>
		</div>

		<!-- View Detailed Census button -->
		<AquaButton variant="primary" fullWidth onclick={() => goto('/mrd/census')}>
			<div class="flex items-center justify-center gap-2">
				View Detailed Census
				<ChevronRight size={16} />
			</div>
		</AquaButton>
	{/if}
</div>

<!-- Patient list modal -->
<AquaModal
	open={modalOpen}
	title={modalTitle}
	onclose={() => (modalOpen = false)}
	panelClass="sm:max-w-md"
>
	{#if modalLoading}
		<div class="flex justify-center py-8">
			<Activity size={24} class="animate-spin text-blue-500" />
		</div>
	{:else if modalPatients.length === 0}
		<div class="text-center py-8 text-gray-500 text-sm">No records found</div>
	{:else}
		<div class="space-y-2 max-h-[60vh] overflow-y-auto">
			{#each modalPatients as p}
				<button
					class="w-full flex items-center gap-3 p-3 rounded-xl transition-colors"
					style="background: #f8fafc; border: 1px solid #e2e8f0;"
					onclick={() => navigateToPatient(p.id)}
				>
					<Avatar name={p.name} size="sm" />
					<div class="flex-1 text-left min-w-0">
						<div class="font-semibold text-sm truncate">{p.name}</div>
						<div class="text-xs text-gray-500">{p.patient_id} · Age {p.age}</div>
						{#if p.diagnosis}
							<div class="text-xs text-gray-400 truncate">{p.diagnosis}</div>
						{/if}
					</div>
					<div class="text-right shrink-0">
						<div class="text-xs text-gray-400">{p.date}</div>
						{#if p.time}
							<div class="text-xs text-gray-400">{p.time}</div>
						{/if}
					</div>
					<ChevronRight size={16} class="text-gray-400 shrink-0" />
				</button>
			{/each}
		</div>
	{/if}
</AquaModal>
