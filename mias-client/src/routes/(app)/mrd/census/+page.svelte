<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { mrdApi, type DepartmentRow, type CensusPatient } from '$lib/api/mrd';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		BarChart3, Activity, ChevronRight, Clock, Download
	} from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let departments: DepartmentRow[] = $state([]);
	let snapshotInfo = $state('');

	let fromDate = $state(new Date().toISOString().split('T')[0]);
	let toDate = $state(new Date().toISOString().split('T')[0]);

	// Modal
	let modalOpen = $state(false);
	let modalTitle = $state('');
	let modalPatients: CensusPatient[] = $state([]);
	let modalLoading = $state(false);

	const columns = [
		{ key: 'op', label: 'OP' },
		{ key: 'ip', label: 'IP' },
		{ key: 'ot', label: 'OT' },
		{ key: 'inv_total', label: 'Inv' },
		{ key: 'discharges', label: 'Dis' },
	];

	async function fetchBreakdown() {
		loading = true;
		try {
			const [bd, health] = await Promise.all([
				mrdApi.getDepartmentBreakdown({ from_date: fromDate, to_date: toDate }),
				mrdApi.getHealth(),
			]);
			departments = bd.departments;
			if (health.snapshot_age_hours !== null) {
				snapshotInfo = `Snapshot as of ${health.snapshot_age_hours}h ago`;
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
			inv_total: 'investigations', discharges: 'discharges',
		};
		const apiCategory = categoryMap[category];
		if (!apiCategory) return;

		modalTitle = `${dept} - ${label} Records`;
		modalOpen = true;
		modalLoading = true;
		modalPatients = [];
		try {
			const res = await mrdApi.getCensusPatients({
				category: apiCategory as any,
				from_date: fromDate,
				to_date: toDate,
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

	function navigateToPatient(patientId: string) {
		modalOpen = false;
		goto(`/mrd/patients?id=${patientId}`);
	}

	onMount(() => {
		if (auth.role !== 'MRD') {
			goto('/dashboard');
			return;
		}
		fetchBreakdown();
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

	<!-- Date range + Update -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<BarChart3 size={18} class="text-blue-600" />
				<span class="font-semibold text-sm">Detailed Census</span>
			</div>
		{/snippet}
		<div class="flex gap-2 items-end">
			<div class="flex-1">
				<label for="mrd-census-from-date" class="text-xs text-gray-500 block mb-1">From</label>
				<input id="mrd-census-from-date" type="date" bind:value={fromDate}
					class="w-full px-3 py-2 rounded-lg border text-sm"
					style="border-color: #d1d5db; background: #f9fafb;" />
			</div>
			<div class="flex-1">
				<label for="mrd-census-to-date" class="text-xs text-gray-500 block mb-1">To</label>
				<input id="mrd-census-to-date" type="date" bind:value={toDate}
					class="w-full px-3 py-2 rounded-lg border text-sm"
					style="border-color: #d1d5db; background: #f9fafb;" />
			</div>
			<AquaButton variant="primary" size="sm" onclick={fetchBreakdown} {loading}>
				Update
			</AquaButton>
		</div>
	</AquaCard>

	<!-- Department Breakdown Table -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<Activity size={24} class="animate-spin text-blue-500" />
		</div>
	{:else}
		<div class="rounded-xl overflow-hidden" style="border: 1px solid #e2e8f0;">
			<div class="overflow-x-auto">
				<table class="w-full text-xs">
					<thead>
						<tr style="background: linear-gradient(to bottom, #1e40af, #1e3a8a);">
							<th class="text-left px-3 py-2.5 text-white font-semibold sticky left-0"
								style="background: #1e3a8a; min-width: 100px;">
								Department
							</th>
							{#each columns as col}
								<th class="text-center px-2 py-2.5 text-white font-semibold" style="min-width: 44px;">
									{col.label}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each departments as dept, i}
							{@const isGrandTotal = dept.department === 'Grand Total'}
							<tr
								class="{isGrandTotal ? 'font-bold' : ''}"
								style="background: {isGrandTotal ? '#f0f9ff' : i % 2 === 0 ? '#ffffff' : '#f8fafc'};
									{isGrandTotal ? 'border-top: 2px solid #3b82f6;' : ''}"
							>
								<td class="px-3 py-2 sticky left-0 font-medium truncate"
									style="background: inherit; max-width: 120px; color: {isGrandTotal ? '#1e40af' : '#1e293b'};">
									{dept.department || 'Unknown'}
								</td>
								{#each columns as col}
									{@const val = (dept as any)[col.key] ?? 0}
									<td class="text-center px-2 py-2">
										{#if val > 0}
											<button
												class="inline-flex items-center justify-center min-w-[28px] px-1.5 py-0.5 rounded-md text-xs font-semibold transition-colors"
												style="background: #dbeafe; color: #1e40af; cursor: pointer;"
												onclick={() => openCellModal(dept.department, col.key, col.label)}
											>
												{val}
											</button>
										{:else}
											<span class="text-gray-300">0</span>
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Export button -->
		<AquaButton variant="secondary" fullWidth onclick={() => goto('/mrd/exports')}>
			<div class="flex items-center justify-center gap-2">
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
