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

const ICON_BASE = '/assets/nav';

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
              <img
                src={`${ICON_BASE}/${tab}-${active ? 'active' : 'inactive'}.svg`}
                alt=""
                width="20"
                height="20"
                loading="eager"
              />
            </span>
            <span className="bottom-nav-label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
