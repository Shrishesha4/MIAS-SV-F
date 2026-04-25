<script lang="ts">
  import { onMount, tick } from 'svelte';

  interface Tab {
    id: string;
    label: string;
    icon?: any;
  }

  interface Props {
    tabs: Tab[];
    activeTab: string;
    onchange: (tabId: string) => unknown;
    variant?: 'default' | 'jiggle';
    stretch?: boolean;
    size?: 'default' | 'compact';
    ariaLabel?: string;
  }

  let {
    tabs,
    activeTab,
    onchange,
    variant = 'default',
    stretch = true,
    size = 'default',
    ariaLabel = 'Tab navigation',
  }: Props = $props();

  let tabBarElement: HTMLDivElement | undefined = $state();
  let tabElements: Array<HTMLButtonElement | null> = $state([]);
  let sliderStyle = $state('opacity: 0;');

  function updateSlider() {
    if (variant !== 'jiggle' || !tabBarElement) {
      sliderStyle = 'opacity: 0;';
      return;
    }

    const activeIndex = tabs.findIndex((tab) => tab.id === activeTab);
    const activeElement = activeIndex >= 0 ? tabElements[activeIndex] : null;

    if (!activeElement) {
      sliderStyle = 'opacity: 0;';
      return;
    }

    sliderStyle = [
      `width: ${activeElement.offsetWidth}px`,
      `height: ${activeElement.offsetHeight}px`,
      `transform: translate3d(${activeElement.offsetLeft}px, ${activeElement.offsetTop}px, 0)`,
      'opacity: 1',
    ].join('; ');
  }

  function scheduleSliderUpdate() {
    void tick().then(updateSlider);
  }

  onMount(() => {
    scheduleSliderUpdate();

    if (typeof ResizeObserver === 'undefined') {
      return;
    }

    const observer = new ResizeObserver(() => {
      updateSlider();
    });

    if (tabBarElement) {
      observer.observe(tabBarElement);
    }

    return () => observer.disconnect();
  });

  $effect(() => {
    tabs.length;
    activeTab;
    variant;
    scheduleSliderUpdate();
  });
</script>

<svelte:window onresize={scheduleSliderUpdate} />

<div
  bind:this={tabBarElement}
  class="tab-bar"
  class:tab-bar--default={variant === 'default'}
  class:tab-bar--jiggle={variant === 'jiggle'}
  class:tab-bar--fill={stretch}
  class:tab-bar--fit={!stretch}
  class:tab-bar--compact={size === 'compact'}
  role="tablist"
  aria-label={ariaLabel}
