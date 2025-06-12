import { authService } from '@/lib/api/auth-service';
import QRCode from 'qrcode';
import { useCallback, useEffect, useRef, useState } from 'react';

interface QRCodeData {
  token: string;
}

interface LoginStatus {
  requires_2fa: boolean;
  user_id: number | null;
  status: string | null;
}

export const useTelegramQRLogin = (initDataRaw: string) => {
  const [qrData, setQRData] = useState<QRCodeData | null>(null);
  const [qrCodeUrl, setQRCodeUrl] = useState<string>('');
  const [loginStatus, setLoginStatus] = useState<LoginStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isGeneratingRef = useRef<boolean>(false);

  const startPolling = useCallback((token: string, onExpired?: () => void) => {
    if (!initDataRaw) {
      setError('Telegram initialization data is not available');
      return;
    }

    // Clear any existing polling
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    console.log('Starting polling with token:', token, 'and initDataRaw:', initDataRaw);

    const interval = setInterval(async () => {
      try {
        if (!initDataRaw) {
          console.error('initDataRaw is missing during polling');
          clearInterval(interval);
          intervalRef.current = null;
          return;
        }

        const response = await authService.checkQRLogin(token, initDataRaw);
        console.log('Polling response:', response);
        
        if (response.success && response.data) {
          setLoginStatus(response.data);
          
          if (response.data.status === 'success' || response.data.requires_2fa) {
            console.log('Polling stopped due to:', response.data.status);
            clearInterval(interval);
            intervalRef.current = null;
          }
        } else {
          // Handle failed responses (token expired, session expired, etc.)
          console.log('Polling failed:', response.message);
          
          if (response.message && (
            response.message.includes('expired') || 
            response.message.includes('Session expired') ||
            response.message.includes('authorization token has expired')
          )) {
            console.log('Token expired, stopping polling and will regenerate QR code');
            clearInterval(interval);
            intervalRef.current = null;
            
            // Clear current state
            setQRData(null);
            setQRCodeUrl('');
            setLoginStatus(null);
            setError('QR code expired, generating new one...');
            
            // Call the expired callback if provided
            if (onExpired) {
              setTimeout(onExpired, 1000);
            }
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
        // On network errors, continue polling but limit retries
      }
    }, 5000);

    intervalRef.current = interval;
  }, [initDataRaw]);

  const generateQRCode = useCallback(async () => {
    if (!initDataRaw) {
      setError('Telegram initialization data is not available');
      return;
    }

    // Prevent multiple simultaneous generations
    if (isGeneratingRef.current) {
      console.log('QR code generation already in progress, skipping...');
      return;
    }

    try {
      isGeneratingRef.current = true;
      setLoading(true);
      setError(null);
      
      console.log('Generating QR code with initDataRaw:', initDataRaw);
      
      const response = await authService.generateQRCode(initDataRaw);
      console.log('QR code generation response:', response);
      
      if (response.success && response.data) {
        console.log('Response data:', response.data);
        console.log('Token from response:', response.data.token);
        setQRData(response.data);
        
        const loginUrl = `tg://login?token=${response.data.token}`;
        console.log('Generated login URL:', loginUrl);
        
        const qrCodeDataUrl = await QRCode.toDataURL(loginUrl, {
          width: 300,
          margin: 2,
          color: {
            dark: '#000000',
            light: '#ffffff'
          }
        });
        console.log('QR code data URL generated:', qrCodeDataUrl ? 'YES' : 'NO');
        console.log('QR code data URL length:', qrCodeDataUrl.length);
        setQRCodeUrl(qrCodeDataUrl);
        
        // Start polling with auto-regeneration on expiry (using a direct reference to avoid circular dependency)
        startPolling(response.data.token, () => {
          // Reset the generating flag and call generateQRCode after a delay
          isGeneratingRef.current = false;
          setTimeout(() => generateQRCode(), 500);
        });
      } else {
        console.error('Response not successful or no data:', response);
        setError(response.message || 'Failed to generate QR code');
      }
    } catch (err) {
      console.error('QR code generation error:', err);
      setError('Failed to generate QR code');
    } finally {
      setLoading(false);
      isGeneratingRef.current = false;
    }
  }, [initDataRaw, startPolling]);

  const verify2FA = useCallback(async (twoFactorCode: string) => {
    if (!qrData || !twoFactorCode || !initDataRaw) {
      setError('Required data is not available');
      return false;
    }

    try {
      setLoading(true);
      setError(null);
      console.log('Verifying 2FA with code:', twoFactorCode);
      
      const response = await authService.verify2FA(qrData.token, initDataRaw, twoFactorCode);
      console.log('2FA verification response:', response);
      
      if (response.success && response.data) {
        setLoginStatus(response.data);
        return true; // Always return true for successful response, regardless of status
      }
      return false;
    } catch (err) {
      console.error('2FA verification error:', err);
      setError('Failed to verify 2FA code');
      return false;
    } finally {
      setLoading(false);
    }
  }, [qrData, initDataRaw]);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      isGeneratingRef.current = false;
    };
  }, []);

  return {
    qrData,
    qrCodeUrl,
    loginStatus,
    loading,
    error,
    generateQRCode,
    verify2FA,
    clearError: () => setError(null)
  };
}; 