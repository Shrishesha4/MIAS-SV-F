import axios from 'axios';
import { browser } from '$app/environment';
import { get } from 'svelte/store';
import { authStore } from '$lib/stores/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Required so the browser sends the httpOnly refresh_token cookie
  // to cross-origin API endpoints.
  withCredentials: true,
});

// Request interceptor - attach Bearer token from in-memory store
client.interceptors.request.use((config) => {
  if (browser) {
    const auth = get(authStore);
    if (auth.accessToken) {
      config.headers.Authorization = `Bearer ${auth.accessToken}`;
    }
  }
  return config;
});

// Response interceptor - silent token refresh on 401
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry && browser) {
      originalRequest._retry = true;

      try {
        // POST with no body; httpOnly cookie is sent automatically via withCredentials.
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          { withCredentials: true },
        );

        const { access_token, user_id, role } = response.data;
        authStore.setTokens(access_token, user_id, role);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return client(originalRequest);
      } catch {
        authStore.logout();
        if (browser) window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default client;
