'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { api, ActivityItem, TransferRequest } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const { user, account, logout, refreshUserData } = useAuth();
  const router = useRouter();
  
  const [toHandle, setToHandle] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [isLoadingActivity, setIsLoadingActivity] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }
    loadActivity();
  }, [user, router]);

  const loadActivity = async () => {
    try {
      const data = await api.getActivity();
      setActivity(data);
    } catch (err) {
      console.error('Failed to load activity:', err);
    } finally {
      setIsLoadingActivity(false);
    }
  };

  const handleSendMoney = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      const amountCents = Math.round(parseFloat(amount) * 100);
      if (amountCents <= 0) {
        throw new Error('Amount must be greater than 0');
      }

      if (!account || amountCents > account.balance) {
        throw new Error('Insufficient balance');
      }

      const transfer: TransferRequest = {
        to_handle: toHandle,
        amount: amountCents,
        note: note || undefined,
      };

      // Generate idempotency key
      const idempotencyKey = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      const result = await api.createTransfer(transfer, idempotencyKey);

      if (result.status === 'pending_review') {
        setSuccess('Transfer is under review due to fraud detection');
      } else {
        setSuccess(`Successfully sent $${amount} to @${toHandle}`);
      }

      // Reset form
      setToHandle('');
      setAmount('');
      setNote('');

      // Refresh data
      await refreshUserData();
      await loadActivity();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Transfer failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  if (!user || !account) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Vaultly</h1>
            <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Balance Card */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-2">Your Balance</h2>
          <p className="text-4xl font-bold text-gray-900">
            ${(account.balance / 100).toFixed(2)}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            @{user.handle}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Send Money Form */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Send Money</h2>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
                {success}
              </div>
            )}

            <form onSubmit={handleSendMoney} className="space-y-4">
              <div>
                <label htmlFor="toHandle" className="block text-sm font-medium text-gray-700 mb-1">
                  Recipient (@username)
                </label>
                <input
                  id="toHandle"
                  type="text"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="username"
                  value={toHandle}
                  onChange={(e) => setToHandle(e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
                  Amount (USD)
                </label>
                <input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="note" className="block text-sm font-medium text-gray-700 mb-1">
                  Note (optional)
                </label>
                <textarea
                  id="note"
                  rows={3}
                  maxLength={280}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What's this for?"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Sending...' : 'Send Money'}
              </button>
            </form>
          </div>

          {/* Activity Feed */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h2>
            
            {isLoadingActivity ? (
              <div className="text-center py-8 text-gray-500">Loading activity...</div>
            ) : activity.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No recent activity. Start by sending money to someone!
              </div>
            ) : (
              <div className="space-y-4">
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`text-sm font-medium ${
                          item.direction === 'sent' ? 'text-red-600' : 'text-green-600'
                        }`}>
                          {item.direction === 'sent' ? 'Sent to' : 'Received from'}
                        </span>
                        <span className="text-sm font-medium text-gray-900">
                          @{item.counterparty_handle}
                        </span>
                      </div>
                      {item.note && (
                        <p className="text-sm text-gray-600 mt-1">{item.note}</p>
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className={`text-lg font-bold ${
                      item.direction === 'sent' ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {item.direction === 'sent' ? '-' : '+'}
                      ${(item.amount / 100).toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
