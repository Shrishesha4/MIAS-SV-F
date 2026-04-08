<script lang="ts">
	import { goto } from '$app/navigation';
	import { ArrowLeft, Bell, Plus, Shield, UserRound } from 'lucide-svelte';
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

<div
	class="pb-2"
	style=""
>
	<div
	class="sticky top-0 z-20 px-4 py-0"
	style="">
	</div>

	<div class="mx-auto flex max-w-md flex-col gap-3 px-4 pt-3 md:max-w-4xl md:px-6">
		<div
			class="rounded-[20px] border p-4"
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
				class="overflow-x-auto rounded-[20px] border px-3 py-3"
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

		{#if children}
			{@render children()}
		{/if}
	</div>
</div>