<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { cubicOut } from 'svelte/easing';
	import { fade, fly } from 'svelte/transition';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { notificationCountStore } from '$lib/stores/notifications';
	import { attendanceApi, type AttendanceStatus } from '$lib/api/attendance';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import { nurseApi } from '$lib/api/nurse';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import { getMenuItems } from '$lib/config/menuItems';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import NavBar from '$lib/components/layout/NavBar.svelte';
	import SideMenu from '$lib/components/layout/SideMenu.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import { LogOut, Search, Pin, PinOff, Loader2, UserCheck, Building2 } from 'lucide-svelte';
	import { page } from '$app/state';
	import ToastContainer from '$lib/components/ui/ToastContainer.svelte';

	let { children } = $props();
	let sideMenuOpen = $state(false);

	let 	authState = $state(get(authStore));
	authStore.subscribe(v => authState = v);

	let userName = $state('User');
	let userIdDisplay = $state('');
	let unreadNotifications = $state(get(notificationCountStore));
	let attendanceStatus = $state<AttendanceStatus | null>(null);
	let attendanceLoading = $state(false);
	let attendanceSubmitting = $state(false);

	// Clinic picker for student/faculty
	let clinics = $state<ClinicInfo[]>([]);
	let selectedClinicId = $state<string>('');
	let clinicsLoading = $state(false);

	// Floating sidebar state
	let sidebarPinned = $state(false);
	let sidebarHovered = $state(false);
	let sidebarSearchQuery = $state('');
	let hoverTimeout: ReturnType<typeof setTimeout> | null = null;
	const unsubscribeNotificationCount = notificationCountStore.subscribe((value) => {
		unreadNotifications = value;
	});

	const sidebarOpen = $derived(sidebarPinned || sidebarHovered);

	const currentPath = $derived(page.url.pathname);
	const pageTransitionKey = $derived(currentPath.startsWith('/admin') ? '/admin' : currentPath);
	const menuItems = $derived(getMenuItems(authState.role ?? ''));

	// Show check-in modal only if not checked in and not skipped (admin/IP day2+)
	const needsDailyCheckIn = $derived(
		Boolean(attendanceStatus && !attendanceStatus.checked_in && !attendanceStatus.skip_modal)
	);
	// Student/faculty need to pick a clinic
	const needsClinicPicker = $derived(
		needsDailyCheckIn && (authState.role === 'STUDENT' || authState.role === 'FACULTY')
	);
	const attendanceCounts = $derived(
		attendanceStatus?.counts ?? {
			patients: 0,
			students: 0,
			faculty: 0,
			nurses: 0,
			reception: 0,
			admins: 0,
			total: 0
		}
	);

	const filteredMenuItems = $derived(
		sidebarSearchQuery.trim()
			? menuItems.filter(item => item.label.toLowerCase().includes(sidebarSearchQuery.toLowerCase()))
			: menuItems
	);

	function isActive(path: string): boolean {
		if (path === '/dashboard' || path === '/admin' || path === '/reception') {
			return currentPath === path;
		}
		return currentPath.startsWith(path);
	}

	function navigate(path: string) {
		goto(path);
		if (!sidebarPinned) {
			sidebarHovered = false;
		}
	}

	function handleTriggerEnter() {
		if (hoverTimeout) clearTimeout(hoverTimeout);
		hoverTimeout = setTimeout(() => { sidebarHovered = true; }, 150);
	}

	function handleTriggerLeave() {
		if (hoverTimeout) clearTimeout(hoverTimeout);
	}

	function handleSidebarLeave() {
		if (!sidebarPinned) {
			sidebarHovered = false;
		}
	}

	function togglePin() {
		sidebarPinned = !sidebarPinned;
		if (!sidebarPinned) sidebarHovered = false;
	}

	function closeSidebar() {
		sidebarPinned = false;
		sidebarHovered = false;
		sidebarSearchQuery = '';
	}

	function logout() {
		authStore.logout();
		goto('/login');
	}

	async function loadAttendanceStatus() {
		attendanceLoading = true;
		try {
			attendanceStatus = await attendanceApi.getTodayStatus();
			// Load clinics if student/faculty needs to pick one
			if (
				attendanceStatus &&
				!attendanceStatus.checked_in &&
				!attendanceStatus.skip_modal &&
				(authState.role === 'STUDENT' || authState.role === 'FACULTY')
			) {
				clinicsLoading = true;
				try {
					clinics = await clinicsApi.listClinics();
					// Pre-select first active clinic
					const activeClinics = clinics.filter(c => c.is_active);
					if (activeClinics.length > 0) {
						selectedClinicId = activeClinics[0].id;
					}
				} finally {
					clinicsLoading = false;
				}
			}
		} catch {
			attendanceStatus = null;
		} finally {
			attendanceLoading = false;
		}
	}

	async function submitDailyCheckIn() {
		if (attendanceSubmitting) return;
		// For student/faculty, require clinic selection
		if (needsClinicPicker && !selectedClinicId) return;
		attendanceSubmitting = true;
		try {
			const clinicId = needsClinicPicker ? selectedClinicId : undefined;
			attendanceStatus = await attendanceApi.checkInToday(clinicId);
		} finally {
			attendanceSubmitting = false;
		}
	}

	onMount(async () => {
		const a = get(authStore);
		if (!a.isAuthenticated) {
			goto('/login');
			return;
		}
		try {
			if (a.role === 'PATIENT') {
				const patient = await patientApi.getCurrentPatient();
				userName = patient.name;
				userIdDisplay = patient.patient_id;
				const notifs = await patientApi.getNotifications(patient.id);
				notificationCountStore.set(notifs.filter((n: any) => !n.is_read).length);
			} else if (a.role === 'STUDENT') {
				const student = await studentApi.getMe();
				userName = student.name;
				userIdDisplay = student.student_id;
				const notifs = await studentApi.getNotifications(student.id);
				notificationCountStore.set(notifs.filter((n: any) => !n.is_read).length);
			} else if (a.role === 'FACULTY') {
				const faculty = await facultyApi.getMe();
				userName = faculty.name;
				userIdDisplay = faculty.faculty_id;
				const notifs = await facultyApi.getNotifications(faculty.id);
				notificationCountStore.set(notifs.filter((n: any) => !n.is_read).length);
			} else if (a.role === 'NURSE') {
				const nurse = await nurseApi.getMe();
				userName = nurse.name;
				userIdDisplay = nurse.nurse_id;
				notificationCountStore.set(0);
				// Redirect to station selection if not yet selected (but not if already on setup or station pages)
				const currentPath = window.location.pathname;
				if (!nurse.has_selected_station && currentPath !== '/nurse-setup') {
					goto('/nurse-setup');
				}
			} else if (a.role === 'ADMIN') {
				userName = 'Administrator';
				userIdDisplay = 'ADMIN';
				notificationCountStore.set(0);
				if (window.location.pathname === '/dashboard') {
					goto('/admin/clinics');
				}
			} else if (a.role === 'RECEPTION') {
				userName = 'Reception';
				userIdDisplay = 'RECEPTION';
				notificationCountStore.set(0);
				if (window.location.pathname === '/dashboard') {
					goto('/reception');
				}
			}
		} catch {
			// If API fails, use defaults
		}
		await loadAttendanceStatus();
	});

	onDestroy(() => {
		unsubscribeNotificationCount();
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="min-h-screen">
	<!-- Desktop: Floating sidebar backdrop (when pinned/hovered) -->
	{#if sidebarOpen}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="sidebar-backdrop motion-overlay" onclick={closeSidebar}></div>
	{/if}

	<!-- Desktop: Thin trigger strip (always visible, left edge) removed - sidebar opens via NavBar icon hover -->

	<!-- Desktop: Floating sidebar panel -->
	<aside
		class="floating-sidebar"
		class:floating-sidebar-open={sidebarOpen}
		onmouseleave={handleSidebarLeave}
	>
		<!-- Header with user info + pin toggle -->
		<div class="sidebar-header">
			<div class="flex items-center gap-3 flex-1 min-w-0">
				<Avatar name={userName} size="sm" />
				<div class="min-w-0">
					<p class="text-sm font-semibold text-blue-900 truncate" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
						{userName}
					</p>
					<p class="text-xs text-blue-700">{userIdDisplay}</p>
				</div>
			</div>
			<button
				class="motion-control w-7 h-7 rounded-md flex items-center justify-center cursor-pointer shrink-0"
				style="background: rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.1);"
				onclick={togglePin}
				title={sidebarPinned ? 'Unpin sidebar' : 'Pin sidebar'}
			>
				{#if sidebarPinned}
					<PinOff class="w-3.5 h-3.5 text-blue-700" />
				{:else}
					<Pin class="w-3.5 h-3.5 text-gray-500" />
				{/if}
			</button>
		</div>

		<!-- Search bar -->
		<div class="px-3 py-2" style="border-bottom: 1px solid rgba(0,0,0,0.08);">
			<div class="relative">
				<Search class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
				<input
					type="text"
					placeholder="Search pages..."
					bind:value={sidebarSearchQuery}
					class="motion-control w-full pl-8 pr-3 py-1.5 text-xs rounded-md outline-none"
					style="background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.12);
					       box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
				/>
			</div>
		</div>

		<!-- Navigation -->
		<nav class="flex-1 overflow-y-auto py-2 px-2">
			{#each filteredMenuItems as item}
				{@const Icon = item.icon}
				{@const active = isActive(item.path)}
				<button
					class="sidebar-item motion-list-item"
					class:sidebar-item-active={active}
					onclick={() => navigate(item.path)}
				>
					<div class="sidebar-icon" class:sidebar-icon-active={active}>
						<Icon class="w-4 h-4" />
					</div>
					<span class="text-sm font-medium truncate">{item.label}</span>
				</button>
			{/each}
			{#if filteredMenuItems.length === 0}
				<p class="text-xs text-gray-400 text-center py-4">No pages match</p>
			{/if}
		</nav>

		<!-- Logout -->
		<div class="p-3" style="border-top: 1px solid rgba(0,0,0,0.1);">
			<button
				class="motion-control w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium cursor-pointer
				       transition-all active:translate-y-0.5"
				style="background: linear-gradient(to bottom, #ff5a5a, #cc0000);
				       border: 1px solid rgba(0,0,0,0.2);
				       box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
				onclick={logout}
			>
				<LogOut class="w-4 h-4" />
				<span>Sign Out</span>
			</button>
		</div>
	</aside>

	<!-- Main Content Area (full width, content flows under trigger strip) -->
	<div class="flex flex-col min-h-screen">
		<NavBar
			showBack={currentPath !== '/dashboard' && currentPath !== '/admin' && currentPath !== '/reception'}
			notificationCount={unreadNotifications}
			onmenuclick={() => sideMenuOpen = true}
			onmenuenter={handleTriggerEnter}
			onmenuleave={handleTriggerLeave}
		/>

		<main class="flex-1 pb-4">
			<div class="content-container">
				{#key pageTransitionKey}
					<div
						class="page-transition-shell"
						in:fade={{ duration: 180 }}
						out:fade={{ duration: 140 }}
					>
						{@render children()}
					</div>
				{/key}
			</div>
		</main>
	</div>

	<ToastContainer />

	{#if needsDailyCheckIn}
		<AquaModal
			title="Daily hospital check-in"
			panelClass="sm:max-w-lg"
			contentClass="p-5"
		>
			<div class="space-y-4">
				<div class="rounded-2xl px-4 py-4" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid #93c5fd;">
					<p class="text-sm font-semibold text-gray-900">Please mark today&apos;s hospital presence before continuing.</p>
					<p class="mt-1 text-xs text-gray-600">
						{#if needsClinicPicker}
							Select the clinic you're working in today.
						{:else}
							Everyone checks in once each day so the hospital census stays accurate.
						{/if}
					</p>
				</div>

				{#if needsClinicPicker}
					<!-- Clinic picker for student/faculty -->
					<div>
						<label class="block text-xs font-medium text-gray-700 mb-1.5">
							<Building2 class="inline w-3.5 h-3.5 mr-1 -mt-0.5" />
							Select your clinic for today
						</label>
						{#if clinicsLoading}
							<div class="flex items-center justify-center py-4">
								<Loader2 class="w-5 h-5 text-blue-500 animate-spin" />
							</div>
						{:else}
							<select
								bind:value={selectedClinicId}
								class="w-full rounded-xl px-4 py-3 text-sm outline-none"
								style="background: #fff; border: 1px solid rgba(0,0,0,0.15); box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
							>
								<option value="" disabled>Choose a clinic...</option>
								{#each clinics.filter(c => c.is_active) as clinic}
									<option value={clinic.id}>{clinic.name} ({clinic.department})</option>
								{/each}
							</select>
						{/if}
					</div>
				{/if}

				<div class="grid grid-cols-1 gap-3">
					<div class="rounded-xl px-4 py-3" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08);">
						<p class="text-[11px] uppercase tracking-[0.16em] text-gray-500">Patients today</p>
						<p class="mt-1 text-2xl font-bold text-blue-700">{attendanceCounts.patients}</p>
					</div>
					<!-- <div class="rounded-xl px-4 py-3" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08);">
						<p class="text-[11px] uppercase tracking-[0.16em] text-gray-500">Total present</p>
						<p class="mt-1 text-2xl font-bold text-gray-900">{attendanceCounts.total}</p>
					</div> -->
				</div>

				<!-- <div class="grid grid-cols-3 gap-2 text-center">
					<div class="rounded-xl px-3 py-2" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">Students</p>
						<p class="text-lg font-bold text-gray-800">{attendanceCounts.students}</p>
					</div>
					<div class="rounded-xl px-3 py-2" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">Faculty</p>
						<p class="text-lg font-bold text-gray-800">{attendanceCounts.faculty}</p>
					</div>
					<div class="rounded-xl px-3 py-2" style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-[10px] uppercase tracking-[0.14em] text-gray-500">Nurses</p>
						<p class="text-lg font-bold text-gray-800">{attendanceCounts.nurses}</p>
					</div>
				</div> -->

				<button
					class="w-full rounded-2xl px-4 py-3 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 2px 6px rgba(29,78,216,0.35);"
					onclick={submitDailyCheckIn}
					disabled={attendanceSubmitting || (needsClinicPicker && !selectedClinicId)}
				>
					{#if attendanceSubmitting}
						<Loader2 class="mr-2 inline h-4 w-4 animate-spin" /> Completing check-in
					{:else}
						<UserCheck class="mr-2 inline h-4 w-4" /> Check In
					{/if}
				</button>
			</div>
		</AquaModal>
	{/if}

	<!-- Mobile Overlay Menu -->
	<div class="md:hidden">
		<SideMenu
			bind:open={sideMenuOpen}
			onclose={() => sideMenuOpen = false}
			{userName}
			userRole={authState.role ?? ''}
			userId={userIdDisplay}
		/>
	</div>
</div>

<style>
	/* Content container - mobile: full width, desktop: full width */
	.content-container {
		width: min(100%, 448px);
		margin-left: auto;
		margin-right: auto;
	}

	/* ── Floating sidebar panel ────────────────────────── */
	.floating-sidebar {
		display: none;
	}

	/* ── Backdrop ──────────────────────────────────────── */
	.sidebar-backdrop {
		display: none;
	}

	@media (min-width: 768px) {
		.content-container {
			width: min(calc(100% - 32px), 1440px);
		}

		.sidebar-backdrop {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 40;
			background: rgba(0, 0, 0, 0.15);
		}

		.floating-sidebar {
			display: flex;
			flex-direction: column;
			position: fixed;
			left: 0;
			top: 0;
			bottom: 0;
			width: 260px;
			z-index: 45;
			background-color: #dce1e8;
			background-image:
				repeating-linear-gradient(
					0deg,
					rgba(180, 190, 210, 0.15),
					rgba(180, 190, 210, 0.15) 1px,
					transparent 1px,
					transparent 2px
				);
			border-right: 1px solid rgba(0,0,0,0.12);
			box-shadow: 4px 0 16px rgba(0,0,0,0.12);
			transform: translateX(-100%);
			opacity: 0;
			transition:
				transform var(--motion-duration-slow) var(--motion-ease-emphasized),
				opacity var(--motion-duration-fast) var(--motion-ease-standard),
				box-shadow var(--motion-duration-base) var(--motion-ease-standard);
			pointer-events: none;
		}

		.floating-sidebar-open {
			transform: translateX(0);
			opacity: 1;
			pointer-events: auto;
		}
	}

	@media (min-width: 1024px) {
		.content-container {
			width: min(calc(100% - 48px), 1520px);
		}

		.floating-sidebar {
			width: 280px;
		}
	}

	.sidebar-header {
		padding: 12px 16px;
		display: flex;
		align-items: center;
		gap: 8px;
		background-image: linear-gradient(to bottom, #d1dbed, #b8c6df);
		border-bottom: 1px solid rgba(0,0,0,0.15);
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		padding: 8px 10px;
		border-radius: 8px;
		text-align: left;
		color: #1e3a5f;
		cursor: pointer;
		transition:
			transform var(--motion-duration-fast) var(--motion-ease-standard),
			background-color var(--motion-duration-fast) var(--motion-ease-standard),
			border-color var(--motion-duration-fast) var(--motion-ease-standard),
			box-shadow var(--motion-duration-fast) var(--motion-ease-standard),
			color var(--motion-duration-fast) var(--motion-ease-standard);
		border: 1px solid transparent;
		background: transparent;
	}

	.sidebar-item:hover {
		background-color: rgba(255,255,255,0.5);
	}

	.sidebar-item-active {
		background: linear-gradient(to bottom, #4d90fe, #3b7aed);
		color: white;
		border-color: rgba(0,0,0,0.15);
		box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);
		text-shadow: 0 1px 1px rgba(0,0,0,0.2);
	}

	.sidebar-item-active:hover {
		background: linear-gradient(to bottom, #5a9bff, #4888f5);
	}

	.sidebar-icon {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 6px;
		flex-shrink: 0;
		background: linear-gradient(to bottom, rgba(255,255,255,0.6), rgba(255,255,255,0.3));
		border: 1px solid rgba(0,0,0,0.08);
		color: #3b6cb5;
	}

	.sidebar-icon-active {
		background: linear-gradient(to bottom, rgba(255,255,255,0.3), rgba(255,255,255,0.1));
		border-color: rgba(0,0,0,0.1);
		color: white;
	}
</style>
