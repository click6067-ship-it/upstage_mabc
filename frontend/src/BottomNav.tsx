import { useCallback } from 'react';

export type BottomTab = 'home' | 'statement' | 'compare' | 'settings';

interface BottomNavProps {
  activeTab: BottomTab;
  onTabChange: (tab: BottomTab) => void;
}

const TAB_LABELS: Array<[BottomTab, string]> = [
  ['home', '홈'],
  ['statement', '명세서'],
  ['compare', '비교 결과'],
  ['settings', '설정'],
];

const ICON_BASE = '/assets/nav';

// 모든 탭은 항상 누를 수 있다. 내 입력이 없으면 '명세서'·'비교 결과'는 예시 명세서(가상)로 보여 준다.
export default function BottomNav({ activeTab, onTabChange }: BottomNavProps) {
  const press = useCallback((tab: BottomTab) => onTabChange(tab), [onTabChange]);

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
