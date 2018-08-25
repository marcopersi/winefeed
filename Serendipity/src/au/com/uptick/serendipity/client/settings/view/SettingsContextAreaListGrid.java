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

package au.com.uptick.serendipity.client.settings.view;

import au.com.uptick.serendipity.client.data.ContextAreaDataSource;

import com.allen_sauer.gwt.log.client.Log;
import com.smartgwt.client.data.DataSource;
import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.ListGridFieldType;
import com.smartgwt.client.widgets.grid.ListGrid;
import com.smartgwt.client.widgets.grid.ListGridField;
import com.smartgwt.client.widgets.grid.events.DataArrivedEvent;
import com.smartgwt.client.widgets.grid.events.DataArrivedHandler;

public class SettingsContextAreaListGrid extends ListGrid {
  
  private static final String URL_PREFIX = "icons/48/";   
  private static final String URL_SUFFIX = ".png";   
  
  private static final int ICON_FIELD_WIDTH = 80;
  
  private static final int CELL_HEIGHT = 66;  // 56  
  private static final int IMAGE_SIZE = 48;  

  public SettingsContextAreaListGrid(DataSource dataSource) {
    super();

    // initialise the List Grid
    this.setBaseStyle("crm-ContextAreaFeatureCell"); 
    this.setDataSource(dataSource); 
    // this.setWidth100();  
    // this.setHeight100();  
    this.setShowAllRecords(true);    
    this.setWrapCells(true);  
    this.setCellHeight(CELL_HEIGHT);  

    // hide the column header
    this.setShowHeader(false);
            
    // feature 1 icon field
    ListGridField featureIcon1Field = new ListGridField(ContextAreaDataSource.COLUMN1_ICON, 
        ContextAreaDataSource.COLUMN1_ICON_DISPLAY_NAME, ICON_FIELD_WIDTH);  
    featureIcon1Field.setImageSize(IMAGE_SIZE); 
    featureIcon1Field.setAlign(Alignment.CENTER);
    featureIcon1Field.setType(ListGridFieldType.IMAGE);  
    featureIcon1Field.setImageURLPrefix(URL_PREFIX);  
    featureIcon1Field.setImageURLSuffix(URL_SUFFIX);  
    featureIcon1Field.setCanEdit(false);  
          
    // feature 1 description
    ListGridField featureDescription1Field = new ListGridField(ContextAreaDataSource.COLUMN1_DESCRIPTION,
        ContextAreaDataSource.COLUMN1_DESCRIPTION_DISPLAY_NAME);
    // TO DO - find out how to align top ???
    // featureDescription1Field.setAlign(top);
        
    // feature 2 icon field
    ListGridField featureIcon2Field = new ListGridField(ContextAreaDataSource.COLUMN2_ICON, 
        ContextAreaDataSource.COLUMN2_ICON_DISPLAY_NAME, ICON_FIELD_WIDTH);  
    featureIcon2Field.setImageSize(IMAGE_SIZE); 
    featureIcon2Field.setAlign(Alignment.CENTER);
    featureIcon2Field.setType(ListGridFieldType.IMAGE);  
    featureIcon2Field.setImageURLPrefix(URL_PREFIX);  
    featureIcon2Field.setImageURLSuffix(URL_SUFFIX);  
    featureIcon2Field.setCanEdit(false);  
          
    // feature 2 description
    ListGridField featureDescription2Field = new ListGridField(ContextAreaDataSource.COLUMN2_DESCRIPTION,
        ContextAreaDataSource.COLUMN2_DESCRIPTION_DISPLAY_NAME);  
            
    // add the fields to the list grid
    this.setFields(new ListGridField[] {featureIcon1Field, featureDescription1Field, featureIcon2Field, featureDescription2Field});
    
    // register the Data Arrived Handler
    this.addDataArrivedHandler(new DataArrivedHandler() {
      @Override
      public void onDataArrived(DataArrivedEvent event) {
        Log.debug("onDataArrived()"); 
      }
    });       

    // populate the List Grid
    this.setAutoFetchData(true);
  }
}
