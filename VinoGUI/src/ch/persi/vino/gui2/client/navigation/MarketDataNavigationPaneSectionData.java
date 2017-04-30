package ch.persi.vino.gui2.client.navigation;

import ch.persi.vino.gui2.client.marketdata.gui.MarketDataView;
public class MarketDataNavigationPaneSectionData {
	private static NavigationPaneRecord[] records;

	public static NavigationPaneRecord[] getRecords() {
		if (records == null) {
			records = getNewRecords();
		}
		return records;
	}

	public static NavigationPaneRecord[] getNewRecords() {
		return new NavigationPaneRecord[] { 
				new NavigationPaneRecord("chart_line", "MarketData", new MarketDataView.Factory(), null) 
		};
	}
}
