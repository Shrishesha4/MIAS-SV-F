<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import {
		adminApi,
		type AcademicGroup,
		type AcademicOverviewResponse,
		type AcademicOverviewStudent,
		type AcademicTarget,
		type AcademicWeightageItem,
		type Programme,
		type StudentAcademicProgress
	} from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import {
		Users,
		BarChart3,
		MessageSquareText,
		Activity,
		Search,
		ArrowRight,
		ShieldCheck,
		Target,
		BookOpen,
		Plus,
		Edit3,
		Trash2,
		CheckCircle2,
		Settings2,
		TrendingUp,
		Award,
		Clock3,
		Filter,
		X
	} from 'lucide-svelte';

	type TabId = 'groups' | 'performance' | 'feedback' | 'activity' | 'analytics';
	type ApiError = { response?: { data?: { detail?: string } } };

	const auth = get(authStore);

	const tabs: Array<{ id: TabId; label: string; icon: typeof Users }> = [
		{ id: 'groups', label: 'Groups', icon: Users },
		{ id: 'performance', label: 'Performance', icon: BarChart3 },
		{ id: 'feedback', label: 'Feedback', icon: MessageSquareText },
		{ id: 'activity', label: 'Activity', icon: Activity },
		{ id: 'analytics', label: 'Analytics', icon: TrendingUp }
	];

	const degreeTypes = ['Undergraduate', 'Postgraduate', 'Diploma', 'Certificate', 'Doctoral'];
	const targetCategories = ['ACADEMIC', 'CLINICAL', 'LABORATORY', 'ADMINISTRATIVE'];

	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let activeTab = $state<TabId>('groups');
	let searchQuery = $state('');

	let programmes = $state<Programme[]>([]);
	let groups = $state<AcademicGroup[]>([]);
	let targets = $state<AcademicTarget[]>([]);
	let weightages = $state<AcademicWeightageItem[]>([]);
	let students = $state<AcademicOverviewStudent[]>([]);

	let selectedProgrammeId = $state('');
	let selectedGroupId = $state('');
	let selectedStudentId = $state('');

	let progressLoading = $state(false);
	let progressCache = $state<Record<string, StudentAcademicProgress>>({});

	let showProgrammeModal = $state(false);
	let editingProgrammeId = $state('');
	let programmeName = $state('');
	let programmeCode = $state('');
	let programmeDescription = $state('');
	let programmeDegreeType = $state('');
	let programmeDuration = $state('');
	let programmeIsActive = $state(true);

	let showGroupModal = $state(false);
	let editingGroupId = $state('');
	let groupProgrammeId = $state('');
	let groupName = $state('');
	let groupDescription = $state('');
	let groupIsActive = $state(true);
	let groupStudentIds = $state<string[]>([]);

	let showTargetModal = $state(false);
	let editingTargetId = $state('');
	let targetGroupId = $state('');
	let targetMetricName = $state('');
	let targetCategory = $state('ACADEMIC');
	let targetValue = $state(0);
	let targetSortOrder = $state(0);
	let targetFormDefinitionId = $state('');

	let showStudentProgressModal = $state(false);
	let progressStudentId = $state('');
	let progressStudentName = $state('');

	const shellStyle =
		'background: linear-gradient(180deg, #dbe3ee 0%, #d5dee9 52%, #d2dae5 100%);';
	const cardStyle =
		'background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(247,249,252,0.96)); border: 1px solid rgba(130,145,166,0.22); box-shadow: 0 3px 12px rgba(73,93,124,0.12), inset 0 1px 0 rgba(255,255,255,0.72);';



	const filteredGroups = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();

		return [...groups]
			.filter((group) => !selectedProgrammeId || group.programme_id === selectedProgrammeId)
			.filter((group) => {
				if (!query) return true;
				return [group.name, group.description ?? '', group.programme_name ?? '']
					.join(' ')
					.toLowerCase()
					.includes(query);
			})
			.sort((left, right) => left.name.localeCompare(right.name));
	});

	const filteredStudents = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();

		return [...students]
			.filter((student) => !selectedProgrammeId || student.program === getProgrammeName(selectedProgrammeId))
			.filter((student) => !selectedGroupId || student.academic_group_id === selectedGroupId)
			.filter((student) => {
				if (!query) return true;
				return [
					student.name,
					student.student_id,
					student.program,
					student.academic_group_name ?? '',
					student.academic_standing ?? ''
				]
					.join(' ')
					.toLowerCase()
					.includes(query);
			})
			.sort((left, right) => left.name.localeCompare(right.name));
	});

	const filteredTargets = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();

		return [...targets]
			.filter((target) => !selectedProgrammeId || target.programme_id === selectedProgrammeId)
			.filter((target) => !selectedGroupId || target.group_id === selectedGroupId)
			.filter((target) => {
				if (!query) return true;
				return [
					target.metric_name,
					target.category,
					target.group_name ?? '',
					target.programme_name ?? '',
					target.form_name ?? ''
				]
					.join(' ')
					.toLowerCase()
					.includes(query);
			})
			.sort((left, right) => {
				if (left.sort_order !== right.sort_order) return left.sort_order - right.sort_order;
				return left.metric_name.localeCompare(right.metric_name);
			});
	});

	const filteredWeightages = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();

		return [...weightages]
			.filter((item) =>
				!query
					? true
					: [item.name ?? '', item.department ?? '', item.procedure_name ?? '', item.section ?? '']
							.join(' ')
							.toLowerCase()
							.includes(query)
			)
			.sort((left, right) => {
				const leftConfigured = left.has_weightage ? 1 : 0;
				const rightConfigured = right.has_weightage ? 1 : 0;
				if (leftConfigured !== rightConfigured) return rightConfigured - leftConfigured;
				return (left.name ?? '').localeCompare(right.name ?? '');
			});
	});

	const availableStudents = $derived.by(() => {
		const selectedProgramme = programmes.find((programme) => programme.id === groupProgrammeId);
		const eligible = selectedProgramme
			? students.filter((student) => student.program === selectedProgramme.name)
			: students;

		return [...eligible].sort((left, right) => left.name.localeCompare(right.name));
	});

	const selectableGroups = $derived.by(() => {
		return [...groups]
			.filter((group) => !selectedProgrammeId || group.programme_id === selectedProgrammeId)
			.sort((left, right) => left.name.localeCompare(right.name));
	});

	const availableTargetForms = $derived.by(() => {
		return [...weightages].sort((left, right) => {
			const leftLabel = [left.department ?? '', left.name ?? '', left.procedure_name ?? ''].join(' ');
			const rightLabel = [right.department ?? '', right.name ?? '', right.procedure_name ?? ''].join(' ');
			return leftLabel.localeCompare(rightLabel);
		});
	});

	const selectedGroup = $derived(groups.find((group) => group.id === selectedGroupId) ?? null);
	const selectedStudentProgress = $derived(progressStudentId ? progressCache[progressStudentId] ?? null : null);

	const totalProgrammeCount = $derived(programmes.length);

	const activeGroupCount = $derived(groups.filter((group) => group.is_active).length);
	const configuredWeightageCount = $derived(weightages.filter((item) => item.has_weightage).length);

	const analyticsSummary = $derived.by(() => {
		const relevantStudents = filteredStudents;
		const progressItems = relevantStudents
			.map((student) => progressCache[student.id])
			.filter(Boolean) as StudentAcademicProgress[];

		const approvedCaseRecords = progressItems.reduce(
			(total, item) => total + (item.summary?.approved_case_records ?? 0),
			0
		);
		const totalEarnedPoints = progressItems.reduce(
			(total, item) => total + (item.summary?.total_earned_points ?? 0),
			0
		);
		const avgProgress =
			progressItems.length > 0
				? Math.round(
						progressItems.reduce(
							(total, item) => total + (item.summary?.overall_percent ?? 0),
							0
						) / progressItems.length
					)
				: 0;
		const avgGpa =
			relevantStudents.length > 0
				? (
						relevantStudents.reduce((total, student) => total + Number(student.gpa ?? 0), 0) /
						relevantStudents.length
					).toFixed(2)
				: '0.00';

		return {
			studentCount: relevantStudents.length,
			groupCount: filteredGroups.length,
			approvedCaseRecords,
			totalEarnedPoints,
			avgProgress,
			avgGpa
		};
	});

	const standingBreakdown = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const student of filteredStudents) {
			const key = student.academic_standing || 'Unknown';
			counts[key] = (counts[key] ?? 0) + 1;
		}
		return Object.entries(counts)
			.map(([label, count]) => ({ label, count }))
			.sort((left, right) => right.count - left.count);
	});

	const groupPerformanceRows = $derived.by(() => {
		return filteredGroups.map((group) => {
			const groupStudents = filteredStudents.filter((student) => student.academic_group_id === group.id);
			const progressItems = groupStudents
				.map((student) => progressCache[student.id])
				.filter(Boolean) as StudentAcademicProgress[];

			const avgProgress =
				progressItems.length > 0
					? Math.round(
							progressItems.reduce(
								(total, item) => total + (item.summary?.overall_percent ?? 0),
								0
							) / progressItems.length
						)
					: 0;

			const approvedCaseRecords = progressItems.reduce(
				(total, item) => total + (item.summary?.approved_case_records ?? 0),
				0
			);

			const earnedPoints = progressItems.reduce(
				(total, item) => total + (item.summary?.total_earned_points ?? 0),
				0
			);

			return {
				id: group.id,
				name: group.name,
				programmeName: group.programme_name ?? getProgrammeName(group.programme_id),
				studentCount: groupStudents.length,
				targetCount: group.target_count,
				avgProgress,
				approvedCaseRecords,
				earnedPoints
			};
		});
	});

	const feedbackRows = $derived.by(() => {
		const rows: Array<{
			id: string;
			studentId: string;
			studentName: string;
			groupName: string;
			formName: string;
			department: string;
			score: number;
			comments: string;
			status: string;
		}> = [];

		for (const student of filteredStudents) {
			const progress = progressCache[student.id];
			if (!progress) continue;

			for (const unmatched of progress.weightages?.unmatched_records ?? []) {
				if (!unmatched.form_name && !unmatched.department) continue;
				rows.push({
					id: unmatched.id,
					studentId: student.student_id,
					studentName: student.name,
					groupName: student.academic_group_name ?? 'Unassigned',
					formName: unmatched.form_name ?? 'Case Record',
					department: unmatched.department ?? 'General',
					score: 0,
					comments: unmatched.status ?? 'Recorded activity pending mapped feedback',
					status: unmatched.status ?? 'Pending'
				});
			}
		}

		return rows.slice(0, 20);
	});

	const activityRows = $derived.by(() => {
		const rows: Array<{
			id: string;
			studentName: string;
			groupName: string;
			label: string;
			value: string;
			date: string;
		}> = [];

		for (const student of filteredStudents) {
			const progress = progressCache[student.id];
			if (!progress) continue;

			for (const item of progress.weightages?.items ?? []) {
				if ((item.approved_count ?? 0) <= 0) continue;
				rows.push({
					id: `${student.id}-${item.form_definition_id}`,
					studentName: student.name,
					groupName: student.academic_group_name ?? 'Unassigned',
					label: item.name ?? 'Case Record',
					value: `${item.approved_count} approved • ${item.earned_points} pts`,
					date: item.department ?? 'General'
				});
			}
		}

		return rows
			.sort((left, right) => right.value.localeCompare(left.value))
			.slice(0, 24);
	});

	onMount(async () => {
		if (auth.role !== 'ACADEMIC_MANAGER') {
			void goto(resolve('/dashboard'));
			return;
		}

		await loadWorkspace();
	});

	async function loadWorkspace() {
		loading = true;
		error = '';
		try {
			const overview: AcademicOverviewResponse = await adminApi.getAcademicsOverview();
			programmes = overview.programmes ?? [];
			groups = overview.groups ?? [];
			targets = overview.targets ?? [];
			weightages = overview.weightages ?? [];
			students = overview.students ?? [];

			if (selectedProgrammeId && !programmes.some((programme) => programme.id === selectedProgrammeId)) {
				selectedProgrammeId = '';
			}
			if (selectedGroupId && !groups.some((group) => group.id === selectedGroupId)) {
				selectedGroupId = '';
			}
			if (selectedStudentId && !students.some((student) => student.id === selectedStudentId)) {
				selectedStudentId = '';
			}

			await preloadStudentProgress();
		} catch (errorValue: unknown) {
			error = (errorValue as ApiError)?.response?.data?.detail || 'Failed to load academic manager workspace';
		} finally {
			loading = false;
		}
	}

	async function preloadStudentProgress() {
		progressLoading = true;
		try {
			const nextCache: Record<string, StudentAcademicProgress> = {};
			await Promise.all(
				students.map(async (student) => {
					try {
						nextCache[student.id] = await adminApi.getStudentAcademicProgress(student.id);
					} catch {
						// keep page usable even if one student progress payload fails
					}
				})
			);
			progressCache = nextCache;
		} finally {
			progressLoading = false;
		}
	}

	function switchTab(tabId: string) {
		activeTab = tabId as TabId;
		searchQuery = '';
		if (tabId !== 'groups' && tabId !== 'performance' && tabId !== 'feedback' && tabId !== 'activity' && tabId !== 'analytics') {
			selectedGroupId = '';
		}
	}

	function clearFilters() {
		selectedProgrammeId = '';
		selectedGroupId = '';
		selectedStudentId = '';
		searchQuery = '';
	}

	function getProgrammeName(programmeId: string) {
		return programmes.find((programme) => programme.id === programmeId)?.name ?? 'Unknown Programme';
	}

	function getGroupName(groupId: string) {
		return groups.find((group) => group.id === groupId)?.name ?? 'Unknown Group';
	}

	async function saveProgramme() {
		if (!programmeName.trim() || !programmeCode.trim()) {
			toastStore.addToast('Programme name and code are required', 'error');
			return;
		}

		saving = true;
		try {
			const payload = {
				name: programmeName.trim(),
				code: programmeCode.trim().toUpperCase(),
				description: programmeDescription.trim() || undefined,
				degree_type: programmeDegreeType || undefined,
				duration_years: programmeDuration.trim() || undefined,
				is_active: programmeIsActive
			};

			if (editingProgrammeId) {
				await adminApi.updateProgramme(editingProgrammeId, payload);
				toastStore.addToast('Programme updated successfully', 'success');
			} else {
				await adminApi.createProgramme(payload);
				toastStore.addToast('Programme created successfully', 'success');
			}

			showProgrammeModal = false;
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to save programme',
				'error'
			);
		} finally {
			saving = false;
		}
	}

	function openCreateGroup(prefillProgrammeId = selectedProgrammeId) {
		editingGroupId = '';
		groupProgrammeId = prefillProgrammeId || programmes[0]?.id || '';
		groupName = '';
		groupDescription = '';
		groupIsActive = true;
		groupStudentIds = [];
		showGroupModal = true;
	}

	function openEditGroup(group: AcademicGroup) {
		editingGroupId = group.id;
		groupProgrammeId = group.programme_id;
		groupName = group.name;
		groupDescription = group.description ?? '';
		groupIsActive = group.is_active;
		groupStudentIds = [...group.student_ids];
		showGroupModal = true;
	}

	function toggleGroupStudent(studentId: string) {
		if (groupStudentIds.includes(studentId)) {
			groupStudentIds = groupStudentIds.filter((id) => id !== studentId);
		} else {
			groupStudentIds = [...groupStudentIds, studentId];
		}
	}

	async function saveGroup() {
		if (!groupProgrammeId) {
			toastStore.addToast('Select a programme first', 'error');
			return;
		}
		if (!groupName.trim()) {
			toastStore.addToast('Group name is required', 'error');
			return;
		}

		saving = true;
		try {
			const payload = {
				programme_id: groupProgrammeId,
				name: groupName.trim(),
				description: groupDescription.trim() || undefined,
				is_active: groupIsActive,
				student_ids: groupStudentIds
			};

			if (editingGroupId) {
				await adminApi.updateAcademicGroup(editingGroupId, payload);
				toastStore.addToast('Academic group updated successfully', 'success');
			} else {
				await adminApi.createAcademicGroup(payload);
				toastStore.addToast('Academic group created successfully', 'success');
			}

			showGroupModal = false;
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to save academic group',
				'error'
			);
		} finally {
			saving = false;
		}
	}

	async function deleteGroup(group: AcademicGroup) {
		if (!window.confirm(`Delete ${group.name}? Assigned students will be unassigned from this group.`)) {
			return;
		}

		try {
			await adminApi.deleteAcademicGroup(group.id);
			toastStore.addToast('Academic group deleted successfully', 'success');
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to delete academic group',
				'error'
			);
		}
	}

	function openCreateTarget(prefillGroupId = selectedGroupId || selectableGroups[0]?.id || '') {
		editingTargetId = '';
		targetGroupId = prefillGroupId;
		targetMetricName = '';
		targetCategory = 'ACADEMIC';
		targetValue = 0;
		targetSortOrder = 0;
		targetFormDefinitionId = '';
		showTargetModal = true;
	}

	function openEditTarget(target: AcademicTarget) {
		editingTargetId = target.id;
		targetGroupId = target.group_id;
		targetMetricName = target.metric_name;
		targetCategory = target.category;
		targetValue = target.target_value;
		targetSortOrder = target.sort_order;
		targetFormDefinitionId = target.form_definition_id ?? '';
		showTargetModal = true;
	}

	function applyFormToTarget(formDefinitionId: string) {
		targetFormDefinitionId = formDefinitionId;
		const selected = availableTargetForms.find((item) => item.form_definition_id === formDefinitionId);
		if (selected && !targetMetricName.trim()) {
			targetMetricName = selected.name ?? '';
		}
	}

	async function saveTarget() {
		if (!targetGroupId) {
			toastStore.addToast('Select an academic group first', 'error');
			return;
		}
		if (!targetMetricName.trim()) {
			toastStore.addToast('Metric name is required', 'error');
			return;
		}

		saving = true;
		try {
			const payload = {
				group_id: targetGroupId,
				form_definition_id: targetFormDefinitionId || undefined,
				metric_name: targetMetricName.trim(),
				category: targetCategory,
				target_value: Number(targetValue) || 0,
				sort_order: Number(targetSortOrder) || 0
			};

			if (editingTargetId) {
				await adminApi.updateAcademicTarget(editingTargetId, payload);
				toastStore.addToast('Academic target updated successfully', 'success');
			} else {
				await adminApi.createAcademicTarget(payload);
				toastStore.addToast('Academic target created successfully', 'success');
			}

			showTargetModal = false;
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to save academic target',
				'error'
			);
		} finally {
			saving = false;
		}
	}

	async function deleteTarget(target: AcademicTarget) {
		if (!window.confirm(`Delete target "${target.metric_name}"?`)) return;

		try {
			await adminApi.deleteAcademicTarget(target.id);
			toastStore.addToast('Academic target deleted successfully', 'success');
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to delete academic target',
				'error'
			);
		}
	}

	async function updateWeightage(item: AcademicWeightageItem, nextPoints: number) {
		try {
			await adminApi.updateAcademicWeightage(item.form_definition_id, {
				points: Math.max(0, Number(nextPoints) || 0)
			});
			toastStore.addToast('Weightage updated successfully', 'success');
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to update weightage',
				'error'
			);
		}
	}

	async function openStudentProgress(student: AcademicOverviewStudent) {
		progressStudentId = student.id;
		progressStudentName = student.name;
		showStudentProgressModal = true;

		if (!progressCache[student.id]) {
			try {
				progressLoading = true;
				progressCache = {
					...progressCache,
					[student.id]: await adminApi.getStudentAcademicProgress(student.id)
				};
			} catch (errorValue: unknown) {
				toastStore.addToast(
					(errorValue as ApiError)?.response?.data?.detail || 'Failed to load student progress',
					'error'
				);
			} finally {
				progressLoading = false;
			}
		}
	}
