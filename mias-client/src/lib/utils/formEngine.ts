/**
 * FormEngine — pure, framework-agnostic conditional logic evaluator.
 *
 * Responsibilities:
 *   - Evaluate RuleCondition / CompoundCondition predicates against current values
 *   - Apply FormAction side-effects (show/hide/enable/disable/set_value/set_options)
 *   - Evaluate legacy per-field FieldCondition shortcuts
 *   - Build a dependency map for incremental re-evaluation
 *   - Detect circular references at construction time
 *
 * This module has zero UI coupling. It can be used from Svelte $derived,
 * React useMemo, Vue computed, or plain JS.
 */

import type {
	AnyCondition,
	CompoundCondition,
	ConditionOperator,
	FieldCondition,
	FormAction,
	FormFieldDefinition,
	FormRule,
	FormState,
	RuleCondition,
} from '$lib/types/forms';

// ─── Condition evaluation ────────────────────────────────────────────────────

function normalizeValue(v: any): string {
	if (v === null || v === undefined) return '';
	if (typeof v === 'boolean') return v ? 'yes' : 'no';
	return String(v).toLowerCase().trim();
}

function evaluateSingle(cond: RuleCondition, values: Record<string, any>): boolean {
	const raw = values[cond.field];
	const actual = normalizeValue(raw);
	const expected = normalizeValue(cond.value);
	const op: ConditionOperator = cond.operator;

	switch (op) {
		case 'equals':
			return actual === expected;
		case 'not_equals':
			return actual !== expected;
		case 'greater_than':
			return Number(raw) > Number(cond.value);
		case 'less_than':
			return Number(raw) < Number(cond.value);
		case 'greater_than_or_equal':
			return Number(raw) >= Number(cond.value);
		case 'less_than_or_equal':
			return Number(raw) <= Number(cond.value);
		case 'contains':
			return actual.includes(expected);
		case 'includes':
			return Array.isArray(raw) ? raw.map(normalizeValue).includes(expected) : actual.includes(expected);
		case 'empty':
			return raw === null || raw === undefined || raw === '' || (Array.isArray(raw) && raw.length === 0);
		case 'not_empty':
			return raw !== null && raw !== undefined && raw !== '' && !(Array.isArray(raw) && raw.length === 0);
		default:
			return true;
	}
}

function isCompound(cond: AnyCondition): cond is CompoundCondition {
	return 'and' in cond || 'or' in cond;
}

export function evaluateCondition(cond: AnyCondition, values: Record<string, any>): boolean {
	if (isCompound(cond)) {
		if (cond.and) return cond.and.every((c) => evaluateSingle(c, values));
		if (cond.or) return cond.or.some((c) => evaluateSingle(c, values));
		return true;
	}
	return evaluateSingle(cond as RuleCondition, values);
}

/** Legacy FieldCondition bridge — maps old shorthand operators to engine operators */
export function evaluateLegacyCondition(cond: FieldCondition, values: Record<string, any>): boolean {
	const opMap: Record<string, ConditionOperator> = {
		eq: 'equals',
		ne: 'not_equals',
		contains: 'contains',
		gt: 'greater_than',
		lt: 'less_than',
		gte: 'greater_than_or_equal',
		lte: 'less_than_or_equal',
		empty: 'empty',
		not_empty: 'not_empty',
	};
	return evaluateSingle(
		{ field: cond.field, operator: opMap[cond.operator] ?? 'equals', value: cond.value },
		values
	);
}

// ─── Dependency tracking ─────────────────────────────────────────────────────

function extractConditionFields(cond: AnyCondition): string[] {
	if (isCompound(cond)) {
		return [...(cond.and ?? []), ...(cond.or ?? [])].map((c) => c.field);
	}
	return [(cond as RuleCondition).field];
}

/** Maps each field key → set of rule indices that depend on it. O(rules) build. */
function buildDependencyMap(rules: FormRule[]): Map<string, Set<number>> {
	const map = new Map<string, Set<number>>();
	for (let i = 0; i < rules.length; i++) {
		for (const fieldKey of extractConditionFields(rules[i].if)) {
			if (!map.has(fieldKey)) map.set(fieldKey, new Set());
			map.get(fieldKey)!.add(i);
		}
	}
	return map;
}

/** Circular reference detection: collect all targets an action chain modifies */
function detectCircular(rules: FormRule[]): string | null {
	for (let i = 0; i < rules.length; i++) {
		const condFields = new Set(extractConditionFields(rules[i].if));
		const actionTargets = [...(rules[i].then ?? []), ...(rules[i].else ?? [])].map((a) => a.target);
		for (const target of actionTargets) {
			if (condFields.has(target)) {
				return `Rule[${i}]: condition reads "${target}" but then/else also writes to it — circular`;
			}
		}
	}
	return null;
}

// ─── Action application ──────────────────────────────────────────────────────

function applyActions(
	actions: FormAction[],
	state: { visibility: Record<string, boolean>; enabled: Record<string, boolean>; options: Record<string, string[]>; values: Record<string, any> }
): void {
	for (const act of actions) {
		switch (act.action) {
			case 'show':
				state.visibility[act.target] = true;
				break;
			case 'hide':
				state.visibility[act.target] = false;
				break;
			case 'enable':
				state.enabled[act.target] = true;
				break;
			case 'disable':
				state.enabled[act.target] = false;
				break;
			case 'set_value':
				state.values[act.target] = act.value;
				break;
			case 'set_options':
				if (Array.isArray(act.value)) state.options[act.target] = act.value;
				break;
		}
	}
}

// ─── Public API ───────────────────────────────────────────────────────────────

export interface FormEngineResult {
	/** Which field keys a changed field affects (for incremental updates) */
	affectedByField: (changedKey: string) => number[];
	/** Warning message if circular references detected */
	circularWarning: string | null;
	/**
	 * Compute full FormState from current values.
	 * Call this on every reactive value change (Svelte $derived, React useMemo, Vue computed).
	 */
	evaluate: (fields: FormFieldDefinition[], values: Record<string, any>) => FormState;
}

/**
 * Create a form engine instance from a set of rules.
 * Immutable — recreate when rules change.
 */
export function createFormEngine(rules: FormRule[] = []): FormEngineResult {
	const deps = buildDependencyMap(rules);
	const circularWarning = detectCircular(rules);

	return {
		circularWarning,

		affectedByField(changedKey: string): number[] {
			return [...(deps.get(changedKey) ?? [])];
		},

		evaluate(fields: FormFieldDefinition[], values: Record<string, any>): FormState {
			const visibility: Record<string, boolean> = {};
			const enabled: Record<string, boolean> = {};
			const options: Record<string, string[]> = {};
			const errors: Record<string, string> = {};

			// Defaults: evaluate legacy per-field conditions
			for (const field of fields) {
				if (field.condition) {
					visibility[field.key] = evaluateLegacyCondition(field.condition, values);
				} else {
					visibility[field.key] = true;
				}
				enabled[field.key] = true;
			}

			// Apply declarative rules (later rules win on conflict)
			const mutable = { visibility, enabled, options, values: { ...values } };
			for (const rule of rules) {
				const met = evaluateCondition(rule.if, values);
				applyActions(met ? rule.then : (rule.else ?? []), mutable);
			}

			return { values: mutable.values, visibility, enabled, options, errors };
		},
	};
}
