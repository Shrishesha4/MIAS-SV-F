<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import { clinicsApi } from '$lib/api/clinics';
	import { insuranceCategoriesApi, type PublicInsuranceCategory } from '$lib/api/insuranceCategories';
	import { Camera, ImagePlus, Move, Building2, CheckCircle2, RotateCcw } from 'lucide-svelte';

	const clinicId = page.params.clinicId;

	// ─── State ──────────────────────────────────────────────
	let clinicInfo = $state<{ id: string; name: string; department: string; location?: string; faculty_name?: string } | null>(null);
	let insuranceCategories = $state<PublicInsuranceCategory[]>([]);
	let loadError = $state('');
	let loadingPage = $state(true);
	let submitting = $state(false);
	let done = $state(false);
	let submitError = $state('');
	let currentStep = $state(1); // 1=details, 2=insurance, 3=account

	// Step 1 – personal details
	let name = $state('');
	let dob = $state('');
	let gender = $state('MALE');
	let bloodGroup = $state('O+');
	let phone = $state('');
	let address = $state('');

	// Step 2 – insurance & category
	let selectedInsuranceCategoryId = $state('');
	let selectedPatientCategoryId = $state('');
	const selectedInsurance = $derived(insuranceCategories.find(c => c.id === selectedInsuranceCategoryId));
	const availablePatientCategories = $derived(selectedInsurance?.patient_categories ?? []);

	// Step 3 – account
	let username = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');

	// Photo
	let patientPhoto = $state('');
	let photoGalleryInput = $state<HTMLInputElement>();
	let pendingPhotoSrc = $state('');
	let cropImage = $state<HTMLImageElement | null>(null);
	let showPhotoCropper = $state(false);
	let cropZoom = $state(1);
	let cropOffsetX = $state(0);
	let cropOffsetY = $state(0);
	let cropDragActive = $state(false);
	let cropDragStartX = 0;
	let cropDragStartY = 0;
	let cropStartOffsetX = 0;
	let cropStartOffsetY = 0;
	const CROP_FRAME_SIZE = 240;
	const CROP_EXPORT_SIZE = 720;
	const cropBaseScale = $derived.by(() => {
		if (!cropImage) return 1;
		return Math.max(CROP_FRAME_SIZE / cropImage.naturalWidth, CROP_FRAME_SIZE / cropImage.naturalHeight);
	});
	const cropDisplayScale = $derived(cropBaseScale * cropZoom);

	// Camera modal
	let showCameraModal = $state(false);
	let cameraStream = $state<MediaStream | null>(null);
	let cameraVideoEl = $state<HTMLVideoElement | null>(null);
	let cameraFacing = $state<'environment' | 'user'>('environment');

	// ─── Load ────────────────────────────────────────────────
	onMount(async () => {
		try {
			const [clinics, cats] = await Promise.all([
				clinicsApi.listClinicsPublic(),
				insuranceCategoriesApi.listPublicCategories(),
			]);
			clinicInfo = clinics.find(c => c.id === clinicId) ?? null;
			if (!clinicInfo) {
				loadError = 'Clinic not found or is no longer active.';
			}
			insuranceCategories = cats;
		} catch {
			loadError = 'Failed to load clinic information.';
		} finally {
			loadingPage = false;
		}
	});

	// ─── Validation ──────────────────────────────────────────
	function validateStep(n: number): string {
		if (n === 1) {
			if (!name.trim()) return 'Full name is required';
			if (!dob) return 'Date of birth is required';
			if (!phone.trim() || phone.replace(/\D/g, '').length < 10) return 'Valid phone number required';
		}
		if (n === 3) {
			if (!username.trim()) return 'Username is required';
			if (!email.trim() || !email.includes('@')) return 'Valid email required';
			if (password.length < 6) return 'Password must be at least 6 characters';
			if (password !== confirmPassword) return 'Passwords do not match';
		}
		return '';
	}

	function nextStep() {
		const err = validateStep(currentStep);
		if (err) { submitError = err; return; }
		submitError = '';
		currentStep++;
	}

	// ─── Photo (camera) ──────────────────────────────────────
	async function openCamera() {
		if (!navigator.mediaDevices?.getUserMedia) { photoGalleryInput?.click(); return; }
		try {
			cameraStream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: cameraFacing, width: { ideal: 1280 }, height: { ideal: 720 } },
				audio: false,
			});
			showCameraModal = true;
		} catch { photoGalleryInput?.click(); }
	}

	function stopCamera() {
		cameraStream?.getTracks().forEach(t => t.stop());
		cameraStream = null;
		showCameraModal = false;
	}

	async function flipCamera() {
		cameraFacing = cameraFacing === 'environment' ? 'user' : 'environment';
		cameraStream?.getTracks().forEach(t => t.stop());
		try {
			cameraStream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: cameraFacing, width: { ideal: 1280 }, height: { ideal: 720 } },
				audio: false,
			});
		} catch { stopCamera(); }
	}

	function snapPhoto() {
		const video = cameraVideoEl;
		if (!video) return;
		const canvas = document.createElement('canvas');
		canvas.width = video.videoWidth || 640;
		canvas.height = video.videoHeight || 480;
		canvas.getContext('2d')!.drawImage(video, 0, 0);
		stopCamera();
		openPhotoCropperFromDataUrl(canvas.toDataURL('image/jpeg', 0.92));
	}

	function bindCameraStream(node: HTMLVideoElement, stream: MediaStream | null) {
		cameraVideoEl = node;
		if (stream) node.srcObject = stream;
		return {
			update(s: MediaStream | null) { node.srcObject = s; },
			destroy() { cameraVideoEl = null; },
		};
	}

	async function handlePhotoFile(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		try {
			const dataUrl = await new Promise<string>((resolve, reject) => {
				const r = new FileReader();
				r.onload = () => resolve(String(r.result || ''));
				r.onerror = reject;
				r.readAsDataURL(file);
			});
			await openPhotoCropperFromDataUrl(dataUrl);
		} catch { /* ignore */ } finally { input.value = ''; }
	}

	async function openPhotoCropperFromDataUrl(dataUrl: string) {
		if (!dataUrl.startsWith('data:image/')) return;
		const image = await new Promise<HTMLImageElement>((resolve, reject) => {
			const img = new Image();
			img.onload = () => resolve(img);
			img.onerror = reject;
			img.src = dataUrl;
		});
		pendingPhotoSrc = dataUrl;
		cropImage = image;
		cropZoom = 1; cropOffsetX = 0; cropOffsetY = 0;
		showPhotoCropper = true;
	}

	function startCropDrag(e: PointerEvent) {
		cropDragActive = true;
		cropDragStartX = e.clientX; cropDragStartY = e.clientY;
		cropStartOffsetX = cropOffsetX; cropStartOffsetY = cropOffsetY;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}
	function moveCropDrag(e: PointerEvent) {
		if (!cropDragActive) return;
		cropOffsetX = cropStartOffsetX + (e.clientX - cropDragStartX) / cropDisplayScale;
		cropOffsetY = cropStartOffsetY + (e.clientY - cropDragStartY) / cropDisplayScale;
	}
	function endCropDrag() { cropDragActive = false; }

	function applyPhotoCrop() {
		const canvas = document.createElement('canvas');
		canvas.width = CROP_EXPORT_SIZE; canvas.height = CROP_EXPORT_SIZE;
		const ctx = canvas.getContext('2d')!;
		const scale = cropDisplayScale;
		const visibleW = CROP_FRAME_SIZE / scale;
		const visibleH = CROP_FRAME_SIZE / scale;
		const centerX = cropImage!.naturalWidth / 2 - cropOffsetX;
		const centerY = cropImage!.naturalHeight / 2 - cropOffsetY;
		const sx = centerX - visibleW / 2;
		const sy = centerY - visibleH / 2;
		ctx.drawImage(cropImage!, sx, sy, visibleW, visibleH, 0, 0, CROP_EXPORT_SIZE, CROP_EXPORT_SIZE);
		patientPhoto = canvas.toDataURL('image/jpeg', 0.88);
		showPhotoCropper = false;
	}

	// ─── Submit ───────────────────────────────────────────────
	async function handleSubmit() {
		const err = validateStep(3);
		if (err) { submitError = err; return; }
		submitting = true;
		submitError = '';
		try {
			await authApi.signup({
				username: username.trim(),
				password,
				email: email.trim(),
				role: 'PATIENT',
				preferred_clinic_id: clinicId,
				patient_data: {
					name: name.trim(),
					date_of_birth: dob,
					gender,
					blood_group: bloodGroup,
					phone: phone.trim(),
					email: email.trim(),
					address: address.trim() || undefined,
					photo: patientPhoto || undefined,
					insurance_category_id: selectedInsuranceCategoryId || undefined,
					patient_category_id: selectedPatientCategoryId || undefined,
				},
			});
			done = true;
		} catch (e: any) {
			submitError = e?.response?.data?.detail || 'Registration failed. Please try again.';
		} finally {
			submitting = false;
		}
	}

	const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'];
	const genders = ['MALE', 'FEMALE', 'OTHER'];
