<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type AdminUser } from '$lib/api/admin';
	import AdminMobileScaffold from '$lib/components/layout/AdminMobileScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Search, Users, Shield, ShieldOff, Trash2,
		ChevronRight, Plus, User
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let users: AdminUser[] = $state([]);
	let total = $state(0);
	let currentPage = $state(1);
	let searchQuery = $state('');
	let roleFilter = $state('');
	let statusFilter = $state('');
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	// Create user modal
	let createUserModal = $state(false);
	let newUserRole = $state('NURSE');
	let newUserData = $state({
		username: '',
		email: '',
		password: '',
		name: '',
		phone: '',
		department: ''
	});
	let creatingUser = $state(false);

	// Read initial filter from URL
	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		const params = new URLSearchParams(window.location.search);
		roleFilter = params.get('role') || '';
		loadUsers();
	});

	async function loadUsers() {
		loading = true;
		error = '';
		try {
			const params: any = { page: currentPage, limit: 20 };
			if (roleFilter) params.role = roleFilter;
			if (searchQuery) params.search = searchQuery;
			if (statusFilter) params.status = statusFilter;
			const res = await adminApi.getUsers(params);
			users = res.items;
			total = res.total;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load users';
		} finally {
			loading = false;
		}
	}

	function handleSearch() {
		currentPage = 1;
		loadUsers();
	}

	function setRoleFilter(r: string) {
		roleFilter = r;
		currentPage = 1;
		loadUsers();
	}

	function setStatusFilter(s: string) {
		statusFilter = s;
		currentPage = 1;
		loadUsers();
	}

	async function toggleBlock(u: AdminUser) {
		confirmMessage = u.is_active
			? `Block user "${u.name}" (${u.username})? They won't be able to log in.`
			: `Unblock user "${u.name}" (${u.username})?`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				if (u.is_active) {
					await adminApi.blockUser(u.id);
				} else {
					await adminApi.unblockUser(u.id);
				}
				await loadUsers();
			} catch (e: any) {
				error = e.response?.data?.detail || 'Action failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function deleteUser(u: AdminUser) {
		confirmMessage = `Permanently delete user "${u.name}" (${u.username})? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await adminApi.deleteUser(u.id);
				await loadUsers();
			} catch (e: any) {
				error = e.response?.data?.detail || 'Delete failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function createUser() {
		if (!newUserData.username || !newUserData.email || !newUserData.password || !newUserData.name) {
			toastStore.addToast('Please fill in all required fields', 'error');
			return;
		}
		
		creatingUser = true;
		try {
			await adminApi.createUser({
				username: newUserData.username,
				email: newUserData.email,
				password: newUserData.password,
				role: newUserRole,
				name: newUserData.name,
				phone: newUserData.phone || undefined,
				department: newUserData.department || undefined,
			});
			toastStore.addToast('User created successfully', 'success');
			createUserModal = false;
			newUserData = { username: '', email: '', password: '', name: '', phone: '', department: '' };
			newUserRole = 'NURSE';
			await loadUsers();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to create user', 'error');
		} finally {
			creatingUser = false;
		}
	}

	const totalPages = $derived(Math.ceil(total / 20));

	const roleTabs = [
		{ id: '', label: 'All' },
		{ id: 'PATIENT', label: 'Patients' },
		{ id: 'STUDENT', label: 'Students' },
		{ id: 'FACULTY', label: 'Faculty' },
		{ id: 'NURSE', label: 'Nurses' },
		{ id: 'RECEPTION', label: 'Reception' },
		{ id: 'ADMIN', label: 'Admins' },
	];

	function roleColor(role: string) {
		const map: Record<string, string> = {
			PATIENT: '#10b981',
			STUDENT: '#f59e0b',
			FACULTY: '#8b5cf6',
			ADMIN: '#ef4444',
			RECEPTION: '#3b82f6',
			NURSE: '#14b8a6',
		};
		return map[role] || '#6b7280';
	}
</script>

<AdminMobileScaffold
	title="System Administration"
	titleIcon={Users}
	navItems={adminPageNavItems}
	activeNav="users"
	backHref="/admin"
>
	<div class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">User Management</h2>
				<p class="mt-0.5 text-[11px] text-slate-500">{total} total users</p>
			</div>
			<button
				onclick={() => createUserModal = true}
				class="px-3 py-1.5 rounded-xl text-xs font-semibold text-white cursor-pointer shadow-md"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
			>
				Add New
			</button>
		</div>

		<div class="relative">
			<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
			<input
				type="text"
				placeholder="Search by username or email..."
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Enter' && handleSearch()}
				class="w-full pl-9 pr-3 py-2 rounded-2xl text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
				style="background: white; box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
			/>
		</div>

		<div class="flex gap-1.5 overflow-x-auto pb-1">
			{#each roleTabs as tab}
				<button
					class="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap cursor-pointer transition-all"
					style={roleFilter === tab.id
						? `background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);`
						: `background: white; color: #4b5563; border: 1px solid #e5e7eb;`}
					onclick={() => setRoleFilter(tab.id)}
				>
					{tab.label}
				</button>
			{/each}
		</div>

		<div class="flex gap-1.5 overflow-x-auto pb-1">
			{#each [{ id: '', label: 'All Status' }, { id: 'active', label: 'Active' }, { id: 'blocked', label: 'Blocked' }] as sf}
				<button
					class="shrink-0 px-2.5 py-1 rounded-full text-[11px] cursor-pointer"
					style={statusFilter === sf.id
						? 'background: #1e3a5f; color: white;'
						: 'background: #f3f4f6; color: #6b7280;'}
					onclick={() => setStatusFilter(sf.id)}
				>
					{sf.label}
				</button>
			{/each}
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
			</div>
		{:else if error}
			<div class="p-4 rounded-xl bg-white shadow-md">
				<p class="text-red-500 text-center py-4">{error}</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each users as u}
					<div class="p-3 rounded-xl bg-white shadow-md flex items-center gap-2.5">
						<div class="w-11 h-11 flex items-center justify-center rounded-full shrink-0" style="background: linear-gradient(to bottom, {roleColor(u.role)}, {roleColor(u.role)}dd);">
							<User class="w-5 h-5 text-white" />
						</div>

						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-1.5">
								<p class="text-sm font-bold text-gray-900 truncate">{u.name}</p>
								{#if !u.is_active}
									<span class="text-[9px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">Blocked</span>
								{/if}
							</div>
							<p class="text-xs text-red-600 font-semibold truncate uppercase">{u.role} • {u.username}</p>
						</div>

						<div class="flex flex-col gap-0.5 shrink-0">
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-100"
								title={u.is_active ? 'Block' : 'Unblock'}
								onclick={() => toggleBlock(u)}
							>
								{#if u.is_active}
									<ShieldOff class="w-3.5 h-3.5 text-orange-500" />
								{:else}
									<Shield class="w-3.5 h-3.5 text-green-500" />
								{/if}
							</button>
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-red-50"
								title="Delete"
								onclick={() => deleteUser(u)}
							>
								<Trash2 class="w-3.5 h-3.5 text-red-400" />
							</button>
						</div>
					</div>
				{/each}

				{#if users.length === 0}
					<div class="text-center py-12 text-gray-400 text-sm">No users found</div>
				{/if}
			</div>

			{#if totalPages > 1}
				<div class="flex items-center justify-center gap-4 py-2">
					<button
						class="p-2 rounded-lg cursor-pointer disabled:opacity-30"
						disabled={currentPage <= 1}
						onclick={() => { currentPage--; loadUsers(); }}
					>
						<ChevronRight class="w-5 h-5 text-blue-600 rotate-180" />
					</button>
					<span class="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
					<button
						class="p-2 rounded-lg cursor-pointer disabled:opacity-30"
						disabled={currentPage >= totalPages}
						onclick={() => { currentPage++; loadUsers(); }}
					>
						<ChevronRight class="w-5 h-5 text-blue-600" />
					</button>
				</div>
			{/if}
		{/if}
	</div>
</AdminMobileScaffold>

<!-- Create User Modal -->
{#if createUserModal}
	<AquaModal title="Create New User" onclose={() => createUserModal = false}>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="p-4 space-y-4">
			<!-- Role Selection -->
			<div>
				<label for="userRole" class="block text-xs font-semibold text-gray-700 mb-1">Role *</label>
				<select
					id="userRole"
					bind:value={newUserRole}
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				>
					<option value="NURSE">Nurse</option>
					<option value="RECEPTION">Reception</option>
					<option value="STUDENT">Student</option>
					<option value="FACULTY">Faculty</option>
					<option value="PATIENT">Patient</option>
					<option value="ADMIN">Admin</option>
				</select>
			</div>

			<!-- Name -->
			<div>
				<label class="block text-xs font-semibold text-gray-700 mb-1">Full Name *</label>
				<input
					type="text"
					bind:value={newUserData.name}
					placeholder="Enter full name"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<!-- Username -->
			<div>
				<label class="block text-xs font-semibold text-gray-700 mb-1">Username *</label>
				<input
					type="text"
					bind:value={newUserData.username}
					placeholder="Enter username"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<!-- Email -->
			<div>
				<label class="block text-xs font-semibold text-gray-700 mb-1">Email *</label>
				<input
					type="email"
					bind:value={newUserData.email}
					placeholder="Enter email"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<!-- Password -->
			<div>
				<label class="block text-xs font-semibold text-gray-700 mb-1">Password *</label>
				<input
					type="password"
					bind:value={newUserData.password}
					placeholder="Enter password"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<!-- Phone -->
			<div>
				<label class="block text-xs font-semibold text-gray-700 mb-1">Phone</label>
				<input
					type="tel"
					bind:value={newUserData.phone}
					placeholder="Enter phone number"
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				/>
			</div>

			<!-- Department (for Nurse/Faculty) -->
			{#if newUserRole === 'NURSE' || newUserRole === 'FACULTY'}
				<div>
					<label class="block text-xs font-semibold text-gray-700 mb-1">Department</label>
					<input
						type="text"
						bind:value={newUserData.department}
						placeholder="Enter department"
						class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>
			{/if}

			<!-- Action Buttons -->
			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => createUserModal = false}>
					Cancel
				</AquaButton>
				<AquaButton
					variant="primary"
					fullWidth
					disabled={creatingUser}
					onclick={createUser}
				>
					{creatingUser ? 'Creating...' : 'Create User'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

<!-- Confirm Modal -->
{#if confirmModal}
	<AquaModal title="Confirm Action" onclose={() => confirmModal = false}>
		<div class="p-4 space-y-4">
			<p class="text-sm text-gray-700">{confirmMessage}</p>
			<div class="flex gap-2">
				<AquaButton variant="secondary" fullWidth onclick={() => confirmModal = false}>
					Cancel
				</AquaButton>
				<AquaButton
					variant="danger"
					fullWidth
					disabled={actionLoading}
					onclick={() => confirmAction && confirmAction()}
				>
					{actionLoading ? 'Processing...' : 'Confirm'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
