<script lang="ts">
	import { onMount } from 'svelte';
	import {
		adminApi,
		type AcademicGroup,
		type AcademicOverviewResponse,
		type AcademicOverviewStudent,
		type AcademicTarget,
		type AcademicWeightageItem,
		type Programme
	} from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import {
		GraduationCap,
		Users,
		Target,
		Scale,
		Plus,
		Edit3,
		Trash2,
		Search,
		Check,
		CheckCircle2,
		ShieldCheck,
		ArrowRight,
		Settings2,
		BookOpen
	} from 'lucide-svelte';

	type TabId = 'programmes' | 'groups' | 'targets' | 'weightages';
	type ApiError = { response?: { data?: { detail?: string } } };

	let {
		mode = 'admin',
		title,
		subtitle
	}: {
		mode?: 'admin' | 'academic-manager';
		title?: string;
		subtitle?: string;
	} = $props();

	const tabItems: { id: TabId; label: string; icon: typeof GraduationCap }[] = [
		{ id: 'programmes', label: 'Programs', icon: GraduationCap },
		{ id: 'groups', label: 'Groups', icon: Users },
		{ id: 'targets', label: 'Targets', icon: Target },
		{ id: 'weightages', label: 'Weightage', icon: Scale }
	];

	let loading = $state(true);
	let saving = $state(false);
	let error = $state('');
	let activeTab = $state<TabId>('programmes');

	let programmes = $state<Programme[]>([]);
	let groups = $state<AcademicGroup[]>([]);
	let targets = $state<AcademicTarget[]>([]);
	let weightages = $state<AcademicWeightageItem[]>([]);
	let students = $state<AcademicOverviewStudent[]>([]);

	let selectedProgrammeId = $state('');
	let selectedGroupId = $state('');
	let searchQuery = $state('');

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
	let deletingTargetId = $state('');
	let togglingProgrammeId = $state('');
	let togglingGroupId = $state('');

	const degreeTypes = ['Undergraduate', 'Postgraduate', 'Diploma', 'Certificate', 'Doctoral'];
	const targetCategories = ['ACADEMIC', 'CLINICAL', 'LABORATORY', 'ADMINISTRATIVE'];

	const filteredProgrammes = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();
		const items = [...programmes].sort((left, right) => left.name.localeCompare(right.name));

		if (!query) {
			return items;
		}

		return items.filter((programme) =>
			[
				programme.name,
				programme.code,
				programme.description ?? '',
				programme.degree_type ?? '',
				programme.duration_years ?? ''
			]
				.join(' ')
				.toLowerCase()
				.includes(query)
		);
	});

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

	const totalProgrammeCount = $derived(programmes.length);
	const activeProgrammeCount = $derived(programmes.filter((programme) => programme.is_active).length);
	const activeGroupCount = $derived(groups.filter((group) => group.is_active).length);
	const configuredWeightageCount = $derived(weightages.filter((item) => item.has_weightage).length);

	onMount(async () => {
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
		} catch (errorValue: unknown) {
			error = (errorValue as ApiError)?.response?.data?.detail || 'Failed to load academics workspace';
		} finally {
			loading = false;
		}
	}

	function switchTab(tabId: string) {
		activeTab = tabId as TabId;
		searchQuery = '';
		if (tabId !== 'targets') {
			selectedGroupId = '';
		}
	}

	function openCreateProgramme() {
		editingProgrammeId = '';
		programmeName = '';
		programmeCode = '';
		programmeDescription = '';
		programmeDegreeType = '';
		programmeDuration = '';
		programmeIsActive = true;
		showProgrammeModal = true;
	}

	function openEditProgramme(programme: Programme) {
		editingProgrammeId = programme.id;
		programmeName = programme.name;
		programmeCode = programme.code;
		programmeDescription = programme.description ?? '';
		programmeDegreeType = programme.degree_type ?? '';
		programmeDuration = programme.duration_years ?? '';
		programmeIsActive = programme.is_active;
		showProgrammeModal = true;
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

	async function deactivateProgramme(programme: Programme) {
		if (!window.confirm(`Deactivate ${programme.name}?`)) return;

		try {
			await adminApi.deleteProgramme(programme.id);
			toastStore.addToast('Programme deactivated successfully', 'success');
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to deactivate programme',
				'error'
			);
		}
	}

	async function toggleProgrammeActive(event: Event, programme: Programme) {
		event.stopPropagation();
		if (togglingProgrammeId) return;
		togglingProgrammeId = programme.id;
		try {
			await adminApi.updateProgramme(programme.id, { is_active: !programme.is_active });
			programmes = programmes.map((item) =>
				item.id === programme.id ? { ...item, is_active: !item.is_active } : item
			);
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to update programme status',
				'error'
			);
		} finally {
			togglingProgrammeId = '';
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

	async function toggleGroupActive(event: Event, group: AcademicGroup) {
		event.stopPropagation();
		if (togglingGroupId) return;
		togglingGroupId = group.id;
		try {
			await adminApi.updateAcademicGroup(group.id, {
				programme_id: group.programme_id,
				name: group.name,
				description: group.description ?? undefined,
				is_active: !group.is_active,
				student_ids: group.student_ids
			});
			groups = groups.map((item) =>
				item.id === group.id ? { ...item, is_active: !item.is_active } : item
			);
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to update group status',
				'error'
			);
		} finally {
			togglingGroupId = '';
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
		deletingTargetId = target.id;

		try {
			await adminApi.deleteAcademicTarget(target.id);
			toastStore.addToast('Academic target deleted successfully', 'success');
			if (editingTargetId === target.id) {
				showTargetModal = false;
				editingTargetId = '';
			}
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast(
				(errorValue as ApiError)?.response?.data?.detail || 'Failed to delete academic target',
				'error'
			);
		} finally {
			deletingTargetId = '';
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

	function getProgrammeName(programmeId: string) {
		return programmes.find((programme) => programme.id === programmeId)?.name ?? 'Unknown Programme';
	}

	function getGroupName(groupId: string) {
		return groups.find((group) => group.id === groupId)?.name ?? 'Unknown Group';
	}
</script>

<div class="flex flex-col gap-3">
	<!-- Header: section title left, tab bar right -->
	<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
		<p class="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Academic Programs</p>
		<TabBar tabs={tabItems} activeTab={activeTab} onchange={switchTab} variant="jiggle" stretch={false} size="compact" />
	</div>

	<!-- Action row: filter selects + add button -->
	<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
		<div class="flex flex-col gap-2 sm:flex-row">
			{#if activeTab === 'groups' || activeTab === 'targets'}
				<select
					bind:value={selectedProgrammeId}
					class="w-full rounded-2xl border px-3 py-2.5 text-sm font-semibold text-slate-700 outline-none sm:w-[220px]"
					style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
				>
					<option value="">All programmes</option>
					{#each programmes as programme (programme.id)}
						<option value={programme.id}>{programme.name}</option>
					{/each}
				</select>
			{/if}
			{#if activeTab === 'targets'}
				<select
					bind:value={selectedGroupId}
					class="w-full rounded-2xl border px-3 py-2.5 text-sm font-semibold text-slate-700 outline-none sm:w-[220px]"
					style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
				>
					<option value="">All groups</option>
					{#each selectableGroups as group (group.id)}
						<option value={group.id}>{group.name}</option>
					{/each}
				</select>
			{/if}
		</div>

		<div class="flex justify-end">
			{#if activeTab === 'programmes'}
				<button
					type="button"
					class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
					onclick={openCreateProgramme}
				>
					<Plus class="h-4 w-4" />
					<span>Add Program</span>
				</button>
			{:else if activeTab === 'groups'}
				<button
					type="button"
					class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
					onclick={() => openCreateGroup()}
				>
					<Plus class="h-4 w-4" />
					<span>Add Group</span>
				</button>
			{:else if activeTab === 'targets'}
				<button
					type="button"
					class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
					onclick={() => openCreateTarget()}
				>
					<Plus class="h-4 w-4" />
					<span>Add Target</span>
				</button>
			{/if}
		</div>
	</div>

	<!-- Content -->
	{#if loading}
		<div class="flex items-center justify-center py-16">
			<div class="h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
		</div>
	{:else if error}
		<div class="rounded-2xl border px-4 py-8 text-center"
			style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
			<p class="text-sm font-semibold text-red-600">{error}</p>
		</div>
	{:else}
		{#if activeTab === 'programmes'}
			<div class="space-y-2">
				{#if filteredProgrammes.length === 0}
					<div class="rounded-2xl border px-4 py-10 text-center"
						style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
						<p class="text-sm font-semibold text-slate-500">No programmes found.</p>
					</div>
				{:else}
					{#each filteredProgrammes as programme (programme.id)}
						<div
							role="button"
							tabindex="0"
							class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
							style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);"
							onclick={() => openEditProgramme(programme)}
							onkeydown={(event) => {
								if (event.key === 'Enter' || event.key === ' ') {
									event.preventDefault();
									openEditProgramme(programme);
								}
							}}
						>
							<!-- Left: blue circle with graduation cap -->
							<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 10px rgba(37,99,235,0.28);">
								<GraduationCap class="h-5 w-5 text-white" />
							</div>

							<!-- Center: name + status row -->
							<div class="min-w-0 flex-1">
								<p class="truncate font-bold text-slate-900">{programme.name}</p>
								<div class="mt-1 flex items-center gap-2">
									<span class="text-xs text-slate-500">{programme.student_count} Students Enrolled</span>
								</div>
							</div>

							<!-- Right: iOS-style status switch only -->
							<div class="flex shrink-0 items-center">
								<button
									type="button"
									role="switch"
									aria-checked={programme.is_active}
									aria-label={`Toggle ${programme.name} active status`}
									onclick={(event) => toggleProgrammeActive(event, programme)}
									disabled={togglingProgrammeId === programme.id}
									class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
								>
									<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${programme.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
										<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${programme.is_active ? 'left-6' : 'left-1'}`}>
											{#if togglingProgrammeId === programme.id}
												<Check class="m-auto h-3 w-3 animate-pulse text-slate-300" />
											{/if}
										</span>
									</span>
								</button>
							</div>
						</div>
					{/each}
				{/if}
			</div>

		{:else if activeTab === 'groups'}
			<div class="space-y-2">
				{#if filteredGroups.length === 0}
					<div class="rounded-2xl border px-4 py-10 text-center"
						style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
						<p class="text-sm font-semibold text-slate-500">No academic groups found.</p>
					</div>
				{:else}
					{#each filteredGroups as group (group.id)}
						<div
							role="button"
							tabindex="0"
							class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
							style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);"
							onclick={() => openEditGroup(group)}
							onkeydown={(event) => {
								if (event.key === 'Enter' || event.key === ' ') {
									event.preventDefault();
									openEditGroup(group);
								}
							}}
						>
							<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #8b5cf6, #6d28d9); box-shadow: 0 4px 10px rgba(109,40,217,0.28);">
								<Users class="h-5 w-5 text-white" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate font-bold text-slate-900">{group.name}</p>
								<div class="mt-1 flex items-center gap-2">
									<span class="text-xs text-slate-500">
										{group.programme_name ?? getProgrammeName(group.programme_id)} • {group.student_count} students
									</span>
								</div>
							</div>
							<div class="flex shrink-0 items-center">
								<button
									type="button"
									role="switch"
									aria-checked={group.is_active}
									aria-label={`Toggle ${group.name} active status`}
									onclick={(event) => toggleGroupActive(event, group)}
									disabled={togglingGroupId === group.id}
									class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
								>
									<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${group.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
										<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${group.is_active ? 'left-6' : 'left-1'}`}>
											{#if togglingGroupId === group.id}
												<Check class="m-auto h-3 w-3 animate-pulse text-slate-300" />
											{/if}
										</span>
									</span>
								</button>
							</div>
						</div>
					{/each}
				{/if}
			</div>

		{:else if activeTab === 'targets'}
			<div class="space-y-2">
				{#if filteredTargets.length === 0}
					<div class="rounded-2xl border px-4 py-10 text-center"
						style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
						<p class="text-sm font-semibold text-slate-500">No academic targets found.</p>
					</div>
				{:else}
					{#each filteredTargets as target (target.id)}
						<div
							role="button"
							tabindex="0"
							class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left cursor-pointer transition-transform hover:-translate-y-[1px] active:scale-[0.99]"
							style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);"
							onclick={() => openEditTarget(target)}
							onkeydown={(event) => {
								if (event.key === 'Enter' || event.key === ' ') {
									event.preventDefault();
									openEditTarget(target);
								}
							}}
						>
							<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #f97316, #ea580c); box-shadow: 0 4px 10px rgba(234,88,12,0.28);">
								<Target class="h-5 w-5 text-white" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate font-bold text-slate-900">{target.metric_name}</p>
								<div class="mt-1 flex items-center gap-2">
									<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.14em]"
										style="background: rgba(239,246,255,0.95); color: #1d4ed8;">{target.category}</span>
									<span class="text-xs text-slate-500">
										Target {target.target_value} • {target.group_name ?? getGroupName(target.group_id)}
									</span>
								</div>
							</div>
							<div class="flex shrink-0 items-center">
								<button
									type="button"
									onclick={(event) => {
										event.stopPropagation();
										void deleteTarget(target);
									}}
									disabled={deletingTargetId === target.id}
									class="inline-flex h-8 w-8 items-center justify-center rounded-full text-red-600 transition-colors hover:bg-red-50 disabled:opacity-60"
									title="Delete target"
								>
									{#if deletingTargetId === target.id}
										<Check class="h-3.5 w-3.5 animate-pulse text-slate-300" />
									{:else}
										<Trash2 class="h-4 w-4" />
									{/if}
								</button>
							</div>
						</div>
					{/each}
				{/if}
			</div>

		{:else if activeTab === 'weightages'}
			<div class="space-y-2">
				{#if filteredWeightages.length === 0}
					<div class="rounded-2xl border px-4 py-10 text-center"
						style="background: rgba(255,255,255,0.9); border-color: rgba(148,163,184,0.22);">
						<p class="text-sm font-semibold text-slate-500">No case-record forms found.</p>
					</div>
				{:else}
					{#each filteredWeightages as item (item.form_definition_id)}
						<div class="flex items-center gap-3 rounded-2xl border px-4 py-3"
							style="background: rgba(255,255,255,0.97); border-color: rgba(148,163,184,0.14); box-shadow: 0 1px 4px rgba(15,23,42,0.05);">
							<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #f59e0b, #d97706); box-shadow: 0 4px 10px rgba(217,119,6,0.28);">
								<Scale class="h-5 w-5 text-white" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="truncate font-bold text-slate-900">{item.name ?? 'Unnamed Form'}</p>
								<div class="mt-1 flex items-center gap-2">
									{#if item.has_weightage}
										<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.14em]"
											style="background: rgba(220,252,231,0.95); color: #15803d;">Configured</span>
									{:else}
										<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.14em]"
											style="background: rgba(254,249,195,0.95); color: #a16207;">Unset</span>
									{/if}
									<span class="text-xs text-slate-500">
										{item.department ?? 'General'}{#if item.procedure_name} • {item.procedure_name}{/if}
									</span>
								</div>
							</div>
							<div class="flex shrink-0 items-center gap-3">
								<div class="rounded-xl border px-3 py-1.5 text-center"
									style="background: rgba(248,250,252,0.95); border-color: rgba(148,163,184,0.22);">
									<p class="text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">pts</p>
									<p class="text-sm font-black text-slate-900">{item.points}</p>
								</div>
								<input
									type="number"
									min="0"
									value={item.points}
									onchange={(event) => updateWeightage(item, Number((event.currentTarget as HTMLInputElement).value))}
									class="w-20 rounded-xl border px-2 py-2 text-xs font-bold text-slate-700 outline-none"
									style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
								/>
								<button
									class="rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 6px rgba(37,99,235,0.25);"
									onclick={() => updateWeightage(item, item.points)}
								>
									Save
								</button>
							</div>
						</div>
					{/each}
				{/if}
			</div>
		{/if}
	{/if}
</div>

{#if showProgrammeModal}
	<AquaModal
		title={editingProgrammeId ? 'Edit Programme' : 'Create Programme'}
		onclose={() => (showProgrammeModal = false)}
	>
		<!-- svelte-ignore a11y_label_has_associated_control -->
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
			<!-- svelte-ignore a11y_label_has_associated_control -->
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
		<!-- svelte-ignore a11y_label_has_associated_control -->
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
				{#if editingTargetId}
					<AquaButton
						variant="danger"
						fullWidth
						disabled={deletingTargetId === editingTargetId}
						onclick={() => {
							const target = targets.find((item) => item.id === editingTargetId);
							if (target) {
								void deleteTarget(target);
							}
						}}
					>
						{deletingTargetId === editingTargetId ? 'Deleting...' : 'Delete Target'}
					</AquaButton>
				{/if}
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
