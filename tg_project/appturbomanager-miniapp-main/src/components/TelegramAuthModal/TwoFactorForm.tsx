import { useState } from 'react';

interface TwoFactorFormProps {
  onSubmit: (code: string) => Promise<boolean>;
  loading: boolean;
}

export const TwoFactorForm: React.FC<TwoFactorFormProps> = ({ onSubmit, loading }) => {
  const [code, setCode] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      await onSubmit(code);
    }
  };

  return (
    <div className="w-full max-w-md space-y-4">
      <div className="text-center">
        <h3 className="text-lg font-semibold mb-2">Two-Factor Authentication</h3>
        <p className="text-base-content/70">Please enter the 2FA code sent to your Telegram account</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Enter 2FA code"
          className="input input-bordered w-full"
        />
        <button 
          type="submit"
          disabled={loading || !code.trim()}
          className="btn btn-primary w-full"
        >
          {loading ? <span className="loading loading-spinner"></span> : 'Verify Code'}
        </button>
      </form>
    </div>
  );
}; 