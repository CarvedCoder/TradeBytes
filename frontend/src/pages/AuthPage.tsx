/**
 * Auth Page - WebAuthn Passkey Registration & Login.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import api from '@/lib/api';
import { KeyRound, Fingerprint, ArrowRight, Loader2 } from 'lucide-react';

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  const handleRegister = async () => {
    if (!displayName.trim()) {
      setError('Please enter a display name');
      return;
    }
    setLoading(true);
    setError('');

    try {
      // Step 1: Begin registration
      const { data: beginData } = await api.post('/auth/register/begin', {
        display_name: displayName,
      });

      // Step 2: Create credential via WebAuthn API
      const credential = await navigator.credentials.create({
        publicKey: beginData.options,
      });

      if (!credential) throw new Error('Credential creation failed');

      // Step 3: Complete registration
      const { data: completeData } = await api.post('/auth/register/complete', {
        challenge_id: beginData.challenge_id,
        credential: credential,
      });

      setTokens(completeData.access_token, completeData.refresh_token);
      setUser(completeData.user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    setLoading(true);
    setError('');

    try {
      // Step 1: Begin login
      const { data: beginData } = await api.post('/auth/login/begin', {
        display_name: displayName || undefined,
      });

      // Step 2: Get credential via WebAuthn API
      const credential = await navigator.credentials.get({
        publicKey: beginData.options,
      });

      if (!credential) throw new Error('Authentication failed');

      // Step 3: Complete login
      const { data: completeData } = await api.post('/auth/login/complete', {
        challenge_id: beginData.challenge_id,
        credential: credential,
      });

      setTokens(completeData.access_token, completeData.refresh_token);
      setUser(completeData.user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-950">
      <div className="w-full max-w-md space-y-8 p-8">
        {/* Logo */}
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-600 shadow-lg shadow-primary-600/30">
            <span className="text-2xl font-bold">TB</span>
          </div>
          <h1 className="text-3xl font-bold text-white">TradeBytes</h1>
          <p className="mt-2 text-surface-200">
            AI-Powered Finance Education & Investment Intelligence
          </p>
        </div>

        {/* Auth Card */}
        <div className="card space-y-6">
          {/* Toggle */}
          <div className="flex rounded-lg bg-surface-800 p-1">
            <button
              onClick={() => setMode('login')}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                mode === 'login' ? 'bg-primary-600 text-white' : 'text-surface-200'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setMode('register')}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                mode === 'register' ? 'bg-primary-600 text-white' : 'text-surface-200'
              }`}
            >
              Register
            </button>
          </div>

          {/* Display Name */}
          {(mode === 'register' || displayName) && (
            <div>
              <label className="mb-1 block text-sm font-medium text-surface-200">
                Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="satoshi_trader"
                className="input-field"
                autoFocus
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </div>
          )}

          {/* Action Button */}
          <button
            onClick={mode === 'login' ? handleLogin : handleRegister}
            disabled={loading}
            className="btn-primary flex w-full items-center justify-center gap-2 py-3"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                {mode === 'login' ? (
                  <Fingerprint className="h-5 w-5" />
                ) : (
                  <KeyRound className="h-5 w-5" />
                )}
                {mode === 'login' ? 'Sign in with Passkey' : 'Create Passkey'}
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-surface-200">
            Secured with WebAuthn passkeys. No passwords needed.
          </p>
        </div>
      </div>
    </div>
  );
}
