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

/**
 * @author Rob Ferguson
 *
 */
public class ActivitiesRecord extends ListGridRecord {

  public static final String ICON = "icon";
  public static final String ICON_DISPLAY_NAME = "#";
  public static final String ACTIVITY_TYPE = "activityType";
  public static final String SUBJECT = "subject";
  public static final String REGARDING = "regarding";
  public static final String PRIORITY = "priority";
  public static final String START_DATE = "startDate";
  public static final String DUE_DATE = "dueDate";

  public ActivitiesRecord() { }

  public ActivitiesRecord(String icon,
      String activityType,
      String subject,
      String regarding,
      String priority,
      String startDate,
      String dueDate) {
    setIcon(icon);
    setActivityType(activityType);
    setSubject(subject);
    setRegarding(regarding);
    setPriority(priority);
    setStartDate(startDate);
    setDueDate(dueDate);
  }

  public void setIcon(String attribute) {
    setAttribute(ICON, attribute);
  }

  public void setActivityType(String attribute) {
    setAttribute(ACTIVITY_TYPE, attribute);
  }

  public void setSubject(String attribute) {
    setAttribute(SUBJECT, attribute);
  }

  public void setRegarding(String attribute) {
    setAttribute(REGARDING, attribute);
  }

  public void setPriority(String attribute) {
    setAttribute(PRIORITY, attribute);
  }

  public void setStartDate(String attribute) {
    setAttribute(START_DATE, attribute);
  }

  public void setDueDate(String attribute) {
    setAttribute(DUE_DATE, attribute);
  }

  public String getIcon() {
    return getAttributeAsString(ICON);
  }

  public String getActivityType() {
    return getAttributeAsString(ACTIVITY_TYPE);
  }

  public String getSubject() {
    return getAttributeAsString(SUBJECT);
  }

  public String getRegarding() {
    return getAttributeAsString(REGARDING);
  }

  public String getPriority() {
    return getAttributeAsString(PRIORITY);
  }

  public String getStartDate() {
    return getAttributeAsString(START_DATE);
  }

  public String getDueDate() {
    return getAttributeAsString(DUE_DATE);
  }
}
