<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import { authStore } from '$lib/stores/auth';
	import { nurseApi } from '$lib/api/nurse';
	import { toastStore } from '$lib/stores/toast';

	let hospital = $state('');
	let ward = $state('');
	let shift = $state('');
	let loading = $state(false);
	let wards = $state.raw<string[]>([]);
	let wardsLoading = $state(false);

	const HOSPITALS = [
		'Saveetha Medical College Hospital',
		'Saveetha Dental College Hospital',
		'Saveetha General Hospital',
	];

	const SHIFTS = [
		'Morning Shift (08:00-16:00)',
		'Evening Shift (16:00-00:00)',
		'Night Shift (00:00-08:00)',
	];

	async function loadAvailableWards() {
		wardsLoading = true;
		try {
			wards = await nurseApi.getAvailableWards();
		} catch (error: any) {
			console.error('Error loading wards:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to load wards', 'error');
			wards = [];
		} finally {
			wardsLoading = false;
		}
	}

	async function handleSubmit() {
		if (!hospital || !ward) {
			toastStore.addToast('Please select hospital and ward', 'error');
			return;
		}

		loading = true;
		try {
			await nurseApi.selectStation({
				hospital,
				ward,
				shift: shift || undefined,
			});

			toastStore.addToast('Station selected successfully!', 'success');
			goto('/nurse-station');
		} catch (error: any) {
			console.error('Error selecting station:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to select station', 'error');
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const auth = get(authStore);
		if (auth.role !== 'NURSE') {
			goto('/dashboard');
			return;
		}
		void loadAvailableWards();
	});
</script>

<div class="min-h-screen p-4 flex flex-col items-center justify-center">
	<div class="w-full max-w-md">
		<div class="mb-6 text-center">
			<div
				class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(0,0,0,0.2);"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="32"
					height="32"
					viewBox="0 0 24 24"
					fill="none"
					stroke="white"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
					<circle cx="12" cy="7" r="4" />
				</svg>
			</div>
			<h1 class="text-2xl font-bold text-gray-800 mb-2">Welcome, Nurse!</h1>
			<p class="text-gray-600">Please select your hospital and station to get started</p>
		</div>

		<AquaCard>
			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
				<!-- svelte-ignore a11y_label_has_associated_control -->
				<div class="space-y-4">
					<!-- Hospital Selection -->
					<div>
						<label class="block text-sm font-semibold text-gray-700 mb-2">Hospital *</label>
						<select
							bind:value={hospital}
							class="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-blue-500 focus:outline-none transition-colors"
							style="background: linear-gradient(to bottom, #ffffff, #f9fafb);"
							required
						>
							<option value="">Select a hospital</option>
							{#each HOSPITALS as h}
								<option value={h}>{h}</option>
							{/each}
						</select>
					</div>

					<!-- Ward Selection -->
					<div>
						<label class="block text-sm font-semibold text-gray-700 mb-2">Ward / Station *</label>
						<select
							bind:value={ward}
							disabled={wardsLoading || wards.length === 0}
							class="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-blue-500 focus:outline-none transition-colors"
							style="background: linear-gradient(to bottom, #ffffff, #f9fafb);"
							required
						>
							<option value="">{wardsLoading ? 'Loading wards...' : (wards.length === 0 ? 'No wards available' : 'Select a ward')}</option>
							{#each wards as w}
								<option value={w}>{w}</option>
							{/each}
						</select>
						{#if !wardsLoading && wards.length === 0}
							<p class="mt-2 text-xs text-gray-500">No created wards are available yet.</p>
						{/if}
					</div>

					<!-- Shift Selection (Optional) -->
					<div>
						<label class="block text-sm font-semibold text-gray-700 mb-2">Shift (Optional)</label>
						<select
							bind:value={shift}
							class="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-blue-500 focus:outline-none transition-colors"
							style="background: linear-gradient(to bottom, #ffffff, #f9fafb);"
						>
							<option value="">Select a shift</option>
							{#each SHIFTS as s}
								<option value={s}>{s}</option>
							{/each}
						</select>
					</div>

					<div class="pt-4">
						<AquaButton type="submit" variant="primary" size="lg" fullWidth={true} {loading}>
							Continue to Nurse Station
						</AquaButton>
					</div>
				</div>
			</form>
		</AquaCard>

		<p class="text-center text-xs text-gray-500 mt-4">
			You can change your station assignment later in the profile settings
		</p>
	</div>
</div>

<style>
	select {
		-webkit-appearance: none;
		-moz-appearance: none;
		appearance: none;
		background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
		background-position: right 0.75rem center;
		background-repeat: no-repeat;
		background-size: 1.5em 1.5em;
		padding-right: 2.5rem;
	}
</style>
