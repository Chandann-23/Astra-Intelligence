"use client";

import { useEffect, useState } from 'react';
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030303] flex items-center justify-center font-sans">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030303] flex flex-col items-center justify-center p-4 font-sans relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="w-full max-w-md z-10">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 to-zinc-500 tracking-tight">
            Astra Engine
          </h1>
          <p className="text-[10px] text-zinc-500 uppercase tracking-[0.3em] mt-2 font-bold">Secure Access Gateway</p>
        </div>

        <div className="bg-zinc-950/60 backdrop-blur-3xl border border-white/10 p-8 rounded-2xl shadow-2xl">
          <Auth
            supabaseClient={supabase}
            appearance={{
              theme: ThemeSupa,
              variables: {
                default: {
                  colors: {
                    brand: '#06b6d4', // cyan-500
                    brandAccent: '#0891b2', // cyan-600
                    brandButtonText: 'white',
                    defaultButtonBackground: '#18181b', // zinc-900
                    defaultButtonBackgroundHover: '#27272a', // zinc-800
                    inputBackground: '#09090b', // zinc-950
                    inputBorder: '#27272a', // zinc-800
                    inputBorderHover: '#3f3f46', // zinc-700
                    inputBorderFocus: '#06b6d4',
                  }
                }
              },
              className: {
                container: 'font-sans',
                label: 'text-zinc-400 font-medium',
                button: 'rounded-xl font-medium tracking-wide',
                input: 'rounded-xl border-white/5 bg-black/50 text-white placeholder-zinc-600',
              }
            }}
            theme="dark"
            providers={['google']} 
          />
        </div>
      </div>
    </div>
  );
}
