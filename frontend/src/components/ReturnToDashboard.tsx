import React from 'react';
import Link from 'next/link';

const ReturnToDashboard: React.FC = () => (
  <Link href="/dashboard" className="inline-flex items-center justify-center rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold text-[#334155] hover:bg-[#F1F5F9]">
    Return to dashboard
  </Link>
);

export default ReturnToDashboard;