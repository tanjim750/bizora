import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThemeToggle from '@/components/layout/ThemeToggle';

let mockTheme = 'light';
const mockSetTheme = vi.fn();

vi.mock('next-themes', () => ({
  useTheme: () => ({
    resolvedTheme: mockTheme,
    setTheme: mockSetTheme,
  }),
}));

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTheme = 'light';
  });

  it('renders switch to dark theme when light and calls setTheme', async () => {
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const button = await screen.findByRole('button', { name: 'Switch to dark theme' });
    expect(button).toBeInTheDocument();

    await user.click(button);
    expect(mockSetTheme).toHaveBeenCalledWith('dark');
  });

  it('renders switch to light theme when dark and calls setTheme', async () => {
    mockTheme = 'dark';
    const user = userEvent.setup();
    render(<ThemeToggle />);

    const button = await screen.findByRole('button', { name: 'Switch to light theme' });
    expect(button).toBeInTheDocument();

    await user.click(button);
    expect(mockSetTheme).toHaveBeenCalledWith('light');
  });
});
