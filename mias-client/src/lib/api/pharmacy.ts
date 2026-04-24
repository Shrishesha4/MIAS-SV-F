import client from './client';

export interface PharmacyOrderMedication {
	id: string;
	name: string;
	dosage: string;
	frequency: string;
	duration: string;
	instructions?: string | null;
}

export interface PharmacyOrder {
	id: string;
	prescription_id?: string | null;
	patient: {
		id: string;
		name: string;
		patient_id: string;
	} | null;
	doctor: string;
	department: string;
	requested_by?: string | null;
	requested_at?: string | null;
	dispensing_status: 'PENDING_PREPARATION' | 'READY_FOR_DISPATCH' | 'ISSUED';
	is_urgent: boolean;
	notes?: string | null;
	prepared_at?: string | null;
	issued_at?: string | null;
	medications: PharmacyOrderMedication[];
}

export interface PharmacyDashboardSummary {
	in_preparation: number;
	ready_for_dispatch: number;
	issued_today: number;
	urgent_orders: number;
}

export interface PharmacyDashboardResponse {
	summary: PharmacyDashboardSummary;
	preparation_tray: PharmacyOrder[];
	dispatch_tray: PharmacyOrder[];
}

export const pharmacyApi = {
	async getDashboard(search?: string): Promise<PharmacyDashboardResponse> {
		const response = await client.get('/pharmacy/dashboard', {
			params: search?.trim() ? { search } : undefined,
		});
		return response.data;
	},

	async markPrepared(prescriptionId: string) {
		const response = await client.post(`/pharmacy/prescriptions/${prescriptionId}/prepare`);
		return response.data;
	},

	async markIssued(prescriptionId: string) {
		const response = await client.post(`/pharmacy/prescriptions/${prescriptionId}/issue`);
		return response.data;
	},
};