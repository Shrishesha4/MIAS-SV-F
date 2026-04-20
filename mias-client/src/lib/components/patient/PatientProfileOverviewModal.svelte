<script lang="ts">
	import { onMount } from 'svelte';
	import {
		Activity,
		AlertTriangle,
		BadgeIndianRupee,
		BedDouble,
		CalendarClock,
		ClipboardList,
		CreditCard,
		FileText,
		HeartPulse,
		ImagePlus,
		NotebookText,
		Pill,
		Search,
		Shield,
		TestTube2,
		UserRound,
		Wallet,
	} from 'lucide-svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
	import { patientApi } from '$lib/api/patients';
	import { walletApi } from '$lib/api/wallet';
	import { toastStore } from '$lib/stores/toast';
	import type {
		Admission,
		Patient,
		Prescription,
		PrescriptionRequest,
		Report,
		Vital,
		WalletTransaction,
	} from '$lib/api/types';
	import { resolvePhotoSrc } from '$lib/utils/photo';

	type OverviewTab = 'information' | 'insurance' | 'transactions' | 'logs';
	type LogType =
		| 'ALL'
		| 'CASE_RECORD'
		| 'VITAL'
		| 'PRESCRIPTION'
		| 'PRESCRIPTION_REQUEST'
		| 'REPORT'
		| 'ADMISSION'
		| 'DIAGNOSIS'
		| 'ALERT';

	interface LogDetail {
		label: string;
		value: string;
	}

	interface LogEntry {
		id: string;
		type: Exclude<LogType, 'ALL'>;
		timestamp: string;
		actor: string;
		title: string;
		summary: string;
		details: LogDetail[];
		searchableText: string;
	}

	interface Props {
		patient: Patient;
		caseRecords?: any[];
		vitals?: Vital[];
		prescriptions?: Prescription[];
		prescriptionRequests?: PrescriptionRequest[];
		reports?: Report[];
		admissions?: Admission[];
		initialAlertHistory?: any[];
		editable?: boolean;
		onclose: () => void;
		onpatientupdated?: (patient: Patient) => void;
	}

	const {
		patient,
		caseRecords = [],
		vitals = [],
		prescriptions = [],
		prescriptionRequests = [],
		reports = [],
		admissions = [],
		initialAlertHistory = [],
		editable = false,
		onclose,
		onpatientupdated,
	}: Props = $props();

	const tabs = [
		{ id: 'information', label: 'Information', icon: UserRound },
		{ id: 'insurance', label: 'Insurance', icon: Shield },
		{ id: 'transactions', label: 'Transactions', icon: Wallet },
		{ id: 'logs', label: 'Logs', icon: ClipboardList },
	] satisfies Array<{ id: OverviewTab; label: string; icon: typeof UserRound }>;

	let activeTab = $state<OverviewTab>('information');
	let photoInput = $state<HTMLInputElement | null>(null);
	let photoUploading = $state(false);
	let alertHistory = $state.raw<any[]>([]);
	let hospitalTransactions = $state.raw<WalletTransaction[]>([]);
	let pharmacyTransactions = $state.raw<WalletTransaction[]>([]);
	let hospitalBalance = $state<any>(null);
	let pharmacyBalance = $state<any>(null);
	let transactionsLoading = $state(false);
	let logsLoading = $state(false);
	let logTypeFilter = $state<LogType>('ALL');
	let logActorFilter = $state('ALL');
	let logSearch = $state('');

	const resolvedPhoto = $derived(resolvePhotoSrc(patient.photo));
	const age = $derived(
		patient.date_of_birth
			? Math.floor((Date.now() - new Date(patient.date_of_birth).getTime()) / (365.25 * 24 * 60 * 60 * 1000))
			: null
	);

	const combinedTransactions = $derived.by(() => {
		const decorate = (walletType: 'hospital' | 'pharmacy', items: WalletTransaction[]) =>
			items.map((item) => ({ ...item, walletLabel: walletType === 'hospital' ? 'Hospital' : 'Pharmacy' }));
		return [...decorate('hospital', hospitalTransactions), ...decorate('pharmacy', pharmacyTransactions)].sort(
			(a, b) => getTimestampMs(`${b.date}T${b.time || '00:00:00'}`) - getTimestampMs(`${a.date}T${a.time || '00:00:00'}`)
		);
	});

	const actorOptions = $derived.by(() => {
		const actors = new Set<string>();
		for (const entry of logEntries) {
			if (entry.actor && entry.actor !== 'Unknown') {
				actors.add(entry.actor);
			}
		}
		return ['ALL', ...Array.from(actors).sort((a, b) => a.localeCompare(b))];
	});

	function addDetail(details: LogDetail[], label: string, value: unknown) {
		if (value === null || value === undefined || value === '') {
			return;
		}
		const rendered = Array.isArray(value) ? value.filter(Boolean).join(', ') : String(value).trim();
		if (!rendered) {
			return;
		}
		details.push({ label, value: rendered });
	}

	function getTimestampMs(value?: string | null): number {
		if (!value) return 0;
		const parsed = new Date(value);
		return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
	}

	function formatDateTime(value?: string | null): string {
		if (!value) return 'Unknown time';
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return value;
		return parsed.toLocaleString([], {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	function formatDate(value?: string | null): string {
		if (!value) return '—';
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return value;
		return parsed.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });
	}

	function formatCurrency(value?: number | null): string {
		return `₹${Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
	}

	const logEntries = $derived.by<LogEntry[]>(() => {
		const items: LogEntry[] = [];

		for (const record of caseRecords) {
			const details: LogDetail[] = [];
			addDetail(details, 'Department', record.department);
			addDetail(details, 'Procedure', record.procedure_name);
			addDetail(details, 'Findings', record.findings);
			addDetail(details, 'Diagnosis', record.diagnosis);
			addDetail(details, 'Treatment', record.treatment);
			addDetail(details, 'Notes', record.notes);
			addDetail(details, 'Status', record.status);
			addDetail(details, 'Approved by', record.approver_name || record.approved_by);
			const timestamp = record.last_modified_at || record.created_at || `${record.date || ''}T${record.time || '00:00:00'}`;
			const actor = record.last_modified_by || record.created_by_name || 'Unknown';
			items.push({
				id: `case-record-${record.id}`,
				type: 'CASE_RECORD',
				timestamp,
				actor,
				title: record.procedure_name || record.type || 'Case record entry',
				summary: [record.department, record.status].filter(Boolean).join(' • '),
				details,
				searchableText: [actor, record.description, record.findings, record.diagnosis, record.treatment, record.notes]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const vital of vitals) {
			const details: LogDetail[] = [];
			addDetail(details, 'Blood Pressure', vital.systolic_bp && vital.diastolic_bp ? `${vital.systolic_bp}/${vital.diastolic_bp}` : '');
			addDetail(details, 'Heart Rate', vital.heart_rate ? `${vital.heart_rate} bpm` : '');
			addDetail(details, 'Respiratory Rate', vital.respiratory_rate ? `${vital.respiratory_rate}/min` : '');
			addDetail(details, 'Temperature', vital.temperature ? `${vital.temperature}` : '');
			addDetail(details, 'SpO2', vital.oxygen_saturation ? `${vital.oxygen_saturation}%` : '');
			addDetail(details, 'Weight', vital.weight);
			addDetail(details, 'Blood Glucose', vital.blood_glucose);
			addDetail(details, 'Cholesterol', vital.cholesterol);
			addDetail(details, 'BMI', vital.bmi);
			addDetail(details, 'Hemoglobin', vital.hemoglobin);
			addDetail(details, 'WBC', vital.wbc);
			items.push({
				id: `vital-${vital.id}`,
				type: 'VITAL',
				timestamp: vital.recorded_at,
				actor: vital.recorded_by || 'Unknown',
				title: 'Vital signs recorded',
				summary: details.slice(0, 3).map((detail) => `${detail.label}: ${detail.value}`).join(' • '),
				details,
				searchableText: [vital.recorded_by, ...details.map((detail) => `${detail.label} ${detail.value}`)]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const prescription of prescriptions) {
			const details: LogDetail[] = [];
			addDetail(details, 'Department', prescription.department);
			addDetail(details, 'Status', prescription.status);
			addDetail(
				details,
				'Medications',
				prescription.medications.map((medication) => `${medication.name} ${medication.dosage} • ${medication.frequency}`)
			);
			addDetail(details, 'Notes', prescription.notes);
			items.push({
				id: `prescription-${prescription.id}`,
				type: 'PRESCRIPTION',
				timestamp: `${prescription.date || ''}T00:00:00`,
				actor: prescription.doctor || 'Unknown',
				title: `Prescription${prescription.department ? ` • ${prescription.department}` : ''}`,
				summary: `${prescription.status}${prescription.medications.length ? ` • ${prescription.medications.length} medication(s)` : ''}`,
				details,
				searchableText: [prescription.doctor, prescription.notes, ...details.map((detail) => detail.value)]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const request of prescriptionRequests) {
			const details: LogDetail[] = [];
			addDetail(details, 'Medication', request.medication);
			addDetail(details, 'Dosage', request.dosage);
			addDetail(details, 'Status', request.status);
			addDetail(details, 'Notes', request.notes);
			addDetail(details, 'Responded by', request.responded_by);
			addDetail(details, 'Response notes', request.response_notes);
			items.push({
				id: `prescription-request-${request.id}`,
				type: 'PRESCRIPTION_REQUEST',
				timestamp: request.responded_at || `${request.requested_date || ''}T00:00:00`,
				actor: request.responded_by || 'Patient request',
				title: `Prescription request • ${request.medication}`,
				summary: request.status,
				details,
				searchableText: [request.medication, request.notes, request.responded_by, request.response_notes]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const report of reports) {
			const details: LogDetail[] = [];
			addDetail(details, 'Department', report.department);
			addDetail(details, 'Status', report.status);
			addDetail(details, 'Ordered by', report.ordered_by);
			addDetail(details, 'Performed by', report.performed_by);
			addDetail(details, 'Summary', report.result_summary);
			addDetail(details, 'Notes', report.notes);
			addDetail(
				details,
				'Findings',
				(report.findings || []).map((finding) => `${finding.parameter}: ${finding.value}${finding.status ? ` (${finding.status})` : ''}`)
			);
			items.push({
				id: `report-${report.id}`,
				type: 'REPORT',
				timestamp: `${report.date || ''}T${report.time || '00:00:00'}`,
				actor: report.performed_by || report.ordered_by || 'Unknown',
				title: report.title || `${report.type} report`,
				summary: [report.type, report.department, report.status].filter(Boolean).join(' • '),
				details,
				searchableText: [report.title, report.result_summary, report.notes, report.ordered_by, report.performed_by]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const admission of admissions) {
			const details: LogDetail[] = [];
			addDetail(details, 'Department', admission.department);
			addDetail(details, 'Ward / Bed', [admission.ward, admission.bed_number].filter(Boolean).join(' / '));
			addDetail(details, 'Status', admission.status);
			addDetail(details, 'Reason', admission.reason);
			addDetail(details, 'Diagnosis', admission.provisional_diagnosis || admission.diagnosis);
			addDetail(details, 'Care Plan', admission.proposed_plan);
			addDetail(details, 'Physical Examination', admission.physical_examination);
			addDetail(details, 'Notes', admission.notes);
			items.push({
				id: `admission-${admission.id}`,
				type: 'ADMISSION',
				timestamp: admission.created_at || admission.admission_date,
				actor: admission.attending_doctor || 'Unknown',
				title: `${admission.status} admission`,
				summary: [admission.department, admission.ward, admission.bed_number].filter(Boolean).join(' • '),
				details,
				searchableText: [admission.reason, admission.diagnosis, admission.proposed_plan, admission.notes, admission.attending_doctor]
					.filter(Boolean)
					.join(' ')
					.toLowerCase(),
			});
		}

		for (const entry of patient.diagnosis_entries || []) {
			items.push({
				id: `diagnosis-added-${entry.id}`,
				type: 'DIAGNOSIS',
				timestamp: entry.added_at || '',
				actor: entry.added_by || 'Unknown',
				title: 'Diagnosis added',
				summary: entry.diagnosis,
				details: [
					{ label: 'Diagnosis', value: entry.diagnosis },
					...(entry.icd_code ? [{ label: 'ICD Code', value: entry.icd_code }] : []),
					...(entry.icd_description ? [{ label: 'ICD Description', value: entry.icd_description }] : []),
				],
				searchableText: [entry.diagnosis, entry.icd_code, entry.icd_description, entry.added_by].filter(Boolean).join(' ').toLowerCase(),
			});
			if (entry.removed_at) {
				items.push({
					id: `diagnosis-removed-${entry.id}`,
					type: 'DIAGNOSIS',
					timestamp: entry.removed_at,
					actor: entry.removed_by || 'Unknown',
					title: 'Diagnosis removed',
					summary: entry.diagnosis,
					details: [{ label: 'Diagnosis', value: entry.diagnosis }],
					searchableText: [entry.diagnosis, entry.removed_by].filter(Boolean).join(' ').toLowerCase(),
				});
			}
		}

		for (const alert of alertHistory) {
			const details: LogDetail[] = [];
			addDetail(details, 'Severity', alert.severity);
			addDetail(details, 'Type', alert.type);
			addDetail(details, 'Description', alert.description);
			addDetail(details, 'Status', alert.is_active ? 'Active' : 'Inactive');
			items.push({
				id: `alert-${alert.id}`,
				type: 'ALERT',
				timestamp: alert.added_at || '',
				actor: alert.added_by || 'Unknown',
				title: alert.title || 'Medical alert',
				summary: `${alert.is_active ? 'Active' : 'Inactive'}${alert.severity ? ` • ${alert.severity}` : ''}`,
				details,
				searchableText: [alert.title, alert.description, alert.added_by, alert.type, alert.severity].filter(Boolean).join(' ').toLowerCase(),
			});
		}

		return items.sort((a, b) => getTimestampMs(b.timestamp) - getTimestampMs(a.timestamp));
	});

	const filteredLogs = $derived.by(() => {
		const query = logSearch.trim().toLowerCase();
		return logEntries.filter((entry) => {
			if (logTypeFilter !== 'ALL' && entry.type !== logTypeFilter) {
				return false;
			}
			if (logActorFilter !== 'ALL' && entry.actor !== logActorFilter) {
				return false;
			}
			if (query && !entry.searchableText.includes(query) && !entry.title.toLowerCase().includes(query) && !entry.summary.toLowerCase().includes(query)) {
				return false;
			}
			return true;
		});
	});

	async function loadSupplementalData() {
		logsLoading = true;
		transactionsLoading = true;
		try {
			const [nextAlertHistory, nextHospitalTransactions, nextPharmacyTransactions, nextHospitalBalance, nextPharmacyBalance] =
				await Promise.all([
					patientApi.getMedicalAlertHistory(patient.id).catch(() => initialAlertHistory),
					patientApi.getWalletTransactions(patient.id, 'hospital').catch(() => []),
					patientApi.getWalletTransactions(patient.id, 'pharmacy').catch(() => []),
					walletApi.getBalance(patient.id, 'hospital').catch(() => null),
					walletApi.getBalance(patient.id, 'pharmacy').catch(() => null),
				]);
			alertHistory = nextAlertHistory;
			hospitalTransactions = nextHospitalTransactions;
			pharmacyTransactions = nextPharmacyTransactions;
			hospitalBalance = nextHospitalBalance;
			pharmacyBalance = nextPharmacyBalance;
		} finally {
			logsLoading = false;
			transactionsLoading = false;
		}
	}

	async function handlePhotoUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file || photoUploading) {
			return;
		}
		photoUploading = true;
		try {
			const result = await patientApi.uploadPhoto(patient.id, file);
			onpatientupdated?.({ ...patient, photo: result.photo });
			toastStore.addToast('Patient photo updated', 'success');
		} catch {
			toastStore.addToast('Failed to update patient photo', 'error');
		} finally {
			photoUploading = false;
			input.value = '';
		}
	}

	onMount(() => {
		alertHistory = initialAlertHistory;
		void loadSupplementalData();
	});

	// ── Redesigned modal state ──────────────────────────────────────────────
	let selectedWallet = $state<'HOSPITAL' | 'PHARMACY'>('HOSPITAL');
	let insuranceView = $state<'list' | 'add'>('list');
	let claimsView = $state<'list' | 'new'>('list');
	let selectedClaim = $state<any | null>(null);

	let addInsCarrier = $state('');
	let addInsPolicyNum = $state('');
	let addInsCoverage = $state('');
	let addInsValidUntil = $state('');
	let savingIns = $state(false);

	let newClaimDesc = $state('');
	let newClaimAmount = $state('');
	let newClaimEmail = $state('');
	let newClaimDetails = $state('');

	// svelte-ignore state_referenced_locally
	let mappedEmail = $state(patient.email || '');
	let claimReply = $state('');
	let claims = $state<any[]>([]);

	const selectedWalletTxns = $derived(
		selectedWallet === 'HOSPITAL' ? hospitalTransactions : pharmacyTransactions
	);
	const selectedWalletBalance = $derived(
		selectedWallet === 'HOSPITAL' ? hospitalBalance : pharmacyBalance
	);

	function isInsuranceActive(policy: any): boolean {
		if (!policy.valid_until) return true;
		return new Date(policy.valid_until) >= new Date();
	}

	async function handleAddInsurance() {
		if (!addInsCarrier.trim() || !addInsPolicyNum.trim()) {
			toastStore.addToast('Carrier name and policy number are required', 'error');
			return;
		}
		savingIns = true;
		try {
			await patientApi.addInsurancePolicy(patient.id, {
				provider: addInsCarrier,
				policy_number: addInsPolicyNum,
				valid_until: addInsValidUntil || undefined,
				coverage_type: addInsCoverage || undefined,
			});
			onpatientupdated?.({ ...patient });
			addInsCarrier = ''; addInsPolicyNum = ''; addInsCoverage = ''; addInsValidUntil = '';
			insuranceView = 'list';
			toastStore.addToast('Insurance policy added', 'success');
		} catch {
			toastStore.addToast('Failed to add insurance policy', 'error');
		} finally {
			savingIns = false;
		}
	}

	function handleNewClaim() {
		if (!newClaimDesc.trim() || !newClaimAmount.trim()) {
			toastStore.addToast('Description and amount are required', 'error');
			return;
		}
		const clmNum = claims.length + 1;
		const clmId = `CLM-${String(clmNum).padStart(3, '0')}`;
		const claim = {
			id: clmId,
			description: newClaimDesc,
			amount: parseFloat(newClaimAmount),
			email: newClaimEmail,
			details: newClaimDetails,
			status: 'PENDING',
			date: new Date().toISOString().split('T')[0],
			provider: patient.insurance_policies?.[0]?.provider || 'Insurance',
			messages: [
				{
					from: 'SYSTEM',
					subject: `Claim Submission: ${clmId}`,
					body: `Initial claim submission for patient ${patient.patient_id}. Amount: ₹${parseFloat(newClaimAmount).toLocaleString('en-IN')}.`,
					timestamp: new Date().toISOString(),
				},
			],
		};
		const emailTo = newClaimEmail;
		const body = newClaimDetails || newClaimDesc;
		claims = [...claims, claim];
		newClaimDesc = ''; newClaimAmount = ''; newClaimEmail = ''; newClaimDetails = '';
		claimsView = 'list';
		if (emailTo) {
			window.open(`mailto:${emailTo}?subject=Insurance Claim: ${clmId}&body=${encodeURIComponent(body)}`, '_blank');
		}
		toastStore.addToast(`Claim ${clmId} submitted`, 'success');
	}

	function sendClaimReply() {
		if (!claimReply.trim() || !selectedClaim) return;
		const msg = {
			from: 'ME',
			subject: `RE: ${selectedClaim.id}`,
			body: claimReply.trim(),
			timestamp: new Date().toISOString(),
		};
		const updated = { ...selectedClaim, messages: [...selectedClaim.messages, msg] };
		claims = claims.map((c) => (c.id === updated.id ? updated : c));
		selectedClaim = updated;
		claimReply = '';
	}
</script>

<AquaModal
	onclose={onclose}
	panelClass="sm:max-w-[580px]"
	contentClass="p-0"
>
	{#snippet header()}
		{#if selectedClaim}
			<div class="flex flex-1 items-center justify-between gap-2">
				<div class="flex items-center gap-2.5">
					<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-600">
						<FileText class="h-4.5 w-4.5 text-white" />
					</div>
					<div class="min-w-0">
						<p class="truncate text-[15px] font-black text-slate-900">Claim Communication: {selectedClaim.id}</p>
						<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600">{selectedClaim.provider}</p>
					</div>
				</div>
				<button
					type="button"
					onclick={() => (selectedClaim = null)}
					class="shrink-0 rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-white"
					style="background: linear-gradient(to bottom, #4d90fe, #1a56db);"
				>Exit to Profile</button>
			</div>
		{:else}
			<div class="flex items-center gap-2.5">
				<div class="relative shrink-0">
					<div class="h-11 w-11 overflow-hidden rounded-full border-2 border-white shadow-md">
						{#if resolvedPhoto}
							<img src={resolvedPhoto} alt={patient.name} class="h-full w-full object-cover" />
						{:else}
							<div class="flex h-full w-full items-center justify-center bg-blue-100 text-base font-black text-blue-600">
								{patient.name.slice(0, 1).toUpperCase()}
							</div>
						{/if}
					</div>
					{#if editable}
						<button
							class="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-blue-600 text-white shadow"
							type="button"
							onclick={() => photoInput?.click()}
							disabled={photoUploading}
						>
							{#if photoUploading}
								<div class="h-2 w-2 animate-spin rounded-full border border-white border-t-transparent"></div>
							{:else}
								<ImagePlus class="h-2.5 w-2.5" />
							{/if}
						</button>
						<input bind:this={photoInput} type="file" accept="image/*" class="hidden" onchange={handlePhotoUpload} />
					{/if}
				</div>
				<div>
					<p class="text-[17px] font-black leading-tight text-slate-900">{patient.name}</p>
					<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600">Patient Profile &amp; Wallet</p>
				</div>
			</div>
		{/if}
	{/snippet}

	<div class="flex flex-col">
		<!-- Tab bar -->
		{#if !selectedClaim}
			<div class="flex border-b border-slate-200 bg-white">
				{#each [
					{ id: 'information', label: 'INFORMATION' },
					{ id: 'insurance', label: 'INSURANCE' },
					{ id: 'transactions', label: 'TRANSACTIONS' },
				] as tab}
					<button
						type="button"
						onclick={() => (activeTab = tab.id as OverviewTab)}
						class="relative px-4 py-3.5 text-[11px] tracking-[0.12em] transition-colors"
						style={activeTab === tab.id ? 'color: #2563eb; font-weight: 800;' : 'color: #9ca3af; font-weight: 600;'}
					>
						{tab.label}
						{#if activeTab === tab.id}
							<span class="absolute inset-x-2 bottom-0 h-0.5 rounded-t-full bg-blue-600"></span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}

		<!-- Scrollable content -->
		<div class="overflow-y-auto px-5 py-4" style="max-height: calc(85vh - 180px);">
			{#if selectedClaim}
				<!-- Claim communication view -->
				<div class="space-y-3 pb-16">
					{#each selectedClaim.messages as msg, i (i)}
						<div class="rounded-xl border border-slate-200 bg-white p-4">
							<div class="mb-2 flex items-start justify-between gap-2">
								<p class="text-[10px] font-black uppercase tracking-[0.14em] text-blue-600">
									{msg.from === 'SYSTEM' ? 'System' : msg.from === 'ME' ? 'You' : msg.from}
								</p>
								<p class="shrink-0 text-[10px] font-medium text-slate-400">
									{new Date(msg.timestamp).toLocaleString([], { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
								</p>
							</div>
							<p class="text-sm font-black text-slate-900">{msg.subject}</p>
							<p class="mt-1 text-sm text-slate-700">{msg.body}</p>
						</div>
					{/each}
				</div>

			{:else if activeTab === 'information'}
				<div class="space-y-4 pb-2">
					<!-- DEMOGRAPHICS -->
					<div>
						<p class="mb-2 text-[11px] font-black uppercase tracking-[0.14em] text-slate-500">Demographics</p>
						<div class="overflow-hidden rounded-xl border border-slate-200">
							{#each [
								['FULL NAME', patient.name, true],
								['PATIENT ID', patient.patient_id, false],
								['DATE OF BIRTH', patient.date_of_birth ? `${patient.date_of_birth}${age !== null ? ` (${age}Y)` : ''}` : '—', false],
							] as [label, value, highlight], i}
								<div class="flex items-center justify-between px-4 py-3 {i > 0 ? 'border-t border-slate-100' : ''}">
									<p class="text-[11px] font-bold uppercase tracking-[0.12em] {highlight ? 'text-blue-600' : 'text-slate-500'}">{label}</p>
									<p class="text-sm font-bold text-slate-900">{value || '—'}</p>
								</div>
							{/each}
						</div>
					</div>

					<!-- MEDICAL & CONTACT -->
					<div>
						<p class="mb-2 text-[11px] font-black uppercase tracking-[0.14em] text-slate-500">Medical &amp; Contact</p>
						<div class="overflow-hidden rounded-xl border border-slate-200">
							{#each [
								['GENDER', patient.gender],
								['BLOOD GROUP', patient.blood_group],
								['CONTACT', patient.phone],
							] as [label, value], i}
								<div class="flex items-center justify-between px-4 py-3 {i > 0 ? 'border-t border-slate-100' : ''}">
									<p class="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p>
									<p class="text-sm font-bold text-slate-900">{value || '—'}</p>
								</div>
							{/each}
						</div>
					</div>

					<!-- RESIDENTIAL ADDRESS -->
					<div>
						<p class="mb-2 text-[11px] font-black uppercase tracking-[0.14em] text-slate-500">Residential Address</p>
						<div class="rounded-xl border border-slate-200 px-4 py-3">
							<p class="text-sm font-medium text-slate-700">{patient.address || 'No address recorded'}</p>
						</div>
					</div>

					<!-- CURRENT WALLET BALANCE -->
					<div class="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3.5">
						<div>
							<p class="text-[10px] font-black uppercase tracking-[0.14em] text-blue-600">Current Wallet Balance</p>
							<p class="mt-1 text-2xl font-black text-blue-900">
								{#if transactionsLoading}
									<span class="text-base text-slate-400">Loading…</span>
								{:else}
									₹ {Number(hospitalBalance?.balance || 0).toLocaleString('en-IN')}
								{/if}
							</p>
						</div>
						<button
							type="button"
							onclick={() => (activeTab = 'transactions')}
							class="rounded-xl px-4 py-2 text-xs font-black uppercase tracking-wide text-white"
							style="background: linear-gradient(to bottom, #4d90fe, #1a56db); box-shadow: 0 2px 6px rgba(37,99,235,0.3);"
						>View Ledger</button>
					</div>
				</div>

			{:else if activeTab === 'insurance'}
				<div class="space-y-4 pb-2">
					{#if insuranceView === 'add'}
						<!-- Add insurance inline form -->
						<div>
							<div class="mb-3 flex items-center justify-between">
								<p class="text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">Insurance Coverage</p>
								<button type="button" onclick={() => (insuranceView = 'list')} class="rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db);">Cancel</button>
							</div>
							<div class="space-y-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4">
								<div class="grid grid-cols-2 gap-3">
									<div>
										<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Carrier Name</p>
										<input bind:value={addInsCarrier} placeholder="e.g. Apollo Munich" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
									</div>
									<div>
										<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Policy Number</p>
										<input bind:value={addInsPolicyNum} placeholder="e.g. POL-12345" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
									</div>
									<div>
										<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Coverage Amount</p>
										<input bind:value={addInsCoverage} placeholder="e.g. ₹ 3,00,000" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
									</div>
									<div>
										<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Valid Until</p>
										<input type="date" bind:value={addInsValidUntil} class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
									</div>
								</div>
								<div class="flex justify-end">
									<button type="button" onclick={handleAddInsurance} disabled={savingIns} class="rounded-xl px-6 py-2.5 text-sm font-black uppercase tracking-wide text-white disabled:opacity-50" style="background: #16a34a;">
										{savingIns ? 'Saving…' : 'Save Insurance'}
									</button>
								</div>
							</div>
						</div>
					{:else}
						<!-- Insurance coverage list -->
						<div>
							<div class="mb-3 flex items-center justify-between">
								<p class="text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">Insurance Coverage</p>
								<button type="button" onclick={() => (insuranceView = 'add')} class="rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db);">Add Insurance</button>
							</div>
							{#if (patient.insurance_policies || []).length === 0}
								<div class="rounded-xl border border-slate-200 px-4 py-8 text-center text-sm text-slate-400">No insurance policies linked.</div>
							{:else}
								<div class="space-y-3">
									{#each patient.insurance_policies as policy (policy.id)}
										{@const active = isInsuranceActive(policy)}
										<div class="rounded-xl border p-4 {active ? 'border-blue-100 bg-blue-50/30' : 'border-slate-200 bg-white'}">
											<div class="mb-3 flex items-center justify-between">
												<div class="flex items-center gap-2">
													<div class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 {active ? 'border-blue-600 bg-blue-600' : 'border-slate-300'}">
														{#if active}<div class="h-2 w-2 rounded-full bg-white"></div>{/if}
													</div>
													<p class="text-sm font-black text-slate-900">{policy.provider}</p>
												</div>
												<span class="rounded px-2 py-0.5 text-[10px] font-black uppercase tracking-wide {active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}">{active ? 'Active' : 'Expired'}</span>
											</div>
											<div class="grid grid-cols-2 gap-2 text-xs">
												<div>
													<p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Policy Number</p>
													<p class="mt-0.5 font-bold text-slate-800">{policy.policy_number}</p>
												</div>
												<div>
													<p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Coverage</p>
													<p class="mt-0.5 font-bold text-slate-800">{policy.coverage_type || '—'}</p>
												</div>
												<div>
													<p class="text-[10px] font-bold uppercase tracking-wide text-slate-400">Valid Until</p>
													<p class="mt-0.5 font-bold text-slate-800">{formatDate(policy.valid_until)}</p>
												</div>
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>

						<!-- Email mapping -->
						<div>
							<p class="mb-3 text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">Email Mapping &amp; Communications</p>
							<div class="rounded-xl border border-slate-200 bg-white p-4">
								<p class="mb-2 text-[10px] font-bold uppercase tracking-wide text-slate-500">Mapped Patient Email Address</p>
								<div class="flex gap-2">
									<input bind:value={mappedEmail} class="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none" placeholder="patient@example.com" />
									<button type="button" class="rounded-lg px-4 py-2 text-xs font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db);">Update</button>
								</div>
							</div>
						</div>

						<!-- Claims -->
						<div>
							{#if claimsView === 'new'}
								<div>
									<div class="mb-3 flex items-center justify-between">
										<p class="text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">Claims History &amp; Submission</p>
										<button type="button" onclick={() => (claimsView = 'list')} class="rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db);">Cancel</button>
									</div>
									<div class="space-y-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4">
										<div>
											<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Claim Description</p>
											<input bind:value={newClaimDesc} placeholder="e.g. Physical Therapy Session" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
										</div>
										<div class="grid grid-cols-2 gap-3">
											<div>
												<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Amount</p>
												<input bind:value={newClaimAmount} type="number" placeholder="e.g. ₹ 5,000" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
											</div>
											<div>
												<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Recipient Email (Insurance)</p>
												<input bind:value={newClaimEmail} type="email" placeholder="claims@insurer.in" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none" />
											</div>
										</div>
										<div>
											<p class="mb-1 text-[10px] font-black uppercase tracking-wide text-blue-700">Submission Details (Email Body)</p>
											<textarea bind:value={newClaimDetails} placeholder="Enter detailed notes for the insurance provider..." rows={4} class="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none"></textarea>
										</div>
										<div class="flex justify-end">
											<button type="button" onclick={handleNewClaim} class="rounded-xl px-6 py-2.5 text-sm font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db); box-shadow: 0 2px 6px rgba(37,99,235,0.3);">Submit via Email</button>
										</div>
									</div>
								</div>
							{:else}
								<div class="flex items-center justify-between mb-3">
									<p class="text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">Claims History &amp; Submission</p>
									<button type="button" onclick={() => (claimsView = 'new')} class="rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-white" style="background: linear-gradient(to bottom, #4d90fe, #1a56db);">New Claim</button>
								</div>
								{#if claims.length === 0}
									<div class="rounded-xl border border-slate-200 px-4 py-8 text-center text-sm text-slate-400">No claims submitted yet.</div>
								{:else}
									<div class="space-y-2.5">
										{#each claims as claim (claim.id)}
											<button type="button" onclick={() => (selectedClaim = claim)} class="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5 text-left transition-colors hover:bg-slate-50">
												<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50">
													<FileText class="h-4 w-4 text-blue-600" />
												</div>
												<div class="min-w-0 flex-1">
													<p class="text-sm font-black text-slate-900">{claim.description}</p>
													<p class="mt-0.5 text-xs text-slate-400">{claim.id} • {claim.date} • {claim.provider}</p>
												</div>
												<div class="shrink-0 text-right">
													<p class="text-sm font-black text-slate-900">₹ {claim.amount.toLocaleString('en-IN')}</p>
													<p class="mt-0.5 text-[10px] font-black uppercase tracking-wide {claim.status === 'APPROVED' ? 'text-green-600' : claim.status === 'REJECTED' ? 'text-red-600' : 'text-orange-500'}">{claim.status}</p>
												</div>
											</button>
										{/each}
									</div>
								{/if}
							{/if}
						</div>
					{/if}
				</div>

			{:else if activeTab === 'transactions'}
				<div class="space-y-4 pb-2">
					<!-- Wallet toggle cards -->
					<div class="grid grid-cols-2 gap-3">
						{#each [
							{ type: 'HOSPITAL' as const, label: 'General Wallet', balance: hospitalBalance, icon: CreditCard, activeGrad: 'linear-gradient(135deg, #3b82f6, #1d4ed8)' },
							{ type: 'PHARMACY' as const, label: 'Pharmacy Wallet', balance: pharmacyBalance, icon: Pill, activeGrad: 'linear-gradient(135deg, #a855f7, #7c3aed)' },
						] as w}
							<button
								type="button"
								onclick={() => (selectedWallet = w.type)}
								class="relative rounded-xl border p-3.5 text-left transition-all"
								style={selectedWallet === w.type
									? `background: ${w.activeGrad}; border-color: transparent;`
									: 'background: white; border-color: rgb(226 232 240);'}
							>
								<div class="mb-1.5 flex items-center justify-between">
									<p class="text-[10px] font-black uppercase tracking-[0.12em] {selectedWallet === w.type ? 'text-white/80' : 'text-slate-500'}">{w.label}</p>
									<div class="flex items-center gap-1.5">
										{#if selectedWallet === w.type}
											<span class="flex h-5 w-5 items-center justify-center rounded-full bg-white/25 text-xs font-black text-white">+</span>
										{/if}
										<w.icon class="h-4 w-4 {selectedWallet === w.type ? 'text-white/70' : 'text-slate-400'}" />
									</div>
								</div>
								<p class="text-lg font-black {selectedWallet === w.type ? 'text-white' : 'text-slate-900'}">
									{#if transactionsLoading}—{:else}₹ {Number(w.balance?.balance || 0).toLocaleString('en-IN')}{/if}
								</p>
							</button>
						{/each}
					</div>

					<!-- Ledger table -->
					<div>
						<div class="mb-3 flex items-center justify-between">
							<p class="text-[11px] font-black uppercase tracking-[0.14em] text-slate-700">
								{selectedWallet === 'HOSPITAL' ? 'General' : 'Pharmacy'} Ledger
							</p>
							<button type="button" class="flex items-center gap-1 text-xs font-bold text-blue-600">
								<span>↓</span> Print Statement
							</button>
						</div>
						<div class="overflow-hidden rounded-xl border border-slate-200">
							{#if transactionsLoading}
								<div class="py-12 text-center text-sm text-slate-400">Loading transactions…</div>
							{:else if selectedWalletTxns.length === 0}
								<div class="py-12 text-center text-sm text-slate-400">No transactions for this wallet.</div>
							{:else}
								<div class="grid grid-cols-[110px_1fr_90px] border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">
									<span>Date</span>
									<span>Description</span>
									<span class="text-right">Amount</span>
								</div>
								{#each selectedWalletTxns as txn (txn.id)}
									<div class="grid grid-cols-[110px_1fr_90px] items-center border-b border-slate-100 px-4 py-3 last:border-b-0">
										<p class="text-xs font-medium text-slate-600">{String(txn.date ?? '').split('T')[0] || '—'}</p>
										<div class="min-w-0 pr-2">
											<p class="truncate text-sm font-bold text-slate-900">{txn.description}</p>
											{#if txn.reference_number || txn.id}
												<p class="mt-0.5 text-[10px] font-medium text-slate-400">{txn.reference_number || String(txn.id).slice(0, 8).toUpperCase()}</p>
											{/if}
										</div>
										<p class="text-right text-sm font-black {txn.type === 'CREDIT' ? 'text-emerald-600' : 'text-rose-600'}">
											{txn.type === 'CREDIT' ? '+' : '-'}₹{Math.abs(Number(txn.amount)).toLocaleString('en-IN')}
										</p>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		{#if selectedClaim}
			<!-- Claim reply footer -->
			<div class="shrink-0 border-t border-slate-200 bg-white px-5 py-3">
				<div class="flex gap-2">
					<textarea
						bind:value={claimReply}
						placeholder="Type your reply to the insurance company..."
						rows={2}
						class="flex-1 resize-none rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none"
					></textarea>
					<button
						type="button"
						onclick={sendClaimReply}
						class="self-end rounded-xl px-4 py-2.5 text-[11px] font-black uppercase tracking-wide text-white"
						style="background: linear-gradient(to bottom, #4d90fe, #1a56db); box-shadow: 0 2px 6px rgba(37,99,235,0.3); min-width: 90px;"
					>Send Reply</button>
				</div>
			</div>
		{:else}
			<div class="shrink-0 border-t border-slate-200 px-5 py-4" style="background: #f8f9fb; border-radius: 16px">
				<button
					type="button"
					onclick={onclose}
					class="w-full rounded-xl py-3 text-sm font-black uppercase tracking-[0.1em] text-white"
					style="background: linear-gradient(to bottom, #4d90fe, #1a56db); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
				>Close Profile</button>
			</div>
		{/if}
	</div>
</AquaModal>


