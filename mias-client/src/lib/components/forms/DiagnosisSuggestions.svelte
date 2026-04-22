<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { diagnosisStore } from '$lib/stores/diagnosis';
	import type { DiagnosisRequest, DiagnosisSuggestion } from '$lib/api/ai';
	import { slide } from 'svelte/transition';

	interface Props {
		patientId: string;
		department?: string | null;
		formName?: string | null;
		formValues?: Record<string, unknown>;
		priorDiagnoses?: Array<Record<string, unknown>> | null;
		topN?: number;
		autoAnalyze?: boolean;
		onSuggestionSelect?: ((suggestion: DiagnosisSuggestion) => void) | undefined;
	}

	let {
		patientId,
		department = null,
		formName = null,
		formValues = {},
		priorDiagnoses = null,
		topN = 5,
		autoAnalyze = true,
		onSuggestionSelect = undefined,
	}: Props = $props();

	let suggestions = $state<DiagnosisSuggestion[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let lastAnalyzedAt = $state<Date | null>(null);
	let unsubscribe: (() => void) | null = null;

	function isMeaningfulValue(value: unknown): boolean {
		if (value === null || value === undefined) return false;
		if (typeof value === 'string') return value.trim().length > 0;
		if (Array.isArray(value)) return value.length > 0;
		if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0;
		return true;
	}

	function normalizeFormValue(value: unknown): unknown {
		if (value === null || value === undefined) return null;
		if (typeof value === 'string') {
			const trimmed = value.trim();
			return trimmed.length > 0 ? trimmed : null;
		}
		if (value instanceof Date) {
			return value.toISOString();
		}
		if (typeof File !== 'undefined' && value instanceof File) {
			return {
				name: value.name,
				type: value.type,
				size: value.size,
			};
		}
		if (typeof FileList !== 'undefined' && value instanceof FileList) {
			const files = Array.from(value).map((file) => normalizeFormValue(file)).filter(isMeaningfulValue);
			return files.length > 0 ? files : null;
		}
		if (Array.isArray(value)) {
			const items = value.map((item) => normalizeFormValue(item)).filter(isMeaningfulValue);
			return items.length > 0 ? items : null;
		}
		if (typeof value === 'object') {
			const normalizedEntries = Object.entries(value as Record<string, unknown>)
				.map(([key, item]) => [key, normalizeFormValue(item)] as const)
				.filter(([, item]) => isMeaningfulValue(item));
			return normalizedEntries.length > 0 ? Object.fromEntries(normalizedEntries) : null;
		}
		return value;
	}

	const sanitizedFormValues = $derived.by(() => {
		const nextValues: Record<string, unknown> = {};
		for (const [key, value] of Object.entries(formValues)) {
			const normalizedValue = normalizeFormValue(value);
			if (isMeaningfulValue(normalizedValue)) {
				nextValues[key] = normalizedValue;
			}
		}
		return nextValues;
	});

	const hasAnalyzableInput = $derived(Object.keys(sanitizedFormValues).length > 0);

	const request = $derived.by<DiagnosisRequest | null>(() => {
		if (!patientId) {
			return null;
		}

		return {
			patient_id: patientId,
			department,
			form_name: formName,
			form_values: sanitizedFormValues,
			prior_diagnoses: priorDiagnoses,
			top_n: topN,
		};
	});

	onMount(() => {
		unsubscribe = diagnosisStore.subscribe((state) => {
			suggestions = state.suggestions;
			loading = state.loading;
			error = state.error;
			lastAnalyzedAt = state.lastAnalyzedAt;
		});
	});

	onDestroy(() => {
		if (unsubscribe) unsubscribe();
		diagnosisStore.clearSuggestions();
	});

	$effect(() => {
		const nextRequest = request;

		if (!autoAnalyze) {
			return;
		}

		if (!nextRequest || !hasAnalyzableInput) {
			diagnosisStore.clearSuggestions();
			return;
		}

		void diagnosisStore.analyze(nextRequest);
	});

	function triggerAnalysis(): void {
		if (!request) {
			return;
		}

		void diagnosisStore.analyze(request, { force: true });
	}

	function handleSelect(suggestion: DiagnosisSuggestion): void {
		if (onSuggestionSelect !== undefined) {
			onSuggestionSelect(suggestion);
		}
	}

	function confidenceColor(confidence: number): string {
		if (confidence >= 80) return 'text-green-700';
		if (confidence >= 60) return 'text-yellow-700';
		return 'text-red-700';
	}

	function confidenceBarColor(confidence: number): string {
		if (confidence >= 80) return 'bg-green-500';
		if (confidence >= 60) return 'bg-yellow-500';
		return 'bg-red-500';
	}

	function formatTime(date: Date | null): string {
		if (!date) return '';
		return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	function buttonStyle(): string {
		return 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);';
	}

	function suggestionCardStyle(): string {
		return 'background-color: white; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 1px 2px rgba(0,0,0,0.05);';
	}
</script>

<div class="mb-3 flex items-center gap-2">
	<div
		class="inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium"
		style={autoAnalyze
			? 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white; border: 1px solid rgba(0,0,0,0.2); box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);'
			: buttonStyle()}
	>
		{#if loading}
			<svg class="w-3 h-3 animate-spin" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
			</svg>
			<span>{autoAnalyze ? 'Analyzing inline' : 'Analyzing...'}</span>
		{:else}
			<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
			</svg>
			<span>{autoAnalyze ? 'AI Diagnosis' : 'AI Diagnosis'}</span>
		{/if}
	</div>

	{#if !autoAnalyze}
		<button
			type="button"
			onclick={triggerAnalysis}
			disabled={loading || !patientId}
			class="px-3 py-1.5 text-xs font-medium rounded-md transition-all active:translate-y-0.5"
			style={buttonStyle()}
		>
			Run Analysis
		</button>
	{/if}

	{#if lastAnalyzedAt}
		<span class="text-[10px] text-gray-400">
			Last analyzed: {formatTime(lastAnalyzedAt)}
		</span>
	{:else if autoAnalyze}
		<span class="text-[10px] text-gray-400">
			Analyzes while you type
		</span>
	{/if}
</div>

<!-- Error Display -->
{#if error}
	<div class="mb-3 p-2 rounded-md text-xs" style="background-color: rgba(255,0,0,0.05); border: 1px solid rgba(220,50,50,0.2);">
		<div class="flex items-center gap-1 text-red-600 font-medium mb-1">
			<svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
			</svg>
			Diagnosis Error
		</div>
		<p class="text-red-500">{error}</p>
		<button
			type="button"
			onclick={() => diagnosisStore.retry()}
			class="mt-1 text-xs text-red-600 underline hover:text-red-700"
		>
			Retry
		</button>
	</div>
{/if}

<!-- Loading State -->
{#if loading && !suggestions.length}
	<div class="mb-3 p-3 rounded-md" style="background-color: rgba(0,0,0,0.02);">
		<div class="flex items-center gap-2">
			<svg class="w-4 h-4 animate-spin text-blue-600" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
			</svg>
			<span class="text-sm text-gray-600">AI is analyzing your form data...</span>
		</div>
	</div>
{/if}

{#if !loading && !error && !suggestions.length && !hasAnalyzableInput}
	<div class="mb-3 p-3 rounded-md text-xs text-gray-500" style="background-color: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.06);">
		Enter clinical findings, symptoms, or assessment fields to get AI diagnosis suggestions.
	</div>
{/if}

<!-- Suggestions List -->
{#if suggestions.length}
	<div class="mb-3 space-y-2">
		<div class="flex items-center justify-between mb-1">
			<span class="text-xs font-semibold text-blue-800">
				AI Diagnosis Suggestions
			</span>
			<span class="text-[10px] text-gray-400">
				{suggestions.length} suggestions
			</span>
		</div>

		{#each suggestions as suggestion, index (suggestion.disease)}
			<button
				type="button"
				class="w-full p-2 rounded-md cursor-pointer text-left transition-all hover:shadow-sm"
				style={suggestionCardStyle()}
				transition:slide={{ duration: 200, delay: index * 50 }}
				onclick={() => handleSelect(suggestion)}
			>
				<div class="flex items-start justify-between gap-2">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-1">
							<span class="text-xs font-bold text-gray-800">#{index + 1}</span>
							<span class="text-sm font-medium text-gray-800 truncate">
								{suggestion.disease}
							</span>
							{#if suggestion.icd_code}
								<span class="text-[10px] px-1 py-0.5 rounded text-gray-500" style="background-color: rgba(0,0,0,0.05);">
									{suggestion.icd_code}
								</span>
							{/if}
						</div>

						<!-- Confidence Bar -->
						<div class="w-full h-1.5 rounded-full mb-1" style="background-color: rgba(0,0,0,0.05);">
							<div
								class="h-full rounded-full transition-all"
								style="width: {suggestion.confidence}%; background-color: {confidenceBarColor(suggestion.confidence)};"
							></div>
						</div>

						<!-- Confidence and Reasoning -->
						<div class="flex items-center justify-between">
							<span class="text-xs font-semibold {confidenceColor(suggestion.confidence)}">
								{suggestion.confidence.toFixed(1)}% confidence
							</span>
						</div>

						<!-- Reasoning (collapsible) -->
						<div class="mt-1 text-[11px] text-gray-600 italic">
							{suggestion.reasoning}
						</div>
					</div>
				</div>
			</button>
		{/each}
	</div>
{/if}
