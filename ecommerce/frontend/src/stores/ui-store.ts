import { create } from 'zustand';

export type UiState = {
  searchOpen: boolean;
  mobileNavOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  setMobileNavOpen: (open: boolean) => void;
};

export const initialUiState: Omit<UiState, 'setSearchOpen' | 'setMobileNavOpen'> = {
  searchOpen: false,
  mobileNavOpen: false,
};

export const useUiStore = create<UiState>((set) => ({
  ...initialUiState,
  setSearchOpen: (searchOpen: boolean) => set({ searchOpen }),
  setMobileNavOpen: (mobileNavOpen: boolean) => set({ mobileNavOpen }),
}));
