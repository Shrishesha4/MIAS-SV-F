<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { nurseApi, type Nurse, type NurseClinic } from '$lib/api/nurse';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import { User, MapPin, Phone, Mail, Building2 } from 'lucide-svelte';

	let loading = $state(true);
	let saving = $state(false);
	let nurse = $state<Nurse | null>(null);
	let editMode = $state(false);
	let clinics = $state<NurseClinic[]>([]);
	let clinicsLoading = $state(false);

	let form = $state({
		hospital: '',
		phone: '',
		email: '',
	});

	async function loadProfile() {
		try {
			loading = true;
			const [nurseProfile, availableClinics] = await Promise.all([
				nurseApi.getMe(),
				nurseApi.getClinics().catch((): NurseClinic[] => []),
			]);
			nurse = nurseProfile;
			clinics = availableClinics;
			form = {
				hospital: nurseProfile.hospital || '',
				phone: nurseProfile.phone || '',
				email: nurseProfile.email || '',
			};
		} catch (error: any) {
			console.error('Error loading profile:', error);
			toastStore.addToast('Failed to load profile', 'error');
		} finally {
			loading = false;
		}
	}

	async function handleSave() {
		if (!editMode) {
			editMode = true;
			return;
		}

		try {
			saving = true;
			await nurseApi.updateProfile(form);
			nurse = await nurseApi.getMe();
			toastStore.addToast('Profile updated successfully', 'success');
			editMode = false;
		} catch (error: any) {
			console.error('Error updating profile:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to update profile', 'error');
		} finally {
			saving = false;
		}
	}

	function handleCancel() {
		if (nurse) {
			form = {
				hospital: nurse.hospital || '',
				phone: nurse.phone || '',
				email: nurse.email || '',
			};
		}
		editMode = false;
	}

	onMount(async () => {
		const auth = get(authStore);
		if (auth.role !== 'NURSE') {
			goto('/dashboard');
			return;
		}
		await loadProfile();
	});
</script>

<div class="p-4 max-w-2xl mx-auto space-y-4">
	{#if loading}
		<div class="text-center py-12">
			<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
		</div>
	{:else if nurse}
		<!-- Profile Header -->
		<AquaCard padding={true}>
			{#snippet header()}
				<div class="flex items-center gap-3">
					<div
						class="flex items-center justify-center w-14 h-14 rounded-2xl"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(0,0,0,0.2);"
					>
						<User class="w-7 h-7 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<h1 class="text-xl font-bold text-gray-900 truncate">Nurse Profile</h1>
						<p class="text-sm text-gray-600 truncate">{nurse?.nurse_id}</p>
					</div>
				</div>
			{/snippet}

			<div class="flex items-center gap-4 mt-4">
				<Avatar name={nurse.name} size="lg" />
				<div class="flex-1">
					<h2 class="text-2xl font-bold text-gray-900">{nurse.name}</h2>
					<p class="text-sm text-gray-600">{nurse.nurse_id}</p>
				</div>
			</div>
		</AquaCard>

		<!-- Station Assignment -->
		<AquaCard padding={true}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<MapPin class="w-5 h-5 text-blue-600" />
					<h2 class="text-base font-bold text-gray-800">Station Assignment</h2>
				</div>
			{/snippet}

			<div class="space-y-4">
				<!-- Clinic -->
				<div>
					<div class="flex items-center gap-2 mb-2">
						<Building2 class="w-4 h-4 text-gray-600" />
						<span class="text-sm font-semibold text-gray-700">Clinic</span>
					</div>
					{#if editMode}
						<select
							bind:value={form.hospital}
							disabled={clinicsLoading}
							class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
						>
							<option value="">{clinicsLoading ? 'Loading...' : 'Select Clinic'}</option>
							{#each clinics as clinic}
								<option value={clinic.name}>{clinic.name}{clinic.location ? ` — ${clinic.location}` : ''}</option>
							{/each}
						</select>
					{:else}
						<p class="text-base text-gray-900">{form.hospital || 'Not assigned'}</p>
					{/if}
				</div>
			</div>
		</AquaCard>

		<!-- Contact Information -->
		<AquaCard padding={true}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<Phone class="w-5 h-5 text-blue-600" />
					<h2 class="text-base font-bold text-gray-800">Contact Information</h2>
				</div>
			{/snippet}

			<div class="space-y-4">
				<!-- Phone -->
				<div>
					<div class="flex items-center gap-2 mb-2">
						<Phone class="w-4 h-4 text-gray-600" />
						<span class="text-sm font-semibold text-gray-700">Phone</span>
					</div>
					{#if editMode}
						<input
							type="tel"
							bind:value={form.phone}
							placeholder="+91 90000 00000"
							class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
						/>
					{:else}
						<p class="text-base text-gray-900">{form.phone || 'Not provided'}</p>
					{/if}
				</div>

				<!-- Email -->
				<div>
					<div class="flex items-center gap-2 mb-2">
						<Mail class="w-4 h-4 text-gray-600" />
						<span class="text-sm font-semibold text-gray-700">Email</span>
					</div>
					{#if editMode}
						<input
							type="email"
							bind:value={form.email}
							placeholder="nurse@hospital.com"
							class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
						/>
					{:else}
						<p class="text-base text-gray-900">{form.email || 'Not provided'}</p>
					{/if}
				</div>
			</div>
		</AquaCard>

		<!-- Action Buttons -->
		<div class="flex gap-3">
			{#if editMode}
				<AquaButton variant="secondary" onclick={handleCancel} fullWidth>Cancel</AquaButton>
				<AquaButton variant="primary" onclick={handleSave} loading={saving} fullWidth>
					Save Changes
				</AquaButton>
			{:else}
				<AquaButton variant="primary" onclick={handleSave} fullWidth>Edit Profile</AquaButton>
			{/if}
		</div>
	{/if}
</div>
