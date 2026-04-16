import client from './client';
import type {
  Patient,
  Vital,
  VitalParameterConfig,
  MedicalRecord,
  Prescription,
  WalletTransaction,
  Admission,
  Report,
  Notification,
  AdmissionIOEventsResponse,
  AdmissionSoapNote,
  AdmissionSoapPlanItems,
  AdmissionSoapMeta,
  AdmissionEquipment,
} from './types';

export interface Appointment {
  id: string;
  patient_id?: string;
  date: string;
  time: string;
  doctor: string;
  department: string;
  status: string;
  notes?: string;
}

export interface ActiveMedication {
  id: string;
  prescription_id: string;
  name: string;
  dosage: string;
  frequency: string;
  instructions?: string;
  doctor?: string;
}

export interface PatientDashboard {
  next_appointment: Appointment | null;
  active_medications: ActiveMedication[];
  hospital_balance: number;
  pharmacy_balance: number;
  last_visit: string | null;
}

export interface MedicationDoseLog {
  id: string;
  medication_id: string;
  medication_name: string;
  medication_dosage: string;
  status: 'TAKEN' | 'MISSED' | 'SKIPPED';
  logged_at: string;
  scheduled_time: string | null;
  notes: string | null;
}

export interface MedicationAdherence {
  total_doses: number;
  taken: number;
  missed: number;
  skipped: number;
  adherence_rate: number;
  period_days: number;
}

