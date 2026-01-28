package ch.persi.vino.gui2.client.trading;

import ch.persi.vino.gui2.client.components.ContentAreaFactory;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.widgets.Canvas;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.VLayout;

public class TradingView extends VLayout {

	private static final String DESCRIPTION = "TradingView";
	
	public TradingView()
	{
		super();
		
		GWT.log("initialization of TradingView runs...", null);
			
	    init();
	    
	    initContent();
	    
	}
	
	private final void init()
	{
		setStyleName("vino-Content");
		setWidth("*"); 
	}
	
	private final void initContent()
	{
		addMember(new Label("trading component"));		
	}
	
	public static class Factory implements ContentAreaFactory {

		private String id;

		@Override
		public Canvas create() {
			TradingView view = new TradingView();
			id = view.getID();

			GWT.log("TradingView.Factory.create()->view.getID() - " + id, null);
			return view;
		}

		@Override
		public String getID() {
			return id;
		}

		@Override
		public String getDescription() {
			return DESCRIPTION;
		}
	}
}