<script module lang="ts">
  let openModalCount = 0;
  let previousBodyOverflow = '';

  function lockBodyScroll() {
    if (typeof document === 'undefined') {
      return;
    }

    if (openModalCount === 0) {
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }

    openModalCount += 1;
  }

  function unlockBodyScroll() {
    if (typeof document === 'undefined' || openModalCount === 0) {
      return;
    }

    openModalCount -= 1;

    if (openModalCount === 0) {
      document.body.style.overflow = previousBodyOverflow;
    }
  }
</script>

<script lang="ts">
  import type { Snippet } from 'svelte';
  import { cubicOut } from 'svelte/easing';
  import { fade, fly } from 'svelte/transition';
  import { X } from 'lucide-svelte';

  interface Props {
    open?: boolean;
    title?: string;
    onclose?: () => void;
    onClose?: () => void;  // Alternative prop name
    header?: Snippet;
    panelClass?: string;
    contentClass?: string;
    children: Snippet;
  }

  let {
    open = true,
    title = '',
    onclose,
    onClose,
    header,
    panelClass = 'sm:max-w-md',
    contentClass = 'p-4',
    children
  }: Props = $props();

  function portal(node: HTMLElement) {
    if (typeof document === 'undefined') {
      return {};
    }

    document.body.appendChild(node);
    lockBodyScroll();

    return {
      destroy() {
        unlockBodyScroll();
        node.remove();
      }
    };
  }

  const handleClose = () => {
    if (onclose) onclose();
    if (onClose) onClose();
  };
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    use:portal
    class="fixed left-0 top-0 z-[200] flex h-[100dvh] w-screen items-end justify-center p-3 sm:items-center sm:p-4 motion-overlay"
    style="background-color: rgba(15, 23, 42, 0.14); backdrop-filter: blur(3px); -webkit-backdrop-filter: blur(3px);"
    onkeydown={(e) => e.key === 'Escape' && handleClose()}
    transition:fade={{ duration: 180 }}
  >
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="absolute inset-0" onclick={handleClose}></div>
    <div
      class={`motion-dialog pointer-events-auto relative flex max-h-[90vh] w-full flex-col ${panelClass}`}
      style="background-color: white;
            border-radius: 20px;
            box-shadow: 0 -8px 28px rgba(0,0,0,0.18);
             border: 1px solid rgba(0,0,0,0.1);"
      in:fly={{ y: 24, duration: 280, easing: cubicOut }}
      out:fly={{ y: 18, duration: 180 }}
    >
      <!-- Header -->
      <div
        class="px-4 py-3 flex items-center justify-between z-10 shrink-0"
        style="background-image: linear-gradient(to bottom, #f8f9fb, #e8eef5);
               box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
               border-bottom: 1px solid rgba(0,0,0,0.1);
           border-radius: 20px 20px 0 0;"
      >
        {#if header}
          <div class="flex-1">
            {@render header()}
          </div>
        {:else if title}
          <h3 class="text-blue-900 font-semibold" style="text-shadow: 0 1px 0 rgba(255,255,255,0.7);">
            {title}
          </h3>
        {:else}
          <div></div>
        {/if}
        <button class="motion-control modal-close text-gray-500 hover:text-gray-700 cursor-pointer ml-2" onclick={handleClose}>
          <X class="w-5 h-5" />
        </button>
      </div>
      <div class={`${contentClass} overflow-y-auto flex-1`}>
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  .motion-dialog {
    transition: box-shadow 220ms ease, transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
    overflow: hidden;
  }

  .motion-overlay {
    inset: 0;
  }

  .modal-close {
    transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1), color 180ms ease;
  }

  @media (hover: hover) and (pointer: fine) {
    .modal-close:hover {
      transform: rotate(90deg) scale(1.04);
    }
  }
</style>
