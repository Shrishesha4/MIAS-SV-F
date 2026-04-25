<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { browser } from '$app/environment';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import { insuranceCategoriesApi, type InsuranceCategory, type WalkInType } from '$lib/api/insuranceCategories';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { Building2, PencilLine, Plus, Settings, QrCode, Download, Copy, ExternalLink } from 'lucide-svelte';

	const auth = get(authStore);
	const clinicTypeOptions = ['IP', 'OP', 'ER'];

	// ─── QR Modal ──────────────────────────────────────────
	let qrClinic = $state<ClinicInfo | null>(null);
	let showQrModal = $state(false);
	let qrDataUrl = $state('');

	function clinicRegUrl(clinic: ClinicInfo): string {
		if (!browser) return '';
		return `${window.location.origin}/register/clinic/${clinic.id}`;
	}

	async function openQrModal(clinic: ClinicInfo) {
		qrClinic = clinic;
		showQrModal = true;
		qrDataUrl = '';
		const url = clinicRegUrl(clinic);
		try {
			const QRCode = (await import('qrcode')).default;
			qrDataUrl = await QRCode.toDataURL(url, {
				width: 400,
				margin: 2,
				color: { dark: '#0f172a', light: '#ffffff' },
			});
		} catch { qrDataUrl = ''; }
	}

	function downloadQr() {
		if (!qrDataUrl || !qrClinic) return;
		const a = document.createElement('a');
		a.href = qrDataUrl;
		a.download = `${qrClinic.name.replace(/\s+/g, '-')}-registration-qr.png`;
		a.click();
	}

	function copyLink() {
		if (!qrClinic) return;
		navigator.clipboard.writeText(clinicRegUrl(qrClinic));
		toastStore.addToast('Link copied', 'success');
	}


	// Walk-in types - fetched dynamically
	let walkInTypes = $state<WalkInType[]>([]);
	let insuranceCategories = $state<InsuranceCategory[]>([]);
	let creatingSuggestionClinicId = $state<string | null>(null);

	let configModal = $state(false);
	let configClinic: ClinicInfo | null = $state(null);
	let configInsuranceCategoryId = $state('');
	let configContextLabel = $state('');
	let configRegistrationFee = $state(100);
	let configIsEnabled = $state(true);
	let configWalkInType = $state('NO_WALK_IN');
	let savingConfig = $state(false);

	let loading = $state(true);
	let error = $state('');
	let clinics: ClinicInfo[] = $state([]);
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	let clinicModal = $state(false);
	let editingClinic: ClinicInfo | null = $state(null);
	let clinicData = $state({
		name: '',
		block: '',
		clinic_type: 'OP',
		access_mode: 'WALK_IN' as ClinicInfo['access_mode'],
		walk_in_type: 'NO_WALK_IN',
		department: '',
		location: '',
		is_active: true
	});
	let savingClinic = $state(false);
	let selectedWalkInTypes = $state<string[]>([]);

	// When a ghost card triggers clinic creation, remember which insurance mapping to auto-create.
	let pendingInsuranceConfig = $state<{
		insuranceCategoryId: string;
		insuranceCategoryName: string;
		patientTypeName: string;
		walkInType: string;
	} | null>(null);

	type MissingConfigCard = {
		id: string;
		clinic: ClinicInfo | null;
		insuranceCategoryId: string;
		insuranceCategoryName: string;
		patientTypeName: string;
		walkInType: string;
	};

	function patientTypeToWalkInType(patientTypeName: string): string {
		return `WALKIN_${patientTypeName.toUpperCase().replace(/\s+/g, '_').replace(/-/g, '_')}`;
	}

	function walkInTypeToLabel(walkInType: string): string {
		if (walkInType === 'NO_WALK_IN') return 'No Walk In';
		if (walkInType.startsWith('WALKIN_')) {
			return `Walkin ${walkInType.replace('WALKIN_', '').replace(/_/g, ' ')}`;
		}
		return walkInType;
	}

	const clinicFormWalkInTypes = $derived.by<WalkInType[]>(() => {
		if (!clinicData.walk_in_type) return walkInTypes;
		if (walkInTypes.some((item) => item.value === clinicData.walk_in_type)) {
			return walkInTypes;
		}
		return [
			{ value: clinicData.walk_in_type, label: walkInTypeToLabel(clinicData.walk_in_type) },
			...walkInTypes,
		];
	});

	const clinicSelectableWalkInTypes = $derived.by(() => clinicFormWalkInTypes.filter((item) => item.value !== 'NO_WALK_IN'));
	const clinicSupportsWalkInTypes = $derived(clinicData.clinic_type !== 'IP');

	const missingConfigCards = $derived.by<MissingConfigCard[]>(() => {
		if (insuranceCategories.length === 0) return [];

		const activeClinics = clinics.filter((clinic) => clinic.is_active);
		if (activeClinics.length === 0) {
			const noClinicMissing: MissingConfigCard[] = [];
			for (const category of insuranceCategories) {
				for (const patientType of category.patient_categories) {
					const walkInType = patientTypeToWalkInType(patientType.name);
					noClinicMissing.push({
						id: `${category.id}::NO_CLINIC::${walkInType}`,
						clinic: null,
						insuranceCategoryId: category.id,
						insuranceCategoryName: category.name,
						patientTypeName: patientType.name,
						walkInType,
					});
				}
			}
			return noClinicMissing;
		}

		const existingConfigKeys = new Set<string>();
		for (const category of insuranceCategories) {
			for (const config of category.clinic_configs) {
				existingConfigKeys.add(`${category.id}::${config.clinic_id}::${config.walk_in_type}`);
			}
		}

		const missing: MissingConfigCard[] = [];
		for (const category of insuranceCategories) {
			for (const patientType of category.patient_categories) {
				const walkInType = patientTypeToWalkInType(patientType.name);
				const matchedClinic = activeClinics.find((c) =>
					c.walk_in_type === walkInType || (c.walk_in_types?.includes(walkInType) ?? false)
				) ?? null;

				const key = matchedClinic
					? `${category.id}::${matchedClinic.id}::${walkInType}`
					: `${category.id}::NO_CLINIC::${walkInType}`;

				// Skip if a config already exists for this combo.
				if (matchedClinic && existingConfigKeys.has(key)) continue;

				missing.push({
					id: key,
					clinic: matchedClinic,
					insuranceCategoryId: category.id,
					insuranceCategoryName: category.name,
					patientTypeName: patientType.name,
					walkInType,
				});
			}
		}

		return missing;
	});

	const missingClinicCount = $derived.by(() => missingConfigCards.length);

	function clinicAccessModeLabel(clinicType: string, accessMode: ClinicInfo['access_mode']) {
		if ((clinicType || '').toUpperCase() === 'IP') return 'No Walk-In Clinic';
		if (accessMode === 'APPOINTMENT_ONLY') return 'Appointment Only';
		return 'Walk-In Clinic';
	}

	async function loadWalkInTypes() {
		try {
			walkInTypes = await insuranceCategoriesApi.getWalkInTypes();
		} catch (e) {
			console.error('Failed to load walk-in types:', e);
		}
	}

	async function loadInsuranceCategories() {
		try {
			insuranceCategories = await insuranceCategoriesApi.listCategories();
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to load insurance categories', 'error');
		}
	}

	type ClinicConfigEntry = { insuranceCategoryId: string; insuranceCategoryName: string; patientTypeName: string; walkInType: string; };

	// Map clinic_id → list of insurance configs that reference it.
	const clinicConfigMap = $derived.by<Record<string, ClinicConfigEntry[]>>(() => {
		const map: Record<string, ClinicConfigEntry[]> = {};
		for (const category of insuranceCategories) {
			for (const config of category.clinic_configs) {
				if (!map[config.clinic_id]) map[config.clinic_id] = [];
				const patientTypeName = config.walk_in_type.startsWith('WALKIN_')
					? config.walk_in_type.slice(7).replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c: string) => c.toUpperCase())
					: config.walk_in_type;
				map[config.clinic_id].push({
					insuranceCategoryId: category.id,
					insuranceCategoryName: category.name,
					patientTypeName,
					walkInType: config.walk_in_type,
				});
			}
		}
		return map;
	});

	let configPickerModal = $state(false);
	let configPickerClinic: ClinicInfo | null = $state(null);
	let configPickerEntries = $state<ClinicConfigEntry[]>([]);

	function openClinicConfigPicker(clinic: ClinicInfo) {
		const entries = clinicConfigMap[clinic.id] ?? [];
		if (entries.length === 0) {
			toastStore.addToast('No insurance configs found for this clinic', 'error');
			return;
		}
		if (entries.length === 1) {
			const e = entries[0];
			openConfigEditor(clinic, e.insuranceCategoryId, e.walkInType, `${e.insuranceCategoryName} • ${e.patientTypeName}`);
			return;
		}
		configPickerClinic = clinic;
		configPickerEntries = entries;
		configPickerModal = true;
	}

	const clinicCards = $derived.by(() =>
		clinics.map((clinic) => ({
			clinic,
			description: [clinic.location, clinic.department, clinic.block].filter(Boolean).join(' • ') || 'Clinic service',
			accessModeLabel: clinicAccessModeLabel(clinic.clinic_type, clinic.access_mode)
		}))
	);

	function upsertClinic(updatedClinic: ClinicInfo) {
		const clinicIndex = clinics.findIndex((clinic) => clinic.id === updatedClinic.id);

		if (clinicIndex === -1) {
			clinics = [updatedClinic, ...clinics];
			return;
		}

		clinics = clinics.map((clinic) => (clinic.id === updatedClinic.id ? { ...clinic, ...updatedClinic } : clinic));
	}

	function removeClinic(clinicId: string) {
		clinics = clinics.filter((clinic) => clinic.id !== clinicId);
	}

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}

		loadClinics();
		loadWalkInTypes();
		loadInsuranceCategories();
	});

	async function loadClinics() {
		loading = true;
		error = '';

		try {
			clinics = await clinicsApi.listClinics();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load clinics';
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		editingClinic = null;
		pendingInsuranceConfig = null;
		clinicData = {
			name: '',
			block: '',
			clinic_type: 'OP',
			access_mode: 'WALK_IN',
			walk_in_type: 'NO_WALK_IN',
			department: '',
			location: '',
			is_active: true
		};
		selectedWalkInTypes = [];
		clinicModal = true;
	}

	async function openEditModal(clinic: ClinicInfo) {
		editingClinic = clinic;
		clinicData = {
			name: clinic.name,
			block: clinic.block || '',
			clinic_type: clinicTypeOptions.includes(clinic.clinic_type) ? clinic.clinic_type : 'OP',
			access_mode: clinic.access_mode || 'WALK_IN',
			walk_in_type: (clinic as any).walk_in_type || 'NO_WALK_IN',
			department: clinic.department || '',
			location: clinic.location || '',
			is_active: clinic.is_active ?? true
		};
		selectedWalkInTypes = clinic.walk_in_types?.length
			? [...clinic.walk_in_types]
			: clinic.walk_in_type && clinic.walk_in_type !== 'NO_WALK_IN'
				? [clinic.walk_in_type]
				: [];
		clinicModal = true;
	}

	function handleClinicTypeChange(nextType: string) {
		clinicData.clinic_type = nextType;
		if (nextType === 'IP') {
			selectedWalkInTypes = [];
			clinicData.walk_in_type = 'NO_WALK_IN';
			return;
		}

		if (selectedWalkInTypes.length === 0 && clinicData.walk_in_type && clinicData.walk_in_type !== 'NO_WALK_IN') {
			selectedWalkInTypes = [clinicData.walk_in_type];
		}
	}

	function toggleWalkInType(value: string, checked: boolean) {
		if (checked) {
			selectedWalkInTypes = selectedWalkInTypes.includes(value) ? selectedWalkInTypes : [...selectedWalkInTypes, value];
			return;
		}

		selectedWalkInTypes = selectedWalkInTypes.filter((item) => item !== value);
	}

	async function saveClinic() {
		if (!clinicData.name.trim()) {
			toastStore.addToast('Clinic name is required', 'error');
			return;
		}

		savingClinic = true;
		try {
			const usesMultiWalkInTypes = clinicData.clinic_type === 'ER' || clinicData.clinic_type === 'OP';
			const normalizedWalkInTypes = usesMultiWalkInTypes ? selectedWalkInTypes.filter(Boolean) : [];
			const payload = {
				name: clinicData.name.trim(),
				block: clinicData.block.trim() || undefined,
				clinic_type: clinicData.clinic_type,
				access_mode: clinicData.access_mode,
				walk_in_type: clinicData.clinic_type === 'IP'
					? 'NO_WALK_IN'
					: usesMultiWalkInTypes
						? (normalizedWalkInTypes[0] || 'NO_WALK_IN')
						: clinicData.walk_in_type,
				walk_in_types: clinicData.clinic_type === 'IP'
					? []
					: usesMultiWalkInTypes
						? normalizedWalkInTypes
						: undefined,
				department: clinicData.department.trim() || undefined,
				location: clinicData.location.trim() || undefined,
				is_active: clinicData.is_active
			};
			let savedClinic: ClinicInfo;

			if (editingClinic) {
				savedClinic = await clinicsApi.updateClinic(editingClinic.id, payload);
				upsertClinic(savedClinic);
				toastStore.addToast('Clinic updated successfully', 'success');
			} else {
				savedClinic = await clinicsApi.createClinic(payload);
				upsertClinic(savedClinic);

				// If this clinic was created from a ghost card, auto-create the insurance config.
				if (pendingInsuranceConfig) {
					const pending = pendingInsuranceConfig;
					pendingInsuranceConfig = null;
					try {
						await insuranceCategoriesApi.saveClinicConfigByClinic(
							pending.insuranceCategoryId,
							savedClinic.id,
							{ walk_in_type: pending.walkInType, registration_fee: 100, is_enabled: true },
							pending.walkInType,
						);
						await loadInsuranceCategories();
						toastStore.addToast(
							`Clinic created and linked to ${pending.insuranceCategoryName} • ${pending.patientTypeName}`,
							'success',
						);
						// Open config editor so the admin can adjust fee/enabled.
						await openConfigEditor(
							savedClinic,
							pending.insuranceCategoryId,
							pending.walkInType,
							`${pending.insuranceCategoryName} • ${pending.patientTypeName}`,
						);
					} catch (configErr: any) {
						toastStore.addToast(
							(configErr as any)?.response?.data?.detail || 'Clinic created but failed to link insurance config',
							'error',
						);
					}
				} else {
					toastStore.addToast('Clinic created successfully', 'success');
				}
			}

			clinicModal = false;
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save clinic', 'error');
		} finally {
			savingClinic = false;
		}
	}

	async function deleteClinic(clinic: ClinicInfo) {
		confirmMessage = `Permanently delete "${clinic.name}"? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await clinicsApi.deleteClinic(clinic.id);
				removeClinic(clinic.id);
				toastStore.addToast('Clinic deleted successfully', 'success');
			} catch (e: any) {
				error = e.response?.data?.detail || 'Delete failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function runConfirmAction() {
		if (!confirmAction) {
			return;
		}

		await confirmAction();
	}

	async function toggleActive(clinic: ClinicInfo) {
		try {
			const updatedClinic = await clinicsApi.updateClinic(clinic.id, { is_active: !clinic.is_active });
			upsertClinic(updatedClinic);
			toastStore.addToast(`Clinic ${clinic.is_active ? 'deactivated' : 'activated'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Action failed', 'error');
		}
	}

	async function openConfigEditor(clinic: ClinicInfo, insuranceCategoryId: string, walkInType: string, contextLabel: string) {
		try {
			const config = await insuranceCategoriesApi.getClinicConfigByClinic(insuranceCategoryId, clinic.id, walkInType);
			configClinic = clinic;
			configInsuranceCategoryId = insuranceCategoryId;
			configContextLabel = contextLabel;
			configRegistrationFee = config.registration_fee;
			configIsEnabled = config.is_enabled;
			configWalkInType = walkInType || config.walk_in_type;
			configModal = true;
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to load clinic configuration', 'error');
		}
	}

	async function createSuggestionAndEdit(card: MissingConfigCard) {
		if (card.clinic) {
			// Clinic already exists — just create the missing insurance config and open the editor.
			creatingSuggestionClinicId = card.clinic.id;
			try {
				await insuranceCategoriesApi.saveClinicConfigByClinic(
					card.insuranceCategoryId,
					card.clinic.id,
					{ walk_in_type: card.walkInType, registration_fee: 100, is_enabled: true },
					card.walkInType,
				);
				await loadInsuranceCategories();
				await openConfigEditor(
					card.clinic,
					card.insuranceCategoryId,
					card.walkInType,
					`${card.insuranceCategoryName} • ${card.patientTypeName}`,
				);
			} catch (e: any) {
				toastStore.addToast(e?.response?.data?.detail || 'Failed to create config', 'error');
			} finally {
				creatingSuggestionClinicId = null;
			}
			return;
		}

		// No clinic yet — open create modal so admin can make a new one.
		pendingInsuranceConfig = {
			insuranceCategoryId: card.insuranceCategoryId,
			insuranceCategoryName: card.insuranceCategoryName,
			patientTypeName: card.patientTypeName,
			walkInType: card.walkInType,
		};
		editingClinic = null;
		clinicData = {
			name: '',
			block: '',
			clinic_type: 'OP',
			access_mode: 'WALK_IN',
			walk_in_type: card.walkInType,
			department: '',
			location: '',
			is_active: true
		};
		selectedWalkInTypes = [card.walkInType];
		clinicModal = true;
	}

	async function saveConfigEditor() {
		if (!configClinic || !configInsuranceCategoryId) return;
		savingConfig = true;
		try {
			await insuranceCategoriesApi.saveClinicConfigByClinic(configInsuranceCategoryId, configClinic.id, {
				walk_in_type: configWalkInType,
				registration_fee: configRegistrationFee,
				is_enabled: configIsEnabled,
			}, configWalkInType);
			await loadInsuranceCategories();
			configModal = false;
			configClinic = null;
			configInsuranceCategoryId = '';
			configContextLabel = '';
			toastStore.addToast('Clinic configuration updated', 'success');
		} catch (e: any) {
			toastStore.addToast(e?.response?.data?.detail || 'Failed to update clinic configuration', 'error');
		} finally {
			savingConfig = false;
		}
	}
</script>

<div class="space-y-4 lg:space-y-5">

	<div class="flex items-center justify-between gap-3">
		<div>
			<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">Hospital Clinics</h2>
			<p class="mt-1 text-xs text-slate-500 lg:hidden">{clinics.length} clinics configured</p>
		</div>
		<button
			onclick={openCreateModal}
			class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
		>
			<Plus class="h-4 w-4" />
			<span>Add New</span>
		</button>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="h-8 w-8 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600"></div>
		</div>
	{:else if error}
		<div class="rounded-[18px] border px-6 py-10 text-center" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
			<p class="text-sm font-semibold text-rose-500">{error}</p>
		</div>
	{:else}
		<div class="clinics-table grid grid-cols-1 gap-3 lg:gap-0 lg:rounded-[18px] lg:overflow-hidden lg:border lg:border-slate-200/70 lg:divide-y lg:divide-slate-100/80">
			<!-- Desktop table header -->
			<div class="hidden lg:grid lg:items-center lg:px-5 lg:py-2.5 lg:[grid-template-columns:2rem_1fr_12rem_auto] lg:gap-x-5"
				 style="background: linear-gradient(to bottom, rgba(248,250,253,0.98), rgba(241,245,250,0.96));">
				<div></div>
				<span class="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Clinic</span>
				<span class="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Location</span>
				<span class="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 text-right">Actions</span>
			</div>

			{#each clinicCards as item (item.clinic.id)}
				<div
					class="clinic-item min-h-[92px] rounded-[18px] border px-4 py-4 transition-transform hover:-translate-y-[1px] lg:px-5"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);"
				>
					<div class="flex items-start gap-3 lg:grid lg:items-center lg:[grid-template-columns:2rem_1fr_12rem_auto] lg:gap-x-5">
						<div
							class="flex h-12 w-12 lg:h-8 lg:w-8 shrink-0 items-center justify-center rounded-full"
							style="background: linear-gradient(to bottom, #3c8af4, #1667d8); box-shadow: 0 4px 10px rgba(20,95,210,0.24), inset 0 1px 0 rgba(255,255,255,0.3);"
						>
							<Building2 class="h-5 w-5 lg:h-4 lg:w-4 text-white" />
						</div>

						<div class="min-w-0 flex-1 lg:flex-none">
							<h3 class="truncate text-[15px] font-bold text-slate-900">{item.clinic.name}</h3>
							<div class="mt-1 flex items-center gap-2 flex-wrap">
								<span class="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600">{item.clinic.clinic_type}</span>
								<span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600">{item.accessModeLabel}</span>
								{#if item.clinic.clinic_type !== 'IP' && item.clinic.walk_in_types?.length}
									{#each item.clinic.walk_in_types as wt}
										<span class="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-semibold text-orange-600">{walkInTypeToLabel(wt)}</span>
									{/each}
								{/if}
								{#if !item.clinic.is_active}
									<span class="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600">Inactive</span>
								{/if}
							</div>
							<!-- Description below badges on mobile only -->
							<p class="mt-1 truncate text-xs text-slate-500 lg:hidden">{item.description}</p>
						</div>

						<!-- Description column — desktop only -->
						<p class="hidden lg:block truncate text-xs text-slate-500">{item.description}</p>

						<div class="flex shrink-0 items-center gap-2 lg:justify-end">
							<button
								type="button"
								class="relative flex h-6 w-11 items-center rounded-full p-[2px] cursor-pointer transition-colors"
								style={item.clinic.is_active
									? 'background: linear-gradient(to bottom, #34d399, #10b981); box-shadow: inset 0 1px 0 rgba(255,255,255,0.32);'
									: 'background: linear-gradient(to bottom, #d7dee8, #bcc7d5); box-shadow: inset 0 1px 0 rgba(255,255,255,0.62);'}
								title={item.clinic.is_active ? 'Deactivate clinic' : 'Activate clinic'}
								onclick={() => toggleActive(item.clinic)}
							>
								<span
									class="h-5 w-5 rounded-full bg-white shadow-sm transition-transform"
									style={item.clinic.is_active ? 'transform: translateX(20px);' : 'transform: translateX(0);'}
								></span>
							</button>
							{#if (clinicConfigMap[item.clinic.id]?.length ?? 0) > 0}
							<button
								type="button"
								class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer hover:bg-blue-50"
								title="Edit insurance config"
								onclick={() => openClinicConfigPicker(item.clinic)}
							>
								<Settings class="h-4 w-4 text-blue-400" />
							</button>
							{/if}
							<button
								type="button"
								class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer hover:bg-emerald-50"
								title="Registration QR code"
								onclick={() => openQrModal(item.clinic)}
							>
								<QrCode class="h-4 w-4 text-emerald-500" />
							</button>
							<button
								type="button"
								class="flex h-8 w-8 items-center justify-center rounded-full cursor-pointer hover:bg-slate-100"
								title="Edit clinic"
								onclick={() => openEditModal(item.clinic)}
							>
								<PencilLine class="h-4 w-4 text-slate-400" />
							</button>
						</div>
					</div>
				</div>
			{/each}

			{#each missingConfigCards as missing (missing.id)}
				<div
					class="clinic-item missing-item min-h-[92px] rounded-[18px] border px-4 py-4 lg:px-5"
					style="opacity: 0.55; border-style: dashed; border-width: 1.5px; border-color: rgba(59,130,246,0.45); background: linear-gradient(to bottom, rgba(248,251,255,0.98), rgba(240,246,255,0.95)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.94);"
				>
					<div class="flex items-start gap-3 lg:grid lg:items-center lg:[grid-template-columns:2rem_1fr_12rem_auto] lg:gap-x-5">
						<div
							class="flex h-12 w-12 lg:h-8 lg:w-8 shrink-0 items-center justify-center rounded-full"
							style="background: linear-gradient(to bottom, #93c5fd, #60a5fa);"
						>
							<Building2 class="h-5 w-5 lg:h-4 lg:w-4 text-white" />
						</div>
						<div class="min-w-0 flex-1 lg:flex-none">
							<h3 class="truncate text-[15px] font-bold text-slate-900">{missing.clinic?.name || 'No clinic created yet'}</h3>
							<div class="mt-1 flex items-center gap-2 flex-wrap">
								<span class="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-blue-700">Missing Mapping</span>
								<span class="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-600">{missing.insuranceCategoryName}</span>
								<span class="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-600">{missing.patientTypeName}</span>
							</div>
							<p class="mt-1 truncate text-xs text-slate-500 lg:hidden">{missing.clinic ? ([missing.clinic.location, missing.clinic.department, missing.clinic.block].filter(Boolean).join(' • ') || 'Clinic service') : 'Create a clinic first, then map this insurance + patient type.'}</p>
							<!-- Action button — mobile only -->
							<button
								type="button"
								onclick={() => createSuggestionAndEdit(missing)}
								disabled={creatingSuggestionClinicId === missing.id}
								class="mt-2 inline-flex lg:hidden items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold text-blue-700 cursor-pointer disabled:opacity-60"
								style="background: rgba(219,234,254,0.9);"
							>
								<Plus class="h-3.5 w-3.5" />
								{missing.clinic
									? (creatingSuggestionClinicId === missing.id ? 'Adding...' : 'Add for this type')
									: 'Create Clinic'}
							</button>
						</div>

						<!-- Location column — desktop only -->
						<p class="hidden lg:block truncate text-xs text-slate-500">{missing.clinic ? ([missing.clinic.location, missing.clinic.department, missing.clinic.block].filter(Boolean).join(' • ') || 'Clinic service') : 'Create a clinic first.'}</p>

						<!-- Action column — desktop only -->
						<div class="hidden lg:flex items-center justify-end">
							<button
								type="button"
								onclick={() => createSuggestionAndEdit(missing)}
								disabled={creatingSuggestionClinicId === missing.id}
								class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold text-blue-700 cursor-pointer disabled:opacity-60"
								style="background: rgba(219,234,254,0.9);"
							>
								<Plus class="h-3.5 w-3.5" />
								{missing.clinic
									? (creatingSuggestionClinicId === missing.id ? 'Adding...' : 'Add for this type')
									: 'Create Clinic'}
							</button>
						</div>
					</div>
				</div>
			{/each}

			{#if clinicCards.length === 0 && missingConfigCards.length === 0}
				<div class="rounded-[18px] border px-6 py-12 text-center" style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(249,251,253,0.96)); border-color: rgba(158,173,193,0.26); box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);">
					<Building2 class="mx-auto mb-3 h-12 w-12 text-blue-300" />
					<p class="text-sm font-semibold text-slate-500">No clinics configured yet</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

{#if clinicModal}
	<AquaModal title={editingClinic ? 'Edit Clinic' : 'Create New Clinic'} onclose={() => { clinicModal = false; pendingInsuranceConfig = null; }}>
		<div class="space-y-4">
			<div>
				<label for="clinic-name" class="mb-1 block text-sm font-medium text-gray-700">Clinic Name *</label>
				<input
					id="clinic-name"
					type="text"
					bind:value={clinicData.name}
					placeholder="e.g. Saveetha General Clinic"
					class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
				/>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div>
					<label for="clinic-block" class="mb-1 block text-sm font-medium text-gray-700">Block</label>
					<input
						id="clinic-block"
						type="text"
						bind:value={clinicData.block}
						placeholder="e.g. Block A"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>

				<div>
					<label for="clinic-type" class="mb-1 block text-sm font-medium text-gray-700">Type</label>
					<select
						id="clinic-type"
						bind:value={clinicData.clinic_type}
						onchange={(event) => handleClinicTypeChange((event.currentTarget as HTMLSelectElement).value)}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					>
						{#each clinicTypeOptions as clinicType}
							<option value={clinicType}>{clinicType}</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div>
					<label for="clinic-department" class="mb-1 block text-sm font-medium text-gray-700">Department</label>
					<input
						id="clinic-department"
						type="text"
						bind:value={clinicData.department}
						placeholder="e.g. General Medicine"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>

				<div>
					<label for="clinic-location" class="mb-1 block text-sm font-medium text-gray-700">Location</label>
					<input
						id="clinic-location"
						type="text"
						bind:value={clinicData.location}
						placeholder="e.g. Ground Floor, Wing A"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
					/>
				</div>
			</div>

			{#if clinicSupportsWalkInTypes}
				<div class="border-t border-gray-200 pt-4 mt-2">
					<p class="block text-sm font-medium text-gray-700 mb-2">Walk-in Types <span class="text-xs text-gray-500">(select one or more)</span></p>
					<div class="space-y-2 rounded-lg border border-gray-200 p-3 max-h-48 overflow-y-auto">
						{#each clinicSelectableWalkInTypes as type}
							<label class="flex items-center gap-2.5 cursor-pointer">
								<input
									type="checkbox"
									class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
									checked={selectedWalkInTypes.includes(type.value)}
									onchange={(event) => toggleWalkInType(type.value, (event.target as HTMLInputElement).checked)}
								/>
								<span class="text-sm text-gray-700">{type.label}</span>
							</label>
						{/each}
						{#if clinicSelectableWalkInTypes.length === 0}
							<p class="text-xs text-gray-400 italic">No walk-in types configured. Add patient categories first.</p>
						{/if}
					</div>
					{#if selectedWalkInTypes.length > 0}
						<p class="mt-1.5 text-xs text-blue-600 font-medium">{selectedWalkInTypes.length} type{selectedWalkInTypes.length !== 1 ? 's' : ''} selected</p>
					{:else}
						<p class="mt-1 text-xs text-amber-500">No types selected</p>
					{/if}
				</div>
			{/if}

			<label class="flex items-center gap-2 text-sm text-gray-700 mt-4">
				<input
					type="checkbox"
					bind:checked={clinicData.is_active}
					class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
				/>
				<span>Active</span>
			</label>

			<div class="flex gap-3 pt-2">
				<button
					type="button"
					onclick={() => { clinicModal = false; pendingInsuranceConfig = null; }}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
					disabled={savingClinic}
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={saveClinic}
					disabled={savingClinic}
					class="flex-1 rounded-lg px-4 py-2 font-medium text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				>
					{savingClinic ? 'Saving...' : editingClinic ? 'Update' : 'Create'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if configModal && configClinic}
	<AquaModal title={`Edit Config • ${configClinic.name}`} onclose={() => { configModal = false; configClinic = null; configInsuranceCategoryId = ''; configContextLabel = ''; configWalkInType = 'NO_WALK_IN'; }}>
		<div class="space-y-4">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Mapping Context</p>
				<p class="mt-1 text-sm font-medium text-slate-700">{configContextLabel}</p>
			</div>
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Walk-in Type</p>
				<p class="mt-1 text-sm font-medium text-slate-700">{configWalkInType}</p>
			</div>

			<div>
				<label for="clinic-config-registration-fee" class="mb-1 block text-sm font-medium text-gray-700">Registration Fee</label>
				<input
					id="clinic-config-registration-fee"
					type="number"
					min="0"
					step="1"
					bind:value={configRegistrationFee}
					class="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
				/>
			</div>

			<label class="flex items-center gap-2 text-sm text-gray-700">
				<input type="checkbox" bind:checked={configIsEnabled} class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
				<span>Enabled for this insurance + patient type</span>
			</label>

			<div class="flex gap-3 pt-2">
				<button
					type="button"
					onclick={() => { configModal = false; configClinic = null; configInsuranceCategoryId = ''; configContextLabel = ''; configWalkInType = 'NO_WALK_IN'; }}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
					disabled={savingConfig}
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={saveConfigEditor}
					disabled={savingConfig}
					class="flex-1 rounded-lg px-4 py-2 font-medium text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				>
					{savingConfig ? 'Saving...' : 'Save Config'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if configPickerModal && configPickerClinic}
	<AquaModal title={`Select Config — ${configPickerClinic.name}`} onclose={() => { configPickerModal = false; configPickerClinic = null; configPickerEntries = []; }}>
		<div class="space-y-3">
			<p class="text-sm text-slate-500">This clinic has multiple insurance configs. Select one to edit:</p>
			{#each configPickerEntries as entry}
				<button
					type="button"
					class="w-full rounded-xl border px-4 py-3 text-left hover:bg-blue-50 cursor-pointer transition-colors"
					style="border-color: rgba(158,173,193,0.3);"
					onclick={() => {
						configPickerModal = false;
						openConfigEditor(configPickerClinic!, entry.insuranceCategoryId, entry.walkInType, `${entry.insuranceCategoryName} • ${entry.patientTypeName}`);
						configPickerClinic = null;
						configPickerEntries = [];
					}}
				>
					<p class="text-sm font-semibold text-slate-800">{entry.insuranceCategoryName}</p>
					<p class="text-xs text-slate-500">{entry.patientTypeName}</p>
				</button>
			{/each}
		</div>
	</AquaModal>
{/if}

{#if confirmModal}
	<AquaModal title="Confirm Action" onclose={() => confirmModal = false}>
		<div class="space-y-6">
			<p class="text-sm text-gray-700">{confirmMessage}</p>
			<div class="flex gap-3">
				<button
					type="button"
					onclick={() => confirmModal = false}
					class="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50"
					disabled={actionLoading}
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={runConfirmAction}
					disabled={actionLoading}
					class="flex-1 rounded-lg bg-red-600 px-4 py-2 font-medium text-white hover:bg-red-700 cursor-pointer"
				>
					{actionLoading ? 'Processing...' : 'Confirm'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showQrModal && qrClinic}
<AquaModal title="Registration QR Code" onclose={() => showQrModal = false} panelClass="sm:max-w-[400px]">
<div class="flex flex-col items-center gap-4 py-2">
<div class="flex h-12 w-12 items-center justify-center rounded-2xl" style="background: linear-gradient(to bottom, #3b82f6, #1d4ed8); box-shadow: 0 4px 14px rgba(29,78,216,0.3);">
<Building2 class="h-6 w-6 text-white" />
</div>
<div class="text-center">
<p class="text-base font-bold text-slate-900">{qrClinic.name}</p>
<p class="text-xs text-slate-500 mt-0.5">{qrClinic.department}</p>
</div>

{#if qrDataUrl}
<div class="rounded-2xl overflow-hidden border border-slate-200 p-2 bg-white">
<img src={qrDataUrl} alt="QR code" class="w-[240px] h-[240px]" />
</div>
{:else}
<div class="w-[240px] h-[240px] rounded-2xl bg-slate-100 flex items-center justify-center">
<div class="w-8 h-8 rounded-full border-2 border-blue-400 border-t-transparent animate-spin"></div>
</div>
{/if}

<div class="w-full rounded-xl px-3 py-2 text-center" style="background: #f0f4fa; border: 1px solid rgba(0,0,0,0.08);">
<p class="text-[10px] font-mono text-slate-500 break-all">{clinicRegUrl(qrClinic)}</p>
</div>

<div class="flex w-full gap-2">
<button type="button" onclick={copyLink} class="flex flex-1 items-center justify-center gap-2 rounded-[999px] py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: #f0f4fa; border: 1px solid rgba(0,0,0,0.1);">
<Copy class="h-4 w-4" />
Copy Link
</button>
<button type="button" onclick={downloadQr} disabled={!qrDataUrl} class="flex flex-1 items-center justify-center gap-2 rounded-[999px] py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-50" style="background: linear-gradient(to bottom, #4d90fe, #1d4ed8); box-shadow: 0 3px 10px rgba(29,78,216,0.28);">
<Download class="h-4 w-4" />
Download
</button>
</div>

<a href={clinicRegUrl(qrClinic)} target="_blank" rel="noopener noreferrer" class="flex items-center gap-1.5 text-xs font-semibold text-blue-500 hover:underline">
<ExternalLink class="h-3.5 w-3.5" />
Open registration page
</a>
</div>
</AquaModal>
{/if}


<style>
@media (min-width: 1024px) {
.clinics-table {
box-shadow: 0 3px 8px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.94);
}
.clinic-item {
background: white !important;
box-shadow: none !important;
border-color: transparent !important;
border-style: solid !important;
border-width: 0 !important;
border-radius: 0 !important;
min-height: 0 !important;
padding-top: 0.75rem !important;
padding-bottom: 0.75rem !important;
transition: none !important;
transform: none !important;
}
.clinic-item:hover {
background: rgba(239, 246, 255, 0.45) !important;
}
.missing-item {
opacity: 0.6 !important;
}
}
</style>
