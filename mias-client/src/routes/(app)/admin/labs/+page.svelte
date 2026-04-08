<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { labsApi, type LabInfo } from '$lib/api/labs';
	import AdminMobileScaffold from '$lib/components/layout/AdminMobileScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Search, FlaskConical, Trash2, Edit3, CheckCircle2, XCircle
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let labs: LabInfo[] = $state([]);
	let searchQuery = $state('');
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	// Create/Edit lab modal
	let labModal = $state(false);
	let editingLab: LabInfo | null = $state(null);
	let labData = $state({
		name: '',
		block: '',
		lab_type: 'General',
		department: '',
		location: '',
		contact_phone: '',
		operating_hours: '',
		is_active: true
	});
	let savingLab = $state(false);

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
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

	const filteredLabs = $derived(() => {
		if (!searchQuery) return labs;
		const q = searchQuery.toLowerCase();
		return labs.filter(l =>
			l.name.toLowerCase().includes(q) ||
			l.block?.toLowerCase().includes(q) ||
			l.department.toLowerCase().includes(q) ||
			l.lab_type.toLowerCase().includes(q)
		);
	});

	function openCreateModal() {
		editingLab = null;
		labData = {
			name: '',
			block: '',
			lab_type: 'General',
			department: '',
			location: '',
			contact_phone: '',
			operating_hours: '',
			is_active: true
		};
		labModal = true;
	}

	function openEditModal(lab: LabInfo) {
		editingLab = lab;
		labData = {
			name: lab.name,
			block: lab.block || '',
			lab_type: lab.lab_type,
			department: lab.department,
			location: lab.location || '',
			contact_phone: lab.contact_phone || '',
			operating_hours: lab.operating_hours || '',
			is_active: lab.is_active
		};
		labModal = true;
	}

	async function saveLab() {
		if (!labData.name.trim() || !labData.department.trim()) {
			toastStore.addToast('Name and department are required', 'error');
			return;
		}
		savingLab = true;
		try {
			if (editingLab) {
				await labsApi.update(editingLab.id, labData);
				toastStore.addToast('Lab updated successfully', 'success');
			} else {
				await labsApi.create(labData);
				toastStore.addToast('Lab created successfully', 'success');
			}
			labModal = false;
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save lab', 'error');
		} finally {
			savingLab = false;
		}
	}

	function deleteLab(lab: LabInfo) {
		confirmMessage = `Are you sure you want to delete "${lab.name}"?`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await labsApi.delete(lab.id);
				toastStore.addToast('Lab deleted successfully', 'success');
				await loadLabs();
			} catch (e: any) {
				toastStore.addToast(e.response?.data?.detail || 'Failed to delete lab', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}
</script>

<AdminMobileScaffold navItems={adminPageNavItems} title="Labs" activeNav="/admin/labs">
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-4 text-sm">{error}</div>
	{:else}
		<!-- Search + Create -->
		<div class="flex items-center gap-2 mb-3">
			<div class="flex-1 relative">
				<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
				<input
					type="text"
					placeholder="Search labs..."
					class="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-300"
					bind:value={searchQuery}
				/>
			</div>
			<button
				onclick={openCreateModal}
				class="px-4 py-2 text-sm font-medium text-white rounded-lg"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
			>
				+ Add
			</button>
		</div>

		<!-- Labs List -->
		<div class="space-y-2">
			{#each filteredLabs() as lab (lab.id)}
				<div
					class="flex items-center gap-3 p-3 rounded-lg border border-gray-200"
					style="background: linear-gradient(to bottom, #ffffff, #f9fafb);"
				>
					<div
						class="flex items-center justify-center rounded-full"
						style="width: 36px; height: 36px; background: linear-gradient(to bottom, #8b5cf6, #7c3aed); box-shadow: 0 1px 2px rgba(0,0,0,0.2);"
					>
						<FlaskConical class="w-5 h-5 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-0.5">
							<div class="text-sm font-semibold text-gray-900">{lab.name}</div>
							{#if lab.is_active}
								<CheckCircle2 class="w-3.5 h-3.5 text-green-600" />
							{:else}
								<XCircle class="w-3.5 h-3.5 text-gray-400" />
							{/if}
						</div>
						<div class="text-xs text-gray-600 flex items-center gap-2">
							<span>{lab.lab_type}</span>
							{#if lab.block}
								<span class="text-gray-400">•</span>
								<span>{lab.block}</span>
							{/if}
							<span class="text-gray-400">•</span>
							<span>{lab.department}</span>
						</div>
						{#if lab.operating_hours}
							<div class="text-xs text-gray-500 mt-0.5">{lab.operating_hours}</div>
						{/if}
					</div>
					<div class="flex items-center gap-1.5">
						<button
							onclick={() => openEditModal(lab)}
							class="p-1.5 rounded-lg"
							style="background: linear-gradient(to bottom, #fbbf24, #f59e0b);"
						>
							<Edit3 class="w-3.5 h-3.5 text-white" />
						</button>
						<button
							onclick={() => deleteLab(lab)}
							class="p-1.5 rounded-lg"
							style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
						>
							<Trash2 class="w-3.5 h-3.5 text-white" />
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</AdminMobileScaffold>

<!-- Create/Edit Lab Modal -->
{#if labModal}
	<AquaModal
		title={editingLab ? 'Edit Lab' : 'Create Lab'}
		onclose={() => { labModal = false; }}
	>
		<div class="space-y-3">
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Name *</label>
				<input
					type="text"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.name}
				/>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Lab Type *</label>
				<select
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.lab_type}
				>
					<option value="General">General</option>
					<option value="Pathology">Pathology</option>
					<option value="Radiology">Radiology</option>
					<option value="Microbiology">Microbiology</option>
					<option value="Biochemistry">Biochemistry</option>
					<option value="Hematology">Hematology</option>
				</select>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Department *</label>
				<input
					type="text"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.department}
				/>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Block</label>
				<input
					type="text"
					placeholder="e.g., Block C"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.block}
				/>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Location</label>
				<input
					type="text"
					placeholder="e.g., Ground Floor, Wing A"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.location}
				/>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Contact Phone</label>
				<input
					type="tel"
					placeholder="+91-44-2680-1234"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.contact_phone}
				/>
			</div>
			<div>
				<label class="block text-xs font-medium text-gray-700 mb-1">Operating Hours</label>
				<input
					type="text"
					placeholder="e.g., 24/7 or 8 AM - 6 PM"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
					bind:value={labData.operating_hours}
				/>
			</div>
			<div class="flex items-center gap-2">
				<input
					type="checkbox"
					id="lab-active"
					class="rounded"
					bind:checked={labData.is_active}
				/>
				<label for="lab-active" class="text-sm text-gray-700">Active</label>
			</div>
		</div>
		<div class="flex gap-2 mt-4">
			<button
				onclick={() => { labModal = false; }}
				class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg"
				disabled={savingLab}
			>
				Cancel
			</button>
			<button
				onclick={saveLab}
				class="flex-1 px-4 py-2 text-sm font-medium text-white rounded-lg"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				disabled={savingLab}
			>
				{savingLab ? 'Saving...' : 'Save'}
			</button>
		</div>
	</AquaModal>
{/if}

<!-- Confirm Delete Modal -->
{#if confirmModal}
	<AquaModal title="Confirm Delete" onclose={() => { confirmModal = false; }}>
		<p class="text-sm text-gray-700 mb-4">{confirmMessage}</p>
		<div class="flex gap-2">
			<button
				onclick={() => { confirmModal = false; }}
				class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg"
				disabled={actionLoading}
			>
				Cancel
			</button>
			<button
				onclick={() => confirmAction?.()}
				class="flex-1 px-4 py-2 text-sm font-medium text-white rounded-lg"
				style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
				disabled={actionLoading}
			>
				{actionLoading ? 'Deleting...' : 'Delete'}
			</button>
		</div>
	</AquaModal>
{/if}
