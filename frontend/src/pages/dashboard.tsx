import React, { ChangeEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';
import { documentsAPI, itrAPI } from '@/lib/api';

type UserDocument = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  created_at?: string;
};

const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [documentMessage, setDocumentMessage] = useState('');
  const [itrMessage, setItrMessage] = useState('');
  const [checkingItr, setCheckingItr] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      documentsAPI.list().then((response) => setDocuments(response.data)).catch(() => undefined);
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleDocumentSelection = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setDocumentMessage('Please choose a PDF document.');
      return;
    }

    try {
      const response = await documentsAPI.register('other', file.name, '2026-27');
      setDocuments((current) => [response.data, ...current]);
      setDocumentMessage('Document registered. Processing will be added in the next phase.');
    } catch {
      setDocumentMessage('Document registration is unavailable right now.');
    }
  };

  const handleFileItr = async () => {
    setCheckingItr(true);
    setItrMessage("Let's check your ITR eligibility.");
    try {
      const response = await itrAPI.eligibility();
      if (response.data.eligible) {
        setItrMessage('Based on your current Tax Profile, ITR-1 can be prepared.');
      } else {
        setItrMessage(`ITR-1 cannot currently be prepared because ${response.data.reasons.join(' ')}`);
      }
    } catch (error: any) {
      setItrMessage(error.response?.data?.detail || 'Complete and save your Tax Profile before preparing ITR-1.');
    } finally {
      setCheckingItr(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-primary">TaxWise</h1>
            </div>
            <div className="flex items-center">
              <span className="text-gray-700 mr-4">
                Welcome, {user?.firstName} {user?.lastName}
              </span>
              <button
                onClick={handleLogout}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-blue-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-lg shadow">
          <div className="px-4 py-5 sm:px-6">
            <h2 className="text-lg leading-6 font-medium text-gray-900">
              Welcome to TaxWise Dashboard
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">
              Manage your tax profile and file your ITR effortlessly.
            </p>
          </div>
          <div className="border-t border-gray-200 px-4 py-5 sm:p-6">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {/* Tax Profile Card */}
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">Tax Profile</p>
                    <p className="text-2xl font-bold text-primary mt-2">Get Started</p>
                  </div>
                  <div className="text-4xl">📋</div>
                </div>
                <Link href="/tax-profile">
                  <button className="mt-4 w-full bg-primary text-white py-2 rounded-md hover:bg-blue-700 transition-colors">
                    Create Profile
                  </button>
                </Link>
              </div>

              {/* File ITR Card */}
              <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">File ITR</p>
                    <p className="text-2xl font-bold text-green-600 mt-2">ITR-1 preparation</p>
                  </div>
                  <div className="text-4xl">📄</div>
                </div>
                <button onClick={handleFileItr} disabled={checkingItr} className="mt-4 w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700 disabled:opacity-50">
                  {checkingItr ? 'Checking...' : 'File ITR'}
                </button>
                {itrMessage && <p className="mt-3 text-sm text-gray-700" role="status">{itrMessage}</p>}
                {itrMessage.startsWith('Based on') && <Link href="/itr-preview"><button className="mt-2 w-full rounded-md border border-green-600 py-2 text-sm font-medium text-green-700">Continue</button></Link>}
              </div>

              {/* AI Copilot Card */}
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm font-medium">AI Copilot</p>
                    <p className="text-2xl font-bold text-purple-600 mt-2">Coming Soon</p>
                  </div>
                  <div className="text-4xl">🤖</div>
                </div>
                <button
                  disabled
                  className="mt-4 w-full bg-gray-300 text-gray-600 py-2 rounded-md cursor-not-allowed"
                >
                  Disabled
                </button>
              </div>
            </div>

            {/* Quick Start */}
            <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-lg font-medium text-blue-900 mb-2">Quick Start</h3>
              <ol className="list-decimal list-inside text-blue-800 space-y-1">
                <li>Create your tax profile with personal and financial information</li>
                <li>Upload supporting documents</li>
                <li>Review your information</li>
                <li>File your ITR</li>
              </ol>
            </div>

            {/* Optional document intake */}
            <section className="mt-8 border-t border-gray-200 pt-8" aria-labelledby="documents-heading">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 id="documents-heading" className="text-lg font-medium text-gray-900">My Documents</h3>
                  <p className="mt-1 text-sm text-gray-500">Have tax documents? Upload PDF (Optional)</p>
                  <p className="mt-1 text-xs text-gray-400">You can skip this and use TaxWise normally.</p>
                </div>
                <label className="inline-flex cursor-pointer items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  <span>Upload PDF</span>
                  <input type="file" accept="application/pdf" className="sr-only" onChange={handleDocumentSelection} />
                </label>
              </div>
              {documentMessage && <p className="mt-3 text-sm text-gray-600" role="status">{documentMessage}</p>}
              {documents.length > 0 && (
                <ul className="mt-5 divide-y divide-gray-200 border border-gray-200 rounded-md">
                  {documents.map((document) => (
                    <li key={document.id} className="flex items-center justify-between px-4 py-3 text-sm">
                      <span className="font-medium text-gray-800">{document.original_filename}</span>
                      <span className="text-gray-500">{document.status}</span>
                    </li>
                  ))}
                </ul>
              )}
              <button type="button" className="mt-4 text-sm font-medium text-gray-500 hover:text-gray-700">
                Skip for now
              </button>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
