<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import { walletApi } from '$lib/api/wallet';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import {
		Wallet, ArrowUp, ArrowDown, CreditCard, ChevronDown, ChevronUp,
		Plus, Building, FileText, Clock, X
	} from 'lucide-svelte';

	const walletType = $derived(
		page.url.pathname.includes('pharmacy') ? 'PHARMACY' : 'HOSPITAL'
	);

	let allTransactions: any[] = $state([]);
	let walletBalance: any = $state(null);
	let loading = $state(true);
	let expandedTxnId = $state<string | null>(null);
	let filterType = $state<'ALL' | 'CREDIT' | 'DEBIT'>('ALL');

	const transactions = $derived(
		allTransactions.filter(t => t.wallet_type === walletType)
	);

	const totalCredit = $derived(
		walletBalance?.total_credits ?? transactions.filter(t => t.type === 'CREDIT').reduce((sum: number, t: any) => sum + Number(t.amount), 0)
	);

	const totalDebit = $derived(
		walletBalance?.total_debits ?? transactions.filter(t => t.type === 'DEBIT').reduce((sum: number, t: any) => sum + Number(t.amount), 0)
	);

	const balance = $derived(walletBalance?.balance ?? (totalCredit - totalDebit));

	const filteredTransactions = $derived(
		filterType === 'ALL' ? transactions : transactions.filter(t => t.type === filterType)
	);

	onMount(async () => {
		if (!redirectIfUnauthorized(['PATIENT'])) return;
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
			toastStore.addToast('Failed to load wallet data', 'error');
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-3 py-4 md:px-6 md:py-6 space-y-3">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Balance Card (Blue Gradient) -->
		<div class="px-4 py-4 rounded-xl text-white"
			style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
				   box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.3);
				   border: 1px solid rgba(0,0,0,0.2);">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="w-10 h-10 rounded-full flex items-center justify-center"
						style="background: rgba(255,255,255,0.2); border: 1px solid rgba(0,0,0,0.1);
							   box-shadow: inset 0 1px 0 rgba(255,255,255,0.3);">
						<Wallet class="w-5 h-5 text-white" />
					</div>
					<div>
						<p class="text-xs text-blue-100">Available Balance</p>
						<p class="text-xl font-bold">₹{Math.abs(balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
					</div>
				</div>
				<div class="px-2.5 py-1.5 rounded-lg"
					style="background: rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.3);">
					<span class="text-sm font-medium text-white">
						SMC-{walletType === 'HOSPITAL' ? 'General' : 'Pharma'}
					</span>
				</div>
			</div>
			<div class="flex gap-4 mt-4 pt-3" style="border-top: 1px solid rgba(255,255,255,0.2);">
				<div class="flex items-center gap-1.5">
					<div class="w-6 h-6 rounded-full flex items-center justify-center"
						style="background: rgba(74,222,128,0.3);">
						<ArrowDown class="w-3.5 h-3.5 text-green-200" />
					</div>
					<div>
						<p class="text-[10px] text-blue-200">Credits</p>
						<p class="text-sm font-semibold">₹{totalCredit.toLocaleString('en-IN')}</p>
					</div>
				</div>
				<div class="flex items-center gap-1.5">
					<div class="w-6 h-6 rounded-full flex items-center justify-center"
						style="background: rgba(248,113,113,0.3);">
						<ArrowUp class="w-3.5 h-3.5 text-red-200" />
					</div>
					<div>
						<p class="text-[10px] text-blue-200">Debits</p>
						<p class="text-sm font-semibold">₹{totalDebit.toLocaleString('en-IN')}</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Filter Buttons -->
		<div class="flex gap-2">
			{#each (['ALL', 'CREDIT', 'DEBIT'] as const) as type}
				<button
					class="flex-1 px-3 py-2 text-xs font-medium rounded-lg cursor-pointer transition-all"
					style="background: {filterType === type ? 'linear-gradient(to bottom, #4d90fe, #0066cc)' : 'linear-gradient(to bottom, #ffffff, #f5f5f5)'};
						   color: {filterType === type ? 'white' : '#374151'};
						   border: 1px solid {filterType === type ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.12)'};
						   box-shadow: 0 1px 2px rgba(0,0,0,{filterType === type ? '0.15' : '0.06'});"
					onclick={() => filterType = type}
				>
					{type === 'ALL' ? 'All' : type === 'CREDIT' ? 'Credits' : 'Debits'}
				</button>
			{/each}
		</div>

		<!-- Transaction History -->
		<div class="overflow-hidden"
			style="background-color: white; border-radius: 10px;
				   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				   border: 1px solid rgba(0,0,0,0.1);">
			<div class="p-3 flex items-center gap-2"
				style="background: linear-gradient(to bottom, #f8f9fa, #edf0f5);
					   border-bottom: 1px solid rgba(0,0,0,0.06);">
				<CreditCard class="w-4 h-4 text-blue-700" />
				<div>
					<h2 class="font-semibold text-gray-800 text-sm">Transaction History</h2>
					<p class="text-[10px] text-gray-500">{walletType === 'HOSPITAL' ? 'Hospital' : 'Pharmacy'} Wallet</p>
				</div>
			</div>

			<div class="divide-y" style="border-color: rgba(0,0,0,0.06);">
				{#each filteredTransactions as txn}
					<div>
						<!-- Transaction Row -->
						<button
							class="w-full p-3 flex items-center justify-between cursor-pointer text-left transition-colors"
							style="background: {expandedTxnId === txn.id ? 'linear-gradient(to bottom, #e8f0ff, #d8e6ff)' : 'linear-gradient(to bottom, #ffffff, #f8f9fa)'};"
							onclick={() => expandedTxnId = expandedTxnId === txn.id ? null : txn.id}
						>
							<div class="flex items-center gap-3">
								<div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
									style="background: {txn.type === 'CREDIT' ? 'linear-gradient(to bottom, #4ade80, #22c55e)' : 'linear-gradient(to bottom, #f87171, #ef4444)'};
										   box-shadow: 0 1px 2px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.1);">
									{#if txn.type === 'CREDIT'}
										<Plus class="w-4 h-4 text-white" />
									{:else}
										<ArrowUp class="w-4 h-4 text-white" />
									{/if}
								</div>
								<div>
									<p class="text-sm font-medium text-gray-800">{txn.description}</p>
									<p class="text-xs text-gray-500">
										{new Date(txn.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
									</p>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-sm font-bold {txn.type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}">
									{txn.type === 'CREDIT' ? '+' : '-'}₹{Number(txn.amount).toLocaleString('en-IN')}
								</span>
								<div class="w-5 h-5 rounded-full flex items-center justify-center"
									style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
										   border: 1px solid rgba(0,0,0,0.1);">
									{#if expandedTxnId === txn.id}
										<ChevronUp class="w-3 h-3 text-blue-700" />
									{:else}
										<ChevronDown class="w-3 h-3 text-blue-700" />
									{/if}
								</div>
							</div>
						</button>

						<!-- Expanded Invoice/Receipt -->
						{#if expandedTxnId === txn.id}
							<div class="p-4 space-y-3" style="background-color: #f9fafb; border-top: 1px solid rgba(0,0,0,0.06);">
								<div class="flex items-center justify-between">
									<h3 class="font-semibold text-gray-800 text-sm">Transaction Receipt</h3>
									<button
										class="w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
										style="background: linear-gradient(to bottom, #fee2e2, #fecaca);
											   border: 1px solid rgba(0,0,0,0.1);"
										onclick={() => expandedTxnId = null}
									>
										<X class="w-3 h-3 text-red-600" />
									</button>
								</div>

								<!-- Invoice Card -->
								<div class="rounded-lg overflow-hidden" style="border: 1px solid rgba(0,0,0,0.1);">
									<!-- Invoice Header -->
									<div class="p-3 text-white"
										style="background: linear-gradient(to bottom, #2563eb, #1d4ed8);">
										<div class="flex justify-between items-start">
											<div>
												<p class="text-sm font-bold">Saveetha Medical College</p>
												<p class="text-[10px] text-blue-200">Chennai 600077</p>
											</div>
											<div class="text-right">
												<p class="text-xs font-semibold">{txn.type === 'DEBIT' ? 'INVOICE' : 'RECEIPT'}</p>
												{#if txn.invoice_number}
													<p class="text-[10px] text-blue-200">#{txn.invoice_number}</p>
												{/if}
											</div>
										</div>
									</div>

									<!-- Service Info -->
									<div class="p-3 space-y-2 text-xs" style="background-color: #f9fafb; border-bottom: 1px solid rgba(0,0,0,0.06);">
										{#if txn.department}
											<div class="flex items-center gap-2 text-gray-600">
												<Building class="w-3 h-3 text-gray-400" />
												<span>Department: {txn.department}</span>
											</div>
										{/if}
										{#if txn.payment_method}
											<div class="flex items-center gap-2 text-gray-600">
												<CreditCard class="w-3 h-3 text-gray-400" />
												<span>Payment: {txn.payment_method}</span>
											</div>
										{/if}
										{#if txn.reference_number}
											<div class="flex items-center gap-2 text-gray-600">
												<FileText class="w-3 h-3 text-gray-400" />
												<span>Ref: {txn.reference_number}</span>
											</div>
										{/if}
										{#if txn.provider}
											<div class="flex items-center gap-2 text-gray-600">
												<Clock class="w-3 h-3 text-gray-400" />
												<span>Provider: {txn.provider}</span>
											</div>
										{/if}
									</div>

									<!-- Line Items -->
									{#if txn.items && txn.items.length > 0}
										<div class="p-3" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
											<p class="text-xs font-semibold text-gray-700 mb-2">Details</p>
											<div class="space-y-1">
												{#each txn.items as item}
													<div class="flex items-center justify-between text-xs py-1.5 px-2 rounded"
														style="background-color: rgba(0,0,0,0.02);">
														<div class="flex-1 min-w-0">
															<span class="text-gray-700">{item.description}</span>
															{#if item.quantity > 1}
																<span class="text-gray-400 ml-1">×{item.quantity}</span>
															{/if}
														</div>
														<span class="font-medium text-gray-800 ml-2">₹{Number(item.total).toLocaleString('en-IN')}</span>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Summary -->
									<div class="p-3 space-y-1" style="background-color: #f9fafb;">
										{#if txn.subtotal != null}
											<div class="flex justify-between text-xs">
												<span class="text-gray-500">Subtotal</span>
												<span class="font-medium text-gray-700">₹{Number(txn.subtotal).toLocaleString('en-IN')}</span>
											</div>
										{/if}
										{#if txn.tax != null && Number(txn.tax) > 0}
											<div class="flex justify-between text-xs">
												<span class="text-gray-500">Tax</span>
												<span class="font-medium text-gray-700">₹{Number(txn.tax).toLocaleString('en-IN')}</span>
											</div>
										{/if}
										{#if txn.insurance_coverage != null && Number(txn.insurance_coverage) > 0}
											<div class="flex justify-between text-xs">
												<span class="text-gray-500">Insurance Coverage</span>
												<span class="font-medium text-green-600">-₹{Number(txn.insurance_coverage).toLocaleString('en-IN')}</span>
											</div>
										{/if}
										<div class="flex justify-between text-sm pt-1" style="border-top: 1px solid rgba(0,0,0,0.08);">
											<span class="font-semibold text-gray-700">Total</span>
											<span class="font-bold {txn.type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}">
												{txn.type === 'CREDIT' ? '+' : '-'}₹{Number(txn.amount).toLocaleString('en-IN')}
											</span>
										</div>
									</div>

									<!-- Insurance Info -->
									{#if txn.insurance_provider}
										<div class="p-3 text-xs" style="border-top: 1px solid rgba(0,0,0,0.06);">
											<p class="font-semibold text-gray-700 mb-1">Insurance</p>
											<div class="grid grid-cols-2 gap-1 text-gray-600">
												<span>Provider: {txn.insurance_provider}</span>
												{#if txn.policy_number}<span>Policy: {txn.policy_number}</span>{/if}
												{#if txn.claim_number}<span>Claim: {txn.claim_number}</span>{/if}
											</div>
										</div>
									{/if}

									<!-- Notes -->
									{#if txn.notes}
										<div class="p-3 text-xs" style="border-top: 1px solid rgba(0,0,0,0.06);">
											<p class="font-semibold text-gray-700 mb-0.5">Notes</p>
											<p class="text-gray-600 italic">{txn.notes}</p>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{/each}

				{#if filteredTransactions.length === 0}
					<div class="text-center py-10">
						<div class="w-14 h-14 mx-auto rounded-full flex items-center justify-center mb-3"
							style="background-color: #f3f4f6;">
							<Wallet class="w-6 h-6 text-gray-400" />
						</div>
						<p class="text-sm font-medium text-gray-800 mb-0.5">No transactions</p>
						<p class="text-xs text-gray-500">No {filterType !== 'ALL' ? filterType.toLowerCase() : ''} transactions found.</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
