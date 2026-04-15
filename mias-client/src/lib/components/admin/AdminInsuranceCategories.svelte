<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { insuranceCategoriesApi, type InsuranceCategory } from '$lib/api/insuranceCategories';
	import { adminApi, type PatientCategoryConfig } from '$lib/api/admin';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import SystemConfigTabs from '$lib/components/admin/SystemConfigTabs.svelte';
	import { Briefcase, Building2, CircleOff, HeartPulse, Landmark, Loader2, PencilLine, Plus, ShieldCheck, Trash2, Wallet } from 'lucide-svelte';

	const auth = get(authStore);

	// State
	let loading = $state(true);
	let saving = $state(false);
	let deletingId = $state<string | null>(null);
	let categories = $state<InsuranceCategory[]>([]);
	let patientCategories = $state<PatientCategoryConfig[]>([]);
	let editorOpen = $state(false);

	// Form state
	let formName = $state('');
	let formDescription = $state('');
	let formIconKey = $state<InsuranceCategory['icon_key']>('shield');
	let formCustomBadgeSymbol = $state('');
	let formColorPrimary = $state('#60A5FA');
	let formColorSecondary = $state('#1D4ED8');
	let formIsActive = $state(true);
	let formSortOrder = $state(0);
	let formPatientCategoryIds = $state<string[]>([]);
	let editingId = $state<string | null>(null);

	const insuranceIcons = {
		shield: ShieldCheck,
		landmark: Landmark,
		briefcase: Briefcase,
		building: Building2,
		wallet: Wallet,
		heart: HeartPulse,
		off: CircleOff,
	} as const;

	const iconOptions: Array<{ value: InsuranceCategory['icon_key']; label: string }> = [
		{ value: 'shield', label: 'Shield' },
		{ value: 'landmark', label: 'Government' },
		{ value: 'briefcase', label: 'Corporate' },
		{ value: 'building', label: 'Institution' },
		{ value: 'wallet', label: 'Self pay' },
		{ value: 'heart', label: 'Health plan' },
		{ value: 'off', label: 'Uninsured' },
	];
	const PreviewIcon = $derived(insuranceIcons[formIconKey]);

	// Derived values
	const activeCategoryCount = $derived.by(() => categories.filter((item) => item.is_active).length);

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
			const [categoriesData, patientCategoriesData] = await Promise.all([
				insuranceCategoriesApi.listCategories(),
				adminApi.getPatientCategories(),
			]);
			categories = categoriesData;
			patientCategories = patientCategoriesData;
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
		formIconKey = 'shield';
		formCustomBadgeSymbol = '';
		formColorPrimary = '#60A5FA';
		formColorSecondary = '#1D4ED8';
		formIsActive = true;
		formSortOrder = categories.length;
		formPatientCategoryIds = [];
		editorOpen = true;
	}

	function openEdit(category: InsuranceCategory) {
		editingId = category.id;
		formName = category.name;
		formDescription = category.description || '';
		formIconKey = category.icon_key;
		formCustomBadgeSymbol = category.custom_badge_symbol || '';
		formColorPrimary = category.color_primary;
		formColorSecondary = category.color_secondary;
		formIsActive = category.is_active;
		formSortOrder = category.sort_order;
		formPatientCategoryIds = category.patient_categories.map(pc => pc.id);
		editorOpen = true;
	}

	function closeEditor() {
		editorOpen = false;
		editingId = null;
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
					icon_key: formIconKey,
					custom_badge_symbol: formCustomBadgeSymbol.trim() || null,
					color_primary: formColorPrimary,
					color_secondary: formColorSecondary,
					is_active: formIsActive,
					sort_order: formSortOrder,
					patient_category_ids: formPatientCategoryIds,
				});
				toastStore.addToast('Insurance category updated', 'success');
			} else {
				await insuranceCategoriesApi.createCategory({
					name: formName,
					description: formDescription,
					icon_key: formIconKey,
					custom_badge_symbol: formCustomBadgeSymbol.trim() || null,
					color_primary: formColorPrimary,
					color_secondary: formColorSecondary,
					is_active: formIsActive,
					sort_order: formSortOrder,
					patient_category_ids: formPatientCategoryIds,
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
</script>

<div class="space-y-4">
	<div class="rounded-[24px] border border-slate-200 p-3"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.92), rgba(246,249,255,0.92)); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
		<SystemConfigTabs activeTab="insurance" />
	</div>

	<div class="grid gap-4 md:grid-cols-2">
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
	</div>

	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
		<div class="mb-4 rounded-[18px] border border-sky-200/80 px-4 py-3 text-sm text-slate-600"
			style="background: linear-gradient(135deg, rgba(239,246,255,0.95), rgba(224,242,254,0.92));">
			Insurance settings control the badge symbol itself. Patient-type glow colors are configured separately in the Patients tab.
		</div>
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
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Preview</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Name</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Patient Categories</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Status</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each categories as category (category.id)}
							{@const CategoryIcon = insuranceIcons[category.icon_key]}
							<tr class="border-t border-slate-200 align-top">
								<td class="px-4 py-4">
									<div class="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold"
										style={`background: linear-gradient(135deg, ${category.color_primary}, ${category.color_secondary}); color: white; box-shadow: 0 10px 20px rgba(15,23,42,0.12);`}>
										{#if category.custom_badge_symbol}
											<span class="text-[10px] font-black leading-none tracking-tight">{category.custom_badge_symbol}</span>
										{:else}
											<CategoryIcon class="h-3.5 w-3.5" />
										{/if}
										<span>Live</span>
									</div>
								</td>
								<td class="px-4 py-4">
									<div class="flex items-center gap-2">
										<p class="font-semibold text-slate-900">{category.name}</p>
									</div>
									{#if category.description}
										<p class="text-xs text-slate-500 mt-1">{category.description}</p>
									{/if}
								</td>
								<td class="px-4 py-4">
									{#if category.patient_categories.length > 0}
										<div class="flex flex-wrap gap-1">
											{#each category.patient_categories as pc}
												<span class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium text-blue-700" style="background: rgba(59,130,246,0.12);">
													{pc.name}
												</span>
											{/each}
										</div>
									{:else}
										<span class="text-sm text-slate-400">None</span>
									{/if}
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
</div>

<!-- Category Editor Modal -->
{#if editorOpen}
	<AquaModal title={editingId ? 'Edit Insurance Category' : 'Add Insurance Category'} onclose={closeEditor} panelClass="sm:max-w-[560px]">
		<div class="space-y-4">
			<div class="rounded-[18px] border border-slate-200 p-4"
				style={`background: linear-gradient(135deg, ${formColorPrimary}, ${formColorSecondary}); box-shadow: 0 12px 24px rgba(15,23,42,0.08);`}>
				<div class="flex items-center gap-3 text-white">
					<div class="flex h-10 w-10 items-center justify-center rounded-full border border-white/40 bg-white/15">
						{#if formCustomBadgeSymbol.trim()}
							<span class="text-sm font-black leading-none tracking-tight">{formCustomBadgeSymbol.trim().slice(0, 3).toUpperCase()}</span>
						{:else}
							<PreviewIcon class="h-5 w-5" />
						{/if}
					</div>
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-white/75">Insurance Badge Preview</p>
						<p class="text-sm font-bold">{formName || 'Insurance category'}</p>
					</div>
				</div>
			</div>

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

			<div class="grid gap-4 md:grid-cols-3">
				<div>
					<label for="insurance-category-icon" class="mb-1 block text-sm font-medium text-slate-700">Symbol</label>
					<select id="insurance-category-icon" bind:value={formIconKey} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300">
						{#each iconOptions as option}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="insurance-category-custom-symbol" class="mb-1 block text-sm font-medium text-slate-700">Custom Badge</label>
					<input id="insurance-category-custom-symbol" type="text" bind:value={formCustomBadgeSymbol} maxlength="3" placeholder="e.g. TP" class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-blue-300" />
					<p class="mt-1 text-xs text-slate-500">Optional. If set, this overrides the icon in the patient badge.</p>
				</div>
				<div>
					<label for="insurance-category-primary-color" class="mb-1 block text-sm font-medium text-slate-700">Primary Color</label>
					<input id="insurance-category-primary-color" type="color" bind:value={formColorPrimary} class="h-12 w-full rounded-2xl border border-slate-200 px-2 py-2" />
				</div>
				<div>
					<label for="insurance-category-secondary-color" class="mb-1 block text-sm font-medium text-slate-700">Secondary Color</label>
					<input id="insurance-category-secondary-color" type="color" bind:value={formColorSecondary} class="h-12 w-full rounded-2xl border border-slate-200 px-2 py-2" />
				</div>
			</div>

			<div>
				<div class="mb-1 text-sm font-medium text-slate-700">Patient Categories</div>
				<div class="space-y-2 max-h-40 overflow-y-auto rounded-2xl border border-slate-200 p-3">
					{#each patientCategories as pc}
						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								bind:group={formPatientCategoryIds}
								value={pc.id}
								class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
							/>
							<span class="text-slate-700">{pc.name}</span>
						</label>
					{/each}
				</div>
				<p class="mt-1 text-xs text-slate-500">Select which patient categories belong to this insurance category</p>
			</div>

			<div class="grid gap-3 md:grid-cols-2">
				<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
					<span class="text-sm font-medium text-slate-700">Active category</span>
					<input type="checkbox" bind:checked={formIsActive} class="h-4 w-4" />
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
