<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { FileText, ChevronDown, ChevronUp, Stethoscope, FlaskConical, Syringe, Pill } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let records: any[] = $state([]);
	let loading = $state(true);

	const typeColors: Record<string, string> = {
		CONSULTATION: '#4d90fe',
		LABORATORY: '#f97316',
		PROCEDURE: '#8b5cf6',
		MEDICATION: '#ec4899',
	};

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			records = await patientApi.getRecords(patient.id);
		} catch (err) {
			console.error('Failed to load records', err);
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
	{#each records as record}
		<AquaCard padding={false}>
			<button
				class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
				onclick={() => toggleExpand(record.id)}
			>
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, {typeColors[record.type]}cc, {typeColors[record.type]});"
				>
					<div>
						{#if record.type === 'CONSULTATION'}
							<Stethoscope class="w-5 h-5 text-white" />
						{:else if record.type === 'LABORATORY'}
							<FlaskConical class="w-5 h-5 text-white" />
						{:else if record.type === 'PROCEDURE'}
							<Syringe class="w-5 h-5 text-white" />
						{:else}
							<Pill class="w-5 h-5 text-white" />
						{/if}
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800 truncate">{record.description}</p>
					<p class="text-xs text-gray-500">
						{new Date(record.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						· {record.time} · {record.department}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<StatusBadge variant={record.status === 'Completed' ? 'success' : 'pending'}>
						{record.status}
					</StatusBadge>
					{#if expandedId === record.id}
						<ChevronUp class="w-4 h-4 text-gray-400" />
					{:else}
						<ChevronDown class="w-4 h-4 text-gray-400" />
					{/if}
				</div>
			</button>

			{#if expandedId === record.id}
				<div class="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
					<div>
						<p class="text-xs text-gray-500 mb-0.5">Performed By</p>
						<p class="text-sm text-gray-800">{record.performed_by}</p>
					</div>
					{#if record.diagnosis}
						<div>
							<p class="text-xs text-gray-500 mb-0.5">Diagnosis</p>
							<p class="text-sm text-gray-800">{record.diagnosis}</p>
						</div>
					{/if}
					{#if record.recommendations}
						<div>
							<p class="text-xs text-gray-500 mb-0.5">Recommendations</p>
							<p class="text-sm text-gray-800">{record.recommendations}</p>
						</div>
					{/if}

					{#if record.findings.length > 0}
						<div>
							<p class="text-xs text-gray-500 mb-2">Findings</p>
							<div class="space-y-1">
								{#each record.findings as finding}
									<div class="flex items-center justify-between py-1.5 px-2 rounded bg-gray-50">
										<span class="text-xs text-gray-600">{finding.parameter}</span>
										<div class="flex items-center gap-2">
											<span class="text-xs font-medium text-gray-800">{finding.value}</span>
											{#if finding.reference}
												<span class="text-[10px] text-gray-400">({finding.reference})</span>
											{/if}
											<StatusBadge variant={finding.status === 'Normal' ? 'normal' : 'warning'} size="sm">
												{finding.status}
											</StatusBadge>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if records.length === 0}
		<div class="text-center py-12 text-gray-400">
			<FileText class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No medical records found</p>
		</div>
	{/if}
	{/if}
</div>
