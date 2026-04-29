<script lang="ts">
	import { onMount } from 'svelte';
	import { attendanceApi, type AttendanceLogItem } from '$lib/api/attendance';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { Loader2, RefreshCw } from 'lucide-svelte';

	const roleOptions = [
		'ALL',
		'PATIENT',
		'STUDENT',
		'FACULTY',
		'ACADEMIC_MANAGER',
		'NUTRITIONIST',
		'LAB_TECHNICIAN',
		'NURSE',
		'NURSE_SUPERINTENDENT',
		'RECEPTION',
		'BILLING',
		'ACCOUNTS',
		'PHARMACY',
		'OT_MANAGER',
		'MRD'
	];

	let logs = $state<AttendanceLogItem[]>([]);
	let loading = $state(false);
	let reloading = $state(false);
	let errorMessage = $state('');

	let roleFilter = $state('ALL');
	let dateFilter = $state('');
	let searchFilter = $state('');
	let checkedInOnly = $state(false);
	let checkedOutOnly = $state(false);

	let total = $state(0);
	let limit = $state(50);
	let offset = $state(0);

	const hasPrev = $derived(offset > 0);
	const hasNext = $derived(offset + logs.length < total);

	function formatDateTime(value: string | null): string {
		if (!value) return '-';
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return value;
		return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
	}

	function formatDuration(minutes: number | null): string {
		if (minutes == null) return '-';
		if (minutes < 60) return `${minutes}m`;
		const hrs = Math.floor(minutes / 60);
		const mins = minutes % 60;
		return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
	}

	async function loadLogs(resetOffset = false) {
		if (resetOffset) {
			offset = 0;
		}
		if (!loading) {
			loading = true;
		} else {
			reloading = true;
		}
		errorMessage = '';
		try {
			const response = await attendanceApi.getLogs({
				role: roleFilter === 'ALL' ? undefined : roleFilter,
				targetDate: dateFilter || undefined,
				query: searchFilter.trim() || undefined,
				checkedInOnly,
				checkedOutOnly,
				limit,
				offset
			});
			logs = response.items;
			total = response.total;
		} catch (error: any) {
			errorMessage = error?.response?.data?.detail ?? 'Failed to load attendance logs';
		} finally {
			loading = false;
			reloading = false;
		}
	}

	function applyFilters() {
		void loadLogs(true);
	}

	function clearFilters() {
		roleFilter = 'ALL';
		dateFilter = '';
		searchFilter = '';
		checkedInOnly = false;
		checkedOutOnly = false;
		void loadLogs(true);
	}

	function prevPage() {
		if (!hasPrev) return;
		offset = Math.max(0, offset - limit);
		void loadLogs(false);
	}

	function nextPage() {
		if (!hasNext) return;
		offset += limit;
		void loadLogs(false);
	}

	onMount(() => {
		void loadLogs(true);
	});
</script>

<AquaCard>
	{#snippet header()}
		<div class="flex items-center justify-between gap-3">
			<div>
				<p class="text-sm font-semibold text-slate-900">Attendance Logs</p>
				<p class="text-xs text-slate-500">Who checked in/out, when, and where.</p>
			</div>
			<button
				class="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60"
				style="border-color: rgba(15,23,42,0.14); background: #fff;"
				onclick={() => loadLogs(false)}
				disabled={loading || reloading}
			>
				{#if reloading}
					<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Refreshing
				{:else}
					<RefreshCw class="mr-1 inline h-3.5 w-3.5" /> Refresh
				{/if}
			</button>
		</div>
	{/snippet}

	<div class="space-y-4">
		<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
			<label class="flex flex-col gap-1">
				<span class="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Role</span>
				<select bind:value={roleFilter} class="rounded-xl border px-3 py-2 text-sm" style="border-color: rgba(15,23,42,0.12);">
					{#each roleOptions as role}
						<option value={role}>{role}</option>
					{/each}
				</select>
			</label>

			<label class="flex flex-col gap-1">
				<span class="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Date</span>
				<input bind:value={dateFilter} type="date" class="rounded-xl border px-3 py-2 text-sm" style="border-color: rgba(15,23,42,0.12);" />
			</label>

			<label class="flex flex-col gap-1">
				<span class="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Search user</span>
				<input bind:value={searchFilter} type="text" placeholder="Username or email" class="rounded-xl border px-3 py-2 text-sm" style="border-color: rgba(15,23,42,0.12);" />
			</label>
		</div>

		<div class="flex flex-wrap items-center gap-3 text-sm">
			<label class="inline-flex items-center gap-2">
				<input bind:checked={checkedInOnly} type="checkbox" /> Checked in only
			</label>
			<label class="inline-flex items-center gap-2">
				<input bind:checked={checkedOutOnly} type="checkbox" /> Checked out only
			</label>
			<button class="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white" onclick={applyFilters}>Apply</button>
			<button class="rounded-lg border px-3 py-1.5 text-xs font-semibold text-slate-700" style="border-color: rgba(15,23,42,0.14);" onclick={clearFilters}>Reset</button>
		</div>

		{#if errorMessage}
			<p class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
		{/if}

		<div class="overflow-x-auto rounded-2xl border" style="border-color: rgba(15,23,42,0.1);">
			<table class="min-w-full text-sm">
				<thead class="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
					<tr>
						<th class="px-3 py-2">User</th>
						<th class="px-3 py-2">Role</th>
						<th class="px-3 py-2">Check In</th>
						<th class="px-3 py-2">Check Out</th>
						<th class="px-3 py-2">Where</th>
						<th class="px-3 py-2">Duration</th>
					</tr>
				</thead>
				<tbody>
					{#if loading}
						<tr>
							<td colspan="6" class="px-3 py-6 text-center text-slate-500">
								<Loader2 class="mr-2 inline h-4 w-4 animate-spin" /> Loading logs...
							</td>
						</tr>
					{:else if logs.length === 0}
						<tr>
							<td colspan="6" class="px-3 py-6 text-center text-slate-500">No attendance logs found for the selected filters.</td>
						</tr>
					{:else}
						{#each logs as log (log.id)}
							<tr class="border-t" style="border-color: rgba(15,23,42,0.08);">
								<td class="px-3 py-2">
									<p class="font-semibold text-slate-800">{log.username}</p>
									<p class="text-xs text-slate-500">{log.email}</p>
								</td>
								<td class="px-3 py-2">{log.role}</td>
								<td class="px-3 py-2">{formatDateTime(log.checked_in_at)}</td>
								<td class="px-3 py-2">{formatDateTime(log.checked_out_at)}</td>
								<td class="px-3 py-2">
									<p class="text-slate-700">{log.clinic_name ?? log.check_in_location ?? '-'}</p>
									{#if log.check_out_location}
										<p class="text-xs text-slate-500">Out: {log.check_out_location}</p>
									{/if}
								</td>
								<td class="px-3 py-2">{formatDuration(log.duration_minutes)}</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>

		<div class="flex items-center justify-between text-xs text-slate-500">
			<p>Showing {logs.length === 0 ? 0 : offset + 1}-{offset + logs.length} of {total}</p>
			<div class="flex items-center gap-2">
				<button class="rounded-lg border px-2 py-1 disabled:opacity-50" style="border-color: rgba(15,23,42,0.14);" onclick={prevPage} disabled={!hasPrev}>Prev</button>
				<button class="rounded-lg border px-2 py-1 disabled:opacity-50" style="border-color: rgba(15,23,42,0.14);" onclick={nextPage} disabled={!hasNext}>Next</button>
			</div>
		</div>
	</div>
</AquaCard>
