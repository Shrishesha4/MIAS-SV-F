import client from './client';

export interface AttendanceCounts {
	patients: number;
	students: number;
	faculty: number;
	nurses: number;
	reception: number;
	admins: number;
	total: number;
}

export interface AttendanceStatus {
	today: string;
	checked_in: boolean;
	checked_in_at: string | null;
	open_hour: number;
	role: string;
	skip_modal?: boolean;  // True when this role should not be blocked by the daily check-in modal
	counts: AttendanceCounts;
}

export const attendanceApi = {
	async getTodayStatus(): Promise<AttendanceStatus> {
		return (await client.get('/attendance/today')).data;
	},

	async checkInToday(clinicId?: string): Promise<AttendanceStatus> {
		return (await client.post('/attendance/check-in', { clinic_id: clinicId })).data;
	}
};
