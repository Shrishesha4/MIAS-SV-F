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
	import PatientCaseSheet from '$lib/components/mrd/PatientCaseSheet.svelte';
	import {
		Users, Bed, Scissors, Baby, Skull, TestTube,
		LogOut, Calendar, ChevronRight, Activity, Clock, BarChart3
	} from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let census: CensusData | null = $state(null);
	let snapshotInfo = $state('');

	let fromDate = $state(new Date().toISOString().split('T')[0]);
	let toDate = $state(new Date().toISOString().split('T')[0]);

	// Modal state
	let modalOpen = $state(false);
	let modalTitle = $state('');
	let modalPatients: CensusPatient[] = $state([]);
	let modalLoading = $state(false);

	// Case sheet state
	let caseSheetOpen = $state(false);
	let selectedPatient = $state<{
		id: string; patient_id: string; name: string;
		age?: number; diagnosis?: string; department?: string;
	} | null>(null);

	const cards: { key: CensusCategory; label: string; icon: any; color: string; bg: string }[] = [
		{ key: 'op', label: 'Out-Patient', icon: Users, color: '#2563eb', bg: '#eff6ff' },
		{ key: 'ip', label: 'In-Patient', icon: Bed, color: '#16a34a', bg: '#f0fdf4' },
		{ key: 'ot', label: 'OT Procedures', icon: Scissors, color: '#7c3aed', bg: '#f5f3ff' },
		{ key: 'births', label: 'Births', icon: Baby, color: '#db2777', bg: '#fdf2f8' },
		{ key: 'deaths', label: 'Deaths', icon: Skull, color: '#4b5563', bg: '#f9fafb' },
		{ key: 'investigations', label: 'Investigations', icon: TestTube, color: '#ea580c', bg: '#fff7ed' },
		{ key: 'discharges', label: 'Discharges', icon: LogOut, color: '#0891b2', bg: '#ecfeff' },
	];

	function getCount(key: CensusCategory): number {
		if (!census) return 0;
		const map: Record<CensusCategory, number> = {
			op: census.op_count, ip: census.ip_count, ot: census.ot_procedures,
			births: census.births, deaths: census.deaths,
			investigations: census.investigations, discharges: census.discharges,
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
				snapshotInfo = `${health.snapshot_age_hours.toFixed(1)}h ago`;
			} else {
				snapshotInfo = 'Live';
			}
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to load census', 'error');
		} finally {
			loading = false;
		}
	}

	async function openCategoryModal(key: CensusCategory, label: string) {
		modalTitle = label;
		modalOpen = true;
		modalLoading = true;
		modalPatients = [];
		try {
			const res = await mrdApi.getCensusPatients({
				category: key, from_date: fromDate, to_date: toDate, page_size: 50,
			});
			modalPatients = res.items;
		} catch {
			toastStore.addToast('Failed to load patients', 'error');
		} finally {
			modalLoading = false;
		}
	}

	function openPatientSheet(p: CensusPatient) {
		selectedPatient = {
			id: p.id, patient_id: p.patient_id, name: p.name,
			age: p.age, diagnosis: p.diagnosis, department: p.department,
		};
		modalOpen = false;
		caseSheetOpen = true;
	}

	onMount(() => {
		if (auth.role !== 'MRD') { goto('/dashboard'); return; }
		fetchCensus();
	});
</script>

