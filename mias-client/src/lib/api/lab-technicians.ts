import client from './client';

export interface TechnicianLab {
	id: string;
	name: string;
	department: string;
	lab_type: string;
	location?: string | null;
	is_active: boolean;
}

export interface LabTechnicianProfile {
	id: string;
	technician_id: string;
	user_id: string;
	name: string;
	phone?: string | null;
	email?: string | null;
	photo?: string | null;
	department?: string | null;
	/** @deprecated use `batches` — kept for compat with single-batch scenarios */
	group_id?: string | null;
	/** @deprecated use `batches` — kept for compat with single-batch scenarios */
	group_name?: string | null;
	/** All batches this technician belongs to */
	batches: Array<{ id: string; name: string }>;
	has_selected_lab: number;
	active_lab?: TechnicianLab | null;
	last_checked_in_at?: string | null;
	permitted_labs: TechnicianLab[];
}

export interface LabTechnicianGroupSummary {
	id: string;
	name: string;
	description?: string | null;
	is_active: boolean;
	technician_count: number;
	technician_ids: string[];
	technicians: Array<{
		id: string;
		technician_id: string;
		name: string;
	}>;
	lab_ids: string[];
	labs: TechnicianLab[];
}

export interface LabTestParameterTemplate {
	id: string;
	name: string;
	unit?: string | null;
	reference_required: boolean;
	normal_range?: string | null;
	low?: number | null;
	critically_low?: number | null;
	high?: number | null;
	critically_high?: number | null;
}

export interface LabQueueReport {
	id: string;
	lab_id?: string | null;
	lab_test_id?: string | null;
	patient_id: string;
	patient_name: string;
	patient_code?: string | null;
	title: string;
	type: string;
	department: string;
	ordered_by: string;
	ordered_at?: string | null;
	time?: string | null;
	status: 'NORMAL' | 'ABNORMAL' | 'CRITICAL' | 'PENDING';
	workflow_status: 'NEW' | 'IN_PROGRESS' | 'COMPLETED';
	accepted_by_user_id?: string | null;
	accepted_at?: string | null;
	accepted_by_name?: string | null;
	accepted_by_me: boolean;
	performed_by?: string | null;
	supervised_by?: string | null;
	result_summary?: string | null;
	notes?: string | null;
	findings: Array<{
		id: string;
		parameter: string;
		value: string;
		reference?: string | null;
		status: string;
	}>;
	test_parameters?: LabTestParameterTemplate[] | null;
}

export interface LabDashboardResponse {
	technician: LabTechnicianProfile;
	new_orders: LabQueueReport[];
	in_progress_orders: LabQueueReport[];
	completed_reports: LabQueueReport[];
}

export interface LabTechnicianGroupPayload {
	name: string;
	description?: string;
	technician_ids: string[];
	lab_ids: string[];
	is_active?: boolean;
}

export interface LabResultPayload {
	status: 'NORMAL' | 'ABNORMAL' | 'CRITICAL';
	result_summary?: string;
	notes?: string;
	supervised_by?: string;
	findings: Array<{
		parameter: string;
		value: string;
		reference?: string;
		status?: string;
	}>;
}

export const labTechnicianApi = {
	async getAll(): Promise<LabTechnicianProfile[]> {
		const response = await client.get('/lab-technicians');
		return response.data;
	},

	async getGroups(): Promise<LabTechnicianGroupSummary[]> {
		const response = await client.get('/lab-technicians/groups');
		return response.data;
	},

	async createGroup(data: LabTechnicianGroupPayload): Promise<LabTechnicianGroupSummary> {
		const response = await client.post('/lab-technicians/groups', data);
		return response.data;
	},

	async updateGroup(groupId: string, data: LabTechnicianGroupPayload): Promise<LabTechnicianGroupSummary> {
		const response = await client.put(`/lab-technicians/groups/${groupId}`, data);
		return response.data;
	},

	async deleteGroup(groupId: string): Promise<{ message: string }> {
		const response = await client.delete(`/lab-technicians/groups/${groupId}`);
		return response.data;
	},

	async getMe(): Promise<LabTechnicianProfile> {
		const response = await client.get('/lab-technicians/me');
		return response.data;
	},

	async selectActiveLab(labId: string): Promise<LabTechnicianProfile> {
		const response = await client.put('/lab-technicians/me/lab', { lab_id: labId });
		return response.data;
	},

	async getDashboard(): Promise<LabDashboardResponse> {
		const response = await client.get('/lab-technicians/me/dashboard');
		return response.data;
	},

	async getReport(reportId: string): Promise<LabQueueReport> {
		const response = await client.get(`/lab-technicians/reports/${reportId}`);
		return response.data;
	},

	async acceptReport(reportId: string): Promise<{ message: string }> {
		const response = await client.post(`/lab-technicians/reports/${reportId}/accept`);
		return response.data;
	},

	async saveResults(reportId: string, data: LabResultPayload): Promise<LabQueueReport> {
		const response = await client.put(`/lab-technicians/reports/${reportId}/results`, data);
		return response.data;
	},
};