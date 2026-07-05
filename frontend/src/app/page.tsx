'use client';

import { useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.push('/dashboard');
      } else {
        router.push('/login');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-br from-indigo-600 via-blue-600 to-blue-500">
      <div className="h-16 w-16 rounded-2xl bg-white/20 flex items-center justify-center text-3xl font-bold text-white mb-4">
        V
      </div>
      <h1 className="text-4xl font-bold mb-2 text-white">Vaultly</h1>
      <p className="text-lg text-blue-100">Loading...</p>
    </main>
  );
}
