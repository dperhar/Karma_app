import React, { useState, useEffect } from 'react';
import { authService } from '@/core/api/services/auth-service';
import QRCode from 'qrcode';

interface TelegramAuthProps {
  onAuthSuccess?: (userId: number) => void;
  onAuthError?: (error: string) => void;
}

export const TelegramAuth: React.FC<TelegramAuthProps> = ({
  onAuthSuccess,
  onAuthError,
}) => {
  const [step, setStep] = useState<'loading' | 'qr' | '2fa' | 'success' | 'error'>('loading');
  const [token, setToken] = useState<string>('');
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [polling, setPolling] = useState<boolean>(false);

  // Generate QR code on component mount
  useEffect(() => {
    generateQRCode();
  }, []);

  const generateQRCode = async () => {
    try {
      setStep('loading');
      setError('');
      
      const response = await authService.generateQRCode();
      
      if (response.success && response.data) {
        setToken(response.data.token);
        
        // Generate QR code using qrcode library
        const loginUrl = `tg://login?token=${response.data.token}`;
        const qrDataUrl = await QRCode.toDataURL(loginUrl, {
          width: 300,
          margin: 2,
          color: {
            dark: '#000000',
            light: '#ffffff'
          }
        });
        
        setQrCodeUrl(qrDataUrl);
        setStep('qr');
        startPolling(response.data.token);
      } else {
        throw new Error(response.message || 'Failed to generate QR code');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      setStep('error');
      onAuthError?.(errorMessage);
    }
  };

  const startPolling = (authToken: string) => {
    if (polling) return;
    
    setPolling(true);
    
    const pollInterval = setInterval(async () => {
      try {
        // For development mode, we don't have initDataRaw from Telegram
        // so we'll use empty string - the backend should handle this case
        const response = await authService.checkQRLogin(authToken, '');
        
        if (response.success && response.data) {
          const { status, requires_2fa, user_id } = response.data;
          
          if (status === 'success' && user_id) {
            clearInterval(pollInterval);
            setPolling(false);
            setStep('success');
            onAuthSuccess?.(user_id);
          } else if (requires_2fa) {
            clearInterval(pollInterval);
            setPolling(false);
            setStep('2fa');
          }
          // Continue polling if status is pending or null
        }
      } catch (err) {
        console.error('Polling error:', err);
        // Don't stop polling on error, just log it
      }
    }, 2000); // Poll every 2 seconds

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      setPolling(false);
      if (step === 'qr') {
        setError('QR code expired. Please try again.');
        setStep('error');
      }
    }, 5 * 60 * 1000);
  };

  const handle2FA = async () => {
    if (!password.trim()) {
      setError('Please enter your 2FA password');
      return;
    }

    try {
      setError('');
      
      const response = await authService.verify2FA(token, '', password);
      
      if (response.success && response.data) {
        const { status, user_id } = response.data;
        
        if (status === 'success' && user_id) {
          setStep('success');
          onAuthSuccess?.(user_id);
        } else {
          throw new Error('2FA verification failed');
        }
      } else {
        throw new Error(response.message || '2FA verification failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '2FA verification failed';
      setError(errorMessage);
      onAuthError?.(errorMessage);
    }
  };

  const handleRetry = () => {
    setPassword('');
    setError('');
    generateQRCode();
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '24px',
      maxWidth: '400px',
      margin: '0 auto',
      textAlign: 'center',
    }}>
      {step === 'loading' && (
        <div>
          <div style={{ marginBottom: '16px' }}>🔄</div>
          <h3>Generating QR Code...</h3>
          <p>Please wait while we prepare your authentication.</p>
        </div>
      )}

      {step === 'qr' && (
        <div>
          <div style={{ marginBottom: '16px' }}>📱</div>
          <h3>Scan QR Code with Telegram</h3>
          {qrCodeUrl && (
            <div style={{ marginBottom: '16px' }}>
              <img 
                src={qrCodeUrl} 
                alt="Telegram QR Code" 
                style={{ 
                  width: '300px', 
                  height: '300px',
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  backgroundColor: '#fff',
                  padding: '16px'
                }} 
              />
            </div>
          )}
          <p style={{ fontSize: '14px', color: '#666' }}>
            1. Open Telegram on your phone<br />
            2. Go to Settings → Privacy and Security → Active Sessions<br />
            3. Tap "Link Desktop Device"<br />
            4. Point your camera at the QR code above
          </p>
          {polling && (
            <div style={{ marginTop: '16px', color: '#007aff' }}>
              ⏳ Waiting for authentication...
            </div>
          )}
        </div>
      )}

      {step === '2fa' && (
        <div>
          <div style={{ marginBottom: '16px' }}>🔐</div>
          <h3>Two-Factor Authentication</h3>
          <p style={{ marginBottom: '16px' }}>Enter your 2FA password:</p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="2FA Password"
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              marginBottom: '16px',
              fontSize: '16px',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handle2FA();
              }
            }}
          />
          <button
            onClick={handle2FA}
            style={{
              background: '#007aff',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer',
              width: '100%',
            }}
          >
            Verify
          </button>
          {error && (
            <p style={{ color: '#ff3b30', marginTop: '16px', fontSize: '14px' }}>
              {error}
            </p>
          )}
        </div>
      )}

      {step === 'success' && (
        <div>
          <div style={{ marginBottom: '16px', fontSize: '48px' }}>✅</div>
          <h3>Authentication Successful!</h3>
          <p>You are now logged in to your Telegram account.</p>
        </div>
      )}

      {step === 'error' && (
        <div>
          <div style={{ marginBottom: '16px', fontSize: '48px' }}>❌</div>
          <h3>Authentication Failed</h3>
          <p style={{ color: '#ff3b30', marginBottom: '16px' }}>{error}</p>
          <button
            onClick={handleRetry}
            style={{
              background: '#007aff',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer',
            }}
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}; 