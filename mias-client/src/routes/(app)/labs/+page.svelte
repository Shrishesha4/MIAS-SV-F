<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { labTechnicianApi, type LabDashboardResponse, type LabQueueReport } from '$lib/api/lab-technicians';
	import { facultyApi, type FacultySearchResult } from '$lib/api/faculty';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaSelect from '$lib/components/ui/AquaSelect.svelte';
	import { RefreshCw, Loader2, FlaskConical, ShieldCheck, ClipboardList, CheckCircle2, CircleAlert, Search, FileText, Microscope, Clock3, ChevronRight, Plus, Trash2, TestTube2 } from 'lucide-svelte';

	type QueueTab = 'new' | 'progress' | 'completed';
	type FindingRow = {
		parameter: string;
		value: string;
		reference: string;
		status: string;
		unit?: string;
		isTemplate?: boolean;
		paramTemplate?: {
			low?: number | null;
			critically_low?: number | null;
			high?: number | null;
			critically_high?: number | null;
			reference_required?: boolean;
		};
	};
	type ResultForm = {
		supervisor_id: string;
		findings: FindingRow[];
	};

	function createEmptyFindingRow(): FindingRow {
		return {
			parameter: '',
			value: '',
			reference: '',
			status: 'Normal',
		};
	}

	function createEmptyResultForm(): ResultForm {
		return {
			supervisor_id: '',
			findings: [],
		};
	}

	function computeStatusPreview(value: string, row: FindingRow): string {
		if (!row.paramTemplate || !row.paramTemplate.reference_required) return '';
		const v = parseFloat(value);
		if (isNaN(v)) return '';
		const { critically_low, critically_high, low, high } = row.paramTemplate;
		if (critically_low != null && v <= critically_low) return 'Critically Low';
		if (critically_high != null && v >= critically_high) return 'Critically High';
		if (low != null && v < low) return 'Low';
		if (high != null && v > high) return 'High';
		return 'Normal';
	}

	function formatTimestamp(value: string | null | undefined, time: string | null | undefined = null): string {
		if (!value) {
			return 'Time not recorded';
		}
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) {
			return value;
		}
		const formatted = parsed.toLocaleString('en-IN', {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit',
		});
		return time ? `${formatted} · ${time}` : formatted;
	}

	const auth = get(authStore);

	let loading = $state(true);
	let refreshing = $state(false);
	let error = $state('');
	let dashboard = $state<LabDashboardResponse | null>(null);
	let activeTab = $state<QueueTab>('new');
	let searchQuery = $state('');
	let checkingInLabId = $state<string | null>(null);
	let acceptingReportId = $state<string | null>(null);
	let savingResults = $state(false);
	let detailLoading = $state(false);
	let showDetailModal = $state(false);
	let showResultsModal = $state(false);
	let selectedReportId = $state<string | null>(null);
	let reportDetail = $state<LabQueueReport | null>(null);
	let resultForm = $state<ResultForm>(createEmptyResultForm());
	let supervisors = $state<FacultySearchResult[]>([]);

	const computedOverallStatus = $derived.by(() => {
		const activeStatuses = resultForm.findings
			.filter((f) => f.value.trim())
			.map((f) => f.status);
		if (activeStatuses.some((s) => s === 'Critically Low' || s === 'Critically High')) return 'CRITICAL' as const;
		if (activeStatuses.some((s) => s === 'Low' || s === 'High')) return 'ABNORMAL' as const;
		return 'NORMAL' as const;
	});

	const technician = $derived(dashboard?.technician ?? null);
	const hasTemplateParams = $derived((reportDetail?.test_parameters?.length ?? 0) > 0);
	const queueCounts = $derived.by(() => ({
		new: dashboard?.new_orders.length ?? 0,
		progress: dashboard?.in_progress_orders.length ?? 0,
		completed: dashboard?.completed_reports.length ?? 0,
	}));

	const visibleReports = $derived.by(() => {
		const reports = activeTab === 'new'
			? dashboard?.new_orders ?? []
			: activeTab === 'progress'
				? dashboard?.in_progress_orders ?? []
				: dashboard?.completed_reports ?? [];

		const query = searchQuery.trim().toLowerCase();
		if (!query) {
			return reports;
		}

		return reports.filter((report) => {
			return [
				report.title,
				report.patient_name,
				report.patient_code ?? '',
				report.ordered_by,
				report.department,
			]
				.join(' ')
				.toLowerCase()
				.includes(query);
		});
	});

	onMount(async () => {
		if (auth.role !== 'LAB_TECHNICIAN') {
			goto('/dashboard');
			return;
		}
		await loadDashboard(true);
	});

	async function loadDashboard(showPrimarySpinner = false) {
		if (showPrimarySpinner) {
			loading = true;
		} else {
			refreshing = true;
		}

		error = '';
		try {
			dashboard = await labTechnicianApi.getDashboard();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load lab dashboard';
		} finally {
			loading = false;
			refreshing = false;
		}
	}

	async function checkInToLab(labId: string) {
		checkingInLabId = labId;
		try {
			await labTechnicianApi.selectActiveLab(labId);
			toastStore.addToast('Checked in successfully', 'success');
			await loadDashboard(false);
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Could not check in to the selected lab', 'error');
		} finally {
			checkingInLabId = null;
		}
	}

	function populateResultForm(report: LabQueueReport) {
		const params = report.test_parameters;
		const paramsByName = new Map(params?.map((p) => [p.name, p]) ?? []);
		let findings: FindingRow[];

		if (report.findings.length > 0) {
			// Re-editing existing results — restore with template metadata if available
			findings = report.findings.map((finding) => {
				const p = paramsByName.get(finding.parameter);
				return {
					parameter: finding.parameter,
					value: finding.value,
					reference: finding.reference ?? '',
					status: finding.status || 'Normal',
					unit: p?.unit ?? undefined,
					isTemplate: !!p,
					paramTemplate: p
						? { low: p.low, critically_low: p.critically_low, high: p.high, critically_high: p.critically_high, reference_required: p.reference_required }
						: undefined,
				};
			});
		} else if (params && params.length > 0) {
			// First-time entry — pre-populate rows from template
			findings = params.map((p) => ({
				parameter: p.name,
				value: '',
				reference: p.normal_range ?? '',
				status: 'Normal',
				unit: p.unit ?? undefined,
				isTemplate: true,
				paramTemplate: { low: p.low, critically_low: p.critically_low, high: p.high, critically_high: p.critically_high, reference_required: p.reference_required },
			}));
		} else {
			findings = [];
		}

		resultForm = {
			supervisor_id: supervisors.find((sup) => sup.name === report.supervised_by)?.id ?? '',
			findings,
		};
	}

	async function loadReportDetail(reportId: string, mode: 'view' | 'results') {
		selectedReportId = reportId;
		reportDetail = null;
		detailLoading = true;
		showDetailModal = mode === 'view';
		showResultsModal = mode === 'results';

		if (mode === 'results' && supervisors.length === 0) {
			try {
				supervisors = await facultyApi.searchFaculty('');
			} catch {
				// non-blocking — supervisor dropdown will be empty
			}
		}

		try {
			const detail = await labTechnicianApi.getReport(reportId);
			reportDetail = detail;
			if (mode === 'results') {
				populateResultForm(detail);
			}
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to load report details', 'error');
			showDetailModal = false;
			showResultsModal = false;
			selectedReportId = null;
		} finally {
			detailLoading = false;
		}
	}

	function closeDetailModal() {
		showDetailModal = false;
		if (!showResultsModal) {
			reportDetail = null;
			selectedReportId = null;
		}
	}

	function closeResultsModal() {
		showResultsModal = false;
		resultForm = createEmptyResultForm();
		if (!showDetailModal) {
			reportDetail = null;
			selectedReportId = null;
		}
	}

	async function acceptOrder(reportId: string, openResultsAfter = false) {
		acceptingReportId = reportId;
		try {
			await labTechnicianApi.acceptReport(reportId);
			toastStore.addToast('Lab order accepted', 'success');
			await loadDashboard(false);
			if (openResultsAfter) {
				await loadReportDetail(reportId, 'results');
			}
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Could not accept this order', 'error');
		} finally {
			acceptingReportId = null;
		}
	}

	function addFindingRow() {
		resultForm = {
			...resultForm,
			findings: [...resultForm.findings, createEmptyFindingRow()],
		};
	}

	function removeFindingRow(index: number) {
		if (resultForm.findings.length === 1) {
			resultForm = {
				...resultForm,
				findings: [createEmptyFindingRow()],
			};
			return;
		}

		resultForm = {
			...resultForm,
			findings: resultForm.findings.filter((_, rowIndex) => rowIndex !== index),
		};
	}

	function updateFindingRow(index: number, field: keyof FindingRow, value: string) {
		const nextRows = resultForm.findings.slice();
		const updated = { ...nextRows[index], [field]: value };
		// Auto-compute status preview when value changes on a template row
		if (field === 'value' && updated.isTemplate) {
			updated.status = computeStatusPreview(value, updated) || 'Normal';
		}
		nextRows[index] = updated;
		resultForm = { ...resultForm, findings: nextRows };
	}

	async function saveResults() {
		if (!selectedReportId) {
			return;
		}

		const findings = resultForm.findings
			.map((finding) => ({
				parameter: finding.parameter.trim(),
				value: finding.value.trim(),
				reference: finding.reference.trim(),
				status: finding.status.trim() || 'Normal',
			}))
			.filter((finding) => finding.parameter && finding.value);

		if (findings.length === 0) {
			toastStore.addToast('Add at least one result row with a value', 'error');
			return;
		}

		if (!resultForm.supervisor_id.trim()) {
			toastStore.addToast('Select supervisor before submitting results', 'error');
			return;
		}

		savingResults = true;
		try {
			await labTechnicianApi.saveResults(selectedReportId, {
				status: computedOverallStatus,
				supervisor_id: resultForm.supervisor_id.trim(),
				findings,
			});
			toastStore.addToast('Results submitted for supervisor approval', 'success');
			closeResultsModal();
			await loadDashboard(false);
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save lab results', 'error');
		} finally {
			savingResults = false;
		}
	}