</script>

<svelte:head>
	<title>{clinicInfo?.name ?? 'Clinic'} — Patient Registration</title>
</svelte:head>

<div class="min-h-screen flex flex-col" style="background: linear-gradient(160deg, #e8f0ff 0%, #f5f8ff 45%, #eef3ff 100%);">
	<!-- Header -->
	<div class="px-4 pt-8 pb-4 text-center">
		<div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl" style="background: linear-gradient(to bottom, #3b82f6, #1d4ed8); box-shadow: 0 6px 18px rgba(29,78,216,0.32);">
			<Building2 class="h-7 w-7 text-white" />
		</div>
		{#if loadingPage}
			<div class="h-5 w-40 mx-auto rounded-full bg-blue-100 animate-pulse"></div>
		{:else if clinicInfo}
			<h1 class="text-xl font-extrabold text-slate-900">{clinicInfo.name}</h1>
			<p class="mt-1 text-sm text-slate-500">{clinicInfo.department}{clinicInfo.location ? ` · ${clinicInfo.location}` : ''}</p>
			<p class="mt-2 text-xs font-semibold uppercase tracking-widest text-blue-500">Patient Check-In Registration</p>
		{:else}
			<p class="text-base font-semibold text-rose-500">{loadError}</p>
		{/if}
	</div>

	{#if !loadingPage && clinicInfo && !done}
		<!-- Progress pills -->
		<div class="flex justify-center gap-2 px-4 mb-6">
			{#each [1, 2, 3] as s}
				<div class="h-1.5 flex-1 max-w-[72px] rounded-full transition-colors" style={currentStep >= s ? 'background:#3b82f6' : 'background:#dbe4f0'}></div>
			{/each}
		</div>

		<div class="flex-1 px-4 pb-10 max-w-md mx-auto w-full">
			<div class="rounded-[24px] p-5" style="background: rgba(255,255,255,0.94); box-shadow: 0 8px 28px rgba(15,23,42,0.1), inset 0 1px 0 rgba(255,255,255,0.9); border: 1px solid rgba(200,214,230,0.4);">

				{#if currentStep === 1}
					<!-- Step 1: Personal details -->
					<p class="text-base font-bold text-slate-900 mb-4">Personal Details</p>

					<!-- Photo -->
					<div class="flex items-center gap-3 mb-5">
						{#if patientPhoto}
							<img src={patientPhoto} alt="patient" class="h-16 w-16 rounded-2xl object-cover" style="box-shadow: 0 2px 8px rgba(0,0,0,0.12);" />
						{:else}
							<div class="h-16 w-16 rounded-2xl flex items-center justify-center shrink-0" style="background: #f0f4fa; border: 1.5px dashed rgba(100,130,180,0.4);">
								<Camera class="h-6 w-6 text-slate-400" />
							</div>
						{/if}
						<div class="flex gap-2">
							<button type="button" onclick={() => openCamera()} class="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-white cursor-pointer" style="background: linear-gradient(to bottom, #4d90fe, #3b7aed); box-shadow: 0 2px 8px rgba(59,122,237,0.28);">
								<Camera class="h-3.5 w-3.5" /> Take
							</button>
							<button type="button" onclick={() => photoGalleryInput?.click()} class="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 cursor-pointer" style="background: #f0f4fa; border: 1px solid rgba(15,23,42,0.1);">
								<ImagePlus class="h-3.5 w-3.5" /> Upload
							</button>
							{#if patientPhoto}
								<button type="button" onclick={() => openPhotoCropperFromDataUrl(patientPhoto)} class="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-slate-500 cursor-pointer" style="background: #f0f4fa; border: 1px solid rgba(15,23,42,0.1);">
									<Move class="h-3.5 w-3.5" />
								</button>
							{/if}
						</div>
						<input bind:this={photoGalleryInput} type="file" accept="image/*" class="hidden" onchange={handlePhotoFile} />
					</div>

					<div class="space-y-3">
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Full Name *</label>
							<input bind:value={name} placeholder="Patient full name" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
						</div>
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-xs font-semibold text-slate-600 mb-1">Date of Birth *</label>
								<input type="date" bind:value={dob} class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
							</div>
							<div>
								<label class="block text-xs font-semibold text-slate-600 mb-1">Gender *</label>
								<select bind:value={gender} class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;">
									{#each genders as g}<option>{g}</option>{/each}
								</select>
							</div>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-xs font-semibold text-slate-600 mb-1">Blood Group</label>
								<select bind:value={bloodGroup} class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;">
									{#each bloodGroups as bg}<option>{bg}</option>{/each}
								</select>
							</div>
							<div>
								<label class="block text-xs font-semibold text-slate-600 mb-1">Phone *</label>
								<input type="tel" bind:value={phone} placeholder="10-digit number" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
							</div>
						</div>
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Address</label>
							<textarea bind:value={address} rows="2" placeholder="Optional" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400 resize-none" style="border-color: rgba(0,0,0,0.12); background: #fafcff;"></textarea>
						</div>
					</div>

				{:else if currentStep === 2}
					<!-- Step 2: Insurance & patient type -->
					<p class="text-base font-bold text-slate-900 mb-4">Insurance & Patient Type</p>
					<p class="text-xs text-slate-500 mb-4">Select your insurance provider and patient category. This determines your billing and the clinic you'll be assigned to.</p>

					{#if insuranceCategories.length === 0}
						<p class="text-sm text-slate-400 text-center py-4">No insurance categories configured.</p>
					{:else}
						<div class="space-y-2 mb-4">
							{#each insuranceCategories as cat}
								<button
									type="button"
									onclick={() => { selectedInsuranceCategoryId = cat.id; selectedPatientCategoryId = ''; }}
									class="w-full flex items-center gap-3 rounded-2xl border p-3 cursor-pointer text-left transition-all"
									style={selectedInsuranceCategoryId === cat.id
										? `border-color: ${cat.color_primary}; background: ${cat.color_secondary}20;`
										: 'border-color: rgba(0,0,0,0.1); background: #fafcff;'}
								>
									<div class="h-9 w-9 rounded-xl flex items-center justify-center shrink-0 text-white text-sm font-bold"
										style="background: linear-gradient(to bottom, {cat.color_primary}, {cat.color_secondary ?? cat.color_primary});">
										{cat.custom_badge_symbol ?? cat.name[0]}
									</div>
									<div class="flex-1 min-w-0">
										<p class="text-sm font-semibold text-slate-800">{cat.name}</p>
										{#if cat.description}<p class="text-xs text-slate-500 truncate">{cat.description}</p>{/if}
									</div>
									{#if selectedInsuranceCategoryId === cat.id}
										<CheckCircle2 class="h-4 w-4 shrink-0" style="color: {cat.color_primary}" />
									{/if}
								</button>
							{/each}
						</div>

						{#if availablePatientCategories.length > 0}
							<div class="mt-3">
								<p class="text-xs font-semibold text-slate-600 mb-2">Patient Category</p>
								<div class="grid grid-cols-2 gap-2">
									{#each availablePatientCategories as pc}
										<button
											type="button"
											onclick={() => selectedPatientCategoryId = pc.id}
											class="rounded-xl border p-2.5 text-xs font-semibold cursor-pointer transition-all text-left"
											style={selectedPatientCategoryId === pc.id
												? 'border-color: #3b82f6; background: #eff6ff; color: #1d4ed8;'
												: 'border-color: rgba(0,0,0,0.1); background: #fafcff; color: #475569;'}
										>
											{pc.name}
										</button>
									{/each}
								</div>
							</div>
						{/if}
					{/if}

				{:else if currentStep === 3}
					<!-- Step 3: Account credentials -->
					<p class="text-base font-bold text-slate-900 mb-4">Create Account</p>
					<div class="space-y-3">
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Username *</label>
							<input bind:value={username} placeholder="Choose a username" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Email *</label>
							<input type="email" bind:value={email} placeholder="your@email.com" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Password *</label>
							<input type="password" bind:value={password} placeholder="Min. 6 characters" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-slate-600 mb-1">Confirm Password *</label>
							<input type="password" bind:value={confirmPassword} placeholder="Repeat password" class="w-full rounded-xl border px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-400" style="border-color: rgba(0,0,0,0.12); background: #fafcff;" />
						</div>
					</div>
				{/if}

				{#if submitError}
					<p class="mt-3 text-xs text-red-500">{submitError}</p>
				{/if}

				<!-- Nav buttons -->
				<div class="mt-5 flex gap-2">
					{#if currentStep > 1}
						<button type="button" onclick={() => { currentStep--; submitError = ''; }} class="flex-1 rounded-[999px] py-3 text-sm font-bold text-slate-600 cursor-pointer" style="background: #f0f4fa; border: 1px solid rgba(0,0,0,0.08);">
							Back
						</button>
					{/if}
					{#if currentStep < 3}
						<button type="button" onclick={nextStep} class="flex-1 rounded-[999px] py-3 text-sm font-bold text-white cursor-pointer" style="background: linear-gradient(to bottom, #4d90fe, #1d4ed8); box-shadow: 0 4px 14px rgba(29,78,216,0.3);">
							Continue
						</button>
					{:else}
						<button type="button" onclick={handleSubmit} disabled={submitting} class="flex-1 rounded-[999px] py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #4d90fe, #1d4ed8); box-shadow: 0 4px 14px rgba(29,78,216,0.3);">
							{submitting ? 'Registering…' : 'Complete Registration'}
						</button>
					{/if}
				</div>
			</div>

			<p class="mt-4 text-center text-xs text-slate-400">
				Already registered? <a href="/login" class="font-semibold text-blue-500 hover:underline">Sign in</a>
			</p>
		</div>

	{:else if done}
		<!-- Success screen -->
		<div class="flex-1 flex flex-col items-center justify-center px-6 text-center">
			<div class="mb-4 flex h-20 w-20 items-center justify-center rounded-full" style="background: linear-gradient(to bottom, #34d399, #10b981); box-shadow: 0 8px 24px rgba(16,185,129,0.32);">
				<CheckCircle2 class="h-10 w-10 text-white" />
			</div>
			<h2 class="text-2xl font-extrabold text-slate-900">You're checked in!</h2>
			<p class="mt-2 text-sm text-slate-500 max-w-xs">
				Registration complete. You've been added to <strong>{clinicInfo?.name}</strong>. Please wait to be called.
			</p>
			<a href="/login" class="mt-8 inline-block rounded-[999px] px-8 py-3 text-sm font-bold text-white" style="background: linear-gradient(to bottom, #3b82f6, #1d4ed8); box-shadow: 0 4px 14px rgba(29,78,216,0.3);">
				Sign In to Your Account
			</a>
		</div>
	{:else if loadError}
		<div class="flex-1 flex flex-col items-center justify-center px-6 text-center">
			<p class="text-base font-semibold text-rose-500 mb-4">{loadError}</p>
			<a href="/" class="text-sm text-blue-500 hover:underline">Go to home</a>
		</div>
	{/if}
</div>

<!-- Photo cropper -->
{#if showPhotoCropper && cropImage}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-4">
		<div class="w-full max-w-sm rounded-[28px] bg-white p-4" style="box-shadow: 0 18px 48px rgba(15,23,42,0.28);">
			<div class="mb-4 flex items-start justify-between gap-3">
				<div>
					<p class="text-base font-bold text-slate-900">Crop photo</p>
					<p class="text-xs text-slate-500 mt-0.5">Drag to reposition · scroll to zoom</p>
				</div>
				<button type="button" onclick={() => showPhotoCropper = false} class="text-xs font-semibold text-slate-500 cursor-pointer hover:text-slate-700 rounded-full px-3 py-1.5">Close</button>
			</div>
			<div class="flex justify-center mb-4">
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="relative overflow-hidden rounded-[28px] bg-slate-100 touch-none select-none"
					style={`width: ${CROP_FRAME_SIZE}px; height: ${CROP_FRAME_SIZE}px;`}
					onpointerdown={startCropDrag}
					onpointermove={moveCropDrag}
					onpointerup={endCropDrag}
					onpointerleave={endCropDrag}
					onpointercancel={endCropDrag}
					onwheel={(e) => { e.preventDefault(); cropZoom = Math.max(1, Math.min(4, cropZoom - e.deltaY * 0.005)); }}
				>
					<img
						src={pendingPhotoSrc}
						alt="crop"
						draggable="false"
						style={`position: absolute; transform-origin: center; transform: scale(${cropDisplayScale}) translate(${cropOffsetX}px, ${cropOffsetY}px); user-select: none;`}
					/>
				</div>
			</div>
			<input type="range" min="1" max="4" step="0.05" bind:value={cropZoom} class="w-full mb-4" />
			<button type="button" onclick={applyPhotoCrop} class="w-full rounded-[999px] py-3 text-sm font-bold text-white cursor-pointer" style="background: linear-gradient(to bottom, #4d90fe, #1d4ed8);">Use Photo</button>
		</div>
	</div>
{/if}

<!-- Camera modal -->
{#if showCameraModal && cameraStream}
	<div class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black">
		<!-- svelte-ignore a11y_media_has_caption -->
		<video use:bindCameraStream={cameraStream} autoplay playsinline class="w-full max-h-[calc(100dvh-140px)] object-cover"></video>
		<div class="absolute inset-x-0 bottom-0 flex items-center justify-between px-8 py-6 bg-gradient-to-t from-black/80 to-transparent">
			<button type="button" onclick={stopCamera} class="w-11 h-11 flex items-center justify-center rounded-full bg-white/20 text-white cursor-pointer">
				<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
			</button>
			<button type="button" onclick={snapPhoto} class="w-16 h-16 rounded-full border-4 border-white bg-white/30 cursor-pointer hover:bg-white/50 transition-colors" aria-label="Take photo"></button>
			<button type="button" onclick={flipCamera} class="w-11 h-11 flex items-center justify-center rounded-full bg-white/20 text-white cursor-pointer">
				<RotateCcw class="w-5 h-5" />
			</button>
		</div>
	</div>
{/if}
