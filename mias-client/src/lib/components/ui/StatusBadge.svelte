<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    variant?: 'success' | 'error' | 'warning' | 'info' | 'normal' | 'abnormal' | 'critical' | 'pending';
    size?: 'sm' | 'md';
    children: Snippet;
  }

  let {
    variant = 'info',
    size = 'sm',
    children,
  }: Props = $props();

  const variantStyles: Record<string, string> = {
    success: 'background: linear-gradient(to bottom, #a7f3d0, #6ee7b7); border: 1px solid rgba(16,185,129,0.3); color: #065f46;',
    error: 'background: linear-gradient(to bottom, #ff5a5a, #cc0000); color: white;',
    warning: 'background: linear-gradient(to bottom, #ff9500, #ff5e3a); color: white;',
    info: 'background: linear-gradient(to bottom, #4d90fe, #0066cc); color: white;',
    normal: 'background: linear-gradient(to bottom, #34c759, #30b350); color: white;',
    abnormal: 'background: linear-gradient(to bottom, #ff9500, #ff5e3a); color: white;',
    critical: 'background: linear-gradient(to bottom, #ff3b30, #d70015); color: white;',
    pending: 'background: linear-gradient(to bottom, #8e8e93, #636366); color: white;',
  };

  const sizeClasses: Record<string, string> = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  };
</script>

<span
  class="inline-flex items-center rounded-full font-medium {sizeClasses[size]}"
  style={variantStyles[variant]}
>
  {@render children()}
</span>
