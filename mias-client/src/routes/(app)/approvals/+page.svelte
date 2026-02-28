<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { facultyApi } from '$lib/api/faculty';
	import { approvalsApi, type ApprovalItem } from '$lib/api/approvals';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import {
		CheckCircle, XCircle, Clock, ClipboardList, AlertTriangle,
		FileText, Eye, Calendar, Stethoscope, ChevronLeft
	} from 'lucide-svelte';

	// State
	let activeTab = $state('pending');
	let pendingApprovals: ApprovalItem[] = $state([]);
	let historyApprovals: ApprovalItem[] = $state([]);
	let loading = $state(true);
	let facultyId = $state('');
	let approvalType = $state('case-records');
	let processingId = $state<string | null>(null);
	let scores = $state<Record<string, number>>({});

	const tabs = [
		{ id: 'pending', label: 'Pending Approvals' },
		{ id: 'history', label: 'Approval History' },
	];

	// Approval type titles
	const typeLabels: Record<string, string> = {
		'case-records': 'Case Record Approvals',
		'discharge': 'Discharge Summary Approvals',
		'admissions': 'Admission Approvals',
		'prescriptions': 'Prescription Approvals',
	};

	function getScore(id: string): number {
		return scores[id] || 3;
	}

	function setScore(id: string, score: number) {
		scores[id] = score;
		scores = { ...scores };
	}

	async function handleApprove(id: string) {
		processingId = id;
		try {
			const score = getScore(id);
			await approvalsApi.processApproval(facultyId, id, { 
				status: 'APPROVED', 
				score,
				comments: 'Approved'
			});
			// Move from pending to history
			const item = pendingApprovals.find(a => a.id === id);
			if (item) {
				pendingApprovals = pendingApprovals.filter(a => a.id !== id);
				historyApprovals = [{...item, status: 'APPROVED', score, processed_at: new Date().toISOString()}, ...historyApprovals];
			}
		} catch (err) {
			console.error('Failed to approve', err);
		} finally {
			processingId = null;
		}
	}

	async function handleReject(id: string) {
		processingId = id;
		try {
			await approvalsApi.processApproval(facultyId, id, { 
				status: 'REJECTED',
				comments: 'Rejected'
			});
			// Move from pending to history
			const item = pendingApprovals.find(a => a.id === id);
			if (item) {
				pendingApprovals = pendingApprovals.filter(a => a.id !== id);
				historyApprovals = [{...item, status: 'REJECTED', processed_at: new Date().toISOString()}, ...historyApprovals];
			}
		} catch (err) {
			console.error('Failed to reject', err);
		} finally {
			processingId = null;
		}
	}

	function formatDate(dateStr: string): string {
		if (!dateStr) return '';
		const d = new Date(dateStr);
		return d.toLocaleDateString('en-US', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
		}) + ' ' + d.toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	onMount(async () => {
		// Get approval type from URL
		const urlType = page.url?.searchParams?.get('type') || 'case-records';
		approvalType = urlType;

		try {
			const faculty = await facultyApi.getMe();
			facultyId = faculty.id;
			
			// Load pending approvals for this type
			pendingApprovals = await approvalsApi.getPendingApprovals(faculty.id, approvalType);
			
			// Load history
			historyApprovals = await approvalsApi.getApprovalHistory(faculty.id);
			// Filter history by type
			historyApprovals = historyApprovals.filter(a => {
				const typeMap: Record<string, string> = {
					'case-records': 'CASE_RECORD',
					'discharge': 'DISCHARGE_SUMMARY',
					'admissions': 'ADMISSION',
					'prescriptions': 'PRESCRIPTION',
				};
				return a.type === typeMap[approvalType];
			});
		} catch (err) {
			console.error('Failed to load approvals', err);
		} finally {
			loading = false;
		}
	});

	// Auto-refresh approvals every 30 seconds
	$effect(() => {
		if (loading || !facultyId) return;
		const interval = setInterval(async () => {
			try {
				pendingApprovals = await approvalsApi.getPendingApprovals(facultyId, approvalType);
			} catch (err) {
				console.error('Auto-refresh failed', err);
			}
		}, 30000);
		return () => clearInterval(interval);
	});
</script>

