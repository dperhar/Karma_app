'use client';

import { useEffect, useState } from 'react';
import { isTMA, initData, miniApp } from '@telegram-apps/sdk-react';
import { isEnvironmentMocked } from '@/utils/mockTelegramEnv';

interface EnvironmentStatus {
  isDev: boolean;
  isEnvironmentMocked: boolean;
  isTMADetected: boolean;
  hasWindow: boolean;
  hasTelegram: boolean;
  hasWebApp: boolean;
  sessionMocked: string | null;
  initDataPresent: boolean;
  errors: string[];
}

export default function TestInitPage() {
  const [envStatus, setEnvStatus] = useState<EnvironmentStatus | null>(null);
  
  useEffect(() => {
    // Test environment state
    const testEnvironment = () => {
      const errors: string[] = [];
      
      try {
        const status: EnvironmentStatus = {
          isDev: process.env.NODE_ENV === 'development',
          isEnvironmentMocked: isEnvironmentMocked(),
          isTMADetected: false,
          hasWindow: typeof window !== 'undefined',
          hasTelegram: false,
          hasWebApp: false,
          sessionMocked: null,
          initDataPresent: false,
          errors: []
        };

        // Check Telegram environment
        try {
          status.isTMADetected = isTMA('simple');
        } catch (e) {
          errors.push(`isTMA check failed: ${e}`);
        }

        if (typeof window !== 'undefined') {
          status.hasTelegram = !!window.Telegram;
          status.hasWebApp = !!(window.Telegram?.WebApp);
          status.sessionMocked = window.sessionStorage?.getItem("env-mocked");
        }

        // Check init data
        try {
          const data = initData.raw();
          status.initDataPresent = !!data;
        } catch (e) {
          errors.push(`initData check failed: ${e}`);
        }

        status.errors = errors;
        setEnvStatus(status);
      } catch (e) {
        setEnvStatus({
          isDev: false,
          isEnvironmentMocked: false,
          isTMADetected: false,
          hasWindow: false,
          hasTelegram: false,
          hasWebApp: false,
          sessionMocked: null,
          initDataPresent: false,
          errors: [`Global error: ${e}`]
        });
      }
    };

    // Run test immediately and after a short delay
    testEnvironment();
    const timeout = setTimeout(testEnvironment, 1000);
    
    return () => clearTimeout(timeout);
  }, []);

  if (!envStatus) {
    return (
      <div className="container mx-auto p-8">
        <h1 className="text-2xl font-bold mb-4">Environment Test</h1>
        <p>Loading test results...</p>
      </div>
    );
  }

  const getStatusColor = (condition: boolean) => 
    condition ? 'text-green-500' : 'text-red-500';

  const getStatusIcon = (condition: boolean) => 
    condition ? '✅' : '❌';

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-2xl font-bold mb-6">Telegram Environment Test</h1>
      
      <div className="grid gap-4 mb-6">
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Environment Status</h2>
            
            <div className="space-y-2">
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.isDev)}`}>
                {getStatusIcon(envStatus.isDev)}
                <span>Development Mode: {envStatus.isDev ? 'Yes' : 'No'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.hasWindow)}`}>
                {getStatusIcon(envStatus.hasWindow)}
                <span>Window Object: {envStatus.hasWindow ? 'Available' : 'Not Available'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.hasTelegram)}`}>
                {getStatusIcon(envStatus.hasTelegram)}
                <span>Telegram Object: {envStatus.hasTelegram ? 'Available' : 'Not Available'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.hasWebApp)}`}>
                {getStatusIcon(envStatus.hasWebApp)}
                <span>Telegram WebApp: {envStatus.hasWebApp ? 'Available' : 'Not Available'}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Mock Environment</h2>
            
            <div className="space-y-2">
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.isEnvironmentMocked)}`}>
                {getStatusIcon(envStatus.isEnvironmentMocked)}
                <span>Environment Mocked: {envStatus.isEnvironmentMocked ? 'Yes' : 'No'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(!!envStatus.sessionMocked)}`}>
                {getStatusIcon(!!envStatus.sessionMocked)}
                <span>Session Storage: {envStatus.sessionMocked || 'Not Set'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.isTMADetected)}`}>
                {getStatusIcon(envStatus.isTMADetected)}
                <span>TMA Detected: {envStatus.isTMADetected ? 'Yes' : 'No'}</span>
              </div>
              
              <div className={`flex items-center gap-2 ${getStatusColor(envStatus.initDataPresent)}`}>
                {getStatusIcon(envStatus.initDataPresent)}
                <span>Init Data: {envStatus.initDataPresent ? 'Available' : 'Not Available'}</span>
              </div>
            </div>
          </div>
        </div>

        {envStatus.errors.length > 0 && (
          <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
              <h2 className="card-title text-red-500">Errors</h2>
              <ul className="list-disc list-inside space-y-1">
                {envStatus.errors.map((error, index) => (
                  <li key={index} className="text-red-400">{error}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      <div className="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <div>
          <h3 className="font-bold">Expected Results in Development:</h3>
          <p>✅ Development Mode should be Yes</p>
          <p>✅ Environment Mocked should be Yes</p>
          <p>✅ Telegram Object should be Available</p>
          <p>✅ Session Storage should be "1"</p>
          <p>✅ Init Data should be Available</p>
        </div>
      </div>
    </div>
  );
} 