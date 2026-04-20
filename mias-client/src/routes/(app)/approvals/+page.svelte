<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { facultyApi } from '$lib/api/faculty';
    import { approvalsApi, type ApprovalItem } from '$lib/api/approvals';
    import { toastStore } from '$lib/stores/toast';
    import { redirectIfUnauthorized } from '$lib/utils/roleGuard';
    import AquaCard from '$lib/components/ui/AquaCard.svelte';
    import Avatar from '$lib/components/ui/Avatar.svelte';
    import InsuranceTypeBadges from '$lib/components/patient/InsuranceTypeBadges.svelte';
    import PatientInsuranceAvatar from '$lib/components/patient/PatientInsuranceAvatar.svelte';
    import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
    import type { FormFieldDefinition } from '$lib/types/forms';
    import {
        CheckCircle, XCircle, Clock, ClipboardList, AlertTriangle,
        FileText, Eye, Calendar, Stethoscope, ChevronLeft, X,
        Building, Bed, User, Shield, Heart
    } from 'lucide-svelte';

    type ApprovalCaseRecordDraft = {
        type?: string;
        procedure_name?: string;
        procedure_description?: string;
        doctor_name?: string;
        description?: string;
        department?: string;
        findings?: string;
        diagnosis?: string;
        treatment?: string;
        notes?: string;
        form_fields?: FormFieldDefinition[];
        form_values?: Record<string, any>;
    };

    type ApprovalAdmissionDraft = {
        department?: string;
        ward?: string;
        bed_number?: string;
        attending_doctor?: string;
        reason?: string;
        diagnosis?: string;
        notes?: string;
        referring_doctor?: string;
        drug_allergy?: string;
        chief_complaints?: string;
        history_of_present_illness?: string;
        medication_history?: string;
        weight_admission?: string | number;
        pain_score?: string | number;
        physical_examination?: string;
        provisional_diagnosis?: string;
        proposed_plan?: string;
        discharge_summary?: string;
    };

    type ApprovalMedicationDraft = {
        id: string;
        name?: string;
        dosage?: string;
        frequency?: string;
        duration?: string;
        timing?: string;
        instructions?: string;
        start_date?: string;
        end_date?: string;
    };

    type ApprovalPrescriptionDraft = {
        doctor?: string;
        department?: string;
        notes?: string;
        medications: ApprovalMedicationDraft[];
    };

    type ApprovalDraft = {
        case_record?: ApprovalCaseRecordDraft;
        admission?: ApprovalAdmissionDraft;
        prescription?: ApprovalPrescriptionDraft;
    };

    // State
    let activeTab = $state('pending');
    let pendingApprovals: ApprovalItem[] = $state([]);
    let historyApprovals: ApprovalItem[] = $state([]);
    let loading = $state(true);
    let facultyId = $state('');
    let approvalType = $state('case-records');
    let processingId = $state<string | null>(null);
    let scores = $state<Record<string, number>>({});
    let approvalComments: Record<string, string> = $state({});
    let detailModal = $state<ApprovalItem | null>(null);
    let approvalDrafts: Record<string, ApprovalDraft> = $state({});

    const tabs = [
        { id: 'pending', label: 'Pending Approvals' },
        { id: 'history', label: 'Approval History' },
    ];

    // Approval type titles
    const typeLabels: Record<string, string> = {
        'case-records': 'Case Record Approvals',
        'discharge': 'Discharge Approvals',
        'admissions': 'Admission Approvals',
        'prescriptions': 'Prescription Approvals',
    };

    const scoreOptions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

    const frequencyOptions = [
        '1-0-1 (M/N)',
        '1-1-1 (M/A/N)',
        '0-0-1 (N)',
        '1-0-0 (M)',
        '0-1-0 (A)',
        '1-1-0 (M/A)',
        '0-1-1 (A/N)',
        'As needed',
        'Once daily',
        'Twice daily',
        'Three times daily',
        'Four times daily',
    ];

    function addDraftMedication(approvalId: string) {
        const draft = approvalDrafts[approvalId];
        if (!draft?.prescription) return;
        draft.prescription.medications = [
            ...draft.prescription.medications,
            { id: crypto.randomUUID(), name: '', dosage: '', frequency: '1-0-1 (M/N)', duration: '', timing: 'AFTER', instructions: '' },
        ];
        approvalDrafts = { ...approvalDrafts };
    }

    function removeDraftMedication(approvalId: string, index: number) {
        const draft = approvalDrafts[approvalId];
        if (!draft?.prescription) return;
        draft.prescription.medications = draft.prescription.medications.filter((_, i) => i !== index);
        approvalDrafts = { ...approvalDrafts };
    }

    let isAdmissionType = $derived(approvalType === 'admissions');
    let usesScore = $derived(approvalType === 'case-records');
    let pageTitle = $derived(typeLabels[approvalType] || 'Approvals');
    let activeCount = $derived(activeTab === 'pending' ? pendingApprovals.length : historyApprovals.length);

    function getScore(id: string): number {
        return scores[id] ?? 5;
    }

    function setScore(id: string, score: number) {
        scores[id] = score;
        scores = { ...scores };
    }

    function formatScoreLabel(score?: number | null): string {
        if (score === undefined || score === null) return '';
        return score === 0 ? 'F' : String(score);
    }

    function createApprovalDraft(approval: ApprovalItem): ApprovalDraft {
        return {
            case_record: approval.case_record
                ? {
                    type: approval.case_record.type || '',
                    procedure_name: approval.case_record.procedure_name || '',
                    procedure_description: approval.case_record.procedure_description || '',
                    doctor_name: approval.case_record.doctor_name || '',
                    description: approval.case_record.description || '',
                    department: approval.case_record.department || '',
                    findings: approval.case_record.findings || '',
                    diagnosis: approval.case_record.diagnosis || '',
                    treatment: approval.case_record.treatment || '',
                    notes: approval.case_record.notes || '',
                    form_fields: approval.case_record.form_fields || undefined,
                    form_values: approval.case_record.form_values
                        ? { ...approval.case_record.form_values as Record<string, any> }
                        : undefined,
                }
                : undefined,
            admission: approval.admission
                ? {
                    department: approval.admission.department || '',
                    ward: approval.admission.ward || '',
                    bed_number: approval.admission.bed_number || '',
                    attending_doctor: approval.admission.attending_doctor || '',
                    reason: approval.admission.reason || '',
                    diagnosis: approval.admission.diagnosis || '',
                    notes: approval.admission.notes || '',
                    referring_doctor: approval.admission.referring_doctor || '',
                    drug_allergy: approval.admission.drug_allergy || '',
                    chief_complaints: approval.admission.chief_complaints || '',
                    history_of_present_illness: approval.admission.history_of_present_illness || '',
                    medication_history: approval.admission.medication_history || '',
                    weight_admission: approval.admission.weight_admission || '',
                    pain_score: approval.admission.pain_score || '',
                    physical_examination: approval.admission.physical_examination || '',
                    provisional_diagnosis: approval.admission.provisional_diagnosis || '',
                    proposed_plan: approval.admission.proposed_plan || '',
                    discharge_summary: approval.admission.discharge_summary || '',
                }
                : undefined,
            prescription: approval.prescription
                ? {
                    doctor: approval.prescription.doctor || '',
                    department: approval.prescription.department || '',
                    notes: approval.prescription.notes || '',
                    medications: (approval.prescription.medications || []).map((medication) => ({
                        id: medication.id,
                        name: medication.name || '',
                        dosage: medication.dosage || '',
                        frequency: medication.frequency || '1-0-1 (M/N)',
                        duration: medication.duration || '',
                        timing: (medication as any).timing || 'AFTER',
                        instructions: medication.instructions || '',
                        start_date: medication.start_date || '',
                        end_date: medication.end_date || '',
                    })),
                }
                : undefined,
        };
    }

    function ensureApprovalDraft(approval: ApprovalItem): ApprovalDraft {
        if (!approvalDrafts[approval.id]) {
            approvalDrafts[approval.id] = createApprovalDraft(approval);
            approvalDrafts = { ...approvalDrafts };
        }
        return approvalDrafts[approval.id];
    }

    function applyDraftToApprovalItem(approval: ApprovalItem): ApprovalItem {
        const draft = approvalDrafts[approval.id];
        if (!draft) return approval;

        return {
            ...approval,
            case_record: approval.case_record && draft.case_record
                ? { ...approval.case_record, ...draft.case_record }
                : approval.case_record,
            admission: approval.admission && draft.admission
                ? { ...approval.admission, ...draft.admission }
                : approval.admission,
            prescription: approval.prescription && draft.prescription
                ? {
                    ...approval.prescription,
                    ...draft.prescription,
                    medications: draft.prescription.medications.map(m => ({
                        id: m.id,
                        name: m.name ?? '',
                        dosage: m.dosage ?? '',
                        frequency: m.frequency ?? '',
                        duration: m.duration ?? '',
                        instructions: m.instructions,
                        start_date: m.start_date,
                        end_date: m.end_date,
                    })),
                }
                : approval.prescription,
        };
    }

    function buildApprovalPayload(approval: ApprovalItem, status: 'APPROVED' | 'REJECTED') {
        const usesScoreForApproval = approval.type === 'CASE_RECORD';
        const score = getScore(approval.id);
        const draft = approvalDrafts[approval.id];

        return {
            status,
            score: usesScoreForApproval ? score : undefined,
            grade: usesScoreForApproval ? formatScoreLabel(score) : undefined,
            comments: approvalComments[approval.id] || (status === 'APPROVED' ? 'Approved' : 'Rejected'),
            case_record_updates: draft?.case_record,
            admission_updates: draft?.admission,
            prescription_updates: draft?.prescription,
        };
    }

    async function handleApprove(approval: ApprovalItem) {
        processingId = approval.id;
        try {
            await approvalsApi.processApproval(facultyId, approval.id, buildApprovalPayload(approval, 'APPROVED'));
            const item = pendingApprovals.find(a => a.id === approval.id);
            if (item) {
                const editedItem = applyDraftToApprovalItem(item);
                pendingApprovals = pendingApprovals.filter(a => a.id !== approval.id);
                historyApprovals = [{
                    ...editedItem,
                    status: 'APPROVED',
                    score: approval.type === 'CASE_RECORD' ? getScore(approval.id) : undefined,
                    processed_at: new Date().toISOString(),
                }, ...historyApprovals];
            }
            if (detailModal?.id === approval.id) detailModal = null;
        } catch (err) {
            toastStore.addToast('Failed to approve', 'error');
        } finally {
            processingId = null;
        }
    }

    async function handleReject(approval: ApprovalItem) {
        processingId = approval.id;
        try {
            await approvalsApi.processApproval(facultyId, approval.id, buildApprovalPayload(approval, 'REJECTED'));
            const item = pendingApprovals.find(a => a.id === approval.id);
            if (item) {
                const editedItem = applyDraftToApprovalItem(item);
                pendingApprovals = pendingApprovals.filter(a => a.id !== approval.id);
                historyApprovals = [{ ...editedItem, status: 'REJECTED', processed_at: new Date().toISOString() }, ...historyApprovals];
            }
            if (detailModal?.id === approval.id) detailModal = null;
        } catch (err) {
            toastStore.addToast('Failed to reject', 'error');
        } finally {
            processingId = null;
        }
    }

    function formatDate(dateStr: string): string {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        }) + ' ' + d.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function openDetail(approval: ApprovalItem) {
        ensureApprovalDraft(approval);
        detailModal = approval;
    }

    onMount(async () => {
        if (!redirectIfUnauthorized(['FACULTY'])) return;

        const urlType = page.url?.searchParams?.get('type') || 'case-records';
        approvalType = urlType;

        try {
            const faculty = await facultyApi.getMe();
            facultyId = faculty.id;

            pendingApprovals = await approvalsApi.getPendingApprovals(faculty.id, approvalType);
            historyApprovals = await approvalsApi.getApprovalHistory(faculty.id);
            historyApprovals = historyApprovals.filter(a => {
                const typeMap: Record<string, string> = {
                    'case-records': 'CASE_RECORD',
                    'discharge': 'DISCHARGE_SUMMARY',
                    'admissions': 'ADMISSION',
                    'prescriptions': 'PRESCRIPTION',
                };
                return a.type === typeMap[approvalType];
            });
        } catch (err) {
            toastStore.addToast('Failed to load approvals', 'error');
        } finally {
            loading = false;
        }
    });

    $effect(() => {
        if (loading || !facultyId) return;
        const interval = setInterval(async () => {
            try {
                pendingApprovals = await approvalsApi.getPendingApprovals(facultyId, approvalType);
            } catch (err) {
                toastStore.addToast('Auto-refresh failed', 'error');
            }
        }, 30000);
        return () => clearInterval(interval);
    });
