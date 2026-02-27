<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { GraduationCap, Search, BookOpen, BarChart3, ChevronRight, Users } from 'lucide-svelte';

	// Students are loaded from approvals (listing distinct students who submitted)
	// Since there's no dedicated /faculty/{id}/students endpoint, we derive from approvals
	let students: any[] = $state([]);
	let loading = $state(true);

	let searchQuery = $state('');

	const filteredStudents = $derived(
		students.filter(s =>
			s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			(s.student_id || '').toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	function gpaColor(gpa: number): string {
		if (gpa >= 3.7) return '#22c55e';
		if (gpa >= 3.3) return '#3b82f6';
		if (gpa >= 3.0) return '#f97316';
		return '#ef4444';
	}

	onMount(async () => {
		try {
			const faculty = await facultyApi.getMe();
			const approvals = await facultyApi.getApprovals(faculty.id);
			// Derive unique students from approvals data
			const studentMap = new Map<string, any>();
			for (const approval of approvals) {
				const studentName = approval.submitted_by || approval.case_record?.student_name || 'Unknown';
				if (!studentMap.has(studentName)) {
					studentMap.set(studentName, {
						id: approval.student_id || studentName,
						student_id: approval.case_record?.student_id || '',
						name: studentName,
						cases_completed: 0,
						cases_pending: 0,
						status: 'Active',
					});
				}
				const student = studentMap.get(studentName)!;
				if (approval.status === 'APPROVED') {
					student.cases_completed++;
				} else {
					student.cases_pending++;
				}
			}
			students = Array.from(studentMap.values());
		} catch (err) {
			console.error('Failed to load students', err);
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
				<GraduationCap class="w-5 h-5 text-blue-700" />
				<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
					My Students
				</h2>
				<span class="ml-auto text-xs text-blue-600 font-semibold bg-blue-100 px-2 py-0.5 rounded-full">
					{students.length}
				</span>
			</div>
		{/snippet}

		<!-- Search -->
		<div class="mb-3">
			<div class="relative">
				<Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
				<input
					type="text"
					placeholder="Search students..."
					class="w-full pl-9 pr-3 py-2 text-sm rounded-lg outline-none"
					style="border: 1px solid rgba(0,0,0,0.2); border-radius: 6px; background-color: rgba(255,255,255,0.8); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
					bind:value={searchQuery}
				/>
			</div>
		</div>

		<!-- Summary -->
		<div class="grid grid-cols-3 gap-2">
			<div class="text-center p-2 rounded-lg bg-blue-50">
				<p class="text-lg font-bold text-blue-600">{students.length}</p>
				<p class="text-[10px] text-gray-500">Total</p>
			</div>
			<div class="text-center p-2 rounded-lg bg-green-50">
				<p class="text-lg font-bold text-green-600">{students.reduce((a, s) => a + s.cases_completed, 0)}</p>
				<p class="text-[10px] text-gray-500">Cases Done</p>
			</div>
			<div class="text-center p-2 rounded-lg bg-orange-50">
				<p class="text-lg font-bold text-orange-600">{students.reduce((a, s) => a + s.cases_pending, 0)}</p>
				<p class="text-[10px] text-gray-500">Pending</p>
			</div>
		</div>
	</AquaCard>

	<!-- Student List -->
	{#each filteredStudents as student}
		<AquaCard padding={false}>
			<div class="px-4 py-3 flex items-center gap-3">
				<Avatar name={student.name} size="md" />
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2">
						<p class="text-sm font-semibold text-gray-800">{student.name}</p>
						<StatusBadge variant="success">Active</StatusBadge>
					</div>
					<p class="text-xs text-gray-500 mt-0.5">{student.student_id}</p>
					{#if student.year}
					<div class="flex items-center gap-3 mt-1.5 text-[10px]">
						<span class="flex items-center gap-1 text-gray-500">
							<BookOpen class="w-3 h-3" />
							Year {student.year} · Sem {student.semester}
						</span>
						{#if student.gpa}
						<span class="flex items-center gap-1 font-semibold" style="color: {gpaColor(student.gpa)}">
							<BarChart3 class="w-3 h-3" />
							GPA {student.gpa.toFixed(1)}
						</span>
						{/if}
					</div>
					{/if}
				</div>
				<div class="text-right shrink-0">
					<p class="text-xs text-gray-400">Cases</p>
					<p class="text-sm font-bold text-gray-700">{student.cases_completed}</p>
					{#if student.cases_pending > 0}
						<p class="text-[10px] text-orange-500 font-medium">{student.cases_pending} pending</p>
					{/if}
				</div>
			</div>
		</AquaCard>
	{/each}

	{#if filteredStudents.length === 0}
		<div class="text-center py-12">
			<Users class="w-10 h-10 text-gray-300 mx-auto mb-2" />
			<p class="text-sm text-gray-400">No students found</p>
		</div>
	{/if}
	{/if}
</div>
