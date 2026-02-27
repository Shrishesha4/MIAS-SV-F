<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { studentApi } from '$lib/api/students';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Users, ChevronRight, Search, Activity, FileText } from 'lucide-svelte';

	let searchQuery = $state('');
	let assignedPatients: any[] = $state([]);
	let loading = $state(true);

	const filteredPatients = $derived(
		assignedPatients.filter(p =>
			(p.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
			(p.patient_id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
			(p.condition || '').toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	onMount(async () => {
		try {
			const student = await studentApi.getMe();
			assignedPatients = await studentApi.getAssignedPatients(student.id);
		} catch (err) {
			console.error('Failed to load patients', err);
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
				<Users class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Assigned Patients
				</h2>
				<span class="ml-auto text-xs text-blue-600 font-semibold bg-blue-100 px-2 py-0.5 rounded-full">
					{assignedPatients.length}
				</span>
			</div>
		{/snippet}

		<!-- Search -->
		<div class="mb-3">
			<div class="relative">
				<Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
				<input
					type="text"
					placeholder="Search patients..."
					class="w-full pl-9 pr-3 py-2 text-sm rounded-lg outline-none"
					style="border: 1px solid rgba(0,0,0,0.2); border-radius: 6px; background-color: rgba(255,255,255,0.8); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
					bind:value={searchQuery}
				/>
			</div>
		</div>
	</AquaCard>

	<!-- Patient List -->
	{#each filteredPatients as patient}
		<button
			class="w-full text-left cursor-pointer"
			onclick={() => goto(`/patients/${patient.id}`)}
		>
			<AquaCard padding={false}>
				<div class="px-4 py-3 flex items-center gap-3">
					<Avatar name={patient.name} size="md" />
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<p class="text-sm font-semibold text-gray-800">{patient.name}</p>
							<StatusBadge variant="info">{patient.gender}</StatusBadge>
						</div>
					<p class="text-xs text-gray-500 mt-0.5">{patient.patient_id}{patient.age ? ` · Age ${patient.age}` : ''}</p>
					{#if patient.condition}
						<div class="flex items-center gap-3 mt-1.5">
							<span class="inline-flex items-center gap-1 text-[10px] text-orange-600 font-medium">
								<Activity class="w-3 h-3" />
								{patient.condition}
							</span>
						</div>
					{/if}
					</div>
					<ChevronRight class="w-5 h-5 text-gray-300 shrink-0" />
				</div>
			</AquaCard>
		</button>
	{/each}

	{#if filteredPatients.length === 0}
		<div class="text-center py-12">
			<Users class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No patients found</p>
		</div>
	{/if}
	{/if}
</div>
