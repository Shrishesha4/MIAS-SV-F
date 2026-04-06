<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type Department, type FacultyItem } from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Building, Plus, Edit3, Trash2, ChevronLeft, Users, CheckCircle
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let departments: Department[] = $state([]);
	let facultyList: FacultyItem[] = $state([]);

	// Form state
	let showForm = $state(false);
	let editingId = $state('');
	let formName = $state('');
	let formCode = $state('');
	let formDescription = $state('');
	let formHeadFacultyId = $state('');
	let formLoading = $state(false);
	let formError = $state('');

	// Delete confirm
	let deleteModal = $state(false);
	let deletingDept: Department | null = $state(null);
	let deleteLoading = $state(false);

	onMount(async () => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		await loadData();
	});

	async function loadData() {
		loading = true;
		try {
			const [d, f] = await Promise.all([
				adminApi.getDepartments(),
				adminApi.getFaculty(),
			]);
			departments = d;
			facultyList = f;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load departments';
		} finally {
			loading = false;
		}
	}

	function openCreate() {
		editingId = '';
		formName = '';
		formCode = '';
		formDescription = '';
		formHeadFacultyId = '';
		formError = '';
		showForm = true;
	}

	function openEdit(dept: Department) {
		editingId = dept.id;
		formName = dept.name;
		formCode = dept.code;
		formDescription = dept.description || '';
		formHeadFacultyId = dept.head_faculty_id || '';
		formError = '';
		showForm = true;
	}

	async function submitForm() {
		if (!formName.trim() || !formCode.trim()) {
			formError = 'Name and code are required';
			return;
		}
		formLoading = true;
		formError = '';
		try {
			const data = {
				name: formName.trim(),
				code: formCode.trim(),
				description: formDescription.trim() || undefined,
				head_faculty_id: formHeadFacultyId || undefined,
			};
			if (editingId) {
				await adminApi.updateDepartment(editingId, data);
			} else {
				await adminApi.createDepartment(data as any);
			}
			showForm = false;
			await loadData();
		} catch (e: any) {
			formError = e.response?.data?.detail || 'Failed to save';
		} finally {
			formLoading = false;
		}
	}

	function confirmDelete(dept: Department) {
		deletingDept = dept;
		deleteModal = true;
	}

	async function doDelete() {
		if (!deletingDept) return;
		deleteLoading = true;
		try {
			await adminApi.deleteDepartment(deletingDept.id);
			deleteModal = false;
			await loadData();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Deactivate failed';
		} finally {
			deleteLoading = false;
		}
	}
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4 max-w-4xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<button class="text-blue-600 cursor-pointer" onclick={() => goto('/admin')}>
				<ChevronLeft class="w-5 h-5" />
			</button>
			<div>
				<h1 class="text-lg font-bold text-blue-900">Departments</h1>
				<p class="text-xs text-gray-500">{departments.length} departments</p>
			</div>
		</div>
		<AquaButton size="sm" onclick={openCreate}>
			<div class="flex items-center gap-1">
				<Plus class="w-4 h-4" />
				<span>Add</span>
			</div>
		</AquaButton>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<AquaCard>
			<p class="text-red-500 text-center py-4">{error}</p>
		</AquaCard>
	{:else}
		<div class="space-y-3">
			{#each departments as dept}
				<AquaCard>
					<div class="flex items-start gap-3">
						<div
							class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
							style="background: linear-gradient(135deg, {dept.is_active ? '#8b5cf6' : '#9ca3af'}, {dept.is_active ? '#6d28d9' : '#6b7280'});"
						>
							<Building class="w-5 h-5 text-white" />
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<h3 class="text-sm font-semibold text-blue-900">{dept.name}</h3>
								<span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono">{dept.code}</span>
								{#if !dept.is_active}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">Inactive</span>
								{/if}
							</div>
							{#if dept.description}
								<p class="text-xs text-gray-500 mt-0.5">{dept.description}</p>
							{/if}
							<div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
								<span class="flex items-center gap-1">
									<Users class="w-3 h-3" />
									{dept.faculty_count} faculty
								</span>
								{#if dept.head_faculty_name}
									<span class="flex items-center gap-1">
										<CheckCircle class="w-3 h-3 text-green-500" />
										Head: {dept.head_faculty_name}
									</span>
								{/if}
							</div>
						</div>
						<div class="flex gap-1 shrink-0">
							<button class="p-2 rounded-lg cursor-pointer hover:bg-gray-100" onclick={() => openEdit(dept)}>
								<Edit3 class="w-4 h-4 text-blue-500" />
							</button>
							<button class="p-2 rounded-lg cursor-pointer hover:bg-red-50" onclick={() => confirmDelete(dept)}>
								<Trash2 class="w-4 h-4 text-red-400" />
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}

			{#if departments.length === 0}
				<div class="text-center py-12">
					<Building class="w-12 h-12 text-gray-300 mx-auto mb-3" />
					<p class="text-gray-400 text-sm">No departments yet</p>
					<AquaButton size="sm" onclick={openCreate}>
						<span>Create First Department</span>
					</AquaButton>
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Create/Edit Department Modal -->
{#if showForm}
	<AquaModal title={editingId ? 'Edit Department' : 'New Department'} onclose={() => showForm = false}>
		<div class="p-4 space-y-4">
			{#if formError}
				<p class="text-red-500 text-sm bg-red-50 rounded-lg p-2">{formError}</p>
			{/if}
			<div>
				<label for="dept-name" class="text-xs font-medium text-gray-600 block mb-1">Name *</label>
				<input
					id="dept-name"
					type="text"
					bind:value={formName}
					placeholder="e.g. Cardiology"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>
			<div>
				<label for="dept-code" class="text-xs font-medium text-gray-600 block mb-1">Code *</label>
				<input
					id="dept-code"
					type="text"
					bind:value={formCode}
					placeholder="e.g. CARD"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 uppercase"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>
			<div>
				<label for="dept-desc" class="text-xs font-medium text-gray-600 block mb-1">Description</label>
				<textarea
					id="dept-desc"
					bind:value={formDescription}
					placeholder="Optional description..."
					rows="2"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 resize-none"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				></textarea>
			</div>
			<div>
				<label for="dept-head" class="text-xs font-medium text-gray-600 block mb-1">Head of Department</label>
				<select
					id="dept-head"
					bind:value={formHeadFacultyId}
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 bg-white"
				>
					<option value="">None</option>
					{#each facultyList as f}
						<option value={f.id}>{f.name} – {f.department}</option>
					{/each}
				</select>
			</div>
			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => showForm = false}>
					Cancel
				</AquaButton>
				<AquaButton fullWidth disabled={formLoading} onclick={submitForm}>
					{formLoading ? 'Saving...' : editingId ? 'Update' : 'Create'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

<!-- Delete Confirm Modal -->
{#if deleteModal && deletingDept}
	<AquaModal title="Deactivate Department" onclose={() => deleteModal = false}>
		<div class="p-4 space-y-4">
			<p class="text-sm text-gray-700">
				Deactivate department <strong>{deletingDept.name}</strong>?
				Faculty members won't be removed.
			</p>
			<div class="flex gap-2">
				<AquaButton variant="secondary" fullWidth onclick={() => deleteModal = false}>
					Cancel
				</AquaButton>
				<AquaButton variant="danger" fullWidth disabled={deleteLoading} onclick={doDelete}>
					{deleteLoading ? 'Deactivating...' : 'Deactivate'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
