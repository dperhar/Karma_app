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
}

export const TelegramAuthModal: React.FC<TelegramAuthModalProps> = ({
  isOpen,
  onClose,
  initDataRaw,
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

  const handle2FASubmit = async (code: string): Promise<boolean> => {
    const success = await verify2FA(code);
    if (success) {
      onClose();
      return true;
    }
    return false;
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
            ) : loginStatus?.user_id ? (
              <div className="text-center space-y-2">
                <div className="text-success text-lg font-semibold">
                  Login Successful!
                </div>
                <p className="text-base-content/70">You can now close this window</p>
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