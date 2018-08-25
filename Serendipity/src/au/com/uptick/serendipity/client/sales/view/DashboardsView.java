/**
 * (C) Copyright 2010, 2011 upTick Pty Ltd
 *
 * Licensed under the terms of the GNU General Public License version 3
 * as published by the Free Software Foundation. You may obtain a copy of the
 * License at: http://www.gnu.org/copyleft/gpl.html
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package au.com.uptick.serendipity.client.sales.view;

import au.com.uptick.serendipity.client.sales.presenter.DashboardsPresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.DashboardsUiHandlers;
import au.com.uptick.serendipity.client.widgets.FusionChart;
import au.com.uptick.serendipity.client.widgets.AmChart;

import com.google.gwt.user.client.ui.Widget;
import com.gwtplatform.mvp.client.ViewWithUiHandlers;
import com.smartgwt.client.types.Overflow;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.layout.VLayout;

public class DashboardsView extends ViewWithUiHandlers<DashboardsUiHandlers> implements
  DashboardsPresenter.MyView {

  private static final String CONTEXT_AREA_WIDTH = "*";
 
  private VLayout panel;

  // @Inject
  public DashboardsView() {
    super();

    panel = new VLayout();
    panel.setStyleName("crm-ContextArea");
    panel.setWidth(CONTEXT_AREA_WIDTH);
    
    panel.setOverflow(Overflow.AUTO);
    
    drawFusionCharts(panel);
    
    // drawAmCharts(panel);
  }
  
  @Override
  public Widget asWidget() {
    return panel;
  } 
  
  public void setResultSet() { 
  }

  private void drawFusionCharts(VLayout panel) {
    
    FusionChart chart1 = new FusionChart("FCF_StackedColumn2D.swf", "400", "350", "StCol2D.xml"); 
       
    FusionChart chart2 = new FusionChart("FCF_StackedBar2D.swf", "400", "350", "StBar2D.xml");  
    
    // AmChart chart2 = new AmChart("amline.swf", "600", "350", "line_and_area_settings.xml", "line_and_area_data.xml"); // 600, 400
    // FusionChart chart2 = new FusionChart("FCF_StackedArea2D.swf", "400", "350", "StArea2D.xml"); // 600, 350
    
    FusionChart chart3 = new FusionChart("FCF_Doughnut2D.swf", "400", "350", "Doughnut2D.xml"); // 500, 369
    
    FusionChart chart4 = new FusionChart("FCF_Funnel.swf", "350", "300", "Funnel.xml"); // 400, 300  
    
    HLayout northLayout = new HLayout();
    northLayout.setHeight("50%");
    northLayout.setBackgroundColor("#FFFFFF");
    
    northLayout.addMember(chart1);
    northLayout.addMember(chart2);    
    
    HLayout southLayout = new HLayout();
    southLayout.setHeight("50%");    
    southLayout.setBackgroundColor("#FFFFFF");

    southLayout.addMember(chart3);
    southLayout.addMember(chart4);
    
    panel.addMember(northLayout);
    panel.addMember(southLayout);
  }

  private void drawAmCharts(VLayout panel) {
    
    String chart1Data = new String("USA;19544\nJapan;5455\nFrance;2313\nGermany;2208\nUK;2057\nIndia;1771\nRussia;1495\nSouth Korea;1281");
    String chart1Settings = new String("<settings><data_type>csv</data_type><legend><enabled>0</enabled></legend>" + 
        "<pie><inner_radius>30</inner_radius><height>7</height><angle>10</angle><gradient></gradient></pie>" + 
      "<animation><start_time>1</start_time><pull_out_time>1</pull_out_time></animation><data_labels><show>{title}</show>" + 
      "<max_width>100</max_width></data_labels></settings>");

    AmChart chart1 = new AmChart("ampie.swf", "400", "350", chart1Settings, chart1Data, "");  // 600, 400   
    
    AmChart chart2 = new AmChart("ampie.swf", "400", "350", "pie_and_donut_settings.xml", "pie_and_donut_data.txt"); 
    
    AmChart chart3 = new AmChart("amline.swf", "400", "350", "line_settings.xml", "line_data.xml"); 
    
    AmChart chart4 = new AmChart("amline.swf", "400", "350", "line_and_area_settings.xml", "line_and_area_data.xml"); 
 
    HLayout northLayout = new HLayout();
    northLayout.setHeight("50%");
    northLayout.setBackgroundColor("#FFFFFF");
    
    northLayout.addMember(chart2);
    northLayout.addMember(chart1);    
    
    HLayout southLayout = new HLayout();
    southLayout.setHeight("50%");    
    southLayout.setBackgroundColor("#FFFFFF");

    southLayout.addMember(chart3);
    southLayout.addMember(chart4);
    
    panel.addMember(northLayout);
    panel.addMember(southLayout);
  }    
}

/*

  private void drawOfcChart(VLayout panel) {
    ChartWidget chartWidget = new ChartWidget();
    chartWidget.setChartData(getSketchChartData());
    chartWidget.setSize("400", "300");
    panel.addChild(chartWidget);
  }
  
  private ChartData getLineChartData() {
    ChartData cd = new ChartData("Relative Performance", "font-size: 14px; font-family: Verdana; text-align: center;");
    cd.setBackgroundColour("#ffffff");

    LineChart lc1 = new LineChart();
    lc1.setLineStyle(new LineChart.LineStyle(2, 4));
    lc1.setDotStyle(null);
    lc1.setText("PoorEnterprises Pty");
    lc1.setColour("#ff0000");
    for (int t = 0; t < 30; t++) {
      lc1.addValues(Random.nextDouble() * .5 - .5);
    }
    LineChart lc2 = new LineChart();
    lc2.setDotStyle(new HollowDot());
    lc2.setColour("#009900");
    lc2.setText("Ave-Ridge Co LLC");
    for (int t = 0; t < 30; t++) {
      lc2.addValues(Random.nextDouble() * .8);
    }
    LineChart lc3 = new LineChart();
    lc3.setDotStyle(new Star());
    lc3.setColour("#0000ff");
    lc3.setText("Suu Perb Enterprises");
    for (int t = 0; t < 30; t++) {
      lc3.addValues(Random.nextDouble() * 1.1 + .5);
    }
    XAxis xa = new XAxis();
    xa.setSteps(2);
    cd.setXAxis(xa);

    YAxis ya = new YAxis();
    ya.setMax(2);
    ya.setMin(-1);
    cd.setYAxis(ya);

    cd.setXLegend(new Text("Annual performance over 30 years", "{font-size: 10px; color: #000000}"));

    cd.addElements(lc1);
    cd.addElements(lc2);
    cd.addElements(lc3);
    return cd;
  }
  
  private ChartData getSketchChartData() {
    ChartData cd2 = new ChartData("How many pies were eaten?", "font-size: 14px; font-family: Verdana; text-align: center;");
    cd2.setBackgroundColour("#ffffff");
    XAxis xa = new XAxis();
    xa.setLabels("John", "Frank", "Mary", "Andy", "Mike", "James");
    // xa.setMax(6);
    cd2.setXAxis(xa);
    SketchBarChart sketch = new SketchBarChart("#00aa00", "#009900", 6);
    sketch.setTooltip("#val# pies");
    sketch.addValues(Random.nextInt(6) + 1, Random.nextInt(5) + 1, Random.nextInt(3) + 1);
    SketchBarChart.SketchBar skb = new SketchBarChart.SketchBar(Random.nextInt(5) + 5);
    skb.setColour("#6666ff");
    skb.setTooltip("Winner!<br>#val# pies");
    sketch.addBars(skb);
    sketch.addValues(Random.nextInt(5) + 1, Random.nextInt(5) + 1);
    cd2.addElements(sketch);
    return cd2;
  }

  public void loadVisualizationApi() {
    
    Log.debug("loadVisualizationApi()");
    
    // Create a callback to be called when the visualization API has been loaded.
    Runnable onLoadCallback = new Runnable() {
      public void run() {
        
        Log.debug("onLoadCallback()");

        // pie = new PieChart(createTable(), createOptions());
        // RootPanel.get("chart_sibling_div").add(pie);
        // RootPanel.get("chart_nested_div").add(pie);
        
        Element div = DOM.getElementById("chart_nested_div");
        
        if (div != null) {
          Log.debug("DOM.getElementById(\"chart_nested_div\") - " + div.getId());
        }        
        
        // drawGoogleVisualizationChart();
      }
    };

    // Load the visualization api, passing the onLoadCallback to be called when loading is complete.
    VisualizationUtils.loadVisualizationApi("1.1", onLoadCallback, PieChart.PACKAGE);
  }  
  
  private native void drawGoogleVisualizationChart() /*-{
  
    // Create our data table.
    var dataTable = new $wnd.google.visualization.DataTable();
    
    dataTable.addColumn('string', 'Task');
    dataTable.addColumn('number', 'Hours per Day');
    dataTable.addRows(5);
    dataTable.setValue(0, 0, "Work");
    dataTable.setValue(0, 1, 11);
    dataTable.setValue(1, 0, "Eat");
    dataTable.setValue(1, 1, 2);
    dataTable.setValue(2, 0, "Commute");
    dataTable.setValue(2, 1, 2);
    dataTable.setValue(3, 0, "Watch TV");
    dataTable.setValue(3, 1, 2);
    dataTable.setValue(4, 0, "Sleep");
    dataTable.setValue(4, 1, 7);
    
    // Instantiate and draw our chart, passing in some options.
    // var chart = new $wnd.google.visualization.PieChart($doc.getElementById('chart_sibling_div'));
    var googleChart = new $wnd.google.visualization.PieChart($doc.getElementById('chart_nested_div'));
    googleChart.draw(dataTable, {width: 400, height: 240});

  }-*/;  
  
  /*
  
  private AbstractDataTable createTable() {
    DataTable data = DataTable.create();
    data.addColumn(ColumnType.STRING, "Task");
    data.addColumn(ColumnType.NUMBER, "Hours per Day");
    data.addRows(5);
    data.setValue(0, 0, "Work");
    data.setValue(0, 1, 11);
    data.setValue(1, 0, "Eat");
    data.setValue(1, 1, 2);
    data.setValue(2, 0, "Commute");
    data.setValue(2, 1, 2);
    data.setValue(3, 0, "Watch TV");
    data.setValue(3, 1, 2);
    data.setValue(4, 0, "Sleep");
    data.setValue(4, 1, 7);
    return data;
  }
  
  private PieOptions createOptions() {
    PieOptions options = PieChart.createPieOptions();
    options.setWidth(400);
    options.setHeight(240);
    options.set3D(true);
    options.setTitle("My Daily Activities");
    return options;
  }

*/