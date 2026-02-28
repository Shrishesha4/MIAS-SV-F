<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { facultyApi } from '$lib/api/faculty';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import {
		User, Phone, Mail, MapPin, Calendar, Shield, Crown,
		Heart, AlertTriangle, GraduationCap, Stethoscope, BadgeCheck,
		Award, CheckCircle2, BookOpen, Clock, XCircle, CircleDot,
		Upload, PenTool, Camera, Image
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
	let photoInput: HTMLInputElement;
	let signatureInput: HTMLInputElement;

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
			console.error('Failed to upload photo', err);
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
			console.error('Failed to upload signature', err);
		} finally {
			signatureUploading = false;
		}
	}

	function getAttendanceIcon(value: number) {
		return value >= 90 ? 'good' : value >= 75 ? 'warn' : 'bad';
	}

	onMount(async () => {
		try {
			if (role === 'PATIENT') {
				patient = await patientApi.getCurrentPatient();
			} else if (role === 'STUDENT') {
				sp = await studentApi.getMe();
			} else if (role === 'FACULTY') {
				faculty = await facultyApi.getMe();
			}
		} catch (err) {
			console.error('Failed to load profile', err);
		} finally {
			loading = false;
		}
	});
</script>

<div class="px-4 py-4 space-y-4">
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
						<p class="text-xs text-gray-500">{sp.emergency_contact.relationship_ || sp.emergency_contact.relationship}</p>
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

	{:else if role === 'PATIENT' && patient}
		<!-- Patient Profile -->
		<AquaCard>
			<div class="text-center">
				<Avatar name={patient.name} size="lg" />
				<div class="mt-3 flex items-center justify-center gap-2">
					<h2 class="text-xl font-bold text-blue-900">{patient.name}</h2>
					{#if patient.category === 'ELITE'}
						<Crown class="w-5 h-5 text-yellow-500" />
					{/if}
				</div>
				<p class="text-sm text-gray-600 mt-1">{patient.patient_id}</p>
				<div class="flex justify-center gap-2 mt-2">
					<StatusBadge variant="success">
						<BadgeCheck class="w-3 h-3 mr-1" /> Verified
					</StatusBadge>
					<StatusBadge variant="info">{patient.category}</StatusBadge>
				</div>
			</div>
		</AquaCard>

		<AquaCard>
			{#snippet header()}
				<User class="w-4 h-4 text-blue-600 mr-2" />
				<span class="text-blue-900 font-semibold text-sm">Personal Information</span>
			{/snippet}
			<div class="space-y-3">
				<div class="flex items-center gap-3">
					<Calendar class="w-4 h-4 text-gray-400" />
					<div>
						<p class="text-xs text-gray-500">Date of Birth</p>
						<p class="text-sm text-gray-800">{new Date(patient.date_of_birth).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<Heart class="w-4 h-4 text-gray-400" />
					<div>
						<p class="text-xs text-gray-500">Blood Group</p>
						<p class="text-sm text-gray-800">{patient.blood_group}</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<Phone class="w-4 h-4 text-gray-400" />
					<div>
						<p class="text-xs text-gray-500">Phone</p>
						<p class="text-sm text-gray-800">{patient.phone}</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<Mail class="w-4 h-4 text-gray-400" />
					<div>
						<p class="text-xs text-gray-500">Email</p>
						<p class="text-sm text-gray-800">{patient.email}</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<MapPin class="w-4 h-4 text-gray-400" />
					<div>
						<p class="text-xs text-gray-500">Address</p>
						<p class="text-sm text-gray-800">{patient.address}</p>
					</div>
				</div>
			</div>
		</AquaCard>

		{#if patient.emergency_contact}
			<AquaCard>
				{#snippet header()}
					<Phone class="w-4 h-4 text-red-500 mr-2" />
					<span class="text-blue-900 font-semibold text-sm">Emergency Contact</span>
				{/snippet}
				<div class="space-y-2">
					<div class="flex justify-between"><span class="text-sm text-gray-500">Name</span><span class="text-sm text-gray-800 font-medium">{patient.emergency_contact.name}</span></div>
					<div class="flex justify-between"><span class="text-sm text-gray-500">Relationship</span><span class="text-sm text-gray-800">{patient.emergency_contact.relationship_ || patient.emergency_contact.relationship}</span></div>
					<div class="flex justify-between"><span class="text-sm text-gray-500">Phone</span><span class="text-sm text-blue-600">{patient.emergency_contact.phone}</span></div>
				</div>
			</AquaCard>
		{/if}

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
						onclick={() => photoInput.click()}
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
				onclick={() => signatureInput.click()}
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
