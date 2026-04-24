<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { get } from 'svelte/store';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import {
		nutritionistApi,
		type NutritionistPatient,
		type NutritionistPortalData,
		type NutritionistProfile,
	} from '$lib/api/nutritionists';
	import {
		ChefHat,
		ChevronDown,
		Clock3,
		FileText,
		LogOut,
		MapPin,
		Save,
		Search,
		UserCheck,
		Users,
	} from 'lucide-svelte';

	const auth = get(authStore);

	let loading = $state(true);
	let checkingIn = $state(false);
	let checkingOut = $state(false);
	let savingPatientId = $state<string | null>(null);
	let searchQuery = $state('');
	let expandedPatientId = $state<string | null>(null);
	let profile = $state.raw<NutritionistProfile | null>(null);
	let portal = $state.raw<NutritionistPortalData | null>(null);
	let noteDrafts = $state<Record<string, string>>({});
	let updatingStatusPatientId = $state<string | null>(null);

	function getPatientKey(patient: NutritionistPatient) {
		return patient.patient_db_id ?? patient.id;
	}

	function getSavedNote(patient: NutritionistPatient) {
		return patient.nutrition_note.trim();
	}

	function getDraftNote(patient: NutritionistPatient) {
		return (noteDrafts[getPatientKey(patient)] ?? '').trim();
	}

	function hasSavedNote(patient: NutritionistPatient) {
		return getSavedNote(patient).length > 0;
	}

	function hasUnsavedDraft(patient: NutritionistPatient) {
		const draft = getDraftNote(patient);
		return draft.length > 0 && draft !== getSavedNote(patient);
	}

	function getVisiblePreview(patient: NutritionistPatient) {
		const draft = getDraftNote(patient);
		const content = draft || getSavedNote(patient);
		return content || 'Awaiting nutritionist assessment and diet instructions.';
	}

	function isCompleted(patient: NutritionistPatient) {
		return patient.nutrition_note_is_completed;
	}

	function getCompletionStatusLabel(patient: NutritionistPatient) {
		if (isCompleted(patient)) {
			return 'Completed';
		}
		if (hasSavedNote(patient)) {
			return 'Note saved';
		}
		return 'No note yet';
	}

	function getCompletionTimestampText(patient: NutritionistPatient) {
		if (isCompleted(patient)) {
			return patient.nutrition_note_completed_at
				? `Marked done ${new Date(patient.nutrition_note_completed_at).toLocaleTimeString('en-US', {
						hour: '2-digit',
						minute: '2-digit',
					})}`
				: 'Marked done';
		}
		if (hasSavedNote(patient)) {
			return formatSavedAt(patient.nutrition_note_updated_at);
		}
		return 'Pending note';
	}

	function getPrimaryActionLabel(patient: NutritionistPatient) {
		return isCompleted(patient) ? 'Reopen' : 'Mark Done';
	}

	function syncDrafts(patients: NutritionistPatient[]) {
		const nextDrafts: Record<string, string> = {};
		for (const patient of patients) {
			const key = getPatientKey(patient);
			nextDrafts[key] = patient.nutrition_note ?? '';
		}
		noteDrafts = nextDrafts;
	}

	function syncExpandedPatient(patients: NutritionistPatient[]) {
		if (patients.length === 0) {
			expandedPatientId = null;
			return;
		}

		if (!expandedPatientId || !patients.some((patient) => getPatientKey(patient) === expandedPatientId)) {
			expandedPatientId = getPatientKey(patients[0]);
		}
	}

	function getErrorMessage(error: unknown, fallback: string) {
		if (typeof error === 'object' && error !== null && 'response' in error) {
			const response = (error as { response?: { data?: { detail?: unknown } } }).response;
			if (typeof response?.data?.detail === 'string' && response.data.detail.trim()) {
				return response.data.detail;
			}
		}
		return fallback;
	}

	const checkedIn = $derived(Boolean(portal?.checked_in));
	const patients = $derived(portal?.patients ?? []);
	const pendingDietCount = $derived(patients.filter((patient) => !isCompleted(patient)).length);
	const completedDietCount = $derived(patients.filter((patient) => isCompleted(patient)).length);

	const filteredPatients = $derived.by(() => {
		const query = searchQuery.trim().toLowerCase();
		return [...patients]
			.filter((patient) => {
				if (!query) return true;
				return [
					patient.patient_name,
					patient.patient_id,
					patient.provider_name,
					patient.assigned_student_name,
					patient.category,
					getVisiblePreview(patient),
				]
					.filter(Boolean)
					.some((value) => String(value).toLowerCase().includes(query));
			})
			.sort((left, right) => {
				const completionDifference = Number(isCompleted(left)) - Number(isCompleted(right));
				if (completionDifference !== 0) return completionDifference;
				const noteDifference = Number(hasSavedNote(right)) - Number(hasSavedNote(left));
				if (noteDifference !== 0) return noteDifference;
				return left.patient_name.localeCompare(right.patient_name);
			});
	});

	function formatTime(timestamp: string | null) {
		if (!timestamp) return 'Not checked in';
		return new Date(timestamp).toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	function formatSavedAt(timestamp: string | null) {
		if (!timestamp) return 'Pending';
		return `Saved ${new Date(timestamp).toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
		})}`;
	}

	async function loadPortal() {
		loading = true;
		try {
			const [nextProfile, nextPortal] = await Promise.all([
				nutritionistApi.getMe(),
				nutritionistApi.getPatients(),
			]);
			profile = nextProfile;
			portal = nextPortal;
			syncDrafts(nextPortal.patients);
			syncExpandedPatient(nextPortal.patients);
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to load nutritionist portal'), 'error');
		} finally {
			loading = false;
		}
	}

	async function refreshPatients() {
		try {
			const nextPortal = await nutritionistApi.getPatients();
			portal = nextPortal;
			syncDrafts(nextPortal.patients);
			syncExpandedPatient(nextPortal.patients);
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to refresh clinic patients'), 'error');
		}
	}

	async function handleCheckIn() {
		checkingIn = true;
		try {
			const result = await nutritionistApi.checkIn();
			toastStore.addToast(`Checked in to ${result.clinic_name}`, 'success');
			await loadPortal();
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to check in'), 'error');
		} finally {
			checkingIn = false;
		}
	}

	async function handleCheckOut() {
		if (!portal?.active_session) return;
		checkingOut = true;
		try {
			const result = await nutritionistApi.checkOut(portal.active_session.id);
			toastStore.addToast(`Checked out from ${result.clinic_name}`, 'success');
			await loadPortal();
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to check out'), 'error');
		} finally {
			checkingOut = false;
		}
	}

	async function saveNote(patient: NutritionistPatient, options?: { successMessage?: string; skipRefresh?: boolean }) {
		const key = getPatientKey(patient);
		const content = getDraftNote(patient);
		if (!content) {
			toastStore.addToast('Enter nutrition notes before saving', 'error');
			return false;
		}
		if (!checkedIn) {
			toastStore.addToast('Check in to your clinic before saving notes', 'error');
			return false;
		}

		savingPatientId = key;
		try {
			await nutritionistApi.saveNote(key, content);
			toastStore.addToast(options?.successMessage ?? `Saved notes for ${patient.patient_name}`, 'success');
			if (!options?.skipRefresh) {
				await refreshPatients();
			}
			expandedPatientId = key;
			return true;
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to save nutrition note'), 'error');
			return false;
		} finally {
			savingPatientId = null;
		}
	}

	async function updateNoteStatus(patient: NutritionistPatient, isCompletedValue: boolean) {
		const key = getPatientKey(patient);
		if (!checkedIn) {
			toastStore.addToast('Check in to your clinic before updating completion status', 'error');
			return;
		}

		updatingStatusPatientId = key;
		try {
			await nutritionistApi.updateNoteStatus(key, isCompletedValue);
			toastStore.addToast(
				isCompletedValue
					? `Marked ${patient.patient_name} as done`
					: `Reopened ${patient.patient_name} for follow-up`,
				'success',
			);
			await refreshPatients();
			expandedPatientId = key;
		} catch (error: unknown) {
			toastStore.addToast(getErrorMessage(error, 'Failed to update completion status'), 'error');
		} finally {
			updatingStatusPatientId = null;
		}
	}

	async function handlePatientAction(patient: NutritionistPatient) {
		const key = getPatientKey(patient);

		if (isCompleted(patient)) {
			await updateNoteStatus(patient, false);
			return;
		}

		if (!checkedIn) {
			toastStore.addToast('Check in to your clinic before marking a patient done', 'error');
			return;
		}

		const content = getDraftNote(patient);
		if (!content) {
			expandedPatientId = key;
			toastStore.addToast('Add a nutrition note before marking this patient done', 'error');
			return;
		}

		let noteReady = hasSavedNote(patient) && !hasUnsavedDraft(patient);

		if (!noteReady) {
			const noteSaved = await saveNote(patient, {
				successMessage: `Saved notes for ${patient.patient_name}`,
				skipRefresh: true,
			});
			if (!noteSaved) {
				return;
			}
			noteReady = true;
		}

		if (noteReady) {
			await updateNoteStatus(patient, true);
		}
	}

	function togglePatient(patient: NutritionistPatient) {
		const key = getPatientKey(patient);
		expandedPatientId = expandedPatientId === key ? null : key;
	}

	onMount(() => {
		if (auth.role !== 'NUTRITIONIST') {
			void goto(resolve('/dashboard'));
			return;
		}
		void loadPortal();
	});
</script>

<div class="mx-auto max-w-screen-2xl space-y-4 px-4 py-4 md:px-6 md:py-6">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="h-8 w-8 animate-spin rounded-full border-3 border-emerald-500 border-t-transparent"></div>
		</div>
	{:else if profile && portal}
		<div
			class="overflow-hidden rounded-[30px] border border-white/80 px-5 py-5"
			style="background: linear-gradient(180deg, rgba(255,255,255,0.99), rgba(240,247,244,0.96)); box-shadow: 0 18px 40px rgba(15, 23, 42, 0.1);"
		>
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
				<div class="flex min-w-0 items-center gap-4">
					<div
						class="flex h-16 w-16 shrink-0 items-center justify-center rounded-[22px] text-white"
						style="background: linear-gradient(180deg, #16a34a, #059669); box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 12px 22px rgba(5, 150, 105, 0.24);"
					>
						<ChefHat class="h-8 w-8" />
					</div>
					<div class="min-w-0">
						<h1 class="text-2xl font-bold text-slate-900">Nutritionist Portal</h1>
						<p class="mt-1 text-sm font-semibold text-slate-600">
							Dietary Management • {profile.clinic?.department || 'Assigned Clinic'}
						</p>
						<div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
							<span class="font-semibold text-slate-700">{profile.name}</span>
							<span>{profile.nutritionist_id}</span>
							<span>{profile.clinic?.name}</span>
							{#if profile.clinic?.location}
								<span class="flex items-center gap-1"><MapPin class="h-3.5 w-3.5" /> {profile.clinic.location}</span>
							{/if}
							<span class="flex items-center gap-1">
								<Clock3 class="h-3.5 w-3.5" />
								{checkedIn ? `Checked in at ${formatTime(portal.active_session?.checked_in_at ?? null)}` : 'Not checked in yet'}
							</span>
						</div>
					</div>
				</div>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-[auto_auto] lg:min-w-[360px]">
					<div class="rounded-[22px] border border-emerald-100 bg-white/85 px-4 py-4 text-center">
						<p class="text-4xl font-bold text-emerald-600">{pendingDietCount}</p>
						<p class="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Pending Completion</p>
					</div>
					<div class="grid gap-2">
						<div class="grid grid-cols-2 gap-2">
							<div class="rounded-2xl border border-emerald-100 bg-white/80 px-3 py-3 text-center">
								<p class="text-2xl font-bold text-slate-900">{completedDietCount}</p>
								<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Completed</p>
							</div>
							<div class="rounded-2xl border border-emerald-100 bg-white/80 px-3 py-3 text-center">
								<p class="text-2xl font-bold {checkedIn ? 'text-emerald-700' : 'text-amber-600'}">{checkedIn ? 'IN' : 'OUT'}</p>
								<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Status</p>
							</div>
						</div>
						<div class="flex gap-2">
							<button
								type="button"
								onclick={handleCheckIn}
								disabled={checkedIn || checkingIn}
								class="flex-1 rounded-2xl px-4 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
								style="background: linear-gradient(180deg, #34d399, #10b981); box-shadow: 0 8px 14px rgba(16, 185, 129, 0.22);"
							>
								{#if checkingIn}
									Checking in...
								{:else}
									<UserCheck class="mr-1 inline h-4 w-4" /> Check In
								{/if}
							</button>
							<button
								type="button"
								onclick={handleCheckOut}
								disabled={!checkedIn || checkingOut}
								class="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-50"
							>
								{#if checkingOut}
									Checking out...
								{:else}
									<LogOut class="mr-1 inline h-4 w-4" /> Check Out
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div
			class="rounded-[24px] border border-white/80 px-4 py-4"
			style="background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,248,252,0.96)); box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);"
		>
			<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
				<div>
					<p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Assigned Clinic</p>
					<h2 class="mt-1 text-xl font-bold text-slate-900">{profile.clinic?.name}</h2>
					<p class="mt-1 text-sm text-slate-600">Check in like the student clinic flow, save daily nutrition notes, then mark each patient done when the review is complete.</p>
				</div>
				<div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
					<p class="font-semibold uppercase tracking-[0.16em] text-slate-400">Live Session</p>
					<p class="mt-1 text-sm font-semibold text-slate-800">{portal.active_session ? formatTime(portal.active_session.checked_in_at) : 'Waiting for check-in'}</p>
					<p class="mt-1">{profile.clinic?.department} • {profile.clinic?.clinic_type}</p>
				</div>
			</div>

			<div class="relative mt-4">
				<Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search patients or diet types..."
					class="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm text-slate-700 outline-none"
					style="box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.06);"
				/>
			</div>

			{#if !checkedIn}
				<div class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
					Check in to {profile.clinic?.name} before you can mark a patient done, reopen a completed review, or save nutrition notes.
				</div>
			{/if}
		</div>

		<div class="space-y-3">
			<div class="flex items-center justify-between px-1">
				<div>
					<p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Clinic Queue</p>
					<h2 class="mt-1 text-xl font-bold text-slate-900">Today's Nutrition Reviews</h2>
				</div>
				<div class="rounded-full border border-emerald-100 bg-white px-3 py-1 text-xs font-semibold text-emerald-700">
					<Users class="mr-1 inline h-3.5 w-3.5" /> {filteredPatients.length} visible
				</div>
			</div>

			{#if filteredPatients.length === 0}
				<div class="rounded-[28px] border border-dashed border-slate-300 bg-white/80 px-5 py-10 text-center text-sm text-slate-500">
					No clinic patients match the current search.
				</div>
			{:else}
				{#each filteredPatients as patient (getPatientKey(patient))}
					{@const patientKey = getPatientKey(patient)}
					{@const expanded = expandedPatientId === patientKey}
					<div
						class="overflow-hidden rounded-[28px] border border-white/80"
						style="background: linear-gradient(180deg, rgba(255,255,255,0.99), rgba(246,249,252,0.96)); box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);"
					>
						<div class="flex flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
							<div class="flex min-w-0 items-center gap-3">
								<div class="relative shrink-0">
									<Avatar src={patient.photo} name={patient.patient_name} size="md" />
									<div class="absolute bottom-0 right-0 h-3.5 w-3.5 rounded-full border-2 border-white {isCompleted(patient) ? 'bg-emerald-500' : hasSavedNote(patient) ? 'bg-sky-500' : 'bg-amber-400'}"></div>
								</div>
								<div class="min-w-0">
									<div class="flex flex-wrap items-center gap-2">
										<h3 class="truncate text-xl font-bold text-slate-900">{patient.patient_name}</h3>
										<span class="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-700">{patient.patient_id}</span>
									</div>
									<div class="mt-1 flex flex-wrap items-center gap-3 text-sm">
										<span class="font-semibold {isCompleted(patient) ? 'text-emerald-700' : hasSavedNote(patient) ? 'text-sky-700' : 'text-amber-600'}">
											{getCompletionStatusLabel(patient)}
										</span>
										<span class="text-slate-400">•</span>
										<span class="text-slate-500"><Clock3 class="mr-1 inline h-3.5 w-3.5" /> {patient.appointment_time || 'Ongoing'}</span>
										{#if patient.provider_name}
											<span class="text-slate-500">{patient.provider_name}</span>
										{/if}
									</div>
									<p class="mt-2 line-clamp-1 text-sm text-slate-500">{getVisiblePreview(patient)}</p>
								</div>
							</div>

							<div class="flex items-center gap-2 self-end lg:self-center">
								<button
									type="button"
									onclick={() => void handlePatientAction(patient)}
									disabled={!checkedIn || savingPatientId === patientKey || updatingStatusPatientId === patientKey}
									class="rounded-2xl px-4 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
									style="background: linear-gradient(180deg, #60a5fa, #2563eb); box-shadow: 0 10px 18px rgba(37, 99, 235, 0.22);"
								>
									{#if savingPatientId === patientKey}
										Saving...
									{:else if updatingStatusPatientId === patientKey}
										Updating...
									{:else}
										{getPrimaryActionLabel(patient)}
									{/if}
								</button>
								<button
									type="button"
									onclick={() => togglePatient(patient)}
									class="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500 transition hover:text-slate-700"
									aria-label={expanded ? 'Collapse patient note panel' : 'Expand patient note panel'}
									aria-expanded={expanded}
								>
									<ChevronDown class="h-5 w-5 transition-transform {expanded ? 'rotate-180' : ''}" />
								</button>
							</div>
						</div>

						{#if expanded}
							<div class="grid gap-4 border-t border-slate-200/80 px-4 py-4 xl:grid-cols-[1.1fr_0.9fr]">
								<div class="space-y-4">
									<div>
										<p class="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
											<FileText class="h-4 w-4" /> Clinic Context
										</p>
										<div class="mt-3 rounded-[24px] border border-slate-200 bg-white px-4 py-4" style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);">
											<div class="grid gap-3 sm:grid-cols-2">
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Clinic</p>
													<p class="mt-1 text-base font-bold text-slate-900">{profile.clinic?.name}</p>
												</div>
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Current Status</p>
													<p class="mt-1 text-base font-bold text-slate-900">{patient.status}</p>
												</div>
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Provider</p>
													<p class="mt-1 text-base font-bold text-slate-900">{patient.provider_name || 'Not assigned'}</p>
												</div>
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Queue Time</p>
													<p class="mt-1 text-base font-bold text-slate-900">{patient.appointment_time || 'Ongoing'}</p>
												</div>
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Source</p>
													<p class="mt-1 text-base font-bold text-slate-900">{patient.source === 'assignment' ? 'Student assignment' : 'Clinic appointment'}</p>
												</div>
												<div>
													<p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Assigned Student</p>
													<p class="mt-1 text-base font-bold text-slate-900">{patient.assigned_student_name || 'Not assigned'}</p>
												</div>
											</div>
										</div>
									</div>

									<div>
										<p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Daily Coverage</p>
										<div class="mt-3 rounded-[24px] border border-slate-200 bg-white px-4 py-4">
											<div class="space-y-3 text-sm text-slate-600">
												<div class="flex items-start justify-between gap-3">
													<span class="font-semibold text-slate-500">Category</span>
													<span class="text-right font-semibold text-slate-900">{patient.category || 'General'}</span>
												</div>
												<div class="flex items-start justify-between gap-3">
													<span class="font-semibold text-slate-500">Note status</span>
													<span class="text-right font-semibold {isCompleted(patient) ? 'text-emerald-700' : hasSavedNote(patient) ? 'text-sky-700' : 'text-amber-600'}">
														{getCompletionTimestampText(patient)}
													</span>
												</div>
												<div class="flex items-start justify-between gap-3">
													<span class="font-semibold text-slate-500">Clinic session</span>
													<span class="text-right font-semibold text-slate-900">
														{portal.active_session ? `Started ${formatTime(portal.active_session.checked_in_at)}` : 'Not checked in'}
													</span>
												</div>
											</div>
										</div>
									</div>
								</div>

								<div>
									<p class="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
										<FileText class="h-4 w-4" /> Nutritionist Notes
									</p>
									<div class="mt-3 rounded-[24px] border border-slate-200 bg-white p-4" style="box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);">
										<textarea
											rows="10"
											value={noteDrafts[patientKey] ?? ''}
											oninput={(event) => noteDrafts[patientKey] = (event.currentTarget as HTMLTextAreaElement).value}
											placeholder="Write dietary assessment, feeding advice, restrictions, supplements, counselling points, or follow-up notes here..."
											class="min-h-[260px] w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none"
											style="box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.06);"
											disabled={!checkedIn}
										></textarea>

										<div class="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
											<p class="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
												{hasUnsavedDraft(patient)
													? 'Draft changed — save note separately before marking this patient done.'
													: isCompleted(patient)
														? getCompletionTimestampText(patient)
														: hasSavedNote(patient)
															? 'Note saved — pending completion'
															: 'No note saved yet'}
											</p>
											<button
												type="button"
												onclick={() => void saveNote(patient)}
												disabled={!checkedIn || savingPatientId === patientKey}
												class="rounded-2xl px-4 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
												style="background: linear-gradient(180deg, #10b981, #059669); box-shadow: 0 10px 16px rgba(5, 150, 105, 0.22);"
											>
												{#if savingPatientId === patientKey}
													Saving...
												{:else}
													<Save class="mr-1 inline h-4 w-4" /> {hasSavedNote(patient) ? 'Update Note' : 'Save Note'}
												{/if}
											</button>
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	{:else}
		<div class="rounded-[28px] border border-dashed border-slate-300 bg-white/80 px-5 py-10 text-center text-sm text-slate-500">
			Unable to load the nutritionist portal.
		</div>
	{/if}
</div>
