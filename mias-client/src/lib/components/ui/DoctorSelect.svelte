<script lang="ts">
	import { facultyApi, type FacultySearchResult } from '$lib/api/faculty';
	import { Search, X, ChevronDown, Loader2 } from 'lucide-svelte';
	import { onMount } from 'svelte';

	interface Props {
		value?: string;
		placeholder?: string;
		disabled?: boolean;
		onselect?: (faculty: FacultySearchResult) => void;
		onclear?: () => void;
	}

	let {
		value = $bindable(''),
		placeholder = 'Search doctor or surgeon…',
		disabled = false,
		onselect,
		onclear,
	}: Props = $props();

	let query = $state(value);
	let results = $state<FacultySearchResult[]>([]);
	let loading = $state(false);
	let showDropdown = $state(false);
	let highlightIndex = $state(-1);
	let inputEl: HTMLInputElement | undefined = $state();
	let dropdownEl: HTMLDivElement | undefined = $state();
	let dropdownStyle = $state('');
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		query = value;
	});

	function updatePosition() {
		if (!inputEl) return;
		const r = inputEl.getBoundingClientRect();
		dropdownStyle = `top:${Math.round(r.bottom + 4)}px;left:${Math.round(r.left)}px;width:${Math.round(r.width)}px;`;
	}

	async function fetchResults(q: string) {
		loading = true;
		try {
			results = await facultyApi.searchFaculty(q);
		} catch {
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleInput(e: Event) {
		query = (e.target as HTMLInputElement).value;
		highlightIndex = -1;
		if (debounceTimer) clearTimeout(debounceTimer);
		if (query.length === 0) {
			results = [];
			showDropdown = false;
			return;
		}
		showDropdown = true;
		requestAnimationFrame(updatePosition);
		debounceTimer = setTimeout(() => fetchResults(query), 250);
	}

	function handleFocus() {
		if (query.length > 0) {
			showDropdown = true;
			requestAnimationFrame(updatePosition);
			if (results.length === 0) fetchResults(query);
		} else {
			showDropdown = true;
			requestAnimationFrame(updatePosition);
			fetchResults('');
		}
	}

	function handleBlur() {
		setTimeout(() => {
			showDropdown = false;
			highlightIndex = -1;
		}, 200);
	}

	function handleSelect(item: FacultySearchResult) {
		value = item.name;
		query = item.name;
		showDropdown = false;
		highlightIndex = -1;
		onselect?.(item);
	}

	function handleClear() {
		value = '';
		query = '';
		results = [];
		showDropdown = false;
		highlightIndex = -1;
		onclear?.();
		inputEl?.focus();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showDropdown) {
			if (e.key === 'ArrowDown') {
				showDropdown = true;
				requestAnimationFrame(updatePosition);
				fetchResults(query);
			}
			return;
		}
		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				highlightIndex = Math.min(highlightIndex + 1, results.length - 1);
				scrollHighlight();
				break;
			case 'ArrowUp':
				e.preventDefault();
				highlightIndex = Math.max(highlightIndex - 1, 0);
				scrollHighlight();
				break;
			case 'Enter':
				e.preventDefault();
				if (highlightIndex >= 0 && results[highlightIndex]) handleSelect(results[highlightIndex]);
				break;
			case 'Escape':
				showDropdown = false;
				highlightIndex = -1;
				break;
		}
	}

	function scrollHighlight() {
		if (dropdownEl && highlightIndex >= 0) {
			const el = dropdownEl.children[highlightIndex] as HTMLElement;
			el?.scrollIntoView({ block: 'nearest' });
		}
	}

	function portalDropdown(node: HTMLElement) {
		document.body.appendChild(node);
		return { destroy() { node.remove(); } };
	}

	onMount(() => {
		const sync = () => { if (showDropdown) requestAnimationFrame(updatePosition); };
		window.addEventListener('resize', sync);
		window.addEventListener('scroll', sync, true);
		return () => {
			window.removeEventListener('resize', sync);
			window.removeEventListener('scroll', sync, true);
		};
	});

	$effect(() => {
		if (showDropdown) requestAnimationFrame(updatePosition);
	});
</script>

<div class="relative w-full">
	<div class="relative">
		<div class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2">
			{#if loading}
				<Loader2 class="h-4 w-4 animate-spin text-blue-400" />
			{:else}
				<Search class="h-4 w-4 text-slate-400" />
			{/if}
		</div>
		<input
			bind:this={inputEl}
			type="text"
			{placeholder}
			{disabled}
			value={query}
			oninput={handleInput}
			onfocus={handleFocus}
			onblur={handleBlur}
			onkeydown={handleKeydown}
			class="block w-full rounded-xl border border-slate-200 py-2.5 pl-9 pr-8 text-sm text-slate-800
				   focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400
				   disabled:bg-gray-100 disabled:text-gray-400 transition-all"
			style="background: #fafcff;"
			autocomplete="off"
		/>
		{#if query}
			<button
				type="button"
				class="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded-full p-1 hover:bg-gray-100"
				onclick={handleClear}
			>
				<X class="h-3.5 w-3.5 text-slate-400" />
			</button>
		{:else}
			<div class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
				<ChevronDown class="h-3.5 w-3.5 text-slate-300" />
			</div>
		{/if}
	</div>

	{#if showDropdown}
		<div
			use:portalDropdown
			bind:this={dropdownEl}
			class="fixed z-[260] max-h-60 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg"
			style={dropdownStyle}
		>
			{#if loading}
				<div class="flex items-center justify-center gap-2 py-4">
					<div class="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
					<span class="text-sm text-gray-400">Searching…</span>
				</div>
			{:else if results.length === 0}
				<div class="py-3 px-4 text-center text-sm text-gray-400">No doctors found</div>
			{:else}
				{#each results as item, i}
					<button
						type="button"
						class="flex w-full cursor-pointer items-center gap-2 px-4 py-2.5 text-left transition-colors
							   {i === highlightIndex ? 'bg-blue-50' : 'hover:bg-gray-50'}
							   {i > 0 ? 'border-t border-gray-50' : ''}"
						onmousedown={() => handleSelect(item)}
					>
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-slate-800">{item.name}</p>
							{#if item.department}
								<p class="truncate text-xs text-slate-400">{item.department}</p>
							{/if}
						</div>
						{#if item.specialty}
							<span class="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">
								{item.specialty}
							</span>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>
