<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import {
		CheckCircle, XCircle, Clock, Clipboard, User, AlertTriangle,
		FileText, Eye, Calendar, Stethoscope
	} from 'lucide-svelte';

	// State
	let activeTab = $state('pending');
	let approvals: any[] = $state([]);
	let loading = $state(true);
	let facultyId = $state('');
	let approvalStates = $state<Record<string, { status: string; score: number; comments: string }>>({});

	// Comment modal state
	let showCommentModal = $state(false);
	let commentApprovalId = $state('');
	let commentText = $state('');
	let commentAction = $state<'APPROVED' | 'REJECTED'>('APPROVED');

	const tabs = [
		{ id: 'pending', label: 'Pending Approvals' },
		{ id: 'history', label: 'Approval History' },
	];

	// Derive pending and history items
	const pendingApprovals = $derived(
		approvals.filter(a => getApprovalStatus(a.id) === 'PENDING')
	);

	const historyApprovals = $derived(
		approvals.filter(a => getApprovalStatus(a.id) !== 'PENDING')
	);

	function getApprovalStatus(id: string) {
		return approvalStates[id]?.status || 'PENDING';
	}

	function getApprovalScore(id: string) {
		return approvalStates[id]?.score || 0;
	}

	function setScore(id: string, score: number) {
		if (!approvalStates[id]) {
			approvalStates[id] = { status: 'PENDING', score: 0, comments: '' };
		}
		approvalStates[id].score = score;
		approvalStates = { ...approvalStates };
	}

	function openCommentModal(id: string, action: 'APPROVED' | 'REJECTED') {
		commentApprovalId = id;
		commentAction = action;
		commentText = '';
		showCommentModal = true;
	}

	async function handleApprove(id: string, withComment = false) {
		if (withComment) {
			const comments = commentText;
			showCommentModal = false;
			try {
				const score = getApprovalScore(id);
				await facultyApi.processApproval(facultyId, id, { status: 'APPROVED', comments, score });
				if (!approvalStates[id]) {
					approvalStates[id] = { status: 'PENDING', score: 0, comments: '' };
				}
				approvalStates[id].status = 'APPROVED';
				approvalStates[id].comments = comments;
				approvalStates = { ...approvalStates };
			} catch (err) {
				console.error('Failed to approve', err);
			}
		} else {
			openCommentModal(id, 'APPROVED');
		}
	}

	async function handleReject(id: string, withComment = false) {
		if (withComment) {
			const comments = commentText;
			showCommentModal = false;
			try {
				await facultyApi.processApproval(facultyId, id, { status: 'REJECTED', comments });
				if (!approvalStates[id]) {
					approvalStates[id] = { status: 'PENDING', score: 0, comments: '' };
				}
				approvalStates[id].status = 'REJECTED';
				approvalStates[id].comments = comments;
				approvalStates = { ...approvalStates };
			} catch (err) {
				console.error('Failed to reject', err);
			}
		} else {
			openCommentModal(id, 'REJECTED');
		}
	}

	function submitWithComment() {
		if (commentAction === 'APPROVED') {
			handleApprove(commentApprovalId, true);
		} else {
			handleReject(commentApprovalId, true);
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
		try {
			const faculty = await facultyApi.getMe();
			facultyId = faculty.id;
			approvals = await facultyApi.getApprovals(faculty.id);

			// Initialize approval states
			approvals.forEach(a => {
				if (!approvalStates[a.id]) {
					approvalStates[a.id] = {
						status: a.status || 'PENDING',
						score: a.score || 0,
						comments: a.comments || '',
					};
				}
			});
		} catch (err) {
			console.error('Failed to load approvals', err);
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
		<div class="flex items-center gap-3 mb-2">
			<div class="w-10 h-10 rounded-lg flex items-center justify-center"
				style="background: linear-gradient(to bottom, #3b82f620, #3b82f610); border: 1px solid rgba(59,130,246,0.3);">
				<Clipboard class="w-5 h-5 text-blue-600" />
			</div>
			<h1 class="text-xl font-bold text-gray-800">Case Record Approvals</h1>
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
			{#each pendingApprovals as approval}
				{@const currentScore = getApprovalScore(approval.id)}
				<AquaCard padding={false}>
					<div class="p-4">
						<!-- Patient Info Header -->
						<div class="flex items-start gap-3 mb-3">
							<div class="relative shrink-0">
								{#if approval.patient?.photo}
									<img src={approval.patient.photo} alt={approval.patient?.name || 'Patient'}
										class="w-14 h-14 rounded-full object-cover border-2 border-white shadow" />
								{:else}
									<Avatar name={approval.patient?.name || approval.case_record?.patient_name || 'Patient'} size="lg" />
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center justify-between">
									<h3 class="text-base font-bold text-gray-800">
										{approval.patient?.name || approval.case_record?.patient_name || 'Unknown Patient'}
									</h3>
									<button class="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer"
										style="background: rgba(0,0,0,0.05);"
										onclick={() => goto(`/patients/${approval.patient?.id || approval.case_record?.patient_id}`)}>
										<Eye class="w-4 h-4 text-gray-400" />
									</button>
								</div>
								<p class="text-xs text-gray-500">
									ID: {approval.patient?.patient_id || approval.case_record?.patient_id || 'N/A'}
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
								{approval.case_record?.type || 'Case Record'}
							</h4>
							<p class="text-sm text-gray-600 mb-2">
								{approval.case_record?.description || 'No description provided'}
							</p>
							<div class="flex items-center gap-4 text-xs text-gray-500">
								<span class="flex items-center gap-1">
									<Stethoscope class="w-3 h-3" />
									{approval.case_record?.doctor_name || approval.submitted_by || 'Unknown'}
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
									>
										{score}
									</button>
								{/each}
							</div>
						</div>

						<!-- Action Buttons -->
						<div class="flex gap-3">
							<button
								class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold cursor-pointer"
								style="background: white; color: #dc2626; border: 2px solid #fecaca;"
								onclick={() => handleReject(approval.id)}
							>
								<XCircle class="w-4 h-4" />
								Reject
							</button>
							<button
								class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-white text-sm font-semibold cursor-pointer"
								style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.1);"
								onclick={() => handleApprove(approval.id)}
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
					<Clipboard class="w-4 h-4 text-blue-600 mr-2" />
					<span class="text-blue-900 font-semibold text-sm">Approval History</span>
					<span class="ml-auto text-xs text-gray-500">{historyApprovals.length} items</span>
				{/snippet}

				<div class="space-y-3">
					{#each historyApprovals as approval}
						{@const status = getApprovalStatus(approval.id)}
						{@const score = getApprovalScore(approval.id)}
						<div class="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
							<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
								style="background: {status === 'APPROVED' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};">
								{#if status === 'APPROVED'}
									<CheckCircle class="w-5 h-5 text-green-500" />
								{:else}
									<XCircle class="w-5 h-5 text-red-500" />
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold text-gray-800">
									{approval.case_record?.type || 'Case Record'}
								</p>
								<p class="text-xs text-gray-500 truncate">
									{approval.patient?.name || approval.case_record?.patient_name || 'Unknown'} · ID: {approval.patient?.patient_id || approval.case_record?.patient_id || 'N/A'}
								</p>
							</div>
							<div class="text-right shrink-0">
								<p class="text-xs font-bold" style="color: {status === 'APPROVED' ? '#16a34a' : '#dc2626'};">
									{status === 'APPROVED' ? 'Approved' : 'Rejected'}
								</p>
								{#if status === 'APPROVED' && score > 0}
									<p class="text-xs text-gray-500">Score: {score}</p>
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

<!-- Comment Modal -->
{#if showCommentModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4" style="background: rgba(0,0,0,0.5);">
		<div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
			<h3 class="text-lg font-bold text-gray-800 mb-1">
				{commentAction === 'APPROVED' ? 'Approve' : 'Reject'} Case Record
			</h3>
			<p class="text-sm text-gray-500 mb-4">Add optional comments for this action.</p>

			<textarea
				class="w-full p-3 rounded-lg text-sm resize-none"
				style="border: 1px solid rgba(0,0,0,0.15); background: #f8f9fb;"
				rows="4"
				placeholder="Enter your comments (optional)..."
				bind:value={commentText}
			></textarea>

			<div class="flex gap-3 mt-4">
				<button
					class="flex-1 py-2.5 rounded-lg text-sm font-medium cursor-pointer"
					style="background: #f1f5f9; color: #64748b; border: 1px solid rgba(0,0,0,0.1);"
					onclick={() => showCommentModal = false}
				>
					Cancel
				</button>
				<button
					class="flex-1 py-2.5 rounded-lg text-sm font-medium text-white cursor-pointer"
					style="background: linear-gradient(to bottom, {commentAction === 'APPROVED' ? '#22c55e, #16a34a' : '#ef4444, #dc2626'});"
					onclick={submitWithComment}
				>
					{commentAction === 'APPROVED' ? 'Approve' : 'Reject'}
				</button>
			</div>
		</div>
	</div>
{/if}
