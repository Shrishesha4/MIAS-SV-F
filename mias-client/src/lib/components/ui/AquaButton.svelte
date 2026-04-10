<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    variant?: 'primary' | 'secondary' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    fullWidth?: boolean;
    disabled?: boolean;
    loading?: boolean;
    type?: 'button' | 'submit';
    onclick?: (e: MouseEvent) => void;
    children: Snippet;
  }

  let {
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    disabled = false,
    loading = false,
    type = 'button',
    onclick,
    children,
  }: Props = $props();

  const variantStyles: Record<string, string> = {
    primary: 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;',
    secondary: 'background: linear-gradient(to bottom, #f0f4fa, #d5dde8); color: #1e40af;',
    danger: 'background: linear-gradient(to bottom, #ff5a5a, #cc0000); color: white;',
  };

  const sizeClasses: Record<string, string> = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };
</script>

<button
  {type}
  disabled={disabled || loading}
  class="motion-control relative overflow-hidden transition-all active:translate-y-0.5 active:shadow-inner
         before:absolute before:inset-0 before:bg-gradient-to-b before:from-white
         before:via-transparent before:to-transparent before:opacity-50 before:transition-opacity
         font-medium rounded-lg cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
         {sizeClasses[size]}
         {fullWidth ? 'w-full' : ''}"
  style="{variantStyles[variant]}
         border: 1px solid rgba(0,0,0,0.2);
         box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
  {onclick}
>
  {#if loading}
    <span class="inline-flex items-center gap-1.5">
      <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      {@render children()}
    </span>
  {:else}
    {@render children()}
  {/if}
</button>

<style>
  @media (hover: hover) and (pointer: fine) {
    button:hover:not(:disabled) {
      box-shadow: 0 6px 14px rgba(0,0,0,0.16), inset 0 1px 0 rgba(255,255,255,0.45);
    }

    button:hover:not(:disabled)::before {
      opacity: 0.7;
    }
  }
</style>
