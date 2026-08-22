import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';

const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.push('/login');
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
                    <p className="text-2xl font-bold text-green-600 mt-2">Coming Soon</p>
                  </div>
                  <div className="text-4xl">📄</div>
                </div>
                <button
                  disabled
                  className="mt-4 w-full bg-gray-300 text-gray-600 py-2 rounded-md cursor-not-allowed"
                >
                  Disabled
                </button>
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
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
