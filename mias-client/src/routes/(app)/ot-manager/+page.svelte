<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { otApi, type OTBooking, type OTTheater, type OTSchedule } from '$lib/api/ot';
	import { toastStore } from '$lib/stores/toast';
	import { goto } from '$app/navigation';
	import {
		Filter, LayoutGrid, LayoutList, Search, Settings,
		ChevronLeft, ChevronRight, CheckCircle, X as XIcon, Clock, User as UserIcon
	} from 'lucide-svelte';

	// ── Auth guard ───────────────────────────────────────────────────────────
	const auth = get(authStore);

	// ── State ────────────────────────────────────────────────────────────────
	let managerName = $state('OT Manager');
	let managerId = $state('');
	let schedule = $state<OTSchedule | null>(null);
	let loading = $state(false);
	let approvingId = $state<string | null>(null);
	let rejectingId = $state<string | null>(null);

	let scheduleMode = $state<'wall' | 'grid'>('wall');
	let filterOpen = $state(false);
	let selectedTheaterIds = $state<Set<string>>(new Set());
	let density = $state(4);
	let searchQuery = $state('');

	function todayISO() { return new Date().toISOString().split('T')[0]; }
	let anchorDate = $state(todayISO());

	// ── Derived ──────────────────────────────────────────────────────────────
	const weekDates = $derived(schedule?.week_dates ?? []);

	const visibleTheaters = $derived(
		(schedule?.theaters ?? []).filter(t => selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id))
	);

	const totalSurgeries = $derived(
		(schedule?.bookings ?? []).filter(b => b.date === anchorDate && b.status !== 'CANCELLED').length
	);

	// ── Helpers ──────────────────────────────────────────────────────────────
	const OP_START = 8 * 60;
	const OP_END   = 20 * 60;

	function toMins(t: string) {
		const [h, m] = t.split(':').map(Number);
		return h * 60 + (m || 0);
	}
	function fmtMins(mins: number) {
		const h = Math.floor(mins / 60);
		const m = mins % 60;
		return `${h}:${m.toString().padStart(2, '0')}`;
	}

	function bookingsForTheaterDay(theaterId: string): OTBooking[] {
		return (schedule?.bookings ?? [])
			.filter(b => b.theater_id === theaterId && b.date === anchorDate && b.status !== 'CANCELLED')
			.sort((a, b) => a.start_time.localeCompare(b.start_time));
	}

	function scheduledCount(theaterId: string) {
		return bookingsForTheaterDay(theaterId).filter(b => b.status === 'SCHEDULED').length +
		       bookingsForTheaterDay(theaterId).filter(b => ['CONFIRMED','IN_PROGRESS','COMPLETED'].includes(b.status)).length;
	}

	type SlotBooking   = { type: 'booking'; booking: OTBooking };
	type SlotAvailable = { type: 'available'; start: string; end: string };
	type Slot = SlotBooking | SlotAvailable;

	function computeSlots(theaterId: string): Slot[] {
		const bks = bookingsForTheaterDay(theaterId);
		const slots: Slot[] = [];
		let cursor = OP_START;
		for (const b of bks) {
			const bStart = toMins(b.start_time);
			const bEnd   = toMins(b.end_time);
			if (bStart > cursor + 1) slots.push({ type: 'available', start: fmtMins(cursor), end: fmtMins(bStart) });
			slots.push({ type: 'booking', booking: b });
			cursor = bEnd;
		}
		if (cursor < OP_END - 30) slots.push({ type: 'available', start: fmtMins(cursor), end: fmtMins(OP_END) });
		return slots;
	}

	function fmtDay(iso: string) {
		const d = new Date(iso + 'T00:00:00');
		return {
			day: d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(),
			num: d.getDate(),
		};
	}

	const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
		SCHEDULED:   { bg: '#dbeafe', text: '#1d4ed8', label: 'SCHEDULED' },
		CONFIRMED:   { bg: '#dcfce7', text: '#16a34a', label: 'CONFIRMED' },
		IN_PROGRESS: { bg: '#ffedd5', text: '#ea580c', label: 'IN PROGRESS' },
		COMPLETED:   { bg: '#f3f4f6', text: '#6b7280', label: 'COMPLETED' },
		CANCELLED:   { bg: '#fee2e2', text: '#dc2626', label: 'CANCELLED' },
	};

	// ── Grid view helpers ────────────────────────────────────────────────────
	const TOTAL_MINS = OP_END - OP_START;

	function gridBookingStyle(b: OTBooking) {
		const start = toMins(b.start_time);
		const end   = toMins(b.end_time);
		const left  = ((start - OP_START) / TOTAL_MINS) * 100;
		const width = ((end - start) / TOTAL_MINS) * 100;
		return `left:${left.toFixed(2)}%; width:${Math.max(width, 1).toFixed(2)}%; position:absolute; top:3px; bottom:3px;`;
	}

	const GRID_COLORS = ['#dcfce7','#fef9c3','#dbeafe','#fce7f3','#ede9fe','#ffedd5','#f0fdf4'];
	const GRID_TEXT   = ['#166534','#854d0e','#1e3a8a','#9d174d','#5b21b6','#7c2d12','#14532d'];
	function gridColor(i: number) { return GRID_COLORS[i % GRID_COLORS.length]; }
	function gridText(i: number)  { return GRID_TEXT[i % GRID_TEXT.length]; }

	const gridHours = $derived.by(() => {
		const step = Math.max(1, Math.round(12 / Math.max(1, density)));
		const hrs: string[] = [];
		for (let h = 8; h <= 20; h += step) hrs.push(`${h}:00`);
		return hrs;
	});

	// ── Data load ────────────────────────────────────────────────────────────
	async function loadSchedule(date?: string) {
		loading = true;
		try {
			schedule = await otApi.getSchedule(date ?? anchorDate);
		} catch {
			toastStore.addToast('Failed to load schedule', 'error');
		} finally {
			loading = false;
		}
	}

	function selectDay(d: string) {
		anchorDate = d;
		loadSchedule(d);
	}

	function prevWeek() {
		const d = new Date(anchorDate);
		d.setDate(d.getDate() - 7);
		anchorDate = d.toISOString().split('T')[0];
		loadSchedule(anchorDate);
	}
	function nextWeek() {
		const d = new Date(anchorDate);
		d.setDate(d.getDate() + 7);
		anchorDate = d.toISOString().split('T')[0];
		loadSchedule(anchorDate);
	}

	// ── Actions ──────────────────────────────────────────────────────────────
	async function approveBooking(bookingId: string) {
		approvingId = bookingId;
		try {
			await otApi.approveBooking(bookingId);
			toastStore.addToast('Booking approved', 'success');
			await loadSchedule();
		} catch {
			toastStore.addToast('Failed to approve booking', 'error');
		} finally {
			approvingId = null;
		}
	}

	async function rejectBooking(bookingId: string) {
		rejectingId = bookingId;
		try {
			await otApi.rejectBooking(bookingId);
			toastStore.addToast('Booking rejected', 'success');
			await loadSchedule();
		} catch {
			toastStore.addToast('Failed to reject booking', 'error');
		} finally {
			rejectingId = null;
		}
	}

	onMount(async () => {
		if (auth.role !== 'OT_MANAGER') { goto('/dashboard'); return; }
		try {
			const mgr = await otApi.getManagerProfile();
			managerName = mgr.name;
			managerId = mgr.manager_id;
		} catch { /* ignore */ }
		await loadSchedule();
	});
