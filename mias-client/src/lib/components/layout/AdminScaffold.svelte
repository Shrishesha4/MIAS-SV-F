<script lang="ts">
	import { goto } from '$app/navigation';
	import { ArrowLeft, ChevronRight, Shield } from 'lucide-svelte';
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

	const TitleIcon = $derived(titleIcon);
</script>

<div class="pb-2 lg:min-h-screen lg:bg-[linear-gradient(to_bottom,rgba(225,232,244,0.88),rgba(236,241,249,0.94))] lg:pb-6">
	<div class="mx-auto flex max-w-md flex-col gap-3 px-4 pt-3 md:max-w-4xl md:px-6 lg:max-w-[1480px] lg:grid lg:grid-cols-[290px_minmax(0,1fr)] lg:gap-5 lg:px-5 lg:pt-4">
		{#if navItems.length > 0}
			<aside class="hidden lg:block lg:self-start">
				<div
					class="sticky top-4 flex min-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-[28px] border"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.94), rgba(243,247,252,0.97)); box-shadow: 0 12px 30px rgba(97,112,134,0.18), inset 0 1px 0 rgba(255,255,255,0.92); border-color: rgba(134,151,175,0.22);"
				>
					<div class="border-b px-4 py-4" style="border-color: rgba(160,174,196,0.2); background: linear-gradient(to bottom, rgba(206,218,237,0.78), rgba(225,232,244,0.42));">
						<div class="flex items-center gap-3">
							<div
								class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
								style="background: linear-gradient(to bottom, #6eafff, #0d66d0); box-shadow: 0 4px 12px rgba(13,102,208,0.32), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);"
							>
								<Shield class="h-5 w-5 text-white" />
							</div>
							<div class="min-w-0 flex-1">
								<p class="text-base font-bold leading-tight text-slate-900">Admin Panel</p>
								<p class="mt-0.5 text-xs font-medium text-slate-500">Desktop Control Center</p>
							</div>
							<div class="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(74,222,128,0.9)]"></div>
						</div>
					</div>

					<div class="flex-1 px-3 py-3">
						<div class="space-y-2">
							{#each navItems as item (item.id)}
								{@const NavIcon = item.icon}
								{@const isActive = item.id === activeNav}
								<button
									class="flex w-full items-center gap-3 rounded-[18px] px-3 py-3 text-left cursor-pointer transition-all"
									style={isActive
										? 'background: linear-gradient(to bottom, #2a7bf5, #0d66d0); box-shadow: 0 8px 18px rgba(13,102,208,0.28), inset 0 1px 0 rgba(255,255,255,0.3); border: 1px solid rgba(0,0,0,0.14);'
										: 'background: linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(238,243,248,0.96)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.88); border: 1px solid rgba(175,189,208,0.2);'}
									onclick={() => handleNav(item)}
								>
									<div
										class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
										style={isActive
											? 'background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.18);'
											: 'background: linear-gradient(to bottom, rgba(255,255,255,0.82), rgba(229,236,244,0.92)); border: 1px solid rgba(160,174,196,0.18);'}
									>
										<NavIcon class="h-4 w-4 {isActive ? 'text-white' : 'text-slate-500'}" />
									</div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-[13px] font-bold {isActive ? 'text-white' : 'text-slate-800'}">{item.label}</p>
									</div>
									<ChevronRight class="h-4 w-4 shrink-0 {isActive ? 'text-white/80' : 'text-slate-400'}" />
								</button>
							{/each}
						</div>
					</div>
				</div>
			</aside>
		{/if}

		<section class="min-w-0 space-y-4 lg:space-y-5">
			<div
				class="rounded-[20px] border p-4 lg:hidden"
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
					class="overflow-x-auto rounded-[20px] border px-3 py-3 lg:hidden"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.54), rgba(241,245,251,0.7)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.92); border-color: rgba(255,255,255,0.42);"
				>
					<div class="flex min-w-max items-start justify-between gap-3">
						{#each navItems as item (item.id)}
							{@const NavIcon = item.icon}
							{@const isActive = item.id === activeNav}
							<button class="flex min-w-[56px] flex-col items-center gap-1.5 cursor-pointer" onclick={() => handleNav(item)}>
								<div
									class="flex h-10 w-10 items-center justify-center rounded-full transition-all"
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

			<div
				class="hidden items-center justify-between rounded-[24px] border px-5 py-4 lg:flex"
				style="background: linear-gradient(to bottom, rgba(208,219,236,0.82), rgba(227,234,244,0.7)); box-shadow: 0 8px 18px rgba(97,112,134,0.12), inset 0 1px 0 rgba(255,255,255,0.7); border-color: rgba(146,163,186,0.22);"
			>
				<div class="flex min-w-0 items-center gap-3">
					{#if backHref}
						<button
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full cursor-pointer"
							style="background: linear-gradient(to bottom, rgba(255,255,255,0.95), rgba(232,239,247,0.96)); box-shadow: 0 4px 10px rgba(97,112,134,0.14), inset 0 1px 0 rgba(255,255,255,0.9); border: 1px solid rgba(150,166,188,0.2);"
							onclick={() => goto(backHref)}
						>
							<ArrowLeft class="h-4 w-4 text-blue-700" />
						</button>
					{/if}
					<div
						class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full"
						style="background: linear-gradient(to bottom, #6eafff, #0d66d0); box-shadow: 0 4px 12px rgba(13,102,208,0.32), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);"
					>
						<TitleIcon class="h-6 w-6 text-white" />
					</div>
					<div class="min-w-0">
						<h1 class="truncate text-2xl font-bold leading-tight text-slate-900">{title}</h1>
						<p class="mt-0.5 truncate text-sm text-slate-500">{subtitle}</p>
					</div>
				</div>
			</div>

			{#if children}
				<div class="min-w-0">
					{@render children()}
				</div>
			{/if}
		</section>
	</div>
</div>