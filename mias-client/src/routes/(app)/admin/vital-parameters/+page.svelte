<script lang="ts">
	import { onMount } from 'svelte';
	import { adminApi, type VitalParameter } from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { Heart, Plus, Edit2, Trash2, Check, X } from 'lucide-svelte';

	let parameters: VitalParameter[] = $state([]);
	let loading = $state(true);
	let saving = $state(false);

	// Modal state
	let showModal = $state(false);
	let editingParam: VitalParameter | null = $state(null);
	let formData = $state({
		name: '',
		display_name: '',
		category: 'Primary',
		unit: '',
		value_style: 'single' as 'single' | 'slash',
		min_value: '',
		max_value: '',
		sort_order: 0,
		is_active: true
	});

	const categories = ['Primary', 'Secondary', 'Biochemistry', 'Haematology'];
	const unitPresets = ['mmHg', 'bpm', '%', '°F', '/min', 'mg/dL', 'kg', 'lbs', 'mEq/L', 'U/L', 'g/dL', '×10³/µL', '×10⁶/µL'];

	async function loadParameters() {
		try {
			loading = true;
			parameters = await adminApi.getVitalParameters();
		} catch (err) {
			toastStore.addToast('Failed to load vital parameters', 'error');
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		editingParam = null;
		formData = {
			name: '',
			display_name: '',
			category: 'Primary',
			unit: '',
			value_style: 'single',
			min_value: '',
			max_value: '',
			sort_order: parameters.length,
			is_active: true
		};
		showModal = true;
	}

	function openEditModal(param: VitalParameter) {
		editingParam = param;
		formData = {
			name: param.name,
			display_name: param.display_name,
			category: param.category,
			unit: param.unit || '',
			value_style: param.value_style || 'single',
			min_value: param.min_value?.toString() || '',
			max_value: param.max_value?.toString() || '',
			sort_order: param.sort_order,
			is_active: param.is_active
		};
		showModal = true;
	}

	async function handleSave() {
		if (!formData.name.trim() || !formData.display_name.trim() || !formData.unit.trim()) {
			toastStore.addToast('Name, display name, and unit are required', 'error');
			return;
		}

		saving = true;
		try {
			const data = {
				name: formData.name.trim(),
				display_name: formData.display_name.trim(),
				category: formData.category,
				unit: formData.unit.trim(),
				min_value: formData.min_value ? parseFloat(formData.min_value) : undefined,
				max_value: formData.max_value ? parseFloat(formData.max_value) : undefined,
				value_style: formData.value_style,
				sort_order: formData.sort_order,
				is_active: formData.is_active
			};

			if (editingParam) {
				await adminApi.updateVitalParameter(editingParam.id, data);
				toastStore.addToast('Vital parameter updated', 'success');
			} else {
				await adminApi.createVitalParameter(data);
				toastStore.addToast('Vital parameter created', 'success');
			}
			showModal = false;
			await loadParameters();
		} catch (err: any) {
			toastStore.addToast(err.response?.data?.detail || 'Failed to save parameter', 'error');
		} finally {
			saving = false;
		}
	}

	async function handleDelete(param: VitalParameter) {
		if (!confirm(`Are you sure you want to deactivate "${param.display_name}"?`)) return;
		try {
			await adminApi.deleteVitalParameter(param.id);
			toastStore.addToast('Vital parameter deactivated', 'success');
			await loadParameters();
		} catch (err) {
			toastStore.addToast('Failed to deactivate parameter', 'error');
		}
	}

	async function toggleActive(param: VitalParameter) {
		try {
			await adminApi.updateVitalParameter(param.id, { is_active: !param.is_active });
			await loadParameters();
		} catch (err) {
			toastStore.addToast('Failed to update parameter', 'error');
		}
	}

	onMount(loadParameters);

	const groupedParams = $derived(() => {
		const groups: Record<string, VitalParameter[]> = {};
		for (const cat of categories) groups[cat] = [];
		for (const p of parameters) {
			if (!groups[p.category]) groups[p.category] = [];
			groups[p.category].push(p);
		}
		return groups;
	});
</script>

	<div class="p-4 space-y-4">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-xl font-bold text-gray-800">Manage Vital Parameters</h2>
				<p class="text-sm text-gray-500">Configure which vitals appear in patient monitoring forms</p>
			</div>
			<AquaButton variant="primary" onclick={openCreateModal}>
				<Plus class="w-4 h-4" />
			</AquaButton>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-20">
				<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
			</div>
		{:else}
			{#each categories as category}
				{@const catParams = groupedParams()[category]}
				{#if catParams.length > 0}
					<AquaCard>
						<h3 class="font-bold text-gray-800 mb-3">{category} Vitals</h3>
						<div class="space-y-2">
							{#each catParams as param}
								<div class="flex items-center justify-between p-3 rounded-lg"
									style="background: {param.is_active ? '#f8f9fb' : '#fef2f2'}; border: 1px solid rgba(0,0,0,0.06);">
									<div class="flex items-center gap-3">
										<div class="w-8 h-8 rounded-lg flex items-center justify-center"
											style="background: linear-gradient(to bottom, {param.is_active ? '#3b82f6' : '#ef4444'}, {param.is_active ? '#2563eb' : '#dc2626'});">
											<Heart class="w-4 h-4 text-white" />
										</div>
										<div>
											<p class="font-medium text-gray-800">{param.display_name}</p>
											<p class="text-xs text-gray-500">
												{param.name}
												{#if param.unit}· {param.unit}{/if}
												· {param.value_style === 'slash' ? 'Slash value' : 'Single value'}
												{#if param.min_value !== null && param.max_value !== null}
													· Range: {param.min_value}-{param.max_value}
												{/if}
											</p>
										</div>
									</div>
									<div class="flex items-center gap-2">
										<button
											class="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
											onclick={() => toggleActive(param)}
											title={param.is_active ? 'Deactivate' : 'Activate'}
										>
											{#if param.is_active}
												<Check class="w-4 h-4 text-green-600" />
											{:else}
												<X class="w-4 h-4 text-red-500" />
											{/if}
										</button>
										<button
											class="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
											onclick={() => openEditModal(param)}
										>
											<Edit2 class="w-4 h-4 text-blue-600" />
										</button>
										<!-- Delete action hidden until admin disable flow replaces hard delete UI. -->
										<!--
										<button
											class="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
											onclick={() => handleDelete(param)}
										>
											<Trash2 class="w-4 h-4 text-red-500" />
										</button>
										-->
									</div>
								</div>
							{/each}
						</div>
					</AquaCard>
				{/if}
			{/each}

			{#if parameters.length === 0}
				<AquaCard>
					<div class="text-center py-8">
						<Heart class="w-12 h-12 text-gray-300 mx-auto mb-3" />
						<p class="text-gray-500">No vital parameters configured</p>
						<p class="text-sm text-gray-400 mb-4">Add parameters to configure the vitals form</p>
						<AquaButton variant="primary" onclick={openCreateModal}>
							<Plus class="w-4 h-4 mr-1" /> Add First Parameter
						</AquaButton>
					</div>
				</AquaCard>
			{/if}
		{/if}
	</div>

{#if showModal}
	<AquaModal title={editingParam ? 'Edit Vital Parameter' : 'Add Vital Parameter'} onclose={() => showModal = false}>
		<div class="space-y-4">
			<div>
				<label for="param-name" class="block text-sm font-medium text-gray-700 mb-1">Field Name (unique identifier)</label>
				<input
					id="param-name"
					type="text"
					class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder="e.g., systolic_bp"
					bind:value={formData.name}
					disabled={!!editingParam}
				/>
				{#if editingParam}
					<p class="text-xs text-gray-400 mt-1">Field name cannot be changed after creation</p>
				{/if}
			</div>

			<div>
				<label for="param-display" class="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
				<input
					id="param-display"
					type="text"
					class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder="e.g., Systolic BP"
					bind:value={formData.display_name}
				/>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="param-category" class="block text-sm font-medium text-gray-700 mb-1">Category</label>
					<select
						id="param-category"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
						bind:value={formData.category}
					>
						{#each categories as cat}
							<option value={cat}>{cat}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="param-unit" class="block text-sm font-medium text-gray-700 mb-1">Unit</label>
					<input
						id="param-unit"
						type="text"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
						placeholder="e.g., mmHg"
						bind:value={formData.unit}
						required
					/>
				</div>
			</div>

			<div class="space-y-2">
				<div class="flex flex-wrap gap-2">
					{#each unitPresets as preset (preset)}
						<button
							type="button"
							class="rounded-full px-3 py-1 text-xs font-semibold transition-colors"
							style="background: {formData.unit === preset ? 'rgba(59,130,246,0.12)' : '#f8fafc'}; color: {formData.unit === preset ? '#2563eb' : '#475569'}; border: 1px solid {formData.unit === preset ? 'rgba(59,130,246,0.26)' : 'rgba(148,163,184,0.22)'};"
							onclick={() => formData.unit = preset}
						>
							{preset}
						</button>
					{/each}
				</div>
				<p class="text-xs text-gray-400">Pick a unit or type your own. Every vital parameter now requires one.</p>
			</div>

			<fieldset class="space-y-2">
				<legend class="block text-sm font-medium text-gray-700 mb-2">Value Style</legend>
				<div class="grid grid-cols-2 gap-2">
					<button
						type="button"
						class="rounded-xl px-3 py-2 text-sm font-semibold transition-colors"
						style="background: {formData.value_style === 'single' ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : '#f8fafc'}; color: {formData.value_style === 'single' ? '#2563eb' : '#475569'}; border: 1px solid {formData.value_style === 'single' ? 'rgba(59,130,246,0.24)' : 'rgba(148,163,184,0.22)'};"
						onclick={() => formData.value_style = 'single'}
					>
						Single value
					</button>
					<button
						type="button"
						class="rounded-xl px-3 py-2 text-sm font-semibold transition-colors"
						style="background: {formData.value_style === 'slash' ? 'linear-gradient(to bottom, #eff6ff, #dbeafe)' : '#f8fafc'}; color: {formData.value_style === 'slash' ? '#2563eb' : '#475569'}; border: 1px solid {formData.value_style === 'slash' ? 'rgba(59,130,246,0.24)' : 'rgba(148,163,184,0.22)'};"
						onclick={() => formData.value_style = 'slash'}
					>
						Slash style
					</button>
				</div>
				<p class="mt-2 text-xs text-gray-400">Use slash style for paired readings such as pressure-style values. Use single value for normal numeric vitals.</p>
			</fieldset>

			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="param-min" class="block text-sm font-medium text-gray-700 mb-1">Min Value</label>
					<input
						id="param-min"
						type="number"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
						placeholder="Optional"
						bind:value={formData.min_value}
					/>
				</div>

				<div>
					<label for="param-max" class="block text-sm font-medium text-gray-700 mb-1">Max Value</label>
					<input
						id="param-max"
						type="number"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
						placeholder="Optional"
						bind:value={formData.max_value}
					/>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div>
					<label for="param-sort" class="block text-sm font-medium text-gray-700 mb-1">Sort Order</label>
					<input
						id="param-sort"
						type="number"
						class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
						bind:value={formData.sort_order}
					/>
				</div>

				<div class="flex items-center pt-6">
					<label class="flex items-center gap-2 cursor-pointer">
						<input id="param-active" type="checkbox" class="w-4 h-4" bind:checked={formData.is_active} />
						<span class="text-sm text-gray-700">Active</span>
					</label>
				</div>
			</div>

			<div class="flex gap-2 justify-end pt-4 border-t border-gray-100">
				<AquaButton variant="secondary" onclick={() => showModal = false}>Cancel</AquaButton>
				<AquaButton variant="primary" loading={saving} onclick={handleSave}>
					{editingParam ? 'Update' : 'Create'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
