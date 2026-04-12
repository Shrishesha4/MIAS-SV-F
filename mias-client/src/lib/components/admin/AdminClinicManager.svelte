<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import { insuranceCategoriesApi, type WalkInType } from '$lib/api/insuranceCategories';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { Building2, PencilLine, Plus, Trash2 } from 'lucide-svelte';

	const auth = get(authStore);
	const clinicTypeOptions = ['IP', 'OP', 'ER'];

	// Walk-in types - fetched dynamically
	let walkInTypes = $state<WalkInType[]>([]);

	let loading = $state(true);
	let error = $state('');
	let clinics: ClinicInfo[] = $state([]);
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	let clinicModal = $state(false);
	let editingClinic: ClinicInfo | null = $state(null);
	let clinicData = $state({
		name: '',
		block: '',
		clinic_type: 'OP',
		access_mode: 'WALK_IN' as ClinicInfo['access_mode'],
		walk_in_type: 'NO_WALK_IN',
		department: '',
		location: '',
		is_active: true
	});
	let savingClinic = $state(false);

	function clinicAccessModeLabel(accessMode: ClinicInfo['access_mode']) {
		if (accessMode === 'APPOINTMENT_ONLY') return 'Appointment Only';
		return 'Walk-In Clinic';
	}

	async function loadWalkInTypes() {
		try {
			walkInTypes = await insuranceCategoriesApi.getWalkInTypes();
		} catch (e) {
			console.error('Failed to load walk-in types:', e);
		}
	}

	const clinicCards = $derived.by(() =>
		clinics.map((clinic) => ({
			clinic,
			description: [clinic.location, clinic.department, clinic.block].filter(Boolean).join(' • ') || 'Clinic service',
			accessModeLabel: clinicAccessModeLabel(clinic.access_mode)
		}))
	);

	function upsertClinic(updatedClinic: ClinicInfo) {
		const clinicIndex = clinics.findIndex((clinic) => clinic.id === updatedClinic.id);

		if (clinicIndex === -1) {
			clinics = [updatedClinic, ...clinics];
			return;
		}

		clinics = clinics.map((clinic) => (clinic.id === updatedClinic.id ? { ...clinic, ...updatedClinic } : clinic));
	}

	function removeClinic(clinicId: string) {
		clinics = clinics.filter((clinic) => clinic.id !== clinicId);
	}

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}

		loadClinics();
		loadWalkInTypes();
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

	function openCreateModal() {
		editingClinic = null;
		clinicData = {
			name: '',
			block: '',
			clinic_type: 'OP',
			access_mode: 'WALK_IN',
			walk_in_type: 'NO_WALK_IN',
			department: '',
			location: '',
			is_active: true
		};
		clinicModal = true;
	}

	async function openEditModal(clinic: ClinicInfo) {
		editingClinic = clinic;
		clinicData = {
			name: clinic.name,
			block: clinic.block || '',
			clinic_type: clinicTypeOptions.includes(clinic.clinic_type) ? clinic.clinic_type : 'OP',
			access_mode: clinic.access_mode || 'WALK_IN',
			walk_in_type: (clinic as any).walk_in_type || 'NO_WALK_IN',
			department: clinic.department || '',
			location: clinic.location || '',
			is_active: clinic.is_active ?? true
		};
		clinicModal = true;
	}

	async function saveClinic() {
		if (!clinicData.name.trim()) {
			toastStore.addToast('Clinic name is required', 'error');
			return;
		}

		savingClinic = true;
		try {
			const payload = {
				name: clinicData.name.trim(),
				block: clinicData.block.trim() || undefined,
				clinic_type: clinicData.clinic_type,
				access_mode: clinicData.access_mode,
				walk_in_type: clinicData.walk_in_type,
				department: clinicData.department.trim() || undefined,
				location: clinicData.location.trim() || undefined,
				is_active: clinicData.is_active
			};
			let savedClinic: ClinicInfo;

			if (editingClinic) {
				savedClinic = await clinicsApi.updateClinic(editingClinic.id, payload);
				upsertClinic(savedClinic);
			} else {
				savedClinic = await clinicsApi.createClinic(payload);
				upsertClinic(savedClinic);
			}

			toastStore.addToast(editingClinic ? 'Clinic updated successfully' : 'Clinic created successfully', 'success');
			clinicModal = false;
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
				removeClinic(clinic.id);
				toastStore.addToast('Clinic deleted successfully', 'success');
			} catch (e: any) {
				error = e.response?.data?.detail || 'Delete failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function runConfirmAction() {
		if (!confirmAction) {
			return;
		}

		await confirmAction();
	}

	async function toggleActive(clinic: ClinicInfo) {
		try {
			const updatedClinic = await clinicsApi.updateClinic(clinic.id, { is_active: !clinic.is_active });
			upsertClinic(updatedClinic);
			toastStore.addToast(`Clinic ${clinic.is_active ? 'deactivated' : 'activated'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Action failed', 'error');
		}
	}
</script>

<div class="space-y-4 lg:space-y-5">
	<div class="flex items-center justify-between gap-3">
		<div>
			<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Hospital Clinics</h2>
			<p class="mt-1 text-xs text-slate-500 lg:hidden">{clinics.length} clinics configured</p>
		</div>
		<button
			onclick={openCreateModal}
			class="flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-white cursor-pointer lg:px-4"
			style="background: linear-gradient(to bottom, #3c8af4, #1667d8); box-shadow: 0 3px 8px rgba(22,103,216,0.24), inset 0 1px 0 rgba(255,255,255,0.22);"
		>
			<Plus class="h-3.5 w-3.5" />
			<span>Add New</span>
		</button>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="h-8 w-8 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600"></div>
		</div>
	{:else if error}
		<div class="rounded-[18px] border px-6 py-10 text-center" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
			<p class="text-sm font-semibold text-rose-500">{error}</p>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-3 xl:grid-cols-2">
			{#each clinicCards as item (item.clinic.id)}
				<div
					class="min-h-[92px] rounded-[18px] border px-4 py-4 transition-transform hover:-translate-y-[1px]"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);"
				>
					<div class="flex items-start gap-3">
						<div
							class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
							style="background: linear-gradient(to bottom, #3c8af4, #1667d8); box-shadow: 0 4px 10px rgba(20,95,210,0.24), inset 0 1px 0 rgba(255,255,255,0.3);"
						>
							<Building2 class="h-5 w-5 text-white" />
						</div>

						<div class="min-w-0 flex-1">
							<h3 class="truncate text-[15px] font-bold text-slate-900">{item.clinic.name}</h3>
							<div class="mt-1 flex items-center gap-2">
								<span class="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600">{item.clinic.clinic_type}</span>
								<span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600">{item.accessModeLabel}</span>
								{#if !item.clinic.is_active}
									<span class="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600">Inactive</span>
								{/if}
							</div>
							<p class="mt-1 truncate text-xs text-slate-500">{item.description}</p>
						</div>

						<div class="flex shrink-0 items-center gap-2">
							<button
								type="button"
								class="relative flex h-6 w-11 items-center rounded-full p-[2px] cursor-pointer transition-colors"
								style={item.clinic.is_active
									? 'background: linear-gradient(to bottom, #34d399, #10b981); box-shadow: inset 0 1px 0 rgba(255,255,255,0.32);'
									: 'background: linear-gradient(to bottom, #d7dee8, #bcc7d5); box-shadow: inset 0 1px 0 rgba(255,255,255,0.62);'}
								title={item.clinic.is_active ? 'Deactivate clinic' : 'Activate clinic'}
								onclick={() => toggleActive(item.clinic)}
							>
								<span
									class="h-5 w-5 rounded-full bg-white shadow-sm transition-transform"
									style={item.clinic.is_active ? 'transform: translateX(20px);' : 'transform: translateX(0);'}
								></span>
							</button>
							<button
								type="button"
								class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer hover:bg-slate-100"
								title="Edit clinic"
								onclick={() => openEditModal(item.clinic)}
							>
								<PencilLine class="h-4 w-4 text-slate-400" />
							</button>
							<button
								type="button"
								class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer hover:bg-rose-50"
								title="Delete clinic"
								onclick={() => deleteClinic(item.clinic)}
							>
								<Trash2 class="h-4 w-4 text-rose-400" />
							</button>
						</div>
					</div>
				</div>
			{/each}

			{#if clinicCards.length === 0}
				<div class="rounded-[18px] border px-6 py-12 text-center xl:col-span-2" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
					<Building2 class="mx-auto mb-3 h-12 w-12 text-blue-300" />
					<p class="text-sm font-semibold text-slate-500">No clinics configured yet</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

{#if clinicModal}
	<AquaModal title={editingClinic ? 'Edit Clinic' : 'Create New Clinic'} onclose={() => clinicModal = false}>
		<div class="space-y-4">
			<div>
				<label for="clinic-name" class="mb-1 block text-sm font-medium text-gray-700">Clinic Name *</label>
				<input
					id="clinic-name"
					type="text"
					bind:value={clinicData.name}
					placeholder="e.g. Saveetha General Clinic"
					class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
				/>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div>
					<label for="clinic-block" class="mb-1 block text-sm font-medium text-gray-700">Block</label>
					<input
						id="clinic-block"
						type="text"
						bind:value={clinicData.block}
						placeholder="e.g. Block A"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>

				<div>
					<label for="clinic-type" class="mb-1 block text-sm font-medium text-gray-700">Type</label>
					<select
						id="clinic-type"
						bind:value={clinicData.clinic_type}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					>
						{#each clinicTypeOptions as clinicType}
							<option value={clinicType}>{clinicType}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div>
					<label for="clinic-department" class="mb-1 block text-sm font-medium text-gray-700">Department</label>
					<input
						id="clinic-department"
						type="text"
						bind:value={clinicData.department}
						placeholder="e.g. General Medicine"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>

				<div>
					<label for="clinic-location" class="mb-1 block text-sm font-medium text-gray-700">Location</label>
					<input
						id="clinic-location"
						type="text"
						bind:value={clinicData.location}
						placeholder="e.g. Ground Floor, Wing A"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>
			</div>

			<!-- Walk-in Type -->
			<div class="border-t border-gray-200 pt-4 mt-2">
				<label for="walk-in-type" class="block text-sm font-medium text-gray-700 mb-2">Walk-in Type</label>
				<select
					id="walk-in-type"
					bind:value={clinicData.walk_in_type}
					class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
				>
					{#each walkInTypes as type}
						<option value={type.value}>{type.label}</option>
					{/each}
				</select>
				<p class="mt-1 text-xs text-gray-500">The walk-in type for this clinic</p>
			</div>

			<label class="flex items-center gap-2 text-sm text-gray-700 mt-4">
				<input
					type="checkbox"
					bind:checked={clinicData.is_active}
					class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
				/>
				<span>Active</span>
			</label>

			<div class="flex gap-3 pt-2">
				<button
					type="button"
					onclick={() => clinicModal = false}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
					disabled={savingClinic}
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={saveClinic}
					disabled={savingClinic}
					class="flex-1 rounded-lg px-4 py-2 font-medium text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				>
					{savingClinic ? 'Saving...' : editingClinic ? 'Update' : 'Create'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if confirmModal}
	<AquaModal title="Confirm Action" onclose={() => confirmModal = false}>
		<div class="space-y-6">
			<p class="text-sm text-gray-700">{confirmMessage}</p>
			<div class="flex gap-3">
				<button
					type="button"
					onclick={() => confirmModal = false}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
					disabled={actionLoading}
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={runConfirmAction}
					disabled={actionLoading}
					class="flex-1 rounded-lg bg-red-600 px-4 py-2 font-medium text-white hover:bg-red-700 cursor-pointer"
				>
					{actionLoading ? 'Processing...' : 'Confirm'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}