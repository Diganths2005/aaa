import '@/styles/globals.css';
import { useEffect, useState } from 'react';
import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import { useAuthStore } from '@/store/auth';

function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const hydrate = useAuthStore((state) => state.hydrate);
  const [authReady, setAuthReady] = useState(false);
  const showDashboardLink = router.pathname === '/tax-profile';
  const isPublicRoute = ['/', '/login', '/signup', '/404'].includes(router.pathname);

  useEffect(() => {
    hydrate();
    setAuthReady(true);
  }, [hydrate]);

  if (!isPublicRoute && !authReady) return null;

  return (
    <>
      {showDashboardLink && <div className="fixed right-6 top-6 z-50"><ReturnToDashboard /></div>}
      <Component {...pageProps} />
    </>
  );
}

export default App;