</script>

<svelte:head>
	<title>Academic Manager Workspace | MIAS</title>
</svelte:head>

<div class="min-h-screen px-3 py-3 sm:px-4 sm:py-4 lg:px-6" style={shellStyle}>
	<div class="mx-auto flex w-full max-w-7xl flex-col gap-4">
		<div class="rounded-[28px] p-4 sm:p-5" style={cardStyle}>
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
				<div>
					<p class="text-[11px] font-black uppercase tracking-[0.24em] text-slate-500">
						Academic Manager
					</p>
					<h1 class="mt-1 text-xl font-black text-slate-800 sm:text-2xl">
						Academic Manager Workspace
					</h1>
					<p class="mt-1 text-sm text-slate-500">
						Real academic operations dashboard powered by live programme, group, target, and student progress data.
					</p>
				</div>

				<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
					<div class="rounded-2xl px-3 py-3"
						style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.28);">
						<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Programmes</p>
						<p class="mt-1 text-xl font-black text-slate-900">{totalProgrammeCount}</p>
					</div>
					<div class="rounded-2xl px-3 py-3"
						style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.28);">
						<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Active Groups</p>
						<p class="mt-1 text-xl font-black text-emerald-700">{activeGroupCount}</p>
					</div>
					<div class="rounded-2xl px-3 py-3"
						style="background: rgba(250,245,255,0.9); border: 1px solid rgba(192,132,252,0.28);">
						<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Students</p>
						<p class="mt-1 text-xl font-black text-violet-700">{students.length}</p>
					</div>
					<div class="rounded-2xl px-3 py-3"
						style="background: rgba(255,247,237,0.9); border: 1px solid rgba(251,146,60,0.28);">
						<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Weighted Forms</p>
						<p class="mt-1 text-xl font-black text-orange-600">{configuredWeightageCount}</p>
					</div>
				</div>
			</div>

			<div class="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
				<div class="min-w-0">
					<TabBar tabs={tabs} activeTab={activeTab} onchange={switchTab} variant="jiggle" stretch={false} />
				</div>

				<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
					<div class="relative min-w-0 sm:w-[280px]">
						<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Search workspace..."
							class="w-full rounded-2xl border px-10 py-2.5 text-sm font-medium text-slate-700 outline-none"
							style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24); box-shadow: inset 0 1px 2px rgba(15,23,42,0.06);"
						/>
					</div>

					<div class="flex items-center gap-2">
						<div class="flex items-center gap-2 rounded-2xl border px-3 py-2"
							style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);">
							<Filter class="h-4 w-4 text-slate-400" />
							<select
								bind:value={selectedProgrammeId}
								class="bg-transparent text-sm font-semibold text-slate-700 outline-none"
							>
								<option value="">All programmes</option>
								{#each programmes as programme (programme.id)}
									<option value={programme.id}>{programme.name}</option>
								{/each}
							</select>
						</div>

						<div class="flex items-center gap-2 rounded-2xl border px-3 py-2"
							style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);">
							<Users class="h-4 w-4 text-slate-400" />
							<select
								bind:value={selectedGroupId}
								class="bg-transparent text-sm font-semibold text-slate-700 outline-none"
							>
								<option value="">All groups</option>
								{#each selectableGroups as group (group.id)}
									<option value={group.id}>{group.name}</option>
								{/each}
							</select>
						</div>

						<button
							class="flex items-center gap-1 rounded-2xl px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-600 cursor-pointer"
							style="background: rgba(255,255,255,0.96); border: 1px solid rgba(148,163,184,0.24);"
							onclick={clearFilters}
						>
							<X class="h-3.5 w-3.5" />
							Clear
						</button>
					</div>
				</div>
			</div>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<div class="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
			</div>
		{:else if error}
			<AquaCard>
				<div class="py-8 text-center">
					<p class="text-sm font-semibold text-red-600">{error}</p>
				</div>
			</AquaCard>
		{:else if activeTab === 'groups'}
			<div class="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.9fr)]">
				<div class="space-y-4">
					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center justify-between gap-3">
							<div class="flex items-center gap-2">
								<Users class="h-4 w-4 text-slate-500" />
								<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Academic Groups</p>
							</div>
							<AquaButton onclick={() => openCreateGroup()}>
								<Plus class="mr-1 h-4 w-4" /> Add Group
							</AquaButton>
						</div>

						<div class="space-y-3">
							{#if filteredGroups.length === 0}
								<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
									<Users class="mx-auto h-10 w-10 text-slate-300" />
									<p class="mt-4 text-base font-black text-slate-700">No academic groups found</p>
									<p class="mt-2 text-sm text-slate-500">
										Create a group or adjust your filters to see live academic group data.
									</p>
								</div>
							{:else}
								{#each filteredGroups as group (group.id)}
									<div
										class="rounded-[22px] p-4"
										style={`background: ${selectedGroupId === group.id ? 'linear-gradient(to bottom, rgba(239,246,255,0.98), rgba(219,234,254,0.96))' : 'linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96))'}; border: 1px solid ${selectedGroupId === group.id ? 'rgba(59,130,246,0.28)' : 'rgba(148,163,184,0.18)'};`}
									>
										<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
											<div class="min-w-0">
												<div class="flex items-center gap-2">
													<h3 class="truncate text-base font-black text-slate-900">{group.name}</h3>
													{#if group.is_active}
														<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]"
															style="background: rgba(220,252,231,0.95); color: #15803d;">
															Active
														</span>
													{:else}
														<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]"
															style="background: rgba(254,226,226,0.95); color: #b91c1c;">
															Inactive
														</span>
													{/if}
												</div>
												<p class="mt-1 text-xs font-black uppercase tracking-[0.18em] text-violet-600">
													{group.programme_name ?? getProgrammeName(group.programme_id)}
												</p>
												{#if group.description}
													<p class="mt-2 text-sm text-slate-600">{group.description}</p>
												{/if}
												<div class="mt-3 flex flex-wrap gap-2">
													<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
														style="background: rgba(239,246,255,0.95); color: #1d4ed8;">
														{group.student_count} students
													</span>
													<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
														style="background: rgba(255,247,237,0.95); color: #c2410c;">
														{group.target_count} targets
													</span>
												</div>
											</div>

											<div class="flex flex-wrap gap-2 md:justify-end">
												<button
													class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
													style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 6px rgba(37,99,235,0.25);"
													onclick={() => (selectedGroupId = group.id)}
												>
													<ArrowRight class="h-3.5 w-3.5" /> View
												</button>
												<button
													class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
													style="background: linear-gradient(to bottom, #64748b, #475569); box-shadow: 0 2px 6px rgba(71,85,105,0.25);"
													onclick={() => openEditGroup(group)}
												>
													<Edit3 class="h-3.5 w-3.5" /> Edit
												</button>
												<button
													class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
													style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 2px 6px rgba(220,38,38,0.25);"
													onclick={() => deleteGroup(group)}
												>
													<Trash2 class="h-3.5 w-3.5" /> Delete
												</button>
											</div>
										</div>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				</div>

				<div class="space-y-4">
					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center gap-2">
							<ShieldCheck class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Selected Group Summary</p>
						</div>

						{#if selectedGroup}
							<div class="space-y-3">
								<div class="rounded-[22px] px-4 py-4"
									style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.22);">
									<p class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Group</p>
									<p class="mt-1 text-lg font-black text-slate-900">{selectedGroup.name}</p>
									<p class="mt-1 text-sm text-slate-600">{selectedGroup.programme_name ?? getProgrammeName(selectedGroup.programme_id)}</p>
								</div>

								<div class="grid grid-cols-2 gap-2">
									<div class="rounded-2xl px-3 py-3"
										style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.22);">
										<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Students</p>
										<p class="mt-1 text-xl font-black text-emerald-700">{selectedGroup.student_count}</p>
									</div>
									<div class="rounded-2xl px-3 py-3"
										style="background: rgba(255,247,237,0.9); border: 1px solid rgba(251,146,60,0.22);">
										<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Targets</p>
										<p class="mt-1 text-xl font-black text-orange-600">{selectedGroup.target_count}</p>
									</div>
								</div>

								<div class="rounded-[22px] border px-4 py-4"
									style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.18);">
									<p class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Students in group</p>
									<div class="mt-3 space-y-2">
										{#each filteredStudents.filter((student) => student.academic_group_id === selectedGroup.id).slice(0, 8) as student (student.id)}
											<button
												class="flex w-full items-center justify-between rounded-2xl px-3 py-3 text-left cursor-pointer"
												style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);"
												onclick={() => openStudentProgress(student)}
											>
												<div class="min-w-0">
													<p class="truncate text-sm font-black text-slate-900">{student.name}</p>
													<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
														{student.student_id} • GPA {student.gpa}
													</p>
												</div>
												<ArrowRight class="h-4 w-4 shrink-0 text-slate-300" />
											</button>
										{/each}
										{#if filteredStudents.filter((student) => student.academic_group_id === selectedGroup.id).length === 0}
											<p class="text-sm text-slate-500">No students assigned to this group.</p>
										{/if}
									</div>
								</div>
							</div>
						{:else}
							<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
								<Users class="mx-auto h-10 w-10 text-slate-300" />
								<p class="mt-4 text-base font-black text-slate-700">Select a group</p>
								<p class="mt-2 text-sm text-slate-500">
									Choose a live academic group from the list to inspect its students and targets.
								</p>
							</div>
						{/if}
					</div>

					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center justify-between gap-3">
							<div class="flex items-center gap-2">
								<Target class="h-4 w-4 text-slate-500" />
								<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Targets</p>
							</div>
							<AquaButton onclick={() => openCreateTarget()}>
								<Plus class="mr-1 h-4 w-4" /> Add Target
							</AquaButton>
						</div>

						<div class="space-y-2">
							{#each filteredTargets.slice(0, 8) as target (target.id)}
								<div class="rounded-2xl px-3 py-3"
									style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);">
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="truncate text-sm font-black text-slate-900">{target.metric_name}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{target.group_name ?? getGroupName(target.group_id)} • {target.category}
											</p>
										</div>
										<div class="text-right">
											<p class="text-sm font-black text-emerald-700">{target.target_value}</p>
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Target</p>
										</div>
									</div>
									<div class="mt-3 flex gap-2">
										<button
											class="rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #64748b, #475569);"
											onclick={() => openEditTarget(target)}
										>
											Edit
										</button>
										<button
											class="rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
											onclick={() => deleteTarget(target)}
										>
											Delete
										</button>
									</div>
								</div>
							{/each}
							{#if filteredTargets.length === 0}
								<p class="text-sm text-slate-500">No targets found for the current filters.</p>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{:else if activeTab === 'performance'}
			<div class="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<BarChart3 class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Student Performance</p>
					</div>

					<div class="space-y-3">
						{#if filteredStudents.length === 0}
							<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
								<BarChart3 class="mx-auto h-10 w-10 text-slate-300" />
								<p class="mt-4 text-base font-black text-slate-700">No students found</p>
								<p class="mt-2 text-sm text-slate-500">Adjust filters to view live student performance data.</p>
							</div>
						{:else}
							{#each filteredStudents as student (student.id)}
								{@const progress = progressCache[student.id]}
								<div class="rounded-[22px] p-4"
									style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); border: 1px solid rgba(148,163,184,0.18);">
									<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
										<div class="min-w-0">
											<p class="truncate text-base font-black text-slate-900">{student.name}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{student.student_id} • {student.program} • {student.academic_group_name ?? 'Unassigned'}
											</p>
										</div>

										<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
											<div class="rounded-2xl px-3 py-2"
												style="background: rgba(239,246,255,0.95);">
												<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Progress</p>
												<p class="mt-1 text-lg font-black text-blue-600">{Math.round(progress?.summary?.overall_percent ?? 0)}%</p>
											</div>
											<div class="rounded-2xl px-3 py-2"
												style="background: rgba(240,253,244,0.95);">
												<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Approved</p>
												<p class="mt-1 text-lg font-black text-emerald-700">{progress?.summary?.approved_case_records ?? 0}</p>
											</div>
											<div class="rounded-2xl px-3 py-2"
												style="background: rgba(255,247,237,0.95);">
												<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Points</p>
												<p class="mt-1 text-lg font-black text-orange-600">{progress?.summary?.total_earned_points ?? 0}</p>
											</div>
											<div class="rounded-2xl px-3 py-2"
												style="background: rgba(250,245,255,0.95);">
												<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">GPA</p>
												<p class="mt-1 text-lg font-black text-violet-700">{student.gpa}</p>
											</div>
										</div>
									</div>

									<div class="mt-4 flex items-center justify-between gap-3">
										<div class="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
											<div
												class="h-full rounded-full"
												style={`width: ${Math.min(Math.round(progress?.summary?.overall_percent ?? 0), 100)}%; background: linear-gradient(to right, #3b82f6, #10b981);`}
											></div>
										</div>
										<button
											class="rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
											onclick={() => openStudentProgress(student)}
										>
											View Details
										</button>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>

				<div class="space-y-4">
					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center gap-2">
							<Award class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Performance Summary</p>
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Avg Progress</p>
								<p class="mt-1 text-xl font-black text-blue-600">{analyticsSummary.avgProgress}%</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Avg GPA</p>
								<p class="mt-1 text-xl font-black text-emerald-700">{analyticsSummary.avgGpa}</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(255,247,237,0.9); border: 1px solid rgba(251,146,60,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Approved Records</p>
								<p class="mt-1 text-xl font-black text-orange-600">{analyticsSummary.approvedCaseRecords}</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(250,245,255,0.9); border: 1px solid rgba(192,132,252,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Earned Points</p>
								<p class="mt-1 text-xl font-black text-violet-700">{analyticsSummary.totalEarnedPoints}</p>
							</div>
						</div>
					</div>

					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center gap-2">
							<ShieldCheck class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Academic Standing</p>
						</div>

						<div class="space-y-2">
							{#each standingBreakdown as item (item.label)}
								<div class="flex items-center justify-between rounded-2xl px-3 py-3"
									style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);">
									<p class="text-sm font-black text-slate-800">{item.label}</p>
									<p class="text-sm font-black text-slate-500">{item.count}</p>
								</div>
							{/each}
							{#if standingBreakdown.length === 0}
								<p class="text-sm text-slate-500">No standing data available.</p>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{:else if activeTab === 'feedback'}
			<div class="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<MessageSquareText class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Feedback Stream</p>
					</div>

					<div class="space-y-3">
						{#if feedbackRows.length === 0}
							<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
								<MessageSquareText class="mx-auto h-10 w-10 text-slate-300" />
								<p class="mt-4 text-base font-black text-slate-700">No feedback items available</p>
								<p class="mt-2 text-sm text-slate-500">
									Feedback is derived from real academic progress and unmatched record activity already in the app.
								</p>
							</div>
						{:else}
							{#each feedbackRows as row (row.id)}
								<div class="rounded-[22px] p-4"
									style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); border: 1px solid rgba(148,163,184,0.18);">
									<div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
										<div class="min-w-0">
											<p class="text-base font-black text-slate-900">{row.studentName}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{row.studentId} • {row.groupName}
											</p>
											<p class="mt-2 text-sm font-semibold text-slate-700">{row.formName}</p>
											<p class="mt-1 text-xs text-slate-500">{row.department}</p>
											<p class="mt-3 text-sm text-slate-600">{row.comments}</p>
										</div>

										<div class="flex flex-col items-end gap-2">
											<span class="rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-[0.16em]"
												style="background: rgba(239,246,255,0.95); color: #1d4ed8;">
												{row.status}
											</span>
											<span class="rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-[0.16em]"
												style="background: rgba(255,247,237,0.95); color: #c2410c;">
												Score {row.score}
											</span>
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>

				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<TrendingUp class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Feedback Summary</p>
					</div>

					<div class="grid grid-cols-2 gap-2">
						<div class="rounded-2xl px-3 py-3"
							style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.22);">
							<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Items</p>
							<p class="mt-1 text-xl font-black text-blue-600">{feedbackRows.length}</p>
						</div>
						<div class="rounded-2xl px-3 py-3"
							style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.22);">
							<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Students</p>
							<p class="mt-1 text-xl font-black text-emerald-700">{new Set(feedbackRows.map((row) => row.studentId)).size}</p>
						</div>
					</div>
				</div>
			</div>
		{:else if activeTab === 'activity'}
			<div class="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<Activity class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Academic Activity</p>
					</div>

					<div class="space-y-3">
						{#if activityRows.length === 0}
							<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
								<Activity class="mx-auto h-10 w-10 text-slate-300" />
								<p class="mt-4 text-base font-black text-slate-700">No activity found</p>
								<p class="mt-2 text-sm text-slate-500">
									Activity is generated from real approved academic work already stored in the app.
								</p>
							</div>
						{:else}
							{#each activityRows as row (row.id)}
								<div class="rounded-[22px] p-4"
									style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); border: 1px solid rgba(148,163,184,0.18);">
									<div class="flex items-center justify-between gap-3">
										<div class="min-w-0">
											<p class="truncate text-base font-black text-slate-900">{row.studentName}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{row.groupName}
											</p>
											<p class="mt-2 text-sm font-semibold text-slate-700">{row.label}</p>
											<p class="mt-1 text-xs text-slate-500">{row.date}</p>
										</div>
										<div class="text-right">
											<p class="text-sm font-black text-blue-600">{row.value}</p>
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>
				</div>

				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<Clock3 class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Activity Summary</p>
					</div>

					<div class="grid grid-cols-2 gap-2">
						<div class="rounded-2xl px-3 py-3"
							style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.22);">
							<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Rows</p>
							<p class="mt-1 text-xl font-black text-blue-600">{activityRows.length}</p>
						</div>
						<div class="rounded-2xl px-3 py-3"
							style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.22);">
							<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Students</p>
							<p class="mt-1 text-xl font-black text-emerald-700">{new Set(activityRows.map((row) => row.studentName)).size}</p>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.85fr)]">
				<div class="rounded-[28px] p-5" style={cardStyle}>
					<div class="mb-4 flex items-center gap-2">
						<TrendingUp class="h-4 w-4 text-slate-500" />
						<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Academic Analytics</p>
					</div>

					<div class="space-y-3">
						{#each groupPerformanceRows as row (row.id)}
							<div class="rounded-[22px] p-4"
								style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); border: 1px solid rgba(148,163,184,0.18);">
								<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
									<div class="min-w-0">
										<p class="truncate text-base font-black text-slate-900">{row.name}</p>
										<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
											{row.programmeName}
										</p>
									</div>

									<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
										<div class="rounded-2xl px-3 py-2" style="background: rgba(239,246,255,0.95);">
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Students</p>
											<p class="mt-1 text-lg font-black text-blue-600">{row.studentCount}</p>
										</div>
										<div class="rounded-2xl px-3 py-2" style="background: rgba(240,253,244,0.95);">
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Progress</p>
											<p class="mt-1 text-lg font-black text-emerald-700">{row.avgProgress}%</p>
										</div>
										<div class="rounded-2xl px-3 py-2" style="background: rgba(255,247,237,0.95);">
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Approved</p>
											<p class="mt-1 text-lg font-black text-orange-600">{row.approvedCaseRecords}</p>
										</div>
										<div class="rounded-2xl px-3 py-2" style="background: rgba(250,245,255,0.95);">
											<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Points</p>
											<p class="mt-1 text-lg font-black text-violet-700">{row.earnedPoints}</p>
										</div>
									</div>
								</div>
							</div>
						{/each}
						{#if groupPerformanceRows.length === 0}
							<p class="text-sm text-slate-500">No analytics rows available for the current filters.</p>
						{/if}
					</div>
				</div>

				<div class="space-y-4">
					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center gap-2">
							<BookOpen class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Overview</p>
						</div>

						<div class="grid grid-cols-2 gap-2">
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Students</p>
								<p class="mt-1 text-xl font-black text-blue-600">{analyticsSummary.studentCount}</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Groups</p>
								<p class="mt-1 text-xl font-black text-emerald-700">{analyticsSummary.groupCount}</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(255,247,237,0.9); border: 1px solid rgba(251,146,60,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Approved</p>
								<p class="mt-1 text-xl font-black text-orange-600">{analyticsSummary.approvedCaseRecords}</p>
							</div>
							<div class="rounded-2xl px-3 py-3"
								style="background: rgba(250,245,255,0.9); border: 1px solid rgba(192,132,252,0.22);">
								<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Avg Progress</p>
								<p class="mt-1 text-xl font-black text-violet-700">{analyticsSummary.avgProgress}%</p>
							</div>
						</div>
					</div>

					<div class="rounded-[28px] p-5" style={cardStyle}>
						<div class="mb-4 flex items-center gap-2">
							<Settings2 class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.2em] text-slate-600">Weightage</p>
						</div>

						<div class="space-y-2">
							{#each filteredWeightages.slice(0, 8) as item (item.form_definition_id)}
								<div class="rounded-2xl px-3 py-3"
									style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);">
									<div class="flex items-center justify-between gap-3">
										<div class="min-w-0">
											<p class="truncate text-sm font-black text-slate-900">{item.name ?? 'Unnamed Form'}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{item.department ?? 'General'}
											</p>
										</div>
										<div class="flex items-center gap-2">
											<input
												type="number"
												min="0"
												value={item.points}
												onchange={(event) => updateWeightage(item, Number((event.currentTarget as HTMLInputElement).value))}
												class="w-20 rounded-xl border px-3 py-2 text-sm font-bold text-slate-700 outline-none"
												style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
											/>
										</div>
									</div>
								</div>
							{/each}
							{#if filteredWeightages.length === 0}
								<p class="text-sm text-slate-500">No weightage items found.</p>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

{#if showProgrammeModal}
	<AquaModal
		title={editingProgrammeId ? 'Edit Programme' : 'Create Programme'}
		onclose={() => (showProgrammeModal = false)}
	>
		<div class="space-y-4 p-4">
			<div class="grid gap-3 md:grid-cols-2">
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Programme Name *</label>
					<input
						type="text"
						bind:value={programmeName}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="Enter programme name"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Code *</label>
					<input
						type="text"
						bind:value={programmeCode}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm uppercase focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="Enter code"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Degree Type</label>
					<select
						bind:value={programmeDegreeType}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="">Select degree type</option>
						{#each degreeTypes as degreeType (degreeType)}
							<option value={degreeType}>{degreeType}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Duration</label>
					<input
						type="text"
						bind:value={programmeDuration}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="e.g. 4 Years"
					/>
				</div>
				<div class="md:col-span-2">
					<label class="mb-1 block text-xs font-semibold text-gray-700">Description</label>
					<textarea
						bind:value={programmeDescription}
						rows="3"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="Optional description"
					></textarea>
				</div>
				<div class="md:col-span-2">
					<label class="flex items-center gap-2 text-sm font-semibold text-gray-700">
						<input type="checkbox" bind:checked={programmeIsActive} />
						Programme is active
					</label>
				</div>
			</div>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => (showProgrammeModal = false)}>
					Cancel
				</AquaButton>
				<AquaButton variant="primary" fullWidth disabled={saving} onclick={saveProgramme}>
					{saving ? 'Saving...' : editingProgrammeId ? 'Update Programme' : 'Create Programme'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showGroupModal}
	<AquaModal
		title={editingGroupId ? 'Edit Academic Group' : 'Create Academic Group'}
		panelClass="max-w-[min(920px,94vw)]"
		onclose={() => (showGroupModal = false)}
	>
		<div class="space-y-4 p-4">
			<div class="grid gap-3 md:grid-cols-2">
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Programme *</label>
					<select
						bind:value={groupProgrammeId}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="">Select programme</option>
						{#each programmes as programme (programme.id)}
							<option value={programme.id}>{programme.name}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Group Name *</label>
					<input
						type="text"
						bind:value={groupName}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="Enter group name"
					/>
				</div>
				<div class="md:col-span-2">
					<label class="mb-1 block text-xs font-semibold text-gray-700">Description</label>
					<textarea
						bind:value={groupDescription}
						rows="3"
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="Optional description"
					></textarea>
				</div>
				<div class="md:col-span-2">
					<label class="flex items-center gap-2 text-sm font-semibold text-gray-700">
						<input type="checkbox" bind:checked={groupIsActive} />
						Group is active
					</label>
				</div>
			</div>

			<div class="rounded-2xl border p-3"
				style="background: rgba(248,250,252,0.9); border-color: rgba(148,163,184,0.22);">
				<div class="mb-3 flex items-center justify-between gap-2">
					<div>
						<p class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">Assign Students</p>
						<p class="mt-1 text-xs text-slate-500">{groupStudentIds.length} selected</p>
					</div>
					<div class="rounded-full px-2.5 py-1 text-[11px] font-bold"
						style="background: rgba(239,246,255,0.95); color: #1d4ed8;">
						{availableStudents.length} eligible
					</div>
				</div>

				<div class="max-h-[280px] space-y-2 overflow-y-auto pr-1">
					{#if availableStudents.length === 0}
						<p class="py-6 text-center text-sm font-semibold text-slate-500">
							No students available for this programme.
						</p>
					{:else}
						{#each availableStudents as student (student.id)}
							<button
								type="button"
								class="flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left cursor-pointer transition-transform hover:-translate-y-[1px]"
								style={`background: ${groupStudentIds.includes(student.id) ? 'linear-gradient(to bottom, rgba(239,246,255,0.98), rgba(219,234,254,0.96))' : 'white'}; border-color: ${groupStudentIds.includes(student.id) ? 'rgba(59,130,246,0.35)' : 'rgba(148,163,184,0.18)'};`}
								onclick={() => toggleGroupStudent(student.id)}
							>
								<div class="min-w-0">
									<p class="truncate text-sm font-black text-slate-900">{student.name}</p>
									<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
										{student.student_id} • Year {student.year} • Sem {student.semester}
									</p>
									<p class="mt-1 text-xs text-slate-500">{student.program}</p>
								</div>
								{#if groupStudentIds.includes(student.id)}
									<CheckCircle2 class="h-5 w-5 shrink-0 text-blue-600" />
								{:else}
									<ArrowRight class="h-4 w-4 shrink-0 text-slate-300" />
								{/if}
							</button>
						{/each}
					{/if}
				</div>
			</div>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => (showGroupModal = false)}>
					Cancel
				</AquaButton>
				<AquaButton variant="primary" fullWidth disabled={saving} onclick={saveGroup}>
					{saving ? 'Saving...' : editingGroupId ? 'Update Group' : 'Create Group'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showTargetModal}
	<AquaModal
		title={editingTargetId ? 'Edit Academic Target' : 'Create Academic Target'}
		panelClass="max-w-[min(920px,94vw)]"
		onclose={() => (showTargetModal = false)}
	>
		<div class="space-y-4 p-4">
			<div class="grid gap-3 md:grid-cols-2">
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Academic Group *</label>
					<select
						bind:value={targetGroupId}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="">Select group</option>
						{#each groups as group (group.id)}
							<option value={group.id}>{group.name} • {group.programme_name ?? getProgrammeName(group.programme_id)}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Category</label>
					<select
						bind:value={targetCategory}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						{#each targetCategories as category (category)}
							<option value={category}>{category}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Metric Name *</label>
					<input
						type="text"
						bind:value={targetMetricName}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
						placeholder="e.g. Clinical Communication"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Target Value</label>
					<input
						type="number"
						min="0"
						bind:value={targetValue}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Sort Order</label>
					<input
						type="number"
						min="0"
						bind:value={targetSortOrder}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs font-semibold text-gray-700">Linked Form</label>
					<select
						bind:value={targetFormDefinitionId}
						onchange={(event) => applyFormToTarget((event.currentTarget as HTMLSelectElement).value)}
						class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
					>
						<option value="">No linked form</option>
						{#each availableTargetForms as form (form.form_definition_id)}
							<option value={form.form_definition_id}>
								{form.department ?? 'General'} • {form.name ?? 'Unnamed'}
								{#if form.procedure_name} • {form.procedure_name}{/if}
							</option>
						{/each}
					</select>
				</div>
			</div>

			<div class="rounded-2xl border p-3"
				style="background: rgba(248,250,252,0.9); border-color: rgba(148,163,184,0.22);">
				<div class="flex items-start gap-3">
					<div class="flex h-10 w-10 items-center justify-center rounded-2xl"
						style="background: linear-gradient(to bottom, #eff6ff, #dbeafe);">
						<ShieldCheck class="h-5 w-5 text-blue-600" />
					</div>
					<div>
						<p class="text-sm font-black text-slate-900">Target linking tip</p>
						<p class="mt-1 text-xs leading-5 text-slate-500">
							Linking a target to a case-record form lets the system track progress automatically from approved records.
						</p>
					</div>
				</div>
			</div>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => (showTargetModal = false)}>
					Cancel
				</AquaButton>
				<AquaButton variant="primary" fullWidth disabled={saving} onclick={saveTarget}>
					{saving ? 'Saving...' : editingTargetId ? 'Update Target' : 'Create Target'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showStudentProgressModal}
	<AquaModal
		title={`${progressStudentName} Progress`}
		panelClass="max-w-[min(1100px,96vw)]"
		onclose={() => {
			showStudentProgressModal = false;
			progressStudentId = '';
			progressStudentName = '';
		}}
	>
		<div class="space-y-4 p-4">
			{#if progressLoading && !selectedStudentProgress}
				<div class="flex items-center justify-center py-12">
					<div class="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
				</div>
			{:else if selectedStudentProgress}
				<div class="grid gap-3 md:grid-cols-4">
					<div class="rounded-2xl px-4 py-4"
						style="background: rgba(239,246,255,0.95); border: 1px solid rgba(96,165,250,0.22);">
						<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Overall</p>
						<p class="mt-1 text-2xl font-black text-blue-600">{Math.round(selectedStudentProgress.summary.overall_percent)}%</p>
					</div>
					<div class="rounded-2xl px-4 py-4"
						style="background: rgba(240,253,244,0.95); border: 1px solid rgba(74,222,128,0.22);">
						<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Completed Targets</p>
						<p class="mt-1 text-2xl font-black text-emerald-700">{selectedStudentProgress.summary.completed_targets}/{selectedStudentProgress.summary.total_targets}</p>
					</div>
					<div class="rounded-2xl px-4 py-4"
						style="background: rgba(255,247,237,0.95); border: 1px solid rgba(251,146,60,0.22);">
						<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Approved Records</p>
						<p class="mt-1 text-2xl font-black text-orange-600">{selectedStudentProgress.summary.approved_case_records}</p>
					</div>
					<div class="rounded-2xl px-4 py-4"
						style="background: rgba(250,245,255,0.95); border: 1px solid rgba(192,132,252,0.22);">
						<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Earned Points</p>
						<p class="mt-1 text-2xl font-black text-violet-700">{selectedStudentProgress.summary.total_earned_points}</p>
					</div>
				</div>

				<div class="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
					<div class="rounded-[22px] border p-4"
						style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.18);">
						<div class="mb-3 flex items-center gap-2">
							<Target class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.18em] text-slate-600">Target Progress</p>
						</div>

						<div class="space-y-3">
							{#each selectedStudentProgress.targets as target (target.id)}
								<div class="rounded-2xl px-3 py-3"
									style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);">
									<div class="flex items-center justify-between gap-3">
										<div class="min-w-0">
											<p class="truncate text-sm font-black text-slate-900">{target.metric_name}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{target.completed_value}/{target.target_value} • {target.category}
											</p>
										</div>
										<p class="text-sm font-black text-blue-600">{Math.round(target.percent)}%</p>
									</div>
									<div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
										<div
											class="h-full rounded-full"
											style={`width: ${Math.min(Math.round(target.percent), 100)}%; background: linear-gradient(to right, #3b82f6, #10b981);`}
										></div>
									</div>
								</div>
							{/each}
							{#if selectedStudentProgress.targets.length === 0}
								<p class="text-sm text-slate-500">No targets configured for this student.</p>
							{/if}
						</div>
					</div>

					<div class="rounded-[22px] border p-4"
						style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.18);">
						<div class="mb-3 flex items-center gap-2">
							<Award class="h-4 w-4 text-slate-500" />
							<p class="text-sm font-black uppercase tracking-[0.18em] text-slate-600">Weighted Forms</p>
						</div>

						<div class="space-y-3">
							{#each selectedStudentProgress.weightages.items as item (item.form_definition_id)}
								<div class="rounded-2xl px-3 py-3"
									style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.16);">
									<div class="flex items-center justify-between gap-3">
										<div class="min-w-0">
											<p class="truncate text-sm font-black text-slate-900">{item.name ?? 'Unnamed Form'}</p>
											<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
												{item.approved_count} approved • {item.points} pts each
											</p>
										</div>
										<p class="text-sm font-black text-emerald-700">{item.earned_points}</p>
									</div>
								</div>
							{/each}
							{#if selectedStudentProgress.weightages.items.length === 0}
								<p class="text-sm text-slate-500">No weighted form activity found.</p>
							{/if}
						</div>
					</div>
				</div>
			{:else}
				<div class="rounded-[22px] border border-dashed border-slate-300/90 px-5 py-10 text-center">
					<p class="text-base font-black text-slate-700">No progress data available</p>
				</div>
			{/if}
		</div>
	</AquaModal>
{/if}
