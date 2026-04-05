<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import {
		Users, UserCheck, Clock, Calendar, Building, Search
	} from 'lucide-svelte';

	const auth = get(authStore);
	let loading = $state(true);

	onMount(async () => {
		if (auth.role !== 'RECEPTION') {
			goto('/dashboard');
			return;
		}
		loading = false;
	});
</script>

<div class="px-4 py-4 space-y-4">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-2">
		<div
			class="w-10 h-10 rounded-xl flex items-center justify-center"
			style="background: linear-gradient(135deg, #10b981, #059669);"
		>
			<Building class="w-5 h-5 text-white" />
		</div>
		<div>
			<h1 class="text-lg font-bold text-gray-800">Reception Dashboard</h1>
			<p class="text-xs text-gray-500">Clinic Reception Management</p>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<span class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></span>
		</div>
	{:else}
		<!-- Stats Row -->
		<div class="grid grid-cols-2 gap-3">
			<AquaCard>
				<div class="flex items-center gap-3 p-1">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(59,130,246,0.1);">
						<Users class="w-5 h-5" style="color: #3b82f6;" />
					</div>
					<div>
						<p class="text-2xl font-bold text-gray-800">0</p>
						<p class="text-xs text-gray-500">In Queue</p>
					</div>
				</div>
			</AquaCard>
			<AquaCard>
				<div class="flex items-center gap-3 p-1">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(16,185,129,0.1);">
						<UserCheck class="w-5 h-5" style="color: #10b981;" />
					</div>
					<div>
						<p class="text-2xl font-bold text-gray-800">0</p>
						<p class="text-xs text-gray-500">Checked In</p>
					</div>
				</div>
			</AquaCard>
			<AquaCard>
				<div class="flex items-center gap-3 p-1">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(245,158,11,0.1);">
						<Clock class="w-5 h-5" style="color: #f59e0b;" />
					</div>
					<div>
						<p class="text-2xl font-bold text-gray-800">0</p>
						<p class="text-xs text-gray-500">In Progress</p>
					</div>
				</div>
			</AquaCard>
			<AquaCard>
				<div class="flex items-center gap-3 p-1">
					<div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background: rgba(139,92,246,0.1);">
						<Calendar class="w-5 h-5" style="color: #8b5cf6;" />
					</div>
					<div>
						<p class="text-2xl font-bold text-gray-800">0</p>
						<p class="text-xs text-gray-500">Today's Appts</p>
					</div>
				</div>
			</AquaCard>
		</div>

		<!-- Patient Search -->
		<AquaCard>
			<div class="p-1">
				<h3 class="text-sm font-semibold text-gray-700 mb-3">Quick Patient Lookup</h3>
				<div
					class="flex items-center px-3 py-2.5 rounded-lg"
					style="border: 1px solid rgba(0,0,0,0.15); background: white;"
				>
					<Search class="w-4 h-4 text-gray-400 mr-2" />
					<input
						type="text"
						placeholder="Search by Patient ID or Name..."
						class="flex-1 outline-none text-sm text-gray-700 bg-transparent placeholder-gray-400"
					/>
				</div>
			</div>
		</AquaCard>

		<!-- Placeholder -->
		<AquaCard>
			<div class="p-4 text-center">
				<div class="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center" style="background: rgba(16,185,129,0.1);">
					<Building class="w-8 h-8" style="color: #10b981;" />
				</div>
				<h3 class="text-base font-semibold text-gray-800 mb-1">Reception Module</h3>
				<p class="text-sm text-gray-500">Patient check-in, queue management, and appointment features coming soon.</p>
			</div>
		</AquaCard>
	{/if}
</div>
