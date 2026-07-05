'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { api, ActivityItem, TransferRequest } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { avatarColor, initials } from '@/lib/avatar';

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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-600 via-blue-600 to-blue-500">
        <div className="text-center text-white font-medium">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-blue-500 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-white/20 flex items-center justify-center text-lg font-bold text-white">
              V
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-tight">Vaultly</h1>
              <p className="text-xs text-blue-100">Welcome, {user.full_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`h-9 w-9 rounded-full ${avatarColor(user.handle)} flex items-center justify-center text-sm font-bold text-white`}>
              {initials(user.full_name)}
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 text-sm font-medium text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-lg transition"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Balance Card */}
        <div className="bg-gradient-to-br from-indigo-600 via-blue-600 to-blue-500 rounded-2xl shadow-lg p-6 mb-8 text-white">
          <h2 className="text-sm font-medium text-blue-100 mb-2">Your Balance</h2>
          <p className="text-4xl font-bold">
            ${(account.balance / 100).toFixed(2)}
          </p>
          <span className="inline-block mt-3 text-xs font-medium bg-white/20 px-2.5 py-1 rounded-full">
            @{user.handle}
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Send Money Form */}
          <div className="bg-white rounded-2xl shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Send Money</h2>

            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-lg mb-4 text-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-lg mb-4 text-sm">
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
                  className="w-full px-4 py-2.5 border border-gray-200 bg-gray-50 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                  className="w-full px-4 py-2.5 border border-gray-200 bg-gray-50 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                  className="w-full px-4 py-2.5 border border-gray-200 bg-gray-50 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="What's this for? 🍕"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-600 to-blue-500 hover:from-indigo-700 hover:to-blue-600 text-white font-semibold py-3 px-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md transition"
              >
                {isLoading ? 'Sending...' : 'Send Money'}
              </button>
            </form>
          </div>

          {/* Activity Feed */}
          <div className="bg-white rounded-2xl shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>

            {isLoadingActivity ? (
              <div className="text-center py-8 text-gray-500">Loading activity...</div>
            ) : activity.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No recent activity. Start by sending money to someone!
              </div>
            ) : (
              <div className="space-y-3">
                {activity.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-xl transition"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`h-10 w-10 shrink-0 rounded-full ${avatarColor(item.counterparty_handle)} flex items-center justify-center text-sm font-bold text-white`}>
                        {initials(item.counterparty_name)}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm text-gray-500">
                            {item.direction === 'sent' ? 'To' : 'From'}
                          </span>
                          <span className="text-sm font-semibold text-gray-900 truncate">
                            @{item.counterparty_handle}
                          </span>
                        </div>
                        {item.note && (
                          <p className="text-sm text-gray-600 truncate">{item.note}</p>
                        )}
                        <p className="text-xs text-gray-400">
                          {new Date(item.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className={`text-base font-bold shrink-0 ml-3 ${
                      item.direction === 'sent' ? 'text-gray-700' : 'text-emerald-600'
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
