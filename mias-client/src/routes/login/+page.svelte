<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores/auth';
	import { authApi } from '$lib/api/auth';
	import { User, KeyRound, LogIn, UserPlus, Eye, EyeOff } from 'lucide-svelte';

	let username = $state('');
	let password = $state('');
	let loading = $state(false);
	let error = $state('');
	let showForgotMsg = $state(false);
	let showPassword = $state(false);

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
			if (result.role === 'STUDENT') {
				goto('/patients');
			} else {
				goto('/dashboard');
			}
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
<div
	class="min-h-screen flex flex-col items-center justify-start px-4 py-6 sm:py-8 relative overflow-hidden"
	onkeydown={handleKeydown}
>
	<div
		class="absolute inset-0"
		style="background: linear-gradient(180deg, #dce7f5 0%, #d7e2f1 45%, #d3deee 100%);"
	></div>

	<!-- Top banner -->
	<div class="relative z-10 w-full max-w-6xl">
		<div
			class="w-full overflow-hidden rounded-[0_0_28px_28px] border border-white/70"
			style="box-shadow: 0 10px 28px rgba(70, 102, 150, 0.14);"
		>
			<img
				src="/login_banner.png"
				alt="Saveetha Medical portal banner"
				class="block h-auto max-h-[240px] w-full object-cover object-center"
			/>
		</div>
	</div>

	<!-- Bottom: Login Card -->
	<div class="relative z-10 w-full max-w-sm mt-[-8px] sm:mt-[-16px]">
		<div
			class="w-full rounded-2xl overflow-hidden"
			style="background: rgba(255,255,255,0.97);
				   box-shadow: 0 8px 32px rgba(0,0,0,0.28), 0 1px 4px rgba(0,0,0,0.1);
				   border: 1px solid rgba(255,255,255,0.8);"
		>
			<div class="px-6 py-7">
				<h2 class="text-lg font-bold text-gray-800 mb-5 text-center">Login</h2>

				{#if error}
					<div class="mb-4 px-3 py-2 rounded-lg text-sm text-red-600"
						style="background: rgba(255,0,0,0.04); border: 1px solid rgba(220,50,50,0.2);">
						{error}
					</div>
				{/if}

				<!-- Username -->
				<div class="mb-3.5">
					<label for="login-username" class="text-xs font-medium text-gray-600 mb-1 block">ID / Username</label>
					<div class="relative">
						<User class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
						<input
							id="login-username"
							type="text"
							placeholder="Enter your ID or username"
							bind:value={username}
							class="w-full pl-9 pr-3 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
					</div>
				</div>

				<!-- Password -->
				<div class="mb-5">
					<label for="login-password" class="text-xs font-medium text-gray-600 mb-1 block">Password</label>
					<div class="relative">
						<KeyRound class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
						<input
							id="login-password"
							type={showPassword ? 'text' : 'password'}
							placeholder="Enter your password"
							bind:value={password}
							class="w-full pl-9 pr-10 py-2.5 rounded-lg text-sm outline-none"
							style="background: #f7f9fd; border: 1px solid rgba(0,0,0,0.14);"
						/>
						<button
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 cursor-pointer hover:text-gray-600"
							onclick={() => showPassword = !showPassword}
						>
							{#if showPassword}<EyeOff class="w-4 h-4" />{:else}<Eye class="w-4 h-4" />{/if}
						</button>
					</div>
				</div>

				<!-- Login Button -->
				<button
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-white font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-60"
					style="background: linear-gradient(to bottom, #4d90fe, #3b7aed);
						   box-shadow: 0 2px 8px rgba(59,122,237,0.4);
						   border: 1px solid rgba(0,0,0,0.1);"
					disabled={loading}
					onclick={handleLogin}
				>
					{#if loading}
						<span class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
						Signing in...
					{:else}
						<LogIn class="w-4 h-4" />
						Login
					{/if}
				</button>

				<!-- Forgot password -->
				<div class="mt-3 text-center">
					<button
						class="text-xs text-blue-600 cursor-pointer hover:underline"
						onclick={() => showForgotMsg = !showForgotMsg}
					>
						Forgot Password?
					</button>
					{#if showForgotMsg}
						<p class="mt-2 text-xs text-gray-600 bg-blue-50 rounded-lg px-3 py-2 border border-blue-100 text-left">
							Contact hospital support: <span class="font-medium">support@saveethamedical.com</span>
						</p>
					{/if}
				</div>

				<!-- Divider -->
				<!-- <div class="relative flex items-center py-4">
					<div class="flex-grow border-t border-gray-200"></div>
					<span class="flex-shrink-0 mx-4 text-gray-400 text-xs uppercase tracking-wider">Or</span>
					<div class="flex-grow border-t border-gray-200"></div>
				</div> -->

				<!-- New Patient Registration -->
				<!-- <button
					type="button"
					onclick={() => goto('/register')}
					class="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm cursor-pointer transition-opacity hover:opacity-90 active:scale-[0.98]"
					style="background: linear-gradient(to bottom, #f0f4fa, #dce6f5);
						   color: #1e4db7;
						   box-shadow: 0 1px 4px rgba(0,0,0,0.1);
						   border: 1px solid rgba(0,0,0,0.12);"
				>
					<UserPlus class="w-4 h-4" />
					New Patient Registration
				</button> -->

				<!-- Quick Login (Dev) -->
				<!-- <div class="mt-5 pt-4 border-t border-gray-100">
					<p class="text-[10px] text-gray-400 text-center mb-2.5 uppercase tracking-wider">Quick Login (Dev)</p>
					<div class="flex flex-wrap justify-center gap-1.5">
						<button
							class="px-2.5 py-1 text-xs rounded-md cursor-pointer font-medium"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.06);"
							onclick={() => { username = 'p1'; password = 'p1'; }}
						>Patient</button>
						<button
							class="px-2.5 py-1 text-xs rounded-md cursor-pointer font-medium"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.06);"
							onclick={() => { username = 's1'; password = 's1'; }}
						>Student</button>
						<button
							class="px-2.5 py-1 text-xs rounded-md cursor-pointer font-medium"
							style="color: #1d4ed8; border: 1px solid rgba(59,130,246,0.25); background: rgba(59,130,246,0.06);"
							onclick={() => { username = 'd1'; password = 'd1'; }}
						>Faculty</button>
						<button
							class="px-2.5 py-1 text-xs rounded-md cursor-pointer font-medium"
							style="color: #15803d; border: 1px solid rgba(34,197,94,0.25); background: rgba(34,197,94,0.06);"
							onclick={() => { username = 'r'; password = 'r'; }}
						>Reception</button>
						<button
							class="px-2.5 py-1 text-xs rounded-md cursor-pointer font-medium"
							style="color: #9333ea; border: 1px solid rgba(147,51,234,0.25); background: rgba(147,51,234,0.06);"
							onclick={() => { username = 'a'; password = 'a'; }}
						>Admin</button>
					</div>
				</div> -->
			</div>
		</div>

		<p class="text-center text-slate-600 text-[11px] mt-4">
			Need help? Contact hospital support at 
		</p>
		<p class="text-center text-slate-600 text-[11px] pb-2">
			<a href="mailto:support@saveethamedical.com" class="text-blue-600 hover:underline">support@saveethamedical.com</a>
		</p>
	</div>
</div>
