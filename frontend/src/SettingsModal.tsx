import { useCallback } from 'react';

interface SettingsModalProps {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
  const overlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  return (
    <div className="settings-overlay" onClick={overlayClick} role="dialog" aria-modal="true" aria-label="설정">
      <div className="settings-modal">
        <header className="settings-modal-header">
          <h2 className="settings-modal-title">설정</h2>
          <button className="settings-modal-close" onClick={onClose} type="button" aria-label="닫기">
            &#10005;
          </button>
        </header>
        <div className="settings-modal-body">
          <p className="settings-modal-text">
            같은 일자리·같은 급여기간의 정정 전/후 명세서만 비교할 수 있어요.
          </p>
          <p className="settings-modal-text">
            새로고침하면 이 화면에서 임시로 표시한 입력과 결과가 사라질 수 있어요.
          </p>
          <p className="settings-modal-text">
            로그인, 언어 전환, 저장 기능은 아직 제공되지 않아요.
          </p>
        </div>
        <div className="settings-modal-actions">
          <button className="btn btn-secondary" onClick={onClose} type="button">
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
