<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Pill, ChevronDown, ChevronUp, Clock, RefreshCw } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let prescriptions: any[] = $state([]);
	let loading = $state(true);

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		ACTIVE: 'success',
		BOUGHT: 'info',
		RECEIVE: 'warning',
		COMPLETED: 'pending',
	};

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			prescriptions = await patientApi.getPrescriptions(patient.id);
		} catch (err) {
			console.error('Failed to load prescriptions', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	{#each prescriptions as rx}
		<AquaCard padding={false}>
			<button
				class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
				onclick={() => expandedId = expandedId === rx.id ? null : rx.id}
			>
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, #ec4899cc, #ec4899);"
				>
					<Pill class="w-5 h-5 text-white" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{rx.doctor}</p>
					<p class="text-xs text-gray-500">
						{new Date(rx.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						· {rx.department}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<StatusBadge variant={statusVariant[rx.status]}>{rx.status}</StatusBadge>
					{#if expandedId === rx.id}
						<ChevronUp class="w-4 h-4 text-gray-400" />
					{:else}
						<ChevronDown class="w-4 h-4 text-gray-400" />
					{/if}
				</div>
			</button>

			{#if expandedId === rx.id}
				<div class="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
					{#each rx.medications as med}
						<div class="p-3 rounded-lg bg-gray-50">
							<div class="flex items-center justify-between mb-2">
								<p class="text-sm font-semibold text-gray-800">{med.name}</p>
								<span class="text-xs text-blue-600 font-medium">{med.dosage}</span>
							</div>
							<div class="grid grid-cols-2 gap-2 text-xs">
								<div class="flex items-center gap-1 text-gray-500">
									<Clock class="w-3 h-3" />
									{med.frequency}
								</div>
								<div class="flex items-center gap-1 text-gray-500">
									<RefreshCw class="w-3 h-3" />
									{med.refills_remaining} refills left
								</div>
							</div>
							{#if med.instructions}
								<p class="text-xs text-gray-600 mt-2 italic">{med.instructions}</p>
							{/if}
							<div class="flex justify-between mt-2 text-[10px] text-gray-400">
								<span>Start: {new Date(med.start_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
								<span>End: {new Date(med.end_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if prescriptions.length === 0}
		<div class="text-center py-12 text-gray-400">
			<Pill class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No prescriptions found</p>
		</div>
	{/if}
	{/if}
</div>
