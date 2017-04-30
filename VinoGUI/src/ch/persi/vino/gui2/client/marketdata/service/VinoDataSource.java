package ch.persi.vino.gui2.client.marketdata.service;

import java.util.ArrayList;
import java.util.List;

import ch.persi.vino.gui2.client.lib.GenericGwtRpcDataSource;
import ch.persi.vino.gui2.shared.WineOffering;

import com.google.gwt.core.client.GWT;
import com.smartgwt.client.data.DataSourceField;
import com.smartgwt.client.data.fields.DataSourceTextField;
import com.smartgwt.client.widgets.grid.ListGridRecord;

public class VinoDataSource
		extends
		GenericGwtRpcDataSource<WineOffering, ListGridRecord, VinoDaoServiceAsync> {

	private static VinoDataSource instance;

	// forces to use the singleton through getInstance();
	private VinoDataSource() {
	};

	public static VinoDataSource getInstance() {
		if (instance == null) {
			instance = new VinoDataSource();
		}
		return (instance);
	}

	@Override
	public void copyValues(ListGridRecord from, WineOffering to) {
		to.setCountryCode(from.getAttribute("countryCode"));
		to.setLatestPrice(from.getAttribute("latestPrice"));
		to.setLatestRating(from.getAttribute("latestRating"));
		to.setOrigin(from.getAttribute("origin"));
		to.setRatingAgency(from.getAttribute("ratingAgency"));
		to.setVintage(from.getAttribute("vintage"));
		to.setWineName(from.getAttribute("wineName"));
	}

	@Override
	public void copyValues(WineOffering from, ListGridRecord to) {
		to.setAttribute("countryCode", from.getCountryCode());
		to.setAttribute("latestPrice", from.getLatestPrice());
		to.setAttribute("latestRating", from.getLatestRating());
		to.setAttribute("origin", from.getOrigin());
		to.setAttribute("ratingAgency", from.getRatingAgency());
		to.setAttribute("vintage", from.getVintage());
		to.setAttribute("wineName", from.getWineName());
	}

	@Override
	public List<DataSourceField> getDataSourceFields() {

		List<DataSourceField> fields = new ArrayList<>();
		DataSourceTextField countryField = new DataSourceTextField("countryCode", "Country");
		fields.add(countryField);

		DataSourceTextField originField = new DataSourceTextField("origin", "Origin");
		fields.add(originField);

		DataSourceTextField ratingAgencyField = new DataSourceTextField("ratingAgency", "RatingAgency");
		fields.add(ratingAgencyField);

		DataSourceTextField vintageField = new DataSourceTextField("vintage", "Vintage");
		fields.add(vintageField);

		DataSourceTextField wineNameField = new DataSourceTextField("wineName", "wineName");
		fields.add(wineNameField);
		
		DataSourceTextField latestPriceField = new DataSourceTextField("latestPrice","LatestPrice");
		fields.add(latestPriceField);

		DataSourceTextField latestRatingField = new DataSourceTextField("latestRating", "LatestRating");
		fields.add(latestRatingField);

		
		//
//		DataSourceIntegerField idField = new DataSourceIntegerField("id");
//		idField.setHidden(true);
//		idField.setPrimaryKey(true);
//		fields.add(idField);
//
//		DataSourceTextField nameField = new DataSourceTextField("name", "Name");
//		nameField.setRequired(true);
//		fields.add(nameField);
//
//		DataSourceTextField locationField = new DataSourceTextField("location", "Location");
//		locationField.setRequired(true);
//		fields.add(locationField);
//
		return fields;
	}

	@Override
	public WineOffering getNewDataObjectInstance() {
		return new WineOffering();
	}

	@Override
	public ListGridRecord getNewRecordInstance() {
		return new ListGridRecord();
	}

	@Override
	public VinoDaoServiceAsync getServiceAsync() {
		return GWT.create(VinoDaoService.class);
	}

}
