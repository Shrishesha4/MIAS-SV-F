<script lang="ts">
	import { onMount } from 'svelte';

	interface EnhancedSelect {
		trigger: HTMLButtonElement;
		cleanup: () => void;
	}

	const enhanced = new WeakMap<HTMLSelectElement, EnhancedSelect>();
	let activeDropdown: HTMLDivElement | null = null;
	let activeSelect: HTMLSelectElement | null = null;
	let observer: MutationObserver | null = null;
	let styleEl: HTMLStyleElement | null = null;

	function ensureStyles() {
		if (styleEl && document.head.contains(styleEl)) return;
		styleEl = document.createElement('style');
		styleEl.id = 'mias-select-enhancer-styles';
		styleEl.textContent = `
			.mias-native-hidden {
				position: absolute !important;
				width: 1px !important;
				height: 1px !important;
				padding: 0 !important;
				margin: -1px !important;
				overflow: hidden !important;
				clip: rect(0,0,0,0) !important;
				white-space: nowrap !important;
				border: 0 !important;
				opacity: 0 !important;
				pointer-events: none !important;
			}
			.mias-select-trigger {
				display: flex !important;
				align-items: center !important;
				justify-content: space-between !important;
				gap: 8px !important;
				width: 100% !important;
				text-align: left !important;
				cursor: pointer !important;
				background: rgba(255,255,255,0.96) !important;
				border: 1px solid #e2e8f0 !important;
				border-radius: 12px !important;
				padding: 10px 12px !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
				box-shadow: inset 0 1px 2px rgba(15,23,42,0.04) !important;
				transition: border-color 0.15s, box-shadow 0.15s !important;
				box-sizing: border-box !important;
				min-height: 42px !important;
				outline: none !important;
			}
			.mias-select-trigger:hover:not(:disabled) {
				border-color: #93c5fd !important;
			}
			.mias-select-trigger:focus {
				border-color: #60a5fa !important;
				box-shadow: inset 0 1px 2px rgba(15,23,42,0.04), 0 0 0 2px rgba(96,165,250,0.2) !important;
			}
			.mias-select-trigger:disabled {
				cursor: not-allowed !important;
				opacity: 0.5 !important;
			}
			.mias-select-trigger-label {
				flex: 1 !important;
				overflow: hidden !important;
				text-overflow: ellipsis !important;
				white-space: nowrap !important;
			}
			.mias-select-trigger-label.placeholder {
				color: #94a3b8 !important;
			}
			.mias-select-chevron {
				flex-shrink: 0 !important;
				width: 16px !important;
				height: 16px !important;
				color: #94a3b8 !important;
				transition: transform 0.15s !important;
			}
			.mias-select-chevron.open {
				transform: rotate(180deg) !important;
			}
			.mias-select-dropdown {
				position: fixed !important;
				z-index: 10050 !important;
				background: white !important;
				border: 1px solid rgba(148,163,184,0.24) !important;
				border-radius: 16px !important;
				box-shadow: 0 8px 32px rgba(15,23,42,0.14), 0 2px 8px rgba(15,23,42,0.06) !important;
				overflow: hidden !important;
				display: flex !important;
				flex-direction: column !important;
				max-height: 300px !important;
			}
			.mias-select-search-wrap {
				display: flex !important;
				align-items: center !important;
				gap: 8px !important;
				padding: 8px 12px !important;
				border-bottom: 1px solid rgba(148,163,184,0.16) !important;
				background: rgba(248,250,252,0.9) !important;
				flex-shrink: 0 !important;
			}
			.mias-select-search-wrap svg {
				width: 14px !important;
				height: 14px !important;
				color: #94a3b8 !important;
				flex-shrink: 0 !important;
			}
			.mias-select-search {
				flex: 1 !important;
				border: none !important;
				background: transparent !important;
				outline: none !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
			}
			.mias-select-search::placeholder {
				color: #94a3b8 !important;
			}
			.mias-select-options {
				overflow-y: auto !important;
				flex: 1 !important;
				min-height: 0 !important;
			}
			.mias-select-option {
				display: block !important;
				width: 100% !important;
				text-align: left !important;
				padding: 9px 14px !important;
				font-size: 0.875rem !important;
				color: #1e293b !important;
				background: transparent !important;
				border: none !important;
				cursor: pointer !important;
				transition: background 0.1s !important;
			}
			.mias-select-option:hover,
			.mias-select-option.highlighted {
				background: rgba(59,130,246,0.06) !important;
				color: #1d4ed8 !important;
			}
			.mias-select-option.selected {
				background: rgba(59,130,246,0.1) !important;
				color: #1d4ed8 !important;
				font-weight: 500 !important;
			}
			.mias-select-empty {
				padding: 12px 14px !important;
				font-size: 0.875rem !important;
				color: #94a3b8 !important;
				text-align: center !important;
			}
		`;
		document.head.appendChild(styleEl);
	}

	type OptionItem = { value: string; label: string };

	function getOptions(select: HTMLSelectElement): OptionItem[] {
		return Array.from(select.options)
			.filter((o) => !(o.value === '' && o.disabled))
			.map((o) => ({ value: o.value, label: o.text || o.value }));
	}

	function getSelectedLabel(select: HTMLSelectElement): string {
		const opt = select.options[select.selectedIndex];
		return opt ? opt.text : '';
	}

	function syncTrigger(select: HTMLSelectElement, trigger: HTMLButtonElement) {
		const label = trigger.querySelector<HTMLSpanElement>('.mias-select-trigger-label');
		if (!label) return;
		const text = getSelectedLabel(select);
		const firstOpt = select.options[0];
		const isPlaceholder =
			!select.value || (firstOpt && firstOpt.value === '' && select.selectedIndex === 0);
		if (isPlaceholder || !text) {
			label.textContent = firstOpt?.text || 'Select...';
			label.classList.add('placeholder');
		} else {
			label.textContent = text;
			label.classList.remove('placeholder');
		}
		trigger.disabled = select.disabled;
	}

	function closeDropdown() {
		if (activeDropdown) {
			activeDropdown.remove();
			activeDropdown = null;
		}
		if (activeSelect) {
			const info = enhanced.get(activeSelect);
			if (info) {
				const chevron = info.trigger.querySelector('.mias-select-chevron');
				chevron?.classList.remove('open');
			}
			activeSelect = null;
		}
	}

	function openDropdown(select: HTMLSelectElement, trigger: HTMLButtonElement) {
		// Close any existing dropdown
		closeDropdown();

		activeSelect = select;
		const chevron = trigger.querySelector('.mias-select-chevron');
		chevron?.classList.add('open');

		const options = getOptions(select);
		const currentValue = select.value;

		const dropdown = document.createElement('div');
		dropdown.className = 'mias-select-dropdown';
		activeDropdown = dropdown;

		// Search row
		const searchWrap = document.createElement('div');
		searchWrap.className = 'mias-select-search-wrap';
		searchWrap.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>`;
		const searchInput = document.createElement('input');
		searchInput.type = 'text';
		searchInput.placeholder = 'Search...';
		searchInput.className = 'mias-select-search';
		searchWrap.appendChild(searchInput);
		dropdown.appendChild(searchWrap);

		// Options list
		const optionsList = document.createElement('div');
		optionsList.className = 'mias-select-options';
		dropdown.appendChild(optionsList);

		let highlightIndex = -1;
		let filtered = options.filter((o) => o.value !== '');

		function renderOptions(list: OptionItem[]) {
			optionsList.innerHTML = '';
			if (list.length === 0) {
				const empty = document.createElement('div');
				empty.className = 'mias-select-empty';
				empty.textContent = 'No results';
				optionsList.appendChild(empty);
				return;
			}
			list.forEach((opt, idx) => {
				const btn = document.createElement('button');
				btn.type = 'button';
				btn.className = 'mias-select-option';
				btn.textContent = opt.label;
				if (opt.value === currentValue) btn.classList.add('selected');
				if (idx === highlightIndex) btn.classList.add('highlighted');
				btn.addEventListener('mousedown', (e) => {
					e.preventDefault();
					selectValue(opt.value);
				});
				optionsList.appendChild(btn);
			});
		}

		function selectValue(val: string) {
			select.value = val;
			// Fire both change and input so Svelte bind:value and onchange both catch it
			select.dispatchEvent(new Event('change', { bubbles: true }));
			select.dispatchEvent(new Event('input', { bubbles: true }));
			syncTrigger(select, trigger);
			closeDropdown();
			trigger.focus();
		}

		function filterOptions(q: string) {
			const lower = q.trim().toLowerCase();
			if (!lower) {
				filtered = options.filter((o) => o.value !== '');
			} else {
				filtered = options.filter(
					(o) =>
						o.value !== '' &&
						(o.label.toLowerCase().includes(lower) || o.value.toLowerCase().includes(lower))
				);
			}
			highlightIndex = -1;
			renderOptions(filtered);
		}

		searchInput.addEventListener('input', (e) => {
			filterOptions((e.target as HTMLInputElement).value);
		});

		searchInput.addEventListener('keydown', (e) => {
			switch (e.key) {
				case 'ArrowDown':
					e.preventDefault();
					highlightIndex = Math.min(highlightIndex + 1, filtered.length - 1);
					renderOptions(filtered);
					optionsList.querySelectorAll<HTMLElement>('.mias-select-option')[highlightIndex]?.scrollIntoView({ block: 'nearest' });
					break;
				case 'ArrowUp':
					e.preventDefault();
					highlightIndex = Math.max(highlightIndex - 1, -1);
					renderOptions(filtered);
					if (highlightIndex >= 0) {
						optionsList.querySelectorAll<HTMLElement>('.mias-select-option')[highlightIndex]?.scrollIntoView({ block: 'nearest' });
					}
					break;
				case 'Enter':
					e.preventDefault();
					if (highlightIndex >= 0 && filtered[highlightIndex]) {
						selectValue(filtered[highlightIndex].value);
					}
					break;
				case 'Escape':
					e.preventDefault();
					closeDropdown();
					trigger.focus();
					break;
				case 'Tab':
					closeDropdown();
					break;
			}
		});

		// Position — clamp to viewport
		const r = trigger.getBoundingClientRect();
		const dropdownMaxH = 300;
		const dropdownW = Math.max(Math.round(r.width), 180);
		const spaceBelow = window.innerHeight - r.bottom;
		if (spaceBelow < dropdownMaxH && r.top > dropdownMaxH) {
			dropdown.style.bottom = `${Math.round(window.innerHeight - r.top + 4)}px`;
			dropdown.style.top = 'auto';
		} else {
			dropdown.style.top = `${Math.round(r.bottom + 4)}px`;
		}
		// Clamp left so dropdown never overflows the right edge of the viewport
		const clampedLeft = Math.min(Math.round(r.left), window.innerWidth - dropdownW - 8);
		dropdown.style.left = `${Math.max(clampedLeft, 8)}px`;
		dropdown.style.width = `${dropdownW}px`;

		document.body.appendChild(dropdown);
		renderOptions(filtered);
		requestAnimationFrame(() => searchInput.focus());
	}

	function enhanceSelect(select: HTMLSelectElement) {
		if (enhanced.has(select)) return;
		if (select.dataset.searchableEnhanced === 'skip') return;
		if (select.closest('.mias-select-dropdown')) return;
		// Skip selects inside AquaSelect portals or with very few options (0-1)
		if (select.options.length <= 1) return;

		ensureStyles();

		// Hide native select accessibly
		select.classList.add('mias-native-hidden');

		// Create trigger button
		const trigger = document.createElement('button');
		trigger.type = 'button';
		trigger.className = 'mias-select-trigger';

		const label = document.createElement('span');
		label.className = 'mias-select-trigger-label';
		trigger.appendChild(label);

		const chevronSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		chevronSvg.setAttribute('viewBox', '0 0 24 24');
		chevronSvg.setAttribute('fill', 'none');
		chevronSvg.setAttribute('stroke', 'currentColor');
		chevronSvg.setAttribute('stroke-width', '2');
		chevronSvg.setAttribute('stroke-linecap', 'round');
		chevronSvg.setAttribute('stroke-linejoin', 'round');
		chevronSvg.classList.add('mias-select-chevron');
		const chevronPath = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
		chevronPath.setAttribute('points', '6 9 12 15 18 9');
		chevronSvg.appendChild(chevronPath);
		trigger.appendChild(chevronSvg);

		syncTrigger(select, trigger);

		trigger.addEventListener('click', (e) => {
			e.preventDefault();
			e.stopPropagation();
			if (activeSelect === select) {
				closeDropdown();
				return;
			}
			openDropdown(select, trigger);
		});

		// Intercept programmatic .value = '...' assignments from Svelte reactivity
		const proto = Object.getPrototypeOf(select); // HTMLSelectElement.prototype
		const origDescriptor = Object.getOwnPropertyDescriptor(proto, 'value');
		if (origDescriptor && origDescriptor.set) {
			Object.defineProperty(select, 'value', {
				get() {
					return origDescriptor.get!.call(this);
				},
				set(val: string) {
					origDescriptor.set!.call(this, val);
					syncTrigger(select, trigger);
				},
				configurable: true
			});
		}

		// Also watch for options being added/changed (e.g. dynamic option lists)
		const optObserver = new MutationObserver(() => {
			syncTrigger(select, trigger);
		});
		optObserver.observe(select, { childList: true, subtree: true, attributes: true, attributeFilter: ['selected'] });

		// Insert trigger right after the select in the DOM
		select.insertAdjacentElement('afterend', trigger);

		// Copy any explicit width/height styling from parent
		const parentStyle = window.getComputedStyle(select.parentElement ?? select);
		if (parentStyle.display === 'flex' || parentStyle.display === 'grid') {
			trigger.style.flex = '1 1 0%';
			trigger.style.minWidth = '0';
		}

		enhanced.set(select, {
			trigger,
			cleanup: () => {
				optObserver.disconnect();
				trigger.remove();
				select.classList.remove('mias-native-hidden');
				// Restore original value descriptor
				delete (select as unknown as Record<string, unknown>)['value'];
			}
		});
	}

	function upgradeAllSelects() {
		document.querySelectorAll<HTMLSelectElement>('select').forEach(enhanceSelect);
	}

	onMount(() => {
		ensureStyles();
		upgradeAllSelects();

		observer = new MutationObserver((mutations) => {
			let needsUpgrade = false;
			for (const mutation of mutations) {
				for (const node of Array.from(mutation.addedNodes)) {
					if (node.nodeType !== 1) continue;
					const el = node as Element;
					if (el.tagName === 'SELECT') {
						needsUpgrade = true;
					} else if (el.querySelectorAll) {
						if (el.querySelectorAll('select').length > 0) needsUpgrade = true;
					}
					// Also handle removed enhanced selects (clean up their triggers)
				}
				for (const node of Array.from(mutation.removedNodes)) {
					if (node.nodeType !== 1) continue;
					const el = node as Element;
					if (el.tagName === 'SELECT') {
						const info = enhanced.get(el as HTMLSelectElement);
						info?.cleanup();
					}
				}
			}
			if (needsUpgrade) {
				requestAnimationFrame(upgradeAllSelects);
			}
		});

		observer.observe(document.body, { childList: true, subtree: true });

		// Close dropdown on scroll or resize
		const onScroll = () => closeDropdown();
		const onResize = () => closeDropdown();
		window.addEventListener('scroll', onScroll, true);
		window.addEventListener('resize', onResize);

		// Close on outside click
		const onMousedown = (e: MouseEvent) => {
			if (!activeDropdown) return;
			const target = e.target as Node;
			if (activeDropdown.contains(target)) return;
			if (activeSelect && enhanced.get(activeSelect)?.trigger.contains(target)) return;
			closeDropdown();
		};
		document.addEventListener('mousedown', onMousedown);

		return () => {
			observer?.disconnect();
			closeDropdown();
			window.removeEventListener('scroll', onScroll, true);
			window.removeEventListener('resize', onResize);
			document.removeEventListener('mousedown', onMousedown);
			styleEl?.remove();
		};
	});
</script>
