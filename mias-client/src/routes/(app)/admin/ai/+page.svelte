<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { authStore } from '$lib/stores/auth';
	import {
		adminApi,
		type AIProviderConfig,
		type AIProviderType,
	} from '$lib/api/admin';
	import AdminScaffold from '$lib/components/layout/AdminScaffold.svelte';
	import { adminPageNavItems } from '$lib/config/admin-nav';
	import { toastStore } from '$lib/stores/toast';
	import {
		BrainCircuit,
		Bot,
		CheckCircle2,
		KeyRound,
		Link2,
		Loader2,
		Save,
		Sparkles,
		XCircle,
	} from 'lucide-svelte';

	const auth = get(authStore);
	const providers: AIProviderType[] = ['OPENAI', 'ANTHROPIC', 'GEMINI', 'OPENAI_COMPATIBLE'];

	let loading = $state(true);
	let saving = $state(false);
	let testing = $state(false);
	let config = $state<AIProviderConfig | null>(null);
	let form = $state({
		provider: 'OPENAI' as AIProviderType,
		model: '',
		base_url: '',
		system_prompt: '',
		temperature: 0.2,
		is_enabled: false,
	});
	let apiKeyInput = $state('');
	let testPreview = $state<{ findings: string; diagnosis: string; treatment: string } | null>(null);

	const providerDefaults = $derived(config?.provider_defaults ?? {});

	onMount(() => {
		if (auth.role !== 'ADMIN') {
			goto('/dashboard');
			return;
		}
		loadConfig();
	});

	async function loadConfig() {
		loading = true;
		try {
			const next = await adminApi.getAIProviderConfig();
			config = next;
			form = {
				provider: next.provider,
				model: next.model,
				base_url: next.base_url || '',
				system_prompt: next.system_prompt || '',
				temperature: next.temperature,
				is_enabled: next.is_enabled,
			};
			apiKeyInput = '';
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to load AI configuration', 'error');
		} finally {
			loading = false;
		}
	}

	function selectProvider(provider: AIProviderType) {
		form.provider = provider;
		form.model = providerDefaults[provider] || form.model;
	}

	async function saveConfig() {
		saving = true;
		try {
			const next = await adminApi.updateAIProviderConfig({
				provider: form.provider,
				model: form.model,
				api_key: apiKeyInput || undefined,
				base_url: form.base_url || undefined,
				system_prompt: form.system_prompt || undefined,
				temperature: Number(form.temperature),
				is_enabled: form.is_enabled,
			});
			config = next;
			apiKeyInput = '';
			toastStore.addToast(next.message || 'AI provider settings saved', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to save AI configuration', 'error');
		} finally {
			saving = false;
		}
	}

	async function testConnection() {
		testing = true;
		try {
			const result = await adminApi.testAIProviderConnection();
			testPreview = result.preview;
			toastStore.addToast(result.message, 'success');
			await loadConfig();
		} catch (error: any) {
			testPreview = null;
			toastStore.addToast(error?.response?.data?.detail || 'Failed to test AI provider', 'error');
			await loadConfig();
		} finally {
			testing = false;
		}
	}
</script>

<AdminScaffold
	title="AI Provider"
	titleIcon={BrainCircuit}
	navItems={adminPageNavItems}
	activeNav="ai"
	backHref="/admin"
>
	<div class="space-y-4">
		<div class="rounded-[24px] border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, rgba(255,255,255,0.97), rgba(248,250,253,0.96)); box-shadow: 0 10px 26px rgba(15,23,42,0.06);">
			<div class="flex items-start gap-3">
				<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
					style="background: linear-gradient(to bottom, #eff6ff, #dbeafe); border: 1px solid rgba(59,130,246,0.16);">
					<Sparkles class="h-5 w-5 text-blue-600" />
				</div>
				<div>
					<h2 class="text-sm font-bold uppercase tracking-[0.16em] text-slate-600">Case Record AI Drafting</h2>
					<p class="mt-1 text-sm text-slate-500">Configure one provider here, then students and faculty can generate Findings, Diagnosis, and Treatment drafts directly inside the case-record flow.</p>
				</div>
			</div>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-16">
				<Loader2 class="h-8 w-8 animate-spin text-blue-600" />
			</div>
		{:else}
			<div class="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)]">
				<div class="space-y-4 rounded-[24px] border border-slate-200 p-4"
					style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
					<div>
						<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Provider</p>
						<div class="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
							{#each providers as provider}
								<button
									type="button"
									class="rounded-2xl px-3 py-3 text-xs font-bold uppercase tracking-[0.12em] cursor-pointer"
									style={form.provider === provider
										? 'background: linear-gradient(to bottom, #3b82f6, #2563eb); color: white; box-shadow: 0 10px 20px rgba(37,99,235,0.22);'
										: 'background: linear-gradient(to bottom, #ffffff, #f8fafc); color: #64748b; border: 1px solid rgba(148,163,184,0.2);'}
									onclick={() => selectProvider(provider)}
								>
									{provider.replaceAll('_', ' ')}
								</button>
							{/each}
						</div>
					</div>

					<div class="grid gap-4 md:grid-cols-2">
						<div>
							<label for="ai-provider-model" class="mb-1 block text-sm font-medium text-slate-700">Model</label>
							<input
								id="ai-provider-model"
								type="text"
								bind:value={form.model}
								placeholder={providerDefaults[form.provider] || 'Enter model name'}
								class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
							/>
						</div>
						<div>
							<label for="ai-provider-temperature" class="mb-1 block text-sm font-medium text-slate-700">Temperature</label>
							<input
								id="ai-provider-temperature"
								type="number"
								min="0"
								max="2"
								step="0.1"
								bind:value={form.temperature}
								class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
							/>
						</div>
					</div>

					<div>
						<label for="ai-provider-base-url" class="mb-1 block text-sm font-medium text-slate-700">Base URL</label>
						<input
							id="ai-provider-base-url"
							type="text"
							bind:value={form.base_url}
							placeholder="Optional override for self-hosted or compatible providers"
							class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
						/>
					</div>

					<div>
						<label for="ai-provider-api-key" class="mb-1 block text-sm font-medium text-slate-700">API Key</label>
						<input
							id="ai-provider-api-key"
							type="password"
							bind:value={apiKeyInput}
							placeholder={config?.masked_api_key || 'Leave blank to keep the current key'}
							class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
						/>
						<p class="mt-1 text-xs text-slate-400">Existing key stays unchanged unless you enter a new one.</p>
					</div>

					<div>
						<label for="ai-provider-system-prompt" class="mb-1 block text-sm font-medium text-slate-700">System Prompt</label>
						<textarea
							id="ai-provider-system-prompt"
							rows="6"
							bind:value={form.system_prompt}
							class="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
						></textarea>
					</div>

					<label class="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
						<div>
							<p class="text-sm font-semibold text-slate-800">Enable this provider</p>
							<p class="text-xs text-slate-400">The case-record submit flow uses only the enabled provider.</p>
						</div>
						<input type="checkbox" bind:checked={form.is_enabled} class="h-4 w-4" />
					</label>

					<div class="flex flex-wrap gap-2">
						<button
							type="button"
							class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer disabled:opacity-60"
							style="background: linear-gradient(to bottom, #3b82f6, #2563eb);"
							onclick={saveConfig}
							disabled={saving}
						>
							{#if saving}
								<Loader2 class="h-4 w-4 animate-spin" />
							{:else}
								<Save class="h-4 w-4" />
							{/if}
							Save Settings
						</button>
						<button
							type="button"
							class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold cursor-pointer disabled:opacity-60"
							style="background: linear-gradient(to bottom, #ffffff, #eff6ff); color: #2563eb; border: 1px solid rgba(59,130,246,0.18);"
							onclick={testConnection}
							disabled={testing}
						>
							{#if testing}
								<Loader2 class="h-4 w-4 animate-spin" />
							{:else}
								<Link2 class="h-4 w-4" />
							{/if}
							Test Connection
						</button>
					</div>
				</div>

				<div class="space-y-4">
					<div class="rounded-[24px] border border-slate-200 p-4"
						style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
						<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Connection Status</p>
						<div class="mt-3 flex items-center gap-3">
							<div class="flex h-11 w-11 items-center justify-center rounded-full"
								style={config?.last_test_status === 'SUCCESS'
									? 'background: rgba(34,197,94,0.12); color: #16a34a;'
									: 'background: rgba(248,113,113,0.12); color: #dc2626;'}>
								{#if config?.last_test_status === 'SUCCESS'}
									<CheckCircle2 class="h-5 w-5" />
								{:else}
									<XCircle class="h-5 w-5" />
								{/if}
							</div>
							<div>
								<p class="text-sm font-semibold text-slate-800">{config?.last_test_status === 'SUCCESS' ? 'Provider reachable' : 'Not verified yet'}</p>
								<p class="text-xs text-slate-400">{config?.last_tested_at ? `Last tested ${new Date(config.last_tested_at).toLocaleString()}` : 'Run a connection test after saving credentials.'}</p>
							</div>
						</div>
						{#if config?.last_error}
							<p class="mt-3 rounded-2xl bg-red-50 px-3 py-2 text-xs text-red-600">{config.last_error}</p>
						{/if}
					</div>

					<div class="rounded-[24px] border border-slate-200 p-4"
						style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
						<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Saved Configuration</p>
						<div class="mt-3 space-y-3 text-sm text-slate-600">
							<div class="flex items-center gap-2"><Bot class="h-4 w-4 text-slate-400" /> {config?.provider || 'OPENAI'} · {config?.model || 'Not set'}</div>
							<div class="flex items-center gap-2"><KeyRound class="h-4 w-4 text-slate-400" /> {config?.masked_api_key || 'No API key saved'}</div>
							<div class="flex items-center gap-2"><Link2 class="h-4 w-4 text-slate-400" /> {config?.base_url || 'Using provider default endpoint'}</div>
						</div>
					</div>

					{#if testPreview}
						<div class="rounded-[24px] border border-slate-200 p-4"
							style="background: linear-gradient(to bottom, #ffffff, #f8fafc); box-shadow: 0 14px 30px rgba(15,23,42,0.06);">
							<p class="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Latest Test Output</p>
							<div class="mt-3 space-y-3 text-sm text-slate-700">
								<div><span class="font-semibold text-slate-900">Findings:</span> {testPreview.findings}</div>
								<div><span class="font-semibold text-slate-900">Diagnosis:</span> {testPreview.diagnosis}</div>
								<div><span class="font-semibold text-slate-900">Treatment:</span> {testPreview.treatment}</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</AdminScaffold>