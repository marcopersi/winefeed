package ch.persi.vino.gui2.client;

import ch.persi.vino.gui2.client.components.ContentAreaFactory;
import ch.persi.vino.gui2.client.marketdata.gui.MarketDataView;
import ch.persi.vino.gui2.client.menu.ApplicationMenu;
import ch.persi.vino.gui2.client.navigation.Header;
import ch.persi.vino.gui2.client.navigation.MarketDataNavigationPaneSectionData;
import ch.persi.vino.gui2.client.navigation.NavigationPane;
import ch.persi.vino.gui2.client.navigation.NavigationPaneHeader;
import ch.persi.vino.gui2.client.navigation.NavigationPaneRecord;
import ch.persi.vino.gui2.client.navigation.PortfolioNavigationPaneSectionData;
import ch.persi.vino.gui2.client.navigation.TradingNavigationPaneSectionData;

import com.google.gwt.core.client.EntryPoint;
import com.google.gwt.core.client.GWT;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.CssResource;
import com.google.gwt.resources.client.CssResource.NotStrict;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.RootLayoutPanel;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.grid.events.RecordClickEvent;
import com.smartgwt.client.widgets.grid.events.RecordClickHandler;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.layout.VLayout;
import com.smartgwt.client.widgets.menu.Menu;
import com.smartgwt.client.widgets.menu.events.ClickHandler;
import com.smartgwt.client.widgets.menu.events.MenuItemClickEvent;

public class VinoGUI implements EntryPoint {

	/**
	 * total (sum) height of header and application menu 
	 */
	private static final int NORTH_HEIGHT = 85;
	
	/**
	 * the default menue width
	 */
	private static final int DEFAULT_MENU_WIDTH = 70;
	
	HLayout bodyContainer = null;
	private NavigationPane navigationPane;
//	private VLayout navigationPane;
	private NavigationPaneHeader navigationPaneHeader;

	private VinoConstants translationConstants = GWT.create(VinoConstants.class);

	interface GlobalResources extends ClientBundle {
		@NotStrict
		@Source("VinoGUI2.css")
		CssResource css();
		
	  }  	
	
	@Override
	public void onModuleLoad() {
		GWT.log("init runs...", null);

		GWT.<GlobalResources>create(GlobalResources.class).css().ensureInjected();
		
		// get rid of scroll bars, and clear out the window's built-in margin,
		// because we want to take advantage of the entire client area
		Window.enableScrolling(false);
		Window.setMargin("0px");

		// add the main layout container to GWT's root panel
		RootLayoutPanel.get().add(createContent());
	}
	
	private VLayout createContent()
	{
		VLayout contentArea = new VLayout();
		contentArea.setWidth100();
		contentArea.setHeight100();
		contentArea.addMember(createHeaderPart());
		contentArea.addMember(createBodyPart());
		return contentArea;
	}
	
	private HLayout createBodyPart() {
		bodyContainer = new HLayout();
		bodyContainer.setMembers(getNavigationPane(), new MarketDataView());
		return bodyContainer;
	}

	private final HLayout createHeaderPart()
	{
		HLayout headerPart = new HLayout();
		headerPart.setHeight(NORTH_HEIGHT);

		VLayout vLayout = new VLayout();
		vLayout.addMember(new Header());
		vLayout.addMember(createApplicationMenue());
		vLayout.addMember(getNavigationPaneHeader());

		headerPart.addMember(vLayout);
		return headerPart;
	}
	
