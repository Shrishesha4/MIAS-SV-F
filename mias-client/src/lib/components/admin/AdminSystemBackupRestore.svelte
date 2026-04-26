<script lang="ts">
	import { adminApi } from '$lib/api/admin';
	import { toastStore } from '$lib/stores/toast';
	import { Download, Upload, ShieldAlert, Loader2, FileArchive } from 'lucide-svelte';

	type SystemBackupImportResponse = {
		message: string;
		summary: { total_rows: number; tables: Record<string, number> };
	};

	const systemBackupAdminApi = adminApi as typeof adminApi & {
		downloadSystemBackup: () => Promise<Blob>;
		importSystemBackup: (file: File) => Promise<SystemBackupImportResponse>;
	};

	let exporting = $state(false);
	let importing = $state(false);
	let selectedFile = $state<File | null>(null);
	let lastImportSummary = $state<{ total_rows: number; tables: Record<string, number> } | null>(null);

	function formatTimestamp(date = new Date()): string {
		const pad = (value: number) => String(value).padStart(2, '0');
		return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
	}

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		selectedFile = input.files?.[0] ?? null;
		lastImportSummary = null;
	}

	async function handleExport() {
		exporting = true;
		try {
			const blob = await systemBackupAdminApi.downloadSystemBackup();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `mias_system_backup_${formatTimestamp()}.json`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
			toastStore.addToast('System backup downloaded', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to download backup', 'error');
		} finally {
			exporting = false;
		}
	}

	async function handleImport() {
		if (!selectedFile) {
			toastStore.addToast('Choose a backup file first', 'error');
			return;
		}
		importing = true;
		try {
			const result = await systemBackupAdminApi.importSystemBackup(selectedFile);
			lastImportSummary = result.summary;
			toastStore.addToast(result.message || 'System backup imported', 'success');
		} catch (error: any) {
			toastStore.addToast(error?.response?.data?.detail || 'Failed to import backup', 'error');
		} finally {
			importing = false;
		}
	}
</script>

<div class="space-y-4">
	<div class="rounded-3xl border border-blue-200 p-4"
		style="background: linear-gradient(to bottom, rgba(239,246,255,0.92), rgba(219,234,254,0.9)); box-shadow: 0 10px 24px rgba(37,99,235,0.12);">
		<div class="flex items-start gap-3">
			<div class="mt-0.5 rounded-full p-2 text-blue-700" style="background: rgba(59,130,246,0.15);">
				<ShieldAlert class="h-4 w-4" />
			</div>
			<div>
				<p class="text-sm font-bold text-blue-900">Backup & Restore</p>
				<p class="mt-1 text-xs text-blue-800/80">This exports and restores full system data for migration to a fresh installation. Import replaces existing data.</p>
			</div>
		</div>
	</div>

	<div class="grid gap-4 lg:grid-cols-2">
		<div class="rounded-3xl border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(248,250,252,0.95)); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
			<p class="text-sm font-bold text-slate-900">Create Backup</p>
			<p class="mt-1 text-xs text-slate-500">Downloads a JSON backup with users, clinics, labs, departments, forms, and all configured data.</p>
			<button
				type="button"
				onclick={handleExport}
				disabled={exporting}
				class="mt-4 inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5 disabled:opacity-60"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
			>
				{#if exporting}
					<Loader2 class="h-4 w-4 animate-spin" />
					Preparing...
				{:else}
					<Download class="h-4 w-4" />
					Download Backup
				{/if}
			</button>
		</div>

		<div class="rounded-3xl border border-slate-200 p-4"
			style="background: linear-gradient(to bottom, rgba(255,255,255,0.96), rgba(248,250,252,0.95)); box-shadow: 0 10px 24px rgba(15,23,42,0.06);">
			<p class="text-sm font-bold text-slate-900">Restore Backup</p>
			<p class="mt-1 text-xs text-slate-500">Import a previously exported JSON backup. Existing database rows will be replaced.</p>
			<label class="mt-4 block">
				<input
					type="file"
					accept="application/json,.json"
					onchange={onFileChange}
					class="block w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700"
				/>
			</label>
			<button
				type="button"
				onclick={handleImport}
				disabled={importing || !selectedFile}
				class="mt-3 inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-white cursor-pointer transition-all hover:-translate-y-[1px] active:translate-y-0.5 disabled:opacity-60"
				style="background: linear-gradient(to bottom, #3b82f6, #2563eb); border: 1px solid rgba(0,0,0,0.15); box-shadow: 0 4px 12px rgba(37,99,235,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
			>
				{#if importing}
					<Loader2 class="h-4 w-4 animate-spin" />
					Importing...
				{:else}
					<Upload class="h-4 w-4" />
					Import Backup
				{/if}
			</button>
		</div>
	</div>

	{#if lastImportSummary}
		<div class="rounded-3xl border border-emerald-200 p-4"
			style="background: linear-gradient(to bottom, rgba(236,253,245,0.92), rgba(209,250,229,0.9)); box-shadow: 0 10px 24px rgba(16,185,129,0.12);">
			<div class="flex items-start gap-3">
				<div class="mt-0.5 rounded-full p-2 text-emerald-700" style="background: rgba(16,185,129,0.15);">
					<FileArchive class="h-4 w-4" />
				</div>
				<div class="w-full">
					<p class="text-sm font-bold text-emerald-900">Import complete</p>
					<p class="mt-1 text-xs text-emerald-800/80">Total rows restored: {lastImportSummary.total_rows}</p>
					<div class="mt-3 max-h-56 overflow-auto rounded-xl border border-emerald-200 bg-white/80 p-2">
						{#each Object.entries(lastImportSummary.tables) as [tableName, count] (tableName)}
							<div class="flex items-center justify-between border-b border-emerald-100 py-1 text-xs last:border-b-0">
								<span class="font-medium text-slate-700">{tableName}</span>
								<span class="font-bold text-emerald-700">{count}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
