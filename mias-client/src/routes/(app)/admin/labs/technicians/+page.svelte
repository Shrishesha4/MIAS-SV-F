<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { labTechnicianApi, type LabTechnicianGroupSummary, type LabTechnicianProfile } from '$lib/api/lab-technicians';
	import { labsApi, type LabInfo } from '$lib/api/labs';
	import { toastStore } from '$lib/stores/toast';
	import { Search, Save, Trash2, RefreshCw, Users, Layers3, FlaskConical, ShieldCheck, Plus, CheckCircle2, Circle, ArrowLeft, UserRound } from 'lucide-svelte';

	const auth = get(authStore);

	type GroupForm = {
		name: string;
		description: string;
		technician_ids: string[];
		lab_ids: string[];
		is_active: boolean;
	};

	function createEmptyGroupForm(): GroupForm {
		return {
			name: '',
			description: '',
			technician_ids: [],
			lab_ids: [],
			is_active: true,
		};
	}

	let loading = $state(true);
	let saving = $state(false);
	let deleting = $state(false);
	let error = $state('');
	let searchQuery = $state('');
	let technicians = $state.raw<LabTechnicianProfile[]>([]);
	let groups = $state.raw<LabTechnicianGroupSummary[]>([]);
	let labs = $state.raw<LabInfo[]>([]);
	let selectedGroupId = $state<string | null>(null);
	let groupForm = $state<GroupForm>(createEmptyGroupForm());

	const filteredTechnicians = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();
		const items = technicians
			.slice()
			.sort((left, right) => left.name.localeCompare(right.name));

		if (!query) {
			return items;
		}

		return items.filter((technician) => {
			return [
				technician.name,
				technician.technician_id,
				technician.department ?? '',
				technician.group_name ?? '',
			]
				.join(' ')
				.toLowerCase()
				.includes(query);
		});
	});

	const selectedTechnicians = $derived.by(() => {
		const selectedIds = new Set(groupForm.technician_ids);
		return technicians.filter((technician) => selectedIds.has(technician.id));
	});

	const selectedLabs = $derived.by(() => {
		const selectedIds = new Set(groupForm.lab_ids);
		return labs.filter((lab) => selectedIds.has(lab.id));
	});

	onMount(async () => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		await loadPageData(false);
	});

	async function loadPageData(preserveSelection = true) {
		loading = true;
		error = '';
		try {
			const [technicianItems, groupItems, labItems] = await Promise.all([
				labTechnicianApi.getAll(),
				labTechnicianApi.getGroups(),
				labsApi.getAll(),
			]);

			technicians = technicianItems;
			groups = groupItems;
			labs = labItems.filter((lab) => lab.is_active);

			if (preserveSelection && selectedGroupId) {
				const selected = groupItems.find((group) => group.id === selectedGroupId);
				if (selected) {
					loadGroupIntoEditor(selected);
				} else {
					resetEditor();
				}
			}
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load technician assignments';
		} finally {
			loading = false;
		}
	}

	function resetEditor() {
		selectedGroupId = null;
		groupForm = createEmptyGroupForm();
	}

	function loadGroupIntoEditor(group: LabTechnicianGroupSummary) {
		selectedGroupId = group.id;
		groupForm = {
			name: group.name,
			description: group.description ?? '',
			technician_ids: [...group.technician_ids],
			lab_ids: [...group.lab_ids],
			is_active: group.is_active,
		};
	}

	function toggleTechnician(technicianId: string) {
		const current = new Set(groupForm.technician_ids);
		if (current.has(technicianId)) {
			current.delete(technicianId);
		} else {
			current.add(technicianId);
		}
		groupForm = {
			...groupForm,
			technician_ids: Array.from(current),
		};
	}

	function toggleLab(labId: string) {
		const current = new Set(groupForm.lab_ids);
		if (current.has(labId)) {
			current.delete(labId);
		} else {
			current.add(labId);
		}
		groupForm = {
			...groupForm,
			lab_ids: Array.from(current),
		};
	}

	async function saveGroup() {
		const name = groupForm.name.trim();
		if (!name) {
			toastStore.addToast('Batch name is required', 'error');
			return;
		}
		if (groupForm.technician_ids.length === 0) {
			toastStore.addToast('Select at least one technician', 'error');
			return;
		}
		if (groupForm.lab_ids.length === 0) {
			toastStore.addToast('Select at least one permitted lab', 'error');
			return;
		}

		saving = true;
		try {
			const payload = {
				name,
				description: groupForm.description.trim() || undefined,
				technician_ids: groupForm.technician_ids,
				lab_ids: groupForm.lab_ids,
				is_active: groupForm.is_active,
			};

			const savedGroup = selectedGroupId
				? await labTechnicianApi.updateGroup(selectedGroupId, payload)
				: await labTechnicianApi.createGroup(payload);

			toastStore.addToast(selectedGroupId ? 'Batch updated successfully' : 'Batch created successfully', 'success');
			selectedGroupId = savedGroup.id;
			await loadPageData(true);
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save technician batch', 'error');
		} finally {
			saving = false;
		}
	}

	async function deleteGroup() {
		if (!selectedGroupId) {
			return;
		}
		if (!window.confirm('Delete this technician batch? Assigned technicians will lose this lab access set.')) {
			return;
		}

		deleting = true;
		try {
			await labTechnicianApi.deleteGroup(selectedGroupId);
			toastStore.addToast('Batch deleted successfully', 'success');
			resetEditor();
			await loadPageData(false);
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to delete technician batch', 'error');
		} finally {
			deleting = false;
		}
	}
