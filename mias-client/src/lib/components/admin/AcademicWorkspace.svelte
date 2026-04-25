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
		{ id: 'programmes', label: 'Programmes', icon: GraduationCap },
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

	const degreeTypes = ['Undergraduate', 'Postgraduate', 'Diploma', 'Certificate', 'Doctoral'];
	const targetCategories = ['ACADEMIC', 'CLINICAL', 'LABORATORY', 'ADMINISTRATIVE'];

	const pageTitle = $derived(
		title ?? (mode === 'academic-manager' ? 'Academic Manager Workspace' : 'Academics Workspace')
	);
	const pageSubtitle = $derived(
		subtitle ?? (
			mode === 'academic-manager'
				? 'Manage programmes, student groups, targets, and academic weightage.'
				: 'Configure programmes, academic groups, targets, and case-record weightage.'
		)
	);

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

	function getProgrammeName(programmeId: string) {
		return programmes.find((programme) => programme.id === programmeId)?.name ?? 'Unknown Programme';
	}

	function getGroupName(groupId: string) {
		return groups.find((group) => group.id === groupId)?.name ?? 'Unknown Group';
	}
</script>

<div class="space-y-4 lg:space-y-5">
	<div class="rounded-[26px] border px-4 py-4 md:px-5 md:py-5"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(247,250,253,0.96)); border-color: rgba(148,163,184,0.22); box-shadow: 0 10px 24px rgba(15,23,42,0.08), inset 0 1px 0 rgba(255,255,255,0.92);">
		<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<div class="flex h-11 w-11 items-center justify-center rounded-2xl"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 6px 14px rgba(37,99,235,0.28), inset 0 1px 0 rgba(255,255,255,0.35);">
						<BookOpen class="h-5 w-5 text-white" />
					</div>
					<div class="min-w-0">
						<h1 class="truncate text-base font-black uppercase tracking-[0.18em] text-slate-700">
							{pageTitle}
						</h1>
						<p class="mt-1 text-xs text-slate-500">{pageSubtitle}</p>
					</div>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
				<div class="rounded-2xl px-3 py-3"
					style="background: rgba(239,246,255,0.9); border: 1px solid rgba(96,165,250,0.28);">
					<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Programmes</p>
					<p class="mt-1 text-xl font-black text-slate-900">{totalProgrammeCount}</p>
				</div>
				<div class="rounded-2xl px-3 py-3"
					style="background: rgba(240,253,244,0.9); border: 1px solid rgba(74,222,128,0.28);">
					<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Active</p>
					<p class="mt-1 text-xl font-black text-emerald-700">{activeProgrammeCount}</p>
				</div>
				<div class="rounded-2xl px-3 py-3"
					style="background: rgba(250,245,255,0.9); border: 1px solid rgba(192,132,252,0.28);">
					<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Groups</p>
					<p class="mt-1 text-xl font-black text-violet-700">{activeGroupCount}</p>
				</div>
				<div class="rounded-2xl px-3 py-3"
					style="background: rgba(255,247,237,0.9); border: 1px solid rgba(251,146,60,0.28);">
					<p class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Weighted</p>
					<p class="mt-1 text-xl font-black text-orange-600">{configuredWeightageCount}</p>
				</div>
			</div>
		</div>
	</div>

	<div class="rounded-[24px] border px-3 py-3 md:px-4"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(248,250,252,0.96)); border-color: rgba(148,163,184,0.2); box-shadow: 0 8px 20px rgba(15,23,42,0.06), inset 0 1px 0 rgba(255,255,255,0.92);">
		<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
			<div class="min-w-0">
				<TabBar tabs={tabItems} activeTab={activeTab} onchange={switchTab} variant="jiggle" stretch={false} />
			</div>

			<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
				<div class="relative min-w-0 sm:w-[260px]">
					<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Search workspace..."
						class="w-full rounded-2xl border px-10 py-2.5 text-sm font-medium text-slate-700 outline-none"
						style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24); box-shadow: inset 0 1px 2px rgba(15,23,42,0.06);"
					/>
				</div>

				{#if activeTab === 'programmes'}
					<AquaButton onclick={openCreateProgramme}>
						<Plus class="mr-1 h-4 w-4" /> Add Programme
					</AquaButton>
				{:else if activeTab === 'groups'}
					<AquaButton onclick={() => openCreateGroup()}>
						<Plus class="mr-1 h-4 w-4" /> Add Group
					</AquaButton>
				{:else if activeTab === 'targets'}
					<AquaButton onclick={() => openCreateTarget()}>
						<Plus class="mr-1 h-4 w-4" /> Add Target
					</AquaButton>
				{/if}
			</div>
		</div>

		{#if activeTab === 'groups' || activeTab === 'targets'}
			<div class="mt-3 flex flex-col gap-2 md:flex-row">
				<select
					bind:value={selectedProgrammeId}
					class="w-full rounded-2xl border px-3 py-2.5 text-sm font-semibold text-slate-700 outline-none md:max-w-[280px]"
					style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
				>
					<option value="">All programmes</option>
					{#each programmes as programme (programme.id)}
						<option value={programme.id}>{programme.name}</option>
					{/each}
				</select>

				{#if activeTab === 'targets'}
					<select
						bind:value={selectedGroupId}
						class="w-full rounded-2xl border px-3 py-2.5 text-sm font-semibold text-slate-700 outline-none md:max-w-[280px]"
						style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
					>
						<option value="">All groups</option>
						{#each selectableGroups as group (group.id)}
							<option value={group.id}>{group.name}</option>
						{/each}
					</select>
				{/if}
			</div>
		{/if}
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
	{:else}
		{#if activeTab === 'programmes'}
			<div class="space-y-3">
				{#if filteredProgrammes.length === 0}
					<AquaCard>
						<div class="py-10 text-center">
							<p class="text-sm font-semibold text-slate-500">No programmes found.</p>
						</div>
					</AquaCard>
				{:else}
					{#each filteredProgrammes as programme (programme.id)}
						<AquaCard>
							<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h3 class="truncate text-base font-black text-slate-900">{programme.name}</h3>
										{#if programme.is_active}
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
									<p class="mt-1 text-xs font-black uppercase tracking-[0.18em] text-blue-600">
										{programme.code}
										{#if programme.degree_type} • {programme.degree_type}{/if}
										{#if programme.duration_years} • {programme.duration_years}{/if}
									</p>
									{#if programme.description}
										<p class="mt-2 text-sm text-slate-600">{programme.description}</p>
									{/if}
									<div class="mt-3 flex flex-wrap gap-2">
										<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
											style="background: rgba(239,246,255,0.95); color: #1d4ed8;">
											{programme.student_count} students
										</span>
										<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
											style="background: rgba(245,243,255,0.95); color: #6d28d9;">
											{programme.group_count ?? 0} groups
										</span>
									</div>
								</div>

								<div class="flex flex-wrap gap-2 md:justify-end">
									<button
										class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #64748b, #475569); box-shadow: 0 2px 6px rgba(71,85,105,0.25);"
										onclick={() => openEditProgramme(programme)}
									>
										<Edit3 class="h-3.5 w-3.5" /> Edit
									</button>
									<button
										class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 2px 6px rgba(220,38,38,0.25);"
										onclick={() => deactivateProgramme(programme)}
									>
										<Trash2 class="h-3.5 w-3.5" /> Deactivate
									</button>
								</div>
							</div>
						</AquaCard>
					{/each}
				{/if}
			</div>
		{:else if activeTab === 'groups'}
			<div class="space-y-3">
				{#if filteredGroups.length === 0}
					<AquaCard>
						<div class="py-10 text-center">
							<p class="text-sm font-semibold text-slate-500">No academic groups found.</p>
						</div>
					</AquaCard>
				{:else}
					{#each filteredGroups as group (group.id)}
						<AquaCard>
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
						</AquaCard>
					{/each}
				{/if}
			</div>
		{:else if activeTab === 'targets'}
			<div class="space-y-3">
				{#if filteredTargets.length === 0}
					<AquaCard>
						<div class="py-10 text-center">
							<p class="text-sm font-semibold text-slate-500">No academic targets found.</p>
						</div>
					</AquaCard>
				{:else}
					{#each filteredTargets as target (target.id)}
						<AquaCard>
							<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h3 class="truncate text-base font-black text-slate-900">{target.metric_name}</h3>
										<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]"
											style="background: rgba(239,246,255,0.95); color: #1d4ed8;">
											{target.category}
										</span>
									</div>
									<p class="mt-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
										{target.programme_name ?? 'Programme'} • {target.group_name ?? getGroupName(target.group_id)}
									</p>
									<div class="mt-3 flex flex-wrap gap-2">
										<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
											style="background: rgba(240,253,244,0.95); color: #15803d;">
											Target {target.target_value}
										</span>
										<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
											style="background: rgba(248,250,252,0.95); color: #475569;">
											Sort {target.sort_order}
										</span>
										{#if target.form_name}
											<span class="rounded-full px-2.5 py-1 text-[11px] font-bold"
												style="background: rgba(245,243,255,0.95); color: #6d28d9;">
												{target.form_name}
											</span>
										{/if}
									</div>
								</div>

								<div class="flex flex-wrap gap-2 md:justify-end">
									<button
										class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #64748b, #475569); box-shadow: 0 2px 6px rgba(71,85,105,0.25);"
										onclick={() => openEditTarget(target)}
									>
										<Edit3 class="h-3.5 w-3.5" /> Edit
									</button>
									<button
										class="flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
										style="background: linear-gradient(to bottom, #ef4444, #dc2626); box-shadow: 0 2px 6px rgba(220,38,38,0.25);"
										onclick={() => deleteTarget(target)}
									>
										<Trash2 class="h-3.5 w-3.5" /> Delete
									</button>
								</div>
							</div>
						</AquaCard>
					{/each}
				{/if}
			</div>
		{:else if activeTab === 'weightages'}
			<div class="space-y-3">
				{#if filteredWeightages.length === 0}
					<AquaCard>
						<div class="py-10 text-center">
							<p class="text-sm font-semibold text-slate-500">No case-record forms found.</p>
						</div>
					</AquaCard>
				{:else}
					{#each filteredWeightages as item (item.form_definition_id)}
						<AquaCard>
							<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h3 class="truncate text-base font-black text-slate-900">{item.name ?? 'Unnamed Form'}</h3>
										{#if item.has_weightage}
											<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]"
												style="background: rgba(220,252,231,0.95); color: #15803d;">
												Configured
											</span>
										{:else}
											<span class="rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em]"
												style="background: rgba(254,249,195,0.95); color: #a16207;">
												Unset
											</span>
										{/if}
									</div>
									<p class="mt-1 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
										{item.department ?? 'General'}
										{#if item.procedure_name} • {item.procedure_name}{/if}
										{#if item.section} • {item.section}{/if}
									</p>
								</div>

								<div class="flex flex-col gap-2 sm:flex-row sm:items-center">
									<div class="rounded-2xl px-3 py-2"
										style="background: rgba(248,250,252,0.95); border: 1px solid rgba(148,163,184,0.22);">
										<p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Points</p>
										<p class="mt-0.5 text-lg font-black text-slate-900">{item.points}</p>
									</div>
									<div class="flex items-center gap-2">
										<input
											type="number"
											min="0"
											value={item.points}
											onchange={(event) => updateWeightage(item, Number((event.currentTarget as HTMLInputElement).value))}
											class="w-24 rounded-xl border px-3 py-2 text-sm font-bold text-slate-700 outline-none"
											style="background: rgba(255,255,255,0.96); border-color: rgba(148,163,184,0.24);"
										/>
										<button
											class="rounded-xl px-3 py-2 text-xs font-black text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 6px rgba(37,99,235,0.25);"
											onclick={() => updateWeightage(item, item.points)}
										>
											<Settings2 class="mr-1 inline h-3.5 w-3.5" /> Save
										</button>
									</div>
								</div>
							</div>
						</AquaCard>
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
