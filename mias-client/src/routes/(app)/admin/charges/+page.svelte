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
	import { Pencil, Check, Power, X, ShieldCheck, Landmark, Briefcase, Building2, Wallet, HeartPulse, CircleOff, Maximize2, Minimize2 } from 'lucide-svelte';

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
		insuranceIconKey: InsuranceCategory['icon_key'];
		insuranceBadgeSymbol: string | null;
		insuranceColorPrimary: string;
		insuranceColorSecondary: string;
		patientCategoryId: string | null;
		patientCategoryName: string;
		patientColorPrimary: string;
		patientColorSecondary: string;
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
	let savingRegFee = $state(false);
	let regFeeDrafts = $state<Record<string, string>>({});
	let savingRegFeeKey = $state<string | null>(null);

	const categoryTabs = [
		{ id: 'REGISTRATION', label: 'REGISTRATION' },
		{ id: 'CLINICAL', label: 'CLINICAL' },
		{ id: 'LABS', label: 'LABS' },
		{ id: 'ADMIN', label: 'ADMIN' }
	];
	const insuranceIcons = {
		shield: ShieldCheck,
		landmark: Landmark,
		briefcase: Briefcase,
		building: Building2,
		wallet: Wallet,
		heart: HeartPulse,
		off: CircleOff
	} as const;

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
	let columnOrder = $state<string[]>([]);
	let columnWidths = $state<Record<string, number>>({});
	let itemColumnWidth = $state(180);
	let registrationColumnOrder = $state<string[]>([]);
	let registrationColumnWidths = $state<Record<string, number>>({});
	let registrationItemColumnWidth = $state(180);
	let draggedColumnKey = $state<string | null>(null);
	let dragOverColumnKey = $state<string | null>(null);
	let draggedRegistrationColumnKey = $state<string | null>(null);
	let dragOverRegistrationColumnKey = $state<string | null>(null);
	let resizeState = $state<{ key: string; startX: number; startWidth: number } | null>(null);
	let sheetContainer = $state<HTMLDivElement | null>(null);
	let isSheetFullscreen = $state(false);
	let layoutPrefsReady = $state(false);

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

	function withAlpha(color: string, alpha: number): string {
		const normalized = color.trim();
		if (!/^#[0-9a-fA-F]{6}$/.test(normalized)) {
			return `rgba(37, 99, 235, ${alpha})`;
		}
		const hex = normalized.slice(1);
		const red = Number.parseInt(hex.slice(0, 2), 16);
		const green = Number.parseInt(hex.slice(2, 4), 16);
		const blue = Number.parseInt(hex.slice(4, 6), 16);
		return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
	}

	function compactLabel(value: string): string {
		const parts = value
			.split(/[\s/-]+/)
			.map((part) => part.trim())
			.filter(Boolean);
		if (parts.length >= 2) {
			return parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase();
		}
		return value.slice(0, 3).toUpperCase();
	}

	function showExpandedColumnHeader(key: string): boolean {
		return (columnWidths[key] ?? 72) >= 116;
	}

	function showExpandedRegistrationHeader(key: string): boolean {
		return (registrationColumnWidths[key] ?? 92) >= 132;
	}

	function buildPricingColumns(
		chargeItems: ChargeItem[],
		categoryItems: PatientCategoryConfig[],
		insuranceItems: InsuranceCategory[]
	): PricingTierOption[] {
		const tiers: PricingTierOption[] = [];
		const sortedCategories = sortPatientCategories(categoryItems);
		const categoriesByName = new Map(
			sortedCategories.map((category) => [normalizePricingKey(category.name), category])
		);
		const seenTierKeys = new Set<string>();

		for (const insurance of sortInsuranceCategories(insuranceItems)) {
			for (const patientCategory of sortInsurancePatientCategories(insurance.patient_categories || [])) {
				const matchedCategory = categoriesByName.get(normalizePricingKey(patientCategory.name));
				if (!matchedCategory) {
					continue;
				}

				const tierKey = `${insurance.name} - ${patientCategory.name}`;
				const normalizedTierKey = normalizePricingKey(tierKey);
				if (seenTierKeys.has(normalizedTierKey)) {
					continue;
				}

				tiers.push({
					key: tierKey,
					insuranceId: insurance.id,
					insuranceName: insurance.name,
					insuranceIconKey: insurance.icon_key,
					insuranceBadgeSymbol: insurance.custom_badge_symbol?.trim().toUpperCase() || null,
					insuranceColorPrimary: insurance.color_primary,
					insuranceColorSecondary: insurance.color_secondary,
					patientCategoryId: matchedCategory.id,
					patientCategoryName: patientCategory.name,
					patientColorPrimary: matchedCategory.color_primary,
					patientColorSecondary: matchedCategory.color_secondary
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

				const matchedCategory = sortedCategories.find(
					(category) => normalizedTierKey.endsWith(`- ${normalizePricingKey(category.name)}`)
				);
				if (matchedCategory) {
					tiers.push({
						key: existingTierKey,
						insuranceId: null,
						insuranceName: existingTierKey.replace(new RegExp(`\\s*-\\s*${matchedCategory.name}$`, 'i'), '').trim() || existingTierKey,
						insuranceIconKey: 'off',
						insuranceBadgeSymbol: null,
						insuranceColorPrimary: '#94A3B8',
						insuranceColorSecondary: '#475569',
						patientCategoryId: matchedCategory.id,
						patientCategoryName: matchedCategory.name,
						patientColorPrimary: matchedCategory.color_primary,
						patientColorSecondary: matchedCategory.color_secondary,
						isLegacy: true
					});
				} else {
					tiers.push({
						key: existingTierKey,
						insuranceId: null,
						insuranceName: existingTierKey,
						insuranceIconKey: 'off',
						insuranceBadgeSymbol: null,
						insuranceColorPrimary: '#94A3B8',
						insuranceColorSecondary: '#475569',
						patientCategoryId: null,
						patientCategoryName: 'Other',
						patientColorPrimary: '#94A3B8',
						patientColorSecondary: '#475569',
						isLegacy: true
					});
				}

				seenTierKeys.add(normalizedTierKey);
			}
		}

		return tiers;
	}

	function syncColumnOrder(nextColumns: string[]) {
		if (nextColumns.length === 0) return;
		const existing = columnOrder.filter((key) => nextColumns.includes(key));
		const missing = nextColumns.filter((key) => !existing.includes(key));
		const nextOrder = [...existing, ...missing];
		if (
			nextOrder.length === columnOrder.length &&
			nextOrder.every((key, index) => key === columnOrder[index])
		) {
			return;
		}
		columnOrder = nextOrder;
	}

	function syncColumnWidths(nextColumns: string[]) {
		const nextWidths: Record<string, number> = {};
		for (const key of nextColumns) {
			nextWidths[key] = Math.max(50, columnWidths[key] ?? 67);
		}
		const sameKeys =
			Object.keys(nextWidths).length === Object.keys(columnWidths).length &&
			Object.entries(nextWidths).every(([key, value]) => columnWidths[key] === value);
		if (!sameKeys) {
			columnWidths = nextWidths;
		}
	}

	function syncRegistrationColumnOrder(nextColumns: string[]) {
		if (nextColumns.length === 0) return;
		const existing = registrationColumnOrder.filter((key) => nextColumns.includes(key));
		const missing = nextColumns.filter((key) => !existing.includes(key));
		const nextOrder = [...existing, ...missing];
		if (
			nextOrder.length === registrationColumnOrder.length &&
			nextOrder.every((key, index) => key === registrationColumnOrder[index])
		) {
			return;
		}
		registrationColumnOrder = nextOrder;
	}

	function syncRegistrationColumnWidths(nextColumns: string[]) {
		const nextWidths: Record<string, number> = {};
		for (const key of nextColumns) {
			nextWidths[key] = Math.max(50, registrationColumnWidths[key] ?? 67);
		}
		const sameKeys =
			Object.keys(nextWidths).length === Object.keys(registrationColumnWidths).length &&
			Object.entries(nextWidths).every(([key, value]) => registrationColumnWidths[key] === value);
		if (!sameKeys) {
			registrationColumnWidths = nextWidths;
		}
	}

	const availablePricingTiers = $derived.by(() => buildPricingColumns(charges, priceCategories, insuranceCategories));
	const pricingColumns = $derived.by(() => availablePricingTiers.map((tier) => tier.key));
	const orderedPricingTiers = $derived.by(() => {
		const byKey = new Map(availablePricingTiers.map((tier) => [tier.key, tier]));
		return columnOrder.map((key) => byKey.get(key)).filter((tier): tier is PricingTierOption => Boolean(tier));
	});
	const tableGridStyle = $derived.by(() => {
		const pricingTemplate = orderedPricingTiers.map((tier) => `${Math.max(50, columnWidths[tier.key] ?? 67)}px`).join(' ');
		return `grid-template-columns: ${Math.max(120, itemColumnWidth)}px ${pricingTemplate || '67px'};`;
	});
	const orderedRegistrationCategories = $derived.by(() => {
		const byId = new Map(priceCategories.map((category) => [category.id, category]));
		return registrationColumnOrder
			.map((key) => byId.get(key))
			.filter((category): category is PatientCategoryConfig => Boolean(category));
	});
	const registrationGridStyle = $derived.by(() => {
		const registrationTemplate = orderedRegistrationCategories
			.map((category) => `${Math.max(50, registrationColumnWidths[category.id] ?? 67)}px`)
			.join(' ');
		return `grid-template-columns: ${Math.max(120, registrationItemColumnWidth)}px ${registrationTemplate || '67px'};`;
	});

	function buildEmptyPrices(categoryNames: string[]): Record<string, number | null> {
		return Object.fromEntries(categoryNames.map((categoryName) => [categoryName, null]));
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
		const draft = priceDrafts[priceDraftKey(charge.id, tier)];
		if (draft !== undefined) return draft;
		const price = charge.prices[tier];
		if (price === null || price === undefined) return '';
		return String(price);
	}

	function isPriceSet(charge: ChargeItem, tier: ChargeTier): boolean {
		return charge.prices[tier] !== null && charge.prices[tier] !== undefined;
	}

	function priceCellId(chargeId: string, tier: ChargeTier): string {
		return `charge-cell-${chargeId}-${String(tier).toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
	}

	function regFeeCellId(insuranceId: string, categoryId: string): string {
		return `reg-fee-cell-${insuranceId}-${categoryId}`;
	}

	function resetPriceDraft(chargeId: string, tier: ChargeTier) {
		delete priceDrafts[priceDraftKey(chargeId, tier)];
	}

	function getRegFeeInputValue(comboKey: string): string {
		return regFeeDrafts[comboKey] ?? String(registrationFees[comboKey] ?? 0);
	}

	function resetRegFeeDraft(comboKey: string) {
		delete regFeeDrafts[comboKey];
	}

	function focusPriceCell(rowIndex: number, columnIndex: number) {
		const charge = filteredCharges[rowIndex];
		const tier = orderedPricingTiers[columnIndex];
		if (!charge || !tier) {
			return;
		}
		const target = document.getElementById(priceCellId(charge.id, tier.key)) as HTMLInputElement | null;
		target?.focus();
		target?.select();
	}

	function focusRegFeeCell(rowIndex: number, columnIndex: number): boolean {
		const insurance = insuranceCategories[rowIndex];
		const category = orderedRegistrationCategories[columnIndex];
		if (!insurance || !category) {
			return false;
		}
		const target = document.getElementById(regFeeCellId(insurance.id, category.id)) as HTMLInputElement | null;
		if (!target) {
			return false;
		}
		target.focus();
		target.select();
		return true;
	}

	function handlePriceCellKeydown(event: KeyboardEvent, rowIndex: number, columnIndex: number) {
		if (event.altKey || event.ctrlKey || event.metaKey) {
			return;
		}

		if (event.key === 'ArrowLeft') {
			event.preventDefault();
			focusPriceCell(rowIndex, columnIndex - 1);
			return;
		}

		if (event.key === 'ArrowRight') {
			event.preventDefault();
			focusPriceCell(rowIndex, columnIndex + 1);
			return;
		}

		if (event.key === 'ArrowUp') {
			event.preventDefault();
			focusPriceCell(rowIndex - 1, columnIndex);
			return;
		}

		if (event.key === 'ArrowDown' || event.key === 'Enter') {
			event.preventDefault();
			focusPriceCell(rowIndex + 1, columnIndex);
			return;
		}
	}

	function handleRegFeeCellKeydown(event: KeyboardEvent, rowIndex: number, columnIndex: number) {
		if (event.altKey || event.ctrlKey || event.metaKey) {
			return;
		}

		const attemptMove = (rowStep: number, columnStep: number) => {
			let nextRow = rowIndex + rowStep;
			let nextColumn = columnIndex + columnStep;
			while (
				nextRow >= 0 &&
				nextColumn >= 0 &&
				nextRow < insuranceCategories.length &&
				nextColumn < orderedRegistrationCategories.length
			) {
				if (focusRegFeeCell(nextRow, nextColumn)) {
					return;
				}
				nextRow += rowStep;
				nextColumn += columnStep;
			}
		};

		if (event.key === 'ArrowLeft') {
			event.preventDefault();
			attemptMove(0, -1);
			return;
		}

		if (event.key === 'ArrowRight') {
			event.preventDefault();
			attemptMove(0, 1);
			return;
		}

		if (event.key === 'Tab') {
			event.preventDefault();
			attemptMove(0, event.shiftKey ? -1 : 1);
			return;
		}

		if (event.key === 'ArrowUp') {
			event.preventDefault();
			attemptMove(-1, 0);
			return;
		}

		if (event.key === 'ArrowDown' || event.key === 'Enter') {
			event.preventDefault();
			attemptMove(1, 0);
		}
	}

	function moveColumn(fromKey: string, toKey: string) {
		if (fromKey === toKey) {
			return;
		}
		const fromIndex = columnOrder.indexOf(fromKey);
		const toIndex = columnOrder.indexOf(toKey);
		if (fromIndex === -1 || toIndex === -1) {
			return;
		}
		const nextOrder = [...columnOrder];
		const [moved] = nextOrder.splice(fromIndex, 1);
		nextOrder.splice(toIndex, 0, moved);
		columnOrder = nextOrder;
	}

	function moveRegistrationColumn(fromKey: string, toKey: string) {
		if (fromKey === toKey) {
			return;
		}
		const fromIndex = registrationColumnOrder.indexOf(fromKey);
		const toIndex = registrationColumnOrder.indexOf(toKey);
		if (fromIndex === -1 || toIndex === -1) {
			return;
		}
		const nextOrder = [...registrationColumnOrder];
		const [moved] = nextOrder.splice(fromIndex, 1);
		nextOrder.splice(toIndex, 0, moved);
		registrationColumnOrder = nextOrder;
	}

	function resetColumnDragState() {
		draggedColumnKey = null;
		dragOverColumnKey = null;
	}

	function resetRegistrationColumnDragState() {
		draggedRegistrationColumnKey = null;
		dragOverRegistrationColumnKey = null;
	}

	function handleColumnDragStart(event: DragEvent, key: string) {
		draggedColumnKey = key;
		dragOverColumnKey = key;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.dropEffect = 'move';
			event.dataTransfer.setData('text/plain', key);
		}
	}

	function handleColumnDragOver(event: DragEvent, key: string) {
		event.preventDefault();
		dragOverColumnKey = key;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleColumnDrop(event: DragEvent, key: string) {
		event.preventDefault();
		const fromKey = draggedColumnKey;
		resetColumnDragState();
		if (!fromKey) {
			return;
		}
		moveColumn(fromKey, key);
	}

	function handleRegistrationColumnDragStart(event: DragEvent, key: string) {
		draggedRegistrationColumnKey = key;
		dragOverRegistrationColumnKey = key;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.dropEffect = 'move';
			event.dataTransfer.setData('text/plain', key);
		}
	}

	function handleRegistrationColumnDragOver(event: DragEvent, key: string) {
		event.preventDefault();
		dragOverRegistrationColumnKey = key;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleRegistrationColumnDrop(event: DragEvent, key: string) {
		event.preventDefault();
		const fromKey = draggedRegistrationColumnKey;
		resetRegistrationColumnDragState();
		if (!fromKey) {
			return;
		}
		moveRegistrationColumn(fromKey, key);
	}

	function startColumnResize(event: MouseEvent, key: string, width: number) {
		event.preventDefault();
		event.stopPropagation();
		resizeState = { key, startX: event.clientX, startWidth: width };
	}

	function handleResizeMouseMove(event: MouseEvent) {
		if (!resizeState) {
			return;
		}
		const nextWidth = Math.max(
			resizeState.key === '__item__' || resizeState.key === 'reg::__item__' ? 120 : 50,
			resizeState.startWidth + (event.clientX - resizeState.startX)
		);
		if (resizeState.key === '__item__') {
			itemColumnWidth = nextWidth;
			return;
		}
		if (resizeState.key === 'reg::__item__') {
			registrationItemColumnWidth = nextWidth;
			return;
		}
		if (resizeState.key.startsWith('reg::')) {
			const columnKey = resizeState.key.slice(5);
			registrationColumnWidths = {
				...registrationColumnWidths,
				[columnKey]: nextWidth
			};
			return;
		}
		columnWidths = {
			...columnWidths,
			[resizeState.key]: nextWidth
		};
	}

	function stopColumnResize() {
		resizeState = null;
	}

	async function toggleSheetFullscreen() {
		if (!sheetContainer) {
			return;
		}
		if (document.fullscreenElement === sheetContainer) {
			await document.exitFullscreen();
			return;
		}
		await sheetContainer.requestFullscreen();
	}

	function handleFullscreenChange() {
		isSheetFullscreen = document.fullscreenElement === sheetContainer;
	}

	function loadSheetLayout() {
		try {
			const raw = localStorage.getItem('mias-charge-sheet-layout-v1');
			if (!raw) {
				layoutPrefsReady = true;
				return;
			}
			const parsed = JSON.parse(raw) as {
				pricingOrder?: string[];
				pricingWidths?: Record<string, number>;
				pricingItemWidth?: number;
				registrationOrder?: string[];
				registrationWidths?: Record<string, number>;
				registrationItemWidth?: number;
			};
			columnOrder = Array.isArray(parsed.pricingOrder) ? parsed.pricingOrder : [];
			columnWidths = parsed.pricingWidths ?? {};
			itemColumnWidth = typeof parsed.pricingItemWidth === 'number' ? parsed.pricingItemWidth : 180;
			registrationColumnOrder = Array.isArray(parsed.registrationOrder) ? parsed.registrationOrder : [];
			registrationColumnWidths = parsed.registrationWidths ?? {};
			registrationItemColumnWidth = typeof parsed.registrationItemWidth === 'number' ? parsed.registrationItemWidth : 180;
		} catch {
			columnOrder = [];
			columnWidths = {};
			itemColumnWidth = 180;
			registrationColumnOrder = [];
			registrationColumnWidths = {};
			registrationItemColumnWidth = 180;
		} finally {
			layoutPrefsReady = true;
		}
	}

	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		loadSheetLayout();
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

			const nextPricingColumns = buildPricingColumns(chargeItems, categoryItems, insuranceItems).map((tier) => tier.key);
			syncColumnOrder(nextPricingColumns);
			charges = chargeItems.map((charge) => mergeChargePrices(charge, nextPricingColumns));
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load charges';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		syncColumnOrder(pricingColumns);
		syncColumnWidths(pricingColumns);
	});

	$effect(() => {
		syncRegistrationColumnOrder(priceCategories.map((category) => category.id));
		syncRegistrationColumnWidths(priceCategories.map((category) => category.id));
	});

	$effect(() => {
		if (!layoutPrefsReady) {
			return;
		}
		localStorage.setItem(
			'mias-charge-sheet-layout-v1',
			JSON.stringify({
				pricingOrder: columnOrder,
				pricingWidths: columnWidths,
				pricingItemWidth: itemColumnWidth,
				registrationOrder: registrationColumnOrder,
				registrationWidths: registrationColumnWidths,
				registrationItemWidth: registrationItemColumnWidth
			})
		);
	});

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
		const rawValue = (priceDrafts[draftKey] ?? getPriceInputValue(charge, tier)).trim();
		// Empty input on an unset price — no change needed
		if (rawValue === '' && !isPriceSet(charge, tier)) {
			resetPriceDraft(charge.id, tier);
			return;
		}
		// Empty input on a set price — treat as clearing (set to 0)
		const nextPrice = rawValue === '' ? 0 : Number(rawValue);
		if (!Number.isFinite(nextPrice) || nextPrice < 0) {
			toastStore.addToast('Price must be a valid non-negative number', 'error');
			return;
		}

		const currentPrice = charge.prices[tier];
		if (nextPrice === (currentPrice ?? null) || (currentPrice !== null && nextPrice === currentPrice)) {
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

	async function saveRegFeeEdit(insuranceId: string, categoryId: string) {
		const key = `${insuranceId}::${categoryId}`;
		const nextPrice = Number((regFeeDrafts[key] ?? String(registrationFees[key] ?? 0)).trim());
		if (!Number.isFinite(nextPrice) || nextPrice < 0) {
			toastStore.addToast('Fee must be a valid non-negative number', 'error');
			return;
		}

		if (nextPrice === (registrationFees[key] ?? 0)) {
			resetRegFeeDraft(key);
			return;
		}

		const clinicRef = regFeeClinicMap[key];
		if (!clinicRef) {
			toastStore.addToast('No clinic config found for this combination', 'error');
			return;
		}

		savingRegFee = true;
		savingRegFeeKey = key;
		try {
			await insuranceCategoriesApi.saveClinicConfigByClinic(
				insuranceId,
				clinicRef.clinicId,
				{ registration_fee: nextPrice, walk_in_type: clinicRef.walkInType },
				clinicRef.walkInType,
			);
			registrationFees[key] = nextPrice;
			resetRegFeeDraft(key);
			toastStore.addToast('Registration fee updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update registration fee', 'error');
		} finally {
			savingRegFee = false;
			if (savingRegFeeKey === key) {
				savingRegFeeKey = null;
			}
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
			prices: Object.fromEntries(pricingColumns.map((c) => [c, 0]))
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

<svelte:window onmousemove={handleResizeMouseMove} onmouseup={stopColumnResize} />
<svelte:document onfullscreenchange={handleFullscreenChange} />

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
			<div bind:this={sheetContainer} class={`relative pt-2 ${isSheetFullscreen ? 'h-full w-full bg-white p-3' : ''}`}>
				<button
					type="button"
					class={`absolute z-30 flex h-8 w-8 items-center justify-center border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 ${isSheetFullscreen ? 'right-0 top-0' : '-right-2 -top-2'}`}
					aria-label={isSheetFullscreen ? 'Exit fullscreen sheet view' : 'Open sheet view in fullscreen'}
					title={isSheetFullscreen ? 'Exit fullscreen' : 'Open fullscreen'}
					onclick={() => void toggleSheetFullscreen()}
				>
					{#if isSheetFullscreen}
						<Minimize2 class="h-4 w-4" />
					{:else}
						<Maximize2 class="h-4 w-4" />
					{/if}
				</button>
				<div class="overflow-x-auto overflow-y-hidden border border-slate-300 bg-white rounded-xl" style="-webkit-overflow-scrolling: touch; overscroll-behavior-x: contain; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
					<div class="min-w-max">
						<div class="sticky top-0 z-20 grid items-stretch border-b border-slate-300 bg-slate-100 shadow-[inset_0_-1px_0_rgba(203,213,225,1)]" style={registrationGridStyle}>
						    <div class="relative flex items-center overflow-hidden border-r border-slate-300 px-2 py-1 text-[10pt] font-bold text-slate-700 uppercase tracking-[0.14em]">
								<span class="truncate">Insurance</span>
								<button
									type="button"
									class="column-resizer"
									aria-label="Resize insurance column"
									onmousedown={(event) => startColumnResize(event, 'reg::__item__', registrationItemColumnWidth)}
								></button>
							</div>
							{#each orderedRegistrationCategories as category (category.id)}
								<div
									class={`charge-column-header relative flex min-h-[33px] flex-col items-center justify-center overflow-hidden border-r border-slate-300 px-1 py-1 text-center ${draggedRegistrationColumnKey === category.id ? 'is-dragging' : ''} ${dragOverRegistrationColumnKey === category.id && draggedRegistrationColumnKey !== null && draggedRegistrationColumnKey !== category.id ? 'is-drop-target' : ''}`}
									role="columnheader"
									tabindex="0"
									aria-label={`Reorder registration column ${category.name}`}
									title={category.name}
									draggable="true"
									style={`background: linear-gradient(to bottom, #ffffff, ${withAlpha(category.color_primary, 0.12)});`}
									ondragstart={(event) => handleRegistrationColumnDragStart(event, category.id)}
									ondragover={(event) => handleRegistrationColumnDragOver(event, category.id)}
									ondragenter={(event) => handleRegistrationColumnDragOver(event, category.id)}
									ondrop={(event) => handleRegistrationColumnDrop(event, category.id)}
									ondragend={resetRegistrationColumnDragState}
								>
									{#if showExpandedRegistrationHeader(category.id)}
										<div class="flex flex-col items-center gap-1 px-1">
											<div
												class="mx-auto flex items-center justify-center text-black"
												style={` width: 0px; height: 0px;`}
											>
											<p class="mt-1 text-[10px] font-black uppercase leading-none tracking-[0.12em] text-slate-700">{(category.name)}</p>
											</div>
											<!-- <p class="text-[8px] font-black leading-tight text-slate-700">{category.name}</p> -->
										</div>
									{:else}
										<!-- <div
											class="mx-auto flex items-center justify-center border text-black"
											style={` width: 25px; height: 25px;`}
										>
											<span class="text-[8px] font-black leading-none">{compactLabel(category.name)}</span>
										</div> -->
										<p class="mt-1 text-[10px] font-black uppercase leading-none tracking-[0.12em] text-slate-700">{(category.name)}</p>
									{/if}
									<button
										type="button"
										class="column-resizer"
										aria-label={`Resize ${category.name} registration column`}
										onmousedown={(event) => startColumnResize(event, `reg::${category.id}`, registrationColumnWidths[category.id] ?? 92)}
									></button>
								</div>
							{/each}
						</div>

						{#if insuranceCategories.length === 0}
							<div class="px-4 py-8 text-center text-slate-500 text-sm">No insurance categories configured.</div>
						{:else}
							{#each insuranceCategories as insurance, rowIndex}
								{@const InsuranceIcon = insuranceIcons[insurance.icon_key]}
								<div class="grid items-stretch border-b border-slate-300 group" style={registrationGridStyle}>
									<div class="border-r border-slate-300 bg-white px-2 py-1.5">
										<div class="flex items-center gap-2">
											<div
												class="flex items-center justify-center border text-white"
												style={`background: linear-gradient(135deg, ${insurance.color_primary}, ${insurance.color_secondary}); border-color: ${withAlpha(insurance.color_secondary, 0.35)}; width: 18px; height: 18px;`}
											>
												{#if insurance.custom_badge_symbol}
													<span class="text-[8px] font-black leading-none">{insurance.custom_badge_symbol.slice(0, 2).toUpperCase()}</span>
												{:else}
													<InsuranceIcon class="h-3 w-3" />
												{/if}
											</div>
											<p class="truncate text-[10pt] font-semibold text-slate-900" title={insurance.name}>{insurance.name}</p>
										</div>
									</div>
									{#each orderedRegistrationCategories as category (category.id)}
										{@const isEligible = insurance.patient_categories?.some(pc => pc.id === category.id)}
										{@const comboKey = `${insurance.id}::${category.id}`}
										{@const hasConfig = comboKey in registrationFees}
										<div class="border-r border-slate-300 bg-white">
											{#if !isEligible || !hasConfig}
												<div class="flex h-[33px] items-center justify-center px-1 text-[10pt] text-slate-400">N/A</div>
											{:else}
												<label class="flex h-[33px] items-center gap-1 px-1" class:bg-blue-50={savingRegFeeKey === comboKey}>
													<span class="text-[10pt] font-semibold leading-none text-slate-400">₹</span>
													<input
														id={regFeeCellId(insurance.id, category.id)}
														type="number"
														min="0"
														step="1"
														title={`${insurance.name} • ${category.name}`}
														class="compact-number-input h-full w-full min-w-0 bg-transparent px-0 text-right text-[10pt] font-semibold leading-none text-slate-800 outline-none"
														value={getRegFeeInputValue(comboKey)}
														disabled={savingRegFeeKey === comboKey}
														oninput={(event) => {
															regFeeDrafts[comboKey] = (event.currentTarget as HTMLInputElement).value;
														}}
														onblur={() => saveRegFeeEdit(insurance.id, category.id)}
														onkeydown={(event) => {
															handleRegFeeCellKeydown(event, rowIndex, orderedRegistrationCategories.findIndex((entry) => entry.id === category.id));
															if (event.defaultPrevented) {
																return;
															}
															if (event.key === 'Escape') {
																event.preventDefault();
																resetRegFeeDraft(comboKey);
															}
														}}
													/>
												</label>
											{/if}
										</div>
									{/each}
								</div>
							{/each}
						{/if}
					</div>
				</div>
			</div>
		{:else}
		<!-- Pricing Table -->
		<div bind:this={sheetContainer} class={`relative pt-2 ${isSheetFullscreen ? 'h-full w-full bg-white p-3' : ''}`}>
    		<button
    			type="button"
    			class={`absolute z-30 flex h-8 w-8 items-center justify-center border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-slate-900 ${isSheetFullscreen ? 'right-0 top-0' : '-right-2 -top-2'}`}
    			aria-label={isSheetFullscreen ? 'Exit fullscreen sheet view' : 'Open sheet view in fullscreen'}
    			title={isSheetFullscreen ? 'Exit fullscreen' : 'Open fullscreen'}
    			onclick={() => void toggleSheetFullscreen()}
    		>
    			{#if isSheetFullscreen}
    				<Minimize2 class="h-4 w-4" />
    			{:else}
    				<Maximize2 class="h-4 w-4" />
    			{/if}
    		</button>
    		<div
    			class="overflow-x-auto overflow-y-hidden border border-slate-300 bg-white rounded-xl"
    			style="-webkit-overflow-scrolling: touch; overscroll-behavior-x: contain; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;"
    		>
    			<div class="min-w-max">
    				<!-- Table Header -->
    				<div class="sticky top-0 z-20 grid items-stretch border-b border-slate-300 bg-gradient-to-b from-slate-200 to-slate-100 shadow-sm" style={tableGridStyle}>
    					<div class="relative flex items-center overflow-hidden border-r border-slate-300 px-2 py-1 text-[10pt] font-bold text-slate-700 uppercase tracking-[0.14em]">
    						<span class="truncate">Item</span>
    						<button
    							type="button"
    							class="column-resizer"
    							aria-label="Resize item column"
    							onmousedown={(event) => startColumnResize(event, '__item__', itemColumnWidth)}
    						></button>
    					</div>
    					{#each orderedPricingTiers as tier (tier.key)}
    						{@const InsuranceIcon = insuranceIcons[tier.insuranceIconKey]}
    						<div
    							class={`charge-column-header relative flex min-h-[65px] flex-col items-center justify-center overflow-hidden border-r border-slate-300 px-1 py-1 text-center ${draggedColumnKey === tier.key ? 'is-dragging' : ''} ${dragOverColumnKey === tier.key && draggedColumnKey !== null && draggedColumnKey !== tier.key ? 'is-drop-target' : ''}`}
    							role="columnheader"
    							tabindex="0"
    							aria-label={`Reorder column ${tier.patientCategoryName} ${tier.insuranceName}`}
    							title={`${tier.patientCategoryName} • ${tier.insuranceName}`}
    							draggable="true"
    							style={`background: linear-gradient(to bottom, #ffffff, ${withAlpha(tier.patientColorPrimary, 0.12)});`}
    							ondragstart={(event) => handleColumnDragStart(event, tier.key)}
    							ondragover={(event) => handleColumnDragOver(event, tier.key)}
    							ondragenter={(event) => handleColumnDragOver(event, tier.key)}
    							ondrop={(event) => handleColumnDrop(event, tier.key)}
    							ondragend={resetColumnDragState}
    						>
    							{#if showExpandedColumnHeader(tier.key)}
    								<div class="flex flex-col items-center gap-1 px-1">
       									<div
                                            class="mx-auto flex flex-col items-center justify-center text-black leading-tight"
                                            style={`width: auto; height: auto;`}
                                        >
    										{#if tier.insuranceBadgeSymbol}
    											<!-- <span class="text-[8px] font-black leading-none">{tier.insuranceBadgeSymbol.slice(0, 2)}</span> -->
    										{:else}
    											<InsuranceIcon class="h-3 w-3" />
    										{/if}
    									</div>
    									<p class="text-[11px] font-black leading-tight text-slate-700">{tier.patientCategoryName}</p>
    									<p class="text-[9px] leading-tight text-slate-500">{tier.insuranceName}</p>
    								</div>
    							{:else}
   								<div
                                    class="mx-auto flex flex-col items-center justify-center text-black leading-tight"
                                    style={`width: auto; height: auto;`}
                                >
    									{#if tier.insuranceBadgeSymbol}
    										<!-- <span class="text-[8px] font-black leading-none">{tier.insuranceBadgeSymbol.slice(0, 2)}</span> -->
    										<p class="text-[8px] leading-tight text-slate-500">{tier.insuranceName}</p>
    									{:else}
    										<InsuranceIcon class="h-3 w-3" />
    									{/if}
    									<p class="text-[8px] font-black leading-tight text-slate-700">{tier.patientCategoryName}</p>
    								</div>
    								<!-- <div class="mx-auto mt-1 h-1 w-7" style={`background: linear-gradient(90deg, ${tier.patientColorPrimary}, ${tier.patientColorSecondary});`}></div> -->
    								<!-- <p class="mt-1 text-[7px] font-black uppercase leading-none tracking-[0.12em] text-slate-700">{compactLabel(tier.patientCategoryName)}</p> -->
    							{/if}
    							<button
    								type="button"
    								class="column-resizer"
    								aria-label={`Resize ${tier.patientCategoryName} ${tier.insuranceName} column`}
    								onmousedown={(event) => startColumnResize(event, tier.key, columnWidths[tier.key] ?? 72)}
    							></button>
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
    						<div class="grid items-stretch group border-b border-slate-200 even:bg-slate-50/60 hover:bg-blue-50/40 transition-colors" style={tableGridStyle}>
        						<div class="sticky top-0 z-20 grid items-stretch border-b border-slate-300 bg-gradient-to-b from-slate-200 to-slate-100 shadow-sm" style={tableGridStyle}>
    							{#if isEditingMeta}
    								<div class="space-y-1 border border-blue-200/70 bg-blue-50/55 p-2">
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
    								<div class="flex items-start gap-1.5 px-2 py-1.5">
    									<div class="min-w-0 flex-1">
       										<p class="truncate font-medium leading-4 text-slate-900 text-[11pt]" title={charge.name}>{charge.name}</p>
    										<div class="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-slate-500">
    											<span class="truncate" title={charge.item_code}>{charge.item_code}</span>
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
    						{#each orderedPricingTiers as tier, columnIndex (tier.key)}
    							{@const inputKey = priceDraftKey(charge.id, tier.key)}
    							{@const priceIsSet = isPriceSet(charge, tier.key) || priceDrafts[inputKey] !== undefined}
    							<div class="min-w-0 border-r border-slate-200 shadow-[inset_-1px_0_0_rgba(0,0,0,0.04)]" style="background: {priceIsSet ? '#fff' : '#f8fafc'};">
    								<label class="flex h-[33px] items-center gap-1 px-1" class:bg-blue-50={savingPriceKey === inputKey}>
    									<span class="text-[10pt] font-semibold leading-none" style="color: {priceIsSet ? '#94a3b8' : '#cbd5e1'};">{priceIsSet ? '₹' : ''}</span>
    									<input
    										id={priceCellId(charge.id, tier.key)}
    										type="number"
    										min="0"
    										step="1"
    										placeholder="–"
    										title={`${charge.name} • ${tier.patientCategoryName} • ${tier.insuranceName}`}
    										class="compact-number-input h-full w-full min-w-0 bg-transparent px-0 text-right text-[11pt] font-semibold tracking-tight tabular-nums outline-none placeholder:text-slate-300 placeholder:font-normal"
    										style="color: {priceIsSet ? '#0f172a' : '#94a3b8'};"
    										value={getPriceInputValue(charge, tier.key)}
    										disabled={savingPriceKey === inputKey}
    										oninput={(event) => {
    											priceDrafts[inputKey] = (event.currentTarget as HTMLInputElement).value;
    										}}
    										onblur={() => savePriceEdit(charge, tier.key)}
    										onkeydown={(event) => {
    											handlePriceCellKeydown(event, i, columnIndex);
    											if (event.defaultPrevented) {
    												return;
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
    						</div>
    					{/each}
    				{/if}
    			</div>
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

	.charge-column-header {
		cursor: grab;
		user-select: none;
		border-radius: 0;
		transition:
			transform 0.18s ease,
			background-color 0.18s ease,
			box-shadow 0.18s ease;
	}

	.charge-column-header:hover {
		background: rgba(239, 246, 255, 0.95) !important;
	}

	.charge-column-header.is-dragging {
		cursor: grabbing;
		opacity: 0.65;
		transform: scale(0.98);
	}

	.charge-column-header.is-drop-target {
		background: rgba(219, 234, 254, 0.95) !important;
		box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.35);
	}

	.column-resizer {
		position: absolute;
		top: 0;
		right: -4px;
		width: 8px;
		height: 100%;
		padding: 0;
		border: 0;
		background: transparent;
		cursor: col-resize;
		z-index: 2;
	}

	.column-resizer::after {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		left: 3px;
		width: 1px;
		background: rgba(148, 163, 184, 0.75);
	}

	.column-resizer:hover::after,
	.column-resizer:focus-visible::after {
		background: rgba(37, 99, 235, 0.9);
		box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.18);
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
