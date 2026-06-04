"use client";

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Mail, Lock, ArrowRight, AlertCircle, CheckCircle2, Loader2, Sparkles } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authMode, setAuthMode] = useState<'signin' | 'signup' | 'forgot'>('signin');
  
  // Form fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    // Check if user is already logged in
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        router.push('/');
      } else {
        setLoading(false);
      }
    };
    checkUser();

    // Listen for auth state changes
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        router.push('/');
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [router]);

  const handleGoogleSignIn = async () => {
    setFormLoading(true);
    setError(null);
    setMessage(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: typeof window !== 'undefined' ? `${window.location.origin}/` : '',
        }
      });
      if (error) throw error;
    } catch (err: any) {
      setError(err.message || "Failed to authenticate with Google");
      setFormLoading(false);
    }
  };

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setFormLoading(true);
    setError(null);
    setMessage(null);
    
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password
      });
      if (error) throw error;
      router.push('/');
    } catch (err: any) {
      setError(err.message || "Invalid login credentials");
      setFormLoading(false);
    }
  };

  const handleEmailSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setFormLoading(true);
    setError(null);
    setMessage(null);
    
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: typeof window !== 'undefined' ? `${window.location.origin}/` : '',
        }
      });
      
      setFormLoading(false);
      if (error) throw error;
      
      if (data?.user && data.session === null) {
        setMessage("Verification email sent! Please check your inbox to activate your account.");
      } else {
        router.push('/');
      }
    } catch (err: any) {
      setError(err.message || "Failed to create account");
      setFormLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setFormLoading(true);
    setError(null);
    setMessage(null);
    
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: typeof window !== 'undefined' ? `${window.location.origin}/` : '',
      });
      setFormLoading(false);
      if (error) throw error;
      setMessage("Password reset link sent! Check your email inbox.");
    } catch (err: any) {
      setError(err.message || "Failed to send reset link");
      setFormLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030303] flex items-center justify-center font-sans">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030303] flex flex-col items-center justify-center p-4 font-sans relative overflow-hidden">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/5 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-500/5 rounded-full blur-[140px] pointer-events-none" />
      
      {/* Background Noise Grid */}
      <div className="absolute inset-0 opacity-[0.015] bg-[url('https://grainy-gradients.vercel.app/noise.svg')] pointer-events-none" />
      
      <div className="w-full max-w-md z-10">
        {/* Logo and Brand */}
        <div className="text-center mb-8 flex flex-col items-center">
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-purple-500 p-[1px] shadow-[0_0_30px_rgba(6,182,212,0.2)] mb-4"
          >
            <div className="w-full h-full bg-[#0a0a0a] rounded-2xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-cyan-400" />
            </div>
          </motion.div>
          <motion.h1 
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-3xl font-bold text-white tracking-tight"
          >
            Astra Engine
          </motion.h1>
          <motion.p 
            initial={{ y: 5, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-[10px] text-zinc-500 uppercase tracking-[0.35em] mt-2 font-bold"
          >
            Secure access gateway
          </motion.p>
        </div>

        {/* Auth Card Container */}
        <motion.div 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="bg-zinc-950/40 backdrop-blur-2xl border border-white/5 p-8 rounded-3xl shadow-[0_0_80px_rgba(0,0,0,0.8)] relative group overflow-hidden"
        >
          {/* Card Border Glow */}
          <div className="absolute inset-0 border border-cyan-500/10 rounded-3xl pointer-events-none transition-colors duration-500 group-hover:border-cyan-500/20" />
          
          <AnimatePresence mode="wait">
            {/* Errors / Success Alerts */}
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6 p-3.5 bg-red-500/5 border border-red-500/20 rounded-xl flex items-start gap-3"
              >
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span className="text-[11px] font-medium text-red-400 leading-normal">{error}</span>
              </motion.div>
            )}

            {message && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mb-6 p-3.5 bg-emerald-500/5 border border-emerald-500/20 rounded-xl flex items-start gap-3"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span className="text-[11px] font-medium text-emerald-400 leading-normal">{message}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Social Log In */}
          {authMode === 'signin' && (
            <>
              <button
                type="button"
                disabled={formLoading}
                onClick={handleGoogleSignIn}
                className="w-full h-11 rounded-xl bg-zinc-900 border border-white/5 flex items-center justify-center gap-3 text-xs font-semibold text-zinc-200 hover:bg-white/5 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
              >
                {formLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
                ) : (
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path
                      fill="#EA4335"
                      d="M5.266 9.765A7.077 7.077 0 0 1 12 4.909c1.69 0 3.218.6 4.418 1.582L19.91 3C17.782 1.145 15.055 0 12 0 7.354 0 3.373 2.736 1.482 6.727l3.784 3.038z"
                    />
                    <path
                      fill="#4285F4"
                      d="M23.49 12.273c0-.818-.073-1.609-.209-2.373H12v4.509h6.445a5.51 5.51 0 0 1-2.39 3.618l3.736 2.891c2.182-2.009 3.445-4.964 3.445-8.645z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.266 14.235a7.127 7.127 0 0 1 0-4.47l-3.784-3.038a11.968 11.968 0 0 0 0 10.546l3.784-3.038z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 24c3.245 0 5.973-1.073 7.964-2.909l-3.736-2.891c-1.036.691-2.364 1.109-4.228 1.109-3.418 0-6.318-2.318-7.355-5.427L.863 17.273C2.754 21.264 6.736 24 12 24z"
                    />
                  </svg>
                )}
                <span>Sign in with Google</span>
              </button>

              <div className="relative my-6 flex items-center justify-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/5" />
                </div>
                <span className="relative px-3 bg-[#0d0d0d] text-[10px] uppercase font-bold tracking-widest text-zinc-600">
                  or email credentials
                </span>
              </div>
            </>
          )}

          {/* Form Actions */}
          <form onSubmit={
            authMode === 'signin' ? handleEmailSignIn :
            authMode === 'signup' ? handleEmailSignUp :
            handleForgotPassword
          } className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-[10px] uppercase font-bold tracking-widest text-zinc-500">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-600" />
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  disabled={formLoading}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-11 pl-11 pr-4 bg-black/40 border border-white/5 rounded-xl text-xs text-zinc-200 placeholder-zinc-700 focus:outline-none focus:border-cyan-500/40 focus:ring-2 focus:ring-cyan-500/5 transition-all duration-300"
                />
              </div>
            </div>

            {/* Password Field (Sign In and Sign Up only) */}
            {authMode !== 'forgot' && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label htmlFor="password" className="text-[10px] uppercase font-bold tracking-widest text-zinc-500">
                    Password
                  </label>
                  {authMode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode('forgot');
                        setError(null);
                        setMessage(null);
                      }}
                      className="text-[9px] text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                    >
                      Forgot?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3.5 w-4 h-4 text-zinc-600" />
                  <input
                    id="password"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    disabled={formLoading}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full h-11 pl-11 pr-4 bg-black/40 border border-white/5 rounded-xl text-xs text-zinc-200 placeholder-zinc-700 focus:outline-none focus:border-cyan-500/40 focus:ring-2 focus:ring-cyan-500/5 transition-all duration-300"
                  />
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={formLoading}
              className="w-full h-11 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-xl text-xs font-semibold hover:from-cyan-400 hover:to-cyan-500 transition-all shadow-[0_0_20px_rgba(6,182,212,0.15)] flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none mt-6"
            >
              {formLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-white" />
              ) : (
                <>
                  <span>
                    {authMode === 'signin' ? 'Sign In' :
                     authMode === 'signup' ? 'Create Account' :
                     'Send Reset Link'}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Mode Switcher */}
          <div className="mt-8 text-center border-t border-white/5 pt-6">
            {authMode === 'signin' ? (
              <p className="text-[11px] text-zinc-500">
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('signup');
                    setError(null);
                    setMessage(null);
                  }}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors ml-1"
                >
                  Sign Up
                </button>
              </p>
            ) : (
              <p className="text-[11px] text-zinc-500">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('signin');
                    setError(null);
                    setMessage(null);
                  }}
                  className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors ml-1"
                >
                  Sign In
                </button>
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
