'use client';

import { Button } from '@/components/Button/Button';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { TelegramAuthModal } from '@/components/TelegramAuthModal/TelegramAuthModal';
import { userService } from '@/core/api/services/user-service';
import { useUserStore } from '@/store/userStore';
import { AIModel, UserUpdate } from '@/types/user';
import { initData, useSignal } from '@telegram-apps/sdk-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export default function SettingsPage() {
  const initDataRaw = useSignal(initData.raw);
  const initDataState = useSignal(initData.state);
  const chatType = useSignal(initData.chatType);
  const chatInstance = useSignal(initData.chatInstance);
  const startParam = useSignal(initData.startParam);
  const user = useSignal(initData.user);

  // Ref to track initial data load
  const initialLoadRef = useRef(false);

  const [showQRModal, setShowQRModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // User data from store
  const { user: userData, fetchUser, isLoading, updateUser } = useUserStore();

  // Form state
  const [formData, setFormData] = useState<UserUpdate>({
    first_name: '',
    last_name: '',
    email: null,
    telegram_chats_load_limit: null,
    telegram_messages_load_limit: null,
    preferred_ai_model: null,
    preferred_message_context_size: null,
  });

  // Load user data - only once on initial mount
  useEffect(() => {
    if (initialLoadRef.current) return;
    
    const loadData = async () => {
      if (initDataRaw) {
        console.log('Fetching fresh user data from server on settings page (initial load)');
        await fetchUser(initDataRaw);
        initialLoadRef.current = true;
      }
    };
    
    loadData();
  }, [fetchUser, initDataRaw]);
  
  // Update form when user data changes
  useEffect(() => {
    if (userData) {
      setFormData({
        first_name: userData.first_name,
        last_name: userData.last_name || '',
        email: userData.email,
        telegram_chats_load_limit: userData.telegram_chats_load_limit,
        telegram_messages_load_limit: userData.telegram_messages_load_limit,
        preferred_ai_model: userData.preferred_ai_model,
        preferred_message_context_size: userData.preferred_message_context_size,
      });
    }
  }, [userData]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target as HTMLInputElement;
    
    // Handle different input types
    if (type === 'number') {
      setFormData({
        ...formData,
        [name]: value ? parseInt(value, 10) : null,
      });
    } else {
      setFormData({
        ...formData,
        [name]: value || null,
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    console.log('Submitting form with initDataRaw:', initDataRaw);
    
    try {
      const response = await userService.updateUser(formData, initDataRaw);
      if (response.success) {
        // Update the user store with all form data values
        updateUser({
          first_name: formData.first_name,
          last_name: formData.last_name || undefined,
          email: formData.email,
          telegram_chats_load_limit: formData.telegram_chats_load_limit,
          telegram_messages_load_limit: formData.telegram_messages_load_limit,
          preferred_ai_model: formData.preferred_ai_model,
          preferred_message_context_size: formData.preferred_message_context_size
        });
        
        setSuccessMessage('User settings updated successfully!');
        
        // Still fetch user data to ensure everything is in sync
        fetchUser(initDataRaw);
      } else {
        setErrorMessage(response.error || 'Failed to update user settings');
      }
    } catch (error) {
      setErrorMessage('An error occurred while updating user settings');
      console.error(error);
    } finally {
      setIsSaving(false);
      // Clear success message after 3 seconds
      if (successMessage) {
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    }
  };

  const router = useRouter();
  const handleBackToHome = () => router.replace('/');

  // Handle settings click navigation - since we're already on settings page, this is undefined
  const handleSettingsClick = undefined;

  // Loading state
  if (isLoading) {
    return (
      <Page back onBack={handleBackToHome}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }

  return (
    <Page back onBack={handleBackToHome}>
      <Header 
        title="Settings"
        onSettingsClick={handleSettingsClick}
      />
      <div className="container mx-auto p-4">
        <div className="grid grid-cols-1 gap-4">
          {/* Telegram Authentication Section */}
          <section className="bg-base-200 rounded-box p-4 shadow-sm">
            <h2 className="text-xl font-bold mb-4">Telegram Authentication</h2>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <p className="text-base-content text-opacity-70">
                {user ? (
                  <span>Connected as: {user.firstName} {user.lastName}</span>
                ) : (
                  <span>Not connected to Telegram</span>
                )}
              </p>
              <Button
                onClick={() => setShowQRModal(true)}
                className={user ? 'btn-outline btn-sm' : 'btn-primary btn-sm'}
              >
                {user ? 'Reconnect Telegram' : 'Connect Telegram'}
              </Button>
            </div>
          </section>

          {/* User Settings Form */}
          <section className="bg-base-200 rounded-box p-4 shadow-sm">
            <h2 className="text-xl font-bold mb-4">User Settings</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Success/Error Messages */}
              {successMessage && (
                <div className="alert alert-success shadow-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{successMessage}</span>
                </div>
              )}
              {errorMessage && (
                <div className="alert alert-error shadow-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{errorMessage}</span>
                </div>
              )}
              
              {/* Personal Information */}
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body p-4">
                  <h3 className="card-title text-lg mb-2">Personal Information</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text">First Name*</span>
                      </label>
                      <input
                        type="text"
                        name="first_name"
                        value={formData.first_name || ''}
                        onChange={handleInputChange}
                        className="input input-bordered w-full"
                        required
                      />
                    </div>
                    
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text">Last Name</span>
                      </label>
                      <input
                        type="text"
                        name="last_name"
                        value={formData.last_name || ''}
                        onChange={handleInputChange}
                        className="input input-bordered w-full"
                      />
                    </div>
                  </div>
                  
                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">Email</span>
                    </label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email || ''}
                      onChange={handleInputChange}
                      className="input input-bordered w-full"
                    />
                  </div>
                </div>
              </div>
              
              {/* Telegram Settings */}
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body p-4">
                  <h3 className="card-title text-lg mb-2">Telegram Settings</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text">Chats Load Limit</span>
                      </label>
                      <input
                        type="number"
                        name="telegram_chats_load_limit"
                        value={formData.telegram_chats_load_limit || ''}
                        onChange={handleInputChange}
                        className="input input-bordered w-full"
                        min="1"
                      />
                    </div>
                    
                    <div className="form-control">
                      <label className="label">
                        <span className="label-text">Messages Load Limit</span>
                      </label>
                      <input
                        type="number"
                        name="telegram_messages_load_limit"
                        value={formData.telegram_messages_load_limit || ''}
                        onChange={handleInputChange}
                        className="input input-bordered w-full"
                        min="1"
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              {/* AI Settings */}
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body p-4">
                  <h3 className="card-title text-lg mb-2">AI Settings</h3>
                  
                  <div className="form-control mb-4">
                    <label className="label">
                      <span className="label-text">Preferred AI Model</span>
                    </label>
                    <select
                      name="preferred_ai_model"
                      value={formData.preferred_ai_model || ''}
                      onChange={handleInputChange}
                      className="select select-bordered w-full"
                    >
                      <option value="">Select AI Model</option>
                      {Object.entries(AIModel).map(([key, value]) => (
                        <option key={key} value={value}>
                          {key.replace(/_/g, ' ')}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="form-control">
                    <label className="label">
                      <span className="label-text">Message Context Size</span>
                    </label>
                    <input
                      type="number"
                      name="preferred_message_context_size"
                      value={formData.preferred_message_context_size || ''}
                      onChange={handleInputChange}
                      className="input input-bordered w-full"
                      min="1"
                    />
                  </div>
                </div>
              </div>
              
              {/* App Information */}
              <div className="card bg-base-100 shadow-sm">
                <div className="card-body p-4">
                  <h3 className="card-title text-lg mb-2">App Information</h3>
                  
                  <table className="table table-zebra w-full">
                    <tbody>
                      <tr>
                        <td className="font-medium">Chat Type</td>
                        <td>{chatType || 'N/A'}</td>
                      </tr>
                      <tr>
                        <td className="font-medium">Chat Instance</td>
                        <td>{chatInstance || 'N/A'}</td>
                      </tr>
                      <tr>
                        <td className="font-medium">Start Param</td>
                        <td>{startParam || 'N/A'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              
              <div className="card-actions justify-end mt-6">
                <Button 
                  type="submit" 
                  disabled={isSaving} 
                  className="btn-primary"
                >
                  {isSaving ? (
                    <>
                      <span className="loading loading-spinner loading-xs mr-2"></span>
                      Saving...
                    </>
                  ) : (
                    'Save Settings'
                  )}
                </Button>
              </div>
            </form>
          </section>
        </div>

        {initDataRaw && (
          <TelegramAuthModal
            isOpen={showQRModal}
            onClose={() => setShowQRModal(false)}
            initDataRaw={initDataRaw}
          />
        )}
      </div>
    </Page>
  );
} 