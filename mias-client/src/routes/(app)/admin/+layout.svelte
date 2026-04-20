<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { cubicOut } from 'svelte/easing';
	import { fly } from 'svelte/transition';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import {
		BarChart3,
		BookOpen,
		BrainCircuit,
		Building2,
		Cpu,
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
	// Freeze key for system sub-routes so the system sub-layout handles those transitions
	const transitionKey = $derived(
		currentPath.startsWith('/admin/system') ? '/admin/system' :
		currentPath.startsWith('/admin/ot') ? '/admin/ot' : currentPath
	);

	const scaffoldConfig = $derived.by<ScaffoldConfig>(() => {
		if (currentPath.startsWith('/admin/system')) {
			return { title: 'System Config', activeNav: 'system', titleIcon: BrainCircuit };
		}
		if (currentPath.startsWith('/admin/ot')) {
			return { title: 'Operation Theaters', activeNav: 'ot', titleIcon: Cpu };
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

	// Custom exit transition: pull element out of normal flow so incoming content
	// doesn't push it down (which causes the "stutter from center" double-height issue)
	function pageExit(node: HTMLElement) {
		node.style.position = 'absolute';
		node.style.inset = '0';
		node.style.zIndex = '0';
		node.style.pointerEvents = 'none';
		node.style.overflow = 'hidden';
		return {
			duration: 140,
			css: (t: number) => `opacity: ${t * 0.3};`
		};
	}

	onMount(() => {
		document.body.classList.add('admin-layout-active');
		return () => document.body.classList.remove('admin-layout-active');
	});
</script>

<AdminScaffold
	title={scaffoldConfig.title}
	titleIcon={scaffoldConfig.titleIcon}
	navItems={adminPageNavItems}
	activeNav={scaffoldConfig.activeNav}
>
	{#key transitionKey}
		<div
			class="admin-page-root"
			in:fly={{ x: 16, duration: 260, easing: cubicOut, opacity: 0 }}
			out:pageExit
		>
			{@render children()}
		</div>
	{/key}
</AdminScaffold>

<style>
	.admin-page-root {
		position: relative;
		width: 100%;
		min-height: 100%;
	}

	@media (min-width: 768px) {
		:global(body.admin-layout-active .floating-sidebar),
		:global(body.admin-layout-active .sidebar-backdrop) {
			display: none !important;
		}
	}

	@media (min-width: 1024px) {
		:global(body.admin-layout-active) {
			overflow: hidden;
			height: 100dvh;
		}
	}
</style>