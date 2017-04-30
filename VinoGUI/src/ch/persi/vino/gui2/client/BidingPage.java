package ch.persi.vino.gui2.client;

import ch.persi.vino.gui2.client.marketdata.service.VinoDataSource;

import com.google.gwt.core.client.EntryPoint;
import com.google.gwt.core.client.GWT;
import com.google.gwt.resources.client.ClientBundle;
import com.google.gwt.resources.client.CssResource;
import com.google.gwt.resources.client.CssResource.NotStrict;
import com.google.gwt.user.client.ui.RootPanel;
import com.google.gwt.user.client.ui.VerticalPanel;
import com.smartgwt.client.types.FetchMode;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.grid.ListGrid;
import com.smartgwt.client.widgets.grid.ListGridField;
import com.smartgwt.client.widgets.grid.events.EditorEnterEvent;
import com.smartgwt.client.widgets.grid.events.EditorEnterHandler;

public class BidingPage implements EntryPoint {

	private final VinoDataSource instance = VinoDataSource.getInstance();

	interface GlobalResources extends ClientBundle {
		@NotStrict
		@Source("VinoGUI2.css")
		CssResource css();
	  }  
	
	@Override
	public void onModuleLoad() {
		
		GWT.<GlobalResources>create(GlobalResources.class).css().ensureInjected();
		
		
		VerticalPanel aPanel = new VerticalPanel();
		
		aPanel.setSpacing(20);
		
//				aPanel.add(new ChartProvider().getChart());
		
		// adding the data list
		aPanel.add(createListGrid());
		
		// make it visible
		RootPanel.get().add(aPanel);
		
		
//		Runnable aRunnableCallBack = new Runnable(){
//
//			@Override
//			public void run() {
//			}
//		};
//		
//		// loading the google visualization dependencies, passing the executable call back to be executed once loaded
//		VisualizationUtils.loadVisualizationApi(aRunnableCallBack, AnnotatedTimeLine.PACKAGE);
	}

	final ListGrid createListGrid() {
		
		
		ListGridField lotNumber = new ListGridField("lotNumber", "Lot", 50);
		ListGridField wineNameField = new ListGridField("wineName", "Wine", 200);
		ListGridField owc = new ListGridField("owc", "OHK", 50);
		ListGridField lower = new ListGridField("lower", "Preis von", 100);
		ListGridField higher = new ListGridField("higher", "Preis bis", 100);
		ListGridField gross = new ListGridField("gross", "Brutto", 100);

		ListGridField bid = new ListGridField("bid", "Gebot", 100);
		bid.setCanEdit(true);
		bid.addEditorEnterHandler(new EditorEnterHandler() {

			@Override
			public void onEditorEnter(EditorEnterEvent event) {
				SC.say("received the input of :" + event.getSource().toString());
				
				// FIXME: how to update gross column/cell now ?
			}
		});


		final ListGrid countryGrid = new ListGrid();
		countryGrid.setWidth(1240);  
        countryGrid.setHeight(300);  
		countryGrid.setDataSource(instance);  
		countryGrid.setFields(lotNumber, wineNameField, owc,
				lower, higher, bid,
				gross);
		countryGrid.setAutoFetchData(true);
		countryGrid.setDataFetchMode(FetchMode.PAGED);
		countryGrid.setShowAllRecords(true);
		countryGrid.setDataPageSize(1);
//		countryGrid.setCanEdit(false);
		countryGrid.setShowFilterEditor(true);
		return countryGrid;
	}

}
