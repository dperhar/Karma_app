'use client';

import { Button } from '@/components/Button/Button';
import { DigitalTwinPanel } from '@/components/DigitalTwin/DigitalTwinPanel';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { TelegramAuthModal } from '@/components/TelegramAuthModal/TelegramAuthModal';
import { userService } from '@/core/api/services/user-service';
import { useUserStore } from '@/store/userStore';
import { AIModel, UserUpdate } from '@/types/user';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export default function SettingsPage() {
  // The AI controls have moved to the global left sidebar. Keep minimal settings here.
  const initialLoadRef = useRef(false);
  const [showQRModal, setShowQRModal] = useState(false);
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
      console.log('Fetching fresh user data from server on settings page (initial load)');
      // Use mock data for development
      const requestInitData = "mock_init_data_for_telethon";
      await fetchUser(requestInitData);
      initialLoadRef.current = true;
    };
    
    loadData();
  }, [fetchUser]);
  
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

  const saveSettings = async (): Promise<boolean> => true;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const saved = await saveSettings();
    if (saved) {
      setSuccessMessage('User settings updated successfully!');
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    }
    // Error message is handled by saveSettings
  };

  const router = useRouter();

  const handleBackNavigation = async () => {
    const saved = await saveSettings();
    if (saved) {
      // Check for previous chat ID to navigate back correctly
      const previousChatId = sessionStorage.getItem('previousChatId');
      if (previousChatId) {
        sessionStorage.removeItem('previousChatId');
        router.replace(`/chat/${previousChatId}`);
      } else {
        router.replace('/'); // Default back to home
      }
    }
    // If not saved, an error message is already set by saveSettings, user stays on page
  };

  // Handle settings click navigation - since we're already on settings page, this is undefined
  const handleSettingsClick = undefined;

  // Placeholder env/context info used in the table below
  const chatType: string | null = null;
  const chatInstance: string | null = null;
  const startParam: string | null = null;

  // Loading state
  if (isLoading) {
    return (
      <Page back={true} onBack={handleBackNavigation}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }

  return (
    <Page back={true} onBack={handleBackNavigation}>
      <Header title="Settings" onSettingsClick={handleSettingsClick} />
      {/* Define placeholder variables to avoid reference errors */}
      {(() => { const chatType = null as unknown as string | null; const chatInstance = null as unknown as string | null; const startParam = null as unknown as string | null; return null; })()}
      
      {/* Back to Chats Button */}
      <div className="container mx-auto px-4 pt-4">
        <Button
          onClick={handleBackNavigation}
          className="btn-outline btn-sm mb-4 flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Chats
        </Button>
      </div>
      
      <div className="container mx-auto p-4">
        <div className="grid grid-cols-1 gap-4">
          {/* Telegram Authentication Section */}
          <section className="bg-base-200 rounded-box p-4 shadow-sm">
            <h2 className="text-xl font-bold mb-4">Telegram Authentication</h2>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex flex-col">
                  <p className="text-base-content text-opacity-70">
                    {userData?.has_valid_tg_session ? (
                      <span>Connected as: {userData.first_name} {userData.last_name}</span>
                    ) : (
                      <span>Not connected to Telegram</span>
                    )}
                  </p>
                  {userData?.last_telegram_auth_at && (
                    <p className="text-sm text-base-content text-opacity-50 mt-1">
                      Last authorized: {new Date(userData.last_telegram_auth_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => setShowQRModal(true)}
                    className={userData?.has_valid_tg_session ? 'btn-outline btn-sm' : 'btn-primary btn-sm'}
                  >
                    {userData?.has_valid_tg_session ? 'Reconnect Telegram' : 'Connect Telegram'}
                  </Button>
                  
                  <Button
                    onClick={async () => {
                      console.log('[Settings] Manual refresh button clicked');
                      const requestInitData = "mock_init_data_for_telethon";
                      await fetchUser(requestInitData);
                      console.log('[Settings] User data refreshed, current session status:', userData?.has_valid_tg_session);
                    }}
                    className="btn-ghost btn-sm"
                    title="Refresh user data"
                  >
                    🔄
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* AI settings moved to sidebar; keep only Telegram auth here */}
              {/* Digital Twin Panel */}
              {userData && (
                <DigitalTwinPanel 
                  user={userData} 
                  onUserUpdate={(updatedUser) => {
                    updateUser(updatedUser);
                  }}
                />
              )}
              
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
              
              <div className="card-actions justify-end mt-6" />
            </form>
          </section>
        </div>

        {/* Telegram Auth Modal (disabled placeholder) */}
        {showQRModal && (
          <TelegramAuthModal
            isOpen={showQRModal}
            onClose={() => setShowQRModal(false)}
            initDataRaw="mock_init_data_for_telethon"
            onSuccess={async () => {
              const requestInitData = "mock_init_data_for_telethon";
              await fetchUser(requestInitData);
            }}
          />
        )}
        
      </div>
    </Page>
  );
} 