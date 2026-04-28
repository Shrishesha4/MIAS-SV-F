<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { labTechnicianApi, type LabTechnicianGroupSummary, type LabTechnicianProfile } from '$lib/api/lab-technicians';
	import { labsApi, type LabInfo } from '$lib/api/labs';
	import { toastStore } from '$lib/stores/toast';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { Search, Save, Trash2, RefreshCw, Users, Layers3, FlaskConical, Plus, CheckCircle2, Circle, ArrowLeft, UserRound } from 'lucide-svelte';

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

	const tabs = [
		{ id: 'technicians', label: 'All Technicians' },
		{ id: 'batches', label: 'Batches' },
	];

	let activeTab = $state('technicians');
	let loading = $state(true);
	let saving = $state(false);
	let deleting = $state(false);
	let error = $state('');
	let searchQuery = $state('');
	let batchSearchQuery = $state('');
	let technicians = $state.raw<LabTechnicianProfile[]>([]);
	let groups = $state.raw<LabTechnicianGroupSummary[]>([]);
	let labs = $state.raw<LabInfo[]>([]);
	let selectedGroupId = $state<string | null>(null);
	let groupForm = $state<GroupForm>(createEmptyGroupForm());

	const filteredTechnicians = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();
		const items = technicians
			.slice()
			.sort((a, b) => a.name.localeCompare(b.name));
		if (!query) return items;
		return items.filter((t) =>
			[t.name, t.technician_id, t.department ?? '', ...t.batches.map((b) => b.name)]
				.join(' ')
				.toLowerCase()
				.includes(query),
		);
	});

	const filteredBatchTechnicians = $derived.by(() => {
		const query = batchSearchQuery.trim().toLowerCase();
		const items = technicians.slice().sort((a, b) => a.name.localeCompare(b.name));
		if (!query) return items;
		return items.filter((t) =>
			[t.name, t.technician_id, t.department ?? ''].join(' ').toLowerCase().includes(query),
		);
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
			toastStore.addToast('Batch deleted', 'success');
			resetEditor();
			await loadPageData(false);
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to delete batch', 'error');
		} finally {
			deleting = false;
		}
	}
</script>

