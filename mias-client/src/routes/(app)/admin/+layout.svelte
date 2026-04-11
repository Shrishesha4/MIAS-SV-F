<script lang="ts">
	import { page } from '$app/state';
	import { cubicOut } from 'svelte/easing';
	import { fade, fly } from 'svelte/transition';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import {
		BarChart3,
		BookOpen,
		BrainCircuit,
		Building2,
		FileText,
		FlaskConical,
		Heart,
		IndianRupee,
		Stethoscope,
		Users,
	} from 'lucide-svelte';

	interface ScaffoldConfig {
		title: string;
		activeNav: string;
		titleIcon: any;
	}

	let { children } = $props();

	const currentPath = $derived(page.url.pathname.replace(/\/+$/, '') || '/admin');
	const contentSlide = { y: 20, duration: 280, opacity: 0.12, easing: cubicOut };

	const scaffoldConfig = $derived.by<ScaffoldConfig>(() => {
		if (currentPath.startsWith('/admin/system')) {
			return { title: 'System Config', activeNav: 'system', titleIcon: BrainCircuit };
		}

		switch (currentPath) {
			case '/admin':
			case '/admin/clinics':
				return { title: 'Hospital Clinics', activeNav: 'clinics', titleIcon: Building2 };
			case '/admin/departments':
				return { title: 'Medical Departments', activeNav: 'departments', titleIcon: Stethoscope };
			case '/admin/users':
				return { title: 'System Administration', activeNav: 'users', titleIcon: Users };
			case '/admin/labs':
				return { title: 'Labs', activeNav: 'labs', titleIcon: FlaskConical };
			case '/admin/charges':
				return { title: 'Charge Master', activeNav: 'charges', titleIcon: IndianRupee };
			case '/admin/programmes':
				return { title: 'System Administration', activeNav: 'programmes', titleIcon: BookOpen };
			case '/admin/forms':
				return { title: 'System Forms', activeNav: 'forms', titleIcon: FileText };
			case '/admin/vital-parameters':
				return { title: 'Vital Parameters', activeNav: 'vital_parameters', titleIcon: Heart };
			case '/admin/analytics':
				return { title: 'System Administration', activeNav: 'analytics', titleIcon: BarChart3 };
			default:
				return { title: 'Hospital Clinics', activeNav: 'clinics', titleIcon: Building2 };
		}
	});
</script>

<AdminScaffold
	title={scaffoldConfig.title}
	titleIcon={scaffoldConfig.titleIcon}
	navItems={adminPageNavItems}
	activeNav={scaffoldConfig.activeNav}
>
	{#key currentPath}
		<div in:fade={{ duration: 180 }} out:fade={{ duration: 130 }}>
			{@render children()}
		</div>
	{/key}
</AdminScaffold>