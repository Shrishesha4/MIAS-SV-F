<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type Department } from '$lib/api/admin';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		ChevronRight, Plus, Stethoscope, Trash2
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let departments: Department[] = $state([]);

	// Form state
	let showForm = $state(false);
	let editingId = $state('');
	let formName = $state('');
	let formCode = $state('');
	let formDescription = $state('');
	let formLoading = $state(false);
	let formError = $state('');

	// Delete confirm
	let deleteModal = $state(false);
	let deletingDept: Department | null = $state(null);
	let deleteLoading = $state(false);

	onMount(async () => {
		if (auth.role !== 'ADMIN') { window.location.href = '/dashboard'; return; }
		await loadData();
	});

	async function loadData() {
		loading = true;
		try {
			const d = await adminApi.getDepartments();
			departments = d;
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
		formError = '';
		showForm = true;
	}

	function openEdit(dept: Department) {
		editingId = dept.id;
		formName = dept.name;
		formCode = dept.code;
		formDescription = dept.description || '';
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

<AdminScaffold
	title="Medical Departments"
	titleIcon={Stethoscope}
	navItems={adminPageNavItems}
	activeNav="departments"
	backHref="/admin"
>
	<div class="space-y-4 lg:space-y-5">
		<div class="flex items-center justify-between gap-3">
			<div>
				<h2 class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 lg:text-[13px]">Medical Departments</h2>
				<p class="mt-1 text-xs text-slate-500 lg:hidden">{departments.length} departments configured</p>
			</div>
			<button
				onclick={openCreate}
				class="flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-white cursor-pointer lg:px-4"
				style="background: linear-gradient(to bottom, #3c8af4, #1667d8); box-shadow: 0 3px 8px rgba(22,103,216,0.24), inset 0 1px 0 rgba(255,255,255,0.22);"
			>
				<Plus class="h-3.5 w-3.5" />
				<span>Add New</span>
			</button>
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
			{#each departments as dept (dept.id)}
				<div
					class="group flex items-center gap-4 rounded-[18px] border px-4 py-4 cursor-pointer transition-transform hover:-translate-y-[1px]"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);"
					role="button"
					tabindex="0"
					onclick={() => openEdit(dept)}
					onkeydown={(event) => {
						if (event.key === 'Enter' || event.key === ' ') {
							event.preventDefault();
							openEdit(dept);
						}
					}}
				>
					<div
						class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
						style="background: linear-gradient(180deg, ${dept.is_active ? '#b26eff' : '#b5bcc8'} 0%, ${dept.is_active ? '#7b23df' : '#7f8a99'} 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);"
					>
						<Stethoscope class="h-5 w-5 text-white" />
					</div>

					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<h3 class="truncate text-[15px] font-bold text-slate-900">{dept.name}</h3>
							{#if !dept.is_active}
								<span class="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600">Inactive</span>
							{/if}
						</div>
						<p class="mt-0.5 text-[10px] font-bold uppercase tracking-[0.18em] text-violet-600">Medical Department</p>
						{#if dept.description}
							<p class="mt-1 truncate text-xs text-slate-500">{dept.description}</p>
						{/if}
					</div>

					<div class="flex items-center gap-2 shrink-0">
						<button
							class="hidden h-8 w-8 items-center justify-center rounded-full cursor-pointer opacity-0 transition-opacity hover:bg-rose-50 group-hover:flex group-hover:opacity-100"
							onclick={(event) => { event.stopPropagation(); confirmDelete(dept); }}
						>
							<Trash2 class="h-4 w-4 text-rose-500" />
						</button>
						<ChevronRight class="h-4 w-4 text-slate-300 transition-colors group-hover:text-slate-500" />
					</div>
				</div>
			{/each}

			{#if departments.length === 0}
				<div class="rounded-[18px] border px-6 py-12 text-center" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
					<Stethoscope class="mx-auto mb-3 h-12 w-12 text-violet-300" />
					<p class="text-sm font-semibold text-slate-500">No departments yet</p>
					<AquaButton size="sm" onclick={openCreate}>
						<span>Create First Department</span>
					</AquaButton>
				</div>
			{/if}
		</div>
	{/if}
	</div>
</AdminScaffold>

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
