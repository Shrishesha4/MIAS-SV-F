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
</script>

<AquaModal
	title="Patient Profile & Activity"
	onclose={onclose}
	panelClass="max-w-none h-[calc(100dvh-24px)] max-h-[calc(100dvh-24px)] lg:h-auto lg:max-h-[90vh] lg:max-w-[min(1120px,92vw)]"
	contentClass="p-0"
>
	{#snippet header()}
		<div class="flex min-w-0 items-center gap-2.5">
			<PatientInsuranceAvatar
				name={patient.name}
				src={patient.photo}
				size="md"
				insurancePolicies={patient.insurance_policies}
				patientCategory={patient.category}
				patientCategoryColorPrimary={patient.category_color_primary}
				patientCategoryColorSecondary={patient.category_color_secondary}
			/>
			<div class="min-w-0">
				<p class="truncate text-lg font-black text-slate-900">{patient.name}</p>
				<p class="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">Patient Profile & Logs</p>
			</div>
		</div>
	{/snippet}

	<div class="flex h-full flex-col">
		<div class="border-b border-slate-200 bg-white px-3 py-2.5">
			<TabBar tabs={tabs} activeTab={activeTab} onchange={(tabId) => { activeTab = tabId as OverviewTab; }} ariaLabel="Patient profile tabs" />
		</div>

		<div class="flex-1 overflow-y-auto bg-slate-50/70 p-3.5 sm:p-4">
			{#if activeTab === 'information'}
				<div class="space-y-4">
					<div class="rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
						<div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
							<div class="flex items-start gap-3.5">
								<div class="relative">
									<div class="overflow-hidden rounded-full border-4 border-white shadow-lg">
										{#if resolvedPhoto}
											<img src={resolvedPhoto} alt={patient.name} class="h-24 w-24 object-cover" />
										{:else}
											<div class="flex h-24 w-24 items-center justify-center bg-slate-200 text-2xl font-black text-slate-600">
												{patient.name.slice(0, 1).toUpperCase()}
											</div>
										{/if}
									</div>
									{#if editable}
										<button
											class="absolute bottom-1 right-1 flex h-8.5 w-8.5 items-center justify-center rounded-full border border-blue-200 bg-blue-600 text-white shadow-lg"
											type="button"
											onclick={() => photoInput?.click()}
											disabled={photoUploading}
										>
											{#if photoUploading}
												<div class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
											{:else}
												<ImagePlus class="h-3.5 w-3.5" />
											{/if}
										</button>
										<input bind:this={photoInput} type="file" accept="image/*" class="hidden" onchange={handlePhotoUpload} />
									{/if}
								</div>
								<div class="space-y-1.5">
									<div>
										<h2 class="text-2xl font-black tracking-tight text-slate-900">{patient.name}</h2>
										<p class="mt-0.5 text-base font-semibold text-slate-500">ID: {patient.patient_id}</p>
									</div>
									<p class="text-base font-semibold text-slate-700">{age ?? '—'}, {patient.gender || '—'}, Blood: {patient.blood_group || '—'}</p>
									<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} />
									{#if editable}
										<p class="text-xs text-slate-500">Students and faculty can update the patient photo from here.</p>
									{/if}
								</div>
							</div>
						</div>
					</div>

					<div class="grid gap-4 xl:grid-cols-2">
						<div class="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
							<div class="border-b border-slate-200 bg-slate-100/80 px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-600">Demographics</div>
							<div class="space-y-2.5 p-3.5">
								{#each [
									['Full Name', patient.name],
									['Patient ID', patient.patient_id],
									['Date of Birth', patient.date_of_birth ? `${formatDate(patient.date_of_birth)}${age !== null ? ` (${age}Y)` : ''}` : '—'],
								] as item}
									<div class="flex items-center justify-between rounded-xl border border-slate-200 px-3.5 py-3">
										<p class="text-xs font-black uppercase tracking-[0.16em] text-slate-500">{item[0]}</p>
										<p class="text-base font-black text-slate-900">{item[1] || '—'}</p>
									</div>
								{/each}
							</div>
						</div>

						<div class="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
							<div class="border-b border-slate-200 bg-slate-100/80 px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-600">Medical & Contact</div>
							<div class="space-y-2.5 p-3.5">
								{#each [
									['Gender', patient.gender],
									['Blood Group', patient.blood_group],
									['Contact', patient.phone],
									['Email', patient.email],
									['Primary Diagnosis', patient.primary_diagnosis],
								] as item}
									<div class="flex items-center justify-between rounded-xl border border-slate-200 px-3.5 py-3">
										<p class="text-xs font-black uppercase tracking-[0.16em] text-slate-500">{item[0]}</p>
										<p class="text-right text-base font-black text-slate-900">{item[1] || '—'}</p>
									</div>
								{/each}
							</div>
						</div>
					</div>

					<div class="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
						<div class="border-b border-slate-200 bg-slate-100/80 px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-600">Residential Address</div>
						<div class="p-4 text-base font-semibold text-slate-800">{patient.address || 'No address recorded'}</div>
					</div>
				</div>
			{:else if activeTab === 'insurance'}
				<div class="space-y-3.5">
					{#if (patient.insurance_policies || []).length === 0}
						<div class="rounded-[20px] border border-slate-200 bg-white px-5 py-10 text-center text-sm text-slate-400 shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
							No insurance policies linked to this patient.
						</div>
					{:else}
						{#each patient.insurance_policies || [] as policy (policy.id)}
							<div class="rounded-[20px] border border-slate-200 bg-white p-4 shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
								<div class="flex flex-wrap items-start justify-between gap-2.5">
									<div>
										<p class="text-xl font-black text-slate-900">{policy.provider}</p>
										<p class="mt-0.5 text-xs font-semibold text-slate-500">Policy #{policy.policy_number}</p>
									</div>
									<InsuranceTypeBadges insurancePolicies={[policy]} />
								</div>
								<div class="mt-3.5 grid gap-2.5 md:grid-cols-3">
									<div class="rounded-xl border border-slate-200 px-3.5 py-2.5">
										<p class="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Coverage</p>
										<p class="mt-1 text-base font-bold text-slate-900">{policy.coverage_type || '—'}</p>
									</div>
									<div class="rounded-xl border border-slate-200 px-3.5 py-2.5">
										<p class="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Valid Until</p>
										<p class="mt-1 text-base font-bold text-slate-900">{formatDate(policy.valid_until)}</p>
									</div>
									<div class="rounded-xl border border-slate-200 px-3.5 py-2.5">
										<p class="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Insurance Category</p>
										<p class="mt-1 text-base font-bold text-slate-900">{patient.category || '—'}</p>
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			{:else if activeTab === 'transactions'}
				<div class="space-y-3.5">
					<div class="grid gap-3.5 lg:grid-cols-2">
						{#each [
							{ label: 'Hospital Wallet', icon: CreditCard, balance: hospitalBalance },
							{ label: 'Pharmacy Wallet', icon: BadgeIndianRupee, balance: pharmacyBalance },
						] as walletCard}
							<div class="rounded-[20px] border border-slate-200 bg-gradient-to-br from-blue-600 to-blue-700 p-4 text-white shadow-[0_12px_24px_rgba(37,99,235,0.2)]">
								<div class="flex items-center justify-between">
									<div>
										<p class="text-xs font-bold uppercase tracking-[0.18em] text-blue-100">{walletCard.label}</p>
										<p class="mt-1.5 text-2xl font-black">{formatCurrency(walletCard.balance?.balance)}</p>
									</div>
									<walletCard.icon class="h-7 w-7 text-blue-100" />
								</div>
								<div class="mt-4 grid grid-cols-2 gap-2.5 text-sm">
									<div class="rounded-xl bg-white/10 px-3 py-2.5">
										<p class="text-xs text-blue-100">Credits</p>
										<p class="mt-1 font-black">{formatCurrency(walletCard.balance?.total_credits)}</p>
									</div>
									<div class="rounded-xl bg-white/10 px-3 py-2.5">
										<p class="text-xs text-blue-100">Debits</p>
										<p class="mt-1 font-black">{formatCurrency(walletCard.balance?.total_debits)}</p>
									</div>
								</div>
							</div>
						{/each}
					</div>

					<div class="overflow-hidden rounded-[20px] border border-slate-200 bg-white shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
						<div class="border-b border-slate-200 px-4 py-3 text-xs font-black uppercase tracking-[0.18em] text-slate-600">All Transactions</div>
						<div class="max-h-[46vh] overflow-y-auto p-3.5">
							{#if transactionsLoading}
								<div class="py-12 text-center text-slate-400">Loading transactions…</div>
							{:else if combinedTransactions.length === 0}
								<div class="py-12 text-center text-slate-400">No transactions found.</div>
							{:else}
								<div class="space-y-2.5">
									{#each combinedTransactions as transaction (transaction.id)}
										<div class="rounded-xl border border-slate-200 px-3.5 py-3.5">
											<div class="flex flex-wrap items-start justify-between gap-2.5">
												<div>
													<p class="text-sm font-black text-slate-900">{transaction.description}</p>
													<p class="mt-0.5 text-xs font-medium text-slate-500">{transaction.walletLabel} • {formatDate(`${transaction.date}T${transaction.time || '00:00:00'}`)}</p>
												</div>
												<div class={`rounded-lg px-2.5 py-1 text-xs font-black ${transaction.type === 'CREDIT' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
													{transaction.type} • {formatCurrency(transaction.amount)}
												</div>
											</div>
											<div class="mt-2.5 grid gap-1.5 text-xs text-slate-600 md:grid-cols-2">
												{#if transaction.payment_method}<p><span class="font-semibold text-slate-700">Method:</span> {transaction.payment_method}</p>{/if}
												{#if transaction.department}<p><span class="font-semibold text-slate-700">Department:</span> {transaction.department}</p>{/if}
												{#if transaction.provider}<p><span class="font-semibold text-slate-700">Provider:</span> {transaction.provider}</p>{/if}
												{#if transaction.reference_number}<p><span class="font-semibold text-slate-700">Reference:</span> {transaction.reference_number}</p>{/if}
												{#if transaction.notes}<p class="md:col-span-2"><span class="font-semibold text-slate-700">Notes:</span> {transaction.notes}</p>{/if}
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					</div>
				</div>
			{:else}
				<div class="space-y-3.5">
					<div class="grid gap-2.5 rounded-[20px] border border-slate-200 bg-white p-3.5 shadow-[0_8px_20px_rgba(15,23,42,0.05)] md:grid-cols-[160px_200px_1fr]">
						<div>
							<label for="profile-log-type" class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Filter by type</label>
							<select id="profile-log-type" bind:value={logTypeFilter} class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 outline-none">
								{#each ['ALL', 'CASE_RECORD', 'VITAL', 'PRESCRIPTION', 'PRESCRIPTION_REQUEST', 'REPORT', 'ADMISSION', 'DIAGNOSIS', 'ALERT'] as type}
									<option value={type}>{type === 'ALL' ? 'All entries' : type.replaceAll('_', ' ')}</option>
								{/each}
							</select>
						</div>
						<div>
							<label for="profile-log-actor" class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Filter by actor</label>
							<select id="profile-log-actor" bind:value={logActorFilter} class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 outline-none">
								{#each actorOptions as actor}
									<option value={actor}>{actor === 'ALL' ? 'All actors' : actor}</option>
								{/each}
							</select>
						</div>
						<div>
							<label for="profile-log-search" class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Search details</label>
							<div class="relative mt-1.5">
								<Search class="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
								<input id="profile-log-search" bind:value={logSearch} class="w-full rounded-xl border border-slate-200 px-9 py-2 text-sm font-medium text-slate-700 outline-none" placeholder="Search actor, diagnosis, notes, medications, findings..." />
							</div>
						</div>
					</div>

					<div class="flex items-center justify-between px-1">
						<p class="text-xs font-semibold text-slate-500">{filteredLogs.length} matching log entr{filteredLogs.length === 1 ? 'y' : 'ies'}</p>
						<p class="text-xs font-semibold text-slate-500">Newest first</p>
					</div>

					{#if logsLoading && filteredLogs.length === 0}
						<div class="rounded-[24px] border border-slate-200 bg-white px-6 py-12 text-center text-slate-400 shadow-[0_10px_24px_rgba(15,23,42,0.05)]">Loading logs…</div>
					{:else if filteredLogs.length === 0}
						<div class="rounded-[24px] border border-slate-200 bg-white px-6 py-12 text-center text-slate-400 shadow-[0_10px_24px_rgba(15,23,42,0.05)]">No entries match the current filters.</div>
					{:else}
						<div class="space-y-3">
							{#each filteredLogs as entry (entry.id)}
								<div class="rounded-[20px] border border-slate-200 bg-white p-4 shadow-[0_8px_20px_rgba(15,23,42,0.05)]">
									<div class="flex flex-wrap items-start justify-between gap-2.5">
										<div class="min-w-0">
											<div class="flex flex-wrap items-center gap-1.5">
												<span class="rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-[0.16em] text-blue-700">{entry.type.replaceAll('_', ' ')}</span>
												<p class="text-xs font-semibold text-slate-500">{formatDateTime(entry.timestamp)}</p>
											</div>
											<p class="mt-1.5 text-lg font-black text-slate-900">{entry.title}</p>
											<p class="mt-0.5 text-sm font-semibold text-slate-600">{entry.summary || 'No summary available'}</p>
										</div>
										<div class="rounded-xl bg-slate-100 px-2.5 py-1.5 text-right">
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Actor</p>
											<p class="text-sm font-bold text-slate-800">{entry.actor || 'Unknown'}</p>
										</div>
									</div>

									{#if entry.details.length > 0}
										<div class="mt-3 grid gap-2.5 md:grid-cols-2">
											{#each entry.details as detail (`${entry.id}-${detail.label}`)}
												<div class="rounded-xl border border-slate-200 px-3.5 py-2.5">
													<p class="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">{detail.label}</p>
													<p class="mt-1 whitespace-pre-wrap text-xs font-medium leading-5 text-slate-800">{detail.value}</p>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</AquaModal>
