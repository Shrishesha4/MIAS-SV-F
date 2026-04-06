<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi } from '$lib/api/faculty';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Calendar, Clock, MapPin, Users, Coffee, BookOpen, Plus, Trash2, Edit, ChevronLeft, ChevronRight } from 'lucide-svelte';

	let scheduleItems: any[] = $state([]);
	let loading = $state(true);
	let faculty: any = $state(null);

	// Date navigation
	let selectedDate = $state(new Date());

	const formattedDate = $derived(
		selectedDate.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
	);

	function changeDate(offset: number) {
		const newDate = new Date(selectedDate);
		newDate.setDate(newDate.getDate() + offset);
		selectedDate = newDate;
	}

	// Create modal state
	let showCreateModal = $state(false);
	let createLoading = $state(false);
	let newTitle = $state('');
	let newType = $state('Clinical');
	let newTimeStart = $state('');
	let newTimeEnd = $state('');
	let newLocation = $state('');

	const scheduleTypes = ['Clinical', 'Lecture', 'Review', 'Office Hours', 'Break'];

	function getTypeColor(type: string): string {
		switch (type) {
			case 'Clinical': return '#ef4444';
			case 'Lecture': return '#3b82f6';
			case 'Review': return '#8b5cf6';
			case 'Office Hours': return '#22c55e';
			case 'Break': return '#9ca3af';
			default: return '#6b7280';
		}
	}

	function getStatusVariant(status: string): 'success' | 'info' | 'pending' | 'warning' {
		switch (status) {
			case 'Completed': return 'success';
			case 'In Progress': return 'info';
			default: return 'pending';
		}
	}

	async function loadSchedule() {
		if (!faculty) return;
		try {
			loading = true;
			scheduleItems = await facultyApi.getSchedule(faculty.id);
		} catch (err) {
			toastStore.addToast('Failed to load schedule', 'error');
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		newTitle = '';
		newType = 'Clinical';
		newTimeStart = '';
		newTimeEnd = '';
		newLocation = '';
		showCreateModal = true;
	}

	async function handleCreate() {
		if (!newTitle.trim() || !newTimeStart || !newTimeEnd) {
			toastStore.addToast('Please fill in all required fields', 'warning');
			return;
		}
		createLoading = true;
		try {
			await facultyApi.createScheduleItem(faculty.id, {
				title: newTitle.trim(),
				type: newType,
				time_start: newTimeStart,
				time_end: newTimeEnd,
				location: newLocation.trim(),
				date: selectedDate.toISOString().split('T')[0],
			});
			toastStore.addToast('Schedule item created', 'success');
			showCreateModal = false;
			await loadSchedule();
		} catch (err) {
			toastStore.addToast('Failed to create schedule item', 'error');
		} finally {
			createLoading = false;
		}
	}

	async function handleDelete(item: any) {
		if (!confirm(`Delete "${item.title}"?`)) return;
		try {
			await facultyApi.deleteScheduleItem(faculty.id, item.id);
			toastStore.addToast('Schedule item deleted', 'success');
			await loadSchedule();
		} catch (err) {
			toastStore.addToast('Failed to delete schedule item', 'error');
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['FACULTY'])) return;
		try {
			faculty = await facultyApi.getMe();
			scheduleItems = await facultyApi.getSchedule(faculty.id);
		} catch (err) {
			toastStore.addToast('Failed to load schedule', 'error');
		} finally {
			loading = false;
		}
	});

	// Reload schedule when date changes
	$effect(() => {
		// Subscribe to selectedDate
		const _date = selectedDate;
		if (faculty) {
			loadSchedule();
		}
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading && !faculty}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	<!-- Header -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2 w-full">
				<Calendar class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Schedule
				</h2>
			</div>
		{/snippet}

		<!-- Date navigation -->
		<div class="flex items-center justify-between">
			<button
				class="p-1.5 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors"
				style="border: 1px solid rgba(0,0,0,0.08);"
				onclick={() => changeDate(-1)}
			>
				<ChevronLeft class="w-4 h-4 text-blue-600" />
			</button>
			<p class="text-sm text-gray-700 font-medium">{formattedDate}</p>
			<button
				class="p-1.5 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors"
				style="border: 1px solid rgba(0,0,0,0.08);"
				onclick={() => changeDate(1)}
			>
				<ChevronRight class="w-4 h-4 text-blue-600" />
			</button>
		</div>
	</AquaCard>

	<!-- Schedule Items -->
	{#if loading}
		<div class="flex items-center justify-center py-10">
			<div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		{#each scheduleItems as item}
			<AquaCard padding={false}>
				<div class="flex items-stretch">
					<!-- Color bar -->
					<div class="w-1 shrink-0 rounded-l-[10px]" style="background-color: {getTypeColor(item.type || 'Clinical')};"></div>

					<div class="flex-1 px-4 py-3">
						<div class="flex items-center justify-between mb-1">
							<p class="text-sm font-semibold text-gray-800">{item.title}</p>
							<div class="flex items-center gap-2">
								{#if item.status}
									<StatusBadge variant={getStatusVariant(item.status)}>{item.status}</StatusBadge>
								{/if}
								<button
									class="p-1 rounded-md cursor-pointer hover:bg-red-50 transition-colors"
									onclick={() => handleDelete(item)}
									title="Delete"
								>
									<Trash2 class="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
								</button>
							</div>
						</div>

						<div class="flex items-center gap-3 text-xs text-gray-500">
							{#if item.time_start || item.time}
								<span class="flex items-center gap-1">
									<Clock class="w-3 h-3" />
									{item.time_start && item.time_end ? `${item.time_start} - ${item.time_end}` : item.time}
								</span>
							{/if}
							{#if item.location}
								<span class="flex items-center gap-1">
									<MapPin class="w-3 h-3" />
									{item.location}
								</span>
							{/if}
						</div>

						{#if item.students && item.students > 0}
							<div class="flex items-center gap-1 mt-1.5 text-[10px] text-gray-400">
								<Users class="w-3 h-3" />
								{item.students} {item.students === 1 ? 'student' : 'students'}
							</div>
						{/if}
					</div>
				</div>
			</AquaCard>
		{/each}

		{#if scheduleItems.length === 0}
			<div class="text-center py-12">
				<Calendar class="w-10 h-10 text-gray-300 mx-auto mb-2" />
				<p class="text-sm text-gray-400">No schedule items for this day</p>
			</div>
		{/if}
	{/if}
	{/if}
</div>

<!-- Floating Action Button -->
<button
	class="fixed bottom-20 right-4 w-14 h-14 rounded-full flex items-center justify-center cursor-pointer shadow-lg z-40"
	style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
	       box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);"
	onclick={openCreateModal}
>
	<Plus class="w-6 h-6 text-white" />
</button>

<!-- Create Schedule Item Modal -->
<AquaModal open={showCreateModal} title="New Schedule Item" onclose={() => showCreateModal = false}>
	<form class="space-y-4" onsubmit={(e) => { e.preventDefault(); handleCreate(); }}>
		<!-- Title -->
		<div>
			<label for="sched-title" class="block text-xs font-semibold text-gray-600 mb-1">Title *</label>
			<input
				id="sched-title"
				type="text"
				bind:value={newTitle}
				placeholder="e.g. Morning Clinical Round"
				class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
			/>
		</div>

		<!-- Type -->
		<div>
			<label for="sched-type" class="block text-xs font-semibold text-gray-600 mb-1">Type</label>
			<select
				id="sched-type"
				bind:value={newType}
				class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-300 bg-white"
			>
				{#each scheduleTypes as sType}
					<option value={sType}>{sType}</option>
				{/each}
			</select>
		</div>

		<!-- Time Start / End -->
		<div class="grid grid-cols-2 gap-3">
			<div>
				<label for="sched-start" class="block text-xs font-semibold text-gray-600 mb-1">Start Time *</label>
				<input
					id="sched-start"
					type="time"
					bind:value={newTimeStart}
					class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
				/>
			</div>
			<div>
				<label for="sched-end" class="block text-xs font-semibold text-gray-600 mb-1">End Time *</label>
				<input
					id="sched-end"
					type="time"
					bind:value={newTimeEnd}
					class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
				/>
			</div>
		</div>

		<!-- Location -->
		<div>
			<label for="sched-location" class="block text-xs font-semibold text-gray-600 mb-1">Location</label>
			<input
				id="sched-location"
				type="text"
				bind:value={newLocation}
				placeholder="e.g. Ward 3, Room 201"
				class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
			/>
		</div>

		<!-- Actions -->
		<div class="flex gap-3 pt-2">
			<button
				type="button"
				class="flex-1 py-2.5 rounded-xl text-sm font-semibold cursor-pointer"
				style="background: #e5e7eb; color: #64748b; border: 1px solid rgba(0,0,0,0.1);"
				onclick={() => showCreateModal = false}
			>
				Cancel
			</button>
			<button
				type="submit"
				class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white cursor-pointer disabled:opacity-50"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);
				       box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
				       border: 1px solid rgba(255,255,255,0.2);"
				disabled={createLoading}
			>
				{createLoading ? 'Creating...' : 'Create'}
			</button>
		</div>
	</form>
</AquaModal>
