import client from './client';

export interface PendingPatient {
	id: string;
	patient_id: string;
	name: string;
	age: number | null;
	phone: string;
	email: string;
	registered_at: string;
	has_appointment: boolean;
	has_admission: boolean;
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

export const staffApi = {
	async getPendingPatients(): Promise<PendingPatient[]> {
		const response = await client.get('/staff/pending-patients');
		return response.data;
	},

	async assignToClinic(data: AssignToClinicRequest): Promise<{ id: string; appointment_id: string }> {
		const response = await client.post('/staff/assign-to-clinic', data);
		return response.data;
	},

	async assignToWard(data: AssignToWardRequest): Promise<{ id: string; admission_id: string }> {
		const response = await client.post('/staff/assign-to-ward', data);
		return response.data;
	}
};