{#if loading}
	<div class="flex items-center justify-center py-16">
		<div class="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
	</div>
{:else if error}
	<div class="rounded-2xl border px-4 py-8 text-center" style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
		<p class="text-sm font-semibold text-red-600">{error}</p>
	</div>
{:else}
	<div class="flex flex-col gap-4">
		<!-- Page header: academics-style -->
		<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex flex-col gap-1">
				<button
					onclick={() => goto('/admin/labs')}
					class="inline-flex w-fit items-center gap-1.5 text-[11px] font-semibold text-slate-400 transition-colors hover:text-slate-600 cursor-pointer"
				>
					<ArrowLeft class="h-3 w-3" />
					Back to labs
				</button>
				<p class="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Lab Technician Management</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<span class="rounded-full border px-3 py-1 text-xs font-semibold text-slate-600" style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.2);">{technicians.length} Technicians</span>
				<span class="rounded-full border px-3 py-1 text-xs font-semibold text-slate-600" style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.2);">{groups.length} Batches</span>
				<span class="rounded-full border px-3 py-1 text-xs font-semibold text-slate-600" style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.2);">{labs.length} Active Labs</span>
			</div>
		</div>

		<!-- Tabs -->
		<TabBar
			tabs={tabs}
			activeTab={activeTab}
			onchange={(id) => { activeTab = id; searchQuery = ''; batchSearchQuery = ''; }}
			variant="jiggle"
			stretch={false}
			size="compact"
		/>

		<!-- ─── All Technicians tab ─── -->
		{#if activeTab === 'technicians'}
			<div class="flex flex-col gap-3">
				<div class="relative">
					<Search class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Search by name, ID, department, or batch…"
						class="w-full rounded-2xl py-2.5 pl-9 pr-4 text-sm outline-none"
						style="background: rgba(255,255,255,0.97); border: 1px solid rgba(148,163,184,0.25);"
					/>
				</div>

				{#if filteredTechnicians.length === 0}
					<div class="rounded-2xl border px-4 py-12 text-center" style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
						<p class="text-sm text-slate-400">No technicians found.</p>
					</div>
				{:else}
					<div class="space-y-1.5">
						{#each filteredTechnicians as tech}
							<div
								class="flex items-start gap-3 rounded-2xl border px-4 py-3"
								style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);"
							>
								<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
									{tech.name.slice(0, 1).toUpperCase()}
								</div>
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-2">
										<p class="text-sm font-bold text-slate-900">{tech.name}</p>
										<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-slate-500" style="background: #f1f5f9;">{tech.technician_id}</span>
									</div>
									{#if tech.department}
										<p class="text-[11px] text-slate-500">{tech.department}</p>
									{/if}
									<div class="mt-1.5 flex flex-wrap gap-1">
										{#if tech.batches.length === 0}
											<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-slate-400" style="background: #f1f5f9;">No batches</span>
										{:else}
											{#each tech.batches as batch}
												<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: #ede9fe; color: #6d28d9;">{batch.name}</span>
											{/each}
										{/if}
										{#if tech.active_lab}
											<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-emerald-700" style="background: #dcfce7;">In: {tech.active_lab.name}</span>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

		<!-- ─── Batches tab ─── -->
		{:else}
			<!-- Two-column layout -->
			<div class="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">

				<!-- Left: Batch list -->
				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between">
						<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Batches</p>
						<button
							onclick={resetEditor}
							class="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-[11px] font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.25);"
						>
							<Plus class="h-3.5 w-3.5" />
							New Batch
						</button>
					</div>

					{#if groups.length === 0}
						<div class="rounded-2xl border px-4 py-10 text-center" style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
							<p class="text-sm text-slate-400">No batches yet.</p>
						</div>
					{:else}
						<div class="space-y-1.5">
							{#each groups as group}
								<div
									role="button"
									tabindex="0"
									onclick={() => loadGroupIntoEditor(group)}
									onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); loadGroupIntoEditor(group); } }}
									class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
									style={selectedGroupId === group.id
										? 'background: linear-gradient(to bottom, #eff6ff, #dbeafe); border-color: #93c5fd; box-shadow: 0 1px 4px rgba(37,99,235,0.10);'
										: 'background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);'}
								>
									<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
										style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 10px rgba(37,99,235,0.24);">
										<Layers3 class="h-4 w-4 text-white" />
									</div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-bold text-slate-900">{group.name}</p>
										<p class="text-[11px] text-slate-500">{group.technician_count} techs · {group.labs.length} labs</p>
									</div>
									<span class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em]"
										style={group.is_active ? 'background: #dcfce7; color: #166534;' : 'background: #e5e7eb; color: #475569;'}>
										{group.is_active ? 'Active' : 'Off'}
									</span>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Right: Editor -->
				<div class="flex flex-col gap-4">
					<!-- Editor action row -->
					<div class="flex items-center justify-between">
						<div>
							<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Batch editor</p>
							<p class="mt-0.5 text-base font-bold text-slate-900">{selectedGroupId ? 'Edit batch' : 'New batch'}</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								onclick={() => loadPageData(true)}
								class="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-semibold text-slate-700 cursor-pointer"
								style="background: rgba(255,255,255,0.97); border: 1px solid rgba(148,163,184,0.2);"
							>
								<RefreshCw class="h-3.5 w-3.5" />
								Refresh
							</button>
							<button
								onclick={saveGroup}
								disabled={saving}
								class="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-semibold text-white cursor-pointer disabled:opacity-60 transition-all hover:-translate-y-[1px] active:translate-y-0.5"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.28), inset 0 1px 0 rgba(255,255,255,0.25);"
							>
								<Save class="h-3.5 w-3.5" />
								{saving ? 'Saving…' : selectedGroupId ? 'Save changes' : 'Create batch'}
							</button>
							{#if selectedGroupId}
								<button
									onclick={deleteGroup}
									disabled={deleting}
									class="inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-semibold text-red-600 cursor-pointer disabled:opacity-60"
									style="background: rgba(255,255,255,0.97); border: 1px solid rgba(252,165,165,0.4);"
								>
									<Trash2 class="h-3.5 w-3.5" />
									{deleting ? '…' : 'Delete'}
								</button>
							{/if}
						</div>
					</div>

					<!-- Batch name + notes + access summary -->
					<div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_200px]">
						<div class="space-y-3">
							<div>
								<label for="lab-tech-batch-name" class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">Batch name</label>
								<input
									id="lab-tech-batch-name"
									type="text"
									bind:value={groupForm.name}
									placeholder="e.g. CBC Morning Team"
									class="w-full rounded-2xl px-4 py-2.5 text-sm outline-none"
									style="background: rgba(255,255,255,0.97); border: 1px solid rgba(148,163,184,0.25);"
								/>
							</div>
							<div>
								<label for="lab-tech-batch-notes" class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">Notes</label>
								<textarea
									id="lab-tech-batch-notes"
									bind:value={groupForm.description}
									rows="2"
									placeholder="Shift focus, device ownership, reporting coverage…"
									class="w-full resize-none rounded-2xl px-4 py-2.5 text-sm outline-none"
									style="background: rgba(255,255,255,0.97); border: 1px solid rgba(148,163,184,0.25);"
								></textarea>
							</div>
						</div>

						<div class="flex flex-col gap-2 rounded-2xl border px-4 py-3"
							style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.18);">
							<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">Summary</p>
							<div class="flex items-center justify-between text-sm text-slate-700">
								<span>Technicians</span>
								<strong class="text-slate-900">{groupForm.technician_ids.length}</strong>
							</div>
							<div class="flex items-center justify-between text-sm text-slate-700">
								<span>Permitted labs</span>
								<strong class="text-slate-900">{groupForm.lab_ids.length}</strong>
							</div>
							<label class="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
								<input type="checkbox" bind:checked={groupForm.is_active} class="accent-blue-600" />
								<span>Active for check-in</span>
							</label>
						</div>
					</div>

					<!-- Technician + Lab selectors -->
					<div class="grid gap-4 2xl:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">

						<!-- Technician multi-select -->
						<div class="flex flex-col gap-2">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-1.5">
									<Users class="h-3.5 w-3.5 text-slate-400" />
									<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">
										Technicians <span class="normal-case font-medium">(multi-select)</span>
									</p>
								</div>
								<div class="relative">
									<Search class="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
									<input
										type="text"
										bind:value={batchSearchQuery}
										placeholder="Search…"
										class="w-36 rounded-full py-1.5 pl-8 pr-3 text-xs outline-none"
										style="background: rgba(255,255,255,0.97); border: 1px solid rgba(148,163,184,0.25);"
									/>
								</div>
							</div>

							<div class="space-y-1.5">
								{#each filteredBatchTechnicians as tech}
									{@const isSelected = groupForm.technician_ids.includes(tech.id)}
									<div
										role="button"
										tabindex="0"
										onclick={() => toggleTechnician(tech.id)}
										onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTechnician(tech.id); } }}
										class="flex items-center gap-3 rounded-2xl border px-4 py-3 cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
										style={isSelected
											? 'background: linear-gradient(to bottom, #eff6ff, #dbeafe); border-color: #93c5fd;'
											: 'background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);'}
									>
										<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
											style="background: rgba(59,130,246,0.1);">
											<UserRound class="h-4 w-4 text-blue-600" />
										</div>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-semibold text-slate-900">{tech.name}</p>
											<p class="text-[11px] text-slate-500">{tech.technician_id}{tech.department ? ` · ${tech.department}` : ''}</p>
										</div>
										<!-- Other batches this tech belongs to (excluding the one being edited) -->
										<div class="flex shrink-0 flex-col items-end gap-1">
											{#each tech.batches.filter((b) => b.id !== selectedGroupId) as b}
												<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: #ede9fe; color: #6d28d9;">{b.name}</span>
											{/each}
											{#if tech.active_lab}
												<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-emerald-700" style="background: #dcfce7;">{tech.active_lab.name}</span>
											{/if}
										</div>
										{#if isSelected}
											<CheckCircle2 class="h-4 w-4 shrink-0 text-blue-500" />
										{:else}
											<Circle class="h-4 w-4 shrink-0 text-slate-300" />
										{/if}
									</div>
								{/each}
							</div>
						</div>

						<!-- Lab multi-select -->
						<div class="flex flex-col gap-2">
							<div class="flex items-center gap-1.5">
								<FlaskConical class="h-3.5 w-3.5 text-slate-400" />
								<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Permitted labs</p>
							</div>

							<div class="space-y-1.5">
								{#each labs as lab}
									{@const isSelected = groupForm.lab_ids.includes(lab.id)}
									<div
										role="button"
										tabindex="0"
										onclick={() => toggleLab(lab.id)}
										onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleLab(lab.id); } }}
										class="flex items-center gap-3 rounded-2xl border px-4 py-3 cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
										style={isSelected
											? 'background: linear-gradient(to bottom, #ecfdf5, #d1fae5); border-color: #6ee7b7;'
											: 'background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);'}
									>
										<div class="min-w-0 flex-1">
											<p class="truncate text-sm font-semibold text-slate-900">{lab.name}</p>
											<p class="text-[11px] text-slate-500">{lab.lab_type} · {lab.department}</p>
										</div>
										{#if isSelected}
											<CheckCircle2 class="h-4 w-4 shrink-0 text-emerald-500" />
										{:else}
											<Circle class="h-4 w-4 shrink-0 text-slate-300" />
										{/if}
									</div>
								{/each}
							</div>

							<!-- Selection chips summary -->
							{#if selectedTechnicians.length > 0 || selectedLabs.length > 0}
								<div class="mt-1 rounded-2xl border px-3 py-3 space-y-2"
									style="background: rgba(255,255,255,0.6); border-color: rgba(148,163,184,0.18);">
									{#if selectedTechnicians.length > 0}
										<div>
											<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Selected ({selectedTechnicians.length})</p>
											<div class="mt-1 flex flex-wrap gap-1">
												{#each selectedTechnicians as t}
													<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-slate-700" style="background: #e2e8f0;">{t.name}</span>
												{/each}
											</div>
										</div>
									{/if}
									{#if selectedLabs.length > 0}
										<div>
											<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Labs ({selectedLabs.length})</p>
											<div class="mt-1 flex flex-wrap gap-1">
												{#each selectedLabs as l}
													<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold text-slate-700" style="background: #dcfce7;">{l.name}</span>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{/if}

	</div>
{/if}