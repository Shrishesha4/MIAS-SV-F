import client from './client';

export interface AttendanceCounts {
	patients: number;
	students: number;
	faculty: number;
	nutritionists: number;
	nurses: number;
	reception: number;
	admins: number;
	total: number;
}

export interface AttendanceStatus {
	today: string;
	checked_in: boolean;
	checked_in_at: string | null;
	checked_out_at?: string | null;
	check_in_location?: string | null;
	check_out_location?: string | null;
	open_hour: number;
	role: string;
	skip_modal?: boolean;  // True when this role should not be blocked by the daily check-in modal
	counts: AttendanceCounts;
}

export interface AttendanceLogItem {
	id: string;
	user_id: string;
	username: string;
	email: string;
	role: string;
	check_in_date: string;
	checked_in_at: string | null;
	checked_out_at: string | null;
	check_in_location: string | null;
	check_out_location: string | null;
	clinic_id: string | null;
	clinic_name: string | null;
	currently_checked_in: boolean;
	duration_minutes: number | null;
}

export interface AttendanceLogsResponse {
	items: AttendanceLogItem[];
	total: number;
	limit: number;
	offset: number;
}

export const attendanceApi = {
	async getTodayStatus(): Promise<AttendanceStatus> {
		return (await client.get('/attendance/today')).data;
	},

	async checkInToday(clinicId?: string, location?: string): Promise<AttendanceStatus> {
		return (await client.post('/attendance/check-in', { clinic_id: clinicId, location })).data;
	},

	async checkOutToday(location?: string): Promise<AttendanceStatus> {
		return (await client.post('/attendance/check-out', { location })).data;
	},

	async getLogs(params?: {
		role?: string;
		targetDate?: string;
		query?: string;
		checkedInOnly?: boolean;
		checkedOutOnly?: boolean;
		limit?: number;
		offset?: number;
	}): Promise<AttendanceLogsResponse> {
		const searchParams = new URLSearchParams();
		if (params?.role) searchParams.set('role', params.role);
		if (params?.targetDate) searchParams.set('target_date', params.targetDate);
		if (params?.query) searchParams.set('query', params.query);
		if (params?.checkedInOnly) searchParams.set('checked_in_only', 'true');
		if (params?.checkedOutOnly) searchParams.set('checked_out_only', 'true');
		if (params?.limit != null) searchParams.set('limit', String(params.limit));
		if (params?.offset != null) searchParams.set('offset', String(params.offset));

		const query = searchParams.toString();
		return (await client.get(`/attendance/logs${query ? `?${query}` : ''}`)).data;
	}
};
