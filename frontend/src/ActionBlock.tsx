import React from 'react';

interface Props {
  title: string;
  subtitle?: string;
  primaryLabel?: string;
  primaryOnClick?: () => void;
  secondaryLabel?: string;
  secondaryOnClick?: () => void;
  children?: React.ReactNode;
}

export default function ActionBlock({
  title,
  subtitle,
  primaryLabel,
  primaryOnClick,
  secondaryLabel,
  secondaryOnClick,
  children,
}: Props) {
  return (
    <div className="action-block">
      {title ? <h3 className="action-block-title">{title}</h3> : null}
      {subtitle ? <p className="action-block-sub">{subtitle}</p> : null}
      <div className="action-block-btns">
        {primaryLabel ? (
          <button className="action-block-primary" onClick={primaryOnClick} type="button">
            {primaryLabel}
          </button>
        ) : null}
        {secondaryLabel ? (
          <button className="action-block-secondary" onClick={secondaryOnClick} type="button">
            {secondaryLabel}
          </button>
        ) : null}
      </div>
      {children ? <div className="action-block-body">{children}</div> : null}
    </div>
  );
}
