<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { labsApi, type LabInfo, type LabTest, type LabTestGroup } from '$lib/api/labs';
	import { adminApi } from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { FlaskConical, Trash2, X, Plus, Pencil } from 'lucide-svelte';

	const DEFAULT_LAB_TYPE = 'General';
	const COMMON_LAB_TYPES = [
		'Pathology',
		'Radiology',
		'Microbiology',
		'Biochemistry',
		'Hematology',
		'General'
	];

	function createEmptyLabData() {
		return {
			name: '',
			block: '',
			lab_type: DEFAULT_LAB_TYPE,
			department: '',
			location: '',
			contact_phone: '',
			operating_hours: '',
			is_active: true
		};
	}

	function normalizeLabText(value: string) {
		return value.trim();
	}

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let labs: LabInfo[] = $state([]);

	// Configuration panel state
	let configLab: LabInfo | null = $state(null);
	let configTab = $state('tests');
	let labTests: LabTest[] = $state([]);
	let labGroups: LabTestGroup[] = $state([]);
	let loadingConfig = $state(false);

	// Create/Edit lab modal
	let labModal = $state(false);
	let editingLab: LabInfo | null = $state(null);
	let labData = $state(createEmptyLabData());
	let savingLab = $state(false);
	let departments: string[] = $state([]);
	let availableLabTypes = $derived.by(() => {
		const suggestedTypes = [...COMMON_LAB_TYPES, ...labs.map((lab) => lab.lab_type), labData.lab_type]
			.map((value) => value.trim())
			.filter((value) => value.length > 0);

		return Array.from(new Set(suggestedTypes));
	});

	// Test modal
	let testModal = $state(false);
	let editingTest: LabTest | null = $state(null);
	let testData = $state({
		name: '',
		code: '',
		category: 'Hematology'
	});
	let savingTest = $state(false);

	// Group modal
	let groupModal = $state(false);
	let editingGroup: LabTestGroup | null = $state(null);
	let groupData = $state({
		name: '',
		test_ids: [] as string[]
	});
	let savingGroup = $state(false);
	let allAvailableTests: LabTest[] = $state([]);

	// Delete confirmation
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	const configTabs = [
		{ id: 'tests', label: 'TESTS' },
		{ id: 'groups', label: 'GROUPS' }
	];

	onMount(async () => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		loadLabs();
		try {
			const deptList = await adminApi.getDepartments();
			departments = deptList.filter((d: any) => d.is_active !== false).map((d: any) => d.name);
		} catch (e: any) {
			// non-critical, departments list is optional
		}
	});

	async function loadLabs() {
		loading = true;
		error = '';
		try {
			labs = await labsApi.getAll();
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load labs';
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		editingLab = null;
		labData = createEmptyLabData();
		labModal = true;
	}

	async function saveLab() {
		const payload = {
			name: normalizeLabText(labData.name),
			block: normalizeLabText(labData.block),
			lab_type: normalizeLabText(labData.lab_type) || DEFAULT_LAB_TYPE,
			department: normalizeLabText(labData.department),
			location: normalizeLabText(labData.location),
			contact_phone: normalizeLabText(labData.contact_phone),
			operating_hours: normalizeLabText(labData.operating_hours),
			is_active: labData.is_active
		};

		if (!payload.name || !payload.department) {
			toastStore.addToast('Name and department are required', 'error');
			return;
		}
		savingLab = true;
		try {
			if (editingLab) {
				await labsApi.update(editingLab.id, payload);
				toastStore.addToast('Lab updated successfully', 'success');
			} else {
				await labsApi.create(payload);
				toastStore.addToast('Lab created successfully', 'success');
			}
			labModal = false;
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to save lab', 'error');
		} finally {
			savingLab = false;
		}
	}

	async function openConfigPanel(lab: LabInfo) {
		configLab = lab;
		configTab = 'tests';
		await loadLabConfig(lab.id);
	}

	function closeConfigPanel() {
		configLab = null;
		labTests = [];
		labGroups = [];
	}

	async function loadLabConfig(labId: string) {
		loadingConfig = true;
		try {
			[labTests, labGroups] = await Promise.all([
				labsApi.getTests(labId),
				labsApi.getGroups(labId)
			]);
		} catch (e: any) {
			toastStore.addToast('Failed to load lab configuration', 'error');
		} finally {
			loadingConfig = false;
		}
	}

	function openTestModal() {
		editingTest = null;
		testData = { name: '', code: '', category: 'Hematology' };
		testModal = true;
	}

	function openEditTestModal(test: LabTest) {
		editingTest = test;
		testData = {
			name: test.name,
			code: test.code,
			category: test.category
		};
		testModal = true;
	}

	async function saveTest() {
		if (!configLab || !testData.name.trim() || !testData.code.trim()) {
			toastStore.addToast('Name and code are required', 'error');
			return;
		}
		savingTest = true;
		try {
			if (editingTest) {
				await labsApi.updateTest(configLab.id, editingTest.id, testData);
				toastStore.addToast('Test updated successfully', 'success');
			} else {
				await labsApi.createTest(configLab.id, testData);
				toastStore.addToast('Test created successfully', 'success');
			}
			testModal = false;
			await loadLabConfig(configLab.id);
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || `Failed to ${editingTest ? 'update' : 'create'} test`, 'error');
		} finally {
			savingTest = false;
		}
	}

	function confirmDeleteTest(test: LabTest) {
		confirmMessage = 'Delete test "' + test.name + '"?';
		confirmAction = async () => {
			actionLoading = true;
			try {
				await labsApi.deleteTest(configLab!.id, test.id);
				toastStore.addToast('Test deleted', 'success');
				await loadLabConfig(configLab!.id);
				await loadLabs();
			} catch (e: any) {
				toastStore.addToast('Failed to delete test', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function openGroupModal() {
		editingGroup = null;
		groupData = { name: '', test_ids: [] };
		if (configLab) {
			allAvailableTests = await labsApi.getTests(configLab.id);
		}
		groupModal = true;
	}

	async function openEditGroupModal(group: LabTestGroup) {
		editingGroup = group;
		groupData = {
			name: group.name,
			test_ids: group.tests.map(t => t.id)
		};
		if (configLab) {
			allAvailableTests = await labsApi.getTests(configLab.id);
		}
		groupModal = true;
	}

	function toggleTestInGroup(testId: string) {
		if (groupData.test_ids.includes(testId)) {
			groupData.test_ids = groupData.test_ids.filter(id => id !== testId);
		} else {
			groupData.test_ids = [...groupData.test_ids, testId];
		}
	}

	async function saveGroup() {
		if (!configLab || !groupData.name.trim()) {
			toastStore.addToast('Group name is required', 'error');
			return;
		}
		savingGroup = true;
		try {
			if (editingGroup) {
				await labsApi.updateGroup(configLab.id, editingGroup.id, groupData);
				toastStore.addToast('Group updated successfully', 'success');
			} else {
				await labsApi.createGroup(configLab.id, groupData);
				toastStore.addToast('Group created successfully', 'success');
			}
			groupModal = false;
			await loadLabConfig(configLab.id);
			await loadLabs();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || `Failed to ${editingGroup ? 'update' : 'create'} group`, 'error');
		} finally {
			savingGroup = false;
		}
	}

	function confirmDeleteGroup(group: LabTestGroup) {
		confirmMessage = 'Delete group "' + group.name + '"?';
		confirmAction = async () => {
			actionLoading = true;
			try {
				await labsApi.deleteGroup(configLab!.id, group.id);
				toastStore.addToast('Group deleted', 'success');
				await loadLabConfig(configLab!.id);
				await loadLabs();
			} catch (e: any) {
				toastStore.addToast('Failed to delete group', 'error');
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}
</script>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<div class="text-red-500 text-center py-4 text-sm">{error}</div>
	{:else}
		<div class="flex items-center justify-between mb-4">
			<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Laboratory Services</p>
			<button
				onclick={openCreateModal}
				class="px-4 py-2 text-sm font-semibold text-white rounded-full"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
			>
				Add New
			</button>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			{#each labs as lab (lab.id)}
				<div
					class="rounded-2xl p-4"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
				>
					<div class="flex items-start justify-between mb-4">
						<div class="flex items-center gap-3">
							<div
								class="flex items-center justify-center rounded-xl"
								style="width: 44px; height: 44px; background: linear-gradient(to bottom, #06b6d4, #0891b2); box-shadow: 0 2px 8px rgba(6,182,212,0.3);"
							>
								<FlaskConical class="w-5 h-5 text-white" />
							</div>
							<div>
								<h3 class="font-bold text-slate-900">{lab.name}</h3>
								<p class="text-xs text-slate-500">
									{lab.lab_type || DEFAULT_LAB_TYPE} • {lab.block || 'No Block'} • {lab.is_active ? 'Active' : 'Inactive'}
								</p>
							</div>
						</div>
						<button
							onclick={() => openConfigPanel(lab)}
							class="px-4 py-1.5 text-xs font-semibold text-slate-600 rounded-full"
							style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0); box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);"
						>
							Configure
						</button>
					</div>

					<div class="grid grid-cols-2 gap-3">
						<div class="rounded-xl px-4 py-3 text-center" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe);">
							<p class="text-xs font-semibold text-blue-600 tracking-wide uppercase">Tests</p>
							<p class="text-2xl font-bold text-blue-900">{lab.test_count || 0}</p>
						</div>
						<div class="rounded-xl px-4 py-3 text-center" style="background: linear-gradient(to bottom, #faf5ff, #ede9fe);">
							<p class="text-xs font-semibold text-purple-600 tracking-wide uppercase">Groups</p>
							<p class="text-2xl font-bold text-purple-900">{lab.group_count || 0}</p>
						</div>
					</div>
				</div>
			{/each}
		</div>

		{#if configLab}
			<div
				class="mt-6 rounded-2xl p-4"
				style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);"
			>
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-3">
						<div>
							<h3 class="font-bold text-slate-900">{configLab.name} Configuration</h3>
							<p class="text-xs text-slate-500">{configLab.lab_type || DEFAULT_LAB_TYPE} • {configLab.department}</p>
						</div>
						<TabBar tabs={configTabs} activeTab={configTab} onchange={(id) => configTab = id} />
					</div>
					<button onclick={closeConfigPanel} class="p-1.5 text-slate-400 hover:text-slate-600">
						<X class="w-5 h-5" />
					</button>
				</div>

				{#if loadingConfig}
					<div class="flex items-center justify-center py-8">
						<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
					</div>
				{:else if configTab === 'tests'}
					<div class="flex items-center justify-between mb-3">
						<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Available Tests</p>
						<button onclick={openTestModal} class="flex items-center gap-1 text-sm font-semibold text-blue-600">
							<Plus class="w-4 h-4" /> Add New Test
						</button>
					</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						{#each labTests as test (test.id)}
							<div class="flex items-center justify-between p-3 rounded-xl" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5); border: 1px solid rgba(0,0,0,0.04);">
								<div>
									<p class="font-semibold text-slate-900">{test.name}</p>
									<p class="text-xs text-slate-500">{test.category} • {test.code}</p>
								</div>
							<div class="flex items-center gap-1">
								<button onclick={() => openEditTestModal(test)} class="p-1.5 text-slate-400 hover:text-blue-500">
									<Pencil class="w-4 h-4" />
								</button>
								<button onclick={() => confirmDeleteTest(test)} class="p-1.5 text-slate-400 hover:text-red-500">
									<Trash2 class="w-4 h-4" />
								</button>
							</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex items-center justify-between mb-3">
						<p class="text-xs font-semibold text-slate-500 tracking-wide uppercase">Test Groups / Packages</p>
						<button onclick={openGroupModal} class="flex items-center gap-1 text-sm font-semibold text-blue-600">
							<Plus class="w-4 h-4" /> Create Group
						</button>
					</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						{#each labGroups as group (group.id)}
							<div class="p-3 rounded-xl" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5); border: 1px solid rgba(0,0,0,0.04);">
								<div class="flex items-center justify-between mb-2">
									<p class="font-semibold text-slate-900">{group.name}</p>
								<div class="flex items-center gap-1">
									<button onclick={() => openEditGroupModal(group)} class="p-1.5 text-slate-400 hover:text-blue-500">
										<Pencil class="w-4 h-4" />
									</button>
									<button onclick={() => confirmDeleteGroup(group)} class="p-1.5 text-slate-400 hover:text-red-500">
										<Trash2 class="w-4 h-4" />
									</button>
								</div>
								</div>
								<div class="flex flex-wrap gap-1.5">
									{#each group.tests as test (test.id)}
										<span class="px-2 py-1 text-xs font-medium text-blue-700 rounded-md" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe);">{test.name}</span>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	{/if}

{#if labModal}
	<AquaModal title={editingLab ? 'Edit Lab' : 'Add New Lab'} onclose={() => { labModal = false; }}>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="space-y-3">
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Name *</label>
				<input type="text" placeholder="e.g., Central Pathology Lab" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={labData.name} />
			</div>
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Lab Type</label>
				<input
					type="text"
					list="lab-type-options"
					placeholder="Select or type a lab type"
					class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl"
					style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
					bind:value={labData.lab_type}
				/>
				<datalist id="lab-type-options">
					{#each availableLabTypes as labType (labType)}
						<option value={labType}></option>
					{/each}
				</datalist>
				<p class="mt-1 text-xs text-slate-500">Pick an existing type or enter a new one.</p>
			</div>
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Department *</label>
				<select
					class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #fafafa);"
					bind:value={labData.department}
				>
					<option value="" disabled selected>Select a department</option>
					{#each departments as dept (dept)}
						<option value={dept}>{dept}</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Block</label>
				<input type="text" placeholder="e.g., Block C" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={labData.block} />
			</div>
			<div class="flex items-center gap-2">
				<input type="checkbox" id="lab-active" class="rounded" bind:checked={labData.is_active} />
				<label for="lab-active" class="text-sm text-slate-700">Active</label>
			</div>
		</div>
		<div class="flex gap-2 mt-4">
			<button onclick={() => { labModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingLab}>Cancel</button>
			<button onclick={saveLab} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" disabled={savingLab}>{savingLab ? 'Saving...' : editingLab ? 'Update Lab' : 'Create Lab'}</button>
		</div>
	</AquaModal>
{/if}

{#if testModal}
	<AquaModal title={editingTest ? 'Edit Lab Test' : 'Add New Lab Test'} onclose={() => { testModal = false; }}>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="space-y-3">
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Test Name</label>
				<input type="text" placeholder="e.g. Complete Blood Count" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={testData.name} />
			</div>
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Category</label>
				<input type="text" placeholder="e.g. Hematology" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={testData.category} />
			</div>
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Test Code</label>
				<input type="text" placeholder="e.g. HEM001" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={testData.code} />
			</div>
		</div>
		<div class="flex gap-2 mt-4">
			<button onclick={() => { testModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingTest}>Cancel</button>
			<button onclick={saveTest} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" disabled={savingTest}>{savingTest ? (editingTest ? 'Updating...' : 'Creating...') : (editingTest ? 'Update Test' : 'Create Test')}</button>
		</div>
	</AquaModal>
{/if}

{#if groupModal}
	<AquaModal title={editingGroup ? 'Edit Test Group' : 'Create Test Group'} onclose={() => { groupModal = false; }}>
		<div class="space-y-3">
			<!-- svelte-ignore a11y_label_has_associated_control -->
			<div>
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Group Name</label>
				<input type="text" placeholder="e.g. Executive Health Checkup" class="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-xl" style="background: linear-gradient(to bottom, #ffffff, #fafafa);" bind:value={groupData.name} />
			</div>
			<div>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<label class="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1">Select Tests</label>
				<div class="max-h-48 overflow-y-auto rounded-xl p-2" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5); border: 1px solid rgba(0,0,0,0.05);">
					{#each allAvailableTests as test (test.id)}
						<button type="button" onclick={() => toggleTestInGroup(test.id)} class="w-full text-left px-3 py-2 rounded-lg mb-1 transition-colors" class:bg-blue-50={groupData.test_ids.includes(test.id)} class:hover:bg-slate-100={!groupData.test_ids.includes(test.id)}>
							<p class="font-semibold text-sm text-slate-900">{test.name}</p>
							<p class="text-xs text-slate-500">{test.category} • {test.code}</p>
						</button>
					{/each}
				</div>
			</div>
		</div>
		<div class="flex gap-2 mt-4">
			<button onclick={() => { groupModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingGroup}>Cancel</button>
			<button onclick={saveGroup} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" disabled={savingGroup}>{savingGroup ? (editingGroup ? 'Updating...' : 'Creating...') : (editingGroup ? 'Update Group' : 'Create Group')}</button>
		</div>
	</AquaModal>
{/if}

{#if confirmModal}
	<AquaModal title="Confirm Delete" onclose={() => { confirmModal = false; }}>
		<p class="text-sm text-slate-700 mb-4">{confirmMessage}</p>
		<div class="flex gap-2">
			<button onclick={() => { confirmModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={actionLoading}>Cancel</button>
			<button onclick={() => confirmAction?.()} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #ef4444, #dc2626);" disabled={actionLoading}>{actionLoading ? 'Deleting...' : 'Delete'}</button>
		</div>
	</AquaModal>
{/if}
