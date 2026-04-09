<script lang="ts">
	import { Pill, Plus, Trash2 } from 'lucide-svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';

	interface Medication {
		name: string;
		dosage: string;
		duration: string;
		frequency: string;
		timing: string;
		instructions: string;
	}

	interface Patient {
		id: string;
		patient_id: string;
		name: string;
	}

	interface Faculty {
		id: string;
		name: string;
		department: string;
	}

	interface Props {
		patient: Patient;
		facultyApprovers: Faculty[];
		onClose: () => void;
		onSubmit: (data: {
			diagnosis: string;
			medications: Medication[];
			faculty_id: string;
		}) => Promise<void>;
	}

	let { patient, facultyApprovers, onClose, onSubmit }: Props = $props();

	let diagnosis = $state('');
	let medications: Medication[] = $state([]);
	let selectedFacultyId = $state('');
	let submitting = $state(false);

	const frequencyOptions = [
		'1-0-1 (M/N)',
		'1-1-1 (M/A/N)',
		'0-0-1 (N)',
		'1-0-0 (M)',
		'0-1-0 (A)',
		'1-1-0 (M/A)',
		'0-1-1 (A/N)',
		'As needed',
		'Once daily',
		'Twice daily',
		'Three times daily',
		'Four times daily',
	];

	function addMedication() {
		medications = [
			...medications,
			{
				name: '',
				dosage: '',
				duration: '',
				frequency: '1-0-1 (M/N)',
				timing: 'AFTER',
				instructions: '',
			},
		];
	}

	function removeMedication(index: number) {
		medications = medications.filter((_, i) => i !== index);
	}

	async function handleSubmit() {
		if (!diagnosis.trim() || medications.length === 0 || !selectedFacultyId) {
			return;
		}

		// Validate all medications have required fields
		const invalidMed = medications.find((m) => !m.name || !m.dosage || !m.duration);
		if (invalidMed) {
			return;
		}

		submitting = true;
		try {
			await onSubmit({
				diagnosis,
				medications,
				faculty_id: selectedFacultyId,
			});
		} finally {
			submitting = false;
		}
	}

	const canSubmit = $derived(
		diagnosis.trim() &&
			medications.length > 0 &&
			selectedFacultyId &&
			medications.every((m) => m.name && m.dosage && m.duration)
	);
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center" style="background-color: rgba(0,0,0,0.5);">
	<div class="relative w-full max-w-4xl max-h-[90vh] flex flex-col" style="background-color: white; border-radius: 16px; box-shadow: 0 -4px 20px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.1); margin: 0 16px;">
		<!-- Header -->
		<div class="px-4 py-3 flex items-center justify-between shrink-0" style="background-image: linear-gradient(to bottom, #f8f9fb, #e8eef5); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1); border-bottom: 1px solid rgba(0,0,0,0.1); border-radius: 16px 16px 0 0;">
			<div class="flex flex-col gap-1 flex-1">
				<div class="flex items-center gap-2">
					<Pill class="w-5 h-5 text-purple-600" />
					<span class="font-semibold text-gray-800">Create New Prescription</span>
				</div>
				<p class="text-xs font-medium uppercase tracking-wide" style="color: #8b5cf6;">
					PATIENT: {patient.name} ({patient.patient_id})
				</p>
			</div>
			<button class="text-gray-500 hover:text-gray-700 cursor-pointer ml-2" onclick={onClose} type="button" aria-label="Close modal">
				<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
			</button>
		</div>

		<!-- Content -->
		<div class="p-4 overflow-y-auto flex-1">

			<div class="space-y-4">
				<!-- Clinical Diagnosis -->
				<div>
					<label
						for="diagnosis"
						class="block text-xs font-semibold text-gray-600 uppercase tracking-wide mb-1.5"
					>
						Clinical Diagnosis
					</label>
					<textarea
						id="diagnosis"
						bind:value={diagnosis}
						rows="3"
						placeholder="Enter diagnosis..."
						class="w-full px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 resize-none"
						style="background: rgba(255,255,255,0.95);"
					></textarea>
				</div>

				<!-- Medications -->
				<div>
					<div class="flex items-center justify-between mb-2">
						<div class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
							Medications ({medications.length})
						</div>
						<button
							onclick={addMedication}
							class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer transition-all hover:scale-105"
							style="background: linear-gradient(to bottom, #a855f7, #9333ea); box-shadow: 0 2px 4px rgba(147,51,234,0.3);"
							type="button"
						>
							<Plus class="w-3.5 h-3.5" />
							ADD DRUG
						</button>
					</div>

					{#if medications.length === 0}
						<div
							class="text-center py-8 rounded-lg border-2 border-dashed border-gray-200 text-sm text-gray-400"
						>
							No medications added. Click "ADD DRUG" to add a medication.
						</div>
					{:else}
						<div class="overflow-x-auto -mx-1 px-1">
							<div class="space-y-2" style="min-width: 800px;">
					<!-- Table Header -->
					<div
						class="grid gap-2 px-2 py-1.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider"
						style="grid-template-columns: 30px 1fr 0.8fr 0.6fr 1fr 0.8fr 1.2fr 30px;"
					>
						<div>#</div>
						<div>Drug Name *</div>
						<div>Dosage</div>
						<div>Duration</div>
						<div>Frequency</div>
						<div>Timing</div>
						<div>Instructions</div>
						<div></div>
					</div>

					<!-- Medication Rows -->
					{#each medications as med, index}
						<div
							class="grid gap-2 p-2 rounded-lg items-center transition-colors hover:bg-gray-50"
							style="grid-template-columns: 30px 1fr 0.8fr 0.6fr 1fr 0.8fr 1.2fr 30px; border: 1px solid rgba(0,0,0,0.08); background: white;"
						>
							<div class="text-xs text-gray-500 font-medium">{index + 1}</div>

							<!-- Drug Name -->
							<input
								type="text"
								bind:value={med.name}
								placeholder="D"
								class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
							/>

							<!-- Dosage -->
							<input
								type="text"
								bind:value={med.dosage}
								placeholder="500mg"
								class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
							/>

							<!-- Duration -->
							<input
								type="text"
								bind:value={med.duration}
								placeholder="7 days"
								class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
							/>

							<!-- Frequency -->
							<select
								bind:value={med.frequency}
								class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400 cursor-pointer"
							>
								{#each frequencyOptions as opt}
									<option value={opt}>{opt}</option>
								{/each}
							</select>

							<!-- Timing -->
							<div class="flex gap-1">
								<button
									type="button"
									onclick={() => (med.timing = 'BEFORE')}
									class="flex-1 px-2 py-1 rounded text-[10px] font-semibold transition-all cursor-pointer"
									class:selected={med.timing === 'BEFORE'}
									style={med.timing === 'BEFORE'
										? 'background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid #3b82f6;'
										: 'background: rgba(0,0,0,0.03); color: #6b7280; border: 1px solid rgba(0,0,0,0.1);'}
								>
									BEFORE
								</button>
								<button
									type="button"
									onclick={() => (med.timing = 'AFTER')}
									class="flex-1 px-2 py-1 rounded text-[10px] font-semibold transition-all cursor-pointer"
									class:selected={med.timing === 'AFTER'}
									style={med.timing === 'AFTER'
										? 'background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid #3b82f6;'
										: 'background: rgba(0,0,0,0.03); color: #6b7280; border: 1px solid rgba(0,0,0,0.1);'}
								>
									AFTER
								</button>
							</div>

							<!-- Instructions -->
							<input
								type="text"
								bind:value={med.instructions}
								placeholder="Instructions..."
								class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
							/>

							<!-- Delete -->
							<button
								type="button"
								onclick={() => removeMedication(index)}
								class="flex items-center justify-center w-6 h-6 rounded hover:bg-red-50 transition-colors cursor-pointer"
							>
								<Trash2 class="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
							</button>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- Faculty Approval -->
	<div>
		<label for="faculty" class="block text-sm font-medium text-gray-700 mb-1">
			Faculty Approval <span class="text-red-500">*</span>
		</label>
		<select
			id="faculty"
			bind:value={selectedFacultyId}
			class="block w-full px-3 py-2 rounded-md text-sm cursor-pointer"
			style="border: 1px solid #d1d5db; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.9);"
		>
			<option value="">Select Approver</option>
			{#each facultyApprovers as fac}
				<option value={fac.id}>{fac.name} ({fac.department})</option>
			{/each}
		</select>
	</div>

	<!-- Footer Actions -->
	<div class="flex justify-end gap-2 mt-6">
		<button
			class="px-4 py-2 rounded-md text-sm font-medium cursor-pointer"
			style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
			onclick={onClose}
			disabled={submitting}
			type="button"
		>
			Cancel
		</button>
		<button
			class="px-6 py-2 rounded-md text-sm font-medium text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #a855f7, #7e22ce); border: 1px solid rgba(0,0,0,0.2);
			       box-shadow: 0 2px 4px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.4);"
			onclick={handleSubmit}
			disabled={submitting || !canSubmit}
			type="button"
		>
			{submitting ? 'Submitting...' : 'SUBMIT PRESCRIPTION'}
		</button>
	</div>
</div>
		</div>
	</div>
</div>
