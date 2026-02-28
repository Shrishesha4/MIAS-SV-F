import client from './client';

export interface ICD10Code {
  code: string;
  description: string;
  category: string;
}

export interface Medicine {
  name: string;
  generic: string;
  category: string;
  common_dosages: string[];
  common_frequencies: string[];
  form: string;
  source?: string;
}

export interface DiagnosisSuggestion {
  text: string;
  icd_code: string | null;
  icd_description: string | null;
  category: string;
}

export const autocompleteApi = {
  async searchICD10(query: string, limit = 20): Promise<ICD10Code[]> {
    const response = await client.get('/autocomplete/icd10', {
      params: { q: query, limit },
    });
    return response.data;
  },

  async searchMedicines(query: string, limit = 20): Promise<Medicine[]> {
    const response = await client.get('/autocomplete/medicines', {
      params: { q: query, limit },
    });
    return response.data;
  },

  async getMedicineDetails(medicineName: string): Promise<Medicine> {
    const response = await client.get(`/autocomplete/medicine-details/${encodeURIComponent(medicineName)}`);
    return response.data;
  },

  async getFrequencies(): Promise<string[]> {
    const response = await client.get('/autocomplete/frequencies');
    return response.data;
  },

  async getDurations(): Promise<string[]> {
    const response = await client.get('/autocomplete/durations');
    return response.data;
  },

  async getDosageForms(): Promise<string[]> {
    const response = await client.get('/autocomplete/dosage-forms');
    return response.data;
  },

  async searchDiagnoses(query: string, limit = 20): Promise<DiagnosisSuggestion[]> {
    const response = await client.get('/autocomplete/diagnoses', {
      params: { q: query, limit },
    });
    return response.data;
  },
};
