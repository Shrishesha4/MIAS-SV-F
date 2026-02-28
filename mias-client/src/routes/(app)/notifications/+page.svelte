<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { Bell, AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-svelte';

	const colorMap: Record<string, string> = {
		INFO: '#4d90fe',
		WARNING: '#f97316',
		ERROR: '#ef4444',
		SUCCESS: '#22c55e',
	};

	let notifications: any[] = $state([]);
	let loading = $state(true);

	function timeAgo(dateStr: string): string {
		const now = Date.now();
		const diff = now - new Date(dateStr).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		return `${days}d ago`;
	}

	let cachedRole = $state('');
	let cachedEntityId = $state('');

	onMount(async () => {
		try {
			const auth = get(authStore);
			const role = auth.role;
			cachedRole = role || '';
			if (role === 'PATIENT') {
				const patient = await patientApi.getCurrentPatient();
				cachedEntityId = patient.id;
				notifications = await patientApi.getNotifications(patient.id);
			} else if (role === 'STUDENT') {
				const student = await studentApi.getMe();
				cachedEntityId = student.id;
				notifications = await studentApi.getNotifications(student.id);
			} else if (role === 'FACULTY') {
				const faculty = await facultyApi.getMe();
				cachedEntityId = faculty.id;
				notifications = await facultyApi.getNotifications(faculty.id);
			}
		} catch (err) {
			console.error('Failed to load notifications', err);
		} finally {
			loading = false;
		}
	});

	// Auto-refresh notifications every 15 seconds
	$effect(() => {
		if (loading || !cachedEntityId) return;
		const interval = setInterval(async () => {
			try {
				if (cachedRole === 'PATIENT') {
					notifications = await patientApi.getNotifications(cachedEntityId);
				} else if (cachedRole === 'STUDENT') {
					notifications = await studentApi.getNotifications(cachedEntityId);
				} else if (cachedRole === 'FACULTY') {
					notifications = await facultyApi.getNotifications(cachedEntityId);
				}
			} catch (err) {
				console.error('Auto-refresh failed', err);
			}
		}, 15000);
		return () => clearInterval(interval);
	});
</script>

<div class="px-4 py-4 space-y-2">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	{#each notifications as notif}
		<div
			class="flex items-start gap-3 p-3 rounded-xl transition-colors"
			style="background-color: {notif.is_read ? 'white' : 'rgba(77, 144, 254, 0.05)'};
			       border-radius: 10px;
			       box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
			       border: 1px solid {notif.is_read ? 'rgba(0,0,0,0.1)' : 'rgba(77, 144, 254, 0.2)'};"
		>
			<div
				class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
				style="background: linear-gradient(to bottom, {colorMap[notif.type]}cc, {colorMap[notif.type]});"
			>
				{#if notif.type === 'INFO'}
				<Info class="w-4 h-4 text-white" />
			{:else if notif.type === 'WARNING'}
				<AlertTriangle class="w-4 h-4 text-white" />
			{:else if notif.type === 'ERROR'}
				<AlertCircle class="w-4 h-4 text-white" />
			{:else}
				<CheckCircle class="w-4 h-4 text-white" />
			{/if}
			</div>
			<div class="flex-1 min-w-0">
				<div class="flex items-center justify-between">
					<p class="text-sm font-semibold text-gray-800">{notif.title}</p>
					{#if !notif.is_read}
						<div class="w-2 h-2 rounded-full bg-blue-500 shrink-0"></div>
					{/if}
				</div>
				<p class="text-xs text-gray-600 mt-0.5">{notif.message}</p>
				<p class="text-[10px] text-gray-400 mt-1">{timeAgo(notif.created_at)}</p>
			</div>
		</div>
	{/each}

	{#if notifications.length === 0}
		<div class="text-center py-12 text-gray-400">
			<Bell class="w-12 h-12 mx-auto mb-3 opacity-50" />
			<p class="text-sm">No notifications</p>
		</div>
	{/if}
	{/if}
</div>
