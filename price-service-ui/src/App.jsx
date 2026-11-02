import { useState } from "react";
import SearchPanel from "./components/SearchPanel.jsx";
import Tabs from "./components/Tabs.jsx";
import TopWinesPanel from "./components/TopWinesPanel.jsx";

const TABS = [
  { id: "search", label: "Search" },
  { id: "top", label: "Most price data" },
];

function App() {
  const [activeTab, setActiveTab] = useState("search");
  const [selectedWine, setSelectedWine] = useState(null);

  function openWineFromLeaderboard(wine) {
    setSelectedWine(wine);
    setActiveTab("search");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="app-eyebrow">Winefeed</p>
        <h1 className="app-title">Wine Price Search</h1>
      </header>

      <Tabs tabs={TABS} activeId={activeTab} onChange={setActiveTab} />

      <div
        role="tabpanel"
        id="tabpanel-search"
        aria-labelledby="tab-search"
        hidden={activeTab !== "search"}
        className="tab-panel"
      >
        {activeTab === "search" && (
          <SearchPanel selectedWine={selectedWine} onSelectWine={setSelectedWine} />
        )}
      </div>

      <div
        role="tabpanel"
        id="tabpanel-top"
        aria-labelledby="tab-top"
        hidden={activeTab !== "top"}
        className="tab-panel"
      >
        {activeTab === "top" && <TopWinesPanel onSelectWine={openWineFromLeaderboard} />}
      </div>
    </div>
  );
}

export default App;
