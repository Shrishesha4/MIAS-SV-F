<script lang="ts">
	import { mrdApi, type MrdRecord, type MrdAdmission, type MrdPrescription } from '$lib/api/mrd';
	import { toastStore } from '$lib/stores/toast';
	import SideSheet from './SideSheet.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import {
		FileText, Bed, Pill, Activity, Calendar, User, Phone, Hash, Baby, Skull
	} from 'lucide-svelte';

	interface PatientInfo {
		id: string;
		patient_id: string;
		name: string;
		age?: number;
		gender?: string | null;
		phone?: string | null;
		date_of_birth?: string | null;
		diagnosis?: string;
		department?: string;
		is_deceased?: boolean;
		children?: { id: string; patient_id: string; name: string }[];
	}

	interface Props {
		open: boolean;
		patient: PatientInfo | null;
		onclose: () => void;
	}

	let { open, patient, onclose }: Props = $props();

	type TabKey = 'records' | 'admissions' | 'prescriptions';

	let activeTab = $state<TabKey>('records');
	let records = $state<MrdRecord[]>([]);
	let admissions = $state<MrdAdmission[]>([]);
	let prescriptions = $state<MrdPrescription[]>([]);
	let loadingTab = $state<TabKey | null>(null);
	let loadedTabs = $state<Set<TabKey>>(new Set());
	let lastFetchedPatientId = $state<string | null>(null);

	const tabs = [
		{ id: 'records', label: 'Records' },
		{ id: 'admissions', label: 'Admissions' },
		{ id: 'prescriptions', label: 'Prescriptions' },
	];

	const isDeceased = $derived(patient?.is_deceased ?? false);
	const babyRecords = $derived(patient?.children ?? []);

	function getDateRange() {
		const to = new Date().toISOString().split('T')[0];
		const from = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
		return { from_date: from, to_date: to };
	}

	async function fetchTab(tab: TabKey) {
		if (!patient || loadedTabs.has(tab) || loadingTab === tab) return;
		loadingTab = tab;
		const dates = getDateRange();
		try {
			if (tab === 'records') {
				const res = await mrdApi.getRecords({ ...dates, patient_id: patient.id, page_size: 50 });
				records = res.items;
			} else if (tab === 'admissions') {
				const res = await mrdApi.getAdmissions({ ...dates, patient_id: patient.id, page_size: 50 });
				admissions = res.items;
			} else if (tab === 'prescriptions') {
				const res = await mrdApi.getPrescriptions({ ...dates, patient_id: patient.id, page_size: 50 });
				prescriptions = res.items;
			}
			loadedTabs = new Set([...loadedTabs, tab]);
		} catch (e: any) {
			toastStore.addToast(`Failed to load ${tab}`, 'error');
		} finally {
			loadingTab = null;
		}
	}

	function switchTab(tab: TabKey) {
		activeTab = tab;
		fetchTab(tab);
	}

	// Reset state when patient changes
	$effect(() => {
		if (patient && open && patient.id !== lastFetchedPatientId) {
			records = [];
			admissions = [];
			prescriptions = [];
			loadedTabs = new Set();
			activeTab = 'records';
			lastFetchedPatientId = patient.id;
			fetchTab('records');
		}
	});
</script>

