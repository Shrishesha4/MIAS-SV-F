<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { chargesApi, type ChargeItem, type ChargeCategory, type ChargeTier, type CreateChargeItemRequest } from '$lib/api/labs';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { Plus, Trash2, Pencil, IndianRupee, Check, X } from 'lucide-svelte';

	type ChargeMetaDraft = {
		name: string;
		item_code: string;
		category: ChargeCategory;
		description: string;
	};

	type PriceEditState = {
		chargeId: string;
		tier: ChargeTier;
		value: string;
	};

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let charges: ChargeItem[] = $state([]);
	let activeCategory: ChargeCategory = $state('CLINICAL');

	const categoryTabs = [
		{ id: 'CLINICAL', label: 'CLINICAL' },
		{ id: 'LABS', label: 'LABS' },
		{ id: 'ADMIN', label: 'ADMIN' }
	];

	const tiers: ChargeTier[] = ['CLASSIC', 'PRIME', 'ELITE', 'COMMUNITY'];
	const tierLabels: Record<ChargeTier, string> = {
		CLASSIC: 'Classic',
		PRIME: 'Prime',
		ELITE: 'Elite',
		COMMUNITY: 'Community'
	};

	// Add/Edit modal
	let chargeModal = $state(false);
	let editingCharge: ChargeItem | null = $state(null);
	let chargeData = $state<CreateChargeItemRequest>({
		item_code: '',
		name: '',
		category: 'CLINICAL',
		description: '',
		is_active: true,
		prices: { CLASSIC: 0, PRIME: 0, ELITE: 0, COMMUNITY: 0 }
	});
	let savingCharge = $state(false);
	let editingMetaId = $state<string | null>(null);
	let metaDraft = $state<ChargeMetaDraft>({
		name: '',
		item_code: '',
		category: 'CLINICAL',
		description: ''
	});
	let savingMeta = $state(false);
	let editingPrice = $state<PriceEditState | null>(null);
	let savingPrice = $state(false);

	// Delete confirmation
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	const filteredCharges = $derived(charges.filter(c => c.category === activeCategory));

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		loadCharges();
	});

	async function loadCharges() {
		loading = true;
		error = '';
		try {
			charges = await chargesApi.getAll();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load charges';
		} finally {
			loading = false;
		}
	}

	function updateChargeInState(updatedCharge: ChargeItem) {
		charges = charges.map((charge) => (charge.id === updatedCharge.id ? updatedCharge : charge));
	}

	function startMetaEdit(charge: ChargeItem) {
		editingPrice = null;
		editingMetaId = charge.id;
		metaDraft = {
			name: charge.name,
			item_code: charge.item_code,
			category: charge.category,
			description: charge.description || ''
		};
	}

	function cancelMetaEdit() {
		editingMetaId = null;
		metaDraft = {
			name: '',
			item_code: '',
			category: 'CLINICAL',
			description: ''
		};
	}

	async function saveMetaEdit(charge: ChargeItem) {
		if (!metaDraft.name.trim() || !metaDraft.item_code.trim()) {
			toastStore.addToast('Title and code are required', 'error');
			return;
		}

		savingMeta = true;
		try {
			const updated = await chargesApi.update(charge.id, {
				name: metaDraft.name.trim(),
				item_code: metaDraft.item_code.trim(),
				category: metaDraft.category,
				description: metaDraft.description.trim() || undefined
			});
			updateChargeInState(updated);
			cancelMetaEdit();
			toastStore.addToast('Charge details updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update charge details', 'error');
		} finally {
			savingMeta = false;
		}
	}

	function startPriceEdit(charge: ChargeItem, tier: ChargeTier) {
		editingMetaId = null;
		editingPrice = {
			chargeId: charge.id,
			tier,
			value: String(charge.prices[tier] ?? 0)
		};
	}

	function cancelPriceEdit() {
		editingPrice = null;
	}

	async function savePriceEdit(charge: ChargeItem) {
		if (!editingPrice || editingPrice.chargeId !== charge.id) return;

		const nextPrice = Number(editingPrice.value);
		if (!Number.isFinite(nextPrice) || nextPrice < 0) {
			toastStore.addToast('Price must be a valid non-negative number', 'error');
			return;
		}

		savingPrice = true;
		try {
			const updated = await chargesApi.update(charge.id, {
				prices: { [editingPrice.tier]: nextPrice }
			});
			updateChargeInState(updated);
			cancelPriceEdit();
			toastStore.addToast('Price updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update price', 'error');
		} finally {
			savingPrice = false;
		}
	}

	function openCreateModal() {
		editingCharge = null;
		chargeData = {
			name: '',
			item_code: '',
			category: activeCategory,
			description: '',
			is_active: true,
			prices: { CLASSIC: 0, PRIME: 0, ELITE: 0, COMMUNITY: 0 }
		};
		chargeModal = true;
	}

	async function saveCharge() {
		if (!chargeData.name.trim() || !chargeData.item_code.trim()) {
			toastStore.addToast('Name and code are required', 'error');
			return;
		}
		savingCharge = true;
		try {
			if (editingCharge) {
				await chargesApi.update(editingCharge.id, chargeData);
				toastStore.addToast('Charge updated successfully', 'success');
			} else {
				await chargesApi.create(chargeData);
				toastStore.addToast('Charge created successfully', 'success');
			}
			chargeModal = false;
			await loadCharges();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save charge', 'error');
		} finally {
			savingCharge = false;
		}
	}

	function confirmDeleteCharge(charge: ChargeItem) {
		confirmMessage = `Delete charge "${charge.name}"?`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await chargesApi.delete(charge.id);
				toastStore.addToast('Charge deleted', 'success');
				await loadCharges();
			} catch (e: any) {
				toastStore.addToast('Failed to delete charge', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	function formatPrice(price: number): string {
		return '₹' + price.toLocaleString('en-IN');
	}
</script>

<AdminScaffold navItems={adminPageNavItems} title="Charge Master" activeNav="charges" titleIcon={IndianRupee}>
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-4 text-sm">{error}</div>
	{:else}
		<div class="flex items-center justify-between mb-4">
			<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Charge Master (Rates)</p>
			<button
				onclick={openCreateModal}
				class="px-4 py-2 text-sm font-semibold text-white rounded-full"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
			>
				Add New
			</button>
		</div>

		<!-- Category Tabs -->
		<div class="mb-4">
			<TabBar tabs={categoryTabs} activeTab={activeCategory} onchange={(id) => activeCategory = id as ChargeCategory} />
		</div>

		<!-- Pricing Table -->
		<div
			class="rounded-2xl overflow-hidden"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
		>
			<!-- Table Header -->
			<div class="grid grid-cols-6 gap-2 px-4 py-3" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);">
				<div class="col-span-2 text-xs font-bold text-slate-700 uppercase tracking-wide">Item</div>
				{#each tiers as tier}
					<div class="text-xs font-bold text-slate-700 uppercase tracking-wide text-center">{tierLabels[tier]}</div>
				{/each}
			</div>

			<!-- Table Body -->
			{#if filteredCharges.length === 0}
				<div class="px-4 py-8 text-center text-slate-500 text-sm">
					No charges in this category. Click "Add New" to create one.
				</div>
			{:else}
				{#each filteredCharges as charge, i (charge.id)}
					{@const isEditingMeta = editingMetaId === charge.id}
					<div
						class="grid grid-cols-6 gap-2 px-4 py-3 items-center group"
						class:border-t={i > 0}
						style={i > 0 ? 'border-color: rgba(0,0,0,0.06);' : ''}
					>
						<div class="col-span-2">
							{#if isEditingMeta}
								<div class="space-y-2 rounded-xl border border-blue-200/70 bg-blue-50/55 p-3">
									<input
										type="text"
										class="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm font-semibold text-slate-900"
										style="background: rgba(255,255,255,0.95);"
										bind:value={metaDraft.name}
										placeholder="Title"
									/>
									<div class="grid grid-cols-[minmax(0,1fr)_120px] gap-2">
										<input
											type="text"
											class="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600"
											style="background: rgba(255,255,255,0.95);"
											bind:value={metaDraft.item_code}
											placeholder="Code"
										/>
										<select
											class="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600"
											style="background: rgba(255,255,255,0.95);"
											bind:value={metaDraft.category}
										>
											<option value="CLINICAL">Clinical</option>
											<option value="LABS">Labs</option>
											<option value="ADMIN">Admin</option>
										</select>
									</div>
									<input
										type="text"
										class="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600"
										style="background: rgba(255,255,255,0.95);"
										bind:value={metaDraft.description}
										placeholder="Description"
									/>
									<div class="flex items-center justify-end gap-1.5">
										<button
											onclick={() => saveMetaEdit(charge)}
											class="flex h-7 w-7 items-center justify-center rounded-full text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
											disabled={savingMeta}
										>
											<Check class="h-3.5 w-3.5" />
										</button>
										<button
											onclick={cancelMetaEdit}
											class="flex h-7 w-7 items-center justify-center rounded-full text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #94a3b8, #64748b);"
											disabled={savingMeta}
										>
											<X class="h-3.5 w-3.5" />
										</button>
									</div>
								</div>
							{:else}
								<div class="flex items-start gap-2">
									<div class="min-w-0 flex-1">
										<p class="font-semibold text-slate-900 text-sm">{charge.name}</p>
										<div class="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
											<span>{charge.item_code}</span>
											<span class="rounded-full px-2 py-0.5 font-semibold"
												style="background: rgba(59,130,246,0.1); color: #1d4ed8;">
												{charge.category}
											</span>
										</div>
										{#if charge.description}
											<p class="mt-1 line-clamp-2 text-xs text-slate-400">{charge.description}</p>
										{/if}
									</div>
									<div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
										<button onclick={() => startMetaEdit(charge)} class="p-1 text-slate-400 hover:text-blue-500 cursor-pointer">
											<Pencil class="w-3.5 h-3.5" />
										</button>
										<button onclick={() => confirmDeleteCharge(charge)} class="p-1 text-slate-400 hover:text-red-500 cursor-pointer">
											<Trash2 class="w-3.5 h-3.5" />
										</button>
									</div>
								</div>
							{/if}
						</div>
						{#each tiers as tier}
							{@const isEditingThisPrice = editingPrice?.chargeId === charge.id && editingPrice?.tier === tier}
							<div class="flex justify-center">
								{#if isEditingThisPrice}
									<div class="flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50/60 px-2 py-1">
										<span class="text-xs font-semibold text-slate-500">₹</span>
										<input
											type="number"
											min="0"
											step="1"
											class="w-16 bg-transparent text-center text-sm font-semibold text-slate-800 outline-none"
											value={editingPrice?.value ?? ''}
											oninput={(event) => {
												if (editingPrice) {
													editingPrice.value = (event.currentTarget as HTMLInputElement).value;
												}
											}}
											onkeydown={(event) => {
												if (event.key === 'Enter') {
													savePriceEdit(charge);
												}
												if (event.key === 'Escape') {
													cancelPriceEdit();
												}
											}}
										/>
										<button
											onclick={() => savePriceEdit(charge)}
											class="flex h-6 w-6 items-center justify-center rounded-full text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
											disabled={savingPrice}
										>
											<Check class="h-3 w-3" />
										</button>
										<button
											onclick={cancelPriceEdit}
											class="flex h-6 w-6 items-center justify-center rounded-full text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #94a3b8, #64748b);"
											disabled={savingPrice}
										>
											<X class="h-3 w-3" />
										</button>
									</div>
								{:else}
									<button
										onclick={() => startPriceEdit(charge, tier)}
										class="min-w-[92px] rounded-xl px-3 py-2 text-sm font-semibold text-slate-800 cursor-pointer transition-colors hover:bg-slate-100"
										style="background: linear-gradient(to bottom, rgba(248,250,252,0.96), rgba(241,245,249,0.92)); border: 1px solid rgba(148,163,184,0.18);"
									>
										{formatPrice(charge.prices[tier])}
									</button>
								{/if}
							</div>
						{/each}
					</div>
				{/each}
			{/if}
		</div>

		<!-- Legend -->
		<div class="mt-4 p-3 rounded-xl" style="background: linear-gradient(to bottom, #fffbeb, #fef3c7); border: 1px solid rgba(217,119,6,0.2);">
			<p class="text-xs font-semibold text-amber-800 mb-2">Pricing Tiers</p>
			<div class="grid grid-cols-2 gap-2 text-xs text-amber-700">
				<div><span class="font-semibold">Classic:</span> Standard ward patients</div>
				<div><span class="font-semibold">Prime:</span> Semi-private rooms</div>
				<div><span class="font-semibold">Elite:</span> Private/Deluxe rooms</div>
				<div><span class="font-semibold">Community:</span> Subsidized care</div>
			</div>
		</div>
	{/if}
</AdminScaffold>

{#if chargeModal}
	<AquaModal title={editingCharge ? 'Edit Charge Item' : 'Add New Charge Item'} onclose={() => { chargeModal = false; }}>
		<div class="space-y-3">
			<div>
				<label for="charge-name" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Name *</label>
				<input id="charge-name" type="text" placeholder="e.g., Blood Test - CBC" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.name} />
			</div>
			<div>
				<label for="charge-code" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Item Code *</label>
				<input id="charge-code" type="text" placeholder="e.g., LAB-CBC-001" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.item_code} />
			</div>
			<div>
				<label for="charge-category" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Category</label>
				<select id="charge-category" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.category}>
					<option value="CLINICAL">Clinical</option>
					<option value="LABS">Labs</option>
					<option value="ADMIN">Admin</option>
				</select>
			</div>
			<div>
				<label for="charge-desc" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Description</label>
				<input id="charge-desc" type="text" placeholder="Optional description" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.description} />
			</div>

			<div>
				<p class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">Pricing (₹)</p>
				<div class="grid grid-cols-2 gap-2">
					{#each tiers as tier}
						<div>
							<label for="price-{tier}" class="block text-xs text-slate-500 mb-1">{tierLabels[tier]}</label>
							<input
								id="price-{tier}"
								type="number"
								min="0"
								step="1"
								class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl"
								style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
								bind:value={chargeData.prices![tier]}
							/>
						</div>
					{/each}
				</div>
			</div>

			<div class="flex items-center gap-2">
				<input type="checkbox" id="charge-active" class="rounded" bind:checked={chargeData.is_active} />
				<label for="charge-active" class="text-sm text-slate-700">Active</label>
			</div>
		</div>
		<div class="flex gap-2 mt-4">
			<button onclick={() => { chargeModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingCharge}>Cancel</button>
			<button onclick={saveCharge} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" disabled={savingCharge}>{savingCharge ? 'Saving...' : editingCharge ? 'Update' : 'Create'}</button>
		</div>
	</AquaModal>
{/if}

{#if confirmModal}
	<AquaModal title="Confirm Delete" onclose={() => { confirmModal = false; }}>
		<p class="text-sm text-slate-700 mb-4">{confirmMessage}</p>
		<div class="flex gap-2">
			<button onclick={() => { confirmModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={actionLoading}>Cancel</button>
			<button onclick={() => confirmAction?.()} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #ef4444, #dc2626);" disabled={actionLoading}>{actionLoading ? 'Deleting...' : 'Delete'}</button>
		</div>
	</AquaModal>
{/if}
