package ch.persi.vino.gui2.client.portfolio;

import ch.persi.vino.gui2.client.components.ContentAreaFactory;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.widgets.Canvas;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.VLayout;

public class PortfolioView extends VLayout {

	private static final String DESCRIPTION = "PortfolioView";
	
	public PortfolioView()
	{
		super();
		
		GWT.log("initialization of PortfolioView runs...", null);
			
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
		addMember(new Label("Portfolio component"));		
	}
	
	public static class Factory implements ContentAreaFactory {

		private String id;

		@Override
		public Canvas create() {
			PortfolioView view = new PortfolioView();
			id = view.getID();

			GWT.log("PortfolioView.Factory.create()->view.getID() - " + id, null);
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