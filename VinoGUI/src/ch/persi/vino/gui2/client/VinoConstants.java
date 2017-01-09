package ch.persi.vino.gui2.client;

import com.google.gwt.i18n.client.Constants;

public interface VinoConstants extends Constants {

	// Menus
	
	  @DefaultStringValue("<u>N</u>ew Activity")
	  String NewActivityMenuName();
	  
	  @DefaultStringValue("Task, Fax, Phone Call, Email, Letter, Appointment")
	  String NewActivityMenuItemNames(); 
	  
	  @DefaultStringValue("New Re<u>c</u>ord")
	  String NewRecordMenuName();  
	  
	  @DefaultStringValue("Account, Contact, separator, Lead, Opportunity")
	  String NewRecordMenuItemNames();
	  
	  @DefaultStringValue("<u>G</u>o To")
	  String GoToMenuName();  
	  
	  @DefaultStringValue("Sales")
	  String SalesMenuItemName();

	  @DefaultStringValue("Leads, Opportunities, Accounts, Contacts")
	  String SalesMenuItemNames();  
	  
	  @DefaultStringValue("Settings")
	  String SettingsMenuItemName();

	  @DefaultStringValue("Administration, Templates, Data Management")
	  String SettingsMenuItemNames();    
	  
	  @DefaultStringValue("Resource Centre")
	  String ResourceCentreMenuItemName();

	  @DefaultStringValue("Highlights, Sales, Settings")
	  String ResourceCentreMenuItemNames();
	  
	  @DefaultStringValue("<u>T</u>ools")
	  String ToolsMenuName();  
	  
	  @DefaultStringValue("Import Data, Duplicate Detection, Advanced Find, Options")
	  String ToolsMenuItemNames();

	  @DefaultStringValue("<u>H</u>elp")
	  String HelpMenuName();  
	  
	  @DefaultStringValue("Help on this Page, Contents, myCRM Online, About myCRM")
	  String HelpMenuItemNames();
	  
	  // Navigation Pane Header
	  
	  @DefaultStringValue("Workplace")
	  String Workplace();
	  
	  @DefaultStringValue("Activites")
	  String Activites();
	  
	  // Navigation Pane 
	  
	  @DefaultStringValue("Sales")
	  String SalesStackSectionName();
	  
	  @DefaultStringValue("Settings")
	  String SettingsStackSectionName();
	  
	  @DefaultStringValue("Resource Centre")
	  String ResourceCentreStackSectionName();
	  
	  @DefaultStringValue("Market Data")
	  String MarketDataStackSectionName();
	  
	  @DefaultStringValue("Portfolio")
	  String PortfolioStackSectionName();

	  @DefaultStringValue("Trading")
	  String TradingStackSectionName();
	  
	  
	  // Toolbar
	  
	  @DefaultStringValue("New")
	  String New();
	  
	  // Form Toolbar
	  
	  @DefaultStringValue("Save and Close")
	  String SaveAndClose();
	  
	  @DefaultStringValue("Help")
	  String Help();
	  
	  // Form Tabs
	  
	  @DefaultStringValue("General")
	  String GeneralTab();
	  
	  @DefaultStringValue("Administration")
	  String AdministrationTab();  
	  
	  @DefaultStringValue("Notes")
	  String NotesTab(); 
	
	
}
