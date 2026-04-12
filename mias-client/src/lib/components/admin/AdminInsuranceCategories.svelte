<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { insuranceCategoriesApi, type InsuranceCategory, type WalkInType, type ClinicConfig } from '$lib/api/insuranceCategories';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import SystemConfigTabs from '$lib/components/admin/SystemConfigTabs.svelte';
	import { Loader2, PencilLine, Plus, ShieldCheck, Star, Trash2, Building2, Settings2, IndianRupee } from 'lucide-svelte';

	const auth = get(authStore);

	// State
	let loading = $state(true);
	let saving = $state(false);
	let deletingId = $state<string | null>(null);
	let categories = $state<InsuranceCategory[]>([]);
	let walkInTypes = $state<WalkInType[]>([]);
	let editorOpen = $state(false);
	let configEditorOpen = $state(false);
	let selectedCategory = $state<InsuranceCategory | null>(null);

	// Form state
	let formName = $state('');
	let formDescription = $state('');
	let formIsActive = $state(true);
	let formIsDefault = $state(false);
	let formSortOrder = $state(0);
	let editingId = $state<string | null>(null);

	// Config form state
	let editingConfig = $state<ClinicConfig | null>(null);
	let configWalkInType = $state('');
	let configRegistrationFee = $state(100);
	let configIsEnabled = $state(true);

	// Derived values
	const activeCategoryCount = $derived.by(() => categories.filter((item) => item.is_active).length);
	const totalClinicConfigs = $derived.by(() => 
		categories.reduce((sum, item) => sum + (item.clinic_configs?.length || 0), 0)
	);

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			void goto('/dashboard');
			return;
		}
		void loadData();
	});

	async function loadData() {
		loading = true;
		try {
			const [categoriesData, walkInTypesData] = await Promise.all([
				insuranceCategoriesApi.listCategories(),
				insuranceCategoriesApi.getWalkInTypes(),
			]);
			categories = categoriesData;
			walkInTypes = walkInTypesData;
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load insurance categories', 'error');
		} finally {
			loading = false;
		}
	}

	function openCreate() {
		editingId = null;
		formName = '';
		formDescription = '';
		formIsActive = true;
		formIsDefault = categories.length === 0;
		formSortOrder = categories.length;
		editorOpen = true;
	}

	function openEdit(category: InsuranceCategory) {
		editingId = category.id;
		formName = category.name;
		formDescription = category.description || '';
		formIsActive = category.is_active;
		formIsDefault = category.is_default;
		formSortOrder = category.sort_order;
		editorOpen = true;
	}

	function openConfigEditor(category: InsuranceCategory, config: ClinicConfig) {
		selectedCategory = category;
		editingConfig = config;
		configWalkInType = config.walk_in_type;
		configRegistrationFee = config.registration_fee;
		configIsEnabled = config.is_enabled;
		configEditorOpen = true;
	}

	function closeEditor() {
		editorOpen = false;
		editingId = null;
	}

	function closeConfigEditor() {
		configEditorOpen = false;
		selectedCategory = null;
		editingConfig = null;
	}

	async function saveCategory() {
		if (!formName.trim()) {
			toastStore.addToast('Category name is required', 'error');
			return;
		}

		saving = true;
		try {
			if (editingId) {
				await insuranceCategoriesApi.updateCategory(editingId, {
					name: formName,
					description: formDescription,
					is_active: formIsActive,
					is_default: formIsDefault,
					sort_order: formSortOrder,
				});
				toastStore.addToast('Insurance category updated', 'success');
			} else {
				await insuranceCategoriesApi.createCategory({
					name: formName,
					description: formDescription,
					is_active: formIsActive,
					is_default: formIsDefault,
					sort_order: formSortOrder,
				});
				toastStore.addToast('Insurance category created', 'success');
			}
			await loadData();
			closeEditor();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save insurance category', 'error');
		} finally {
			saving = false;
		}
	}

	async function saveClinicConfig() {
		if (!selectedCategory || !editingConfig) return;

		saving = true;
		try {
			await insuranceCategoriesApi.updateClinicConfig(
				selectedCategory.id,
				editingConfig.id,
				{
					walk_in_type: configWalkInType,
					registration_fee: configRegistrationFee,
					is_enabled: configIsEnabled,
				}
			);
			toastStore.addToast('Clinic configuration updated', 'success');
			await loadData();
			closeConfigEditor();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to update clinic configuration', 'error');
		} finally {
			saving = false;
		}
	}

	async function setDefault(category: InsuranceCategory) {
		try {
			await insuranceCategoriesApi.updateCategory(category.id, { is_default: true });
			categories = categories.map((item) => ({
				...item,
				is_default: item.id === category.id,
			}));
			toastStore.addToast(`${category.name} is now the default category`, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to update default category', 'error');
		}
	}

	async function removeCategory(category: InsuranceCategory) {
		deletingId = category.id;
		try {
			await insuranceCategoriesApi.deleteCategory(category.id);
			categories = categories.filter((item) => item.id !== category.id);
			toastStore.addToast('Insurance category deleted', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete insurance category', 'error');
		} finally {
			deletingId = null;
		}
	}

	function getWalkInTypeLabel(value: string): string {
		const type = walkInTypes.find(t => t.value === value);
		return type?.label || value;
	}
</script>

<div class="space-y-4">
	<div class="rounded-[24px] border border-slate-200 p-3"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.92), rgba(246,249,255,0.92)); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
		<SystemConfigTabs activeTab="insurance" />
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
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Clinic Configs</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{totalClinicConfigs}</p>
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
				Add Insurance Category
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
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Clinics</th>
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
										{#if category.is_default}
											<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-amber-700"
												style="background: rgba(251,191,36,0.18); border: 1px solid rgba(245,158,11,0.22);">
												<Star class="h-3 w-3" /> Default
											</span>
										{/if}
									</div>
									{#if category.description}
										<p class="text-xs text-slate-500 mt-1">{category.description}</p>
									{/if}
								</td>
								<td class="px-4 py-4">
									<div class="space-y-1">
										{#each category.clinic_configs.slice(0, 3) as config}
											<div class="flex items-center gap-2 text-xs">
												<Building2 class="h-3 w-3 text-slate-400" />
												<span class={config.is_enabled ? 'text-slate-700' : 'text-slate-400'}>
													{config.clinic_name}
												</span>
												<span class="text-slate-400">•</span>
												<span class="text-blue-600">{getWalkInTypeLabel(config.walk_in_type)}</span>
												<span class="text-slate-400">•</span>
												<span class="text-emerald-600">₹{config.registration_fee}</span>
											</div>
										{/each}
										{#if category.clinic_configs.length > 3}
											<p class="text-xs text-slate-400">+{category.clinic_configs.length - 3} more clinics</p>
										{/if}
									</div>
									<button
										type="button"
										class="mt-2 text-xs font-semibold text-blue-600 hover:text-blue-700 cursor-pointer flex items-center gap-1"
										onclick={() => {
											if (category.clinic_configs && category.clinic_configs.length > 0) {
												openConfigEditor(category, category.clinic_configs[0]);
											} else {
												toastStore.addToast('No clinic configurations available', 'error');
											}
										}}
									>
										<Settings2 class="h-3 w-3" />
										Configure Clinics
									</button>
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
										{#if !category.is_default}
											<button type="button" class="rounded-full px-3 py-1.5 text-xs font-semibold text-blue-700 cursor-pointer" style="background: rgba(59,130,246,0.12);" onclick={() => setDefault(category)}>
												<ShieldCheck class="mr-1 inline h-3.5 w-3.5" /> Default
											</button>
										{/if}
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
</div>

<!-- Category Editor Modal -->
{#if editorOpen}
	<AquaModal title={editingId ? 'Edit Insurance Category' : 'Add Insurance Category'} onclose={closeEditor} panelClass="sm:max-w-[560px]">
		<div class="space-y-4">
			<div class="grid gap-4 md:grid-cols-2">
				<div>
					<label for="insurance-category-name" class="mb-1 block text-sm font-medium text-slate-700">Name *</label>
					<input id="insurance-category-name" type="text" bind:value={formName} placeholder="e.g., Elite Care" class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
				</div>
				<div>
					<label for="insurance-category-order" class="mb-1 block text-sm font-medium text-slate-700">Sort Order</label>
					<input id="insurance-category-order" type="number" bind:value={formSortOrder} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300" />
				</div>
			</div>

			<div>
				<label for="insurance-category-description" class="mb-1 block text-sm font-medium text-slate-700">Description</label>
				<textarea id="insurance-category-description" rows="3" bind:value={formDescription} placeholder="Brief description of this insurance category" class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"></textarea>
			</div>

			<div class="grid gap-3 md:grid-cols-2">
				<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
					<span class="text-sm font-medium text-slate-700">Active category</span>
					<input type="checkbox" bind:checked={formIsActive} class="h-4 w-4" />
				</label>
				<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
					<span class="text-sm font-medium text-slate-700">Default category</span>
					<input type="checkbox" bind:checked={formIsDefault} class="h-4 w-4" />
				</label>
			</div>

			<div class="flex justify-end gap-2">
				<button type="button" class="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={closeEditor}>Cancel</button>
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

<!-- Clinic Config Editor Modal -->
{#if configEditorOpen && selectedCategory && editingConfig}
	<AquaModal title="Configure Clinics for {selectedCategory.name}" onclose={closeConfigEditor} panelClass="sm:max-w-[720px]">
		<div class="space-y-4 max-h-[60vh] overflow-y-auto">
			<p class="text-sm text-slate-500">Configure walk-in types and pricing for each clinic in this insurance category.</p>
			
			<div class="space-y-3">
				{#each selectedCategory.clinic_configs as config (config.id)}
					<div class="rounded-xl border border-slate-200 p-4" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96));">
						<div class="flex items-center gap-3 mb-3">
							<div class="h-8 w-8 rounded-lg bg-blue-100 flex items-center justify-center">
								<Building2 class="h-4 w-4 text-blue-600" />
							</div>
							<div class="flex-1">
								<p class="font-semibold text-slate-900 text-sm">{config.clinic_name}</p>
							</div>
						</div>
						
						<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
							<div>
								<label for="walkin-{config.id}" class="text-xs font-medium text-slate-500 mb-1 block">Walk-in Type</label>
								<select 
									id="walkin-{config.id}"
									class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 whitespace-pre-line"
									style="white-space: pre-line;"
									onchange={(e) => {
										if (config.id === editingConfig!.id) {
											configWalkInType = (e.target as HTMLSelectElement).value;
										} else {
											// Update via API for other configs
											insuranceCategoriesApi.updateClinicConfig(selectedCategory!.id, config.id, {
												walk_in_type: (e.target as HTMLSelectElement).value
											}).then(() => loadData());
										}
									}}
								>
									{#each walkInTypes as type}
										<option value={type.value} selected={config.walk_in_type === type.value}>{type.label}</option>
									{/each}
								</select>
								<p class="mt-1 text-xs text-slate-400">Options: No Walk In, Walkin Prime, Walkin Classic, Walkin Camp, Walk in Elite</p>
							</div>
								<div>
									<label for="fee-{config.id}" class="text-xs font-medium text-slate-500 mb-1 block">Registration Fee (₹)</label>
									<div class="relative">
										<IndianRupee class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
										<input 
											id="fee-{config.id}"
											type="number" 
											class="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
											value={config.registration_fee}
											onchange={(e) => {
												const value = parseFloat((e.target as HTMLInputElement).value);
												if (config.id === editingConfig!.id) {
													configRegistrationFee = value;
												} else {
													insuranceCategoriesApi.updateClinicConfig(selectedCategory!.id, config.id, {
														registration_fee: value
													}).then(() => loadData());
												}
											}}
										/>
									</div>
								</div>
								<div class="flex items-end">
									<label for="enabled-{config.id}" class="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
										<input 
											id="enabled-{config.id}"
											type="checkbox" 
											checked={config.is_enabled}
											class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
											onchange={(e) => {
												const checked = (e.target as HTMLInputElement).checked;
												if (config.id === editingConfig!.id) {
													configIsEnabled = checked;
												} else {
													insuranceCategoriesApi.updateClinicConfig(selectedCategory!.id, config.id, {
														is_enabled: checked
													}).then(() => loadData());
												}
											}}
										/>
										<span>Enabled</span>
									</label>
								</div>
							</div>
						</div>
					{/each}
				</div>

			<div class="flex justify-end gap-2 pt-4 border-t border-slate-200">
				<button type="button" class="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={closeConfigEditor}>Cancel</button>
				<button type="button" class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={saveClinicConfig} disabled={saving}>
					{#if saving}
						<Loader2 class="h-4 w-4 animate-spin" />
					{/if}
					Save Configuration
				</button>
			</div>
		</div>
	</AquaModal>
{/if}
