<script lang="ts">
	import type { Snippet } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { X } from 'lucide-svelte';

	interface Props {
		open: boolean;
		title?: string;
		onclose: () => void;
		header?: Snippet;
		children: Snippet;
	}

	let { open, title = '', onclose, header, children }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-[200] flex"
		onkeydown={handleKeydown}
		transition:fade={{ duration: 150 }}
	>
		<!-- Backdrop -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="absolute inset-0"
			style="background: rgba(15,23,42,0.18); backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px);"
			onclick={onclose}
		></div>

		<!-- Panel -->
		<div
			class="ml-auto relative w-full max-w-lg h-full flex flex-col"
			style="background: #ffffff; box-shadow: -8px 0 32px rgba(0,0,0,0.12);"
			in:fly={{ x: 320, duration: 280, easing: cubicOut }}
			out:fly={{ x: 320, duration: 200 }}
		>
			<!-- Header -->
			<div
				class="px-5 py-4 flex items-center justify-between shrink-0"
				style="background: linear-gradient(to bottom, #f8f9fb, #f1f5f9);
					border-bottom: 1px solid rgba(0,0,0,0.08);"
			>
				{#if header}
					<div class="flex-1 min-w-0">
						{@render header()}
					</div>
				{:else if title}
					<h2 class="text-base font-semibold text-slate-800 truncate">{title}</h2>
				{:else}
					<div></div>
				{/if}
				<button
					class="ml-3 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
					onclick={onclose}
				>
					<X size={20} />
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto">
				{@render children()}
			</div>
		</div>
	</div>
{/if}

<style>
	@media (prefers-reduced-motion: reduce) {
		:global(.side-sheet-panel) {
			transition: none !important;
		}
	}
</style>