>
  {#if variant === 'jiggle'}
    <div class="tab-slider" aria-hidden="true" style={sliderStyle}></div>
  {/if}

  {#each tabs as tab, index (tab.id)}
    <button
      bind:this={tabElements[index]}
      type="button"
      class="tab-button"
      class:tab-button--default={variant === 'default'}
      class:tab-button--jiggle={variant === 'jiggle'}
      class:tab-button--stretch={stretch}
      class:tab-button--auto={!stretch}
      class:tab-button--compact={size === 'compact'}
      class:is-active={activeTab === tab.id}
      class:is-inactive={activeTab !== tab.id}
      role="tab"
      aria-selected={activeTab === tab.id}
      tabindex={activeTab === tab.id ? 0 : -1}
      onclick={() => void onchange(tab.id)}
    >
      {#if tab.icon}
        {@const Icon = tab.icon}
        <Icon class="h-4 w-4 shrink-0" />
      {/if}
      <span class="tab-label">{tab.label}</span>
      {#if variant === 'default'}
        <div class="tab-underline"></div>
      {/if}
    </button>
  {/each}
</div>

<style>
  .tab-bar {
    position: relative;
    display: flex;
    gap: 0.35rem;
    max-width: 100%;
  }

  .tab-bar--fill {
    width: 100%;
  }

  .tab-bar--fit {
    width: max-content;
  }

  .tab-bar--default {
    overflow: hidden;
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 10px;
    background-color: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.05);
  }

  .tab-bar--jiggle {
    padding: 0.28rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 1rem;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(241, 245, 249, 0.96)),
      radial-gradient(circle at top, rgba(96, 165, 250, 0.12), transparent 58%);
    /*box-shadow:
      0 8px 18px rgba(15, 23, 42, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.92);*/
  }

  .tab-bar--jiggle.tab-bar--fill {
    min-width: 100%;
  }

  .tab-slider {
    position: absolute;
    top: 0;
    left: 0;
    border: 1px solid rgba(29, 78, 216, 0.2);
    border-radius: 0.75rem;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 60%, #1d4ed8 100%);
    /*box-shadow:
      0 10px 22px rgba(37, 99, 235, 0.22),
      inset 0 1px 0 rgba(255, 255, 255, 0.32),
      inset 0 -1px 0 rgba(15, 23, 42, 0.12);*/
    transition:
        transform 280ms cubic-bezier(0.34, 1.56, 0.64, 1),
        width 500ms cubic-bezier(0.34, 1.56, 0.64, 1),
        height 420ms cubic-bezier(0.34, 1.56, 0.64, 1),
        opacity 10ms ease;
    pointer-events: none;
  }

  .tab-button {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    cursor: pointer;
    white-space: nowrap;
    border: 1px solid transparent;
    transition:
      transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
      color 220ms ease,
      background 220ms ease,
      box-shadow 220ms ease,
      border-color 220ms ease;
  }

  .tab-button--stretch {
    flex: 1 1 0;
  }

  .tab-button--auto {
    flex: 0 0 auto;
  }

  .tab-button--default {
    padding: 0.625rem 0.75rem;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .tab-button--jiggle {
    z-index: 1;
    min-height: 2.7rem;
    padding: 0.62rem 0.88rem;
    border-radius: 1.1rem;
    background: transparent;
    font-size: 0.84rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #667085;
  }

  .tab-bar--compact {
    gap: 0.25rem;
  }

  .tab-bar--jiggle.tab-bar--compact {
    padding: 0.2rem;
    border-radius: 0.9rem;
  }

  .tab-button--jiggle.tab-button--compact {
    min-height: 2.3rem;
    padding: 0.48rem 0.7rem;
    border-radius: 0.9rem;
    font-size: 0.76rem;
  }

  .tab-button--jiggle:hover {
    color: #475467;
    transform: translateY(-1px);
  }

  .tab-button--jiggle.is-active {
    color: white;
  }

  .tab-button--default.is-active {
    color: #2563eb;
    background-color: rgba(59, 130, 246, 0.05);
  }

  .tab-button--default.is-inactive {
    color: #6b7280;
  }

  .tab-button--default.is-inactive:hover {
    color: #374151;
    background-color: rgba(0, 0, 0, 0.02);
  }

  .tab-label,
  .tab-underline {
    position: relative;
    z-index: 1;
  }

  .tab-underline {
    position: absolute;
    bottom: 0;
    left: 0.5rem;
    right: 0.5rem;
    height: 0.125rem;
    border-radius: 999px;
    background: #3b82f6;
    opacity: 0;
    transform: scaleX(0.35);
    transform-origin: center;
    transition: opacity 300ms ease, transform 300ms ease;
  }

  .tab-button--default.is-active .tab-underline {
    opacity: 1;
    transform: scaleX(1);
  }

  @media (max-width: 640px) {
    .tab-button--jiggle {
      min-height: 2.5rem;
      padding: 0.55rem 0.78rem;
      font-size: 0.79rem;
    }

    .tab-button--jiggle.tab-button--compact {
      min-height: 2.15rem;
      padding: 0.42rem 0.62rem;
      font-size: 0.72rem;
    }

    .tab-slider {
      border-radius: 1rem;
    }
  }
</style>
