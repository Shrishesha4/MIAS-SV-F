<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import { patientApi } from '$lib/api/patients';
	import { studentApi } from '$lib/api/students';
	import { formsApi } from '$lib/api/forms';
	import { authApi } from '$lib/api/auth';
	import { insuranceCategoriesApi, type PublicInsuranceCategory } from '$lib/api/insuranceCategories';
	import {
		defaultAdmissionDischargeFields,
		defaultAdmissionIntakeFields,
		defaultAdmissionTransferFields,
	} from '$lib/config/default-form-definitions';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import type { Admission } from '$lib/api/types';
	import type { FormDefinition } from '$lib/types/forms';
	import {
		appendSupplementalText,
		buildAdmissionAssessmentSubmission,
		asOptionalNumber,
		asOptionalString,
		buildSupplementalFormDescription,
		mergeFieldOptions,
		persistFormFiles,
		resolveFormFieldsByType,
	} from '$lib/utils/forms';
	import AquaCard from '$lib/components/ui/AquaCard.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
	import { 
		Bed, Calendar, User, Building, ChevronDown, ChevronUp, ChevronLeft,
		Clock, Link, FileText, CheckCircle, Circle, ArrowRightCircle, X,
		Plus, Search, LogOut, ArrowRight, Filter, Send, AlertTriangle,
		Phone, Mail, Printer, Download, Hospital
	} from 'lucide-svelte';

	const auth = get(authStore);
	const role = auth.role;
	const isFacultyOrAdmin = role === 'FACULTY' || role === 'ADMIN';
	const isStudent = role === 'STUDENT';

	// Shared state
	let admissions: any[] = $state([]);
	let admissionsMap = $state<Record<string, any>>({});
	let loading = $state(true);
	let expandedId = $state<string | null>(null);
	let showDischargeSummary = $state(false);
	let selectedAdmission = $state<any>(null);

	// Faculty/Admin state
	let filterStatus = $state('');
	let showAdmitModal = $state(false);
	let showDischargeModal = $state(false);
	let showTransferModal = $state(false);
	let actionAdmission = $state<any>(null);
	let submitting = $state(false);
	let actionError = $state('');
	let admissionFormDefinitions: FormDefinition[] = $state([]);
	let admitFormData: Record<string, any> = $state({});
	let dischargeFormData: Record<string, any> = $state({});
	let transferFormData: Record<string, any> = $state({});
	let insuranceOptions: PublicInsuranceCategory[] = $state([]);
	let insuranceLoading = $state(false);
	let admitInsuranceCategoryId = $state('');
	let reqInsuranceCategoryId = $state('');

	// Admit form fields
	let searchQuery = $state('');
	let searchResults: any[] = $state([]);
	let searching = $state(false);
	let selectedPatient = $state<any>(null);
	let admitDepartment = $state('');
	let admitWard = $state('');
	let admitBed = $state('');
	let admitReason = $state('');
	let admitDiagnosis = $state('');
	let admitNotes = $state('');
	let dbDepartments: { id: string; name: string; code: string }[] = $state([]);

	// Assessment form expanded fields
	let assessmentSection = $state(0); // 0-based step index
	let triageCategory = $state('');
	let chiefComplaint = $state('');
	let onsetDuration = $state('');
	let vitalsSystolic = $state('');
	let vitalsDiastolic = $state('');
	let vitalsHR = $state('');
	let vitalsRR = $state('');
	let vitalsTemp = $state('');
	let vitalsSpO2 = $state('');
	let vitalsWeight = $state('');
	let gcsBestEye = $state(4);
	let gcsBestVerbal = $state(5);
	let gcsBestMotor = $state(6);
	const gcsTotal = $derived(gcsBestEye + gcsBestVerbal + gcsBestMotor);
	let cbgValue = $state('');
	let painScore = $state(0);
	let clinicalHistory = $state('');
	let pastMedicalHistory = $state('');
	let allergiesText = $state('');
	let currentMedications = $state('');
	let assessmentPlan = $state('');
	let treatmentPlan = $state('');

	const assessmentSteps = ['Triage', 'Vitals', 'Neuro/Pain', 'History', 'Plan'];

	// Discharge form fields
	let dischargeSummary = $state('');
	let dischargeInstructions = $state('');
	let dischargeDiagnosis = $state('');
	let followUpDate = $state('');

	// Transfer form fields
	let transferDepartment = $state('');
	let transferWard = $state('');
	let transferBed = $state('');
	let transferDoctor = $state('');
	let transferNotes = $state('');

	// Student admission request state
	let studentId = $state('');
	let admissionRequests: any[] = $state([]);
	let showRequestModal = $state(false);
	let assignedPatients: any[] = $state([]);
	let facultyApprovers: any[] = $state([]);
	let reqPatient = $state<any>(null);
	let reqFaculty = $state('');
	let reqDepartment = $state('');
	let reqWard = $state('');
	let reqBed = $state('');
	let reqReason = $state('');
	let reqDiagnosis = $state('');
	let reqNotes = $state('');
	let reqError = $state('');
	let reqSubmitting = $state(false);
	let requestFormData: Record<string, any> = $state({});

	const departmentOptions = $derived(dbDepartments.map((department) => department.name));
	const admissionRequestFields = $derived(
		mergeFieldOptions(defaultAdmissionIntakeFields, { department: departmentOptions })
	);
	const admissionIntakeFields = $derived(
		mergeFieldOptions(defaultAdmissionIntakeFields, { department: departmentOptions })
	);
	const admissionDischargeFields = $derived(
		resolveFormFieldsByType(admissionFormDefinitions, 'ADMISSION_DISCHARGE', defaultAdmissionDischargeFields)
	);
	const admissionTransferFields = $derived(
		mergeFieldOptions(
			resolveFormFieldsByType(admissionFormDefinitions, 'ADMISSION_TRANSFER', defaultAdmissionTransferFields),
			{ department: departmentOptions }
		)
	);

	const filteredAdmissions = $derived(
		filterStatus
			? admissions.filter((a: any) => a.status === filterStatus)
			: admissions
	);

	function getStatusIcon(status: string) {
		if (status === 'Discharged') return { color: '#22c55e', icon: CheckCircle };
		if (status === 'Transferred') return { color: '#3b82f6', icon: ArrowRightCircle };
		return { color: '#f59e0b', icon: Circle }; // Active
	}

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('en-US', { 
			month: 'short', day: 'numeric', year: 'numeric' 
		});
	}

	function toggleExpand(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	function openDischargeSummary(admission: any) {
		selectedAdmission = admission;
		showDischargeSummary = true;
	}

	function closeDischargeSummary() {
		showDischargeSummary = false;
		selectedAdmission = null;
	}

	function handlePrintSummary() {
		window.print();
	}

	function handleDownloadSummary() {
		window.print();
	}

	function getRelatedAdmission(id: string | undefined): any | undefined {
		if (!id) return undefined;
		return admissionsMap[id];
	}

	// Faculty actions
	async function searchPatients() {
		if (!searchQuery.trim()) { searchResults = []; return; }
		searching = true;
		try {
			searchResults = await patientApi.searchPatientsForAdmission(searchQuery);
		} catch { searchResults = []; }
		finally { searching = false; }
	}

	function selectPatient(p: any) {
		selectedPatient = p;
		searchQuery = p.name;
		searchResults = [];
		admitInsuranceCategoryId = getCurrentInsuranceCategoryId(p);
	}

	function openAdmitModal() {
		selectedPatient = null;
		searchQuery = '';
		searchResults = [];
		admitFormData = {};
		admitInsuranceCategoryId = '';
		actionError = '';
		showAdmitModal = true;
	}

	async function submitAdmit() {
		if (!selectedPatient) { actionError = 'Please select a patient'; return; }
		if (insuranceOptions.length > 0 && !admitInsuranceCategoryId) { actionError = 'Please select the insurance type for this admission'; return; }
		if (!admitFormData.department) { actionError = 'Please select a department'; return; }
		if (!admitFormData.ward) { actionError = 'Ward is required'; return; }
		if (!admitFormData.bed_number) { actionError = 'Bed number is required'; return; }
		submitting = true;
		actionError = '';
		try {
			const submittedValues = await persistFormFiles(
				admissionIntakeFields,
				admitFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'admission-intake'
			);
			const physicalExamination = [
				['Pallor', asOptionalString(submittedValues.pallor)],
				['Icterus', asOptionalString(submittedValues.icterus)],
				['Cyanosis', asOptionalString(submittedValues.cyanosis)],
				['Clubbing', asOptionalString(submittedValues.clubbing)],
				['Pedal Edema', asOptionalString(submittedValues.pedal_edema)],
				['Lymph nodes', asOptionalString(submittedValues.lymph_nodes)],
				['CVS', asOptionalString(submittedValues.cvs)],
				['RS', asOptionalString(submittedValues.rs)],
				['Abdomen', asOptionalString(submittedValues.abdomen)],
				['CNS', asOptionalString(submittedValues.cns)],
			]
				.filter(([, value]) => value)
				.map(([label, value]) => `${label}: ${value}`)
				.join('; ');
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.additional_information),
				buildSupplementalFormDescription(
					admissionIntakeFields,
					submittedValues,
					new Set([
						'department',
						'ward',
						'bed_number',
						'drug_allergy',
						'chief_complaints',
						'history_of_present_illness',
						'medication_history',
						'weight_admission',
						'pallor',
						'icterus',
						'cyanosis',
						'clubbing',
						'pedal_edema',
						'lymph_nodes',
						'cvs',
						'rs',
						'abdomen',
						'cns',
						'pain_score',
						'provisional_diagnosis',
						'proposed_plan',
						'additional_information',
					])
				)
			);
			const chiefComplaints = asOptionalString(submittedValues.chief_complaints);
			const provisionalDiagnosis = asOptionalString(submittedValues.provisional_diagnosis);
			await patientApi.createAdmission(selectedPatient.id, {
				insurance_category_id: admitInsuranceCategoryId || undefined,
				department: asOptionalString(submittedValues.department) || '',
				ward: asOptionalString(submittedValues.ward) || '',
				bed_number: asOptionalString(submittedValues.bed_number) || '',
				reason: chiefComplaints,
				diagnosis: provisionalDiagnosis,
				notes,
				drug_allergy: asOptionalString(submittedValues.drug_allergy),
				chief_complaints: chiefComplaints,
				history_of_present_illness: asOptionalString(submittedValues.history_of_present_illness),
				medication_history: asOptionalString(submittedValues.medication_history),
				weight_admission: asOptionalNumber(submittedValues.weight_admission),
				pain_score: asOptionalNumber(submittedValues.pain_score),
				provisional_diagnosis: provisionalDiagnosis,
				proposed_plan: asOptionalString(submittedValues.proposed_plan),
				physical_examination: physicalExamination || undefined,
			});
			showAdmitModal = false;
			toastStore.addToast('Patient admitted successfully', 'success');
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to create admission';
			toastStore.addToast(actionError, 'error');
		} finally { submitting = false; }
	}

	function openDischargeModal(admission: any) {
		actionAdmission = admission;
		dischargeFormData = {
			diagnosis: admission.diagnosis || '',
			discharge_summary: '',
			discharge_instructions: '',
			follow_up_date: '',
		};
		actionError = '';
		showDischargeModal = true;
	}

	async function submitDischarge() {
		if (!dischargeFormData.discharge_summary) { actionError = 'Discharge summary is required'; return; }
		submitting = true;
		actionError = '';
		try {
			const submittedValues = await persistFormFiles(
				admissionDischargeFields,
				dischargeFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'admission-discharge'
			);
			const dischargeInstructions = appendSupplementalText(
				asOptionalString(submittedValues.discharge_instructions),
				buildSupplementalFormDescription(
					admissionDischargeFields,
					submittedValues,
					new Set(['diagnosis', 'discharge_summary', 'discharge_instructions', 'follow_up_date'])
				)
			);
			await patientApi.dischargePatient(actionAdmission.patient_id, actionAdmission.id, {
				discharge_summary: asOptionalString(submittedValues.discharge_summary),
				discharge_instructions: dischargeInstructions,
				diagnosis: asOptionalString(submittedValues.diagnosis),
				follow_up_date: asOptionalString(submittedValues.follow_up_date) || null,
			});
			showDischargeModal = false;
			toastStore.addToast('Patient discharged successfully', 'success');
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to discharge';
			toastStore.addToast(actionError, 'error');
		} finally { submitting = false; }
	}

	function openTransferModal(admission: any) {
		actionAdmission = admission;
		transferFormData = {};
		actionError = '';
		showTransferModal = true;
	}

	async function submitTransfer() {
		if (!transferFormData.department) { actionError = 'Please select target department'; return; }
		if (!transferFormData.ward) { actionError = 'Ward is required'; return; }
		if (!transferFormData.bed_number) { actionError = 'Bed number is required'; return; }
		submitting = true;
		actionError = '';
		try {
			const submittedValues = await persistFormFiles(
				admissionTransferFields,
				transferFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'admission-transfer'
			);
			const notes = appendSupplementalText(
				asOptionalString(submittedValues.notes),
				buildSupplementalFormDescription(
					admissionTransferFields,
					submittedValues,
					new Set(['department', 'ward', 'bed_number', 'attending_doctor', 'notes'])
				)
			);
			await patientApi.transferPatient(actionAdmission.patient_id, actionAdmission.id, {
				department: asOptionalString(submittedValues.department) || '',
				ward: asOptionalString(submittedValues.ward) || '',
				bed_number: asOptionalString(submittedValues.bed_number) || '',
				attending_doctor: asOptionalString(submittedValues.attending_doctor),
				notes,
			});
			showTransferModal = false;
			toastStore.addToast('Patient transferred successfully', 'success');
			await loadAdmissions();
		} catch (err: any) {
			actionError = err?.response?.data?.detail || 'Failed to transfer';
			toastStore.addToast(actionError, 'error');
		} finally { submitting = false; }
	}

	async function loadAdmissions() {
		loading = true;
		try {
			if (isFacultyOrAdmin) {
				admissions = await patientApi.getAllAdmissions();
			} else if (isStudent && studentId) {
				admissionRequests = await studentApi.getAdmissionRequests(studentId);
			} else {
				const patient = await patientApi.getCurrentPatient();
				admissions = await patientApi.getAdmissions(patient.id);
			}
			admissionsMap = {};
			admissions.forEach((a: any) => { admissionsMap[a.id] = a; });
		} catch (err) {
			toastStore.addToast('Failed to load admissions', 'error');
		} finally { loading = false; }
	}

	function openRequestModal() {
		reqPatient = null;
		reqFaculty = '';
		reqInsuranceCategoryId = '';
		requestFormData = {};
		reqError = '';
		showRequestModal = true;
	}

	async function submitAdmissionRequest() {
		if (!reqPatient) { reqError = 'Please select a patient'; return; }
		if (!reqFaculty) { reqError = 'Please select approving faculty'; return; }
		if (insuranceOptions.length > 0 && !reqInsuranceCategoryId) { reqError = 'Please select the insurance type for this admission'; return; }
		if (!requestFormData.department) { reqError = 'Please select a department'; return; }
		if (!requestFormData.ward) { reqError = 'Ward is required'; return; }
		if (!requestFormData.bed_number) { reqError = 'Bed number is required'; return; }
		reqSubmitting = true;
		reqError = '';
		try {
			const submittedValues = await persistFormFiles(
				admissionRequestFields,
				requestFormData,
				(file, options) => formsApi.uploadFile(file, options),
				'admission-request'
			);
			const assessment = buildAdmissionAssessmentSubmission(admissionRequestFields, submittedValues);
			await studentApi.submitAdmissionRequest(studentId, {
				patient_id: reqPatient.id,
				faculty_id: reqFaculty,
				insurance_category_id: reqInsuranceCategoryId || undefined,
				department: assessment.department,
				ward: assessment.ward,
				bed_number: assessment.bedNumber,
				reason: assessment.chiefComplaints || '',
				diagnosis: assessment.provisionalDiagnosis,
				notes: assessment.notes,
			});
			showRequestModal = false;
			toastStore.addToast('Admission request submitted successfully', 'success');
			await loadAdmissions();
		} catch (err: any) {
			reqError = err?.response?.data?.detail || 'Failed to submit admission request';
			toastStore.addToast(reqError, 'error');
		} finally { reqSubmitting = false; }
	}

	onMount(async () => {
		try {
			admissionFormDefinitions = await formsApi.getForms();
		} catch {}
		try {
			insuranceLoading = true;
			insuranceOptions = await insuranceCategoriesApi.listPublicCategories();
		} catch {
			insuranceOptions = [];
		} finally {
			insuranceLoading = false;
		}
		if (isFacultyOrAdmin) {
			try {
				const depts = await authApi.getDepartments();
				dbDepartments = depts;
			} catch {}
		}
		if (isStudent) {
			try {
				const me = await studentApi.getMe();
				studentId = me.id;
				assignedPatients = await studentApi.getAssignedPatients(me.id);
				facultyApprovers = await studentApi.getFacultyApprovers();
				const depts = await authApi.getDepartments();
				dbDepartments = depts;
			} catch {}
		}
		await loadAdmissions();
	});

	function getCurrentInsuranceCategoryId(patient: any): string {
		return patient?.insurance_policies?.find((policy: any) => policy.insurance_category_id)?.insurance_category_id || '';
	}

	function getInsuranceName(categoryId: string): string {
		return insuranceOptions.find((option) => option.id === categoryId)?.name || '';
	}
