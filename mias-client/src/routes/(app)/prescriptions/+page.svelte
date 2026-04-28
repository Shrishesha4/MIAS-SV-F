<script lang="ts">
	import { onMount } from 'svelte';
	import { patientApi } from '$lib/api/patients';
	import type { Prescription } from '$lib/api/types';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaInput from '$lib/components/ui/AquaInput.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaSelect from '$lib/components/ui/AquaSelect.svelte';
	import {
		Pill, Search, ChevronLeft, Eye, Download, Printer, Calendar,
		User, Building, Phone, Mail, ExternalLink, RefreshCw, X,
		ShoppingCart, CheckCircle
	} from 'lucide-svelte';

	const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'pending'> = {
		ACTIVE: 'success',
		BOUGHT: 'info',
		RECEIVE: 'warning',
		COMPLETED: 'pending',
	};

	const statusLabels: Record<string, string> = {
		ACTIVE: 'Active',
		BOUGHT: 'Bought',
		RECEIVE: 'Receive',
		COMPLETED: 'Completed',
	};

	let prescriptions: Prescription[] = $state([]);
	let loading = $state(true);
	let searchQuery = $state('');
	let selectedStatus = $state('all');
	let selectedPrescription = $state<Prescription | null>(null);
	let showModal = $state(false);
	let renewingId = $state('');
	let patient: any = $state(null);

	const API_BASE = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8001';

	const statusFilters = [
		{ value: 'all', label: 'All' },
		{ value: 'ACTIVE', label: 'Active' },
		{ value: 'RECEIVE', label: 'To Receive' },
		{ value: 'BOUGHT', label: 'Bought' },
		{ value: 'COMPLETED', label: 'Completed' },
	];

	const filteredPrescriptions = $derived.by(() => {
		let filtered = prescriptions;

		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			filtered = filtered.filter(p => 
				p.doctor.toLowerCase().includes(q) ||
				p.prescription_id?.toLowerCase().includes(q) ||
				p.medications.some(m => m.name.toLowerCase().includes(q))
			);
		}

		if (selectedStatus !== 'all') {
			filtered = filtered.filter(p => p.status === selectedStatus);
		}

		return filtered;
	});

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-US', { 
			month: 'short', 
			day: 'numeric', 
			year: 'numeric' 
		});
	}

	function openPrescriptionDetail(rx: Prescription) {
		selectedPrescription = rx;
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		selectedPrescription = null;
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['PATIENT'])) return;
		try {
			patient = await patientApi.getCurrentPatient();
			prescriptions = await patientApi.getPrescriptions(patient.id);
		} catch (err) {
			toastStore.addToast('Failed to load prescriptions', 'error');
		} finally {
			loading = false;
		}
	});

	let buyingId = $state('');

	async function buyPrescription(rx: Prescription) {
		if (!patient || buyingId) return;
		buyingId = rx.id;
		try {
			await patientApi.updatePrescriptionStatus(patient.id, rx.id, { status: 'BOUGHT' });
			prescriptions = await patientApi.getPrescriptions(patient.id);
			toastStore.addToast('Prescription marked as bought', 'success');
			showModal = false;
			selectedPrescription = null;
		} catch (err) {
			toastStore.addToast('Failed to buy prescription', 'error');
		} finally {
			buyingId = '';
		}
	}

	async function renewPrescription(rx: Prescription) {
		if (!patient || renewingId) return;
		renewingId = rx.id;
		try {
			await patientApi.renewPrescription(patient.id, rx.id);
			prescriptions = await patientApi.getPrescriptions(patient.id);
			showModal = false;
			selectedPrescription = null;
		} catch (err) {
			toastStore.addToast('Failed to renew prescription', 'error');
		} finally {
			renewingId = '';
		}
	}
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	<!-- Header -->
	<div class="flex items-center gap-3">
		<button class="p-2 rounded-full hover:bg-gray-100" onclick={() => history.back()}>
			<ChevronLeft class="w-5 h-5 text-gray-600" />
		</button>
		<h1 class="text-lg font-bold text-gray-800">My Prescriptions</h1>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
		<!-- Search -->
		<AquaInput 
			placeholder="Search by medication, doctor, or ID..." 
			icon={Search}
			bind:value={searchQuery}
		/>

		<!-- Status Filter -->
		<div class="flex items-center gap-2">
			<span class="text-sm text-gray-600">Status:</span>
			<AquaSelect
				bind:value={selectedStatus}
				options={statusFilters}
			/>
		</div>

		<!-- Results Header -->
		<div class="flex items-center justify-between px-4 py-3 rounded-xl"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
			<span class="text-white font-semibold">Prescription History</span>
			<span class="px-3 py-1 rounded-full text-xs font-medium bg-white text-blue-600">
				{filteredPrescriptions.length} Prescriptions
			</span>
		</div>

		<!-- Completed filter indicator (optional) -->
		{#if selectedStatus === 'COMPLETED'}
			<div class="flex items-center gap-2">
				<StatusBadge variant="pending">
					<CheckCircle class="w-3 h-3 mr-1" />
					Completed
				</StatusBadge>
			</div>
		{/if}

		<!-- Prescriptions List -->
		<div class="space-y-3">
			{#each filteredPrescriptions as rx}
				<AquaCard padding={false}>
					<div class="p-4 flex items-start gap-3">
						<!-- Icon -->
						<div 
							class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
							style="background: linear-gradient(to bottom, #94a3b8, #64748b);"
						>
							<Pill class="w-5 h-5 text-white" />
						</div>

						<!-- Content -->
						<div class="flex-1 min-w-0">
							<p class="text-sm font-semibold text-gray-800">
								Prescription {rx.prescription_id || rx.id.slice(0, 12)}
							</p>
							<div class="flex items-center gap-1 mt-1 text-xs text-gray-500">
								<Calendar class="w-3 h-3" />
								<span>{formatDate(rx.date)}</span>
							</div>
							<p class="text-xs text-gray-600 mt-1">{rx.doctor}</p>
							<p class="text-xs text-gray-500">{rx.department}</p>
						</div>

						<!-- Actions -->
						<div class="flex flex-col items-end gap-2">
							<StatusBadge variant={statusVariant[rx.status]}>
								{#if rx.status === 'ACTIVE'}
									<CheckCircle class="w-3 h-3 mr-1" />
								{/if}
								{statusLabels[rx.status]}
							</StatusBadge>
							<button 
								class="px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1 cursor-pointer"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white;"
								onclick={() => openPrescriptionDetail(rx)}
							>
								<Eye class="w-3 h-3" />
								View
							</button>
						</div>
					</div>
				</AquaCard>
			{/each}
		</div>

		{#if filteredPrescriptions.length === 0}
			<div class="text-center py-12 text-gray-400">
				<Pill class="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p class="text-sm">No prescriptions found</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Prescription Detail Modal -->
{#if showModal && selectedPrescription}
	<AquaModal onClose={closeModal}>
		{#snippet header()}
			<div class="flex items-center justify-between w-full">
				<span class="font-semibold text-gray-800">Prescription Details</span>
				<div class="flex items-center gap-2">
					<button class="p-2 hover:bg-gray-100 rounded-full cursor-pointer" onclick={() => window.print()}>
						<Printer class="w-5 h-5 text-gray-600" />
					</button>
					<button class="p-2 hover:bg-gray-100 rounded-full">
						<Download class="w-5 h-5 text-gray-600" />
					</button>
				</div>
			</div>
		{/snippet}

		<div class="space-y-4">
			<!-- Status and Buy/Renew buttons -->
			<div class="flex items-center gap-3">
				<StatusBadge variant={statusVariant[selectedPrescription.status]} size="md">
					{#if selectedPrescription.status === 'ACTIVE'}
						<CheckCircle class="w-3 h-3 mr-1" />
					{/if}
					{statusLabels[selectedPrescription.status]}
				</StatusBadge>
				{#if selectedPrescription.status === 'ACTIVE' || selectedPrescription.status === 'RECEIVE'}
					<button
						class="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 cursor-pointer"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a); color: white;"
						onclick={() => buyPrescription(selectedPrescription!)}
						disabled={!!buyingId}
					>
						{#if buyingId === selectedPrescription.id}
							<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
							Buying...
						{:else}
							<ShoppingCart class="w-4 h-4" />
							Buy
						{/if}
					</button>
				{/if}
				{#if selectedPrescription.status === 'COMPLETED'}
					<button 
						class="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 cursor-pointer"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white;
						       box-shadow: 0 2px 6px rgba(37,99,235,0.3);"
						onclick={() => renewPrescription(selectedPrescription!)}
						disabled={!!renewingId}>
						{#if renewingId === selectedPrescription.id}
							<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
							Renewing...
						{:else}
							<RefreshCw class="w-4 h-4" />
							Renew Prescription
						{/if}
					</button>
				{/if}
			</div>

			<!-- Hospital Header -->
			{#if selectedPrescription.hospital_name}
				<div class="rounded-xl p-4"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);">
					<div class="flex justify-between">
						<div>
							<h3 class="text-white font-bold">{selectedPrescription.hospital_name}</h3>
							<p class="text-blue-100 text-xs mt-1">{selectedPrescription.hospital_address}</p>
							{#if selectedPrescription.hospital_website}
								<a href="https://{selectedPrescription.hospital_website}" 
									class="flex items-center gap-1 text-blue-100 text-xs mt-1 hover:text-white">
									<ExternalLink class="w-3 h-3" />
									{selectedPrescription.hospital_website}
								</a>
							{/if}
						</div>
						<div class="text-right">
							<p class="text-white font-bold text-sm">PRESCRIPTION</p>
							<p class="text-blue-100 text-xs mt-1">
								Prescription ID: {selectedPrescription.prescription_id || selectedPrescription.id.slice(0, 12)}
							</p>
							<p class="text-blue-100 text-xs">
								Date: {formatDate(selectedPrescription.date)}
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Patient Information -->
			{#if selectedPrescription.patient}
				<div class="p-4 rounded-xl border border-gray-200">
					<h4 class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
						<User class="w-4 h-4" />
						Patient Information
					</h4>
					<div class="space-y-2 text-sm">
						<div>
							<span class="text-gray-500">Name:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.patient.name}</span>
						</div>
						<div>
							<span class="text-gray-500">Patient ID:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.patient.patient_id}</span>
						</div>
						<div>
							<span class="text-gray-500">Date of Birth:</span>
							<span class="ml-1 text-gray-800">
								{new Date(selectedPrescription.patient.date_of_birth).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
							</span>
						</div>
						<div>
							<span class="text-gray-500">Gender:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.patient.gender}</span>
						</div>
						<div>
							<span class="text-gray-500">Contact:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.patient.phone}</span>
						</div>
						<div>
							<span class="text-gray-500">Address:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.patient.address}</span>
						</div>
					</div>
				</div>
			{/if}

			<!-- Prescriber Information -->
			<div class="p-4 rounded-xl border border-gray-200">
				<h4 class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
					<User class="w-4 h-4" />
					Prescriber Information
				</h4>
				<div class="space-y-2 text-sm">
					<div>
						<span class="text-gray-500">Doctor:</span>
						<span class="ml-1 text-gray-800">{selectedPrescription.doctor}</span>
					</div>
					<div>
						<span class="text-gray-500">Department:</span>
						<span class="ml-1 text-gray-800">{selectedPrescription.department}</span>
					</div>
					{#if selectedPrescription.doctor_license}
						<div>
							<span class="text-gray-500">License No:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.doctor_license}</span>
						</div>
					{/if}
					{#if selectedPrescription.hospital_name}
						<div class="pt-2 border-t border-gray-100">
							<span class="text-gray-500">Hospital:</span>
							<span class="ml-1 text-gray-800">{selectedPrescription.hospital_name}</span>
						</div>
						{#if selectedPrescription.hospital_contact}
							<div>
								<span class="text-gray-500">Contact:</span>
								<span class="ml-1 text-gray-800">{selectedPrescription.hospital_contact}</span>
							</div>
						{/if}
						{#if selectedPrescription.hospital_email}
							<div>
								<span class="text-gray-500">Email:</span>
								<span class="ml-1 text-gray-800">{selectedPrescription.hospital_email}</span>
							</div>
						{/if}
					{/if}
				</div>
			</div>

			<!-- Medications -->
			<div>
				<h4 class="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
					<Pill class="w-4 h-4" />
					Medications
				</h4>
				<div class="space-y-3">
					{#each selectedPrescription.medications as med}
						<div class="p-4 rounded-xl border border-gray-200">
							<div class="flex items-start justify-between">
								<div>
									<p class="flex items-center gap-2 font-semibold text-gray-800">
										<Pill class="w-4 h-4 text-blue-600" />
										{med.name} {med.dosage}
									</p>
									<div class="mt-2 space-y-1 text-sm text-gray-600">
										<p><span class="text-gray-500">Frequency:</span> {med.frequency}</p>
										<p><span class="text-gray-500">Duration:</span> {med.duration}</p>
										{#if med.instructions}
											<p><span class="text-gray-500">Instructions:</span> {med.instructions}</p>
										{/if}
									</div>
								</div>
								<div class="text-right text-xs">
									<p class="text-gray-500">Valid:</p>
									<p class="text-gray-700">{med.start_date} -</p>
									<p class="text-gray-700">{med.end_date}</p>
									{#if med.refills_remaining > 0}
										<span class="mt-2 inline-block px-2 py-1 rounded border border-gray-300 text-gray-700 font-medium">
											Refills: {med.refills_remaining}
										</span>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Additional Notes -->
			{#if selectedPrescription.notes}
				<div class="p-4 rounded-xl bg-blue-50 border border-blue-100">
					<h4 class="flex items-center gap-2 text-sm font-semibold text-blue-800 mb-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						Additional Notes
					</h4>
					<p class="text-sm text-blue-700">{selectedPrescription.notes}</p>
				</div>
			{/if}

			<!-- Doctor Signature -->
			<div class="text-center py-4 border-t border-gray-100">
				<div class="text-gray-400 italic text-sm mb-2">Doctor Signature</div>
				{#if selectedPrescription.doctor_signature}
					<img src="{API_BASE}{selectedPrescription.doctor_signature}" alt="Doctor Signature"
						class="max-h-16 mx-auto mb-2" style="image-rendering: auto;" />
				{/if}
				<p class="font-semibold text-gray-800">{selectedPrescription.doctor}</p>
				<p class="text-sm text-gray-500">{selectedPrescription.department}</p>
				<p class="text-xs text-gray-400">Date: {formatDate(selectedPrescription.date)}</p>
			</div>

			<!-- Footer -->
			<div class="p-4 rounded-xl bg-gray-50 text-center text-xs text-gray-500 space-y-1">
				<p>This is an official prescription from {selectedPrescription.hospital_name || 'the hospital'}.</p>
				{#if selectedPrescription.hospital_email}
					<p>For any inquiries, please contact our pharmacy at {selectedPrescription.hospital_email}</p>
				{/if}
				<p>Document generated on: {new Date().toLocaleDateString('en-GB')} {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</p>
			</div>
		</div>
	</AquaModal>
{/if}
