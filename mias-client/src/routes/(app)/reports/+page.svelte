<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import type { Report, ReportFinding, ReportImage } from '$lib/api/types';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaInput from '$lib/components/ui/AquaInput.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { 
		TestTube, Search, Filter, ChevronLeft, Eye, Download, Clock, 
		Image as ImageIcon, CheckCircle, AlertTriangle, X, ZoomIn
	} from 'lucide-svelte';

	const statusVariant: Record<string, 'normal' | 'abnormal' | 'critical' | 'pending'> = {
		NORMAL: 'normal',
		ABNORMAL: 'abnormal',
		CRITICAL: 'critical',
		PENDING: 'pending',
	};

	let reports: Report[] = $state([]);
	let loading = $state(true);
	let searchQuery = $state('');
	let selectedType = $state('all');
	let selectedPeriod = $state('all');
	let selectedReport = $state<Report | null>(null);
	let showModal = $state(false);

	const reportTypes = [
		{ value: 'all', label: 'All Types' },
		{ value: 'Laboratory', label: 'Laboratory' },
		{ value: 'Radiology', label: 'Radiology' },
		{ value: 'Cardiology', label: 'Cardiology' },
	];

	const timePeriods = [
		{ value: 'all', label: 'All Time' },
		{ value: '7', label: 'Last 7 Days' },
		{ value: '30', label: 'Last 30 Days' },
		{ value: '90', label: 'Last 3 Months' },
		{ value: '365', label: 'Last Year' },
	];

	const filteredReports = $derived(() => {
		let filtered = reports;

		// Filter by search query
		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			filtered = filtered.filter(r => 
				r.title.toLowerCase().includes(q) || 
				r.id.toLowerCase().includes(q) ||
				r.department.toLowerCase().includes(q)
			);
		}

		// Filter by type
		if (selectedType !== 'all') {
			filtered = filtered.filter(r => r.type === selectedType);
		}

		// Filter by time period
		if (selectedPeriod !== 'all') {
			const days = parseInt(selectedPeriod);
			const cutoff = new Date();
			cutoff.setDate(cutoff.getDate() - days);
			filtered = filtered.filter(r => new Date(r.date) >= cutoff);
		}

		return filtered;
	});

	// Group reports by date
	const groupedReports = $derived(() => {
		const groups: Record<string, Report[]> = {};
		filteredReports().forEach(r => {
			const dateKey = new Date(r.date).toLocaleDateString('en-US', { 
				weekday: 'long', 
				year: 'numeric', 
				month: 'long', 
				day: 'numeric' 
			});
			if (!groups[dateKey]) groups[dateKey] = [];
			groups[dateKey].push(r);
		});
		return groups;
	});

	function formatTime(timeStr: string | undefined): string {
		return timeStr || '';
	}

	function getReportIcon(type: string) {
		if (type === 'Radiology') return { bg: '#f97316', icon: 'radiology' };
		if (type === 'Cardiology') return { bg: '#ef4444', icon: 'cardiology' };
		return { bg: '#8b5cf6', icon: 'lab' };
	}

	function openReportDetail(report: Report) {
		selectedReport = report;
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		selectedReport = null;
	}

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			reports = await patientApi.getReports(patient.id);
		} catch (err) {
			console.error('Failed to load reports', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
	<!-- Header -->
	<div class="flex items-center gap-3">
		<button class="p-2 rounded-full hover:bg-gray-100" onclick={() => history.back()}>
			<ChevronLeft class="w-5 h-5 text-gray-600" />
		</button>
		<h1 class="text-lg font-bold text-gray-800">Investigation Reports</h1>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Search & Filter -->
		<AquaCard>
			<div class="space-y-3">
				<div class="flex items-center gap-2 text-blue-600 font-medium text-sm">
					<Search class="w-4 h-4" />
					Search & Filter
				</div>
				
				<AquaInput 
					placeholder="Search by report name, ID, or department" 
					icon={Search}
					bind:value={searchQuery}
				/>

				<div>
					<label for="report-type-filter" class="text-xs text-gray-500 mb-1 block">Report Type</label>
					<div class="relative">
						<select 
							id="report-type-filter"
							bind:value={selectedType}
							class="w-full px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm text-gray-700 appearance-none cursor-pointer"
						>
							{#each reportTypes as type}
								<option value={type.value}>{type.label}</option>
							{/each}
						</select>
						<Filter class="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
					</div>
				</div>

				<div>
					<label for="time-period-filter" class="text-xs text-gray-500 mb-1 block">Time Period</label>
					<div class="relative">
						<select 
							id="time-period-filter"
							bind:value={selectedPeriod}
							class="w-full px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm text-gray-700 appearance-none cursor-pointer"
						>
							{#each timePeriods as period}
								<option value={period.value}>{period.label}</option>
							{/each}
						</select>
						<Clock class="w-4 h-4 text-gray-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
					</div>
				</div>
			</div>
		</AquaCard>

		<!-- Results Header -->
		<div class="flex items-center justify-between px-4 py-3 rounded-xl"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
			<span class="text-white font-semibold">Investigation Reports</span>
			<span class="px-3 py-1 rounded-full text-xs font-medium bg-white text-blue-600">
				{filteredReports().length} Reports
			</span>
		</div>

		<!-- Reports List grouped by date -->
		{#each Object.entries(groupedReports()) as [dateKey, dateReports]}
			<div class="text-sm text-gray-500 font-medium px-1">{dateKey}</div>
			
			{#each dateReports as report}
				<AquaCard padding={false}>
					<div class="p-4">
						<div class="flex items-start gap-3">
							<!-- Icon -->
							<div 
								class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
								style="background: {getReportIcon(report.type).bg};"
							>
								<TestTube class="w-5 h-5 text-white" />
							</div>

							<!-- Content -->
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold text-gray-800">{report.title}</p>
								
								<!-- Status badges -->
								<div class="flex items-center gap-2 mt-1">
									<StatusBadge variant={statusVariant[report.status]}>
										{report.status === 'PENDING' ? 'Pending' : 'Completed'}
									</StatusBadge>
									{#if report.status !== 'PENDING'}
										<StatusBadge variant={statusVariant[report.status]}>
											{#if report.status === 'NORMAL'}
												<CheckCircle class="w-3 h-3 mr-1" />
											{:else if report.status === 'ABNORMAL'}
												<AlertTriangle class="w-3 h-3 mr-1" />
											{/if}
											{report.status.charAt(0) + report.status.slice(1).toLowerCase()}
										</StatusBadge>
									{/if}
								</div>

								<!-- Meta info -->
								<div class="flex items-center gap-1 mt-2 text-xs text-gray-500">
									<Clock class="w-3 h-3" />
									<span>{formatTime(report.time)}</span>
									<span class="mx-1">·</span>
									<span>{report.department}</span>
									{#if report.images && report.images.length > 0}
										<span class="mx-1">·</span>
										<ImageIcon class="w-3 h-3" />
										<span>{report.images.length} Image{report.images.length > 1 ? 's' : ''}</span>
									{/if}
								</div>
								<p class="text-xs text-gray-400 mt-1">
									Report ID: {report.id.slice(0, 12)}... · Type: {report.type}
								</p>
							</div>

							<!-- View Button -->
							<button 
								class="w-10 h-10 rounded-full flex items-center justify-center shrink-0 cursor-pointer"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
								onclick={() => openReportDetail(report)}
							>
								<Eye class="w-5 h-5 text-white" />
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}
		{/each}

		{#if filteredReports().length === 0}
			<div class="text-center py-12 text-gray-400">
				<TestTube class="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p class="text-sm">No reports found</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Report Detail Modal -->
{#if showModal && selectedReport}
	{@const report = selectedReport}
	<AquaModal onClose={closeModal}>
		{#snippet header()}
			<div class="flex items-center justify-between w-full">
				<div class="flex items-center gap-2">
					{#if report.status === 'PENDING'}
						<span class="w-2 h-2 rounded-full bg-red-500"></span>
					{/if}
					<span class="font-semibold text-gray-800">{report.title}</span>
				</div>
				{#if report.status !== 'PENDING'}
					<button class="p-2 hover:bg-gray-100 rounded-full">
						<Download class="w-5 h-5 text-gray-600" />
					</button>
				{/if}
			</div>
		{/snippet}

		<div class="space-y-4">
			<!-- Report Header -->
			<div class="flex items-start gap-3">
				<div 
					class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
					style="background: {getReportIcon(report.type).bg};"
				>
					<TestTube class="w-6 h-6 text-white" />
				</div>
				<div class="flex-1">
					<h3 class="font-semibold text-gray-800">{report.title}</h3>
					<p class="text-sm text-gray-500">{report.department}</p>
				</div>
				<StatusBadge variant={statusVariant[report.status]}>
					{report.status === 'PENDING' ? 'Pending' : report.status.charAt(0) + report.status.slice(1).toLowerCase()}
				</StatusBadge>
			</div>

			<!-- Report Info Card -->
			<div class="p-4 rounded-xl bg-gray-50 space-y-2">
				<div class="grid grid-cols-2 gap-y-2 text-sm">
					<div>
						<span class="text-gray-500">Report ID:</span>
						<span class="ml-1 text-gray-800 font-medium">{report.id.slice(0, 12)}...</span>
					</div>
					<div>
						<span class="text-gray-500">Type:</span>
						<span class="ml-1 text-gray-800">{report.type}</span>
					</div>
					<div class="col-span-2">
						<span class="text-gray-500">Date & Time:</span>
						<span class="ml-1 text-gray-800">
							{new Date(report.date).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })}, {report.time}
						</span>
					</div>
				</div>
				{#if report.performed_by || report.supervised_by}
					<div class="border-t border-gray-200 pt-2 mt-2 space-y-1 text-sm">
						{#if report.performed_by}
							<div>
								<span class="text-gray-500">Performed By:</span>
								<span class="ml-1 text-gray-800">{report.performed_by}</span>
							</div>
						{/if}
						{#if report.supervised_by}
							<div>
								<span class="text-gray-500">Supervised By:</span>
								<span class="ml-1 text-gray-800">{report.supervised_by}</span>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			{#if report.status === 'PENDING'}
				<!-- Pending State -->
				<div class="p-6 rounded-xl bg-gray-50 text-center">
					<div class="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center mx-auto mb-3">
						<Clock class="w-8 h-8 text-gray-500" />
					</div>
					<h4 class="font-semibold text-gray-800 mb-1">Results Pending</h4>
					<p class="text-sm text-gray-500">
						This report is still being processed.<br/>
						Results will be available soon.
					</p>
				</div>
			{:else}
				<!-- Images -->
				{#if report.images && report.images.length > 0}
					<div>
						<h4 class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
							<ImageIcon class="w-4 h-4" />
							Images
						</h4>
						<div class="space-y-3">
							{#each report.images as image}
								<div class="rounded-xl overflow-hidden border border-gray-200">
									<div class="relative">
										<img 
											src={image.url} 
											alt={image.title} 
											class="w-full h-48 object-cover"
										/>
										<button class="absolute bottom-2 left-2 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shadow-lg">
											<ZoomIn class="w-4 h-4 text-white" />
										</button>
									</div>
									<div class="p-3 bg-gray-50">
										<p class="font-medium text-sm text-gray-800">{image.title}</p>
										{#if image.description}
											<p class="text-xs text-gray-500 mt-1">{image.description}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Findings -->
				{#if report.findings && report.findings.length > 0}
					<div>
						<h4 class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
							<TestTube class="w-4 h-4" />
							Findings
						</h4>
						<div class="rounded-xl border border-gray-200 overflow-hidden">
							<table class="w-full text-sm">
								<thead>
									<tr class="bg-gray-50 border-b border-gray-200">
										<th class="px-3 py-2 text-left font-medium text-gray-600">Parameter</th>
										<th class="px-3 py-2 text-left font-medium text-gray-600">Value</th>
										<th class="px-3 py-2 text-left font-medium text-gray-600">Reference</th>
										<th class="px-3 py-2 text-right font-medium text-gray-600"></th>
									</tr>
								</thead>
								<tbody>
									{#each report.findings as finding}
										<tr class="border-b border-gray-100 last:border-0">
											<td class="px-3 py-2.5 text-gray-700">{finding.parameter}</td>
											<td class="px-3 py-2.5 font-medium text-gray-800">{finding.value}</td>
											<td class="px-3 py-2.5 text-gray-500 text-xs">{finding.reference || '-'}</td>
											<td class="px-3 py-2.5 text-right">
												{#if finding.status === 'Normal'}
													<span class="w-3 h-3 rounded-full bg-green-500 inline-block"></span>
												{:else if finding.status === 'High' || finding.status === 'Low'}
													<span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
												{:else if finding.status === 'Critical'}
													<span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span>
												{:else}
													<span class="w-3 h-3 rounded-full bg-gray-300 inline-block"></span>
												{/if}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{/if}

				<!-- Download Button -->
				<button 
					class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				>
					<Download class="w-5 h-5" />
					Download Report
				</button>
			{/if}
		</div>
	</AquaModal>
{/if}
