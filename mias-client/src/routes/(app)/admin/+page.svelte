<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { adminApi, type AdminDashboard } from '$lib/api/admin';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import {
		Users, GraduationCap, Building, UserCheck, UserX, Bed,
		Pill, CheckCircle, TrendingUp, ChevronRight, Shield,
		Activity, BarChart3, Settings, FileText
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);
	let error = $state('');
	let dashboard: AdminDashboard | null = $state(null);
	let roleDistribution: Record<string, number> = $state({});

	onMount(async () => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		try {
			const [d, rd] = await Promise.all([
				adminApi.getDashboard(),
				adminApi.getRoleDistribution(),
			]);
			dashboard = d;
			roleDistribution = rd;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load dashboard';
		} finally {
			loading = false;
		}
	});

	const quickLinks = [
		{ icon: Users, label: 'Manage Users', path: '/admin/users', color: '#3b82f6' },
		{ icon: Building, label: 'Departments', path: '/admin/departments', color: '#8b5cf6' },
		{ icon: BarChart3, label: 'Analytics', path: '/admin/analytics', color: '#10b981' },
	];
</script>

<div class="px-4 py-4 space-y-4 max-w-4xl mx-auto">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-2">
		<div
			class="w-10 h-10 rounded-xl flex items-center justify-center"
			style="background: linear-gradient(135deg, #4d90fe, #0066cc); box-shadow: 0 2px 8px rgba(0,102,204,0.3);"
		>
			<Shield class="w-5 h-5 text-white" />
		</div>
		<div>
			<h1 class="text-xl font-bold text-blue-900" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
				Admin Panel
			</h1>
			<p class="text-xs text-blue-600">Hospital Management Overview</p>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
		</div>
	{:else if error}
		<AquaCard>
			<p class="text-red-500 text-center py-8">{error}</p>
		</AquaCard>
	{:else if dashboard}
		<!-- Stats Grid -->
		<div class="grid grid-cols-2 gap-3">
			<button class="text-left cursor-pointer" onclick={() => goto('/admin/users')}>
				<AquaCard>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							 style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">
							<Users class="w-5 h-5 text-white" />
						</div>
						<div>
							<p class="text-2xl font-bold text-blue-900">{dashboard.total_users}</p>
							<p class="text-xs text-gray-500">Total Users</p>
						</div>
					</div>
				</AquaCard>
			</button>

			<button class="text-left cursor-pointer" onclick={() => goto('/admin/users?role=PATIENT')}>
				<AquaCard>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							 style="background: linear-gradient(135deg, #10b981, #059669);">
							<UserCheck class="w-5 h-5 text-white" />
						</div>
						<div>
							<p class="text-2xl font-bold text-blue-900">{dashboard.total_patients}</p>
							<p class="text-xs text-gray-500">Patients</p>
						</div>
					</div>
				</AquaCard>
			</button>

			<button class="text-left cursor-pointer" onclick={() => goto('/admin/users?role=STUDENT')}>
				<AquaCard>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							 style="background: linear-gradient(135deg, #f59e0b, #d97706);">
							<GraduationCap class="w-5 h-5 text-white" />
						</div>
						<div>
							<p class="text-2xl font-bold text-blue-900">{dashboard.total_students}</p>
							<p class="text-xs text-gray-500">Students</p>
						</div>
					</div>
				</AquaCard>
			</button>

			<button class="text-left cursor-pointer" onclick={() => goto('/admin/users?role=FACULTY')}>
				<AquaCard>
					<div class="flex items-center gap-3">
						<div class="w-10 h-10 rounded-lg flex items-center justify-center"
							 style="background: linear-gradient(135deg, #8b5cf6, #6d28d9);">
							<Activity class="w-5 h-5 text-white" />
						</div>
						<div>
							<p class="text-2xl font-bold text-blue-900">{dashboard.total_faculty}</p>
							<p class="text-xs text-gray-500">Faculty</p>
						</div>
					</div>
				</AquaCard>
			</button>
		</div>

		<!-- Activity Row -->
		<div class="grid grid-cols-3 gap-3">
			<AquaCard>
				<div class="text-center">
					<p class="text-xl font-bold text-green-700">{dashboard.active_admissions}</p>
					<p class="text-[10px] text-gray-500 mt-1">Active Admissions</p>
				</div>
			</AquaCard>
			<AquaCard>
				<div class="text-center">
					<p class="text-xl font-bold text-orange-600">{dashboard.pending_approvals}</p>
					<p class="text-[10px] text-gray-500 mt-1">Pending Approvals</p>
				</div>
			</AquaCard>
			<AquaCard>
				<div class="text-center">
					<p class="text-xl font-bold text-red-600">{dashboard.blocked_users}</p>
					<p class="text-[10px] text-gray-500 mt-1">Blocked Users</p>
				</div>
			</AquaCard>
		</div>

		<!-- Recent Registrations banner -->
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

		<!-- Role Distribution -->
		<AquaCard>
			{#snippet header()}
				<FileText class="w-4 h-4 text-blue-700 mr-2" />
				<span class="text-sm font-semibold text-blue-900">Role Distribution</span>
			{/snippet}
			<div class="space-y-2">
				{#each Object.entries(roleDistribution) as [role, count]}
					{@const total = Object.values(roleDistribution).reduce((a, b) => a + b, 0)}
					{@const pct = total > 0 ? Math.round((count / total) * 100) : 0}
					{@const colors: Record<string, string> = { PATIENT: '#10b981', STUDENT: '#f59e0b', FACULTY: '#8b5cf6', ADMIN: '#ef4444' }}
					<div>
						<div class="flex items-center justify-between text-xs mb-1">
							<span class="font-medium text-gray-700">{role}</span>
							<span class="text-gray-500">{count} ({pct}%)</span>
						</div>
						<div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
							<div
								class="h-full rounded-full transition-all"
								style="width: {pct}%; background-color: {colors[role] || '#6b7280'};"
							></div>
						</div>
					</div>
				{/each}
			</div>
		</AquaCard>

		<!-- Quick Links -->
		<div class="space-y-2">
			<p class="text-xs font-semibold text-gray-500 uppercase tracking-wider px-1">Quick Access</p>
			{#each quickLinks as link}
				{@const Icon = link.icon}
				<button
					class="w-full text-left cursor-pointer"
					onclick={() => goto(link.path)}
				>
					<AquaCard>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3">
								<div class="w-9 h-9 rounded-lg flex items-center justify-center"
									 style="background: linear-gradient(135deg, {link.color}, {link.color}dd);">
									<Icon class="w-4 h-4 text-white" />
								</div>
								<span class="font-medium text-blue-900 text-sm">{link.label}</span>
							</div>
							<ChevronRight class="w-4 h-4 text-gray-400" />
						</div>
					</AquaCard>
				</button>
			{/each}
		</div>

		<!-- Patient Categories -->
		{#if Object.keys(dashboard.patient_categories).length > 0}
			<AquaCard>
				{#snippet header()}
					<Users class="w-4 h-4 text-blue-700 mr-2" />
					<span class="text-sm font-semibold text-blue-900">Patient Categories</span>
				{/snippet}
				<div class="grid grid-cols-2 gap-3">
					{#each Object.entries(dashboard.patient_categories) as [cat, count]}
						{@const catColors: Record<string, string> = { GENERAL: '#6b7280', ELITE: '#f59e0b', VIP: '#8b5cf6', STAFF: '#3b82f6' }}
						<div class="flex items-center gap-2 py-1">
							<div
								class="w-3 h-3 rounded-full"
								style="background-color: {catColors[cat] || '#6b7280'};"
							></div>
							<span class="text-xs text-gray-600">{cat}</span>
							<span class="text-xs font-bold text-blue-900 ml-auto">{count}</span>
						</div>
					{/each}
				</div>
			</AquaCard>
		{/if}
	{/if}
</div>
