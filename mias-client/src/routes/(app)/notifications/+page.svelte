<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { notificationCountStore } from '$lib/stores/notifications';
	import { toastStore } from '$lib/stores/toast';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Bell, AlertCircle, CheckCircle, AlertTriangle, Info,
		Filter, ChevronDown, ChevronRight, X, ArrowLeft
	} from 'lucide-svelte';

	const colorMap: Record<string, { bg: string; icon: string; light: string }> = {
		INFO: { bg: '#4d90fe', icon: '#4d90fe', light: 'rgba(77,144,254,0.1)' },
		WARNING: { bg: '#f97316', icon: '#f97316', light: 'rgba(249,115,22,0.1)' },
		ERROR: { bg: '#ef4444', icon: '#ef4444', light: 'rgba(239,68,68,0.1)' },
		SUCCESS: { bg: '#22c55e', icon: '#22c55e', light: 'rgba(34,197,94,0.1)' },
	};

	const filterOptions = [
		{ id: 'all', label: 'All Notifications' },
		{ id: 'unread', label: 'Unread' },
		{ id: 'INFO', label: 'Information' },
		{ id: 'WARNING', label: 'Warnings' },
		{ id: 'ERROR', label: 'Alerts' },
		{ id: 'SUCCESS', label: 'Success' },
	];

	let notifications: any[] = $state([]);
	let loading = $state(true);
	let activeFilter = $state('all');
	let dropdownOpen = $state(false);
	let selectedNotif: any | null = $state(null);

	let cachedRole = $state('');
	let cachedEntityId = $state('');

	const unreadCount = $derived(notifications.filter(n => !n.is_read).length);
	const currentFilterLabel = $derived(filterOptions.find(f => f.id === activeFilter)?.label || 'All');

	const filteredNotifications = $derived.by(() => {
		let list = notifications;
		if (activeFilter === 'unread') list = list.filter(n => !n.is_read);
		else if (activeFilter !== 'all') list = list.filter(n => n.type === activeFilter);
		return list;
	});

	// Group: unread first, then read, both sorted by date
	const groupedUnread = $derived(filteredNotifications.filter(n => !n.is_read));
	const groupedRead = $derived(filteredNotifications.filter(n => n.is_read));
	const selectedNotifColors = $derived(selectedNotif ? (colorMap[selectedNotif.type] || colorMap.INFO) : colorMap.INFO);

	function timeAgo(dateStr: string): string {
		const now = Date.now();
		const diff = now - new Date(dateStr).getTime();
		const mins = Math.floor(diff / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		return `${days}d ago`;
	}

	function syncUnreadCount(items: any[]) {
		notificationCountStore.set(items.filter((n) => !n.is_read).length);
	}

	async function loadNotifications() {
		try {
			if (cachedRole === 'PATIENT') {
				notifications = await patientApi.getNotifications(cachedEntityId);
			} else if (cachedRole === 'STUDENT') {
				notifications = await studentApi.getNotifications(cachedEntityId);
			} else if (cachedRole === 'FACULTY') {
				notifications = await facultyApi.getNotifications(cachedEntityId);
			}
			syncUnreadCount(notifications);
		} catch (err) {
			toastStore.addToast('Failed to load notifications', 'error');
		}
	}

	async function markAllRead() {
		try {
			if (cachedRole === 'PATIENT') {
				await patientApi.markNotificationsRead(cachedEntityId);
			} else if (cachedRole === 'STUDENT') {
				await studentApi.markNotificationsRead(cachedEntityId);
			} else if (cachedRole === 'FACULTY') {
				await facultyApi.markNotificationsRead(cachedEntityId);
			}
			notifications = notifications.map((notification) => ({ ...notification, is_read: true }));
			syncUnreadCount(notifications);
			await loadNotifications();
		} catch (err) {
			toastStore.addToast('Failed to mark notifications as read', 'error');
		}
	}

	onMount(async () => {
		try {
			const auth = get(authStore);
			const role = auth.role;
			cachedRole = role || '';
			if (role === 'PATIENT') {
				const patient = await patientApi.getCurrentPatient();
				cachedEntityId = patient.id;
			} else if (role === 'STUDENT') {
				const student = await studentApi.getMe();
				cachedEntityId = student.id;
			} else if (role === 'FACULTY') {
				const faculty = await facultyApi.getMe();
				cachedEntityId = faculty.id;
			} else if (role === 'ADMIN' || role === 'RECEPTION') {
				// Admin and Reception roles don't have notifications
				notifications = [];
				syncUnreadCount([]);
				loading = false;
				return;
			}
			await loadNotifications();
		} catch (err) {
			toastStore.addToast('Failed to load notifications', 'error');
		} finally {
			loading = false;
		}
	});

	$effect(() => {
		if (loading || !cachedEntityId) return;
		const interval = setInterval(loadNotifications, 15000);
		return () => clearInterval(interval);
	});
</script>

<div class="px-3 py-4 md:px-6 md:py-6 space-y-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Header Card -->
		<div class="overflow-hidden"
			style="background-color: white; border-radius: 10px;
				   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				   border: 1px solid rgba(0,0,0,0.1);">
			<div class="p-4 flex items-center justify-between gap-3"
				style="border-bottom: 1px solid rgba(0,0,0,0.06);">
				<div class="flex items-center gap-2 min-w-0">
					<button
						class="w-8 h-8 flex items-center justify-center rounded-full cursor-pointer"
						style="background: linear-gradient(to bottom, #ffffff, #f3f4f6);
							   border: 1px solid rgba(0,0,0,0.08);
							   box-shadow: 0 1px 2px rgba(0,0,0,0.06);"
						onclick={() => window.history.back()}
						aria-label="Go back"
					>
						<ArrowLeft class="w-4 h-4 text-gray-700" />
					</button>
					<div class="flex items-center gap-2 min-w-0">
						<Bell class="w-4 h-4 text-blue-700" />
						<h2 class="font-semibold text-gray-800 text-sm truncate">Notifications</h2>
						{#if unreadCount > 0}
							<span class="bg-red-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
								{unreadCount}
							</span>
						{/if}
					</div>
				</div>
				{#if unreadCount > 0}
					<button
						class="text-xs text-blue-600 font-medium cursor-pointer hover:text-blue-800 shrink-0"
						onclick={markAllRead}
					>
						Mark all as read
					</button>
				{/if}
			</div>

			<!-- Filter Dropdown -->
			<div class="p-3 relative" style="background-color: #f9fafb;">
				<button
					class="w-full px-4 py-2.5 flex items-center justify-between text-sm font-medium text-gray-700 cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #f8f9fa);
						   border: 1px solid rgba(0,0,0,0.12); border-radius: 8px;
						   box-shadow: 0 1px 2px rgba(0,0,0,0.06);"
					onclick={() => dropdownOpen = !dropdownOpen}
				>
					<div class="flex items-center gap-2">
						<Filter class="w-3.5 h-3.5 text-gray-500" />
						<span>{currentFilterLabel}</span>
					</div>
					<ChevronDown class="w-4 h-4 text-gray-400 transition-transform {dropdownOpen ? 'rotate-180' : ''}" />
				</button>
				{#if dropdownOpen}
					<div class="absolute left-3 right-3 mt-1 z-50 py-1"
						style="background: white; border: 1px solid rgba(0,0,0,0.12);
							   border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
						{#each filterOptions as opt}
							<button
								class="w-full px-4 py-2.5 text-left text-sm flex items-center cursor-pointer transition-colors"
								style="background: {activeFilter === opt.id ? 'rgba(59,130,246,0.05)' : 'transparent'};
									   color: {activeFilter === opt.id ? '#2563eb' : '#374151'};
									   font-weight: {activeFilter === opt.id ? '600' : '400'};"
								onclick={() => { activeFilter = opt.id; dropdownOpen = false; }}
							>
								{opt.label}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Unread Section -->
		{#if groupedUnread.length > 0}
			<div class="overflow-hidden"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<div class="px-4 py-2 flex items-center gap-2"
					style="background: linear-gradient(to bottom, #fefce8, #fef9c3);
						   border-bottom: 1px solid rgba(0,0,0,0.06);">
					<AlertTriangle class="w-3 h-3 text-amber-600" />
					<p class="text-xs font-semibold text-amber-800">Unread ({groupedUnread.length})</p>
				</div>
				<div class="divide-y divide-gray-50">
					{#each groupedUnread as notif}
						{@const colors = colorMap[notif.type] || colorMap.INFO}
						<button
							class="w-full p-3 flex items-center gap-3 cursor-pointer text-left transition-colors"
							style="background-color: rgba(77,144,254,0.03);"
							onclick={() => selectedNotif = notif}
						>
							<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
								style="background: linear-gradient(to bottom, {colors.bg}cc, {colors.bg});">
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
								<div class="flex items-center gap-1.5">
									<p class="text-xs font-semibold text-gray-900 truncate">{notif.title}</p>
									<div class="w-2 h-2 rounded-full bg-blue-500 shrink-0"></div>
								</div>
								<p class="text-[11px] text-gray-500 truncate mt-0.5">{notif.message}</p>
								<p class="text-[10px] text-gray-400 mt-0.5">{timeAgo(notif.created_at)}</p>
							</div>
							<ChevronRight class="w-4 h-4 text-gray-300 shrink-0" />
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Read Section -->
		{#if groupedRead.length > 0}
			<div class="overflow-hidden"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<div class="px-4 py-2"
					style="background-color: #f9fafb; border-bottom: 1px solid rgba(0,0,0,0.06);">
					<p class="text-xs font-semibold text-gray-500">Earlier</p>
				</div>
				<div class="divide-y divide-gray-50">
					{#each groupedRead as notif}
						{@const colors = colorMap[notif.type] || colorMap.INFO}
						<button
							class="w-full p-3 flex items-center gap-3 cursor-pointer text-left transition-colors"
							onclick={() => selectedNotif = notif}
						>
							<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
								style="background: {colors.light};">
								{#if notif.type === 'INFO'}
									<Info class="w-4 h-4" style="color: {colors.icon};" />
								{:else if notif.type === 'WARNING'}
									<AlertTriangle class="w-4 h-4" style="color: {colors.icon};" />
								{:else if notif.type === 'ERROR'}
									<AlertCircle class="w-4 h-4" style="color: {colors.icon};" />
								{:else}
									<CheckCircle class="w-4 h-4" style="color: {colors.icon};" />
								{/if}
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-xs font-medium text-gray-700 truncate">{notif.title}</p>
								<p class="text-[11px] text-gray-400 truncate mt-0.5">{notif.message}</p>
								<p class="text-[10px] text-gray-400 mt-0.5">{timeAgo(notif.created_at)}</p>
							</div>
							<ChevronRight class="w-4 h-4 text-gray-300 shrink-0" />
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Empty -->
		{#if filteredNotifications.length === 0}
			<div class="text-center py-12"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<div class="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3"
					style="background-color: #f3f4f6;">
					<Bell class="w-7 h-7 text-gray-400" />
				</div>
				<p class="text-sm font-medium text-gray-800 mb-1">No notifications</p>
				<p class="text-xs text-gray-500">
					You don't have any {activeFilter !== 'all' ? filterOptions.find(f => f.id === activeFilter)?.label.toLowerCase() : ''} notifications.
				</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Details Modal -->
{#if selectedNotif}
	<AquaModal title={selectedNotif.title} onclose={() => selectedNotif = null}>
		<div class="space-y-3">
			<div class="px-4 py-3 rounded-lg" style="background-color: {selectedNotifColors.light};">
				<div class="flex items-center gap-2 mb-2">
					{#if selectedNotif.type === 'INFO'}
						<Info class="w-4 h-4" style="color: {selectedNotifColors.icon};" />
					{:else if selectedNotif.type === 'WARNING'}
						<AlertTriangle class="w-4 h-4" style="color: {selectedNotifColors.icon};" />
					{:else if selectedNotif.type === 'ERROR'}
						<AlertCircle class="w-4 h-4" style="color: {selectedNotifColors.icon};" />
					{:else}
						<CheckCircle class="w-4 h-4" style="color: {selectedNotifColors.icon};" />
					{/if}
					<span class="text-xs font-bold uppercase" style="color: {selectedNotifColors.icon};">{selectedNotif.type}</span>
				</div>
				<p class="text-sm text-gray-800">{selectedNotif.message}</p>
			</div>
			<p class="text-[10px] text-gray-400">
				{new Date(selectedNotif.created_at).toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' })}
			</p>
		</div>
	</AquaModal>
{/if}
