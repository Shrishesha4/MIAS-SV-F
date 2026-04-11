<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import {
		adminApi,
		type AdminCreateUserPayload,
		type AdminUser,
		type Department,
		type PatientCategoryConfig,
		type Programme,
	} from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import {
		Search, Shield, ShieldOff, Trash2,
		ChevronRight, Plus, User
	} from 'lucide-svelte';

	const auth = get(authStore);
	type CreateUserRole = 'PATIENT' | 'STUDENT' | 'FACULTY' | 'ADMIN' | 'RECEPTION' | 'NURSE';

	type CreateUserFormData = {
		username: string;
		email: string;
		password: string;
		name: string;
		photo: string;
		date_of_birth: string;
		gender: string;
		blood_group: string;
		phone: string;
		address: string;
		category: string;
		aadhaar_id: string;
		abha_id: string;
		primary_diagnosis: string;
		diagnosis_doctor: string;
		diagnosis_date: string;
		diagnosis_time: string;
		year: string;
		semester: string;
		program: string;
		degree: string;
		gpa: string;
		academic_standing: string;
		academic_advisor: string;
		department: string;
		specialty: string;
		availability: string;
		hospital: string;
		ward: string;
		shift: string;
	};

	const genderOptions = ['MALE', 'FEMALE', 'OTHER'];
	const bloodGroupOptions = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
	const academicStandingOptions = ['Good Standing', 'Probation', 'At Risk', 'Honors'];

	function createEmptyUserData(): CreateUserFormData {
		return {
			username: '',
			email: '',
			password: '',
			name: '',
			photo: '',
			date_of_birth: '',
			gender: 'OTHER',
			blood_group: '',
			phone: '',
			address: '',
			category: '',
			aadhaar_id: '',
			abha_id: '',
			primary_diagnosis: '',
			diagnosis_doctor: '',
			diagnosis_date: '',
			diagnosis_time: '',
			year: '',
			semester: '',
			program: '',
			degree: '',
			gpa: '',
			academic_standing: 'Good Standing',
			academic_advisor: '',
			department: '',
			specialty: '',
			availability: '',
			hospital: '',
			ward: '',
			shift: '',
		};
	}

	let loading = $state(true);
	let error = $state('');
	let users: AdminUser[] = $state([]);
	let total = $state(0);
	let currentPage = $state(1);
	let searchQuery = $state('');
	let roleFilter = $state('');
	let statusFilter = $state('');
	let confirmModal = $state(false);
	let confirmAction: (() => Promise<void>) | null = $state(null);
	let confirmMessage = $state('');
	let actionLoading = $state(false);

	// Create user modal
	let createUserModal = $state(false);
	let newUserRole = $state<CreateUserRole>('NURSE');
	let newUserData = $state<CreateUserFormData>(createEmptyUserData());
	let creatingUser = $state(false);
	let departments = $state.raw<Department[]>([]);
	let programmes = $state.raw<Programme[]>([]);
	let patientCategories = $state.raw<PatientCategoryConfig[]>([]);

	// Read initial filter from URL
	onMount(() => {
		if (auth.role !== 'ADMIN') { goto('/dashboard'); return; }
		const params = new URLSearchParams(window.location.search);
		roleFilter = params.get('role') || '';
		void loadUsers();
		void loadCreateUserOptions();
	});

	function normalizeOptionalString(value: string): string | undefined {
		const trimmed = value.trim();
		return trimmed ? trimmed : undefined;
	}

	function parseOptionalInteger(value: string): number | undefined {
		const trimmed = value.trim();
		if (!trimmed) return undefined;
		const parsed = Number.parseInt(trimmed, 10);
		return Number.isFinite(parsed) ? parsed : undefined;
	}

	function parseOptionalFloat(value: string): number | undefined {
		const trimmed = value.trim();
		if (!trimmed) return undefined;
		const parsed = Number.parseFloat(trimmed);
		return Number.isFinite(parsed) ? parsed : undefined;
	}

	function defaultPatientCategoryName(): string {
		return patientCategories.find((category) => category.is_default)?.name || patientCategories[0]?.name || '';
	}

	function resetCreateUserForm(role: CreateUserRole = 'NURSE') {
		newUserRole = role;
		const next = createEmptyUserData();
		next.category = defaultPatientCategoryName();
		newUserData = next;
	}

	function openCreateUserModal() {
		resetCreateUserForm('NURSE');
		createUserModal = true;
	}

	function handleCreateRoleChange(role: CreateUserRole) {
		newUserRole = role;
		if (role === 'PATIENT' && !newUserData.category) {
			newUserData.category = defaultPatientCategoryName();
		}
		if (role === 'STUDENT' && !newUserData.academic_standing) {
			newUserData.academic_standing = 'Good Standing';
		}
	}

	async function loadCreateUserOptions() {
		try {
			const [departmentItems, programmeItems, categoryItems] = await Promise.all([
				adminApi.getDepartments(),
				adminApi.getProgrammes(),
				adminApi.getPatientCategories(),
			]);
			departments = departmentItems.filter((department) => department.is_active);
			programmes = programmeItems.filter((programme) => programme.is_active);
			patientCategories = categoryItems.filter((category) => category.is_active);
			if (!newUserData.category) {
				newUserData.category = defaultPatientCategoryName();
			}
		} catch {
			// Keep the modal usable even if auxiliary options fail to load.
		}
	}

	async function loadUsers() {
		loading = true;
		error = '';
		try {
			const params: any = { page: currentPage, limit: 20 };
			if (roleFilter) params.role = roleFilter;
			if (searchQuery) params.search = searchQuery;
			if (statusFilter) params.status = statusFilter;
			const res = await adminApi.getUsers(params);
			users = res.items;
			total = res.total;
		} catch (e: any) {
			error = e.response?.data?.detail || 'Failed to load users';
		} finally {
			loading = false;
		}
	}

	function handleSearch() {
		currentPage = 1;
		loadUsers();
	}

	function setRoleFilter(r: string) {
		roleFilter = r;
		currentPage = 1;
		loadUsers();
	}

	function setStatusFilter(s: string) {
		statusFilter = s;
		currentPage = 1;
		loadUsers();
	}

	async function toggleBlock(u: AdminUser) {
		confirmMessage = u.is_active
			? `Block user "${u.name}" (${u.username})? They won't be able to log in.`
			: `Unblock user "${u.name}" (${u.username})?`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				if (u.is_active) {
					await adminApi.blockUser(u.id);
				} else {
					await adminApi.unblockUser(u.id);
				}
				await loadUsers();
			} catch (e: any) {
				error = e.response?.data?.detail || 'Action failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function deleteUser(u: AdminUser) {
		confirmMessage = `Permanently delete user "${u.name}" (${u.username})? This cannot be undone.`;
		confirmAction = async () => {
			actionLoading = true;
			try {
				await adminApi.deleteUser(u.id);
				await loadUsers();
			} catch (e: any) {
				error = e.response?.data?.detail || 'Delete failed';
			} finally {
				actionLoading = false;
				confirmModal = false;
			}
		};
		confirmModal = true;
	}

	async function createUser() {
		if (!newUserData.username.trim() || !newUserData.email.trim() || !newUserData.password || !newUserData.name.trim()) {
			toastStore.addToast('Username, email, password, and full name are required', 'error');
			return;
		}

		if (newUserRole === 'PATIENT' && !newUserData.date_of_birth) {
			toastStore.addToast('Date of birth is required for patients', 'error');
			return;
		}

		if (newUserRole === 'STUDENT') {
			if (!newUserData.year.trim() || !newUserData.semester.trim() || !newUserData.program.trim()) {
				toastStore.addToast('Year, semester, and program are required for students', 'error');
				return;
			}
			if (parseOptionalInteger(newUserData.year) === undefined || parseOptionalInteger(newUserData.semester) === undefined) {
				toastStore.addToast('Year and semester must be valid numbers', 'error');
				return;
			}
		}

		if (newUserRole === 'FACULTY' && !newUserData.department.trim()) {
			toastStore.addToast('Department is required for faculty', 'error');
			return;
		}

		if (newUserData.gpa.trim() && parseOptionalFloat(newUserData.gpa) === undefined) {
			toastStore.addToast('GPA must be a valid number', 'error');
			return;
		}

		const payload: AdminCreateUserPayload = {
			username: newUserData.username.trim(),
			email: newUserData.email.trim(),
			password: newUserData.password,
			role: newUserRole,
			name: newUserData.name.trim(),
			photo: normalizeOptionalString(newUserData.photo),
		};

		if (newUserRole === 'PATIENT') {
			payload.date_of_birth = newUserData.date_of_birth;
			payload.gender = newUserData.gender;
			payload.blood_group = normalizeOptionalString(newUserData.blood_group);
			payload.phone = normalizeOptionalString(newUserData.phone);
			payload.address = normalizeOptionalString(newUserData.address);
			payload.category = normalizeOptionalString(newUserData.category);
			payload.aadhaar_id = normalizeOptionalString(newUserData.aadhaar_id);
			payload.abha_id = normalizeOptionalString(newUserData.abha_id);
			payload.primary_diagnosis = normalizeOptionalString(newUserData.primary_diagnosis);
			payload.diagnosis_doctor = normalizeOptionalString(newUserData.diagnosis_doctor);
			payload.diagnosis_date = normalizeOptionalString(newUserData.diagnosis_date);
			payload.diagnosis_time = normalizeOptionalString(newUserData.diagnosis_time);
		}

		if (newUserRole === 'STUDENT') {
			payload.year = parseOptionalInteger(newUserData.year);
			payload.semester = parseOptionalInteger(newUserData.semester);
			payload.program = normalizeOptionalString(newUserData.program);
			payload.degree = normalizeOptionalString(newUserData.degree);
			payload.gpa = parseOptionalFloat(newUserData.gpa);
			payload.academic_standing = normalizeOptionalString(newUserData.academic_standing);
			payload.academic_advisor = normalizeOptionalString(newUserData.academic_advisor);
		}

		if (newUserRole === 'FACULTY') {
			payload.department = normalizeOptionalString(newUserData.department);
			payload.specialty = normalizeOptionalString(newUserData.specialty);
			payload.phone = normalizeOptionalString(newUserData.phone);
			payload.availability = normalizeOptionalString(newUserData.availability);
		}

		if (newUserRole === 'NURSE') {
			payload.department = normalizeOptionalString(newUserData.department);
			payload.phone = normalizeOptionalString(newUserData.phone);
			payload.hospital = normalizeOptionalString(newUserData.hospital);
			payload.ward = normalizeOptionalString(newUserData.ward);
			payload.shift = normalizeOptionalString(newUserData.shift);
		}
		
		creatingUser = true;
		try {
			await adminApi.createUser(payload);
			toastStore.addToast('User created successfully', 'success');
			createUserModal = false;
			resetCreateUserForm('NURSE');
			await loadUsers();
		} catch (e: any) {
			toastStore.addToast(e.response?.data?.detail || 'Failed to create user', 'error');
		} finally {
			creatingUser = false;
		}
	}

	const totalPages = $derived(Math.ceil(total / 20));

	const roleTabs = [
		{ id: '', label: 'All' },
		{ id: 'PATIENT', label: 'Patients' },
		{ id: 'STUDENT', label: 'Students' },
		{ id: 'FACULTY', label: 'Faculty' },
		{ id: 'NURSE', label: 'Nurses' },
		{ id: 'RECEPTION', label: 'Reception' },
		{ id: 'ADMIN', label: 'Admins' },
	];

	function roleColor(role: string) {
		const map: Record<string, string> = {
			PATIENT: '#10b981',
			STUDENT: '#f59e0b',
			FACULTY: '#8b5cf6',
			ADMIN: '#ef4444',
			RECEPTION: '#3b82f6',
			NURSE: '#14b8a6',
		};
		return map[role] || '#6b7280';
	}