export const patientApi = {
  async getCurrentPatient(): Promise<Patient> {
    const response = await client.get('/patients/me');
    return response.data;
  },

  async getPatient(patientId: string): Promise<Patient> {
    const response = await client.get(`/patients/${patientId}`);
    return response.data;
  },

  async getVitals(patientId: string, days: number = 30): Promise<Vital[]> {
    const response = await client.get(`/patients/${patientId}/vitals`, {
      params: { days },
    });
    return response.data;
  },

  async createVital(patientId: string, vital: Partial<Vital>): Promise<Vital> {
    const response = await client.post(`/patients/${patientId}/vitals`, vital);
    return response.data;
  },

	async getActiveVitalParameters(): Promise<VitalParameterConfig[]> {
		const response = await client.get('/vitals/parameters');
		return response.data;
	},

  async getRecords(patientId: string): Promise<MedicalRecord[]> {
    const response = await client.get(`/patients/${patientId}/records`);
    return response.data;
  },

  async getPrescriptions(patientId: string): Promise<Prescription[]> {
    const response = await client.get(`/patients/${patientId}/prescriptions`);
    return response.data;
  },

  async getAdmissions(patientId: string): Promise<Admission[]> {
    const response = await client.get(`/patients/${patientId}/admissions`);
    return response.data;
  },

  async getReports(patientId: string): Promise<Report[]> {
    const response = await client.get(`/patients/${patientId}/reports`);
    return response.data;
  },

  async getNotifications(patientId: string): Promise<Notification[]> {
    const response = await client.get(`/patients/${patientId}/notifications`);
    return response.data;
  },

  async markNotificationsRead(patientId: string) {
    const response = await client.put(`/patients/${patientId}/notifications/read`);
    return response.data;
  },

  async getWalletTransactions(patientId: string, walletType: 'hospital' | 'pharmacy'): Promise<WalletTransaction[]> {
    const response = await client.get(`/patients/${patientId}/wallet/${walletType}/transactions`);
    return response.data;
  },

  async getAppointments(patientId: string): Promise<Appointment[]> {
    const response = await client.get(`/patients/${patientId}/appointments`);
    return response.data;
  },

  async getNextAppointment(patientId: string): Promise<Appointment | null> {
    const response = await client.get(`/patients/${patientId}/next-appointment`);
    return response.data;
  },

  async getActiveMedications(patientId: string): Promise<ActiveMedication[]> {
    const response = await client.get(`/patients/${patientId}/active-medications`);
    return response.data;
  },

  async getDashboard(patientId: string): Promise<PatientDashboard> {
    const response = await client.get(`/patients/${patientId}/dashboard`);
    return response.data;
  },

  async getWalletBalance(patientId: string, walletType: 'hospital' | 'pharmacy'): Promise<{ balance: number }> {
    const response = await client.get(`/wallet/balance/${patientId}/${walletType}`);
    return response.data;
  },

  async addInsurancePolicy(patientId: string, data: { provider: string; policy_number: string; valid_until?: string; coverage_type?: string }) {
    const response = await client.post(`/patients/${patientId}/insurance`, data);
    return response.data;
  },

  async deleteInsurancePolicy(patientId: string, policyId: string) {
    const response = await client.delete(`/patients/${patientId}/insurance/${policyId}`);
    return response.data;
  },

  async logMedicationDose(
    patientId: string,
    medicationId: string,
    data: { status: string; scheduled_time?: string; notes?: string }
  ): Promise<{ id: string; status: string; logged_at: string; message: string }> {
    const response = await client.post(`/patients/${patientId}/medications/${medicationId}/log-dose`, data);
    return response.data;
  },

  async getMedicationHistory(patientId: string, days = 7): Promise<MedicationDoseLog[]> {
    const response = await client.get(`/patients/${patientId}/medication-history`, {
      params: { days },
    });
    return response.data;
  },

  async getMedicationAdherence(patientId: string, days = 30): Promise<MedicationAdherence> {
    const response = await client.get(`/patients/${patientId}/medication-adherence`, {
      params: { days },
    });
    return response.data;
  },

  // Primary Diagnosis
  async updatePrimaryDiagnosis(patientId: string, data: { diagnosis: string; doctor?: string; date?: string; time?: string }) {
    const response = await client.put(`/patients/${patientId}/primary-diagnosis`, data);
    return response.data;
  },

  async addPrimaryDiagnosisEntry(
    patientId: string,
    data: { diagnosis: string; icd_code?: string; icd_description?: string }
  ) {
    const response = await client.post(`/patients/${patientId}/primary-diagnosis/entries`, data);
    return response.data;
  },

  async removePrimaryDiagnosisEntry(patientId: string, entryId: string) {
    const response = await client.delete(`/patients/${patientId}/primary-diagnosis/entries/${entryId}`);
    return response.data;
  },

  // Medical Alerts
  async addMedicalAlert(patientId: string, data: { title: string; type?: string; severity?: string; added_by?: string }) {
    const response = await client.post(`/patients/${patientId}/medical-alerts`, data);
    return response.data;
  },

  async removeMedicalAlert(patientId: string, alertId: string) {
    const response = await client.delete(`/patients/${patientId}/medical-alerts/${alertId}`);
    return response.data;
  },

  async getMedicalAlertHistory(patientId: string) {
    const response = await client.get(`/patients/${patientId}/medical-alerts/history`);
    return response.data;
  },

  // Prescriptions
  async createPrescription(patientId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/prescriptions`, data);
    return response.data;
  },

  async updatePrescription(patientId: string, rxId: string, data: Record<string, unknown>) {
    const response = await client.put(`/patients/${patientId}/prescriptions/${rxId}`, data);
    return response.data;
  },

  // Prescription Requests
  async getPrescriptionRequests(patientId: string) {
    const response = await client.get(`/patients/${patientId}/prescription-requests`);
    return response.data;
  },

  async createPrescriptionRequest(patientId: string, data: { medication: string; dosage?: string; notes?: string }) {
    const response = await client.post(`/patients/${patientId}/prescription-requests`, data);
    return response.data;
  },

  async respondToPrescriptionRequest(patientId: string, requestId: string, data: { status: string; responded_by?: string; notes?: string }) {
    const response = await client.put(`/patients/${patientId}/prescription-requests/${requestId}/respond`, data);
    return response.data;
  },

  async renewPrescription(patientId: string, rxId: string) {
    const response = await client.post(`/patients/${patientId}/prescriptions/${rxId}/renew`);
    return response.data;
  },

  // Case Records
  async getCaseRecords(patientId: string) {
    const response = await client.get(`/patients/${patientId}/case-records`);
    return response.data;
  },

  async createCaseRecord(patientId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/case-records`, data);
    return response.data;
  },

  async generateCaseRecordDraft(patientId: string, data: {
    department?: string;
    procedure?: string;
    form_name?: string;
    form_description?: string;
    form_values?: Record<string, unknown>;
  }): Promise<{ findings: string; diagnosis: string; treatment: string }> {
    const response = await client.post(`/patients/${patientId}/case-record-draft`, data);
    return response.data;
  },

  // Admissions
  async getAllAdmissions(params?: { status?: string; department?: string }) {
    const response = await client.get('/admissions/', { params });
    return response.data;
  },

  async searchPatientsForAdmission(q: string = '') {
    const response = await client.get('/admissions/patients/search', { params: { q } });
    return response.data;
  },

  async createAdmission(patientId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/admissions`, data);
    return response.data;
  },

  async updateAdmission(patientId: string, admissionId: string, data: Record<string, unknown>) {
    const response = await client.put(`/patients/${patientId}/admissions/${admissionId}`, data);
    return response.data;
  },

  async dischargePatient(patientId: string, admissionId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/admissions/${admissionId}/discharge`, data);
    return response.data;
  },

  async transferPatient(patientId: string, admissionId: string, data: Record<string, unknown>) {
    const response = await client.post(`/patients/${patientId}/admissions/${admissionId}/transfer`, data);
    return response.data;
  },

  async updateProfile(patientId: string, data: { name?: string; phone?: string; email?: string; address?: string; blood_group?: string }) {
    const response = await client.put(`/patients/${patientId}/profile`, data);
    return response.data;
  },

  async uploadPhoto(patientId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post(`/patients/${patientId}/upload-photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async updatePrescriptionStatus(patientId: string, rxId: string, data: { status: string }) {
    const response = await client.put(`/patients/${patientId}/prescriptions/${rxId}/status`, data);
    return response.data;
  },

  // IO Events (for admitted patients)
  async getIOEvents(admissionId: string): Promise<AdmissionIOEventsResponse> {
    const response = await client.get(`/admissions/${admissionId}/io-events`);
    return response.data;
  },

  async addIOEvent(admissionId: string, data: { event_time: string; event_type: string; description?: string; amount_ml?: number }) {
    const response = await client.post(`/admissions/${admissionId}/io-events`, data);
    return response.data;
  },

  async deleteIOEvent(admissionId: string, eventId: string) {
    const response = await client.delete(`/admissions/${admissionId}/io-events/${eventId}`);
    return response.data;
  },

  // SOAP Notes
  async getSOAPNotes(admissionId: string): Promise<AdmissionSoapNote[]> {
    const response = await client.get(`/admissions/${admissionId}/soap-notes`);
    return response.data;
  },

  async createSOAPNote(admissionId: string, data: { subjective?: string; objective?: string; assessment?: string; plan?: string; plan_items?: AdmissionSoapPlanItems; note_meta?: AdmissionSoapMeta }) {
    const response = await client.post(`/admissions/${admissionId}/soap-notes`, data);
    return response.data;
  },

  async updateSOAPNote(admissionId: string, noteId: string, data: { subjective?: string; objective?: string; assessment?: string; plan?: string; plan_items?: AdmissionSoapPlanItems; note_meta?: AdmissionSoapMeta }) {
    const response = await client.put(`/admissions/${admissionId}/soap-notes/${noteId}`, data);
    return response.data;
  },

  // Connected Equipment
  async getEquipment(admissionId: string): Promise<AdmissionEquipment[]> {
    const response = await client.get(`/admissions/${admissionId}/equipment`);
    return response.data;
  },

  async connectEquipment(admissionId: string, data: { equipment_type: string; equipment_id?: string; connected_since?: string; status?: string; live_data?: Record<string, number | string> }) {
    const response = await client.post(`/admissions/${admissionId}/equipment`, data);
    return response.data;
  },

  async disconnectEquipment(admissionId: string, equipId: string) {
    const response = await client.delete(`/admissions/${admissionId}/equipment/${equipId}`);
    return response.data;
  },
};
