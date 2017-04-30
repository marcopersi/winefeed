package ch.persi.vino.gui2.client.navigation;

import ch.persi.vino.gui2.client.components.ContentAreaFactory;

import com.smartgwt.client.widgets.grid.ListGridRecord;
import com.smartgwt.client.widgets.grid.events.CellDoubleClickHandler;

public class NavigationPaneRecord extends ListGridRecord {

	public NavigationPaneRecord(String theIcon, String theName,
			ContentAreaFactory theContentFactory,
			CellDoubleClickHandler theClickHandler) {
		setIcon(theIcon);
		setName(theName);
		setFactory(theContentFactory);
		setDoubleClickHandler(theClickHandler);
	}

	public void setIcon(String theApplicationIcon) {
		setAttribute("icon", theApplicationIcon);
	}

	public void setName(String appName) {
		setAttribute("name", appName);
	}

	public void setFactory(ContentAreaFactory theContentFactory) {
		setAttribute("factory", theContentFactory);
	}

	public void setDoubleClickHandler(CellDoubleClickHandler theDoubleClickhandler) {
		setAttribute("clickHandler", theDoubleClickhandler);
	}

	public String getIcon() {
		return getAttributeAsString("icon");
	}

	public String getName() {
		return getAttributeAsString("name");
	}

	public ContentAreaFactory getFactory() {
		return (ContentAreaFactory) getAttributeAsObject("factory");
	}

	public CellDoubleClickHandler getDoubleClickHandler() {
		return (CellDoubleClickHandler) getAttributeAsObject("clickHandler");
	}
}