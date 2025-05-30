import { useEffect } from 'react';

interface QRCodeDisplayProps {
  qrCodeUrl: string;
  onError: () => void;
}

export const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({ qrCodeUrl, onError }) => {
  useEffect(() => {
    console.log('QRCodeDisplay received qrCodeUrl:', qrCodeUrl ? 'YES' : 'NO');
    console.log('QR code URL length:', qrCodeUrl?.length || 0);
    if (qrCodeUrl && qrCodeUrl.startsWith('data:image')) {
      console.log('QR code URL appears to be valid base64 image');
    } else {
      console.log('QR code URL is not a valid base64 image:', qrCodeUrl);
    }
  }, [qrCodeUrl]);

  return (
    <div className="bg-base-100 p-4 rounded-box shadow-sm w-fit">
      {qrCodeUrl ? (
        <div className="relative w-[300px] h-[300px]">
          <img
            src={qrCodeUrl}
            alt="Telegram QR Code"
            className="w-full h-full rounded-box object-contain"
            onError={(e) => {
              console.error('Image load error:', e);
              onError();
            }}
            onLoad={() => {
              console.log('Image loaded successfully');
            }}
          />
        </div>
      ) : (
        <div className="w-[300px] h-[300px] flex items-center justify-center bg-base-200 rounded-box">
          <span className="loading loading-spinner loading-lg"></span>
        </div>
      )}
    </div>
  );
}; 