import client from './client';
import type { Report } from './types';

export const reportsApi = {
	async getReport(reportId: string): Promise<Report> {
		const response = await client.get(`/reports/${reportId}`);
		return response.data;
	},
};