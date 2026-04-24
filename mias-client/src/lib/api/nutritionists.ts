import client from './client';
import type { ClinicPatientInfo } from './clinics';

export interface NutritionistClinicSession {
	id: string;
	clinic_id: string;
	clinic_name: string;
	department: string;
	status: string;
	date: string | null;
	checked_in_at: string | null;
	checked_out_at: string | null;
}

export interface NutritionistClinicSummary {
	id: string;
	name: string;
	department: string;
	location: string | null;
	block: string | null;
	clinic_type: string;
}

export interface NutritionistProfile {
	id: string;
	nutritionist_id: string;
	name: string;
	phone: string | null;
	email: string | null;
	photo: string | null;
	clinic: NutritionistClinicSummary | null;
	active_session: NutritionistClinicSession | null;
}

export interface NutritionistPatient extends ClinicPatientInfo {
	nutrition_note_id: string | null;
	nutrition_note: string;
	nutrition_note_updated_at: string | null;
	nutrition_note_is_completed: boolean;
	nutrition_note_completed_at: string | null;
}

export interface NutritionistPortalData {
	clinic: NutritionistClinicSummary | null;
	checked_in: boolean;
	active_session: NutritionistClinicSession | null;
	patients: NutritionistPatient[];
}

export const nutritionistApi = {
	async getMe(): Promise<NutritionistProfile> {
		return (await client.get('/nutritionists/me')).data;
	},

	async getPatients(): Promise<NutritionistPortalData> {
		return (await client.get('/nutritionists/me/patients')).data;
	},

	async checkIn() {
		return (await client.post('/nutritionists/me/check-in')).data;
	},

	async checkOut(sessionId: string) {
		return (await client.post(`/nutritionists/me/check-out/${sessionId}`)).data;
	},

	async saveNote(patientId: string, content: string) {
		return (await client.put(`/nutritionists/me/patients/${patientId}/note`, { content })).data;
	},

	async updateNoteStatus(patientId: string, is_completed: boolean) {
		return (await client.put(`/nutritionists/me/patients/${patientId}/status`, { is_completed })).data;
	},
};
