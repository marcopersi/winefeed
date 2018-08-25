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

import java.util.Date;

import com.google.gwt.user.client.ui.Widget;
import com.google.inject.Inject;

import com.gwtplatform.mvp.client.ViewImpl;

import com.smartgwt.client.data.DataSource;
import com.smartgwt.client.data.fields.DataSourceDateField;
import com.smartgwt.client.data.fields.DataSourceSequenceField;
import com.smartgwt.client.data.fields.DataSourceTextField;
import com.smartgwt.client.widgets.calendar.Calendar;
import com.smartgwt.client.widgets.calendar.CalendarEvent;
import com.smartgwt.client.widgets.layout.LayoutSpacer;
import com.smartgwt.client.widgets.layout.VLayout;

import com.allen_sauer.gwt.log.client.Log;

import au.com.uptick.serendipity.client.sales.presenter.CalendarPresenter;

public class CalendarView extends ViewImpl implements CalendarPresenter.MyView {
  
  private static final String CONTEXT_AREA_WIDTH = "*";  
 
  private VLayout panel; 
  
  @Inject
  public CalendarView() {
    
    Log.debug("CalendarView()");   
    
    panel = new VLayout();
    
    // initialise the Calendar View layout container
    panel.setStyleName("crm-ContextArea");
    panel.setWidth(CONTEXT_AREA_WIDTH);  
  
    DataSource eventDS = new DataSource();  
    DataSourceSequenceField eventIdField = new DataSourceSequenceField("eventId");  
    eventIdField.setPrimaryKey(true);  
     
    DataSourceTextField nameField = new DataSourceTextField("name");  
    DataSourceTextField descField = new DataSourceTextField("description");  
    DataSourceDateField startDateField = new DataSourceDateField("startDate");  
    DataSourceDateField endDateField = new DataSourceDateField("endDate");  
     
    eventDS.setFields(eventIdField, nameField, descField, startDateField, endDateField);  
    eventDS.setClientOnly(true);  
    eventDS.setTestData(CalendarData.getRecords());  
     
    Calendar calendar = new Calendar();  
    calendar.setShowWeekends(false);  
    calendar.setShowWorkday(true);  
    calendar.setScrollToWorkday(true);  
    calendar.setDataSource(eventDS);  
    calendar.setAutoFetchData(true);  
  
    LayoutSpacer paddingTop = new LayoutSpacer(); 
    paddingTop.setHeight(8);
  
    panel.addMember(paddingTop);
    panel.addMember(calendar);    
  }

  @Override
  public Widget asWidget() {
    return panel;
  }
  
  @SuppressWarnings("deprecation")
  public static class CalendarData {  
   
    private static CalendarEvent[] records;  
    private static Date today = new Date();  
    private static int year = today.getYear();  
    private static int month = today.getMonth();  
    private static int start = today.getDate() - today.getDay();  
     
    public static CalendarEvent[] getRecords() {  
      if (records == null) {  
        records = getNewRecords();  
      }  
      return records;  
    }  
     
  // @SuppressWarnings("deprecation")
  public static CalendarEvent[] getNewRecords() {  
    return new CalendarEvent[] {  
        new CalendarEvent(1, "Meeting", "Shareholders meeting: monthly forecast report", new Date(year, month, start + 2, 9, 0, 0), new Date(year, month, start + 2, 14, 0, 0)),  
        new CalendarEvent(2, "Realtor", "Breakfast with realtor to discuss moving plans", new Date(year, month, start + 3, 8, 0, 0), new Date(year, month, start + 3, 10, 0, 0)),  
        new CalendarEvent(3, "Soccer", "Little league soccer finals", new Date(year, month, start + 4, 13, 0, 0), new Date(year, month, start + 4, 16, 0, 0)),  
        new CalendarEvent(4, "Sleep", "Catch up on sleep", new Date(year, month, start + 4, 5, 0, 0), new Date(year, month, start + 4, 9, 0, 0)),  
        new CalendarEvent(5, "Inspection", "Home inspector coming", new Date(year, month, start + 4, 10, 0, 0), new Date(year, month, start + 4, 12, 0, 0), false, "testStyle"),  
        new CalendarEvent(6, "Airport run", "Pick James up from the airport", new Date(year, month, start + 4, 1, 0, 0), new Date(year, month, start + 4, 3, 0, 0)),  
        new CalendarEvent(7, "Dinner Party", "Prepare elaborate meal for friends", new Date(year, month, start + 4, 17, 0, 0), new Date(year, month, start + 4, 20, 0, 0)),  
        new CalendarEvent(8, "Poker", "Poker at Steve's house", new Date(year, month, start + 4, 21, 0, 0), new Date(year, month, start + 4, 23, 0, 0)),  
        new CalendarEvent(9, "Meeting", "Board of directors meeting: discussion of next months strategy", new Date(year, month, start + 5, 11, 0, 0), new Date(year, month, start + 5, 15, 0, 0))  
      };  
    } 
  }  
}
