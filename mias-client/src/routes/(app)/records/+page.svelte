<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
	import { patientApi } from '$lib/api/patients';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import {
		FileText, ChevronDown, ChevronRight, Stethoscope, FlaskConical, Syringe, Pill,
		Search, User, CheckCircle, X, ClipboardList
	} from 'lucide-svelte';

	let records: any[] = $state([]);
	let loading = $state(true);
	let expandedId = $state<string | null>(null);
	let searchQuery = $state('');
	let filterType = $state('All');
	let selectedRecord: any | null = $state(null);

	const typeColors: Record<string, string> = {
		CONSULTATION: '#4d90fe',
		LABORATORY: '#f97316',
		PROCEDURE: '#8b5cf6',
		MEDICATION: '#ec4899',
	};

	const typeLabels: Record<string, string> = {
		CONSULTATION: 'Consultation',
		LABORATORY: 'Laboratory',
		PROCEDURE: 'Procedure',
		MEDICATION: 'Medication',
	};

	const filteredRecords = $derived.by(() => {
		let list = records;
		if (filterType !== 'All') list = list.filter(r => r.type === filterType);
		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			list = list.filter(r =>
				r.description?.toLowerCase().includes(q) ||
				r.performed_by?.toLowerCase().includes(q) ||
				r.department?.toLowerCase().includes(q) ||
				r.diagnosis?.toLowerCase().includes(q)
			);
		}
		return list;
	});

	const departments = $derived([...new Set(records.map((r: any) => r.department))].sort());

	function getStatusVariant(status: string) {
		if (status === 'Completed') return 'success';
		if (status === 'Results Available') return 'info';
		if (status === 'Active') return 'warning';
		return 'pending';
	}

	onMount(async () => {
		if (!redirectIfUnauthorized(['PATIENT'])) return;
		try {
			const auth = get(authStore);
			const role = auth.role;
			if (role === 'PATIENT') {
				const patient = await patientApi.getCurrentPatient();
				records = await patientApi.getRecords(patient.id);
			}
		} catch (err) {
			toastStore.addToast('Failed to load records', 'error');
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
		<!-- Search & Filter Card -->
		<div class="overflow-hidden"
			style="background-color: white; border-radius: 10px;
				   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				   border: 1px solid rgba(0,0,0,0.1);">
			<div class="p-3 flex items-center gap-2"
				style="border-bottom: 1px solid rgba(0,0,0,0.06);">
				<ClipboardList class="w-4 h-4 text-blue-700" />
				<h2 class="font-semibold text-gray-800 text-sm">Medical Records</h2>
				<span class="text-[10px] text-gray-400 ml-auto">{filteredRecords.length} record{filteredRecords.length !== 1 ? 's' : ''}</span>
			</div>
			<div class="p-3 space-y-2" style="background-color: #f9fafb;">
				<!-- Search -->
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<Search class="w-3.5 h-3.5 text-gray-400" />
					</div>
					<input
						type="text"
						placeholder="Search records..."
						class="block w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
						style="border-color: rgba(0,0,0,0.12); box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
						bind:value={searchQuery}
					/>
				</div>
				<!-- Type Filter Pills -->
				<div class="flex gap-1.5 overflow-x-auto pb-1">
					{#each ['All', 'CONSULTATION', 'LABORATORY', 'PROCEDURE', 'MEDICATION'] as t}
						<button
							class="px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap cursor-pointer transition-colors shrink-0"
							style="background: {filterType === t ? 'linear-gradient(to bottom, #4d90fe, #0066cc)' : 'linear-gradient(to bottom, #ffffff, #f5f5f5)'};
								   color: {filterType === t ? 'white' : '#374151'};
								   border: 1px solid {filterType === t ? 'rgba(0,0,0,0.2)' : 'rgba(0,0,0,0.12)'};
								   box-shadow: 0 1px 2px rgba(0,0,0,{filterType === t ? '0.15' : '0.05'});"
							onclick={() => filterType = t}
						>
							{t === 'All' ? 'All Types' : typeLabels[t]}
						</button>
					{/each}
				</div>
			</div>
		</div>

		<!-- Records List -->
		{#if filteredRecords.length > 0}
			<div class="overflow-hidden"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<div class="divide-y" style="border-color: rgba(0,0,0,0.06);">
					{#each filteredRecords as record}
						{@const color = typeColors[record.type] || '#6b7280'}
						<!-- Record Card -->
						<div>
							<!-- Header Bar -->
							<button
								class="w-full px-3 py-2 flex items-center justify-between cursor-pointer text-left"
								style="background: linear-gradient(to bottom, #e8f0fa, #d5e3f5);
									   border-bottom: 1px solid rgba(0,0,0,0.06);"
								onclick={() => expandedId = expandedId === record.id ? null : record.id}
							>
								<div class="flex items-center gap-2">
									<div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
										style="background: linear-gradient(to bottom, {color}cc, {color});
											   box-shadow: 0 1px 2px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.3);
											   border: 1px solid rgba(0,0,0,0.15);">
										{#if record.type === 'CONSULTATION'}
											<Stethoscope class="w-3.5 h-3.5 text-white" />
										{:else if record.type === 'LABORATORY'}
											<FlaskConical class="w-3.5 h-3.5 text-white" />
										{:else if record.type === 'PROCEDURE'}
											<Syringe class="w-3.5 h-3.5 text-white" />
										{:else}
											<Pill class="w-3.5 h-3.5 text-white" />
										{/if}
									</div>
									<div class="flex items-center text-sm">
										<span class="font-medium text-gray-800">
											{new Date(record.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
										</span>
										<span class="mx-1.5 text-gray-400">·</span>
										<span class="text-gray-600 text-xs">{record.time}</span>
									</div>
								</div>
								<div class="flex items-center gap-2">
									<StatusBadge variant={getStatusVariant(record.status)}>
										{record.status}
									</StatusBadge>
									<ChevronRight class="w-4 h-4 text-gray-400 transition-transform {expandedId === record.id ? 'rotate-90' : ''}" />
								</div>
							</button>

							<!-- Body -->
							<button
								class="w-full px-3 py-2 text-left cursor-pointer"
								onclick={() => expandedId = expandedId === record.id ? null : record.id}
							>
								<p class="text-sm font-medium text-gray-900">{typeLabels[record.type] || record.type}</p>
								<p class="text-sm text-gray-600 truncate">{record.description}</p>
								<p class="text-xs text-gray-500 mt-0.5">{record.department}</p>
							</button>

							<!-- Footer -->
							<div class="px-3 py-2 flex items-center justify-between text-xs"
								style="background-color: rgba(245,248,252,0.8); border-top: 1px solid rgba(0,0,0,0.05);">
								<div class="flex items-center gap-1 text-gray-600">
									<User class="w-3 h-3 text-gray-400" />
									<span>{record.performed_by}</span>
								</div>
								{#if record.supervised_by && record.supervised_by !== record.performed_by}
									<div class="flex items-center gap-1 text-gray-600">
										<CheckCircle class="w-3 h-3 text-green-500" />
										<span>{record.supervised_by}</span>
									</div>
								{/if}
							</div>

							<!-- Expanded Content -->
							{#if expandedId === record.id}
								<div class="p-3 space-y-3"
									style="background: linear-gradient(to bottom, rgba(235,245,255,0.9), rgba(225,235,245,0.8));
										   border-top: 1px solid rgba(0,0,0,0.08);">
									<div class="flex justify-between items-center">
										<h3 class="font-medium text-gray-800 text-sm">Record Details</h3>
										<button
											class="w-5 h-5 rounded-full flex items-center justify-center cursor-pointer"
											style="background: linear-gradient(to bottom, #ff5a5a, #cc0000);
												   box-shadow: 0 1px 2px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.2);"
											onclick={() => expandedId = null}
										>
											<X class="w-2.5 h-2.5 text-white" />
										</button>
									</div>

									<!-- Meta Grid -->
									<div class="grid grid-cols-2 gap-2 text-sm">
										<div>
											<p class="text-gray-500 text-xs">Performed By</p>
											<p class="font-medium text-gray-800">{record.performed_by}</p>
										</div>
										{#if record.supervised_by}
											<div>
												<p class="text-gray-500 text-xs">Supervised By</p>
												<p class="font-medium text-gray-800">{record.supervised_by}</p>
											</div>
										{/if}
									</div>

									{#if record.diagnosis}
										<div>
											<p class="text-gray-500 text-xs mb-0.5">Diagnosis</p>
											<p class="text-sm text-gray-800">{record.diagnosis}</p>
										</div>
									{/if}

									{#if record.evaluation}
										<div>
											<p class="text-gray-500 text-xs mb-0.5">Evaluation</p>
											<p class="text-sm text-gray-800">{record.evaluation}</p>
										</div>
									{/if}

									{#if record.recommendations}
										<div>
											<p class="text-gray-500 text-xs mb-0.5">Recommendations</p>
											<p class="text-sm text-gray-800">{record.recommendations}</p>
										</div>
									{/if}

									{#if record.notes}
										<div>
											<p class="text-gray-500 text-xs mb-0.5">Notes</p>
											<p class="text-sm text-gray-700 italic">{record.notes}</p>
										</div>
									{/if}

									<!-- Findings Table -->
									{#if record.findings && record.findings.length > 0}
										<div>
											<p class="text-gray-500 text-xs mb-2">Findings</p>
											<div class="space-y-1">
												{#each record.findings as finding}
													<div class="flex items-center justify-between py-1.5 px-2 rounded"
														style="background-color: rgba(255,255,255,0.7);">
														<span class="text-xs text-gray-600">{finding.parameter}</span>
														<div class="flex items-center gap-2">
															<span class="text-xs font-medium text-gray-800">{finding.value}</span>
															{#if finding.reference}
																<span class="text-[10px] text-gray-400">({finding.reference})</span>
															{/if}
															<StatusBadge variant={finding.status === 'Normal' ? 'normal' : 'warning'} size="sm">
																{finding.status}
															</StatusBadge>
														</div>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Images -->
									{#if record.images && record.images.length > 0}
										<div>
											<p class="text-gray-500 text-xs mb-1">Images ({record.images.length})</p>
											<div class="flex flex-wrap gap-2">
												{#each record.images as image}
													<button
														class="w-14 h-14 rounded overflow-hidden cursor-pointer hover:opacity-80 transition-opacity"
														style="border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 2px rgba(0,0,0,0.1);"
														onclick={() => window.open(image.url, '_blank')}
													>
														<img src={image.url} alt={image.title} class="w-full h-full object-cover" />
													</button>
												{/each}
											</div>
										</div>
									{/if}

									<!-- View Full Report Button -->
									<button
										class="w-full py-2 text-sm font-medium rounded-lg cursor-pointer"
										style="background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;
											   border: 1px solid rgba(0,0,0,0.2);
											   box-shadow: 0 1px 2px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.2);"
										onclick={() => selectedRecord = record}
									>
										View Full Report
									</button>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<!-- Empty State -->
			<div class="text-center py-12"
				style="background-color: white; border-radius: 10px;
					   box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
					   border: 1px solid rgba(0,0,0,0.1);">
				<div class="w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-3"
					style="background-color: #f3f4f6;">
					<FileText class="w-7 h-7 text-gray-400" />
				</div>
				<p class="text-sm font-medium text-gray-800 mb-1">No records found</p>
				<p class="text-xs text-gray-500">
					{searchQuery || filterType !== 'All' ? 'Try adjusting your search or filter.' : 'No medical records available yet.'}
				</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Full Report Modal -->
{#if selectedRecord}
	<AquaModal title="Medical Report" onclose={() => selectedRecord = null}>
		<div class="space-y-4">
			<!-- Record Header -->
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
					style="background: linear-gradient(to bottom, {typeColors[selectedRecord.type]}cc, {typeColors[selectedRecord.type]});">
					{#if selectedRecord.type === 'CONSULTATION'}
						<Stethoscope class="w-5 h-5 text-white" />
					{:else if selectedRecord.type === 'LABORATORY'}
						<FlaskConical class="w-5 h-5 text-white" />
					{:else if selectedRecord.type === 'PROCEDURE'}
						<Syringe class="w-5 h-5 text-white" />
					{:else}
						<Pill class="w-5 h-5 text-white" />
					{/if}
				</div>
				<div>
					<p class="text-sm font-semibold text-gray-900">{selectedRecord.description}</p>
					<p class="text-xs text-gray-500">
						{new Date(selectedRecord.date).toLocaleDateString('en-IN', { dateStyle: 'long' })} · {selectedRecord.time}
					</p>
				</div>
			</div>

			<!-- Details Grid -->
			<div class="grid grid-cols-2 gap-3 text-sm">
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Type</p>
					<p class="font-medium text-gray-800">{typeLabels[selectedRecord.type]}</p>
				</div>
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Department</p>
					<p class="font-medium text-gray-800">{selectedRecord.department}</p>
				</div>
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Performed By</p>
					<p class="font-medium text-gray-800">{selectedRecord.performed_by}</p>
				</div>
				{#if selectedRecord.supervised_by}
					<div>
						<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Supervised By</p>
						<p class="font-medium text-gray-800">{selectedRecord.supervised_by}</p>
					</div>
				{/if}
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">Status</p>
					<StatusBadge variant={getStatusVariant(selectedRecord.status)}>
						{selectedRecord.status}
					</StatusBadge>
				</div>
			</div>

			{#if selectedRecord.diagnosis}
				<div class="p-3 rounded-lg" style="background-color: rgba(77,144,254,0.06); border: 1px solid rgba(77,144,254,0.15);">
					<p class="text-[10px] text-blue-600 uppercase tracking-wider mb-1 font-semibold">Diagnosis</p>
					<p class="text-sm text-gray-800">{selectedRecord.diagnosis}</p>
				</div>
			{/if}

			{#if selectedRecord.evaluation}
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Evaluation</p>
					<p class="text-sm text-gray-700">{selectedRecord.evaluation}</p>
				</div>
			{/if}

			{#if selectedRecord.findings && selectedRecord.findings.length > 0}
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-2">Findings</p>
					<div class="space-y-1">
						{#each selectedRecord.findings as finding}
							<div class="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50">
								<span class="text-xs text-gray-600">{finding.parameter}</span>
								<div class="flex items-center gap-2">
									<span class="text-xs font-semibold text-gray-800">{finding.value}</span>
									{#if finding.reference}
										<span class="text-[10px] text-gray-400">({finding.reference})</span>
									{/if}
									<StatusBadge variant={finding.status === 'Normal' ? 'normal' : 'warning'} size="sm">
										{finding.status}
									</StatusBadge>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if selectedRecord.recommendations}
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-1">Recommendations</p>
					<p class="text-sm text-gray-700">{selectedRecord.recommendations}</p>
				</div>
			{/if}

			{#if selectedRecord.notes}
				<div class="p-3 rounded-lg" style="background-color: #fefce8; border: 1px solid rgba(234,179,8,0.2);">
					<p class="text-[10px] text-amber-700 uppercase tracking-wider mb-1 font-semibold">Notes</p>
					<p class="text-sm text-gray-700 italic">{selectedRecord.notes}</p>
				</div>
			{/if}

			{#if selectedRecord.images && selectedRecord.images.length > 0}
				<div>
					<p class="text-[10px] text-gray-400 uppercase tracking-wider mb-2">Images</p>
					<div class="space-y-2">
						{#each selectedRecord.images as image}
							<button
								class="w-full rounded-lg overflow-hidden cursor-pointer text-left"
								style="border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
								onclick={() => window.open(image.url, '_blank')}
							>
								<img src={image.url} alt={image.title} class="w-full h-32 object-cover" />
								<div class="px-3 py-2 bg-gray-50">
									<p class="text-xs font-medium text-gray-800">{image.title}</p>
									{#if image.description}
										<p class="text-[10px] text-gray-500 mt-0.5">{image.description}</p>
									{/if}
								</div>
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</AquaModal>
{/if}
