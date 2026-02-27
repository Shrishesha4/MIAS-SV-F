<script lang="ts">
  interface Props {
    src?: string | null;
    name: string;
    size?: 'sm' | 'md' | 'lg';
  }

  let { src = null, name, size = 'md' }: Props = $props();

  const sizeClasses: Record<string, string> = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-12 h-12 text-sm',
    lg: 'w-20 h-20 text-xl',
  };

  const initials = $derived(
    name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  );
</script>

{#if src}
  <img
    {src}
    alt={name}
    class="rounded-full object-cover {sizeClasses[size]}"
    style="border: 2px solid rgba(255,255,255,0.9);
           box-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);"
  />
{:else}
  <div
    class="rounded-full flex items-center justify-center font-bold text-white {sizeClasses[size]}"
    style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
           border: 2px solid rgba(255,255,255,0.9);
           box-shadow: 0 1px 3px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);"
  >
    {initials}
  </div>
{/if}
