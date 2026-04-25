<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { otApi, type OTTheater } from '$lib/api/ot';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { Loader2, PencilLine, Plus, Power, Stethoscope, Trash2 } from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let saving = $state(false);
	let deletingId = $state<string | null>(null);
	let togglingId = $state<string | null>(null);
	let theaters = $state<OTTheater[]>([]);
	let search = $state('');
	let editorOpen = $state(false);
	const otIdCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

	function sortTheatersByOtId(items: OTTheater[]) {
		return [...items].sort((a, b) => otIdCollator.compare(a.ot_id, b.ot_id));
	}

	type OTFormState = {
		id: string | null;
		ot_id: string;
		name: string;
		location: string;
		description: string;
		is_active: boolean;
	};

	let form = $state<OTFormState>({
		id: null, ot_id: '', name: '', location: '', description: '', is_active: true,
	});

	const filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		if (!q) return theaters;
		return theaters.filter(t =>
			[t.ot_id, t.name, t.location, t.description].some(v => v?.toLowerCase().includes(q))
		);
	});
	const activeCount = $derived(theaters.filter(t => t.is_active).length);
	const locationCount = $derived(new Set(theaters.map(t => t.location).filter(Boolean)).size);

	onMount(async () => {
		if (auth.role !== 'ADMIN') return;
		try {
			theaters = sortTheatersByOtId(await otApi.listTheaters());
		} catch {
			toastStore.addToast('Failed to load OT rooms', 'error');
		} finally {
			loading = false;
		}
	});

	function openNew() {
		form = { id: null, ot_id: '', name: '', location: '', description: '', is_active: true };
		editorOpen = true;
	}

	function openEdit(t: OTTheater) {
		form = { id: t.id, ot_id: t.ot_id, name: t.name ?? '', location: t.location ?? '', description: t.description ?? '', is_active: t.is_active };
		editorOpen = true;
	}

	async function save() {
		if (!form.ot_id.trim()) {
			toastStore.addToast('OT ID is required', 'error');
			return;
		}
		saving = true;
		try {
			if (form.id) {
				const updated = await otApi.updateTheater(form.id, {
					name: form.name || undefined,
					location: form.location || undefined,
					description: form.description || undefined,
					is_active: form.is_active,
				});
				theaters = sortTheatersByOtId(theaters.map(t => t.id === updated.id ? updated : t));
				toastStore.addToast('OT updated', 'success');
			} else {
				const created = await otApi.createTheater({
					ot_id: form.ot_id.trim().toUpperCase(),
					name: form.name || undefined,
					location: form.location || undefined,
					description: form.description || undefined,
				});
				theaters = sortTheatersByOtId([...theaters, created]);
				toastStore.addToast('OT created', 'success');
			}
			editorOpen = false;
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to save', 'error');
		} finally {
			saving = false;
		}
	}

	async function toggleActive(t: OTTheater) {
		togglingId = t.id;
		try {
			const updated = await otApi.updateTheater(t.id, { is_active: !t.is_active });
			theaters = sortTheatersByOtId(theaters.map(x => x.id === updated.id ? updated : x));
		} catch {
			toastStore.addToast('Failed to update', 'error');
		} finally {
			togglingId = null;
		}
	}

	async function deleteTheater(t: OTTheater) {
		if (!confirm(`Delete ${t.ot_id}? This cannot be undone.`)) return;
		deletingId = t.id;
		try {
			await otApi.deleteTheater(t.id);
			theaters = theaters.filter(x => x.id !== t.id);
			toastStore.addToast('OT deleted', 'success');
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to delete', 'error');
		} finally {
			deletingId = null;
		}
	}
</script>

