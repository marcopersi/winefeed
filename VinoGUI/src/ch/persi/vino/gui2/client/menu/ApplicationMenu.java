package ch.persi.vino.gui2.client.menu;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.widgets.layout.VLayout;
import com.smartgwt.client.widgets.menu.Menu;
import com.smartgwt.client.widgets.menu.MenuBar;
import com.smartgwt.client.widgets.menu.MenuItem;
import com.smartgwt.client.widgets.menu.MenuItemSeparator;
import com.smartgwt.client.widgets.menu.events.ClickHandler;

public class ApplicationMenu extends VLayout {

	/**
	 * the background color of the application menue bar
	 */
	private static final String BACKGROUND_COLOR = "#4096EE";

	/**
	 * the height of the menu
	 */
	private static final int APPLICATION_MENU_HEIGHT = 27;

	/**
	 * the shadow depth
	 */
	private static final int DEFAULT_SHADOW_DEPTH = 10;

	private static final String SEPARATOR = "separator";
	private static final String ICON_PREFIX = "icons/16/";
	private static final String ICON_SUFFIX = ".png";

	private MenuBar menuBar;
	private int menuPosition = 0;

	public ApplicationMenu() {
		super();

		GWT.log("initialization of the application menue runs", null);

		init();

		initContent();
	}

	private final void init() {
		setHeight(APPLICATION_MENU_HEIGHT);
		setBackgroundColor(BACKGROUND_COLOR);
		setStyleName("vino-ApplicationMenu");
	}

	private final void initContent() {
		// creating & adding the menu bar
		menuBar = new MenuBar();
		addMember(menuBar);  	
	}

	public Menu addMenu(String theMenueName, int theWidth, String theMenueItems,ClickHandler theClickHandler) {
		// initialise the new menu
		Menu menu = new Menu(); 
		menu.setTitle(theMenueName);
		menu.setShowShadow(true);  
		menu.setShadowDepth(DEFAULT_SHADOW_DEPTH); 
		menu.setWidth(theWidth);
		
		// create an array of menu item names 
		String[] menuItems = process(theMenueItems);
		
		for (int i = 0; i < menuItems.length; i++) {
		  // remove any whitespace
		  String menuItemName = menuItems[i].replaceAll("\\W", "");

		  if (menuItemName.contentEquals(SEPARATOR)) {
		    MenuItemSeparator separator = new MenuItemSeparator();
		    menu.addItem(separator);  
		    continue;
		  }
			  
		  MenuItem menuItem = new MenuItem(menuItems[i], getIcon(menuItems[i])); 
		  menuItem.addClickHandler(theClickHandler);
		  menu.addItem(menuItem);    
		}
			
		Menu[] menus = new Menu[1]; 
		menus[0] = menu;
		menuBar.addMenus(menus, menuPosition);
		menuPosition++ ;
		
		return menus[0];
	  }
		  
	  public Menu addMenu(String menuName, int width) {
		// initialise the new menu
		Menu menu = new Menu(); 
		menu.setTitle(menuName);
		menu.setShowShadow(true);  
		menu.setShadowDepth(DEFAULT_SHADOW_DEPTH); 
		menu.setWidth(width);
			
		Menu[] menus = new Menu[1]; 
		menus[0] = menu;
		menuBar.addMenus(menus, menuPosition);	
		menuPosition++ ;
			
		return menu;
	  }
		  
	  public Menu addSubMenu(Menu parentMenu, String subMenuName, String menuItemNames) {
		// initialise the new sub menu
		Menu menu = new Menu(); 
		menu.setShowShadow(true);  
		menu.setShadowDepth(DEFAULT_SHADOW_DEPTH); 
				
		MenuItem menuItem = new MenuItem(subMenuName);
		
		// create an array of menu item names 
		String[] menuItems = process(menuItemNames);

		for (int i = 0; i < menuItems.length; i++) {
		  // remove any whitespace
		  String menuItemName = menuItems[i].replaceAll("\\W", "");
				  
		  if (menuItemName.contentEquals(SEPARATOR)) {
		    MenuItemSeparator separator = new MenuItemSeparator();
		    menu.addItem(separator);  
		    continue;
		  }
				  
		  menuItem = new MenuItem(menuItems[i], getIcon(menuItems[i])); 
		  // menuItem.addClickHandler(clickHandler);
		  menu.addItem(menuItem);    
		}
				
		// add the sub menu to the menu item
		menuItem = new MenuItem(subMenuName);
		parentMenu.addItem(menuItem); 
		menuItem.setSubmenu(menu);
				
		return menu;
	  }  
		  
	  public final static String DELIMITER = ",";
		  
	  public static String[] process(String line) {
	    return line.split(DELIMITER);
	  }
		  
	  private static String getIcon(String applicationName) {
		// remove any whitespace
		String name = applicationName.replaceAll("\\W", "");
		// e.g. "icons/16/" + "activities" + ".png"	
		String icon = ICON_PREFIX + name.toLowerCase() + ICON_SUFFIX ; 
		return icon ;
	  }	
}
