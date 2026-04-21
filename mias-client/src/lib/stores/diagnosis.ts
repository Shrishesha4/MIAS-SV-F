import { writable, derived, get } from 'svelte/store';
import type { DiagnosisSuggestion, DiagnosisRequest } from '$lib/api/ai';
import { aiApi } from '$lib/api/ai';

const DEBOUNCE_MS = 1500;

interface DiagnosisStoreState {
	suggestions: DiagnosisSuggestion[];
	loading: boolean;
	error: string | null;
	lastAnalyzedAt: Date | null;
	debounceTimer: ReturnType<typeof setTimeout> | null;
	lastRequestKey: string | null;
}

function createDiagnosisStore() {
	let lastRequest: DiagnosisRequest | null = null;
	let latestRequestKey: string | null = null;

	const state = writable<DiagnosisStoreState>({
		suggestions: [],
		loading: false,
		error: null,
		lastAnalyzedAt: null,
		debounceTimer: null,
		lastRequestKey: null,
	});

	function generateRequestKey(request: DiagnosisRequest): string {
		return JSON.stringify({
			patient_id: request.patient_id,
			department: request.department,
			form_name: request.form_name,
			form_values: request.form_values,
			prior_diagnoses: request.prior_diagnoses,
			top_n: request.top_n,
		});
	}

	function cloneRequest(request: DiagnosisRequest): DiagnosisRequest {
		return {
			...request,
			form_values: JSON.parse(JSON.stringify(request.form_values ?? {})),
			prior_diagnoses: request.prior_diagnoses
				? JSON.parse(JSON.stringify(request.prior_diagnoses))
				: request.prior_diagnoses,
		};
	}

	async function analyze(request: DiagnosisRequest, options: { force?: boolean } = {}): Promise<void> {
		const nextRequest = cloneRequest(request);
		const requestKey = generateRequestKey(nextRequest);
		lastRequest = nextRequest;
		latestRequestKey = requestKey;

		// Cancel previous debounce
		const currentState = get(state);
		if (currentState.debounceTimer) {
			clearTimeout(currentState.debounceTimer);
		}

		// If same request as last time and not loading, skip
		if (!options.force && requestKey === currentState.lastRequestKey && !currentState.loading) {
			return;
		}

		// Set debounce
		const timer = setTimeout(async () => {
			// Update state to loading
			state.update((s) => ({
				...s,
				loading: true,
				error: null,
				debounceTimer: null,
				lastRequestKey: requestKey,
			}));

			try {
				const suggestions = await aiApi.getDiagnosisSuggestions(nextRequest);
				if (latestRequestKey !== requestKey) {
					return;
				}
				state.update((s) => ({
					...s,
					suggestions,
					loading: false,
					lastAnalyzedAt: new Date(),
				}));
			} catch (err: any) {
				if (latestRequestKey !== requestKey) {
					return;
				}
				state.update((s) => ({
					...s,
					loading: false,
					error: err?.response?.data?.detail || 'Failed to get diagnosis suggestions',
				}));
			}
		}, DEBOUNCE_MS);

		state.update((s) => ({
			...s,
			debounceTimer: timer,
		}));
	}

	function clearSuggestions(): void {
		const currentState = get(state);
		if (currentState.debounceTimer) {
			clearTimeout(currentState.debounceTimer);
		}

		lastRequest = null;
		latestRequestKey = null;

		state.update((s) => ({
			...s,
			suggestions: [],
			loading: false,
			error: null,
			lastAnalyzedAt: null,
			debounceTimer: null,
			lastRequestKey: null,
		}));
	}

	function retry(): void {
		if (lastRequest) {
			state.update((s) => ({
				...s,
				error: null,
			}));
			void analyze(lastRequest, { force: true });
		}
	}

	return {
		subscribe: state.subscribe,
		analyze,
		clearSuggestions,
		retry,
	};
}

export const diagnosisStore = createDiagnosisStore();

// Derived stores for convenience
export const hasSuggestions = derived(diagnosisStore, ($s) => $s.suggestions.length > 0);
export const hasError = derived(diagnosisStore, ($s) => $s.error !== null);
