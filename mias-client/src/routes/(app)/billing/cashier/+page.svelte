<script lang="ts">
	import { onMount } from 'svelte';

	import { billingApi, type BillingProfile } from '$lib/api/billing';
	import { walletApi } from '$lib/api/wallet';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaSelect from '$lib/components/ui/AquaSelect.svelte';
	import {
		Search, User, ChevronRight, Plus, ArrowUp, ArrowDown,
		CreditCard, BarChart3, Building2, Pill
	} from 'lucide-svelte';

	// ── State ─────────────────────────────────────────────────────────
	let profile = $state<BillingProfile | null>(null);
	let activeTab = $state<'CASHIER' | 'REPORTS'>('CASHIER');

	let searchQuery = $state('');
	let searchResults = $state<any[]>([]);
	let searchLoading = $state(false);
	let searchDebounce: ReturnType<typeof setTimeout> | null = null;

	let selectedPatient = $state<any | null>(null);
	let walletSummary = $state<any | null>(null);
	let walletLoading = $state(false);

	// Topup modal
	let topupOpen = $state(false);
	let topupWalletType = $state<'HOSPITAL' | 'PHARMACY'>('HOSPITAL');
	let topupAmount = $state('');
	let topupMethod = $state('Cash');
	let topupRef = $state('');
	let topupNote = $state('');
	let topupLoading = $state(false);

	const paymentMethods = ['Cash', 'UPI', 'Card', 'Net Banking', 'Cheque'];

	// ── Lifecycle ─────────────────────────────────────────────────────
	onMount(async () => {
		if (!redirectIfUnauthorized(['BILLING'])) return;
		try {
			profile = await billingApi.getMe();
		} catch {
			toastStore.addToast('Failed to load billing profile', 'error');
		}
	});

	// ── Search ────────────────────────────────────────────────────────
	function handleSearchInput() {
		if (searchDebounce) clearTimeout(searchDebounce);
		if (!searchQuery.trim()) {
			searchResults = [];
			return;
		}
		searchDebounce = setTimeout(async () => {
			searchLoading = true;
			try {
				searchResults = await walletApi.searchPatients(searchQuery);
			} catch {
				searchResults = [];
			} finally {
				searchLoading = false;
			}
		}, 300);
	}

	async function selectPatient(p: any) {
		selectedPatient = p;
		walletLoading = true;
		walletSummary = null;
		try {
			walletSummary = await walletApi.getPatientSummary(p.id);
		} catch {
			toastStore.addToast('Failed to load wallet data', 'error');
		} finally {
			walletLoading = false;
		}
	}

	// ── Topup ─────────────────────────────────────────────────────────
	function openTopup(wt: 'HOSPITAL' | 'PHARMACY') {
		topupWalletType = wt;
		topupAmount = '';
		topupMethod = 'Cash';
		topupRef = '';
		topupNote = '';
		topupOpen = true;
	}

	async function submitTopup() {
		const amt = parseFloat(topupAmount);
		if (!amt || amt <= 0) {
			toastStore.addToast('Enter valid amount', 'error');
			return;
		}
		topupLoading = true;
		try {
			const res = await walletApi.topup({
				patient_id: selectedPatient.id,
				wallet_type: topupWalletType,
				amount: amt,
				payment_method: topupMethod,
				reference_id: topupRef,
				description: topupNote || `Top-up by ${profile?.name ?? 'Billing'} at ${profile?.counter_name ?? 'Counter'}`,
			});
			toastStore.addToast(`₹${amt} added to ${topupWalletType} wallet`, 'success');
			topupOpen = false;
			// Refresh wallet
			walletSummary = await walletApi.getPatientSummary(selectedPatient.id);
		} catch {
			toastStore.addToast('Top-up failed', 'error');
		} finally {
			topupLoading = false;
		}
	}

	function fmt(n: number) {
		return '₹' + Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2 });
	}
</script>

