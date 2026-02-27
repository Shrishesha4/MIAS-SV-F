<script lang="ts">
	import { onMount } from 'svelte';
	import { studentApi } from '$lib/api/students';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Clipboard, ChevronDown, ChevronUp, Award, User, Calendar, Stethoscope } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let caseRecords: any[] = $state([]);
	let loading = $state(true);

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		APPROVED: 'success',
		SUBMITTED: 'info',
		DRAFT: 'pending',
		REJECTED: 'error' as any,
	};

	onMount(async () => {
		try {
			const student = await studentApi.getMe();
			caseRecords = await studentApi.getCaseRecords(student.id);
		} catch (err) {
			console.error('Failed to load case records', err);
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
	<!-- Header -->
	<AquaCard>
		{#snippet header()}
			<div class="flex items-center gap-2 w-full">
				<Clipboard class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Case Records
				</h2>
				<span class="ml-auto text-xs text-blue-600 font-semibold bg-blue-100 px-2 py-0.5 rounded-full">
					{caseRecords.length}
				</span>
			</div>
		{/snippet}
		<p class="text-xs text-gray-500">Your clinical case documentation and evaluations</p>
	</AquaCard>

	<!-- Case Record List -->
	{#each caseRecords as cr}
		<AquaCard padding={false}>
			<button
				class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
				onclick={() => expandedId = expandedId === cr.id ? null : cr.id}
			>
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, #8b5cf6cc, #8b5cf6);"
				>
					<Clipboard class="w-5 h-5 text-white" />
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{cr.chief_complaint}</p>
					<p class="text-xs text-gray-500 mt-0.5">
						{new Date(cr.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
						{#if cr.time} · {cr.time}{/if}
						{#if cr.department} · {cr.department}{/if}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<StatusBadge variant={statusVariant[cr.status] ?? 'pending'}>{cr.status}</StatusBadge>
					{#if expandedId === cr.id}
						<ChevronUp class="w-4 h-4 text-gray-400" />
					{:else}
						<ChevronDown class="w-4 h-4 text-gray-400" />
					{/if}
				</div>
			</button>

			{#if expandedId === cr.id}
				<div class="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
					<!-- Examination -->
					<div class="p-3 rounded-lg bg-gray-50">
						<p class="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
							<Stethoscope class="w-3 h-3" />
							Examination
						</p>
						<p class="text-xs text-gray-600">{cr.examination}</p>
					</div>

					<!-- Diagnosis -->
					<div class="p-3 rounded-lg bg-blue-50">
						<p class="text-xs font-semibold text-blue-700 mb-1">Diagnosis</p>
						<p class="text-xs text-gray-700">{cr.diagnosis}</p>
					</div>

					<!-- Treatment Plan -->
					<div class="p-3 rounded-lg bg-green-50">
						<p class="text-xs font-semibold text-green-700 mb-1">Treatment Plan</p>
						<p class="text-xs text-gray-700">{cr.treatment_plan}</p>
					</div>

					<!-- History -->
					{#if cr.history}
						<div class="p-3 rounded-lg bg-gray-50">
							<p class="text-xs font-semibold text-gray-700 mb-1">History</p>
							<p class="text-xs text-gray-600">{cr.history}</p>
						</div>
					{/if}

					<!-- Footer info -->
					<div class="flex items-center justify-between pt-2 text-[10px] text-gray-400">
						<div class="flex items-center gap-3">
							{#if cr.grade}
								<span class="flex items-center gap-1">
									<Award class="w-3 h-3" />
									Grade: <strong class="text-gray-600">{cr.grade}</strong>
								</span>
							{/if}
							{#if cr.provider}
								<span class="flex items-center gap-1">
									<User class="w-3 h-3" />
									{cr.provider}
								</span>
							{/if}
						</div>
						{#if cr.approver}
							<span>Approved by {cr.approver}</span>
						{/if}
					</div>
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if caseRecords.length === 0}
		<div class="text-center py-12">
			<Clipboard class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No case records yet</p>
		</div>
	{/if}
	{/if}
</div>
