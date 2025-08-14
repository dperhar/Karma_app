'use client';

import { Modal } from '@/components/Modal/Modal';
import { useTelegramQRLogin } from '@/hooks/useTelegramQRLogin';
import { useEffect } from 'react';
import { QRCodeDisplay } from './QRCodeDisplay';
import { TwoFactorForm } from './TwoFactorForm';


interface TelegramAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initDataRaw: string;
  onSuccess?: () => void;
}

// Helper function to update Telegram environment with authenticated user data
const updateTelegramEnvironment = (userData: { user_id: number; status: string }) => {
  try {
    console.log('🔄 Updating session with authenticated user:', userData.user_id);
    
    // Simply mark the session as authenticated since Telethon handles the actual connection
    if (typeof window !== 'undefined') {
      sessionStorage.setItem("env-authenticated", "1");
      sessionStorage.setItem("authenticated-user-id", userData.user_id.toString());
    }

    console.log('✅ Session updated with authenticated user:', userData.user_id);
    return true;
  } catch (error) {
    console.error('❌ Failed to update session:', error);
    return false;
  }
};

export const TelegramAuthModal: React.FC<TelegramAuthModalProps> = ({
  isOpen,
  onClose,
  initDataRaw,
  onSuccess,
}) => {
  const {
    qrData,
    qrCodeUrl,
    loginStatus,
    loading,
    error,
    generateQRCode,
    verify2FA,
    clearError
  } = useTelegramQRLogin(initDataRaw);

  useEffect(() => {
    if (isOpen) {
      generateQRCode();
    }
  }, [isOpen, generateQRCode]);

  // Handle successful authentication
  useEffect(() => {
    if (loginStatus?.user_id && loginStatus?.status === 'success') {
      console.log('🎉 Authentication successful, updating environment...');
      
      // Type-safe data for environment update
      const authData = {
        user_id: loginStatus.user_id,
        status: loginStatus.status,
      };
      
      // Update Telegram environment with authenticated user data
      const envUpdated = updateTelegramEnvironment(authData);
      
      if (envUpdated) {
        // Dev: rely on server cookie; only keep a light marker for header override
        try {
          const expiry = Date.now() + 30 * 24 * 60 * 60 * 1000;
          localStorage.setItem('karma_auth', JSON.stringify({
            userId: loginStatus.user_id,
            authenticatedAt: Date.now(),
            expiresAt: expiry,
          }));
        } catch {}
        const timer = setTimeout(() => {
          onSuccess?.();
          onClose();
        }, 500);
        return () => clearTimeout(timer);
      } else {
        console.error('Failed to update environment, keeping modal open');
      }
    }
  }, [loginStatus?.user_id, loginStatus?.status, onSuccess, onClose]);

  const handle2FASubmit = async (code: string): Promise<boolean> => {
    const success = await verify2FA(code);
    
    // Don't manually call onSuccess here - let the useEffect handle it
    // after environment is properly updated
    return success;
  };

  const handleQRCodeError = () => {
    clearError();
    generateQRCode();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Telegram Login"
    >
      <div className="modal-box max-h-[90vh] overflow-y-auto">
        {loading && !qrData ? (
          <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
            <span className="loading loading-spinner loading-lg"></span>
            <p className="text-base-content/70">Generating QR code...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
            <div className="text-error mb-4">{error}</div>
            <button className="btn btn-primary" onClick={generateQRCode}>Try Again</button>
          </div>
        ) : qrData ? (
          <div className="flex flex-col items-center space-y-6">
            <QRCodeDisplay
              qrCodeUrl={qrCodeUrl}
              onError={handleQRCodeError}
            />

            {loginStatus?.requires_2fa ? (
              <TwoFactorForm
                onSubmit={handle2FASubmit}
                loading={loading}
              />
            ) : loginStatus?.user_id && loginStatus?.status === 'success' ? (
              <div className="text-center space-y-2">
                <div className="text-success text-lg font-semibold">
                  Login Successful!
                </div>
                <p className="text-base-content/70">Updating environment...</p>
                <span className="loading loading-spinner loading-md"></span>
              </div>
            ) : (
              <div className="text-center space-y-2">
                <h3 className="text-lg font-semibold">Scan QR Code</h3>
                <p className="text-base-content/70">
                  Open Telegram on your phone and scan this QR code to log in
                </p>
                <div className="text-sm text-base-content/50 mt-2">
                  Status: {loginStatus?.status || 'Waiting for scan...'}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </Modal>
  );
}; 