</script>

{#if loading}
	<div class="px-4 py-16 text-center text-sm text-slate-500">Loading lab dashboard...</div>
{:else if error}
	<div class="rounded-[24px] px-4 py-4 text-sm text-red-700" style="background: #fef2f2; border: 1px solid #fecaca;">{error}</div>
{:else if !technician}
	<div class="rounded-[24px] px-4 py-6 text-sm text-slate-600" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.34);">Technician profile not found.</div>
{:else}
	<div class="space-y-4">
		<div class="rounded-[28px] px-5 py-5"
			style="background: linear-gradient(135deg, #0f172a, #1d4ed8 58%, #38bdf8); box-shadow: 0 18px 36px rgba(15,23,42,0.18);">
			<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
				<div>
					<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-blue-100">Lab Operations</p>
					<h1 class="mt-1 text-xl font-bold text-white">{technician.name}</h1>
					<p class="mt-1 text-sm text-blue-100">
						{technician.technician_id}
						{#if technician.department}
							· {technician.department}
						{/if}
					</p>
					{#if technician.group_name}
						<p class="mt-2 inline-flex rounded-full px-3 py-1 text-[11px] font-semibold text-white" style="background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.18);">
							Batch: {technician.group_name}
						</p>
					{/if}
				</div>

				<button
					onclick={() => loadDashboard(false)}
					disabled={refreshing}
					class="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.18);"
				>
					{#if refreshing}
						<Loader2 class="h-4 w-4 animate-spin" />
					{:else}
						<RefreshCw class="h-4 w-4" />
					{/if}
					Refresh queue
				</button>
			</div>
		</div>

		{#if technician.permitted_labs.length === 0}
			<div class="rounded-[26px] px-5 py-6"
				style="background: linear-gradient(to bottom, #fff7ed, #fffbeb); border: 1px solid #fdba74; box-shadow: 0 10px 20px rgba(251,146,60,0.12);">
				<div class="flex items-center gap-3 text-orange-900">
					<CircleAlert class="h-5 w-5" />
					<div>
						<h2 class="text-base font-bold">No lab access assigned yet</h2>
						<p class="mt-1 text-sm text-orange-800">Your admin needs to place you into a technician batch and assign at least one permitted lab.</p>
					</div>
				</div>
			</div>
		{:else if !technician.active_lab}
			<div class="space-y-4">
				<div class="rounded-[26px] px-5 py-5"
					style="background: linear-gradient(to bottom, #eff6ff, #f8fbff); border: 1px solid rgba(96,165,250,0.3); box-shadow: 0 10px 24px rgba(37,99,235,0.09);">
					<div class="flex items-center gap-3 text-blue-950">
						<ShieldCheck class="h-5 w-5" />
						<div>
							<h2 class="text-base font-bold">Check in to a permitted lab</h2>
							<p class="mt-1 text-sm text-slate-600">You need to select an active lab before you can accept orders or enter results.</p>
						</div>
					</div>
				</div>

				<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
					{#each technician.permitted_labs as lab}
						<div class="rounded-[26px] px-5 py-5"
							style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.26); box-shadow: 0 10px 22px rgba(15,23,42,0.06);">
							<div class="flex items-start justify-between gap-3">
								<div>
									<p class="text-lg font-bold text-slate-900">{lab.name}</p>
									<p class="mt-1 text-sm text-slate-500">{lab.lab_type} · {lab.department}</p>
									{#if lab.location}
										<p class="mt-1 text-xs text-slate-400">{lab.location}</p>
									{/if}
								</div>
								<div class="flex h-12 w-12 items-center justify-center rounded-2xl text-sky-700" style="background: rgba(59,130,246,0.12);">
									<FlaskConical class="h-5 w-5" />
								</div>
							</div>

							<button
								onclick={() => checkInToLab(lab.id)}
								disabled={checkingInLabId !== null}
								class="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
								style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 10px 18px rgba(37,99,235,0.18);"
							>
								{#if checkingInLabId === lab.id}
									<Loader2 class="h-4 w-4 animate-spin" />
									Checking in...
								{:else}
									<ChevronRight class="h-4 w-4" />
									Check in here
								{/if}
							</button>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<div class="space-y-4">
				<div class="rounded-[28px] px-5 py-5"
					style="background: linear-gradient(to bottom, #ffffff, #f8fbff); border: 1px solid rgba(148,163,184,0.26); box-shadow: 0 12px 28px rgba(15,23,42,0.06);">
					<div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
						<div>
							<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Active lab</p>
							<h2 class="mt-1 text-xl font-bold text-slate-900">{technician.active_lab.name}</h2>
							<p class="mt-1 text-sm text-slate-500">{technician.active_lab.lab_type} · {technician.active_lab.department}</p>
							{#if technician.active_lab.location}
								<p class="mt-1 text-xs text-slate-400">{technician.active_lab.location}</p>
							{/if}
							{#if technician.last_checked_in_at}
								<p class="mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold text-emerald-700" style="background: #dcfce7;">
									<CheckCircle2 class="h-3.5 w-3.5" />
									Checked in {formatTimestamp(technician.last_checked_in_at)}
								</p>
							{/if}
						</div>

						<div class="xl:max-w-md">
							<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Switch station</p>
							<div class="mt-3 flex flex-wrap gap-2">
								{#each technician.permitted_labs as lab}
									<button
										onclick={() => checkInToLab(lab.id)}
										disabled={checkingInLabId !== null}
										class="rounded-full px-3 py-2 text-xs font-semibold cursor-pointer disabled:opacity-60"
										style={technician.active_lab.id === lab.id
											? 'background: linear-gradient(to bottom, #dbeafe, #bfdbfe); color: #1d4ed8; border: 1px solid #60a5fa;'
											: 'background: #f8fafc; color: #334155; border: 1px solid rgba(148,163,184,0.3);'}
									>
										{#if checkingInLabId === lab.id}
											<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" />
										{/if}
										{lab.name}
									</button>
								{/each}
							</div>
						</div>
					</div>
				</div>

				<div class="grid gap-4 md:grid-cols-3">
					<div class="rounded-[24px] px-4 py-4" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid rgba(96,165,250,0.28);">
						<div class="flex items-center gap-2 text-blue-900">
							<ClipboardList class="h-4 w-4" />
							<p class="text-sm font-semibold">New orders</p>
						</div>
						<p class="mt-3 text-3xl font-bold text-blue-900">{queueCounts.new}</p>
					</div>
					<div class="rounded-[24px] px-4 py-4" style="background: linear-gradient(to bottom, #fff7ed, #ffedd5); border: 1px solid rgba(251,146,60,0.28);">
						<div class="flex items-center gap-2 text-orange-900">
							<TestTube2 class="h-4 w-4" />
							<p class="text-sm font-semibold">In progress</p>
						</div>
						<p class="mt-3 text-3xl font-bold text-orange-900">{queueCounts.progress}</p>
					</div>
					<div class="rounded-[24px] px-4 py-4" style="background: linear-gradient(to bottom, #ecfdf5, #d1fae5); border: 1px solid rgba(52,211,153,0.28);">
						<div class="flex items-center gap-2 text-emerald-900">
							<CheckCircle2 class="h-4 w-4" />
							<p class="text-sm font-semibold">Completed</p>
						</div>
						<p class="mt-3 text-3xl font-bold text-emerald-900">{queueCounts.completed}</p>
					</div>
				</div>

				<div class="rounded-[28px] px-5 py-5"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.26); box-shadow: 0 12px 28px rgba(15,23,42,0.06);">
					<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
						<div class="flex flex-wrap gap-2">
							<button
								onclick={() => activeTab = 'new'}
								class="rounded-full px-4 py-2 text-sm font-semibold cursor-pointer"
								style={activeTab === 'new' ? 'background: linear-gradient(to bottom, #2563eb, #1d4ed8); color: white;' : 'background: #f1f5f9; color: #475569;'}
							>
								New Orders ({queueCounts.new})
							</button>
							<button
								onclick={() => activeTab = 'progress'}
								class="rounded-full px-4 py-2 text-sm font-semibold cursor-pointer"
								style={activeTab === 'progress' ? 'background: linear-gradient(to bottom, #ea580c, #c2410c); color: white;' : 'background: #f1f5f9; color: #475569;'}
							>
								In Progress ({queueCounts.progress})
							</button>
							<button
								onclick={() => activeTab = 'completed'}
								class="rounded-full px-4 py-2 text-sm font-semibold cursor-pointer"
								style={activeTab === 'completed' ? 'background: linear-gradient(to bottom, #059669, #047857); color: white;' : 'background: #f1f5f9; color: #475569;'}
							>
								Completed ({queueCounts.completed})
							</button>
						</div>

						<div class="relative w-full xl:w-80">
							<label for="lab-order-search" class="sr-only">Search lab orders</label>
							<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
							<input
								id="lab-order-search"
								type="text"
								bind:value={searchQuery}
								placeholder="Search patient, order, department"
								class="w-full rounded-2xl py-3 pl-10 pr-4 text-sm outline-none"
								style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.32);"
							/>
						</div>
					</div>

					<div class="mt-5 space-y-3">
						{#if visibleReports.length === 0}
							<div class="rounded-[24px] px-5 py-8 text-center"
								style="background: #f8fafc; border: 1px dashed rgba(148,163,184,0.48);">
								<div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl text-slate-500" style="background: #e2e8f0;">
									<Microscope class="h-6 w-6" />
								</div>
								<p class="mt-4 text-sm font-semibold text-slate-700">No items in this queue</p>
								<p class="mt-1 text-xs text-slate-500">Orders appear here once they belong to your active lab and match this tab.</p>
							</div>
						{:else}
							{#each visibleReports as report}
								<div class="rounded-[24px] px-4 py-4"
									style="background: white; border: 1px solid rgba(148,163,184,0.26); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
									<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
										<div>
											<div class="flex flex-wrap items-center gap-2">
												<p class="text-base font-bold text-slate-900">{report.title}</p>
												<span class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em]"
													style={report.status === 'CRITICAL'
														? 'background: #fee2e2; color: #b91c1c;'
														: report.status === 'ABNORMAL'
															? 'background: #ffedd5; color: #c2410c;'
															: report.status === 'NORMAL'
																? 'background: #dcfce7; color: #166534;'
																: 'background: #e2e8f0; color: #475569;'}>
													{report.status}
												</span>
											</div>
											<p class="mt-1 text-sm text-slate-600">{report.patient_name}{#if report.patient_code} · {report.patient_code}{/if}</p>
											<div class="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
												<span class="rounded-full px-2.5 py-1" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.24);">{report.type}</span>
												<span class="rounded-full px-2.5 py-1" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.24);">{report.department}</span>
												<span class="rounded-full px-2.5 py-1" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.24);">Ordered by {report.ordered_by}</span>
												<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-1" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.24);">
													<Clock3 class="h-3 w-3" />
													{formatTimestamp(report.ordered_at, report.time)}
												</span>
											</div>

											{#if report.result_summary}
												<p class="mt-3 text-sm text-slate-600">{report.result_summary}</p>
											{/if}

											{#if activeTab === 'progress' && report.accepted_by_name}
												<p class="mt-3 text-xs font-medium text-slate-500">
													{report.accepted_by_me ? 'Assigned to you' : `Accepted by ${report.accepted_by_name}`}
												</p>
											{/if}
										</div>

										<div class="flex flex-col gap-2 lg:min-w-[210px]">
											<!-- <button
												onclick={() => loadReportDetail(report.id, 'view')}
												class="inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer"
												style="background: #f1f5f9;"
											>
												<FileText class="h-4 w-4" />
												View details
											</button> -->

											{#if activeTab === 'new'}
												<button
													onclick={() => acceptOrder(report.id, false)}
													disabled={acceptingReportId !== null}
													class="inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
													style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 10px 18px rgba(37,99,235,0.18);"
												>
													{#if acceptingReportId === report.id}
														<Loader2 class="h-4 w-4 animate-spin" />
														Accepting...
													{:else}
														<ChevronRight class="h-4 w-4" />
														Accept order
													{/if}
												</button>
												<button
													onclick={() => acceptOrder(report.id, true)}
													disabled={acceptingReportId !== null}
													class="inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-blue-700 cursor-pointer disabled:opacity-60"
													style="background: #dbeafe;"
												>
													<Microscope class="h-4 w-4" />
													Accept and enter results
												</button>
											{:else if activeTab === 'progress'}
												{#if report.accepted_by_me}
													{#if report.awaiting_supervisor_approval}
														<div class="rounded-2xl px-4 py-2.5 text-center text-xs font-semibold text-amber-700" style="background: #fef3c7; border: 1px solid #fcd34d;">
															Awaiting supervisor approval
														</div>
													{:else}
														<button
															onclick={() => loadReportDetail(report.id, 'results')}
															class="inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-white cursor-pointer"
															style="background: linear-gradient(to bottom, #ea580c, #c2410c); box-shadow: 0 10px 18px rgba(234,88,12,0.18);"
														>
															<Microscope class="h-4 w-4" />
															Enter results
														</button>
													{/if}
												{:else}
													<div class="rounded-2xl px-4 py-2.5 text-center text-xs font-semibold text-slate-500" style="background: #f8fafc; border: 1px dashed rgba(148,163,184,0.4);">
														Waiting for current assignee
													</div>
												{/if}
											{:else}
												<div class="rounded-2xl px-4 py-2.5 text-center text-xs font-semibold text-emerald-700" style="background: #dcfce7;">
													Completed by {report.performed_by || 'technician'}
												</div>
											{/if}
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<AquaModal
	open={showDetailModal}
	title="Lab Report"
	onclose={closeDetailModal}
	panelClass="sm:max-w-3xl"
	contentClass="p-5"
>
	{#if detailLoading || !reportDetail}
		<div class="py-8 text-center text-sm text-slate-500">Loading report details...</div>
	{:else}
		<div class="space-y-4">
			<div class="rounded-[22px] px-4 py-4" style="background: linear-gradient(to bottom, #f8fafc, #eef2ff); border: 1px solid rgba(148,163,184,0.28);">
				<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
					<div>
						<h3 class="text-lg font-bold text-slate-900">{reportDetail.title}</h3>
						<p class="mt-1 text-sm text-slate-500">{reportDetail.patient_name}{#if reportDetail.patient_code} · {reportDetail.patient_code}{/if}</p>
						<p class="mt-2 text-xs text-slate-400">Ordered {formatTimestamp(reportDetail.ordered_at, reportDetail.time)}</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-700" style="background: #e2e8f0;">{reportDetail.type}</span>
						<span class="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-700" style="background: #e2e8f0;">{reportDetail.department}</span>
					</div>
				</div>
			</div>

			<div class="grid gap-4 md:grid-cols-2">
				<div class="rounded-[22px] px-4 py-4" style="background: white; border: 1px solid rgba(148,163,184,0.28);">
					<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Workflow</p>
					<p class="mt-2 text-sm text-slate-700">Status: <strong>{reportDetail.workflow_status}</strong></p>
					<p class="mt-1 text-sm text-slate-700">Ordered by: <strong>{reportDetail.ordered_by}</strong></p>
					<p class="mt-1 text-sm text-slate-700">Performed by: <strong>{reportDetail.performed_by || 'Not set'}</strong></p>
					<p class="mt-1 text-sm text-slate-700">Supervised by: <strong>{reportDetail.supervised_by || 'Not set'}</strong></p>
				</div>

				<div class="rounded-[22px] px-4 py-4" style="background: white; border: 1px solid rgba(148,163,184,0.28);">
					<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Summary</p>
					<p class="mt-2 text-sm text-slate-700">{reportDetail.result_summary || 'No summary entered yet.'}</p>
					<p class="mt-3 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Notes</p>
					<p class="mt-2 text-sm text-slate-700">{reportDetail.notes || 'No notes entered yet.'}</p>
				</div>
			</div>

			<div class="rounded-[22px] px-4 py-4" style="background: white; border: 1px solid rgba(148,163,184,0.28);">
				<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Result rows</p>
				{#if reportDetail.findings.length === 0}
					<p class="mt-3 text-sm text-slate-500">No structured result rows added.</p>
				{:else}
					<div class="mt-3 overflow-x-auto">
						<table class="min-w-full text-sm">
							<thead>
								<tr class="text-left text-slate-500">
									<th class="pb-2 pr-4">Parameter</th>
									<th class="pb-2 pr-4">Value</th>
									<th class="pb-2 pr-4">Reference</th>
									<th class="pb-2">Status</th>
								</tr>
							</thead>
							<tbody>
								{#each reportDetail.findings as finding}
									<tr class="border-t border-slate-100 text-slate-700">
										<td class="py-2 pr-4 font-medium">{finding.parameter}</td>
										<td class="py-2 pr-4">{finding.value}</td>
										<td class="py-2 pr-4">{finding.reference || '—'}</td>
										<td class="py-2">{finding.status}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</AquaModal>

<AquaModal
	open={showResultsModal}
	title="Enter Lab Results"
	onclose={closeResultsModal}
	panelClass="sm:max-w-4xl"
	contentClass="p-5"
>
	{#if detailLoading || !reportDetail}
		<div class="py-8 text-center text-sm text-slate-500">Loading report form...</div>
	{:else}
		<div class="space-y-4">
			<div class="rounded-[22px] px-4 py-4" style="background: linear-gradient(to bottom, #eff6ff, #f8fbff); border: 1px solid rgba(96,165,250,0.28);">
				<p class="text-sm font-semibold text-slate-900">{reportDetail.title}</p>
				<p class="mt-1 text-xs text-slate-500">{reportDetail.patient_name}{#if reportDetail.patient_code} · {reportDetail.patient_code}{/if}</p>
			</div>

			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<p class="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Overall Status</p>
					<div class="flex h-[46px] items-center rounded-2xl px-4"
						style="background: white; border: 1px solid rgba(148,163,184,0.35);">
						{#if computedOverallStatus === 'CRITICAL'}
							<span class="rounded-full px-3 py-1 text-xs font-semibold text-red-700" style="background: #fee2e2;">Critical</span>
						{:else if computedOverallStatus === 'ABNORMAL'}
							<span class="rounded-full px-3 py-1 text-xs font-semibold text-amber-700" style="background: #fef3c7;">Abnormal</span>
						{:else}
							<span class="rounded-full px-3 py-1 text-xs font-semibold text-emerald-700" style="background: #dcfce7;">Normal</span>
						{/if}
						<span class="ml-2 text-xs text-slate-400">Auto-computed from results</span>
					</div>
				</div>

				<div>
					<label for="lab-result-supervisor" class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Supervised by</label>
				<AquaSelect
					id="lab-result-supervisor"
					bind:value={resultForm.supervisor_id}
					options={supervisors.map(sup => ({value: sup.id, label: sup.name + (sup.department ? ' · ' + sup.department : '')}))}
					placeholder="— Select supervisor —"
				/>
				</div>
			</div>

			<div class="rounded-[22px] px-4 py-4" style="background: white; border: 1px solid rgba(148,163,184,0.28);">
				<div class="flex items-center justify-between gap-3">
					<div>
						<p class="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
							{hasTemplateParams ? 'Test parameters' : 'Structured result rows'}
						</p>
						<p class="mt-1 text-sm text-slate-500">
							{hasTemplateParams
								? 'Enter values for each parameter. Status is auto-computed from reference ranges.'
								: 'Add parameter-wise readings if this test needs individual values.'}
						</p>
					</div>
					{#if !hasTemplateParams}
						<button
							onclick={addFindingRow}
							class="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-blue-700 cursor-pointer"
							style="background: #dbeafe;"
						>
							<Plus class="h-3.5 w-3.5" />
							Add row
						</button>
					{/if}
				</div>

				<div class="mt-4 space-y-3">
					{#each resultForm.findings as finding, index}
						{#if finding.isTemplate}
							<div class="grid grid-cols-[minmax(0,1fr)_140px_84px] gap-3 rounded-[20px] px-3 py-3"
								style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.2);">
								<!-- Parameter name (read-only) -->
								<div>
									<p class="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Parameter</p>
									<div class="w-full rounded-xl px-3 py-2 text-sm text-slate-700"
										style="background: #f1f5f9; border: 1px solid rgba(148,163,184,0.24);">
										{finding.parameter}{#if finding.reference}<span class="ml-1.5 text-xs text-slate-400">({finding.reference})</span>{/if}
									</div>
								</div>
								<!-- Value input with unit hint -->
								<div>
									<label for={`finding-value-${index}`} class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
										Value{finding.unit ? ` (${finding.unit})` : ''}
									</label>
									<input
										id={`finding-value-${index}`}
										type="text"
										value={finding.value}
										oninput={(event) => updateFindingRow(index, 'value', (event.currentTarget as HTMLInputElement).value)}
										placeholder="0.0"
										class="w-full rounded-xl px-3 py-2 text-sm outline-none"
										style="background: white; border: 1px solid rgba(148,163,184,0.32);"
									/>
								</div>
								<!-- Status badge (auto-computed preview) -->
								<div class="flex items-end pb-1">
									{#if !finding.value}
										<span class="text-xs text-slate-400 px-1">—</span>
									{:else if finding.status === 'Normal'}
										<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold text-emerald-700 whitespace-nowrap" style="background: #dcfce7;">Normal</span>
									{:else if finding.status === 'Low' || finding.status === 'High'}
										<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold text-amber-700 whitespace-nowrap" style="background: #fef3c7;">{finding.status}</span>
									{:else if finding.status === 'Critically Low' || finding.status === 'Critically High'}
										<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold text-red-700 whitespace-nowrap" style="background: #fee2e2;">{finding.status}</span>
									{:else}
										<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold text-slate-600 whitespace-nowrap" style="background: #f1f5f9;">{finding.status || '—'}</span>
									{/if}
								</div>
							</div>
						{:else}
							<div class="grid gap-3 rounded-[20px] px-3 py-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_160px]"
								style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.2);">
								<div>
									<label for={`finding-parameter-${index}`} class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Parameter</label>
									<input
										id={`finding-parameter-${index}`}
										type="text"
										value={finding.parameter}
										oninput={(event) => updateFindingRow(index, 'parameter', (event.currentTarget as HTMLInputElement).value)}
										placeholder="Hemoglobin"
										class="w-full rounded-xl px-3 py-2 text-sm outline-none"
										style="background: white; border: 1px solid rgba(148,163,184,0.32);"
									/>
								</div>
								<div>
									<label for={`finding-value-${index}`} class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Value</label>
									<input
										id={`finding-value-${index}`}
										type="text"
										value={finding.value}
										oninput={(event) => updateFindingRow(index, 'value', (event.currentTarget as HTMLInputElement).value)}
										placeholder="13.4 g/dL"
										class="w-full rounded-xl px-3 py-2 text-sm outline-none"
										style="background: white; border: 1px solid rgba(148,163,184,0.32);"
									/>
								</div>
								<div>
									<label for={`finding-reference-${index}`} class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Reference</label>
									<input
										id={`finding-reference-${index}`}
										type="text"
										value={finding.reference}
										oninput={(event) => updateFindingRow(index, 'reference', (event.currentTarget as HTMLInputElement).value)}
										placeholder="12 - 16"
										class="w-full rounded-xl px-3 py-2 text-sm outline-none"
										style="background: white; border: 1px solid rgba(148,163,184,0.32);"
									/>
								</div>
								<div>
									<label for={`finding-status-${index}`} class="mb-1 block text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Row status</label>
									<input
										id={`finding-status-${index}`}
										type="text"
										value={finding.status}
										oninput={(event) => updateFindingRow(index, 'status', (event.currentTarget as HTMLInputElement).value)}
										placeholder="Normal"
										class="w-full rounded-xl px-3 py-2 text-sm outline-none"
										style="background: white; border: 1px solid rgba(148,163,184,0.32);"
									/>
								</div>
							</div>
						{/if}
					{/each}
				</div>
			</div>

			<div class="flex flex-col gap-2 sm:flex-row">
				<button
					onclick={closeResultsModal}
					class="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-slate-700 cursor-pointer"
					style="background: #f1f5f9;"
				>
					Cancel
				</button>
				<button
					onclick={saveResults}
					disabled={savingResults || !resultForm.supervisor_id.trim()}
					class="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #059669, #047857); box-shadow: 0 10px 18px rgba(5,150,105,0.18);"
				>
					{#if savingResults}
						<Loader2 class="h-4 w-4 animate-spin" />
						Submitting...
					{:else}
						<CheckCircle2 class="h-4 w-4" />
						Submit for approval
					{/if}
				</button>
			</div>
		</div>
	{/if}
</AquaModal>