</script>

<!-- ═══════════════════════════════════════════════════════════════════════════
     OT MANAGER DASHBOARD
     ═══════════════════════════════════════════════════════════════════════════ -->
<div class="flex flex-col min-h-dvh" style="background: #eef1f6;">

	<!-- ── Top header ──────────────────────────────────────────────────────── -->
	<div class="flex items-center justify-between px-6 py-4 bg-white border-b border-slate-200">
		<div class="flex items-center gap-3">
			<div class="flex h-10 w-10 items-center justify-center rounded-xl"
				style="background: linear-gradient(to bottom right, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);">
				<svg class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
				</svg>
			</div>
			<div>
				<p class="text-base font-black uppercase tracking-wider text-slate-900">OT Manager Dashboard</p>
				<p class="text-[10px] font-bold uppercase tracking-widest text-blue-600">Master Schedule &amp; Resource Allocation</p>
			</div>
		</div>
		<div class="flex items-center gap-3">
			<div class="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
				<Search class="h-3.5 w-3.5 text-slate-400" />
				<input
					bind:value={searchQuery}
					placeholder="Search surgeries..."
					class="w-40 bg-transparent text-xs text-slate-700 outline-none placeholder:text-slate-400"
				/>
			</div>
			<button class="rounded-xl border border-slate-200 p-2 hover:bg-slate-50 cursor-pointer text-slate-500">
				<Settings class="h-4 w-4" />
			</button>
		</div>
	</div>

	<!-- ── Week + Controls ─────────────────────────────────────────────────── -->
	<div class="flex items-center gap-4 px-6 py-4">
		<!-- Week strip -->
		<div class="flex flex-1 items-center gap-2">
			<button onclick={prevWeek} class="rounded-xl border border-slate-200 bg-white p-2 cursor-pointer hover:bg-slate-50 text-slate-500">
				<ChevronLeft class="h-4 w-4" />
			</button>
			<div class="flex flex-1 gap-2">
				{#each weekDates as d}
					{@const f = fmtDay(d)}
					<button
						onclick={() => selectDay(d)}
						class="flex flex-1 flex-col items-center rounded-xl py-2.5 cursor-pointer transition-all text-center border {d === anchorDate ? 'text-white border-transparent' : 'text-slate-600 bg-white border-slate-200 hover:bg-slate-50'}"
						style={d === anchorDate ? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 3px 10px rgba(37,99,235,0.35);' : ''}
					>
						<span class="text-[9px] font-black uppercase tracking-widest {d === anchorDate ? 'opacity-80' : 'text-slate-400'}">{f.day}</span>
						<span class="text-lg font-black leading-tight">{f.num}</span>
					</button>
				{/each}
			</div>
			<button onclick={nextWeek} class="rounded-xl border border-slate-200 bg-white p-2 cursor-pointer hover:bg-slate-50 text-slate-500">
				<ChevronRight class="h-4 w-4" />
			</button>
		</div>

		<!-- View toggle + Density + Filter -->
		<div class="flex items-center gap-2">
			<!-- Grid / List toggle -->
			<div class="flex rounded-xl border border-slate-200 bg-white overflow-hidden">
				<button
					onclick={() => scheduleMode = 'grid'}
					class="p-2 cursor-pointer transition-colors {scheduleMode === 'grid' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-50'}"
					title="Grid view"
				>
					<LayoutGrid class="h-4 w-4" />
				</button>
				<button
					onclick={() => scheduleMode = 'wall'}
					class="p-2 cursor-pointer transition-colors {scheduleMode === 'wall' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-50'}"
					title="Wall view"
				>
					<LayoutList class="h-4 w-4" />
				</button>
			</div>

			<!-- Density -->
			<div class="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5">
				<span class="text-[9px] font-black uppercase tracking-widest text-slate-400">DENSITY</span>
				<input type="range" min="1" max="10" bind:value={density} class="w-20 cursor-pointer accent-blue-600" />
				<span class="w-3 text-center text-xs font-black text-slate-700">{density}</span>
			</div>

			<!-- Filter -->
			<div class="relative">
				<button
					onclick={() => filterOpen = !filterOpen}
					class="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-black uppercase tracking-wide text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
				>
					<Filter class="h-3.5 w-3.5" />
					FILTER OTs ({selectedTheaterIds.size > 0 ? selectedTheaterIds.size : (schedule?.theaters.length ?? 0)})
				</button>
				{#if filterOpen}
				<div class="absolute right-0 top-full mt-2 z-20 w-56 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
					<p class="mb-2 px-1 text-[9px] font-black uppercase tracking-widest text-slate-400">Filter by OT Room</p>
					{#each schedule?.theaters ?? [] as t}
					<label class="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-2 hover:bg-slate-50">
						<input type="checkbox"
							checked={selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id)}
							onchange={() => {
								const s = new Set(selectedTheaterIds);
								const all = schedule?.theaters ?? [];
								if (s.size === 0) all.forEach(x => s.add(x.id));
								s.has(t.id) ? s.delete(t.id) : s.add(t.id);
								selectedTheaterIds = s.size === all.length ? new Set() : s;
							}}
							class="rounded accent-blue-600"
						/>
						<span class="text-xs text-slate-700">{t.ot_id}{t.name ? ` — ${t.name}` : ''}</span>
					</label>
					{/each}
				</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- ── Content area ─────────────────────────────────────────────────────── -->
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
		</div>
	{:else if scheduleMode === 'wall'}
	<!-- ════ WALL VIEW ════ -->
	<div class="flex flex-1 gap-4 overflow-x-auto overflow-y-auto px-6 pb-6 min-h-0">
		{#each visibleTheaters as theater}
			{@const slots = computeSlots(theater.id)}
			{@const sched = scheduledCount(theater.id)}
			<div class="flex w-[280px] shrink-0 flex-col rounded-2xl bg-white border border-slate-200 overflow-hidden" style="box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
				<!-- OT column header -->
				<div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
					<span class="text-sm font-black text-slate-800">{theater.ot_id}{theater.name ? ` — ${theater.name}` : ''}</span>
					{#if sched > 0}
					<span class="rounded-full px-2.5 py-0.5 text-[10px] font-black text-white"
						style="background: linear-gradient(to right, #3b82f6, #2563eb);">
						{sched} Scheduled
					</span>
					{/if}
				</div>
				<!-- Slots list -->
				<div class="flex flex-col gap-2 overflow-y-auto p-3">
					{#each slots as slot}
						{#if slot.type === 'available'}
							<!-- Empty available slot -->
							<div class="rounded-xl border-2 border-dashed border-red-300 bg-red-50 px-3 py-2.5">
								<div class="flex items-center justify-between">
									<span class="text-[11px] font-bold text-red-500">{slot.start} – {slot.end}</span>
									<span class="rounded-lg bg-red-500 px-2 py-0.5 text-[9px] font-black text-white">EMPTY +</span>
								</div>
								<p class="mt-1 text-[9px] font-black uppercase tracking-widest text-red-400">AVAILABLE SLOT</p>
							</div>
						{:else if slot.booking.status === 'SCHEDULED'}
							<!-- Pending approval slot — orange dashed -->
							<div class="rounded-xl border-2 border-dashed border-orange-400 bg-orange-50 px-3 py-2.5">
								<div class="flex items-center justify-between mb-1">
									<span class="text-[11px] font-bold text-orange-600">{slot.booking.start_time} – {slot.booking.end_time}</span>
									<button
										onclick={() => approveBooking(slot.booking.id)}
										disabled={approvingId === slot.booking.id}
										class="flex items-center gap-1 rounded-lg px-2 py-0.5 text-[9px] font-black text-white cursor-pointer disabled:opacity-60"
										style="background: linear-gradient(to right, #f97316, #ea580c);"
									>
										{#if approvingId === slot.booking.id}
											<span class="h-2.5 w-2.5 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>
										{:else}
											<CheckCircle class="h-2.5 w-2.5" />
										{/if}
										APPROVE BOOKING ✓
									</button>
								</div>
								<p class="text-[10px] font-black text-orange-700 uppercase tracking-wide">
									PENDING: {slot.booking.doctor_name ? `DR. ${slot.booking.doctor_name.split(' ').slice(-1)[0].toUpperCase()}` : 'FACULTY'}
								</p>
								<p class="text-[10px] italic text-orange-500 mt-0.5">{slot.booking.procedure}</p>
								<div class="mt-1.5 flex justify-end">
									<button
										onclick={() => rejectBooking(slot.booking.id)}
										disabled={rejectingId === slot.booking.id}
										class="text-[8px] font-bold text-red-400 hover:text-red-600 cursor-pointer"
									>Reject</button>
								</div>
							</div>
						{:else}
							<!-- Regular booking card -->
							{@const sc = STATUS_COLORS[slot.booking.status] ?? STATUS_COLORS.SCHEDULED}
							<div class="rounded-xl border border-slate-100 bg-white px-3 py-2.5 space-y-1.5" style="box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
								<div class="flex items-center justify-between">
									<span class="text-[12px] font-black text-slate-800">{slot.booking.patient_name ?? 'Patient'}</span>
									<span class="rounded-full px-2 py-0.5 text-[9px] font-black" style="background:{sc.bg}; color:{sc.text};">{sc.label}</span>
								</div>
								<p class="text-[11px] font-semibold text-blue-600">{slot.booking.procedure}</p>
								<div class="flex items-center justify-between">
									<span class="flex items-center gap-1 text-[10px] text-slate-500">
										<Clock class="h-3 w-3" />
										{slot.booking.start_time} – {slot.booking.end_time}
									</span>
									<span class="flex items-center gap-1 text-[9px] text-slate-400">
										<UserIcon class="h-3 w-3" />
										{slot.booking.doctor_name.split(' ').slice(-1)[0]}
									</span>
								</div>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		{/each}

		{#if visibleTheaters.length === 0}
			<div class="flex flex-1 items-center justify-center">
				<p class="text-sm text-slate-400">No OT rooms to display</p>
			</div>
		{/if}
	</div>

	{:else}
	<!-- ════ GRID VIEW ════ -->
	<div class="flex-1 overflow-auto px-4 pb-6 min-h-0">
		<div style="min-width: 900px;">
			<!-- Header row -->
			<div class="flex sticky top-0 z-10 rounded-t-xl overflow-hidden" style="background:#eef1f6;">
				<div class="w-24 shrink-0 py-3 pr-2 text-[9px] font-black uppercase tracking-widest text-slate-400 text-center border-r border-slate-200 bg-white">ROOM</div>
				<div class="relative flex-1 flex bg-white border-b border-slate-200">
					{#each Array.from({length: 12}, (_, i) => i + 8) as h}
						<div class="flex-1 py-3 text-center text-[10px] font-bold text-slate-500 border-r border-slate-200">
							{h}:00
						</div>
					{/each}
				</div>
			</div>
			<!-- Rows -->
			{#each visibleTheaters as theater, ti}
				{@const bks = bookingsForTheaterDay(theater.id)}
				<div class="flex border-b border-slate-200" class:bg-slate-50={ti % 2 === 1}>
					<div class="w-24 shrink-0 flex items-center justify-center py-3 pr-2 text-[10px] font-black text-slate-700 border-r border-slate-200 bg-white">
						{theater.ot_id}
					</div>
					<div class="relative flex-1 h-16 bg-white">
						{#each Array.from({length: 13}, (_, i) => i) as i}
							<div class="absolute top-0 bottom-0 border-r border-slate-100" style="left:{(i/12*100).toFixed(2)}%;"></div>
						{/each}
						{#each bks as b, bi}
							{@const isPending = b.status === 'SCHEDULED'}
							{@const cellBg = isPending ? '#fff7ed' : gridColor(bi)}
							{@const cellBorder = isPending ? '#f97316' : gridText(bi)}
							{@const cellBorderStyle = isPending ? 'dashed' : 'solid'}
							<div
								class="absolute rounded-md px-1.5 py-1 overflow-hidden cursor-pointer transition-opacity hover:opacity-90 border"
								style="{gridBookingStyle(b)} background:{cellBg}; border-color:{cellBorder}; border-style:{cellBorderStyle};"
								title="{b.patient_name ?? 'Patient'} — {b.procedure} ({b.start_time}–{b.end_time})"
							>
								<p class="text-[9px] font-black leading-tight truncate" style="color:{isPending ? '#c2410c' : gridText(bi)};">{b.patient_name ?? 'Patient'}</p>
								<p class="text-[8px] leading-tight truncate" style="color:{isPending ? '#c2410c' : gridText(bi)};">{b.procedure}</p>
								{#if isPending}
									<p class="text-[8px] font-bold text-orange-600">PENDING</p>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
	{/if}
</div>

<!-- Backdrop for filter -->
{#if filterOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-10" onclick={() => filterOpen = false} onkeydown={(e) => { if (e.key === 'Escape') filterOpen = false; }}></div>
{/if}