</script>

<div class="px-4 py-4 md:px-6 md:py-6">
    {#if loading}
        <div class="flex items-center justify-center py-20">
            <div class="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
    {:else}
        <div class="mx-auto max-w-5xl space-y-5">
            <!-- Header -->
            <div class="flex items-start gap-3">
                <button
                    class="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-full cursor-pointer"
                    style="background: linear-gradient(to bottom, #f8f9fb, #e8eef5); border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);"
                    onclick={() => goto('/dashboard')}
                    aria-label="Back to dashboard"
                >
                    <ChevronLeft class="h-5 w-5 text-blue-600" />
                </button>

                <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-3">
                        <div
                            class="flex h-11 w-11 items-center justify-center rounded-2xl"
                            style="background: linear-gradient(to bottom, #eef5ff, #dbeafe); border: 1px solid rgba(59,130,246,0.2); box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);"
                        >
                            <ClipboardList class="h-5 w-5 text-blue-600" />
                        </div>
                        <div class="min-w-0">
                            <div class="flex flex-wrap items-center gap-2">
                                <h1 class="text-2xl font-bold text-slate-900">{pageTitle}</h1>
                                <span
                                    class="rounded-full px-2 py-0.5 text-xs font-bold"
                                    style="background: rgba(59,130,246,0.12); color: #2563eb;"
                                >
                                    {activeCount}
                                </span>
                            </div>
                            <p class="mt-1 text-sm text-slate-500">
                                {activeTab === 'pending'
                                    ? 'Review requests and process the pending approvals below.'
                                    : 'Processed decisions for this approval workflow.'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab Bar -->
            <div class="mx-auto flex max-w-3xl rounded-[20px] p-1" style="background: linear-gradient(to bottom, #e2e8f0, #eef2f7); border: 1px solid rgba(148,163,184,0.2); box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);">
                {#each tabs as tab}
                    <button
                        class="flex-1 rounded-[16px] px-4 py-3 text-sm font-semibold text-center cursor-pointer transition-all"
                        style="color: {activeTab === tab.id ? '#2563eb' : '#64748b'};
                               background: {activeTab === tab.id ? 'linear-gradient(to bottom, #ffffff, #f8fafc)' : 'transparent'};
                               box-shadow: {activeTab === tab.id ? '0 10px 24px rgba(15,23,42,0.08), inset 0 1px 0 rgba(255,255,255,0.85)' : 'none'};"
                        onclick={() => activeTab = tab.id}
                    >
                        {tab.label}
                    </button>
                {/each}
            </div>

            <!-- Pending Approvals Tab -->
            {#if activeTab === 'pending'}
                <div class="space-y-5">
                    {#each pendingApprovals as approval (approval.id)}
                        {@const currentScore = getScore(approval.id)}
                        {@const isProcessing = processingId === approval.id}
                        {@const requestDate = approval.submitted_at || approval.case_record?.date || approval.admission?.admission_date || approval.created_at}
                        {@const requestedBy = isAdmissionType
                            ? approval.admission?.referring_doctor || approval.admission?.attending_doctor || approval.submitted_by?.name || 'Not provided'
                            : approval.submitted_by?.name || approval.case_record?.doctor_name || 'Not provided'}
                        {@const summaryLabel = isAdmissionType ? 'Reason for Admission' : 'Case Record Summary'}
                        {@const summaryTitle = isAdmissionType
                            ? approval.admission?.reason || 'No reason provided'
                            : approval.case_record?.procedure_name || approval.case_record?.type || 'Case Record'}
                        {@const summaryBody = isAdmissionType
                            ? approval.admission?.diagnosis || approval.patient?.primary_diagnosis || 'No diagnosis recorded'
                            : approval.case_record?.description || approval.case_record?.procedure_description || approval.patient?.primary_diagnosis || 'No description provided'}
                        <div class="mx-auto max-w-3xl rounded-[28px] border border-slate-200 px-4 py-4 md:px-5 md:py-5"
                            style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 24px 50px rgba(15,23,42,0.08), inset 0 1px 0 rgba(255,255,255,0.8);">
                            <div class="flex items-start justify-between gap-4">
                                <div class="flex min-w-0 items-start gap-4">
                                    <div class="shrink-0">
                                        <PatientInsuranceAvatar
                                            name={approval.patient?.name || 'Patient'}
                                            src={approval.patient?.photo || null}
                                            size="lg"
                                            insurancePolicies={approval.patient?.insurance_policies}
                                            patientCategory={approval.patient?.category}
                                            patientCategoryColorPrimary={approval.patient?.category_color_primary}
                                            patientCategoryColorSecondary={approval.patient?.category_color_secondary}
                                        />
                                    </div>
                                    <div class="min-w-0">
                                        <h3 class="text-2xl font-bold text-slate-900">{approval.patient?.name || 'Unknown Patient'}</h3>
                                        <p class="mt-1 text-sm font-semibold text-slate-400">{approval.patient?.patient_id || 'N/A'}</p>
                                        <InsuranceTypeBadges insurancePolicies={approval.patient?.insurance_policies} compact maxVisible={2} />
                                        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                            <span>{approval.patient?.age || '—'}{approval.patient?.age ? ' yrs' : ''}</span>
                                            <span>{approval.patient?.gender || '—'}</span>
                                            {#if approval.patient?.blood_group}
                                                <span class="rounded-full px-2 py-0.5 font-bold"
                                                    style="background: rgba(239, 68, 68, 0.1); color: #dc2626;">
                                                    {approval.patient.blood_group}
                                                </span>
                                            {/if}
                                        </div>
                                    </div>
                                </div>

                                <button
                                    class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full cursor-pointer"
                                    style="background: linear-gradient(to bottom, #f8fafc, #e2e8f0); border: 1px solid rgba(148,163,184,0.18);"
                                    onclick={() => openDetail(approval)}
                                    title="View full details"
                                    aria-label="View full details"
                                >
                                    <Eye class="h-4 w-4 text-blue-500" />
                                </button>
                            </div>

                            <div class="mt-5 grid gap-3 md:grid-cols-3">
                                <div class="rounded-2xl px-4 py-3 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.16);">
                                    <p class="text-xs font-semibold text-slate-400">{isAdmissionType ? 'Department' : 'Record Type'}</p>
                                    <p class="mt-1 text-base font-bold text-slate-800">
                                        {isAdmissionType
                                            ? approval.admission?.department || 'General'
                                            : approval.case_record?.procedure_name || approval.case_record?.type || 'Case Record'}
                                    </p>
                                </div>
                                <div class="rounded-2xl px-4 py-3 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.16);">
                                    <p class="text-xs font-semibold text-slate-400">Requested by</p>
                                    <p class="mt-1 text-base font-bold text-slate-800">{requestedBy}</p>
                                </div>
                                <div class="rounded-2xl px-4 py-3 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); border: 1px solid rgba(148,163,184,0.16);">
                                    <p class="text-xs font-semibold text-slate-400">Date</p>
                                    <p class="mt-1 text-base font-bold text-slate-800">{formatDate(requestDate)}</p>
                                </div>
                            </div>

                            <div class="mt-4 rounded-2xl px-4 py-3" style="background: linear-gradient(to right, #eff6ff, #dbeafe66); border: 1px solid rgba(96,165,250,0.22);">
                                <div class="flex items-center gap-2 text-blue-600">
                                    {#if isAdmissionType}
                                        <Building class="h-4 w-4" />
                                    {:else}
                                        <FileText class="h-4 w-4" />
                                    {/if}
                                    <span class="text-xs font-bold">{summaryLabel}</span>
                                </div>
                                <p class="mt-1.5 text-lg font-bold text-slate-900">{summaryTitle}</p>
                                <p class="mt-1 text-sm text-slate-600">{summaryBody}</p>
                            </div>

                            {#if (approval.patient?.medical_alerts && approval.patient.medical_alerts.length > 0) || (approval.patient?.allergies && approval.patient.allergies.length > 0)}
                                <div class="mt-3 rounded-2xl px-4 py-3" style="background: linear-gradient(to right, #fef2f2, #fee2e266); border: 1px solid rgba(248,113,113,0.2);">
                                    <div class="flex items-center gap-2 text-red-500">
                                        <AlertTriangle class="h-4 w-4" />
                                        <span class="text-xs font-bold text-red-500">Medical Alerts</span>
                                    </div>
                                    <p class="mt-1.5 text-base font-bold text-red-600">
                                        {#if approval.patient?.allergies && approval.patient.allergies.length > 0}
                                            {approval.patient.allergies.map((allergy) => allergy.allergen).join(', ')}
                                        {:else}
                                            {approval.patient?.medical_alerts?.map((alert) => alert.title).join(', ')}
                                        {/if}
                                    </p>
                                </div>
                            {/if}

                            <div class="mt-4 space-y-2 text-sm text-slate-600">
                                {#if !isAdmissionType && approval.case_record?.doctor_name}
                                    <p class="flex items-center gap-2">
                                        <Stethoscope class="h-4 w-4 text-slate-400" />
                                        <span><span class="font-semibold text-slate-700">Provider:</span> {approval.case_record.doctor_name}</span>
                                    </p>
                                {/if}
                                {#if isAdmissionType && approval.admission?.ward}
                                    <p class="flex items-center gap-2">
                                        <Bed class="h-4 w-4 text-slate-400" />
                                        <span><span class="font-semibold text-slate-700">Ward / Bed:</span> {approval.admission.ward}{approval.admission.bed_number ? ` · ${approval.admission.bed_number}` : ''}</span>
                                    </p>
                                {/if}
                                {#if approval.submitted_by}
                                    <p class="flex items-center gap-2">
                                        <User class="h-4 w-4 text-slate-400" />
                                        <span><span class="font-semibold text-slate-700">Submitted by:</span> {approval.submitted_by.name}</span>
                                    </p>
                                {/if}
                                {#if approval.patient?.primary_diagnosis && (!isAdmissionType || approval.patient.primary_diagnosis !== approval.admission?.diagnosis)}
                                    <p class="flex items-start gap-2">
                                        <Heart class="mt-0.5 h-4 w-4 text-slate-400" />
                                        <span><span class="font-semibold text-slate-700">Primary diagnosis:</span> {approval.patient.primary_diagnosis}</span>
                                    </p>
                                {/if}
                            </div>

                            <div class="mt-5 border-t border-slate-200 pt-4">
                                <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                                    <div class="space-y-4">
                                        {#if usesScore}
                                            <div>
                                                <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Score</p>
                                                <div class="flex flex-wrap gap-2">
                                                    {#each scoreOptions as score}
                                                        <button
                                                            class="h-10 min-w-10 rounded-2xl px-3 text-sm font-bold cursor-pointer transition-all"
                                                            style="background: {currentScore === score ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : 'linear-gradient(to bottom, #ffffff, #f8fafc)'};
                                                                   color: {currentScore === score ? 'white' : '#64748b'};
                                                                   border: 1px solid {currentScore === score ? '#2563eb' : 'rgba(148,163,184,0.24)'};
                                                                   box-shadow: {currentScore === score ? '0 10px 20px rgba(37,99,235,0.22)' : 'none'};"
                                                            onclick={() => setScore(approval.id, score)}
                                                            disabled={isProcessing}
                                                        >
                                                            {formatScoreLabel(score)}
                                                        </button>
                                                    {/each}
                                                </div>
                                            </div>
                                        {/if}

                                        <div>
                                            <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Comments</p>
                                            <textarea
                                                class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
                                                rows="3"
                                                placeholder="Add comments..."
                                                value={approvalComments[approval.id] || ''}
                                                oninput={(e) => {
                                                    approvalComments[approval.id] = e.currentTarget.value;
                                                    approvalComments = { ...approvalComments };
                                                }}
                                                disabled={isProcessing}
                                            ></textarea>
                                        </div>
                                    </div>

                                    <div class="flex flex-col gap-2 sm:flex-row">
                                        <button
                                            class="inline-flex min-w-32 items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold cursor-pointer disabled:opacity-50"
                                            style="background: linear-gradient(to bottom, #fffbfb, #fff1f2); color: #dc2626; border: 1px solid rgba(248,113,113,0.24); box-shadow: 0 10px 18px rgba(248,113,113,0.08);"
                                            onclick={() => handleReject(approval)}
                                            disabled={isProcessing}
                                        >
                                            <XCircle class="h-4 w-4" />
                                            Reject
                                        </button>
                                        <button
                                            class="inline-flex min-w-32 items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white cursor-pointer disabled:opacity-50"
                                            style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 12px 22px rgba(34,197,94,0.24);"
                                            onclick={() => handleApprove(approval)}
                                            disabled={isProcessing}
                                        >
                                            <CheckCircle class="h-4 w-4" />
                                            {isAdmissionType ? 'Admit' : 'Approve'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/each}

                    {#if pendingApprovals.length === 0}
                        <div class="mx-auto max-w-3xl rounded-[28px] border border-slate-200 px-6 py-12 text-center"
                            style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 18px 40px rgba(15,23,42,0.06);">
                            <CheckCircle class="mx-auto mb-3 h-12 w-12 text-green-200" />
                            <p class="text-base font-semibold text-slate-500">No pending approvals</p>
                            <p class="mt-1 text-sm text-slate-400">All requests in this queue have been processed.</p>
                        </div>
                    {/if}
                </div>

            <!-- Approval History Tab -->
            {:else if activeTab === 'history'}
                <div class="mx-auto max-w-3xl">
                    <AquaCard>
                {#snippet header()}
                    <ClipboardList class="w-4 h-4 text-blue-600 mr-2" />
                    <span class="text-blue-900 font-semibold text-sm">Approval History</span>
                    <span class="ml-auto text-xs text-gray-500">{historyApprovals.length} items</span>
                {/snippet}

                <div class="space-y-3">
                    {#each historyApprovals as approval (approval.id)}
                        {@const isApproved = approval.status === 'APPROVED'}
                        <div class="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
                            <div class="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                                style="background: {isApproved ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};">
                                {#if isApproved}
                                    <CheckCircle class="w-5 h-5 text-green-500" />
                                {:else}
                                    <XCircle class="w-5 h-5 text-red-500" />
                                {/if}
                            </div>
                            <div class="flex-1 min-w-0">
                                <p class="text-sm font-semibold text-gray-800">
                                    {#if isAdmissionType && approval.admission}
                                        Admission · {approval.admission.department || 'Unknown'}
                                    {:else}
                                        {approval.case_record?.procedure_name || approval.case_record?.type || 'Case Record'}
                                    {/if}
                                </p>
                                <p class="text-xs text-gray-500 truncate">
                                    {approval.patient?.name || 'Unknown'} · ID: {approval.patient?.patient_id || 'N/A'}
                                </p>
                            </div>
                            <div class="text-right shrink-0">
                                <p class="text-xs font-bold px-2 py-0.5 rounded-full inline-block"
                                    style="background: {isApproved ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'};
                                           color: {isApproved ? '#16a34a' : '#dc2626'};">
                                    {isApproved ? 'Approved' : 'Rejected'}
                                </p>
                                {#if isApproved && approval.score !== undefined && approval.score !== null}
                                    <p class="text-xs text-gray-500">Score: {formatScoreLabel(approval.score)}</p>
                                {/if}
                                <p class="text-[10px] text-gray-400">
                                    {formatDate(approval.processed_at || approval.created_at)}
                                </p>
                            </div>
                        </div>
                    {/each}

                    {#if historyApprovals.length === 0}
                        <div class="text-center py-8">
                            <Clock class="w-10 h-10 text-gray-200 mx-auto mb-2" />
                            <p class="text-sm text-gray-400">No approval history yet</p>
                        </div>
                    {/if}
                </div>
                    </AquaCard>
                </div>
            {/if}
        </div>
    {/if}
</div>

<!-- Patient Record Detail Modal -->
{#if detailModal}
    {@const approval = detailModal}
    {@const draft = approvalDrafts[approval.id]}
    {@const currentScore = getScore(approval.id)}
    {@const isProcessing = processingId === approval.id}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="fixed left-0 top-0 z-[80] flex h-[100dvh] w-screen items-end justify-center p-3 sm:items-center sm:p-4"
        onclick={(e) => { if (e.target === e.currentTarget) detailModal = null; }}>
        <div class="absolute inset-0" style="background: rgba(15, 23, 42, 0.14); backdrop-filter: blur(3px); -webkit-backdrop-filter: blur(3px);" onclick={() => detailModal = null}></div>
        <div class="relative w-full max-w-lg bg-white rounded-t-2xl max-h-[92vh] overflow-y-auto sm:rounded-2xl"
            style="animation: slideUp 0.3s ease-out;">

            <!-- Modal Header -->
            <div class="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-3 flex items-center justify-between rounded-t-2xl sm:rounded-t-2xl">
                <h2 class="text-lg font-bold text-gray-800">Patient Record Details</h2>
                <button
                    class="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer"
                    style="background: rgba(0,0,0,0.05);"
                    onclick={() => detailModal = null}
                >
                    <X class="w-4 h-4 text-gray-500" />
                </button>
            </div>

            <div class="p-4 space-y-4">
                <!-- Patient Header -->
                <div class="flex items-start gap-3">
                    <div class="relative shrink-0">
                        <PatientInsuranceAvatar
                            name={approval.patient?.name || 'Patient'}
                            src={approval.patient?.photo || null}
                            size="lg"
                            insurancePolicies={approval.patient?.insurance_policies}
                            patientCategory={approval.patient?.category}
                            patientCategoryColorPrimary={approval.patient?.category_color_primary}
                            patientCategoryColorSecondary={approval.patient?.category_color_secondary}
                        />
                    </div>
                    <div class="flex-1">
                        <h3 class="text-lg font-bold text-gray-800">{approval.patient?.name || 'Unknown'}</h3>
                        <p class="text-xs text-gray-500">ID: {approval.patient?.patient_id || 'N/A'}</p>
                        <InsuranceTypeBadges insurancePolicies={approval.patient?.insurance_policies} compact maxVisible={2} />
                        <div class="flex flex-wrap gap-1.5 mt-2">
                            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                style="background: rgba(59, 130, 246, 0.1); color: #2563eb;">
                                {approval.patient?.age || '—'} yrs · {approval.patient?.gender || '—'}
                            </span>
                            {#if approval.patient?.blood_group}
                                <span class="text-[10px] font-bold px-2 py-0.5 rounded-full"
                                    style="background: rgba(239, 68, 68, 0.1); color: #dc2626;">
                                    {approval.patient.blood_group}
                                </span>
                            {/if}
                            {#if isAdmissionType && approval.admission?.department}
                                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                    style="background: rgba(16, 185, 129, 0.1); color: #059669;">
                                    {approval.admission.department}
                                </span>
                            {/if}
                            {#if isAdmissionType && approval.admission?.attending_doctor}
                                <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                    style="background: rgba(139, 92, 246, 0.1); color: #7c3aed;">
                                    {approval.admission.attending_doctor}
                                </span>
                            {/if}
                        </div>
                    </div>
                </div>

                <!-- Medical Alerts & Diagnosis Section -->
                <div class="rounded-xl overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
                    <div class="px-4 py-2.5" style="background: linear-gradient(to right, #fef3c7, #fde68a33);">
                        <h4 class="text-sm font-bold text-amber-800 flex items-center gap-2">
                            <Shield class="w-4 h-4" />
                            Medical Alerts & Diagnosis
                        </h4>
                    </div>
                    <div class="p-4 space-y-3">
                        <!-- Allergies -->
                        {#if approval.patient?.allergies && approval.patient.allergies.length > 0}
                            <div class="rounded-lg p-3" style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.15);">
                                <div class="flex items-center gap-2 mb-1.5">
                                    <AlertTriangle class="w-3.5 h-3.5 text-red-500" />
                                    <span class="text-xs font-bold text-red-700">Allergies</span>
                                </div>
                                <div class="flex flex-wrap gap-1.5">
                                    {#each approval.patient.allergies as allergy}
                                        <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                                            style="background: {allergy.severity === 'HIGH' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'};
                                                   color: {allergy.severity === 'HIGH' ? '#dc2626' : '#d97706'};">
                                            {allergy.allergen} ({allergy.severity})
                                        </span>
                                    {/each}
                                </div>
                            </div>
                        {/if}

                        <!-- Medical Alerts -->
                        {#if approval.patient?.medical_alerts && approval.patient.medical_alerts.length > 0}
                            <div class="rounded-lg p-3" style="background: rgba(245, 158, 11, 0.06); border: 1px solid rgba(245, 158, 11, 0.15);">
                                <div class="flex items-center gap-2 mb-1.5">
                                    <Heart class="w-3.5 h-3.5 text-amber-600" />
                                    <span class="text-xs font-bold text-amber-700">Active Alerts</span>
                                </div>
                                <div class="space-y-1.5">
                                    {#each approval.patient.medical_alerts as alert}
                                        <div class="flex items-start gap-2">
                                            <span class="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                                                style="background: {alert.severity === 'HIGH' ? '#dc2626' : '#d97706'};"></span>
                                            <div>
                                                <p class="text-xs font-semibold text-gray-700">{alert.title}</p>
                                                {#if alert.description}
                                                    <p class="text-[10px] text-gray-500">{alert.description}</p>
                                                {/if}
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {/if}

                        <!-- Primary Diagnosis -->
                        <div class="rounded-lg p-3" style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.15);">
                            <div class="flex items-center gap-2 mb-1">
                                <FileText class="w-3.5 h-3.5 text-blue-500" />
                                <span class="text-xs font-bold text-blue-700">Primary Diagnosis</span>
                            </div>
                            <p class="text-sm text-gray-700">
                                {approval.patient?.primary_diagnosis || 'No primary diagnosis recorded'}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Procedure / Admission Information -->
                <div class="rounded-xl overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
                    <div class="px-4 py-2.5" style="background: linear-gradient(to right, #dbeafe, #bfdbfe33);">
                        <h4 class="text-sm font-bold text-blue-800 flex items-center gap-2">
                            <ClipboardList class="w-4 h-4" />
                            {isAdmissionType ? 'Admission Information' : 'Procedure Information'}
                        </h4>
                    </div>
                    <div class="p-4">
                        {#if isAdmissionType && approval.admission}
                            <div class="space-y-3">
                                <div class="grid grid-cols-2 gap-3">
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Request Type</p>
                                        <p class="text-sm font-semibold text-gray-800">Admission Request</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Date & Time</p>
                                        <p class="text-sm text-gray-800">{formatDate(approval.admission.admission_date || approval.created_at)}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Department</p>
                                        <p class="text-sm text-gray-800">{approval.admission.department}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Provider</p>
                                        <p class="text-sm text-gray-800">{approval.admission.attending_doctor || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Ward / Bed</p>
                                        <p class="text-sm text-gray-800">{approval.admission.ward || 'N/A'} {approval.admission.bed_number ? `· ${approval.admission.bed_number}` : ''}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Record ID</p>
                                        <p class="text-xs text-gray-600 font-mono">{approval.admission.id.slice(0, 8).toUpperCase()}</p>
                                    </div>
                                </div>

                                {#if approval.admission.reason}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Reason for Admission</p>
                                        <p class="text-sm text-gray-800">{approval.admission.reason}</p>
                                    </div>
                                {/if}

                                {#if approval.admission.diagnosis}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Diagnosis</p>
                                        <p class="text-sm text-gray-800">{approval.admission.diagnosis}</p>
                                    </div>
                                {/if}

                                {#if approval.admission.referring_doctor}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Referring Doctor</p>
                                        <p class="text-sm text-gray-800">{approval.admission.referring_doctor}</p>
                                    </div>
                                {/if}

                                {#if approval.admission.notes}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Notes</p>
                                        <p class="text-sm text-gray-700">{approval.admission.notes}</p>
                                    </div>
                                {/if}
                            </div>
                        {:else if approval.case_record}
                            <div class="space-y-3">
                                <div class="grid grid-cols-2 gap-3">
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Procedure</p>
                                        <p class="text-sm font-semibold text-gray-800">{approval.case_record.procedure_name || approval.case_record.type}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Date & Time</p>
                                        <p class="text-sm text-gray-800">{formatDate(approval.case_record.date)}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Provider</p>
                                        <p class="text-sm text-gray-800">{approval.case_record.doctor_name || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Record ID</p>
                                        <p class="text-xs text-gray-600 font-mono">{approval.case_record.id.slice(0, 8).toUpperCase()}</p>
                                    </div>
                                </div>
                                {#if approval.case_record.description}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Description</p>
                                        <p class="text-sm text-gray-800">{approval.case_record.description}</p>
                                    </div>
                                {/if}
                                {#if approval.case_record.procedure_description}
                                    <div>
                                        <p class="text-[10px] text-gray-400 uppercase font-semibold mb-0.5">Procedure Details</p>
                                        <p class="text-sm text-gray-700">{approval.case_record.procedure_description}</p>
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                </div>

                {#if draft}
                    <div class="rounded-xl overflow-hidden" style="border: 1px solid rgba(0,0,0,0.08);">
                        <div class="px-4 py-2.5" style="background: linear-gradient(to right, #f8fafc, #eef2ff);">
                            <h4 class="text-sm font-bold text-slate-800 flex items-center gap-2">
                                <FileText class="w-4 h-4 text-blue-500" />
                                Edit Submitted Details Before Decision
                            </h4>
                        </div>
                        <div class="space-y-3 p-4">
                            {#if approval.case_record && draft.case_record}
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Procedure</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.case_record.procedure_name} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Provider</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.case_record.doctor_name} />
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Description</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.description}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Procedure Details</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.procedure_description}></textarea>
                                </div>
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Findings</p>
                                        <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.findings}></textarea>
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Diagnosis</p>
                                        <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.diagnosis}></textarea>
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Treatment</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.treatment}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Notes</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.case_record.notes}></textarea>
                                </div>
                            {:else if approval.admission && draft.admission}
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Department</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.department} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Attending Doctor</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.attending_doctor} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Ward</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.ward} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Bed Number</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.bed_number} />
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Reason for Admission</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.reason}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Diagnosis</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.diagnosis}></textarea>
                                </div>
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">H/O Allergies</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.drug_allergy} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Current Medications</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.medication_history} />
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Chief Complaints</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.chief_complaints}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">History of Present Illness</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.history_of_present_illness}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Physical Examination</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.physical_examination}></textarea>
                                </div>
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Weight</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.weight_admission} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Pain Score</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.pain_score} />
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Provisional Diagnosis</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="2" bind:value={draft.admission.provisional_diagnosis}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Proposed Care Plan</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.proposed_plan}></textarea>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Referring Doctor</p>
                                    <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.admission.referring_doctor} />
                                </div>
                                {#if approval.type === 'DISCHARGE_SUMMARY'}
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Discharge Summary</p>
                                        <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="4" bind:value={draft.admission.discharge_summary}></textarea>
                                    </div>
                                {/if}
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Notes</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="3" bind:value={draft.admission.notes}></textarea>
                                </div>
                            {:else if approval.prescription && draft.prescription}
                                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Prescriber</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.prescription.doctor} />
                                    </div>
                                    <div>
                                        <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Department</p>
                                        <input class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300" bind:value={draft.prescription.department} />
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-1 text-[10px] font-semibold uppercase text-gray-400">Prescription Notes</p>
                                    <textarea class="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300" rows="2" bind:value={draft.prescription.notes}></textarea>
                                </div>
                                <!-- Medications table — matches PrescriptionForm layout -->
                                <div>
                                    <div class="flex items-center justify-between mb-2">
                                        <div class="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                                            Medications ({draft.prescription.medications.length})
                                        </div>
                                        <button
                                            type="button"
                                            onclick={() => addDraftMedication(approval.id)}
                                            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white cursor-pointer transition-all hover:scale-105"
                                            style="background: linear-gradient(to bottom, #a855f7, #9333ea); box-shadow: 0 2px 4px rgba(147,51,234,0.3);"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                                            ADD DRUG
                                        </button>
                                    </div>

                                    {#if draft.prescription.medications.length === 0}
                                        <div class="text-center py-8 rounded-lg border-2 border-dashed border-gray-200 text-sm text-gray-400">
                                            No medications. Click "ADD DRUG" to add one.
                                        </div>
                                    {:else}
                                        <div class="overflow-x-auto -mx-1 px-1">
                                            <div class="space-y-2" style="min-width: 800px;">
                                                <!-- Table Header -->
                                                <div
                                                    class="grid gap-2 px-2 py-1.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider"
                                                    style="grid-template-columns: 30px 1fr 0.8fr 0.6fr 1fr 0.8fr 1.2fr 30px;"
                                                >
                                                    <div>#</div>
                                                    <div>Drug Name *</div>
                                                    <div>Dosage</div>
                                                    <div>Duration</div>
                                                    <div>Frequency</div>
                                                    <div>Timing</div>
                                                    <div>Instructions</div>
                                                    <div></div>
                                                </div>

                                                {#each draft.prescription.medications as medication, index (medication.id)}
                                                    <div
                                                        class="grid gap-2 p-2 rounded-lg items-center"
                                                        style="grid-template-columns: 30px 1fr 0.8fr 0.6fr 1fr 0.8fr 1.2fr 30px; border: 1px solid rgba(0,0,0,0.08); background: white;"
                                                    >
                                                        <div class="text-xs text-gray-500 font-medium">{index + 1}</div>

                                                        <input
                                                            type="text"
                                                            bind:value={medication.name}
                                                            placeholder="Drug name"
                                                            class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                        />
                                                        <input
                                                            type="text"
                                                            bind:value={medication.dosage}
                                                            placeholder="500mg"
                                                            class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                        />
                                                        <input
                                                            type="text"
                                                            bind:value={medication.duration}
                                                            placeholder="7 days"
                                                            class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                        />
                                                        <select
                                                            bind:value={medication.frequency}
                                                            class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400 cursor-pointer"
                                                        >
                                                            {#each frequencyOptions as opt}
                                                                <option value={opt}>{opt}</option>
                                                            {/each}
                                                        </select>
                                                        <div class="flex gap-1">
                                                            <button
                                                                type="button"
                                                                onclick={() => (medication.timing = 'BEFORE')}
                                                                class="flex-1 px-2 py-1 rounded text-[10px] font-semibold transition-all cursor-pointer"
                                                                style={medication.timing === 'BEFORE'
                                                                    ? 'background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid #3b82f6;'
                                                                    : 'background: rgba(0,0,0,0.03); color: #6b7280; border: 1px solid rgba(0,0,0,0.1);'}
                                                            >BEFORE</button>
                                                            <button
                                                                type="button"
                                                                onclick={() => (medication.timing = 'AFTER')}
                                                                class="flex-1 px-2 py-1 rounded text-[10px] font-semibold transition-all cursor-pointer"
                                                                style={medication.timing === 'AFTER'
                                                                    ? 'background: rgba(59,130,246,0.1); color: #3b82f6; border: 1px solid #3b82f6;'
                                                                    : 'background: rgba(0,0,0,0.03); color: #6b7280; border: 1px solid rgba(0,0,0,0.1);'}
                                                            >AFTER</button>
                                                        </div>
                                                        <input
                                                            type="text"
                                                            bind:value={medication.instructions}
                                                            placeholder="Instructions..."
                                                            class="px-2 py-1.5 rounded text-xs border border-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                        />
                                                        <button
                                                            type="button"
                                                            aria-label="Remove medication"
                                                            onclick={() => removeDraftMedication(approval.id, index)}
                                                            class="flex items-center justify-center w-6 h-6 rounded hover:bg-red-50 transition-colors cursor-pointer"
                                                        >
                                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14H6L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4h6v2"></path></svg>
                                                        </button>
                                                    </div>
                                                {/each}
                                            </div>
                                        </div>
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}

                <!-- Submitted By -->
                {#if approval.submitted_by}
                    <div class="rounded-xl p-3" style="background: rgba(139, 92, 246, 0.05); border: 1px solid rgba(139, 92, 246, 0.15);">
                        <div class="flex items-center gap-2">
                            <User class="w-3.5 h-3.5 text-purple-500" />
                            <span class="text-xs text-gray-500">Submitted by</span>
                            <span class="text-xs font-bold text-gray-800">{approval.submitted_by.name}</span>
                            <span class="text-[10px] text-gray-400">({approval.submitted_by.student_id})</span>
                        </div>
                    </div>
                {/if}

                {#if usesScore}
                    <div>
                        <p class="text-xs text-gray-500 mb-2 font-semibold">Approval Score:</p>
                        <div class="flex flex-wrap gap-2">
                            {#each scoreOptions as score}
                                <button
                                    class="h-11 min-w-11 rounded-lg px-3 text-sm font-bold cursor-pointer transition-all"
                                    style="background: {currentScore === score ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#f1f5f9'};
                                           color: {currentScore === score ? 'white' : '#64748b'};
                                           border: 1px solid {currentScore === score ? '#2563eb' : 'rgba(0,0,0,0.1)'};"
                                    onclick={() => setScore(approval.id, score)}
                                    disabled={isProcessing}
                                >
                                    {formatScoreLabel(score)}
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Comments -->
                <div>
                    <p class="text-xs text-gray-500 mb-2 font-semibold">Comments (optional):</p>
                    <textarea
                        class="w-full rounded-lg border border-gray-200 p-2 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-blue-300"
                        rows="3"
                        placeholder="Add comments..."
                        value={approvalComments[approval.id] || ''}
                        oninput={(e) => {
                            approvalComments[approval.id] = e.currentTarget.value;
                            approvalComments = { ...approvalComments };
                        }}
                        disabled={isProcessing}
                    ></textarea>
                </div>

                <!-- Action Buttons -->
                <div class="flex gap-3 pb-4">
                    <button
                        class="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold cursor-pointer disabled:opacity-50"
                        style="background: white; color: #dc2626; border: 2px solid #fecaca;"
                        onclick={() => handleReject(approval)}
                        disabled={isProcessing}
                    >
                        <XCircle class="w-4 h-4" />
                        Reject
                    </button>
                    <button
                        class="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-white text-sm font-semibold cursor-pointer disabled:opacity-50"
                        style="background: linear-gradient(to bottom, #22c55e, #16a34a); border: 1px solid rgba(0,0,0,0.1);"
                        onclick={() => handleApprove(approval)}
                        disabled={isProcessing}
                    >
                        <CheckCircle class="w-4 h-4" />
                        Approve
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    @keyframes slideUp {
        from { transform: translateY(100%); }
        to { transform: translateY(0); }
    }
</style>