<div class="space-y-4">
	<!-- Stats -->
	<div class="grid gap-4 md:grid-cols-3">
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Total OT Rooms</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{theaters.length}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active</p>
			<p class="mt-3 text-3xl font-bold text-green-600">{activeCount}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Locations</p>
			<p class="mt-3 text-3xl font-bold text-blue-600">{locationCount}</p>
		</div>
	</div>

	<!-- Header + search -->
	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
		<div class="mb-3 flex items-center justify-between">
			<div class="flex items-center gap-2">
				<Stethoscope class="h-4 w-4 text-blue-600" />
				<span class="text-sm font-bold text-slate-800">Operation Theater Rooms</span>
			</div>
			<button
				onclick={openNew}
				class="flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold text-white"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.25);"
			>
				<Plus class="h-3.5 w-3.5" />
				Add OT
			</button>
		</div>

		<!-- Search -->
		<div class="relative">
			<input
				type="text"
				placeholder="Search OT rooms…"
				bind:value={search}
				class="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 pr-10 text-sm text-slate-800 outline-none focus:border-blue-400"
			/>
		</div>

		{#if loading}
			<div class="flex justify-center py-8">
				<Loader2 class="h-6 w-6 animate-spin text-blue-500" />
			</div>
		{:else if filtered.length === 0}
			<p class="py-8 text-center text-sm text-slate-400">
				{search ? 'No results' : 'No OT rooms yet. Click Add OT to create one.'}
			</p>
		{:else}
			<div class="mt-3 space-y-2">
				{#each filtered as t (t.id)}
					<div class="flex items-start gap-3 rounded-xl border border-slate-100 p-3"
						style="background: {t.is_active ? '#f8faff' : '#f8f8f8'};">
						<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
							style="background: linear-gradient(to bottom, {t.is_active ? '#eff6ff, #dbeafe' : '#f1f5f9, #e2e8f0'}); border: 1px solid {t.is_active ? 'rgba(59,130,246,0.2)' : 'rgba(148,163,184,0.2)'};">
							<Stethoscope class="h-4 w-4 {t.is_active ? 'text-blue-600' : 'text-slate-400'}" />
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="text-sm font-bold text-slate-800">{t.ot_id}</span>
								{#if t.name}
									<span class="text-sm text-slate-500">— {t.name}</span>
								{/if}
								<span class="ml-auto shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold {t.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}">
									{t.is_active ? 'Active' : 'Inactive'}
								</span>
							</div>
							{#if t.location}
								<p class="text-xs text-slate-500 mt-0.5">📍 {t.location}</p>
							{/if}
							{#if t.description}
								<p class="text-xs text-slate-400 mt-0.5 truncate">{t.description}</p>
							{/if}
						</div>
						<div class="flex shrink-0 items-center gap-1">
							<button
								title={t.is_active ? 'Deactivate' : 'Activate'}
								onclick={() => toggleActive(t)}
								disabled={togglingId === t.id}
								class="rounded-lg p-1.5 transition-colors hover:bg-slate-100 cursor-pointer disabled:opacity-50"
							>
								{#if togglingId === t.id}
									<Loader2 class="h-3.5 w-3.5 animate-spin text-slate-500" />
								{:else}
									<Power class="h-3.5 w-3.5 {t.is_active ? 'text-green-600' : 'text-slate-400'}" />
								{/if}
							</button>
							<button
								title="Edit"
								onclick={() => openEdit(t)}
								class="rounded-lg p-1.5 transition-colors hover:bg-blue-50 cursor-pointer"
							>
								<PencilLine class="h-3.5 w-3.5 text-blue-500" />
							</button>
							<button
								title="Delete"
								onclick={() => deleteTheater(t)}
								disabled={deletingId === t.id}
								class="rounded-lg p-1.5 transition-colors hover:bg-red-50 cursor-pointer disabled:opacity-50"
							>
								{#if deletingId === t.id}
									<Loader2 class="h-3.5 w-3.5 animate-spin text-red-400" />
								{:else}
									<Trash2 class="h-3.5 w-3.5 text-red-400" />
								{/if}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<!-- Add / Edit Modal -->
<AquaModal open={editorOpen} onclose={() => editorOpen = false}>
	{#snippet header()}
		<div class="flex items-center gap-2">
			<Stethoscope class="h-5 w-5 text-blue-600" />
			<span class="font-semibold text-slate-800">{form.id ? 'Edit OT Room' : 'Add OT Room'}</span>
		</div>
	{/snippet}
	{#snippet children()}
		<div class="space-y-4">
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="block text-sm font-medium text-slate-700 mb-1">OT ID <span class="text-red-500">*</span></label>
				<input
					type="text"
					placeholder="e.g. OT-01"
					bind:value={form.ot_id}
					disabled={!!form.id}
					class="block w-full rounded-md border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-400"
				/>
				<p class="mt-1 text-xs text-slate-400">Unique identifier like OT-01, OT-02…</p>
			</div>
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="block text-sm font-medium text-slate-700 mb-1">Name</label>
				<input type="text" placeholder="e.g. Main Surgical OT" bind:value={form.name}
					class="block w-full rounded-md border border-slate-200 px-3 py-2 text-sm" />
			</div>
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="block text-sm font-medium text-slate-700 mb-1">Location</label>
				<input type="text" placeholder="e.g. Block A – Floor 3" bind:value={form.location}
					class="block w-full rounded-md border border-slate-200 px-3 py-2 text-sm" />
			</div>
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="block text-sm font-medium text-slate-700 mb-1">Description</label>
				<textarea rows={2} placeholder="Optional notes…" bind:value={form.description}
					class="block w-full rounded-md border border-slate-200 px-3 py-2 text-sm resize-none"></textarea>
			</div>
			{#if form.id}
				<label class="flex items-center gap-2 cursor-pointer">
					<input type="checkbox" bind:checked={form.is_active} class="rounded" />
					<span class="text-sm text-slate-700">Active</span>
				</label>
			{/if}
			<div class="flex justify-end gap-2 pt-1">
				<button onclick={() => editorOpen = false}
					class="rounded-md px-4 py-2 text-sm font-medium cursor-pointer"
					style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.15);">
					Cancel
				</button>
				<button onclick={save} disabled={saving}
					class="rounded-md px-4 py-2 text-sm font-medium text-white cursor-pointer disabled:opacity-50"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); border: 1px solid rgba(0,0,0,0.2);">
					{saving ? 'Saving…' : (form.id ? 'Update' : 'Create')}
				</button>
			</div>
		</div>
	{/snippet}
</AquaModal>
