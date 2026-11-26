import { create } from 'zustand';

export type AnnounceState = {
  message: string;
  nonce: number;
  announce: (message: string) => void;
};

export const initialAnnounceState: Omit<AnnounceState, 'announce'> = {
  message: '',
  nonce: 0,
};

export const useAnnounceStore = create<AnnounceState>((set) => ({
  ...initialAnnounceState,
  announce: (message: string) =>
    set((state) => ({
      message,
      nonce: state.nonce + 1,
    })),
}));

export const announce = (m: string) => useAnnounceStore.getState().announce(m);
