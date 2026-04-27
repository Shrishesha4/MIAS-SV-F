<svelte:head>
	<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
</svelte:head>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { geofencingApi } from '$lib/api/geofencing';
	import { toastStore } from '$lib/stores/toast';
	import AquaButton from '$lib/components/ui/AquaButton.svelte';
	import AquaModal from '$lib/components/ui/AquaModal.svelte';
	import { MapPin, Plus, Pencil, Trash2, Check, X, Crosshair } from 'lucide-svelte';

	// ── Constants ──────────────────────────────────────────────────────────
	const DEFAULT_LAT = 13.024119133954391;
	const DEFAULT_LNG = 80.01579495919825;
	const DEFAULT_ZOOM = 17;

	const MAP_VIEWS = [
		{
			id: 'osm',
			label: 'Map',
			url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
			attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
			maxZoom: 19,
		},
		{
			id: 'satellite',
			label: 'Satellite',
			url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
			attribution: 'Tiles © Esri',
			maxZoom: 19,
		},
		{
			id: 'clean',
			label: 'Clean',
			url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
			attribution: '© <a href="https://carto.com/">CartoDB</a>',
			maxZoom: 19,
		},
	];

	// ── Types ──────────────────────────────────────────────────────────────
	interface Zone {
		id: string;
		name: string;
		polygon: { lat: number; lng: number }[];
		is_active: boolean;
	}

	// ── State ──────────────────────────────────────────────────────────────
	let zones = $state<Zone[]>([]);
	let loading = $state(true);
	let currentViewId = $state('osm');

	// Draw mode
	let isDrawing = $state(false);
	let draftVertices = $state<{ lat: number; lng: number }[]>([]);
	let draftName = $state('');
	let saving = $state(false);

	// Edit modal
	let showEditModal = $state(false);
	let editingZone = $state<Zone | null>(null);
	let editName = $state('');
	let editSaving = $state(false);

	// Leaflet refs
	let mapEl: HTMLDivElement;
	let map: any;
	let L: any;
	let tileLayer: any = null;
	let draftPolyline: any = null;
	let draftMarkers: any[] = [];
	let zonePolygons: Record<string, any> = {};
	let clickHandler: any = null;
	let locateMarker: any = null;
	let locateCircle: any = null;
	let locating = $state(false);

	// ── Data ───────────────────────────────────────────────────────────────
	async function loadZones() {
		try {
			zones = await geofencingApi.listZones();
		} catch {
			toastStore.addToast('Failed to load zones', 'error');
		} finally {
			loading = false;
		}
	}

	// ── Leaflet init ───────────────────────────────────────────────────────
	onMount(async () => {
		await loadZones();

		// Leaflet must be imported client-side only
		L = (await import('leaflet')).default;
		// Leaflet default icon fix for Vite
		delete (L.Icon.Default.prototype as any)._getIconUrl;
		L.Icon.Default.mergeOptions({
			iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
			iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
			shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
		});

		map = L.map(mapEl, { zoomControl: true }).setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);
		applyTileLayer('osm');
		renderZones();
	});

	onDestroy(() => { if (map) map.remove(); });

	// ── Tile layer switching ───────────────────────────────────────────────
	function applyTileLayer(viewId: string) {
		if (!L || !map) return;
		if (tileLayer) { map.removeLayer(tileLayer); tileLayer = null; }
		const view = MAP_VIEWS.find((v) => v.id === viewId)!;
		tileLayer = L.tileLayer(view.url, { attribution: view.attribution, maxZoom: view.maxZoom }).addTo(map);
		currentViewId = viewId;
	}

	// ── Zone rendering ────────────────────────────────────────────────────
	function renderZones() {
		if (!L || !map) return;
		// Clear existing
		Object.values(zonePolygons).forEach((p: any) => map.removeLayer(p));
		zonePolygons = {};

		for (const zone of zones) {
			if (zone.polygon.length < 3) continue;
			const latlngs = zone.polygon.map((v) => [v.lat, v.lng]);
			const active = zone.is_active;
			const poly = L.polygon(latlngs, {
				color: active ? '#10b981' : '#94a3b8',
				fillColor: active ? '#10b981' : '#94a3b8',
				fillOpacity: active ? 0.22 : 0.08,
				weight: active ? 3 : 2,
				dashArray: active ? undefined : '6, 4',
			})
				.addTo(map)
				.bindTooltip(zone.name, { permanent: true, direction: 'center', className: 'zone-label' });
			zonePolygons[zone.id] = poly;
		}
	}

	$effect(() => {
		// Re-render whenever zones change
		if (L && map) renderZones();
	});

	// ── Draw mode ─────────────────────────────────────────────────────────
	function startDrawing() {
		if (!map) return;
		isDrawing = true;
		draftVertices = [];
		draftName = `Zone ${zones.length + 1}`;

		// Change cursor
		mapEl.style.cursor = 'crosshair';

		// Click to add vertex
		clickHandler = map.on('click', (e: any) => {
			draftVertices = [...draftVertices, { lat: e.latlng.lat, lng: e.latlng.lng }];
			updateDraftPreview();
		});
	}

	function updateDraftPreview() {
		if (!L || !map) return;

		// Remove old preview
		if (draftPolyline) { map.removeLayer(draftPolyline); draftPolyline = null; }
		draftMarkers.forEach((m) => map.removeLayer(m));
		draftMarkers = [];

		if (draftVertices.length === 0) return;

		// Draw markers
		for (const v of draftVertices) {
			const m = L.circleMarker([v.lat, v.lng], {
				radius: 6,
				color: '#f59e0b',
				fillColor: '#f59e0b',
				fillOpacity: 1,
				weight: 2,
			}).addTo(map);
			draftMarkers.push(m);
		}

		// Draw closed polygon preview when ≥ 3 vertices
		if (draftVertices.length >= 3) {
			const latlngs = draftVertices.map((v) => [v.lat, v.lng]);
			draftPolyline = L.polygon(latlngs, {
				color: '#f59e0b',
				fillOpacity: 0.15,
				dashArray: '5, 5',
				weight: 2,
			}).addTo(map);
		} else if (draftVertices.length >= 2) {
			const latlngs = draftVertices.map((v) => [v.lat, v.lng]);
			draftPolyline = L.polyline(latlngs, { color: '#f59e0b', dashArray: '5, 5', weight: 2 }).addTo(map);
		}
	}

	function cancelDrawing() {
		isDrawing = false;
		draftVertices = [];
		mapEl.style.cursor = '';
		if (clickHandler) { map.off('click'); clickHandler = null; }
		if (draftPolyline) { map.removeLayer(draftPolyline); draftPolyline = null; }
		draftMarkers.forEach((m) => map.removeLayer(m));
		draftMarkers = [];
	}

	function undoLastVertex() {
		if (draftVertices.length === 0) return;
		draftVertices = draftVertices.slice(0, -1);
		updateDraftPreview();
	}

	async function saveDraft() {
		if (draftVertices.length < 3) {
			toastStore.addToast('Add at least 3 points to form a polygon.', 'warning');
			return;
		}
		if (!draftName.trim()) {
			toastStore.addToast('Enter a zone name.', 'warning');
			return;
		}
		saving = true;
		try {
			await geofencingApi.createZone({ name: draftName.trim(), polygon: draftVertices, is_active: true });
			toastStore.addToast(`Zone "${draftName}" created.`, 'success');
			cancelDrawing();
			await loadZones();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Failed to save zone.', 'error');
		} finally {
			saving = false;
		}
	}

	// ── Edit / delete ─────────────────────────────────────────────────────
	function openEdit(zone: Zone) {
		editingZone = zone;
		editName = zone.name;
		showEditModal = true;
	}

	async function saveEdit() {
		if (!editingZone || !editName.trim()) return;
		editSaving = true;
		try {
			await geofencingApi.updateZone(editingZone.id, { name: editName.trim() });
			toastStore.addToast('Zone updated.', 'success');
			showEditModal = false;
			await loadZones();
		} catch (err: any) {
			toastStore.addToast(err?.response?.data?.detail || 'Update failed.', 'error');
		} finally {
			editSaving = false;
		}
	}

	async function toggleActive(zone: Zone) {
		try {
			await geofencingApi.updateZone(zone.id, { is_active: !zone.is_active });
			toastStore.addToast(`Zone "${zone.name}" ${zone.is_active ? 'deactivated' : 'activated'}.`, 'success');
			await loadZones();
		} catch {
			toastStore.addToast('Failed to update zone.', 'error');
		}
	}

	async function deleteZone(zone: Zone) {
		if (!confirm(`Delete zone "${zone.name}"? This cannot be undone.`)) return;
		try {
			await geofencingApi.deleteZone(zone.id);
			toastStore.addToast(`Zone "${zone.name}" deleted.`, 'success');
			await loadZones();
		} catch {
			toastStore.addToast('Failed to delete zone.', 'error');
		}
	}

	// ── Locate me ─────────────────────────────────────────────────────────
	function locateMe() {
		if (!map || !L) return;
		if (!navigator.geolocation) {
			toastStore.addToast('Geolocation not supported by this browser.', 'error');
			return;
		}
		locating = true;
		navigator.geolocation.getCurrentPosition(
			(pos) => {
				locating = false;
				const { latitude: lat, longitude: lng, accuracy } = pos.coords;
				map.setView([lat, lng], 18);
				if (locateMarker) map.removeLayer(locateMarker);
			if (locateCircle) map.removeLayer(locateCircle);
			locateMarker = L.circleMarker([lat, lng], {
				radius: 8,
				color: '#2563eb',
				fillColor: '#3b82f6',
				fillOpacity: 0.9,
				weight: 3,
			})
				.addTo(map)
				.bindPopup(`Your location<br><span style="font-size:11px;color:#64748b">±${Math.round(accuracy)}m accuracy</span>`, { maxWidth: 160 })
				.openPopup();
			locateCircle = L.circle([lat, lng], {
				radius: accuracy,
				color: '#3b82f6',
				fillColor: '#3b82f6',
				fillOpacity: 0.08,
				weight: 1,
			}).addTo(map);
			},
			() => {
				locating = false;
				toastStore.addToast('Could not get your location. Check browser permissions.', 'error');
			},
			{ enableHighAccuracy: true, timeout: 10000 }
		);
	}
