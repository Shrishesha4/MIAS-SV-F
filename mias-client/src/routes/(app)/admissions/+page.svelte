<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Bed, Calendar, User, Building } from 'lucide-svelte';

	let admissions: any[] = $state([]);
	let loading = $state(true);

	const statusVariant: Record<string, 'success' | 'info' | 'warning'> = {
		ACTIVE: 'warning',
		DISCHARGED: 'success',
		TRANSFERRED: 'info',
	};

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			admissions = await patientApi.getAdmissions(patient.id);
		} catch (err) {
			console.error('Failed to load admissions', err);
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
	{#each admissions as admission}
		<AquaCard>
			{#snippet header()}
				<Bed class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm flex-1">{admission.reason}</span>
				<StatusBadge variant={statusVariant[admission.status]}>{admission.status}</StatusBadge>
			{/snippet}
			<div class="space-y-2">
				<div class="flex items-center gap-2">
					<Calendar class="w-4 h-4 text-gray-400" />
					<div class="text-sm">
						<span class="text-gray-500">Admitted:</span>
						<span class="text-gray-800 ml-1">
							{new Date(admission.admission_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						</span>
						{#if admission.discharge_date}
							<span class="text-gray-500 ml-2">Discharged:</span>
							<span class="text-gray-800 ml-1">
								{new Date(admission.discharge_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
							</span>
						{/if}
					</div>
				</div>
				<div class="flex items-center gap-2">
					<Building class="w-4 h-4 text-gray-400" />
					<span class="text-sm text-gray-800">{admission.department} · {admission.ward} · Bed {admission.bed_number}</span>
				</div>
				<div class="flex items-center gap-2">
					<User class="w-4 h-4 text-gray-400" />
					<span class="text-sm text-gray-800">{admission.attending_doctor}</span>
				</div>
				{#if admission.diagnosis}
					<div class="mt-2 p-2 rounded bg-gray-50">
						<p class="text-xs text-gray-500 mb-0.5">Diagnosis</p>
						<p class="text-sm text-gray-700">{admission.diagnosis}</p>
					</div>
				{/if}
			</div>
		</AquaCard>
	{/each}

	{#if admissions.length === 0}
		<div class="text-center py-12 text-gray-400">
			<Bed class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No admissions found</p>
		</div>
	{/if}
	{/if}
</div>
