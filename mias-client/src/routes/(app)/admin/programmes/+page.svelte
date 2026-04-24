<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import {
		adminApi,
		type AcademicGroup,
		type AcademicOverviewResponse,
		type AcademicOverviewStudent,
		type AcademicTarget,
		type AcademicWeightageItem,
		type Programme
	} from '$lib/api/admin';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		BookOpen,
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
		NotebookTabs
	} from 'lucide-svelte';

	type TabId = 'programmes' | 'groups' | 'targets' | 'weightages';
	type ApiError = { response?: { data?: { detail?: string } } };

	const auth = get(authStore);
	const tabItems: { id: TabId; label: string; icon: typeof GraduationCap }[] = [
		{ id: 'programmes', label: 'Programmes', icon: GraduationCap },
		{ id: 'groups', label: 'Groups', icon: Users },
		{ id: 'targets', label: 'Targets', icon: Target },
		{ id: 'weightages', label: 'Weightages', icon: Scale }
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

	const stats = $derived({
		programmes: programmes.length,
		groups: groups.length,
		targets: targets.length,
		configuredWeightages: weightages.filter((item) => item.has_weightage).length
	});

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
			.filter((item) => !query
				? true
				: [item.name ?? '', item.department ?? '', item.procedure_name ?? '', item.section ?? '']
						.join(' ')
						.toLowerCase()
						.includes(query))
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

	onMount(async () => {
		if (auth.role !== 'ADMIN') {
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
		} catch (errorValue: unknown) {
			error = (errorValue as ApiError)?.response?.data?.detail || 'Failed to load academics workspace';
		} finally {
			loading = false;
		}
	}

	function switchTab(tabId: TabId) {
		activeTab = tabId;
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to save programme', 'error');
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to deactivate programme', 'error');
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to save academic group', 'error');
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to delete academic group', 'error');
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
		if (targetValue < 0) {
			toastStore.addToast('Target value cannot be negative', 'error');
			return;
		}

		saving = true;
		try {
			const payload = {
				group_id: targetGroupId,
				form_definition_id: targetFormDefinitionId || undefined,
				metric_name: targetMetricName.trim(),
				category: targetCategory,
				target_value: Number(targetValue),
				sort_order: Number(targetSortOrder)
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to save academic target', 'error');
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
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to delete academic target', 'error');
		}
	}

	async function saveWeightage(item: AcademicWeightageItem, points: number) {
		if (Number.isNaN(points) || points < 0) {
			toastStore.addToast('Points must be zero or greater', 'error');
			return;
		}

		try {
			await adminApi.updateAcademicWeightage(item.form_definition_id, { points });
			toastStore.addToast('Weightage updated successfully', 'success');
			await loadWorkspace();
		} catch (errorValue: unknown) {
			toastStore.addToast((errorValue as ApiError)?.response?.data?.detail || 'Failed to update weightage', 'error');
		}
	}

	function openTargetsForGroup(group: AcademicGroup) {
		selectedProgrammeId = group.programme_id;
		selectedGroupId = group.id;
		activeTab = 'targets';
		searchQuery = '';
	}

	function openGroupsForProgramme(programme: Programme) {
		selectedProgrammeId = programme.id;
		selectedGroupId = '';
		activeTab = 'groups';
		searchQuery = '';
	}

	function studentsForGroup(group: AcademicGroup) {
		return students
			.filter((student) => group.student_ids.includes(student.id))
			.sort((left, right) => left.name.localeCompare(right.name));
	}
</script>

<div class="space-y-4 px-4 py-4 md:px-6 md:py-6">
	<div
		class="rounded-[28px] px-5 py-5"
		style="background: linear-gradient(135deg, #0f172a, #1d4ed8 58%, #38bdf8); box-shadow: 0 18px 34px rgba(15,23,42,0.18);"
	>
		<div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
			<div class="max-w-2xl">
				<div class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-white/90"
					style="background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.18);">
					<NotebookTabs class="h-3.5 w-3.5" />
					<span>Academics workspace</span>
				</div>
				<h1 class="mt-3 text-2xl font-bold text-white">Configure programmes, groups, targets and form weightages</h1>
				<p class="mt-2 text-sm text-blue-100">
					Manage the full Academics surface end to end so student progress is driven by real configured targets and approved case-record forms.
				</p>
			</div>

			<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
				<div class="rounded-2xl px-3 py-3 text-center"
					style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Programmes</p>
					<p class="mt-1 text-2xl font-bold text-white">{stats.programmes}</p>
				</div>
				<div class="rounded-2xl px-3 py-3 text-center"
					style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Groups</p>
					<p class="mt-1 text-2xl font-bold text-white">{stats.groups}</p>
				</div>
				<div class="rounded-2xl px-3 py-3 text-center"
					style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Targets</p>
					<p class="mt-1 text-2xl font-bold text-white">{stats.targets}</p>
				</div>
				<div class="rounded-2xl px-3 py-3 text-center"
					style="background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.18);">
					<p class="text-[10px] uppercase tracking-[0.18em] text-blue-100">Weighted forms</p>
					<p class="mt-1 text-2xl font-bold text-white">{stats.configuredWeightages}</p>
				</div>
			</div>
		</div>

		<div class="mt-5 flex gap-2 overflow-x-auto pb-1">
			{#each tabItems as item (item.id)}
				{@const Icon = item.icon}
				<button
					class="shrink-0 rounded-full px-4 py-2 text-sm font-semibold cursor-pointer transition-transform hover:-translate-y-0.5"
					style={activeTab === item.id
						? 'background: linear-gradient(to bottom, #ffffff, #dbeafe); color: #1d4ed8; border: 1px solid rgba(255,255,255,0.8); box-shadow: 0 10px 18px rgba(15,23,42,0.14);'
						: 'background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.92); border: 1px solid rgba(255,255,255,0.18);'}
					onclick={() => switchTab(item.id)}
				>
					<div class="flex items-center gap-2">
						<Icon class="h-4 w-4" />
						<span>{item.label}</span>
					</div>
				</button>
			{/each}
		</div>
	</div>

	<div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
		<div class="space-y-3">
			<div class="rounded-3xl px-4 py-4"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.24); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
				<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
					<div class="relative flex-1">
						<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Search current tab..."
							class="w-full rounded-2xl border px-10 py-2.5 text-sm outline-none"
							style="background: #fff; border-color: rgba(148,163,184,0.28); box-shadow: inset 0 1px 3px rgba(15,23,42,0.06);"
						/>
					</div>

					<div class="flex flex-wrap gap-2">
						{#if activeTab === 'groups' || activeTab === 'targets'}
							<select
								bind:value={selectedProgrammeId}
								class="rounded-xl border px-3 py-2 text-sm outline-none bg-white"
								style="border-color: rgba(148,163,184,0.28);"
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
								class="rounded-xl border px-3 py-2 text-sm outline-none bg-white"
								style="border-color: rgba(148,163,184,0.28);"
							>
								<option value="">All groups</option>
								{#each selectableGroups as group (group.id)}
									<option value={group.id}>{group.name}</option>
								{/each}
							</select>
						{/if}

						{#if activeTab === 'programmes'}
							<AquaButton size="sm" onclick={openCreateProgramme}>
								<div class="flex items-center gap-1.5">
									<Plus class="h-4 w-4" />
									<span>New programme</span>
								</div>
							</AquaButton>
						{:else if activeTab === 'groups'}
							<AquaButton size="sm" onclick={() => openCreateGroup()}>
								<div class="flex items-center gap-1.5">
									<Plus class="h-4 w-4" />
									<span>New group</span>
								</div>
							</AquaButton>
						{:else if activeTab === 'targets'}
							<AquaButton size="sm" onclick={() => openCreateTarget()}>
								<div class="flex items-center gap-1.5">
									<Plus class="h-4 w-4" />
									<span>New target</span>
								</div>
							</AquaButton>
						{/if}
					</div>
				</div>
			</div>

			{#if loading}
				<div class="flex items-center justify-center py-20">
					<div class="h-9 w-9 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600"></div>
				</div>
			{:else if error}
				<AquaCard>
					<div class="py-10 text-center">
						<p class="text-sm font-semibold text-red-600">{error}</p>
						<div class="mt-4">
							<AquaButton size="sm" onclick={loadWorkspace}>
								<span>Retry</span>
							</AquaButton>
						</div>
					</div>
				</AquaCard>
			{:else if activeTab === 'programmes'}
				<div class="space-y-3">
					{#if filteredProgrammes.length === 0}
						<AquaCard>
							<div class="py-12 text-center">
								<GraduationCap class="mx-auto h-12 w-12 text-slate-300" />
								<p class="mt-3 text-sm text-slate-500">No programmes match your search.</p>
							</div>
						</AquaCard>
					{:else}
						{#each filteredProgrammes as programme (programme.id)}
							<AquaCard>
								<div class="flex items-start gap-3">
									<div class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
										style="background: linear-gradient(135deg, {programme.is_active ? '#2563eb' : '#94a3b8'}, {programme.is_active ? '#1d4ed8' : '#64748b'});">
										<BookOpen class="h-5 w-5 text-white" />
									</div>

									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-center gap-2">
											<h2 class="text-sm font-semibold text-slate-900">{programme.name}</h2>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style="background: #dbeafe; color: #1d4ed8;">{programme.code}</span>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style={programme.is_active ? 'background: #dcfce7; color: #166534;' : 'background: #e2e8f0; color: #475569;'}>
												{programme.is_active ? 'Active' : 'Inactive'}
											</span>
										</div>

										{#if programme.description}
											<p class="mt-1 text-xs text-slate-500">{programme.description}</p>
										{/if}

										<div class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
											<div class="rounded-2xl px-3 py-2" style="background: rgba(37,99,235,0.07);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Students</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{programme.student_count}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(16,185,129,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Groups</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{programme.group_count ?? 0}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(148,163,184,0.1);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Degree</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{programme.degree_type || '—'}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(124,58,237,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Duration</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{programme.duration_years || '—'}</p>
											</div>
										</div>

										<div class="mt-4 flex flex-wrap gap-2">
											<AquaButton size="sm" variant="secondary" onclick={() => openEditProgramme(programme)}>
												<div class="flex items-center gap-1.5">
													<Edit3 class="h-4 w-4" />
													<span>Edit</span>
												</div>
											</AquaButton>
											<AquaButton size="sm" onclick={() => openGroupsForProgramme(programme)}>
												<div class="flex items-center gap-1.5">
													<Users class="h-4 w-4" />
													<span>Manage groups</span>
												</div>
											</AquaButton>
											<AquaButton size="sm" variant="secondary" onclick={() => deactivateProgramme(programme)}>
												<div class="flex items-center gap-1.5">
													<Trash2 class="h-4 w-4" />
													<span>Deactivate</span>
												</div>
											</AquaButton>
										</div>
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
							<div class="py-12 text-center">
								<Users class="mx-auto h-12 w-12 text-slate-300" />
								<p class="mt-3 text-sm text-slate-500">No academic groups match your current filters.</p>
							</div>
						</AquaCard>
					{:else}
						{#each filteredGroups as group (group.id)}
							<AquaCard>
								<div class="flex items-start gap-3">
									<div class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
										style="background: linear-gradient(135deg, {group.is_active ? '#0ea5e9' : '#94a3b8'}, {group.is_active ? '#2563eb' : '#64748b'});">
										<Users class="h-5 w-5 text-white" />
									</div>

									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-center gap-2">
											<h2 class="text-sm font-semibold text-slate-900">{group.name}</h2>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style="background: #eff6ff; color: #2563eb;">{group.programme_name}</span>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style={group.is_active ? 'background: #dcfce7; color: #166534;' : 'background: #e2e8f0; color: #475569;'}>
												{group.is_active ? 'Active' : 'Inactive'}
											</span>
										</div>

										<p class="mt-1 text-xs text-slate-500">{group.description || 'No description added yet.'}</p>

										<div class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
											<div class="rounded-2xl px-3 py-2" style="background: rgba(37,99,235,0.07);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Students</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{group.student_count}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(16,185,129,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Targets</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{group.target_count}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(124,58,237,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Members</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{studentsForGroup(group).slice(0, 2).map((student) => student.name).join(', ') || '—'}</p>
											</div>
										</div>

										<div class="mt-4 flex flex-wrap gap-2">
											<AquaButton size="sm" variant="secondary" onclick={() => openEditGroup(group)}>
												<div class="flex items-center gap-1.5">
													<Edit3 class="h-4 w-4" />
													<span>Edit</span>
												</div>
											</AquaButton>
											<AquaButton size="sm" onclick={() => openTargetsForGroup(group)}>
												<div class="flex items-center gap-1.5">
													<Target class="h-4 w-4" />
													<span>Set targets</span>
												</div>
											</AquaButton>
											<AquaButton size="sm" variant="secondary" onclick={() => deleteGroup(group)}>
												<div class="flex items-center gap-1.5">
													<Trash2 class="h-4 w-4" />
													<span>Delete</span>
												</div>
											</AquaButton>
										</div>
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
							<div class="py-12 text-center">
								<Target class="mx-auto h-12 w-12 text-slate-300" />
								<p class="mt-3 text-sm text-slate-500">No academic targets match the current programme, group or search filters.</p>
							</div>
						</AquaCard>
					{:else}
						{#each filteredTargets as target (target.id)}
							<AquaCard>
								<div class="flex items-start gap-3">
									<div class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
										style="background: linear-gradient(135deg, #7c3aed, #4f46e5);">
										<Target class="h-5 w-5 text-white" />
									</div>

									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-center gap-2">
											<h2 class="text-sm font-semibold text-slate-900">{target.metric_name}</h2>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style="background: #ede9fe; color: #6d28d9;">{target.category}</span>
											{#if target.form_name}
												<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
													style="background: #f0fdf4; color: #166534;">{target.form_name}</span>
											{/if}
										</div>

										<div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
											<div class="rounded-2xl px-3 py-2" style="background: rgba(37,99,235,0.07);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Programme</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{target.programme_name || '—'}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(16,185,129,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Group</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{target.group_name || '—'}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(124,58,237,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Target value</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{target.target_value}</p>
											</div>
											<div class="rounded-2xl px-3 py-2" style="background: rgba(148,163,184,0.1);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Sort order</p>
												<p class="mt-1 text-sm font-bold text-slate-900">{target.sort_order}</p>
											</div>
										</div>

										<div class="mt-4 flex flex-wrap gap-2">
											<AquaButton size="sm" variant="secondary" onclick={() => openEditTarget(target)}>
												<div class="flex items-center gap-1.5">
													<Edit3 class="h-4 w-4" />
													<span>Edit</span>
												</div>
											</AquaButton>
											<AquaButton size="sm" variant="secondary" onclick={() => deleteTarget(target)}>
												<div class="flex items-center gap-1.5">
													<Trash2 class="h-4 w-4" />
													<span>Delete</span>
												</div>
											</AquaButton>
										</div>
									</div>
								</div>
							</AquaCard>
						{/each}
					{/if}
				</div>
			{:else}
				<div class="space-y-3">
					{#if filteredWeightages.length === 0}
						<AquaCard>
							<div class="py-12 text-center">
								<Scale class="mx-auto h-12 w-12 text-slate-300" />
								<p class="mt-3 text-sm text-slate-500">No form weightages match your search.</p>
							</div>
						</AquaCard>
					{:else}
						{#each filteredWeightages as item (item.form_definition_id)}
							<AquaCard>
								<div class="flex items-start gap-3">
									<div class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
										style="background: linear-gradient(135deg, {item.has_weightage ? '#059669' : '#94a3b8'}, {item.has_weightage ? '#10b981' : '#64748b'});">
										<Scale class="h-5 w-5 text-white" />
									</div>

									<div class="min-w-0 flex-1">
										<div class="flex flex-wrap items-center gap-2">
											<h2 class="text-sm font-semibold text-slate-900">{item.name || 'Unnamed form'}</h2>
											<span class="rounded-full px-2 py-0.5 text-[10px] font-bold"
												style={item.has_weightage ? 'background: #dcfce7; color: #166534;' : 'background: #e2e8f0; color: #475569;'}>
												{item.has_weightage ? 'Configured' : 'Unconfigured'}
											</span>
										</div>

										<p class="mt-1 text-xs text-slate-500">
											{item.department || 'General'}{item.procedure_name ? ` · ${item.procedure_name}` : ''}{item.section ? ` · ${item.section}` : ''}
										</p>

										<div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
											<div class="rounded-2xl px-3 py-2"
												style="background: rgba(16,185,129,0.08);">
												<p class="text-[10px] uppercase tracking-[0.16em] text-slate-500">Current points</p>
												<p class="mt-1 text-lg font-bold text-slate-900">{item.points}</p>
											</div>

											<div class="flex items-center gap-2">
												<input
													type="number"
													min="0"
													value={item.points}
													onchange={(event) => {
														const value = Number((event.currentTarget as HTMLInputElement).value);
														void saveWeightage(item, value);
													}}
													class="w-28 rounded-xl border px-3 py-2 text-sm outline-none"
													style="border-color: rgba(148,163,184,0.28); background: white;"
												/>
												<span class="text-xs font-medium text-slate-500">points</span>
											</div>
										</div>
									</div>
								</div>
							</AquaCard>
						{/each}
					{/if}
				</div>
			{/if}
		</div>

		<div class="space-y-3">
			<AquaCard>
				{#snippet header()}
					<ShieldCheck class="mr-2 h-4 w-4 text-blue-600" />
					<span class="text-sm font-semibold text-blue-900">Current focus</span>
				{/snippet}

				<div class="space-y-3 text-sm text-slate-600">
					{#if activeTab === 'programmes'}
						<div class="rounded-2xl px-4 py-4" style="background: #eff6ff; border: 1px solid rgba(96,165,250,0.28);">
							<p class="font-semibold text-slate-900">Programme catalogue</p>
							<p class="mt-1 text-xs text-slate-600">
								Create the academic programme anchors used by groups, targets and student assignment filters.
							</p>
						</div>
					{:else if activeTab === 'groups'}
						<div class="rounded-2xl px-4 py-4" style="background: #f0fdf4; border: 1px solid rgba(74,222,128,0.28);">
							<p class="font-semibold text-slate-900">Student grouping</p>
							<p class="mt-1 text-xs text-slate-600">
								Bind students into programme-linked academic groups before setting target goals for each cohort.
							</p>
						</div>
					{:else if activeTab === 'targets'}
						<div class="rounded-2xl px-4 py-4" style="background: #faf5ff; border: 1px solid rgba(196,181,253,0.32);">
							<p class="font-semibold text-slate-900">Target configuration</p>
							<p class="mt-1 text-xs text-slate-600">
								Define expected totals per group and optionally pin them to a specific case-record form for cleaner progress matching.
							</p>
						</div>
					{:else}
						<div class="rounded-2xl px-4 py-4" style="background: #ecfeff; border: 1px solid rgba(103,232,249,0.3);">
							<p class="font-semibold text-slate-900">Academic weightages</p>
							<p class="mt-1 text-xs text-slate-600">
								Assign point values to approved case-record forms so student progress can show earned and possible totals.
							</p>
						</div>
					{/if}

					<div class="space-y-2">
						<p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Quick guide</p>
						<div class="rounded-2xl px-3 py-3" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
							<div class="flex items-start gap-2">
								<CheckCircle2 class="mt-0.5 h-4 w-4 text-emerald-500" />
								<p class="text-xs text-slate-600">Start with a programme, then create at least one academic group for it.</p>
							</div>
						</div>
						<div class="rounded-2xl px-3 py-3" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
							<div class="flex items-start gap-2">
								<CheckCircle2 class="mt-0.5 h-4 w-4 text-emerald-500" />
								<p class="text-xs text-slate-600">Assign students to groups before configuring group targets.</p>
							</div>
						</div>
						<div class="rounded-2xl px-3 py-3" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
							<div class="flex items-start gap-2">
								<CheckCircle2 class="mt-0.5 h-4 w-4 text-emerald-500" />
								<p class="text-xs text-slate-600">Use weightages to control student-facing earned points from approved case-record forms.</p>
							</div>
						</div>
					</div>
				</div>
			</AquaCard>

			<AquaCard>
				{#snippet header()}
					<Settings2 class="mr-2 h-4 w-4 text-blue-600" />
					<span class="text-sm font-semibold text-blue-900">Snapshot</span>
				{/snippet}

				<div class="space-y-3">
					<div class="rounded-2xl px-4 py-3" style="background: rgba(37,99,235,0.07);">
						<p class="text-[11px] uppercase tracking-[0.16em] text-slate-500">Students without group</p>
						<p class="mt-1 text-2xl font-bold text-slate-900">
							{students.filter((student) => !student.academic_group_id).length}
						</p>
					</div>

					<div class="rounded-2xl px-4 py-3" style="background: rgba(16,185,129,0.08);">
						<p class="text-[11px] uppercase tracking-[0.16em] text-slate-500">Groups with targets</p>
						<p class="mt-1 text-2xl font-bold text-slate-900">
							{groups.filter((group) => group.target_count > 0).length}
						</p>
					</div>

					<div class="rounded-2xl px-4 py-3" style="background: rgba(124,58,237,0.08);">
						<p class="text-[11px] uppercase tracking-[0.16em] text-slate-500">Forms still unconfigured</p>
						<p class="mt-1 text-2xl font-bold text-slate-900">
							{weightages.filter((item) => !item.has_weightage).length}
						</p>
					</div>
				</div>
			</AquaCard>

			{#if activeTab === 'groups' && filteredGroups.length > 0}
				<AquaCard>
					{#snippet header()}
						<Users class="mr-2 h-4 w-4 text-blue-600" />
						<span class="text-sm font-semibold text-blue-900">Selected programme groups</span>
					{/snippet}

					<div class="space-y-2">
						{#each filteredGroups.slice(0, 4) as group (group.id)}
							<div class="rounded-2xl px-3 py-3" style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
								<div class="flex items-center justify-between gap-2">
									<div class="min-w-0">
										<p class="truncate text-sm font-semibold text-slate-900">{group.name}</p>
										<p class="text-xs text-slate-500">{group.programme_name}</p>
									</div>
									<button
										class="rounded-full p-2 cursor-pointer"
										style="background: #e0f2fe;"
										onclick={() => openTargetsForGroup(group)}
									>
										<ArrowRight class="h-4 w-4 text-sky-700" />
									</button>
								</div>
							</div>
						{/each}
					</div>
				</AquaCard>
			{/if}
		</div>
	</div>
</div>

{#if showProgrammeModal}
	<AquaModal title={editingProgrammeId ? 'Edit Programme' : 'Create Programme'} onclose={() => showProgrammeModal = false}>
		<div class="space-y-4 p-4">
			<div>
				<label for="programme-name" class="mb-1 block text-xs font-medium text-slate-600">Programme name *</label>
				<input
					id="programme-name"
					type="text"
					bind:value={programmeName}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="e.g. BDS"
				/>
			</div>

			<div>
				<label for="programme-code" class="mb-1 block text-xs font-medium text-slate-600">Code *</label>
				<input
					id="programme-code"
					type="text"
					bind:value={programmeCode}
					class="w-full rounded-xl border px-3 py-2 text-sm uppercase outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="e.g. BDS"
				/>
			</div>

			<div>
				<label for="programme-description" class="mb-1 block text-xs font-medium text-slate-600">Description</label>
				<textarea
					id="programme-description"
					rows="3"
					bind:value={programmeDescription}
					class="w-full resize-none rounded-xl border px-3 py-2 text-sm outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="Short summary for this programme"
				></textarea>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<div>
					<label for="programme-degree" class="mb-1 block text-xs font-medium text-slate-600">Degree type</label>
					<select
						id="programme-degree"
						bind:value={programmeDegreeType}
						class="w-full rounded-xl border px-3 py-2 text-sm outline-none bg-white"
						style="border-color: rgba(148,163,184,0.28);"
					>
						<option value="">Select degree type</option>
						{#each degreeTypes as degreeType (degreeType)}
							<option value={degreeType}>{degreeType}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="programme-duration" class="mb-1 block text-xs font-medium text-slate-600">Duration</label>
					<input
						id="programme-duration"
						type="text"
						bind:value={programmeDuration}
						class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
						style="border-color: rgba(148,163,184,0.28); background: white;"
						placeholder="e.g. 4 years"
					/>
				</div>
			</div>

			<label class="flex items-center gap-2 rounded-2xl px-3 py-3 text-sm text-slate-700"
				style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
				<input type="checkbox" bind:checked={programmeIsActive} />
				<span>Programme is active</span>
			</label>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => showProgrammeModal = false}>
					Cancel
				</AquaButton>
				<AquaButton fullWidth loading={saving} onclick={saveProgramme}>
					{editingProgrammeId ? 'Update Programme' : 'Create Programme'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showGroupModal}
	<AquaModal title={editingGroupId ? 'Edit Academic Group' : 'Create Academic Group'} onclose={() => showGroupModal = false}>
		<div class="space-y-4 p-4">
			<div>
				<label for="group-programme" class="mb-1 block text-xs font-medium text-slate-600">Programme *</label>
				<select
					id="group-programme"
					bind:value={groupProgrammeId}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none bg-white"
					style="border-color: rgba(148,163,184,0.28);"
				>
					<option value="">Select programme</option>
					{#each programmes as programme (programme.id)}
						<option value={programme.id}>{programme.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="group-name" class="mb-1 block text-xs font-medium text-slate-600">Group name *</label>
				<input
					id="group-name"
					type="text"
					bind:value={groupName}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="e.g. Third Year Cohort A"
				/>
			</div>

			<div>
				<label for="group-description" class="mb-1 block text-xs font-medium text-slate-600">Description</label>
				<textarea
					id="group-description"
					rows="3"
					bind:value={groupDescription}
					class="w-full resize-none rounded-xl border px-3 py-2 text-sm outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="Optional notes for this academic group"
				></textarea>
			</div>

			<label class="flex items-center gap-2 rounded-2xl px-3 py-3 text-sm text-slate-700"
				style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
				<input type="checkbox" bind:checked={groupIsActive} />
				<span>Group is active</span>
			</label>

			<div>
				<div class="mb-2 flex items-center justify-between">
					<p class="block text-xs font-medium text-slate-600">Assign students</p>
					<span class="text-[11px] text-slate-500">{groupStudentIds.length} selected</span>
				</div>

				<div class="max-h-64 space-y-2 overflow-y-auto rounded-2xl px-3 py-3"
					style="background: #f8fafc; border: 1px solid rgba(148,163,184,0.22);">
					{#if availableStudents.length === 0}
						<p class="text-sm text-slate-500">No students available for this programme.</p>
					{:else}
						{#each availableStudents as student (student.id)}
							<label class="flex items-center gap-3 rounded-xl px-3 py-2 text-sm cursor-pointer"
								style="background: white; border: 1px solid rgba(148,163,184,0.16);">
								<input
									type="checkbox"
									checked={groupStudentIds.includes(student.id)}
									onchange={() => toggleGroupStudent(student.id)}
								/>
								<div class="min-w-0 flex-1">
									<p class="truncate font-medium text-slate-900">{student.name}</p>
									<p class="text-xs text-slate-500">{student.student_id} · Year {student.year} · Sem {student.semester}</p>
								</div>
							</label>
						{/each}
					{/if}
				</div>
			</div>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => showGroupModal = false}>
					Cancel
				</AquaButton>
				<AquaButton fullWidth loading={saving} onclick={saveGroup}>
					{editingGroupId ? 'Update Group' : 'Create Group'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showTargetModal}
	<AquaModal title={editingTargetId ? 'Edit Academic Target' : 'Create Academic Target'} onclose={() => showTargetModal = false}>
		<div class="space-y-4 p-4">
			<div>
				<label for="target-group" class="mb-1 block text-xs font-medium text-slate-600">Academic group *</label>
				<select
					id="target-group"
					bind:value={targetGroupId}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none bg-white"
					style="border-color: rgba(148,163,184,0.28);"
				>
					<option value="">Select group</option>
					{#each selectableGroups as group (group.id)}
						<option value={group.id}>{group.programme_name} · {group.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="target-form" class="mb-1 block text-xs font-medium text-slate-600">Linked form definition</label>
				<select
					id="target-form"
					value={targetFormDefinitionId}
					onchange={(event) => applyFormToTarget((event.currentTarget as HTMLSelectElement).value)}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none bg-white"
					style="border-color: rgba(148,163,184,0.28);"
				>
					<option value="">Not linked to a specific form</option>
					{#each availableTargetForms as form (form.form_definition_id)}
						<option value={form.form_definition_id}>
							{form.department || 'General'} · {form.name || 'Unnamed form'}
						</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="target-metric" class="mb-1 block text-xs font-medium text-slate-600">Metric name *</label>
				<input
					id="target-metric"
					type="text"
					bind:value={targetMetricName}
					class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
					style="border-color: rgba(148,163,184,0.28); background: white;"
					placeholder="e.g. Complete Denture Cases"
				/>
			</div>

			<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
				<div>
					<label for="target-category" class="mb-1 block text-xs font-medium text-slate-600">Category</label>
					<select
						id="target-category"
						bind:value={targetCategory}
						class="w-full rounded-xl border px-3 py-2 text-sm outline-none bg-white"
						style="border-color: rgba(148,163,184,0.28);"
					>
						{#each targetCategories as category (category)}
							<option value={category}>{category}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="target-value" class="mb-1 block text-xs font-medium text-slate-600">Target value</label>
					<input
						id="target-value"
						type="number"
						min="0"
						bind:value={targetValue}
						class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
						style="border-color: rgba(148,163,184,0.28); background: white;"
					/>
				</div>

				<div>
					<label for="target-order" class="mb-1 block text-xs font-medium text-slate-600">Sort order</label>
					<input
						id="target-order"
						type="number"
						min="0"
						bind:value={targetSortOrder}
						class="w-full rounded-xl border px-3 py-2 text-sm outline-none"
						style="border-color: rgba(148,163,184,0.28); background: white;"
					/>
				</div>
			</div>

			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => showTargetModal = false}>
					Cancel
				</AquaButton>
				<AquaButton fullWidth loading={saving} onclick={saveTarget}>
					{editingTargetId ? 'Update Target' : 'Create Target'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
