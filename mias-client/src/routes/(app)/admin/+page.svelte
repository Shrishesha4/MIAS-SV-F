<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import {
		adminApi,
		type AdminDashboard,
		type AdminUser,
		type Department,
		type Programme
	} from '$lib/api/admin';
	import { debounce } from '$lib/utils/debounce';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import {
		Users,
		GraduationCap,
		Building,
		UserCheck,
		CheckCircle,
		TrendingUp,
		ChevronRight,
		Shield,
		Activity,
		BarChart3,
		FileText,
		BookOpen,
		Search,
		Plus,
		X,
		Ban,
		Loader2,
		Stethoscope
	} from 'lucide-svelte';

	const auth = get(authStore);
	type AdminTabId = 'overview' | 'users' | 'departments' | 'programmes';

	let loading = $state(true);
	let error = $state('');

	let dashboard: AdminDashboard | null = $state(null);
	let roleDistribution: Record<string, number> = $state({});
	let users: AdminUser[] = $state([]);
	let usersTotal = $state(0);
	let departments: Department[] = $state([]);
	let programmes: Programme[] = $state([]);

	let activeTab = $state<AdminTabId>('overview');
	const adminTabs = $derived.by(() => [
		{
			id: 'overview' as const,
			label: 'Overview',
			description: 'Live system metrics and portal-wide operational summary.',
			Icon: BarChart3,
			badge: `${dashboard?.total_users ?? 0}`
		},
		{
			id: 'users' as const,
			label: 'Users',
			description: 'Search, filter, block, and unblock portal accounts.',
			Icon: Users,
			badge: `${usersTotal || dashboard?.total_users || 0}`
		},
		{
			id: 'departments' as const,
			label: 'Departments',
			description: 'Maintain clinical departments and their availability.',
			Icon: Stethoscope,
			badge: `${departments.length || dashboard?.total_departments || 0}`
		},
		{
			id: 'programmes' as const,
			label: 'Programmes',
			description: 'Manage academic programmes and enrollment structure.',
			Icon: GraduationCap,
			badge: programmes.length > 0 ? `${programmes.length}` : 'Open'
		}
	]);
	const activeTabMeta = $derived(adminTabs.find((tab) => tab.id === activeTab) ?? adminTabs[0]);

	let userSearch = $state('');
	let userRoleFilter = $state('all');
	let usersPage = $state(1);
	let loadingUsers = $state(false);

	let showAddDept = $state(false);
	let newDeptName = $state('');
	let newDeptCode = $state('');
	let savingDept = $state(false);

	let showAddProg = $state(false);
	let newProgName = $state('');
	let newProgCode = $state('');
	let savingProg = $state(false);

	let showAddUser = $state(false);
	let newUserUsername = $state('');
	let newUserEmail = $state('');
	let newUserPassword = $state('');
	let newUserRole = $state('PATIENT');
	let newUserName = $state('');
	let newUserDob = $state('');
	let newUserGender = $state('MALE');
	let newUserBloodGroup = $state('');
	let newUserPhone = $state('');
	let newUserYear = $state(1);
	let newUserSemester = $state(1);
	let newUserProgram = $state('');
	let newUserDepartment = $state('');
	let newUserSpecialty = $state('');
	let savingUser = $state(false);
	let addUserError = $state('');

	async function loadUsers() {
		loadingUsers = true;
		try {
			const params: Record<string, any> = { page: usersPage, limit: 20 };
			if (userRoleFilter !== 'all') params.role = userRoleFilter;
			if (userSearch.trim()) params.search = userSearch.trim();
			const res = await adminApi.getUsers(params);
			users = res.items;
			usersTotal = res.total;
		} catch {
			/* ignore */
		} finally {
			loadingUsers = false;
		}
	}

	async function toggleUserBlock(user: AdminUser) {
		try {
			if (user.is_active) await adminApi.blockUser(user.id);
			else await adminApi.unblockUser(user.id);
			await loadUsers();
		} catch {
			/* ignore */
		}
	}

	async function loadDepartments() {
		departments = await adminApi.getDepartments();
	}

	async function loadProgrammes() {
		programmes = await adminApi.getProgrammes();
	}

	async function handleAddDept() {
		if (!newDeptName.trim() || !newDeptCode.trim()) return;
		savingDept = true;
		try {
			await adminApi.createDepartment({ name: newDeptName, code: newDeptCode });
			await loadDepartments();
			showAddDept = false;
			newDeptName = '';
			newDeptCode = '';
		} catch {
			/* ignore */
		} finally {
			savingDept = false;
		}
	}

	async function handleAddProg() {
		if (!newProgName.trim() || !newProgCode.trim()) return;
		savingProg = true;
		try {
			await adminApi.createProgramme({ name: newProgName, code: newProgCode });
			await loadProgrammes();
			showAddProg = false;
			newProgName = '';
			newProgCode = '';
		} catch {
			/* ignore */
		} finally {
			savingProg = false;
		}
	}

	async function handleAddUser() {
		if (!newUserUsername.trim() || !newUserEmail.trim() || !newUserPassword.trim()) return;
		savingUser = true;
		addUserError = '';
		try {
			await adminApi.createUser({
				username: newUserUsername.trim(),
				email: newUserEmail.trim(),
				password: newUserPassword,
				role: newUserRole,
				name: newUserName.trim() || undefined,
				date_of_birth: newUserDob || undefined,
				gender: newUserGender || undefined,
				blood_group: newUserBloodGroup.trim() || undefined,
				phone: newUserPhone.trim() || undefined,
				year: newUserRole === 'STUDENT' ? newUserYear : undefined,
				semester: newUserRole === 'STUDENT' ? newUserSemester : undefined,
				program: newUserRole === 'STUDENT' ? newUserProgram.trim() || undefined : undefined,
				department: newUserRole === 'FACULTY' ? newUserDepartment.trim() || undefined : undefined,
				specialty: newUserRole === 'FACULTY' ? newUserSpecialty.trim() || undefined : undefined,
			});
			await loadUsers();
			showAddUser = false;
			newUserUsername = ''; newUserEmail = ''; newUserPassword = ''; newUserName = '';
			newUserDob = ''; newUserBloodGroup = ''; newUserPhone = '';
			newUserProgram = ''; newUserDepartment = ''; newUserSpecialty = '';
		} catch (e: any) {
			addUserError = e.response?.data?.detail || 'Failed to create user';
		} finally {
			savingUser = false;
		}
	}

	async function toggleDeptActive(dept: Department) {
		await adminApi.updateDepartment(dept.id, { is_active: !dept.is_active });
		await loadDepartments();
	}

	async function toggleProgActive(prog: Programme) {
		await adminApi.updateProgramme(prog.id, { is_active: !prog.is_active });
		await loadProgrammes();
	}

	$effect(() => {
		if (loading) return;
		if (activeTab === 'users') loadUsers();
		else if (activeTab === 'departments') loadDepartments();
		else if (activeTab === 'programmes') loadProgrammes();
	});

	const debouncedLoadUsers = debounce(() => loadUsers(), 300);

	$effect(() => {
		if (activeTab !== 'users') return;
		userRoleFilter;
		usersPage;
		loadUsers();
	});

	$effect(() => {
		if (activeTab !== 'users') return;
		userSearch;
		debouncedLoadUsers();
	});

	onMount(async () => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}

		try {
			const [d, rd] = await Promise.all([adminApi.getDashboard(), adminApi.getRoleDistribution()]);
			dashboard = d;
			roleDistribution = rd;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load dashboard';
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-3 py-4 md:px-6 md:py-6">
	<div class="admin-shell">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<div class="text-center py-8">
			<p class="text-red-500 text-sm">{error}</p>
		</div>
	{:else if dashboard}
		<div class="admin-split flex flex-col gap-4 md:flex-row" style="min-height: calc(100vh - 7rem);">
			<div class="admin-pane w-full md:w-80 lg:w-96 shrink-0 rounded-xl overflow-hidden flex flex-col"
				style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
				<div class="p-4 border-b border-gray-100">
					<div class="flex items-center gap-3">
						<div class="w-12 h-12 rounded-full flex items-center justify-center shrink-0"
							style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
								box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
								border: 1px solid rgba(0,0,0,0.3);">
							<Shield class="w-6 h-6 text-white" />
						</div>
						<div class="min-w-0">
							<h2 class="text-lg font-semibold text-gray-900 truncate">System Administration</h2>
							<p class="text-xs text-gray-500">Root access · Saveetha Medical College</p>
						</div>
					</div>
				</div>

				<div class="grid grid-cols-3 gap-2 p-3 border-b border-gray-100 bg-slate-50/60">
					<div class="rounded-lg px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-lg font-bold text-blue-700">{dashboard.total_users}</p>
						<p class="text-[10px] uppercase tracking-wide text-gray-500">Users</p>
					</div>
					<div class="rounded-lg px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-lg font-bold text-orange-600">{dashboard.pending_approvals}</p>
						<p class="text-[10px] uppercase tracking-wide text-gray-500">Pending</p>
					</div>
					<div class="rounded-lg px-3 py-2 text-center" style="background: white; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-lg font-bold text-red-600">{dashboard.blocked_users}</p>
						<p class="text-[10px] uppercase tracking-wide text-gray-500">Blocked</p>
					</div>
				</div>

				<div class="flex-1 overflow-y-auto p-2">
					{#each adminTabs as tab (tab.id)}
						{@const isActive = activeTab === tab.id}
						{@const TabIcon = tab.Icon}
						<button
							class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors cursor-pointer rounded-xl border mb-2"
							style="background: {isActive ? 'linear-gradient(to right, rgba(59,130,246,0.10), rgba(37,99,235,0.04))' : 'white'};
								border-color: {isActive ? 'rgba(59,130,246,0.25)' : 'rgba(0,0,0,0.06)'};
								box-shadow: {isActive ? '0 4px 16px rgba(59,130,246,0.12)' : '0 1px 2px rgba(0,0,0,0.04)'};"
							onclick={() => activeTab = tab.id}
						>
							<div class="w-11 h-11 rounded-full flex items-center justify-center shrink-0"
								style="background: {isActive ? 'linear-gradient(to bottom, #4d90fe, #0066cc)' : 'linear-gradient(to bottom, #eef4ff, #e2e8f0)'};
									border: 1px solid {isActive ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.08)'};">
								<TabIcon class="w-5 h-5 {isActive ? 'text-white' : 'text-slate-500'}" />
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold {isActive ? 'text-blue-900' : 'text-gray-800'}">{tab.label}</p>
								<p class="text-xs {isActive ? 'text-blue-700/75' : 'text-gray-500'}">{tab.description}</p>
							</div>
							<div class="flex items-center gap-2 shrink-0">
								<span class="px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide"
									style="background: {isActive ? 'rgba(37,99,235,0.12)' : 'rgba(148,163,184,0.12)'};
										color: {isActive ? '#1d4ed8' : '#64748b'};">
									{tab.badge}
								</span>
								<ChevronRight class="w-4 h-4 {isActive ? 'text-blue-500' : 'text-gray-300'}" />
							</div>
						</button>
					{/each}
				</div>
			</div>

			<div class="admin-pane flex-1 rounded-xl overflow-hidden flex flex-col"
				style="background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);">
				{#if activeTabMeta}
					{@const ActiveIcon = activeTabMeta.Icon}
					<div class="px-4 py-4 md:px-5 md:py-5 border-b border-gray-100 bg-slate-50/40 flex flex-wrap items-start justify-between gap-3">
						<div class="flex items-center gap-3 min-w-0">
							<div class="w-12 h-12 rounded-full flex items-center justify-center shrink-0"
								style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
									box-shadow: 0 1px 3px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.35);
									border: 1px solid rgba(0,0,0,0.18);">
								<ActiveIcon class="w-5 h-5 text-white" />
							</div>
							<div class="min-w-0">
								<h3 class="text-lg font-semibold text-gray-900">{activeTabMeta.label}</h3>
								<p class="text-sm text-gray-500">{activeTabMeta.description}</p>
							</div>
						</div>

						<div class="flex items-center gap-2">
							{#if activeTab === 'users'}
								<div class="flex items-center px-3 py-2 rounded-lg"
									style="border: 1px solid rgba(0,0,0,0.12); background: white; box-shadow: inset 0 1px 2px rgba(0,0,0,0.04);">
									<Search class="w-3.5 h-3.5 text-gray-400 mr-2 shrink-0" />
									<input type="text" placeholder="Search users…" class="w-36 outline-none text-xs text-gray-600 bg-transparent" bind:value={userSearch} />
									{#if userSearch}
										<button class="cursor-pointer ml-1" onclick={() => userSearch = ''}>
											<X class="w-3 h-3 text-gray-400" />
										</button>
									{/if}
								</div>
								<button
									class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white cursor-pointer shrink-0"
									style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
									onclick={() => { showAddUser = true; addUserError = ''; }}
								>
									<Plus class="w-4 h-4" />
									Add User
								</button>
							{:else if activeTab === 'departments'}
								<button
									class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white cursor-pointer"
									style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
									onclick={() => showAddDept = true}
								>
									<Plus class="w-4 h-4" />
									Add Department
								</button>
							{:else if activeTab === 'programmes'}
								<button
									class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white cursor-pointer"
									style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
									onclick={() => showAddProg = true}
								>
									<Plus class="w-4 h-4" />
									Add Programme
								</button>
							{:else}
								<div class="px-3 py-2 rounded-lg text-xs font-semibold uppercase tracking-wide text-blue-700"
									style="background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.12);">
									{activeTabMeta.badge} items
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<div class="flex-1 overflow-y-auto p-4 md:p-5 space-y-4">
					{#if activeTab === 'overview'}
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
							{#each [
								{ val: dashboard.total_users, label: 'Total Users', grad: '#3b82f6, #1d4ed8', Icon: Users },
								{ val: dashboard.total_patients, label: 'Patients', grad: '#10b981, #059669', Icon: UserCheck },
								{ val: dashboard.total_students, label: 'Students', grad: '#f59e0b, #d97706', Icon: GraduationCap },
								{ val: dashboard.total_faculty, label: 'Faculty', grad: '#8b5cf6, #6d28d9', Icon: Activity }
							] as stat (stat.label)}
								<div class="overflow-hidden"
									style="background-color: white; border-radius: 10px;
										box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
										border: 1px solid rgba(0,0,0,0.1);
										background-image: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(245,245,245,0.8));">
									<div class="flex items-center gap-3 p-3">
										<div class="w-10 h-10 rounded-lg flex items-center justify-center"
											style="background: linear-gradient(135deg, {stat.grad});">
											<stat.Icon class="w-5 h-5 text-white" />
										</div>
										<div>
											<p class="text-2xl font-bold text-blue-900">{stat.val}</p>
											<p class="text-xs text-gray-500">{stat.label}</p>
										</div>
									</div>
								</div>
							{/each}
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
							{#each [
								{ val: dashboard.active_admissions, label: 'Active Admissions', color: 'text-green-700' },
								{ val: dashboard.pending_approvals, label: 'Pending Approvals', color: 'text-orange-600' },
								{ val: dashboard.blocked_users, label: 'Blocked Users', color: 'text-red-600' }
							] as stat (stat.label)}
								<div class="text-center p-3"
									style="background-color: white; border-radius: 10px;
										box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
										border: 1px solid rgba(0,0,0,0.1);
										background-image: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(245,245,245,0.8));">
									<p class="text-xl font-bold {stat.color}">{stat.val}</p>
									<p class="text-[10px] text-gray-500 mt-1">{stat.label}</p>
								</div>
							{/each}
						</div>

						<AquaCard>
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-3">
									<TrendingUp class="w-5 h-5 text-green-600" />
									<div>
										<p class="text-sm font-semibold text-blue-900">New Registrations (7 days)</p>
										<p class="text-xs text-gray-500">{dashboard.recent_registrations} new users this week</p>
									</div>
								</div>
								<span class="text-2xl font-bold text-green-600">+{dashboard.recent_registrations}</span>
							</div>
						</AquaCard>

						<AquaCard>
							{#snippet header()}
								<FileText class="w-4 h-4 text-blue-700 mr-2" />
								<span class="text-sm font-semibold text-blue-900">Role Distribution</span>
							{/snippet}
							<div class="space-y-2">
								{#each Object.entries(roleDistribution) as [role, count]}
									{@const total = Object.values(roleDistribution).reduce((a, b) => a + b, 0)}
									{@const pct = total > 0 ? Math.round((count / total) * 100) : 0}
									{@const colors: Record<string, string> = { PATIENT: '#10b981', STUDENT: '#f59e0b', FACULTY: '#8b5cf6', ADMIN: '#ef4444', RECEPTION: '#3b82f6' }}
									<div>
										<div class="flex items-center justify-between text-xs mb-1">
											<span class="font-medium text-gray-700">{role}</span>
											<span class="text-gray-500">{count} ({pct}%)</span>
										</div>
										<div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
											<div class="h-full rounded-full transition-all" style="width: {pct}%; background-color: {colors[role] || '#6b7280'};"></div>
										</div>
									</div>
								{/each}
							</div>
						</AquaCard>

						{#if Object.keys(dashboard.patient_categories).length > 0}
							<AquaCard>
								{#snippet header()}
									<Users class="w-4 h-4 text-blue-700 mr-2" />
									<span class="text-sm font-semibold text-blue-900">Patient Categories</span>
								{/snippet}
								<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
									{#each Object.entries(dashboard.patient_categories) as [cat, count]}
										{@const catColors: Record<string, string> = { GENERAL: '#6b7280', ELITE: '#f59e0b', VIP: '#8b5cf6', STAFF: '#3b82f6' }}
										<div class="flex items-center gap-2 py-1">
											<div class="w-3 h-3 rounded-full" style="background-color: {catColors[cat] || '#6b7280'};"></div>
											<span class="text-xs text-gray-600">{cat}</span>
											<span class="text-xs font-bold text-blue-900 ml-auto">{count}</span>
										</div>
									{/each}
								</div>
							</AquaCard>
						{/if}

					{:else if activeTab === 'users'}
						<div class="flex items-center justify-between mb-1">
							<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
								User Management
							</h3>
							<span class="text-[10px] text-gray-400">{usersTotal} total</span>
						</div>

						{#if showAddUser}
							<div class="p-4" style="background-color: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); border: 1px solid rgba(0,0,0,0.1);">
								<h4 class="text-sm font-bold text-gray-900 mb-3">New User</h4>
								{#if addUserError}
									<p class="text-xs text-red-500 mb-2">{addUserError}</p>
								{/if}
								<div class="space-y-2">
									<div class="grid grid-cols-2 gap-2">
										<input type="text" placeholder="Username *" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserUsername} />
										<input type="email" placeholder="Email *" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserEmail} />
									</div>
									<input type="password" placeholder="Password *" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserPassword} />
									<select class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserRole}>
										{#each ['PATIENT', 'STUDENT', 'FACULTY', 'ADMIN'] as r}
											<option value={r}>{r}</option>
										{/each}
									</select>
									<input type="text" placeholder="Full Name" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserName} />
									{#if newUserRole === 'PATIENT'}
										<div class="grid grid-cols-2 gap-2">
											<input type="date" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserDob} />
											<select class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserGender}>
												<option value="MALE">Male</option>
												<option value="FEMALE">Female</option>
												<option value="OTHER">Other</option>
											</select>
										</div>
										<div class="grid grid-cols-2 gap-2">
											<input type="text" placeholder="Blood Group (e.g. A+)" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserBloodGroup} />
											<input type="text" placeholder="Phone" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserPhone} />
										</div>
									{:else if newUserRole === 'STUDENT'}
										<div class="grid grid-cols-2 gap-2">
											<input type="number" placeholder="Year" min="1" max="10" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserYear} />
											<input type="number" placeholder="Semester" min="1" max="20" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserSemester} />
										</div>
										<input type="text" placeholder="Program (e.g. MBBS)" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserProgram} />
									{:else if newUserRole === 'FACULTY'}
										<div class="grid grid-cols-2 gap-2">
											<input type="text" placeholder="Department" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserDepartment} />
											<input type="text" placeholder="Specialty" class="px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserSpecialty} />
										</div>
										<input type="text" placeholder="Phone" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newUserPhone} />
									{/if}
									<div class="flex gap-2 pt-1">
										<button
											class="flex-1 py-2 rounded-lg text-xs font-medium text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
											onclick={handleAddUser}
											disabled={savingUser}
										>
											{savingUser ? 'Creating…' : 'Create User'}
										</button>
										<button class="px-4 py-2 text-xs font-bold text-gray-500 cursor-pointer" onclick={() => { showAddUser = false; addUserError = ''; }}>Cancel</button>
									</div>
								</div>
							</div>
						{/if}

						<div class="flex gap-1.5 overflow-x-auto pb-1">
							{#each ['all', 'PATIENT', 'STUDENT', 'FACULTY', 'ADMIN', 'RECEPTION'] as role}
								<button
									class="shrink-0 px-3 py-1.5 rounded-full text-[10px] font-semibold cursor-pointer transition-all"
									style="background: {userRoleFilter === role ? 'linear-gradient(to bottom, #4d90fe, #0066cc)' : 'linear-gradient(to bottom, #ffffff, #e6e9f0)'};
										color: {userRoleFilter === role ? 'white' : '#475569'};
										border: 1px solid {userRoleFilter === role ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.15)'};
										box-shadow: {userRoleFilter === role ? '0 1px 3px rgba(0,102,204,0.3)' : '0 1px 2px rgba(0,0,0,0.1)'};"
									onclick={() => {
										userRoleFilter = role;
										usersPage = 1;
									}}
								>
									{role === 'all' ? 'All' : role}
								</button>
							{/each}
						</div>

						{#if loadingUsers}
							<div class="flex items-center justify-center py-8">
								<Loader2 class="w-5 h-5 text-blue-500 animate-spin" />
							</div>
						{:else}
							<div class="space-y-2">
								{#each users as user}
									<div class="p-3 flex items-center justify-between"
										style="background-color: white; border-radius: 8px;
											box-shadow: 0 1px 2px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
											border: 1px solid rgba(0,0,0,0.07);
											opacity: {user.is_active ? 1 : 0.6};">
										<div class="flex items-center min-w-0">
											<div class="w-9 h-9 rounded-full flex items-center justify-center mr-3 shrink-0"
												style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
													box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);">
												<span class="text-white text-xs font-bold">{user.name ? user.name[0].toUpperCase() : 'U'}</span>
											</div>
											<div class="min-w-0">
												<p class="text-xs font-semibold text-gray-900 truncate">{user.name || user.username}</p>
												<p class="text-[10px] text-gray-400 truncate">
													{user.username} · <span class="font-bold uppercase text-blue-600">{user.role}</span>
													{#if !user.is_active}
														<span class="text-red-500 font-bold"> · BLOCKED</span>
													{/if}
												</p>
											</div>
										</div>
										<button
											class="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer shrink-0"
											style="background: {user.is_active ? 'linear-gradient(to bottom, #ef4444, #dc2626)' : 'linear-gradient(to bottom,#10b981, #059669)'};
												box-shadow: 0 1px 2px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);
												border: 1px solid rgba(0,0,0,0.15);"
											title={user.is_active ? 'Block user' : 'Unblock user'}
											onclick={() => toggleUserBlock(user)}
										>
											{#if user.is_active}
												<Ban class="w-3.5 h-3.5 text-white" />
											{:else}
												<CheckCircle class="w-3.5 h-3.5 text-white" />
											{/if}
										</button>
									</div>
								{/each}
								{#if users.length === 0}
									<div class="text-center py-8">
										<Users class="w-7 h-7 mx-auto text-gray-300 mb-2" />
										<p class="text-sm text-gray-400">No users found</p>
									</div>
								{/if}
							</div>
						{/if}

					{:else if activeTab === 'departments'}
						<div class="flex items-center justify-between mb-1">
							<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
								Medical Departments
							</h3>
							<span class="text-[10px] text-gray-400">{departments.length} loaded</span>
						</div>

						{#if showAddDept}
							<div class="p-4"
								style="background-color: white; border-radius: 10px;
									box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
									border: 1px solid rgba(0,0,0,0.1);">
								<h4 class="text-sm font-bold text-gray-900 mb-3">New Department</h4>
								<div class="space-y-3">
									<input type="text" placeholder="Department Name" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newDeptName} />
									<input type="text" placeholder="Department Code (e.g. GEN-MED)" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newDeptCode} />
									<div class="flex gap-2">
										<button
											class="flex-1 py-2 rounded-lg text-xs font-medium text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
											onclick={handleAddDept}
											disabled={savingDept}
										>
											{savingDept ? 'Saving...' : 'Save'}
										</button>
										<button class="px-4 py-2 text-xs font-bold text-gray-500 cursor-pointer" onclick={() => showAddDept = false}>Cancel</button>
									</div>
								</div>
							</div>
						{/if}

						<div class="space-y-2">
							{#each departments as dept}
								<div class="p-3 flex items-center justify-between transition-opacity"
									style="background-color: white; border-radius: 10px;
										box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
										border: 1px solid rgba(0,0,0,0.1);
										opacity: {dept.is_active ? 1 : 0.6};">
									<div class="flex items-center">
										<div class="w-10 h-10 rounded-full flex items-center justify-center mr-3"
											style="background: linear-gradient(to bottom, {dept.is_active ? '#4d90fe, #0066cc' : '#9ca3af, #4b5563'});
												box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
												border: 1px solid rgba(0,0,0,0.3);">
											<Stethoscope class="w-4 h-4 text-white" />
										</div>
										<div>
											<p class="text-sm font-medium text-gray-900">{dept.name}</p>
											<p class="text-[10px] font-bold uppercase tracking-wider {dept.is_active ? 'text-blue-600' : 'text-gray-500'}">
												{dept.code} · {dept.faculty_count} faculty · {dept.is_active ? 'Active' : 'Inactive'}
											</p>
										</div>
									</div>
									<button
										class="w-8 h-8 rounded-full border flex items-center justify-center cursor-pointer transition-all"
										style="{dept.is_active
											? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); border-color: rgba(0,0,0,0.3); box-shadow: 0 2px 4px rgba(0,102,204,0.3), inset 0 1px 0 rgba(255,255,255,0.4);'
											: 'background: white; border-color: rgba(0,0,0,0.1); box-shadow: inset 0 1px 2px rgba(0,0,0,0.08);'}"
										title={dept.is_active ? 'Deactivate' : 'Activate'}
										onclick={() => toggleDeptActive(dept)}
									>
										<CheckCircle class="w-5 h-5 {dept.is_active ? 'text-white' : 'text-gray-200'}" />
									</button>
								</div>
							{/each}
							{#if departments.length === 0}
								<div class="text-center py-8">
									<Building class="w-7 h-7 mx-auto text-gray-300 mb-2" />
									<p class="text-sm text-gray-400">No departments yet</p>
								</div>
							{/if}
						</div>

					{:else if activeTab === 'programmes'}
						<div class="flex items-center justify-between mb-1">
							<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
								Academic Programs
							</h3>
							<span class="text-[10px] text-gray-400">{programmes.length} loaded</span>
						</div>

						{#if showAddProg}
							<div class="p-4"
								style="background-color: white; border-radius: 10px;
									box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
									border: 1px solid rgba(0,0,0,0.1);">
								<h4 class="text-sm font-bold text-gray-900 mb-3">New Program</h4>
								<div class="space-y-3">
									<input type="text" placeholder="Program Name" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newProgName} />
									<input type="text" placeholder="Code (e.g. MBBS)" class="w-full px-3 py-2 bg-gray-50 border border-gray-100 rounded-lg text-sm outline-none" style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);" bind:value={newProgCode} />
									<div class="flex gap-2">
										<button
											class="flex-1 py-2 rounded-lg text-xs font-medium text-white cursor-pointer"
											style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
											onclick={handleAddProg}
											disabled={savingProg}
										>
											{savingProg ? 'Saving...' : 'Save'}
										</button>
										<button class="px-4 py-2 text-xs font-bold text-gray-500 cursor-pointer" onclick={() => showAddProg = false}>Cancel</button>
									</div>
								</div>
							</div>
						{/if}

						<div class="space-y-2">
							{#each programmes as prog}
								<div class="p-3 flex items-center justify-between transition-opacity"
									style="background-color: white; border-radius: 10px;
										box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
										border: 1px solid rgba(0,0,0,0.1);
										opacity: {prog.is_active ? 1 : 0.6};">
									<div class="flex items-center">
										<div class="w-10 h-10 rounded-full flex items-center justify-center mr-3"
											style="background: linear-gradient(to bottom, {prog.is_active ? '#4d90fe, #0066cc' : '#9ca3af, #4b5563'});
												box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
												border: 1px solid rgba(0,0,0,0.3);">
											<GraduationCap class="w-4 h-4 text-white" />
										</div>
										<div>
											<p class="text-sm font-medium text-gray-900">{prog.name}</p>
											<p class="text-[10px] font-bold uppercase tracking-wider {prog.is_active ? 'text-blue-600' : 'text-gray-500'}">
												{prog.code} · {prog.student_count} students · {prog.is_active ? 'Active' : 'Inactive'}
											</p>
										</div>
									</div>
									<button
										class="w-8 h-8 rounded-full border flex items-center justify-center cursor-pointer transition-all"
										style="{prog.is_active
											? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); border-color: rgba(0,0,0,0.3); box-shadow: 0 2px 4px rgba(0,102,204,0.3), inset 0 1px 0 rgba(255,255,255,0.4);'
											: 'background: white; border-color: rgba(0,0,0,0.1); box-shadow: inset 0 1px 2px rgba(0,0,0,0.08);'}"
										title={prog.is_active ? 'Deactivate' : 'Activate'}
										onclick={() => toggleProgActive(prog)}
									>
										<CheckCircle class="w-5 h-5 {prog.is_active ? 'text-white' : 'text-gray-200'}" />
									</button>
								</div>
							{/each}
							{#if programmes.length === 0}
								<div class="text-center py-8">
									<BookOpen class="w-7 h-7 mx-auto text-gray-300 mb-2" />
									<p class="text-sm text-gray-400">No programs yet</p>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
</div>

<style>
	@media (min-width: 768px) {
		.admin-shell {
			height: calc(100vh - 6.5rem);
			overflow: hidden;
		}

		.admin-split {
			height: 100%;
		}

		.admin-pane {
			height: 100%;
		}
	}
</style>