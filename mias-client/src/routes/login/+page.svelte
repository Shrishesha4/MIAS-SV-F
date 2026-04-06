<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { authApi } from '$lib/api/auth';
	import { User, KeyRound, LogIn, UserPlus } from 'lucide-svelte';

	let username = $state('');
	let password = $state('');
	let loading = $state(false);
	let error = $state('');
	let showForgotMsg = $state(false);

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
				error = 'Invalid username or password';
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
<div class="min-h-screen flex flex-col max-w-md mx-auto" onkeydown={handleKeydown}>
	<!-- Hospital Banner Section -->
	<div class="relative overflow-hidden" style="min-height: 280px;">
		<!-- Background gradient simulating hospital image -->
		<div class="absolute inset-0" style="
			background: linear-gradient(160deg, #87CEEB 0%, #B0D4E8 30%, #d1dbed 60%, #c8d5e8 100%);
		"></div>
		<div class="absolute inset-0" style="
			background: linear-gradient(to bottom, rgba(255,255,255,0.1), rgba(255,255,255,0.6));
		"></div>
		<div class="absolute bottom-0 left-0 right-0 h-24" style="
			background: linear-gradient(to top, rgba(200,213,232,0.8), transparent);
		"></div>

		<!-- Logo & Title -->
		<div class="relative z-10 px-6 pt-10 pb-6">
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
	<div class="px-4 -mt-6 relative z-20 flex-1">
		<div
			class="w-full max-w-sm mx-auto overflow-hidden"
			style="background-color: white;
			       border-radius: 10px;
			       box-shadow: 0 2px 6px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);
			       background-image: linear-gradient(to bottom, rgba(255,255,255,1), rgba(245,245,245,0.97));"
		>
			<div class="px-6 py-8">
				<h2
					class="text-xl font-semibold mb-6 text-center text-gray-800"
					style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);"
				>
					Medical Portal Login
				</h2>

				{#if error}
					<div class="mb-4 px-3 py-2 rounded-lg text-sm text-red-600"
						style="background-color: rgba(255,0,0,0.04);
						       border: 1px solid rgba(220,50,50,0.2);">
						{error}
					</div>
				{/if}

				<!-- Username -->
				<div class="mb-5">
					<div
						class="flex items-center px-4 py-3"
						style="border: 1px solid rgba(0,0,0,0.2);
						       border-radius: 6px;
						       background-color: rgba(255,255,255,0.8);
						       box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
					>
						<User class="h-5 w-5 text-gray-400 mr-3 shrink-0" />
						<input
							type="text"
							placeholder="ID / Username"
							bind:value={username}
							class="flex-1 outline-none text-gray-700 bg-transparent placeholder-gray-400"
						/>
					</div>
				</div>

				<!-- Password -->
				<div class="mb-6">
					<div
						class="flex items-center px-4 py-3"
						style="border: 1px solid rgba(0,0,0,0.2);
						       border-radius: 6px;
						       background-color: rgba(255,255,255,0.8);
						       box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);"
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
					class="w-full py-3 rounded-lg flex items-center justify-center font-medium text-white cursor-pointer
					       disabled:opacity-50 disabled:cursor-not-allowed transition-all active:translate-y-0.5 active:shadow-inner"
					style="background: linear-gradient(to bottom, #4d90fe, #0066cc);
					       box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.4);
					       border: 1px solid rgba(0,0,0,0.2);"
					disabled={loading}
					onclick={handleLogin}
				>
					{#if loading}
						<span class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
						Signing in...
					{:else}
						<LogIn class="w-5 h-5 mr-2" />
						Login
					{/if}
				</button>

				<!-- Forgot Password & Divider -->
				<div class="mt-5 text-center flex flex-col space-y-4">
					<button
						class="text-sm text-blue-600 cursor-pointer hover:text-blue-800 transition-colors"
						style="text-shadow: 0 1px 0 rgba(255,255,255,0.5);"
						onclick={() => showForgotMsg = true}
					>
						Forgot Password?
					</button>
					{#if showForgotMsg}
						<p class="text-xs text-gray-600 bg-blue-50 rounded-lg px-3 py-2 border border-blue-200">
							Please contact hospital support at <span class="font-medium">support@saveethamedical.com</span> to reset your password.
						</p>
					{/if}

					<div class="relative flex items-center py-2">
						<div class="flex-grow border-t border-gray-300"></div>
						<span class="flex-shrink-0 mx-4 text-gray-400 text-xs uppercase tracking-wider">Or</span>
						<div class="flex-grow border-t border-gray-300"></div>
					</div>

					<!-- New Patient Registration -->
					<button
						type="button"
						onclick={() => goto('/signup')}
						class="w-full py-3 rounded-lg flex items-center justify-center font-medium text-blue-700 cursor-pointer
						       transition-all active:translate-y-0.5 active:shadow-inner"
						style="background: linear-gradient(to bottom, #f0f4fa, #d5dde8);
						       box-shadow: 0 1px 3px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.8);
						       border: 1px solid rgba(0,0,0,0.2);"
					>
						<UserPlus class="w-5 h-5 mr-2" />
						New Patient Registration
					</button>
				</div>

				<!-- Quick Login (Demo) -->
				<div class="mt-6 pt-4 border-t border-gray-200">
					<p class="text-xs text-gray-400 text-center mb-3">Quick Login (Dev)</p>
					<div class="flex flex-wrap justify-center gap-2">
						<button
							class="px-3 py-1.5 text-xs rounded-md cursor-pointer font-medium transition-colors"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 'p1'; password = 'p1'; }}
						>Patient</button>
						<button
							class="px-3 py-1.5 text-xs rounded-md cursor-pointer font-medium transition-colors"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 's1'; password = 's1'; }}
						>Student</button>
						<button
							class="px-3 py-1.5 text-xs rounded-md cursor-pointer font-medium transition-colors"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.05);"
							onclick={() => { username = 'd1'; password = 'd1'; }}
						>Faculty</button>
						<button
							class="px-3 py-1.5 text-xs rounded-md cursor-pointer font-medium transition-colors"
							style="color: #15803d; border: 1px solid rgba(34,197,94,0.25); background: rgba(34,197,94,0.05);"
							onclick={() => { username = 'r'; password = 'r'; }}
						>Reception</button>
						<button
							class="px-3 py-1.5 text-xs rounded-md cursor-pointer font-medium transition-colors"
							style="color: #9333ea; border: 1px solid rgba(147,51,234,0.25); background: rgba(147,51,234,0.05);"
							onclick={() => { username = 'a'; password = 'a'; }}
						>Admin</button>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Footer -->
	<div class="py-6 text-center" style="text-shadow: 0 1px 0 rgba(255,255,255,0.8);">
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
