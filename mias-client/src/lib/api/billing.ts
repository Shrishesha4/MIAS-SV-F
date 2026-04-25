import client from './client';

export interface BillingProfile {
  id: string;
  billing_id: string;
  name: string;
  counter_name: string | null;
  phone: string | null;
  email: string | null;
  username: string;
}

export interface AccountsAnalyticsSummary {
  total_collection: number;
  cash: number;
  card_digital: number;
}

export interface AccountsAnalyticsBillingCenter {
  id: string;
  name: string;
  value: number;
  color: string;
}

export interface AccountsAnalyticsTransaction {
  id: string;
  name: string;
  subtitle: string;
  amount: number;
  method: string;
  time: string;
  type: string;
  wallet_type: string;
  date: string | null;
  reference_number: string | null;
  provider: string | null;
}

export interface AccountsAnalyticsCollectionRow {
  id: string;
  department: string;
  cash: number;
  card: number;
  total: number;
}

export interface AccountsAnalyticsUserRow {
  id: string;
  name: string;
  total_collection: number;
  transactions: number;
  status: string;
  status_tone: 'primary' | 'success' | 'warning';
}

export interface AccountsAnalyticsTrendSeries {
  id: string;
  label: string;
  color: string;
  values: number[];
}

export interface AccountsAnalyticsTrendSections {
  OVERVIEW: AccountsAnalyticsTrendSeries[];
  DEPARTMENTS: AccountsAnalyticsTrendSeries[];
  INVESTIGATIONS: AccountsAnalyticsTrendSeries[];
}

export interface AccountsAnalyticsMeta {
  start_date: string;
  end_date: string;
  branch: string;
  department: string;
  billing_user_count: number;
}

export interface AccountsAnalyticsResponse {
  summary: AccountsAnalyticsSummary;
  billing_centers: AccountsAnalyticsBillingCenter[];
  live_transactions: AccountsAnalyticsTransaction[];
  collections: AccountsAnalyticsCollectionRow[];
  users: AccountsAnalyticsUserRow[];
  trend_labels: string[];
  trends: Partial<Record<'1W' | '1M' | '1Q' | '1Y', AccountsAnalyticsTrendSections>>;
  meta: AccountsAnalyticsMeta;
}

export const billingApi = {
  async getMe(): Promise<BillingProfile> {
    const response = await client.get('/billing/me');
    return response.data;
  },

  async getAccountsAnalytics(params?: {
    start_date?: string;
    end_date?: string;
    branch?: string;
    department?: string;
    trend_range?: '1W' | '1M' | '1Q' | '1Y';
  }): Promise<AccountsAnalyticsResponse> {
    const response = await client.get('/billing/accounts/analytics', {
      params,
    });
    return response.data;
  },
};
