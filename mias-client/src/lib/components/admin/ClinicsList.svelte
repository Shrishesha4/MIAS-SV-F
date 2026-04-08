<script lang="ts">
	import { onMount } from 'svelte';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { Building2, Search, Edit3, Trash2, CheckCircle2, XCircle, Plus } from 'lucide-svelte';

	let loading = $state(true);
	let error = $state('');
	let clinics: ClinicInfo[] = $state([]);
	let searchQuery = $state('');

	// Modal states
	let clinicModal = $state(false);
	let editingClinic: ClinicInfo | null = $state(null);
	let clinicData = $state({
		name: '',
		block: '',
		clinic_type: 'General',
		department: '',
		location: '',
		is_active: true
	});
	let savingClinic = $state(false);

	// Confirm modal
	let confirmModal = $state(false);
	let confirmMessage = $state('');
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let actionLoading = $state(false);

	onMount(() => {
		loadClinics();
	});

	async function loadClinics() {
		loading = true;
		error = '';
		try {
			clinics = await clinicsApi.listClinics();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load clinics';
		} finally {
			loading = false;
		}
	}

	const filteredClinics = $derived.by(() => {
		if (!searchQuery) return clinics;
		const q = searchQuery.toLowerCase();
		return clinics.filter(c =>
			c.name.toLowerCase().includes(q) ||
			c.block?.toLowerCase().includes(q) ||
			c.department.toLowerCase().includes(q)
		);
	});

	function openCreateModal() {
		editingClinic = null;
		clinicData = { name: '', block: '', clinic_type: 'General', department: '', location: '', is_active: true };
		clinicModal = true;
	}

	function openEditModal(clinic: ClinicInfo) {
		editingClinic = clinic;
		clinicData = {
			name: clinic.name,
			block: clinic.block || '',
			clinic_type: clinic.clinic_type,
			department: clinic.department,
			location: clinic.location || '',
			is_active: clinic.is_active
		};
		clinicModal = true;
	}

	async function saveClinic() {
		if (!clinicData.name || !clinicData.department) {
			toastStore.addToast('Name and department are required', 'error');
			return;
		}
		savingClinic = true;
		try {
			if (editingClinic) {
				await clinicsApi.updateClinic(editingClinic.id, clinicData);
				toastStore.addToast('Clinic updated', 'success');
			} else {
				await clinicsApi.createClinic(clinicData);
				toastStore.addToast('Clinic created', 'success');
			}
			clinicModal = false;
			await loadClinics();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save', 'error');
		} finally {
			savingClinic = false;
		}
	}

	async function deleteClinic(clinic: ClinicInfo) {
		confirmMessage = `Delete "${clinic.name}"? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await clinicsApi.deleteClinic(clinic.id);
				toastStore.addToast('Clinic deleted', 'success');
				await loadClinics();
			} catch (e: any) {
				toastStore.addToast(e.response?.data?.detail || 'Delete failed', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function toggleActive(clinic: ClinicInfo) {
		try {
			await clinicsApi.updateClinic(clinic.id, { is_active: !clinic.is_active });
			toastStore.addToast(`Clinic ${clinic.is_active ? 'deactivated' : 'activated'}`, 'success');
			await loadClinics();
		} catch (e: any) {
			toastStore.addToast('Action failed', 'error');
		}
	}
</script>

<div class="space-y-3">
	<!-- Header -->
	<div class="flex items-center justify-between gap-2">
		<div>
			<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Clinics</h2>
			<p class="mt-0.5 text-[11px] text-slate-500">{clinics.length} total</p>
		</div>
		<button
			onclick={openCreateModal}
			class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
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
			placeholder="Search clinics..."
			bind:value={searchQuery}
			class="w-full pl-9 pr-3 py-2 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
			style="background: white;"
		/>
	</div>

	<!-- List -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin w-7 h-7 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-6 text-sm">{error}</div>
	{:else}
		<div class="space-y-2">
			{#each filteredClinics as clinic (clinic.id)}
				<div class="p-3 rounded-xl bg-white shadow-sm border border-gray-100 flex items-center gap-2.5">
					<div class="w-10 h-10 flex items-center justify-center rounded-full shrink-0" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
						<Building2 class="w-5 h-5 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<p class="text-sm font-semibold text-gray-900 truncate">{clinic.name}</p>
						<p class="text-xs text-gray-500 truncate">
							{#if clinic.block}{clinic.block} • {/if}{clinic.clinic_type} • {clinic.department}
							{#if !clinic.is_active}<span class="text-red-500 ml-1">• Inactive</span>{/if}
						</p>
					</div>
					<div class="flex items-center gap-1 shrink-0">
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-blue-50" onclick={() => openEditModal(clinic)} title="Edit">
							<Edit3 class="w-3.5 h-3.5 text-blue-500" />
						</button>
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-100" onclick={() => toggleActive(clinic)} title={clinic.is_active ? 'Deactivate' : 'Activate'}>
							{#if clinic.is_active}
								<CheckCircle2 class="w-3.5 h-3.5 text-green-500" />
							{:else}
								<XCircle class="w-3.5 h-3.5 text-orange-500" />
							{/if}
						</button>
						<button class="p-1.5 rounded-lg cursor-pointer hover:bg-red-50" onclick={() => deleteClinic(clinic)} title="Delete">
							<Trash2 class="w-3.5 h-3.5 text-red-400" />
						</button>
					</div>
				</div>
			{/each}
			{#if filteredClinics.length === 0}
				<div class="text-center py-10 text-gray-400 text-sm">
					{searchQuery ? 'No clinics match your search' : 'No clinics yet'}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Create/Edit Modal -->
{#if clinicModal}
	<AquaModal title={editingClinic ? 'Edit Clinic' : 'New Clinic'} onclose={() => clinicModal = false}>
		<div class="space-y-3 p-1">
			<div>
				<label for="clinic-name" class="block text-xs font-medium text-gray-700 mb-1">Clinic Name *</label>
				<input id="clinic-name" type="text" bind:value={clinicData.name} placeholder="Saveetha General Clinic" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500" />
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div>
					<label for="clinic-block" class="block text-xs font-medium text-gray-700 mb-1">Block</label>
					<input id="clinic-block" type="text" bind:value={clinicData.block} placeholder="Block A" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500" />
				</div>
				<div>
					<label for="clinic-type" class="block text-xs font-medium text-gray-700 mb-1">Type</label>
					<select id="clinic-type" bind:value={clinicData.clinic_type} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500">
						<option value="General">General</option>
						<option value="Specialty">Specialty</option>
						<option value="Emergency">Emergency</option>
					</select>
				</div>
			</div>
			<div>
				<label for="clinic-dept" class="block text-xs font-medium text-gray-700 mb-1">Department *</label>
				<input id="clinic-dept" type="text" bind:value={clinicData.department} placeholder="General Medicine" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500" />
			</div>
			<div>
				<label for="clinic-location" class="block text-xs font-medium text-gray-700 mb-1">Location</label>
				<input id="clinic-location" type="text" bind:value={clinicData.location} placeholder="Ground Floor, Wing A" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-blue-500" />
			</div>
			<div class="flex items-center gap-2">
				<input type="checkbox" id="clinic-active" bind:checked={clinicData.is_active} class="rounded" />
				<label for="clinic-active" class="text-sm text-gray-700">Active</label>
			</div>
			<div class="flex gap-2 pt-2">
				<button onclick={() => clinicModal = false} class="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium text-sm cursor-pointer" disabled={savingClinic}>Cancel</button>
				<button onclick={saveClinic} disabled={savingClinic} class="flex-1 px-4 py-2 rounded-lg text-white font-medium text-sm cursor-pointer" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
					{savingClinic ? 'Saving...' : 'Save'}
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