</script>

<style>
	:global(.zone-label) {
		background: rgba(255, 255, 255, 0.92) !important;
		border: none !important;
		box-shadow: 0 1px 6px rgba(0, 0, 0, 0.18) !important;
		border-radius: 6px !important;
		padding: 3px 9px !important;
		font-size: 11px !important;
		font-weight: 700 !important;
		color: #1e293b !important;
		white-space: nowrap !important;
		pointer-events: none !important;
	}
	:global(.zone-label::before) { display: none !important; }
</style>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<MapPin size={18} class="text-blue-500" />
			<h3 class="font-semibold text-slate-800 text-sm">Campus Geofence Zones</h3>
		</div>
		{#if !isDrawing}
			<AquaButton variant="primary" size="sm" onclick={startDrawing}>
				<Plus size={14} class="mr-1" />Draw Zone
			</AquaButton>
		{/if}
	</div>

	<!-- Draw toolbar (shown while drawing) -->
	{#if isDrawing}
		<div class="rounded-xl p-3 flex flex-wrap items-center gap-3"
			style="background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3);">
			<p class="text-amber-700 text-xs font-medium flex-1 min-w-0">
				Drawing mode — click on the map to add vertices ({draftVertices.length} added).
				{#if draftVertices.length >= 3}Need at least 3.{/if}
			</p>
			<input
				type="text"
				bind:value={draftName}
				placeholder="Zone name"
				class="px-3 py-1.5 rounded-lg text-sm border border-amber-300 bg-white text-slate-800"
				style="min-width: 140px;"
			/>
			<button onclick={undoLastVertex} class="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 bg-white border border-slate-200">
				Undo
			</button>
			<button onclick={cancelDrawing} class="px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 bg-white border border-red-200">
				<X size={13} class="inline mr-0.5" />Cancel
			</button>
			<button onclick={saveDraft} disabled={saving || draftVertices.length < 3}
				class="px-3 py-1.5 rounded-lg text-xs font-semibold text-white"
				style="background: {draftVertices.length >= 3 ? 'linear-gradient(to bottom, #3b82f6, #2563eb)' : '#94a3b8'}; opacity: {saving ? 0.7 : 1};">
				<Check size={13} class="inline mr-0.5" />{saving ? 'Saving…' : 'Save Zone'}
			</button>
		</div>
	{/if}

	<!-- Map wrapper -->
	<div class="relative w-full rounded-2xl overflow-hidden"
		style="height: 420px; border: 1px solid rgba(0,0,0,0.1); box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
		<div bind:this={mapEl} class="w-full h-full"></div>
		<!-- Map view switcher (top-left next to zoom controls) -->
		<div class="absolute top-3 z-[1000] flex rounded-xl overflow-hidden shadow-md"
			style="left: 54px; border: 1px solid rgba(0,0,0,0.15);">
			{#each MAP_VIEWS as view}
				<button
					onclick={() => applyTileLayer(view.id)}
					class="px-3 py-1.5 text-xs font-semibold transition-colors"
					style="background: {currentViewId === view.id
						? 'linear-gradient(to bottom, #3b82f6, #2563eb)'
						: 'rgba(255,255,255,0.93)'}; color: {currentViewId === view.id ? '#fff' : '#374151'};"
				>{view.label}</button>
			{/each}
		</div>
		<!-- Locate Me button -->
		<button
			onclick={locateMe}
			disabled={locating}
			class="absolute bottom-4 right-4 z-[1000] flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-white shadow-lg"
			style="background: linear-gradient(to bottom, #3b82f6, #2563eb); opacity: {locating ? 0.7 : 1};"
			title="Pan to my current location"
		>
			<Crosshair size={14} />{locating ? 'Locating…' : 'My Location'}
		</button>
	</div>

	<!-- Zone list -->
	{#if loading}
		<div class="py-6 text-center text-sm text-slate-500">Loading zones…</div>
	{:else if zones.length === 0}
		<div class="py-6 text-center text-sm text-slate-500">
			No geofence zones configured. Use "Draw Zone" to add one.
		</div>
	{:else}
		<div class="space-y-2">
			{#each zones as zone (zone.id)}
				<div class="flex items-center gap-3 rounded-xl px-4 py-3"
					style="background: {zone.is_active ? 'linear-gradient(to right, #ecfdf5, #f0fdf9)' : '#f8fafc'}; border: 1px solid {zone.is_active ? '#6ee7b7' : '#e2e8f0'};">
					<div class="w-3 h-3 rounded-full flex-shrink-0"
						style="background: {zone.is_active ? '#10b981' : '#94a3b8'};"></div>
					<div class="flex-1 min-w-0">
						<p class="text-sm font-medium text-slate-800 truncate">{zone.name}</p>
						<p class="text-xs text-slate-500">{zone.polygon.length} vertices · {zone.is_active ? 'Active' : 'Inactive'}</p>
					</div>
					<!-- iOS-style toggle -->
					<button
						onclick={() => toggleActive(zone)}
						class="relative flex-shrink-0 w-11 h-6 rounded-full transition-colors duration-200 focus:outline-none"
						style="background: {zone.is_active ? '#10b981' : '#d1d5db'};"
						title="{zone.is_active ? 'Deactivate' : 'Activate'}"
						aria-label="{zone.is_active ? 'Deactivate zone' : 'Activate zone'}"
					>
						<span
							class="absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200"
							style="left: {zone.is_active ? '22px' : '2px'};"
						></span>
					</button>
					<button onclick={() => openEdit(zone)} class="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-colors">
						<Pencil size={14} />
					</button>
					<button onclick={() => deleteZone(zone)} class="p-1.5 rounded-lg text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors">
						<Trash2 size={14} />
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Edit name modal -->
{#if showEditModal && editingZone}
	<AquaModal open={showEditModal} title="Edit Zone" onclose={() => { showEditModal = false; }}>
		<div class="space-y-4 p-1">
			<div>
				<label for="zone-name-input" class="text-xs font-medium text-slate-600 block mb-1">Zone Name</label>
				<input
					id="zone-name-input"
					type="text"
					bind:value={editName}
					class="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 bg-white"
					onkeydown={(e) => { if (e.key === 'Enter') saveEdit(); }}
				/>
			</div>
			<div class="flex gap-2">
				<AquaButton variant="secondary" size="sm" onclick={() => { showEditModal = false; }} fullWidth>Cancel</AquaButton>
				<AquaButton variant="primary" size="sm" onclick={saveEdit} loading={editSaving} fullWidth>Save</AquaButton>
			</div>
		</div>
	</AquaModal>
{/if}
