<script lang="ts">
	import { LUCIDE_ICONS } from '$lib/data/lucideIcons';
	import AquaModal from './AquaModal.svelte';
	import { Search, X } from 'lucide-svelte';

	interface Props {
		value?: string;
		onselect: (name: string) => void;
		onclose: () => void;
	}

	let { value = '', onselect, onclose }: Props = $props();

	let query = $state('');
	let hoveredName = $state<string | null>(null);

	const filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!q) return LUCIDE_ICONS;
		return LUCIDE_ICONS.filter(
			(ic) => ic.name.toLowerCase().includes(q) || ic.kebab.includes(q)
		);
	});

	function renderSvg(node: [string, Record<string, string>][]): string {
		return node.map(([tag, attrs]) => {
			const attrStr = Object.entries(attrs)
				.map(([k, v]) => `${k}="${v}"`)
				.join(' ');
			return `<${tag} ${attrStr}/>`;
		}).join('');
	}

	function pick(name: string) {
		onselect(name);
		onclose();
	}
</script>

<AquaModal onclose={onclose} panelClass="sm:max-w-[680px]" contentClass="p-0">
	{#snippet header()}
		<div class="flex flex-1 items-center justify-between gap-3">
			<div>
				<p class="text-[15px] font-black text-slate-900">Icon Picker</p>
				<p class="text-[10px] font-bold uppercase tracking-[0.14em] text-blue-600">
					{filtered.length} of {LUCIDE_ICONS.length} icons
				</p>
			</div>
			{#if value}
				<div class="flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-1.5">
					<span class="text-[10px] font-black uppercase tracking-wide text-blue-600">Selected:</span>
					<span class="text-sm font-black text-blue-900">{value}</span>
				</div>
			{/if}
		</div>
	{/snippet}

	<div class="flex flex-col" style="height: 70vh;">
		<!-- Search bar -->
		<div class="shrink-0 border-b border-slate-200 bg-white px-4 py-3">
			<div class="relative">
				<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
				<input
					autofocus
					bind:value={query}
					placeholder="Search icons... (e.g. heart, arrow, user)"
					class="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-9 text-sm outline-none focus:border-blue-400 focus:bg-white"
				/>
				{#if query}
					<button
						type="button"
						onclick={() => (query = '')}
						class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
					>
						<X class="h-3.5 w-3.5" />
					</button>
				{/if}
			</div>
		</div>

		<!-- Icon grid -->
		<div class="flex-1 overflow-y-auto p-3">
			{#if filtered.length === 0}
				<div class="flex h-40 items-center justify-center text-sm text-slate-400">
					No icons match "{query}"
				</div>
			{:else}
				<div class="grid grid-cols-[repeat(auto-fill,minmax(72px,1fr))] gap-1.5">
					{#each filtered as icon (icon.name)}
						{@const isSelected = value === icon.name}
						{@const isHovered = hoveredName === icon.name}
						<button
							type="button"
							onclick={() => pick(icon.name)}
							onmouseenter={() => (hoveredName = icon.name)}
							onmouseleave={() => (hoveredName = null)}
							class="flex flex-col items-center gap-1.5 rounded-xl border px-1 py-2.5 transition-all"
							style={isSelected
								? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); border-color: transparent; box-shadow: 0 2px 8px rgba(37,99,235,0.35);'
								: isHovered
								? 'background: #eff6ff; border-color: #bfdbfe;'
								: 'background: white; border-color: #e2e8f0;'}
							title={icon.name}
						>
							<!-- Render SVG inline using icon node data -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke={isSelected ? 'white' : '#3b82f6'}
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<!-- svelte-ignore -->
								{@html renderSvg(icon.node)}
							</svg>
							<span
								class="w-full truncate text-center text-[9px] font-semibold leading-tight"
								style={isSelected ? 'color: white;' : 'color: #64748b;'}
							>
								{icon.name}
							</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="shrink-0 border-t border-slate-200 bg-slate-50 px-4 py-3">
			<p class="text-center text-[11px] text-slate-500">
				Click an icon to select. The PascalCase name (e.g. <strong>HeartPulse</strong>) will be saved.
			</p>
		</div>
	</div>
</AquaModal>
