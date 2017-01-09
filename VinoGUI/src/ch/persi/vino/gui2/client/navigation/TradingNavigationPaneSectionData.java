package ch.persi.vino.gui2.client.navigation;

import ch.persi.vino.gui2.client.trading.TradingView;


public class TradingNavigationPaneSectionData {

	private static NavigationPaneRecord[] records;

	  public static NavigationPaneRecord[] getRecords() {
		if (records == null) {
		  records = getNewRecords();
		}
		return records;
	  }

	  public static NavigationPaneRecord[] getNewRecords() {
		return new NavigationPaneRecord[]{
		  new NavigationPaneRecord("buy", "Buy", new TradingView.Factory(), null),
		  new NavigationPaneRecord("sell", "Sell", new TradingView.Factory(), null)
		};
	  }
}
