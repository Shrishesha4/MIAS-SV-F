<script lang="ts">
	import { goto } from '$app/navigation';
	import { authApi } from '$lib/api/auth';
	import {
		User, KeyRound, Mail, Phone, MapPin, Calendar, Droplet,
		ArrowLeft, UserPlus, Shield, CheckCircle2, Stethoscope,
		GraduationCap, Heart, Building2, BookOpen
	} from 'lucide-svelte';

	type Role = 'PATIENT' | 'STUDENT' | 'FACULTY';

	// Form state
	let selectedRole = $state<Role | null>(null);
	let currentStep = $state(1);
	let loading = $state(false);
	let error = $state('');
	let success = $state(false);

	// Common: Account Info
	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let email = $state('');

	// Patient fields
	let patientName = $state('');
	let patientDob = $state('');
	let patientGender = $state('MALE');
	let patientBloodGroup = $state('');
	let patientPhone = $state('');
	let patientAddress = $state('');
	let patientAadhaar = $state('');
	let patientAbha = $state('');
	let emergencyName = $state('');
	let emergencyPhone = $state('');
	let emergencyRelation = $state('');

	// Student fields
	let studentName = $state('');
	let studentProgram = $state('');
	let studentYear = $state(1);
	let studentSemester = $state(1);
	let studentGpa = $state(0);
	let studentAdvisor = $state('');

	// Faculty fields
	let facultyName = $state('');
	let facultyDepartment = $state('');
	let facultySpecialty = $state('');
	let facultyPhone = $state('');

	const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
	const programs = ['BDS', 'MDS', 'MBBS', 'MD', 'MS'];
	const departments = ['Oral Surgery', 'Orthodontics', 'Periodontics', 'Prosthodontics', 'Endodontics', 'Pedodontics', 'Oral Pathology', 'Public Health Dentistry'];

	function getSteps() {
		if (!selectedRole) return [];
		if (selectedRole === 'PATIENT') {
			return [
				{ id: 1, label: 'Account' },
				{ id: 2, label: 'Personal' },
				{ id: 3, label: 'Contact' },
				{ id: 4, label: 'Emergency' },
			];
		} else if (selectedRole === 'STUDENT') {
			return [
				{ id: 1, label: 'Account' },
				{ id: 2, label: 'Academic' },
			];
		} else {
			return [
				{ id: 1, label: 'Account' },
				{ id: 2, label: 'Professional' },
			];
		}
	}

	let steps = $derived(getSteps());
	let totalSteps = $derived(steps.length);

	function validateAccountStep() {
		if (!username || username.length < 3) {
			error = 'Username must be at least 3 characters';
			return false;
		}
		if (!email || !email.includes('@')) {
			error = 'Please enter a valid email';
			return false;
		}
		if (!password || password.length < 6) {
			error = 'Password must be at least 6 characters';
			return false;
		}
		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return false;
		}
		error = '';
		return true;
	}

	function validatePatientPersonalStep() {
		if (!patientName) { error = 'Please enter your full name'; return false; }
		if (!patientDob) { error = 'Please enter your date of birth'; return false; }
		if (!patientBloodGroup) { error = 'Please select your blood group'; return false; }
		error = '';
		return true;
	}

	function validatePatientContactStep() {
		if (!patientPhone || patientPhone.length < 10) { error = 'Please enter a valid phone number'; return false; }
		error = '';
		return true;
	}

	function validateStudentStep() {
		if (!studentName) { error = 'Please enter your full name'; return false; }
		if (!studentProgram) { error = 'Please select your program'; return false; }
		error = '';
		return true;
	}

	function validateFacultyStep() {
		if (!facultyName) { error = 'Please enter your full name'; return false; }
		if (!facultyDepartment) { error = 'Please select your department'; return false; }
		error = '';
		return true;
	}

	function nextStep() {
		if (currentStep === 1 && !validateAccountStep()) return;
		
		if (selectedRole === 'PATIENT') {
			if (currentStep === 2 && !validatePatientPersonalStep()) return;
			if (currentStep === 3 && !validatePatientContactStep()) return;
		} else if (selectedRole === 'STUDENT') {
			if (currentStep === 2 && !validateStudentStep()) return;
		} else if (selectedRole === 'FACULTY') {
			if (currentStep === 2 && !validateFacultyStep()) return;
		}
		
		if (currentStep < totalSteps) {
			currentStep++;
		}
	}

	function prevStep() {
		if (currentStep > 1) {
			currentStep--;
			error = '';
		}
	}

	function selectRole(role: Role) {
		selectedRole = role;
		currentStep = 1;
		error = '';
	}

	function goBackToRoleSelection() {
		selectedRole = null;
		currentStep = 1;
		error = '';
	}

	async function handleSignup() {
		loading = true;
		error = '';
		try {
			let signupData: any = {
				username,
				password,
				email,
				role: selectedRole,
			};

			if (selectedRole === 'PATIENT') {
				signupData.patient_data = {
					name: patientName,
					date_of_birth: patientDob,
					gender: patientGender,
					blood_group: patientBloodGroup,
					phone: patientPhone,
					email,
					address: patientAddress || undefined,
					aadhaar_id: patientAadhaar || undefined,
					abha_id: patientAbha || undefined,
					emergency_contact: emergencyName ? {
						name: emergencyName,
						phone: emergencyPhone,
						relationship: emergencyRelation,
					} : undefined,
				};
			} else if (selectedRole === 'STUDENT') {
				signupData.student_data = {
					name: studentName,
					program: studentProgram,
					year: studentYear,
					semester: studentSemester,
					gpa: studentGpa,
					academic_advisor: studentAdvisor || undefined,
				};
			} else if (selectedRole === 'FACULTY') {
				signupData.faculty_data = {
					name: facultyName,
					department: facultyDepartment,
					specialty: facultySpecialty || undefined,
					phone: facultyPhone || undefined,
					email,
				};
			}

			await authApi.signup(signupData);
			success = true;
			setTimeout(() => goto('/login'), 2000);
		} catch (err: any) {
			error = err?.response?.data?.detail || 'Failed to create account. Please try again.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="min-h-screen flex flex-col">
	<!-- Hospital Banner Section -->
	<div class="relative overflow-hidden" style="min-height: 160px;">
		<div class="absolute inset-0" style="
			background: linear-gradient(160deg, #87CEEB 0%, #B0D4E8 30%, #d1dbed 60%, #c8d5e8 100%);
		"></div>
		<div class="absolute inset-0" style="
			background: linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0.6));
		"></div>

		<div class="relative z-10 px-6 pt-6 pb-4">
			<button
				class="flex items-center gap-1 text-gray-600 text-sm font-medium cursor-pointer mb-3"
				onclick={() => selectedRole ? goBackToRoleSelection() : goto('/login')}
			>
				<ArrowLeft class="w-4 h-4" /> {selectedRole ? 'Change Role' : 'Back to Login'}
			</button>
			<div class="flex items-center gap-3">
				<svg width="50" height="50" viewBox="0 0 100 100" fill="none">
					<circle cx="42" cy="32" r="14" fill="#00BCD4" opacity="0.9"/>
					<circle cx="58" cy="32" r="14" fill="#FF9800" opacity="0.9"/>
					<circle cx="42" cy="52" r="14" fill="#2196F3" opacity="0.9"/>
					<circle cx="58" cy="52" r="14" fill="#4CAF50" opacity="0.9"/>
					<circle cx="50" cy="42" r="8" fill="white"/>
				</svg>
				<div>
					<h1 class="text-xl font-bold text-gray-800">
						{selectedRole === 'PATIENT' ? 'Patient' : selectedRole === 'STUDENT' ? 'Student' : selectedRole === 'FACULTY' ? 'Doctor' : ''} Registration
					</h1>
					<p class="text-xs text-blue-600 font-medium">Saveetha Medical College and Hospitals</p>
				</div>
			</div>
		</div>
	</div>

	{#if success}
		<div class="px-4 -mt-4 relative z-20 flex-1 flex items-center justify-center">
			<div class="text-center">
				<div class="w-20 h-20 rounded-full mx-auto mb-4 flex items-center justify-center"
					style="background: linear-gradient(to bottom, #22c55e, #16a34a);">
					<CheckCircle2 class="w-10 h-10 text-white" />
				</div>
				<h2 class="text-xl font-bold text-gray-800">Account Created!</h2>
				<p class="text-sm text-gray-500 mt-2">Redirecting to login...</p>
			</div>
		</div>
	{:else if !selectedRole}
		<!-- Role Selection -->
		<div class="px-4 py-6 flex-1">
			<h2 class="text-lg font-bold text-gray-800 text-center mb-6">I am registering as a...</h2>
			<div class="space-y-4">
				<button
					class="w-full p-4 rounded-2xl flex items-center gap-4 cursor-pointer text-left"
					style="background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 2px solid rgba(239,68,68,0.3);"
					onclick={() => selectRole('PATIENT')}
				>
					<div class="w-14 h-14 rounded-xl flex items-center justify-center bg-red-50">
						<Heart class="w-7 h-7 text-red-500" />
					</div>
					<div class="flex-1">
						<h3 class="font-bold text-gray-800">Patient</h3>
						<p class="text-xs text-gray-500">Register for medical care and services</p>
					</div>
				</button>

				<button
					class="w-full p-4 rounded-2xl flex items-center gap-4 cursor-pointer text-left"
					style="background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 2px solid rgba(59,130,246,0.3);"
					onclick={() => selectRole('STUDENT')}
				>
					<div class="w-14 h-14 rounded-xl flex items-center justify-center bg-blue-50">
						<GraduationCap class="w-7 h-7 text-blue-500" />
					</div>
					<div class="flex-1">
						<h3 class="font-bold text-gray-800">Student</h3>
						<p class="text-xs text-gray-500">Medical/Dental student registration</p>
					</div>
				</button>

				<button
					class="w-full p-4 rounded-2xl flex items-center gap-4 cursor-pointer text-left"
					style="background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 2px solid rgba(34,197,94,0.3);"
					onclick={() => selectRole('FACULTY')}
				>
					<div class="w-14 h-14 rounded-xl flex items-center justify-center bg-green-50">
						<Stethoscope class="w-7 h-7 text-green-500" />
					</div>
					<div class="flex-1">
						<h3 class="font-bold text-gray-800">Doctor / Faculty</h3>
						<p class="text-xs text-gray-500">Faculty and medical professional registration</p>
					</div>
				</button>
			</div>
		</div>
	{:else}
		<!-- Step Progress -->
		<div class="px-6 py-4 bg-white">
			<div class="flex items-center justify-between relative">
				<div class="absolute top-4 left-0 right-0 h-0.5 bg-gray-200"></div>
				{#each steps as step}
					<div class="relative z-10 flex flex-col items-center">
						<div class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
							style="background: {currentStep >= step.id ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#e5e7eb'};
							       color: {currentStep >= step.id ? 'white' : '#9ca3af'};">
							{step.id}
						</div>
						<span class="text-[10px] text-gray-500 mt-1">{step.label}</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- Form Card -->
		<div class="px-4 pb-6 flex-1">
			<div
				class="rounded-2xl overflow-hidden"
				style="background-color: white;
				       box-shadow: 0 4px 20px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
				       border: 1px solid rgba(0,0,0,0.08);"
			>
				<div class="p-6 space-y-4">
					{#if error}
						<div class="px-3 py-2 rounded-lg text-sm text-red-700"
							style="background-color: rgba(255,0,0,0.05); border: 1px solid rgba(220,50,50,0.2);">
							{error}
						</div>
					{/if}

					<!-- Step 1: Account Info (all roles) -->
					{#if currentStep === 1}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Create Your Account</h3>
						<div class="space-y-4">
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Username</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="Choose a username" bind:value={username}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Email</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Mail class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="email" placeholder="your@email.com" bind:value={email}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Password</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<KeyRound class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="password" placeholder="Create a password" bind:value={password}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Confirm Password</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<KeyRound class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="password" placeholder="Confirm your password" bind:value={confirmPassword}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
						</div>

					<!-- PATIENT STEPS -->
					{:else if selectedRole === 'PATIENT' && currentStep === 2}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Personal Information</h3>
						<div class="space-y-4">
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Full Name</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="Enter your full name" bind:value={patientName}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Date of Birth</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Calendar class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="date" bind:value={patientDob}
										class="flex-1 outline-none text-gray-700 bg-transparent" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Gender</label>
								<div class="flex gap-3">
									{#each ['MALE', 'FEMALE', 'OTHER'] as g}
										<button
											class="flex-1 py-2.5 rounded-lg text-sm font-medium cursor-pointer"
											style="background: {patientGender === g ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f1f5f9'};
											       color: {patientGender === g ? 'white' : '#64748b'};
											       border: 1px solid {patientGender === g ? '#2563eb' : 'rgba(0,0,0,0.1)'};"
											onclick={() => patientGender = g}
										>
											{g === 'MALE' ? 'Male' : g === 'FEMALE' ? 'Female' : 'Other'}
										</button>
									{/each}
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Blood Group</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Droplet class="h-5 w-5 text-red-400 mr-3 shrink-0" />
									<select bind:value={patientBloodGroup}
										class="flex-1 outline-none text-gray-700 bg-transparent cursor-pointer">
										<option value="">Select blood group</option>
										{#each bloodGroups as bg}
											<option value={bg}>{bg}</option>
										{/each}
									</select>
								</div>
							</div>
						</div>

					{:else if selectedRole === 'PATIENT' && currentStep === 3}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Contact Information</h3>
						<div class="space-y-4">
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Phone Number</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Phone class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="tel" placeholder="+91 XXXXX XXXXX" bind:value={patientPhone}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Address (Optional)</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<MapPin class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="Street address, City" bind:value={patientAddress}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div class="p-3 rounded-lg" style="background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.1);">
								<p class="text-xs font-semibold text-blue-600 mb-3 flex items-center gap-1">
									<Shield class="w-3 h-3" /> Verification IDs (Optional)
								</p>
								<div class="space-y-3">
									<input type="text" placeholder="Aadhaar Number" bind:value={patientAadhaar}
										class="w-full px-3 py-2.5 outline-none text-gray-700 text-sm rounded-lg"
										style="border: 1px solid rgba(0,0,0,0.15);" />
									<input type="text" placeholder="ABHA ID" bind:value={patientAbha}
										class="w-full px-3 py-2.5 outline-none text-gray-700 text-sm rounded-lg"
										style="border: 1px solid rgba(0,0,0,0.15);" />
								</div>
							</div>
						</div>

					{:else if selectedRole === 'PATIENT' && currentStep === 4}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Emergency Contact (Optional)</h3>
						<div class="space-y-4">
							<div class="p-3 rounded-lg" style="background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.1);">
								<div class="space-y-3">
									<div>
										<label class="text-xs text-gray-500 mb-1 block">Contact Name</label>
										<input type="text" placeholder="Emergency contact name" bind:value={emergencyName}
											class="w-full px-3 py-2.5 outline-none text-gray-700 text-sm rounded-lg"
											style="border: 1px solid rgba(0,0,0,0.15);" />
									</div>
									<div>
										<label class="text-xs text-gray-500 mb-1 block">Phone</label>
										<input type="tel" placeholder="Phone number" bind:value={emergencyPhone}
											class="w-full px-3 py-2.5 outline-none text-gray-700 text-sm rounded-lg"
											style="border: 1px solid rgba(0,0,0,0.15);" />
									</div>
									<div>
										<label class="text-xs text-gray-500 mb-1 block">Relationship</label>
										<input type="text" placeholder="e.g., Spouse, Parent, Sibling" bind:value={emergencyRelation}
											class="w-full px-3 py-2.5 outline-none text-gray-700 text-sm rounded-lg"
											style="border: 1px solid rgba(0,0,0,0.15);" />
									</div>
								</div>
							</div>
						</div>

					<!-- STUDENT STEPS -->
					{:else if selectedRole === 'STUDENT' && currentStep === 2}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Academic Information</h3>
						<div class="space-y-4">
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Full Name</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="Enter your full name" bind:value={studentName}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Program</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<BookOpen class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<select bind:value={studentProgram}
										class="flex-1 outline-none text-gray-700 bg-transparent cursor-pointer">
										<option value="">Select program</option>
										{#each programs as p}
											<option value={p}>{p}</option>
										{/each}
									</select>
								</div>
							</div>
							<div class="grid grid-cols-2 gap-3">
								<div>
									<label class="text-xs text-gray-500 mb-1 block">Year</label>
									<select bind:value={studentYear}
										class="w-full px-4 py-3 outline-none text-gray-700 cursor-pointer"
										style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
										{#each [1, 2, 3, 4, 5] as y}
											<option value={y}>Year {y}</option>
										{/each}
									</select>
								</div>
								<div>
									<label class="text-xs text-gray-500 mb-1 block">Semester</label>
									<select bind:value={studentSemester}
										class="w-full px-4 py-3 outline-none text-gray-700 cursor-pointer"
										style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
										{#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as s}
											<option value={s}>Sem {s}</option>
										{/each}
									</select>
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Academic Advisor (Optional)</label>
								<input type="text" placeholder="Advisor name" bind:value={studentAdvisor}
									class="w-full px-4 py-3 outline-none text-gray-700 text-sm"
									style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;" />
							</div>
						</div>

					<!-- FACULTY STEPS -->
					{:else if selectedRole === 'FACULTY' && currentStep === 2}
						<h3 class="text-lg font-bold text-gray-800 mb-4">Professional Information</h3>
						<div class="space-y-4">
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Full Name</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="Dr. Full Name" bind:value={facultyName}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Department</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Building2 class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<select bind:value={facultyDepartment}
										class="flex-1 outline-none text-gray-700 bg-transparent cursor-pointer">
										<option value="">Select department</option>
										{#each departments as d}
											<option value={d}>{d}</option>
										{/each}
									</select>
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Specialty (Optional)</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Stethoscope class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="text" placeholder="e.g., Implantology, Cosmetic Dentistry" bind:value={facultySpecialty}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
							<div>
								<label class="text-xs text-gray-500 mb-1 block">Phone (Optional)</label>
								<div class="flex items-center px-4 py-3" style="border: 1px solid rgba(0,0,0,0.15); border-radius: 8px;">
									<Phone class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
									<input type="tel" placeholder="+91 XXXXX XXXXX" bind:value={facultyPhone}
										class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400" />
								</div>
							</div>
						</div>
					{/if}

					<!-- Navigation Buttons -->
					<div class="flex gap-3 pt-4">
						{#if currentStep > 1}
							<button
								class="flex-1 py-3 rounded-xl text-sm font-semibold cursor-pointer"
								style="background: #f1f5f9; color: #64748b; border: 1px solid rgba(0,0,0,0.1);"
								onclick={prevStep}
							>
								Back
							</button>
						{/if}
						{#if currentStep < totalSteps}
							<button
								class="flex-1 py-3 rounded-xl text-white font-semibold cursor-pointer"
								style="background: linear-gradient(to bottom, #5a9cff, #2d7ae8);
								       box-shadow: 0 2px 8px rgba(45,122,232,0.35), inset 0 1px 0 rgba(255,255,255,0.3);
								       border: 1px solid rgba(0,0,0,0.1);"
								onclick={nextStep}
							>
								Continue
							</button>
						{:else}
							<button
								class="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold cursor-pointer
								       disabled:opacity-50 disabled:cursor-not-allowed"
								style="background: linear-gradient(to bottom, #22c55e, #16a34a);
								       box-shadow: 0 2px 8px rgba(34,197,94,0.35), inset 0 1px 0 rgba(255,255,255,0.3);
								       border: 1px solid rgba(0,0,0,0.1);"
								disabled={loading}
								onclick={handleSignup}
							>
								{#if loading}
									<span class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
									Creating...
								{:else}
									<UserPlus class="w-5 h-5" />
									Create Account
								{/if}
							</button>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Footer -->
	<div class="py-4 text-center">
		<p class="text-xs text-gray-500">
			Already have an account? 
			<button class="text-blue-600 font-medium cursor-pointer" onclick={() => goto('/login')}>Login</button>
		</p>
	</div>
</div>

<style>
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>
