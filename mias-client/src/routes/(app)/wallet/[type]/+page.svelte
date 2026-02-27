<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import { walletApi } from '$lib/api/wallet';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { Wallet, ArrowUp, ArrowDown, CreditCard, Filter } from 'lucide-svelte';

	// Determine wallet type from URL
	const walletType = $derived(
		page.url.pathname.includes('pharmacy') ? 'PHARMACY' : 'HOSPITAL'
	);

	let allTransactions: any[] = $state([]);
	let walletBalance: any = $state(null);
	let loading = $state(true);

	const transactions = $derived(
		allTransactions.filter(t => t.wallet_type === walletType)
	);

	const totalCredit = $derived(
		walletBalance?.total_credits ?? transactions.filter(t => t.type === 'CREDIT').reduce((sum: number, t: any) => sum + t.amount, 0)
	);

	const totalDebit = $derived(
		walletBalance?.total_debits ?? transactions.filter(t => t.type === 'DEBIT').reduce((sum: number, t: any) => sum + t.amount, 0)
	);

	const balance = $derived(walletBalance?.balance ?? (totalCredit - totalDebit));

	let filterType = $state<'ALL' | 'CREDIT' | 'DEBIT'>('ALL');

	const filteredTransactions = $derived(
		filterType === 'ALL' ? transactions : transactions.filter(t => t.type === filterType)
	);

	onMount(async () => {
		try {
			const patient = await patientApi.getCurrentPatient();
			const wt = walletType === 'PHARMACY' ? 'pharmacy' : 'hospital';
			const [txns, bal] = await Promise.all([
				patientApi.getWalletTransactions(patient.id, wt as 'hospital' | 'pharmacy'),
				walletApi.getBalance(patient.id, wt as 'hospital' | 'pharmacy'),
			]);
			allTransactions = txns;
			walletBalance = bal;
		} catch (err) {
			console.error('Failed to load wallet data', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	<!-- Balance Card -->
	<AquaCard>
		<div class="text-center py-2">
			<Wallet class="w-8 h-8 mx-auto mb-2 text-blue-600" />
			<p class="text-sm text-gray-500">{walletType === 'HOSPITAL' ? 'Hospital' : 'Pharmacy'} Wallet Balance</p>
			<p class="text-3xl font-bold text-blue-900 mt-1">
				₹{Math.abs(balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
			</p>
			<div class="flex justify-center gap-6 mt-3">
				<div class="text-center">
					<div class="flex items-center gap-1 text-green-600">
						<ArrowDown class="w-4 h-4" />
						<span class="text-sm font-medium">Credits</span>
					</div>
					<p class="text-sm font-bold text-green-700">₹{totalCredit.toLocaleString('en-IN')}</p>
				</div>
				<div class="text-center">
					<div class="flex items-center gap-1 text-red-600">
						<ArrowUp class="w-4 h-4" />
						<span class="text-sm font-medium">Debits</span>
					</div>
					<p class="text-sm font-bold text-red-700">₹{totalDebit.toLocaleString('en-IN')}</p>
				</div>
			</div>
		</div>
	</AquaCard>

	<!-- Filter -->
	<div class="flex gap-2">
		{#each (['ALL', 'CREDIT', 'DEBIT'] as const) as type}
			<button
				class="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg cursor-pointer transition-all"
				style={filterType === type
					? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; border: 1px solid rgba(0,0,0,0.2);'
					: 'background: linear-gradient(to bottom, #f0f4fa, #d5dde8); color: #1e40af; border: 1px solid rgba(0,0,0,0.2);'}
				onclick={() => filterType = type}
			>
				{type === 'ALL' ? 'All' : type === 'CREDIT' ? 'Credits' : 'Debits'}
			</button>
		{/each}
	</div>

	<!-- Transactions List -->
	<AquaCard>
		{#snippet header()}
			<CreditCard class="w-4 h-4 text-blue-600 mr-2" />
			<span class="text-blue-900 font-semibold text-sm">Transactions</span>
		{/snippet}
		<div class="space-y-0 -mx-4 -mb-4">
			{#each filteredTransactions as txn}
				<div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 last:border-0">
					<div class="flex items-center gap-3">
						<div
							class="w-8 h-8 rounded-full flex items-center justify-center"
							style={txn.type === 'CREDIT'
								? 'background: linear-gradient(to bottom, #4ade80, #22c55e);'
								: 'background: linear-gradient(to bottom, #f87171, #dc2626);'}
						>
							{#if txn.type === 'CREDIT'}
								<ArrowDown class="w-4 h-4 text-white" />
							{:else}
								<ArrowUp class="w-4 h-4 text-white" />
							{/if}
						</div>
						<div>
							<p class="text-sm font-medium text-gray-800">{txn.description}</p>
							<p class="text-xs text-gray-500">
								{new Date(txn.date).toLocaleDateString('en-IN', {
									day: 'numeric', month: 'short',
								})} · {txn.time}
								{#if txn.department}
									· {txn.department}
								{/if}
							</p>
						</div>
					</div>
					<span class="text-sm font-bold {txn.type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}">
						{txn.type === 'CREDIT' ? '+' : '-'}₹{txn.amount.toLocaleString('en-IN')}
					</span>
				</div>
			{/each}

			{#if filteredTransactions.length === 0}
				<div class="px-4 py-8 text-center text-gray-400 text-sm">
					No transactions found
				</div>
			{/if}
		</div>
	</AquaCard>
	{/if}
</div>
