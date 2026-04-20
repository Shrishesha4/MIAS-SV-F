<script lang="ts">
	import { onMount } from 'svelte';
	import { otApi, type OTTheater, type OTBooking, type OTSchedule } from '$lib/api/ot';
	import { toastStore } from '$lib/stores/toast';
	import { Filter, LayoutGrid, LayoutList, Minimize2, ChevronLeft, ChevronRight, X } from 'lucide-svelte';

	interface Props {
		patientId?: string;
		patientName?: string;
		onclose: () => void;
		onbook?: (prefill: { theater_id: string; date: string; start_time: string; end_time: string }) => void;
	}

	let { patientId, patientName, onclose, onbook }: Props = $props();

	type ScheduleMode = 'wall' | 'grid';
	let scheduleMode = $state<ScheduleMode>('wall');
	let schedule = $state<OTSchedule | null>(null);
	let loading = $state(false);
	let filterOpen = $state(false);
	let selectedTheaterIds = $state<Set<string>>(new Set());
	let density = $state(5);

	function todayISO() {
		return new Date().toISOString().split('T')[0];
	}
	let anchorDate = $state(todayISO());

	const visibleTheaters = $derived(
		schedule?.theaters.filter(t => selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id)) ?? []
	);
	const weekDates = $derived(schedule?.week_dates ?? []);

	const totalSurgeries = $derived(
		(schedule?.bookings ?? []).filter(b => b.date === anchorDate && b.status !== 'CANCELLED').length
	);

	async function loadSchedule(date?: string) {
		loading = true;
		try {
			schedule = await otApi.getSchedule(date ?? anchorDate);
		} catch {
			toastStore.addToast('Failed to load OT schedule', 'error');
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

	function fmtDay(iso: string) {
		const d = new Date(iso + 'T00:00:00');
		return { day: d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(), num: d.getDate() };
	}

	function bookingsForTheaterDay(theaterId: string) {
		return (schedule?.bookings ?? [])
			.filter(b => b.theater_id === theaterId && b.date === anchorDate && b.status !== 'CANCELLED')
			.sort((a, b) => a.start_time.localeCompare(b.start_time));
	}

	const OP_START = 8 * 60;  // 08:00
	const OP_END   = 20 * 60; // 20:00

	function toMins(t: string) {
		const [h, m] = t.split(':').map(Number);
		return h * 60 + m;
	}
	function fmtMins(m: number) {
		const h = Math.floor(m / 60);
		const min = m % 60;
		return `${h}:${min.toString().padStart(2, '0')}`;
	}

	type SlotBooking = { type: 'booking'; booking: OTBooking };
	type SlotAvailable = { type: 'available'; start: string; end: string };
	type Slot = SlotBooking | SlotAvailable;

	function computeSlots(theaterId: string): Slot[] {
		const bks = bookingsForTheaterDay(theaterId);
		const slots: Slot[] = [];
		let cursor = OP_START;
		for (const b of bks) {
			const bStart = toMins(b.start_time);
			const bEnd   = toMins(b.end_time);
			if (bStart > cursor) slots.push({ type: 'available', start: fmtMins(cursor), end: fmtMins(bStart) });
			slots.push({ type: 'booking', booking: b });
			cursor = bEnd;
		}
		if (cursor < OP_END) slots.push({ type: 'available', start: fmtMins(cursor), end: fmtMins(OP_END) });
		return slots;
	}

	const STATUS_COLORS: Record<string, string> = {
		SCHEDULED:   '#3b82f6',
		CONFIRMED:   '#22c55e',
		IN_PROGRESS: '#f97316',
		COMPLETED:   '#6b7280',
		CANCELLED:   '#ef4444',
	};

	// Grid view hour columns (08:00 – 20:00 based on density)
	const GRID_HOURS = $derived.by(() => {
		const step = Math.max(1, Math.round(10 / density));
		const hrs: string[] = [];
		for (let h = 8; h <= 19; h += step) hrs.push(`${h}:00`);
		return hrs;
	});

	const TOTAL_MINS = OP_END - OP_START; // 720

	function gridBookingStyle(b: OTBooking) {
		const start = toMins(b.start_time);
		const end   = toMins(b.end_time);
		const left  = ((start - OP_START) / TOTAL_MINS) * 100;
		const width = ((end - start) / TOTAL_MINS) * 100;
		return `left:${left.toFixed(2)}%; width:${width.toFixed(2)}%; position:absolute; top:3px; bottom:3px;`;
	}

	const GRID_COLORS = ['#dcfce7', '#fef9c3', '#dbeafe', '#fce7f3', '#ede9fe', '#ffedd5', '#f0fdf4'];
	function gridColor(idx: number) { return GRID_COLORS[idx % GRID_COLORS.length]; }
	const GRID_TEXT_COLORS = ['#166534', '#854d0e', '#1e3a8a', '#9d174d', '#5b21b6', '#7c2d12', '#14532d'];
	function gridTextColor(idx: number) { return GRID_TEXT_COLORS[idx % GRID_TEXT_COLORS.length]; }

	onMount(() => loadSchedule());
</script>

<!-- fullscreen overlay -->
<div
	class="fixed inset-0 z-[9999] flex flex-col overflow-hidden"
	style="background: #f1f5f9;"
>
	<!-- ── Top bar ──────────────────────────────────────────────────────── -->
	<div class="flex items-center justify-between px-6 py-3 shrink-0" style="background:#f1f5f9; border-bottom: 1px solid #e2e8f0;">
		<div>
			<p class="text-sm font-black uppercase tracking-widest text-slate-800">
				OT SCHEDULE — {schedule?.theaters.length ?? 0} OPERATORIES
			</p>
			<p class="text-xs font-semibold text-blue-600">
				Showing {totalSurgeries} surgeries for {anchorDate}
			</p>
		</div>

		<div class="flex items-center gap-3">
			{#if scheduleMode === 'wall'}
			<!-- Filter -->
			<div class="relative">
				<button
					onclick={() => filterOpen = !filterOpen}
					class="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer hover:bg-slate-50"
				>
					<Filter class="h-3.5 w-3.5" />
					FILTER OTs ({selectedTheaterIds.size > 0 ? selectedTheaterIds.size : (schedule?.theaters.length ?? 0)})
				</button>
				{#if filterOpen}
				<div class="absolute right-0 top-full mt-1 z-10 w-52 rounded-xl border border-slate-200 bg-white p-2 shadow-xl">
					<p class="mb-1.5 px-1 text-[10px] font-bold uppercase text-slate-400">Filter by OT Room</p>
					{#each schedule?.theaters ?? [] as t}
					<label class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50">
						<input type="checkbox"
							checked={selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id)}
							onchange={() => {
								const s = new Set(selectedTheaterIds);
								if (s.size === 0) {
									(schedule?.theaters ?? []).forEach(x => s.add(x.id));
									s.delete(t.id);
								} else if (s.has(t.id)) {
									s.delete(t.id);
									if (s.size === (schedule?.theaters.length ?? 0)) selectedTheaterIds = new Set();
									else selectedTheaterIds = s; return;
								} else {
									s.add(t.id);
									if (s.size === (schedule?.theaters.length ?? 0)) selectedTheaterIds = new Set();
									else selectedTheaterIds = s; return;
								}
								selectedTheaterIds = s.size === (schedule?.theaters.length ?? 0) ? new Set() : s;
							}}
							class="rounded"
						/>
						<span class="text-xs text-slate-700">{t.ot_id}{t.name ? ` — ${t.name}` : ''}</span>
					</label>
					{/each}
				</div>
				{/if}
			</div>

			<!-- Density -->
			<div class="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5">
				<span class="text-[10px] font-bold uppercase text-slate-400">DENSITY</span>
				<input type="range" min="1" max="10" bind:value={density} class="w-20 cursor-pointer accent-blue-600" />
				<span class="w-3 text-center text-xs font-bold text-slate-700">{density}</span>
			</div>
			{/if}

			<!-- GRID / WALL toggle -->
			<div class="flex rounded-xl border border-slate-200 bg-white overflow-hidden">
				<button
					onclick={() => scheduleMode = 'grid'}
					class="px-3 py-1.5 text-xs font-bold uppercase tracking-wide cursor-pointer transition-colors {scheduleMode === 'grid' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'}"
				>GRID</button>
				<button
					onclick={() => scheduleMode = 'wall'}
					class="px-3 py-1.5 text-xs font-bold uppercase tracking-wide cursor-pointer transition-colors {scheduleMode === 'wall' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'}"
				>WALL</button>
			</div>

			<!-- Minimize / close -->
			<button onclick={onclose} class="rounded-xl border border-slate-200 bg-white p-1.5 cursor-pointer hover:bg-slate-50 text-slate-500">
				<Minimize2 class="h-4 w-4" />
			</button>
		</div>
	</div>

	<!-- ── Week date strip ───────────────────────────────────────────────── -->
	<div class="flex shrink-0 items-center gap-2 px-6 py-3" style="background:#f1f5f9;">
		<button onclick={prevWeek} class="rounded-full p-1 hover:bg-slate-200 cursor-pointer text-slate-500"><ChevronLeft class="h-4 w-4"/></button>
		<div class="flex flex-1 gap-2 overflow-x-auto">
			{#each weekDates as d}
				{@const f = fmtDay(d)}
				<button
					onclick={() => selectDay(d)}
					class="flex-1 min-w-[80px] flex flex-col items-center py-2.5 rounded-xl cursor-pointer transition-colors text-center {d === anchorDate ? 'text-white' : 'text-slate-700 bg-white border border-slate-200 hover:bg-slate-50'}"
					style={d === anchorDate ? 'background: linear-gradient(to bottom,#3b82f6,#2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);' : ''}
				>
					<span class="text-[10px] font-bold uppercase tracking-widest opacity-80">{f.day}</span>
					<span class="text-xl font-black leading-none">{f.num}</span>
				</button>
			{/each}
		</div>
		<button onclick={nextWeek} class="rounded-full p-1 hover:bg-slate-200 cursor-pointer text-slate-500"><ChevronRight class="h-4 w-4"/></button>
	</div>

	<!-- ── Content ──────────────────────────────────────────────────────── -->
	{#if loading}
		<div class="flex flex-1 items-center justify-center">
			<div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
		</div>
	{:else if scheduleMode === 'wall'}
	<!-- ════ WALL VIEW ════ -->
	<div class="flex flex-1 gap-4 overflow-x-auto overflow-y-auto px-6 pb-2 pt-1 min-h-0">
		{#each visibleTheaters as theater}
			{@const slots = computeSlots(theater.id)}
			{@const bkCount = slots.filter(s => s.type === 'booking').length}
			<div class="flex w-[240px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-white overflow-hidden" style="box-shadow: 0 1px 4px rgba(0,0,0,0.06);">
				<!-- OT header -->
				<div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
					<span class="text-sm font-black text-slate-800">{theater.ot_id}</span>
					<span class="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-[10px] font-black text-white">{bkCount}</span>
				</div>
				<!-- Slots -->
				<div class="flex flex-col gap-2 overflow-y-auto p-3">
					{#each slots as slot}
						{#if slot.type === 'booking'}
							{@const b = slot.booking}
							<div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2.5 space-y-1" style="box-shadow:0 1px 3px rgba(0,0,0,0.05);">
								<div class="flex items-center justify-between">
									<span class="text-[11px] font-bold text-slate-800">{b.patient_name ?? 'Patient'}</span>
									<span class="rounded-full px-2 py-0.5 text-[9px] font-black uppercase tracking-wide text-white"
										style="background:{STATUS_COLORS[b.status] ?? '#6b7280'};">{b.status.replace('_', ' ')}</span>
								</div>
								<p class="text-[10px] text-slate-500">{b.procedure}</p>
								<div class="flex items-center justify-between">
									<span class="text-[10px] font-bold text-blue-600">{b.start_time} – {b.end_time}</span>
									<span class="text-[9px] text-slate-400">Dr. {b.doctor_name.split(' ').slice(-1)[0]}</span>
								</div>
							</div>
						{:else}
							<!-- Available slot -->
							<button
								onclick={() => onbook?.({ theater_id: theater.id, date: anchorDate, start_time: slot.start, end_time: slot.end })}
								class="w-full cursor-pointer rounded-xl border-2 border-dashed border-red-300 bg-red-50 px-3 py-3 text-center hover:bg-red-100 transition-colors"
							>
								<div class="flex items-center justify-between mb-1">
									<span class="text-[10px] font-bold text-red-500">{slot.start} – {slot.end}</span>
									<span class="rounded-full bg-red-500 px-2 py-0.5 text-[9px] font-black text-white">BOOK NOW +</span>
								</div>
								<p class="text-[9px] font-bold uppercase tracking-widest text-red-400">AVAILABLE SLOT</p>
							</button>
						{/if}
					{/each}
				</div>
			</div>
		{/each}
	</div>

	{:else}
	<!-- ════ GRID VIEW ════ -->
	<div class="flex-1 overflow-auto px-4 pb-2 min-h-0">
		<div class="min-w-[900px]">
			<!-- Header row: ROOM + hour labels -->
			<div class="flex sticky top-0 z-10" style="background:#f1f5f9;">
				<div class="w-20 shrink-0 py-2 pr-2 text-[10px] font-black uppercase tracking-widest text-slate-400 text-center">ROOM</div>
				<div class="relative flex-1 flex border-l border-slate-200">
					{#each Array.from({length: 12}, (_, i) => i + 8) as h}
						<div class="flex-1 py-2 text-center text-[10px] font-bold text-slate-500 border-r border-slate-200">
							{h}:00
						</div>
					{/each}
				</div>
			</div>
			<!-- OT rows -->
			{#each visibleTheaters as theater, ti}
				{@const bks = bookingsForTheaterDay(theater.id)}
				<div class="flex border-t border-slate-200">
					<!-- Room label -->
					<div class="w-20 shrink-0 flex items-center justify-center py-3 pr-2 text-[11px] font-black text-slate-700 text-center">{theater.ot_id}</div>
					<!-- Timeline -->
					<div class="relative flex-1 h-16 border-l border-slate-200">
						<!-- Hour grid lines -->
						{#each Array.from({length: 13}, (_, i) => i) as i}
							<div class="absolute top-0 bottom-0 border-r border-slate-100" style="left:{(i / 12 * 100).toFixed(2)}%;"></div>
						{/each}
						<!-- Booking cells -->
						{#each bks as b, bi}
							<div
								class="absolute rounded-lg border px-2 py-1 overflow-hidden cursor-pointer hover:opacity-90"
								style="{gridBookingStyle(b)} background:{gridColor(bi)}; border-color:{gridTextColor(bi)}40;"
								title="{b.patient_name} — {b.procedure} ({b.start_time}–{b.end_time})"
							>
								<p class="text-[10px] font-black leading-tight truncate" style="color:{gridTextColor(bi)};">{b.patient_name ?? 'Patient'}</p>
								<p class="text-[9px] leading-tight truncate" style="color:{gridTextColor(bi)};">{b.procedure}</p>
								<p class="text-[9px] leading-tight" style="color:{gridTextColor(bi)};">{b.start_time}–{b.end_time}</p>
								<p class="absolute bottom-1 right-1.5 text-[8px] font-bold uppercase" style="color:{gridTextColor(bi)};">
									{b.doctor_name.split(' ').slice(-1)[0]}
								</p>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	</div>
	{/if}

	<!-- ── Bottom close button ───────────────────────────────────────────── -->
	<div class="flex shrink-0 justify-center py-4">
		<button
			onclick={onclose}
			class="rounded-full px-10 py-2.5 text-sm font-black uppercase tracking-widest text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 16px rgba(37,99,235,0.4);"
		>CLOSE CALENDAR</button>
	</div>
</div>

<!-- Backdrop for filter popover -->
{#if filterOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-[9998]" onclick={() => filterOpen = false} onkeydown={(e) => { if (e.key === 'Escape') filterOpen = false; }}></div>
{/if}
