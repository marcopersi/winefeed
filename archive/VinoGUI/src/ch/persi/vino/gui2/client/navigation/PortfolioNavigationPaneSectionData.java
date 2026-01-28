package ch.persi.vino.gui2.client.navigation;

import ch.persi.vino.gui2.client.portfolio.PortfolioView;

public class PortfolioNavigationPaneSectionData {

	private static NavigationPaneRecord[] records;

	  public static NavigationPaneRecord[] getRecords() {
		if (records == null) {
		  records = getNewRecords();
		}
		return records;
	  }

	  public static NavigationPaneRecord[] getNewRecords() {
		return new NavigationPaneRecord[]{
		  new NavigationPaneRecord("find", "Show Portfolios", new PortfolioView.Factory(), null),
		  new NavigationPaneRecord("add", "Add Transaction", new PortfolioView.Factory(), null),
		  new NavigationPaneRecord("find", "Show Transactions", new PortfolioView.Factory(), null)

		};
	  }
}
