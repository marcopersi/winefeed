package ch.persi.vino.gui2.client.components;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.Overflow;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.VLayout;

public class ContentArea extends VLayout{
	/**
	 * the background color of the application ContentArea
	 */
	private static final String BACKGROUND_COLOR = "#EEEEEE";

	public ContentArea() {
		super();

		GWT.log("initialization of the content area runs", null);

		init();

		initContent();
	}

	private final void init() {
		setWidth("*");
		setBackgroundColor(BACKGROUND_COLOR);

	}

	private final void initContent() {
		Label label = new Label();
		label.setContents("Context Area");
		label.setAlign(Alignment.CENTER);
		label.setOverflow(Overflow.HIDDEN);
		addMember(label);
	}

}
