import React from 'react';
import { ActionKind } from './actions';
import './StartScreen.css';

interface Props {
  onChoice: (kind: ActionKind) => void;
  onPdfCompare?: () => void;
}

const choices = [
  {
    value: 'never-paid' as const,
    title: '월급 못 받음',
    desc: '받기로 한 월급이 들어오지 않았어요.',
  },
  {
    value: 'changed' as const,
    title: '적거나 달라짐',
    desc: '금액이 바뀌어서 확인하고 싶은 경우',
  },
  {
    value: 'understand' as const,
    title: '명세서 이해',
    desc: '항목이 여러 개일 때 어떤 게 대응되는지 보는 경우',
  },
  {
    value: 'empty' as const,
    title: '직접 입력',
    desc: '버튼 대신 직접 항목을 입력하고 싶은 경우',
  },
];

export default function StartScreen({ onChoice, onPdfCompare }: Props) {
  const [selected, setSelected] = React.useState<ActionKind | null>(null);

  const handleChoice = (kind: ActionKind) => {
    setSelected(kind);
    onChoice(kind);
  };

  const handleKeyDown = (e: React.KeyboardEvent, kind: ActionKind) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleChoice(kind);
    }
  };

  return (
    <main className="start-page">
      <section className="start-card">
        <div className="start-brand">
          <img
            className="start-logo"
            src="/paychecker-logo.png"
            alt="Paychecker 로고"
          />
          <span className="start-brand-name">Paychecker</span>
        </div>

        <h2 className="start-hero-title">월급명세서, 어디가 달라졌나요?</h2>
        <p className="start-hero-desc">
          한국어 명세서가 낯선 외국인 노동자를 위해, 바뀐 금액과 회사에 물어볼 질문을 정리해 드려요.
        </p>

        <div className="start-pdf-entry">
          {onPdfCompare ? (
            <button
              className="start-pdf-btn"
              type="button"
              onClick={onPdfCompare}
            >
              명세서 PDF 비교
            </button>
          ) : null}
        </div>
        <p className="start-sample-hint">예시 명세서로도 시작할 수 있어요.</p>

        <ul className="start-actions">
          {choices.map(c => (
            <li key={c.value} className="start-choice-item">
              <div
                className={`start-choice-card${selected === c.value ? ' selected' : ''}`}
                onClick={() => handleChoice(c.value)}
                onKeyDown={(e) => handleKeyDown(e, c.value)}
                role="button"
                tabIndex={0}
                aria-pressed={selected === c.value}
              >
                <p className="start-choice-title">{c.title}</p>
                <p className="start-choice-desc">{c.desc}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
