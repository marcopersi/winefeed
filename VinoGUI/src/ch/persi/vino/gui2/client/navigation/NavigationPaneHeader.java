package ch.persi.vino.gui2.client.navigation;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.Overflow;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;

public class NavigationPaneHeader extends HLayout {

	private static final String WEST_WIDTH = "11%";
	private static final String NAVIGATION_PANE_HEADER_HEIGHT = "27px";
	private static final String NAVIGATION_PANE_HEADER_LABEL_DISPLAY_NAME = "Navigation";
	private static final String CONTENT_AREA_HEADER_LABEL_DISPLAY_NAME = "Content";

	private Label navigationPaneHeaderLabel;
	private Label contentAreaHeaderLabel;

	public NavigationPaneHeader() {
		super();

		GWT.log("initialization of NavigationPaneHeader runs..", null);

		// initialise the Navigation Pane Header layout container
		setStyleName("vino-NavigationPane-Header");
		setHeight(NAVIGATION_PANE_HEADER_HEIGHT);

		navigationPaneHeaderLabel = new Label();
		navigationPaneHeaderLabel.setStyleName("vino-NavigationPane-Header-Label");
		navigationPaneHeaderLabel.setWidth(WEST_WIDTH);
		navigationPaneHeaderLabel.setContents(NAVIGATION_PANE_HEADER_LABEL_DISPLAY_NAME);
		navigationPaneHeaderLabel.setAlign(Alignment.LEFT);
		navigationPaneHeaderLabel.setOverflow(Overflow.HIDDEN);

		// initialise the Context Area Header Label
		contentAreaHeaderLabel = new Label();
		contentAreaHeaderLabel.setStyleName("vino-ContentArea-Header-Label");
		contentAreaHeaderLabel.setContents(CONTENT_AREA_HEADER_LABEL_DISPLAY_NAME);
		contentAreaHeaderLabel.setAlign(Alignment.LEFT);
		contentAreaHeaderLabel.setOverflow(Overflow.HIDDEN);

		// add the Labels to the Navigation Pane Header layout container
		this.addMember(navigationPaneHeaderLabel);
		this.addMember(contentAreaHeaderLabel);
	}

	public Label getNavigationPaneHeaderLabel() {
		return navigationPaneHeaderLabel;
	}

	public Label getContentAreaHeaderLabel() {
		return contentAreaHeaderLabel;
	}

	public void setNavigationPaneHeaderLabelContents(String contents) {
		navigationPaneHeaderLabel.setContents(contents);
	}

	public String getNavigationPaneHeaderLabelContents() {
		return navigationPaneHeaderLabel.getContents();
	}

	public void setContentAreaHeaderLabelContents(String contents) {
		contentAreaHeaderLabel.setContents(contents);
	}

	public String getContentAreaHeaderLabelContents() {
		return contentAreaHeaderLabel.getContents();
	}
}
