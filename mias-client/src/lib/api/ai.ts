import client from './client';
import type { Patient } from './types';

export interface DiagnosisSuggestion {
	disease: string;
	confidence: number;
	reasoning: string;
	icd_code: string;
}

export interface DiagnosisRequest {
	patient_id: string;
	department?: string | null;
	form_name?: string | null;
	form_values: Record<string, any>;
	prior_diagnoses?: Array<Record<string, any>> | null;
	top_n?: number;
}

export interface DiagnosisState {
	suggestions: DiagnosisSuggestion[];
	loading: boolean;
	error: string | null;
	lastAnalyzedAt: Date | null;
}

export const aiApi = {
	async getDiagnosisSuggestions(request: DiagnosisRequest): Promise<DiagnosisSuggestion[]> {
		const response = await client.post<DiagnosisSuggestion[]>('/ai/diagnose', request);
		return response.data;
	},

	async testConnection(): Promise<boolean> {
		try {
			const response = await client.post('/ai/diagnose', {
				patient_id: 'test',
				form_values: { test: 'test' },
				top_n: 1,
			});
			return response.status === 200;
		} catch {
			return false;
		}
	},
};
