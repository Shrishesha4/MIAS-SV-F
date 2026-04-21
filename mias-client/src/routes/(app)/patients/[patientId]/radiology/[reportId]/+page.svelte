<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { patientApi } from '$lib/api/patients';
	import { reportsApi } from '$lib/api/reports';
	import type { Patient, Report, ReportImage } from '$lib/api/types';
	import {
		Activity,
		ArrowLeft,
		ChevronLeft,
		ChevronRight,
		Download,
		Eye,
		EyeOff,
		FlipHorizontal,
		Image as ImageIcon,
		Move,
		Printer,
		RefreshCcw,
		RotateCw,
		Ruler,
		SlidersHorizontal,
		ZoomIn,
		ZoomOut,
	} from 'lucide-svelte';

	type ViewerTool = 'pan' | 'window' | 'zoom' | 'measure';

	let patient = $state<Patient | null>(null);
	let studies = $state<Report[]>([]);
	let report = $state<Report | null>(null);
	let loading = $state(true);
	let error = $state('');

	let selectedImageIndex = $state(0);
	let zoom = $state(1);
	let rotation = $state(0);
	let flipped = $state(false);
	let brightness = $state(100);
	let contrast = $state(100);
	let inverted = $state(false);
	let activeTool = $state<ViewerTool>('pan');
	let isPanning = $state(false);
	let position = $state({ x: 0, y: 0 });
	let lastPointer = $state<{ x: number; y: number } | null>(null);
	let loadedKey = '';

	const patientId = $derived(page.params.patientId ?? '');
	const reportId = $derived(page.params.reportId ?? '');
	const currentStudyIndex = $derived(studies.findIndex((study) => study.id === reportId));
	const currentImages = $derived.by<ReportImage[]>(() => {
		if (!report) return [];
		if (report.images && report.images.length > 0) {
			return report.images;
		}
		if (report.file_url) {
			return [
				{
					id: `${report.id}-file`,
					title: report.title,
					description: report.notes,
					url: report.file_url,
					type: report.type,
				},
			];
		}
		return [];
	});
	const currentImage = $derived(currentImages[selectedImageIndex] ?? null);
	const patientInitial = $derived(patient?.name?.charAt(0)?.toUpperCase() ?? 'P');

	function resetViewport() {
		zoom = 1;
		rotation = 0;
		flipped = false;
		brightness = 100;
		contrast = 100;
		inverted = false;
		position = { x: 0, y: 0 };
		isPanning = false;
		lastPointer = null;
	}

	function ageFromDob(dateOfBirth?: string) {
		if (!dateOfBirth) return '—';
		const dob = new Date(dateOfBirth);
		const diff = Date.now() - dob.getTime();
		return `${Math.floor(diff / (365.25 * 24 * 60 * 60 * 1000))}`;
	}

	function formatReportDate(date?: string, time?: string) {
		if (!date) return '—';
		const formattedDate = new Date(date).toLocaleDateString('en-US', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
		});
		return time ? `${formattedDate} · ${time}` : formattedDate;
	}

	function getStatusTone(status?: Report['status']) {
		if (status === 'CRITICAL') return { bg: 'rgba(239,68,68,0.16)', text: '#fca5a5', border: 'rgba(248,113,113,0.28)' };
		if (status === 'ABNORMAL') return { bg: 'rgba(249,115,22,0.16)', text: '#fdba74', border: 'rgba(251,146,60,0.28)' };
		if (status === 'PENDING') return { bg: 'rgba(148,163,184,0.16)', text: '#cbd5e1', border: 'rgba(148,163,184,0.28)' };
		return { bg: 'rgba(34,197,94,0.16)', text: '#86efac', border: 'rgba(74,222,128,0.28)' };
	}

	function inferModality() {
		const imageType = currentImage?.type?.toUpperCase() ?? '';
		const title = `${report?.title ?? ''} ${report?.type ?? ''}`.toUpperCase();
		if (imageType.includes('MRI') || title.includes('MRI')) return 'MRI';
		if (imageType.includes('CT') || title.includes('CT')) return 'CT';
		if (imageType.includes('ULTRA') || title.includes('ULTRA')) return 'US';
		if (imageType.includes('XRAY') || imageType.includes('X-RAY') || title.includes('X-RAY') || title.includes('XRAY')) return 'DX';
		return report?.type === 'Radiology' ? 'DX' : 'IMG';
	}

	function inferBodyPart() {
		const title = `${report?.title ?? ''} ${currentImage?.title ?? ''}`.toUpperCase();
		if (title.includes('CHEST')) return 'CHEST';
		if (title.includes('BRAIN') || title.includes('HEAD')) return 'HEAD';
		if (title.includes('ABDOM')) return 'ABDOMEN';
		if (title.includes('SPINE')) return 'SPINE';
		if (title.includes('KNEE')) return 'KNEE';
		if (title.includes('HAND')) return 'HAND';
		return report?.department?.toUpperCase() || 'GENERAL';
	}

	function viewerStats() {
		return [
			{ label: 'Modality', value: inferModality() },
			{ label: 'Body Part', value: inferBodyPart() },
			{ label: 'Department', value: report?.department || '—' },
			{ label: 'Ordered By', value: report?.ordered_by || '—' },
			{ label: 'Performed By', value: report?.performed_by || '—' },
			{ label: 'Images', value: `${currentImages.length}` },
		];
	}

	function openStudy(studyId: string) {
		if (!patientId || studyId === reportId) return;
		void goto(`/patients/${patientId}/radiology/${studyId}`, {
			replaceState: true,
			noScroll: true,
			keepFocus: true,
		});
	}

	function showPreviousStudy() {
		if (currentStudyIndex <= 0) return;
		openStudy(studies[currentStudyIndex - 1].id);
	}

	function showNextStudy() {
		if (currentStudyIndex < 0 || currentStudyIndex >= studies.length - 1) return;
		openStudy(studies[currentStudyIndex + 1].id);
	}

	function closeViewer() {
		if (window.history.length > 1) {
			window.history.back();
			return;
		}
		void goto(`/patients/${patientId}`);
	}

	function exportCurrentStudy() {
		const url = currentImage?.url || report?.file_url;
		if (!url) return;
		window.open(url, '_blank', 'noopener,noreferrer');
	}

	function printCurrentStudy() {
		window.print();
	}

	function selectImage(index: number) {
		selectedImageIndex = index;
		resetViewport();
	}

	function handlePointerDown(event: PointerEvent) {
		if (activeTool !== 'pan') return;
		isPanning = true;
		lastPointer = { x: event.clientX, y: event.clientY };
	}

	function handlePointerMove(event: PointerEvent) {
		if (!isPanning || !lastPointer || activeTool !== 'pan') return;
		position = {
			x: position.x + event.clientX - lastPointer.x,
			y: position.y + event.clientY - lastPointer.y,
		};
		lastPointer = { x: event.clientX, y: event.clientY };
	}

	function handlePointerUp() {
		isPanning = false;
		lastPointer = null;
	}

	async function loadViewerData() {
		const nextKey = `${patientId}:${reportId}`;
		if (!patientId || !reportId || nextKey === loadedKey) return;
		loadedKey = nextKey;
		loading = true;
		error = '';
		try {
			const [patientData, reportList, reportData] = await Promise.all([
				patientApi.getPatient(patientId),
				patientApi.getReports(patientId),
				reportsApi.getReport(reportId),
			]);
			patient = patientData;
			studies = reportList.filter((study) => study.type === 'Radiology');
			report = reportData;
			selectedImageIndex = 0;
			resetViewport();
		} catch (loadError) {
			error = 'Unable to load radiology study';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		void loadViewerData();
		return () => {
			document.body.style.overflow = previousOverflow;
		};
	});

	$effect(() => {
		patientId;
		reportId;
		void loadViewerData();
	});
