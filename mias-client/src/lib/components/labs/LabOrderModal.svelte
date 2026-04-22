<script lang="ts">
	import { onMount } from 'svelte';
	import { FlaskConical, Search, X, CheckCircle2, Layers } from 'lucide-svelte';
	import { labsApi, type LabInfo, type LabTest, type LabTestGroup, type ChargeItem } from '$lib/api/labs';
	import { walletApi } from '$lib/api/wallet';
	import { chargesApi } from '$lib/api/labs';
	import { toastStore } from '$lib/stores/toast';

	interface Props {
		patientId: string;
		patientCategory?: string;
		onclose: () => void;
		onordered?: () => void;
	}

	let { patientId, patientCategory = '', onclose, onordered }: Props = $props();

	// ── State ──────────────────────────────────────────────
	let labs: LabInfo[] = $state([]);
	let selectedLabId: string = $state('');
	let tests: LabTest[] = $state([]);
	let groups: LabTestGroup[] = $state([]);
	let charges: ChargeItem[] = $state([]);
	let walletBalance: number = $state(0);
	let loading = $state(true);
	let placing = $state(false);
	let tab: 'tests' | 'groups' = $state('tests');
	let search = $state('');
	let clinicalNotes = $state('');
	let selectedTestIds = $state(new Set<string>());
	let selectedGroupIds = $state(new Set<string>());

	// ── Derived ────────────────────────────────────────────
	const catKey = $derived((patientCategory || '').toLowerCase().trim());

	function priceFor(sourceId: string): number {
		const ci = charges.find((c) => c.source_id === sourceId);
		if (!ci) return 0;
		// match by patient category (case-insensitive)
		for (const [k, v] of Object.entries(ci.prices)) {
			if (k.toLowerCase().trim() === catKey && v != null) return v;
		}
		// fallback: first price
		const vals = Object.values(ci.prices).filter((v) => v != null && v > 0);
		return vals.length ? (vals[0] as number) : 0;
	}

	const filteredTests = $derived(
		tests.filter((t) => t.is_active && (!search || t.name.toLowerCase().includes(search.toLowerCase()) || t.category.toLowerCase().includes(search.toLowerCase())))
	);

	const filteredGroups = $derived(
		groups.filter((g) => g.is_active && (!search || g.name.toLowerCase().includes(search.toLowerCase())))
	);

	const total = $derived.by(() => {
		let sum = 0;
		for (const id of selectedTestIds) sum += priceFor(id);
		for (const id of selectedGroupIds) sum += priceFor(id);
		return sum;
	});

	const remaining = $derived(walletBalance - total);
	const selectedCount = $derived(selectedTestIds.size + selectedGroupIds.size);

	// ── Load ───────────────────────────────────────────────
	onMount(async () => {
		try {
			const [allLabs, walletData] = await Promise.all([
				labsApi.getAll(),
				walletApi.getBalance(patientId, 'hospital').catch(() => ({ balance: 0 })),
			]);
			labs = allLabs.filter((l) => l.is_active);
			walletBalance = walletData.balance ?? 0;
			if (labs.length > 0) {
				selectedLabId = labs[0].id;
				await loadLabContent(selectedLabId);
			}
		} catch {
			toastStore.addToast('Failed to load lab data', 'error');
		} finally {
			loading = false;
		}
	});

	async function loadLabContent(labId: string) {
		loading = true;
		selectedTestIds = new Set();
		selectedGroupIds = new Set();
		try {
			const [t, g, ch] = await Promise.all([
				labsApi.getTests(labId),
				labsApi.getGroups(labId),
				chargesApi.getAll('LABS'),
			]);
			tests = t;
			groups = g;
			charges = ch;
		} catch {
			toastStore.addToast('Failed to load lab tests', 'error');
		} finally {
			loading = false;
		}
	}

	async function onLabChange(id: string) {
		selectedLabId = id;
		search = '';
		await loadLabContent(id);
	}

	function toggleTest(id: string) {
		const next = new Set(selectedTestIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedTestIds = next;
	}

	function toggleGroup(id: string) {
		const next = new Set(selectedGroupIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedGroupIds = next;
	}

	async function placeOrder() {
		if (selectedCount === 0) return;
		if (remaining < 0) {
			toastStore.addToast('Insufficient wallet balance', 'error');
			return;
		}
		placing = true;
		try {
			const result = await labsApi.placeOrder({
				patient_id: patientId,
				lab_id: selectedLabId,
				test_ids: [...selectedTestIds],
				group_ids: [...selectedGroupIds],
				clinical_notes: clinicalNotes || undefined,
			});
			toastStore.addToast(result.message, 'success');
			onordered?.();
			onclose();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to place order', 'error');
		} finally {
			placing = false;
		}
	}
</script>

<!-- Backdrop -->
<div
	class="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-0 sm:p-4"
	style="background: rgba(0,0,0,0.5);"
	role="dialog"
	aria-modal="true"
	tabindex="-1"
	onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}
	onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}
