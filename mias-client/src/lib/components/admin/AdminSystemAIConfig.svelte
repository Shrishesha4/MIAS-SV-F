<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import { toastStore } from '$lib/stores/toast';
	import {
		adminApi,
		type AIProviderConfigResponse,
		type AIProviderConfigRow,
		type AIProviderType,
	} from '$lib/api/admin';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import SystemConfigTabs from '$lib/components/admin/SystemConfigTabs.svelte';
	import { Bot, Loader2, Plus, Save, Sparkles, TestTube2, Trash2, WandSparkles } from 'lucide-svelte';

	type AIConfigDraft = AIProviderConfigRow & {
		apiKeyInput: string;
		showApiKey: boolean;
		saving: boolean;
		testing: boolean;
		deleting: boolean;
	};

	const auth = get(authStore);

	let loading = $state(true);
	let adding = $state(false);
	let providerDefaults = $state<Record<string, string>>({});
	let rows = $state<AIConfigDraft[]>([]);
	let promptEditorId = $state<string | null>(null);
	let promptDraft = $state('');
	let lastTestPreview = $state<{ label: string; findings: string; diagnosis: string; treatment: string } | null>(null);

	const activeProviderCount = $derived.by(() => rows.filter((row) => row.is_enabled).length);

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			void goto('/dashboard');
			return;
		}
		void loadRows();
	});

	function toDraft(row: AIProviderConfigRow): AIConfigDraft {
		return {
			...row,
			apiKeyInput: '',
			showApiKey: false,
			saving: false,
			testing: false,
			deleting: false,
		};
	}

	async function loadRows() {
		loading = true;
		try {
			const response: AIProviderConfigResponse = await adminApi.getAIProviderConfigs();
			providerDefaults = response.provider_defaults;
			rows = response.items.map(toDraft);
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load AI provider settings', 'error');
		} finally {
			loading = false;
		}
	}

	async function addRow() {
		adding = true;
		try {
			const created = await adminApi.createAIProviderConfig({
				display_name: `Provider ${rows.length + 1}`,
				provider: 'OPENAI',
				model: providerDefaults.OPENAI || 'gpt-4.1-mini',
				temperature: 0.2,
				batch_size: 10,
				is_enabled: false,
			});
			rows = [...rows, toDraft(created)];
			toastStore.addToast('New AI configuration row created', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to create AI configuration row', 'error');
		} finally {
			adding = false;
		}
	}

	async function saveRow(row: AIConfigDraft) {
		row.saving = true;
		try {
			const saved = await adminApi.updateAIProviderConfig(row.id, {
				display_name: row.display_name,
				provider: row.provider,
				model: row.model,
				base_url: row.base_url || undefined,
				system_prompt: row.system_prompt || undefined,
				temperature: Number(row.temperature),
				batch_size: Number(row.batch_size),
				is_enabled: row.is_enabled,
				api_key: row.apiKeyInput.trim() || undefined,
			});
			rows = rows.map((item) => item.id === row.id ? toDraft(saved) : item);
			toastStore.addToast(saved.message || 'AI configuration saved', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save AI configuration', 'error');
		} finally {
			row.saving = false;
		}
	}

	async function activateRow(row: AIConfigDraft) {
		try {
			const activated = await adminApi.activateAIProviderConfig(row.id);
			rows = rows.map((item) => item.id === row.id ? toDraft(activated) : { ...item, is_enabled: false });
			toastStore.addToast(activated.message || 'Active AI provider updated', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to activate AI provider', 'error');
		}
	}

	async function testRow(row: AIConfigDraft) {
		row.testing = true;
		try {
			const result = await adminApi.testAIProviderConnection(row.id);
			lastTestPreview = {
				label: row.display_name,
				findings: result.preview.findings,
				diagnosis: result.preview.diagnosis,
				treatment: result.preview.treatment,
			};
			await loadRows();
			toastStore.addToast(result.message, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to test AI provider', 'error');
		} finally {
			row.testing = false;
		}
	}

	async function deleteRow(row: AIConfigDraft) {
		row.deleting = true;
		try {
			const result = await adminApi.deleteAIProviderConfig(row.id);
			rows = rows.filter((item) => item.id !== row.id);
			if (promptEditorId === row.id) {
				promptEditorId = null;
				promptDraft = '';
			}
			toastStore.addToast(result.message, 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to delete AI provider', 'error');
		} finally {
			row.deleting = false;
		}
	}

	function openPromptEditor(row: AIConfigDraft) {
		promptEditorId = row.id;
		promptDraft = row.system_prompt || '';
	}

	function resetPromptEditor() {
		promptEditorId = null;
		promptDraft = '';
	}

	async function savePromptEditor() {
		if (!promptEditorId) {
			return;
		}

		try {
			const saved = await adminApi.updateAIProviderConfig(promptEditorId, { system_prompt: promptDraft });
			rows = rows.map((item) => item.id === promptEditorId ? toDraft(saved) : item);
			toastStore.addToast(saved.message || 'System prompt saved', 'success');
			resetPromptEditor();
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save system prompt', 'error');
		}
	}

	function handleProviderChange(row: AIConfigDraft) {
		const previousDefault = providerDefaults[row.provider];
		if (!row.model || row.model === previousDefault) {
			row.model = providerDefaults[row.provider] || row.model;
		}
	}

	function providerLabel(provider: string) {
		return provider.replaceAll('_', ' ');
	}
</script>

<div class="space-y-4">
	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.98), rgba(247,250,255,0.96)); box-shadow: 0 12px 28px rgba(15,23,42,0.06);">
		<div class="flex items-start gap-3">
			<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
				style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid rgba(59,130,246,0.16);">
				<Sparkles class="h-5 w-5 text-blue-600" />
			</div>
			<div>
				<h2 class="text-sm font-bold uppercase tracking-[0.16em] text-slate-600">AI Provider Table</h2>
				<p class="mt-1 text-sm text-slate-500">Manage multiple saved AI endpoints here. Add creates a new editable row immediately, and only one row can be active for case-record drafting at a time.</p>
			</div>
		</div>
	</div>

	<div class="rounded-[24px] border border-slate-200 p-3"
		style="background: linear-gradient(to bottom, rgba(255,255,255,0.92), rgba(246,249,255,0.92)); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
		<SystemConfigTabs activeTab="ai" />
	</div>

	<div class="grid gap-4 md:grid-cols-3">
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Saved Providers</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{rows.length}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Active Providers</p>
			<p class="mt-3 text-3xl font-bold text-slate-900">{activeProviderCount}</p>
		</div>
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 10px 24px rgba(15,23,42,0.05);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Default OpenAI Model</p>
			<p class="mt-3 text-lg font-semibold text-slate-900">{providerDefaults.OPENAI || 'gpt-4.1-mini'}</p>
		</div>
	</div>

	<div class="rounded-[24px] border border-slate-200 p-4"
		style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Provider Matrix</p>
				<p class="mt-1 text-sm text-slate-500">Use Save for row edits, Prompt for the drafting instruction set, Test to verify credentials, and Activate to switch the live provider.</p>
			</div>
			<button
				type="button"
				class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
				onclick={addRow}
				disabled={adding}
			>
				{#if adding}
					<Loader2 class="h-4 w-4 animate-spin" />
				{:else}
					<Plus class="h-4 w-4" />
				{/if}
				Add Row
			</button>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<Loader2 class="h-7 w-7 animate-spin text-blue-600" />
			</div>
		{:else}
			<div class="mt-4 overflow-x-auto rounded-[18px] border border-slate-200">
				<table class="min-w-[1180px] w-full text-left text-sm">
					<thead style="background: linear-gradient(to bottom, rgba(241,245,249,0.98), rgba(248,250,252,0.98));">
						<tr class="text-slate-500">
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Service</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Base URL</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Model</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">API Key</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Batch</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Status</th>
							<th class="px-4 py-3 font-bold uppercase tracking-[0.14em]">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each rows as row (row.id)}
							<tr class="border-t border-slate-200 align-top">
								<td class="px-4 py-4">
									<input type="text" bind:value={row.display_name} class="w-full rounded-2xl border border-slate-200 px-3 py-2.5 text-sm" />
									<select class="mt-2 w-full rounded-2xl border border-slate-200 px-3 py-2.5 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600" bind:value={row.provider} onchange={() => handleProviderChange(row)}>
										<option value="OPENAI">OpenAI</option>
										<option value="ANTHROPIC">Anthropic</option>
										<option value="GEMINI">Gemini</option>
										<option value="OPENAI_COMPATIBLE">OpenAI Compatible</option>
									</select>
								</td>
								<td class="px-4 py-4">
									<input type="text" bind:value={row.base_url} placeholder="https://api.example.com/v1" class="w-full rounded-2xl border border-slate-200 px-3 py-2.5 text-sm" />
									<p class="mt-2 text-xs text-slate-400">Leave blank to use the provider default endpoint.</p>
								</td>
								<td class="px-4 py-4">
									<input type="text" bind:value={row.model} class="w-full rounded-2xl border border-slate-200 px-3 py-2.5 text-sm" />
									<div class="mt-2 flex items-center gap-2">
										<span class="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Temp</span>
										<input type="number" min="0" max="2" step="0.1" bind:value={row.temperature} class="w-24 rounded-2xl border border-slate-200 px-3 py-2 text-sm" />
									</div>
								</td>
								<td class="px-4 py-4">
									<div class="flex gap-2">
										<input type={row.showApiKey ? 'text' : 'password'} bind:value={row.apiKeyInput} placeholder={row.masked_api_key || 'Leave blank to keep existing'} class="min-w-[180px] flex-1 rounded-2xl border border-slate-200 px-3 py-2.5 text-sm" />
										<button type="button" class="rounded-2xl px-3 py-2.5 text-xs font-semibold text-slate-600 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={() => row.showApiKey = !row.showApiKey}>
											{row.showApiKey ? 'Hide' : 'Show'}
										</button>
									</div>
									<p class="mt-2 text-xs text-slate-400">Masked key stays unchanged until you enter a new one.</p>
								</td>
								<td class="px-4 py-4">
									<input type="number" min="1" max="500" bind:value={row.batch_size} class="w-24 rounded-2xl border border-slate-200 px-3 py-2.5 text-sm" />
									<p class="mt-2 text-xs text-slate-400">Saved for future batched drafting flows.</p>
								</td>
								<td class="px-4 py-4">
									<span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold {row.is_enabled ? 'text-emerald-700' : 'text-slate-500'}"
										style={row.is_enabled
											? 'background: rgba(16,185,129,0.14); border: 1px solid rgba(16,185,129,0.18);'
											: 'background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.14);'}>
										{row.is_enabled ? 'Active' : 'Inactive'}
									</span>
									<div class="mt-2 space-y-1 text-xs text-slate-400">
										<div>{providerLabel(row.provider)}</div>
										<div>{row.last_test_status || 'Not tested yet'}</div>
									</div>
								</td>
								<td class="px-4 py-4">
									<div class="flex flex-col gap-2">
										<button type="button" class="inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-white cursor-pointer disabled:opacity-60" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={() => saveRow(row)} disabled={row.saving}>
											{#if row.saving}
												<Loader2 class="h-3.5 w-3.5 animate-spin" />
											{:else}
												<Save class="h-3.5 w-3.5" />
											{/if}
											Save
										</button>
										<button type="button" class="inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={() => openPromptEditor(row)}>
											<WandSparkles class="h-3.5 w-3.5" /> Prompt
										</button>
										<button type="button" class="inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-blue-700 cursor-pointer disabled:opacity-60" style="background: rgba(59,130,246,0.12);" onclick={() => testRow(row)} disabled={row.testing}>
											{#if row.testing}
												<Loader2 class="h-3.5 w-3.5 animate-spin" />
											{:else}
												<TestTube2 class="h-3.5 w-3.5" />
											{/if}
											Test
										</button>
										<button type="button" class="inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold cursor-pointer disabled:opacity-60 {row.is_enabled ? 'text-emerald-700' : 'text-amber-700'}" style={row.is_enabled ? 'background: rgba(16,185,129,0.14);' : 'background: rgba(251,191,36,0.18);'} onclick={() => activateRow(row)} disabled={row.is_enabled}>
											<Bot class="h-3.5 w-3.5" /> {row.is_enabled ? 'Live' : 'Activate'}
										</button>
										<button type="button" class="inline-flex items-center justify-center gap-2 rounded-full px-3 py-2 text-xs font-semibold text-red-600 cursor-pointer disabled:opacity-60" style="background: rgba(248,113,113,0.12);" onclick={() => deleteRow(row)} disabled={row.deleting}>
											<Trash2 class="h-3.5 w-3.5" /> {row.deleting ? 'Deleting...' : 'Delete'}
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>

	{#if lastTestPreview}
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
			<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Latest Test Output</p>
			<p class="mt-2 text-sm font-semibold text-slate-900">{lastTestPreview.label}</p>
			<div class="mt-3 space-y-3 text-sm text-slate-700">
				<div><span class="font-semibold text-slate-900">Findings:</span> {lastTestPreview.findings}</div>
				<div><span class="font-semibold text-slate-900">Diagnosis:</span> {lastTestPreview.diagnosis}</div>
				<div><span class="font-semibold text-slate-900">Treatment:</span> {lastTestPreview.treatment}</div>
			</div>
		</div>
	{/if}

	{#if promptEditorId}
		<AquaModal title="Edit System Prompt" onclose={resetPromptEditor} panelClass="sm:max-w-[760px]">
			<div class="space-y-4">
				<p class="text-sm text-slate-500">This prompt is used when MIAS requests AI-generated case-record draft sections from the selected provider row.</p>
				<textarea rows="12" bind:value={promptDraft} class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"></textarea>
				<div class="flex justify-end gap-2">
					<button type="button" class="rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 cursor-pointer" style="background: rgba(148,163,184,0.12);" onclick={resetPromptEditor}>Cancel</button>
					<button type="button" class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer" style="background: linear-gradient(to bottom, #3b82f6, #2563eb);" onclick={savePromptEditor}>
						<Save class="h-4 w-4" /> Save Prompt
					</button>
				</div>
			</div>
		</AquaModal>
	{/if}
</div>