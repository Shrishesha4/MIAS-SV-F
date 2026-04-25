<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { formsApi, type FormDefinitionPayload } from '$lib/api/forms';
	import DynamicFormRenderer from '$lib/components/forms/DynamicFormRenderer.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import type { FormCategory, FormDefinition, FormFieldDefinition, FormRule, FormSection, FormFieldType, FieldCondition } from '$lib/types/forms';
	import { toastStore } from '$lib/stores/toast';
	import { FileText, GripVertical, Icon, Loader2, Pencil, Plus, Power, RotateCcw, Settings, Sparkles, Trash2, X } from 'lucide-svelte';
	import IconPicker from '$lib/components/ui/IconPicker.svelte';
	import TabBar from '$lib/components/ui/TabBar.svelte';
	import { LUCIDE_ICONS } from '$lib/data/lucideIcons';

	const auth = get(authStore);

	// Portal action: moves node to document.body to escape any stacking context
	function portal(node: HTMLElement): { destroy(): void } {
		document.body.appendChild(node);
		return {
			destroy() {
				if (node.parentNode === document.body) {
					document.body.removeChild(node);
				}
			}
		};
	}
	const hiddenSections: FormSection[] = ['LABORATORY'];
	const defaultSections: FormSection[] = ['ADMISSION', 'CLINICAL', 'ADMINISTRATIVE'];
	const fieldTypes: FormFieldType[] = ['textarea', 'text', 'number', 'select', 'date', 'file', 'email', 'password', 'tel', 'diagnosis', 'department_select', 'faculty_select', 'clinic_select'];

	const fieldTypeLabels: Record<string, string> = {
		department_select: 'DEPARTMENT (DB)',
		faculty_select: 'FACULTY (DB)',
		clinic_select: 'CLINIC (DB)',
	};
	const legacyTypeToSection: Record<string, FormSection> = {
		CASE_RECORD: 'CLINICAL',
		ADMISSION: 'ADMISSION',
		ADMISSION_REQUEST: 'ADMISSION',
		ADMISSION_INTAKE: 'ADMISSION',
		ADMISSION_DISCHARGE: 'ADMISSION',
		ADMISSION_TRANSFER: 'ADMISSION',
		PRESCRIPTION: 'CLINICAL',
		PRESCRIPTION_CREATE: 'CLINICAL',
		PRESCRIPTION_EDIT: 'CLINICAL',
		PRESCRIPTION_REQUEST: 'CLINICAL',
		VITAL_ENTRY: 'CLINICAL',
		LABORATORY: 'LABORATORY',
		LAB: 'LABORATORY',
		LABS: 'LABORATORY',
		PROFILE: 'ADMINISTRATIVE',
		PROFILE_EDIT: 'ADMINISTRATIVE',
		CUSTOM: 'ADMINISTRATIVE',
		ADMINISTRATIVE: 'ADMINISTRATIVE'
	};

	let loadingForms = $state(true);
	let formDefinitions: FormDefinition[] = $state([]);
	let formCategories: FormCategory[] = $state([]);
	let activeSection = $state<FormSection>('ADMISSION');

	let showFormEditor = $state(false);
	let editingFormId: string | null = $state(null);
	let formEditorSection = $state<FormSection>('ADMISSION');
	let formEditorType = $state('');
	let formEditorName = $state('');
	let formEditorSortOrder = $state(0);
	let formEditorIsActive = $state(true);
	let formEditorIcon = $state('');
	let showIconPicker = $state(false);
	let formEditorColor = $state('');
	let formEditorAllowedRoles: string[] = $state([]);
	let formEditorDepartment = $state('');
	let formEditorProcedureName = $state('');
	let formEditorFields: FormFieldDefinition[] = $state([]);
	let formEditorRules: FormRule[] = $state([]);
	let selectedFieldIndex = $state(0);
	let previewValues = $state<Record<string, any>>({});
	let isEditingFormName = $state(false);
	let formNameInput = $state<HTMLInputElement | null>(null);
	let savingForm = $state(false);
	let savingSettings = $state(false);
	let formSaveError = $state('');
	let settingsSaveError = $state('');
	let showFormSettingsModal = $state(false);
	let showCategoryEditor = $state(false);
	let categoryName = $state('');
	let savingCategory = $state(false);
	let categorySaveError = $state('');
	let categoryMenu = $state<{ x: number; y: number; category: FormCategory } | null>(null);
	let draggedFieldIndex = $state<number | null>(null);
	let dragOverFieldIndex = $state<number | null>(null);
	let draggedOptionIndex = $state<number | null>(null);
	let dragOverOptionIndex = $state<number | null>(null);

	let showGeneratePrompt = $state(false);
	let generateDescription = $state('');
	let generating = $state(false);
	let generateError = $state('');
	let generateContext = $state<'studio' | 'settings'>('studio');

	const selectedField = $derived(formEditorFields[selectedFieldIndex] ?? null);
	const hasGeneratedDraft = $derived(formEditorFields.some((field) => field.label.trim() || field.key.trim()));
	const previewSchema = $derived.by(() => {
		const serializedFields = serializeFields(formEditorFields);
		const duplicateKeys = new Set<string>();
		const seenKeys = new Set<string>();
		const previewKeyCounts = new Map<string, number>();
		const firstPreviewKeyBySerializedKey = new Map<string, string>();

		const previewKeys = serializedFields.map((field, index) => {
			const baseKey = field.key || `field_${index + 1}`;
			if (seenKeys.has(baseKey)) {
				duplicateKeys.add(baseKey);
			} else {
				seenKeys.add(baseKey);
			}

			const currentCount = previewKeyCounts.get(baseKey) ?? 0;
			const previewKey = currentCount === 0 ? baseKey : `${baseKey}_${currentCount + 1}`;
			previewKeyCounts.set(baseKey, currentCount + 1);
			if (!firstPreviewKeyBySerializedKey.has(baseKey)) {
				firstPreviewKeyBySerializedKey.set(baseKey, previewKey);
			}
			return previewKey;
		});

		return {
			duplicates: [...duplicateKeys],
			fields: serializedFields.map((field, index) => ({
				...field,
				key: previewKeys[index],
				label: field.label || `Untitled field ${index + 1}`,
				condition: field.condition
					? {
						...field.condition,
						field: firstPreviewKeyBySerializedKey.get(field.condition.field) ?? field.condition.field,
					}
					: undefined,
			})),
		};
	});

	const sectionTabs = $derived.by(() => {
		const activeCategories = [...formCategories]
			.filter((category) => category.is_active)
			.filter((category) => !hiddenSections.includes(category.name.toUpperCase()))
			.sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
		return activeCategories.length > 0 ? activeCategories.map((category) => category.name) : defaultSections;
	});

	const sectionTabItems = $derived(sectionTabs.map((s) => ({ id: s, label: s })));

	const filteredForms = $derived.by(() => {
		return formDefinitions.filter((form) => resolveFormSection(form) === activeSection);
	});

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		loadFormStudio();
	});

	function openCategoryContextMenu(event: MouseEvent, section: FormSection) {
		event.preventDefault();
		const category = formCategories.find((item) => item.name === section);
		if (!category || category.is_system) {
			categoryMenu = null;
			return;
		}
		categoryMenu = { x: event.clientX, y: event.clientY, category };
	}

	async function deleteCategoryFromMenu() {
		if (!categoryMenu) return;
		const target = categoryMenu.category;
		categoryMenu = null;
		try {
			await formsApi.deleteFormCategory(target.id);
			formCategories = sortFormCategories(formCategories.filter((item) => item.id !== target.id));
			syncActiveSection(formCategories);
			await loadFormStudio();
			toastStore.addToast('Form category deleted', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete form category', 'error');
		}
	}

	async function toggleCategoryActiveFromMenu() {
		if (!categoryMenu) return;
		const target = categoryMenu.category;
		categoryMenu = null;
		try {
			const updated = await formsApi.updateFormCategory(target.id, {
				is_active: !target.is_active,
			});
			formCategories = sortFormCategories(
				formCategories.map((item) => (item.id === updated.id ? updated : item))
			);
			syncActiveSection(formCategories);
			toastStore.addToast(`Form category ${updated.is_active ? 'enabled' : 'disabled'}`, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to update form category', 'error');
		}
	}

	function resolveFormSection(form: Pick<FormDefinition, 'section' | 'form_type'>): FormSection {
		const explicitSection = form.section?.toString().toUpperCase();
		if (explicitSection) {
			return explicitSection;
		}
		return legacyTypeToSection[form.form_type?.toString().toUpperCase() || ''] || 'ADMINISTRATIVE';
	}

	function sortFormCategories(categories: FormCategory[]): FormCategory[] {
		return [...categories].sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name));
	}

	function syncActiveSection(categories: FormCategory[]) {
		const activeCategories = sortFormCategories(categories)
			.filter((category) => category.is_active)
			.filter((category) => !hiddenSections.includes(category.name.toUpperCase()));
		if (activeCategories.length === 0) {
			activeSection = defaultSections[0];
			return;
		}
		if (!activeCategories.some((category) => category.name === activeSection)) {
			activeSection = activeCategories[0].name;
		}
	}

	function slugify(value: string) {
		return value
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, '_')
			.replace(/^_+|_+$/g, '');
	}

	function normalizeFieldType(type: string | undefined): FormFieldType {
		const normalized = (type || '').toLowerCase();
		return fieldTypes.includes(normalized as FormFieldType) ? (normalized as FormFieldType) : 'text';
	}

	function createEmptyField(): FormFieldDefinition {
		return {
			key: '',
			label: '',
			type: 'textarea',
			required: false,
			placeholder: ''
		};
	}

	function normalizeGeneratedField(field: Partial<FormFieldDefinition>): FormFieldDefinition {
		return {
			key: slugify(field.key || field.label || ''),
			label: String(field.label || '').trim(),
			type: normalizeFieldType(field.type),
			required: Boolean(field.required),
			placeholder: String(field.placeholder || ''),
			options: Array.isArray(field.options) ? [...field.options] : [],
			rows: typeof field.rows === 'number' ? field.rows : undefined,
			accept: field.accept || undefined,
			multiple: Boolean(field.multiple),
			help_text: String(field.help_text || ''),
			condition: field.condition
				? {
					field: String(field.condition.field || '').trim(),
					operator: field.condition.operator,
					...(field.condition.value !== undefined ? { value: field.condition.value } : {})
				}
				: undefined,
		};
	}

	function isGeneratedPatientIdentityField(field: Partial<FormFieldDefinition>): boolean {
		const key = slugify(field.key || '');
		const label = String(field.label || '')
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, ' ')
			.replace(/\s+/g, ' ');
		return ['patient_id', 'patient_name', 'patient_dob', 'patient_date_of_birth', 'date_of_birth', 'dob'].includes(key)
			|| ['patient id', 'patient name', 'patient dob', 'patient date of birth', 'date of birth', 'dob'].includes(label);
	}

	function isGeneratedInstructionalField(field: Partial<FormFieldDefinition>): boolean {
		const key = slugify(field.key || '');
		const label = String(field.label || '')
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, ' ')
			.replace(/\s+/g, ' ');
		const placeholder = String(field.placeholder || '')
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, ' ')
			.replace(/\s+/g, ' ');
		const helpText = String(field.help_text || '')
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, ' ')
			.replace(/\s+/g, ' ');
		const combined = [label, placeholder, helpText].filter(Boolean).join(' ');
		return ['generate_', 'calculate_', 'submit_', 'save_', 'print_', 'export_'].some((prefix) => key.startsWith(prefix))
			|| ['generate ', 'calculate ', 'submit ', 'save ', 'print ', 'export '].some((prefix) => label.startsWith(prefix))
			|| [
				'clicking this will',
				'this will trigger',
				'trigger the generation',
				'generate differential diagnosis',
				'generate diagnosis',
				'ai generated',
			].some((marker) => combined.includes(marker));
	}

	function sanitizeGeneratedCondition(
		condition: FormFieldDefinition['condition'],
		validKeys: Set<string>
	): FormFieldDefinition['condition'] {
		if (!condition?.field) {
			return undefined;
		}
		const operator = condition.operator;
		const field = condition.field.trim();
		const requiresValue = operator !== 'empty' && operator !== 'not_empty';
		const hasValue = condition.value !== undefined && condition.value !== null && condition.value !== '';
		if (!validKeys.has(field) || (requiresValue && !hasValue)) {
			return undefined;
		}
		return requiresValue ? { field, operator, value: condition.value } : { field, operator };
	}

	function mergeGeneratedFields(
		currentFields: FormFieldDefinition[],
		generatedFields: FormFieldDefinition[]
	): FormFieldDefinition[] {
		const merged = currentFields.map((field) => normalizeGeneratedField(field));
		const keyAliases = new Map<string, string>();
		const keyIndex = new Map<string, number>();
		const labelIndex = new Map<string, number>();

		function registerField(field: FormFieldDefinition, index: number) {
			if (field.key) {
				keyIndex.set(field.key, index);
			}
			const normalizedLabel = slugify(field.label || '');
			if (normalizedLabel) {
				labelIndex.set(normalizedLabel, index);
			}
		}

		merged.forEach(registerField);

		for (const incomingField of generatedFields.map((field) => normalizeGeneratedField(field))) {
			const matchedIndex = keyIndex.get(incomingField.key) ?? labelIndex.get(slugify(incomingField.label || ''));
			if (matchedIndex === undefined) {
				merged.push(incomingField);
				registerField(incomingField, merged.length - 1);
				continue;
			}

			const currentField = merged[matchedIndex];
			const preservedKey = currentField.key || incomingField.key;
			if (incomingField.key && incomingField.key !== preservedKey) {
				keyAliases.set(incomingField.key, preservedKey);
			}
			const incomingOptions = incomingField.options ?? [];
			const currentOptions = currentField.options ?? [];

			const nextField: FormFieldDefinition = {
				...currentField,
				...incomingField,
				key: preservedKey,
				options: incomingField.type === 'select'
					? (incomingOptions.length > 0 ? [...incomingOptions] : [...currentOptions])
					: [...incomingOptions],
				condition: incomingField.condition ?? currentField.condition,
			};
			merged[matchedIndex] = nextField;
			registerField(nextField, matchedIndex);
		}

		const validKeys = new Set(merged.map((field) => field.key).filter(Boolean));
		return merged.map((field) => ({
			...field,
			condition: sanitizeGeneratedCondition(
				field.condition
					? {
						...field.condition,
						field: keyAliases.get(field.condition.field) ?? field.condition.field,
					}
					: undefined,
				validKeys
			),
		}));
	}

	async function loadFormStudio() {
		loadingForms = true;
		try {
			const [forms, categories] = await Promise.all([
				formsApi.getForms({ include_inactive: true }),
				formsApi.getFormCategories(),
			]);
			formDefinitions = forms;
			formCategories = sortFormCategories(categories);
			syncActiveSection(categories);
		} catch {
			toastStore.addToast('Failed to load forms', 'error');
		} finally {
			loadingForms = false;
		}
	}

	function resetFormEditor() {
		showFormEditor = false;
		editingFormId = null;
		formEditorSection = activeSection;
		formEditorType = '';
		formEditorName = '';
		formEditorSortOrder = 0;
		formEditorIsActive = true;
		formEditorIcon = '';
		formEditorColor = '';
		formEditorAllowedRoles = [];
		formEditorDepartment = '';
		formEditorProcedureName = '';
		formEditorFields = [];
		formEditorRules = [];
		selectedFieldIndex = 0;
		previewValues = {};
		isEditingFormName = false;
		formSaveError = '';
		resetFieldDragState();
		resetOptionDragState();
	}

	function resetCategoryEditor() {
		showCategoryEditor = false;
		categoryName = '';
		categorySaveError = '';
	}

	function openCreateFormEditor(section: FormSection = activeSection) {
		resetFormEditor();
		formEditorSection = section;
		formEditorType = section;
		activeSection = section;
		showFormEditor = true;
		addFormField();
	}

	function openCategoryEditor() {
		resetCategoryEditor();
		showCategoryEditor = true;
	}

	function openEditFormEditor(form: FormDefinition) {
		resetFormEditor();
		editingFormId = form.id;
		formEditorSection = resolveFormSection(form);
		formEditorType = form.form_type;
		formEditorName = form.name;
		formEditorSortOrder = form.sort_order || 0;
		formEditorIsActive = form.is_active;
		formEditorIcon = form.icon || '';
		formEditorColor = form.color || '';
		formEditorAllowedRoles = form.allowed_roles ? [...form.allowed_roles] : [];
		formEditorDepartment = form.department || '';
		formEditorProcedureName = form.procedure_name || '';
		formEditorFields = (form.fields.length > 0 ? form.fields : [createEmptyField()]).map((field) => ({
			...field,
			type: normalizeFieldType(field.type)
		}));
		formEditorRules = form.rules ? [...form.rules] : [];
		selectedFieldIndex = 0;
		previewValues = {};
		activeSection = formEditorSection;
		showFormEditor = true;
	}

	function openSettingsOnly(form: FormDefinition) {
		resetFormEditor();
		editingFormId = form.id;
		formEditorSection = resolveFormSection(form);
		formEditorType = form.form_type;
		formEditorName = form.name;
		formEditorSortOrder = form.sort_order || 0;
		formEditorIsActive = form.is_active;
		formEditorIcon = form.icon || '';
		formEditorColor = form.color || '';
		formEditorAllowedRoles = form.allowed_roles ? [...form.allowed_roles] : [];
		formEditorDepartment = form.department || '';
		formEditorProcedureName = form.procedure_name || '';
		formEditorFields = (form.fields.length > 0 ? form.fields : [createEmptyField()]).map((field) => ({
			...field,
			type: normalizeFieldType(field.type)
		}));
		formEditorRules = form.rules ? [...form.rules] : [];
		selectedFieldIndex = 0;
		previewValues = {};
		activeSection = formEditorSection;
		// do NOT set showFormEditor = true — only open settings
		settingsSaveError = '';
		showFormSettingsModal = true;
	}

	function addFormField() {
		const nextFields = [...formEditorFields, createEmptyField()];
		formEditorFields = nextFields;
		selectedFieldIndex = nextFields.length - 1;
	}

	function removeFormField(index: number) {
		resetFieldDragState();
		resetOptionDragState();
		const nextFields = formEditorFields.filter((_, fieldIndex) => fieldIndex !== index);
		if (nextFields.length === 0) {
			formEditorFields = [createEmptyField()];
			selectedFieldIndex = 0;
			return;
		}

		formEditorFields = nextFields;
		if (selectedFieldIndex > index) {
			selectedFieldIndex -= 1;
		} else if (selectedFieldIndex === index) {
			selectedFieldIndex = Math.max(0, index - 1);
		}
	}

	function moveFormField(fromIndex: number, toIndex: number) {
		if (
			fromIndex === toIndex ||
			fromIndex < 0 ||
			toIndex < 0 ||
			fromIndex >= formEditorFields.length ||
			toIndex >= formEditorFields.length
		) {
			return;
		}

		const nextFields = [...formEditorFields];
		const [movedField] = nextFields.splice(fromIndex, 1);
		nextFields.splice(toIndex, 0, movedField);
		formEditorFields = nextFields;

		if (selectedFieldIndex === fromIndex) {
			selectedFieldIndex = toIndex;
			return;
		}

		if (fromIndex < selectedFieldIndex && toIndex >= selectedFieldIndex) {
			selectedFieldIndex -= 1;
			return;
		}

		if (fromIndex > selectedFieldIndex && toIndex <= selectedFieldIndex) {
			selectedFieldIndex += 1;
		}
	}

	function resetFieldDragState() {
		draggedFieldIndex = null;
		dragOverFieldIndex = null;
	}

	function handleFieldDragStart(event: DragEvent, index: number) {
		draggedFieldIndex = index;
		dragOverFieldIndex = index;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.dropEffect = 'move';
			event.dataTransfer.setData('text/plain', String(index));
		}
	}

	function handleFieldDragOver(event: DragEvent, index: number) {
		event.preventDefault();
		dragOverFieldIndex = index;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleFieldDrop(event: DragEvent, index: number) {
		event.preventDefault();
		const fromIndex = draggedFieldIndex;
		resetFieldDragState();
		if (fromIndex === null) {
			return;
		}
		moveFormField(fromIndex, index);
	}

	function patchField(index: number, nextField: FormFieldDefinition) {
		formEditorFields = formEditorFields.map((field, fieldIndex) => (fieldIndex === index ? nextField : field));
	}

	function updateFieldLabel(index: number, label: string) {
		const field = formEditorFields[index];
		const previousAutoKey = slugify(field.label || '');
		const nextField = { ...field, label };
		if (!field.key || field.key === previousAutoKey) {
			nextField.key = slugify(label);
		}
		patchField(index, nextField);
	}

	function updateFieldType(index: number, type: string) {
		const field = formEditorFields[index];
		const nextField: FormFieldDefinition = { ...field, type: normalizeFieldType(type) };
		if (nextField.type === 'select') {
			nextField.options = field.options && field.options.length > 0 ? [...field.options] : [''];
		} else {
			nextField.options = [];
			resetOptionDragState();
		}
		if (nextField.type !== 'textarea') {
			nextField.rows = undefined;
		}
		if (nextField.type !== 'file') {
			nextField.accept = undefined;
			nextField.multiple = false;
		}
		patchField(index, nextField);
	}

	function updateFieldKey(index: number, key: string) {
		patchField(index, { ...formEditorFields[index], key: slugify(key) });
	}

	function updateFieldProperty<K extends keyof FormFieldDefinition>(index: number, property: K, value: FormFieldDefinition[K]) {
		patchField(index, { ...formEditorFields[index], [property]: value } as FormFieldDefinition);
	}

	function getEditorFieldId(field: FormFieldDefinition, index: number): string {
		return `${getEffectiveKey(field, index)}__${index}`;
	}

	function updateFieldRequired(index: number, required: boolean) {
		patchField(index, { ...formEditorFields[index], required });
	}

	function sanitizeOptionList(options: string[] | undefined): string[] {
		return (options ?? []).map((option) => option.trim()).filter(Boolean);
	}

	function updateFieldOptions(index: number, options: string[]) {
		patchField(index, { ...formEditorFields[index], options });
	}

	function addFieldOption(index: number) {
		updateFieldOptions(index, [...(formEditorFields[index].options ?? []), '']);
	}

	function updateFieldOption(index: number, optionIndex: number, value: string) {
		const options = [...(formEditorFields[index].options ?? [])];
		options[optionIndex] = value;
		updateFieldOptions(index, options);
	}

	function removeFieldOption(index: number, optionIndex: number) {
		const options = (formEditorFields[index].options ?? []).filter((_, currentIndex) => currentIndex !== optionIndex);
		updateFieldOptions(index, options);
		resetOptionDragState();
	}

	function moveFieldOption(index: number, fromIndex: number, toIndex: number) {
		const options = [...(formEditorFields[index].options ?? [])];
		if (
			fromIndex === toIndex ||
			fromIndex < 0 ||
			toIndex < 0 ||
			fromIndex >= options.length ||
			toIndex >= options.length
		) {
			return;
		}

		const [movedOption] = options.splice(fromIndex, 1);
		options.splice(toIndex, 0, movedOption);
		updateFieldOptions(index, options);
	}

	function resetOptionDragState() {
		draggedOptionIndex = null;
		dragOverOptionIndex = null;
	}

	function handleOptionDragStart(event: DragEvent, optionIndex: number) {
		draggedOptionIndex = optionIndex;
		dragOverOptionIndex = optionIndex;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.dropEffect = 'move';
			event.dataTransfer.setData('text/plain', String(optionIndex));
		}
	}

	function handleOptionDragOver(event: DragEvent, optionIndex: number) {
		event.preventDefault();
		dragOverOptionIndex = optionIndex;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleOptionDrop(event: DragEvent, fieldIndex: number, optionIndex: number) {
		event.preventDefault();
		const fromIndex = draggedOptionIndex;
		resetOptionDragState();
		if (fromIndex === null) {
			return;
		}
		moveFieldOption(fieldIndex, fromIndex, optionIndex);
	}

	function updateFieldCondition(index: number, condition: FormFieldDefinition['condition']) {
		patchField(index, { ...formEditorFields[index], condition });
	}

	function getEffectiveKey(field: FormFieldDefinition, idx: number): string {
		return field.key?.trim() || slugify(field.label) || `field_${idx + 1}`;
	}

	function getAvailableConditionFields(currentIndex: number) {
		return formEditorFields.slice(0, currentIndex).map((f, idx) => ({
			key: f.key || getEffectiveKey(f, idx),
			label: f.label || f.key || `Field ${idx + 1}`,
			type: f.type,
			options: f.type === 'select' ? sanitizeOptionList(f.options) : []
		}));
	}

	function updateFieldConditionField(index: number, fieldKey: string) {
		const field = formEditorFields[index];
		updateFieldCondition(index, { field: fieldKey, operator: field.condition?.operator || 'not_empty' });
	}

	function updateFieldConditionOperator(index: number, operator: FieldCondition['operator']) {
		const field = formEditorFields[index];
		const next: FieldCondition = { field: field.condition?.field || '', operator };
		if (operator !== 'empty' && operator !== 'not_empty') next.value = field.condition?.value ?? '';
		updateFieldCondition(index, next);
	}

	function updateFieldConditionValue(index: number, value: string) {
		const field = formEditorFields[index];
		updateFieldCondition(index, { ...field.condition, field: field.condition?.field || '', operator: field.condition?.operator || 'not_empty', value });
	}

	function clearFieldCondition(index: number) {
		const nextField = { ...formEditorFields[index] };
		delete nextField.condition;
		patchField(index, nextField);
	}

	function serializeFields(fields: FormFieldDefinition[] = formEditorFields) {
		const finalKeys = fields.map((field, index) => field.key?.trim() || slugify(field.label) || `field_${index + 1}`);

		const keyMap = new Map<string, string>();
		fields.forEach((field, index) => {
			const finalKey = finalKeys[index];
			const rawKey = field.key?.trim();
			const autoKey = slugify(field.label || '');
			if (rawKey) keyMap.set(rawKey, finalKey);
			if (autoKey) keyMap.set(autoKey, finalKey);
			keyMap.set(`field_${index + 1}`, finalKey);
		});

		return fields.map((field, index) => {
			const condition = field.condition
				? {
					...field.condition,
					field: keyMap.get(field.condition.field) ?? field.condition.field,
				  }
				: undefined;

			return {
				...field,
				type: normalizeFieldType(field.type),
				key: finalKeys[index],
				label: field.label.trim(),
				options: field.type === 'select' ? sanitizeOptionList(field.options) : field.options,
				placeholder: field.placeholder || undefined,
				help_text: field.help_text || undefined,
				accept: field.accept || undefined,
				rows: field.rows || undefined,
				multiple: field.multiple || false,
				required: field.required || false,
				condition,
			};
		});
	}

	async function saveFormDefinition() {
		if (!formEditorName.trim()) {
			formSaveError = 'Form name is required';
			return;
		}

		const nextFields = serializeFields();
		if (nextFields.length === 0) {
			formSaveError = 'At least one field is required';
			return;
		}

		const invalidField = nextFields.find((field) => !field.label || !field.key);
		if (invalidField) {
			formSaveError = 'Every field needs a label';
			return;
		}

		const seenKeys = new Set<string>();
		const duplicateKeys = new Set<string>();
		for (const field of nextFields) {
			if (seenKeys.has(field.key)) {
				duplicateKeys.add(field.key);
			} else {
				seenKeys.add(field.key);
			}
		}
		if (duplicateKeys.size > 0) {
			formSaveError = `Field keys must be unique: ${[...duplicateKeys].join(', ')}`;
			return;
		}

		const payload: FormDefinitionPayload = {
			name: formEditorName.trim(),
			section: formEditorSection,
			form_type: formEditorType || formEditorSection,
			department: formEditorDepartment.trim() || undefined,
			procedure_name: formEditorProcedureName.trim() || undefined,
			fields: nextFields,
			rules: formEditorRules.length > 0 ? formEditorRules : undefined,
			sort_order: formEditorSortOrder,
			is_active: formEditorIsActive,
			icon: formEditorIcon.trim() || null,
			color: formEditorColor.trim() || null,
			allowed_roles: formEditorAllowedRoles.length > 0 ? formEditorAllowedRoles : null,
		};

		savingForm = true;
		formSaveError = '';
		try {
			if (editingFormId) {
				await formsApi.updateForm(editingFormId, payload);
				toastStore.addToast('Configuration updated', 'success');
			} else {
				await formsApi.createForm(payload);
				toastStore.addToast('Configuration created', 'success');
			}
			resetFormEditor();
			await loadFormStudio();
		} catch (error: any) {
			formSaveError = error?.response?.data?.detail || 'Failed to save configuration';
		} finally {
			savingForm = false;
		}
	}

	async function saveFormSettings() {
		if (!editingFormId) return;
		if (!formEditorName.trim()) {
			settingsSaveError = 'Form name is required';
			return;
		}
		const nextFields = serializeFields();
		if (nextFields.length === 0) {
			settingsSaveError = 'Form must have at least one field';
			return;
		}
		const payload: FormDefinitionPayload = {
			name: formEditorName.trim(),
			section: formEditorSection,
			form_type: formEditorType || formEditorSection,
			department: formEditorDepartment.trim() || undefined,
			procedure_name: formEditorProcedureName.trim() || undefined,
			fields: nextFields,
			rules: formEditorRules.length > 0 ? formEditorRules : undefined,
			sort_order: formEditorSortOrder,
			is_active: formEditorIsActive,
			icon: formEditorIcon.trim() || null,
			color: formEditorColor.trim() || null,
			allowed_roles: formEditorAllowedRoles.length > 0 ? formEditorAllowedRoles : null,
		};
		savingSettings = true;
		settingsSaveError = '';
		try {
			await formsApi.updateForm(editingFormId, payload);
			toastStore.addToast('Settings saved', 'success');
			showFormSettingsModal = false;
			await loadFormStudio();
		} catch (error: any) {
			settingsSaveError = error?.response?.data?.detail || 'Failed to save settings';
		} finally {
			savingSettings = false;
		}
	}

	async function saveFormCategory() {
		if (!categoryName.trim()) {
			categorySaveError = 'Category name is required';
			return;
		}

		savingCategory = true;
		categorySaveError = '';
		try {
			const created = await formsApi.createFormCategory({
				name: categoryName.trim(),
				sort_order: formCategories.length,
				is_active: true,
			});
			const categories = sortFormCategories([...formCategories, created]);
			formCategories = categories;
			activeSection = created.name;
			resetCategoryEditor();
			toastStore.addToast('Form category created', 'success');
		} catch (error: any) {
			categorySaveError = error?.response?.data?.detail || 'Failed to create form category';
		} finally {
			savingCategory = false;
		}
	}

	async function toggleFormActive(form: FormDefinition) {
		try {
			await formsApi.updateForm(form.id, {
				name: form.name,
				description: form.description || undefined,
				form_type: form.form_type,
				section: resolveFormSection(form),
				department: form.department || undefined,
				procedure_name: form.procedure_name || undefined,
				fields: form.fields,
				sort_order: form.sort_order,
				is_active: !form.is_active
			});
			toastStore.addToast(form.is_active ? 'Configuration deactivated' : 'Configuration activated', 'success');
			await loadFormStudio();
		} catch {
			toastStore.addToast('Failed to update configuration', 'error');
		}
	}

	async function startEditingFormName() {
		isEditingFormName = true;
		await tick();
		formNameInput?.focus();
		formNameInput?.select();
	}

	function stopEditingFormName() {
		formEditorName = formEditorName.trim();
		isEditingFormName = false;
	}

	function openGeneratePrompt(context: 'studio' | 'settings') {
		generateContext = context;
		generateDescription = '';
		generateError = '';
		generating = false;
		showGeneratePrompt = true;
	}

	function closeGeneratePrompt() {
		showGeneratePrompt = false;
		generateDescription = '';
		generateError = '';
	}

	async function runGenerate() {
		if (!generateDescription.trim()) {
			generateError = 'Please describe what this form is for';
			return;
		}
		const hasExistingFields = hasGeneratedDraft;

		generating = true;
		generateError = '';
		try {
			// Pass existing fields for refinement if any exist
			const result = await formsApi.generateForm(
				generateDescription.trim(),
				hasExistingFields ? formEditorFields : undefined,
				formEditorName.trim() || undefined
			);
			formEditorName = result.name || formEditorName || 'Generated Form';
			const generatedFields = (result.fields || [])
				.filter((field) => !isGeneratedPatientIdentityField(field) && !isGeneratedInstructionalField(field))
				.map((field) => normalizeGeneratedField(field));
			if (hasExistingFields && generatedFields.length === 0) {
				generateDescription = '';
				closeGeneratePrompt();
				toastStore.addToast('No additional refinements suggested', 'success');
				showFormEditor = true;
				return;
			}
			const nextFields = hasExistingFields
				? mergeGeneratedFields(formEditorFields, generatedFields)
				: generatedFields;
			formEditorFields = nextFields;
			selectedFieldIndex = hasExistingFields ? Math.min(selectedFieldIndex, Math.max(0, nextFields.length - 1)) : 0;
			if (!hasExistingFields) {
				previewValues = {};
			}
			generateDescription = ''; // Clear for next refinement
			closeGeneratePrompt();
			toastStore.addToast(
				hasExistingFields
					? `Refined form: ${nextFields.length} fields`
					: `Generated ${nextFields.length} fields`,
				'success'
			);
			// Ensure editor stays open
			if (generateContext === 'settings') {
				showFormSettingsModal = false;
			}
			showFormEditor = true;
		} catch (error: any) {
			generateError = error?.response?.data?.detail || 'Failed to generate form. Check AI provider settings.';
		} finally {
			generating = false;
		}
	}

	function getOperatorsForFieldType(type: string): { value: FieldCondition['operator']; label: string }[] {
		const base: { value: FieldCondition['operator']; label: string }[] = [
			{ value: 'not_empty', label: 'is filled' },
			{ value: 'empty', label: 'is empty' },
			{ value: 'eq', label: 'equals' },
			{ value: 'ne', label: 'not equals' },
		];
		if (type === 'text' || type === 'textarea' || type === 'email' || type === 'tel') {
			base.push({ value: 'contains', label: 'contains' });
		}
		if (type === 'number' || type === 'date') {
			base.push(
				{ value: 'gt', label: 'greater than' },
				{ value: 'lt', label: 'less than' },
				{ value: 'gte', label: '≥ (gte)' },
				{ value: 'lte', label: '≤ (lte)' },
			);
		}
		return base;
	}
</script>

{#snippet formCategoryHeader()}
	<div class="flex items-center gap-3">
		<h3 class="text-sm font-bold text-slate-900">New Form Category</h3>
		<span class="rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.12em]" style="background: rgba(37,99,235,0.1); color: #2563eb;">
			TAB
		</span>
	</div>
{/snippet}

{#snippet formEditorHeader()}
	<div class="form-editor-header-shell">
		<div class="min-w-0 flex-1">
			<p class="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-700">Form Studio</p>
			{#if isEditingFormName}
				<input
					bind:this={formNameInput}
					bind:value={formEditorName}
					onblur={stopEditingFormName}
					onkeydown={(event) => {
						if (event.key === 'Enter') {
							event.preventDefault();
							stopEditingFormName();
						}
						if (event.key === 'Escape') {
							event.preventDefault();
							isEditingFormName = false;
						}
					}}
					class="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-base font-bold text-slate-900 outline-none md:max-w-[420px]"
					style="background: rgba(255,255,255,0.96); box-shadow: inset 0 1px 2px rgba(15,23,42,0.06);"
					placeholder="Untitled form"
				/>
			{:else}
				<button
					type="button"
					onclick={startEditingFormName}
					class="form-editor-name-trigger"
				>
					<span class="truncate text-lg font-bold text-slate-950 md:text-[1.35rem]">{formEditorName || 'Untitled Form'}</span>
					<span class="text-[11px] font-medium text-slate-500">Click to rename</span>
				</button>
			{/if}
		</div>

		<div class="header-inline-bar">
			<div class="header-inline-group">
				<p class="header-inline-label">Category</p>
				<select
					class="inline-select"
					bind:value={formEditorSection}
					onchange={(event) => {
						const value = (event.currentTarget as HTMLSelectElement).value;
						formEditorSection = value;
						if (!editingFormId) {
							formEditorType = value;
						}
					}}
				>
					{#each sectionTabs as section}
						<option value={section}>{section}</option>
					{/each}
				</select>
			</div>

			{#if formEditorType === 'CASE_RECORD' || formEditorType === 'CLINICAL'}
				<span class="header-inline-divider" aria-hidden="true"></span>
				<div class="header-inline-group">
					<p class="header-inline-label">Department</p>
					<input
						class="inline-select"
						style="width: 120px;"
						placeholder="e.g. Oral Surgery"
						bind:value={formEditorDepartment}
					/>
				</div>
				<span class="header-inline-divider" aria-hidden="true"></span>
				<div class="header-inline-group">
					<p class="header-inline-label">Procedure</p>
					<input
						class="inline-select"
						style="width: 120px;"
						placeholder="e.g. Extraction"
						bind:value={formEditorProcedureName}
					/>
				</div>
			{/if}

			<span class="header-inline-divider" aria-hidden="true"></span>

			<div class="header-inline-group">
				<p class="header-inline-label">Icon</p>
				<button
					type="button"
					onclick={() => (showIconPicker = true)}
					class="inline-select flex items-center gap-1.5 text-left"
					style="width: 120px; cursor: pointer;"
					title="Pick Lucide icon"
				>
					{#if formEditorIcon}
						{@const iconData = LUCIDE_ICONS.find(i => i.name === formEditorIcon)}
						{#if iconData}
							<Icon iconNode={iconData.node} size={14} color="#2563eb" />
						{/if}
						<span class="truncate text-xs font-semibold text-blue-700">{formEditorIcon}</span>
					{:else}
						<span class="text-slate-400">Pick icon…</span>
					{/if}
				</button>
			</div>

			<span class="header-inline-divider" aria-hidden="true"></span>

			<div class="header-inline-group" style="align-items: center; gap: 6px;">
				<p class="header-inline-label">Color</p>
				<input
					type="color"
					style="width: 28px; height: 28px; padding: 1px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.15); cursor: pointer; background: none;"
					value={formEditorColor || '#6b7280'}
					oninput={(e) => formEditorColor = (e.currentTarget as HTMLInputElement).value}
					title="Pick a color for this form's icon"
				/>
				{#if formEditorColor}
					<button type="button" onclick={() => formEditorColor = ''} class="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer">✕</button>
				{/if}
			</div>

			<span class="header-inline-divider" aria-hidden="true"></span>

			<div class="header-inline-group" style="align-items: center; gap: 4px; flex-wrap: wrap;">
				<p class="header-inline-label">Access</p>
				{#each ['FACULTY', 'STUDENT', 'NURSE', 'RECEPTION', 'PATIENT'] as role}
					<button
						type="button"
						class="px-1.5 py-0.5 rounded text-[10px] font-semibold cursor-pointer transition-colors"
						style={formEditorAllowedRoles.includes(role)
							? 'background: #3b82f6; color: white; border: 1px solid #2563eb;'
							: 'background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;'}
						onclick={() => {
							if (formEditorAllowedRoles.includes(role)) {
								formEditorAllowedRoles = formEditorAllowedRoles.filter(r => r !== role);
							} else {
								formEditorAllowedRoles = [...formEditorAllowedRoles, role];
							}
						}}
					>{role}</button>
				{/each}
				{#if formEditorAllowedRoles.length > 0}
					<button type="button" onclick={() => formEditorAllowedRoles = []} class="text-[10px] text-slate-400 hover:text-slate-600 cursor-pointer ml-1">✕ All</button>
				{/if}
			</div>

			<span class="header-inline-divider" aria-hidden="true"></span>

			<button
				type="button"
				role="switch"
				aria-checked={formEditorIsActive}
				aria-label="Toggle form active status"
				onclick={() => (formEditorIsActive = !formEditorIsActive)}
				class="toggle-switch-shell header-inline-toggle cursor-pointer"
			>
				<span class="text-[11px] font-bold uppercase tracking-[0.12em]" style={`color: ${formEditorIsActive ? '#1d4ed8' : '#64748b'};`}>
					{formEditorIsActive ? 'Active' : 'Inactive'}
				</span>
				<span class={`toggle-switch ${formEditorIsActive ? 'is-on' : ''}`} aria-hidden="true">
					<span class="toggle-thumb"></span>
				</span>
			</button>
		</div>
	</div>
{/snippet}

<div class="space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Form Studio</p>
			<h2 class="mt-1 text-lg font-bold text-slate-900 md:text-xl">Forms</h2>
		</div>
		<button
			onclick={() => openCreateFormEditor(activeSection)}
			class="inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
			style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 6px 14px rgba(37,99,235,0.2), inset 0 1px 0 rgba(255,255,255,0.25);"
		>
			<Plus class="h-3.5 w-3.5" />
			New Form
		</button>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="min-w-0 flex-1"
			oncontextmenu={(event) => {
				const btn = (event.target as HTMLElement).closest('[role="tab"]');
				if (btn) {
					const tabId = sectionTabs[Array.from(btn.parentElement?.querySelectorAll('[role="tab"]') ?? []).indexOf(btn)];
					if (tabId) openCategoryContextMenu(event, tabId);
				}
			}}
		>
			<TabBar
				tabs={sectionTabItems}
				activeTab={activeSection}
				variant="jiggle"
				ariaLabel="Form category navigation"
				onchange={(id) => {
					activeSection = id as typeof activeSection;
					categoryMenu = null;
				}}
			/>
		</div>
		<button
			type="button"
			onclick={openCategoryEditor}
			class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
			aria-label="Add form category"
			title="Add form category"
		>
			<Plus class="h-4 w-4" />
			<span>Add Category</span>
		</button>
	</div>

	{#if categoryMenu}
		<button
			type="button"
			class="fixed inset-0 z-40 cursor-default"
			onclick={() => (categoryMenu = null)}
			aria-label="Close category context menu"
		></button>
		<div
			class="fixed z-50 rounded-xl border border-slate-200 bg-white p-2 shadow-xl"
			style={`left: ${categoryMenu.x}px; top: ${categoryMenu.y}px;`}
		>
			<button
				type="button"
				onclick={toggleCategoryActiveFromMenu}
				class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
			>
				<Power class="h-3.5 w-3.5" />
				{categoryMenu.category.is_active ? 'Disable Tab' : 'Enable Tab'}
			</button>
			<!-- Delete tab action hidden until admin disable flow replaces hard delete UI. -->
			<!--
			<button
				type="button"
				onclick={deleteCategoryFromMenu}
				class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 cursor-pointer"
			>
				<Trash2 class="h-3.5 w-3.5" />
				Delete Tab
			</button>
			-->
		</div>
	{/if}

	{#if loadingForms}
		<div class="flex items-center justify-center py-20">
			<Loader2 class="h-8 w-8 animate-spin text-blue-500" />
		</div>
	{:else if filteredForms.length === 0}
		<div class="rounded-[18px] border border-slate-200 px-5 py-10 text-center" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<FileText class="mx-auto mb-3 h-7 w-7 text-slate-300" />
			<p class="text-sm font-semibold text-slate-700">No {activeSection.toLowerCase()} forms configured yet</p>
			<p class="mt-1.5 text-xs text-slate-400">Create one from the button above and it will appear here.</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each filteredForms as form}
				<div class="flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-colors"
					style="background: white; border-color: rgba(0,0,0,0.08); box-shadow: 0 1px 4px rgba(0,0,0,0.05); opacity: {form.is_active ? 1 : 0.7};">
					<!-- Icon -->
					<div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
						style="background: linear-gradient(135deg, #3b82f6, #2563eb); box-shadow: 0 4px 12px rgba(37,99,235,0.3);">
						<FileText class="w-6 h-6 text-white" />
					</div>
					<!-- Info -->
					<div class="flex-1 min-w-0">
						<h3 class="font-bold text-slate-900 text-sm">{form.name}</h3>
						<p class="text-[11px] font-bold text-slate-400 uppercase tracking-wide mt-0.5">{form.fields.length} FIELDS</p>
						<div class="flex items-center gap-1.5 mt-1.5 flex-wrap">
							<span class="text-[10px] font-bold px-2 py-0.5 rounded"
								style="background: rgba(37,99,235,0.1); color: #2563eb;">{resolveFormSection(form)}</span>
							{#if form.allowed_roles?.length}
								<span class="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded"
									style="background: rgba(16,185,129,0.1); color: #059669; border: 1px solid rgba(16,185,129,0.2);">
									🛡 {form.allowed_roles.length} ROLE{form.allowed_roles.length !== 1 ? 'S' : ''}
								</span>
							{/if}
							{#if !form.is_active}
								<span class="text-[10px] font-bold px-2 py-0.5 rounded"
									style="background: rgba(148,163,184,0.15); color: #64748b;">INACTIVE</span>
							{/if}
						</div>
					</div>
					<!-- Actions -->
					<div class="flex items-center gap-2 shrink-0">
						<button
							onclick={() => openSettingsOnly(form)}
							class="w-9 h-9 flex items-center justify-center rounded-full border cursor-pointer transition-colors hover:bg-slate-100"
							style="border-color: rgba(0,0,0,0.12);"
							title="Form settings"
						>
							<Settings class="w-4.5 h-4.5 text-slate-400" />
						</button>
						<button
							onclick={() => openEditFormEditor(form)}
							class="inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold text-white cursor-pointer"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 4px 10px rgba(37,99,235,0.3);"
						>
							Edit
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.form-tab-scroll {
		display: block;
		max-width: 100%;
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: none;
		-ms-overflow-style: none;
	}

	.form-tab-scroll::-webkit-scrollbar {
		display: none;
	}

	.form-tab-shell :global(.tab-bar--jiggle) {
		border-color: rgba(203, 213, 225, 0.9);
		background: #f8fafc;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
	}

	.form-tab-row {
		display: flex;
		gap: 0.35rem;
		width: max-content;
		padding: 0.28rem;
		border: 1px solid rgba(226, 232, 240, 0.9);
		border-radius: 0.9rem;
		background: #f8fafc;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
	}

	.form-tab-btn {
		flex: 0 0 auto;
		min-height: 2.7rem;
		padding: 0.62rem 0.88rem;
		border: 1px solid transparent;
		border-radius: 0.75rem;
		background: transparent;
		font-size: 0.84rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		color: #667085;
		cursor: pointer;
		white-space: nowrap;
	}

	.form-tab-btn:hover {
		color: #475467;
		transform: translateY(-1px);
	}

	.form-tab-btn.is-active {
		color: white;
		border-color: rgba(29, 78, 216, 0.2);
		background: linear-gradient(135deg, #3b82f6 0%, #2563eb 60%, #1d4ed8 100%);
		box-shadow:
			0 10px 22px rgba(37, 99, 235, 0.22),
			inset 0 1px 0 rgba(255, 255, 255, 0.32),
			inset 0 -1px 0 rgba(15, 23, 42, 0.12);
	}

	.drag-sort-row {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		width: 100%;
		padding: 0.75rem 0.85rem;
		border: 1px solid rgba(226, 232, 240, 0.95);
		border-radius: 0.8rem;
		background: #ffffff;
		box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
		transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease, background 140ms ease, opacity 140ms ease;
	}

	.drag-sort-row.is-selected {
		border-color: rgba(37, 99, 235, 0.42);
		background: #eef4ff;
		box-shadow: 0 6px 14px rgba(37, 99, 235, 0.12);
	}

	.drag-sort-row.is-drop-target {
		border-color: rgba(8, 145, 178, 0.34);
		box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.12);
	}

	.drag-sort-row.is-dragging {
		opacity: 0.72;
		transform: scale(0.99);
	}

	.drag-handle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		flex: 0 0 auto;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 0.6rem;
		background: rgba(148, 163, 184, 0.1);
		color: #64748b;
	}

	.studio-card {
		border: 1px solid rgba(203, 213, 225, 0.95);
		border-radius: 0.9rem;
		background: #ffffff;
		box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08);
	}

	.studio-subcard {
		border: 1px solid rgba(203, 213, 225, 0.95);
		border-radius: 0.75rem;
		background: #f8fafc;
		box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.92);
	}

	.form-editor-header-shell {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		width: 100%;
	}

	.form-editor-name-trigger {
		display: inline-flex;
		min-width: 0;
		max-width: 100%;
		flex-direction: column;
		align-items: flex-start;
		padding: 0.15rem 0;
		text-align: left;
		cursor: pointer;
	}

	.header-inline-bar {
		display: inline-flex;
		align-items: center;
		gap: 0.9rem;
		padding: 0.45rem 0.55rem 0.45rem 0.85rem;
		border: 1px solid rgba(203, 213, 225, 0.95);
		border-radius: 1.1rem;
		background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.96));
		box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08), inset 0 1px 0 rgba(255,255,255,0.9);
	}

	.header-inline-group {
		display: inline-flex;
		align-items: center;
		gap: 0.8rem;
		min-width: 0;
	}

	.header-inline-label {
		margin: 0;
		font-size: 0.66rem;
		font-weight: 800;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: #1d4ed8;
		white-space: nowrap;
	}

	.header-inline-divider {
		width: 1px;
		height: 2rem;
		background: linear-gradient(180deg, rgba(203,213,225,0), rgba(203,213,225,0.9), rgba(203,213,225,0));
	}

	.inline-select {
		width: 9rem;
		padding: 0.65rem 0.85rem;
		border: 1px solid rgba(148, 163, 184, 0.32);
		border-radius: 0.9rem;
		background: #ffffff;
		font-size: 0.78rem;
		font-weight: 700;
		color: #0f172a;
		outline: none;
		cursor: pointer;
		box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
	}

	.header-inline-toggle {
		gap: 0.8rem;
		padding: 0.2rem 0.15rem 0.2rem 0;
		border: 0;
		box-shadow: none;
		background: transparent;
	}

	.toggle-switch-shell {
		display: inline-flex;
		align-items: center;
		gap: 0.7rem;
		padding: 0.65rem 0.8rem;
		border: 1px solid rgba(203, 213, 225, 0.95);
		border-radius: 0.75rem;
		background: #ffffff;
		box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
	}

	.toggle-switch {
		position: relative;
		display: inline-flex;
		align-items: center;
		width: 2.8rem;
		height: 1.6rem;
		padding: 0.14rem;
		border-radius: 999px;
		background: #cbd5e1;
		transition: background 140ms ease;
	}

	.toggle-switch.is-on {
		background: #2563eb;
	}

	.toggle-thumb {
		width: 1.3rem;
		height: 1.3rem;
		border-radius: 999px;
		background: #ffffff;
		box-shadow: 0 2px 6px rgba(15, 23, 42, 0.24);
		transition: transform 140ms ease;
	}

	.toggle-switch.is-on .toggle-thumb {
		transform: translateX(1.18rem);
	}

	@media (min-width: 768px) {
		.form-tab-scroll {
			max-width: 620px;
		}
	}

	@media (max-width: 767px) {
		.form-editor-header-shell {
			flex-direction: column;
			align-items: stretch;
		}

		.header-inline-bar {
			width: 100%;
			justify-content: space-between;
			flex-wrap: wrap;
			gap: 0.8rem;
		}

		.header-inline-group {
			flex: 1 1 auto;
		}

		.inline-select {
			width: 100%;
			max-width: 10rem;
		}

		.header-inline-divider {
			display: none;
		}
	}
</style>

{#if showFormEditor}
	<!-- Form Studio Editor — full screen custom modal -->
	<div use:portal class="fixed inset-0 flex items-center justify-center p-4"
		style="background: rgba(15,23,42,0.18); backdrop-filter: blur(4px); z-index: 9999;">
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="absolute inset-0" onclick={resetFormEditor} onkeydown={(e) => { if (e.key === 'Escape') resetFormEditor(); }}></div>
		<div class="relative flex flex-col rounded-[20px] overflow-hidden w-full"
			style="background: white; box-shadow: 0 -8px 40px rgba(0,0,0,0.22); border: 1px solid rgba(0,0,0,0.1); max-height: calc(100dvh - 4rem); max-width: 1320px;">

			<!-- ── TOP BAR ── -->
			<div class="flex items-center gap-3 px-4 py-3 shrink-0 border-b"
				style="background: linear-gradient(to bottom, #f0f5ff, #e6eeff); border-color: rgba(37,99,235,0.18);">
				<span class="text-[10px] font-black tracking-[0.22em] text-blue-700 uppercase shrink-0 hidden sm:inline">FORM STUDIO</span>
				<div class="flex-1 min-w-0">
					{#if isEditingFormName}
						<input
							bind:this={formNameInput}
							bind:value={formEditorName}
							onblur={stopEditingFormName}
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); stopEditingFormName(); } if (e.key === 'Escape') { e.preventDefault(); isEditingFormName = false; } }}
							class="rounded-[10px] border border-blue-300 px-3 py-1.5 text-sm font-bold text-slate-900 outline-none"
							style="background: rgba(255,255,255,0.96); max-width: 300px;"
							placeholder="Untitled form"
						/>
					{:else}
						<button type="button" onclick={startEditingFormName}
							class="text-sm font-bold text-slate-900 hover:text-blue-700 cursor-pointer truncate max-w-[220px] sm:max-w-[340px] text-left">
							{formEditorName || 'Untitled Form'}
						</button>
					{/if}
				</div>
				<button
					type="button"
					onclick={() => openGeneratePrompt('studio')}
					class="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-bold text-white cursor-pointer"
					style="background: linear-gradient(to bottom, #8b5cf6, #6d28d9); box-shadow: 0 4px 10px rgba(109,40,217,0.25);"
					title={hasGeneratedDraft ? 'AI refine fields' : 'AI generate fields'}
				>
					<Sparkles class="w-3.5 h-3.5" />
					<span class="hidden sm:inline">{hasGeneratedDraft ? 'Refine' : 'Generate'}</span>
				</button>
				<button
					type="button"
					onclick={() => { settingsSaveError = ''; showFormSettingsModal = true; }}
					class="w-9 h-9 flex items-center justify-center rounded-full border cursor-pointer transition-colors hover:bg-blue-50"
					style="border-color: rgba(37,99,235,0.25);"
					title="Form settings"
				>
					<Settings class="w-4 h-4 text-blue-600" />
				</button>
				<button type="button" onclick={resetFormEditor}
					class="w-9 h-9 flex items-center justify-center rounded-full cursor-pointer hover:bg-slate-100 transition-colors">
					<X class="w-5 h-5 text-slate-500" />
				</button>
			</div>

			{#if formSaveError}
				<div class="shrink-0 mx-4 mt-3 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{formSaveError}</div>
			{/if}

			<!-- ── SCROLLABLE 3-COLUMN CONTENT ── -->
			<div class="flex-1 min-h-0 flex gap-4 p-4" style="background: #f3f6fb; overflow-y: hidden; overflow-x: auto;">

				<!-- Fields Overview -->
				<div class="studio-card p-3.5 flex flex-col overflow-hidden" style="width: 260px; min-width: 260px; min-height: 0;">
					<div class="mb-3 shrink-0">
							<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Fields Overview</p>
							<p class="mt-1 text-xs text-slate-500">Drag to reorder. Tap a row to edit.</p>
						</div>
					<div class="flex-1 overflow-y-auto space-y-1.5 pr-1" role="list" aria-label="Form fields">
							{#each formEditorFields as field, index (getEditorFieldId(field, index))}
								<div
									class={`drag-sort-row ${selectedFieldIndex === index ? 'is-selected' : ''} ${draggedFieldIndex === index ? 'is-dragging' : ''} ${dragOverFieldIndex === index && draggedFieldIndex !== null && draggedFieldIndex !== index ? 'is-drop-target' : ''}`}
									role="listitem"
									draggable="true"
									ondragstart={(event) => handleFieldDragStart(event, index)}
									ondragover={(event) => handleFieldDragOver(event, index)}
									ondrop={(event) => handleFieldDrop(event, index)}
									ondragend={resetFieldDragState}
								>
									<button
										type="button"
										class="flex min-w-0 flex-1 items-center gap-2.5 text-left cursor-pointer"
										title={field.key || slugify(field.label) || `field_${index + 1}`}
										onclick={() => { selectedFieldIndex = index; resetOptionDragState(); }}
									>
										<span class="drag-handle" aria-hidden="true"><GripVertical class="h-3.5 w-3.5" /></span>
										<span class="truncate text-sm font-semibold" style={`color: ${selectedFieldIndex === index ? '#0f172a' : '#334155'};`}>
											{field.label || `Untitled field ${index + 1}`}
										</span>
									</button>
								</div>
							{/each}
							<button
								type="button"
								onclick={addFormField}
								class="w-full rounded-xl border border-dashed border-slate-300 px-3 py-3 text-xs font-semibold text-slate-500 cursor-pointer hover:border-slate-400 hover:text-slate-700"
								style="background: rgba(255,255,255,0.55);"
							>
								<Plus class="mr-1.5 inline-block h-3.5 w-3.5" />Add Field
							</button>
						</div>
					</div>

				<!-- Selected Field Editor -->
				<div class="studio-card p-3.5 overflow-y-auto" style="flex: 1; min-width: 0; min-height: 0;">
						{#if selectedField}
							{@const availableFields = getAvailableConditionFields(selectedFieldIndex)}
							<div class="mb-3 flex items-start justify-between gap-3">
								<div>
									<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Selected Field</p>
									<h4 class="mt-1 text-sm font-bold text-slate-900">{selectedField.label || `Field ${selectedFieldIndex + 1}`}</h4>
								</div>
								<button
									type="button"
									onclick={() => removeFormField(selectedFieldIndex)}
									class="inline-flex items-center gap-1.5 rounded-[10px] border border-red-200 px-3 py-1.5 text-[11px] font-bold text-red-600 cursor-pointer"
									style="background: #fff5f5; box-shadow: 0 4px 10px rgba(239,68,68,0.08);"
								>
									<Trash2 class="h-3.5 w-3.5" />Remove
								</button>
							</div>
							<div class="space-y-3">
								<div class="grid gap-3 md:grid-cols-2">
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Label</p>
										<input type="text" class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none" style="background: #ffffff; box-shadow: inset 0 1px 2px rgba(15,23,42,0.08);" value={selectedField.label} oninput={(event) => updateFieldLabel(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)} />
									</div>
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Type</p>
										<select class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none cursor-pointer" style="background: #ffffff; box-shadow: inset 0 1px 2px rgba(15,23,42,0.08);" value={selectedField.type} onchange={(event) => updateFieldType(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value)}>
											{#each fieldTypes as fieldType}
												<option value={fieldType}>{fieldTypeLabels[fieldType] ?? fieldType.toUpperCase()}</option>
											{/each}
										</select>
									</div>
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Required</p>
										<button type="button" role="switch" aria-checked={selectedField.required} aria-label="Toggle required field" onclick={() => updateFieldRequired(selectedFieldIndex, !selectedField.required)} class="toggle-switch-shell w-full justify-between cursor-pointer">
											<span class="text-sm font-bold" style={`color: ${selectedField.required ? '#1d4ed8' : '#64748b'};`}>{selectedField.required ? 'Required' : 'Optional'}</span>
											<span class={`toggle-switch ${selectedField.required ? 'is-on' : ''}`} aria-hidden="true"><span class="toggle-thumb"></span></span>
										</button>
									</div>
								</div>
								<div>
									<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Placeholder</p>
									<input type="text" class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: #ffffff; box-shadow: inset 0 1px 2px rgba(15,23,42,0.08);" value={selectedField.placeholder || ''} oninput={(event) => updateFieldProperty(selectedFieldIndex, 'placeholder', (event.currentTarget as HTMLInputElement).value)} />
								</div>
								<div>
									<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Help Text</p>
									<textarea rows="2" class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none resize-y" style="background: #ffffff; box-shadow: inset 0 1px 2px rgba(15,23,42,0.08);" value={selectedField.help_text || ''} oninput={(event) => updateFieldProperty(selectedFieldIndex, 'help_text', (event.currentTarget as HTMLTextAreaElement).value)}></textarea>
								</div>
								{#if selectedField.type === 'select'}
									<div class="studio-subcard p-3">
										<div class="flex items-center justify-between gap-3">
											<div>
												<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Options</p>
												<p class="mt-1 text-xs text-slate-500">Each option is its own row. Drag to reorder.</p>
											</div>
											<button type="button" onclick={() => addFieldOption(selectedFieldIndex)} class="rounded-[10px] border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 cursor-pointer" style="background: #ffffff; box-shadow: 0 4px 10px rgba(15,23,42,0.06);">
												<Plus class="mr-1 inline-block h-3.5 w-3.5" />Add Option
											</button>
										</div>
										{#if (selectedField.options?.length ?? 0) > 0}
											<div class="mt-3 space-y-2" role="list" aria-label="Select field options">
												{#each selectedField.options ?? [] as option, optionIndex (optionIndex)}
													<div class={`drag-sort-row ${draggedOptionIndex === optionIndex ? 'is-dragging' : ''} ${dragOverOptionIndex === optionIndex && draggedOptionIndex !== null && draggedOptionIndex !== optionIndex ? 'is-drop-target' : ''}`} role="listitem" draggable="true" ondragstart={(event) => handleOptionDragStart(event, optionIndex)} ondragover={(event) => handleOptionDragOver(event, optionIndex)} ondrop={(event) => handleOptionDrop(event, selectedFieldIndex, optionIndex)} ondragend={resetOptionDragState}>
														<span class="drag-handle" aria-hidden="true"><GripVertical class="h-3.5 w-3.5" /></span>
														<input type="text" placeholder={`Option ${optionIndex + 1}`} class="min-w-0 flex-1 rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: #ffffff;" value={option} oninput={(event) => updateFieldOption(selectedFieldIndex, optionIndex, (event.currentTarget as HTMLInputElement).value)} />
														<button type="button" onclick={() => removeFieldOption(selectedFieldIndex, optionIndex)} class="flex h-9 w-9 items-center justify-center rounded-full text-red-500 cursor-pointer hover:bg-red-50" aria-label="Remove option"><Trash2 class="h-3.5 w-3.5" /></button>
													</div>
												{/each}
											</div>
										{:else}
											<button type="button" onclick={() => addFieldOption(selectedFieldIndex)} class="mt-3 w-full rounded-[10px] border border-dashed border-slate-300 px-3 py-3 text-xs font-semibold text-slate-500 cursor-pointer" style="background: rgba(255,255,255,0.55);">Add first option</button>
										{/if}
									</div>
								{/if}
								{#if selectedField.type === 'textarea'}
									<div>
										<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Rows</p>
										<input type="number" min="1" class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: #ffffff;" value={selectedField.rows ?? 3} oninput={(event) => { const parsed = Number.parseInt((event.currentTarget as HTMLInputElement).value, 10); updateFieldProperty(selectedFieldIndex, 'rows', Number.isFinite(parsed) && parsed > 0 ? parsed : undefined); }} />
									</div>
								{/if}
								{#if selectedField.type === 'file'}
									<div class="grid gap-3 md:grid-cols-2">
										<div>
											<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Accepted Types</p>
											<input type="text" placeholder=".pdf,.jpg,image/*" class="w-full rounded-[10px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: #ffffff;" value={selectedField.accept || ''} oninput={(event) => updateFieldProperty(selectedFieldIndex, 'accept', (event.currentTarget as HTMLInputElement).value)} />
										</div>
										<div>
											<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Upload Mode</p>
											<button type="button" role="switch" aria-checked={selectedField.multiple} aria-label="Toggle multiple file uploads" onclick={() => updateFieldProperty(selectedFieldIndex, 'multiple', !selectedField.multiple)} class="toggle-switch-shell w-full justify-between cursor-pointer">
												<span class="text-sm font-bold" style={`color: ${selectedField.multiple ? '#1d4ed8' : '#64748b'};`}>{selectedField.multiple ? 'Multiple Files' : 'Single File'}</span>
												<span class={`toggle-switch ${selectedField.multiple ? 'is-on' : ''}`} aria-hidden="true"><span class="toggle-thumb"></span></span>
											</button>
										</div>
									</div>
								{/if}
								<div class="studio-subcard p-3">
									<p class="mb-3 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Visibility Logic</p>
									{#if availableFields.length === 0}
										<p class="rounded-[14px] border border-slate-200 bg-white px-3 py-3 text-xs text-slate-500">Add a field before this one if you want to make it conditional.</p>
									{:else}
										<div class="space-y-3">
											<div>
												<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Show Field When</p>
												<select class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={selectedField.condition?.field ?? ''} onchange={(event) => { const value = (event.currentTarget as HTMLSelectElement).value; if (!value) { clearFieldCondition(selectedFieldIndex); return; } updateFieldConditionField(selectedFieldIndex, value); }}>
													<option value="">Always show</option>
													{#each availableFields as fieldOption}
														<option value={fieldOption.key}>{fieldOption.label}</option>
													{/each}
												</select>
											</div>
											{#if selectedField.condition?.field}
												{@const controllingField = availableFields.find((fieldOption) => fieldOption.key === selectedField.condition?.field)}
												{@const operatorChoices = getOperatorsForFieldType(controllingField?.type ?? 'text')}
												{@const needsValue = selectedField.condition.operator !== 'empty' && selectedField.condition.operator !== 'not_empty'}
												<div class="grid gap-3 md:grid-cols-2">
													<div>
														<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Operator</p>
														<select class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={selectedField.condition.operator} onchange={(event) => updateFieldConditionOperator(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value as FieldCondition['operator'])}>
															{#each operatorChoices as op}
																<option value={op.value}>{op.label}</option>
															{/each}
														</select>
													</div>
													{#if needsValue}
														<div>
															<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Value</p>
															{#if (selectedField.condition.operator === 'eq' || selectedField.condition.operator === 'ne') && controllingField && controllingField.options.length > 0}
																<select class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none cursor-pointer" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={String(selectedField.condition.value ?? '')} onchange={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLSelectElement).value)}>
																	<option value="">Pick a value</option>
																	{#each controllingField.options as option}
																		<option value={option}>{option}</option>
																	{/each}
																</select>
															{:else if controllingField?.type === 'number' || selectedField.condition.operator === 'gt' || selectedField.condition.operator === 'lt' || selectedField.condition.operator === 'gte' || selectedField.condition.operator === 'lte'}
																<input type="number" class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={String(selectedField.condition.value ?? '')} oninput={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)} />
															{:else if controllingField?.type === 'date'}
																<input type="date" class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={String(selectedField.condition.value ?? '')} oninput={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)} />
															{:else}
																<input type="text" class="w-full rounded-[14px] border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: linear-gradient(to bottom, #ffffff, #f8fafc);" value={String(selectedField.condition.value ?? '')} oninput={(event) => updateFieldConditionValue(selectedFieldIndex, (event.currentTarget as HTMLInputElement).value)} />
															{/if}
														</div>
													{/if}
												</div>
											{/if}
										</div>
									{/if}
								</div>
							</div>
						{:else}
							<div class="flex h-full items-center justify-center rounded-[18px] border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500" style="background: rgba(255,255,255,0.55);">
								Select a field from the overview to configure it.
							</div>
						{/if}
					</div>

				<!-- Live Preview -->
				<div class="studio-card p-3.5 overflow-y-auto" style="flex: 1.1; min-width: 0; min-height: 0;">
						<div class="mb-3 flex items-center justify-between gap-3">
							<div>
								<p class="text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Live Preview</p>
								<p class="mt-1 text-xs text-slate-500">Type into the preview to test placeholders and conditional visibility.</p>
							</div>
							<button type="button" onclick={() => (previewValues = {})} class="inline-flex items-center gap-1.5 rounded-[10px] border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 cursor-pointer" style="background: #ffffff;">
								<RotateCcw class="h-3.5 w-3.5" />Reset
							</button>
						</div>
						{#if previewSchema.duplicates.length > 0}
							<div class="mb-3 rounded-[14px] border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
								Duplicate field keys: {previewSchema.duplicates.join(', ')}. Save blocked until resolved.
							</div>
						{/if}
						<div class="rounded-xl border border-slate-300 p-3" style="background: #ffffff; min-height: 200px;">
							{#if previewSchema.fields.length > 0}
								<DynamicFormRenderer fields={previewSchema.fields} rules={formEditorRules} bind:values={previewValues} idPrefix="form-studio-preview" />
							{:else}
								<div class="flex h-full items-center justify-center text-center text-sm text-slate-500 py-10">Add at least one field to render the preview.</div>
							{/if}
						</div>
				</div>

			</div>

			<!-- ── FIXED BOTTOM SAVE BAR ── -->
			<div class="shrink-0 px-4 py-3 border-t" style="background: linear-gradient(to bottom, #f0f5ff, #e6eeff); border-color: rgba(37,99,235,0.15);">
				<button
					onclick={saveFormDefinition}
					disabled={savingForm}
					class="w-full rounded-[999px] px-8 py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60"
					style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 10px 20px rgba(37,99,235,0.2), inset 0 2px 0 rgba(255,255,255,0.24);"
				>
					{#if savingForm}
						<Loader2 class="mr-2 inline-block h-4 w-4 animate-spin" />Saving...
					{:else}
						Save Configuration
					{/if}
				</button>
			</div>

		</div>
	</div>
{/if}

{#if showFormSettingsModal}
	<AquaModal title="Form Settings" onclose={() => (showFormSettingsModal = false)} panelClass="sm:max-w-[560px]" contentClass="p-0" zIndex={10000}>
		<div class="space-y-4 px-4 py-4">
			<div class="grid gap-3 sm:grid-cols-2">
				<div>
					<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Category</p>
					<select class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-800 outline-none cursor-pointer" style="background: white;" bind:value={formEditorSection} onchange={(event) => { const value = (event.currentTarget as HTMLSelectElement).value; formEditorSection = value; if (!editingFormId) { formEditorType = value; } else { formEditorType = formEditorType || value; } }}>
						{#each sectionTabs as section}
							<option value={section}>{section}</option>
						{/each}
					</select>
				</div>
				<div>
					<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Sort Order</p>
					<input type="number" min="0" class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" style="background: white;" bind:value={formEditorSortOrder} />
				</div>
			</div>
			{#if formEditorSection === 'CLINICAL' || formEditorType === 'CASE_RECORD'}
				<div class="grid gap-3 sm:grid-cols-2">
					<div>
						<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Department</p>
						<input class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" placeholder="e.g. Oral Surgery" bind:value={formEditorDepartment} />
					</div>
					<div>
						<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Procedure Name</p>
						<input class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-700 outline-none" placeholder="e.g. Extraction" bind:value={formEditorProcedureName} />
					</div>
				</div>
			{/if}
			<div class="grid gap-3 sm:grid-cols-2">
				<div>
					<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Icon (Lucide name)</p>
					<div class="flex items-center gap-2">
						{#if formEditorIcon}
							{@const iconData = LUCIDE_ICONS.find(i => i.name === formEditorIcon)}
							{#if iconData}
								<div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl" style="background: linear-gradient(to bottom, #eff6ff, #dbeafe);">
									<Icon iconNode={iconData.node} size={18} color="#2563eb" />
								</div>
							{/if}
						{/if}
						<button
							type="button"
							onclick={() => (showIconPicker = true)}
							class="flex flex-1 items-center gap-2 rounded-xl border border-slate-300 px-3 py-2.5 text-sm text-slate-700 transition-colors hover:border-blue-400 hover:bg-blue-50"
						>
							{#if formEditorIcon}
								<span class="font-semibold text-blue-700">{formEditorIcon}</span>
							{:else}
								<span class="text-slate-400">Pick icon...</span>
							{/if}
							{#if formEditorIcon}
								<span role="button" tabindex="0"
									onclick={(e) => { e.stopPropagation(); formEditorIcon = ''; }}
									onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); formEditorIcon = ''; } }}
									class="ml-auto text-slate-400 hover:text-slate-700"
								>✕</span>
							{/if}
						</button>
					</div>
				</div>
				<div>
					<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Color</p>
					<div class="flex items-center gap-2">
						<input type="color" class="w-10 h-10 rounded-lg border cursor-pointer p-0.5" style="border-color: rgba(0,0,0,0.15);" value={formEditorColor || '#6b7280'} oninput={(e) => formEditorColor = (e.currentTarget as HTMLInputElement).value} />
						{#if formEditorColor}
							<button type="button" onclick={() => formEditorColor = ''} class="text-xs text-slate-500 hover:text-slate-800 cursor-pointer">✕ Clear</button>
						{/if}
					</div>
				</div>
			</div>
			<div>
				<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Access Roles</p>
				<p class="mb-2 text-xs text-slate-500">Select which roles can see this form. Leave empty to show to all roles.</p>
				<div class="flex flex-wrap gap-2">
					{#each ['FACULTY', 'STUDENT', 'NURSE', 'RECEPTION', 'PATIENT'] as role}
						<button
							type="button"
							class="px-3 py-1.5 rounded-full text-xs font-bold cursor-pointer transition-colors"
							style={formEditorAllowedRoles.includes(role)
								? 'background: #3b82f6; color: white; border: 1px solid #2563eb;'
								: 'background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;'}
							onclick={() => {
								if (formEditorAllowedRoles.includes(role)) {
									formEditorAllowedRoles = formEditorAllowedRoles.filter(r => r !== role);
								} else {
									formEditorAllowedRoles = [...formEditorAllowedRoles, role];
								}
							}}
						>{role}</button>
					{/each}
					{#if formEditorAllowedRoles.length > 0}
						<button type="button" onclick={() => formEditorAllowedRoles = []} class="text-xs text-slate-400 hover:text-slate-600 cursor-pointer px-2 py-1">✕ Clear all</button>
					{/if}
				</div>
			</div>
			<div class="flex items-center justify-between pt-1">
				<div>
					<p class="text-sm font-bold text-slate-800">Active</p>
					<p class="text-xs text-slate-500">Visible to users in the system</p>
				</div>
				<button type="button" role="switch" aria-checked={formEditorIsActive} onclick={() => (formEditorIsActive = !formEditorIsActive)} class="toggle-switch-shell cursor-pointer">
					<span class="text-sm font-bold" style={`color: ${formEditorIsActive ? '#1d4ed8' : '#64748b'};`}>{formEditorIsActive ? 'Active' : 'Inactive'}</span>
					<span class={`toggle-switch ${formEditorIsActive ? 'is-on' : ''}`} aria-hidden="true"><span class="toggle-thumb"></span></span>
				</button>
			</div>
			{#if settingsSaveError}
				<p class="text-xs text-red-500 text-center -mt-1">{settingsSaveError}</p>
			{/if}
			<div class="flex gap-2">
				<button type="button" onclick={() => openGeneratePrompt('settings')} class="flex-1 inline-flex items-center justify-center gap-1.5 rounded-[999px] py-2.5 text-sm font-bold text-white cursor-pointer" style="background: linear-gradient(to bottom, #8b5cf6, #6d28d9); box-shadow: 0 8px 18px rgba(109,40,217,0.2);">
					<Sparkles class="w-3.5 h-3.5" />{hasGeneratedDraft ? 'Refine Fields' : 'Generate Fields'}
				</button>
				<button type="button" onclick={saveFormSettings} disabled={savingSettings} class="flex-1 rounded-[999px] py-2.5 text-sm font-bold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 8px 18px rgba(37,99,235,0.2);">
					{savingSettings ? 'Saving…' : 'Save Settings'}
				</button>
			</div>
		</div>
	</AquaModal>
{/if}

{#if showIconPicker}
	<IconPicker
		value={formEditorIcon}
		onselect={(name) => { formEditorIcon = name; }}
		onclose={() => (showIconPicker = false)}
	/>
{/if}

{#if showCategoryEditor}
	<AquaModal
		header={formCategoryHeader}
		onclose={resetCategoryEditor}
		panelClass="sm:max-w-[420px]"
		contentClass="p-0"
	>
		<div class="space-y-4 px-4 py-4" style="background: linear-gradient(to bottom, #ffffff, #f4f7fb);">
			{#if categorySaveError}
				<div class="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{categorySaveError}</div>
			{/if}
			<div>
				<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-blue-700">Category Name</p>
				<input type="text" placeholder="e.g. RADIOLOGY" class="w-full rounded-[14px] border border-slate-300 px-3.5 py-2.5 text-sm font-semibold text-slate-800 outline-none" style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);" bind:value={categoryName} />
				<p class="mt-2 text-xs text-slate-500">The new tab becomes available immediately in the forms studio and in form creation.</p>
			</div>
			<button type="button" onclick={saveFormCategory} disabled={savingCategory} class="w-full rounded-[999px] px-8 py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #1453c4); box-shadow: 0 10px 20px rgba(37,99,235,0.2), inset 0 2px 0 rgba(255,255,255,0.24);">
				{#if savingCategory}<Loader2 class="mr-2 inline-block h-4 w-4 animate-spin" />Creating...{:else}Create Category{/if}
			</button>
		</div>
	</AquaModal>
{/if}

{#if showGeneratePrompt}
	{@const isRefining = hasGeneratedDraft}
	<AquaModal title={isRefining ? "Refine Form with AI" : "AI Form Generator"} onclose={closeGeneratePrompt} panelClass="sm:max-w-[480px]" contentClass="p-0" zIndex={10001}>
		<div class="space-y-4 px-4 py-4 rounded-b-[20px]" style="background: linear-gradient(to bottom, #faf5ff, #f3e8ff);">
			{#if generateError}
				<div class="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs font-medium text-red-600">{generateError}</div>
			{/if}
			{#if isRefining}
				<div class="rounded-xl border border-purple-200 bg-purple-50 px-3.5 py-2.5 text-xs text-purple-700">
					<strong>Refining {formEditorFields.length} existing fields.</strong> Describe changes: add fields, remove fields, modify types, etc.
				</div>
			{/if}
			<div>
				<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-purple-700">{isRefining ? 'Describe Changes' : 'Describe Your Form'}</p>
				<textarea
					rows="3"
					placeholder={isRefining ? "e.g. Add a field for allergies, remove phone number, make email required" : "e.g. Patient intake form for orthodontics department with chief complaint, medical history, and dental examination findings"}
					class="w-full rounded-[14px] border border-purple-300 px-3.5 py-2.5 text-sm text-slate-800 outline-none resize-y"
					style="background: linear-gradient(to bottom, #ffffff, #faf5ff); box-shadow: inset 0 1px 4px rgba(15,23,42,0.04);"
					bind:value={generateDescription}
					onkeydown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runGenerate(); } }}
				></textarea>
				<p class="mt-2 text-xs text-slate-500">Press <kbd class="px-1 py-0.5 rounded bg-slate-200 text-[10px] font-bold">⌘ Enter</kbd> to submit.</p>
			</div>
			<button
				type="button"
				onclick={runGenerate}
				disabled={generating || !generateDescription.trim()}
				class="w-full inline-flex items-center justify-center gap-2 rounded-[999px] px-8 py-3 text-sm font-bold text-white cursor-pointer disabled:opacity-60"
				style="background: linear-gradient(to bottom, #8b5cf6, #6d28d9); box-shadow: 0 10px 20px rgba(109,40,217,0.2), inset 0 2px 0 rgba(255,255,255,0.24);"
			>
				{#if generating}
					<Loader2 class="h-4 w-4 animate-spin" />{isRefining ? 'Refining...' : 'Generating...'}
				{:else}
					<Sparkles class="h-4 w-4" />{isRefining ? 'Refine Form' : 'Generate Form'}
				{/if}
			</button>
		</div>
	</AquaModal>
{/if}
