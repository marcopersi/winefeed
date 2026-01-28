package ch.persi.vino.gui2.client.marketdata.gui;

import ch.persi.vino.gui2.client.components.ContentAreaFactory;
import ch.persi.vino.gui2.client.marketdata.service.VinoDataSource;
import ch.persi.vino.gui2.client.widget.JumpBar;
import ch.persi.vino.gui2.client.widget.StatusBar;
import ch.persi.vino.gui2.client.widget.ToolBar;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.types.ChartType;
import com.smartgwt.client.types.FetchMode;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.Canvas;
import com.smartgwt.client.widgets.chart.FacetChart;
import com.smartgwt.client.widgets.cube.Facet;
import com.smartgwt.client.widgets.grid.ListGrid;
import com.smartgwt.client.widgets.grid.ListGridField;
import com.smartgwt.client.widgets.layout.VLayout;

public class MarketDataView extends VLayout {

	private static final String DESCRIPTION = "MarketDataView";
	private static final String CONTEXT_AREA_WIDTH = "*";

	public MarketDataView()
	{
		super();
		
		GWT.log("initialization of marketDataView runs...", null);
			
	    init();
	    
	    initContent();
	    
	}
	
	private final void init()
	{
		setStyleName("vino-Content");
		setWidth(CONTEXT_AREA_WIDTH);
	}
	
	private final void initContent()
	{
        if(SC.hasCharts()) {  
            if(SC.hasDrawing()) { 
            	final FacetChart chart = new FacetChart();  
            	// FIXME: use the same data for chart and ListGrid 
            	chart.setData(ChartData.getData());  
            	chart.setFacets(new Facet("Datum", "Datum"), new Facet("Wein", "Wein"));  
            	chart.setValueProperty("preis");  
            	chart.setChartType(ChartType.LINE);  
            	chart.setTitle("Wine Prices");  
            	addMember(chart);
            	
            }
        }            
		
//		http://www.smartclient.com/smartgwtee/showcase/#gridCharting		
		
		ListGrid marketDataTable = createMarketDataTable();
		addMember(new ToolBar());
		addMember(marketDataTable);		
		addMember(new StatusBar());
		addMember(new JumpBar());
	}
	
	private final ListGrid createMarketDataTable()
	{
		ListGrid listGrid =  new MarketDataTable();

		VinoDataSource dataSource = getDataSource();
		
		listGrid.setDataSource(dataSource);
		
		return listGrid;
		
	}
	
	private static VinoDataSource getDataSource()
	{
		return VinoDataSource.getInstance();
		
//		ApplicationContext context = new ClassPathXmlApplicationContext("classpath:conf/context.xml");
//		DataService dataService = (DataService) context.getBean("dataService");
//		return dataService;
	}
	
	class MarketDataTable extends ListGrid {
		
		public MarketDataTable()
		{
			super();
			
			ListGridField originField = new ListGridField("origin", "Origin", 60);
			ListGridField wineNameField = new ListGridField("wineName", "Wine", 120);
			ListGridField countryCode = new ListGridField("countryCode", "Country",50);
			ListGridField wineVintageField = new ListGridField("vintage","Vintage", 60);
			ListGridField latestPriceField = new ListGridField("latestPrice","LatestPrice", 70);
			ListGridField ratingField = new ListGridField("latestRating","LatestRating", 40);
			ListGridField ratingAgencyField = new ListGridField("ratingAgency","RatingAgency", 90);
			
// FIXME: different than prototype check it out			
//			setWidth(1240);  
//			setHeight(300);  

			setFields(originField, wineNameField, countryCode,wineVintageField, latestPriceField, ratingField,ratingAgencyField);
			setAutoFetchData(true);
			setDataFetchMode(FetchMode.PAGED);
			setShowAllRecords(true);
			setDataPageSize(1);
			setCanEdit(false);
			setShowFilterEditor(true);
			setStyleName("vino-ContentArea");
		}
	}
	
	public static class Factory implements ContentAreaFactory {

		private String id;

		@Override
		public Canvas create() {
			MarketDataView view = new MarketDataView();
			id = view.getID();
			GWT.log("MarketDataView.Factory.create()->view.getID() - " + id,null);
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
