<script lang="ts">
	import { onMount } from 'svelte';
	import { labsApi, type LabInfo } from '$lib/api/labs';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { FlaskConical, Search, Edit3, Trash2, CheckCircle2, XCircle, Plus } from 'lucide-svelte';

	let loading = $state(true);
	let error = $state('');
	let labs: LabInfo[] = $state([]);
	let searchQuery = $state('');

	// Modal states
	let labModal = $state(false);
	let editingLab: LabInfo | null = $state(null);
	let labData = $state({
		name: '',
		block: '',
		lab_type: 'Pathology',
		department: '',
		location: '',
		contact_phone: '',
		operating_hours: '',
		is_active: true
	});
	let savingLab = $state(false);

	// Confirm modal
	let confirmModal = $state(false);
	let confirmMessage = $state('');
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let actionLoading = $state(false);

	onMount(() => {
		loadLabs();
	});

	async function loadLabs() {
		loading = true;
		error = '';
		try {
			labs = await labsApi.getAll();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load labs';
		} finally {
			loading = false;
		}
	}

	const filteredLabs = $derived.by(() => {
		if (!searchQuery) return labs;
		const q = searchQuery.toLowerCase();
		return labs.filter(l =>
			l.name.toLowerCase().includes(q) ||
			l.block?.toLowerCase().includes(q) ||
			l.lab_type.toLowerCase().includes(q) ||
			l.department?.toLowerCase().includes(q)
		);
	});

	function openCreateModal() {
		editingLab = null;
		labData = { name: '', block: '', lab_type: 'Pathology', department: '', location: '', contact_phone: '', operating_hours: '', is_active: true };
		labModal = true;
	}

	function openEditModal(lab: LabInfo) {
		editingLab = lab;
		labData = {
			name: lab.name,
			block: lab.block || '',
			lab_type: lab.lab_type,
			department: lab.department || '',
			location: lab.location || '',
			contact_phone: lab.contact_phone || '',
			operating_hours: lab.operating_hours || '',
			is_active: lab.is_active
		};
		labModal = true;
	}

	async function saveLab() {
		if (!labData.name || !labData.lab_type) {
			toastStore.addToast('Name and type are required', 'error');
			return;
		}
		savingLab = true;
		try {
			if (editingLab) {
				await labsApi.update(editingLab.id, labData);
				toastStore.addToast('Lab updated', 'success');
			} else {
				await labsApi.create(labData);
				toastStore.addToast('Lab created', 'success');
			}
			labModal = false;
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save', 'error');
		} finally {
			savingLab = false;
		}
	}

	async function deleteLab(lab: LabInfo) {
		confirmMessage = `Delete "${lab.name}"? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await labsApi.delete(lab.id);
				toastStore.addToast('Lab deleted', 'success');
				await loadLabs();
			} catch (e: any) {
				toastStore.addToast(e.response?.data?.detail || 'Delete failed', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function toggleActive(lab: LabInfo) {
		try {
			await labsApi.update(lab.id, { is_active: !lab.is_active });
			toastStore.addToast(`Lab ${lab.is_active ? 'deactivated' : 'activated'}`, 'success');
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast('Action failed', 'error');
		}
	}
</script>

<div class="space-y-3">
	<!-- Header -->
	<div class="flex items-center justify-between gap-2">
		<div>
			<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Labs</h2>
			<p class="mt-0.5 text-[11px] text-slate-500">{labs.length} total</p>
		</div>
		<button
			onclick={openCreateModal}
			class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #8b5cf6, #7c3aed); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
		>
			<Plus class="w-3.5 h-3.5" />
			Add
		</button>
	</div>

	<!-- Search -->
	<div class="relative">
		<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
		<input
			type="text"
			placeholder="Search labs..."
			bind:value={searchQuery}
			class="w-full pl-9 pr-3 py-2 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-purple-400"
			style="background: white;"
		/>
	</div>

	<!-- List -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin w-7 h-7 border-3 border-purple-200 border-t-purple-600 rounded-full"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-6 text-sm">{error}</div>
	{:else}
		<div class="space-y-2">
			{#each filteredLabs as lab (lab.id)}
				<div class="p-3 rounded-xl bg-white shadow-sm border border-gray-100 flex items-center gap-2.5">
					<div class="w-10 h-10 flex items-center justify-center rounded-full shrink-0" style="background: linear-gradient(to bottom, #8b5cf6, #7c3aed);">
						<FlaskConical class="w-5 h-5 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-sm font-semibold text-gray-900 truncate">{lab.name}</p>
						<p class="text-xs text-gray-500 truncate">
							{#if lab.block}{lab.block} • {/if}{lab.lab_type}
							{#if lab.operating_hours} • {lab.operating_hours}{/if}
							{#if !lab.is_active}<span class="text-red-500 ml-1">• Inactive</span>{/if}
						</p>
					</div>
					<div class="flex items-center gap-1 shrink-0">
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-purple-50" onclick={() => openEditModal(lab)} title="Edit">
							<Edit3 class="w-3.5 h-3.5 text-purple-500" />
						</button>
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-100" onclick={() => toggleActive(lab)} title={lab.is_active ? 'Deactivate' : 'Activate'}>
							{#if lab.is_active}
								<CheckCircle2 class="w-3.5 h-3.5 text-green-500" />
							{:else}
								<XCircle class="w-3.5 h-3.5 text-orange-500" />
							{/if}
						</button>
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-red-50" onclick={() => deleteLab(lab)} title="Delete">
							<Trash2 class="w-3.5 h-3.5 text-red-400" />
						</button>
					</div>
				</div>
			{/each}
			{#if filteredLabs.length === 0}
				<div class="text-center py-10 text-gray-400 text-sm">
					{searchQuery ? 'No labs match your search' : 'No labs yet'}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Create/Edit Modal -->
{#if labModal}
	<AquaModal title={editingLab ? 'Edit Lab' : 'New Lab'} onclose={() => labModal = false}>
		<div class="space-y-3 p-1">
			<div>
				<label for="lab-name" class="block text-xs font-medium text-gray-700 mb-1">Lab Name *</label>
				<input id="lab-name" type="text" bind:value={labData.name} placeholder="Central Pathology Lab" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div>
					<label for="lab-block" class="block text-xs font-medium text-gray-700 mb-1">Block</label>
					<input id="lab-block" type="text" bind:value={labData.block} placeholder="Block B" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
				</div>
				<div>
					<label for="lab-type" class="block text-xs font-medium text-gray-700 mb-1">Type *</label>
					<select id="lab-type" bind:value={labData.lab_type} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500">
						<option value="Pathology">Pathology</option>
						<option value="Radiology">Radiology</option>
						<option value="Microbiology">Microbiology</option>
						<option value="Biochemistry">Biochemistry</option>
						<option value="Hematology">Hematology</option>
					</select>
				</div>
			</div>
			<div>
				<label for="lab-dept" class="block text-xs font-medium text-gray-700 mb-1">Department</label>
				<input id="lab-dept" type="text" bind:value={labData.department} placeholder="Diagnostics" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
			</div>
			<div>
				<label for="lab-location" class="block text-xs font-medium text-gray-700 mb-1">Location</label>
				<input id="lab-location" type="text" bind:value={labData.location} placeholder="Ground Floor, Block B" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div>
					<label for="lab-phone" class="block text-xs font-medium text-gray-700 mb-1">Contact Phone</label>
					<input id="lab-phone" type="text" bind:value={labData.contact_phone} placeholder="+91 44 2681 xxxx" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
				</div>
				<div>
					<label for="lab-hours" class="block text-xs font-medium text-gray-700 mb-1">Operating Hours</label>
					<input id="lab-hours" type="text" bind:value={labData.operating_hours} placeholder="8am - 8pm" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-purple-500" />
				</div>
			</div>
			<div class="flex items-center gap-2">
				<input type="checkbox" id="lab-active" bind:checked={labData.is_active} class="rounded" />
				<label for="lab-active" class="text-sm text-gray-700">Active</label>
			</div>
			<div class="flex gap-2 pt-2">
				<button onclick={() => labModal = false} class="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium text-sm cursor-pointer" disabled={savingLab}>Cancel</button>
				<button onclick={saveLab} disabled={savingLab} class="flex-1 px-4 py-2 rounded-lg text-white font-medium text-sm cursor-pointer" style="background: linear-gradient(to bottom, #8b5cf6, #7c3aed);">
					{savingLab ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

<!-- Confirm Delete Modal -->
{#if confirmModal}
	<AquaModal title="Confirm Delete" onclose={() => confirmModal = false}>
		<p class="text-sm text-gray-700 mb-4">{confirmMessage}</p>
		<div class="flex gap-2">
			<button onclick={() => confirmModal = false} class="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium text-sm cursor-pointer" disabled={actionLoading}>Cancel</button>
			<button onclick={() => confirmAction?.()} disabled={actionLoading} class="flex-1 px-4 py-2 rounded-lg text-white font-medium text-sm cursor-pointer" style="background: linear-gradient(to bottom, #ef4444, #dc2626);">
				{actionLoading ? 'Deleting...' : 'Delete'}
			</button>
		</div>
	</AquaModal>
{/if}
