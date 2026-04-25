<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type Department } from '$lib/api/admin';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		ChevronRight, Download, Loader2, PencilLine, Plus, Stethoscope, Trash2, Upload
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let departments: Department[] = $state([]);
	let importing = $state(false);
	let importFeedback = $state('');
	let togglingId = $state('');
	let fileInput: HTMLInputElement;

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
		error = '';
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

	async function toggleDepartmentActive(dept: Department) {
		if (togglingId) return;
		togglingId = dept.id;
		importFeedback = '';
		try {
			await adminApi.updateDepartment(dept.id, { is_active: !dept.is_active });
			departments = departments.map((item) =>
				item.id === dept.id ? { ...item, is_active: !item.is_active } : item
			);
		} catch (e: any) {
			importFeedback = e.response?.data?.detail || 'Failed to update department status';
		} finally {
			togglingId = '';
		}
	}

	function normalizeRowKeys(row: Record<string, unknown>): Record<string, string> {
		const normalized: Record<string, string> = {};
		for (const [key, value] of Object.entries(row)) {
			const cleanKey = key.toLowerCase().trim().replace(/\s+/g, '_');
			normalized[cleanKey] = String(value ?? '').trim();
		}
		return normalized;
	}

	async function downloadSample() {
		const rows = [
			{ name: 'Cardiology', code: 'CARD', description: 'Heart and vascular medicine' },
			{ name: 'General Surgery', code: 'GSUR', description: 'General and laparoscopic surgery' },
			{ name: 'Orthopedics', code: 'ORTHO', description: 'Bone and joint care' },
		];

		try {
			const XLSX = await import('xlsx/xlsx.mjs');
			const worksheet = XLSX.utils.json_to_sheet(rows);
			const workbook = XLSX.utils.book_new();
			XLSX.utils.book_append_sheet(workbook, worksheet, 'Departments');
			XLSX.writeFile(workbook, 'departments-sample.xlsx');
		} catch {
			const csv = [
				'name,code,description',
				...rows.map((row) => `"${row.name}","${row.code}","${row.description}"`)
			].join('\n');
			const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
			const link = document.createElement('a');
			link.href = URL.createObjectURL(blob);
			link.download = 'departments-sample.csv';
			link.click();
			URL.revokeObjectURL(link.href);
		}
	}

	async function handleImport(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		importing = true;
		importFeedback = '';

		try {
			const XLSX = await import('xlsx/xlsx.mjs');
			const buffer = await file.arrayBuffer();
			const workbook = XLSX.read(buffer, { type: 'array' });
			const firstSheet = workbook.SheetNames[0];
			if (!firstSheet) {
				importFeedback = 'No sheet found in import file';
				return;
			}

			const rawRows = XLSX.utils.sheet_to_json(workbook.Sheets[firstSheet], {
				defval: ''
			}) as Record<string, unknown>[];

			if (rawRows.length === 0) {
				importFeedback = 'Import file is empty';
				return;
			}

			const normalizedRows: Record<string, string>[] = rawRows.map(normalizeRowKeys);
			const parsedRows: Array<{ name: string; code: string; description: string }> = normalizedRows
				.map((row) => ({
					name: row.name ?? row.department_name ?? '',
					code: row.code ?? row.department_code ?? '',
					description: row.description ?? ''
				}))
				.filter((row) => row.name.trim() && row.code.trim());

			if (parsedRows.length === 0) {
				importFeedback = 'No valid rows found. Required columns: name, code';
				return;
			}

			const existingByCode = new Map(
				departments.map((dept) => [dept.code.trim().toUpperCase(), dept])
			);

			let success = 0;
			let failed = 0;

			for (const row of parsedRows) {
				const payload = {
					name: row.name.trim(),
					code: row.code.trim().toUpperCase(),
					description: row.description.trim() || undefined,
				};
				const existing = existingByCode.get(payload.code);
				try {
					if (existing) {
						await adminApi.updateDepartment(existing.id, payload);
					} else {
						await adminApi.createDepartment(payload as any);
					}
					success += 1;
				} catch {
					failed += 1;
				}
			}

			await loadData();
			if (failed > 0) {
				importFeedback = `Imported ${success} row(s), ${failed} failed`;
			} else {
				importFeedback = `Imported ${success} row(s)`;
			}
		} catch {
			importFeedback = 'Failed to parse file. Use CSV/XLS/XLSX with name and code columns';
		} finally {
			importing = false;
			input.value = '';
		}
	}
