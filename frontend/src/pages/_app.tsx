import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import ReturnToDashboard from '@/components/ReturnToDashboard';

function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const showDashboardLink = router.pathname === '/tax-profile';

  return (
    <>
      {showDashboardLink && <div className="fixed right-6 top-6 z-50"><ReturnToDashboard /></div>}
      <Component {...pageProps} />
    </>
  );
}

export default App;
