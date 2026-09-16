import React from 'react';
import { ActionKind } from './actions';

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

  return (
    <main className="start-page">
      <section className="start-card">
        <div className="start-brand">
          <h1 className="start-title">Paychecker</h1>
          <p className="start-sub">
            내 월급, 어디가 달라졌을까요?
          </p>
          <p className="start-desc">
            한국어 명세서가 낯선 이주노동자를 위한 급여 확인
          </p>
        </div>

        <div className="start-pdf-entry">
          {onPdfCompare ? (
            <button className="start-pdf-entry-btn" type="button" onClick={onPdfCompare}>
              <span className="start-pdf-entry-title">명세서 PDF 비교</span>
              <span className="start-pdf-entry-desc">
                정정 전후 명세서를 PDF로 올려서 비교할 수 있어요.
              </span>
            </button>
          ) : null}
        </div>

        <ul className="start-actions">
          {choices.map(c => (
            <li key={c.value}>
              <div
                className={`start-choice-card${selected === c.value ? ' selected' : ''}`}
                onClick={() => onChoice(c.value)}
                role="button"
                tabIndex={0}
              >
                <p className="start-choice-title">{c.title}</p>
                <p className="start-choice-desc">{c.desc}</p>
              </div>
            </li>
          ))}
        </ul>

        <p className="start-note">
          입력한 내용은 이 화면에서만 잠깐 기억해요. 새로고침하면 지워질 수 있어요.
        </p>
      </section>
    </main>
  );
}