</script>

<div class="px-4 py-4 md:px-6 md:py-6 space-y-2">
	<!-- Header -->
	<div class="flex items-center gap-3 mb-4">
		<button class="p-2 rounded-full hover:bg-gray-100" onclick={() => history.back()}>
			<ChevronLeft class="w-5 h-5 text-gray-600" />
		</button>
		<h1 class="text-lg font-bold text-gray-800 flex-1">
			{isFacultyOrAdmin ? 'Admission Management' : isStudent ? 'Admission Requests' : 'Admission Records'}
		</h1>
		{#if isFacultyOrAdmin}
			<button
				class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-white text-sm font-medium"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={openAdmitModal}
			>
				<Plus class="w-4 h-4" />
				Admit
			</button>
		{/if}
		{#if isStudent}
			<button
				class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-white text-sm font-medium cursor-pointer"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={openRequestModal}
			>
				<Send class="w-4 h-4" />
				Request
			</button>
		{/if}
	</div>

	<!-- Student: Admission Requests List -->
	{#if isStudent}
		{#if loading}
			<div class="flex items-center justify-center py-20">
				<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
			</div>
		{:else if admissionRequests.length === 0}
			<div class="text-center py-16">
				<Bed class="w-14 h-14 text-gray-200 mx-auto mb-3" />
				<p class="text-sm text-gray-400 mb-1">No admission requests yet</p>
				<p class="text-xs text-gray-300">Submit a request to admit a patient for faculty approval</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each admissionRequests as req}
					{@const isPending = req.status === 'PENDING'}
					{@const isApproved = req.status === 'APPROVED'}
					{@const isRejected = req.status === 'REJECTED'}
					<AquaCard padding={false}>
						<div class="p-4">
							<div class="flex items-start justify-between mb-2">
								<div>
									<h3 class="text-sm font-bold text-gray-800">{req.patient?.name || 'Patient'}</h3>
									<p class="text-xs text-gray-500">ID: {req.patient?.patient_id || 'N/A'}</p>
								</div>
								<span class="text-[10px] font-bold px-2 py-0.5 rounded-full"
									style="background: {isPending ? 'rgba(245, 158, 11, 0.1)' : isApproved ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};
									       color: {isPending ? '#d97706' : isApproved ? '#16a34a' : '#dc2626'};">
									{req.status}
								</span>
							</div>
							{#if req.admission}
								<div class="grid grid-cols-2 gap-2 text-xs mb-2">
									<div class="flex items-center gap-1 text-gray-500">
										<Building class="w-3 h-3" />
										{req.admission.department || 'N/A'}
									</div>
									<div class="flex items-center gap-1 text-gray-500">
										<Bed class="w-3 h-3" />
										{req.admission.ward || 'N/A'}
									</div>
								</div>
								{#if req.admission.reason}
									<p class="text-xs text-gray-600 mb-1">
										<span class="font-semibold">Reason:</span> {req.admission.reason}
									</p>
								{/if}
								{#if req.admission.diagnosis}
									<p class="text-xs text-gray-600">
										<span class="font-semibold">Diagnosis:</span> {req.admission.diagnosis}
									</p>
								{/if}
							{/if}
							{#if isApproved && req.score}
								<p class="text-xs text-green-600 mt-2 font-medium">Score: {req.score}/5</p>
							{/if}
							{#if isRejected && req.comments}
								<p class="text-xs text-red-500 mt-2">{req.comments}</p>
							{/if}
							<p class="text-[10px] text-gray-400 mt-2">
								Submitted {formatDate(req.created_at)}
								{#if req.processed_at}
									· Processed {formatDate(req.processed_at)}
								{/if}
							</p>
						</div>
					</AquaCard>
				{/each}
			</div>
		{/if}
	{/if}

	<!-- Student: Admission Request Modal -->
	{#if showRequestModal}
		<AquaModal title="Admission Initial Assessment Form" onclose={() => { showRequestModal = false; requestFormData = {}; }}>
			<div class="space-y-4">
				{#if reqError}
					<div class="rounded-lg p-3" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2);">
						<div class="flex items-center gap-2">
							<AlertTriangle class="w-4 h-4 text-red-500" />
							<span class="text-sm text-red-600">{reqError}</span>
						</div>
					</div>
				{/if}

				<!-- Patient Selection -->
				<div>
					<label for="request-patient" class="text-xs font-semibold text-gray-600 mb-1 block">Patient *</label>
					<select
						id="request-patient"
						class="w-full px-3 py-2.5 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
						onchange={(e) => {
							const val = (e.target as HTMLSelectElement).value;
							reqPatient = assignedPatients.find((p: any) => p.id === val) || null;
						}}
					>
						<option value="">Select a patient...</option>
						{#each assignedPatients as patient}
							<option value={patient.id}>
								{patient.name} ({patient.patient_id})
							</option>
						{/each}
					</select>
				</div>

				<!-- Faculty Approver -->
				<div>
					<label for="request-faculty" class="text-xs font-semibold text-gray-600 mb-1 block">Approving Faculty *</label>
					<select
						id="request-faculty"
						class="w-full px-3 py-2.5 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
						bind:value={reqFaculty}
					>
						<option value="">Select faculty...</option>
						{#each facultyApprovers as f}
							<option value={f.id}>{f.name} – {f.department}</option>
						{/each}
					</select>
				</div>

				<div>
					<label for="request-insurance" class="text-xs font-semibold text-gray-600 mb-1 block">Insurance Type At Admission *</label>
					<select
						id="request-insurance"
						class="w-full px-3 py-2.5 rounded-lg text-sm border border-gray-200 focus:outline-none focus:border-blue-400"
						bind:value={reqInsuranceCategoryId}
						disabled={insuranceLoading || insuranceOptions.length === 0}
					>
						<option value="">{insuranceLoading ? 'Loading insurance types...' : 'Select insurance type...'}</option>
						{#each insuranceOptions as insurance}
							<option value={insurance.id}>{insurance.name}</option>
						{/each}
					</select>
					{#if reqPatient && reqInsuranceCategoryId}
						<p class="mt-1 text-[11px] text-gray-500">Submitting this request with {getInsuranceName(reqInsuranceCategoryId)}.</p>
					{/if}
				</div>


				<DynamicFormRenderer
					fields={admissionRequestFields}
					bind:values={requestFormData}
					idPrefix="admission-request"
				/>

				<!-- Submit Button -->
				<button
					class="w-full py-3 rounded-xl text-white text-sm font-semibold cursor-pointer disabled:opacity-50"
					style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
					disabled={reqSubmitting}
					onclick={submitAdmissionRequest}
				>
					{reqSubmitting ? 'Submitting...' : 'Send for Approval'}
				</button>
			</div>
		</AquaModal>
	{/if}

	<!-- Faculty: Status Filter -->
	{#if isFacultyOrAdmin}
		<div class="flex gap-2 mb-3 overflow-x-auto pb-1">
			{#each ['', 'Active', 'Pending Approval', 'Discharged', 'Transferred'] as status}
				<button
					class="px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors"
					class:bg-blue-500={filterStatus === status}
					class:text-white={filterStatus === status}
					class:bg-gray-100={filterStatus !== status}
					class:text-gray-600={filterStatus !== status}
					onclick={() => filterStatus = status}
				>
					{status || 'All'}
				</button>
			{/each}
		</div>
	{/if}

	{#if loading}
		<div class="flex items-center justify-center py-20">
			<div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if !isStudent}
		<!-- Admissions List -->
		{#each filteredAdmissions as admission}
			{@const statusInfo = getStatusIcon(admission.status)}
			{@const StatusIcon = statusInfo.icon}
			{@const isExpanded = expandedId === admission.id}
			
			<AquaCard padding={false}>
				<!-- Collapsed Header -->
				<button 
					class="w-full px-4 py-3 flex items-center gap-3 cursor-pointer text-left"
					onclick={() => toggleExpand(admission.id)}
				>
					<!-- Status Icon -->
					<div 
						class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
						style="background: {statusInfo.color}20;"
					>
						<StatusIcon class="w-5 h-5" style="color: {statusInfo.color};" />
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						{#if isFacultyOrAdmin && admission.patient_name}
							<p class="text-sm font-bold text-gray-800">{admission.patient_name}</p>
							<p class="text-xs text-gray-500">{admission.patient_display_id} · {formatDate(admission.admission_date)}</p>
						{:else}
							<p class="text-xs text-gray-500">{formatDate(admission.admission_date)}</p>
							<p class="text-sm font-bold text-gray-800">{admission.ward}, {admission.bed_number}</p>
						{/if}
						<p class="text-xs text-gray-600">{admission.attending_doctor} · {admission.department}</p>
					</div>

					<!-- Status + Expand -->
					<div class="flex items-center gap-2">
						<span
							class="px-2 py-0.5 rounded-full text-xs font-medium"
							style="background: {statusInfo.color}15; color: {statusInfo.color};"
						>{admission.status}</span>
						{#if isExpanded}
							<ChevronUp class="w-4 h-4 text-gray-400" />
						{:else}
							<ChevronDown class="w-4 h-4 text-gray-400" />
						{/if}
					</div>
				</button>

				<!-- Expanded Content -->
				{#if isExpanded}
					<div class="px-4 pb-4 space-y-4 border-t border-gray-100">
						<!-- Dates & Location -->
						<div class="grid grid-cols-2 gap-4 pt-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Admission Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">{formatDate(admission.admission_date)}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Discharge Date</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
										<Calendar class="w-4 h-4 text-blue-600" />
									</div>
									<span class="text-sm font-semibold text-gray-800">
										{admission.discharge_date ? formatDate(admission.discharge_date) : 'Active'}
									</span>
								</div>
							</div>
						</div>

						<div class="grid grid-cols-2 gap-4">
							<div>
								<p class="text-xs text-gray-500 mb-1">Ward & Bed</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
										<Bed class="w-4 h-4 text-gray-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.ward}, {admission.bed_number}</span>
								</div>
							</div>
							<div>
								<p class="text-xs text-gray-500 mb-1">Admitted Under</p>
								<div class="flex items-center gap-2">
									<div class="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
										<User class="w-4 h-4 text-green-600" />
									</div>
									<span class="text-sm font-medium text-gray-800">{admission.attending_doctor}</span>
								</div>
							</div>
						</div>

						<!-- Reason for Admission -->
						{#if admission.reason}
							<div class="p-3 rounded-xl border border-gray-200">
								<p class="text-xs text-gray-500 mb-1">Reason for Admission</p>
								<p class="text-sm text-gray-800">{admission.reason}</p>
							</div>
						{/if}

						<!-- Diagnosis -->
						{#if admission.diagnosis}
							<div class="p-3 rounded-xl bg-gray-50">
								<p class="text-xs text-gray-500 mb-1">Diagnosis</p>
								<p class="text-sm text-gray-800">{admission.diagnosis}</p>
							</div>
						{/if}

						<!-- Related Admission (if transferred) -->
						{#if admission.related_admission_id}
							{@const relatedAdmission = getRelatedAdmission(admission.related_admission_id)}
							{#if relatedAdmission}
								<div class="p-3 rounded-xl bg-blue-50 border border-blue-100">
									<div class="flex items-center gap-2 text-blue-600 mb-2">
										<Link class="w-4 h-4" />
										<span class="text-xs font-medium">Related Admission</span>
									</div>
									<p class="text-sm text-blue-800">
										Transferred from {admission.transferred_from_department} ({admission.referring_doctor})
									</p>
								</div>
							{/if}
						{/if}

						<!-- Transferred From Section -->
						{#if admission.transferred_from_department}
							<div class="p-3 rounded-xl border border-gray-200 space-y-2">
								<div>
									<p class="text-xs text-gray-500">Transferred From</p>
									<p class="text-sm font-semibold text-gray-800">{admission.transferred_from_department}</p>
								</div>
								{#if admission.referring_doctor}
									<div>
										<p class="text-xs text-gray-500">Referring Doctor</p>
										<div class="flex items-center gap-2">
											<User class="w-4 h-4 text-gray-500" />
											<span class="text-sm text-gray-800">{admission.referring_doctor}</span>
										</div>
									</div>
								{/if}
							</div>
						{/if}

						<!-- View Discharge Summary Button -->
						{#if admission.status === 'Discharged' && admission.discharge_summary}
							<button 
								class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2"
								style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
								onclick={() => openDischargeSummary(admission)}
							>
								<FileText class="w-5 h-5" />
								View Discharge Summary
							</button>
						{/if}

						<!-- Faculty Action Buttons -->
						{#if isFacultyOrAdmin && admission.status === 'Active'}
							<div class="flex gap-2 pt-2">
								<button
									class="flex-1 py-2.5 rounded-xl text-white text-sm font-medium flex items-center justify-center gap-1.5"
									style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
									onclick={() => openDischargeModal(admission)}
								>
									<LogOut class="w-4 h-4" />
									Discharge
								</button>
								<button
									class="flex-1 py-2.5 rounded-xl text-white text-sm font-medium flex items-center justify-center gap-1.5"
									style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
									onclick={() => openTransferModal(admission)}
								>
									<ArrowRight class="w-4 h-4" />
									Transfer
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</AquaCard>
		{/each}

		{#if filteredAdmissions.length === 0}
			<div class="text-center py-12 text-gray-400">
				<Bed class="w-12 h-12 mx-auto mb-3 opacity-50" />
				<p class="text-sm">No admissions found</p>
			</div>
		{/if}
	{/if}
</div>

<!-- Discharge Summary Modal - Mac OS X Aqua style -->
{#if showDischargeSummary && selectedAdmission}
	{@const isRehab = selectedAdmission.department?.includes('Rehabilitation')}
	{@const lengthOfStay = selectedAdmission.discharge_date
		? Math.ceil((new Date(selectedAdmission.discharge_date).getTime() - new Date(selectedAdmission.admission_date).getTime()) / (1000 * 60 * 60 * 24))
		: null}
	{@const relatedAdmission = getRelatedAdmission(selectedAdmission.related_admission_id)}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 flex items-center justify-center p-4 z-50 print:p-0 print:static print:bg-white"
		style="background-color: rgba(0,0,0,0.5);"
		onkeydown={(e) => e.key === 'Escape' && closeDischargeSummary()}
	>
		<div
			class="w-full max-w-4xl max-h-[90vh] overflow-auto rounded-xl print:shadow-none print:max-w-none print:max-h-none print:w-full"
			style="background-color: white; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid rgba(0,0,0,0.2);"
		>
			<!-- Report Header with Close Button -->
			<div
				class="sticky top-0 border-b border-gray-200 p-4 flex items-center justify-between z-10 print:hidden"
				style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea); box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);"
			>
				<div class="flex items-center">
					<div class="flex mr-3">
						<button
							onclick={closeDischargeSummary}
							class="w-3.5 h-3.5 rounded-full relative cursor-pointer group"
							style="background: linear-gradient(to bottom, #ff5f57, #e0443e); box-shadow: 0 1px 1px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.25); border: 1px solid rgba(100,0,0,0.4);"
						>
							<X size={8} class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[#7d0000] opacity-0 group-hover:opacity-100" />
						</button>
					</div>
					<h2 class="text-base font-semibold text-gray-800">
						{isRehab ? 'Rehabilitation Discharge Summary' : 'Discharge Summary'}
					</h2>
				</div>
				<div class="flex space-x-2">
					<button
						onclick={handlePrintSummary}
						class="p-2 rounded-lg cursor-pointer"
						style="background: linear-gradient(to bottom, #f8f9fb, #d9e1ea); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
						title="Print Summary"
					>
						<Printer size={16} class="text-blue-700" />
					</button>
					<button
						onclick={handleDownloadSummary}
						class="p-2 rounded-lg cursor-pointer"
						style="background: linear-gradient(to bottom, #f8f9fb, #d9e1ea); border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 2px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.8);"
						title="Download Summary"
					>
						<Download size={16} class="text-blue-700" />
					</button>
				</div>
			</div>

			<!-- Discharge Summary Content -->
			<div class="p-6 print:p-8">
				<!-- Institution Header -->
				<div
					class="text-white p-6 rounded-lg mb-6 print:bg-blue-600 overflow-hidden relative"
					style="background: {isRehab
						? 'linear-gradient(135deg, #9333ea 0%, #8b5cf6 50%, #7e22ce 100%)'
						: 'linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%)'}; box-shadow: 0 2px 10px rgba(0,0,0,0.2), 0 0 1px rgba(0,0,0,0.3); border: 1px solid rgba(0,0,0,0.15);"
				>
					<!-- Aqua glossy effect overlay -->
					<div
						class="absolute inset-0 pointer-events-none"
						style="background: linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.15) 30%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0) 51%, rgba(0,0,0,0.05) 100%); border-radius: 7px;"
					></div>

					<div class="flex flex-col md:flex-row md:justify-between md:items-start gap-4 relative">
						<div>
							<h2 class="text-xl font-bold" style="color: white;">Saveetha Medical College Hospital</h2>
							<p class="mt-1 font-medium" style="color: white;">Saveetha Nagar, Thandalam</p>
							<p class="font-medium" style="color: white;">Chennai 600077</p>
							<div class="flex items-center mt-2">
								<Phone size={14} class="mr-1.5" style="color: white;" />
								<p class="font-medium" style="color: white;">(044) 2680-1050</p>
							</div>
							<div class="flex items-center mt-1">
								<Mail size={14} class="mr-1.5" style="color: white;" />
								<p class="font-medium" style="color: white;">info@saveethamedical.com</p>
							</div>
						</div>
						<div class="text-left md:text-right">
							<h3 class="text-lg font-extrabold tracking-wide" style="color: white;">
								{isRehab ? 'REHABILITATION DISCHARGE SUMMARY' : 'DISCHARGE SUMMARY'}
							</h3>
							<p class="mt-2 font-medium" style="color: white;">Admission ID: {selectedAdmission.id}</p>
							<p class="mt-1 font-medium" style="color: white;">Admission Date: {formatDate(selectedAdmission.admission_date)}</p>
							<p class="mt-1 font-medium" style="color: white;">Discharge Date: {formatDate(selectedAdmission.discharge_date)}</p>
						</div>
					</div>
				</div>

				<!-- Admission Details - Mac OS X Aqua style -->
				<div
					class="bg-white p-5 rounded-lg mb-6 relative overflow-hidden"
					style="border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
				>
					<div
						class="absolute top-0 left-0 right-0 h-8 pointer-events-none"
						style="background: linear-gradient(to bottom, rgba(240,245,250,0.8), rgba(240,245,250,0)); border-top-left-radius: 7px; border-top-right-radius: 7px;"
					></div>
					<h4 class="font-medium text-gray-800 mb-3 pb-2 border-b border-gray-200 flex items-center relative">
						{#if isRehab}
							<Hospital size={16} class="mr-2 text-purple-600" />
						{:else}
							<Bed size={16} class="mr-2 text-blue-600" />
						{/if}
						Admission Details
					</h4>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
						<div>
							<p class="text-sm mb-2">
								<span class="font-medium">Ward & Bed:</span> {selectedAdmission.ward}, {selectedAdmission.bed_number}
							</p>
							<p class="text-sm mb-2">
								<span class="font-medium">Department:</span> {selectedAdmission.department}
							</p>
							<p class="text-sm">
								<span class="font-medium">Admitted Under:</span> {selectedAdmission.attending_doctor}
							</p>
						</div>
						<div>
							<p class="text-sm mb-2">
								<span class="font-medium">Admission Type:</span> {isRehab ? 'Rehabilitation' : 'Inpatient'}
							</p>
							<p class="text-sm mb-2">
								<span class="font-medium">Length of Stay:</span> {lengthOfStay ?? 'N/A'} days
							</p>
							<p class="text-sm">
								<span class="font-medium">Discharge Status:</span> {selectedAdmission.status}
							</p>
						</div>
					</div>
				</div>

				<!-- Rehabilitation Transfer Details -->
				{#if isRehab && relatedAdmission}
					<div
						class="mb-6 p-5 rounded-lg"
						style="background-color: rgba(243, 232, 255, 0.5); border: 1px solid rgba(192, 132, 252, 0.3); box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);"
					>
						<h4
							class="font-medium text-gray-800 mb-3 pb-2 border-b border-purple-100 flex items-center"
							style="text-shadow: 0 1px 0 rgba(255,255,255,0.5);"
						>
							<Hospital size={16} class="mr-2 text-purple-600" />
							Rehabilitation Program
						</h4>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 mb-4">
							<div>
								{#if selectedAdmission.program_duration_days}
									<p class="text-sm mb-2">
										<span class="font-medium">Duration:</span> {selectedAdmission.program_duration_days} days
									</p>
								{/if}
								{#if selectedAdmission.transferred_from_department}
									<p class="text-sm">
										<span class="font-medium">Transferred From:</span> {selectedAdmission.transferred_from_department}
									</p>
								{/if}
							</div>
							<div>
								{#if selectedAdmission.referring_doctor}
									<p class="text-sm mb-2">
										<span class="font-medium">Referring Doctor:</span> {selectedAdmission.referring_doctor}
									</p>
								{/if}
							</div>
						</div>
					</div>
				{/if}

				<!-- Clinical Information -->
				{#if selectedAdmission.diagnosis || selectedAdmission.reason}
					<div
						class="bg-white p-5 rounded-lg mb-6"
						style="border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
					>
						<h4 class="font-medium text-gray-800 mb-3 pb-2 border-b border-gray-200">
							Diagnosis & Complaints
						</h4>
						<div class="space-y-4">
							{#if selectedAdmission.diagnosis}
								<div>
									<p class="text-sm font-medium mb-1">Discharge Diagnosis:</p>
									<p class="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">{selectedAdmission.diagnosis}</p>
								</div>
							{/if}
							{#if selectedAdmission.reason}
								<div>
									<p class="text-sm font-medium mb-1">Reason for Admission:</p>
									<p class="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">{selectedAdmission.reason}</p>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Hospital Course / Summary -->
				{#if selectedAdmission.discharge_summary}
					<div
						class="bg-white p-5 rounded-lg mb-6"
						style="border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
					>
						<h4 class="font-medium text-gray-800 mb-3 pb-2 border-b border-gray-200">
							Hospital Course
						</h4>
						<p class="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">{selectedAdmission.discharge_summary}</p>
					</div>
				{/if}

				<!-- Discharge Instructions -->
				{#if selectedAdmission.discharge_instructions || selectedAdmission.follow_up_date}
					<div
						class="bg-white p-5 rounded-lg mb-6"
						style="border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
					>
						<h4 class="font-medium text-gray-800 mb-3 pb-2 border-b border-gray-200">
							Discharge Instructions
						</h4>
						<div class="space-y-4">
							{#if selectedAdmission.discharge_instructions}
								<div>
									<p class="text-sm font-medium mb-1">Instructions:</p>
									<p class="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">{selectedAdmission.discharge_instructions}</p>
								</div>
							{/if}
							{#if selectedAdmission.follow_up_date}
								<div>
									<p class="text-sm font-medium mb-2">Follow-up Appointment:</p>
									<div class="bg-gray-50 p-3 rounded-md flex items-center gap-2">
										<Calendar size={14} class="text-green-600" />
										<p class="text-sm text-gray-700">
											Scheduled: <strong>{formatDate(selectedAdmission.follow_up_date)}</strong>
										</p>
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				{#if selectedAdmission.notes}
					<div
						class="bg-white p-5 rounded-lg mb-6"
						style="border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
					>
						<h4 class="font-medium text-gray-800 mb-3 pb-2 border-b border-gray-200">
							Additional Notes
						</h4>
						<p class="text-sm text-gray-700 bg-gray-50 p-3 rounded-md">{selectedAdmission.notes}</p>
					</div>
				{/if}

				<!-- Footer -->
				<div class="mt-10 pt-5 border-t border-gray-200 text-center">
					<div class="flex items-center justify-center mb-2">
						<Building size={16} class="text-gray-400 mr-2" />
						<p class="text-sm text-gray-500">
							Saveetha Medical College Hospital, Saveetha Nagar, Thandalam, Chennai 600077
						</p>
					</div>
					<p class="text-xs text-gray-500">
						This is an official discharge summary from Saveetha Medical College Hospital.
					</p>
					<p class="text-xs text-gray-500 mt-1">
						For any inquiries, please contact our medical records department at records@saveethamedical.com
					</p>
					<p class="text-xs text-gray-500 mt-1">
						Document generated on: {new Date().toLocaleString()}
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Admit Patient Modal -->
{#if showAdmitModal}
	<AquaModal onClose={() => { showAdmitModal = false; admitFormData = {}; }}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<Plus class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Admission Initial Assessment Form</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<!-- Patient Search (always visible at top) -->
			<div>
				<label for="admit-patient" class="text-xs text-gray-500 mb-1 block">Patient</label>
				<div class="relative">
					<div class="flex items-center px-3 py-2.5 rounded-xl border border-gray-200">
						<Search class="w-4 h-4 text-gray-400 mr-2 shrink-0" />
						<input
							type="text"
							placeholder="Search patient by name or ID..."
							bind:value={searchQuery}
							oninput={searchPatients}
							class="flex-1 outline-none text-sm text-gray-700 bg-transparent"
						/>
					</div>
					{#if searchResults.length > 0}
						<div class="mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
							{#each searchResults as p}
								<button
									class="w-full px-4 py-2.5 text-left hover:bg-gray-50 flex items-center gap-3 text-sm"
									onclick={() => selectPatient(p)}
								>
									<User class="w-4 h-4 text-gray-400" />
									<div>
										<p class="font-medium text-gray-800">{p.name}</p>
										<p class="text-xs text-gray-500">{p.patient_id} · {p.gender} · {p.blood_group}</p>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
				{#if selectedPatient}
					<div class="mt-2 p-2 rounded-lg bg-blue-50 flex items-center gap-2 text-sm text-blue-700">
						<CheckCircle class="w-4 h-4" />
						<span>{selectedPatient.name} ({selectedPatient.patient_id})</span>
					</div>
				{/if}
			</div>

			<div>
				<label for="admit-insurance" class="text-xs text-gray-500 mb-1 block">Insurance Type At Admission</label>
				<select
					id="admit-insurance"
					class="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-700 disabled:opacity-60"
					bind:value={admitInsuranceCategoryId}
					disabled={insuranceLoading || insuranceOptions.length === 0}
				>
					<option value="">{insuranceLoading ? 'Loading insurance types...' : 'Select insurance type...'}</option>
					{#each insuranceOptions as insurance}
						<option value={insurance.id}>{insurance.name}</option>
					{/each}
				</select>
				{#if selectedPatient && admitInsuranceCategoryId}
					<p class="mt-1 text-[11px] text-gray-500">This admission will use {getInsuranceName(admitInsuranceCategoryId)} for the patient’s insurance selection.</p>
				{/if}
			</div>


			<DynamicFormRenderer
				fields={admissionIntakeFields}
				bind:values={admitFormData}
				idPrefix="admission-intake"
			/>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
				style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
				onclick={submitAdmit}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Admit Patient
			</button>
		</div>
	</AquaModal>
{/if}

<!-- Discharge Modal -->
{#if showDischargeModal && actionAdmission}
	<AquaModal onClose={() => { showDischargeModal = false; dischargeFormData = {}; }}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<LogOut class="w-5 h-5 text-green-600" />
				<span class="font-semibold text-gray-800">Discharge Patient</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<div class="p-3 rounded-xl bg-gray-50 text-sm">
				<p class="text-gray-500">Patient</p>
				<p class="font-semibold text-gray-800">{actionAdmission.patient_name || 'N/A'}</p>
				<p class="text-xs text-gray-500 mt-1">{actionAdmission.department} · {actionAdmission.ward}, {actionAdmission.bed_number}</p>
			</div>


			<DynamicFormRenderer
				fields={admissionDischargeFields}
				bind:values={dischargeFormData}
				idPrefix="admission-discharge"
			/>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50"
				style="background: linear-gradient(to bottom, #22c55e, #16a34a);"
				onclick={submitDischarge}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Confirm Discharge
			</button>
		</div>
	</AquaModal>
{/if}

<!-- Transfer Modal -->
{#if showTransferModal && actionAdmission}
	<AquaModal onClose={() => { showTransferModal = false; transferFormData = {}; }}>
		{#snippet header()}
			<div class="flex items-center gap-2">
				<ArrowRight class="w-5 h-5 text-blue-600" />
				<span class="font-semibold text-gray-800">Transfer Patient</span>
			</div>
		{/snippet}

		<div class="space-y-4">
			{#if actionError}
				<div class="p-3 rounded-lg bg-red-50 text-red-600 text-sm">{actionError}</div>
			{/if}

			<div class="p-3 rounded-xl bg-gray-50 text-sm">
				<p class="text-gray-500">Transferring from</p>
				<p class="font-semibold text-gray-800">{actionAdmission.department}</p>
				<p class="text-xs text-gray-500">{actionAdmission.ward}, {actionAdmission.bed_number} · {actionAdmission.attending_doctor}</p>
			</div>


			<DynamicFormRenderer
				fields={admissionTransferFields}
				bind:values={transferFormData}
				idPrefix="admission-transfer"
			/>

			<button
				class="w-full py-3 rounded-xl text-white font-medium flex items-center justify-center gap-2 disabled:opacity-50"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={submitTransfer}
				disabled={submitting}
			>
				{#if submitting}
					<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
				{/if}
				Confirm Transfer
			</button>
		</div>
	</AquaModal>
{/if}
