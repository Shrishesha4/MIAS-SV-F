<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { adminApi, type ICDCodeRecord } from '$lib/api/admin';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { FileText, Loader2, PencilLine, Plus, Search, Trash2 } from 'lucide-svelte';

	type ICDFormState = {
		id: string | null;
		code: string;
		description: string;
		category: string;
		is_active: boolean;
	};

	const auth = get(authStore);

	let loading = $state(true);
	let saving = $state(false);
	let deletingId = $state<string | null>(null);
	let togglingId = $state<string | null>(null);
	let codes = $state<ICDCodeRecord[]>([]);
	let search = $state('');
	let editorOpen = $state(false);
	let form = $state<ICDFormState>({
		id: null,
		code: '',
		description: '',
		category: 'General',
		is_active: true,
	});

	const filteredCodes = $derived.by(() => {
		const query = search.trim().toLowerCase();
		if (!query) {
			return codes;
		}
		return codes.filter((item) =>
			[item.code, item.description, item.category]
				.some((value) => value.toLowerCase().includes(query))
		);
	});
	const activeCodeCount = $derived.by(() => codes.filter((item) => item.is_active).length);
	const categoryCount = $derived.by(() => new Set(codes.map((item) => item.category)).size);

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			void goto('/dashboard');
			return;
		}
		void loadCodes();
	});

	async function loadCodes() {
		loading = true;
		try {
			codes = await adminApi.getICDCodes({ include_inactive: true });
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load ICD codes', 'error');
		} finally {
			loading = false;
		}
	}

	function resetEditor() {
		editorOpen = false;
		form = {
			id: null,
			code: '',
			description: '',
			category: 'General',
			is_active: true,
		};
	}

	function openCreate() {
		resetEditor();
		editorOpen = true;
	}

	function openEdit(item: ICDCodeRecord) {
		form = {
			id: item.id,
			code: item.code,
			description: item.description,
			category: item.category,
			is_active: item.is_active,
		};
		editorOpen = true;
	}

	async function saveCode() {
		if (!form.code.trim() || !form.description.trim()) {
			toastStore.addToast('ICD code and description are required', 'error');
			return;
		}

		saving = true;
		try {
			if (form.id) {
				const updated = await adminApi.updateICDCode(form.id, {
					code: form.code.trim().toUpperCase(),
					description: form.description.trim(),
					category: form.category.trim() || 'General',
					is_active: form.is_active,
				});
				codes = codes.map((item) => item.id === updated.id ? updated : item);
				toastStore.addToast('ICD code updated', 'success');
			} else {
				const created = await adminApi.createICDCode({
					code: form.code.trim().toUpperCase(),
					description: form.description.trim(),
					category: form.category.trim() || 'General',
					is_active: form.is_active,
				});
				codes = [...codes, created];
				toastStore.addToast('ICD code created', 'success');
			}

			codes = [...codes].sort((left, right) => left.code.localeCompare(right.code));
			resetEditor();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save ICD code', 'error');
		} finally {
			saving = false;
		}
	}

	async function removeCode(item: ICDCodeRecord) {
		deletingId = item.id;
		try {
			const result = await adminApi.deleteICDCode(item.id);
			codes = codes.filter((entry) => entry.id !== item.id);
			toastStore.addToast(result.message, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete ICD code', 'error');
		} finally {
			deletingId = null;
		}
	}

	async function toggleCodeActive(item: ICDCodeRecord) {
		togglingId = item.id;
		try {
			const updated = await adminApi.updateICDCode(item.id, {
				is_active: !item.is_active,
			});
			codes = codes.map((entry) => entry.id === updated.id ? updated : entry);
			toastStore.addToast(`ICD code ${updated.is_active ? 'enabled' : 'disabled'}`, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to update ICD code', 'error');
		} finally {
			togglingId = null;
		}
	}
</script>

<div class="space-y-4">
	<div class="grid gap-4 md:grid-cols-3">
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Codes</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{codes.length}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{activeCodeCount}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Categories</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{categoryCount}</p>
		</div>
	</div>

	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
		<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
			<div class="relative w-full md:max-w-md">
				<div class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">
					<Search class="h-4 w-4 text-slate-400" />
				</div>
				<input
					type="text"
					bind:value={search}
					placeholder="Search by code, disease, or category"
					class="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
				/>
			</div>
			<button
				type="button"
				class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={openCreate}
			>
				<Plus class="h-4 w-4" />
				Add ICD Code
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
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">ICD Code</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Description</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Category</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Status</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredCodes as item (item.id)}
							<tr class="border-t border-slate-200 align-top">
								<td class="px-4 py-4">
									<div class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold text-blue-700"
										style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.18);">
										<FileText class="h-3.5 w-3.5" />
										{item.code}
									</div>
								</td>
								<td class="px-4 py-4">
									<p class="font-semibold text-slate-900">{item.description}</p>
								</td>
								<td class="px-4 py-4 text-slate-600">{item.category}</td>
								<td class="px-4 py-4">
									<button
										type="button"
										role="switch"
										aria-checked={item.is_active}
										aria-label={`Toggle ${item.code} active status`}
										onclick={() => toggleCodeActive(item)}
										disabled={togglingId === item.id}
										class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
									>
										<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${item.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
											<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${item.is_active ? 'left-6' : 'left-1'}`}>
												{#if togglingId === item.id}
													<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
												{/if}
											</span>
										</span>
									</button>
								</td>
								<td class="px-4 py-4">
									<div class="flex flex-wrap gap-2">
										<button type="button" class="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={() => openEdit(item)}>
											<PencilLine class="mr-1 inline h-3.5 w-3.5" /> Edit
										</button>
										<!-- Delete ICD code action hidden until admin disable flow replaces hard delete UI. -->
										<!--
										<button type="button" class="rounded-full px-3 py-1.5 text-xs font-semibold text-red-600 cursor-pointer disabled:opacity-60" style="background: rgba(248,113,113,0.12);" onclick={() => removeCode(item)} disabled={deletingId === item.id}>
											<Trash2 class="mr-1 inline h-3.5 w-3.5" /> {deletingId === item.id ? 'Removing...' : 'Delete'}
										</button>
										-->
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
		<AquaModal title={form.id ? 'Edit ICD Code' : 'Add ICD Code'} onclose={resetEditor} panelClass="sm:max-w-[640px]">
			<div class="space-y-4">
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<label for="icd-code" class="mb-1 block text-sm font-medium text-slate-700">ICD Code</label>
						<input id="icd-code" type="text" bind:value={form.code} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-blue-300" placeholder="E11.9" />
					</div>
					<div>
						<label for="icd-category" class="mb-1 block text-sm font-medium text-slate-700">Category</label>
						<input id="icd-category" type="text" bind:value={form.category} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" placeholder="Endocrine" />
					</div>
				</div>

				<div>
					<label for="icd-description" class="mb-1 block text-sm font-medium text-slate-700">Description</label>
					<textarea id="icd-description" rows="5" bind:value={form.description} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" placeholder="Type 2 diabetes mellitus without complications"></textarea>
				</div>

				<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
					<span class="text-sm font-medium text-slate-700">Active code</span>
					<input type="checkbox" bind:checked={form.is_active} class="h-4 w-4" />
				</label>

				<div class="flex justify-end gap-2">
					<button type="button" class="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={resetEditor}>Cancel</button>
					<button type="button" class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={saveCode} disabled={saving}>
						{#if saving}
							<Loader2 class="h-4 w-4 animate-spin" />
						{/if}
						Save ICD Code
					</button>
				</div>
			</div>
		</AquaModal>
	{/if}
</div>
