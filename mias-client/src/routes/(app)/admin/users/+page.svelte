<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { page } from '$app/state';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type AdminUser } from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import {
		Search, Users, Shield, ShieldOff, Trash2, Filter,
		ChevronLeft, ChevronRight, UserCheck, UserX
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

	const totalPages = $derived(Math.ceil(total / 20));

	const roleTabs = [
		{ id: '', label: 'All' },
		{ id: 'PATIENT', label: 'Patients' },
		{ id: 'STUDENT', label: 'Students' },
		{ id: 'FACULTY', label: 'Faculty' },
		{ id: 'ADMIN', label: 'Admins' },
		{ id: 'RECEPTION', label: 'Reception' },
	];

	function roleColor(role: string) {
		const map: Record<string, string> = {
			PATIENT: '#10b981',
			STUDENT: '#f59e0b',
			FACULTY: '#8b5cf6',
			ADMIN: '#ef4444',
			RECEPTION: '#3b82f6',
		};
		return map[role] || '#6b7280';
	}
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4 max-w-4xl mx-auto">
	<!-- Header -->
	<div class="flex items-center gap-3">
		<button class="text-blue-600 cursor-pointer" onclick={() => goto('/admin')}>
			<ChevronLeft class="w-5 h-5" />
		</button>
		<div>
			<h1 class="text-lg font-bold text-blue-900">User Management</h1>
			<p class="text-xs text-gray-500">{total} total users</p>
		</div>
	</div>

	<!-- Search -->
	<div class="relative">
		<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
		<input
			type="text"
			placeholder="Search by username or email..."
			bind:value={searchQuery}
			onkeydown={(e) => e.key === 'Enter' && handleSearch()}
			class="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
			style="background: white; box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
		/>
	</div>

	<!-- Role Tabs -->
	<div class="flex gap-2 overflow-x-auto pb-1">
		{#each roleTabs as tab}
			<button
				class="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap cursor-pointer transition-all"
				style={roleFilter === tab.id
					? `background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);`
					: `background: white; color: #4b5563; border: 1px solid #e5e7eb;`}
				onclick={() => setRoleFilter(tab.id)}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Status filter -->
	<div class="flex gap-2">
		{#each [{ id: '', label: 'All Status' }, { id: 'active', label: 'Active' }, { id: 'blocked', label: 'Blocked' }] as sf}
			<button
				class="px-2.5 py-1 rounded text-xs cursor-pointer"
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
		<AquaCard>
			<p class="text-red-500 text-center py-4">{error}</p>
		</AquaCard>
	{:else}
		<!-- User list -->
		<div class="space-y-2">
			{#each users as u}
				<AquaCard>
					<div class="flex items-center gap-3">
						<Avatar name={u.name} size="sm" />
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<p class="text-sm font-semibold text-blue-900 truncate">{u.name}</p>
								{#if !u.is_active}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">Blocked</span>
								{/if}
							</div>
							<p class="text-xs text-gray-500 truncate">@{u.username} · {u.email}</p>
							<div class="flex items-center gap-2 mt-1">
								<span
									class="text-[10px] px-1.5 py-0.5 rounded font-medium text-white"
									style="background-color: {roleColor(u.role)};"
								>
									{u.role}
								</span>
								{#if u.last_login}
									<span class="text-[10px] text-gray-400">
										Last: {new Date(u.last_login).toLocaleDateString()}
									</span>
								{/if}
							</div>
						</div>
						<div class="flex gap-1">
							<button
								class="p-2 rounded-lg cursor-pointer hover:bg-gray-100"
								title={u.is_active ? 'Block' : 'Unblock'}
								onclick={() => toggleBlock(u)}
							>
								{#if u.is_active}
									<ShieldOff class="w-4 h-4 text-orange-500" />
								{:else}
									<Shield class="w-4 h-4 text-green-500" />
								{/if}
							</button>
							<button
								class="p-2 rounded-lg cursor-pointer hover:bg-red-50"
								title="Delete"
								onclick={() => deleteUser(u)}
							>
								<Trash2 class="w-4 h-4 text-red-400" />
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}

			{#if users.length === 0}
				<div class="text-center py-12 text-gray-400 text-sm">No users found</div>
			{/if}
		</div>

		<!-- Pagination -->
		{#if totalPages > 1}
			<div class="flex items-center justify-center gap-4 py-2">
				<button
					class="p-2 rounded-lg cursor-pointer disabled:opacity-30"
					disabled={currentPage <= 1}
					onclick={() => { currentPage--; loadUsers(); }}
				>
					<ChevronLeft class="w-5 h-5 text-blue-600" />
				</button>
				<span class="text-sm text-gray-600">
					Page {currentPage} of {totalPages}
				</span>
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
