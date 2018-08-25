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

public class ReportsRecord extends ListGridRecord {

  public static final String ICON = "icon";
  public static final String ICON_DISPLAY_NAME = "#";
  public static final String REPORT_ID = "reportId";
  public static final String REPORT_NAME = "reportName";
  public static final String ENTITY_NAME = "entityName";
  public static final String REPORT_FILENAME = "reportFilename";
  public static final String REPORT_TYPE = "reportType";
  public static final String MODIFIED_ON = "modifiedOn";
  public static final String DESCRIPTION = "description";

  public ReportsRecord() { }

  public ReportsRecord(String icon,
      Long reportId,
      String reportName,
      String entityName,
      String reportFilename,
      String reportType,
      String modifiedOn,
      String description) {
    setIcon(icon);
    setReportId(reportId);
    setReportName(reportName);
    setReportFilename(reportFilename);
    setReportType(reportType);
    setModifiedOn(modifiedOn);
    setDescription(description);
  }

  public void setIcon(String attribute) {
    setAttribute(ICON, attribute);
  }

  public void setReportId(Long attribute) {
    setAttribute(REPORT_ID, attribute);
  }

  public void setReportName(String attribute) {
    setAttribute(REPORT_NAME, attribute);
  }

  public void setEntityName(String attribute) {
    setAttribute(ENTITY_NAME, attribute);
  }

  public void setReportFilename(String attribute) {
    setAttribute(REPORT_FILENAME, attribute);
  }

  public void setReportType(String attribute) {
    setAttribute(REPORT_TYPE, attribute);
  }

  public void setModifiedOn(String attribute) {
    setAttribute(MODIFIED_ON, attribute);
  }

  public void setDescription(String attribute) {
    setAttribute(DESCRIPTION, attribute);
  }

  public String getIcon() {
    return getAttributeAsString(ICON);
  }

  public Long getReportId() {
    return (Long) getAttributeAsObject(REPORT_ID);
  }

  public String getReportName() {
    return getAttributeAsString(REPORT_NAME);
  }

  public String getEntityName() {
    return getAttributeAsString(ENTITY_NAME);
  }

  public String getReportFilename() {
    return getAttributeAsString(REPORT_FILENAME);
  }

  public String getReportType() {
    return getAttributeAsString(REPORT_TYPE);
  }

  public String getModifiedOn() {
    return getAttributeAsString(MODIFIED_ON);
  }

  public String getDescription() {
    return getAttributeAsString(DESCRIPTION);
  }
}
