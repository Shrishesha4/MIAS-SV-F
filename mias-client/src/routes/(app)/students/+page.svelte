<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi } from '$lib/api/faculty';
	import { authApi } from '$lib/api/auth';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { GraduationCap, Search, BookOpen, BarChart3, ChevronRight, Users, Plus, X, UserPlus } from 'lucide-svelte';

	// Students are loaded from approvals (listing distinct students who submitted)
	// Since there's no dedicated /faculty/{id}/students endpoint, we derive from approvals
	let students: any[] = $state([]);
	let loading = $state(true);

	let searchQuery = $state('');

	// Create Student Modal
	let showCreateModal = $state(false);
	let createLoading = $state(false);
	let createError = $state('');
	let createSuccess = $state(false);

	// Create student form fields
	let newUsername = $state('');
	let newPassword = $state('');
	let newEmail = $state('');
	let newName = $state('');
	let newProgram = $state('BDS');
	let newYear = $state(1);
	let newSemester = $state(1);

	const programs = ['BDS', 'MDS', 'MBBS', 'MD', 'MS'];

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

	function openCreateModal() {
		showCreateModal = true;
		createError = '';
		createSuccess = false;
		newUsername = '';
		newPassword = '';
		newEmail = '';
		newName = '';
		newProgram = 'BDS';
		newYear = 1;
		newSemester = 1;
	}

	async function createStudent() {
		createLoading = true;
		createError = '';
		try {
			await authApi.signup({
				username: newUsername,
				password: newPassword,
				email: newEmail,
				role: 'STUDENT',
				student_data: {
					name: newName,
					program: newProgram,
					year: newYear,
					semester: newSemester,
					gpa: 0,
				},
			});
			createSuccess = true;
			// Add to local list
			students = [...students, {
				id: newUsername,
				student_id: '',
				name: newName,
				cases_completed: 0,
				cases_pending: 0,
				status: 'Active',
				year: newYear,
				semester: newSemester,
				program: newProgram,
			}];
			setTimeout(() => {
				showCreateModal = false;
				createSuccess = false;
			}, 1500);
		} catch (err: any) {
			createError = err?.response?.data?.detail || 'Failed to create student account';
		} finally {
			createLoading = false;
		}
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

		<!-- Search and Create Button -->
		<div class="mb-3 flex gap-2">
			<div class="relative flex-1">
				<Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
				<input
					type="text"
					placeholder="Search students..."
					class="w-full pl-9 pr-3 py-2 text-sm rounded-lg outline-none"
					style="border: 1px solid rgba(0,0,0,0.2); border-radius: 6px; background-color: rgba(255,255,255,0.8); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
					bind:value={searchQuery}
				/>
			</div>
			<button
				class="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold cursor-pointer"
				style="background: linear-gradient(to bottom, #22c55e, #16a34a);
				       color: white;
				       box-shadow: 0 2px 6px rgba(34,197,94,0.35), inset 0 1px 0 rgba(255,255,255,0.3);
				       border: 1px solid rgba(0,0,0,0.1);"
				onclick={openCreateModal}
			>
				<Plus class="w-4 h-4" />
				Add
			</button>
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

<!-- Create Student Modal -->
{#if showCreateModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4"
		style="background-color: rgba(0,0,0,0.5);">
		<div class="w-full max-w-md rounded-2xl overflow-hidden"
			style="background-color: white; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
			<!-- Modal Header -->
			<div class="px-5 py-4 flex items-center justify-between"
				style="background: linear-gradient(to bottom, #f0f4f8, #e2e8f0); border-bottom: 1px solid rgba(0,0,0,0.1);">
				<div class="flex items-center gap-2">
					<UserPlus class="w-5 h-5 text-green-600" />
					<h3 class="font-bold text-gray-800">Create Student Account</h3>
				</div>
				<button class="p-1 rounded-full hover:bg-gray-200 cursor-pointer" onclick={() => showCreateModal = false}>
					<X class="w-5 h-5 text-gray-500" />
				</button>
			</div>

			<!-- Modal Body -->
			<div class="p-5 space-y-4">
				{#if createSuccess}
					<div class="text-center py-6">
						<div class="w-16 h-16 rounded-full mx-auto mb-3 flex items-center justify-center"
							style="background: linear-gradient(to bottom, #22c55e, #16a34a);">
							<UserPlus class="w-8 h-8 text-white" />
						</div>
						<p class="text-lg font-bold text-green-700">Student Created!</p>
						<p class="text-sm text-gray-500 mt-1">Account is ready to use</p>
					</div>
				{:else}
					{#if createError}
						<div class="px-3 py-2 rounded-lg text-sm text-red-700"
							style="background-color: rgba(255,0,0,0.05); border: 1px solid rgba(220,50,50,0.2);">
							{createError}
						</div>
					{/if}

					<div>
						<label class="text-xs text-gray-500 mb-1 block">Username</label>
						<input type="text" bind:value={newUsername} placeholder="student_username"
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15);" />
					</div>

					<div>
						<label class="text-xs text-gray-500 mb-1 block">Password</label>
						<input type="password" bind:value={newPassword} placeholder="Create a password"
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15);" />
					</div>

					<div>
						<label class="text-xs text-gray-500 mb-1 block">Email</label>
						<input type="email" bind:value={newEmail} placeholder="student@email.com"
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15);" />
					</div>

					<div>
						<label class="text-xs text-gray-500 mb-1 block">Full Name</label>
						<input type="text" bind:value={newName} placeholder="Student Full Name"
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="border: 1px solid rgba(0,0,0,0.15);" />
					</div>

					<div>
						<label class="text-xs text-gray-500 mb-1 block">Program</label>
						<select bind:value={newProgram}
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none cursor-pointer"
							style="border: 1px solid rgba(0,0,0,0.15);">
							{#each programs as p}
								<option value={p}>{p}</option>
							{/each}
						</select>
					</div>

					<div class="grid grid-cols-2 gap-3">
						<div>
							<label class="text-xs text-gray-500 mb-1 block">Year</label>
							<select bind:value={newYear}
								class="w-full px-3 py-2.5 rounded-lg text-sm outline-none cursor-pointer"
								style="border: 1px solid rgba(0,0,0,0.15);">
								{#each [1, 2, 3, 4, 5] as y}
									<option value={y}>Year {y}</option>
								{/each}
							</select>
						</div>
						<div>
							<label class="text-xs text-gray-500 mb-1 block">Semester</label>
							<select bind:value={newSemester}
								class="w-full px-3 py-2.5 rounded-lg text-sm outline-none cursor-pointer"
								style="border: 1px solid rgba(0,0,0,0.15);">
								{#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as s}
									<option value={s}>Sem {s}</option>
								{/each}
							</select>
						</div>
					</div>
				{/if}
			</div>

			<!-- Modal Footer -->
			{#if !createSuccess}
			<div class="px-5 py-4 flex gap-3"
				style="background: linear-gradient(to bottom, #f0f4f8, #e2e8f0); border-top: 1px solid rgba(0,0,0,0.1);">
				<button
					class="flex-1 py-2.5 rounded-xl text-sm font-semibold cursor-pointer"
					style="background: #e5e7eb; color: #64748b; border: 1px solid rgba(0,0,0,0.1);"
					onclick={() => showCreateModal = false}
				>
					Cancel
				</button>
				<button
					class="flex-1 py-2.5 rounded-xl text-sm font-semibold cursor-pointer text-white disabled:opacity-50"
					style="background: linear-gradient(to bottom, #22c55e, #16a34a);
					       box-shadow: 0 2px 6px rgba(34,197,94,0.35), inset 0 1px 0 rgba(255,255,255,0.3);
					       border: 1px solid rgba(0,0,0,0.1);"
					disabled={createLoading || !newUsername || !newPassword || !newEmail || !newName}
					onclick={createStudent}
				>
					{#if createLoading}
						Creating...
					{:else}
						Create Student
					{/if}
				</button>
			</div>
			{/if}
		</div>
	</div>
{/if}
