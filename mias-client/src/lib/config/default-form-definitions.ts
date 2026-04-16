import type { FormFieldDefinition } from '$lib/types/forms';

const prescriptionFrequencyOptions = [
	'Once daily',
	'Twice daily',
	'Three times daily',
	'Four times daily',
	'Every 8 hours',
	'Every 12 hours',
	'As needed',
	'Once weekly',
];

export const defaultAdmissionRequestFields: FormFieldDefinition[] = [
	{ key: 'department', label: 'Department', type: 'select', options: [], placeholder: 'Select department' },
	{ key: 'ward', label: 'Ward', type: 'text', placeholder: 'e.g., General Ward A' },
	{ key: 'bed_number', label: 'Bed Number', type: 'text', placeholder: 'e.g., A-12' },
	{ key: 'reason', label: 'Reason for Admission', type: 'textarea', required: true, rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'text', placeholder: 'Enter diagnosis' },
	{ key: 'notes', label: 'Additional Notes', type: 'textarea', rows: 2 },
	{ key: 'referring_doctor', label: 'Referring Doctor', type: 'text', placeholder: 'Doctor or clinic name' },
	{ key: 'supporting_documents', label: 'Supporting Documents', type: 'file', multiple: true, accept: '.pdf,.jpg,.jpeg,.png' },
];

