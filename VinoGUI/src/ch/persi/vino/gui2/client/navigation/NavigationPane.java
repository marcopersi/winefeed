package ch.persi.vino.gui2.client.navigation;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.VisibilityMode;
import com.smartgwt.client.widgets.grid.events.RecordClickHandler;
import com.smartgwt.client.widgets.layout.SectionStack;
import com.smartgwt.client.widgets.layout.VLayout;

public class NavigationPane extends VLayout {

	/**
	 * the background color of the navigation pane
	 */
	private static final String BACKGROUND_COLOR = "#3F4C6B";

	/**
	 * the width of the navigation pane
	 */
	private static final int WEST_WIDTH = 200;

	
	private SectionStack sectionStack;
	
	public NavigationPane() {
		super();

		GWT.log("initialization of the navigation pane runs", null);

		init();
		
		initContent();
	}
	
	private final void init()
	{
		setStyleName("vino-NavigationPane");	
	    setWidth(WEST_WIDTH);
		setBackgroundColor(BACKGROUND_COLOR);
		setShowResizeBar(false);
	}
	
	private final void initContent()
	{
		sectionStack = createSectionStack();
		addMember(sectionStack);
	}
	
	private final static SectionStack createSectionStack()
	{
		SectionStack aSectionStack = new SectionStack();
		
		// initialize the Section Stack
		aSectionStack.setWidth(WEST_WIDTH);
		aSectionStack.setVisibilityMode(VisibilityMode.MUTEX);
		aSectionStack.setShowExpandControls(true);
		aSectionStack.setAnimateSections(true);	
		return aSectionStack;
	}
	
	public void add(String theSectionName, NavigationPaneRecord[] theSectionData, RecordClickHandler theClickHandler) {
		sectionStack.addSection(new NavigationPaneSection(theSectionName, theSectionData,theClickHandler));
	} 

	public void expandSection(int theSection) {
		sectionStack.expandSection(theSection);
	} 
}
