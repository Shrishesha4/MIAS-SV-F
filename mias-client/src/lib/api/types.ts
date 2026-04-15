// MIAS API Types

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface Patient {
  id: string;
  patient_id: string;
  name: string;
  date_of_birth: string;
  gender: 'MALE' | 'FEMALE' | 'OTHER';
  blood_group: string;
  phone: string;
  email?: string;
  address: string;
  photo?: string;
  aadhaar_id?: string;
  abha_id?: string;
  category: string;
  category_color_primary?: string;
  category_color_secondary?: string;
  emergency_contact?: EmergencyContact;
  allergies: Allergy[];
  medical_alerts: MedicalAlert[];
  insurance_policies?: InsurancePolicy[];
}

export interface EmergencyContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  address?: string;
}

export interface InsurancePolicy {
  id: string;
  provider: string;
  policy_number: string;
  valid_until?: string;
  coverage_type?: string;
  insurance_category_id?: string;
  icon_key?: 'shield' | 'landmark' | 'briefcase' | 'building' | 'wallet' | 'heart' | 'off';
  custom_badge_symbol?: string | null;
  color_primary?: string;
  color_secondary?: string;
}

export interface Allergy {
  id: string;
  allergen: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  reaction?: string;
}

export interface MedicalAlert {
  id: string;
  type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  symptoms: string[];
  is_active: boolean;
}

export interface Vital {
  id: string;
  patient_id: string;
  recorded_at: string;
  recorded_by?: string;
  systolic_bp?: number;
  diastolic_bp?: number;
  heart_rate?: number;
  respiratory_rate?: number;
  temperature?: number;
  oxygen_saturation?: number;
  weight?: number;
  blood_glucose?: number;
  cholesterol?: number;
  bmi?: number;
  creatinine?: number;
  urea?: number;
  sodium?: number;
  potassium?: number;
  sgot?: number;
  sgpt?: number;
  hemoglobin?: number;
  wbc?: number;
  platelet?: number;
  rbc?: number;
  hct?: number;
  notes?: string;
}

export interface VitalParameterConfig {
  id: string;
  name: string;
  display_name: string;
  category: string;
  unit?: string | null;
  min_value?: number | null;
  max_value?: number | null;
  is_active?: boolean;
  sort_order?: number;
}

export interface AdmissionIOEvent {
  id: string;
  admission_id: string;
  patient_id: string;
  event_time: string;
  event_type: string;
  description?: string;
  amount_ml?: number;
  recorded_by?: string;
  created_at?: string;
}

export interface AdmissionIOEventSummary {
  iv_input_ml: number;
  oral_intake_ml: number;
  urine_output_ml: number;
  stool_count: number;
}

export interface AdmissionIOEventsResponse {
  events: AdmissionIOEvent[];
  summary: AdmissionIOEventSummary;
}

export interface AdmissionPlanEntry {
  id: string;
  name: string;
  status: string;
  dose?: string;
  route?: string;
  frequency?: string;
}

export interface AdmissionSoapPlanItems {
  drug_notes?: string;
  investigation_notes?: string;
  diet_notes?: string;
  drugs?: AdmissionPlanEntry[];
  investigations?: AdmissionPlanEntry[];
  diet?: AdmissionPlanEntry[];
}

export interface AdmissionSoapMeta {
  author?: string;
  supervisor?: string;
  timestamp?: string;
  next_review?: string;
}

export interface AdmissionSoapNote {
  id: string;
  admission_id: string;
  patient_id: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  plan_items?: AdmissionSoapPlanItems;
  note_meta?: AdmissionSoapMeta;
  created_at?: string;
  created_by?: string;
  updated_at?: string;
  updated_by?: string;
}

export interface AdmissionEquipment {
  id: string;
  admission_id: string;
  equipment_type: string;
  equipment_id?: string;
  connected_since?: string;
  status: string;
  live_data?: Record<string, number | string>;
}

export interface MedicalRecord {
  id: string;
  patient_id: string;
  date: string;
  time: string;
  type: 'CONSULTATION' | 'LABORATORY' | 'PROCEDURE' | 'MEDICATION';
  description: string;
  performed_by: string;
  supervised_by?: string;
  department: string;
  status: string;
  diagnosis?: string;
  recommendations?: string;
  findings: MedicalFinding[];
  images: MedicalImage[];
}

export interface MedicalFinding {
  id: string;
  parameter: string;
  value: string;
  reference?: string;
  status: string;
}

export interface MedicalImage {
  id: string;
  title: string;
  description?: string;
  url: string;
  type: string;
}

export interface Prescription {
  id: string;
  prescription_id?: string;
  patient_id: string;
  date: string;
  doctor: string;
  doctor_license?: string;
  department: string;
  hospital_name?: string;
  hospital_address?: string;
  hospital_contact?: string;
  hospital_email?: string;
  hospital_website?: string;
  status: 'ACTIVE' | 'BOUGHT' | 'RECEIVE' | 'COMPLETED';
  notes?: string;
  doctor_signature?: string;
  patient?: {
    name: string;
    patient_id: string;
    date_of_birth: string;
    gender: string;
    phone: string;
    address: string;
  };
  medications: PrescriptionMedication[];
}

export interface PrescriptionMedication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  duration: string;
  instructions?: string;
  refills_remaining: number;
  start_date: string;
  end_date: string;
}

