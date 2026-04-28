<script lang="ts">
	import { onMount } from 'svelte';
	import { ChevronDown, Search, X } from 'lucide-svelte';

	export type SelectOption = string | { value: string; label: string };

	interface Props {
		value?: string;
		options?: SelectOption[];
		placeholder?: string;
		disabled?: boolean;
		id?: string;
		class?: string;
		style?: string;
		onchange?: (value: string) => void;
	}

	let {
		value = $bindable(''),
		options = [],
		placeholder = 'Select...',
		disabled = false,
		id,
		class: extraClass = '',
		style: extraStyle = '',
		onchange,
	}: Props = $props();

	// Normalize options to {value, label} format
	const normalized = $derived(
		options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o))
	);

	// Label for the currently selected value
	const selectedLabel = $derived(normalized.find((o) => o.value === value)?.label ?? '');

	let open = $state(false);
	let searchQuery = $state('');
	let highlightIndex = $state(-1);
	let triggerEl: HTMLButtonElement | undefined = $state();
	let dropdownEl: HTMLDivElement | undefined = $state();
	let searchEl: HTMLInputElement | undefined = $state();
	let dropdownStyle = $state('');

	const filtered = $derived.by(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return normalized;
		return normalized.filter(
			(o) => o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q)
		);
	});

	function updatePosition() {
		if (!triggerEl) return;
		const r = triggerEl.getBoundingClientRect();
		const dropdownHeight = Math.min(300, filtered.length * 40 + 60);
		const spaceBelow = window.innerHeight - r.bottom;
		const openUp = spaceBelow < dropdownHeight && r.top > dropdownHeight;
		if (openUp) {
			dropdownStyle = `position:fixed;z-index:9999;bottom:${Math.round(window.innerHeight - r.top + 4)}px;left:${Math.round(r.left)}px;width:${Math.round(r.width)}px;`;
		} else {
			dropdownStyle = `position:fixed;z-index:9999;top:${Math.round(r.bottom + 4)}px;left:${Math.round(r.left)}px;width:${Math.round(r.width)}px;`;
		}
	}

	function openDropdown() {
		if (disabled) return;
		searchQuery = '';
		highlightIndex = -1;
		open = true;
		requestAnimationFrame(() => {
			updatePosition();
			searchEl?.focus();
		});
	}

	function closeDropdown() {
		open = false;
		searchQuery = '';
		highlightIndex = -1;
	}

	function selectOption(opt: { value: string; label: string }) {
		value = opt.value;
		onchange?.(opt.value);
		closeDropdown();
		triggerEl?.focus();
	}

	function handleTriggerKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
			e.preventDefault();
			openDropdown();
		}
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				highlightIndex = Math.min(highlightIndex + 1, filtered.length - 1);
				scrollHighlight();
				break;
			case 'ArrowUp':
				e.preventDefault();
				highlightIndex = Math.max(highlightIndex - 1, -1);
				scrollHighlight();
				break;
			case 'Enter':
				e.preventDefault();
				if (highlightIndex >= 0 && filtered[highlightIndex]) {
					selectOption(filtered[highlightIndex]);
				}
				break;
			case 'Escape':
				e.preventDefault();
				closeDropdown();
				triggerEl?.focus();
				break;
			case 'Tab':
				closeDropdown();
				break;
		}
	}

	function scrollHighlight() {
		if (dropdownEl && highlightIndex >= 0) {
			const items = dropdownEl.querySelectorAll('[data-option]');
			(items[highlightIndex] as HTMLElement)?.scrollIntoView({ block: 'nearest' });
		}
	}

	function handleClickOutside(e: MouseEvent) {
		if (!open) return;
		if (triggerEl?.contains(e.target as Node)) return;
		if (dropdownEl?.contains(e.target as Node)) return;
		closeDropdown();
	}

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	onMount(() => {
		const sync = () => {
			if (open) requestAnimationFrame(updatePosition);
		};
		window.addEventListener('resize', sync);
		window.addEventListener('scroll', sync, true);
		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			window.removeEventListener('resize', sync);
			window.removeEventListener('scroll', sync, true);
			document.removeEventListener('mousedown', handleClickOutside);
		};
	});

	$effect(() => {
		if (open) requestAnimationFrame(updatePosition);
	});
</script>

<!-- Trigger -->
<button
	bind:this={triggerEl}
	type="button"
	{id}
	{disabled}
	onclick={openDropdown}
	onkeydown={handleTriggerKeydown}
	class="relative flex w-full items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-left outline-none transition-all
		   {disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:border-blue-300 focus:border-blue-400 focus:ring-2 focus:ring-blue-100'}
		   {open ? 'border-blue-400 ring-2 ring-blue-100' : ''}
		   {extraClass}"
	style="background: rgba(255,255,255,0.96); box-shadow: inset 0 1px 2px rgba(15,23,42,0.04); {extraStyle}"
>
	<span class="flex-1 truncate {selectedLabel ? 'text-slate-800' : 'text-slate-400'}">
		{selectedLabel || placeholder}
	</span>
	<ChevronDown
		class="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-150 {open ? 'rotate-180' : ''}"
	/>
</button>

<!-- Portal dropdown -->
{#if open}
	<div
		bind:this={dropdownEl}
		use:portal
		style="{dropdownStyle} border-radius: 16px; border: 1px solid rgba(148,163,184,0.24); background: white; overflow: hidden; box-shadow: 0 8px 32px rgba(15,23,42,0.14), 0 2px 8px rgba(15,23,42,0.06);"
	>
		<!-- Search -->
		<div
			style="border-bottom: 1px solid rgba(148,163,184,0.16); background: rgba(248,250,252,0.9);"
			class="flex items-center gap-2 px-3 py-2"
		>
			<Search class="h-3.5 w-3.5 shrink-0 text-slate-400" />
			<input
				bind:this={searchEl}
				type="text"
				bind:value={searchQuery}
				onkeydown={handleSearchKeydown}
				placeholder="Search..."
				class="flex-1 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
			/>
			{#if searchQuery}
				<button
					type="button"
					onclick={() => {
						searchQuery = '';
						searchEl?.focus();
					}}
					class="cursor-pointer text-slate-400 hover:text-slate-600"
				>
					<X class="h-3.5 w-3.5" />
				</button>
			{/if}
		</div>

		<!-- Options -->
		<div class="max-h-52 overflow-y-auto">
			{#if filtered.length === 0}
				<div class="px-4 py-3 text-center text-sm text-slate-400">No options found</div>
			{:else}
				{#each filtered as opt, i (opt.value)}
					<button
						type="button"
						data-option
						onmousedown={() => selectOption(opt)}
						class="flex w-full cursor-pointer items-center gap-2 px-4 py-2.5 text-left text-sm transition-colors
							   {opt.value === value
							? 'bg-blue-50 font-semibold text-blue-700'
							: i === highlightIndex
								? 'bg-slate-50 text-slate-800'
								: 'text-slate-700 hover:bg-slate-50'}
							   {i > 0 ? 'border-t' : ''}"
						style={i > 0 ? 'border-top-color: rgba(148,163,184,0.1);' : ''}
					>
						<span class="flex-1 truncate">{opt.label}</span>
						{#if opt.value === value}
							<span class="text-blue-400 text-xs">✓</span>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	</div>
{/if}
