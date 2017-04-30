package ch.persi.vino.gui2.client.menu;

import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.menu.events.ClickHandler;
import com.smartgwt.client.widgets.menu.events.MenuItemClickEvent;

public class ApplicationMenuClickHandler implements ClickHandler {

	@Override
	public void onClick(MenuItemClickEvent event) {
		String applicationName = event.getItem().getTitle();
		SC.say("You clicked: " + applicationName);
	}

}
