/**
 * Defines which form fields appear for each procedure.
 * Each field has a key, label, type, and whether it's required.
 */

export interface ProcedureField {
	key: string;
	label: string;
	type: 'text' | 'textarea' | 'number' | 'select' | 'diagnosis';
	required?: boolean;
	placeholder?: string;
	options?: string[];
	rows?: number;
}

export interface ProcedureFieldGroup {
	/** Fields shown between Procedure select and Faculty Approver */
	fields: ProcedureField[];
}

const BP_FIELDS: ProcedureField[] = [
	{ key: 'systolic', label: 'Systolic (mmHg)', type: 'number', required: true, placeholder: 'e.g. 120' },
	{ key: 'diastolic', label: 'Diastolic (mmHg)', type: 'number', required: true, placeholder: 'e.g. 80' },
	{ key: 'patient_position', label: 'Patient Position', type: 'select', required: true, options: ['Sitting', 'Standing', 'Supine', 'Prone', 'Left Lateral', 'Right Lateral'] },
	{ key: 'notes', label: 'Notes', type: 'textarea', placeholder: 'Additional notes...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Clinical findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment plan...', rows: 3 },
];

const PHYSICAL_EXAM_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'e.g. BP 120/80, HR 78, Temp 98.6°F' },
	{ key: 'symptoms', label: 'Symptoms', type: 'textarea', required: true, placeholder: 'Patient-reported symptoms...', rows: 3 },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Clinical observations...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment plan...', rows: 3 },
];

const ECG_FIELDS: ProcedureField[] = [
	{ key: 'heart_rate', label: 'Heart Rate (bpm)', type: 'number', required: true, placeholder: 'e.g. 72' },
	{ key: 'rhythm', label: 'Rhythm', type: 'select', required: true, options: ['Normal Sinus', 'Sinus Tachycardia', 'Sinus Bradycardia', 'Atrial Fibrillation', 'Atrial Flutter', 'Ventricular Tachycardia', 'Other'] },
	{ key: 'observations', label: 'ECG Observations', type: 'textarea', required: true, placeholder: 'PR interval, QRS complex, ST segment...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Interpretation and findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment plan...', rows: 3 },
];

const MEDICATION_REVIEW_FIELDS: ProcedureField[] = [
	{ key: 'current_medications', label: 'Current Medications', type: 'textarea', required: true, placeholder: 'List current medications with dosages...', rows: 3 },
	{ key: 'compliance', label: 'Compliance Assessment', type: 'select', required: true, options: ['Good', 'Partial', 'Poor', 'Non-compliant'] },
	{ key: 'side_effects', label: 'Side Effects', type: 'textarea', placeholder: 'Any reported side effects...', rows: 2 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Review findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Medication changes and plan...', rows: 3 },
];

const GROWTH_ASSESSMENT_FIELDS: ProcedureField[] = [
	{ key: 'height', label: 'Height (cm)', type: 'number', required: true, placeholder: 'e.g. 85' },
	{ key: 'weight', label: 'Weight (kg)', type: 'number', required: true, placeholder: 'e.g. 12.5' },
	{ key: 'head_circumference', label: 'Head Circumference (cm)', type: 'number', placeholder: 'e.g. 46' },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Growth pattern observations...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Recommendations...', rows: 3 },
];

const DEVELOPMENTAL_SCREENING_FIELDS: ProcedureField[] = [
	{ key: 'age_months', label: 'Age (months)', type: 'number', required: true, placeholder: 'e.g. 18' },
	{ key: 'milestones', label: 'Developmental Milestones', type: 'textarea', required: true, placeholder: 'Motor, language, social milestones observed...', rows: 3 },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Behavioral observations...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Screening findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Interventions and follow-up...', rows: 3 },
];

const VACCINATION_FIELDS: ProcedureField[] = [
	{ key: 'vaccine_name', label: 'Vaccine Name', type: 'text', required: true, placeholder: 'e.g. DTaP, MMR, IPV' },
	{ key: 'dose_number', label: 'Dose Number', type: 'text', required: true, placeholder: 'e.g. 1st, 2nd, Booster' },
	{ key: 'site', label: 'Injection Site', type: 'select', required: true, options: ['Left Deltoid', 'Right Deltoid', 'Left Thigh', 'Right Thigh', 'Other'] },
	{ key: 'observations', label: 'Observations', type: 'textarea', placeholder: 'Any immediate reactions...', rows: 2 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Post-vaccination assessment...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Follow-up instructions...', rows: 3 },
];

const WELL_CHILD_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'e.g. HR 110, RR 28, Temp 98.2°F' },
	{ key: 'symptoms', label: 'Symptoms / Concerns', type: 'textarea', required: true, placeholder: 'Parent-reported concerns...', rows: 3 },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'General appearance, nutrition, development...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment and follow-up plan...', rows: 3 },
];