</script>

	<div class="space-y-4 lg:space-y-5">
		<div class="flex items-center justify-between gap-3">
			<div>
				<h2 class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 lg:text-[13px]">Medical Departments</h2>
				<p class="mt-1 text-xs text-slate-500 lg:hidden">{departments.length} departments configured</p>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				<button
					onclick={downloadSample}
					class="hidden items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 cursor-pointer lg:flex"
					style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); box-shadow: 0 2px 6px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.6);"
				>
					<Download class="h-3.5 w-3.5" />
					<span>Sample</span>
				</button>
				<button
					onclick={() => fileInput?.click()}
					disabled={importing}
					class="hidden items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 cursor-pointer disabled:opacity-60 lg:flex"
					style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); box-shadow: 0 2px 6px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.6);"
				>
					{#if importing}
						<Loader2 class="h-3.5 w-3.5 animate-spin" />
					{:else}
						<Upload class="h-3.5 w-3.5" />
					{/if}
					<span>Import</span>
				</button>
				<input
					bind:this={fileInput}
					type="file"
					accept=".csv,.xls,.xlsx"
					onchange={handleImport}
					class="hidden"
				/>
				<button
					onclick={openCreate}
					class="flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-white cursor-pointer lg:px-4"
					style="background: linear-gradient(to bottom, #3c8af4, #1667d8); box-shadow: 0 3px 8px rgba(22,103,216,0.24), inset 0 1px 0 rgba(255,255,255,0.22);"
				>
					<Plus class="h-3.5 w-3.5" />
					<span>Add New</span>
				</button>
			</div>
		</div>

		{#if importFeedback}
			<p class="rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700">{importFeedback}</p>
		{/if}

	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<AquaCard>
			<p class="text-red-500 text-center py-4">{error}</p>
		</AquaCard>
	{:else}
		<div class="space-y-3 lg:hidden">
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
						style={`background: linear-gradient(180deg, ${dept.is_active ? '#b26eff' : '#b5bcc8'} 0%, ${dept.is_active ? '#7b23df' : '#7f8a99'} 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);`}
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
						<!-- Delete department action hidden until admin disable flow replaces hard delete UI. -->
						<!--
						<button
							class="hidden h-8 w-8 items-center justify-center rounded-full cursor-pointer opacity-0 transition-opacity hover:bg-rose-50 group-hover:flex group-hover:opacity-100"
							onclick={(event) => { event.stopPropagation(); confirmDelete(dept); }}
						>
							<Trash2 class="h-4 w-4 text-rose-500" />
						</button>
						-->
						<ChevronRight class="h-4 w-4 text-slate-300 transition-colors group-hover:text-slate-500" />
					</div>
				</div>
			{/each}
		</div>

		<div class="hidden overflow-hidden rounded-[18px] border lg:block" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
			<div class="overflow-x-auto">
				<table class="min-w-full border-collapse">
					<thead>
						<tr class="border-b border-slate-200/80 bg-slate-50/80 text-left">
							<th class="px-4 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Code</th>
							<th class="px-4 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Department</th>
							<!-- <th class="px-4 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Description</th> -->
							<th class="px-4 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Status</th>
							<th class="px-4 py-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#if departments.length === 0}
							<tr>
								<td colspan="5" class="px-6 py-12 text-center">
									<Stethoscope class="mx-auto mb-3 h-12 w-12 text-violet-300" />
									<p class="text-sm font-semibold text-slate-500">No departments yet</p>
									<div class="mt-3">
										<AquaButton size="sm" onclick={openCreate}>
											<span>Create First Department</span>
										</AquaButton>
									</div>
								</td>
							</tr>
						{:else}
							{#each departments as dept (dept.id)}
								<tr class="border-b border-slate-100 last:border-b-0 hover:bg-blue-50/30">
									<td class="px-4 py-3 text-sm font-bold text-violet-700">{dept.code}</td>
									<td class="px-4 py-3 text-sm font-semibold text-slate-800">{dept.name}</td>
									<!-- <td class="max-w-[28rem] px-4 py-3 text-sm text-slate-500">
										<div class="truncate">{dept.description || '—'}</div>
									</td> -->
									<td class="px-4 py-3">
										<button
											type="button"
											role="switch"
											aria-checked={dept.is_active}
											aria-label={`Toggle ${dept.name} active status`}
											onclick={() => toggleDepartmentActive(dept)}
											disabled={togglingId === dept.id}
											class="inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
										>
											<span
												class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${dept.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}
											>
												<span
													class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${dept.is_active ? 'left-6' : 'left-1'}`}
												>
													{#if togglingId === dept.id}
														<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
													{/if}
												</span>
											</span>
											<!-- <span class={`text-[10px] font-bold uppercase tracking-[0.12em] ${dept.is_active ? 'text-emerald-700' : 'text-rose-600'}`}>
												{dept.is_active ? 'Active' : 'Inactive'}
											</span> -->
										</button>
									</td>
									<td class="px-4 py-3">
										<div class="flex items-center gap-2">
											<button
												onclick={() => openEdit(dept)}
												class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50"
											>
												<PencilLine class="h-3.5 w-3.5" />
												Edit
											</button>
										</div>
									</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</div>

		<div class="flex gap-2 lg:hidden">
			<button
				onclick={downloadSample}
				class="flex flex-1 items-center justify-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 cursor-pointer"
				style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); box-shadow: 0 2px 6px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.6);"
			>
				<Download class="h-3.5 w-3.5" />
				<span>Sample</span>
			</button>
			<button
				onclick={() => fileInput?.click()}
				disabled={importing}
				class="flex flex-1 items-center justify-center gap-1 rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 cursor-pointer disabled:opacity-60"
				style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); box-shadow: 0 2px 6px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.6);"
			>
				{#if importing}
					<Loader2 class="h-3.5 w-3.5 animate-spin" />
				{:else}
					<Upload class="h-3.5 w-3.5" />
				{/if}
				<span>Import</span>
			</button>
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
