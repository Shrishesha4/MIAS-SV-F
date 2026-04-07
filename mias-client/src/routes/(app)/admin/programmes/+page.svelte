<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type Programme } from '$lib/api/admin';
	import AdminMobileScaffold from '$lib/components/layout/AdminMobileScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		BookOpen, Plus, Edit3, Trash2, Users, CheckCircle
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let programmes: Programme[] = $state([]);

	// Form state
	let showForm = $state(false);
	let editingId = $state('');
	let formName = $state('');
	let formCode = $state('');
	let formDescription = $state('');
	let formDegreeType = $state('');
	let formDuration = $state('');
	let formLoading = $state(false);
	let formError = $state('');

	// Delete confirm
	let deleteModal = $state(false);
	let deletingProg: Programme | null = $state(null);
	let deleteLoading = $state(false);

	const degreeTypes = ['Undergraduate', 'Postgraduate', 'Diploma', 'Certificate', 'Doctoral'];

	onMount(async () => {
		if (auth.role !== 'ADMIN') { window.location.href = '/dashboard'; return; }
		await loadData();
	});

	async function loadData() {
		loading = true;
		try {
			programmes = await adminApi.getProgrammes();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load programmes';
		} finally {
			loading = false;
		}
	}

	function openCreate() {
		editingId = '';
		formName = '';
		formCode = '';
		formDescription = '';
		formDegreeType = '';
		formDuration = '';
		formError = '';
		showForm = true;
	}

	function openEdit(prog: Programme) {
		editingId = prog.id;
		formName = prog.name;
		formCode = prog.code;
		formDescription = prog.description || '';
		formDegreeType = prog.degree_type || '';
		formDuration = prog.duration_years || '';
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
				degree_type: formDegreeType || undefined,
				duration_years: formDuration.trim() || undefined,
			};
			if (editingId) {
				await adminApi.updateProgramme(editingId, data);
			} else {
				await adminApi.createProgramme(data as any);
			}
			showForm = false;
			await loadData();
		} catch (e: any) {
			formError = e.response?.data?.detail || 'Failed to save';
		} finally {
			formLoading = false;
		}
	}

	function confirmDelete(prog: Programme) {
		deletingProg = prog;
		deleteModal = true;
	}

	async function doDelete() {
		if (!deletingProg) return;
		deleteLoading = true;
		try {
			await adminApi.deleteProgramme(deletingProg.id);
			deleteModal = false;
			await loadData();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Deactivate failed';
		} finally {
			deleteLoading = false;
		}
	}
</script>

<AdminMobileScaffold
	title="System Administration"
	titleIcon={BookOpen}
	navItems={adminPageNavItems}
	activeNav="programmes"
	backHref="/admin"
>
	<div class="space-y-4">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-sm font-bold uppercase tracking-[0.18em] text-slate-600">Programmes</h2>
				<p class="mt-1 text-xs text-slate-500">{programmes.length} academic programmes configured</p>
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
			{#each programmes as prog}
				<AquaCard>
					<div class="flex items-start gap-3">
						<div
							class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
							style="background: linear-gradient(135deg, {prog.is_active ? '#3b82f6' : '#9ca3af'}, {prog.is_active ? '#2563eb' : '#6b7280'});"
						>
							<BookOpen class="w-5 h-5 text-white" />
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<h3 class="text-sm font-semibold text-blue-900">{prog.name}</h3>
								<span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono">{prog.code}</span>
								{#if !prog.is_active}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700">Inactive</span>
								{/if}
							</div>
							{#if prog.description}
								<p class="text-xs text-gray-500 mt-0.5">{prog.description}</p>
							{/if}
							<div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
								{#if prog.degree_type}
									<span class="flex items-center gap-1">
										<CheckCircle class="w-3 h-3 text-green-500" />
										{prog.degree_type}
									</span>
								{/if}
								{#if prog.duration_years}
									<span>{prog.duration_years}</span>
								{/if}
								<span class="flex items-center gap-1">
									<Users class="w-3 h-3" />
									{prog.student_count} students
								</span>
							</div>
						</div>
						<div class="flex gap-1 shrink-0">
							<button class="p-2 rounded-lg cursor-pointer hover:bg-gray-100" onclick={() => openEdit(prog)}>
								<Edit3 class="w-4 h-4 text-blue-500" />
							</button>
							<button class="p-2 rounded-lg cursor-pointer hover:bg-red-50" onclick={() => confirmDelete(prog)}>
								<Trash2 class="w-4 h-4 text-red-400" />
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}

			{#if programmes.length === 0}
				<div class="text-center py-12">
					<BookOpen class="w-12 h-12 text-gray-300 mx-auto mb-3" />
					<p class="text-gray-400 text-sm">No programmes yet</p>
					<AquaButton size="sm" onclick={openCreate}>
						<span>Create First Programme</span>
					</AquaButton>
				</div>
			{/if}
		</div>
	{/if}
	</div>
</AdminMobileScaffold>

<!-- Create/Edit Programme Modal -->
{#if showForm}
	<AquaModal title={editingId ? 'Edit Programme' : 'New Programme'} onclose={() => showForm = false}>
		<div class="p-4 space-y-4">
			{#if formError}
				<p class="text-red-500 text-sm bg-red-50 rounded-lg p-2">{formError}</p>
			{/if}
			<div>
				<label for="prog-name" class="text-xs font-medium text-gray-600 block mb-1">Name *</label>
				<input
					id="prog-name"
					type="text"
					bind:value={formName}
					placeholder="e.g. BDS"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>
			<div>
				<label for="prog-code" class="text-xs font-medium text-gray-600 block mb-1">Code *</label>
				<input
					id="prog-code"
					type="text"
					bind:value={formCode}
					placeholder="e.g. BDS"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 uppercase"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>
			<div>
				<label for="prog-desc" class="text-xs font-medium text-gray-600 block mb-1">Description</label>
				<textarea
					id="prog-desc"
					bind:value={formDescription}
					placeholder="Optional description..."
					rows="2"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 resize-none"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				></textarea>
			</div>
			<div>
				<label for="prog-degree" class="text-xs font-medium text-gray-600 block mb-1">Degree Type</label>
				<select
					id="prog-degree"
					bind:value={formDegreeType}
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 bg-white"
				>
					<option value="">Select type</option>
					{#each degreeTypes as dt}
						<option value={dt}>{dt}</option>
					{/each}
				</select>
			</div>
			<div>
				<label for="prog-dur" class="text-xs font-medium text-gray-600 block mb-1">Duration</label>
				<input
					id="prog-dur"
					type="text"
					bind:value={formDuration}
					placeholder="e.g. 4 years"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400"
					style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>
			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => showForm = false}>
					Cancel
				</AquaButton>
				<AquaButton fullWidth loading={formLoading} onclick={submitForm}>
					{editingId ? 'Update' : 'Create'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

<!-- Delete Confirm Modal -->
{#if deleteModal && deletingProg}
	<AquaModal title="Deactivate Programme" onclose={() => deleteModal = false}>
		<div class="p-4 space-y-4">
			<p class="text-sm text-gray-600">
				Are you sure you want to deactivate <strong>{deletingProg.name}</strong>?
				This will hide it from registration forms.
			</p>
			<div class="flex gap-2">
				<AquaButton variant="secondary" fullWidth onclick={() => deleteModal = false}>
					Cancel
				</AquaButton>
				<AquaButton variant="danger" fullWidth loading={deleteLoading} onclick={doDelete}>
					Deactivate
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