>
	<!-- Sheet -->
	<div
		class="relative flex flex-col w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl overflow-hidden"
		style="background: #f0f4ff; max-height: 92dvh; box-shadow: 0 -4px 40px rgba(0,0,0,0.22);"
	>
		<!-- Header -->
		<div class="flex items-center gap-3 px-5 pt-5 pb-4" style="background: white; border-bottom: 1px solid #e5eaf5;">
			<div class="flex items-center justify-center w-11 h-11 rounded-full shrink-0"
				style="background: linear-gradient(135deg, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(37,99,235,0.35);">
				<FlaskConical class="w-5 h-5 text-white" />
			</div>
			<div class="flex-1 min-w-0">
				<p class="text-base font-bold text-slate-900 leading-tight">Order Investigations</p>
				<p class="text-[11px] font-semibold tracking-widest text-blue-500 uppercase">Laboratory Services</p>
			</div>
			<button onclick={onclose} class="flex items-center justify-center w-8 h-8 rounded-full cursor-pointer transition-colors hover:bg-slate-100">
				<X class="w-4 h-4 text-slate-500" />
			</button>
		</div>

		<!-- Wallet Bar -->
		<div class="flex items-center justify-between px-5 py-3"
			style="background: linear-gradient(to right, #eff6ff, #dbeafe); border-bottom: 1px solid #bfdbfe;">
			<div>
				<p class="text-[10px] font-bold uppercase tracking-widest text-blue-600">Available Balance</p>
				<p class="text-xl font-black text-blue-900">₹ {walletBalance.toLocaleString('en-IN')}</p>
			</div>
			<div class="text-right">
				<p class="text-[10px] font-bold uppercase tracking-widest text-slate-500">Remaining</p>
				<p class="text-xl font-black {remaining < 0 ? 'text-red-600' : 'text-emerald-600'}">
					₹ {remaining.toLocaleString('en-IN')}
				</p>
			</div>
		</div>

		<!-- Lab selector (if multiple labs) -->
		{#if labs.length > 1}
		<div class="px-4 pt-3 pb-1">
			<select
				value={selectedLabId}
				onchange={(e) => onLabChange((e.target as HTMLSelectElement).value)}
				class="w-full px-3 py-2 text-sm font-medium text-slate-800 rounded-xl border border-slate-200 cursor-pointer"
				style="background: white;"
			>
				{#each labs as lab (lab.id)}
					<option value={lab.id}>{lab.name}</option>
				{/each}
			</select>
		</div>
		{/if}

		<!-- Search -->
		<div class="px-4 pt-3 pb-2">
			<div class="relative">
				<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
				<input
					type="text"
					placeholder={tab === 'tests' ? 'Search investigations...' : 'Search test groups...'}
					bind:value={search}
					class="w-full pl-9 pr-4 py-2.5 text-sm text-slate-800 rounded-xl border border-slate-200"
					style="background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.06);"
				/>
			</div>
		</div>

		<!-- Tabs -->
		<div class="flex items-center gap-2 px-4 pb-2">
			<button
				onclick={() => { tab = 'tests'; search = ''; }}
				class="flex items-center gap-1.5 flex-1 justify-center py-2 rounded-xl text-xs font-bold uppercase tracking-wide cursor-pointer transition-all"
				style={tab === 'tests'
					? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 2px 6px rgba(37,99,235,0.3);'
					: 'background: white; color: #64748b; border: 1px solid #e2e8f0;'}
			>
				<FlaskConical class="w-3.5 h-3.5" /> Individual Tests
			</button>
			<button
				onclick={() => { tab = 'groups'; search = ''; }}
				class="flex items-center gap-1.5 flex-1 justify-center py-2 rounded-xl text-xs font-bold uppercase tracking-wide cursor-pointer transition-all"
				style={tab === 'groups'
					? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 2px 6px rgba(37,99,235,0.3);'
					: 'background: white; color: #64748b; border: 1px solid #e2e8f0;'}
			>
				<Layers class="w-3.5 h-3.5" /> Test Groups
			</button>
		</div>

		<!-- List -->
		<div class="flex-1 overflow-y-auto px-4 pb-2 space-y-2">
			{#if loading}
				<div class="flex items-center justify-center py-16">
					<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if tab === 'tests'}
				{#if filteredTests.length === 0}
					<p class="py-10 text-center text-sm text-slate-400">No tests found</p>
				{:else}
					{#each filteredTests as test (test.id)}
						{@const selected = selectedTestIds.has(test.id)}
						{@const price = priceFor(test.id)}
						<button
							onclick={() => toggleTest(test.id)}
							class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer text-left"
							style={selected
								? 'background: white; border: 2px solid #2563eb; box-shadow: 0 2px 8px rgba(37,99,235,0.12);'
								: 'background: white; border: 1px solid #e2e8f0;'}
						>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold truncate {selected ? 'text-blue-700' : 'text-slate-900'}">{test.name}</p>
								<p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">{test.category}</p>
							</div>
							{#if price > 0}
								<p class="text-sm font-bold shrink-0 {selected ? 'text-blue-600' : 'text-slate-700'}">₹ {price.toLocaleString('en-IN')}</p>
							{/if}
							<div class="flex items-center justify-center w-5 h-5 rounded border-2 shrink-0 transition-all"
								style={selected ? 'background: #2563eb; border-color: #2563eb;' : 'border-color: #cbd5e1;'}>
								{#if selected}
									<svg class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
										<path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
									</svg>
								{/if}
							</div>
						</button>
					{/each}
				{/if}
			{:else}
				{#if filteredGroups.length === 0}
					<p class="py-10 text-center text-sm text-slate-400">No test groups found</p>
				{:else}
					{#each filteredGroups as group (group.id)}
						{@const selected = selectedGroupIds.has(group.id)}
						{@const price = priceFor(group.id)}
						<button
							onclick={() => toggleGroup(group.id)}
							class="w-full flex items-start gap-3 px-4 py-3 rounded-xl transition-all cursor-pointer text-left"
							style={selected
								? 'background: white; border: 2px solid #2563eb; box-shadow: 0 2px 8px rgba(37,99,235,0.12);'
								: 'background: white; border: 1px solid #e2e8f0;'}
						>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-semibold {selected ? 'text-blue-700' : 'text-slate-900'}">{group.name}</p>
								{#if group.description}
									<p class="text-xs text-slate-400 mt-0.5">{group.description}</p>
								{/if}
								{#if group.tests.length > 0}
									<div class="flex flex-wrap gap-1 mt-1.5">
										{#each group.tests as t}
											<span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide"
												style="background: #f1f5f9; color: #475569;">{t.code}</span>
										{/each}
									</div>
								{/if}
							</div>
							{#if price > 0}
								<p class="text-sm font-bold shrink-0 {selected ? 'text-blue-600' : 'text-slate-700'}">₹ {price.toLocaleString('en-IN')}</p>
							{/if}
							<div class="flex items-center justify-center w-5 h-5 rounded border-2 shrink-0 mt-0.5 transition-all"
								style={selected ? 'background: #2563eb; border-color: #2563eb;' : 'border-color: #cbd5e1;'}>
								{#if selected}
									<svg class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
										<path d="M2 6l3 3 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
									</svg>
								{/if}
							</div>
						</button>
					{/each}
				{/if}
			{/if}
		</div>

		<!-- Clinical Notes (compact, collapsed by default) -->
		{#if selectedCount > 0}
		<div class="px-4 pb-2">
			<textarea
				bind:value={clinicalNotes}
				placeholder="Clinical notes / indications (optional)..."
				rows={2}
				class="w-full px-3 py-2 text-xs text-slate-700 rounded-xl border border-slate-200 resize-none"
				style="background: white;"
			></textarea>
		</div>
		{/if}

		<!-- Footer -->
		<div class="px-4 pb-5 pt-2" style="background: white; border-top: 1px solid #e5eaf5;">
			<div class="flex items-center justify-between mb-3">
				<p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
					{selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
				</p>
				<p class="text-sm font-black text-slate-900">
					Total: ₹ {total.toLocaleString('en-IN')}
				</p>
			</div>
			<div class="flex gap-2">
				<button
					onclick={onclose}
					class="flex-1 py-3 rounded-xl text-sm font-bold uppercase tracking-wide cursor-pointer transition-all hover:opacity-80"
					style="background: #f1f5f9; color: #64748b;"
					disabled={placing}
				>
					Cancel
				</button>
				<button
					onclick={placeOrder}
					disabled={selectedCount === 0 || remaining < 0 || placing}
					class="flex-1 py-3 rounded-xl text-sm font-bold uppercase tracking-wide cursor-pointer transition-all disabled:opacity-40"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 2px 8px rgba(37,99,235,0.3);"
				>
					{placing ? 'Placing...' : 'Place Order'}
				</button>
			</div>
		</div>
	</div>
</div>