const WOUND_CARE_FIELDS: ProcedureField[] = [
	{ key: 'wound_location', label: 'Wound Location', type: 'text', required: true, placeholder: 'e.g. Right forearm, anterior' },
	{ key: 'wound_type', label: 'Wound Type', type: 'select', required: true, options: ['Incision', 'Laceration', 'Abrasion', 'Puncture', 'Burn', 'Ulcer', 'Surgical'] },
	{ key: 'wound_size', label: 'Wound Size (cm)', type: 'text', required: true, placeholder: 'e.g. 3x2 cm' },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Wound appearance, drainage, signs of infection...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Wound care provided, dressing type, follow-up...', rows: 3 },
];

const SUTURE_REMOVAL_FIELDS: ProcedureField[] = [
	{ key: 'suture_location', label: 'Suture Location', type: 'text', required: true, placeholder: 'e.g. Left forearm' },
	{ key: 'suture_count', label: 'Number of Sutures', type: 'number', required: true, placeholder: 'e.g. 6' },
	{ key: 'wound_healing', label: 'Wound Healing Status', type: 'select', required: true, options: ['Well-healed', 'Partially healed', 'Dehiscence', 'Infected'] },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Wound site appearance...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Post-removal findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Post-removal care instructions...', rows: 3 },
];

const PRE_OP_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, Temp, SpO2, RR' },
	{ key: 'planned_surgery', label: 'Planned Surgery', type: 'text', required: true, placeholder: 'e.g. Appendectomy' },
	{ key: 'symptoms', label: 'Current Symptoms', type: 'textarea', required: true, placeholder: 'Patient-reported symptoms...', rows: 3 },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Pre-operative assessment...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings, lab results...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Pre-operative orders and instructions...', rows: 3 },
];

const POST_OP_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, Temp, SpO2, RR' },
	{ key: 'pain_level', label: 'Pain Level (0-10)', type: 'number', required: true, placeholder: 'e.g. 4' },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Wound site, drainage, mobility...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Post-operative findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Post-operative care plan...', rows: 3 },
];

const PRENATAL_FIELDS: ProcedureField[] = [
	{ key: 'gestational_age', label: 'Gestational Age (weeks)', type: 'number', required: true, placeholder: 'e.g. 28' },
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, Weight, HR' },
	{ key: 'fundal_height', label: 'Fundal Height (cm)', type: 'number', placeholder: 'e.g. 28' },
	{ key: 'symptoms', label: 'Symptoms / Complaints', type: 'textarea', required: true, placeholder: 'Patient concerns...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment and follow-up...', rows: 3 },
];

const PAP_SMEAR_FIELDS: ProcedureField[] = [
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Cervical appearance, specimen collection...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Procedure findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Follow-up plan...', rows: 3 },
];

const BREAST_EXAM_FIELDS: ProcedureField[] = [
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Inspection and palpation findings...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings, any masses or abnormalities...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Recommendations and follow-up...', rows: 3 },
];

