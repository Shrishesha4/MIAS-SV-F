<script lang="ts">
	import { onMount } from 'svelte';
	import { otApi, type OTTheater, type OTBooking, type OTSchedule } from '$lib/api/ot';
	import { toastStore } from '$lib/stores/toast';
	import { ArrowLeft, LayoutGrid, LayoutList, Filter, ChevronLeft, ChevronRight, Loader2, Calendar } from 'lucide-svelte';
	import OTScheduleFullscreen from '$lib/components/case-records/OTScheduleFullscreen.svelte';
	import DoctorSelect from '$lib/components/ui/DoctorSelect.svelte';

	interface Props {
		patientId: string;
		patientName: string;
		onbooked?: (booking: OTBooking) => void;
	}

	let { patientId, patientName, onbooked }: Props = $props();

	type OTView = 'form' | 'schedule';
	let view = $state<OTView>('form');
	let showFullscreenSchedule = $state(false);
	type ScheduleMode = 'wall' | 'grid';
	let scheduleMode = $state<ScheduleMode>('wall');

	let theaters = $state<OTTheater[]>([]);
	let selectedTheaterIds = $state<Set<string>>(new Set());
	let schedule = $state<OTSchedule | null>(null);
	let scheduleLoading = $state(false);
	let anchorDate = $state(todayISO());
	let filterOpen = $state(false);

	let form = $state({
		theater_id: '',
		from_date: todayISO(),
		to_date: todayISO(),
		start_time: '',
		end_time: '',
		procedure: '',
		doctor_name: '',
		notes: '',
	});
	let submitting = $state(false);

	function todayISO() {
		return new Date().toISOString().split('T')[0];
	}

	const PROCEDURES = [
		'Appendectomy', 'Cholecystectomy', 'Hernia Repair', 'Total Hip Replacement',
		'Total Knee Replacement', 'Coronary Bypass', 'Mastectomy', 'Tonsillectomy',
		'Septoplasty', 'Cataract Surgery', 'Knee Arthroscopy', 'Thyroidectomy',
		'Laparoscopy', 'Hysterectomy', 'Prostatectomy', 'Spinal Fusion',
	].sort();

	function bookingCoversDate(booking: OTBooking, targetDate: string): boolean {
		const start = booking.from_date || booking.date;
		const end = booking.to_date || start;
		return start <= targetDate && end >= targetDate;
	}

	const visibleTheaters = $derived(
		schedule?.theaters.filter(t => selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id)) ?? []
	);
	const weekDates = $derived(schedule?.week_dates ?? []);
	const GRID_HOURS = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, '0')}:00`);

	function shortDay(iso: string) {
		const d = new Date(iso + 'T00:00:00');
		return {
			day: d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(),
			num: d.getDate(),
		};
	}

	function isTodayDate(iso: string) { return iso === todayISO(); }

	function getBookingsForTheaterDate(theaterId: string, date: string): OTBooking[] {
		return (schedule?.bookings ?? [])
			.filter(b => b.theater_id === theaterId && bookingCoversDate(b, date) && b.status !== 'CANCELLED')
			.sort((a, b) => a.start_time.localeCompare(b.start_time));
	}

	function computeSlots(bookings: OTBooking[]): Array<
		{ type: 'booking'; data: OTBooking } | { type: 'slot'; start: string; end: string }
	> {
		const result: Array<{ type: 'booking'; data: OTBooking } | { type: 'slot'; start: string; end: string }> = [];
		let cursor = '00:00';
		const DAY_END = '23:59';
		for (const b of bookings) {
			if (b.start_time > cursor) result.push({ type: 'slot', start: cursor, end: b.start_time });
			result.push({ type: 'booking', data: b });
			cursor = b.end_time;
		}
		if (cursor < DAY_END) result.push({ type: 'slot', start: cursor, end: DAY_END });
		return result;
	}

	function statusColor(status: string) {
		switch (status) {
			case 'CONFIRMED': return { bg: '#dcfce7', border: '#86efac', text: '#15803d', label: 'CONFIRMED' };
			case 'IN_PROGRESS': return { bg: '#fef3c7', border: '#fcd34d', text: '#b45309', label: 'IN PROGRESS' };
			case 'SCHEDULED': return { bg: '#dbeafe', border: '#93c5fd', text: '#1d4ed8', label: 'SCHEDULED' };
			case 'COMPLETED': return { bg: '#f3f4f6', border: '#d1d5db', text: '#6b7280', label: 'COMPLETED' };
			default: return { bg: '#f3f4f6', border: '#d1d5db', text: '#6b7280', label: status };
		}
	}

	async function loadSchedule(date?: string) {
		scheduleLoading = true;
		try {
			schedule = await otApi.getSchedule(date ?? anchorDate);
		} catch {
			toastStore.addToast('Failed to load OT schedule', 'error');
		} finally {
			scheduleLoading = false;
		}
	}

	function shiftWeek(dir: 1 | -1) {
		const d = new Date(anchorDate + 'T00:00:00');
		d.setDate(d.getDate() + dir * 7);
		anchorDate = d.toISOString().split('T')[0];
		loadSchedule(anchorDate);
	}

	function prefillFromSlot(theater: OTTheater, start: string, end: string) {
		form.theater_id = theater.id;
		form.from_date = anchorDate;
		form.to_date = anchorDate;
		form.start_time = start;
		form.end_time = end;
		view = 'form';
	}

	async function submit() {
		if (!form.theater_id || !form.from_date || !form.to_date || !form.start_time || !form.end_time || !form.procedure || !form.doctor_name) {
			toastStore.addToast('Fill all required fields', 'error');
			return;
		}
		if (form.to_date < form.from_date) {
			toastStore.addToast('To date cannot be before from date', 'error');
			return;
		}
		if (form.start_time >= form.end_time) {
			toastStore.addToast('End time must be after start time', 'error');
			return;
		}
		submitting = true;
		try {
			const booking = await otApi.createBooking({
				theater_id: form.theater_id,
				patient_id: patientId,
				from_date: form.from_date,
				to_date: form.to_date,
				start_time: form.start_time,
				end_time: form.end_time,
				procedure: form.procedure,
				doctor_name: form.doctor_name,
				notes: form.notes || undefined,
			});
			toastStore.addToast('OT booking submitted', 'success');
			onbooked?.(booking);
			form = { theater_id: '', from_date: todayISO(), to_date: todayISO(), start_time: '', end_time: '', procedure: '', doctor_name: '', notes: '' };
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to submit booking', 'error');
		} finally {
			submitting = false;
		}
	}

	onMount(async () => {
		theaters = await otApi.getActiveTheaters().catch(() => []);
	});
</script>

{#if view === 'form'}
<!-- ── New Surgery Request form ─────────────────────────────────── -->
<div class="flex items-center justify-between mb-4">
	<p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">New Surgery Request</p>
	<button
		onclick={() => showFullscreenSchedule = true}
		class="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-500 hover:bg-slate-50 cursor-pointer"
	>
		<Calendar class="h-3.5 w-3.5" />
		View OT Schedule
	</button>
</div>

<div class="rounded-2xl border border-slate-200 bg-white p-4 space-y-4">
	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">OT Room *</label>
		<div class="relative">
			<select bind:value={form.theater_id}
				class="block w-full appearance-none rounded-xl border border-slate-200 px-3 py-2.5 pr-8 text-sm text-slate-800 cursor-pointer"
				style="background: #fafcff;">
				<option value="">Select OT Room</option>
				{#each theaters as t}
					<option value={t.id}>{t.ot_id}{t.name ? ` — ${t.name}` : ''}{t.location ? ` (${t.location})` : ''}</option>
				{/each}
			</select>
			<ChevronRight class="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 rotate-90 text-slate-400" />
		</div>
	</div>

	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">From Date *</label>
		<input type="date" bind:value={form.from_date}
			class="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800"
			style="background: #fafcff;" />
	</div>

	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">To Date *</label>
		<input type="date" bind:value={form.to_date}
			class="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800"
			style="background: #fafcff;" />
	</div>

	<div class="grid grid-cols-2 gap-3">
		<div>
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">From Time *</label>
			<input
				type="time"
				bind:value={form.start_time}
				step="1800"
				class="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800"
				style="background: #fafcff;"
			/>
		</div>
		<div>
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">To Time *</label>
			<input
				type="time"
				bind:value={form.end_time}
				step="1800"
				class="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800"
				style="background: #fafcff;"
			/>
		</div>
	</div>

	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">Procedure *</label>
		<div class="relative">
			<select bind:value={form.procedure}
				class="block w-full appearance-none rounded-xl border border-slate-200 px-3 py-2.5 pr-8 text-sm text-slate-800 cursor-pointer"
				style="background: #fafcff;">
				<option value="">Select Procedure</option>
				{#each PROCEDURES as p}
					<option value={p}>{p}</option>
				{/each}
			</select>
			<ChevronRight class="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 rotate-90 text-slate-400" />
		</div>
	</div>

	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">Surgeon / Doctor *</label>
		<DoctorSelect bind:value={form.doctor_name} placeholder="Select Surgeon" />
	</div>

	<div>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<label class="block text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">Special Requirements / Notes</label>
		<textarea rows={3} placeholder="E.g. C-arm, specific instruments…" bind:value={form.notes}
			class="block w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800 resize-none"
			style="background: #fafcff;"></textarea>
	</div>
</div>

{#if patientName}
	<div class="mt-3 rounded-xl border border-blue-100 bg-blue-50/70 px-3 py-2 text-xs text-blue-800">
		<span class="font-semibold">Patient:</span> {patientName}
	</div>
{/if}

<div class="mt-4 flex items-center justify-between">
	<div></div>
	<button
		onclick={submit}
		disabled={submitting || !patientId}
		class="flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-bold text-white disabled:opacity-50 cursor-pointer"
		style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 2px 8px rgba(0,102,204,0.25);"
	>
		{#if submitting}<Loader2 class="h-4 w-4 animate-spin" />{/if}
		Send for Approval
	</button>
</div>

{:else}
<!-- ── OT Schedule ──────────────────────────────────────────────── -->
<div class="flex items-center justify-between mb-3">
	<button onclick={() => view = 'form'}
		class="flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 cursor-pointer">
		<ArrowLeft class="h-3.5 w-3.5" />
		BACK TO BOOKING
	</button>
	<button
		onclick={() => { form.theater_id = ''; form.from_date = anchorDate; form.to_date = anchorDate; form.start_time = ''; form.end_time = ''; view = 'form'; }}
		class="rounded-xl px-3 py-1.5 text-xs font-bold text-white cursor-pointer"
		style="background: linear-gradient(to bottom, #4d90fe, #0066cc);">
		NEW BOOKING
	</button>
</div>

<div class="flex items-start justify-between gap-2 mb-3">
	<div>
		<p class="text-xs font-bold text-slate-700">OT SCHEDULE — {schedule?.theaters.length ?? 0} OPERATORIES</p>
		{#if schedule}
			<p class="text-xs font-bold text-blue-600">
				Showing {schedule.bookings.filter(b => bookingCoversDate(b, anchorDate)).length} surgeries for {anchorDate}
			</p>
		{/if}
	</div>
	<div class="flex items-center gap-1.5 shrink-0">
		<!-- Filter -->
		<div class="relative">
			<button onclick={() => { filterOpen = !filterOpen; }}
				class="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold text-slate-600 cursor-pointer hover:bg-slate-50">
				<Filter class="h-3 w-3" />
				FILTER OTs ({selectedTheaterIds.size > 0 ? selectedTheaterIds.size : (schedule?.theaters.length ?? 0)})
			</button>
			{#if filterOpen}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="absolute right-0 top-full mt-1 z-50 w-52 rounded-2xl border border-slate-200 bg-white p-3 shadow-2xl"
					onclick={(e) => e.stopPropagation()}
					onkeydown={() => {}}
				>
					<div class="flex items-center justify-between mb-2">
						<span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Select Rooms</span>
						<button onclick={() => { selectedTheaterIds = new Set(); filterOpen = false; }}
							class="text-[10px] font-bold text-blue-600 cursor-pointer">NONE</button>
					</div>
					<div class="grid grid-cols-2 gap-1.5 max-h-48 overflow-y-auto">
						{#each schedule?.theaters ?? [] as t}
							{@const sel = selectedTheaterIds.size === 0 || selectedTheaterIds.has(t.id)}
							<button
								onclick={() => {
									const s = new Set(selectedTheaterIds.size === 0
										? (schedule?.theaters ?? []).map(x => x.id)
										: selectedTheaterIds);
									if (s.has(t.id)) s.delete(t.id); else s.add(t.id);
									if (s.size === (schedule?.theaters.length ?? 0)) selectedTheaterIds = new Set();
									else selectedTheaterIds = s;
								}}
								class="rounded-xl px-2 py-1.5 text-xs font-bold cursor-pointer transition-colors"
								style="background: {sel ? '#2563eb' : '#f1f5f9'}; color: {sel ? 'white' : '#475569'};"
							>{t.ot_id}</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
		<!-- Grid / Wall -->
		<div class="flex overflow-hidden rounded-xl border border-slate-200 bg-white">
			<button onclick={() => scheduleMode = 'grid'}
				class="px-2.5 py-1.5 cursor-pointer transition-colors {scheduleMode === 'grid' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'}">
				<LayoutGrid class="h-3.5 w-3.5" />
			</button>
			<button onclick={() => scheduleMode = 'wall'}
				class="px-2.5 py-1.5 cursor-pointer transition-colors {scheduleMode === 'wall' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'}">
				<LayoutList class="h-3.5 w-3.5" />
			</button>
		</div>
	</div>
</div>

<!-- Week picker -->
<div class="mb-3 flex items-center gap-1">
	<button onclick={() => shiftWeek(-1)} class="rounded-lg p-1 hover:bg-slate-100 cursor-pointer">
		<ChevronLeft class="h-4 w-4 text-slate-500" />
	</button>
	<div class="flex flex-1 gap-1 overflow-x-auto">
		{#each weekDates as iso}
			{@const { day, num } = shortDay(iso)}
			{@const isToday = isTodayDate(iso)}
			{@const isSel = iso === anchorDate}
			<button
				onclick={() => { anchorDate = iso; }}
				class="flex min-w-[44px] flex-1 flex-col items-center rounded-xl py-1.5 cursor-pointer transition-colors"
				style="background:{isSel?'#2563eb':isToday?'#eff6ff':'white'}; border:1px solid {isSel?'#2563eb':isToday?'#bfdbfe':'#e2e8f0'};"
			>
				<span class="text-[9px] font-bold {isSel ? 'text-white/70' : 'text-slate-400'}">{day}</span>
				<span class="text-sm font-bold {isSel ? 'text-white' : isToday ? 'text-blue-700' : 'text-slate-800'}">{num}</span>
			</button>
		{/each}
	</div>
	<button onclick={() => shiftWeek(1)} class="rounded-lg p-1 hover:bg-slate-100 cursor-pointer">
		<ChevronRight class="h-4 w-4 text-slate-500" />
	</button>
</div>

{#if scheduleLoading}
	<div class="flex justify-center py-10"><Loader2 class="h-6 w-6 animate-spin text-blue-500" /></div>
{:else if !schedule}
	<p class="py-8 text-center text-sm text-slate-400">No data</p>
{:else if scheduleMode === 'wall'}
<!-- Wall view -->
<div class="space-y-3 max-h-[380px] overflow-y-auto pr-0.5">
	{#each visibleTheaters as theater}
		{@const dayBookings = getBookingsForTheaterDate(theater.id, anchorDate)}
		{@const slots = computeSlots(dayBookings)}
		<div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
			<div class="flex items-center gap-2 border-b border-slate-100 px-3 py-2" style="background:#f8fafc;">
				<span class="text-sm font-bold text-slate-800">{theater.ot_id}</span>
				{#if theater.location}<span class="text-xs text-slate-400">· {theater.location}</span>{/if}
				<span class="ml-auto flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
					{dayBookings.length}
				</span>
			</div>
			<div class="divide-y divide-slate-50">
				{#each slots as slot}
					{#if slot.type === 'booking'}
						{@const c = statusColor(slot.data.status)}
						<div class="px-3 py-2.5" style="background:{c.bg}; border-left:3px solid {c.border};">
							<div class="flex items-start justify-between gap-2">
								<div class="min-w-0">
									<p class="text-xs font-bold text-slate-800 truncate">{slot.data.patient_name ?? 'Patient'}</p>
									<p class="text-xs text-slate-600 mt-0.5 truncate">{slot.data.procedure}</p>
								</div>
								<span class="shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-bold"
									style="background:{c.border}22; color:{c.text}; border:1px solid {c.border};">{c.label}</span>
							</div>
							<p class="mt-1 text-[10px] font-semibold text-blue-600">{slot.data.start_time} - {slot.data.end_time}</p>
							<p class="text-[10px] text-slate-400">Dr. {slot.data.doctor_name}</p>
						</div>
					{:else}
						<button
							onclick={() => prefillFromSlot(theater, slot.start, slot.end)}
							class="group w-full cursor-pointer px-3 py-2.5 text-left transition-colors hover:bg-red-50"
							style="border:1.5px dashed #fca5a5; background:#fff5f5;">
							<div class="flex items-center justify-between">
								<p class="text-[10px] font-semibold text-red-400">{slot.start} - {slot.end}</p>
								<span class="rounded-lg px-2 py-1 text-[10px] font-bold text-white transition-transform group-hover:scale-105"
									style="background:#ef4444;">BOOK NOW +</span>
							</div>
							<p class="mt-0.5 text-[10px] font-bold tracking-wider text-red-300">AVAILABLE SLOT</p>
						</button>
					{/if}
				{/each}
			</div>
		</div>
	{/each}
	{#if visibleTheaters.length === 0}
		<p class="py-8 text-center text-sm text-slate-400">No OT rooms to display</p>
	{/if}
</div>

{:else}
<!-- Grid view -->
<div class="max-h-[380px] overflow-auto rounded-2xl border border-slate-200">
	<table class="min-w-max border-collapse text-xs">
		<thead>
			<tr class="sticky top-0 bg-slate-100">
				<th class="sticky left-0 bg-slate-100 px-3 py-2 text-left text-[10px] font-bold uppercase text-slate-500 w-14">ROOM</th>
				{#each GRID_HOURS as hr}
					<th class="min-w-[72px] border-l border-slate-200 px-2 py-2 text-center text-[10px] font-bold text-slate-500">{hr}</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each visibleTheaters as theater}
				{@const dayBookings = getBookingsForTheaterDate(theater.id, anchorDate)}
				<tr class="border-t border-slate-100">
					<td class="sticky left-0 border-r border-slate-100 bg-white px-3 py-2 font-bold text-slate-700">{theater.ot_id}</td>
					{#each GRID_HOURS as hr}
						{@const booking = dayBookings.find(b => b.start_time <= hr && b.end_time > hr)}
						<td class="min-w-[72px] border-l border-slate-100 p-1">
							{#if booking && booking.start_time === hr}
								{@const c = statusColor(booking.status)}
								<div class="rounded-lg p-1.5 text-[9px]" style="background:{c.bg}; border:1px solid {c.border};">
									<p class="font-bold text-slate-700 truncate">{booking.patient_name}</p>
									<p class="truncate text-slate-500">{booking.procedure}</p>
									<p class="font-semibold" style="color:{c.text};">{booking.start_time}-{booking.end_time}</p>
									<p class="text-slate-400">Dr.{booking.doctor_name}</p>
								</div>
							{:else if !booking}
								<button
									onclick={() => prefillFromSlot(theater, hr, `${String(parseInt(hr)+1).padStart(2,'0')}:00`)}
									class="h-full w-full cursor-pointer rounded-lg border border-dashed border-red-200 p-1 text-[9px] font-bold text-red-300 transition-colors hover:bg-red-50"
								>+</button>
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
{/if}

<!-- Send for approval at bottom of schedule view too -->
<div class="mt-4 flex justify-end">
	<button
		onclick={() => view = 'form'}
		class="rounded-xl px-6 py-2.5 text-sm font-bold text-white cursor-pointer"
		style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 2px 8px rgba(0,102,204,0.25); opacity: {patientId ? 1 : 0.5};"
	>
		Send for Approval
	</button>
</div>
{/if}

{#if showFullscreenSchedule}
<OTScheduleFullscreen
	{patientId}
	{patientName}
	onclose={() => showFullscreenSchedule = false}
	onbook={(prefill) => {
		form.theater_id = prefill.theater_id;
		form.from_date = prefill.date;
		form.to_date = prefill.date;
		form.start_time = prefill.start_time;
		form.end_time = prefill.end_time;
		showFullscreenSchedule = false;
	}}
/>
{/if}
