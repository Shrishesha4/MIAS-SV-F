<script lang="ts">
	import { onMount } from 'svelte';
	import { studentApi } from '$lib/api/students';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Calendar, MapPin, Clock, Users, CheckCircle2, CircleDot, Loader } from 'lucide-svelte';

	let clinicSessions: any[] = $state([]);
	let loading = $state(true);

	function getStatusVariant(status: string): 'success' | 'info' | 'pending' | 'warning' {
		switch (status) {
			case 'Checked In': case 'COMPLETED': return 'success';
			case 'In Progress': case 'SCHEDULED': return 'info';
			case 'Completed': return 'pending';
			default: return 'warning';
		}
	}

	const now = new Date();
	const todayStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

	onMount(async () => {
		try {
			const student = await studentApi.getMe();
			clinicSessions = await studentApi.getClinicSessions(student.id);
		} catch (err) {
			console.error('Failed to load clinic sessions', err);
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
	<!-- Clinic Info Header -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2 w-full">
				<Calendar class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Clinic Sessions
				</h2>
			</div>
		{/snippet}

		<div class="space-y-2">
			<div class="flex items-center gap-2 text-sm text-gray-800 font-semibold">
				<Calendar class="w-4 h-4 text-blue-500" />
				{todayStr}
			</div>
			<div class="flex items-center gap-2 text-xs text-gray-500">
				<Users class="w-3.5 h-3.5 text-gray-400" />
				{clinicSessions.length} sessions
			</div>
		</div>
	</AquaCard>

	<!-- Session List -->
	{#each clinicSessions as session}
		<AquaCard padding={false}>
			<div class="px-4 py-3 flex items-center gap-3">
				<div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, #4d90fecc, #0066cc);">
					<Calendar class="w-5 h-5 text-white" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{session.clinic_name || session.department}</p>
					<p class="text-xs text-gray-500 mt-0.5">
						{new Date(session.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						{#if session.department} · {session.department}{/if}
					</p>
				</div>
				<StatusBadge variant={getStatusVariant(session.status)}>{session.status}</StatusBadge>
			</div>
		</AquaCard>
	{/each}

	{#if clinicSessions.length === 0}
		<div class="text-center py-12">
			<Calendar class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No clinic sessions</p>
		</div>
	{/if}
	{/if}
</div>
