<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import NavBar from '$lib/components/layout/NavBar.svelte';
	import SideMenu from '$lib/components/layout/SideMenu.svelte';
	import { page } from '$app/state';

	let { children } = $props();
	let sideMenuOpen = $state(false);

	let authState = $state(get(authStore));
	authStore.subscribe(v => authState = v);

	let userName = $state('User');
	let userIdDisplay = $state('');
	let unreadNotifications = $state(0);

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
				unreadNotifications = notifs.filter((n: any) => !n.is_read).length;
			} else if (a.role === 'STUDENT') {
				const student = await studentApi.getMe();
				userName = student.name;
				userIdDisplay = student.student_id;
				const notifs = await studentApi.getNotifications(student.id);
				unreadNotifications = notifs.filter((n: any) => !n.is_read).length;
			} else if (a.role === 'FACULTY') {
				const faculty = await facultyApi.getMe();
				userName = faculty.name;
				userIdDisplay = faculty.faculty_id;
				const notifs = await facultyApi.getNotifications(faculty.id);
				unreadNotifications = notifs.filter((n: any) => !n.is_read).length;
			} else if (a.role === 'ADMIN') {
				userName = 'Administrator';
				userIdDisplay = 'ADMIN';
				// Redirect to admin panel if on generic dashboard
				if (window.location.pathname === '/dashboard') {
					goto('/admin');
				}
			}
		} catch {
			// If API fails, use defaults
		}
	});
</script>

<div class="flex flex-col min-h-screen">
	<NavBar
		showBack={(page.url.pathname as string) !== '/dashboard'}
		notificationCount={unreadNotifications}
		onmenuclick={() => sideMenuOpen = true}
	/>

	<main class="flex-1 pb-4">
		{@render children()}
	</main>

	<SideMenu
		bind:open={sideMenuOpen}
		onclose={() => sideMenuOpen = false}
		{userName}
		userRole={authState.role ?? ''}
		userId={userIdDisplay}
	/>
</div>