</script>

	<div class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<div>
				<h2 class="text-xs font-bold uppercase tracking-[0.16em] text-slate-600">User Management</h2>
				<p class="mt-0.5 text-[11px] text-slate-500">{total} total users</p>
			</div>
			<button
				onclick={openCreateUserModal}
				class="px-3 py-1.5 rounded-xl text-xs font-semibold text-white cursor-pointer shadow-md"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
			>
				Add New
			</button>
		</div>

		<div class="relative">
			<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
			<input
				type="text"
				placeholder="Search by username or email..."
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Enter' && handleSearch()}
				class="w-full pl-9 pr-3 py-2 rounded-2xl text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
				style="background: white; box-shadow: inset 0 1px 3px rgba(0,0,0,0.08);"
			/>
		</div>

		<div class="flex gap-1.5 overflow-x-auto pb-1">
			{#each roleTabs as tab}
				<button
					class="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-medium whitespace-nowrap cursor-pointer transition-all"
					style={roleFilter === tab.id
						? `background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);`
						: `background: white; color: #4b5563; border: 1px solid #e5e7eb;`}
					onclick={() => setRoleFilter(tab.id)}
				>
					{tab.label}
				</button>
			{/each}
		</div>

		<div class="flex gap-1.5 overflow-x-auto pb-1">
			{#each [{ id: '', label: 'All Status' }, { id: 'active', label: 'Active' }, { id: 'blocked', label: 'Blocked' }] as sf}
				<button
					class="shrink-0 px-2.5 py-1 rounded-full text-[11px] cursor-pointer"
					style={statusFilter === sf.id
						? 'background: #1e3a5f; color: white;'
						: 'background: #f3f4f6; color: #6b7280;'}
					onclick={() => setStatusFilter(sf.id)}
				>
					{sf.label}
				</button>
			{/each}
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<div class="animate-spin w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full"></div>
			</div>
		{:else if error}
			<div class="p-4 rounded-xl bg-white shadow-md">
				<p class="text-red-500 text-center py-4">{error}</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each users as u}
					<div class="p-3 rounded-xl bg-white shadow-md flex items-center gap-2.5">
						<div class="w-11 h-11 flex items-center justify-center rounded-full shrink-0" style="background: linear-gradient(to bottom, {roleColor(u.role)}, {roleColor(u.role)}dd);">
							<User class="w-5 h-5 text-white" />
						</div>

						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-1.5">
								<p class="text-sm font-bold text-gray-900 truncate">{u.name}</p>
								{#if !u.is_active}
									<span class="text-[9px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-medium">Blocked</span>
								{/if}
							</div>
							<p class="text-xs text-red-600 font-semibold truncate uppercase">{u.role} • {u.username}</p>
						</div>

						<div class="flex flex-col gap-0.5 shrink-0">
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-100"
								title={u.is_active ? 'Block' : 'Unblock'}
								onclick={() => toggleBlock(u)}
							>
								{#if u.is_active}
									<ShieldOff class="w-3.5 h-3.5 text-orange-500" />
								{:else}
									<Shield class="w-3.5 h-3.5 text-green-500" />
								{/if}
							</button>
							<button
								class="p-1.5 rounded-lg cursor-pointer hover:bg-red-50"
								title="Delete"
								onclick={() => deleteUser(u)}
							>
								<Trash2 class="w-3.5 h-3.5 text-red-400" />
							</button>
						</div>
					</div>
				{/each}

				{#if users.length === 0}
					<div class="text-center py-12 text-gray-400 text-sm">No users found</div>
				{/if}
			</div>

			{#if totalPages > 1}
				<div class="flex items-center justify-center gap-4 py-2">
					<button
						class="p-2 rounded-lg cursor-pointer disabled:opacity-30"
						disabled={currentPage <= 1}
						onclick={() => { currentPage--; loadUsers(); }}
					>
						<ChevronRight class="w-5 h-5 text-blue-600 rotate-180" />
					</button>
					<span class="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
					<button
						class="p-2 rounded-lg cursor-pointer disabled:opacity-30"
						disabled={currentPage >= totalPages}
						onclick={() => { currentPage++; loadUsers(); }}
					>
						<ChevronRight class="w-5 h-5 text-blue-600" />
					</button>
				</div>
			{/if}
		{/if}
	</div>

<!-- Create User Modal -->
{#if createUserModal}
	<AquaModal title="Create New User" onclose={() => { createUserModal = false; resetCreateUserForm(newUserRole); }}>
		<!-- svelte-ignore a11y_label_has_associated_control -->
		<div class="p-4 space-y-4">
			<div>
				<label for="userRole" class="block text-xs font-semibold text-gray-700 mb-1">Role *</label>
				<select
					id="userRole"
					bind:value={newUserRole}
					onchange={(event) => handleCreateRoleChange((event.currentTarget as HTMLSelectElement).value as CreateUserRole)}
					class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
				>
					<option value="PATIENT">Patient</option>
					<option value="NURSE">Nurse</option>
					<option value="RECEPTION">Reception</option>
					<option value="STUDENT">Student</option>
					<option value="FACULTY">Faculty</option>
					<option value="ADMIN">Admin</option>
				</select>
			</div>

			<div class="grid gap-3 md:grid-cols-2">
				<div>
					<label class="block text-xs font-semibold text-gray-700 mb-1">Full Name *</label>
					<input type="text" bind:value={newUserData.name} placeholder="Enter full name" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
				</div>
				<div>
					<label class="block text-xs font-semibold text-gray-700 mb-1">Username *</label>
					<input type="text" bind:value={newUserData.username} placeholder="Enter username" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
				</div>
				<div>
					<label class="block text-xs font-semibold text-gray-700 mb-1">Email *</label>
					<input type="email" bind:value={newUserData.email} placeholder="Enter email" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
				</div>
				<div>
					<label class="block text-xs font-semibold text-gray-700 mb-1">Password *</label>
					<input type="password" bind:value={newUserData.password} placeholder="Enter password" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
				</div>
				<div class="md:col-span-2">
					<label class="block text-xs font-semibold text-gray-700 mb-1">Photo URL</label>
					<input type="text" bind:value={newUserData.photo} placeholder="Optional photo path or URL" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
				</div>
			</div>

			{#if newUserRole === 'PATIENT'}
				<div class="space-y-3 rounded-xl border border-blue-100 bg-blue-50/40 p-3">
					<p class="text-xs font-bold uppercase tracking-wide text-blue-700">Patient Profile</p>
					<div class="grid gap-3 md:grid-cols-2">
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Date of Birth *</label>
							<input type="date" bind:value={newUserData.date_of_birth} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Gender</label>
							<select bind:value={newUserData.gender} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
								{#each genderOptions as option}
									<option value={option}>{option}</option>
								{/each}
							</select>
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Blood Group</label>
							<select bind:value={newUserData.blood_group} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
								<option value="">Select blood group</option>
								{#each bloodGroupOptions as option}
									<option value={option}>{option}</option>
								{/each}
							</select>
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Phone</label>
							<input type="tel" bind:value={newUserData.phone} placeholder="Enter phone number" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Patient Category</label>
							{#if patientCategories.length > 0}
								<select bind:value={newUserData.category} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
									<option value="">Select category</option>
									{#each patientCategories as category}
										<option value={category.name}>{category.name}</option>
									{/each}
								</select>
							{:else}
								<input type="text" bind:value={newUserData.category} placeholder="Enter category" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
							{/if}
						</div>
						<div class="md:col-span-2">
							<label class="block text-xs font-semibold text-gray-700 mb-1">Address</label>
							<input type="text" bind:value={newUserData.address} placeholder="Enter address" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Aadhaar ID</label>
							<input type="text" bind:value={newUserData.aadhaar_id} placeholder="Enter Aadhaar ID" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">ABHA ID</label>
							<input type="text" bind:value={newUserData.abha_id} placeholder="Enter ABHA ID" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Primary Diagnosis</label>
							<input type="text" bind:value={newUserData.primary_diagnosis} placeholder="Enter primary diagnosis" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Diagnosis Doctor</label>
							<input type="text" bind:value={newUserData.diagnosis_doctor} placeholder="Enter diagnosing doctor" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Diagnosis Date</label>
							<input type="date" bind:value={newUserData.diagnosis_date} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Diagnosis Time</label>
							<input type="time" bind:value={newUserData.diagnosis_time} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
					</div>
				</div>
			{/if}

			{#if newUserRole === 'STUDENT'}
				<div class="space-y-3 rounded-xl border border-amber-100 bg-amber-50/35 p-3">
					<p class="text-xs font-bold uppercase tracking-wide text-amber-700">Student Profile</p>
					<div class="grid gap-3 md:grid-cols-2">
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Year *</label>
							<input type="number" min="1" bind:value={newUserData.year} placeholder="Enter year" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Semester *</label>
							<input type="number" min="1" bind:value={newUserData.semester} placeholder="Enter semester" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Program *</label>
							{#if programmes.length > 0}
								<select bind:value={newUserData.program} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
									<option value="">Select program</option>
									{#each programmes as programme}
										<option value={programme.name}>{programme.name}</option>
									{/each}
								</select>
							{:else}
								<input type="text" bind:value={newUserData.program} placeholder="Enter program" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
							{/if}
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Degree</label>
							<input type="text" bind:value={newUserData.degree} placeholder="Enter degree" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">GPA</label>
							<input type="number" min="0" max="10" step="0.01" bind:value={newUserData.gpa} placeholder="Enter GPA" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Academic Standing</label>
							<select bind:value={newUserData.academic_standing} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
								{#each academicStandingOptions as option}
									<option value={option}>{option}</option>
								{/each}
							</select>
						</div>
						<div class="md:col-span-2">
							<label class="block text-xs font-semibold text-gray-700 mb-1">Academic Advisor</label>
							<input type="text" bind:value={newUserData.academic_advisor} placeholder="Enter academic advisor" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
					</div>
				</div>
			{/if}

			{#if newUserRole === 'FACULTY'}
				<div class="space-y-3 rounded-xl border border-violet-100 bg-violet-50/35 p-3">
					<p class="text-xs font-bold uppercase tracking-wide text-violet-700">Faculty Profile</p>
					<div class="grid gap-3 md:grid-cols-2">
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Department *</label>
							{#if departments.length > 0}
								<select bind:value={newUserData.department} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
									<option value="">Select department</option>
									{#each departments as department}
										<option value={department.name}>{department.name}</option>
									{/each}
								</select>
							{:else}
								<input type="text" bind:value={newUserData.department} placeholder="Enter department" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
							{/if}
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Specialty</label>
							<input type="text" bind:value={newUserData.specialty} placeholder="Enter specialty" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Phone</label>
							<input type="tel" bind:value={newUserData.phone} placeholder="Enter phone number" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Availability</label>
							<input type="text" bind:value={newUserData.availability} placeholder="Enter availability" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
					</div>
				</div>
			{/if}

			{#if newUserRole === 'NURSE'}
				<div class="space-y-3 rounded-xl border border-teal-100 bg-teal-50/35 p-3">
					<p class="text-xs font-bold uppercase tracking-wide text-teal-700">Nurse Profile</p>
					<div class="grid gap-3 md:grid-cols-2">
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Phone</label>
							<input type="tel" bind:value={newUserData.phone} placeholder="Enter phone number" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Department</label>
							{#if departments.length > 0}
								<select bind:value={newUserData.department} class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
									<option value="">Select department</option>
									{#each departments as department}
										<option value={department.name}>{department.name}</option>
									{/each}
								</select>
							{:else}
								<input type="text" bind:value={newUserData.department} placeholder="Enter department" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
							{/if}
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Hospital</label>
							<input type="text" bind:value={newUserData.hospital} placeholder="Enter hospital" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1">Ward</label>
							<input type="text" bind:value={newUserData.ward} placeholder="Enter ward" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
						<div class="md:col-span-2">
							<label class="block text-xs font-semibold text-gray-700 mb-1">Shift</label>
							<input type="text" bind:value={newUserData.shift} placeholder="Enter shift" class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
						</div>
					</div>
				</div>
			{/if}

			<!-- Action Buttons -->
			<div class="flex gap-2 pt-2">
				<AquaButton variant="secondary" fullWidth onclick={() => { createUserModal = false; resetCreateUserForm(newUserRole); }}>
					Cancel
				</AquaButton>
				<AquaButton
					variant="primary"
					fullWidth
					disabled={creatingUser}
					onclick={createUser}
				>
					{creatingUser ? 'Creating...' : 'Create User'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}

<!-- Confirm Modal -->
{#if confirmModal}
	<AquaModal title="Confirm Action" onclose={() => confirmModal = false}>
		<div class="p-4 space-y-4">
			<p class="text-sm text-gray-700">{confirmMessage}</p>
			<div class="flex gap-2">
				<AquaButton variant="secondary" fullWidth onclick={() => confirmModal = false}>
					Cancel
				</AquaButton>
				<AquaButton
					variant="danger"
					fullWidth
					disabled={actionLoading}
					onclick={() => confirmAction && confirmAction()}
				>
					{actionLoading ? 'Processing...' : 'Confirm'}
				</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
