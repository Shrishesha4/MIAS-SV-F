import client from './client';
import type { LoginResponse } from './types';

export const authApi = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await client.post('/auth/login', { username, password });
    return response.data;
  },

  async refresh(refreshToken: string): Promise<LoginResponse> {
    const response = await client.post('/auth/refresh', { refresh_token: refreshToken });
    return response.data;
  },

  async logout(): Promise<void> {
    await client.post('/auth/logout');
  },
};
