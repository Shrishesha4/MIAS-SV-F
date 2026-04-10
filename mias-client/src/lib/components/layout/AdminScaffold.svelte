<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { ArrowLeft, Bell, ChevronRight, HeartPulse, Plus, Shield, ShieldCheck, UserRound } from 'lucide-svelte';
	import { cubicOut, quintOut } from 'svelte/easing';
	import { fade, fly } from 'svelte/transition';
	import type { Snippet } from 'svelte';

	type NavItem = {
		id: string;
		label: string;
		icon: any;
		href?: string;
		onclick?: () => void;
	};

	interface Props {
		title: string;
		subtitle?: string;
		backHref?: string;
		titleIcon?: any;
		navItems?: NavItem[];
		activeNav?: string;
		children?: Snippet;
	}

	let {
		title,
		subtitle = 'Root Access • Saveetha Medical College',
		backHref = '/admin',
		titleIcon = Shield,
		navItems = [],
		activeNav = '',
		children
	}: Props = $props();

	function handleNav(item: NavItem) {
		if (item.onclick) {
			item.onclick();
			return;
		}

		if (item.href) {
			goto(item.href);
		}
	}

	function logout() {
		authStore.logout();
		goto('/login');
	}

	const TitleIcon = $derived(titleIcon);
	const contentSlide = { y: 24, duration: 360, opacity: 0.12, easing: quintOut };
</script>

