import { userService } from '@/core/api/services/user-service';
import { User } from '@/types/user';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

interface UserState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  fetchUser: (initDataRaw?: string) => Promise<void>;
  updateUser: (userData: Partial<User>) => void;
  reset: () => void;
}

// Check if running in browser environment to avoid localStorage issues
const isClient = typeof window !== 'undefined';

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      error: null,
      
      fetchUser: async (initDataRaw?: string) => {
        try {
          set({ isLoading: true, error: null });
          
          // Don't clear existing user data before fetching to prevent unnecessary renders
          // set({ user: null });
          
          const response = await userService.getCurrentUser(initDataRaw);
          
          if (response.success) {
            set({ user: response.data });
          } else {
            set({ error: response.message || 'Failed to fetch user data' });
          }
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to fetch user data' });
        } finally {
          set({ isLoading: false });
        }
      },
      
      updateUser: (userData: Partial<User>) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null
        }));
      },
      
      reset: () => {
        set({ user: null, isLoading: false, error: null });
      }
    }),
    {
      name: 'user-storage',
      storage: isClient ? createJSONStorage(() => localStorage) : createJSONStorage(() => ({
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {}
      })),
      partialize: (state) => ({ user: state.user }), // Only persist the user data
    }
  )
); 