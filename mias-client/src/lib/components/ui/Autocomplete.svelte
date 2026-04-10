<script lang="ts">
	import { Search, X, ChevronDown } from 'lucide-svelte';

	interface Props {
		placeholder?: string;
		value?: string;
		items?: any[];
		labelKey?: string;
		sublabelKey?: string;
		badgeKey?: string;
		onInput?: (query: string) => void;
		onSelect?: (item: any) => void;
		onClear?: () => void;
		loading?: boolean;
		disabled?: boolean;
		minChars?: number;
	}

	let {
		placeholder = 'Search...',
		value = $bindable(''),
		items = [],
		labelKey = 'name',
		sublabelKey = '',
		badgeKey = '',
		onInput,
		onSelect,
		onClear,
		loading = false,
		disabled = false,
		minChars = 1,
	}: Props = $props();

	let showDropdown = $state(false);
	let inputEl: HTMLInputElement | undefined = $state();
	let highlightIndex = $state(-1);
	let dropdownEl: HTMLDivElement | undefined = $state();

	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		value = target.value;
		highlightIndex = -1;
		if (value.length >= minChars) {
			showDropdown = true;
			onInput?.(value);
		} else {
			showDropdown = false;
		}
	}

	function handleSelect(item: any) {
		value = typeof item === 'string' ? item : item[labelKey];
		showDropdown = false;
		highlightIndex = -1;
		onSelect?.(item);
	}

	function handleClear() {
		value = '';
		showDropdown = false;
		highlightIndex = -1;
		onClear?.();
		inputEl?.focus();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!showDropdown || items.length === 0) {
			if (e.key === 'ArrowDown' && value.length >= minChars) {
				showDropdown = true;
				onInput?.(value);
			}
			return;
		}

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				highlightIndex = Math.min(highlightIndex + 1, items.length - 1);
				scrollIntoView();
				break;
			case 'ArrowUp':
				e.preventDefault();
				highlightIndex = Math.max(highlightIndex - 1, 0);
				scrollIntoView();
				break;
			case 'Enter':
				e.preventDefault();
				if (highlightIndex >= 0 && highlightIndex < items.length) {
					handleSelect(items[highlightIndex]);
				}
				break;
			case 'Escape':
				showDropdown = false;
				highlightIndex = -1;
				break;
		}
	}

	function scrollIntoView() {
		if (dropdownEl && highlightIndex >= 0) {
			const el = dropdownEl.children[highlightIndex] as HTMLElement;
			if (el) {
				el.scrollIntoView({ block: 'nearest' });
			}
		}
	}

	function handleFocus() {
		if (value.length >= minChars && items.length > 0) {
			showDropdown = true;
		}
	}

	function handleBlur() {
		// Delay to allow click on dropdown items
		setTimeout(() => {
			showDropdown = false;
			highlightIndex = -1;
		}, 200);
	}

	function getLabel(item: any): string {
		if (typeof item === 'string') return item;
		return item[labelKey] || '';
	}

	function getSublabel(item: any): string {
		if (!sublabelKey || typeof item === 'string') return '';
		return item[sublabelKey] || '';
	}

	function getBadge(item: any): string {
		if (!badgeKey || typeof item === 'string') return '';
		return item[badgeKey] || '';
	}
</script>

<div class="relative w-full">
	<div class="relative">
		<div class="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
			<Search class="w-4 h-4 text-gray-400" />
		</div>
		<input
			bind:this={inputEl}
			type="text"
			{placeholder}
			{value}
			{disabled}
			oninput={handleInput}
			onkeydown={handleKeydown}
			onfocus={handleFocus}
			onblur={handleBlur}
			class="w-full pl-9 pr-8 py-2.5 rounded-xl text-sm border border-gray-200 bg-white
				   focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400
				   disabled:bg-gray-100 disabled:text-gray-400 transition-all"
			autocomplete="off"
		/>
		{#if value}
			<button
				class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-gray-100 cursor-pointer"
				onclick={handleClear}
				type="button"
			>
				<X class="w-3.5 h-3.5 text-gray-400" />
			</button>
		{:else}
			<div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
				<ChevronDown class="w-3.5 h-3.5 text-gray-300" />
			</div>
		{/if}
	</div>

	{#if showDropdown}
		<div
			bind:this={dropdownEl}
			class="absolute left-0 right-0 top-full z-[220] mt-1 max-h-60 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg"
		>
			{#if loading}
				<div class="flex items-center justify-center py-4">
					<div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
					<span class="ml-2 text-sm text-gray-500">Searching...</span>
				</div>
			{:else if items.length === 0}
				<div class="py-3 px-4 text-sm text-gray-400 text-center">
					No results found
				</div>
			{:else}
				{#each items as item, index}
					<button
						class="w-full text-left px-4 py-2.5 flex items-center gap-2 cursor-pointer transition-colors
							   {index === highlightIndex ? 'bg-blue-50' : 'hover:bg-gray-50'}
							   {index > 0 ? 'border-t border-gray-50' : ''}"
						onmousedown={() => handleSelect(item)}
						type="button"
					>
						<div class="flex-1 min-w-0">
							<p class="text-sm font-medium text-gray-800 truncate">
								{getLabel(item)}
							</p>
							{#if getSublabel(item)}
								<p class="text-xs text-gray-500 truncate">{getSublabel(item)}</p>
							{/if}
						</div>
						{#if getBadge(item)}
							<span class="shrink-0 px-2 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 text-gray-600">
								{getBadge(item)}
							</span>
						{/if}
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>