<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
	<!-- Header Row -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
		<div>
			<h1 class="text-xl font-bold text-slate-800">MRD Dashboard</h1>
			<p class="text-sm text-slate-500 mt-0.5">Medical Records Department</p>
		</div>
		{#if snapshotInfo}
			<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
				style="background: #fef3c7; color: #92400e;">
				<Clock size={12} />
				<span>Data: {snapshotInfo}</span>
			</div>
		{/if}
	</div>

	<!-- Date Range Card -->
	<div class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"
		style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
		<div class="flex flex-col sm:flex-row sm:items-end gap-3">
			<div class="flex items-center gap-2 sm:hidden">
				<Calendar size={16} class="text-blue-600" />
				<span class="text-sm font-semibold text-slate-700">Census Period</span>
			</div>
			<div class="flex-1 grid grid-cols-2 gap-3">
				<div>
					<label for="mrd-from" class="block text-[11px] font-medium text-slate-500 mb-1">From</label>
					<input id="mrd-from" type="date" bind:value={fromDate}
						class="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border-color: #e2e8f0; background: #f8fafc;" />
				</div>
				<div>
					<label for="mrd-to" class="block text-[11px] font-medium text-slate-500 mb-1">To</label>
					<input id="mrd-to" type="date" bind:value={toDate}
						class="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border-color: #e2e8f0; background: #f8fafc;" />
				</div>
			</div>
			<AquaButton variant="primary" size="sm" onclick={fetchCensus} {loading}>
				Update
			</AquaButton>
		</div>
	</div>

	<!-- Census Stat Cards -->
	{#if loading}
		<div class="flex items-center justify-center py-16">
			<Activity size={28} class="animate-spin text-blue-500" />
		</div>
	{:else if census}
		<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
			{#each cards as card, i}
				{@const Icon = card.icon}
				{@const count = getCount(card.key)}
				<button
					class="stat-card group relative flex flex-col items-start p-4 rounded-2xl border cursor-pointer"
					style="background: {card.bg}; border-color: transparent;
						--card-delay: {i * 50}ms; animation: cardIn 0.4s ease-out backwards;
						animation-delay: var(--card-delay);"
					onclick={() => openCategoryModal(card.key, card.label)}
				>
					<div class="flex items-center justify-between w-full mb-3">
						<div class="p-2 rounded-xl" style="background: {card.color}15;">
							<Icon size={18} color={card.color} />
						</div>
						<ChevronRight size={14} class="text-slate-300 group-hover:text-slate-500 transition-colors" />
					</div>
					<span class="text-2xl sm:text-3xl font-bold" style="color: {card.color};">
						{count}
					</span>
					<span class="text-xs font-medium text-slate-500 mt-1">{card.label}</span>
				</button>
			{/each}

			<!-- Total card -->
			<button
				class="stat-card group relative flex flex-col items-start p-4 rounded-2xl border cursor-pointer col-span-2 sm:col-span-1"
				style="background: linear-gradient(135deg, #1e293b, #0f172a); border-color: transparent;
					animation: cardIn 0.4s ease-out backwards; animation-delay: {cards.length * 50}ms;"
				onclick={() => goto('/mrd/census')}
			>
				<div class="flex items-center justify-between w-full mb-3">
					<div class="p-2 rounded-xl" style="background: rgba(255,255,255,0.1);">
						<BarChart3 size={18} color="#fff" />
					</div>
					<ChevronRight size={14} class="text-slate-500 group-hover:text-slate-300 transition-colors" />
				</div>
				<span class="text-2xl sm:text-3xl font-bold text-white">{census.total}</span>
				<span class="text-xs font-medium text-slate-400 mt-1">Total Records</span>
			</button>
		</div>

		<!-- Quick Actions -->
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
			<button
				class="flex items-center gap-3 p-4 rounded-2xl border border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/50 transition-colors cursor-pointer"
				style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
				onclick={() => goto('/mrd/census')}
			>
				<div class="p-2.5 rounded-xl" style="background: #eff6ff;">
					<BarChart3 size={20} class="text-blue-600" />
				</div>
				<div class="text-left">
					<p class="text-sm font-semibold text-slate-700">Detailed Census</p>
					<p class="text-xs text-slate-400">Department breakdown</p>
				</div>
			</button>
			<button
				class="flex items-center gap-3 p-4 rounded-2xl border border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/50 transition-colors cursor-pointer"
				style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
				onclick={() => goto('/mrd/patients')}
			>
				<div class="p-2.5 rounded-xl" style="background: #f0fdf4;">
					<Users size={20} class="text-green-600" />
				</div>
				<div class="text-left">
					<p class="text-sm font-semibold text-slate-700">Patient Search</p>
					<p class="text-xs text-slate-400">Find patient records</p>
				</div>
			</button>
		</div>
	{/if}
</div>

<!-- Patient list modal -->
<AquaModal
	open={modalOpen}
	title={modalTitle}
	onclose={() => (modalOpen = false)}
	panelClass="sm:max-w-lg"
>
	{#if modalLoading}
		<div class="flex justify-center py-10">
			<Activity size={22} class="animate-spin text-blue-500" />
		</div>
	{:else if modalPatients.length === 0}
		<div class="text-center py-10 text-sm text-slate-400">No records found</div>
	{:else}
		<p class="text-xs text-slate-400 mb-3">{modalPatients.length} patient(s) · Click to view case sheet</p>
		<div class="space-y-2 max-h-[60vh] overflow-y-auto">
			{#each modalPatients as p}
				<button
					class="w-full flex items-center gap-3 p-3 rounded-xl transition-all hover:scale-[1.01] active:scale-[0.99]"
					style="background: #f8fafc; border: 1px solid #e2e8f0;"
					onclick={() => openPatientSheet(p)}
				>
					<Avatar name={p.name} size="sm" />
					<div class="flex-1 text-left min-w-0">
						<div class="font-semibold text-sm text-slate-800 truncate">{p.name}</div>
						<div class="text-xs text-slate-500">{p.patient_id} · Age {p.age}</div>
						{#if p.diagnosis}
							<div class="text-xs text-slate-400 truncate">{p.diagnosis}</div>
						{/if}
					</div>
					<div class="text-right shrink-0">
						<div class="text-xs text-slate-400">{p.date}</div>
						{#if p.time}
							<div class="text-xs text-slate-400">{p.time}</div>
						{/if}
					</div>
					<ChevronRight size={16} class="text-slate-300 shrink-0" />
				</button>
			{/each}
		</div>
	{/if}
</AquaModal>

<!-- Patient Case Sheet Slide-over -->
<PatientCaseSheet
	open={caseSheetOpen}
	patient={selectedPatient}
	onclose={() => (caseSheetOpen = false)}
/>

<style>
	@keyframes cardIn {
		from { opacity: 0; transform: translateY(12px) scale(0.97); }
		to { opacity: 1; transform: translateY(0) scale(1); }
	}

	.stat-card {
		transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
	}

	@media (hover: hover) {
		.stat-card:hover {
			transform: translateY(-2px);
			box-shadow: 0 8px 24px rgba(0,0,0,0.08);
			border-color: rgba(0,0,0,0.06);
		}
	}

	.stat-card:active {
		transform: scale(0.97);
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-card { animation: none !important; transition: none !important; }
	}
</style>
