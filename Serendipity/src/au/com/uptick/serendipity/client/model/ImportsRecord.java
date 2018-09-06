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

package au.com.uptick.serendipity.client.model;

import com.smartgwt.client.widgets.grid.ListGridRecord;

public class ImportsRecord extends ListGridRecord {

  public static final String ICON = "icon";
  public static final String ICON_DISPLAY_NAME = "#";
  public static final String IMPORT_ID = "importId";
  public static final String IMPORT_NAME = "importName";
  // public static final String RECORD_TYPE = "recordType";
  public static final String ENTITY_NAME = "entityName";
  public static final String MAP = "map";
  public static final String DATA_FILENAME = "dataFilename";
  public static final String ASSIGN_TO = "assignTo";
  public static final String STATUS = "status";
  public static final String SUCCESSES = "successes";
  public static final String ERRORS = "errors";
  public static final String TOTAL = "total";
  public static final String CREATED_ON = "createdOn";

  public ImportsRecord() { }

  public ImportsRecord(String icon,
    Long importId,
    String importName) {
    setIcon(icon);
    setImportId(importId);
    setImportName(importName);
  }

  public void setIcon(String attribute) {
    setAttribute(ICON, attribute);
  }

  public void setImportId(Long attribute) {
    setAttribute(IMPORT_ID, attribute);
  }

  public void setImportName(String attribute) {
    setAttribute(IMPORT_NAME, attribute);
  }


  public String getIcon() {
    return getAttributeAsString(ICON);
  }

  public Long getImportId() {
    return (Long) getAttributeAsObject(IMPORT_ID);
  }

  public String getImportName() {
    return getAttributeAsString(IMPORT_NAME);
  }

}