<SideSheet {open} title="Patient Case Sheet" {onclose}>
	{#if patient}
		<div class="case-sheet-content" class:deceased={isDeceased}>
			<!-- Deceased Banner -->
			{#if isDeceased}
				<div class="flex items-center gap-2 px-5 py-2 text-xs font-semibold"
					style="background: #374151; color: #d1d5db;">
					<Skull size={14} />
					<span>DECEASED</span>
				</div>
			{/if}

			<!-- Patient Header -->
			<div class="px-5 py-4 border-b border-slate-100" style="background: linear-gradient(to bottom, {isDeceased ? '#374151, #1f2937' : '#f0f9ff, #f8fafc'});">
				<div class="flex items-center gap-3">
					<Avatar name={patient.name} size="md" />
					<div class="flex-1 min-w-0">
						<h3 class="font-semibold text-base truncate" style="color: {isDeceased ? '#e5e7eb' : '#0f172a'};">{patient.name}</h3>
						<div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5">
							<span class="inline-flex items-center gap-1 text-xs" style="color: {isDeceased ? '#9ca3af' : '#64748b'};">
								<Hash size={11} />
								{patient.patient_id}
							</span>
							{#if patient.age}
								<span class="inline-flex items-center gap-1 text-xs" style="color: {isDeceased ? '#9ca3af' : '#64748b'};">
									<User size={11} />
									{patient.age} yrs{patient.gender ? ` · ${patient.gender}` : ''}
								</span>
							{:else if patient.date_of_birth}
								<span class="inline-flex items-center gap-1 text-xs" style="color: {isDeceased ? '#9ca3af' : '#64748b'};">
									<Calendar size={11} />
									DOB: {new Date(patient.date_of_birth).toLocaleDateString()}
								</span>
							{/if}
							{#if patient.phone}
								<span class="inline-flex items-center gap-1 text-xs" style="color: {isDeceased ? '#9ca3af' : '#64748b'};">
									<Phone size={11} />
									{patient.phone}
								</span>
							{/if}
						</div>
						{#if patient.diagnosis}
							<p class="text-xs mt-1 truncate" style="color: {isDeceased ? '#6b7280' : '#2563eb'};">{patient.diagnosis}</p>
						{/if}
					</div>
				</div>
			</div>

			<!-- Baby Records Section -->
			{#if babyRecords.length > 0}
				<div class="px-5 py-3 border-b border-slate-100" style="background: #fdf4ff;">
					<p class="text-[11px] font-bold uppercase tracking-wider text-pink-700 mb-2">
						<Baby size={12} class="inline -mt-0.5 mr-1" />
						Linked Newborns ({babyRecords.length})
					</p>
					<div class="space-y-1.5">
						{#each babyRecords as baby}
							<div class="flex items-center gap-2 px-3 py-2 rounded-lg"
								style="background: white; border: 1px solid #f9a8d4;">
								<Baby size={14} class="text-pink-500 shrink-0" />
								<div class="flex-1 min-w-0">
									<p class="text-sm font-medium text-slate-800 truncate">
										{baby.name || 'Baby (unnamed)'}
									</p>
									<p class="text-[11px] text-slate-400">{baby.patient_id}</p>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Tabs -->
			<div class="px-5 pt-3">
				<TabBar
					{tabs}
					activeTab={activeTab}
					onchange={(id) => switchTab(id as TabKey)}
				/>
			</div>

			<!-- Tab Content -->
			<div class="px-5 py-4">
				{#if loadingTab === activeTab}
					<div class="flex items-center justify-center py-12">
						<Activity size={22} class="animate-spin text-blue-500" />
					</div>
				{:else if activeTab === 'records'}
					{#if records.length === 0}
						<div class="text-center py-10 text-sm text-slate-400">
							<FileText size={32} class="mx-auto mb-2 text-slate-300" />
							No records found in the last year
						</div>
					{:else}
						<div class="space-y-3">
							{#each records as rec}
								<div class="rounded-xl border border-slate-100 p-3 hover:border-slate-200 transition-colors"
									style="background: #fafbfc;">
									<div class="flex items-start justify-between gap-2">
										<div class="min-w-0 flex-1">
											<p class="text-sm font-medium text-slate-800 truncate">
												{rec.description || rec.type}
											</p>
											<p class="text-xs text-slate-500 mt-0.5">
												{rec.department} · {rec.performed_by}
											</p>
										</div>
										<div class="text-right shrink-0">
											<p class="text-xs text-slate-400">{rec.date}</p>
											{#if rec.status}
												<span class="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full"
													style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;">
													{rec.status}
												</span>
											{/if}
										</div>
									</div>
									{#if rec.diagnosis}
										<p class="text-xs text-slate-600 mt-2 bg-blue-50 px-2 py-1 rounded-md inline-block">
											{rec.diagnosis}
										</p>
									{/if}
								</div>
							{/each}
						</div>
					{/if}

				{:else if activeTab === 'admissions'}
					{#if admissions.length === 0}
						<div class="text-center py-10 text-sm text-slate-400">
							<Bed size={32} class="mx-auto mb-2 text-slate-300" />
							No admissions found in the last year
						</div>
					{:else}
						<div class="space-y-3">
							{#each admissions as adm}
								<div class="rounded-xl border border-slate-100 p-3 hover:border-slate-200 transition-colors"
									style="background: #fafbfc;">
									<div class="flex items-start justify-between gap-2">
										<div class="min-w-0 flex-1">
											<p class="text-sm font-medium text-slate-800">
												{adm.department}
											</p>
											<p class="text-xs text-slate-500 mt-0.5">
												{adm.attending_doctor}
												{#if adm.ward} · Ward {adm.ward}{/if}
												{#if adm.bed_number} · Bed {adm.bed_number}{/if}
											</p>
										</div>
										<div class="text-right shrink-0">
											<span class="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full"
												style="background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe;">
												{adm.status}
											</span>
										</div>
									</div>
									<div class="flex items-center gap-2 mt-2 text-xs text-slate-400">
										<Calendar size={11} />
										<span>{adm.admission_date}</span>
										{#if adm.discharge_date}
											<span>→ {adm.discharge_date}</span>
										{:else}
											<span class="text-green-600 font-medium">Active</span>
										{/if}
									</div>
									{#if adm.diagnosis}
										<p class="text-xs text-slate-600 mt-2 bg-amber-50 px-2 py-1 rounded-md inline-block">
											{adm.diagnosis}
										</p>
									{/if}
								</div>
							{/each}
						</div>
					{/if}

				{:else if activeTab === 'prescriptions'}
					{#if prescriptions.length === 0}
						<div class="text-center py-10 text-sm text-slate-400">
							<Pill size={32} class="mx-auto mb-2 text-slate-300" />
							No prescriptions found in the last year
						</div>
					{:else}
						<div class="space-y-3">
							{#each prescriptions as rx}
								<div class="rounded-xl border border-slate-100 p-3 hover:border-slate-200 transition-colors"
									style="background: #fafbfc;">
									<div class="flex items-start justify-between gap-2">
										<div class="min-w-0 flex-1">
											<p class="text-sm font-medium text-slate-800">
												{rx.prescription_id}
											</p>
											<p class="text-xs text-slate-500 mt-0.5">
												{rx.doctor} · {rx.department}
											</p>
										</div>
										<div class="text-right shrink-0">
											<p class="text-xs text-slate-400">{rx.date}</p>
											<span class="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full"
												style="background: #fefce8; color: #854d0e; border: 1px solid #fef08a;">
												{rx.status}
											</span>
										</div>
									</div>
									{#if rx.notes}
										<p class="text-xs text-slate-600 mt-2 line-clamp-2">{rx.notes}</p>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/if}
</SideSheet>

<style>
	.case-sheet-content.deceased {
		filter: grayscale(0.7);
		position: relative;
	}
	.case-sheet-content.deceased::before {
		content: '';
		position: absolute;
		inset: 0;
		background: rgba(31, 41, 55, 0.05);
		pointer-events: none;
		z-index: 1;
	}
</style>
