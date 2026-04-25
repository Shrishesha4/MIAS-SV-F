import axios, { AxiosHeaders, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { browser } from '$app/environment';
import { get } from 'svelte/store';
import { authStore } from '$lib/stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081/api/v1';

type RetryableAuthDetail =
	| 'not authenticated'
	| 'invalid or expired token'
	| 'user not found or inactive'
	| 'refresh token missing';

type RetriableRequestConfig = InternalAxiosRequestConfig & {
	_retry?: boolean;
};

type RefreshResponse = {
	access_token: string;
	user_id?: string;
	role?: string;
};

const RETRYABLE_AUTH_DETAILS = new Set<RetryableAuthDetail>([
	'not authenticated',
	'invalid or expired token',
	'user not found or inactive',
	'refresh token missing'
]);

const client = axios.create({
	baseURL: API_BASE_URL,
	headers: {
		'Content-Type': 'application/json'
	},
	// Required so the browser sends the httpOnly refresh_token cookie
	// to cross-origin API endpoints.
	withCredentials: true
});

let refreshPromise: Promise<string | null> | null = null;

function normalizeErrorDetail(error: AxiosError): string {
	const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
	return typeof detail === 'string' ? detail.trim().toLowerCase() : '';
}

function shouldAttemptRefresh(error: AxiosError, request?: RetriableRequestConfig): boolean {
	if (!browser || !request || request._retry) {
		return false;
	}

	const requestUrl = String(request.url || '');
	if (requestUrl.includes('/auth/login') || requestUrl.includes('/auth/refresh') || requestUrl.includes('/auth/logout')) {
		return false;
	}

	const status = error.response?.status;
	if (status !== 401 && status !== 403) {
		return false;
	}

	const detail = normalizeErrorDetail(error);
	if (!detail) {
		return status === 401;
	}

	return RETRYABLE_AUTH_DETAILS.has(detail as RetryableAuthDetail);
}

function setAuthorizationHeader(
	config: Pick<InternalAxiosRequestConfig, 'headers'>,
	accessToken: string
): void {
	const headers =
		config.headers instanceof AxiosHeaders
			? config.headers
			: new AxiosHeaders(config.headers);

	headers.set('Authorization', `Bearer ${accessToken}`);
	config.headers = headers;
}

async function refreshAccessToken(): Promise<string | null> {
	if (!browser) {
		return null;
	}

	if (!refreshPromise) {
		refreshPromise = (async () => {
			try {
				const response = await axios.post<RefreshResponse>(
					`${API_BASE_URL}/auth/refresh`,
					null,
					{ withCredentials: true }
				);

				const { access_token, user_id, role } = response.data;
				if (!access_token) {
					throw new Error('Missing access token from refresh response');
				}

				authStore.setTokens(access_token, user_id, role);
				return access_token;
			} catch {
				authStore.logout();
				if (browser) {
					window.location.href = '/login';
				}
				return null;
			} finally {
				refreshPromise = null;
			}
		})();
	}

	return refreshPromise;
}

// Request interceptor - attach Bearer token from in-memory store
client.interceptors.request.use((config) => {
	if (browser) {
		const auth = get(authStore);
		if (auth.accessToken) {
			setAuthorizationHeader(config, auth.accessToken);
		}
	}
	return config;
});

// Response interceptor - silent token refresh on auth expiry / missing auth
client.interceptors.response.use(
	(response) => response,
	async (error: AxiosError) => {
		const originalRequest = error.config as RetriableRequestConfig | undefined;

		if (!shouldAttemptRefresh(error, originalRequest)) {
			return Promise.reject(error);
		}

		if (!originalRequest) {
			return Promise.reject(error);
		}

		originalRequest._retry = true;

		const accessToken = await refreshAccessToken();
		if (!accessToken) {
			return Promise.reject(error);
		}

		setAuthorizationHeader(originalRequest, accessToken);
		return client(originalRequest);
	}
);

export default client;
