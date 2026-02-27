<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Calendar, Clock, MapPin, Users, Coffee, BookOpen } from 'lucide-svelte';

	const now = new Date();
	const today = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

	let scheduleItems: any[] = $state([]);
	let loading = $state(true);

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

	onMount(async () => {
		try {
			const faculty = await facultyApi.getMe();
			scheduleItems = await facultyApi.getSchedule(faculty.id);
		} catch (err) {
			console.error('Failed to load schedule', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
	{#if loading}
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

		<div class="flex items-center justify-between mb-3">
			<p class="text-sm text-gray-700 font-medium">{today}</p>
		</div>
	</AquaCard>

	<!-- Schedule Items -->
	{#each scheduleItems as item}
		<AquaCard padding={false}>
			<div class="flex items-stretch">
				<!-- Color bar -->
				<div class="w-1 shrink-0 rounded-l-[10px]" style="background-color: {getTypeColor(item.type || 'Clinical')};"></div>

				<div class="flex-1 px-4 py-3">
					<div class="flex items-center justify-between mb-1">
						<p class="text-sm font-semibold text-gray-800">{item.title}</p>
						{#if item.status}
							<StatusBadge variant={getStatusVariant(item.status)}>{item.status}</StatusBadge>
						{/if}
					</div>

					<div class="flex items-center gap-3 text-xs text-gray-500">
						{#if item.time}
							<span class="flex items-center gap-1">
								<Clock class="w-3 h-3" />
								{item.time}
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
			<p class="text-sm text-gray-400">No schedule items</p>
		</div>
	{/if}
	{/if}
</div>
