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
	class="min-h-screen pb-8"
	style="background:
		radial-gradient(circle at top, rgba(255,255,255,0.75), rgba(255,255,255,0) 28%),
		linear-gradient(to bottom, #d9e4f2 0%, #ced9ea 14%, #d8e1ee 40%, #dbe4f0 100%);"
>
	<div
		class="sticky top-0 z-20 border-b px-4 py-3"
		style="background: linear-gradient(to bottom, rgba(205,217,234,0.98), rgba(194,208,228,0.98)); border-color: rgba(120,141,170,0.18); backdrop-filter: blur(10px);"
	>
		<div class="mx-auto flex max-w-md items-center justify-between gap-3 md:max-w-4xl md:px-2">
			<div class="flex items-center gap-3">
				<button
					class="flex h-12 w-12 items-center justify-center rounded-full cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #e5ebf4); box-shadow: 0 3px 8px rgba(84, 106, 138, 0.22), inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(120,141,170,0.18);"
					onclick={() => goto(backHref)}
				>
					<ArrowLeft class="h-5 w-5 text-blue-700" />
				</button>
				<div
					class="flex h-12 w-12 items-center justify-center rounded-full"
					style="background: linear-gradient(to bottom, #5fa0ff, #0d66d0); box-shadow: 0 4px 10px rgba(13,102,208,0.35), inset 0 1px 0 rgba(255,255,255,0.32); border: 1px solid rgba(0,0,0,0.18);"
				>
					<TitleIcon class="h-5 w-5 text-white" />
				</div>
			</div>

			<div class="flex items-center gap-2">
				<button
					class="flex h-12 w-12 items-center justify-center rounded-full cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #e5ebf4); box-shadow: 0 3px 8px rgba(84, 106, 138, 0.22), inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(120,141,170,0.18);"
				>
					<Shield class="h-5 w-5 text-blue-700" />
				</button>
				<button
					class="flex h-12 w-12 items-center justify-center rounded-full cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #e5ebf4); box-shadow: 0 3px 8px rgba(84, 106, 138, 0.22), inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(120,141,170,0.18);"
				>
					<Plus class="h-5 w-5 text-blue-700" />
				</button>
				<button
					class="flex h-12 w-12 items-center justify-center rounded-full cursor-pointer"
					style="background: linear-gradient(to bottom, #ffffff, #e5ebf4); box-shadow: 0 3px 8px rgba(84, 106, 138, 0.22), inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(120,141,170,0.18);"
				>
					<Bell class="h-5 w-5 text-blue-700" />
				</button>
				<button
					class="flex h-12 w-12 items-center justify-center rounded-full cursor-pointer"
					style="background: linear-gradient(to bottom, #5fa0ff, #0d66d0); box-shadow: 0 4px 10px rgba(13,102,208,0.35), inset 0 1px 0 rgba(255,255,255,0.32); border: 2px solid rgba(255,255,255,0.85);"
				>
					<UserRound class="h-5 w-5 text-white" />
				</button>
			</div>
		</div>
	</div>

	<div class="mx-auto flex max-w-md flex-col gap-4 px-4 pt-6 md:max-w-4xl md:px-6">
		<div
			class="rounded-[28px] border p-6"
			style="background: linear-gradient(to bottom, rgba(255,255,255,0.97), rgba(248,250,253,0.96)); box-shadow: 0 6px 18px rgba(97,112,134,0.16), inset 0 1px 0 rgba(255,255,255,0.78); border-color: rgba(134,151,175,0.18);"
		>
			<div class="flex items-center gap-4">
				<div
					class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full"
					style="background: linear-gradient(to bottom, #6eafff, #0d66d0); box-shadow: 0 6px 16px rgba(13,102,208,0.34), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);"
				>
					<TitleIcon class="h-8 w-8 text-white" />
				</div>
				<div class="min-w-0">
					<h1 class="text-[2rem] font-bold leading-tight text-slate-900">{title}</h1>
					<p class="mt-1 text-base text-slate-500">{subtitle}</p>
				</div>
			</div>
		</div>

		{#if navItems.length > 0}
			<div
				class="overflow-x-auto rounded-[28px] border px-4 py-5"
				style="background: linear-gradient(to bottom, rgba(255,255,255,0.54), rgba(241,245,251,0.7)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.92); border-color: rgba(255,255,255,0.42);"
			>
				<div class="flex min-w-max items-start justify-between gap-5">
					{#each navItems as item (item.id)}
						{@const NavIcon = item.icon}
						{@const isActive = item.id === activeNav}
						<button class="flex min-w-[64px] flex-col items-center gap-2 cursor-pointer" onclick={() => handleNav(item)}>
							<div
								class="flex h-12 w-12 items-center justify-center rounded-full transition-all"
								style={isActive
									? 'background: linear-gradient(to bottom, #5fa0ff, #0d66d0); box-shadow: 0 4px 10px rgba(13,102,208,0.35), inset 0 1px 0 rgba(255,255,255,0.34); border: 1px solid rgba(0,0,0,0.16);'
									: 'background: linear-gradient(to bottom, rgba(255,255,255,0.76), rgba(235,240,246,0.95)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.8); border: 1px solid rgba(134,151,175,0.16);'}
							>
								<NavIcon class="h-5 w-5 {isActive ? 'text-white' : 'text-slate-400'}" />
							</div>
							<span class="text-[11px] font-bold uppercase tracking-wide {isActive ? 'text-blue-700' : 'text-slate-400'}">{item.label}</span>
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