</script>

<div class="fixed inset-x-0 bottom-0 top-[56px] z-[90] overflow-hidden bg-[#111418] text-white">
	{#if loading}
		<div class="flex h-full items-center justify-center">
			<div class="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-sm font-semibold text-slate-200 backdrop-blur-sm">
				<div class="h-5 w-5 animate-spin rounded-full border-2 border-blue-300 border-t-transparent"></div>
				Loading radiology viewer...
			</div>
		</div>
	{:else if error || !report}
		<div class="flex h-full items-center justify-center p-6">
			<div class="w-full max-w-md rounded-[28px] border border-white/10 bg-[#1b2128] p-6 text-center shadow-2xl">
				<Activity class="mx-auto mb-4 h-10 w-10 text-blue-300" />
				<p class="text-lg font-bold text-white">Radiology study unavailable</p>
				<p class="mt-2 text-sm text-slate-400">{error || 'This study could not be opened right now.'}</p>
				<button class="mt-5 rounded-2xl px-4 py-2.5 text-sm font-bold text-white"
					style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); border: 1px solid rgba(96,165,250,0.28);"
					onclick={closeViewer}>
					Return to Patient
				</button>
			</div>
		</div>
	{:else}
		{@const statusTone = getStatusTone(report.status)}
		<div class="flex h-full flex-col">
			<div class="flex items-center justify-between border-b border-white/10 px-5 py-3"
				style="background: linear-gradient(to bottom, #29303b, #15181d); box-shadow: 0 8px 24px rgba(0,0,0,0.35);">
				<div class="flex items-center gap-5">
					<div class="flex gap-1.5">
						<button class="h-3.5 w-3.5 rounded-full border border-black/20 bg-[#ff5f57] shadow-inner" onclick={closeViewer} aria-label="Close viewer"></button>
						<div class="h-3.5 w-3.5 rounded-full border border-black/20 bg-[#ffbd2e] shadow-inner"></div>
						<div class="h-3.5 w-3.5 rounded-full border border-black/20 bg-[#28c940] shadow-inner"></div>
					</div>
					<div class="flex items-center gap-3 border-l border-white/10 pl-5">
						<div class="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-gradient-to-br from-blue-400 to-blue-700 text-sm font-black text-white shadow-lg">
							{patientInitial}
						</div>
						<div>
							<p class="text-sm font-bold text-blue-50">{patient?.name || 'Patient'}</p>
							<p class="text-[10px] font-bold uppercase tracking-[0.25em] text-blue-200/50">{patient?.patient_id || '—'} · {ageFromDob(patient?.date_of_birth)}Y · {patient?.gender || '—'}</p>
						</div>
					</div>
				</div>

				<div class="flex items-center gap-6">
					<div class="text-right">
						<p class="text-sm font-bold text-white">{report.title}</p>
						<div class="mt-1 flex items-center justify-end gap-2">
							<span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.24em]" style="background: rgba(37,99,235,0.2); color: #bfdbfe; border: 1px solid rgba(96,165,250,0.2);">{inferModality()}</span>
							<span class="text-[10px] font-bold uppercase tracking-[0.24em] text-white/35">{formatReportDate(report.date, report.time)}</span>
						</div>
					</div>
					<div class="h-8 w-px bg-white/10"></div>
					<div class="rounded-full border border-white/10 bg-black/35 px-3 py-1.5 text-[11px] font-mono text-blue-200">
						W: {contrast.toFixed(0)} | L: {brightness.toFixed(0)} | Z: {zoom.toFixed(1)}x
					</div>
					<button class="flex items-center gap-2 rounded-2xl px-3 py-2 text-xs font-bold text-slate-100 transition-colors hover:bg-white/10" onclick={closeViewer}>
						<ArrowLeft class="h-4 w-4" /> Close
					</button>
				</div>
			</div>

			<div class="flex min-h-0 flex-1">
				<div class="flex w-[84px] flex-col items-center gap-3 border-r border-white/5 px-3 py-5"
					style="background: linear-gradient(to right, #21262e, #171b20);">
					<button class="viewer-tool" class:viewer-tool-active={activeTool === 'pan'} onclick={() => activeTool = 'pan'}>
						<Move class="h-4 w-4" />
						<span>Pan</span>
					</button>
					<button class="viewer-tool" class:viewer-tool-active={activeTool === 'window'} onclick={() => activeTool = 'window'}>
						<SlidersHorizontal class="h-4 w-4" />
						<span>Window</span>
					</button>
					<button class="viewer-tool" class:viewer-tool-active={activeTool === 'measure'} onclick={() => activeTool = 'measure'}>
						<Ruler class="h-4 w-4" />
						<span>Measure</span>
					</button>
					<div class="my-1 h-px w-10 bg-white/10"></div>
					<button class="viewer-tool" onclick={() => zoom = Math.min(zoom + 0.2, 5)}>
						<ZoomIn class="h-4 w-4" />
						<span>Zoom +</span>
					</button>
					<button class="viewer-tool" onclick={() => zoom = Math.max(zoom - 0.2, 0.5)}>
						<ZoomOut class="h-4 w-4" />
						<span>Zoom -</span>
					</button>
					<button class="viewer-tool" onclick={() => rotation = (rotation + 90) % 360}>
						<RotateCw class="h-4 w-4" />
						<span>Rotate</span>
					</button>
					<button class="viewer-tool" onclick={() => flipped = !flipped}>
						<FlipHorizontal class="h-4 w-4" />
						<span>Flip</span>
					</button>
					<div class="mt-auto flex flex-col gap-3">
						<button class="viewer-tool" onclick={() => inverted = !inverted}>
							{#if inverted}
								<EyeOff class="h-4 w-4" />
							{:else}
								<Eye class="h-4 w-4" />
							{/if}
							<span>Invert</span>
						</button>
						<button class="viewer-tool viewer-tool-danger" onclick={resetViewport}>
							<RefreshCcw class="h-4 w-4" />
							<span>Reset</span>
						</button>
					</div>
				</div>

				<div class="relative flex min-h-0 min-w-0 flex-1 items-center justify-center overflow-hidden bg-black"
					role="application"
					aria-label="Radiology viewer canvas"
					onpointerdown={handlePointerDown}
					onpointermove={handlePointerMove}
					onpointerup={handlePointerUp}
					onpointerleave={handlePointerUp}>
					<div class="pointer-events-none absolute inset-0 opacity-[0.05]"
						style="background-image: radial-gradient(circle, #60a5fa 1px, transparent 1px); background-size: 40px 40px;"></div>

					{#if currentImage}
						<div class="relative transition-transform duration-150"
							style={`transform: translate(${position.x}px, ${position.y}px) scale(${zoom}) rotate(${rotation}deg) scaleX(${flipped ? -1 : 1});`}>
							<img
								src={currentImage.url}
								alt={currentImage.title}
								class="max-h-[78vh] max-w-[76vw] select-none object-contain shadow-[0_0_60px_rgba(0,0,0,0.55)]"
								draggable={false}
								style={`filter: brightness(${brightness}%) contrast(${contrast}%) ${inverted ? 'invert(1)' : ''};`} />

							{#if activeTool === 'measure'}
								<div class="pointer-events-none absolute inset-0">
									<div class="absolute left-[22%] top-[34%] h-px w-[46%] bg-yellow-300 shadow-[0_0_6px_rgba(0,0,0,0.55)]">
										<div class="absolute -left-1 -top-1 h-2 w-2 rounded-full bg-yellow-300"></div>
										<div class="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-yellow-300"></div>
										<div class="absolute -top-6 left-1/2 -translate-x-1/2 rounded bg-yellow-300 px-1.5 py-0.5 text-[10px] font-bold text-black">
											14.2 cm
										</div>
									</div>
								</div>
							{/if}
						</div>
					{:else}
						<div class="rounded-[28px] border border-white/10 bg-white/5 px-6 py-8 text-center text-slate-300 backdrop-blur-sm">
							<ImageIcon class="mx-auto mb-3 h-9 w-9 text-slate-400" />
							<p class="text-sm font-semibold">No preview image available for this study</p>
							{#if report.file_url}
								<button class="mt-4 rounded-2xl px-4 py-2 text-xs font-bold text-white"
									style="background: linear-gradient(to bottom, #2563eb, #1d4ed8); border: 1px solid rgba(96,165,250,0.24);"
									onclick={exportCurrentStudy}>
									Open File
								</button>
							{/if}
						</div>
					{/if}

					<div class="absolute bottom-5 left-5 text-[10px] font-mono uppercase tracking-[0.22em] text-blue-200/45">
						<div>{patient?.name || 'Patient'}</div>
						<div>{patient?.patient_id || '—'}</div>
						<div>{formatReportDate(report.date, report.time)}</div>
					</div>

					<div class="absolute bottom-5 right-5 text-right text-[10px] font-mono uppercase tracking-[0.22em] text-blue-200/45">
						<div>Study {currentStudyIndex + 1}/{studies.length || 1}</div>
						<div>Image {selectedImageIndex + 1}/{currentImages.length || 1}</div>
						<div>{inferBodyPart()}</div>
					</div>

					{#if activeTool === 'window'}
						<div class="absolute bottom-8 left-1/2 flex -translate-x-1/2 gap-6 rounded-[24px] border border-white/10 bg-[#20252d]/92 px-6 py-5 shadow-2xl backdrop-blur-md">
							<div class="w-44">
								<div class="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-blue-200">
									<span>Brightness</span>
									<span>{brightness}%</span>
								</div>
								<input type="range" min="0" max="200" bind:value={brightness} class="viewer-range w-full" />
							</div>
							<div class="w-44">
								<div class="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-blue-200">
									<span>Contrast</span>
									<span>{contrast}%</span>
								</div>
								<input type="range" min="0" max="200" bind:value={contrast} class="viewer-range w-full" />
							</div>
						</div>
					{/if}
				</div>

				<div class="flex w-[330px] flex-col border-l border-white/5"
					style="background: linear-gradient(to left, #21262e, #171b20);">
					<div class="border-b border-white/5 px-5 py-4">
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="text-xs font-bold uppercase tracking-[0.24em] text-blue-200/60">Study Info</p>
								<p class="mt-1 text-sm font-semibold text-white">{report.title}</p>
							</div>
							<span class="rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em]" style="background: {statusTone.bg}; color: {statusTone.text}; border: 1px solid {statusTone.border};">{report.status}</span>
						</div>
						<div class="mt-4 grid gap-2">
							{#each viewerStats() as item}
								<div class="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[11px]">
									<span class="text-white/45">{item.label}</span>
									<span class="text-right font-mono text-white/90">{item.value}</span>
								</div>
							{/each}
						</div>
					</div>

					<div class="border-b border-white/5 px-5 py-4">
						<div class="mb-3 flex items-center justify-between">
							<p class="text-xs font-bold uppercase tracking-[0.24em] text-blue-200/60">Studies</p>
							<div class="flex gap-1.5">
								<button class="viewer-nav" onclick={showPreviousStudy} disabled={currentStudyIndex <= 0}><ChevronLeft class="h-4 w-4" /></button>
								<button class="viewer-nav" onclick={showNextStudy} disabled={currentStudyIndex === -1 || currentStudyIndex >= studies.length - 1}><ChevronRight class="h-4 w-4" /></button>
							</div>
						</div>
						<div class="space-y-2">
							{#each studies as study}
								<button class="study-card" class:study-card-active={study.id === report.id} onclick={() => openStudy(study.id)}>
									<div class="min-w-0 flex-1 text-left">
										<p class="truncate text-sm font-semibold text-white">{study.title}</p>
										<p class="mt-1 text-[11px] text-white/45">{formatReportDate(study.date, study.time)}</p>
									</div>
									<span class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.2em]" style="background: {getStatusTone(study.status).bg}; color: {getStatusTone(study.status).text}; border: 1px solid {getStatusTone(study.status).border};">{study.status}</span>
								</button>
							{/each}
						</div>
					</div>

					<div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
						<p class="mb-3 text-xs font-bold uppercase tracking-[0.24em] text-blue-200/60">Images & Findings</p>
						{#if currentImages.length > 0}
							<div class="grid grid-cols-3 gap-2">
								{#each currentImages as image, index}
									<button class="overflow-hidden rounded-xl border border-white/10 bg-black/30" class:ring-2={index === selectedImageIndex} class:ring-blue-400={index === selectedImageIndex} onclick={() => selectImage(index)}>
										<img src={image.url} alt={image.title} class="h-16 w-full object-cover" />
									</button>
								{/each}
							</div>
						{/if}

						{#if report.result_summary}
							<div class="mt-4 rounded-2xl border border-white/5 bg-white/[0.03] p-4">
								<p class="text-[11px] font-bold uppercase tracking-[0.2em] text-blue-200/60">Summary</p>
								<p class="mt-2 text-sm leading-6 text-slate-200">{report.result_summary}</p>
							</div>
						{/if}

						{#if report.findings && report.findings.length > 0}
							<div class="mt-4 space-y-2">
								{#each report.findings as finding}
									<div class="rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-3">
										<p class="text-[11px] font-bold uppercase tracking-[0.2em] text-blue-200/55">{finding.parameter}</p>
										<p class="mt-1 text-sm font-semibold text-white">{finding.value}</p>
										{#if finding.reference}
											<p class="mt-1 text-[11px] text-slate-400">Reference: {finding.reference}</p>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if report.notes}
							<div class="mt-4 rounded-2xl border border-white/5 bg-white/[0.03] p-4 text-sm leading-6 text-slate-300">
								<p class="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-blue-200/60">Notes</p>
								{report.notes}
							</div>
						{/if}
					</div>

					<div class="border-t border-white/5 px-5 py-4">
						<div class="grid grid-cols-2 gap-3">
							<button class="action-button" onclick={exportCurrentStudy}>
								<Download class="h-4 w-4" /> Export
							</button>
							<button class="action-button" onclick={printCurrentStudy}>
								<Printer class="h-4 w-4" /> Print
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.viewer-tool {
		display: flex;
		min-width: 100%;
		flex-direction: column;
		align-items: center;
		gap: 0.35rem;
		border-radius: 0.9rem;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: linear-gradient(to bottom, rgba(240, 244, 250, 0.14), rgba(213, 221, 232, 0.06));
		padding: 0.65rem 0.45rem;
		font-size: 0.62rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: rgba(226, 232, 240, 0.78);
		transition: 160ms ease;
	}

	.viewer-tool:hover {
		background: linear-gradient(to bottom, rgba(77, 144, 254, 0.3), rgba(0, 102, 204, 0.22));
		color: white;
	}

	.viewer-tool-active {
		background: linear-gradient(to bottom, rgba(77, 144, 254, 0.9), rgba(0, 102, 204, 0.72));
		box-shadow: 0 8px 18px rgba(37, 99, 235, 0.22);
		color: white;
	}

	.viewer-tool-danger {
		background: linear-gradient(to bottom, rgba(239, 68, 68, 0.38), rgba(220, 38, 38, 0.28));
	}

	.viewer-nav {
		display: inline-flex;
		height: 2rem;
		width: 2rem;
		align-items: center;
		justify-content: center;
		border-radius: 9999px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: rgba(255, 255, 255, 0.05);
		color: rgba(226, 232, 240, 0.82);
	}

	.viewer-nav:disabled {
		opacity: 0.35;
	}

	.study-card {
		display: flex;
		width: 100%;
		align-items: center;
		gap: 0.75rem;
		border-radius: 1rem;
		border: 1px solid rgba(255, 255, 255, 0.05);
		background: rgba(255, 255, 255, 0.03);
		padding: 0.85rem 0.9rem;
		transition: 160ms ease;
	}

	.study-card:hover,
	.study-card-active {
		border-color: rgba(96, 165, 250, 0.28);
		background: linear-gradient(to right, rgba(37, 99, 235, 0.16), rgba(30, 41, 59, 0.12));
	}

	.action-button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		border-radius: 1rem;
		border: 1px solid rgba(255, 255, 255, 0.08);
		background: rgba(255, 255, 255, 0.05);
		padding: 0.85rem 1rem;
		font-size: 0.75rem;
		font-weight: 700;
		color: rgba(241, 245, 249, 0.9);
	}

	.action-button:hover {
		background: rgba(255, 255, 255, 0.1);
	}

	:global(.viewer-range) {
		accent-color: #60a5fa;
	}
</style>
