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
	import { slide, fade } from 'svelte/transition';
	import { flip } from 'svelte/animate';
	import { FlaskConical, Trash2, X, Plus, Pencil, ChevronRight, Settings2, TestTube2, Layers, MapPin, Phone, Clock, Building2, Users, Loader2 } from 'lucide-svelte';

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
	let togglingLabId = $state<string | null>(null);
	let togglingTestId = $state<string | null>(null);
	let togglingGroupId = $state<string | null>(null);

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

	function openEditLabModal(lab: LabInfo) {
		editingLab = lab;
		labData = {
			name: lab.name,
			block: lab.block || '',
			lab_type: lab.lab_type || DEFAULT_LAB_TYPE,
			department: lab.department || '',
			location: lab.location || '',
			contact_phone: lab.contact_phone || '',
			operating_hours: lab.operating_hours || '',
			is_active: lab.is_active,
		};
		labModal = true;
	}

	function closeLabModal() {
		labModal = false;
		editingLab = null;
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
			if (editingLab && configLab?.id === editingLab.id) {
				configLab = {
					...configLab,
					...payload,
					block: payload.block || undefined,
					location: payload.location || undefined,
					contact_phone: payload.contact_phone || undefined,
					operating_hours: payload.operating_hours || undefined,
				};
			}
			editingLab = null;
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
		testData = {
			name: '',
			code: '',
			category: 'Hematology'
		};
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
			const payload = {
				name: testData.name.trim(),
				code: testData.code.trim(),
				category: testData.category.trim(),
			};
			if (editingTest) {
				await labsApi.updateTest(configLab.id, editingTest.id, payload);
				toastStore.addToast('Test updated successfully', 'success');
			} else {
				await labsApi.createTest(configLab.id, payload);
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
			const payload = {
				name: groupData.name.trim(),
				test_ids: groupData.test_ids,
			};
			if (editingGroup) {
				await labsApi.updateGroup(configLab.id, editingGroup.id, payload);
				toastStore.addToast('Group updated successfully', 'success');
			} else {
				await labsApi.createGroup(configLab.id, payload);
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

	async function toggleLabActive(lab: LabInfo) {
		togglingLabId = lab.id;
		try {
			await labsApi.update(lab.id, { is_active: !lab.is_active });
			await loadLabs();
			if (configLab?.id === lab.id) {
				await loadLabConfig(lab.id);
			}
			toastStore.addToast(`Lab ${lab.is_active ? 'disabled' : 'enabled'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update lab status', 'error');
		} finally {
			togglingLabId = null;
		}
	}

	async function toggleTestActive(test: LabTest) {
		if (!configLab) return;
		togglingTestId = test.id;
		try {
			await labsApi.updateTest(configLab.id, test.id, { is_active: !test.is_active });
			await loadLabConfig(configLab.id);
			await loadLabs();
			toastStore.addToast(`Test ${test.is_active ? 'disabled' : 'enabled'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update test status', 'error');
		} finally {
			togglingTestId = null;
		}
	}

	async function toggleGroupActive(group: LabTestGroup) {
		if (!configLab) return;
		togglingGroupId = group.id;
		try {
			await labsApi.updateGroup(configLab.id, group.id, { is_active: !group.is_active });
			await loadLabConfig(configLab.id);
			await loadLabs();
			toastStore.addToast(`Group ${group.is_active ? 'disabled' : 'enabled'}`, 'success');
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to update group status', 'error');
		} finally {
			togglingGroupId = null;
		}
	}
</script>

{#if loading}
<div class="flex items-center justify-center py-16">
<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
</div>
{:else if error}
<div class="text-red-500 text-center py-4 text-sm">{error}</div>
{:else}

<!-- ── Page Header ─────────────────────────────────── -->
<div class="flex items-center justify-between mb-5">
<div>
<h1 class="text-lg font-bold text-slate-900">Laboratory Services</h1>
<p class="text-xs text-slate-500 mt-0.5">
{labs.filter(l => l.is_active).length} active · {labs.filter(l => !l.is_active).length} inactive
</p>
</div>
<div class="flex items-center gap-2">
<button
onclick={() => goto('/admin/labs/technicians')}
class="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold rounded-xl cursor-pointer transition-all hover:scale-105 active:scale-95"
style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); color: #0f172a; border: 1px solid rgba(148,163,184,0.45); box-shadow: 0 2px 8px rgba(15,23,42,0.08);"
>
<Users class="w-4 h-4" />
Technician Batches
</button>
<button
onclick={openCreateModal}
class="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white rounded-xl cursor-pointer transition-all hover:scale-105 active:scale-95"
style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.35);"
>
<Plus class="w-4 h-4" />
Add Lab
</button>
</div>
</div>

<!-- ── Desktop Table ──────────────────────────────── -->
<div class="hidden md:block rounded-2xl overflow-hidden"
style="box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.07);">

<!-- Table header -->
<div class="grid grid-cols-[1fr_120px_100px_80px_80px_180px] gap-3 px-4 py-2.5"
style="background: linear-gradient(to bottom, #f1f5f9, #e8edf3); border-bottom: 1px solid rgba(0,0,0,0.08);">
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Laboratory</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Type</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Department</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider text-center">Tests</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider text-center">Groups</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Actions</span>
</div>

<!-- Rows -->
{#each labs as lab (lab.id)}
<div
animate:flip={{ duration: 250 }}
class="grid grid-cols-[1fr_120px_100px_80px_80px_180px] gap-3 items-center px-4 py-3 transition-all duration-200 cursor-default group border-b last:border-b-0"
style="
background: {lab.is_active
? (configLab?.id === lab.id ? 'linear-gradient(to right, #eff6ff, #f0f9ff)' : 'white')
: 'linear-gradient(to right, #fafafa, #f5f5f5)'};
border-bottom-color: rgba(0,0,0,0.05);
{lab.is_active ? '' : 'opacity: 0.72;'}
"
>
<!-- Name + status dot -->
<div class="flex items-center gap-3 min-w-0">
<div class="relative shrink-0">
<div class="flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-200"
style="background: {lab.is_active
? 'linear-gradient(to bottom, #06b6d4, #0891b2)'
: 'linear-gradient(to bottom, #94a3b8, #64748b)'};
box-shadow: {lab.is_active ? '0 2px 8px rgba(6,182,212,0.3)' : 'none'};">
<FlaskConical class="w-4 h-4 text-white" />
</div>
<!-- Live status dot -->
<span class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white transition-colors duration-300"
style="background: {lab.is_active ? '#22c55e' : '#94a3b8'};"></span>
</div>
<div class="min-w-0">
<p class="font-semibold text-slate-900 text-sm truncate">{lab.name}</p>
<p class="text-xs text-slate-400 truncate">{lab.block || 'No block'} {lab.location ? '· ' + lab.location : ''}</p>
</div>
</div>

<!-- Type -->
<span class="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium truncate"
style="background: rgba(99,102,241,0.1); color: #4338ca; max-width: 110px;">
{lab.lab_type || DEFAULT_LAB_TYPE}
</span>

<!-- Department -->
<span class="text-xs text-slate-600 truncate">{lab.department || '—'}</span>

<!-- Tests count -->
<div class="flex flex-col items-center">
<span class="text-lg font-bold text-blue-700">{lab.test_count || 0}</span>
<span class="text-[9px] text-slate-400 uppercase tracking-wide">tests</span>
</div>

<!-- Groups count -->
<div class="flex flex-col items-center">
<span class="text-lg font-bold text-purple-700">{lab.group_count || 0}</span>
<span class="text-[9px] text-slate-400 uppercase tracking-wide">groups</span>
</div>

<!-- Actions -->
<div class="flex items-center justify-end gap-1.5">
<button
type="button"
onclick={() => toggleLabActive(lab)}
disabled={togglingLabId === lab.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={lab.is_active}
aria-label={`Toggle ${lab.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${lab.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${lab.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingLabId === lab.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
<button
onclick={() => openEditLabModal(lab)}
class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 cursor-pointer transition-all duration-150"
title="Edit lab"
>
<Pencil class="w-4 h-4" />
</button>
<button
onclick={() => openConfigPanel(lab)}
class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all duration-200 hover:scale-105 active:scale-95"
style="{configLab?.id === lab.id
? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 2px 6px rgba(37,99,235,0.3);'
: 'background: linear-gradient(to bottom, #f1f5f9, #e2e8f0); color: #475569; border: 1px solid rgba(0,0,0,0.07);'}"
>
<Settings2 class="w-3 h-3" />
Config
</button>
</div>
</div>
{/each}

{#if labs.length === 0}
<div class="py-16 text-center text-slate-400">
<FlaskConical class="w-10 h-10 mx-auto mb-3 opacity-30" />
<p class="text-sm font-medium">No labs yet</p>
<p class="text-xs mt-1">Click "Add Lab" to get started</p>
</div>
{/if}
</div>

<!-- ── Mobile Cards ───────────────────────────────── -->
<div class="md:hidden space-y-3">
{#each labs as lab (lab.id)}
<div
animate:flip={{ duration: 250 }}
class="rounded-2xl p-4 transition-all duration-200"
style="
background: {lab.is_active
? 'linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)'
: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)'};
box-shadow: {lab.is_active
? '0 2px 12px rgba(6,182,212,0.1), 0 1px 3px rgba(0,0,0,0.06)'
: '0 1px 4px rgba(0,0,0,0.06)'};
border: 1px solid {lab.is_active ? 'rgba(6,182,212,0.15)' : 'rgba(0,0,0,0.07)'};
{lab.is_active ? '' : 'opacity: 0.8;'}
"
>
<!-- Card header -->
<div class="flex items-start justify-between mb-3">
<div class="flex items-center gap-3">
<div class="relative shrink-0">
<div class="flex items-center justify-center w-10 h-10 rounded-xl"
style="background: {lab.is_active
? 'linear-gradient(to bottom, #06b6d4, #0891b2)'
: 'linear-gradient(to bottom, #94a3b8, #64748b)'};
box-shadow: {lab.is_active ? '0 2px 8px rgba(6,182,212,0.3)' : 'none'};">
<FlaskConical class="w-5 h-5 text-white" />
</div>
<span class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white"
style="background: {lab.is_active ? '#22c55e' : '#94a3b8'};"></span>
</div>
<div>
<h3 class="font-bold text-slate-900 text-sm">{lab.name}</h3>
<p class="text-xs text-slate-500">{lab.lab_type || DEFAULT_LAB_TYPE} · {lab.department || '—'}</p>
</div>
</div>
<button
type="button"
onclick={() => toggleLabActive(lab)}
disabled={togglingLabId === lab.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={lab.is_active}
aria-label={`Toggle ${lab.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${lab.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${lab.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingLabId === lab.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
</div>

<!-- Stats row -->
<div class="grid grid-cols-2 gap-2 mb-3">
<div class="rounded-xl px-3 py-2.5 text-center"
style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid rgba(59,130,246,0.1);">
<p class="text-xs font-semibold text-blue-600 uppercase tracking-wide">Tests</p>
<p class="text-xl font-bold text-blue-900">{lab.test_count || 0}</p>
</div>
<div class="rounded-xl px-3 py-2.5 text-center"
style="background: linear-gradient(to bottom, #faf5ff, #ede9fe); border: 1px solid rgba(139,92,246,0.1);">
<p class="text-xs font-semibold text-purple-600 uppercase tracking-wide">Groups</p>
<p class="text-xl font-bold text-purple-900">{lab.group_count || 0}</p>
</div>
</div>

<!-- Action row -->
<div class="flex gap-2">
<button
onclick={() => openEditLabModal(lab)}
class="flex items-center justify-center gap-1 px-3 py-2 rounded-xl text-xs font-semibold text-blue-600 cursor-pointer"
style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.15);"
>
<Pencil class="w-3.5 h-3.5" />Edit
</button>
<button
onclick={() => openConfigPanel(lab)}
class="flex items-center justify-center gap-1 px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer"
style="{configLab?.id === lab.id
? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white;'
: 'background: linear-gradient(to bottom, #f1f5f9, #e2e8f0); color: #475569; border: 1px solid rgba(0,0,0,0.08);'}"
>
<Settings2 class="w-3.5 h-3.5" />Config
</button>
</div>
</div>
{/each}

{#if labs.length === 0}
<div class="py-16 text-center text-slate-400">
<FlaskConical class="w-10 h-10 mx-auto mb-3 opacity-30" />
<p class="text-sm font-medium">No labs yet. Click "Add Lab" to get started.</p>
</div>
{/if}
</div>

<!-- ── Configure Panel ───────────────────────────── -->
{#if configLab}
<div
transition:fade={{ duration: 200 }}
class="fixed inset-0 z-50 flex items-center justify-center p-4"
style="background: rgba(0,0,0,0.45);"
role="dialog"
tabindex="-1"
aria-modal="true"
onkeydown={(e) => { if (e.key === 'Escape') closeConfigPanel(); }}
onclick={(e) => { if (e.target === e.currentTarget) closeConfigPanel(); }}
>
<div
transition:slide={{ duration: 300, axis: 'y' }}
class="rounded-2xl overflow-hidden w-full max-w-2xl max-h-[88vh] flex flex-col"
style="box-shadow: 0 8px 40px rgba(0,0,0,0.25); border: 1px solid rgba(0,0,0,0.08);"
>
<!-- Panel header -->
<div class="px-5 py-4"
style="background: linear-gradient(to bottom, #1e40af, #1d4ed8); border-bottom: 1px solid rgba(255,255,255,0.1);">
<div class="flex items-start justify-between gap-3">
<div class="flex items-center gap-3 min-w-0">
<div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);">
<Settings2 class="w-5 h-5 text-white" />
</div>
<div class="min-w-0">
<div class="flex items-center gap-2 flex-wrap">
<span class="text-xs text-blue-200 font-medium">Configure</span>
<ChevronRight class="w-3 h-3 text-blue-300" />
<h2 class="text-base font-bold text-white truncate">{configLab.name}</h2>
{#if configLab.is_active}
<span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
style="background: rgba(34,197,94,0.25); color: #86efac; border: 1px solid rgba(34,197,94,0.3);">
ACTIVE
</span>
{:else}
<span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
style="background: rgba(148,163,184,0.2); color: #cbd5e1; border: 1px solid rgba(148,163,184,0.25);">
INACTIVE
</span>
{/if}
</div>
<p class="text-xs text-blue-200 mt-0.5">{configLab.lab_type || DEFAULT_LAB_TYPE} · {configLab.department}</p>
</div>
</div>
<div class="flex items-center gap-2 shrink-0">
<button
onclick={() => configLab && openEditLabModal(configLab)}
class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:scale-105"
style="background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.2);"
>
<Pencil class="w-3 h-3" />Edit Lab
</button>
<button
onclick={closeConfigPanel}
class="p-1.5 rounded-lg text-blue-200 hover:text-white hover:bg-white/10 cursor-pointer transition-all"
title="Close"
>
<X class="w-5 h-5" />
</button>
</div>
</div>

<!-- Tab bar inside header -->
<div class="flex gap-1 mt-4">
<button
onclick={() => configTab = 'tests'}
class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold cursor-pointer transition-all duration-200"
style="{configTab === 'tests'
? 'background: white; color: #1d4ed8; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'
: 'color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.1);'}"
>
<TestTube2 class="w-4 h-4" />
Tests
{#if labTests.length > 0}
<span class="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
style="{configTab === 'tests' ? 'background: #dbeafe; color: #1d4ed8;' : 'background: rgba(255,255,255,0.2); color: white;'}">
{labTests.length}
</span>
{/if}
</button>
<button
onclick={() => configTab = 'groups'}
class="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold cursor-pointer transition-all duration-200"
style="{configTab === 'groups'
? 'background: white; color: #1d4ed8; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'
: 'color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.1);'}"
>
<Layers class="w-4 h-4" />
Groups
{#if labGroups.length > 0}
<span class="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
style="{configTab === 'groups' ? 'background: #ede9fe; color: #5b21b6;' : 'background: rgba(255,255,255,0.2); color: white;'}">
{labGroups.length}
</span>
{/if}
</button>
</div>
</div>

<!-- Panel body -->
<div class="bg-white overflow-y-auto flex-1">
{#if loadingConfig}
<div class="flex items-center justify-center py-12">
<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
</div>

{:else if configTab === 'tests'}
<!-- Tests section -->
<div class="px-5 py-4">
<div class="flex items-center justify-between mb-4">
<div>
<p class="text-sm font-bold text-slate-800">Lab Tests</p>
<p class="text-xs text-slate-500">{labTests.filter(t => t.is_active).length} active / {labTests.length} total</p>
</div>
<button
onclick={openTestModal}
class="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white rounded-xl cursor-pointer transition-all hover:scale-105 active:scale-95"
style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 6px rgba(37,99,235,0.3);"
>
<Plus class="w-3.5 h-3.5" />Add Test
</button>
</div>

{#if labTests.length === 0}
<div class="py-10 text-center text-slate-400">
<TestTube2 class="w-8 h-8 mx-auto mb-2 opacity-30" />
<p class="text-sm">No tests yet. Add the first test.</p>
</div>
{:else}
<!-- Desktop test table -->
<div class="hidden md:block rounded-xl overflow-hidden"
style="border: 1px solid rgba(0,0,0,0.07);">
<div class="grid grid-cols-[1fr_130px_100px_120px] gap-3 px-4 py-2"
style="background: linear-gradient(to bottom, #f8fafc, #f1f5f9); border-bottom: 1px solid rgba(0,0,0,0.06);">
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Test Name</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Category</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Code</span>
<span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Actions</span>
</div>
{#each labTests as test (test.id)}
<div
animate:flip={{ duration: 200 }}
class="grid grid-cols-[1fr_130px_100px_120px] gap-3 items-center px-4 py-3 border-b last:border-b-0 transition-all duration-200"
style="
background: {test.is_active ? 'white' : '#f8fafc'};
border-bottom-color: rgba(0,0,0,0.05);
{test.is_active ? '' : 'opacity: 0.65;'}
"
>
<div class="flex items-center gap-2 min-w-0">
<span class="w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-200"
style="background: {test.is_active ? '#22c55e' : '#94a3b8'};"></span>
<span class="font-semibold text-sm text-slate-900 truncate">{test.name}</span>
</div>
<span class="text-xs text-slate-500 truncate">{test.category}</span>
<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-medium"
style="background: rgba(99,102,241,0.08); color: #4338ca;">
{test.code}
</span>
<div class="flex items-center justify-end gap-1">
<button
type="button"
onclick={() => toggleTestActive(test)}
disabled={togglingTestId === test.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={test.is_active}
aria-label={`Toggle ${test.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${test.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${test.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingTestId === test.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
<button
onclick={() => openEditTestModal(test)}
class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 cursor-pointer transition-all"
>
<Pencil class="w-3.5 h-3.5" />
</button>
</div>
</div>
{/each}
</div>

<!-- Mobile test cards -->
<div class="md:hidden space-y-2">
{#each labTests as test (test.id)}
<div
animate:flip={{ duration: 200 }}
class="flex items-center justify-between p-3 rounded-xl transition-all duration-200"
style="
background: {test.is_active
? 'linear-gradient(to right, #ffffff, #f0fdf4)'
: 'linear-gradient(to right, #f8fafc, #f1f5f9)'};
border: 1px solid {test.is_active ? 'rgba(34,197,94,0.15)' : 'rgba(0,0,0,0.06)'};
{test.is_active ? '' : 'opacity: 0.7;'}
"
>
<div class="flex items-center gap-2.5 min-w-0">
<span class="w-2 h-2 rounded-full shrink-0"
style="background: {test.is_active ? '#22c55e' : '#94a3b8'};"></span>
<div class="min-w-0">
<p class="font-semibold text-sm text-slate-900 truncate">{test.name}</p>
<p class="text-xs text-slate-400">{test.category} · <span class="font-mono">{test.code}</span></p>
</div>
</div>
<div class="flex items-center gap-1 shrink-0 ml-2">
<button
type="button"
onclick={() => toggleTestActive(test)}
disabled={togglingTestId === test.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={test.is_active}
aria-label={`Toggle ${test.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${test.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${test.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingTestId === test.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
<button onclick={() => openEditTestModal(test)} class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 cursor-pointer transition-all">
<Pencil class="w-3.5 h-3.5" />
</button>
</div>
</div>
{/each}
</div>
{/if}
</div>

{:else}
<!-- Groups section -->
<div class="px-5 py-4">
<div class="flex items-center justify-between mb-4">
<div>
<p class="text-sm font-bold text-slate-800">Test Groups / Packages</p>
<p class="text-xs text-slate-500">{labGroups.filter(g => g.is_active).length} active / {labGroups.length} total</p>
</div>
<button
onclick={openGroupModal}
class="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white rounded-xl cursor-pointer transition-all hover:scale-105 active:scale-95"
style="background: linear-gradient(to bottom, #8b5cf6, #7c3aed); box-shadow: 0 2px 6px rgba(124,58,237,0.3);"
>
<Plus class="w-3.5 h-3.5" />Create Group
</button>
</div>

{#if labGroups.length === 0}
<div class="py-10 text-center text-slate-400">
<Layers class="w-8 h-8 mx-auto mb-2 opacity-30" />
<p class="text-sm">No groups yet. Create a test package.</p>
</div>
{:else}
<!-- Desktop group table -->
<div class="hidden md:block space-y-2">
{#each labGroups as group (group.id)}
<div
animate:flip={{ duration: 200 }}
class="rounded-xl overflow-hidden transition-all duration-200"
style="
border: 1px solid {group.is_active ? 'rgba(139,92,246,0.15)' : 'rgba(0,0,0,0.06)'};
{group.is_active ? '' : 'opacity: 0.65;'}
"
>
<div class="flex items-center justify-between px-4 py-3"
style="background: {group.is_active
? 'linear-gradient(to right, #faf5ff, #f5f3ff)'
: 'linear-gradient(to right, #f8fafc, #f1f5f9)'};">
<div class="flex items-center gap-2.5">
<span class="w-1.5 h-1.5 rounded-full"
style="background: {group.is_active ? '#8b5cf6' : '#94a3b8'};"></span>
<p class="font-semibold text-slate-900">{group.name}</p>
<span class="text-xs text-slate-400">{group.tests.length} test{group.tests.length !== 1 ? 's' : ''}</span>
</div>
<div class="flex items-center gap-1">
<button
type="button"
onclick={() => toggleGroupActive(group)}
disabled={togglingGroupId === group.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={group.is_active}
aria-label={`Toggle ${group.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${group.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${group.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingGroupId === group.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
<button onclick={() => openEditGroupModal(group)} class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 cursor-pointer transition-all">
<Pencil class="w-3.5 h-3.5" />
</button>
</div>
</div>
<div class="px-4 py-2.5 flex flex-wrap gap-1.5"
style="background: {group.is_active ? '#fdf4ff' : '#f8fafc'}; border-top: 1px solid {group.is_active ? 'rgba(139,92,246,0.1)' : 'rgba(0,0,0,0.05)'};">
{#each group.tests as test (test.id)}
<span class="px-2.5 py-1 text-xs font-medium rounded-lg"
style="background: {group.is_active ? 'linear-gradient(to bottom, #ede9fe, #ddd6fe)' : '#e2e8f0'}; color: {group.is_active ? '#5b21b6' : '#64748b'};">
{test.name}
</span>
{/each}
{#if group.tests.length === 0}
<span class="text-xs text-slate-400 italic">No tests in this group</span>
{/if}
</div>
</div>
{/each}
</div>

<!-- Mobile group cards -->
<div class="md:hidden space-y-3">
{#each labGroups as group (group.id)}
<div
animate:flip={{ duration: 200 }}
class="rounded-xl overflow-hidden transition-all duration-200"
style="
border: 1px solid {group.is_active ? 'rgba(139,92,246,0.15)' : 'rgba(0,0,0,0.06)'};
{group.is_active ? '' : 'opacity: 0.7;'}
"
>
<div class="flex items-center justify-between p-3"
style="background: {group.is_active ? 'linear-gradient(to right, #faf5ff, #f5f3ff)' : 'linear-gradient(to right, #f8fafc, #f1f5f9)'};">
<div class="flex items-center gap-2 min-w-0">
<span class="w-2 h-2 rounded-full shrink-0"
style="background: {group.is_active ? '#8b5cf6' : '#94a3b8'};"></span>
<div class="min-w-0">
<p class="font-semibold text-sm text-slate-900 truncate">{group.name}</p>
<p class="text-xs text-slate-400">{group.tests.length} test{group.tests.length !== 1 ? 's' : ''}</p>
</div>
</div>
<div class="flex items-center gap-1 shrink-0 ml-2">
<button
type="button"
onclick={() => toggleGroupActive(group)}
disabled={togglingGroupId === group.id}
class="inline-flex items-center disabled:cursor-not-allowed disabled:opacity-70"
role="switch"
aria-checked={group.is_active}
aria-label={`Toggle ${group.name} active status`}
>
<span class={`relative inline-flex h-7 w-12 items-center rounded-full border transition-all duration-200 ${group.is_active ? 'border-emerald-400 bg-emerald-500' : 'border-slate-300 bg-slate-300'}`}>
<span class={`absolute h-5 w-5 rounded-full bg-white shadow-sm transition-all duration-200 ${group.is_active ? 'left-6' : 'left-1'}`}>
{#if togglingGroupId === group.id}
<Loader2 class="m-auto h-3 w-3 animate-spin text-slate-400" />
{/if}
</span>
</span>
</button>
<button onclick={() => openEditGroupModal(group)} class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 cursor-pointer transition-all">
<Pencil class="w-3.5 h-3.5" />
</button>
</div>
</div>
<div class="px-3 pb-3 pt-2 flex flex-wrap gap-1.5"
style="background: {group.is_active ? '#fdf4ff' : '#f8fafc'}; border-top: 1px solid {group.is_active ? 'rgba(139,92,246,0.1)' : 'rgba(0,0,0,0.05)'};">
{#each group.tests as test (test.id)}
<span class="px-2 py-0.5 text-xs font-medium rounded-md"
style="background: {group.is_active ? '#ede9fe' : '#e2e8f0'}; color: {group.is_active ? '#5b21b6' : '#64748b'};">
{test.name}
</span>
{/each}
{#if group.tests.length === 0}
<span class="text-xs text-slate-400 italic">No tests</span>
{/if}
</div>
</div>
{/each}
</div>
{/if}
</div>
{/if}
</div>
</div>
</div>
{/if}

{/if}

<!-- ── Lab Modal ─────────────────────────────────────── -->
{#if labModal}
<AquaModal title={editingLab ? 'Edit Lab' : 'Add New Lab'} onclose={closeLabModal}>
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
<button onclick={closeLabModal} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingLab}>Cancel</button>
<button onclick={saveLab} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" disabled={savingLab}>{savingLab ? 'Saving...' : editingLab ? 'Update Lab' : 'Create Lab'}</button>
</div>
</AquaModal>
{/if}

<!-- ── Test Modal ────────────────────────────────────── -->
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

<!-- ── Group Modal ───────────────────────────────────── -->
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
<div class="max-h-52 overflow-y-auto rounded-xl p-2" style="background: linear-gradient(to bottom, #fafafa, #f5f5f5); border: 1px solid rgba(0,0,0,0.05);">
{#each allAvailableTests as test (test.id)}
<button type="button" onclick={() => toggleTestInGroup(test.id)}
class="w-full text-left px-3 py-2 rounded-lg mb-1 transition-all duration-150 flex items-center gap-2"
style="{groupData.test_ids.includes(test.id)
? 'background: linear-gradient(to right, #eff6ff, #dbeafe); border: 1px solid rgba(59,130,246,0.2);'
: 'background: transparent; border: 1px solid transparent;'}"
>
<span class="w-4 h-4 rounded shrink-0 flex items-center justify-center"
style="background: {groupData.test_ids.includes(test.id) ? '#3b82f6' : 'rgba(0,0,0,0.08)'}; transition: background 0.15s;">
{#if groupData.test_ids.includes(test.id)}
<svg class="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
{/if}
</span>
<div>
<p class="font-semibold text-sm text-slate-900">{test.name}</p>
<p class="text-xs text-slate-500">{test.category} · {test.code}</p>
</div>
</button>
{/each}
{#if allAvailableTests.length === 0}
<p class="text-center text-xs text-slate-400 py-4">No tests available. Add tests first.</p>
{/if}
</div>
{#if groupData.test_ids.length > 0}
<p class="mt-1.5 text-xs text-blue-600 font-medium">{groupData.test_ids.length} test{groupData.test_ids.length !== 1 ? 's' : ''} selected</p>
{/if}
</div>
</div>
<div class="flex gap-2 mt-4">
<button onclick={() => { groupModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={savingGroup}>Cancel</button>
<button onclick={saveGroup} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #8b5cf6, #7c3aed);" disabled={savingGroup}>{savingGroup ? (editingGroup ? 'Updating...' : 'Creating...') : (editingGroup ? 'Update Group' : 'Create Group')}</button>
</div>
</AquaModal>
{/if}

<!-- ── Confirm Delete ────────────────────────────────── -->
{#if confirmModal}
<AquaModal title="Confirm Delete" onclose={() => { confirmModal = false; }}>
<p class="text-sm text-slate-700 mb-4">{confirmMessage}</p>
<div class="flex gap-2">
<button onclick={() => { confirmModal = false; }} class="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);" disabled={actionLoading}>Cancel</button>
<button onclick={() => confirmAction?.()} class="flex-1 px-4 py-2.5 text-sm font-semibold text-white rounded-xl uppercase tracking-wide" style="background: linear-gradient(to bottom, #ef4444, #dc2626);" disabled={actionLoading}>{actionLoading ? 'Deleting...' : 'Delete'}</button>
</div>
</AquaModal>
{/if}
