package ch.persi.vino.gui2.client.widget;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.Overflow;
import com.smartgwt.client.types.VerticalAlignment;
import com.smartgwt.client.widgets.ImgButton;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.layout.LayoutSpacer;

public class StatusBar extends HLayout {
	private static final String STATUSBAR_HEIGHT = "23px";
	private static final String SELECTED_LABEL_DISPLAY_NAME = "1 of 50 selected";
	private static final String PAGE_NUMBER_LABEL_DISPLAY_NAME = "Page 1";

	public StatusBar() {
		super();

		GWT.log("initialization of StatusBar runs...", null);

		// initialise the StatusBar layout container
		setStyleName("vino-StatusBar");
		setHeight(STATUSBAR_HEIGHT);

		// initialise the Selected label
		Label selectedLabel = new Label();
		selectedLabel.setStyleName("vino-StatusBar-Label");
		selectedLabel.setContents(SELECTED_LABEL_DISPLAY_NAME);
		selectedLabel.setAlign(Alignment.LEFT);
		selectedLabel.setOverflow(Overflow.HIDDEN);

		// initialise the Result Set First button
		ImgButton resultSetFirstButton = new ImgButton();
		resultSetFirstButton.setShowRollOver(false);
		resultSetFirstButton.setShowDisabled(false);
		resultSetFirstButton.setShowDown(false);
		resultSetFirstButton.setSize(12);
		resultSetFirstButton.setLayoutAlign(VerticalAlignment.CENTER);
		resultSetFirstButton.setSrc("statusbar/resultsetfirst.png");

		// initialise the Result Set Previous button
		ImgButton resultSetPreviousButton = new ImgButton();
		resultSetPreviousButton.setShowRollOver(false);
		resultSetPreviousButton.setShowDisabled(false);
		resultSetPreviousButton.setShowDown(false);
		resultSetPreviousButton.setSize(12);
		resultSetPreviousButton.setLayoutAlign(VerticalAlignment.CENTER);
		resultSetPreviousButton.setSrc("statusbar/resultsetprevious.png");

		// initialise the Page Number label
		Label pageNumberLabel = new Label();
		pageNumberLabel.setStyleName("vino-StatusBar-Label");
		pageNumberLabel.setContents(PAGE_NUMBER_LABEL_DISPLAY_NAME);
		pageNumberLabel.setWidth(50);
		pageNumberLabel.setAlign(Alignment.RIGHT);
		pageNumberLabel.setOverflow(Overflow.HIDDEN);

		// initialise the Result Set Next button
		ImgButton resultSetNextButton = new ImgButton();
		resultSetNextButton.setShowRollOver(false);
		resultSetNextButton.setShowDisabled(false);
		resultSetNextButton.setShowDown(false);
		resultSetNextButton.setSize(12);
		resultSetNextButton.setLayoutAlign(VerticalAlignment.CENTER);
		resultSetNextButton.setSrc("statusbar/resultsetnext.png");

		// add the widgets to the StatusBar layout container
		addMember(selectedLabel);
		
		// force right alignment
		Label alignRight = new Label(" ");
		alignRight.setAlign(Alignment.RIGHT);
		alignRight.setOverflow(Overflow.HIDDEN);
		addMember(alignRight);
		addMember(resultSetFirstButton);
		addMember(resultSetPreviousButton);
		addMember(pageNumberLabel);
		addMember(resultSetNextButton);
		
		// add some padding
		LayoutSpacer paddingRight = new LayoutSpacer();
		paddingRight.setWidth(8);
		addMember(paddingRight);
	}
}
