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
	{ key: 'triage_category', label: 'Triage Category', type: 'select', options: ['Red', 'Orange', 'Yellow', 'Green'] },
	{ key: 'chief_complaint', label: 'Chief Complaint', type: 'textarea', rows: 2 },
	{ key: 'onset_duration', label: 'Onset / Duration', type: 'text', placeholder: 'e.g. 3 hours' },
	{ key: 'systolic_bp', label: 'Systolic BP', type: 'number' },
	{ key: 'diastolic_bp', label: 'Diastolic BP', type: 'number' },
	{ key: 'heart_rate', label: 'Heart Rate', type: 'number' },
	{ key: 'respiratory_rate', label: 'Respiratory Rate', type: 'number' },
	{ key: 'temperature', label: 'Temperature', type: 'number' },
	{ key: 'oxygen_saturation', label: 'Oxygen Saturation', type: 'number' },
	{ key: 'weight', label: 'Weight', type: 'number' },
	{ key: 'cbg', label: 'CBG', type: 'number' },
	{ key: 'pain_score', label: 'Pain Score', type: 'number' },
	{ key: 'clinical_history', label: 'Clinical History', type: 'textarea', rows: 3 },
	{ key: 'past_medical_history', label: 'Past Medical History', type: 'textarea', rows: 2 },
	{ key: 'allergies', label: 'Known Allergies', type: 'text' },
	{ key: 'current_medications', label: 'Current Medications', type: 'textarea', rows: 2 },
	{ key: 'reason', label: 'Reason for Admission', type: 'textarea', required: true, rows: 2 },
	{ key: 'diagnosis', label: 'Initial Diagnosis', type: 'text', placeholder: 'Working diagnosis' },
	{ key: 'assessment_plan', label: 'Assessment & Differential Diagnosis', type: 'textarea', rows: 2 },
	{ key: 'treatment_plan', label: 'Treatment Plan', type: 'textarea', rows: 2 },
	{ key: 'notes', label: 'Additional Notes', type: 'textarea', rows: 2 },
	{ key: 'intake_documents', label: 'Supporting Documents', type: 'file', multiple: true, accept: '.pdf,.jpg,.jpeg,.png' },
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