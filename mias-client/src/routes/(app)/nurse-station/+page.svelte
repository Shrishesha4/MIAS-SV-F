<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { clinicsApi, type ClinicInfo } from '$lib/api/clinics';
	import { nurseApi, type WardPatient, type NurseOrder, type NewlyRegisteredPatient } from '$lib/api/nurse';
	import { staffApi, type ActiveClinicStudent, type PendingPatient } from '$lib/api/staff';
	import { toastStore } from '$lib/stores/toast';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import Avatar from '$lib/components/ui/Avatar.svelte';
	import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
	import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { ChevronRight, ChevronDown, Stethoscope, ClipboardList, FileText, Loader2, UserCheck, UserPlus, AlertCircle, Zap, RefreshCw } from 'lucide-svelte';

	let loading = $state(true);
	let nurseInfo = $state<{ name: string; hospital: string; ward: string; shift: string } | null>(null);
	let patients = $state<WardPatient[]>([]);
	let newlyRegisteredPatients = $state<NewlyRegisteredPatient[]>([]);
	let pendingPatients = $state<PendingPatient[]>([]);
	let clinics = $state<ClinicInfo[]>([]);
	let expandedPatientId = $state<string | null>(null);
	let currentPatientOrders = $state<NurseOrder[]>([]);
	let sbarForm = $state({ situation: '', background: '', assessment: '', recommendation: '' });
	let savingSBAR = $state(false);
	let assignTarget = $state<PendingPatient | null>(null);
	let showAssignModal = $state(false);
	let assignClinicId = $state('');
	let assignStudents = $state<ActiveClinicStudent[]>([]);
	let assignStudentId = $state('');
	let loadingAssignStudents = $state(false);
	let isAssigning = $state(false);
	let busyPatientId = $state<string | null>(null);

	const intakePatients = $derived(
		pendingPatients.filter((patient) => patient.workflow_status === 'unchecked' || patient.workflow_status === 'unassigned')
	);

	function formatAge(age: number | null) {
		return age === null ? 'Age N/A' : `${age} yrs`;
	}

	function formatGender(gender: string | null) {
		if (!gender) return 'Unknown';
		return gender.charAt(0).toUpperCase() + gender.slice(1).toLowerCase();
	}

	function formatRegisteredAt(value: string) {
		return new Date(value).toLocaleString('en-IN', {
			day: '2-digit',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function loadAssignStudentsForClinic(clinicId: string) {
		if (!clinicId) {
			assignStudents = [];
			assignStudentId = '';
			return;
		}
		loadingAssignStudents = true;
		try {
			assignStudents = await staffApi.getActiveStudents(clinicId);
			assignStudentId = assignStudents[0]?.id || '';
		} catch {
			assignStudents = [];
			assignStudentId = '';
			toastStore.addToast('Could not load active students for this clinic', 'error');
		} finally {
			loadingAssignStudents = false;
		}
	}

	async function openAssignModal(patient: PendingPatient) {
		assignTarget = patient;
		assignClinicId = patient.clinic_id || clinics[0]?.id || '';
		assignStudents = [];
		assignStudentId = '';
		showAssignModal = true;
		if (!assignClinicId) {
			toastStore.addToast('No clinic is available for assignment', 'error');
			return;
		}
		await loadAssignStudentsForClinic(assignClinicId);
	}

	async function handleAssignPatient() {
		if (!assignTarget || !assignClinicId || !assignStudentId) return;
		isAssigning = true;
		try {
			const result = await staffApi.assignToStudent({
				patient_id: assignTarget.id,
				student_id: assignStudentId,
				clinic_id: assignClinicId
			});
			toastStore.addToast(`${assignTarget.name} assigned to ${result.student_name}`, 'success');
			showAssignModal = false;
			assignTarget = null;
			await loadWardData();
		} catch (error: any) {
			toastStore.addToast(error.response?.data?.detail || 'Assignment failed', 'error');
		} finally {
			isAssigning = false;
		}
	}

	async function handleAssignClinicOnly() {
		if (!assignTarget || !assignClinicId) return;
		isAssigning = true;
		try {
			const result = await clinicsApi.checkInPatient(assignClinicId, { patient_id: assignTarget.id });
			toastStore.addToast(result.message || `${assignTarget.name} checked in to clinic`, 'success');
			showAssignModal = false;
			assignTarget = null;
			await loadWardData();
		} catch (error: any) {
			toastStore.addToast(error.response?.data?.detail || 'Clinic check-in failed', 'error');
		} finally {
			isAssigning = false;
		}
	}

	async function handleQueueCheckIn(patient: PendingPatient, autoAssignAfterCheckIn = false) {
		if (!patient.clinic_id) {
			toastStore.addToast('Patient has no allocated clinic. Pick one manually first.', 'warning');
			await openAssignModal(patient);
			return;
		}
		busyPatientId = patient.id;
		try {
			const result = await clinicsApi.checkInPatient(patient.clinic_id, { patient_id: patient.id });
			toastStore.addToast(result.message || `${patient.name} checked in successfully`, 'success');
			if (autoAssignAfterCheckIn) {
				const assignResult = await staffApi.autoAssignPatient(patient.id, patient.clinic_id);
				if (assignResult.clinic_only) {
					toastStore.addToast(assignResult.message || `${patient.name} is waiting in clinic for assignment`, 'warning');
				} else {
					toastStore.addToast(`${patient.name} assigned to ${assignResult.student_name}`, 'success');
				}
			}
			await loadWardData();
		} catch (error: any) {
			toastStore.addToast(error.response?.data?.detail || 'Failed to check in patient', 'error');
		} finally {
			busyPatientId = null;
		}
	}

	async function handleAutoAssign(patient: PendingPatient) {
		if (!patient.clinic_id) {
			toastStore.addToast('Patient has no allocated clinic. Pick a clinic manually first.', 'warning');
			await openAssignModal(patient);
			return;
		}
		busyPatientId = patient.id;
		try {
			const result = await staffApi.autoAssignPatient(patient.id, patient.clinic_id);
			if (result.clinic_only) {
				toastStore.addToast(result.message || `${patient.name} is waiting in clinic for assignment`, 'warning');
			} else {
				toastStore.addToast(`${patient.name} assigned to ${result.student_name}`, 'success');
			}
			await loadWardData();
		} catch (error: any) {
			toastStore.addToast(error.response?.data?.detail || 'Auto assignment failed', 'error');
		} finally {
			busyPatientId = null;
		}
	}

	async function togglePatient(patient: WardPatient) {
		if (expandedPatientId === patient.id) {
			expandedPatientId = null;
			currentPatientOrders = [];
			sbarForm = { situation: '', background: '', assessment: '', recommendation: '' };
		} else {
			expandedPatientId = patient.id;
			await loadPatientDetails(patient.id);
		}
	}

	async function loadPatientDetails(patientId: string) {
		try {
			const orders = await nurseApi.getPatientOrders(patientId);
			currentPatientOrders = orders;
		} catch (error: any) {
			console.error('Error loading patient details:', error);
			toastStore.addToast('Failed to load patient details', 'error');
		}
	}

	async function handleOrderToggle(orderId: string) {
		try {
			await nurseApi.completeOrder(orderId);
			// Reload orders
			if (expandedPatientId) {
				await loadPatientDetails(expandedPatientId);
			}
			toastStore.addToast('Order completed', 'success');
		} catch (error: any) {
			console.error('Error completing order:', error);
			toastStore.addToast('Failed to complete order', 'error');
		}
	}

	async function saveSBAR() {
		if (!expandedPatientId) return;
		
		const patient = patients.find(p => p.id === expandedPatientId);
		if (!patient) return;

		if (!sbarForm.situation && !sbarForm.background && !sbarForm.assessment && !sbarForm.recommendation) {
			toastStore.addToast('Please fill at least one SBAR field', 'warning');
			return;
		}

		try {
			savingSBAR = true;
			await nurseApi.createSBARNote(patient.id, patient.admission_id, sbarForm);
			toastStore.addToast('SBAR note saved successfully', 'success');
			sbarForm = { situation: '', background: '', assessment: '', recommendation: '' };
		} catch (error: any) {
			console.error('Error saving SBAR:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to save SBAR note', 'error');
		} finally {
			savingSBAR = false;
		}
	}

	async function loadWardData() {
		try {
			loading = true;
			const [data, queue, clinicList] = await Promise.all([
				nurseApi.getWardPatients(),
				staffApi.getPendingPatients(),
				clinicsApi.listClinics()
			]);
			nurseInfo = data.nurse;
			patients = data.patients;
			newlyRegisteredPatients = data.newly_registered;
			pendingPatients = queue;
			clinics = clinicList;
		} catch (error: any) {
			console.error('Error loading ward data:', error);
			toastStore.addToast(error.response?.data?.detail || 'Failed to load ward data', 'error');
		} finally {
			loading = false;
		}
	}

	onMount(async () => {
		const auth = get(authStore);
		if (auth.role !== 'NURSE') {
			goto('/dashboard');
			return;
		}
		await loadWardData();
	});
</script>

<div class="p-4 max-w-screen-2xl mx-auto space-y-4">
	{#if loading}
		<div class="text-center py-12">
			<div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
		</div>
	{:else if nurseInfo}
		<!-- Header Card -->
		<AquaCard padding={true}>
			{#snippet header()}
				<div class="flex items-center gap-3">
					<div
						class="flex items-center justify-center w-14 h-14 rounded-2xl"
						style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 2px 8px rgba(0,0,0,0.2);"
					>
						<Stethoscope class="w-7 h-7 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<h1 class="text-xl font-bold text-gray-900 truncate">Nurse Station</h1>
						<p class="text-sm text-gray-600 truncate">{nurseInfo?.ward} • {nurseInfo?.shift || 'All Day'}</p>
					</div>
				</div>
			{/snippet}

			<div class="flex items-center gap-3 mt-4">
				<div
					class="flex-1 px-4 py-3 rounded-xl text-center"
					style="background: linear-gradient(to bottom, #dbeafe, #bfdbfe); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
				>
					<div class="text-2xl font-bold text-blue-900">{patients.length}</div>
					<div class="text-xs font-medium text-blue-700 uppercase">Ward Patients</div>
				</div>
				<div
					class="flex-1 px-4 py-3 rounded-xl text-center"
					style="background: linear-gradient(to bottom, #dcfce7, #bbf7d0); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
				>
					<div class="text-2xl font-bold text-green-900">{newlyRegisteredPatients.length}</div>
					<div class="text-xs font-medium text-green-700 uppercase">New Registrations</div>
				</div>
				<div
					class="flex-1 px-4 py-3 rounded-xl text-center"
					style="background: linear-gradient(to bottom, #fef3c7, #fde047); box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
				>
					<div class="text-2xl font-bold text-yellow-900">{patients.reduce((sum, p) => sum + p.pending_tasks, 0)}</div>
					<div class="text-xs font-medium text-yellow-700 uppercase">Pending</div>
				</div>
			</div>
		</AquaCard>

		<AquaCard padding={false}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<UserCheck class="w-5 h-5 text-blue-600" />
					<h2 class="text-base font-bold text-gray-800">Intake Action Queue</h2>
				</div>
			{/snippet}

			<div class="space-y-3 px-4 py-4">
				<div class="flex items-center justify-between rounded-xl px-4 py-3" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid #bfdbfe;">
					<div>
						<p class="text-sm font-semibold text-gray-900">Unchecked or unassigned patients</p>
						<p class="text-xs text-gray-600">Nurses can check patients into clinic, auto-assign them, or route them manually.</p>
					</div>
					<button
						class="rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
						style="background: rgba(255,255,255,0.78); border: 1px solid rgba(37,99,235,0.16); color: #1d4ed8;"
						onclick={loadWardData}
					>
						<RefreshCw class="mr-1 inline h-3.5 w-3.5" /> Refresh
					</button>
				</div>

				{#if intakePatients.length === 0}
					<div class="rounded-xl border border-dashed border-gray-200 px-4 py-8 text-center text-gray-500">
						<p class="text-sm">No unchecked or unassigned patients need help right now.</p>
					</div>
				{:else}
					{#each intakePatients as patient (patient.id)}
						<div class="rounded-2xl px-4 py-3" style="background: white; border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
							<div class="flex items-start gap-3">
								<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="md" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2 flex-wrap">
										<h3 class="text-sm font-semibold text-gray-900">{patient.name}</h3>
										<StatusBadge variant={patient.workflow_status === 'unchecked' ? 'warning' : 'info'} size="sm">
											{patient.workflow_status === 'unchecked' ? 'Needs check-in' : 'Waiting for student'}
										</StatusBadge>
									</div>
									<p class="text-xs text-gray-600">{patient.patient_id} • {formatAge(patient.age)} • {formatGender(patient.gender)}</p>
									<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
									<p class="mt-1 text-xs font-medium" style={`color: ${patient.clinic_name ? '#2563eb' : '#d97706'};`}>
										{patient.clinic_name || 'No preferred clinic allocated'}
									</p>
									<p class="text-xs text-gray-500">Registered {formatRegisteredAt(patient.registered_at)}</p>
								</div>
							</div>

							<div class="mt-3 flex flex-wrap gap-2">
								{#if patient.workflow_status === 'unchecked'}
									<button
										class="rounded-xl px-3 py-2 text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
										style="background: linear-gradient(to bottom, #10b981, #059669); box-shadow: 0 1px 3px rgba(5,150,105,0.3);"
										onclick={() => handleQueueCheckIn(patient, true)}
										disabled={busyPatientId === patient.id}
									>
										{#if busyPatientId === patient.id}
											<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Working
										{:else}
											<UserCheck class="mr-1 inline h-3.5 w-3.5" /> Check in & route
										{/if}
									</button>
								{:else}
									<button
										class="rounded-xl px-3 py-2 text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
										style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); box-shadow: 0 1px 3px rgba(29,78,216,0.3);"
										onclick={() => handleAutoAssign(patient)}
										disabled={busyPatientId === patient.id}
									>
										{#if busyPatientId === patient.id}
											<Loader2 class="mr-1 inline h-3.5 w-3.5 animate-spin" /> Working
										{:else}
											<Zap class="mr-1 inline h-3.5 w-3.5" /> Auto assign
										{/if}
									</button>
								{/if}

								<button
									class="rounded-xl px-3 py-2 text-xs font-semibold cursor-pointer"
									style="background: #f8fafc; border: 1px solid rgba(0,0,0,0.08); color: #475569;"
									onclick={() => openAssignModal(patient)}
								>
									<UserPlus class="mr-1 inline h-3.5 w-3.5" /> Manual clinic / student
								</button>
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</AquaCard>

		<AquaCard padding={false}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<FileText class="w-5 h-5 text-green-600" />
					<h2 class="text-base font-bold text-gray-800">Newly Registered Patients</h2>
				</div>
			{/snippet}

			<div class="divide-y divide-gray-200">
				{#if newlyRegisteredPatients.length === 0}
					<div class="px-4 py-8 text-center text-gray-500">
						<p class="text-sm">No newly registered patients found</p>
					</div>
				{:else}
					{#each newlyRegisteredPatients as patient (patient.id)}
						<div class="px-4 py-3 hover:bg-gray-50 transition-colors">
							<div class="flex items-start gap-3">
								<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="md" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 flex-wrap">
										<h3 class="text-sm font-semibold text-gray-900">{patient.name}</h3>
										<StatusBadge variant={patient.has_admission ? 'success' : patient.has_appointment ? 'warning' : 'info'} size="sm">
											{patient.has_admission ? 'Admitted' : patient.has_appointment ? 'Assigned' : 'Unassigned'}
										</StatusBadge>
									</div>
									<p class="text-xs text-gray-600">
										{formatAge(patient.age)} • {formatGender(patient.gender)}
									</p>
									<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
									<p class="text-xs text-gray-500 mt-1">
										{patient.patient_id} • {patient.phone || 'No phone'} • Registered {formatRegisteredAt(patient.registered_at)}
									</p>
								</div>
							</div>
						</div>
					{/each}
				{/if}
			</div>
		</AquaCard>

		<!-- Ward Patients Section -->
		<AquaCard padding={false}>
			{#snippet header()}
				<div class="flex items-center gap-2">
					<FileText class="w-5 h-5 text-blue-600" />
					<h2 class="text-base font-bold text-gray-800">All Ward Patients — SBAR Notes</h2>
				</div>
			{/snippet}

			<div class="divide-y divide-gray-200">
				{#if patients.length === 0}
					<div class="px-4 py-8 text-center text-gray-500">
						<p class="text-sm">No active ward patients found</p>
					</div>
				{:else}
					{#each patients as patient (patient.id)}
						<div>
							<!-- Patient Header (Collapsible) -->
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="px-4 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
								onclick={() => togglePatient(patient)}
							>
								<div class="flex items-center gap-3">
									<PatientInsuranceAvatar name={patient.name} src={patient.photo} size="md" insurancePolicies={patient.insurance_policies} patientCategory={patient.category} patientCategoryColorPrimary={patient.category_color_primary} patientCategoryColorSecondary={patient.category_color_secondary} />
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2">
											<h3 class="text-sm font-semibold text-gray-900">{patient.name}</h3>
											<StatusBadge variant="normal" size="sm">
												{patient.ward}
											</StatusBadge>
											<StatusBadge
												variant={patient.bed_number.startsWith('ICU') ? 'critical' : 'info'}
												size="sm"
											>
												{patient.bed_number}
											</StatusBadge>
										</div>
										<p class="text-xs text-gray-600">
											{formatAge(patient.age)} • {formatGender(patient.gender)} • {patient.pending_tasks} pending
										</p>
										<InsuranceTypeBadges insurancePolicies={patient.insurance_policies} compact maxVisible={2} />
									</div>
									<div class="flex items-center gap-2">
										{#if patient.pending_tasks > 0}
											<div
												class="px-3 py-1 rounded-lg text-xs font-bold"
												style="background: linear-gradient(to bottom, #fef3c7, #fde047); color: #78350f; box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
											>
												{patient.pending_tasks} todo
											</div>
										{/if}
										{#if expandedPatientId === patient.id}
											<ChevronDown class="w-5 h-5 text-gray-400" />
										{:else}
											<ChevronRight class="w-5 h-5 text-gray-400" />
										{/if}
									</div>
								</div>
							</div>

							<!-- Expanded View: Orders + SBAR -->
							{#if expandedPatientId === patient.id}
								<div class="px-4 pb-4 bg-gray-50">
									<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
										<!-- Left: Pending Orders -->
										<div
											class="rounded-xl p-4"
											style="background: white; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
										>
											<div class="flex items-center gap-2 mb-3">
												<ClipboardList class="w-5 h-5 text-orange-600" />
												<h3 class="font-bold text-gray-900">Pending Orders</h3>
												<span
													class="ml-auto px-2 py-1 rounded-md text-xs font-bold"
													style="background: linear-gradient(to bottom, #fef3c7, #fde047); color: #78350f;"
												>
													{currentPatientOrders.filter(o => !o.is_completed).length} pending
												</span>
											</div>

											<div class="space-y-2">
												{#each currentPatientOrders as order (order.id)}
													<div
														class="flex items-start gap-3 p-3 rounded-lg"
														style={order.is_completed ? 'background: #f9fafb; opacity: 0.6;' : 'background: white; border: 1px solid #e5e7eb;'}
													>
														<input
															type="checkbox"
															checked={order.is_completed}
															onchange={() => handleOrderToggle(order.id)}
															class="mt-0.5 w-4 h-4 rounded border-gray-300"
														/>
														<div class="flex-1 min-w-0">
															<div class="flex items-center gap-2 mb-1">
																<StatusBadge
																	variant={order.order_type === 'DRUG' ? 'info' : order.order_type === 'INVESTIGATION' ? 'warning' : 'normal'}
																	size="sm"
																>
																	{order.order_type}
																</StatusBadge>
																{#if order.scheduled_time}
																	<span class="text-xs text-gray-500">⏰ {order.scheduled_time}</span>
																{/if}
															</div>
															<p class="text-sm font-semibold text-gray-900" style={order.is_completed ? 'text-decoration: line-through;' : ''}>
																{order.title}
															</p>
															{#if order.description}
																<p class="text-xs text-gray-600">{order.description}</p>
															{/if}
														</div>
													</div>
												{/each}
												{#if currentPatientOrders.length === 0}
													<p class="text-sm text-gray-500 text-center py-4">No orders for this patient</p>
												{/if}
											</div>
										</div>

										<!-- Right: SBAR Notes -->
										<div
											class="rounded-xl p-4"
											style="background: white; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 3px rgba(0,0,0,0.1);"
										>
											<div class="flex items-center gap-2 mb-3">
												<FileText class="w-5 h-5 text-blue-600" />
												<h3 class="font-bold text-gray-900">SBAR Notes</h3>
											</div>

											<!-- svelte-ignore a11y_label_has_associated_control -->
											<div class="space-y-3">
												<!-- Situation -->
												<div>
													<div class="flex items-center gap-2 mb-1">
														<div
															class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white"
															style="background: linear-gradient(to bottom, #ef4444, #dc2626);"
														>
															S
														</div>
														<label class="text-sm font-semibold text-gray-900">Situation</label>
													</div>
													<textarea
														bind:value={sbarForm.situation}
														placeholder="What is happening with the patient right now?"
														class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
														rows="3"
													></textarea>
												</div>

												<!-- Background -->
												<div>
													<div class="flex items-center gap-2 mb-1">
														<div
															class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white"
															style="background: linear-gradient(to bottom, #f97316, #ea580c);"
														>
															B
														</div>
														<label class="text-sm font-semibold text-gray-900">Background</label>
													</div>
													<textarea
														bind:value={sbarForm.background}
														placeholder="What is the clinical background / context?"
														class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
														rows="3"
													></textarea>
												</div>

												<!-- Assessment -->
												<div>
													<div class="flex items-center gap-2 mb-1">
														<div
															class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white"
															style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
														>
															A
														</div>
														<label class="text-sm font-semibold text-gray-900">Assessment</label>
													</div>
													<textarea
														bind:value={sbarForm.assessment}
														placeholder="What do you think the problem is?"
														class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
														rows="3"
													></textarea>
												</div>

												<!-- Recommendation -->
												<div>
													<div class="flex items-center gap-2 mb-1">
														<div
															class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white"
															style="background: linear-gradient(to bottom, #10b981, #059669);"
														>
															R
														</div>
														<label class="text-sm font-semibold text-gray-900">Recommendation</label>
													</div>
													<textarea
														bind:value={sbarForm.recommendation}
														placeholder="What action do you recommend?"
														class="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
														rows="3"
													></textarea>
												</div>

												<!-- Footer -->
												<div class="pt-2 border-t border-gray-200">
													<div class="flex items-center justify-between mb-3">
														<p class="text-xs text-gray-600">
															Nurse: {nurseInfo?.name} • {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
														</p>
													</div>
													<button
														onclick={saveSBAR}
														disabled={savingSBAR}
														class="w-full px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all"
														style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
													>
														{#if savingSBAR}
															<span class="inline-block animate-spin mr-2">⏳</span>
														{/if}
														💾 Save SBAR
													</button>
												</div>
											</div>
										</div>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</AquaCard>
	{/if}
</div>

{#if showAssignModal && assignTarget}
	<AquaModal title="Route Patient from Nurse Station" onclose={() => { showAssignModal = false; assignTarget = null; }}>
		<div class="space-y-3 px-1">
			<div>
				<p class="text-xs font-semibold text-gray-800">{assignTarget.name}</p>
				<p class="text-[10px] text-gray-500">{assignTarget.patient_id}</p>
			</div>

			<div>
				<p class="text-[10px] font-medium text-gray-600 mb-1">Clinic</p>
				<select
					bind:value={assignClinicId}
					onchange={(event) => loadAssignStudentsForClinic((event.currentTarget as HTMLSelectElement).value)}
					class="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-white"
					style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
				>
					{#each clinics as clinic}
						<option value={clinic.id}>{clinic.name}</option>
					{/each}
				</select>
			</div>

			{#if loadingAssignStudents}
				<div class="flex items-center justify-center py-4">
					<div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
				</div>
			{:else if assignStudents.length === 0}
				<div class="space-y-3">
					<div class="flex items-center rounded-lg px-3 py-2" style="background: #fffbeb; border: 1px solid #fde68a;">
						<AlertCircle class="mr-2 h-3.5 w-3.5 text-amber-600" />
						<p class="text-xs text-amber-700">No students are checked in here yet.</p>
					</div>
					<button
						disabled={isAssigning}
						onclick={handleAssignClinicOnly}
						class="w-full py-2 rounded-lg text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
						style="background: linear-gradient(to bottom, #10b981, #059669); box-shadow: 0 1px 3px rgba(5,150,105,0.3);"
					>
						{#if isAssigning}
							<Loader2 class="w-3 h-3 inline mr-1 animate-spin" /> Checking in…
						{:else}
							Check into clinic without assignment
						{/if}
					</button>
				</div>
			{:else}
				<div>
					<p class="text-[10px] font-medium text-gray-600 mb-1">Student</p>
					<select
						bind:value={assignStudentId}
						class="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-white"
						style="box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);"
					>
						{#each assignStudents as student}
							<option value={student.id}>{student.name} ({student.assigned_patient_count} patients)</option>
						{/each}
					</select>
				</div>
				<button
					disabled={isAssigning || !assignStudentId}
					onclick={handleAssignPatient}
					class="w-full py-2 rounded-lg text-xs font-semibold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(37,99,235,0.3);"
				>
					{#if isAssigning}
						<Loader2 class="w-3 h-3 inline mr-1 animate-spin" /> Assigning…
					{:else}
						Assign to student
					{/if}
				</button>
			{/if}
		</div>
	</AquaModal>
{/if}
