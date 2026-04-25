<script lang="ts">
	import { onMount } from 'svelte';
	import {
		billingApi,
		type BillingProfile,
		type AccountsAnalyticsResponse,
		type AccountsAnalyticsBillingCenter,
		type AccountsAnalyticsCollectionRow,
		type AccountsAnalyticsTransaction,
		type AccountsAnalyticsTrendSeries,
		type AccountsAnalyticsUserRow
	} from '$lib/api/billing';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import {
		Wallet,
		IndianRupee,
		Building2,
		CreditCard,
		CalendarDays,
		TrendingUp,
		Users,
		Search,
		Filter,
		ArrowRightLeft,
		Activity,
		UserRound,
		BadgeIndianRupee,
		AlertTriangle,
		ArrowUpRight,
		ShieldCheck
	} from 'lucide-svelte';

	type ViewTab = 'TODAY' | 'COLLECTIONS' | 'TRENDS' | 'USERS';
	type TrendRange = '1W' | '1M' | '1Q' | '1Y';
	type TrendSection = 'OVERVIEW' | 'DEPARTMENTS' | 'INVESTIGATIONS';

	type SummaryCard = {
		id: string;
		label: string;
		value: number;
		icon: typeof Wallet;
		accent: string;
	};

	type InsightCard = {
		id: string;
		title: string;
		value: string;
		description: string;
		tone: 'danger' | 'success' | 'info';
		icon: typeof AlertTriangle;
	};

	let profile = $state<BillingProfile | null>(null);
	let analytics = $state<AccountsAnalyticsResponse | null>(null);
	let loading = $state(true);
	let analyticsLoading = $state(false);

	let activeView = $state<ViewTab>('TODAY');
	let activeTrendRange = $state<TrendRange>('1W');
	let activeTrendSection = $state<TrendSection>('OVERVIEW');

	let selectedBranch = $state('All Branches');
	let selectedDepartment = $state('All Departments');
	let collectionStartDate = $state(new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
	let collectionEndDate = $state(new Date().toISOString().slice(0, 10));
	let lastGeneratedAt = $state('—');

	let userSearch = $state('');
	let usersStartDate = $state(new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
	let usersEndDate = $state(new Date().toISOString().slice(0, 10));

	const pageShellStyle =
		'background: linear-gradient(180deg, #dbe3ee 0%, #d5dee9 52%, #d2dae5 100%);';
	const cardStyle =
		'background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(247,249,252,0.96)); border: 1px solid rgba(130,145,166,0.22); box-shadow: 0 3px 12px rgba(73,93,124,0.12), inset 0 1px 0 rgba(255,255,255,0.72);';
	const viewTabs: Array<{ id: ViewTab; label: string; icon: typeof CalendarDays }> = [
		{ id: 'TODAY', label: 'Today', icon: CalendarDays },
		{ id: 'COLLECTIONS', label: 'Collections', icon: BadgeIndianRupee },
		{ id: 'TRENDS', label: 'Trends', icon: TrendingUp },
		{ id: 'USERS', label: 'Users', icon: Users }
	];

	const trendRanges: TrendRange[] = ['1W', '1M', '1Q', '1Y'];
	const trendSections: TrendSection[] = ['OVERVIEW', 'DEPARTMENTS', 'INVESTIGATIONS'];

	const trendRangeTabs = trendRanges.map((r) => ({ id: r, label: r }));
	const trendSectionTabs = trendSections.map((s) => ({ id: s, label: s.charAt(0) + s.slice(1).toLowerCase() }));

	const branchOptions = $derived.by(() => {
		const branch = analytics?.meta.branch || 'All Branches';
		return ['All Branches', ...(branch !== 'All Branches' ? [branch] : [])];
	});

	const departmentOptions = $derived.by(() => {
		const names = ['All Departments'];

		for (const row of analytics?.collections ?? []) {
			if (!names.includes(row.department)) {
				names.push(row.department);
			}
		}

		if (
			analytics?.meta.department &&
			analytics.meta.department !== 'All Departments' &&
			!names.includes(analytics.meta.department)
		) {
			names.push(analytics.meta.department);
		}

		return names;
	});

	const summaryCards = $derived<SummaryCard[]>([
		{
			id: 'total',
			label: 'Total Collection',
			value: analytics?.summary.total_collection ?? 0,
			icon: Wallet,
			accent: '#2563eb'
		},
		{
			id: 'cash',
			label: 'Cash',
			value: analytics?.summary.cash ?? 0,
			icon: IndianRupee,
			accent: '#16a34a'
		},
		{
			id: 'card',
			label: 'Card/Digital',
			value: analytics?.summary.card_digital ?? 0,
			icon: CreditCard,
			accent: '#2563eb'
		}
	]);

	const billingCenters = $derived<AccountsAnalyticsBillingCenter[]>(analytics?.billing_centers ?? []);
	const liveTransactions = $derived<AccountsAnalyticsTransaction[]>(analytics?.live_transactions ?? []);
	const collectionRows = $derived<AccountsAnalyticsCollectionRow[]>(analytics?.collections ?? []);
	const userPerformanceData = $derived<AccountsAnalyticsUserRow[]>(analytics?.users ?? []);

	const trendLabels = $derived(analytics?.trend_labels ?? []);
	const activeTrendSeries = $derived<AccountsAnalyticsTrendSeries[]>(
		analytics?.trends?.[activeTrendRange]?.[activeTrendSection] ?? []
	);

	const filteredCollectionRows = $derived.by(() => {
		if (selectedDepartment === 'All Departments') return collectionRows;
		return collectionRows.filter((row) => row.department === selectedDepartment);
	});

	const filteredUsers = $derived.by(() => {
		const query = userSearch.trim().toLowerCase();
		if (!query) return userPerformanceData;
		return userPerformanceData.filter((user) => user.name.toLowerCase().includes(query));
	});

	const insightCards = $derived.by<InsightCard[]>(() => {
		const total = analytics?.summary.total_collection ?? 0;
		const cash = analytics?.summary.cash ?? 0;
		const digital = analytics?.summary.card_digital ?? 0;
		const users = analytics?.users ?? [];
		const topUser = users[0];

		const cashShare = total > 0 ? (cash / total) * 100 : 0;
		const digitalShare = total > 0 ? (digital / total) * 100 : 0;

		return [
			{
				id: 'cash-share',
				title: 'Cash Share',
				value: `${cashShare.toFixed(1)}%`,
				description: 'Cash contribution to total collection',
				tone: cashShare > 60 ? 'danger' : 'info',
				icon: AlertTriangle
			},
			{
				id: 'digital-share',
				title: 'Digital Share',
				value: `${digitalShare.toFixed(1)}%`,
				description: 'Card / UPI / online contribution',
				tone: digitalShare > 0 ? 'success' : 'info',
				icon: ArrowUpRight
			},
			{
				id: 'top-user',
				title: 'Top Billing User',
				value: topUser ? topUser.name : '—',
				description: topUser
					? `${formatCurrency(topUser.total_collection)} across ${topUser.transactions} transactions`
					: 'No billing user activity in selected range',
				tone: 'info',
				icon: ShieldCheck
			}
		];
	});

	const chartMax = $derived.by(() => {
		const values = activeTrendSeries.flatMap((series) => series.values);
		if (values.length === 0) return 1000;
		const max = Math.max(...values);
		return Math.ceil(max / 1000) * 1000 + 1000;
	});

	const yTicks = $derived([0, chartMax * 0.25, chartMax * 0.5, chartMax * 0.75, chartMax]);

	const chartWidth = 920;
	const chartHeight = 360;
	const chartPaddingX = 50;
	const chartPaddingTop = 26;
	const chartPaddingBottom = 36;
	const chartInnerWidth = chartWidth - chartPaddingX * 2;
	const chartInnerHeight = chartHeight - chartPaddingTop - chartPaddingBottom;
	const chartBaseY = chartPaddingTop + chartInnerHeight;

	function formatCurrency(value: number) {
		return `₹${value.toLocaleString('en-IN', {
			maximumFractionDigits: 2,
			minimumFractionDigits: value % 1 === 0 ? 0 : 2
		})}`;
	}

	function formatDateTime(value: string | null) {
		if (!value) return '—';
		const date = new Date(value);
		return date.toLocaleString('en-IN', {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusStyle(tone: AccountsAnalyticsUserRow['status_tone']) {
		switch (tone) {
			case 'success':
				return 'background: rgba(220,252,231,0.94); color: #15803d; border: 1px solid rgba(34,197,94,0.18);';
			case 'warning':
				return 'background: rgba(255,237,213,0.96); color: #c2410c; border: 1px solid rgba(249,115,22,0.18);';
			default:
				return 'background: rgba(219,234,254,0.95); color: #2563eb; border: 1px solid rgba(59,130,246,0.18);';
		}
	}

	function getInsightStyle(tone: InsightCard['tone']) {
		switch (tone) {
			case 'danger':
				return 'background: linear-gradient(to bottom, rgba(254,242,242,0.98), rgba(254,226,226,0.92)); border: 1px solid rgba(252,165,165,0.38);';
			case 'success':
				return 'background: linear-gradient(to bottom, rgba(240,253,244,0.98), rgba(220,252,231,0.92)); border: 1px solid rgba(134,239,172,0.42);';
			default:
				return 'background: linear-gradient(to bottom, rgba(239,246,255,0.98), rgba(219,234,254,0.92)); border: 1px solid rgba(147,197,253,0.38);';
		}
	}

	function getInsightTextStyle(tone: InsightCard['tone']) {
		switch (tone) {
			case 'danger':
				return 'color: #dc2626;';
			case 'success':
				return 'color: #16a34a;';
			default:
				return 'color: #2563eb;';
		}
	}

	function getX(index: number, count: number) {
		if (count <= 1) return chartPaddingX + chartInnerWidth / 2;
		return chartPaddingX + (chartInnerWidth / (count - 1)) * index;
	}

	function getY(value: number) {
		return chartPaddingTop + chartInnerHeight - (value / chartMax) * chartInnerHeight;
	}

	function buildLinePath(values: number[]) {
		return values
			.map((value, index) => `${index === 0 ? 'M' : 'L'} ${getX(index, values.length)} ${getY(value)}`)
			.join(' ');
	}

	function buildAreaPath(values: number[]) {
		const firstX = getX(0, values.length);
		const lastX = getX(values.length - 1, values.length);
		return `${buildLinePath(values)} L ${lastX} ${chartBaseY} L ${firstX} ${chartBaseY} Z`;
	}

	async function loadAnalytics(range: TrendRange = activeTrendRange) {
		analyticsLoading = true;
		try {
			const response = await billingApi.getAccountsAnalytics({
				start_date: collectionStartDate,
				end_date: collectionEndDate,
				branch: selectedBranch === 'All Branches' ? undefined : selectedBranch,
				department: selectedDepartment === 'All Departments' ? undefined : selectedDepartment,
				trend_range: range
			});

			analytics = response;
			selectedBranch = response.meta.branch || 'All Branches';
			if (!departmentOptions.includes(selectedDepartment)) {
				selectedDepartment = response.meta.department || 'All Departments';
			}
			lastLoadedTrendRange = range;
			lastGeneratedAt = new Date().toLocaleTimeString('en-IN', {
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch (error: unknown) {
			console.error(error);
			toastStore.addToast('Failed to load accounts analytics', 'error');
		} finally {
			analyticsLoading = false;
		}
	}

	async function generateReport() {
		await loadAnalytics(activeTrendRange);
	}

	function syncUserDateRangeToCollections() {
		collectionStartDate = usersStartDate;
		collectionEndDate = usersEndDate;
		void loadAnalytics(activeTrendRange);
	}

	let lastLoadedTrendRange = $state<TrendRange | null>(null);

	$effect(() => {
		if (activeView !== 'TRENDS' || !analytics) return;
		if (lastLoadedTrendRange === activeTrendRange) return;

		lastLoadedTrendRange = activeTrendRange;
		void loadAnalytics(activeTrendRange);
	});

	onMount(async () => {
		if (!redirectIfUnauthorized(['ACCOUNTS'])) return;

		try {
			profile = await billingApi.getMe();
			await loadAnalytics(activeTrendRange);
		} catch {
			toastStore.addToast('Failed to load central accounts profile', 'error');
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Central Billing Oversight | MIAS</title>
</svelte:head>

<div class="min-h-screen px-2 py-2 sm:px-3 sm:py-3" style={pageShellStyle}>
	<div class="mx-auto flex w-full max-w-5xl flex-col gap-3">
		<div class="flex justify-center">
			<TabBar
				tabs={viewTabs}
				activeTab={activeView}
				onchange={(id) => (activeView = id as typeof activeView)}
				variant="jiggle"
				stretch={false}
			/>
		</div>

		{#if loading}
			<div class="rounded-[18px] px-6 py-10 text-center" style={cardStyle}>
				<div class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
				<p class="mt-3 text-xs font-medium text-slate-500">Loading...</p>
			</div>
		{:else if activeView === 'TODAY'}
			<section class="space-y-3">
				<div class="grid gap-3 grid-cols-3">
					{#each summaryCards as card (card.id)}
						{@const Icon = card.icon}
						<div class="rounded-[16px] px-4 py-3 text-center" style={cardStyle}>
							<div class="mb-1.5 flex items-center justify-center gap-1.5">
								<Icon class="h-3.5 w-3.5" style={`color: ${card.accent};`} />
								<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
									{card.label}
								</p>
							</div>
							<p class="text-xl font-black" style={`color: ${card.accent};`}>
								{formatCurrency(card.value)}
							</p>
						</div>
					{/each}
				</div>

				<div class="space-y-2">
					<p class="px-1 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
						Collection by Billing Center
					</p>
					{#if billingCenters.length > 0}
						<div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
							{#each billingCenters as center (center.id)}
								<div class="rounded-[14px] px-4 py-4 text-center" style={cardStyle}>
									<div class="mb-1.5 flex items-center justify-center gap-1.5">
										<span class="h-2 w-2 rounded-full" style={`background: ${center.color};`}></span>
										<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
											{center.name}
										</p>
									</div>
									<p class="text-lg font-black text-slate-800">{formatCurrency(center.value)}</p>
								</div>
							{/each}
						</div>
					{:else}
						<div class="rounded-[14px] px-4 py-8 text-center" style={cardStyle}>
							<Building2 class="mx-auto h-7 w-7 text-slate-300" />
							<p class="mt-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
								No billing center data
							</p>
						</div>
					{/if}
				</div>

				<div class="overflow-hidden rounded-[18px]" style={cardStyle}>
					<div class="border-b border-slate-200/80 px-4 py-3">
						<p class="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
							Real-Time Transactions
						</p>
					</div>

					<div class="divide-y divide-slate-200/75">
						{#if liveTransactions.length > 0}
							{#each liveTransactions as item (item.id)}
								<div class="flex items-center justify-between gap-3 px-4 py-3">
									<div class="flex items-center gap-2.5">
										<div
											class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
											style="background: linear-gradient(to bottom, rgba(219,234,254,0.98), rgba(191,219,254,0.92)); border: 1px solid rgba(96,165,250,0.28);"
										>
											<ArrowRightLeft class="h-4 w-4 text-blue-600" />
										</div>
										<div>
											<p class="text-sm font-black text-slate-800">{item.name}</p>
											<p class="text-[11px] font-semibold text-slate-400">
												{item.subtitle} · {formatDateTime(item.date)}
											</p>
										</div>
									</div>
									<div class="shrink-0 text-right">
										<p class="text-base font-black text-slate-800">{formatCurrency(item.amount)}</p>
										<p class="text-[11px] font-semibold text-slate-400">{item.method}</p>
									</div>
								</div>
							{/each}
						{:else}
							<div class="px-6 py-8 text-center">
								<ArrowRightLeft class="mx-auto h-8 w-8 text-slate-300" />
								<p class="mt-2 text-xs font-medium text-slate-500">No transactions available</p>
							</div>
						{/if}
					</div>
				</div>
			</section>
		{:else if activeView === 'COLLECTIONS'}
			<section class="space-y-3">
				<div class="rounded-[18px] p-4" style={cardStyle}>
					<div class="mb-3 flex items-center gap-2">
						<Filter class="h-3.5 w-3.5 text-slate-500" />
						<p class="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">
							Filter Collections
						</p>
					</div>

					<div class="grid gap-3 lg:grid-cols-4">
						<div>
							<label
								for="accounts-branch"
								class="mb-1.5 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400"
							>
								Clinic/Branch
							</label>
							<select
								id="accounts-branch"
								bind:value={selectedBranch}
								class="w-full rounded-2xl px-4 py-3 text-sm font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
							>
								{#each branchOptions as option (option)}
									<option value={option}>{option}</option>
								{/each}
							</select>
						</div>

						<div>
							<label
								for="accounts-department"
								class="mb-1.5 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400"
							>
								Department
							</label>
							<select
								id="accounts-department"
								bind:value={selectedDepartment}
								class="w-full rounded-2xl px-4 py-3 text-sm font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
							>
								{#each departmentOptions as option (option)}
									<option value={option}>{option}</option>
								{/each}
							</select>
						</div>

						<div>
							<label
								for="accounts-start-date"
								class="mb-1.5 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400"
							>
								Start Date
							</label>
							<input
								id="accounts-start-date"
								type="date"
								bind:value={collectionStartDate}
								class="w-full rounded-2xl px-4 py-3 text-sm font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
							/>
						</div>

						<div>
							<label
								for="accounts-end-date"
								class="mb-1.5 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400"
							>
								End Date
							</label>
							<input
								id="accounts-end-date"
								type="date"
								bind:value={collectionEndDate}
								class="w-full rounded-2xl px-4 py-3 text-sm font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04);"
							/>
						</div>
					</div>

					<button
						class="mt-3 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-black text-white transition-opacity hover:opacity-95"
						style="background: linear-gradient(to bottom, #2f80ff, #1565d8); border: 1px solid rgba(0,0,0,0.18);"
						onclick={generateReport}
						disabled={analyticsLoading}
					>
						<Filter class="h-4 w-4" />
						{analyticsLoading ? 'Generating...' : 'Generate Report'}
					</button>
				</div>

				<div class="overflow-hidden rounded-[18px]" style={cardStyle}>
					<div class="hidden grid-cols-[2.1fr_1fr_1fr_1fr] gap-4 border-b border-slate-200/80 px-4 py-3 md:grid">
						<p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Department</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Cash</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Card</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Total</p>
					</div>

					<div class="divide-y divide-slate-200/75">
						{#if filteredCollectionRows.length > 0}
							{#each filteredCollectionRows as row (row.id)}
								<div class="grid grid-cols-[2.1fr_1fr_1fr_1fr] items-center gap-4 px-4 py-3">
									<p class="text-sm font-black text-slate-800">{row.department}</p>
									<p class="text-right text-sm font-black text-slate-700">{formatCurrency(row.cash)}</p>
									<p class="text-right text-sm font-black text-slate-700">{formatCurrency(row.card)}</p>
									<p class="text-right text-sm font-black text-blue-600">{formatCurrency(row.total)}</p>
								</div>
							{/each}
						{:else}
							<div class="px-6 py-8 text-center">
								<BadgeIndianRupee class="mx-auto h-8 w-8 text-slate-300" />
								<p class="mt-2 text-xs font-medium text-slate-500">No collection data available</p>
							</div>
						{/if}
					</div>
				</div>
			</section>
		{:else if activeView === 'TRENDS'}
			<section class="space-y-3">
				<div class="flex flex-col items-center gap-2">
					<TabBar
						tabs={trendRangeTabs}
						activeTab={activeTrendRange}
						onchange={(id) => (activeTrendRange = id as TrendRange)}
						variant="jiggle"
						size="compact"
						stretch={false}
					/>
					<TabBar
						tabs={trendSectionTabs}
						activeTab={activeTrendSection}
						onchange={(id) => (activeTrendSection = id as TrendSection)}
						variant="jiggle"
						size="compact"
						stretch={false}
					/>
				</div>

				<div class="rounded-[18px] p-4" style={cardStyle}>
					<div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
						<p class="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
							{activeTrendSection} Trend Analysis
						</p>

						<div class="flex flex-wrap items-center gap-4">
							{#each activeTrendSeries as series (series.id)}
								<div class="flex items-center gap-2">
									<span class="h-2.5 w-2.5 rounded-full" style={`background: ${series.color};`}></span>
									<span class="text-xs font-black uppercase tracking-[0.12em] text-slate-500">
										{series.label}
									</span>
								</div>
							{/each}
						</div>
					</div>

					{#if activeTrendSeries.length > 0 && trendLabels.length > 0}
						<div class="overflow-x-auto">
							<svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} class="min-w-[760px] w-full">
								<defs>
									{#each activeTrendSeries as series (series.id)}
										<linearGradient id={`gradient-${series.id}`} x1="0" y1="0" x2="0" y2="1">
											<stop offset="0%" stop-color={series.color} stop-opacity="0.18"></stop>
											<stop offset="100%" stop-color={series.color} stop-opacity="0.04"></stop>
										</linearGradient>
									{/each}
								</defs>

								{#each yTicks as tick (`${tick}`)}
									<line
										x1={chartPaddingX}
										x2={chartWidth - chartPaddingX}
										y1={getY(tick)}
										y2={getY(tick)}
										stroke="rgba(148,163,184,0.22)"
										stroke-dasharray="4 6"
									></line>
									<text
										x={chartPaddingX - 10}
										y={getY(tick) + 4}
										text-anchor="end"
										font-size="11"
										font-weight="700"
										fill="#94a3b8"
									>
										{Math.round(tick)}
									</text>
								{/each}

								{#each activeTrendSeries as series (series.id)}
									<path d={buildAreaPath(series.values)} fill={`url(#gradient-${series.id})`}></path>
								{/each}

								{#each activeTrendSeries as series (series.id)}
									<path
										d={buildLinePath(series.values)}
										fill="none"
										stroke={series.color}
										stroke-width="3.5"
										stroke-linecap="round"
										stroke-linejoin="round"
									></path>

									{#each series.values as value, index (`${series.id}-${index}`)}
										<circle
											cx={getX(index, series.values.length)}
											cy={getY(value)}
											r="4.5"
											fill={series.color}
										></circle>
									{/each}
								{/each}

								{#each trendLabels as label, index (`${label}-${index}`)}
									<text
										x={getX(index, trendLabels.length)}
										y={chartHeight - 8}
										text-anchor="middle"
										font-size="11"
										font-weight="700"
										fill="#94a3b8"
									>
										{label}
									</text>
								{/each}
							</svg>
						</div>

						<div class="mt-4 grid gap-3 lg:grid-cols-3">
							{#each insightCards as item (item.id)}
								{@const Icon = item.icon}
								<div class="rounded-[14px] p-3" style={getInsightStyle(item.tone)}>
									<div class="mb-2 flex items-center justify-between">
										<p class="text-[10px] font-black uppercase tracking-[0.2em]" style={getInsightTextStyle(item.tone)}>
											{item.title}
										</p>
										<Icon class="h-3.5 w-3.5" style={getInsightTextStyle(item.tone)} />
									</div>
									<p class="text-xl font-black" style={getInsightTextStyle(item.tone)}>{item.value}</p>
									<p class="mt-0.5 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">
										{item.description}
									</p>
								</div>
							{/each}
						</div>
					{:else}
						<div class="rounded-[14px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
							<TrendingUp class="mx-auto h-8 w-8 text-slate-300" />
							<p class="mt-3 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
								No trend data available
							</p>
						</div>
					{/if}
				</div>
			</section>
		{:else}
			<section class="space-y-3">
				<div class="rounded-[18px] p-4" style={cardStyle}>
					<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
						<p class="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
							Billing User Performance
						</p>
						<div class="flex items-center gap-2">
							<input
								type="date"
								bind:value={usersStartDate}
								class="rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28);"
							/>
							<span class="text-xs text-slate-400">–</span>
							<input
								type="date"
								bind:value={usersEndDate}
								class="rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 outline-none"
								style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.28);"
							/>
							<button
								class="cursor-pointer rounded-xl px-3 py-2 text-xs font-black text-white"
								style="background: linear-gradient(to bottom, #2f80ff, #1565d8); border: 1px solid rgba(0,0,0,0.18);"
								onclick={syncUserDateRangeToCollections}
							>
								Apply
							</button>
						</div>
					</div>

					<div class="mt-3 relative">
						<Search class="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
						<input
							type="text"
							placeholder="Search user..."
							bind:value={userSearch}
							class="w-full rounded-xl py-2.5 pl-9 pr-4 text-sm font-medium text-slate-800 outline-none"
							style="background: rgba(255,255,255,0.98); border: 1px solid rgba(148,163,184,0.28);"
						/>
					</div>
				</div>

				<div class="overflow-hidden rounded-[18px]" style={cardStyle}>
					<div class="grid grid-cols-[1.7fr_1fr_1fr_0.9fr] gap-4 border-b border-slate-200/80 px-4 py-3">
						<p class="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">User</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Collection</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Txns</p>
						<p class="text-right text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Status</p>
					</div>

					<div class="divide-y divide-slate-200/75">
						{#if filteredUsers.length > 0}
							{#each filteredUsers as user (user.id)}
								<div class="grid grid-cols-[1.7fr_1fr_1fr_0.9fr] items-center gap-4 px-4 py-3">
									<div class="flex items-center gap-2">
										<div
											class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
											style="background: linear-gradient(to bottom, rgba(219,234,254,0.98), rgba(191,219,254,0.92)); border: 1px solid rgba(96,165,250,0.28);"
										>
											<UserRound class="h-4 w-4 text-blue-600" />
										</div>
										<p class="text-sm font-black text-slate-800">{user.name}</p>
									</div>
									<p class="text-right text-sm font-black text-slate-800">{formatCurrency(user.total_collection)}</p>
									<p class="text-right text-sm font-black text-slate-800">{user.transactions}</p>
									<div class="flex justify-end">
										<span
											class="inline-flex rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em]"
											style={getStatusStyle(user.status_tone)}
										>
											{user.status}
										</span>
									</div>
								</div>
							{/each}
						{:else}
							<div class="px-6 py-8 text-center">
								<Activity class="mx-auto h-8 w-8 text-slate-300" />
								<p class="mt-2 text-xs font-medium text-slate-500">No user performance data.</p>
							</div>
						{/if}
					</div>
				</div>
			</section>
		{/if}
	</div>
</div>
