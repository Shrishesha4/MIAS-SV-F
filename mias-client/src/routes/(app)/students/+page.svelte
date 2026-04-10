<script lang="ts">
	import { onMount } from 'svelte';
	import { facultyApi, type StudentForAssignment, type UnassignedPatient } from '$lib/api/faculty';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { GraduationCap, Search, BookOpen, Users, UserCheck, Link } from 'lucide-svelte';

	let activeTab = $state('students');
	const tabs = [
		{ id: 'students', label: 'Students', icon: Users },
		{ id: 'assignments', label: 'Patient Assignment', icon: UserCheck },
	];

	let students: StudentForAssignment[] = $state([]);
	let allStudents: StudentForAssignment[] = $state([]);
	let unassignedPatients: UnassignedPatient[] = $state([]);
	let loading = $state(true);
	let faculty: any = $state(null);

	let searchQuery = $state('');
	let patientSearchQuery = $state('');
	let selectedStudentForAssign: StudentForAssignment | null = $state(null);
	let assigning = $state(false);

	const filteredStudents = $derived(
		students.filter(s =>
			String(s.name ?? '').toLowerCase().includes(searchQuery.toLowerCase()) ||
			String(s.student_id ?? '').toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	const filteredUnassignedPatients = $derived(
		unassignedPatients.filter(p =>
			p.name.toLowerCase().includes(patientSearchQuery.toLowerCase()) ||
			(p.patient_id || '').toLowerCase().includes(patientSearchQuery.toLowerCase())
		)
	);

	async function assignPatient(patient: UnassignedPatient) {
		if (!selectedStudentForAssign || !faculty) return;
		assigning = true;
		try {
			await facultyApi.assignPatient(faculty.id, selectedStudentForAssign.id, patient.id);
			unassignedPatients = unassignedPatients.filter(p => p.id !== patient.id);
			allStudents = allStudents.map(student =>
				student.id === selectedStudentForAssign?.id
					? { ...student, assigned_patient_count: student.assigned_patient_count + 1 }
					: student
			);
			students = allStudents;
		} catch (err) {
			toastStore.addToast('Failed to assign patient', 'error');
		} finally {
			assigning = false;
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['FACULTY'])) return;
		try {
			faculty = await facultyApi.getMe();
			const [studentsData, patientsData] = await Promise.all([
				facultyApi.getStudents(faculty.id),
				facultyApi.getUnassignedPatients(faculty.id),
			]);
			allStudents = studentsData;
			students = studentsData;
			unassignedPatients = patientsData;
		} catch (err) {
			toastStore.addToast('Failed to load students', 'error');
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<TabBar {tabs} activeTab={activeTab} onchange={(id) => activeTab = id} />

		{#if activeTab === 'students'}
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

				<div class="mb-3 space-y-2">
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
					<div class="rounded-lg px-3 py-2 text-xs text-amber-800"
						style="background: linear-gradient(to bottom, rgba(254, 243, 199, 0.92), rgba(253, 230, 138, 0.72)); border: 1px solid rgba(217, 119, 6, 0.18);">
						Student account creation is restricted to the admin panel. Faculty can search and assign only.
					</div>
				</div>

				<div class="grid grid-cols-2 gap-2">
					<div class="text-center p-2 rounded-lg bg-blue-50">
						<p class="text-lg font-bold text-blue-600">{students.length}</p>
						<p class="text-[10px] text-gray-500">Total Students</p>
					</div>
					<div class="text-center p-2 rounded-lg bg-green-50">
						<p class="text-lg font-bold text-green-600">{students.reduce((count, student) => count + student.assigned_patient_count, 0)}</p>
						<p class="text-[10px] text-gray-500">Assigned Patients</p>
					</div>
				</div>
			</AquaCard>

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
									{#if student.department}
										<span class="flex items-center gap-1 text-gray-500">{student.department}</span>
									{/if}
								</div>
							{/if}
						</div>
						<div class="text-right shrink-0">
							<p class="text-xs text-gray-400">Patients</p>
							<p class="text-sm font-bold text-gray-700">{student.assigned_patient_count}</p>
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
		{:else if activeTab === 'assignments'}
			<AquaCard>
				{#snippet header()}
					<div class="flex items-center gap-2 w-full">
						<UserCheck class="w-5 h-5 text-blue-700" />
						<h2 class="text-sm font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
							Assign Patients to Students
						</h2>
					</div>
				{/snippet}
				<p class="text-xs text-gray-500">Select a student and then assign patients to them</p>
			</AquaCard>

			<AquaCard>
				<div class="flex items-center gap-2 mb-3">
					<GraduationCap class="w-4 h-4 text-gray-500" />
					<span class="text-xs font-semibold text-gray-700">Select Student</span>
				</div>
				<div class="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
					{#each allStudents as student}
						<button
							class="shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all cursor-pointer flex items-center gap-2"
							style="background: {selectedStudentForAssign?.id === student.id ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : 'linear-gradient(to bottom, #f8fafc, #f1f5f9)'};
							       color: {selectedStudentForAssign?.id === student.id ? 'white' : '#475569'};
							       border: 1px solid {selectedStudentForAssign?.id === student.id ? '#2563eb' : '#e2e8f0'};
							       box-shadow: {selectedStudentForAssign?.id === student.id ? '0 2px 4px rgba(37, 99, 235, 0.3)' : 'none'};"
							onclick={() => selectedStudentForAssign = student}
						>
							{student.name}
							<span class="px-1.5 py-0.5 text-[10px] font-bold rounded-full"
								style="background: {selectedStudentForAssign?.id === student.id ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.05)'};">
								{student.assigned_patient_count}
							</span>
						</button>
					{/each}
				</div>
				{#if allStudents.length === 0}
					<p class="text-sm text-gray-400 text-center py-2">No students available</p>
				{/if}
			</AquaCard>

			{#if selectedStudentForAssign}
				<AquaCard>
					<div class="flex items-center justify-between mb-3">
						<div class="flex items-center gap-2">
							<Users class="w-4 h-4 text-gray-500" />
							<span class="text-xs font-semibold text-gray-700">Unassigned Patients</span>
						</div>
						<span class="text-xs text-blue-600 font-semibold bg-blue-100 px-2 py-0.5 rounded-full">
							{unassignedPatients.length}
						</span>
					</div>

					<div class="relative mb-3">
						<Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
						<input
							type="text"
							placeholder="Search patients..."
							class="w-full pl-9 pr-3 py-2 text-sm rounded-lg outline-none"
							style="border: 1px solid rgba(0,0,0,0.15); background-color: rgba(255,255,255,0.8);"
							bind:value={patientSearchQuery}
						/>
					</div>

					<div class="space-y-2 max-h-80 overflow-y-auto">
						{#each filteredUnassignedPatients as patient}
							<div class="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-gradient-to-b from-white to-gray-50/50">
								<div class="relative shrink-0">
									{#if patient.photo}
										<img src={patient.photo} alt={patient.name} class="w-10 h-10 rounded-full object-cover border border-gray-200" />
									{:else}
										<Avatar name={patient.name} size="sm" />
									{/if}
								</div>
								<div class="flex-1 min-w-0">
									<p class="text-sm font-semibold text-gray-800">{patient.name}</p>
									<p class="text-xs text-gray-500">{patient.age} yrs · {patient.gender} · {patient.blood_group}</p>
									<p class="text-xs text-gray-400 truncate">{patient.primary_diagnosis || 'No diagnosis'}</p>
								</div>
								<button
									class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-50"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);"
									onclick={() => assignPatient(patient)}
									disabled={assigning}
								>
									<Link class="w-3 h-3" />
									Assign
								</button>
							</div>
						{/each}
					</div>

					{#if filteredUnassignedPatients.length === 0}
						<p class="text-sm text-gray-400 text-center py-4">No unassigned patients</p>
					{/if}
				</AquaCard>

				<AquaCard padding={false}>
					<div class="px-4 py-3 flex items-center gap-3"
						style="background: linear-gradient(to bottom, rgba(34, 197, 94, 0.1), rgba(34, 197, 94, 0.05));">
						<UserCheck class="w-5 h-5 text-green-600" />
						<div class="flex-1">
							<p class="text-sm font-semibold text-green-800">Assigning to: {selectedStudentForAssign.name}</p>
							<p class="text-xs text-green-600">Year {selectedStudentForAssign.year} · Sem {selectedStudentForAssign.semester}</p>
						</div>
						<span class="text-lg font-bold text-green-600">{selectedStudentForAssign.assigned_patient_count}</span>
					</div>
				</AquaCard>
			{:else}
				<div class="text-center py-12">
					<UserCheck class="w-10 h-10 text-gray-300 mx-auto mb-2" />
					<p class="text-sm text-gray-400">Select a student to assign patients</p>
				</div>
			{/if}
		{/if}
	{/if}
</div>
