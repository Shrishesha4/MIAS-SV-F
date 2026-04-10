<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Search, Building2, Trash2, Edit3, CheckCircle2, XCircle
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let clinics: ClinicInfo[] = $state([]);
	let searchQuery = $state('');
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	// Create/Edit clinic modal
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

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
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

	const filteredClinics = $derived(() => {
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
		clinicData = {
			name: '',
			block: '',
			clinic_type: 'General',
			department: '',
			location: '',
			is_active: true
		};
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
			toastStore.addToast('Please fill in all required fields', 'error');
			return;
		}
		
		savingClinic = true;
		try {
			if (editingClinic) {
				await clinicsApi.updateClinic(editingClinic.id, clinicData);
				toastStore.addToast('Clinic updated successfully', 'success');
			} else {
				await clinicsApi.createClinic(clinicData);
				toastStore.addToast('Clinic created successfully', 'success');
			}
			clinicModal = false;
			await loadClinics();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save clinic', 'error');
		} finally {
			savingClinic = false;
		}
	}

	async function deleteClinic(clinic: ClinicInfo) {
		confirmMessage = `Permanently delete "${clinic.name}"? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await clinicsApi.deleteClinic(clinic.id);
				toastStore.addToast('Clinic deleted successfully', 'success');
				await loadClinics();
			} catch (e: any) {
				error = e.response?.data?.detail || 'Delete failed';
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
			toastStore.addToast(e.response?.data?.detail || 'Action failed', 'error');
		}
	}
</script>

<AdminScaffold
	title="Hospital Clinics"
	titleIcon={Building2}
	navItems={adminPageNavItems}
	activeNav="clinics"
	backHref="/admin"
>
	<div class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Hospital Clinics</h2>
				<p class="mt-0.5 text-[11px] text-slate-500">{clinics.length} total clinics</p>
			</div>
			<button
				onclick={openCreateModal}
				class="px-3 py-1.5 rounded-xl text-xs font-semibold text-white cursor-pointer shadow-md"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
			>
				Add New
			</button>
		</div>

		<div class="relative">
			<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
			<input
				type="text"
				placeholder="Search by name, block, or department..."
				bind:value={searchQuery}
				class="w-full pl-9 pr-3 py-2 rounded-2xl text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
				style="background: white; box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
			/>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
			</div>
		{:else if error}
			<div class="p-4 rounded-xl bg-white shadow-md">
				<p class="text-red-500 text-center py-4">{error}</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each filteredClinics() as clinic}
					<div class="p-3 rounded-xl bg-white shadow-md flex items-center gap-2.5">
						<div class="w-11 h-11 flex items-center justify-center rounded-full shrink-0" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
							<Building2 class="w-5 h-5 text-white" />
						</div>

						<div class="flex-1 min-w-0">
							<p class="text-sm font-bold text-gray-900 truncate">{clinic.name}</p>
							<p class="text-xs text-blue-600 font-semibold truncate uppercase">
								{#if clinic.block}{clinic.block} • {/if}{clinic.clinic_type}
								{#if !clinic.is_active} • <span class="text-red-600">Inactive</span>{/if}
							</p>
						</div>

						<div class="flex items-center gap-1 shrink-0">
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-blue-50"
								title="Edit"
								onclick={() => openEditModal(clinic)}
							>
								<Edit3 class="w-3.5 h-3.5 text-blue-500" />
							</button>
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-100"
								title={clinic.is_active ? 'Deactivate' : 'Activate'}
								onclick={() => toggleActive(clinic)}
							>
								{#if clinic.is_active}
									<CheckCircle2 class="w-3.5 h-3.5 text-green-500" />
								{:else}
									<XCircle class="w-3.5 h-3.5 text-orange-500" />
								{/if}
							</button>
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-red-50"
								title="Delete"
								onclick={() => deleteClinic(clinic)}
							>
								<Trash2 class="w-3.5 h-3.5 text-red-400" />
							</button>
						</div>
					</div>
				{/each}

				{#if filteredClinics().length === 0}
					<div class="text-center py-12 text-gray-400 text-sm">
						{searchQuery ? 'No clinics match your search' : 'No clinics found'}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</AdminScaffold>

{#if clinicModal}
	<AquaModal title={editingClinic ? 'Edit Clinic' : 'Create New Clinic'} onclose={() => clinicModal = false}>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="space-y-4 p-4">
			<div>
				<label class="block text-sm font-medium text-gray-700 mb-1">Clinic Name *</label>
				<input
					type="text"
					bind:value={clinicData.name}
					placeholder="e.g., Saveetha General Clinic"
					class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
				/>
			</div>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Block</label>
					<input
						type="text"
						bind:value={clinicData.block}
						placeholder="e.g., Block A"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Type</label>
					<select
						bind:value={clinicData.clinic_type}
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
					>
						<option value="General">General</option>
						<option value="Specialty">Specialty</option>
						<option value="Emergency">Emergency</option>
					</select>
				</div>
			</div>

			<div>
				<label class="block text-sm font-medium text-gray-700 mb-1">Department *</label>
				<input
					type="text"
					bind:value={clinicData.department}
					placeholder="e.g., General Medicine"
					class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
				/>
			</div>

			<div>
				<label class="block text-sm font-medium text-gray-700 mb-1">Location</label>
				<input
					type="text"
					bind:value={clinicData.location}
					placeholder="e.g., Ground Floor, Wing A"
					class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
				/>
			</div>

			<div class="flex items-center gap-2">
				<input
					type="checkbox"
					id="is_active"
					bind:checked={clinicData.is_active}
					class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
				/>
				<label for="is_active" class="text-sm text-gray-700">Active</label>
			</div>

			<div class="flex gap-3 pt-2">
				<button
					onclick={() => clinicModal = false}
					class="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50"
					disabled={savingClinic}
				>
					Cancel
				</button>
				<button
					onclick={saveClinic}
					disabled={savingClinic}
					class="flex-1 px-4 py-2 rounded-lg text-white font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				>
					{savingClinic ? 'Saving...' : (editingClinic ? 'Update' : 'Create')}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if confirmModal}
	<AquaModal title="Confirm Action" onclose={() => confirmModal = false}>
		<div class="p-4">
			<p class="text-gray-700 mb-6">{confirmMessage}</p>
			<div class="flex gap-3">
				<button
					onclick={() => confirmModal = false}
					class="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-50"
					disabled={actionLoading}
				>
					Cancel
				</button>
				<button
					onclick={confirmAction}
					disabled={actionLoading}
					class="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 cursor-pointer"
				>
					{actionLoading ? 'Processing...' : 'Confirm'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}
