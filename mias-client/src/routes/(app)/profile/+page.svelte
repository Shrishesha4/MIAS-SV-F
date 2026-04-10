<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { formsApi } from '$lib/api/forms';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import { defaultProfileEditFields } from '$lib/config/default-form-definitions';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import type { FormDefinition } from '$lib/types/forms';
	import { asOptionalString, persistFormFiles, resolveFormFieldsByType } from '$lib/utils/forms';
	import {
		User, Phone, Mail, MapPin, Calendar, Shield, Crown,
		Heart, AlertTriangle, GraduationCap, Stethoscope, BadgeCheck,
		Award, CheckCircle2, BookOpen, Clock, XCircle, CircleDot,
		Upload, PenTool, Camera, Image, Plus, Trash2, CreditCard, Droplet, Edit3
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;

	let patient: any = $state(null);
	let sp: any = $state(null);
	let faculty: any = $state(null);
	let loading = $state(true);

	// Faculty upload state
	let photoUploading = $state(false);
	let signatureUploading = $state(false);
	let photoInput = $state<HTMLInputElement>();
	let signatureInput = $state<HTMLInputElement>();

	// Insurance state
	let showAddInsurance = $state(false);
	let newInsurance = $state({ provider: '', policy_number: '', valid_until: '' });
	let addingInsurance = $state(false);

	// Patient edit state
	let showEditModal = $state(false);
	let profileForms: FormDefinition[] = $state([]);
	let profileFormValues: Record<string, any> = $state({});
	let savingProfile = $state(false);

	// Student attendance calendar state
	let attendanceCalendar: any[] = $state([]);
	let calendarMonth = $state(new Date().getMonth());
	let calendarYear = $state(new Date().getFullYear());

	const profileEditFields = $derived(
		resolveFormFieldsByType(profileForms, 'PROFILE_EDIT', defaultProfileEditFields)
	);

	const API_BASE = import.meta.env.VITE_API_URL?.replace('/api/v1', '') || 'http://localhost:8001';

	async function handlePhotoUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		photoUploading = true;
		try {
			const result = await facultyApi.uploadPhoto(file);
			faculty = { ...faculty, photo: result.photo };
		} catch (err) {
			toastStore.addToast('Failed to upload photo', 'error');
		} finally {
			photoUploading = false;
		}
	}

	async function handleSignatureUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		signatureUploading = true;
		try {
			const result = await facultyApi.uploadSignature(file);
			faculty = { ...faculty, signature_image: result.signature_image };
		} catch (err) {
			toastStore.addToast('Failed to upload signature', 'error');
		} finally {
			signatureUploading = false;
		}
	}

	async function updateFacultyAvailability(status: 'Available' | 'Busy' | 'Unavailable') {
		try {
			await facultyApi.updateAvailabilityStatus(status);
			if (faculty) {
				faculty = { ...faculty, availability_status: status };
			}
		} catch (err) {
			toastStore.addToast('Failed to update availability status', 'error');
		}
	}

	async function handleAddInsurance() {
		if (!newInsurance.provider || !newInsurance.policy_number || !patient) return;
		addingInsurance = true;
		try {
			const result = await patientApi.addInsurancePolicy(patient.id, {
				provider: newInsurance.provider,
				policy_number: newInsurance.policy_number,
				valid_until: newInsurance.valid_until || undefined,
			});
			patient = {
				...patient,
				insurance_policies: [...(patient.insurance_policies || []), result],
			};
			newInsurance = { provider: '', policy_number: '', valid_until: '' };
			showAddInsurance = false;
		} catch (err) {
			toastStore.addToast('Failed to add insurance', 'error');
		} finally {
			addingInsurance = false;
		}
	}

	async function handleDeleteInsurance(policyId: string) {
		if (!patient) return;
		try {
			await patientApi.deleteInsurancePolicy(patient.id, policyId);
			patient = {
				...patient,
				insurance_policies: (patient.insurance_policies || []).filter((p: any) => p.id !== policyId),
			};
		} catch (err) {
			toastStore.addToast('Failed to delete insurance', 'error');
		}
	}

	function openEditModal() {
		if (!patient) return;
		profileFormValues = {
			name: patient.name || '',
			phone: patient.phone || '',
			email: patient.email || '',
			address: patient.address || '',
			blood_group: patient.blood_group || '',
		};
		showEditModal = true;
	}

	async function handleSaveProfile() {
		if (!patient) return;
		savingProfile = true;
		try {
			const submittedValues = await persistFormFiles(
				profileEditFields,
				profileFormValues,
				(file, options) => formsApi.uploadFile(file, options),
				'profile-edit'
			);
			await patientApi.updateProfile(patient.id, {
				name: asOptionalString(submittedValues.name),
				phone: asOptionalString(submittedValues.phone),
				email: asOptionalString(submittedValues.email),
				address: asOptionalString(submittedValues.address),
				blood_group: asOptionalString(submittedValues.blood_group),
			});
			patient = await patientApi.getCurrentPatient();
			showEditModal = false;
			profileFormValues = {};
			toastStore.addToast('Profile updated successfully', 'success');
		} catch (err) {
			toastStore.addToast('Failed to update profile', 'error');
		} finally {
			savingProfile = false;
		}
	}

	async function loadAttendanceCalendar() {
		if (!sp) return;
		try {
			attendanceCalendar = await studentApi.getAttendanceCalendar(sp.id, calendarMonth + 1, calendarYear);
		} catch (err) {
			// Calendar is optional - fail silently
		}
	}

	async function changeMonth(delta: number) {
		let newMonth = calendarMonth + delta;
		let newYear = calendarYear;
		if (newMonth > 11) {
			newMonth = 0;
			newYear++;
		} else if (newMonth < 0) {
			newMonth = 11;
			newYear--;
		}
		calendarMonth = newMonth;
		calendarYear = newYear;
		await loadAttendanceCalendar();
	}

	function getCalendarDays() {
		const firstDay = new Date(calendarYear, calendarMonth, 1).getDay();
		const daysInMonth = new Date(calendarYear, calendarMonth + 1, 0).getDate();
		const days: (number | null)[] = [];
		for (let i = 0; i < firstDay; i++) days.push(null);
		for (let i = 1; i <= daysInMonth; i++) days.push(i);
		return days;
	}

	function getAttendanceForDay(day: number): any | null {
		const dateStr = `${calendarYear}-${String(calendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
		return attendanceCalendar.find(a => a.session_date === dateStr);
	}

	onMount(async () => {
		try {
			if (role === 'PATIENT') {
				const [patientData, forms] = await Promise.all([
					patientApi.getCurrentPatient(),
					formsApi.getForms({ form_type: 'PROFILE_EDIT' }).catch(() => []),
				]);
				patient = patientData;
				profileForms = forms;
			} else if (role === 'STUDENT') {
				sp = await studentApi.getMe();
				await loadAttendanceCalendar();
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
			}
		} catch (err) {
			toastStore.addToast('Failed to load profile', 'error');
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-4">
	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else}
	{#if role === 'STUDENT' && sp}
		<!-- Student Profile Header -->
		<AquaCard>
			<div class="flex items-start gap-4">
				<div class="relative">
					<Avatar name={sp.name} size="lg" />
					<div class="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 2px solid white;">
						<CheckCircle2 class="w-3 h-3 text-white" />
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<div class="flex items-start justify-between">
						<div>
							<h2 class="text-xl font-bold text-gray-800">{sp.name}</h2>
							<p class="text-xs text-gray-500">Student ID: {sp.student_id}</p>
						</div>
						<span class="px-2 py-0.5 rounded-full text-xs font-bold shrink-0"
							style="background: linear-gradient(to bottom, #22c55e20, #22c55e10); color: #16a34a; border: 1px solid rgba(34,197,94,0.3);">
							GPA: {sp.gpa}/4.0
						</span>
					</div>
					<div class="flex items-center gap-1 mt-1 text-xs text-gray-500">
						<BookOpen class="w-3 h-3" />
						<span>{sp.degree}</span>
					</div>
					<div class="flex items-center gap-2 mt-2">
						<span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
							style="background: linear-gradient(to bottom, #3b82f620, #3b82f610); color: #2563eb; border: 1px solid rgba(59,130,246,0.3);">
							Year {sp.year}, Sem {sp.semester}
						</span>
					</div>
				</div>
			</div>
			<div class="mt-3 pt-3 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
				<div class="flex items-center gap-1">
					<CheckCircle2 class="w-3.5 h-3.5 text-green-500" />
					<span>{sp.academic_standing}</span>
				</div>
				<div class="flex items-center gap-1">
					<Calendar class="w-3.5 h-3.5 text-gray-400" />
				<span>Attendance: {sp.attendance?.overall ?? 0}%</span>
				</div>
			</div>
		</AquaCard>

		<!-- Academic Standing -->
		<AquaCard>
			{#snippet header()}
				<Award class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Academic Standing</span>
			{/snippet}

			<div class="space-y-4">
				<div class="p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.05);">
					<div class="flex items-center gap-2 mb-3">
						<BookOpen class="w-4 h-4 text-blue-600" />
						<span class="font-semibold text-gray-700 text-sm">Academic Progress</span>
					</div>
					<!-- Overall Attendance -->
					<div class="mb-3">
						<div class="flex justify-between text-xs mb-1">
							<span class="text-gray-600">Overall Attendance</span>
						<span class="font-semibold text-gray-700">{sp.attendance?.overall ?? 0}%</span>
					</div>
					<div class="w-full h-2 rounded-full bg-gray-200 overflow-hidden">
						<div class="h-full rounded-full transition-all"
							style="width: {sp.attendance?.overall ?? 0}%; background: linear-gradient(to right, #3b82f6, #2563eb);">
						</div>
					</div>
				</div>
				<!-- Clinical Attendance -->
				<div>
					<div class="flex justify-between text-xs mb-1">
						<span class="text-gray-600">Clinical Attendance</span>
						<span class="font-semibold text-gray-700">{sp.attendance?.clinical ?? 0}%</span>
					</div>
					<div class="w-full h-2 rounded-full bg-gray-200 overflow-hidden">
						<div class="h-full rounded-full transition-all"
							style="width: {sp.attendance?.clinical ?? 0}%; background: linear-gradient(to right, #2563eb, #1d4ed8);">
							</div>
						</div>
					</div>
				</div>

				<div class="flex items-center gap-2 text-sm text-gray-500">
					<User class="w-4 h-4 text-gray-400" />
					Academic Advisor: <span class="font-medium text-gray-700">{sp.academic_advisor}</span>
				</div>
			</div>
		</AquaCard>

		<!-- Disciplinary Actions -->
		{#if sp.disciplinary_actions.length > 0}
			<AquaCard>
				{#snippet header()}
					<AlertTriangle class="w-4 h-4 text-yellow-500 mr-2" />
					<span class="text-blue-900 font-semibold text-sm">Disciplinary Actions</span>
				{/snippet}
				<div class="space-y-3">
					{#each sp.disciplinary_actions as action}
						<div class="p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.05);">
							<div class="flex items-center justify-between mb-2">
								<div class="flex items-center gap-2">
									<CheckCircle2 class="w-4 h-4 text-green-500" />
									<span class="font-semibold text-gray-800 text-sm">{action.type}</span>
								</div>
								<span class="px-2 py-0.5 rounded text-xs font-bold"
									style="background: {action.status === 'Resolved' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)'};
									       color: {action.status === 'Resolved' ? '#16a34a' : '#dc2626'};
									       border: 1px solid {action.status === 'Resolved' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'};">
									{action.status}
								</span>
							</div>
							<p class="text-sm text-gray-700">{action.description}</p>
							<p class="text-xs text-gray-500 mt-1">Date: {action.date}</p>
							<p class="text-xs text-gray-500 mt-2">{action.details}</p>
							{#if action.resolution}
								<p class="text-xs text-gray-600 mt-1">{action.resolution}</p>
							{/if}
						</div>
					{/each}
				</div>
			</AquaCard>
		{/if}

		<!-- Emergency Contact -->
		{#if sp.emergency_contact}
		<AquaCard>
			{#snippet header()}
				<Phone class="w-4 h-4 text-green-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Emergency Contact</span>
			{/snippet}
			<div class="p-3 rounded-lg" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.05);">
				<div class="flex items-center gap-2 mb-2">
					<div class="w-8 h-8 rounded-full flex items-center justify-center"
						style="background: linear-gradient(to bottom, #ef4444, #dc2626);">
						<User class="w-4 h-4 text-white" />
					</div>
					<div>
						<p class="font-semibold text-gray-800 text-sm">{sp.emergency_contact.name}</p>
						<p class="text-xs text-gray-500">{sp.emergency_contact.relationship}</p>
					</div>
				</div>
				<div class="space-y-2 ml-10">
					<div class="flex items-center gap-2 text-sm">
						<div class="w-6 h-6 rounded-full flex items-center justify-center" style="background: rgba(239,68,68,0.1);">
							<Phone class="w-3 h-3 text-red-500" />
						</div>
						<div>
							<p class="text-gray-800">{sp.emergency_contact.phone}</p>
							<p class="text-xs text-gray-400">Mobile</p>
						</div>
					</div>
					<div class="flex items-center gap-2 text-sm">
						<div class="w-6 h-6 rounded-full flex items-center justify-center" style="background: rgba(239,68,68,0.1);">
							<Mail class="w-3 h-3 text-red-500" />
						</div>
						<div>
							<p class="text-gray-800">{sp.emergency_contact.email}</p>
							<p class="text-xs text-gray-400">Email</p>
						</div>
					</div>
					<div class="flex items-center gap-2 text-sm">
						<div class="w-6 h-6 rounded-full flex items-center justify-center" style="background: rgba(239,68,68,0.1);">
							<MapPin class="w-3 h-3 text-red-500" />
						</div>
						<div>
							<p class="text-gray-800">{sp.emergency_contact.address}</p>
							<p class="text-xs text-gray-400">Address</p>
						</div>
					</div>
				</div>
			</div>
		</AquaCard>
		{/if}

		<!-- Attendance Details -->
		<AquaCard>
			{#snippet header()}
				<Calendar class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Attendance Details</span>
			{/snippet}
			{@const attendanceItems = [
				{ label: 'Clinical Sessions', value: sp.attendance?.clinical ?? 0 },
				{ label: 'Lectures', value: sp.attendance?.lecture ?? 0 },
				{ label: 'Laboratory Sessions', value: sp.attendance?.lab ?? 0 },
				{ label: 'Overall Attendance', value: sp.attendance?.overall ?? 0 },
			]}
			<div class="grid grid-cols-2 gap-3 mb-4">
				{#each attendanceItems as item}
					<div class="p-3 rounded-xl text-center" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
						<p class="text-[10px] text-gray-500 mb-1">{item.label}</p>
						<div class="flex items-center justify-center gap-1">
							<span class="text-2xl font-bold text-gray-800">{item.value}%</span>
							{#if item.value >= 90}
								<CheckCircle2 class="w-5 h-5 text-green-500" />
							{:else if item.value >= 75}
								<AlertTriangle class="w-5 h-5 text-yellow-500" />
							{:else}
								<XCircle class="w-5 h-5 text-red-500" />
							{/if}
						</div>
					</div>
				{/each}
			</div>

			<!-- Recent Absences -->
			{#if sp.recent_absences && sp.recent_absences.length > 0}
				<h4 class="text-sm font-semibold text-gray-600 mb-2">Recent Absences</h4>
				<div class="space-y-2">
					{#each sp.recent_absences as absence}
						<div class="flex items-center gap-3 p-2 rounded-lg" style="background: #f8f9fb;">
							<div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
								style="background: {absence.status === 'Approved' ? '#22c55e' : absence.status === 'Unapproved' ? '#ef4444' : '#f97316'}20;">
								{#if absence.status === 'Approved'}
									<CheckCircle2 class="w-4 h-4 text-green-500" />
								{:else if absence.status === 'Unapproved'}
									<XCircle class="w-4 h-4 text-red-500" />
								{:else}
									<Clock class="w-4 h-4 text-orange-500" />
								{/if}
							</div>
							<div class="flex-1">
								<p class="text-sm text-gray-800 font-medium">{absence.date}</p>
								<p class="text-xs text-gray-500">{absence.reason}</p>
							</div>
							<span class="px-2 py-0.5 rounded text-xs font-bold"
								style="background: {absence.status === 'Approved' ? 'rgba(34,197,94,0.1)' : absence.status === 'Unapproved' ? 'rgba(239,68,68,0.1)' : 'rgba(249,115,22,0.1)'};
								       color: {absence.status === 'Approved' ? '#16a34a' : absence.status === 'Unapproved' ? '#dc2626' : '#ea580c'};
								       border: 1px solid {absence.status === 'Approved' ? 'rgba(34,197,94,0.2)' : absence.status === 'Unapproved' ? 'rgba(239,68,68,0.2)' : 'rgba(249,115,22,0.2)'};">
								{absence.status}
							</span>
						</div>
					{/each}
				</div>
			{/if}
		</AquaCard>

		<!-- Clinic Attendance Calendar -->
		<AquaCard>
			{#snippet header()}
				<Clock class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Clinic Attendance History</span>
			{/snippet}
			
			<div class="flex items-center justify-between mb-4">
				<button class="p-2 rounded-lg hover:bg-gray-100" aria-label="Previous month" onclick={() => changeMonth(-1)}>
					<svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
				</button>
				<h4 class="font-semibold text-gray-700">
					{new Date(calendarYear, calendarMonth).toLocaleString('default', { month: 'long', year: 'numeric' })}
				</h4>
				<button class="p-2 rounded-lg hover:bg-gray-100" aria-label="Next month" onclick={() => changeMonth(1)}>
					<svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>
			</div>

			<div class="grid grid-cols-7 gap-1 text-center text-xs text-gray-500 mb-2">
				<span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span>
			</div>
			<div class="grid grid-cols-7 gap-1">
				{#each getCalendarDays() as day}
					{#if day === null}
						<div class="h-10"></div>
					{:else}
						{@const attendance = getAttendanceForDay(day)}
						<div class="h-10 flex items-center justify-center rounded-lg text-sm relative"
							style="background: {attendance?.checked_in_at ? (attendance.checked_out_at ? '#dcfce7' : '#fef3c7') : '#f8f9fb'};">
							<span class="font-medium {attendance?.checked_in_at ? (attendance.checked_out_at ? 'text-green-700' : 'text-yellow-700') : 'text-gray-600'}">
								{day}
							</span>
							{#if attendance?.checked_in_at}
								<span class="absolute bottom-0.5 w-1.5 h-1.5 rounded-full {attendance.checked_out_at ? 'bg-green-500' : 'bg-yellow-500'}"></span>
							{/if}
						</div>
					{/if}
				{/each}
			</div>

			<div class="flex items-center justify-center gap-4 mt-4 text-xs">
				<div class="flex items-center gap-1">
					<span class="w-3 h-3 rounded bg-green-200"></span>
					<span class="text-gray-600">Completed</span>
				</div>
				<div class="flex items-center gap-1">
					<span class="w-3 h-3 rounded bg-yellow-200"></span>
					<span class="text-gray-600">In Progress</span>
				</div>
			</div>
		</AquaCard>

	{:else if role === 'PATIENT' && patient}
		<!-- Patient Header with Blue Gradient Banner -->
		<div class="rounded-xl overflow-hidden shadow-md"
			style="background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1), 0 0 1px rgba(0,0,0,0.25); border: 1px solid rgba(0,0,0,0.1);">
			<div class="relative h-36"
				style="background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%); box-shadow: inset 0 -1px 0 rgba(255,255,255,0.3);">
				<!-- Glossy overlay -->
				<div class="absolute inset-0 pointer-events-none rounded-t-xl"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.15) 30%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0) 51%, rgba(0,0,0,0.05) 100%);"></div>
				<!-- Avatar positioned at bottom-left -->
				<div class="absolute -bottom-16 left-4">
					<div class="h-28 w-28 rounded-xl overflow-hidden shadow-lg"
						style="border: 3px solid white;">
						{#if patient.photo}
							<img src="{API_BASE}{patient.photo}" alt={patient.name} class="h-full w-full object-cover" />
						{:else}
							<div class="h-full w-full flex items-center justify-center text-3xl font-bold text-white"
								style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">
								{patient.name?.charAt(0) ?? '?'}
							</div>
						{/if}
					</div>
				</div>
			</div>
			<div class="pt-20 pb-4 px-4">
				<div class="flex items-center gap-2">
					<h2 class="text-xl font-bold text-gray-800">{patient.name}</h2>
					{#if patient.category === 'ELITE'}
						<Crown class="w-5 h-5 text-yellow-500" />
					{/if}
				</div>
				<p class="text-sm text-gray-500">Patient ID: {patient.patient_id}</p>
				<div class="flex gap-2 mt-2">
					<StatusBadge variant="success">
						<BadgeCheck class="w-3 h-3 mr-1" /> Verified
					</StatusBadge>
					<StatusBadge variant="info">{patient.category}</StatusBadge>
				</div>
			</div>
		</div>

		<!-- Personal & Contact Info Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
		<!-- Personal Information -->
		<div class="rounded-xl overflow-hidden"
			style="background-color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.1);">
			<div class="px-4 py-3 border-b flex items-center justify-between"
				style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1); border-bottom: 1px solid rgba(0,0,0,0.1);">
				<div class="flex items-center">
					<Shield class="w-4 h-4 text-blue-600 mr-2" />
					<h3 class="font-medium text-gray-800">Personal Information</h3>
				</div>
				<button
					onclick={openEditModal}
					class="px-2.5 py-1 rounded-md text-xs flex items-center cursor-pointer"
					style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);">
					<Edit3 class="w-3 h-3 mr-1 text-blue-700" />
					<span class="text-blue-700 font-medium">Edit</span>
				</button>
			</div>
			<div class="p-4 space-y-4">
				{#if patient.aadhaar_id}
					<div class="flex flex-col">
						<span class="text-sm text-gray-500">Aadhaar ID</span>
						<div class="flex items-center mt-1">
							<span class="text-gray-800 font-medium">{patient.aadhaar_id}</span>
							<div class="ml-2 px-2 py-0.5 rounded text-xs font-medium"
								style="background: linear-gradient(to bottom, #a7f3d0, #6ee7b7); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.7); border: 1px solid rgba(16,185,129,0.3); color: #065f46;">
								Verified
							</div>
						</div>
					</div>
				{/if}
				{#if patient.abha_id}
					<div class="flex flex-col">
						<span class="text-sm text-gray-500">ABHA ID</span>
						<div class="flex items-center mt-1">
							<span class="text-gray-800 font-medium">{patient.abha_id}</span>
							<div class="ml-2 px-2 py-0.5 rounded text-xs font-medium"
								style="background: linear-gradient(to bottom, #a7f3d0, #6ee7b7); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.7); border: 1px solid rgba(16,185,129,0.3); color: #065f46;">
								Verified
							</div>
						</div>
					</div>
				{/if}
				<div class="flex flex-col">
					<span class="text-sm text-gray-500">Date of Birth</span>
					<div class="flex items-center mt-1">
						<Calendar class="w-3.5 h-3.5 text-blue-600 mr-2" />
						<span class="text-gray-800">{new Date(patient.date_of_birth).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
					</div>
				</div>
				<div class="flex flex-col">
					<span class="text-sm text-gray-500">Gender</span>
					<div class="flex items-center mt-1">
						<User class="w-3.5 h-3.5 text-blue-600 mr-2" />
						<span class="text-gray-800">{patient.gender}</span>
					</div>
				</div>
				<div class="flex flex-col">
					<span class="text-sm text-gray-500">Blood Group</span>
					<div class="flex items-center mt-1">
						<Droplet class="w-3.5 h-3.5 text-red-600 mr-2" />
						<span class="text-gray-800">{patient.blood_group}</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Contact Information -->
		<div class="rounded-xl overflow-hidden"
			style="background-color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.1);">
			<div class="px-4 py-3 border-b flex items-center"
				style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1); border-bottom: 1px solid rgba(0,0,0,0.1);">
				<Phone class="w-4 h-4 text-blue-600 mr-2" />
				<h3 class="font-medium text-gray-800">Contact Information</h3>
			</div>
			<div class="p-4 space-y-4">
				<div class="flex items-start p-3 rounded-lg"
					style="background-color: rgba(249,250,251,0.7); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1);">
					<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
						<Phone class="w-3.5 h-3.5 text-white" />
					</div>
					<div>
						<span class="text-gray-800 font-medium">{patient.phone}</span>
						<p class="text-xs text-gray-500">Primary</p>
					</div>
				</div>
				{#if patient.email}
					<div class="flex items-start p-3 rounded-lg"
						style="background-color: rgba(249,250,251,0.7); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1);">
						<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
							style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
							<Mail class="w-3.5 h-3.5 text-white" />
						</div>
						<div>
							<span class="text-gray-800 font-medium">{patient.email}</span>
							<p class="text-xs text-gray-500">Email</p>
						</div>
					</div>
				{/if}
				<div class="flex items-start p-3 rounded-lg"
					style="background-color: rgba(249,250,251,0.7); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.1);">
					<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
						style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
						<MapPin class="w-3.5 h-3.5 text-white" />
					</div>
					<div>
						<span class="text-gray-800 font-medium">{patient.address}</span>
						<p class="text-xs text-gray-500">Address</p>
					</div>
				</div>
			</div>
		</div>
		</div> <!-- end Personal & Contact grid -->

		<!-- Emergency Contact -->
		{#if patient.emergency_contact}
			<div class="rounded-xl overflow-hidden"
				style="background-color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.1);">
				<div class="px-4 py-3 border-b flex items-center"
					style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1); border-bottom: 1px solid rgba(0,0,0,0.1);">
					<AlertTriangle class="w-4 h-4 text-red-600 mr-2" />
					<h3 class="font-medium text-gray-800">Emergency Contact</h3>
				</div>
				<div class="p-4">
					<div class="p-3 rounded-lg"
						style="background-color: rgba(254,242,242,0.4); box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); border: 1px solid rgba(252,165,165,0.3);">
						<div class="flex items-start mb-3">
							<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
								style="background: linear-gradient(to bottom, #f87171, #dc2626); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
								<User class="w-3.5 h-3.5 text-white" />
							</div>
							<div>
								<span class="text-gray-800 font-medium">{patient.emergency_contact.name}</span>
								<p class="text-xs text-gray-500">{patient.emergency_contact.relationship}</p>
							</div>
						</div>
						<div class="flex items-start">
							<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
								style="background: linear-gradient(to bottom, #f87171, #dc2626); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
								<Phone class="w-3.5 h-3.5 text-white" />
							</div>
							<div>
								<span class="text-gray-800 font-medium">{patient.emergency_contact.phone}</span>
								<p class="text-xs text-gray-500">Mobile</p>
							</div>
						</div>
						{#if patient.emergency_contact.email}
							<div class="flex items-start mt-3">
								<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
									style="background: linear-gradient(to bottom, #f87171, #dc2626); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
									<Mail class="w-3.5 h-3.5 text-white" />
								</div>
								<div>
									<span class="text-gray-800 font-medium">{patient.emergency_contact.email}</span>
									<p class="text-xs text-gray-500">Email</p>
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}

		<!-- Insurance Information -->
		<div class="rounded-xl overflow-hidden"
			style="background-color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.08), 0 0 1px rgba(0,0,0,0.2); border: 1px solid rgba(0,0,0,0.1);">
			<div class="px-4 py-3 border-b flex items-center justify-between"
				style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1); border-bottom: 1px solid rgba(0,0,0,0.1);">
				<div class="flex items-center">
					<CreditCard class="w-4 h-4 text-blue-600 mr-2" />
					<h3 class="font-medium text-gray-800">Insurance Information</h3>
				</div>
				<button
					onclick={() => showAddInsurance = !showAddInsurance}
					class="px-2.5 py-1 rounded-md text-xs flex items-center cursor-pointer"
					style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);">
					{#if showAddInsurance}
						<span class="text-blue-700 font-medium">Cancel</span>
					{:else}
						<Plus class="w-3 h-3 mr-1 text-blue-700" />
						<span class="text-blue-700 font-medium">Add</span>
					{/if}
				</button>
			</div>

			<!-- Add Insurance Form -->
			{#if showAddInsurance}
				<div class="p-4 border-b" style="background-color: rgba(243,244,246,0.6); border-bottom: 1px solid rgba(0,0,0,0.1);">
					<div class="space-y-3">
						<div>
							<label for="ins-provider" class="block text-sm text-gray-600 mb-1">Insurance Provider</label>
							<div style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem; background-color: rgba(255,255,255,0.8);">
								<input id="ins-provider" type="text" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700"
									placeholder="Provider name" bind:value={newInsurance.provider} />
							</div>
						</div>
						<div>
							<label for="ins-policy" class="block text-sm text-gray-600 mb-1">Policy Number</label>
							<div style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem; background-color: rgba(255,255,255,0.8);">
								<input id="ins-policy" type="text" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700"
									placeholder="Policy number" bind:value={newInsurance.policy_number} />
							</div>
						</div>
						<div>
							<label for="ins-valid" class="block text-sm text-gray-600 mb-1">Valid Until</label>
							<div style="box-shadow: inset 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.2); border-radius: 0.375rem; background-color: rgba(255,255,255,0.8);">
								<input id="ins-valid" type="date" class="w-full px-3 py-2 bg-transparent outline-none text-gray-700"
									bind:value={newInsurance.valid_until} />
							</div>
						</div>
						<button
							onclick={handleAddInsurance}
							disabled={addingInsurance || !newInsurance.provider || !newInsurance.policy_number}
							class="w-full py-2 rounded-md text-white text-sm font-medium cursor-pointer disabled:opacity-50"
							style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
							{addingInsurance ? 'Adding...' : 'Add Insurance'}
						</button>
					</div>
				</div>
			{/if}

			<!-- Insurance List -->
			<div>
				{#if patient.insurance_policies && patient.insurance_policies.length > 0}
					{#each patient.insurance_policies as insurance}
						<div class="p-4 border-b last:border-b-0" style="border-bottom: 1px solid rgba(0,0,0,0.05);">
							<div class="flex items-start">
								<div class="w-8 h-8 rounded-full flex items-center justify-center mr-3 shrink-0"
									style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
									<CreditCard class="w-3.5 h-3.5 text-white" />
								</div>
								<div class="flex-1">
									<span class="text-gray-800 font-medium">{insurance.provider}</span>
									<div class="flex justify-between items-center mt-1">
										<div>
											<p class="text-sm text-gray-600">Policy: {insurance.policy_number}</p>
											{#if insurance.valid_until}
												<p class="text-xs text-gray-500">Valid until: {new Date(insurance.valid_until).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
											{/if}
										</div>
										<button
											onclick={() => handleDeleteInsurance(insurance.id)}
											class="w-7 h-7 rounded-full flex items-center justify-center cursor-pointer"
											style="background: linear-gradient(to bottom, #fee2e2, #fca5a5); border: 1px solid rgba(220,38,38,0.3); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.7);">
											<Trash2 class="w-3.5 h-3.5 text-red-700" />
										</button>
									</div>
								</div>
							</div>
						</div>
					{/each}
				{:else}
					<div class="p-6 text-center" style="background-color: rgba(249,250,251,0.7);">
						<div class="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center"
							style="background: linear-gradient(to bottom, #e5e7eb, #d1d5db); box-shadow: 0 1px 3px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.1);">
							<AlertTriangle class="w-5 h-5 text-gray-400" />
						</div>
						<p class="text-gray-500 text-sm">No insurance information added yet</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Allergies -->
		{#if patient.allergies && patient.allergies.length > 0}
			<AquaCard>
				{#snippet header()}
					<AlertTriangle class="w-4 h-4 text-orange-500 mr-2" />
					<span class="text-blue-900 font-semibold text-sm">Allergies</span>
				{/snippet}
				<div class="space-y-2">
					{#each patient.allergies as allergy}
						<div class="flex items-center justify-between py-1">
							<span class="text-sm text-gray-800">{allergy.allergen}</span>
							<StatusBadge variant={allergy.severity === 'HIGH' ? 'critical' : allergy.severity === 'MEDIUM' ? 'warning' : 'normal'}>
								{allergy.severity}
							</StatusBadge>
						</div>
					{/each}
				</div>
			</AquaCard>
		{/if}

		<!-- Edit Profile Modal -->
		<AquaModal open={showEditModal} title="Edit Personal Info" onclose={() => { showEditModal = false; profileFormValues = {}; }}>
			<form onsubmit={(e) => { e.preventDefault(); handleSaveProfile(); }} class="space-y-4">
				<DynamicFormRenderer
					fields={profileEditFields}
					bind:values={profileFormValues}
					idPrefix="profile-edit"
				/>
				<button
					type="submit"
					disabled={savingProfile || !profileFormValues.name || !profileFormValues.phone}
					class="w-full py-2 rounded-md text-white text-sm font-medium cursor-pointer disabled:opacity-50"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4); border: 1px solid rgba(0,0,0,0.2);">
					{savingProfile ? 'Saving...' : 'Save Changes'}
				</button>
			</form>
		</AquaModal>

	{:else if role === 'FACULTY' && faculty}
		<!-- Faculty Profile Header with Photo Upload -->
		<AquaCard>
			<div class="text-center">
				<div class="relative inline-block">
					{#if faculty.photo}
						<img src="{API_BASE}{faculty.photo}" alt={faculty.name}
							class="w-20 h-20 rounded-full object-cover border-3 border-white shadow-lg" />
					{:else}
						<Avatar name={faculty.name} size="lg" />
					{/if}
					<button class="absolute -bottom-1 -right-1 w-7 h-7 rounded-full flex items-center justify-center cursor-pointer shadow-md"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 2px solid white;"
						onclick={() => photoInput?.click()}
						disabled={photoUploading}>
						{#if photoUploading}
							<div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
						{:else}
							<Camera class="w-3 h-3 text-white" />
						{/if}
					</button>
					<input bind:this={photoInput} type="file" accept="image/*" class="hidden" onchange={handlePhotoUpload} />
				</div>
				<h2 class="text-xl font-bold text-blue-900 mt-3">{faculty.name}</h2>
				<p class="text-sm text-gray-600 mt-1">{faculty.faculty_id}</p>
				<StatusBadge variant="info">{faculty.department}</StatusBadge>
			</div>
		</AquaCard>

		<!-- Availability Status -->
		<AquaCard padding={false}>
			<div class="px-4 py-3 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<div
						class="w-3 h-3 rounded-full"
						style="background: {faculty.availability_status === 'Available' ? '#22c55e' : faculty.availability_status === 'Busy' ? '#f59e0b' : '#ef4444'};"
					></div>
					<span class="text-sm font-semibold text-gray-700">Status: {faculty.availability_status || 'Available'}</span>
				</div>
				<div class="flex items-center gap-1.5">
					{#each ['Available', 'Busy', 'Unavailable'] as status}
						{@const isActive = (faculty.availability_status || 'Available') === status}
						{@const statusColor = status === 'Available' ? '#22c55e' : status === 'Busy' ? '#f59e0b' : '#ef4444'}
						<button
							class="px-3 py-1 rounded-full text-xs font-medium cursor-pointer transition-all"
							style="background: {isActive ? statusColor : 'transparent'};
								   color: {isActive ? 'white' : '#6b7280'};
								   border: 1px solid {isActive ? statusColor : '#e5e7eb'};"
							onclick={() => updateFacultyAvailability(status as 'Available' | 'Busy' | 'Unavailable')}
						>
							{status}
						</button>
					{/each}
				</div>
			</div>
		</AquaCard>

		<!-- Professional Info -->
		<AquaCard>
			{#snippet header()}
				<Stethoscope class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Professional Info</span>
			{/snippet}
			<div class="space-y-2">
				<div class="flex justify-between"><span class="text-sm text-gray-500">Department</span><span class="text-sm text-gray-800">{faculty.department}</span></div>
				<div class="flex justify-between"><span class="text-sm text-gray-500">Specialty</span><span class="text-sm text-gray-800">{faculty.specialty}</span></div>
				<div class="flex justify-between"><span class="text-sm text-gray-500">Phone</span><span class="text-sm text-blue-600">{faculty.phone}</span></div>
				<div class="flex justify-between"><span class="text-sm text-gray-500">Email</span><span class="text-sm text-blue-600">{faculty.email}</span></div>
				<div class="flex justify-between"><span class="text-sm text-gray-500">Availability</span><span class="text-sm text-gray-800">{faculty.availability}</span></div>
			</div>
		</AquaCard>

		<!-- Signature Management -->
		<AquaCard>
			{#snippet header()}
				<PenTool class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Digital Signature</span>
			{/snippet}
			<p class="text-xs text-gray-500 mb-3">This signature will appear on official prescriptions and documents.</p>

			{#if faculty.signature_image}
				<div class="p-4 rounded-xl text-center" style="background: #f8f9fb; border: 1px solid rgba(0,0,0,0.06);">
					<img src="{API_BASE}{faculty.signature_image}" alt="Signature"
						class="max-h-20 mx-auto" style="image-rendering: auto;" />
					<p class="text-xs text-gray-400 mt-2">Current signature</p>
				</div>
			{:else}
				<div class="p-6 rounded-xl text-center" style="background: #f8f9fb; border: 2px dashed rgba(0,0,0,0.1);">
					<PenTool class="w-8 h-8 text-gray-300 mx-auto mb-2" />
					<p class="text-sm text-gray-400">No signature uploaded</p>
					<p class="text-xs text-gray-400 mt-1">Upload an image of your handwritten signature</p>
				</div>
			{/if}

			<button class="w-full mt-3 py-2.5 rounded-lg text-sm font-medium cursor-pointer flex items-center justify-center gap-2"
				style="background: linear-gradient(to bottom, #4d90fe, #2563eb); color: white;
					   box-shadow: 0 2px 6px rgba(37,99,235,0.3);"
				onclick={() => signatureInput?.click()}
				disabled={signatureUploading}>
				{#if signatureUploading}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
					Uploading...
				{:else}
					<Upload class="w-4 h-4" />
					{faculty.signature_image ? 'Replace Signature' : 'Upload Signature'}
				{/if}
			</button>
			<input bind:this={signatureInput} type="file" accept="image/*" class="hidden" onchange={handleSignatureUpload} />
		</AquaCard>
	{/if}
	{/if}
</div>
