<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    padding?: boolean;
    class?: string;
    header?: Snippet;
    children: Snippet;
  }

  let {
    padding = true,
    class: className = '',
    header,
    children,
  }: Props = $props();
</script>

<div
  class="aqua-card motion-surface overflow-hidden {className}"
  style="background-color: white;
         border-radius: 10px;
         box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24),
                     0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.05);
         border: 1px solid rgba(0,0,0,0.1);"
>
  {#if header}
    <div
      class="px-4 py-3 flex items-center"
      style="background-image: linear-gradient(to bottom, #f8f9fb, #d9e1ea);
             box-shadow: 0 1px 0 rgba(255,255,255,0.8) inset, 0 1px 0 rgba(0,0,0,0.1);
             border-bottom: 1px solid rgba(0,0,0,0.1);"
    >
      {@render header()}
    </div>
  {/if}
  <div class={padding ? 'p-4' : ''}>
    {@render children()}
  </div>
</div>

<style>
  @media (hover: hover) and (pointer: fine) {
    .aqua-card:hover {
      box-shadow: 0 10px 22px rgba(85, 102, 130, 0.14), 0 0 0 1px rgba(0,0,0,0.05), inset 0 -5px 10px rgba(0,0,0,0.04);
    }
  }
</style>
