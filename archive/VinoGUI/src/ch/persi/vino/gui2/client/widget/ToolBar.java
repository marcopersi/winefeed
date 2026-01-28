package ch.persi.vino.gui2.client.widget;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.toolbar.ToolStrip;
import com.smartgwt.client.widgets.toolbar.ToolStripButton;

public class ToolBar extends HLayout {
	
	private static final String TOOLBAR_HEIGHT = "25px";
	private static final String TOOLSTRIP_WIDTH = "*";
	private static final String NEW_BUTTON = "toolbar/new.png";
	private static final String PRINT_PREVIEW_BUTTON = "toolbar/printpreview.png";
	private static final String EXPORT_BUTTON = "toolbar/export.png";
	private static final String MAIL_MERGE_BUTTON = "toolbar/mailmerge.png";
	private static final String REPORTS_BUTTON = "toolbar/reports.png";
	private static final String ASSIGN_BUTTON = "toolbar/assign.png";
	private static final String DELETE_BUTTON = "toolbar/delete.png";
	private static final String EMAIL_BUTTON = "toolbar/sendemail.png";

	private static final String NEW_BUTTON_DISPLAY_NAME = "New";

	public ToolBar() {
		super();

		GWT.log("initialization of ToolBar runs...", null);

		// initialise the ToolBar layout container
		setStyleName("vino-ToolBar");
		setHeight(TOOLBAR_HEIGHT);

		// initialise the ToolStrip
		ToolStrip toolStrip = new ToolStrip();
		toolStrip.setHeight(TOOLBAR_HEIGHT);
		toolStrip.setWidth(TOOLSTRIP_WIDTH);

		// initialise the New button
		ToolStripButton newButton = new ToolStripButton();
		newButton.setIcon(NEW_BUTTON);
		newButton.setTitle(NEW_BUTTON_DISPLAY_NAME);
		newButton.addClickHandler(new ClickHandler() {
			@Override
			public void onClick(ClickEvent event) {
				SC.say("You clicked the New button.");
			}
		});

		toolStrip.addButton(newButton);
		toolStrip.addSeparator();

		// initialise the Print Preview button
		ToolStripButton printPreviewButton = new ToolStripButton();
		printPreviewButton.setIcon(PRINT_PREVIEW_BUTTON);
		toolStrip.addButton(printPreviewButton);

		// initialise the Export button
		ToolStripButton exportButton = new ToolStripButton();
		exportButton.setIcon(EXPORT_BUTTON);
		toolStrip.addButton(exportButton);

		// initialise the Mail Merge button
		ToolStripButton mailMergeButton = new ToolStripButton();
		mailMergeButton.setIcon(MAIL_MERGE_BUTTON);
		toolStrip.addButton(mailMergeButton);

		// initialise the Reports button
		ToolStripButton reportsButton = new ToolStripButton();
		reportsButton.setIcon(REPORTS_BUTTON);
		toolStrip.addButton(reportsButton);
		toolStrip.addSeparator();

		// initialise the Assign button
		ToolStripButton assignButton = new ToolStripButton();
		assignButton.setIcon(ASSIGN_BUTTON);
		toolStrip.addButton(assignButton);

		// initialise the Delete button
		ToolStripButton deleteButton = new ToolStripButton();
		deleteButton.setIcon(DELETE_BUTTON);
		toolStrip.addButton(deleteButton);

		// initialise the Email button
		ToolStripButton emailButton = new ToolStripButton();
		emailButton.setIcon(EMAIL_BUTTON);
		toolStrip.addButton(emailButton);

		// add the ToolStrip to the ToolBar layout container
		addMember(toolStrip);
	}
}
