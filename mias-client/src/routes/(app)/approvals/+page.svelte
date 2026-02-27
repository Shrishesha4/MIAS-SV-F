<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { CheckCircle, XCircle, Clock, Clipboard, ChevronDown, ChevronUp, User, MessageSquare } from 'lucide-svelte';

	let expandedId = $state<string | null>(null);
	let approvals: any[] = $state([]);
	let loading = $state(true);
	let facultyId = $state('');
	let approvalStates = $state<Record<string, string>>({});

	const pendingCount = $derived(approvals.filter(a => getApprovalStatus(a.id) === 'PENDING').length);

	function getApprovalStatus(id: string) {
		return approvalStates[id] || 'PENDING';
	}

	async function handleApprove(id: string) {
		try {
			await facultyApi.processApproval(facultyId, id, { status: 'APPROVED' });
			approvalStates[id] = 'APPROVED';
		} catch (err) {
			console.error('Failed to approve', err);
		}
	}

	async function handleReject(id: string) {
		try {
			await facultyApi.processApproval(facultyId, id, { status: 'REJECTED' });
			approvalStates[id] = 'REJECTED';
		} catch (err) {
			console.error('Failed to reject', err);
		}
	}

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		PENDING: 'warning',
		APPROVED: 'success',
		REJECTED: 'error' as any,
	};

	function timeAgo(dateStr: string): string {
		const diff = Date.now() - new Date(dateStr).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		return `${days}d ago`;
	}

	onMount(async () => {
		try {
			const faculty = await facultyApi.getMe();
			facultyId = faculty.id;
			approvals = await facultyApi.getApprovals(faculty.id);
		} catch (err) {
			console.error('Failed to load approvals', err);
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
				<CheckCircle class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					Pending Approvals
				</h2>
					<span class="ml-auto text-xs text-orange-600 font-semibold bg-orange-100 px-2 py-0.5 rounded-full">
					{pendingCount} pending
				</span>
			</div>
		{/snippet}
		<p class="text-xs text-gray-500">Review and approve student case record submissions</p>
	</AquaCard>

	<!-- Approval List -->
	{#each approvals as approval}
		{@const currentStatus = getApprovalStatus(approval.id)}
		<AquaCard padding={false}>
			<button
				class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
				onclick={() => expandedId = expandedId === approval.id ? null : approval.id}
			>
				<div
					class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, {currentStatus === 'PENDING' ? '#f97316cc, #f97316' : currentStatus === 'APPROVED' ? '#22c55ecc, #22c55e' : '#ef4444cc, #ef4444'});"
				>
					{#if currentStatus === 'APPROVED'}
						<CheckCircle class="w-5 h-5 text-white" />
					{:else if currentStatus === 'REJECTED'}
						<XCircle class="w-5 h-5 text-white" />
					{:else}
						<Clock class="w-5 h-5 text-white" />
					{/if}
				</div>
				<div class="flex-1 min-w-0">
					<p class="text-sm font-semibold text-gray-800">{approval.case_record?.type || approval.type}</p>
					<p class="text-xs text-gray-500 mt-0.5">
						{approval.submitted_by || approval.case_record?.student_name || 'Student'} · {timeAgo(approval.submitted_at || approval.created_at)}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<StatusBadge variant={statusVariant[currentStatus] ?? 'pending'}>{currentStatus}</StatusBadge>
					{#if expandedId === approval.id}
						<ChevronUp class="w-4 h-4 text-gray-400" />
					{:else}
						<ChevronDown class="w-4 h-4 text-gray-400" />
					{/if}
				</div>
			</button>

			{#if expandedId === approval.id}
				<div class="px-4 pb-4 border-t border-gray-100 pt-3 space-y-3">
					<!-- Description -->
					<div class="p-3 rounded-lg bg-gray-50">
						<p class="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
							<Clipboard class="w-3 h-3" />
							Description
						</p>
						<p class="text-xs text-gray-600">{approval.case_record?.description || approval.description}</p>
					</div>

					<!-- Student info -->
					<div class="p-3 rounded-lg bg-blue-50 flex items-center gap-2">
						<User class="w-3.5 h-3.5 text-blue-600" />
						<span class="text-xs text-blue-700 font-medium">{approval.submitted_by || approval.case_record?.student_name || 'Student'}</span>
					</div>

					<!-- Action Buttons (only for pending) -->
					{#if currentStatus === 'PENDING'}
						<div class="flex gap-2 pt-1">
							<button
								class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-white text-sm font-medium cursor-pointer"
								style="background: linear-gradient(to bottom, #22c55e, #16a34a);
								       border: 1px solid rgba(0,0,0,0.2);
								       box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
								onclick={() => handleApprove(approval.id)}
							>
								<CheckCircle class="w-4 h-4" />
								Approve
							</button>
							<button
								class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-white text-sm font-medium cursor-pointer"
								style="background: linear-gradient(to bottom, #ff5a5a, #cc0000);
								       border: 1px solid rgba(0,0,0,0.2);
								       box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
								onclick={() => handleReject(approval.id)}
							>
								<XCircle class="w-4 h-4" />
								Reject
							</button>
						</div>
					{:else}
						<div class="text-center py-1">
							<StatusBadge variant={currentStatus === 'APPROVED' ? 'success' : 'error'} size="md">
								{currentStatus === 'APPROVED' ? 'Approved' : 'Rejected'}
							</StatusBadge>
						</div>
					{/if}
				</div>
			{/if}
		</AquaCard>
	{/each}

	{#if approvals.length === 0}
		<div class="text-center py-12">
			<CheckCircle class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No pending approvals</p>
		</div>
	{/if}
	{/if}
</div>