</script>

{#if loading}
	<div class="px-4 py-12 text-center text-sm text-slate-500">Loading technician access workspace...</div>
{:else if error}
	<div class="rounded-2xl px-4 py-4 text-sm text-red-600" style="background: #fef2f2; border: 1px solid #fecaca;">{error}</div>
{:else}
	<div class="space-y-4">
		<div class="flex flex-col gap-3 rounded-[28px] px-5 py-5 md:flex-row md:items-center md:justify-between"
			style="background: linear-gradient(135deg, #0f172a, #1d4ed8 60%, #38bdf8); box-shadow: 0 16px 32px rgba(15,23,42,0.18);">
			<div>
				<button
					onclick={() => goto('/admin/labs')}
					class="mb-3 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold text-white/90 cursor-pointer"
					style="background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.18);"
				>
					<ArrowLeft class="h-3.5 w-3.5" />
					Back to labs
				</button>
				<h1 class="text-xl font-bold text-white">Lab Technician Batches</h1>
				<p class="mt-1 max-w-2xl text-sm text-blue-100">
					Group technicians into working batches, then assign the labs each batch can check in to and operate from.
				</p>
			</div>
			<div class="grid grid-cols-3 gap-2 text-center text-white">
				<div class="rounded-2xl px-3 py-3" style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Technicians</p>
					<p class="mt-1 text-2xl font-bold">{technicians.length}</p>
				</div>
				<div class="rounded-2xl px-3 py-3" style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Batches</p>
					<p class="mt-1 text-2xl font-bold">{groups.length}</p>
				</div>
				<div class="rounded-2xl px-3 py-3" style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Active labs</p>
					<p class="mt-1 text-2xl font-bold">{labs.length}</p>
				</div>
			</div>
		</div>

		<div class="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
			<section class="rounded-[26px] px-4 py-4"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Existing batches</p>
						<h2 class="mt-1 text-lg font-bold text-slate-900">Personnel groups</h2>
					</div>
					<button
						onclick={resetEditor}
						class="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-[11px] font-semibold text-slate-700 cursor-pointer"
						style="background: #e2e8f0;"
					>
						<Plus class="h-3.5 w-3.5" />
						New
					</button>
				</div>

				<div class="mt-4 space-y-3">
					{#if groups.length === 0}
						<div class="rounded-2xl px-4 py-6 text-center text-sm text-slate-500" style="background: #f8fafc; border: 1px dashed rgba(148,163,184,0.5);">
							No technician batches yet.
						</div>
					{:else}
						{#each groups as group}
							<button
								onclick={() => loadGroupIntoEditor(group)}
								class="w-full rounded-2xl px-4 py-4 text-left cursor-pointer transition-transform hover:-translate-y-0.5"
								style={selectedGroupId === group.id
									? 'background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid #60a5fa; box-shadow: 0 10px 18px rgba(37,99,235,0.14);'
									: 'background: white; border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 6px 16px rgba(15,23,42,0.05);'}
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="text-sm font-semibold text-slate-900">{group.name}</p>
										<p class="mt-1 text-xs text-slate-500">{group.description || 'No notes added for this batch yet.'}</p>
									</div>
									<span class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em]"
										style={group.is_active ? 'background: #dcfce7; color: #166534;' : 'background: #e5e7eb; color: #475569;'}>
										{group.is_active ? 'Active' : 'Inactive'}
									</span>
								</div>

								<div class="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
									<div class="rounded-xl px-3 py-2" style="background: rgba(59,130,246,0.08);">
										<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Techs</p>
										<p class="mt-1 font-bold text-slate-900">{group.technician_count}</p>
									</div>
									<div class="rounded-xl px-3 py-2" style="background: rgba(16,185,129,0.08);">
										<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Labs</p>
										<p class="mt-1 font-bold text-slate-900">{group.labs.length}</p>
									</div>
								</div>

								<div class="mt-3 flex flex-wrap gap-1.5">
									{#each group.labs.slice(0, 3) as lab}
										<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold text-slate-700" style="background: #e2e8f0;">{lab.name}</span>
									{/each}
									{#if group.labs.length > 3}
										<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold text-slate-500" style="background: #f1f5f9;">+{group.labs.length - 3} more</span>
									{/if}
								</div>
							</button>
						{/each}
					{/if}
				</div>
			</section>

			<section class="space-y-4">
				<div class="rounded-[26px] px-5 py-5"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Batch editor</p>
							<h2 class="mt-1 text-lg font-bold text-slate-900">{selectedGroupId ? 'Update technician batch' : 'Create technician batch'}</h2>
							<p class="mt-1 text-sm text-slate-500">Choose staff, assign permitted labs, then save the batch.</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								onclick={() => loadPageData(true)}
								class="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-semibold text-slate-700 cursor-pointer"
								style="background: #e2e8f0;"
							>
								<RefreshCw class="h-3.5 w-3.5" />
								Refresh
							</button>
							<button
								onclick={saveGroup}
								disabled={saving}
								class="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
								style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 8px 16px rgba(37,99,235,0.22);"
							>
								<Save class="h-3.5 w-3.5" />
								{saving ? 'Saving...' : selectedGroupId ? 'Save changes' : 'Create batch'}
							</button>
							{#if selectedGroupId}
								<button
									onclick={deleteGroup}
									disabled={deleting}
									class="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold text-red-700 cursor-pointer disabled:opacity-60"
									style="background: #fee2e2; border: 1px solid #fecaca;"
								>
									<Trash2 class="h-3.5 w-3.5" />
									{deleting ? 'Deleting...' : 'Delete batch'}
								</button>
							{/if}
						</div>
					</div>

					<div class="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
						<div class="space-y-4">
							<div>
								<label for="lab-tech-batch-name" class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Batch name</label>
								<input
									id="lab-tech-batch-name"
									type="text"
									bind:value={groupForm.name}
									placeholder="CBC Morning Team"
									class="w-full rounded-2xl px-4 py-3 text-sm outline-none"
									style="background: white; border: 1px solid rgba(148,163,184,0.35); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
								/>
							</div>

							<div>
								<label for="lab-tech-batch-notes" class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Batch notes</label>
								<textarea
									id="lab-tech-batch-notes"
									bind:value={groupForm.description}
									rows="3"
									placeholder="Shift focus, handling instructions, device ownership, or reporting coverage"
									class="w-full rounded-2xl px-4 py-3 text-sm outline-none"
									style="background: white; border: 1px solid rgba(148,163,184,0.35); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
								></textarea>
							</div>
						</div>

						<div class="rounded-2xl px-4 py-4" style="background: linear-gradient(to bottom, #eff6ff, #f8fbff); border: 1px solid rgba(96,165,250,0.32);">
							<div class="flex items-center gap-2 text-blue-900">
								<ShieldCheck class="h-4 w-4" />
								<p class="text-sm font-semibold">Access summary</p>
							</div>
							<div class="mt-4 space-y-3 text-sm text-slate-700">
								<div class="flex items-center justify-between rounded-xl px-3 py-2" style="background: rgba(255,255,255,0.72);">
									<span>Selected technicians</span>
									<strong>{groupForm.technician_ids.length}</strong>
								</div>
								<div class="flex items-center justify-between rounded-xl px-3 py-2" style="background: rgba(255,255,255,0.72);">
									<span>Permitted labs</span>
									<strong>{groupForm.lab_ids.length}</strong>
								</div>
								<label class="flex items-center gap-2 rounded-xl px-3 py-2 cursor-pointer" style="background: rgba(255,255,255,0.72);">
									<input type="checkbox" bind:checked={groupForm.is_active} class="accent-blue-600" />
									<span>Batch active for check-in</span>
								</label>
							</div>
						</div>
					</div>
				</div>

				<div class="grid gap-4 2xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
					<section class="rounded-[26px] px-5 py-5"
						style="background: linear-gradient(to bottom, #ffffff, #fbfdff); border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
						<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
							<div>
								<div class="flex items-center gap-2 text-slate-900">
									<Users class="h-4 w-4" />
									<h3 class="text-base font-bold">Select technicians</h3>
								</div>
								<p class="mt-1 text-sm text-slate-500">Assign personnel to this batch. Existing batch names are shown for quick audit.</p>
							</div>
							<div class="relative w-full md:w-72">
								<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
								<input
									type="text"
									bind:value={searchQuery}
									placeholder="Search name, ID, batch, department"
									class="w-full rounded-2xl py-2.5 pl-10 pr-4 text-sm outline-none"
									style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.32);"
								/>
							</div>
						</div>

						<div class="mt-4 grid gap-3 md:grid-cols-2">
							{#each filteredTechnicians as technician}
								{@const isSelected = groupForm.technician_ids.includes(technician.id)}
								<button
									onclick={() => toggleTechnician(technician.id)}
									class="rounded-2xl px-4 py-4 text-left cursor-pointer transition-transform hover:-translate-y-0.5"
									style={isSelected
										? 'background: linear-gradient(to bottom, #ecfeff, #dbeafe); border: 1px solid #38bdf8; box-shadow: 0 10px 18px rgba(14,165,233,0.14);'
										: 'background: white; border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 6px 16px rgba(15,23,42,0.05);'}
								>
									<div class="flex items-start justify-between gap-3">
										<div class="flex items-center gap-3">
											<div class="flex h-11 w-11 items-center justify-center rounded-2xl text-slate-700" style="background: rgba(59,130,246,0.1);">
												<UserRound class="h-5 w-5" />
											</div>
											<div>
												<p class="text-sm font-semibold text-slate-900">{technician.name}</p>
												<p class="text-xs text-slate-500">{technician.technician_id} {technician.department ? `· ${technician.department}` : ''}</p>
											</div>
										</div>
										{#if isSelected}
											<CheckCircle2 class="h-5 w-5 text-sky-600" />
										{:else}
											<Circle class="h-5 w-5 text-slate-300" />
										{/if}
									</div>

									<div class="mt-3 flex flex-wrap gap-2">
										<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold"
											style={technician.group_name ? 'background: #ede9fe; color: #6d28d9;' : 'background: #e2e8f0; color: #475569;'}>
											{technician.group_name || 'Unassigned'}
										</span>
										{#if technician.active_lab}
											<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold text-emerald-700" style="background: #dcfce7;">Checked in: {technician.active_lab.name}</span>
										{/if}
									</div>
								</button>
							{/each}
						</div>
					</section>

					<section class="rounded-[26px] px-5 py-5"
						style="background: linear-gradient(to bottom, #ffffff, #fbfdff); border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
						<div class="flex items-center gap-2 text-slate-900">
							<FlaskConical class="h-4 w-4" />
							<h3 class="text-base font-bold">Permitted labs</h3>
						</div>
						<p class="mt-1 text-sm text-slate-500">Technicians in this batch can check in only to the selected labs below.</p>

						<div class="mt-4 space-y-3">
							{#each labs as lab}
								{@const isSelected = groupForm.lab_ids.includes(lab.id)}
								<button
									onclick={() => toggleLab(lab.id)}
									class="w-full rounded-2xl px-4 py-4 text-left cursor-pointer transition-transform hover:-translate-y-0.5"
									style={isSelected
										? 'background: linear-gradient(to bottom, #ecfdf5, #d1fae5); border: 1px solid #34d399; box-shadow: 0 10px 18px rgba(16,185,129,0.14);'
										: 'background: white; border: 1px solid rgba(148,163,184,0.28); box-shadow: 0 6px 16px rgba(15,23,42,0.05);'}
								>
									<div class="flex items-start justify-between gap-3">
										<div>
											<p class="text-sm font-semibold text-slate-900">{lab.name}</p>
											<p class="mt-1 text-xs text-slate-500">{lab.lab_type} · {lab.department}</p>
											{#if lab.location}
												<p class="mt-1 text-xs text-slate-400">{lab.location}</p>
											{/if}
										</div>
										{#if isSelected}
											<CheckCircle2 class="h-5 w-5 text-emerald-600" />
										{:else}
											<Circle class="h-5 w-5 text-slate-300" />
										{/if}
									</div>
								</button>
							{/each}
						</div>

						<div class="mt-5 rounded-2xl px-4 py-4" style="background: #f8fafc; border: 1px dashed rgba(148,163,184,0.48);">
							<div class="flex items-center gap-2 text-slate-900">
								<Layers3 class="h-4 w-4" />
								<p class="text-sm font-semibold">Current selection</p>
							</div>
							<div class="mt-3 space-y-3 text-sm text-slate-600">
								<div>
									<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Technicians</p>
									<div class="mt-2 flex flex-wrap gap-1.5">
										{#if selectedTechnicians.length === 0}
											<span class="text-xs text-slate-400">None selected yet</span>
										{:else}
											{#each selectedTechnicians as technician}
												<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold text-slate-700" style="background: #e2e8f0;">{technician.name}</span>
											{/each}
										{/if}
									</div>
								</div>

								<div>
									<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Labs</p>
									<div class="mt-2 flex flex-wrap gap-1.5">
										{#if selectedLabs.length === 0}
											<span class="text-xs text-slate-400">No lab access assigned</span>
										{:else}
											{#each selectedLabs as lab}
												<span class="rounded-full px-2.5 py-1 text-[10px] font-semibold text-slate-700" style="background: #dcfce7;">{lab.name}</span>
											{/each}
										{/if}
									</div>
								</div>
							</div>
						</div>
					</section>
				</div>
			</section>
		</div>
	</div>
{/if}