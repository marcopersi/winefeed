import { useEffect, useRef, useState } from "react";

export default function Tabs({ tabs, activeId, onChange }) {
  const listRef = useRef(null);
  const buttonRefs = useRef({});
  const [indicator, setIndicator] = useState(null);

  useEffect(() => {
    const button = buttonRefs.current[activeId];
    const list = listRef.current;
    if (!button || !list) {
      return;
    }
    const listRect = list.getBoundingClientRect();
    const buttonRect = button.getBoundingClientRect();
    setIndicator({
      left: buttonRect.left - listRect.left,
      width: buttonRect.width,
    });
  }, [activeId, tabs]);

  return (
    <div className="tabs" role="tablist" ref={listRef}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          ref={(el) => {
            buttonRefs.current[tab.id] = el;
          }}
          type="button"
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={activeId === tab.id}
          aria-controls={`tabpanel-${tab.id}`}
          className="tab-button"
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
      {indicator && (
        <span
          className="tab-indicator"
          style={{ left: indicator.left, width: indicator.width }}
        />
      )}
    </div>
  );
}
