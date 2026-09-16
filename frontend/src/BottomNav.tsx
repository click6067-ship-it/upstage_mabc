import { useCallback } from 'react';

export type BottomTab = 'home' | 'statement' | 'compare' | 'settings';

interface BottomNavProps {
  activeTab: BottomTab;
  hasResult: boolean;
  onTabChange: (tab: BottomTab) => void;
}

const TAB_LABELS: Array<[BottomTab, string]> = [
  ['home', '홈'],
  ['statement', '명세서'],
  ['compare', '비교 결과'],
  ['settings', '설정'],
];

export default function BottomNav({ activeTab, hasResult, onTabChange }: BottomNavProps) {
  const press = useCallback(
    (tab: BottomTab) => {
      if (tab === 'compare' && !hasResult) return;
      onTabChange(tab);
    },
    [hasResult, onTabChange],
  );

  return (
    <nav className="bottom-nav" aria-label="주요 화면 이동">
      {TAB_LABELS.map(([tab, label]) => {
        const active = tab === activeTab;
        return (
          <button
          key={tab}
          className={`bottom-nav-tab${active ? ' active' : ''}`}
          onClick={() => press(tab)}
          aria-current={active ? 'page' : undefined}
          type="button"
          disabled={tab === 'compare' && !hasResult}
          >
            <span className="bottom-nav-icon" data-tab={tab}>
              {tabIcons(tab)}
            </span>
            <span className="bottom-nav-label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function tabIcons(tab: BottomTab): React.ReactNode {
  if (tab === 'home') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12l2-2 4 4 2-2 2 2 2-2 2 2 2-2 4 4 2-2" />
        <path d="M3 20h18" />
      </svg>
    );
  }
  if (tab === 'statement') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    );
  }
  if (tab === 'compare') {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3a6 6 0 0 0-6 6v4" />
        <path d="M12 21a6 6 0 0 0 6-6V11" />
        <path d="M6 11h12" />
        <path d="M6 15h12" />
      </svg>
    );
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}
