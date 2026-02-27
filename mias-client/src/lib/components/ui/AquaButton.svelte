<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    variant?: 'primary' | 'secondary' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    fullWidth?: boolean;
    disabled?: boolean;
    type?: 'button' | 'submit';
    onclick?: (e: MouseEvent) => void;
    children: Snippet;
  }

  let {
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    disabled = false,
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
  {disabled}
  class="relative overflow-hidden transition-all active:translate-y-0.5 active:shadow-inner
         before:absolute before:inset-0 before:bg-gradient-to-b before:from-white
         before:via-transparent before:to-transparent before:opacity-50
         font-medium rounded-lg cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
         {sizeClasses[size]}
         {fullWidth ? 'w-full' : ''}"
  style="{variantStyles[variant]}
         border: 1px solid rgba(0,0,0,0.2);
         box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);"
  {onclick}
>
  {@render children()}
</button>
