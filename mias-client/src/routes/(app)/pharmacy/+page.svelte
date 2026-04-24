<script lang="ts">
	import { onMount } from 'svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { pharmacyApi, type PharmacyDashboardResponse, type PharmacyOrder } from '$lib/api/pharmacy';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import {
		AlertCircle,
		CheckCircle2,
		Clock3,
		Package,
		Pill,
		Printer,
		Search,
		Send,
		UserRound,
	} from 'lucide-svelte';

	type TrayKey = 'preparation' | 'dispatch';

	let dashboard = $state.raw<PharmacyDashboardResponse | null>(null);
	let loading = $state(true);
	let searchQuery = $state('');
	let activeTray = $state<TrayKey>('preparation');
	let processingId = $state('');

	const filteredPreparationTray = $derived.by(() => {
		const orders = dashboard?.preparation_tray ?? [];
		const query = searchQuery.trim().toLowerCase();
		if (!query) return orders;
		return orders.filter((order) => matchesOrder(order, query));
	});

	const filteredDispatchTray = $derived.by(() => {
		const orders = dashboard?.dispatch_tray ?? [];
		const query = searchQuery.trim().toLowerCase();
		if (!query) return orders;
		return orders.filter((order) => matchesOrder(order, query));
	});

	const activeOrders = $derived(activeTray === 'preparation' ? filteredPreparationTray : filteredDispatchTray);

	function matchesOrder(order: PharmacyOrder, query: string): boolean {
		return [
			order.prescription_id || '',
			order.patient?.name || '',
			order.patient?.patient_id || '',
			order.doctor || '',
			order.requested_by || '',
			...order.medications.map((medication) => medication.name),
		].some((value) => value.toLowerCase().includes(query));
	}

	function formatDateTime(value?: string | null): string {
		if (!value) return 'Just now';
		return new Date(value).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit',
		});
	}

	function escapeHtml(value: string): string {
		return value
			.replaceAll('&', '&amp;')
			.replaceAll('<', '&lt;')
			.replaceAll('>', '&gt;')
			.replaceAll('"', '&quot;')
			.replaceAll("'", '&#39;');
	}

	function printLabel(order: PharmacyOrder) {
		const labelWindow = window.open('', '_blank', 'width=420,height=620');
		if (!labelWindow) {
			toastStore.addToast('Allow pop-ups to print labels', 'error');
			return;
		}

		const medicationLines = order.medications
			.map((medication) => `<li>${escapeHtml(medication.name)} ${escapeHtml(medication.dosage)}</li>`)
			.join('');

		labelWindow.document.write(`
			<html>
				<head>
					<title>Prescription Label</title>
					<style>
						body { font-family: Arial, sans-serif; padding: 20px; color: #0f172a; }
						h1 { font-size: 18px; margin-bottom: 4px; }
						p { margin: 6px 0; font-size: 13px; }
						ul { margin: 10px 0 0 18px; padding: 0; }
						li { margin-bottom: 4px; font-size: 13px; }
						.badge { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #dbeafe; color: #1d4ed8; font-size: 11px; font-weight: 700; }
					</style>
				</head>
				<body>
					<h1>${escapeHtml(order.prescription_id || order.id)}</h1>
					<p class="badge">Pharmacy Label</p>
					<p><strong>Patient:</strong> ${escapeHtml(order.patient?.name || 'Unknown')}</p>
					<p><strong>Patient ID:</strong> ${escapeHtml(order.patient?.patient_id || 'N/A')}</p>
					<p><strong>Doctor:</strong> ${escapeHtml(order.doctor || 'N/A')}</p>
					<p><strong>Requested:</strong> ${escapeHtml(formatDateTime(order.requested_at))}</p>
					<p><strong>Medicines:</strong></p>
					<ul>${medicationLines}</ul>
				</body>
			</html>
		`);
		labelWindow.document.close();
		labelWindow.focus();
		labelWindow.print();
		labelWindow.close();
	}

	async function loadDashboard() {
		loading = true;
		try {
			dashboard = await pharmacyApi.getDashboard();
			if (activeTray === 'preparation' && (dashboard.preparation_tray?.length ?? 0) === 0 && (dashboard.dispatch_tray?.length ?? 0) > 0) {
				activeTray = 'dispatch';
			}
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load pharmacy dashboard', 'error');
		} finally {
			loading = false;
		}
	}

	async function markPrepared(order: PharmacyOrder) {
		if (processingId) return;
		processingId = order.id;
		try {
			await pharmacyApi.markPrepared(order.id);
			toastStore.addToast('Prescription moved to dispatch tray', 'success');
			await loadDashboard();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to mark prescription prepared', 'error');
		} finally {
			processingId = '';
		}
	}

	async function markIssued(order: PharmacyOrder) {
		if (processingId) return;
		processingId = order.id;
		try {
			await pharmacyApi.markIssued(order.id);
			toastStore.addToast('Prescription issued successfully', 'success');
			await loadDashboard();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to mark prescription issued', 'error');
		} finally {
			processingId = '';
		}
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['PHARMACY'])) return;
		await loadDashboard();
	});