<div class="min-h-screen" >

	<!-- Header Bar -->
	<div class="px-4 py-3 flex items-center justify-between">
		<div>
			<h1 class="text-xl font-bold text-gray-900">Cashier</h1>
		</div>
		<div class="flex items-center gap-2">
			<button
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold cursor-pointer transition-all"
				class:text-white={activeTab === 'CASHIER'}
				style={activeTab === 'CASHIER'
					? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(37,99,235,0.4); border: 1px solid rgba(0,0,0,0.2);'
					: 'background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.12); color: #374151;'}
				onclick={() => activeTab = 'CASHIER'}
			>
				<CreditCard class="w-3.5 h-3.5" />
				<span>Cashier</span>
			</button>
			<button
				class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold cursor-pointer transition-all"
				class:text-white={activeTab === 'REPORTS'}
				style={activeTab === 'REPORTS'
					? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(37,99,235,0.4); border: 1px solid rgba(0,0,0,0.2);'
					: 'background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.12); color: #374151;'}
				onclick={() => activeTab = 'REPORTS'}
			>
				<BarChart3 class="w-3.5 h-3.5" />
				<span>Reports</span>
			</button>
		</div>
	</div>

	{#if activeTab === 'CASHIER'}
		<!-- Cashier Layout: left panel + right panel -->
		<div class="flex gap-3 p-4 pt-0 h-[calc(100vh-72px)]">

			<!-- Left: Patient Search Panel -->
			<div class="w-72 shrink-0 rounded-xl overflow-hidden flex flex-col"
				style="background: white; border: 1px solid rgba(0,0,0,0.12);
				       box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
				<!-- Panel header -->
				<div class="px-4 py-3" style="border-bottom: 1px solid rgba(0,0,0,0.08);">
					<p class="text-[11px] font-bold uppercase tracking-widest text-gray-500">Patient Search</p>
				</div>
				<!-- Search input -->
				<div class="px-3 py-2.5" style="border-bottom: 1px solid rgba(0,0,0,0.06);">
					<div class="relative">
						<Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
						<input
							type="text"
							placeholder="Name, ID, Phone..."
							bind:value={searchQuery}
							oninput={handleSearchInput}
							class="w-full pl-9 pr-3 py-2 rounded-lg text-sm outline-none"
							style="background: #f3f4f6; border: 1px solid rgba(0,0,0,0.1); box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
						/>
					</div>
				</div>
				<!-- Results -->
				<div class="flex-1 overflow-y-auto">
					{#if searchLoading}
						<div class="flex justify-center py-6">
							<div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
						</div>
					{:else if searchResults.length === 0 && searchQuery}
						<p class="text-xs text-gray-400 text-center py-6">No patients found</p>
					{:else if searchResults.length === 0}
						<p class="text-xs text-gray-400 text-center py-6">Search by name, ID or phone</p>
					{:else}
						{#each searchResults as p}
							<button
								class="w-full flex items-center gap-3 px-4 py-3 text-left cursor-pointer transition-colors"
								class:bg-blue-50={selectedPatient?.id === p.id}
								style={selectedPatient?.id === p.id ? 'border-left: 3px solid #3b82f6;' : 'border-bottom: 1px solid rgba(0,0,0,0.05);'}
								onclick={() => selectPatient(p)}
							>
								<Avatar name={p.name} size="sm" src={p.photo} />
								<div class="flex-1 min-w-0">
									<p class="text-sm font-semibold text-gray-900 truncate">{p.name}</p>
									<p class="text-xs text-gray-500">{p.patient_id}</p>
								</div>
								<ChevronRight class="w-4 h-4 text-gray-400 shrink-0" />
							</button>
						{/each}
					{/if}
				</div>
			</div>

			<!-- Right: Wallet Panel -->
			<div class="flex-1 rounded-xl overflow-hidden"
				style="background: white; border: 1px solid rgba(0,0,0,0.12);
				       box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
				{#if !selectedPatient}
					<!-- Empty state -->
					<div class="flex flex-col items-center justify-center h-full text-center px-8">
						<div class="w-20 h-20 rounded-full flex items-center justify-center mb-4"
							style="background: #f3f4f6;">
							<User class="w-10 h-10 text-gray-300" />
						</div>
						<h3 class="text-lg font-semibold text-gray-400">Select a Patient</h3>
						<p class="text-sm text-gray-400 mt-1">Search and select a patient from the left panel to manage their wallet.</p>
					</div>
				{:else if walletLoading}
					<div class="flex justify-center items-center h-full">
						<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
					</div>
				{:else if walletSummary}
					<div class="p-5 space-y-4 h-full overflow-y-auto">
						<!-- Patient header -->
						<div class="flex items-center gap-3 pb-4" style="border-bottom: 1px solid rgba(0,0,0,0.08);">
							<Avatar name={selectedPatient.name} size="md" src={selectedPatient.photo} />
							<div>
								<h2 class="text-base font-bold text-gray-900">{selectedPatient.name}</h2>
								<p class="text-sm text-gray-500">{selectedPatient.patient_id} · {selectedPatient.phone}</p>
							</div>
						</div>

						<!-- Wallet Cards -->
						<div class="grid grid-cols-2 gap-3">
							<!-- Hospital Wallet -->
							<div class="rounded-xl p-4 text-white relative overflow-hidden"
								style="background: linear-gradient(135deg, #2563eb, #1d4ed8);
								       box-shadow: 0 2px 8px rgba(37,99,235,0.35);">
								<div class="flex items-center gap-2 mb-3">
									<Building2 class="w-4 h-4 opacity-80" />
									<span class="text-xs font-semibold opacity-80 uppercase tracking-wide">Hospital Wallet</span>
								</div>
								<p class="text-2xl font-bold">{fmt(walletSummary.hospital.balance)}</p>
								<div class="flex gap-3 mt-2 text-xs opacity-70">
									<span>↑ {fmt(walletSummary.hospital.total_credits)}</span>
									<span>↓ {fmt(walletSummary.hospital.total_debits)}</span>
								</div>
								<button
									class="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all"
									style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);"
									onclick={() => openTopup('HOSPITAL')}
								>
									<Plus class="w-3.5 h-3.5" />
									Add Funds
								</button>
							</div>

							<!-- Pharmacy Wallet -->
							<div class="rounded-xl p-4 text-white relative overflow-hidden"
								style="background: linear-gradient(135deg, #16a34a, #15803d);
								       box-shadow: 0 2px 8px rgba(22,163,74,0.35);">
								<div class="flex items-center gap-2 mb-3">
									<Pill class="w-4 h-4 opacity-80" />
									<span class="text-xs font-semibold opacity-80 uppercase tracking-wide">Pharmacy Wallet</span>
								</div>
								<p class="text-2xl font-bold">{fmt(walletSummary.pharmacy.balance)}</p>
								<div class="flex gap-3 mt-2 text-xs opacity-70">
									<span>↑ {fmt(walletSummary.pharmacy.total_credits)}</span>
									<span>↓ {fmt(walletSummary.pharmacy.total_debits)}</span>
								</div>
								<button
									class="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all"
									style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3);"
									onclick={() => openTopup('PHARMACY')}
								>
									<Plus class="w-3.5 h-3.5" />
									Add Funds
								</button>
							</div>
						</div>

						<!-- Transaction History -->
						<div>
							<p class="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">Recent Transactions</p>
							{#if walletSummary.transactions.length === 0}
								<p class="text-sm text-gray-400 text-center py-6">No transactions yet</p>
							{:else}
								<div class="space-y-1.5">
									{#each walletSummary.transactions.slice(0, 20) as txn}
										<div class="flex items-center gap-3 px-3 py-2.5 rounded-lg"
											style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.06);">
											<div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
												style={txn.type === 'CREDIT'
													? 'background: #dcfce7; color: #16a34a;'
													: 'background: #fee2e2; color: #dc2626;'}>
												{#if txn.type === 'CREDIT'}
													<ArrowDown class="w-4 h-4" />
												{:else}
													<ArrowUp class="w-4 h-4" />
												{/if}
											</div>
											<div class="flex-1 min-w-0">
												<p class="text-sm font-medium text-gray-800 truncate">{txn.description}</p>
												<p class="text-xs text-gray-500">
													{txn.wallet_type} · {new Date(txn.date).toLocaleDateString('en-IN')}
													{#if txn.payment_method} · {txn.payment_method}{/if}
												</p>
											</div>
											<span class="text-sm font-bold shrink-0"
												style={txn.type === 'CREDIT' ? 'color: #16a34a;' : 'color: #dc2626;'}>
												{txn.type === 'CREDIT' ? '+' : '-'}{fmt(txn.amount)}
											</span>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<!-- Reports Tab (placeholder) -->
		<div class="flex flex-col items-center justify-center h-[calc(100vh-72px)] text-center">
			<BarChart3 class="w-14 h-14 text-gray-300 mb-3" />
			<h3 class="text-lg font-semibold text-gray-400">Reports Coming Soon</h3>
			<p class="text-sm text-gray-400 mt-1">Transaction reports and cash summaries will appear here.</p>
		</div>
	{/if}
</div>

<!-- Topup Modal -->
{#if topupOpen}
	<AquaModal title="Add Funds — {topupWalletType === 'HOSPITAL' ? 'Hospital' : 'Pharmacy'} Wallet" onclose={() => topupOpen = false}>
		<div class="p-5 space-y-4">
			{#if selectedPatient}
				<div class="flex items-center gap-3 px-3 py-2.5 rounded-xl"
					style="background: #eff6ff; border: 1px solid #bfdbfe;">
					<Avatar name={selectedPatient.name} size="sm" src={selectedPatient.photo} />
					<div>
						<p class="text-sm font-semibold text-gray-900">{selectedPatient.name}</p>
						<p class="text-xs text-gray-500">{selectedPatient.patient_id}</p>
					</div>
				</div>
			{/if}

			<div>
				<label for="billing-amount" class="block text-xs font-semibold text-gray-700 mb-1.5">Amount (₹)</label>
				<input
					id="billing-amount"
					type="number"
					placeholder="0.00"
					bind:value={topupAmount}
					min="1"
					step="0.01"
					class="w-full px-4 py-3 rounded-xl text-sm outline-none"
					style="background: white; border: 1px solid rgba(0,0,0,0.15); box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>

			<div>
				<label for="billing-method" class="block text-xs font-semibold text-gray-700 mb-1.5">Payment Method</label>
				<AquaSelect
					id="billing-method"
					bind:value={topupMethod}
					options={paymentMethods}
				/>
			</div>

			<div>
				<label for="billing-ref" class="block text-xs font-semibold text-gray-700 mb-1.5">Reference / Receipt No. (optional)</label>
				<input
					id="billing-ref"
					type="text"
					placeholder="e.g. UPI ref, receipt number"
					bind:value={topupRef}
					class="w-full px-4 py-3 rounded-xl text-sm outline-none"
					style="background: white; border: 1px solid rgba(0,0,0,0.15); box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>

			<div>
				<label for="billing-note" class="block text-xs font-semibold text-gray-700 mb-1.5">Note (optional)</label>
				<input
					id="billing-note"
					type="text"
					placeholder="e.g. OPD visit payment"
					bind:value={topupNote}
					class="w-full px-4 py-3 rounded-xl text-sm outline-none"
					style="background: white; border: 1px solid rgba(0,0,0,0.15); box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
				/>
			</div>

			<AquaButton onclick={submitTopup} loading={topupLoading} fullWidth variant="primary">
				Add {topupAmount ? `₹${parseFloat(topupAmount).toLocaleString('en-IN')}` : 'Funds'}
			</AquaButton>
		</div>
	</AquaModal>
{/if}
