<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type PatientCategoryConfig } from '$lib/api/admin';
	import { insuranceCategoriesApi, type InsuranceCategory } from '$lib/api/insuranceCategories';
	import { chargesApi, type ChargeItem, type ChargeCategory, type ChargeTier, type CreateChargeItemRequest } from '$lib/api/labs';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { Pencil, Check, Power, X } from 'lucide-svelte';

	type ChargeMetaDraft = {
		name: string;
		item_code: string;
		category: ChargeCategory;
		description: string;
	};

	type PricingTierOption = {
		key: string;
		insuranceId: string | null;
		insuranceName: string;
		patientCategoryId: string | null;
		patientCategoryName: string;
		isLegacy?: boolean;
	};

	type PricingColumnGroup = {
		id: string;
		label: string;
		tiers: PricingTierOption[];
		isLegacy?: boolean;
	};

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let charges: ChargeItem[] = $state([]);
	let priceCategories = $state<PatientCategoryConfig[]>([]);
	let insuranceCategories = $state<InsuranceCategory[]>([]);
	let activeCategory: ChargeCategory = $state('REGISTRATION');
	
	// Registration fees keyed by "insuranceId::patientCategoryId" — per combo
	let registrationFees = $state<Record<string, number>>({});
	// Map "insuranceId::patientCategoryId" -> { clinicId, walkInType } for saving
	let regFeeClinicMap = $state<Record<string, { clinicId: string; walkInType: string }>>({});
	let editingRegFee = $state<{ insuranceId: string; categoryId: string; value: string } | null>(null);
	let savingRegFee = $state(false);

	const categoryTabs = [
		{ id: 'REGISTRATION', label: 'REGISTRATION' },
		{ id: 'CLINICAL', label: 'CLINICAL' },
		{ id: 'LABS', label: 'LABS' },
		{ id: 'ADMIN', label: 'ADMIN' }
	];

	// Add/Edit modal
	let chargeModal = $state(false);
	let editingCharge: ChargeItem | null = $state(null);
	let chargeData = $state<CreateChargeItemRequest>({
		item_code: '',
		name: '',
		category: 'CLINICAL',
		description: '',
		is_active: true,
		prices: {}
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
	let priceDrafts = $state<Record<string, string>>({});
	let savingPriceKey = $state<string | null>(null);
	let togglingChargeId = $state<string | null>(null);

	// Delete confirmation
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	const filteredCharges = $derived.by(() => charges.filter((charge) => charge.category === activeCategory));

	function sortPatientCategories(categories: PatientCategoryConfig[]) {
		return [...categories].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
	}

	function sortInsuranceCategories(categories: InsuranceCategory[]) {
		return [...categories].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
	}

	function sortInsurancePatientCategories(categories: InsuranceCategory['patient_categories']) {
		return [...categories].sort((left, right) => left.name.localeCompare(right.name));
	}

	function normalizePricingKey(value: string): string {
		return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
	}

	function buildPricingGroups(
		chargeItems: ChargeItem[],
		categoryItems: PatientCategoryConfig[],
		insuranceItems: InsuranceCategory[]
	): PricingColumnGroup[] {
		const groups: PricingColumnGroup[] = sortPatientCategories(categoryItems).map((category) => ({
			id: category.id,
			label: category.name,
			tiers: []
		}));
		const groupsByCategoryName = new Map(groups.map((group) => [normalizePricingKey(group.label), group]));
		const seenTierKeys = new Set<string>();

		for (const insurance of sortInsuranceCategories(insuranceItems)) {
			for (const patientCategory of sortInsurancePatientCategories(insurance.patient_categories || [])) {
				const group = groupsByCategoryName.get(normalizePricingKey(patientCategory.name));
				if (!group) {
					continue;
				}

				const tierKey = `${insurance.name} - ${patientCategory.name}`;
				const normalizedTierKey = normalizePricingKey(tierKey);
				if (seenTierKeys.has(normalizedTierKey)) {
					continue;
				}

				group.tiers.push({
					key: tierKey,
					insuranceId: insurance.id,
					insuranceName: insurance.name,
					patientCategoryId: patientCategory.id,
					patientCategoryName: patientCategory.name
				});
				seenTierKeys.add(normalizedTierKey);
			}
		}

		for (const charge of chargeItems) {
			for (const existingTierKey of Object.keys(charge.prices || {})) {
				const normalizedTierKey = normalizePricingKey(existingTierKey);
				if (!normalizedTierKey || seenTierKeys.has(normalizedTierKey)) {
					continue;
				}

				const matchedGroup = groups.find((group) => normalizedTierKey.endsWith(`- ${normalizePricingKey(group.label)}`));
				if (matchedGroup) {
					matchedGroup.tiers.push({
						key: existingTierKey,
						insuranceId: null,
						insuranceName: existingTierKey.replace(new RegExp(`\\s*-\\s*${matchedGroup.label}$`, 'i'), '').trim() || existingTierKey,
						patientCategoryId: matchedGroup.id,
						patientCategoryName: matchedGroup.label,
						isLegacy: true
					});
				} else {
					let legacyGroup = groups.find((group) => group.id === '__legacy__');
					if (!legacyGroup) {
						legacyGroup = {
							id: '__legacy__',
							label: 'Other',
							tiers: [],
							isLegacy: true
						};
						groups.push(legacyGroup);
					}

					legacyGroup.tiers.push({
						key: existingTierKey,
						insuranceId: null,
						insuranceName: existingTierKey,
						patientCategoryId: null,
						patientCategoryName: legacyGroup.label,
						isLegacy: true
					});
				}

				seenTierKeys.add(normalizedTierKey);
			}
		}

		return groups;
	}

	function flattenPricingGroups(groups: PricingColumnGroup[]): string[] {
		return groups.flatMap((group) => group.tiers.map((tier) => tier.key));
	}

	const pricingGroups = $derived.by(() => buildPricingGroups(charges, priceCategories, insuranceCategories));
	const pricingColumns = $derived.by(() => flattenPricingGroups(pricingGroups));
	const tableGridStyle = $derived.by(() => `grid-template-columns: minmax(200px, 1.2fr) repeat(${Math.max(pricingGroups.length, 1)}, minmax(148px, 0.92fr));`);

	function buildEmptyPrices(categoryNames: string[]): Record<string, number> {
		return Object.fromEntries(categoryNames.map((categoryName) => [categoryName, 0]));
	}

	function mergeChargePrices(charge: ChargeItem, categoryNames: string[]): ChargeItem {
		const mergedPrices = buildEmptyPrices(categoryNames);
		for (const [categoryName, price] of Object.entries(charge.prices || {})) {
			mergedPrices[categoryName] = price;
		}

		return {
			...charge,
			prices: mergedPrices,
		};
	}

	function priceInputId(categoryName: string): string {
		return `charge-price-${categoryName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
	}

	function priceDraftKey(chargeId: string, tier: ChargeTier): string {
		return `${chargeId}::${tier}`;
	}

	function getPriceInputValue(charge: ChargeItem, tier: ChargeTier): string {
		return priceDrafts[priceDraftKey(charge.id, tier)] ?? String(charge.prices[tier] ?? 0);
	}

	function resetPriceDraft(chargeId: string, tier: ChargeTier) {
		delete priceDrafts[priceDraftKey(chargeId, tier)];
	}

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		void loadCharges();
	});

	async function loadCharges() {
		loading = true;
		error = '';
		try {
			const [chargeItems, categoryItems, insuranceItems] = await Promise.all([
				chargesApi.getAll(),
				adminApi.getPatientCategories(),
				insuranceCategoriesApi.listCategories(),
			]);
			priceCategories = sortPatientCategories(categoryItems);
			insuranceCategories = sortInsuranceCategories(insuranceItems);

			// Build per-combo fees from clinic_configs
			const fees: Record<string, number> = {};
			const clinicMap: Record<string, { clinicId: string; walkInType: string }> = {};
			for (const insurance of insuranceItems) {
				for (const patientCat of insurance.patient_categories) {
					const walkInType = `WALKIN_${patientCat.name.toUpperCase().replace(/\s+/g, '_').replace(/-/g, '_')}`;
					// Prefer configs from clinics that explicitly serve this walk-in type
					const configsForType = insurance.clinic_configs.filter(c => c.walk_in_type === walkInType);
					const config = configsForType.find(c => c.clinic_walk_in_types?.includes(walkInType)) || configsForType[0];
					const key = `${insurance.id}::${patientCat.id}`;
					if (config) {
						fees[key] = config.registration_fee;
						clinicMap[key] = { clinicId: config.clinic_id, walkInType };
					}
				}
			}
			registrationFees = fees;
			regFeeClinicMap = clinicMap;
			
			const nextPricingColumns = flattenPricingGroups(buildPricingGroups(chargeItems, categoryItems, insuranceItems));
			charges = chargeItems.map((charge) => mergeChargePrices(charge, nextPricingColumns));
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load charges';
		} finally {
			loading = false;
		}
	}

	function updateChargeInState(updatedCharge: ChargeItem) {
		const hydratedCharge = mergeChargePrices(updatedCharge, pricingColumns);
		const existingCharge = charges.find((charge) => charge.id === updatedCharge.id);

		if (!existingCharge) {
			charges = [...charges, hydratedCharge];
			return;
		}

		charges = charges.map((charge) =>
			charge.id === hydratedCharge.id
				? {
					...charge,
					...hydratedCharge,
					prices: {
						...charge.prices,
						...hydratedCharge.prices
					}
				}
				: charge
		);
	}

	function startMetaEdit(charge: ChargeItem) {
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
			updateChargeInState({
				...charge,
				...updated,
				name: metaDraft.name.trim(),
				item_code: metaDraft.item_code.trim(),
				category: metaDraft.category,
				description: metaDraft.description.trim() || undefined,
				prices: {
					...charge.prices,
					...updated.prices
				}
			});
			cancelMetaEdit();
			toastStore.addToast('Charge details updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update charge details', 'error');
		} finally {
			savingMeta = false;
		}
	}

	async function savePriceEdit(charge: ChargeItem, tier: ChargeTier) {
		const draftKey = priceDraftKey(charge.id, tier);
		const nextPrice = Number((priceDrafts[draftKey] ?? String(charge.prices[tier] ?? 0)).trim());
		if (!Number.isFinite(nextPrice) || nextPrice < 0) {
			toastStore.addToast('Price must be a valid non-negative number', 'error');
			return;
		}

		if (nextPrice === (charge.prices[tier] ?? 0)) {
			resetPriceDraft(charge.id, tier);
			return;
		}

		savingPriceKey = draftKey;
		try {
			const updated = await chargesApi.update(charge.id, {
				prices: { [tier]: nextPrice }
			});
			updateChargeInState({
				...charge,
				...updated,
				prices: {
					...charge.prices,
					...updated.prices,
					[tier]: nextPrice
				}
			});
			resetPriceDraft(charge.id, tier);
			toastStore.addToast('Price updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update price', 'error');
		} finally {
			if (savingPriceKey === draftKey) {
				savingPriceKey = null;
			}
		}
	}

	async function saveRegFee() {
		if (!editingRegFee) return;

		const nextPrice = Number(editingRegFee.value);
		if (!Number.isFinite(nextPrice) || nextPrice < 0) {
			toastStore.addToast('Fee must be a valid non-negative number', 'error');
			return;
		}

		const key = `${editingRegFee.insuranceId}::${editingRegFee.categoryId}`;
		const clinicRef = regFeeClinicMap[key];
		if (!clinicRef) {
			toastStore.addToast('No clinic config found for this combination', 'error');
			return;
		}

		savingRegFee = true;
		try {
			await insuranceCategoriesApi.saveClinicConfigByClinic(
				editingRegFee.insuranceId,
				clinicRef.clinicId,
				{ registration_fee: nextPrice, walk_in_type: clinicRef.walkInType },
				clinicRef.walkInType,
			);
			registrationFees[key] = nextPrice;
			editingRegFee = null;
			toastStore.addToast('Registration fee updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update registration fee', 'error');
		} finally {
			savingRegFee = false;
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
			prices: buildEmptyPrices(pricingColumns)
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

	async function toggleChargeActive(charge: ChargeItem) {
		togglingChargeId = charge.id;
		try {
			const updated = await chargesApi.update(charge.id, { is_active: !charge.is_active });
			updateChargeInState({
				...charge,
				...updated,
				prices: {
					...charge.prices,
					...updated.prices,
				},
			});
			toastStore.addToast(`Charge ${updated.is_active ? 'enabled' : 'disabled'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update charge status', 'error');
		} finally {
			togglingChargeId = null;
		}
	}

</script>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-4 text-sm">{error}</div>
	{:else}
		<div class="mb-4 flex items-center justify-between gap-3">
			<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Charge Master & Rates</p>
			<div class="w-fit">
				<TabBar
					tabs={categoryTabs}
					activeTab={activeCategory}
					variant="jiggle"
					stretch={false}
					ariaLabel="Charge master categories"
					onchange={(id) => activeCategory = id as ChargeCategory}
				/>
			</div>
		</div>

		<!-- {#if activeCategory !== 'REGISTRATION'}
			<div class="mb-3 flex justify-end">
				<button
					onclick={openCreateModal}
					class="px-4 py-2 text-sm font-semibold text-white rounded-full"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
				>
					Add New
				</button>
			</div>
		{/if} -->

		<!-- Registration Fee Table -->
		{#if activeCategory === 'REGISTRATION'}
			<div
				class="overflow-x-auto rounded-2xl"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
			>
				<table class="w-full min-w-max">
					<thead>
						<tr style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);">
							<th class="px-4 py-3 text-left text-xs font-bold text-slate-700 uppercase tracking-wide border-b border-slate-200">Insurance Type</th>
							{#each priceCategories as category}
								<th class="px-4 py-3 text-center text-xs font-bold text-slate-700 uppercase tracking-wide border-b border-slate-200">{category.name}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#if insuranceCategories.length === 0}
							<tr>
								<td colspan={priceCategories.length + 1} class="px-4 py-8 text-center text-slate-500 text-sm">
									No insurance categories configured.
								</td>
							</tr>
						{:else}
							{#each insuranceCategories as insurance, i}
								<tr class:border-t={i > 0} style="border-color: rgba(0,0,0,0.06);">
									<td class="px-4 py-3 font-semibold text-slate-900 text-sm">{insurance.name}</td>
									{#each priceCategories as category}
									{@const isEditingThis = editingRegFee?.insuranceId === insurance.id && editingRegFee?.categoryId === category.id}
									{@const isEligible = insurance.patient_categories?.some(pc => pc.id === category.id)}
								{@const comboKey = `${insurance.id}::${category.id}`}
								{@const hasConfig = comboKey in registrationFees}
								<td class="px-4 py-3 text-center">
									{#if !isEligible || !hasConfig}
											<span class="text-slate-400 text-sm">N/A</span>
										{:else if isEditingThis}
											<div class="flex items-center justify-center gap-1">
												<span class="text-xs font-semibold text-slate-500">₹</span>
												<input
													type="number"
													min="0"
													step="1"
													class="number-field soft-field w-20 bg-white rounded px-2 py-1 text-sm font-semibold text-slate-800 outline-none text-center"
													value={editingRegFee?.value ?? ''}
													oninput={(event) => {
														if (editingRegFee) {
															editingRegFee.value = (event.currentTarget as HTMLInputElement).value;
														}
													}}
													onkeydown={(event) => {
														if (event.key === 'Enter') {
															saveRegFee();
														}
														if (event.key === 'Escape') {
															editingRegFee = null;
														}
													}}
												/>
												<button
													onclick={saveRegFee}
													class="flex h-7 w-7 items-center justify-center rounded-full text-white cursor-pointer"
													style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
													disabled={savingRegFee}
												>
													<Check class="h-3.5 w-3.5" />
												</button>
												<button
													onclick={() => editingRegFee = null}
													class="flex h-7 w-7 items-center justify-center rounded-full text-white cursor-pointer"
													style="background: linear-gradient(to bottom, #94a3b8, #64748b);"
													disabled={savingRegFee}
												>
													<X class="h-3.5 w-3.5" />
												</button>
											</div>
										{:else}
											<button
											onclick={() => editingRegFee = { insuranceId: insurance.id, categoryId: category.id, value: String(registrationFees[`${insurance.id}::${category.id}`] ?? 0) }}
											class="px-4 py-2 text-sm font-semibold text-slate-800 rounded-lg cursor-pointer transition-colors hover:bg-slate-100"
											style="background: linear-gradient(to bottom, rgba(248,250,252,0.96), rgba(241,245,249,0.92)); border: 1px solid rgba(148,163,184,0.18);"
										>
											₹{registrationFees[`${insurance.id}::${category.id}`] ?? 0}
											</button>
										{/if}
									</td>
								{/each}
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		{:else}
		<!-- Pricing Table -->
		<div
			class="overflow-x-auto overflow-y-hidden rounded-2xl"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06); -webkit-overflow-scrolling: touch; overscroll-behavior-x: contain;"
		>
			<div class="min-w-max">
				<!-- Table Header -->
				<div class="sticky top-0 z-20 grid gap-1 border-b border-slate-200/80 px-2 py-2 backdrop-blur-sm" style={`background: linear-gradient(to bottom, rgba(241,245,249,0.96), rgba(226,232,240,0.94)); box-shadow: 0 1px 0 rgba(148,163,184,0.18); ${tableGridStyle}`}>
					<div class="text-[10px] font-bold text-slate-700 uppercase tracking-[0.16em]">Item</div>
					{#each pricingGroups as group (group.id)}
						<div class="px-1 text-center text-[10px] font-bold uppercase tracking-[0.16em] text-slate-700">
							{group.label}
						</div>
					{/each}
				</div>

				<!-- Table Body -->
				{#if filteredCharges.length === 0}
					<div class="px-4 py-8 text-center text-slate-500 text-sm">
						No charges in this category.
					</div>
				{:else}
					{#each filteredCharges as charge, i (charge.id)}
						{@const isEditingMeta = editingMetaId === charge.id}
						<div
							class="grid gap-1 px-2 py-1.5 items-start group"
							class:border-t={i > 0}
							style={`${tableGridStyle}${i > 0 ? ' border-color: rgba(0,0,0,0.06);' : ''}`}
						>
						<div>
							{#if isEditingMeta}
								<div class="space-y-1.5 rounded-lg border border-blue-200/70 bg-blue-50/55 p-2">
									<input
										type="text"
										class="soft-field w-full rounded-md px-2 py-1 text-xs font-semibold text-slate-900"
										style="background: rgba(255,255,255,0.95);"
										bind:value={metaDraft.name}
										placeholder="Title"
									/>
									<div class="grid grid-cols-[minmax(0,1fr)_96px] gap-1.5">
										<input
											type="text"
											class="soft-field w-full rounded-md px-2 py-1 text-[11px] text-slate-600"
											style="background: rgba(255,255,255,0.95);"
											bind:value={metaDraft.item_code}
											placeholder="Code"
										/>
										<select
											class="soft-field w-full rounded-md px-2 py-1 text-[11px] text-slate-600"
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
										class="soft-field w-full rounded-md px-2 py-1 text-[11px] text-slate-600"
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
								<div class="flex items-start gap-1.5">
									<div class="min-w-0 flex-1">
										<p class="font-semibold leading-4 text-slate-900 text-[13px]">{charge.name}</p>
										<div class="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
											<span>{charge.item_code}</span>
										</div>
									</div>
									<div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
										<button onclick={() => startMetaEdit(charge)} class="p-1 text-slate-400 hover:text-blue-500 cursor-pointer">
											<Pencil class="w-3.5 h-3.5" />
										</button>
										<button onclick={() => toggleChargeActive(charge)} class="p-1 cursor-pointer disabled:opacity-60 {charge.is_active ? 'text-slate-400 hover:text-amber-500' : 'text-slate-400 hover:text-emerald-500'}" disabled={togglingChargeId === charge.id}>
											<Power class="w-3.5 h-3.5" />
										</button>
										<!-- Delete charge action hidden until admin disable flow replaces hard delete UI. -->
										<!--
										<button onclick={() => confirmDeleteCharge(charge)} class="p-1 text-slate-400 hover:text-red-500 cursor-pointer">
											<Trash2 class="w-3.5 h-3.5" />
										</button>
										-->
									</div>
								</div>
							{/if}
						</div>
						{#each pricingGroups as group (group.id)}
							<div class="min-w-0">
								<div class="overflow-hidden rounded-lg border border-slate-200/80 bg-white/80">
									{#if group.tiers.length === 0}
										<div class="px-1.5 py-2 text-center text-[9px] font-semibold uppercase tracking-wide text-slate-400">
											No plans
										</div>
									{:else}
										{#each group.tiers as tier, tierIndex (tier.key)}
											{@const inputKey = priceDraftKey(charge.id, tier.key)}
											<div class:border-t={tierIndex > 0} class="grid grid-cols-[minmax(0,1fr)_68px] items-center gap-0.5 px-1 py-0.5" style="border-color: rgba(148,163,184,0.16);">
												<div class="truncate text-[8px] font-semibold uppercase tracking-wide leading-none text-slate-500">
													{tier.insuranceName}
												</div>
												<label class="flex h-6 items-center gap-0.5 rounded border border-slate-200 bg-slate-50/90 px-1" class:ring-1={savingPriceKey === inputKey} class:ring-blue-300={savingPriceKey === inputKey}>
													<span class="text-[8px] font-semibold leading-none text-slate-400">₹</span>
													<input
														type="number"
														min="0"
														step="1"
														class="compact-number-input h-full w-full min-w-0 bg-transparent text-right text-[9px] font-semibold leading-none text-slate-800 outline-none"
														value={getPriceInputValue(charge, tier.key)}
														disabled={savingPriceKey === inputKey}
														oninput={(event) => {
															priceDrafts[inputKey] = (event.currentTarget as HTMLInputElement).value;
														}}
														onblur={() => savePriceEdit(charge, tier.key)}
														onkeydown={(event) => {
															if (event.key === 'Enter') {
																event.preventDefault();
																void savePriceEdit(charge, tier.key);
															}
															if (event.key === 'Escape') {
																event.preventDefault();
																resetPriceDraft(charge.id, tier.key);
															}
														}}
													/>
												</label>
											</div>
										{/each}
									{/if}
								</div>
							</div>
						{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>
		{/if}
	{/if}

{#if chargeModal}
	<AquaModal title={editingCharge ? 'Edit Charge Item' : 'Add New Charge Item'} onclose={() => { chargeModal = false; }}>
		<div class="space-y-3">
			<div>
				<label for="charge-name" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Name *</label>
				<input id="charge-name" type="text" placeholder="e.g., Blood Test - CBC" class="soft-field w-full px-3 py-2.5 text-sm rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.name} />
			</div>
			<div>
				<label for="charge-code" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Item Code *</label>
				<input id="charge-code" type="text" placeholder="e.g., LAB-CBC-001" class="soft-field w-full px-3 py-2.5 text-sm rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.item_code} />
			</div>
			<div>
				<label for="charge-category" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Category</label>
				<select id="charge-category" class="soft-field w-full px-3 py-2.5 text-sm rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.category}>
					<option value="CLINICAL">Clinical</option>
					<option value="LABS">Labs</option>
					<option value="ADMIN">Admin</option>
				</select>
			</div>
			<div>
				<label for="charge-desc" class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Description</label>
				<input id="charge-desc" type="text" placeholder="Optional description" class="soft-field w-full px-3 py-2.5 text-sm rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={chargeData.description} />
			</div>

			<div>
				<p class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">Pricing (₹)</p>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					{#each pricingColumns as tier}
						<div>
							<label for={priceInputId(tier)} class="block text-xs text-slate-500 mb-1">{tier}</label>
							<input
								id={priceInputId(tier)}
								type="number"
								min="0"
								step="1"
								class="number-field soft-field w-full px-3 py-2 text-sm rounded-xl"
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

<style>
	.soft-field {
		border: 1px solid rgba(203, 213, 225, 0.9);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.92),
			0 1px 2px rgba(148, 163, 184, 0.08);
		outline: none;
	}

	.soft-field:focus {
		border-color: rgba(147, 197, 253, 0.95);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.95),
			0 0 0 3px rgba(191, 219, 254, 0.55);
	}

	.compact-number-input {
		appearance: textfield;
		-webkit-appearance: none;
		-moz-appearance: textfield;
		border: 0 !important;
		box-shadow: none !important;
		background: transparent !important;
		border-radius: 0;
	}

	.number-field {
		appearance: textfield;
		-webkit-appearance: none;
		-moz-appearance: textfield;
	}

	.number-field::-webkit-outer-spin-button,
	.number-field::-webkit-inner-spin-button,
	.compact-number-input::-webkit-outer-spin-button,
	.compact-number-input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}
</style>

{#if confirmModal}
	<AquaModal title="Confirm Delete" onclose={() => { confirmModal = false; }}>
		<p class="text-sm text-slate-700 mb-4">{confirmMessage}</p>
		<div class="flex gap-2">
			<button onclick={() => { confirmModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={actionLoading}>Cancel</button>
			<button onclick={() => confirmAction?.()} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #ef4444, #dc2626);" disabled={actionLoading}>{actionLoading ? 'Deleting...' : 'Delete'}</button>
		</div>
	</AquaModal>
{/if}
