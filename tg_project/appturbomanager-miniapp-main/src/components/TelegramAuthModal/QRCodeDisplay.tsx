import Image from 'next/image';

interface QRCodeDisplayProps {
  qrCodeUrl: string;
  onError: () => void;
}

export const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({ qrCodeUrl, onError }) => {
  return (
    <div className="bg-base-100 p-4 rounded-box shadow-sm w-fit">
      {qrCodeUrl ? (
        <div className="relative w-[300px] h-[300px]">
          <Image
            src={qrCodeUrl}
            alt="Telegram QR Code"
            fill
            priority
            className="rounded-box object-contain"
            onError={onError}
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