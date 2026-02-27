<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { authApi } from '$lib/api/auth';
	import { User, KeyRound, LogIn } from 'lucide-svelte';

	let username = $state('');
	let password = $state('');
	let loading = $state(false);
	let error = $state('');

	async function handleLogin() {
		if (!username || !password) {
			error = 'Please enter both username and password';
			return;
		}
		loading = true;
		error = '';
		try {
			const result = await authApi.login(username, password);
			authStore.setTokens(result.access_token, result.refresh_token, result.user_id, result.role);
			goto('/dashboard');
		} catch (err: any) {
			if (err?.response?.status === 401) {
				error = 'Invalid credentials. Try p/p, s/s, or t/t';
			} else {
				error = 'Connection error. Please check if the server is running.';
			}
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleLogin();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="min-h-screen flex flex-col" onkeydown={handleKeydown}>
	<!-- Hospital Banner Section -->
	<div class="relative overflow-hidden" style="min-height: 260px;">
		<!-- Background gradient simulating hospital image -->
		<div class="absolute inset-0" style="
			background: linear-gradient(160deg, #87CEEB 0%, #B0D4E8 30%, #d1dbed 60%, #c8d5e8 100%);
		"></div>
		<!-- Overlay pattern -->
		<div class="absolute inset-0" style="
			background: linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0.6));
		"></div>
		<!-- Decorative building silhouette -->
		<div class="absolute bottom-0 left-0 right-0 h-24" style="
			background: linear-gradient(to top, rgba(200,213,232,0.8), transparent);
		"></div>

		<!-- Logo & Title -->
		<div class="relative z-10 px-6 pt-10 pb-6">
			<!-- Saveetha Logo SVG -->
			<div class="mb-4">
				<svg width="80" height="80" viewBox="0 0 100 100" fill="none">
					<circle cx="42" cy="32" r="14" fill="#00BCD4" opacity="0.9"/>
					<circle cx="58" cy="32" r="14" fill="#FF9800" opacity="0.9"/>
					<circle cx="42" cy="52" r="14" fill="#2196F3" opacity="0.9"/>
					<circle cx="58" cy="52" r="14" fill="#4CAF50" opacity="0.9"/>
					<circle cx="50" cy="42" r="8" fill="white"/>
				</svg>
			</div>
			<h1 class="text-2xl font-bold text-gray-800 leading-tight">
				Saveetha Medical College and Hospitals
			</h1>
			<p class="text-sm font-semibold text-blue-600 mt-2">
				Medical Information Archival System (MIAS)
			</p>
		</div>
	</div>

	<!-- Login Card -->
	<div class="px-4 -mt-4 relative z-20 flex-1">
		<div
			class="rounded-2xl overflow-hidden"
			style="background-color: white;
			       box-shadow: 0 4px 20px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
			       border: 1px solid rgba(0,0,0,0.08);"
		>
			<div class="px-6 pt-6 pb-2">
				<h2 class="text-xl font-bold text-gray-800 text-center">Medical Portal Login</h2>
			</div>

			<div class="px-6 pb-6 space-y-4">
				{#if error}
					<div class="px-3 py-2 rounded-lg text-sm text-red-700"
						style="background-color: rgba(255,0,0,0.05);
						       border: 1px solid rgba(220,50,50,0.2);">
						{error}
					</div>
				{/if}

				<!-- Username -->
				<div class="space-y-4">
					<div
						class="flex items-center px-4 py-3.5"
						style="border: 1px solid rgba(0,0,0,0.15);
						       border-radius: 8px;
						       background-color: white;"
					>
						<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
						<input
							type="text"
							placeholder="ID / Username"
							bind:value={username}
							class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400"
						/>
					</div>

					<!-- Password -->
					<div
						class="flex items-center px-4 py-3.5"
						style="border: 1px solid rgba(0,0,0,0.15);
						       border-radius: 8px;
						       background-color: white;"
					>
						<KeyRound class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
						<input
							type="password"
							placeholder="Password"
							bind:value={password}
							class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400"
						/>
					</div>
				</div>

				<!-- Login Button -->
				<button
					class="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-white font-semibold text-base cursor-pointer
					       disabled:opacity-50 disabled:cursor-not-allowed transition-all active:translate-y-0.5"
					style="background: linear-gradient(to bottom, #5a9cff, #2d7ae8);
					       border: 1px solid rgba(0,0,0,0.15);
					       box-shadow: 0 2px 8px rgba(45,122,232,0.35), inset 0 1px 0 rgba(255,255,255,0.3);"
					disabled={loading}
					onclick={handleLogin}
				>
					{#if loading}
						<span class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
						Signing in...
					{:else}
						<LogIn class="w-5 h-5" />
						Login
					{/if}
				</button>

				<!-- Forgot Password -->
				<div class="text-center">
					<button class="text-sm text-blue-500 font-medium cursor-pointer hover:text-blue-700 transition-colors">
						Forgot Password?
					</button>
				</div>

				<!-- Test credentials -->
				<div class="pt-2 border-t border-gray-100">
					<p class="text-xs text-gray-400 text-center mb-2">Quick Login (Demo)</p>
					<div class="flex justify-center gap-2">
						<button
							class="px-3 py-1.5 text-xs rounded-lg cursor-pointer text-blue-600 font-medium hover:bg-blue-50 transition-colors"
							style="border: 1px solid rgba(59,130,246,0.2); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 'p'; password = 'p'; }}
						>Patient</button>
						<button
							class="px-3 py-1.5 text-xs rounded-lg cursor-pointer text-blue-600 font-medium hover:bg-blue-50 transition-colors"
							style="border: 1px solid rgba(59,130,246,0.2); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 's'; password = 's'; }}
						>Student</button>
						<button
							class="px-3 py-1.5 text-xs rounded-lg cursor-pointer text-blue-600 font-medium hover:bg-blue-50 transition-colors"
							style="border: 1px solid rgba(59,130,246,0.2); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 't'; password = 't'; }}
						>Faculty</button>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Footer -->
	<div class="py-6 text-center">
		<p class="text-xs text-gray-500">Need help? Contact hospital support at</p>
		<p class="text-xs text-gray-600 font-medium">support@saveethamedical.com</p>
	</div>
</div>

<style>
	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>
