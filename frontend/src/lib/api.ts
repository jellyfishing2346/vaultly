/**
 * API client for communicating with the Vaultly backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiError {
  detail: string;
}

export interface User {
  id: string;
  email: string;
  handle: string;
  full_name: string;
}

export interface Account {
  id: string;
  balance: number;
  currency: string;
}

export interface TransferRequest {
  to_handle: string;
  amount: number;
  note?: string;
}

export interface TransferResponse {
  id: string;
  status: string;
  amount: number;
  note?: string;
  replayed: boolean;
}

export interface ActivityItem {
  id: string;
  direction: 'sent' | 'received';
  counterparty_handle: string;
  counterparty_name: string;
  amount: number;
  note?: string;
  status: string;
  created_at: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  // Auth
  async signup(email: string, handle: string, full_name: string, password: string) {
    return this.request<{ access_token: string }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, handle, full_name, password }),
    });
  }

  async login(email: string, password: string) {
    return this.request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  // User
  async getMe(): Promise<{ user: User; account: Account }> {
    const [user, account] = await Promise.all([
      this.request<User>('/me'),
      this.request<Account>('/me/account'),
    ]);
    return { user, account };
  }

  // Transfers
  async createTransfer(
    transfer: TransferRequest,
    idempotencyKey: string
  ): Promise<TransferResponse> {
    return this.request('/transfers', {
      method: 'POST',
      body: JSON.stringify(transfer),
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    });
  }

  async getActivity(limit: number = 25): Promise<ActivityItem[]> {
    return this.request(`/transfers/activity?limit=${limit}`);
  }
}

export const api = new ApiClient();