export const defaultAdmissionIntakeFields: FormFieldDefinition[] = [
	{ key: 'department', label: 'Department', type: 'select', required: true, options: [] },
	{ key: 'ward', label: 'Ward', type: 'text', required: true, placeholder: 'General Ward' },
	{ key: 'bed_number', label: 'Bed Number', type: 'text', required: true, placeholder: 'A-12' },
	{ key: 'drug_allergy', label: 'H/O allergies', type: 'select', options: ['Yes', 'No'] },
	{ key: 'chief_complaints', label: 'Chief Complaints', type: 'textarea', rows: 3 },
	{ key: 'history_of_present_illness', label: 'History Of present Illness', type: 'textarea', rows: 3 },
	{ key: 'medication_history', label: 'Current Medications', type: 'textarea', rows: 3 },
	{ key: 'weight_admission', label: 'Clinical Examination Weight', type: 'number' },
	{ key: 'pallor', label: 'Pallor', type: 'select', options: ['Yes', 'No'] },
	{ key: 'icterus', label: 'Icterus', type: 'select', options: ['Yes', 'No'] },
	{ key: 'cyanosis', label: 'Cyanosis', type: 'select', options: ['Yes', 'No'] },
	{ key: 'clubbing', label: 'Clubbing', type: 'select', options: ['Yes', 'No'] },
	{ key: 'pedal_edema', label: 'Pedal Edema', type: 'select', options: ['Yes', 'No'] },
	{ key: 'lymph_nodes', label: 'Lymph nodes', type: 'select', options: ['Yes', 'No'] },
	{ key: 'cvs', label: 'CVS', type: 'textarea', rows: 2, help_text: 'Systemic Examination' },
	{ key: 'rs', label: 'RS', type: 'textarea', rows: 2 },
	{ key: 'abdomen', label: 'Abdomen', type: 'textarea', rows: 2 },
	{ key: 'cns', label: 'CNS', type: 'textarea', rows: 2 },
	{ key: 'pain_score', label: 'Pain Score', type: 'select', required: true, options: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'], help_text: '0 = No pain, 1-3 = Mild pain, 4-5 = Moderate pain, 6-7 = Severe pain, 8-9 = Very severe pain, 10 = Worse pain' },
	{ key: 'dvt_score', label: 'DVT score', type: 'text' },
	{ key: 'psychological_evaluation', label: 'Psychological Evaluation', type: 'select', options: ['Normal', 'Anxious', 'Depressed', 'Others(specify)'] },
	{ key: 'provisional_diagnosis', label: 'Provisional Diagnosis', type: 'textarea', rows: 2 },
	{ key: 'proposed_plan', label: 'Proposed Care Plan', type: 'textarea', rows: 3 },
	{ key: 'expected_cost_outcome_briefed', label: 'Expected Cost & Outcome briefed to patient / patient attendants', type: 'select', options: ['Yes', 'No'] },
	{ key: 'additional_information', label: 'Additional Information', type: 'textarea', rows: 3 },
];

export const defaultAdmissionDischargeFields: FormFieldDefinition[] = [
	{ key: 'diagnosis', label: 'Final Diagnosis', type: 'text' },
	{ key: 'discharge_summary', label: 'Discharge Summary', type: 'textarea', required: true, rows: 3 },
	{ key: 'discharge_instructions', label: 'Discharge Instructions', type: 'textarea', rows: 3 },
	{ key: 'follow_up_date', label: 'Follow-up Date', type: 'date' },
	{ key: 'summary_documents', label: 'Summary Attachments', type: 'file', multiple: true, accept: '.pdf,.jpg,.jpeg,.png' },
];

export const defaultAdmissionTransferFields: FormFieldDefinition[] = [
	{ key: 'department', label: 'Target Department', type: 'select', required: true, options: [] },
	{ key: 'ward', label: 'Target Ward', type: 'text', required: true },
	{ key: 'bed_number', label: 'Target Bed Number', type: 'text', required: true },
	{ key: 'attending_doctor', label: 'Attending Doctor', type: 'text' },
	{ key: 'notes', label: 'Transfer Notes', type: 'textarea', rows: 3 },
	{ key: 'transfer_documents', label: 'Transfer Attachments', type: 'file', multiple: true, accept: '.pdf,.jpg,.jpeg,.png' },
];

export const defaultVitalEntryFields: FormFieldDefinition[] = [
	{ key: 'systolic_bp', label: 'Systolic BP', type: 'number' },
	{ key: 'diastolic_bp', label: 'Diastolic BP', type: 'number' },
	{ key: 'heart_rate', label: 'Heart Rate', type: 'number' },
	{ key: 'oxygen_saturation', label: 'Oxygen Saturation', type: 'number' },
	{ key: 'temperature', label: 'Temperature', type: 'number' },
	{ key: 'respiratory_rate', label: 'Respiratory Rate', type: 'number' },
	{ key: 'weight', label: 'Weight', type: 'number' },
	{ key: 'blood_glucose', label: 'Blood Glucose', type: 'number' },
	{ key: 'cholesterol', label: 'Cholesterol', type: 'number' },
	{ key: 'bmi', label: 'BMI', type: 'number' },
];

export const defaultPrescriptionCreateFields: FormFieldDefinition[] = [
	{ key: 'name', label: 'Medication Name', type: 'text', required: true, placeholder: 'e.g. Lisinopril' },
	{ key: 'dosage', label: 'Dosage', type: 'text', required: true, placeholder: 'e.g. 10mg' },
	{ key: 'frequency', label: 'Frequency', type: 'select', required: true, options: prescriptionFrequencyOptions },
	{ key: 'start_date', label: 'Start Date', type: 'date' },
	{ key: 'end_date', label: 'End Date', type: 'date' },
	{ key: 'instructions', label: 'Instructions', type: 'textarea', rows: 3 },
	{ key: 'notes', label: 'Prescription Notes', type: 'textarea', rows: 2 },
	{ key: 'attachment', label: 'Prescription Attachment', type: 'file', accept: '.pdf,.jpg,.jpeg,.png' },
];

export const defaultPrescriptionEditFields: FormFieldDefinition[] = [
	{ key: 'status', label: 'Status', type: 'select', options: ['ACTIVE', 'COMPLETED'] },
	...defaultPrescriptionCreateFields,
];

export const defaultPrescriptionRequestFields: FormFieldDefinition[] = [
	{ key: 'medication', label: 'Medication', type: 'text', required: true, placeholder: 'e.g. Metformin' },
	{ key: 'dosage', label: 'Dosage', type: 'text', placeholder: 'e.g. 500mg' },
	{ key: 'notes', label: 'Notes', type: 'textarea', rows: 3 },
	{ key: 'attachment', label: 'Supporting Attachment', type: 'file', accept: '.pdf,.jpg,.jpeg,.png' },
];

export const defaultProfileEditFields: FormFieldDefinition[] = [
	{ key: 'name', label: 'Name', type: 'text', required: true },
	{ key: 'phone', label: 'Phone', type: 'tel', required: true },
	{ key: 'email', label: 'Email', type: 'email' },
	{ key: 'address', label: 'Address', type: 'textarea', rows: 3 },
	{ key: 'blood_group', label: 'Blood Group', type: 'select', options: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] },
];