</script>

<div class="mx-auto max-w-6xl space-y-4 px-4 py-4 md:px-6 md:py-6">
	<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
		<div>
			<h1 class="text-2xl font-bold text-slate-900">Pharmacy Dashboard</h1>
			<p class="mt-1 text-sm text-slate-500">Manage student prescription requests and dispensing progress.</p>
		</div>
		<div class="relative w-full lg:w-80">
			<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search patient or RX ID..."
				class="w-full rounded-2xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-700 outline-none transition focus:border-blue-400"
				style="box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.06);"
			/>
		</div>
	</div>

	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
		<div class="rounded-3xl border border-amber-200 bg-amber-50/80 p-4" style="box-shadow: 0 10px 24px rgba(245, 158, 11, 0.08);">
			<div class="flex items-center justify-between">
				<p class="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">In Preparation</p>
				<Clock3 class="h-4 w-4 text-amber-500" />
			</div>
			<p class="mt-4 text-3xl font-bold text-slate-900">{dashboard?.summary.in_preparation ?? 0}</p>
		</div>
		<div class="rounded-3xl border border-blue-200 bg-blue-50/80 p-4" style="box-shadow: 0 10px 24px rgba(59, 130, 246, 0.08);">
			<div class="flex items-center justify-between">
				<p class="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Ready For Dispatch</p>
				<Package class="h-4 w-4 text-blue-500" />
			</div>
			<p class="mt-4 text-3xl font-bold text-slate-900">{dashboard?.summary.ready_for_dispatch ?? 0}</p>
		</div>
		<div class="rounded-3xl border border-emerald-200 bg-emerald-50/80 p-4" style="box-shadow: 0 10px 24px rgba(16, 185, 129, 0.08);">
			<div class="flex items-center justify-between">
				<p class="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Issued Today</p>
				<CheckCircle2 class="h-4 w-4 text-emerald-500" />
			</div>
			<p class="mt-4 text-3xl font-bold text-slate-900">{dashboard?.summary.issued_today ?? 0}</p>
		</div>
		<div class="rounded-3xl border border-rose-200 bg-rose-50/80 p-4" style="box-shadow: 0 10px 24px rgba(244, 63, 94, 0.08);">
			<div class="flex items-center justify-between">
				<p class="text-xs font-bold uppercase tracking-[0.16em] text-rose-700">Urgent Orders</p>
				<AlertCircle class="h-4 w-4 text-rose-500" />
			</div>
			<p class="mt-4 text-3xl font-bold text-slate-900">{dashboard?.summary.urgent_orders ?? 0}</p>
		</div>
	</div>

	<AquaCard padding={false}>
		<div class="border-b border-slate-100 px-2 pt-2">
			<div class="grid grid-cols-2 gap-2">
				<button
					class="rounded-2xl px-3 py-3 text-sm font-semibold transition-all cursor-pointer"
					style={activeTray === 'preparation'
						? 'background: linear-gradient(to bottom, #eff6ff, #dbeafe); color: #2563eb; box-shadow: inset 0 -2px 0 #2563eb;'
						: 'background: transparent; color: #64748b;'}
					onclick={() => activeTray = 'preparation'}
				>
					Preparation Tray <span class="ml-1 rounded-full bg-white/90 px-2 py-0.5 text-xs">{filteredPreparationTray.length}</span>
				</button>
				<button
					class="rounded-2xl px-3 py-3 text-sm font-semibold transition-all cursor-pointer"
					style={activeTray === 'dispatch'
						? 'background: linear-gradient(to bottom, #eff6ff, #dbeafe); color: #2563eb; box-shadow: inset 0 -2px 0 #2563eb;'
						: 'background: transparent; color: #64748b;'}
					onclick={() => activeTray = 'dispatch'}
				>
					Dispatch Tray <span class="ml-1 rounded-full bg-white/90 px-2 py-0.5 text-xs">{filteredDispatchTray.length}</span>
				</button>
			</div>
		</div>

		<div class="space-y-3 p-3 md:p-4">
			{#if loading}
				<div class="flex items-center justify-center py-16">
					<div class="h-9 w-9 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600"></div>
				</div>
			{:else if activeOrders.length === 0}
				<div class="rounded-3xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-12 text-center text-slate-500">
					<Pill class="mx-auto mb-3 h-10 w-10 text-slate-300" />
					<p class="text-sm font-medium">No prescription orders in this tray</p>
					<p class="mt-1 text-xs">New student-approved prescriptions will appear here automatically.</p>
				</div>
			{:else}
				{#each activeOrders as order (order.id)}
					<AquaCard padding={false}>
						<div class="flex flex-col gap-4 p-4 lg:flex-row lg:items-start lg:justify-between">
							<div class="min-w-0 flex-1">
								<div class="flex flex-wrap items-center gap-2">
									<span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
										{order.prescription_id || order.id.slice(0, 12)}
									</span>
									<span class="text-xs text-slate-500">{formatDateTime(order.requested_at)}</span>
									{#if order.is_urgent}
										<span class="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-rose-600">Urgent</span>
									{/if}
								</div>

								<div class="mt-3 flex items-start gap-3">
									<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
										<UserRound class="h-5 w-5" />
									</div>
									<div class="min-w-0 flex-1">
										<p class="truncate text-lg font-bold text-slate-900">{order.patient?.name || 'Unknown patient'}</p>
										<p class="text-sm text-slate-500">{order.patient?.patient_id || 'No patient ID'} • Prescribed by {order.doctor}</p>
										<p class="mt-1 text-xs text-slate-400">{order.department}{order.requested_by ? ` • Requested by ${order.requested_by}` : ''}</p>
									</div>
								</div>

								<div class="mt-4 rounded-2xl border border-slate-200 bg-slate-50/80 p-3">
									<div class="space-y-3">
										{#each order.medications as medication (medication.id)}
											<div class="flex gap-3">
												<div class="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-blue-500 shadow-sm">
													<Pill class="h-4 w-4" />
												</div>
												<div class="min-w-0 flex-1">
													<div class="flex flex-wrap items-center gap-2">
														<p class="font-semibold text-slate-900">{medication.name}</p>
														<span class="text-sm text-slate-500">{medication.dosage}</span>
													</div>
													<p class="text-sm text-slate-500">{medication.frequency} • {medication.duration}</p>
													{#if medication.instructions}
														<p class="text-xs text-slate-400">{medication.instructions}</p>
													{/if}
												</div>
											</div>
										{/each}
									</div>
								</div>

								{#if order.notes}
									<p class="mt-3 text-sm text-slate-500">{order.notes}</p>
								{/if}
							</div>

							<div class="flex w-full flex-col gap-2 lg:w-48">
								{#if activeTray === 'preparation'}
									<button
										class="w-full rounded-2xl px-4 py-2.5 text-sm font-semibold text-white shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
										style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(21, 128, 61, 0.45); box-shadow: 0 4px 12px rgba(34, 197, 94, 0.18);"
										disabled={processingId === order.id}
										onclick={() => markPrepared(order)}
									>
										{processingId === order.id ? 'Marking...' : 'Mark Prepared'}
									</button>
								{:else}
									<AquaButton
										variant="primary"
										fullWidth
										disabled={processingId === order.id}
										onclick={() => markIssued(order)}
									>
										{processingId === order.id ? 'Issuing...' : 'Mark Issued'}
									</AquaButton>
								{/if}
								<button
									class="flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm cursor-pointer"
									onclick={() => printLabel(order)}
								>
									<Printer class="h-4 w-4" />
									Print Label
								</button>
								<div class="rounded-2xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-500">
									{#if activeTray === 'dispatch'}
										<Send class="mb-1 h-3.5 w-3.5 text-blue-500" />
										Ready to hand over to patient.
									{:else}
										<Package class="mb-1 h-3.5 w-3.5 text-emerald-500" />
										Prepare medicines and move to dispatch.
									{/if}
								</div>
							</div>
						</div>
					</AquaCard>
				{/each}
			{/if}
		</div>
	</AquaCard>
</div>