const FETAL_MONITORING_FIELDS: ProcedureField[] = [
	{ key: 'gestational_age', label: 'Gestational Age (weeks)', type: 'number', required: true, placeholder: 'e.g. 32' },
	{ key: 'fetal_heart_rate', label: 'Fetal Heart Rate (bpm)', type: 'number', required: true, placeholder: 'e.g. 140' },
	{ key: 'fetal_movement', label: 'Fetal Movement', type: 'select', required: true, options: ['Active', 'Reduced', 'Absent'] },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Monitoring observations...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Monitoring findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Plan of care...', rows: 3 },
];

const MENTAL_STATUS_FIELDS: ProcedureField[] = [
	{ key: 'appearance', label: 'Appearance', type: 'textarea', required: true, placeholder: 'Dress, grooming, psychomotor activity...', rows: 2 },
	{ key: 'mood_affect', label: 'Mood / Affect', type: 'text', required: true, placeholder: 'e.g. Euthymic, Congruent' },
	{ key: 'thought_process', label: 'Thought Process', type: 'select', required: true, options: ['Linear', 'Circumstantial', 'Tangential', 'Loose Associations', 'Flight of Ideas', 'Thought Blocking'] },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Speech, behavior, insight, judgment...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'MSE findings summary...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Treatment plan...', rows: 3 },
];

const COUNSELING_FIELDS: ProcedureField[] = [
	{ key: 'session_type', label: 'Session Type', type: 'select', required: true, options: ['Individual', 'Group', 'Family', 'Couples'] },
	{ key: 'presenting_concern', label: 'Presenting Concern', type: 'textarea', required: true, placeholder: 'Current concerns discussed...', rows: 3 },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Client affect, engagement, progress...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Session findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Therapeutic interventions, homework, plan...', rows: 3 },
];

const PSYCH_MED_MGMT_FIELDS: ProcedureField[] = [
	{ key: 'current_medications', label: 'Current Medications', type: 'textarea', required: true, placeholder: 'List current psychiatric medications...', rows: 3 },
	{ key: 'compliance', label: 'Compliance', type: 'select', required: true, options: ['Good', 'Partial', 'Poor', 'Non-compliant'] },
	{ key: 'side_effects', label: 'Side Effects', type: 'textarea', placeholder: 'Reported side effects...', rows: 2 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Medication changes and plan...', rows: 3 },
];

const RISK_ASSESSMENT_FIELDS: ProcedureField[] = [
	{ key: 'risk_type', label: 'Risk Type', type: 'select', required: true, options: ['Suicidal Ideation', 'Self-harm', 'Violence', 'Substance Abuse', 'Psychosis'] },
	{ key: 'risk_level', label: 'Risk Level', type: 'select', required: true, options: ['Low', 'Moderate', 'High', 'Imminent'] },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Risk factors, protective factors...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Safety plan, interventions...', rows: 3 },
];

const TRIAGE_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, Temp, SpO2, RR' },
	{ key: 'chief_complaint', label: 'Chief Complaint', type: 'text', required: true, placeholder: 'Primary reason for visit' },
	{ key: 'triage_level', label: 'Triage Level', type: 'select', required: true, options: ['1 - Resuscitation', '2 - Emergent', '3 - Urgent', '4 - Less Urgent', '5 - Non-Urgent'] },
	{ key: 'symptoms', label: 'Symptoms', type: 'textarea', required: true, placeholder: 'Onset, duration, severity...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Initial assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Initial management...', rows: 3 },
];

const TRAUMA_CARE_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, Temp, SpO2, RR, GCS' },
	{ key: 'mechanism', label: 'Mechanism of Injury', type: 'text', required: true, placeholder: 'e.g. MVC, Fall from height' },
	{ key: 'injuries', label: 'Injuries Noted', type: 'textarea', required: true, placeholder: 'Primary and secondary survey findings...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Examination findings, imaging...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Interventions performed, disposition...', rows: 3 },
];

const RESUSCITATION_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Initial Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, SpO2, GCS' },
	{ key: 'presenting_condition', label: 'Presenting Condition', type: 'text', required: true, placeholder: 'e.g. Cardiac arrest, Respiratory failure' },
	{ key: 'interventions', label: 'Interventions', type: 'textarea', required: true, placeholder: 'CPR, Defibrillation, Intubation, Medications...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Response to treatment...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Ongoing management, disposition...', rows: 3 },
];