<div class="px-4 py-4 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Header -->
		<div class="flex items-center gap-3 mb-2">
			<button 
				class="w-10 h-10 rounded-full flex items-center justify-center cursor-pointer"
				style="background: linear-gradient(to bottom, #f8f9fb, #e8eef5); border: 1px solid rgba(0,0,0,0.1);"
				onclick={() => goto('/dashboard')}
			>
				<ChevronLeft class="w-5 h-5 text-blue-600" />
			</button>
			<div class="w-10 h-10 rounded-lg flex items-center justify-center"
				style="background: linear-gradient(to bottom, #3b82f620, #3b82f610); border: 1px solid rgba(59,130,246,0.3);">
				<ClipboardList class="w-5 h-5 text-blue-600" />
			</div>
			<h1 class="text-xl font-bold text-gray-800">{typeLabels[approvalType] || 'Approvals'}</h1>
		</div>

		<!-- Tab Bar -->
		<div class="flex rounded-lg overflow-hidden" style="background: #f1f5f9; border: 1px solid rgba(0,0,0,0.1);">
			{#each tabs as tab}
				<button
					class="flex-1 py-2.5 text-sm font-medium text-center cursor-pointer transition-all"
					style="color: {activeTab === tab.id ? '#2563eb' : '#64748b'};
					       background: {activeTab === tab.id ? 'white' : 'transparent'};
					       border-bottom: {activeTab === tab.id ? '2px solid #2563eb' : '2px solid transparent'};"
					onclick={() => activeTab = tab.id}
				>
					{tab.label}
				</button>
			{/each}
		</div>

		<!-- Pending Approvals Tab -->
		{#if activeTab === 'pending'}
			{#each pendingApprovals as approval (approval.id)}
				{@const currentScore = getScore(approval.id)}
				{@const isProcessing = processingId === approval.id}
				<AquaCard padding={false}>
					<div class="p-4">
						<!-- Patient Info Header -->
						<div class="flex items-start gap-3 mb-3">
							<div class="relative shrink-0">
								{#if approval.patient?.photo}
									<img src={approval.patient.photo} alt={approval.patient?.name || 'Patient'}
										class="w-14 h-14 rounded-full object-cover border-2 border-white shadow" />
								{:else}
									<Avatar name={approval.patient?.name || 'Patient'} size="lg" />
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center justify-between">
									<h3 class="text-base font-bold text-gray-800">
										{approval.patient?.name || 'Unknown Patient'}
									</h3>
									<button 
										class="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer"
										style="background: rgba(0,0,0,0.05);"
										onclick={() => goto(`/patients/${approval.patient?.id}`)}
									>
										<Eye class="w-4 h-4 text-gray-400" />
									</button>
								</div>
								<p class="text-xs text-gray-500">
									ID: {approval.patient?.patient_id || 'N/A'}
								</p>
								<p class="text-xs text-gray-500">
									{approval.patient?.age || '—'}, {approval.patient?.gender || '—'}, Blood: {approval.patient?.blood_group || '—'}
								</p>
							</div>
						</div>

						<!-- Allergy Warning (if any) -->
						{#if approval.patient?.allergies && approval.patient.allergies.length > 0}
							<div class="rounded-lg p-3 mb-3" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2);">
								<div class="flex items-center gap-2">
									<AlertTriangle class="w-4 h-4 text-red-500 shrink-0" />
									<span class="text-sm font-semibold text-red-600">
										{approval.patient.allergies.map((a: any) => a.allergen).join(', ')} Allergy
									</span>
								</div>
							</div>
						{/if}

						<!-- Primary Diagnosis -->
						<div class="rounded-lg p-3 mb-3" style="background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.1);">
							<div class="flex items-start gap-2">
								<FileText class="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
								<div>
									{#if approval.patient?.primary_diagnosis}
										<p class="text-sm text-gray-700">{approval.patient.primary_diagnosis}</p>
									{:else}
										<p class="text-sm text-gray-400 italic">No primary diagnosis recorded</p>
									{/if}
								</div>
							</div>
						</div>

						<!-- Procedure Details -->
						<div class="mb-4">
							<h4 class="text-sm font-bold text-gray-800 mb-1">
								{approval.case_record?.procedure_name || approval.case_record?.type || 'Case Record'}
							</h4>
							<p class="text-sm text-gray-600 mb-2">
								{approval.case_record?.description || approval.case_record?.procedure_description || 'No description provided'}
							</p>
							<div class="flex items-center gap-4 text-xs text-gray-500">
								<span class="flex items-center gap-1">
									<Stethoscope class="w-3 h-3" />
									{approval.case_record?.doctor_name || 'Unknown'}
								</span>
								<span class="flex items-center gap-1">
									<Calendar class="w-3 h-3" />
									{formatDate(approval.case_record?.date || approval.created_at)}
								</span>
							</div>
						</div>

						<!-- Score Selection -->
						<div class="mb-4">
							<p class="text-xs text-gray-500 mb-2">Score:</p>
							<div class="flex gap-2">
								{#each [1, 2, 3, 4, 5] as score}
									<button
										class="w-9 h-9 rounded-lg text-sm font-bold cursor-pointer transition-all"
										style="background: {currentScore === score ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f1f5f9'};
										       color: {currentScore === score ? 'white' : '#64748b'};
										       border: 1px solid {currentScore === score ? '#2563eb' : 'rgba(0,0,0,0.1)'};"
										onclick={() => setScore(approval.id, score)}
										disabled={isProcessing}
									>
										{score}
									</button>
								{/each}
							</div>
						</div>

						<!-- Action Buttons -->
						<div class="flex gap-3">
							<button
								class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold cursor-pointer disabled:opacity-50"
								style="background: white; color: #dc2626; border: 2px solid #fecaca;"
								onclick={() => handleReject(approval.id)}
								disabled={isProcessing}
							>
								<XCircle class="w-4 h-4" />
								Reject
							</button>
							<button
								class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-white text-sm font-semibold cursor-pointer disabled:opacity-50"
								style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.1);"
								onclick={() => handleApprove(approval.id)}
								disabled={isProcessing}
							>
								<CheckCircle class="w-4 h-4" />
								Approve
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}

			{#if pendingApprovals.length === 0}
				<div class="text-center py-12">
					<CheckCircle class="w-12 h-12 text-green-200 mx-auto mb-3" />
					<p class="text-sm text-gray-400">No pending approvals</p>
					<p class="text-xs text-gray-300 mt-1">All caught up!</p>
				</div>
			{/if}

		<!-- Approval History Tab -->
		{:else if activeTab === 'history'}
			<AquaCard>
				{#snippet header()}
					<ClipboardList class="w-4 h-4 text-blue-600 mr-2" />
					<span class="text-blue-900 font-semibold text-sm">Approval History</span>
					<span class="ml-auto text-xs text-gray-500">{historyApprovals.length} items</span>
				{/snippet}

				<div class="space-y-3">
					{#each historyApprovals as approval (approval.id)}
						{@const isApproved = approval.status === 'APPROVED'}
						<div class="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
							<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
								style="background: {isApproved ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};">
								{#if isApproved}
									<CheckCircle class="w-5 h-5 text-green-500" />
								{:else}
									<XCircle class="w-5 h-5 text-red-500" />
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold text-gray-800">
									{approval.case_record?.procedure_name || approval.case_record?.type || 'Case Record'}
								</p>
								<p class="text-xs text-gray-500 truncate">
									{approval.patient?.name || 'Unknown'} · ID: {approval.patient?.patient_id || 'N/A'}
								</p>
							</div>
							<div class="text-right shrink-0">
								<p class="text-xs font-bold px-2 py-0.5 rounded-full inline-block"
									style="background: {isApproved ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};
									       color: {isApproved ? '#16a34a' : '#dc2626'};">
									{isApproved ? 'Approved' : 'Rejected'}
								</p>
								{#if isApproved && approval.score}
									<p class="text-xs text-gray-500">Score: {approval.score}</p>
								{/if}
								<p class="text-[10px] text-gray-400">
									{formatDate(approval.processed_at || approval.created_at)}
								</p>
							</div>
						</div>
					{/each}

					{#if historyApprovals.length === 0}
						<div class="text-center py-8">
							<Clock class="w-10 h-10 text-gray-200 mx-auto mb-2" />
							<p class="text-sm text-gray-400">No approval history yet</p>
						</div>
					{/if}
				</div>
			</AquaCard>
		{/if}
	{/if}
</div>
