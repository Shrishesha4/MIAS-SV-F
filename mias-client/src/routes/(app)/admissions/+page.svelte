<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import type { Admission } from '$lib/api/types';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { 
		Bed, Calendar, User, Building, ChevronDown, ChevronUp, ChevronLeft,
		Clock, Link, FileText, CheckCircle, Circle, ArrowRightCircle, X
	} from 'lucide-svelte';

	let admissions: Admission[] = $state([]);
	let admissionsMap = $state<Record<string, Admission>>({});
	let loading = $state(true);
	let expandedId = $state<string | null>(null);
	let showDischargeSummary = $state(false);
	let selectedAdmission = $state<Admission | null>(null);

	function getStatusIcon(status: string) {
		if (status === 'Discharged') return { color: '#22c55e', icon: CheckCircle };
		if (status === 'Transferred') return { color: '#3b82f6', icon: ArrowRightCircle };
		return { color: '#f59e0b', icon: Circle }; // Active
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', { 
			month: 'short', 
			day: 'numeric', 
			year: 'numeric' 
		});
	}

	function formatShortDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', { 
			month: 'short', 
			day: 'numeric', 
			year: 'numeric' 
		});
	}

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	function openDischargeSummary(admission: Admission) {
		selectedAdmission = admission;
		showDischargeSummary = true;
	}

	function closeDischargeSummary() {
		showDischargeSummary = false;
		selectedAdmission = null;
	}

	function getRelatedAdmission(id: string | undefined): Admission | undefined {
		if (!id) return undefined;
		return admissionsMap[id];
	}

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			admissions = await patientApi.getAdmissions(patient.id);
			// Create map for related admissions lookup
			admissions.forEach(a => {
				admissionsMap[a.id] = a;
			});
		} catch (err) {
			console.error('Failed to load admissions', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-2">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-4">
		<button class="p-2 rounded-full hover:bg-gray-100" onclick={() => history.back()}>
			<ChevronLeft class="w-5 h-5 text-gray-600" />
		</button>
		<h1 class="text-lg font-bold text-gray-800">Admission Records</h1>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Admissions List -->
		{#each admissions as admission}
			{@const statusInfo = getStatusIcon(admission.status)}
			{@const StatusIcon = statusInfo.icon}
			{@const isExpanded = expandedId === admission.id}
			
			<AquaCard padding={false}>
				<!-- Collapsed Header -->
				<button 
					class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
					onclick={() => toggleExpand(admission.id)}
				>
					<!-- Status Icon -->
					<div 
						class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
						style="background: {statusInfo.color}20;"
					>
						<StatusIcon class="w-5 h-5" style="color: {statusInfo.color};" />
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<p class="text-xs text-gray-500">{formatShortDate(admission.admission_date)}</p>
						<p class="text-sm font-bold text-gray-800">{admission.ward}, {admission.bed_number}</p>
						<p class="text-xs text-gray-600">{admission.attending_doctor} · {admission.department}</p>
					</div>

					<!-- Expand Arrow -->
					{#if isExpanded}
						<ChevronUp class="w-5 h-5 text-gray-400" />
					{:else}
						<ChevronDown class="w-5 h-5 text-gray-400" />
					{/if}
				</button>

				<!-- Expanded Content -->
				{#if isExpanded}
					<div class="px-4 pb-4 space-y-4 border-t border-gray-100">
						<!-- Dates & Location -->
						<div class="grid grid-cols-2 gap-4 pt-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Admission Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">{formatDate(admission.admission_date)}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Discharge Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">
										{admission.discharge_date ? formatDate(admission.discharge_date) : 'Active'}
									</span>
								</div>
							</div>
						</div>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Ward & Bed</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
										<Bed class="w-4 h-4 text-gray-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.ward}, {admission.bed_number}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Admitted Under</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
										<User class="w-4 h-4 text-green-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.attending_doctor}</span>
								</div>
							</div>
						</div>

						<!-- Reason for Admission -->
						{#if admission.reason}
							<div class="p-3 rounded-xl border border-gray-200">
								<p class="text-xs text-gray-500 mb-1">Reason for Admission</p>
								<p class="text-sm text-gray-800">{admission.reason}</p>
							</div>
						{/if}

						<!-- Diagnosis -->
						{#if admission.diagnosis}
							<div class="p-3 rounded-xl bg-gray-50">
								<p class="text-xs text-gray-500 mb-1">Diagnosis</p>
								<p class="text-sm text-gray-800">{admission.diagnosis}</p>
							</div>
						{/if}

						<!-- Related Admission (if transferred) -->
						{#if admission.related_admission_id}
							{@const relatedAdmission = getRelatedAdmission(admission.related_admission_id)}
							{#if relatedAdmission}
								<div class="p-3 rounded-xl bg-blue-50 border border-blue-100">
									<div class="flex items-center gap-2 text-blue-600 mb-2">
										<Link class="w-4 h-4" />
										<span class="text-xs font-medium">Related Admission</span>
									</div>
									<p class="text-sm text-blue-800">
										Transferred from {admission.transferred_from_department} ({admission.referring_doctor})
									</p>
									<button 
										class="mt-2 flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
										onclick={() => toggleExpand(relatedAdmission.id)}
									>
										<ArrowRightCircle class="w-3 h-3" />
										View Related Admission
									</button>
								</div>
							{/if}
						{/if}

						<!-- Transferred From Section -->
						{#if admission.transferred_from_department}
							<div class="p-3 rounded-xl border border-gray-200 space-y-2">
								<div>
									<p class="text-xs text-gray-500">Transferred From</p>
									<p class="text-sm font-semibold text-gray-800">{admission.transferred_from_department}</p>
								</div>
								{#if admission.referring_doctor}
									<div>
										<p class="text-xs text-gray-500">Referring Doctor</p>
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-gray-500" />
											<span class="text-sm text-gray-800">{admission.referring_doctor} · {admission.transferred_from_department}</span>
										</div>
									</div>
								{/if}
								{#if admission.program_duration_days}
									<div>
										<p class="text-xs text-gray-500">Program Duration</p>
										<p class="text-sm text-gray-800">{admission.program_duration_days} days</p>
									</div>
								{/if}
							</div>
						{/if}

						<!-- View Discharge Summary Button -->
						{#if admission.status === 'Discharged' && admission.discharge_summary}
							<button 
								class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
								onclick={() => openDischargeSummary(admission)}
							>
								<FileText class="w-5 h-5" />
								View Discharge Summary
							</button>
						{/if}
					</div>
				{/if}
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

<!-- Discharge Summary Modal -->
{#if showDischargeSummary && selectedAdmission}
	<AquaModal onClose={closeDischargeSummary}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<FileText class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Discharge Summary</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			<!-- Admission Info -->
			<div class="p-4 rounded-xl bg-gray-50">
				<div class="grid grid-cols-2 gap-3 text-sm">
					<div>
						<span class="text-gray-500">Admitted:</span>
						<span class="ml-1 text-gray-800 font-medium">{formatDate(selectedAdmission.admission_date)}</span>
					</div>
					<div>
						<span class="text-gray-500">Discharged:</span>
						<span class="ml-1 text-gray-800 font-medium">{formatDate(selectedAdmission.discharge_date)}</span>
					</div>
					<div>
						<span class="text-gray-500">Department:</span>
						<span class="ml-1 text-gray-800">{selectedAdmission.department}</span>
					</div>
					<div>
						<span class="text-gray-500">Doctor:</span>
						<span class="ml-1 text-gray-800">{selectedAdmission.attending_doctor}</span>
					</div>
				</div>
			</div>

			<!-- Diagnosis -->
			{#if selectedAdmission.diagnosis}
				<div>
					<h4 class="text-sm font-semibold text-gray-700 mb-2">Diagnosis</h4>
					<p class="text-sm text-gray-800 p-3 rounded-lg bg-gray-50">{selectedAdmission.diagnosis}</p>
				</div>
			{/if}

			<!-- Summary -->
			<div>
				<h4 class="text-sm font-semibold text-gray-700 mb-2">Summary</h4>
				<p class="text-sm text-gray-800 p-3 rounded-lg bg-gray-50">{selectedAdmission.discharge_summary}</p>
			</div>

			<!-- Discharge Instructions -->
			{#if selectedAdmission.discharge_instructions}
				<div>
					<h4 class="text-sm font-semibold text-gray-700 mb-2">Discharge Instructions</h4>
					<p class="text-sm text-gray-800 p-3 rounded-lg bg-blue-50">{selectedAdmission.discharge_instructions}</p>
				</div>
			{/if}

			<!-- Follow-up -->
			{#if selectedAdmission.follow_up_date}
				<div class="p-3 rounded-xl border border-green-200 bg-green-50">
					<div class="flex items-center gap-2">
						<Calendar class="w-4 h-4 text-green-600" />
						<span class="text-sm text-green-800">
							Follow-up scheduled: <strong>{formatDate(selectedAdmission.follow_up_date)}</strong>
						</span>
					</div>
				</div>
			{/if}
		</div>
	</AquaModal>
{/if}
