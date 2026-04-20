import client from './client';

export interface MrdHealthResponse {
	status: string;
	snapshot_age_hours: number | null;
	snapshot_version: string | null;
	database: string;
}

export interface CursorPage<T> {
	items: T[];
	next_cursor: string | null;
	total: number;
}

export interface MrdRecord {
	id: string;
	patient_id: string;
	patient_name: string;
	date: string;
	type: string;
	description: string;
	performed_by: string;
	department: string;
	status: string;
	diagnosis: string | null;
}

export interface MrdRecordDetail extends MrdRecord {
	findings: any[];
	images: any[];
}

export interface MrdPatient {
	id: string;
	patient_id: string;
	name: string;
	phone: string | null;
	date_of_birth: string | null;
	gender: string | null;
}

export interface MrdPrescription {
	id: string;
	prescription_id: string;
	patient_id: string;
	date: string;
	doctor: string;
	department: string;
	status: string;
	notes: string | null;
}

export interface MrdAdmission {
	id: string;
	patient_id: string;
	admission_date: string;
	discharge_date: string | null;
	department: string;
	ward: string | null;
	bed_number: string | null;
	attending_doctor: string;
	status: string;
	diagnosis: string | null;
}

export interface MrdExportJob {
	id: string;
	user_id: string;
	export_type: string;
	status: string;
	created_at: string;
	file_path: string;
	row_count: string;
	error: string;
}

export interface CensusData {
	from_date: string;
	to_date: string;
	op_count: number;
	ip_count: number;
	ot_procedures: number;
	births: number;
	deaths: number;
	investigations: number;
	discharges: number;
	total: number;
}

export interface CensusPatient {
	id: string;
	patient_id: string;
	name: string;
	age: number;
	diagnosis: string;
	department: string;
	date: string;
	time: string;
	status?: string;
}

export interface DepartmentRow {
	department: string;
	op: number;
	ip: number;
	ot: number;
	births: number;
	deaths: number;
	inv_total: number;
	inv_by_type: Record<string, number>;
	discharges: number;
}

export interface DepartmentBreakdown {
	departments: DepartmentRow[];
	investigation_types: string[];
	total: number;
}

export interface MrdLab {
	id: string;
	name: string;
	lab_type: string;
	department: string;
}

export type CensusCategory = 'op' | 'ip' | 'ot' | 'births' | 'deaths' | 'investigations' | 'discharges';

export const mrdApi = {
	async getHealth(): Promise<MrdHealthResponse> {
		const res = await client.get('/mrd/health');
		return res.data;
	},

	async searchPatients(params: {
		name?: string;
		patient_id?: string;
		phone?: string;
		dob_from?: string;
		dob_to?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<CursorPage<MrdPatient>> {
		const res = await client.get('/mrd/patients/search', { params });
		return res.data;
	},

	async getRecords(params: {
		from_date: string;
		to_date: string;
		type?: string;
		department?: string;
		patient_id?: string;
		performed_by?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<CursorPage<MrdRecord>> {
		const res = await client.get('/mrd/records', { params });
		return res.data;
	},

	async getRecord(id: string): Promise<MrdRecordDetail> {
		const res = await client.get(`/mrd/records/${id}`);
		return res.data;
	},

	async getPrescriptions(params: {
		from_date: string;
		to_date: string;
		patient_id?: string;
		department?: string;
		doctor?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<CursorPage<MrdPrescription>> {
		const res = await client.get('/mrd/prescriptions', { params });
		return res.data;
	},

	async getReports(params: {
		from_date: string;
		to_date: string;
		patient_id?: string;
		department?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<CursorPage<any>> {
		const res = await client.get('/mrd/reports', { params });
		return res.data;
	},

	async getAdmissions(params: {
		from_date: string;
		to_date: string;
		patient_id?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<CursorPage<MrdAdmission>> {
		const res = await client.get('/mrd/admissions', { params });
		return res.data;
	},

	async createExport(body: {
		export_type: string;
		from_date: string;
		to_date: string;
	}): Promise<{ job_id: string; status: string }> {
		const res = await client.post('/mrd/exports', body);
		return res.data;
	},

	async listExports(): Promise<{ jobs: MrdExportJob[] }> {
		const res = await client.get('/mrd/exports');
		return res.data;
	},

	async getExport(jobId: string): Promise<MrdExportJob> {
		const res = await client.get(`/mrd/exports/${jobId}`);
		return res.data;
	},

	async getCensus(params: { from_date: string; to_date: string }): Promise<CensusData> {
		const res = await client.get('/mrd/census', { params });
		return res.data;
	},

	async getCensusPatients(params: {
		category: CensusCategory;
		from_date: string;
		to_date: string;
		department?: string;
		cursor?: string;
		page_size?: number;
	}): Promise<{ items: CensusPatient[]; total: number; category: string }> {
		const { category, ...rest } = params;
		const res = await client.get(`/mrd/census/${category}/patients`, { params: rest });
		return res.data;
	},

	async getDepartmentBreakdown(params: {
		from_date: string;
		to_date: string;
	}): Promise<DepartmentBreakdown> {
		const res = await client.get('/mrd/census/department-breakdown', { params });
		return res.data;
	},

	async getLabs(): Promise<{ labs: MrdLab[]; total: number }> {
		const res = await client.get('/mrd/labs');
		return res.data;
	},
};
