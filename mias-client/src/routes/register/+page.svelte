<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { authApi } from '$lib/api/auth';
	import { adminApi } from '$lib/api/admin';
	import { insuranceCategoriesApi, type PublicInsuranceCategory, type PublicClinicInfo } from '$lib/api/insuranceCategories';
	import {
		Phone, ShieldCheck, Fingerprint, BadgeCheck,
		User, Building2, Heart, CreditCard, CircleCheck,
		ArrowLeft, ArrowRight, HeartPulse, Eye, EyeOff,
		CheckCircle2, ChevronRight, Landmark, Briefcase, Wallet, CircleOff
	} from 'lucide-svelte';

	// ─── Step control ──────────────────────────────────────
	// Steps: 1=phone, 2=otp, 3=aadhaar-otp, 4=abha, 5=details, 6=insurance, 7=category?, 8=payment, 9=done
	let step = $state(1);
	const TOTAL_STEPS = 9;
	const progressPct = $derived(Math.round((step / TOTAL_STEPS) * 100));

	// ─── Shared state ──────────────────────────────────────
	let loading = $state(false);
	let error = $state('');

	// Step 1 – phone
	let phone = $state('');

	// Step 2 – OTP
	let otp = $state(['', '', '', '', '', '']);
	let otpInputs = $state<HTMLInputElement[]>([]);

	// Step 3 – Aadhaar OTP (mock)
	let aadhaarNum = $state('');
	let aadhaarOtp = $state(['', '', '', '', '', '']);
	let aadhaarOtpInputs = $state<HTMLInputElement[]>([]);
	let aadhaarConnected = $state(false);

	// Step 4 – ABHA (mocked)
	const mockAbha = $derived(`91-${phone.slice(0,4)}-${phone.slice(4,8)}-${phone.slice(8,10)}12`.replace(/-+$/, ''));

	// Step 5 – Patient details
	let patName = $state('');
	let patDob = $state('');
	let patGender = $state('MALE');
	let patAddress = $state('');
	let patEmail = $state('');
	let patPassword = $state('');
	let showPassword = $state(false);

	// Step 6 – insurance category (fetched from API)
	let insuranceOptions = $state<PublicInsuranceCategory[]>([]);
	let selectedInsuranceId = $state('');
	let insuranceLoading = $state(true);
	const insuranceIcons = {
		shield: ShieldCheck,
		landmark: Landmark,
		briefcase: Briefcase,
		building: Building2,
		wallet: Wallet,
		heart: HeartPulse,
		off: CircleOff,
	} as const;
	const selectedInsurance = $derived.by(() => insuranceOptions.find((option) => option.id === selectedInsuranceId) || null);

	// Step 7 – patient category (fetched from API, conditional)
	let patientCategoryOptions = $state<{ id: string; name: string; description: string | null; color_primary: string; color_secondary: string; registration_fee: number }[]>([]);
	let selectedPatientCategoryId = $state('');
	let patientCategoryLoading = $state(true);
	let showPatientCategoryStep = $derived.by(() => {
		return patientCategoryOptions.length > 1;
	});

	// Step 8 – hospital/clinic (fetched based on insurance category)
	let availableClinics = $state<PublicClinicInfo[]>([]);
	let clinicsLoading = $state(false);
	const selectedPatientCategoryName = $derived.by(() => {
		return patientCategoryOptions.find((c) => c.id === selectedPatientCategoryId)?.name || '';
	});

	const selectedWalkInType = $derived.by(() => {
		if (!selectedPatientCategoryName) return '';
		return `WALKIN_${selectedPatientCategoryName.toUpperCase().replace(/\s+/g, '_').replace(/-/g, '_')}`;
	});

	const eligibleClinics = $derived.by(() => {
		if (!selectedWalkInType) return availableClinics;
		const exact = availableClinics.filter((clinic) => clinic.walk_in_type === selectedWalkInType);
		return exact.length > 0 ? exact : availableClinics;
	});

	// Step 9 – payment (dynamic based on selected clinic)
	let paymentDone = $state(false);

	// Derived registration fee from selected patient category
	const regFee = $derived.by(() => {
		const category = patientCategoryOptions.find((c) => c.id === selectedPatientCategoryId);
		return category?.registration_fee ?? 100;
	});

	// Load insurance categories on mount
	onMount(async () => {
		try {
			insuranceLoading = true;
			const categories = await insuranceCategoriesApi.listPublicCategories();
			console.log('Loaded insurance categories:', categories);
			insuranceOptions = categories;
			// Select first category by default
			if (categories.length > 0) {
				selectedInsuranceId = categories[0].id;
			}
		} catch (e) {
			console.error('Failed to load insurance categories:', e);
			// Fallback to static options
			insuranceOptions = [
				{ id: 'CM_SCHEME', name: 'CM Scheme', description: null, icon_key: 'landmark', custom_badge_symbol: null, color_primary: '#34D399', color_secondary: '#0F766E', patient_categories: [] },
				{ id: 'PRIVATE', name: 'Private Insurance', description: null, icon_key: 'shield', custom_badge_symbol: null, color_primary: '#60A5FA', color_secondary: '#1D4ED8', patient_categories: [] },
				{ id: 'SELF_PAY', name: 'Self Pay', description: null, icon_key: 'wallet', custom_badge_symbol: null, color_primary: '#FB7185', color_secondary: '#E11D48', patient_categories: [] },
			];
			selectedInsuranceId = 'SELF_PAY';
		} finally {
			insuranceLoading = false;
		}
	});

	// Load patient categories when insurance selection changes
	async function loadPatientCategories() {
		if (!selectedInsuranceId) return;
		patientCategoryLoading = true;
		try {
			// Get patient categories from selected insurance category
			const selectedInsurance = insuranceOptions.find(opt => opt.id === selectedInsuranceId);
			if (selectedInsurance && selectedInsurance.patient_categories) {
				// Load registration fees for each patient category
				const categoriesWithFees = await adminApi.getPublicPatientCategories();
				console.log('Loaded patient categories with fees:', categoriesWithFees);
				
				// Merge patient categories from insurance with registration fees
				patientCategoryOptions = selectedInsurance.patient_categories.map(pc => {
					const feeInfo = categoriesWithFees.find(f => f.id === pc.id);
					return {
						id: pc.id,
						name: pc.name,
						description: pc.description,
						color_primary: feeInfo?.color_primary || pc.color_primary || '#60A5FA',
						color_secondary: feeInfo?.color_secondary || pc.color_secondary || '#1D4ED8',
						registration_fee: feeInfo?.registration_fee || 100
					};
				});
				
				if (patientCategoryOptions.length === 1) {
					selectedPatientCategoryId = patientCategoryOptions[0].id;
				} else if (patientCategoryOptions.length > 1) {
					selectedPatientCategoryId = patientCategoryOptions[0].id;
				} else {
					selectedPatientCategoryId = '';
				}
			} else {
				patientCategoryOptions = [];
				selectedPatientCategoryId = '';
			}
		} catch (e) {
			console.error('Failed to load patient categories:', e);
			patientCategoryOptions = [
				{ id: 'CLASSIC', name: 'Classic', description: 'Standard hospital pricing', color_primary: '#60A5FA', color_secondary: '#1D4ED8', registration_fee: 100 },
				{ id: 'PRIME', name: 'Prime', description: 'Priority services', color_primary: '#A78BFA', color_secondary: '#6D28D9', registration_fee: 200 },
				{ id: 'ELITE', name: 'Elite', description: 'Premium services', color_primary: '#FBBF24', color_secondary: '#D97706', registration_fee: 500 },
				{ id: 'COMMUNITY', name: 'Community', description: 'Subsidized services', color_primary: '#34D399', color_secondary: '#047857', registration_fee: 50 },
			];
			selectedPatientCategoryId = 'CLASSIC';
		} finally {
			patientCategoryLoading = false;
		}
	}

	$effect(() => {
		loadPatientCategories();
	});

	// Load clinics when insurance selection changes
	async function loadClinics() {
		if (!selectedInsuranceId || step < 8) return;
		clinicsLoading = true;
		try {
			const clinics = await insuranceCategoriesApi.getCategoryClinics(selectedInsuranceId);
			console.log('Loaded clinics for insurance category:', selectedInsuranceId, clinics);
			availableClinics = clinics;
		} catch (e) {
			console.error('Failed to load clinics:', e);
			// Fallback clinics
			availableClinics = [
				{ 
					config_id: 'default-1', 
					clinic_id: 'SMCH', 
					clinic_name: 'Saveetha Medical College Hospital', 
					clinic_type: 'OP',
					department: 'General Medicine',
					location: 'Main Building',
					walk_in_type: 'WALKIN_CLASSIC',
					walk_in_label: 'Walkin Classic',
					registration_fee: 100 
				},
				{ 
					config_id: 'default-2', 
					clinic_id: 'SDCH', 
					clinic_name: 'Saveetha Dental College Hospital', 
					clinic_type: 'OP',
					department: 'Dental',
					location: 'Dental Block',
					walk_in_type: 'WALKIN_CLASSIC',
					walk_in_label: 'Walkin Classic',
					registration_fee: 100 
				},
			];
		} finally {
			clinicsLoading = false;
		}
	}

	$effect(() => {
		loadClinics();
	});

	// Step 8 – result
	let createdPatientId = $state('');
	let createdUserId = $state('');

	// ─── Navigation helpers ────────────────────────────────
	function next() {
		error = '';
		// Skip patient category step if not needed (only 1 category)
		if (step === 6 && !showPatientCategoryStep) {
			step += 2; // Skip from insurance (6) to payment (8)
		} else {
			step += 1;
		}
	}
	function back() {
		error = '';
		// Skip patient category step if not needed (only 1 category)
		if (step === 8 && !showPatientCategoryStep) {
			step -= 2; // Skip from payment (8) to insurance (6)
		} else if (step > 1) {
			step -= 1;
		} else {
			goto('/login');
		}
	}

	// ─── Step 1: Send OTP ──────────────────────────────────
	function handleSendOtp() {
		if (phone.replace(/\D/g, '').length < 10) {
			error = 'Enter a valid 10-digit mobile number';
			return;
		}
		// mock: just proceed
		next();
	}

	// ─── Step 2: Verify OTP ───────────────────────────────
	function handleOtpInput(e: Event, idx: number) {
		const val = (e.target as HTMLInputElement).value.replace(/\D/g, '');
		otp[idx] = val.slice(-1);
		if (val && idx < 5) otpInputs[idx + 1]?.focus();
	}
	function handleOtpKeydown(e: KeyboardEvent, idx: number) {
		if (e.key === 'Backspace' && !otp[idx] && idx > 0) otpInputs[idx - 1]?.focus();
	}
	function verifyOtp() {
		const full = otp.join('');
		if (full.length < 6) { error = 'Enter the 6-digit OTP'; return; }
		// mock: any OTP works
		next();
	}

	// ─── Step 3: Aadhaar OTP ──────────────────────────────
	function handleAadhaarOtpInput(e: Event, idx: number) {
		const val = (e.target as HTMLInputElement).value.replace(/\D/g, '');
		aadhaarOtp[idx] = val.slice(-1);
		if (val && idx < 5) aadhaarOtpInputs[idx + 1]?.focus();
	}
	function handleAadhaarOtpKeydown(e: KeyboardEvent, idx: number) {
		if (e.key === 'Backspace' && !aadhaarOtp[idx] && idx > 0) aadhaarOtpInputs[idx - 1]?.focus();
	}
	function connectAadhaar() {
		if (aadhaarNum.replace(/\D/g, '').length < 12) { error = 'Enter a valid 12-digit Aadhaar number'; return; }
		const full = aadhaarOtp.join('');
		if (full.length < 6) { error = 'Enter the 6-digit Aadhaar OTP'; return; }
		aadhaarConnected = true;
		// pre-fill name from mock
		if (!patName) patName = 'Patient Name';
	}
	function skipAadhaar() {
		next();
	}

	// ─── Step 5: Patient details ──────────────────────────
	function saveDetails() {
		if (!patName.trim()) { error = 'Full name is required'; return; }
		if (!patDob) { error = 'Date of birth is required'; return; }
		if (!patEmail.trim()) { error = 'Email is required'; return; }
		if (!patPassword || patPassword.length < 6) { error = 'Password must be at least 6 characters'; return; }
		next();
	}

	// ─── Step 9: Pay & Register ───────────────────────────
	async function handlePayAndRegister() {
		loading = true;
		error = '';
		try {
			// Generate unique username from phone + random suffix to prevent collisions
			const phoneDigits = phone.replace(/\D/g, '');
			const randomSuffix = Math.random().toString(36).substring(2, 8); // 6-char random string
			const username = `${phoneDigits}${randomSuffix}`;
			const patientCategory = patientCategoryOptions.find((c) => c.id === selectedPatientCategoryId)?.name
				|| patientCategoryOptions[0]?.name
				|| 'Classic';
			const data = {
				username,
				password: patPassword,
				email: patEmail.trim(),
				role: 'PATIENT' as const,
				patient_data: {
					name: patName.trim(),
					date_of_birth: patDob,
					gender: patGender,
					blood_group: '',
					phone: phone.replace(/\D/g, ''),
					email: patEmail.trim(),
					address: patAddress.trim(),
					abha_id: mockAbha,
					category: patientCategory,
					patient_category_id: selectedPatientCategoryId,
					insurance_category_id: selectedInsuranceId,
				}
			};
			const result = await authApi.signup(data);
			createdUserId = result.user_id;
			// generate mock patient display ID
			createdPatientId = `SMC-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
			paymentDone = true;


			// Auto-login after registration
			const loginResult = await authApi.login(username, patPassword);
			authStore.setTokens(loginResult.access_token, loginResult.refresh_token, loginResult.user_id, loginResult.role);

			// Persist clinic allocation notice for dashboard fullscreen prompt

			step = 9; // show completion screen
		} catch (err: any) {
			error = err?.response?.data?.detail ?? 'Registration failed. Please try again.';
		} finally {
			loading = false;
		}
	}

	// ─── Step 8: Go to dashboard with clinic allocation ──────────────────
	async function goToDashboard() {
		loading = true;
		try {
			goto('/dashboard');
		} catch {
			goto('/login');
		} finally {
			loading = false;
		}
	}

	// ─── OTP box paste support ─────────────────────────────
	function handleOtpPaste(e: ClipboardEvent, arr: string[], inputs: HTMLInputElement[]) {
		const text = e.clipboardData?.getData('text')?.replace(/\D/g, '') ?? '';
		if (text.length >= 6) {
			e.preventDefault();
			arr.splice(0, 6, ...text.slice(0, 6).split(''));
			inputs[5]?.focus();
		}
	}
</script>

<div class="min-h-screen flex flex-col items-center justify-start px-4 py-6"
	 style="background: linear-gradient(160deg, #e8eef8 0%, #dce6f5 100%);">

	<!-- Header -->
	<div class="w-full max-w-sm mb-4 flex items-center gap-3">
		<button
			class="w-9 h-9 rounded-full flex items-center justify-center shrink-0 cursor-pointer transition-opacity hover:opacity-80"
			style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
				   border: 1.5px solid rgba(255,255,255,0.3);
				   box-shadow: 0 1px 3px rgba(0,0,0,0.3);"
			onclick={back}
		>
			<ArrowLeft class="w-4 h-4 text-white" />
		</button>
		<div class="flex-1">
			<p class="text-sm font-bold text-gray-800">New Patient Registration</p>
			{#if step > 1 && step < 10}
				<div class="mt-1.5">
					<div class="flex justify-between text-[10px] text-gray-500 mb-1">
						<span>Registration Progress</span>
						<span>Step {step} of {TOTAL_STEPS - 1}</span>
					</div>
					<div class="h-1.5 rounded-full overflow-hidden" style="background: rgba(0,0,0,0.08);">
						<div
							class="h-full rounded-full transition-all duration-500"
							style="width: {progressPct}%; background: linear-gradient(to right, #4d90fe, #3b7aed);"
						></div>
					</div>
				</div>
			{/if}
		</div>
		<div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
			 style="background: linear-gradient(to bottom, #5a8ed6, #3a6bb5);
				    border: 1.5px solid rgba(255,255,255,0.3);
				    box-shadow: 0 1px 3px rgba(0,0,0,0.3);">
			<HeartPulse class="w-4 h-4 text-white" />
		</div>
	</div>

	<!-- Card -->
	<div class="w-full max-w-sm rounded-2xl overflow-hidden"
		 style="background: white;
				box-shadow: 0 4px 20px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08);
				border: 1px solid rgba(255,255,255,0.8);">

		<!-- ────────────────────── STEP 1: PHONE ───────────────────── -->
		{#if step === 1}
			<div class="flex flex-col items-center px-6 py-8 gap-5">
				<div class="w-16 h-16 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e8f0fe, #d0e1fd);">
					<Phone class="w-7 h-7 text-blue-600" />
				</div>
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Enter Phone Number</h2>
					<p class="text-sm text-gray-500 mt-1">We'll send a one-time password to verify your number.</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				<div class="w-full">
<label for="phone" class="text-xs font-medium text-gray-600 mb-1.5 block">Mobile Number</label>
				<div class="flex gap-2">
					<div class="px-3 py-2.5 rounded-lg text-sm text-gray-700 font-medium shrink-0"
						 style="background: #f0f4fa; border: 1px solid rgba(0,0,0,0.12);">
						+91
					</div>
					<input
						id="phone"
							type="tel"
							inputmode="numeric"
							maxlength="10"
							placeholder="98765 43210"
							bind:value={phone}
							onkeydown={(e) => e.key === 'Enter' && handleSendOtp()}
							class="flex-1 px-3 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
					</div>
				</div>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={handleSendOtp}
				>
					Send OTP <ArrowRight class="w-4 h-4" />
				</button>

				<p class="text-xs text-gray-400 text-center">
					Already registered?
					<a href="/login" class="text-blue-600 font-medium">Sign in</a>
				</p>
			</div>

		<!-- ────────────────────── STEP 2: OTP ────────────────────── -->
		{:else if step === 2}
			<div class="flex flex-col items-center px-6 py-8 gap-5">
				<div class="w-16 h-16 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e8f0fe, #d0e1fd);">
					<ShieldCheck class="w-7 h-7 text-blue-600" />
				</div>
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Verify OTP</h2>
					<p class="text-sm text-gray-500 mt-1">Enter the 6-digit code sent to +91 {phone}</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				<div class="flex gap-2 justify-center">
					{#each otp as digit, i}
						<input
							type="text"
							inputmode="numeric"
							maxlength="1"
							bind:value={otp[i]}
							bind:this={otpInputs[i]}
							oninput={(e) => handleOtpInput(e, i)}
							onkeydown={(e) => handleOtpKeydown(e, i)}
							onpaste={(e) => handleOtpPaste(e, otp, otpInputs)}
							class="w-11 h-12 text-center text-lg font-bold rounded-xl outline-none transition-all"
							style="background: #f7f9fd; border: 2px solid {digit ? '#4d90fe' : 'rgba(0,0,0,0.12)'};"
						/>
					{/each}
				</div>

				<button class="text-sm text-blue-600 font-medium cursor-pointer hover:underline" onclick={() => {}}>
					Resend OTP
				</button>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={verifyOtp}
				>
					Verify & Continue <ArrowRight class="w-4 h-4" />
				</button>
			</div>

		<!-- ────────────────────── STEP 3: AADHAAR ────────────────── -->
		{:else if step === 3}
			<div class="flex flex-col items-center px-6 py-8 gap-5">
				<div class="w-16 h-16 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e6f9ef, #c8f0da);">
					<Fingerprint class="w-7 h-7 text-green-600" />
				</div>
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Aadhaar Verification</h2>
					<p class="text-sm text-gray-500 mt-1">Verify your identity via DigiLocker to fetch your details automatically.</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				{#if !aadhaarConnected}
					<!-- Aadhaar card mock -->
					<div class="w-full rounded-xl p-4 flex items-center gap-3"
						 style="background: linear-gradient(135deg, #1a5276, #2980b9);
								border: 1px solid rgba(255,255,255,0.15);">
						<div class="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center shrink-0">
							<Fingerprint class="w-5 h-5 text-white" />
						</div>
						<div>
							<p class="text-white font-semibold text-sm">Aadhaar</p>
							<p class="text-white/70 text-xs">Fast, secure, and paperless</p>
						</div>
					</div>

					<div class="w-full">
						<label for="aadhaar" class="text-xs font-medium text-gray-600 mb-1.5 block">Aadhaar Number</label>
						<input
							type="text"
							inputmode="numeric"
							maxlength="12"
							id="aadhaar" placeholder="1234 5678 9012"
							bind:value={aadhaarNum}
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
					</div>

					<div class="w-full">
						<label for="aadhaar-otp-0" class="text-xs font-medium text-gray-600 mb-2 block">Aadhaar OTP</label>
						<div class="flex gap-2 justify-center">
							{#each aadhaarOtp as digit, i}
								<input
									type="text"
									inputmode="numeric"
									maxlength="1"
									bind:value={aadhaarOtp[i]}
									bind:this={aadhaarOtpInputs[i]}
									oninput={(e) => handleAadhaarOtpInput(e, i)}
									onkeydown={(e) => handleAadhaarOtpKeydown(e, i)}
									onpaste={(e) => handleOtpPaste(e, aadhaarOtp, aadhaarOtpInputs)}
									class="w-10 h-11 text-center text-base font-bold rounded-xl outline-none transition-all"
									style="background: #f7f9fd; border: 2px solid {digit ? '#22c55e' : 'rgba(0,0,0,0.12)'};"
								/>
							{/each}
						</div>
					</div>

					<button
						class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
						style="background: linear-gradient(to bottom, #22c55e, #16a34a);
							   box-shadow: 0 2px 8px rgba(34,197,94,0.35);
							   border: 1px solid rgba(0,0,0,0.1);"
						onclick={connectAadhaar}
					>
						Connect to DigiLocker <ArrowRight class="w-4 h-4" />
					</button>
				{:else}
					<div class="w-full flex flex-col items-center gap-3 py-2">
						<div class="w-14 h-14 rounded-full flex items-center justify-center"
							 style="background: linear-gradient(to bottom, #e6f9ef, #c8f0da);">
							<CheckCircle2 class="w-7 h-7 text-green-600" />
						</div>
						<p class="text-green-700 font-semibold text-sm">Aadhaar Verified!</p>
						<button
							class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 mt-2"
							style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
								   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
								   border: 1px solid rgba(0,0,0,0.1);"
							onclick={next}
						>
							Continue <ArrowRight class="w-4 h-4" />
						</button>
					</div>
				{/if}

				<button class="text-xs text-gray-400 cursor-pointer hover:text-gray-600 underline" onclick={skipAadhaar}>
					Skip & enter details manually
				</button>
			</div>

		<!-- ────────────────────── STEP 4: ABHA ───────────────────── -->
		{:else if step === 4}
			<div class="flex flex-col items-center px-6 py-8 gap-5">
				<div class="w-16 h-16 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e6f9ef, #c8f0da);">
					<BadgeCheck class="w-7 h-7 text-green-600" />
				</div>
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">ABHA ID Generated</h2>
					<p class="text-sm text-gray-500 mt-1">Your Ayushman Bharat Health Account (ABHA) has been successfully created/linked.</p>
				</div>

				<div class="w-full rounded-xl px-5 py-4 text-center"
					 style="background: linear-gradient(to bottom, #e8f5e9, #c8e6c9);
							border: 1.5px solid #81c784;
							box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);">
					<p class="text-xs font-medium text-green-700 mb-2">Your ABHA Number</p>
					<p class="text-2xl font-bold tracking-widest text-green-800">{mockAbha}</p>
				</div>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={next}
				>
					Continue to Demographics <ArrowRight class="w-4 h-4" />
				</button>
			</div>

		<!-- ────────────────────── STEP 5: PATIENT DETAILS ──────── -->
		{:else if step === 5}
			<div class="flex flex-col px-6 py-6 gap-4">
				<div class="flex items-center gap-3 mb-1">
					<div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
						 style="background: linear-gradient(to bottom, #e8f0fe, #d0e1fd);">
						<User class="w-5 h-5 text-blue-600" />
					</div>
					<div>
						<h2 class="text-base font-bold text-gray-800">Patient Details</h2>
						<p class="text-xs text-gray-500">Please confirm your demographic information.</p>
					</div>
				</div>

				{#if error}<p class="text-xs text-red-500 -mt-2">{error}</p>{/if}

				<div>
					<label for="pat-name" class="text-xs font-medium text-gray-600 mb-1 block">Full Name</label>
					<input
						type="text"
						id="pat-name" placeholder="Name"
						bind:value={patName}
						class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
						style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
					/>
				</div>

				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="pat-dob" class="text-xs font-medium text-gray-600 mb-1 block">Date of Birth</label>
						<input
							id="pat-dob" type="date"
							bind:value={patDob}
							class="w-full px-3 py-2 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
					</div>
					<div>
						<label for="pat-gender" class="text-xs font-medium text-gray-600 mb-1 block">Gender</label>
						<select
							id="pat-gender" bind:value={patGender}
							class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						>
							<option>MALE</option>
							<option>FEMALE</option>
							<option>OTHER</option>
						</select>
					</div>
				</div>

				<div>
					<label for="pat-address" class="text-xs font-medium text-gray-600 mb-1 block">Address</label>
					<textarea
						id="pat-address" placeholder="address"
						bind:value={patAddress}
						rows={2}
						class="w-full px-3 py-2.5 rounded-lg text-sm outline-none resize-none"
						style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
					></textarea>
				</div>

				<div>
					<label for="pat-email" class="text-xs font-medium text-gray-600 mb-1 block">Email</label>
					<input
						id="pat-email" type="email"
						placeholder="email@example.com"
						bind:value={patEmail}
						class="w-full px-3 py-2.5 rounded-lg text-sm outline-none"
						style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
					/>
				</div>

				<div>
<label for="pat-password" class="text-xs font-medium text-gray-600 mb-1 block">Create Password</label>
				<div class="relative">
					<input
						id="pat-password"
							type={showPassword ? 'text' : 'password'}
							placeholder="Min. 6 characters"
							bind:value={patPassword}
							class="w-full px-3 pr-10 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
						<button
							class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer"
							type="button"
							onclick={() => showPassword = !showPassword}
						>
							{#if showPassword}<EyeOff class="w-4 h-4" />{:else}<Eye class="w-4 h-4" />{/if}
						</button>
					</div>
				</div>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98] mt-1"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={saveDetails}
				>
					Continue to Insurance <ArrowRight class="w-4 h-4" />
				</button>
			</div>

		<!-- ────────────────────── STEP 6: INSURANCE ─────────────── -->
		{:else if step === 6}
			<div class="flex flex-col px-6 py-8 gap-5">
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Insurance Type</h2>
					<p class="text-sm text-gray-500 mt-1">Select your insurance type to determine eligible services.</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				{#if insuranceLoading}
					<div class="flex items-center justify-center py-8">
						<div class="h-6 w-6 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600"></div>
					</div>
				{:else}
					<div class="flex flex-col gap-3">
						{#each insuranceOptions as opt}
							{@const InsuranceIcon = insuranceIcons[opt.icon_key]}
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="flex items-center justify-between px-4 py-3.5 rounded-xl cursor-pointer transition-all"
								style={`border: 2px solid ${selectedInsuranceId === opt.id ? opt.color_secondary : 'rgba(0,0,0,0.1)'};
									background: ${selectedInsuranceId === opt.id ? `linear-gradient(135deg, ${opt.color_primary}18, ${opt.color_secondary}22)` : 'white'};
									box-shadow: ${selectedInsuranceId === opt.id ? `0 10px 20px ${opt.color_secondary}22` : 'none'};`}
								onclick={() => selectedInsuranceId = opt.id}
							>
								<div class="flex items-center gap-3 min-w-0">
									<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white"
										style={`background: linear-gradient(135deg, ${opt.color_primary}, ${opt.color_secondary}); box-shadow: 0 8px 16px ${opt.color_secondary}22;`}>
										{#if opt.custom_badge_symbol}
											<span class="text-xs font-black leading-none tracking-tight">{opt.custom_badge_symbol}</span>
										{:else}
											<InsuranceIcon class="w-4 h-4" />
										{/if}
									</div>
									<div class="min-w-0">
										<span class="block text-sm font-semibold {selectedInsuranceId === opt.id ? 'text-slate-900' : 'text-gray-600'}">{opt.name}</span>
										{#if opt.description}
											<p class="mt-0.5 text-xs text-slate-500">{opt.description}</p>
										{/if}
									</div>
								</div>
								{#if selectedInsuranceId === opt.id}
									<CheckCircle2 class="w-5 h-5 shrink-0" style={`color: ${opt.color_secondary};`} />
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				{#if selectedInsurance}
					<div class="rounded-2xl px-4 py-3 text-sm text-slate-600"
						style={`background: linear-gradient(135deg, ${selectedInsurance.color_primary}14, ${selectedInsurance.color_secondary}1F); border: 1px solid ${selectedInsurance.color_primary}44;`}>
						This insurance selection sets the badge symbol shown on the patient avatar. Patient type controls the glow color in the next step.
					</div>
				{/if}

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={next}
				>
					Continue <ArrowRight class="w-4 h-4" />
				</button>
			</div>

		<!-- ────────────────────── STEP 7: PATIENT CATEGORY ─────── -->
		{:else if step === 7}
			<div class="flex flex-col px-6 py-8 gap-5">
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Patient Category</h2>
					<p class="text-sm text-gray-500 mt-1">Select your category to determine pricing and services.</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				{#if patientCategoryLoading}
					<div class="flex items-center justify-center py-8">
						<div class="h-6 w-6 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600"></div>
					</div>
				{:else}
					<div class="flex flex-col gap-3">
						{#each patientCategoryOptions as opt}
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="flex items-center justify-between px-4 py-3.5 rounded-xl cursor-pointer transition-all"
								style={`border: 2px solid ${selectedPatientCategoryId === opt.id ? opt.color_secondary : 'rgba(0,0,0,0.1)'};
									   background: ${selectedPatientCategoryId === opt.id ? `linear-gradient(135deg, ${opt.color_primary}14, ${opt.color_secondary}1E)` : 'white'};
									   box-shadow: ${selectedPatientCategoryId === opt.id ? `0 10px 20px ${opt.color_secondary}20` : 'none'};`}
								onclick={() => selectedPatientCategoryId = opt.id}
							>
								<div class="flex items-center gap-3 flex-1">
									<div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white"
										style={`background: linear-gradient(135deg, ${opt.color_primary}, ${opt.color_secondary}); box-shadow: 0 8px 16px ${opt.color_secondary}22;`}>
										<Building2 class="w-4 h-4" />
									</div>
									<div class="flex-1">
									<span class="text-sm font-semibold {selectedPatientCategoryId === opt.id ? 'text-blue-700' : 'text-gray-600'}">{opt.name}</span>
									{#if opt.description}
										<p class="text-xs text-gray-500 mt-0.5">{opt.description}</p>
									{/if}
									</div>
								</div>
								{#if selectedPatientCategoryId === opt.id}
									<CheckCircle2 class="w-5 h-5 shrink-0" style={`color: ${opt.color_secondary};`} />
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={next}
				>
					Continue <ArrowRight class="w-4 h-4" />
				</button>
			</div>

		{:else if step === 8}
			<div class="flex flex-col items-center px-6 py-8 gap-5">
				<div class="w-16 h-16 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e8f0fe, #d0e1fd);">
					<CreditCard class="w-7 h-7 text-blue-600" />
				</div>
				<div class="text-center">
					<h2 class="text-lg font-bold text-gray-800">Registration Fee</h2>
					<p class="text-sm text-gray-500 mt-1">A one-time fee is required to generate your hospital registration card and IP number.</p>
				</div>

				{#if error}<p class="text-xs text-red-500 text-center -mt-2">{error}</p>{/if}

				<div class="w-full rounded-xl overflow-hidden"
					 style="border: 1px solid rgba(0,0,0,0.12);
							background: #fafbff;">
					<div class="flex justify-between items-center px-4 py-3"
						 style="border-bottom: 1px solid rgba(0,0,0,0.07);">
						<span class="text-sm text-gray-600">Registration Fee</span>
						<span class="text-sm font-semibold text-gray-800">₹{regFee}.00</span>
					</div>
					<div class="flex justify-between items-center px-4 py-3">
						<span class="text-sm font-bold text-gray-800">Total</span>
						<span class="text-base font-bold text-blue-700">₹{regFee}.00</span>
					</div>
				</div>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-60"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={handlePayAndRegister}
					disabled={loading}
				>
					{#if loading}
						<span class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
						Registering...
					{:else}
						Pay ₹{regFee} Now <ArrowRight class="w-4 h-4" />
					{/if}
				</button>
			</div>

		<!-- ────────────────────── STEP 9: COMPLETE ─────────────── -->
		{:else if step === 9}
			<div class="flex flex-col items-center px-6 py-10 gap-5">
				<div class="w-20 h-20 rounded-full flex items-center justify-center"
					 style="background: linear-gradient(to bottom, #e6f9ef, #c8f0da);">
					<CircleCheck class="w-10 h-10 text-green-600" />
				</div>

				<div class="text-center">
					<h2 class="text-xl font-bold text-gray-800">Registration Complete!</h2>
					<p class="text-sm text-gray-500 mt-1.5">Your hospital registration is successful.</p>
				</div>

				<div class="w-full rounded-xl px-5 py-4 text-center"
					 style="background: linear-gradient(to bottom, #eef4ff, #e0eaff);
							border: 1.5px solid #93b8f5;">
					<p class="text-xs font-medium text-blue-600 mb-1.5">Your Patient ID (IP)</p>
					<p class="text-2xl font-bold tracking-wide text-blue-800">{createdPatientId}</p>
				</div>

				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-60"
					style="background: linear-gradient(to bottom, #22c55e, #16a34a);
						   box-shadow: 0 2px 8px rgba(34,197,94,0.35);
						   border: 1px solid rgba(0,0,0,0.1);"
					onclick={goToDashboard}
					disabled={loading}
				>
					{#if loading}
						<span class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
						Loading...
					{:else}
						Proceed to Dashboard <ChevronRight class="w-4 h-4" />
					{/if}
				</button>
			</div>
		{/if}
	</div>

	<!-- Bottom hint for first step -->
	{#if step === 1}
		<p class="mt-6 text-xs text-gray-400 text-center px-4">
			By registering, you agree to our Terms of Service and Privacy Policy. Your data is secured and used only for medical purposes.
		</p>
	{/if}
</div>
