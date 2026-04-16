import client from './client';
import type { InsurancePolicy } from './types';

export interface PendingPatient {
	id: string;
	patient_id: string;
	name: string;
	photo?: string | null;
	age: number | null;
	phone: string;
	email: string;
	registered_at: string;
	has_appointment: boolean;
	has_student_assignment: boolean;
	assigned_student_id: string | null;
	assigned_student_name: string | null;
	has_admission: boolean;
	clinic_id: string | null;
	clinic_name: string | null;
	category?: string | null;
	category_color_primary?: string | null;
	category_color_secondary?: string | null;
	insurance_policies?: InsurancePolicy[];
}

export interface ActiveClinicStudent {
	id: string;
	student_id: string;
	name: string;
	year: number;
	semester: number;
	checked_in_at: string | null;
	session_id: string;
	assigned_patient_count: number;
}

export interface AssignToClinicRequest {
	patient_id: string;
	clinic_id: string;
	scheduled_date: string; // ISO date string
	notes?: string;
}

export interface AssignToWardRequest {
	patient_id: string;
	ward_type: string;
	admission_date: string; // ISO date string
	chief_complaint: string;
	notes?: string;
}

export interface AssignToStudentRequest {
	patient_id: string;
	student_id: string;
	clinic_id?: string;
}

export const staffApi = {
	async getPendingPatients(): Promise<PendingPatient[]> {
		const response = await client.get('/staff/pending-patients');
		return response.data;
	},

	async assignToClinic(data: AssignToClinicRequest): Promise<{ id: string; appointment_id: string }> {
		const response = await client.post('/staff/assign-to-clinic', data);
		return response.data;
	},

	async getActiveStudents(clinicId: string): Promise<ActiveClinicStudent[]> {
		const response = await client.get(`/staff/clinics/${clinicId}/active-students`);
		return response.data;
	},

	async assignToStudent(data: AssignToStudentRequest): Promise<{
		message: string;
		assignment_id: string;
		patient_id: string;
		patient_name: string;
		student_id: string;
		student_name: string;
		student_patient_count: number;
	}> {
		const response = await client.post('/staff/assign-to-student', data);
		return response.data;
	},

	async assignToWard(data: AssignToWardRequest): Promise<{ id: string; admission_id: string }> {
		const response = await client.post('/staff/assign-to-ward', data);
		return response.data;
	},

	async autoAssignPatient(patientId: string, clinicId: string): Promise<{
		message: string;
		assignment_id: string;
		patient_id: string;
		patient_name: string;
		student_id: string;
		student_name: string;
		student_patient_count: number;
	}> {
		const response = await client.post('/staff/auto-assign', {
			patient_id: patientId,
			clinic_id: clinicId,
		});
		return response.data;
	},

	async reassignPatient(patientId: string, studentId: string): Promise<{
		message: string;
		assignment_id: string;
		patient_id: string;
		patient_name: string;
		student_id: string;
		student_name: string;
	}> {
		const response = await client.post('/staff/reassign', {
			patient_id: patientId,
			student_id: studentId,
		});
		return response.data;
	}
};