export interface WalletTransaction {
  id: string;
  patient_id: string;
  wallet_type: 'HOSPITAL' | 'PHARMACY';
  date: string;
  time: string;
  description: string;
  amount: number;
  type: 'CREDIT' | 'DEBIT';
  payment_method?: string;
  reference_number?: string;
  invoice_number?: string;
  department?: string;
  provider?: string;
  subtotal?: number;
  tax?: number;
  insurance_coverage?: number;
  insurance_provider?: string;
  policy_number?: string;
  claim_number?: string;
  notes?: string;
}

export interface Admission {
  id: string;
  patient_id: string;
  admission_date: string;
  discharge_date?: string;
  department: string;
  ward: string;
  bed_number: string;
  attending_doctor: string;
  reason?: string;
  diagnosis?: string;
  status: 'Active' | 'Discharged' | 'Transferred';
  notes?: string;
  program_duration_days?: number;
  related_admission_id?: string;
  transferred_from_department?: string;
  referring_doctor?: string;
  discharge_summary?: string;
  discharge_instructions?: string;
  follow_up_date?: string;
  ioEvents?: AdmissionIOEvent[];
  soapNotes?: AdmissionSoapNote[];
  equipment?: AdmissionEquipment[];
}

export interface ReportFinding {
  id: string;
  parameter: string;
  value: string;
  reference?: string;
  status: string;
}

export interface ReportImage {
  id: string;
  title: string;
  description?: string;
  url: string;
  type?: string;
}

export interface Report {
  id: string;
  patient_id: string;
  date: string;
  time?: string;
  type: string;
  title: string;
  department: string;
  ordered_by: string;
  performed_by?: string;
  supervised_by?: string;
  status: 'NORMAL' | 'ABNORMAL' | 'CRITICAL' | 'PENDING';
  result_summary?: string;
  notes?: string;
  file_url?: string;
  findings?: ReportFinding[];
  images?: ReportImage[];
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  is_read: boolean | number;
  created_at: string;
}

export interface Student {
  id: string;
  student_id: string;
  name: string;
  year: number;
  semester: number;
  program: string;
  photo?: string;
  gpa: number;
  academic_standing: string;
  academic_advisor?: string;
}

export interface Faculty {
  id: string;
  faculty_id: string;
  name: string;
  department: string;
  specialty?: string;
  phone?: string;
  email?: string;
  photo?: string;
  availability?: string;
}

export interface Approval {
  id: string;
  type: string;
  submitted_by: { id: string; student_id?: string; name: string } | string | null;
  submitted_at: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  description?: string;
  patient?: any;
  case_record?: any;
  admission?: any;
  prescription?: any;
  score?: number;
  comments?: string;
  processed_at?: string;
}

export interface CaseRecord {
  id: string;
  patient_id: string;
  student_id: string;
  date: string;
  time?: string;
  department?: string;
  procedure?: string;
  chief_complaint?: string;
  description?: string;
  history?: string;
  examination?: string;
  findings?: string;
  diagnosis: string;
  icd_code?: string;
  treatment_plan?: string;
  treatment?: string;
  notes?: string;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'Pending' | 'Approved' | 'Rejected';
  grade?: string;
  score?: number;
  faculty_comments?: string;
  provider?: string;
  created_by?: string;
  created_by_name?: string;
  created_by_role?: string;
  approver?: string;
  approver_name?: string;
  approved_at?: string;
  created_at?: string;
  updated_at?: string;
}

// ------- New types for redesigned views -------

export interface AssignedPatient {
  id: string;
  patient_id: string;
  name: string;
  age: number;
  gender: 'MALE' | 'FEMALE' | 'OTHER';
  condition: string;
  photo?: string;
}

export interface ClinicInfo {
  name: string;
  location: string;
}

export interface ClinicPatient {
  id: string;
  patient_id: string;
  name: string;
  photo?: string;
  appointment_time: string;
  provider: string;
  status: 'Checked In' | 'In Progress' | 'Waiting' | 'Completed';
}

export interface EmergencyDoctor {
  id: string;
  name: string;
  specialty: string;
  department: string;
  photo?: string;
  status: 'Available' | 'Busy' | 'Unavailable';
  availability: string;
}

export interface StudentProfile extends Student {
  degree: string;
  attendance: number;
  overall_attendance: number;
  clinical_attendance: number;
  lecture_attendance: number;
  lab_attendance: number;
  academic_advisor: string;
  disciplinary_actions: DisciplinaryAction[];
  emergency_contact: StudentEmergencyContact;
  recent_absences: RecentAbsence[];
}

export interface DisciplinaryAction {
  id: string;
  type: string;
  description: string;
  date: string;
  status: 'Resolved' | 'Active' | 'Pending';
  details: string;
  resolution?: string;
}

export interface StudentEmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  email: string;
  address: string;
}

export interface RecentAbsence {
  id: string;
  date: string;
  reason: string;
  status: 'Approved' | 'Unapproved' | 'Pending';
}

export interface PatientDetail extends Patient {
  age: number;
  primary_diagnosis: string;
  diagnosis_doctor: string;
  diagnosis_date: string;
  diagnosis_time: string;
}

export interface PrescriptionRequest {
  id: string;
  medication: string;
  requested_date: string;
  status: 'Pending' | 'Approved' | 'Rejected';
  notes: string;
}

export interface PatientMedication {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  status: 'Active' | 'Completed' | 'Discontinued';
  start_date: string;
  end_date: string;
  instructions?: string;
  prescribed_by: string;
  department: string;
}
