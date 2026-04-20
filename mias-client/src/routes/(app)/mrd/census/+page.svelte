<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { mrdApi, type DepartmentRow, type CensusPatient, type MrdLab } from '$lib/api/mrd';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import PatientCaseSheet from '$lib/components/mrd/PatientCaseSheet.svelte';
	import {
		Activity, ChevronRight, Clock, Download
	} from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let departments: DepartmentRow[] = $state.raw([]);
	let investigationTypes: string[] = $state.raw([]);
	let labs: MrdLab[] = $state.raw([]);
	let snapshotInfo = $state('');

	let fromDate = $state(new Date().toISOString().split('T')[0]);
	let toDate = $state(new Date().toISOString().split('T')[0]);

	// Modal
	let modalOpen = $state(false);
	let modalTitle = $state('');
	let modalPatients: CensusPatient[] = $state([]);
	let modalLoading = $state(false);

	// Case sheet
	let caseSheetOpen = $state(false);
	let selectedPatient = $state<{
		id: string; patient_id: string; name: string;
		age?: number; diagnosis?: string; department?: string;
	} | null>(null);

	// Fixed columns (always shown)
	const fixedColumns = [
		{ key: 'op', label: 'OP', category: 'op' },
		{ key: 'ip', label: 'IP', category: 'ip' },
		{ key: 'ot', label: 'OT', category: 'ot' },
		{ key: 'births', label: 'Births', category: 'births' },
		{ key: 'deaths', label: 'Deaths', category: 'deaths' },
	];

	// Dynamic columns derived from investigation_types
	const dynamicInvColumns = $derived(
		investigationTypes.map(t => ({ key: `inv_${t}`, label: t, type: t }))
	);

	async function fetchBreakdown() {
		loading = true;
		try {
			const [bd, health, labsRes] = await Promise.all([
				mrdApi.getDepartmentBreakdown({ from_date: fromDate, to_date: toDate }),
				mrdApi.getHealth(),
				mrdApi.getLabs(),
			]);
			departments = bd.departments;
			investigationTypes = bd.investigation_types;
			labs = labsRes.labs;
			if (health.snapshot_age_hours !== null) {
				snapshotInfo = `${health.snapshot_age_hours.toFixed(1)}h ago`;
			}
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to load breakdown', 'error');
		} finally {
			loading = false;
		}
	}

	async function openCellModal(dept: string, category: string, label: string) {
		const categoryMap: Record<string, string> = {
			op: 'op', ip: 'ip', ot: 'ot',
			births: 'births', deaths: 'deaths',
			inv_total: 'investigations', discharges: 'discharges',
		};
		const apiCategory = categoryMap[category] || 'investigations';

		modalTitle = `${dept} — ${label}`;
		modalOpen = true;
		modalLoading = true;
		modalPatients = [];
		try {
			const res = await mrdApi.getCensusPatients({
				category: apiCategory as any,
				from_date: fromDate, to_date: toDate,
				department: dept === 'Grand Total' ? undefined : dept,
				page_size: 50,
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

	function getInvCount(dept: DepartmentRow, invType: string): number {
		return dept.inv_by_type?.[invType] ?? 0;
	}

	onMount(() => {
		if (auth.role !== 'MRD') { goto('/dashboard'); return; }
		fetchBreakdown();
	});
</script>

<div class="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-5">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
		<div class="flex items-center gap-3">
			<button class="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer" onclick={() => goto('/mrd/dashboard')}>
				← Back
			</button>
			<div>
				<h1 class="text-xl font-bold text-slate-800">Department Census</h1>
				<p class="text-sm text-slate-500">Breakdown by department · {investigationTypes.length} investigation types</p>
			</div>
		</div>
		{#if snapshotInfo}
			<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
				style="background: #fef3c7; color: #92400e;">
				<Clock size={12} />
				<span>Data: {snapshotInfo}</span>
			</div>
		{/if}
	</div>

	<!-- Date Range -->
	<div class="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"
		style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
		<div class="flex flex-col sm:flex-row sm:items-end gap-3">
			<div class="flex-1 grid grid-cols-2 gap-3">
				<div>
					<label for="census-from" class="block text-[11px] font-medium text-slate-500 mb-1">From</label>
					<input id="census-from" type="date" bind:value={fromDate}
						class="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border-color: #e2e8f0; background: #f8fafc;" />
				</div>
				<div>
					<label for="census-to" class="block text-[11px] font-medium text-slate-500 mb-1">To</label>
					<input id="census-to" type="date" bind:value={toDate}
						class="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2 focus:ring-blue-200"
						style="border-color: #e2e8f0; background: #f8fafc;" />
				</div>
			</div>
			<AquaButton variant="primary" size="sm" onclick={fetchBreakdown} {loading}>
				Update
			</AquaButton>
		</div>
	</div>

	<!-- Table -->
	{#if loading}
		<div class="flex items-center justify-center py-16">
			<Activity size={28} class="animate-spin text-blue-500" />
		</div>
	{:else}
		<div class="rounded-2xl overflow-hidden bg-white border border-slate-200"
			style="box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr style="background: linear-gradient(to bottom, #1e40af, #1e3a8a);">
							<th class="text-left px-4 py-3 text-white font-semibold sticky left-0 z-10"
								style="background: #1e3a8a; min-width: 150px;">
								Department
							</th>
							{#each fixedColumns as col}
								<th class="text-center px-3 py-3 text-white font-semibold whitespace-nowrap" style="min-width: 56px;">
									{col.label}
								</th>
							{/each}
							<!-- Dynamic investigation type columns -->
							{#each dynamicInvColumns as col}
								<th class="text-center px-3 py-3 font-semibold whitespace-nowrap" style="min-width: 64px; color: #bfdbfe;">
									{col.label}
								</th>
							{/each}
							<th class="text-center px-3 py-3 text-white font-semibold whitespace-nowrap" style="min-width: 56px;">
								Inv Total
							</th>
							<th class="text-center px-3 py-3 text-white font-semibold whitespace-nowrap" style="min-width: 56px;">
								Dis
							</th>
						</tr>
					</thead>
					<tbody>
						{#each departments as dept, i}
							{@const isGrandTotal = dept.department === 'Grand Total'}
							<tr
								class="table-row-anim {isGrandTotal ? 'font-bold' : ''}"
								style="background: {isGrandTotal ? '#f0f9ff' : i % 2 === 0 ? '#ffffff' : '#f8fafc'};
									{isGrandTotal ? 'border-top: 2px solid #3b82f6;' : ''}
									animation: rowIn 0.3s ease-out backwards; animation-delay: {i * 30}ms;"
							>
								<td class="px-4 py-2.5 sticky left-0 z-10 font-medium truncate"
									style="background: inherit; max-width: 180px; color: {isGrandTotal ? '#1e40af' : '#1e293b'};">
									{dept.department || 'Unknown'}
								</td>
								<!-- Fixed columns -->
								{#each fixedColumns as col}
									{@const val = (dept as any)[col.key] ?? 0}
									<td class="text-center px-3 py-2.5">
										{#if val > 0}
											<button
												class="inline-flex items-center justify-center min-w-[32px] px-2 py-1 rounded-lg text-xs font-semibold transition-all hover:scale-105 active:scale-95 cursor-pointer"
												style="background: {col.key === 'deaths' ? '#fee2e2' : col.key === 'births' ? '#dcfce7' : '#dbeafe'}; color: {col.key === 'deaths' ? '#991b1b' : col.key === 'births' ? '#166534' : '#1e40af'};"
												onclick={() => openCellModal(dept.department, col.category, col.label)}
											>
												{val}
											</button>
										{:else}
											<span class="text-slate-300">0</span>
										{/if}
									</td>
								{/each}
								<!-- Dynamic investigation columns -->
								{#each dynamicInvColumns as col}
									{@const val = getInvCount(dept, col.type)}
									<td class="text-center px-3 py-2.5">
										{#if val > 0}
											<button
												class="inline-flex items-center justify-center min-w-[32px] px-2 py-1 rounded-lg text-xs font-semibold transition-all hover:scale-105 active:scale-95 cursor-pointer"
												style="background: #ede9fe; color: #5b21b6;"
												onclick={() => openCellModal(dept.department, 'inv_total', col.label)}
											>
												{val}
											</button>
										{:else}
											<span class="text-slate-300">0</span>
										{/if}
									</td>
								{/each}
								<!-- Inv Total -->
								<td class="text-center px-3 py-2.5">
									{#if dept.inv_total > 0}
										<button
											class="inline-flex items-center justify-center min-w-[32px] px-2 py-1 rounded-lg text-xs font-semibold transition-all hover:scale-105 active:scale-95 cursor-pointer"
											style="background: #dbeafe; color: #1e40af;"
											onclick={() => openCellModal(dept.department, 'inv_total', 'Investigations')}
										>
											{dept.inv_total}
										</button>
									{:else}
										<span class="text-slate-300">0</span>
									{/if}
								</td>
								<!-- Discharges -->
								<td class="text-center px-3 py-2.5">
									{#if dept.discharges > 0}
										<button
											class="inline-flex items-center justify-center min-w-[32px] px-2 py-1 rounded-lg text-xs font-semibold transition-all hover:scale-105 active:scale-95 cursor-pointer"
											style="background: #dbeafe; color: #1e40af;"
											onclick={() => openCellModal(dept.department, 'discharges', 'Discharges')}
										>
											{dept.discharges}
										</button>
									{:else}
										<span class="text-slate-300">0</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Export -->
		<AquaButton variant="secondary" onclick={() => goto('/mrd/exports')}>
			<div class="flex items-center gap-2">
				<Download size={16} />
				Export Census Data
			</div>
		</AquaButton>
	{/if}
</div>

<!-- Patient modal -->
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
					<ChevronRight size={16} class="text-slate-300 shrink-0" />
				</button>
			{/each}
		</div>
	{/if}
</AquaModal>

<!-- Case Sheet -->
<PatientCaseSheet
	open={caseSheetOpen}
	patient={selectedPatient}
	onclose={() => (caseSheetOpen = false)}
/>

<style>
	@keyframes rowIn {
		from { opacity: 0; transform: translateX(-8px); }
		to { opacity: 1; transform: translateX(0); }
	}

	@media (prefers-reduced-motion: reduce) {
		.table-row-anim { animation: none !important; }
	}
</style>