<div class="pb-2 lg:min-h-screen lg:bg-[linear-gradient(to_bottom,#d9e3f0_0%,#d4dfec_38%,#ccd8e7_100%)] lg:pb-6">
	<div class="mx-auto flex max-w-md flex-col gap-3 px-4 pt-3 md:max-w-4xl md:px-6 lg:min-h-[calc(100vh-2rem)] lg:max-w-[1370px] lg:grid lg:grid-cols-[255px_minmax(0,1fr)] lg:gap-3 lg:px-5 lg:pt-4">
		{#if navItems.length > 0}
			<aside class="hidden lg:block lg:self-start">
				<div
					class="admin-shell sticky top-4 flex h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-[16px] border"
					style="background: linear-gradient(to bottom, rgba(250,252,255,0.96), rgba(242,247,252,0.94)); box-shadow: 0 10px 24px rgba(95,113,136,0.16), inset 0 1px 0 rgba(255,255,255,0.94); border-color: rgba(132,150,175,0.2);"
				>
					<div class="border-b px-4 py-3.5" style="border-color: rgba(160,174,196,0.18); background: linear-gradient(to bottom, rgba(220,229,241,0.85), rgba(236,241,249,0.55));">
						<div class="flex items-center gap-3">
							<div
								class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #287cff, #005fd8); box-shadow: 0 4px 10px rgba(20,95,210,0.25), inset 0 1px 0 rgba(255,255,255,0.3); border: 1px solid rgba(255,255,255,0.55);"
							>
								<Shield class="h-5 w-5 text-white" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="text-base font-bold leading-tight text-slate-900">Admin Panel</p>
							</div>
						</div>
					</div>
					<div class="flex-1 overflow-y-auto overflow-x-hidden bg-white/55">
						<div class="divide-y" style="border-color: rgba(190,200,214,0.42);">
							{#each navItems as item (item.id)}
								{@const NavIcon = item.icon}
								{@const isActive = item.id === activeNav}
								<button
									class="admin-nav-item motion-list-item flex w-full items-center gap-3 px-4 py-4 text-left cursor-pointer transition-all"
									style={isActive
										? 'background: linear-gradient(to bottom, #1a78f5, #005fda); box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);'
										: 'background: linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(246,249,252,0.98));'}
									onclick={() => handleNav(item)}
								>
									<div
										class="admin-nav-icon flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
										style={isActive
											? 'background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.14);'
											: 'background: linear-gradient(to bottom, #1d7cf6, #005fd7); box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);'}
									>
										<NavIcon class="h-4 w-4 {isActive ? 'text-white' : 'text-white'}" />
									</div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-[14px] font-bold {isActive ? 'text-white' : 'text-slate-900'}">{item.label}</p>
									</div>
									<ChevronRight class="h-4 w-4 shrink-0 {isActive ? 'text-white/85' : 'text-slate-400'}" />
								</button>
							{/each}
						</div>
					</div>

					<div class="px-4 py-4" style="background: linear-gradient(to bottom, rgba(255,255,255,0.78), rgba(246,248,252,0.92)); border-top: 1px solid rgba(190,200,214,0.42);">
						<button
							class="admin-signout flex w-full items-center justify-center rounded-[10px] px-4 py-3 text-sm font-bold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #ff6e68, #ff2946); box-shadow: inset 0 1px 0 rgba(255,255,255,0.32), 0 4px 10px rgba(255,41,70,0.24);"
							onclick={logout}
						>
							Sign Out
						</button>
					</div>
				</div>
			</aside>
		{/if}

		<section class="min-w-0 space-y-4 lg:space-y-0">
			<div
				class="admin-mobile-shell rounded-[20px] border p-4 lg:hidden"
				style="background: linear-gradient(to bottom, rgba(255,255,255,0.97), rgba(248,250,253,0.96)); box-shadow: 0 4px 12px rgba(97,112,134,0.14), inset 0 1px 0 rgba(255,255,255,0.78); border-color: rgba(134,151,175,0.18);"
			>
				<div class="flex items-center gap-3">
					<div
						class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
						style="background: linear-gradient(to bottom, #6eafff, #0d66d0); box-shadow: 0 4px 12px rgba(13,102,208,0.32), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);"
					>
						<TitleIcon class="h-6 w-6 text-white" />
					</div>
					<div class="min-w-0">
						<h1 class="text-2xl font-bold leading-tight text-slate-900">{title}</h1>
						<p class="mt-0.5 text-sm text-slate-500">{subtitle}</p>
					</div>
				</div>
			</div>

			{#if navItems.length > 0}
				<div
					class="admin-mobile-shell overflow-x-auto rounded-[20px] border px-3 py-3 lg:hidden"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.54), rgba(241,245,251,0.7)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.92); border-color: rgba(255,255,255,0.42);"
				>
					<div class="flex min-w-max items-start justify-between gap-3">
						{#each navItems as item (item.id)}
							{@const NavIcon = item.icon}
							{@const isActive = item.id === activeNav}
							<button class="admin-mobile-nav-item motion-control flex min-w-[56px] flex-col items-center gap-1.5 cursor-pointer" onclick={() => handleNav(item)}>
								<div
									class="motion-control flex h-10 w-10 items-center justify-center rounded-full transition-all"
									style={isActive
										? 'background: linear-gradient(to bottom, #5fa0ff, #0d66d0); box-shadow: 0 3px 8px rgba(13,102,208,0.35), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);'
										: 'background: linear-gradient(to bottom, rgba(255,255,255,0.76), rgba(235,240,246,0.95)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(134,151,175,0.16);'}
								>
									<NavIcon class="h-4 w-4 {isActive ? 'text-white' : 'text-slate-400'}" />
								</div>
								<span class="text-[10px] font-bold uppercase tracking-wide {isActive ? 'text-blue-700' : 'text-slate-400'}">{item.label}</span>
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<div class="admin-content-shell hidden min-h-[calc(100vh-2rem)] overflow-hidden rounded-[18px] border lg:flex lg:flex-col" style="border-color: rgba(132,150,175,0.2); background: linear-gradient(to bottom, rgba(235,241,248,0.88), rgba(221,230,240,0.92)); box-shadow: 0 10px 24px rgba(95,113,136,0.12), inset 0 1px 0 rgba(255,255,255,0.84);" in:fade={{ duration: 180 }} out:fade={{ duration: 130 }}>
				{#if children}
					<div class="admin-content-panel min-w-0 flex-1 px-6 py-5" style="background-image: linear-gradient(to bottom, rgba(238,243,248,0.72), rgba(219,228,238,0.78)), repeating-linear-gradient(180deg, rgba(255,255,255,0.1) 0, rgba(255,255,255,0.1) 1px, transparent 1px, transparent 4px);">
						{@render children()}
					</div>
				{/if}
			</div>

			{#if children}
				<div class="admin-content-panel min-w-0 lg:hidden" in:fly={{ y: 18, duration: 300, delay: 90, opacity: 0.14, easing: quintOut }} out:fade={{ duration: 120 }}>
					{@render children()}
				</div>
			{/if}
		</section>
	</div>
</div>

<style>
	.admin-shell,
	.admin-mobile-shell {
		will-change: transform, opacity;
	}

	.admin-content-shell,
	.admin-content-panel {
		will-change: opacity;
	}

	.admin-nav-item,
	.admin-mobile-nav-item,
	.admin-signout {
		transition:
			transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
			box-shadow 220ms ease,
			filter 220ms ease,
			opacity 180ms ease;
	}

	.admin-nav-icon {
		transition:
			transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
			box-shadow 220ms ease;
	}

	@media (hover: hover) and (pointer: fine) {
		.admin-nav-item:hover {
			transform: translateY(-2px);
			filter: saturate(1.03);
		}

		.admin-nav-item:hover .admin-nav-icon {
			transform: translateY(-1px);
		}

		.admin-mobile-nav-item:hover {
			transform: translateY(-2px);
		}

		.admin-signout:hover {
			transform: translateY(-1px);
			box-shadow: inset 0 1px 0 rgba(255,255,255,0.32), 0 8px 16px rgba(255,41,70,0.28);
		}
	}
</style>