<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { adminApi, type PatientCategoryConfig } from '$lib/api/admin';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import SystemConfigTabs from '$lib/components/admin/SystemConfigTabs.svelte';
	import { Loader2, PencilLine, Plus, ShieldCheck, Star, Trash2, UsersRound } from 'lucide-svelte';

	type CategoryFormState = {
		id: string | null;
		name: string;
		description: string;
		is_active: boolean;
		sort_order: number;
	};

	const auth = get(authStore);

	let loading = $state(true);
	let saving = $state(false);
	let deletingId = $state<string | null>(null);
	let categories = $state<PatientCategoryConfig[]>([]);
	let editorOpen = $state(false);
	let form = $state<CategoryFormState>({
		id: null,
		name: '',
		description: '',
		is_active: true,
		sort_order: 0,
	});

	const totalAssignedPatients = $derived.by(() => categories.reduce((sum, item) => sum + item.patient_count, 0));
	const activeCategoryCount = $derived.by(() => categories.filter((item) => item.is_active).length);

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			void goto('/dashboard');
			return;
		}
		void loadCategories();
	});

	async function loadCategories() {
		loading = true;
		try {
			categories = await adminApi.getPatientCategories();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load patient categories', 'error');
		} finally {
			loading = false;
		}
	}

	function resetEditor() {
		editorOpen = false;
		form = {
			id: null,
			name: '',
			description: '',
			is_active: true,
			sort_order: categories.length,
		};
	}

	function openCreate() {
		form = {
			id: null,
			name: '',
			description: '',
			is_active: true,
			sort_order: categories.length,
		};
		editorOpen = true;
	}

	function openEdit(category: PatientCategoryConfig) {
		form = {
			id: category.id,
			name: category.name,
			description: category.description || '',
			is_active: category.is_active,
			sort_order: category.sort_order,
		};
		editorOpen = true;
	}

	async function saveCategory() {
		if (!form.name.trim()) {
			toastStore.addToast('Category name is required', 'error');
			return;
		}

		saving = true;
		try {
			if (form.id) {
				const updated = await adminApi.updatePatientCategory(form.id, {
					name: form.name,
					description: form.description,
					is_active: form.is_active,
					sort_order: form.sort_order,
				});
				categories = categories.map((item) => item.id === updated.id ? updated : item);
				toastStore.addToast('Patient category updated', 'success');
			} else {
				const created = await adminApi.createPatientCategory({
					name: form.name,
					description: form.description,
					is_active: form.is_active,
					sort_order: form.sort_order,
				});
				categories = [...categories, created];
				toastStore.addToast('Patient category created', 'success');
			}

			categories = [...categories].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
			resetEditor();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save patient category', 'error');
		} finally {
			saving = false;
		}
	}

	async function removeCategory(category: PatientCategoryConfig) {
		deletingId = category.id;
		try {
			const result = await adminApi.deletePatientCategory(category.id);
			categories = categories.filter((item) => item.id !== category.id);
			toastStore.addToast(result.message, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete patient category', 'error');
		} finally {
			deletingId = null;
		}
	}
</script>

<div class="space-y-4">
	<!-- <div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(247,250,255,0.96)); box-shadow: 0 12px 28px rgba(15,23,42,0.06);">
		<div class="flex items-start gap-3">
			<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
				style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid rgba(59,130,246,0.16);">
				<UsersRound class="h-5 w-5 text-blue-600" />
			</div>
			<div>
				<h2 class="text-sm font-bold uppercase tracking-[0.16em] text-slate-600">Patient Category Catalog</h2>
				<p class="mt-1 text-sm text-slate-500">Define the patient category list used for registration defaults, reporting, and future billing tiers. Classic, Prime, Elite, and Community are seeded automatically, and you can extend the list here.</p>
			</div>
		</div>
	</div> -->

	<div class="rounded-[24px] border border-slate-200 p-3"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.92), rgba(246,249,255,0.92)); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
		<SystemConfigTabs activeTab="patients" />
	</div>

	<div class="grid gap-4 md:grid-cols-3">
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Categories</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{categories.length}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{activeCategoryCount}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Assigned Patients</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{totalAssignedPatients}</p>
		</div>
	</div>

	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<button
				type="button"
				class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={openCreate}
			>
				<Plus class="h-4 w-4" />
				Add Category
			</button>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<Loader2 class="h-7 w-7 animate-spin text-blue-600" />
			</div>
		{:else}
			<div class="mt-4 overflow-x-auto rounded-[18px] border border-slate-200">
				<table class="min-w-full text-left text-sm">
					<thead style="background: linear-gradient(to bottom, rgba(241,245,249,0.98), rgba(248,250,252,0.98));">
						<tr class="text-slate-500">
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Category</th>
							<!-- <th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Description</th> -->
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Patients</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Status</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each categories as category (category.id)}
							<tr class="border-t border-slate-200 align-top">
								<td class="px-4 py-4">
									<div class="flex items-center gap-2">
										<p class="font-semibold text-slate-900">{category.name}</p>
									</div>
									{#if category.description}
										<p class="text-xs text-slate-500 mt-1">{category.description}</p>
									{/if}
								</td>
								<td class="px-4 py-4">
									<span class="text-base font-semibold text-slate-900">{category.patient_count}</span>
								</td>
								<td class="px-4 py-4">
									<span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {category.is_active ? 'text-emerald-700' : 'text-slate-500'}"
										style={category.is_active
											? 'background: rgba(16,185,129,0.14); border: 1px solid rgba(16,185,129,0.18);'
											: 'background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.14);'}>
										{category.is_active ? 'Active' : 'Inactive'}
									</span>
								</td>
								<td class="px-4 py-4">
									<div class="flex flex-wrap gap-2">
										<button type="button" class="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={() => openEdit(category)}>
											<PencilLine class="mr-1 inline h-3.5 w-3.5" /> Edit
										</button>
										<button type="button" class="rounded-full px-3 py-1.5 text-xs font-semibold text-red-600 cursor-pointer disabled:opacity-60" style="background: rgba(248,113,113,0.12);" onclick={() => removeCategory(category)} disabled={deletingId === category.id}>
											<Trash2 class="mr-1 inline h-3.5 w-3.5" /> {deletingId === category.id ? 'Removing...' : 'Delete'}
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>

	{#if editorOpen}
		<AquaModal title={form.id ? 'Edit Patient Category' : 'Add Patient Category'} onclose={resetEditor} panelClass="sm:max-w-[560px]">
			<div class="space-y-4">
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<label for="patient-category-name" class="mb-1 block text-sm font-medium text-slate-700">Name</label>
						<input id="patient-category-name" type="text" bind:value={form.name} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
					</div>
					<div>
						<label for="patient-category-order" class="mb-1 block text-sm font-medium text-slate-700">Sort Order</label>
						<input id="patient-category-order" type="number" bind:value={form.sort_order} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
					</div>
				</div>

				<div>
					<label for="patient-category-description" class="mb-1 block text-sm font-medium text-slate-700">Description</label>
					<textarea id="patient-category-description" rows="4" bind:value={form.description} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"></textarea>
				</div>

				<div class="grid gap-3 md:grid-cols-2">
					<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
						<span class="text-sm font-medium text-slate-700">Active category</span>
						<input type="checkbox" bind:checked={form.is_active} class="h-4 w-4" />
					</label>
				</div>

				<div class="flex justify-end gap-2">
					<button type="button" class="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={resetEditor}>Cancel</button>
					<button type="button" class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={saveCategory} disabled={saving}>
						{#if saving}
							<Loader2 class="h-4 w-4 animate-spin" />
						{/if}
						Save Category
					</button>
				</div>
			</div>
		</AquaModal>
	{/if}
</div>