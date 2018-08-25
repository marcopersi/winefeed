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

import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.ExpansionMode;
import com.smartgwt.client.types.ListGridFieldType;
import com.smartgwt.client.widgets.grid.ListGridField;

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.model.ActivitiesRecord;
import au.com.uptick.serendipity.client.model.ActivityData;

public class ActivitiesContextAreaListGrid extends SalesContextAreaListGrid {

  private static final int ACTIVITY_TYPE_COLUMN_WIDTH = 90;
  private static final int SUBJECT_COLUMN_WIDTH = 130;
  private static final int REGARDING_COLUMN_WIDTH = 100;
  private static final int PRIORITY_COLUMN_WIDTH = 60;
  private static final int START_DATE_COLUMN_WIDTH = 80;
  private static final int DUE_DATE_COLUMN_WIDTH = 80;

  public ActivitiesContextAreaListGrid() {
    super();

    this.setCanExpandRecords(true);
    this.setExpansionMode(ExpansionMode.DETAIL_FIELD);
    this.setDetailField(ActivitiesRecord.ACTIVITY_TYPE);

    // initialise the List Grid fields
    ListGridField iconField = new ListGridField(ActivitiesRecord.ICON,
        ActivitiesRecord.ICON_DISPLAY_NAME, ICON_COLUMN_WIDTH);
    iconField.setImageSize(16);
    iconField.setAlign(Alignment.CENTER);
    iconField.setType(ListGridFieldType.IMAGE);
    iconField.setImageURLPrefix(URL_PREFIX);
    iconField.setImageURLSuffix(URL_SUFFIX);

    ListGridField activityTypeField = new ListGridField(ActivitiesRecord.ACTIVITY_TYPE,
        Serendipity.getConstants().activityType(), ACTIVITY_TYPE_COLUMN_WIDTH);

    ListGridField subjectField = new ListGridField(ActivitiesRecord.SUBJECT,
        Serendipity.getConstants().subject(), SUBJECT_COLUMN_WIDTH);

    ListGridField regardingField = new ListGridField(ActivitiesRecord.REGARDING,
        Serendipity.getConstants().regarding(), REGARDING_COLUMN_WIDTH);

    ListGridField priorityField = new ListGridField(ActivitiesRecord.PRIORITY,
        Serendipity.getConstants().priority(), PRIORITY_COLUMN_WIDTH);

    ListGridField startDateField = new ListGridField(ActivitiesRecord.START_DATE,
        Serendipity.getConstants().startDate(), START_DATE_COLUMN_WIDTH);

    ListGridField dueDateField = new ListGridField(ActivitiesRecord.DUE_DATE,
        Serendipity.getConstants().dueDate(), DUE_DATE_COLUMN_WIDTH);

    ListGridField emptyField = new ListGridField(EMPTY_FIELD, EMPTY_FIELD_DISPLAY_NAME);

    // set the fields into the List Grid
    this.setFields(new ListGridField[] {iconField, activityTypeField, subjectField, regardingField,
        priorityField, startDateField, dueDateField, emptyField });

    // populate the List Grid
    this.setData(ActivityData.getRecords());
  }
}