const EMERGENCY_STABILIZATION_FIELDS: ProcedureField[] = [
	{ key: 'vital_signs', label: 'Vital Signs', type: 'text', required: true, placeholder: 'BP, HR, Temp, SpO2, RR' },
	{ key: 'presenting_condition', label: 'Presenting Condition', type: 'text', required: true, placeholder: 'e.g. Acute asthma, Anaphylaxis' },
	{ key: 'observations', label: 'Observations', type: 'textarea', required: true, placeholder: 'Clinical observations...', rows: 3 },
	{ key: 'findings', label: 'Findings', type: 'textarea', required: true, placeholder: 'Assessment findings...', rows: 3 },
	{ key: 'diagnosis', label: 'Diagnosis', type: 'diagnosis', required: true },
	{ key: 'treatment', label: 'Treatment', type: 'textarea', required: true, placeholder: 'Stabilization measures, disposition...', rows: 3 },
];

/**
 * Maps "Department::Procedure" to its field configuration.
 * Use getProcedureFields() to look up fields.
 */
const PROCEDURE_FIELD_MAP: Record<string, ProcedureFieldGroup> = {
	// Internal Medicine
	'Internal Medicine::Blood Pressure Monitoring': { fields: BP_FIELDS },
	'Internal Medicine::Physical Examination': { fields: PHYSICAL_EXAM_FIELDS },
	'Internal Medicine::ECG Recording': { fields: ECG_FIELDS },
	'Internal Medicine::Medication Review': { fields: MEDICATION_REVIEW_FIELDS },

	// Pediatrics
	'Pediatrics::Growth Assessment': { fields: GROWTH_ASSESSMENT_FIELDS },
	'Pediatrics::Developmental Screening': { fields: DEVELOPMENTAL_SCREENING_FIELDS },
	'Pediatrics::Vaccination': { fields: VACCINATION_FIELDS },
	'Pediatrics::Well-child Checkup': { fields: WELL_CHILD_FIELDS },

	// Surgery
	'Surgery::Wound Care': { fields: WOUND_CARE_FIELDS },
	'Surgery::Suture Removal': { fields: SUTURE_REMOVAL_FIELDS },
	'Surgery::Pre-operative Assessment': { fields: PRE_OP_FIELDS },
	'Surgery::Post-operative Follow-up': { fields: POST_OP_FIELDS },

	// OB/GYN
	'OB/GYN::Prenatal Checkup': { fields: PRENATAL_FIELDS },
	'OB/GYN::Pap Smear': { fields: PAP_SMEAR_FIELDS },
	'OB/GYN::Breast Examination': { fields: BREAST_EXAM_FIELDS },
	'OB/GYN::Fetal Monitoring': { fields: FETAL_MONITORING_FIELDS },

	// Psychiatry
	'Psychiatry::Mental Status Examination': { fields: MENTAL_STATUS_FIELDS },
	'Psychiatry::Counseling Session': { fields: COUNSELING_FIELDS },
	'Psychiatry::Medication Management': { fields: PSYCH_MED_MGMT_FIELDS },
	'Psychiatry::Risk Assessment': { fields: RISK_ASSESSMENT_FIELDS },

	// Emergency Medicine
	'Emergency Medicine::Triage Assessment': { fields: TRIAGE_FIELDS },
	'Emergency Medicine::Trauma Care': { fields: TRAUMA_CARE_FIELDS },
	'Emergency Medicine::Resuscitation': { fields: RESUSCITATION_FIELDS },
	'Emergency Medicine::Emergency Stabilization': { fields: EMERGENCY_STABILIZATION_FIELDS },
};

/**
 * Get the field configuration for a given department and procedure.
 * Returns null if no specific fields are defined.
 */
export function getProcedureFields(department: string, procedure: string): ProcedureField[] | null {
	const key = `${department}::${procedure}`;
	return PROCEDURE_FIELD_MAP[key]?.fields ?? null;
}