	VLayout getNavigationPane()
	{
		if (navigationPane == null)
		{
			
//			final SectionStack sectionStack = new SectionStack();  
//	        sectionStack.setVisibilityMode(VisibilityMode.MUTEX);  
//	        sectionStack.setWidth(300);  
//	        sectionStack.setHeight(350);  
//	  
//	        SectionStackSection section1 = new SectionStackSection("Market Data");  
//	        section1.setExpanded(true);  
//	        section1.addItem(new Img("images/icons/16/chart_line.png", 16, 16));  
//	        sectionStack.addSection(section1);  
//	  
//	        SectionStackSection section2 = new SectionStackSection("Portfolio");  
//	        section2.setExpanded(false);  
//	        section2.setCanCollapse(false);  
//	        section2.addItem(new Img("images/icons/16/chart_line.png", 16, 16));  
//	        sectionStack.addSection(section2);
//	  
//	        SectionStackSection section3 = new SectionStackSection("Trading");  
//	        section3.setExpanded(false);  
//	        section3.addItem(new Img("images/icons/16/chart_line.png", 16, 16));  
//	        sectionStack.addSection(section3);  
//			
//	        navigationPane = new VLayout();
//	        navigationPane.addMember(sectionStack);
//	        navigationPane.setMargin(20);
//			return navigationPane;
			
			
			navigationPane = new NavigationPane();
			navigationPane.add(translationConstants.MarketDataStackSectionName(), MarketDataNavigationPaneSectionData.getRecords(), new NavigationPaneClickHandler());
			navigationPane.add(translationConstants.PortfolioStackSectionName(), PortfolioNavigationPaneSectionData.getRecords(), new NavigationPaneClickHandler());
			navigationPane.add(translationConstants.TradingStackSectionName(), TradingNavigationPaneSectionData.getRecords(), new NavigationPaneClickHandler());
			navigationPane.expandSection(0); // set market data as default expanded one
		}
	    return navigationPane;
	}
	
	private ApplicationMenu createApplicationMenue()
	{
		// FIXE: adjust menue...File, abmelden ; Administration (run import), usw. usf.  ; Optionen - einstellungen, usw. usf.
		ApplicationMenu applicationMenu = new ApplicationMenu();
		
	    applicationMenu.addMenu(translationConstants.NewActivityMenuName(), DEFAULT_MENU_WIDTH, translationConstants.NewActivityMenuItemNames(),new ApplicationMenuClickHandler());
	    applicationMenu.addMenu(translationConstants.NewRecordMenuName(), DEFAULT_MENU_WIDTH, translationConstants.NewRecordMenuItemNames(),new ApplicationMenuClickHandler());

	    Menu goToMenu = applicationMenu.addMenu(translationConstants.GoToMenuName(), DEFAULT_MENU_WIDTH - 30);
	    applicationMenu.addSubMenu(goToMenu, translationConstants.SalesMenuItemName(), translationConstants.SalesMenuItemNames());
	    applicationMenu.addSubMenu(goToMenu, translationConstants.SettingsMenuItemName(), translationConstants.SettingsMenuItemNames());
	    applicationMenu.addSubMenu(goToMenu, translationConstants.ResourceCentreMenuItemName(), translationConstants.ResourceCentreMenuItemNames());
	    applicationMenu.addMenu(translationConstants.ToolsMenuName(), DEFAULT_MENU_WIDTH - 30, translationConstants.ToolsMenuItemNames(),new ApplicationMenuClickHandler());
	    applicationMenu.addMenu(translationConstants.HelpMenuName(), DEFAULT_MENU_WIDTH - 30, translationConstants.HelpMenuItemNames(),new ApplicationMenuClickHandler());
	    return applicationMenu;
	}
	
	NavigationPaneHeader getNavigationPaneHeader() {
		if (navigationPaneHeader == null)
		{
			navigationPaneHeader = new NavigationPaneHeader();
		}
		return navigationPaneHeader;
	}

	private class ApplicationMenuClickHandler implements ClickHandler {
		public ApplicationMenuClickHandler() {
			// TODO Auto-generated constructor stub
		}

		@Override
		public void onClick(MenuItemClickEvent event) {
			String applicationName = event.getItem().getTitle();
			SC.say("You clicked: " + applicationName);
		}
	}
	
	private class NavigationPaneClickHandler implements RecordClickHandler {
		public NavigationPaneClickHandler() {
			// TODO Auto-generated constructor stub
		}

		@Override
		public void onRecordClick(RecordClickEvent event) {
			NavigationPaneRecord record = (NavigationPaneRecord) event.getRecord();
			getNavigationPaneHeader().setContentAreaHeaderLabelContents(record.getName());	
			
			System.out.println("Within generic NavigationPaneClickHandler, the event is: " + event);
			
			ContentAreaFactory factory = record.getFactory(); // factory which creates the view to be displayed !

			System.out.println("Within generic NavigationPaneClickHandler, the factory is: " + factory);
			
			
			bodyContainer.setMembers(getNavigationPane(), factory.create());
		}

	}
}
