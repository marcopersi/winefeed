package ch.persi.vino.gui2.client.components;

import com.smartgwt.client.widgets.Canvas;

public interface ContentAreaFactory {

	  Canvas create();

	  String getID();

	  String getDescription();
}
