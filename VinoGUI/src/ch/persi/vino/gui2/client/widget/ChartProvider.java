package ch.persi.vino.gui2.client.widget;

import java.util.Date;

import org.joda.time.LocalDateTime;

import com.google.gwt.core.client.GWT;
import com.google.gwt.core.client.JavaScriptException;
import com.google.gwt.user.client.ui.Label;
import com.google.gwt.visualization.client.AbstractDataTable.ColumnType;
import com.google.gwt.visualization.client.DataTable;
import com.google.gwt.visualization.client.events.RangeChangeHandler;
import com.google.gwt.visualization.client.visualizations.AnnotatedTimeLine;
import com.google.gwt.visualization.client.visualizations.AnnotatedTimeLine.Options;

public class ChartProvider {

	private AnnotatedTimeLine chart;
	Label rangeStatusLabel = new Label();

	public AnnotatedTimeLine getChart()
	{
		Options options = Options.create();
		options.setDisplayAnnotations(true);
		
		DataTable data = getDataTable();
		
		try {
			data.setValue(0, 0, toDate(1,2,2011));
			data.setValue(1, 0,	toDate(2,1,2011));
			data.setValue(2, 0,	toDate(3,11,2010));
			data.setValue(3, 0,	toDate(4,7,2010));
			data.setValue(4, 0,	toDate(5,5,2010));
			data.setValue(5, 0,	toDate(6,3,2010));
		} catch (JavaScriptException ex) {
			GWT.log("Error creating data table - Date bug on mac?", ex);
		}
		data.setValue(0, 1, 450);
		data.setValue(0, 4, 410);
		data.setValue(1, 1, 475);
		data.setValue(1, 4, 410);
		data.setValue(2, 1, 465);
		data.setValue(2, 4, 415);
		data.setValue(3, 1, 500);
		data.setValue(3, 4, 455);
		data.setValue(4, 1, 550);
		data.setValue(4, 4, 545);
		data.setValue(5, 1, 600);
		data.setValue(5, 4, 580);

		// creating chart
		chart = new AnnotatedTimeLine(data, options, "1240px", "300px");

		// creating range status label
//		chartPanel.add(rangeStatusLabel);
		
		addHandlers();
		
		return chart;
	}
	
	private final void addHandlers() {
		chart.addRangeChangeHandler(new RangeChangeHandler() {
			@Override
			public void onRangeChange(RangeChangeEvent event) {
				rangeStatusLabel.setText("The range has changed.\n"
						+ event.getStart() + "\nFalls mainly on the plains.\n"
						+ event.getEnd());
			}
		});
	}

	private static final Date toDate(int day, int month, int year)
	{
		return new LocalDateTime(year, month, day, 23, 59).toDate();
	}
	
	private final static DataTable getDataTable()
	{
		DataTable data = DataTable.create();
		data.addColumn(ColumnType.DATE, "Date");
		data.addColumn(ColumnType.NUMBER, "Masseto Price Wermuth");
		data.addColumn(ColumnType.STRING, "title1");
		data.addColumn(ColumnType.STRING, "text1");
		data.addColumn(ColumnType.NUMBER, "Masseto Price Weinboerse");
		data.addColumn(ColumnType.STRING, "title2");
		data.addColumn(ColumnType.STRING, "text2");
		data.addRows(6);
		return data;
	}
}
