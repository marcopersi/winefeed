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

import java.util.List;

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.model.ReportsRecord;
import au.com.uptick.serendipity.shared.dto.sales.ReportsDto;

import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.ExpansionMode;
import com.smartgwt.client.types.ListGridFieldType;
import com.smartgwt.client.widgets.Canvas;
import com.smartgwt.client.widgets.grid.ListGridField;
import com.smartgwt.client.widgets.grid.ListGridRecord;

public class ReportsContextAreaListGrid extends SalesContextAreaListGrid {

  private static final String REPORT_ICON = "report";

  private static final int REPORT_NAME_COLUMN_WIDTH = 140;
  private static final int REPORT_TYPE_COLUMN_WIDTH = 120;
  private static final int MODIFIED_ON_COLUMN_WIDTH = 140;
  private static final int DESCRIPTION_COLUMN_WIDTH = 260;

  public ReportsContextAreaListGrid() {
    super();

    this.setCanExpandRecords(true);
    this.setExpansionMode(ExpansionMode.DETAIL_FIELD);
    this.setDetailField(ReportsRecord.REPORT_ID);

    // initialise the List Grid fields
    ListGridField iconField = new ListGridField(ReportsRecord.ICON,
        ReportsRecord.ICON_DISPLAY_NAME, ICON_COLUMN_WIDTH);
    iconField.setImageSize(16);
    iconField.setAlign(Alignment.CENTER);
    iconField.setType(ListGridFieldType.IMAGE);
    iconField.setImageURLPrefix(URL_PREFIX);
    iconField.setImageURLSuffix(URL_SUFFIX);

    ListGridField reportNameField = new ListGridField(ReportsRecord.REPORT_NAME,
        Serendipity.getConstants().reportName(), REPORT_NAME_COLUMN_WIDTH);

    ListGridField reportTypeField = new ListGridField(ReportsRecord.REPORT_TYPE,
        Serendipity.getConstants().reportType(), REPORT_TYPE_COLUMN_WIDTH);

    ListGridField modifiedOnField = new ListGridField(ReportsRecord.MODIFIED_ON,
        Serendipity.getConstants().modifiedOn(), MODIFIED_ON_COLUMN_WIDTH);

    ListGridField descriptionField = new ListGridField(ReportsRecord.DESCRIPTION,
        Serendipity.getConstants().description(), DESCRIPTION_COLUMN_WIDTH);

    ListGridField emptyField = new ListGridField(EMPTY_FIELD, EMPTY_FIELD_DISPLAY_NAME);

    // set the fields into the List Grid
    this.setFields(new ListGridField[] {iconField, reportNameField, reportTypeField, modifiedOnField,
        descriptionField, emptyField});

    // this.setCanEdit(true);
    // this.setEditEvent(ListGridEditEvent.CLICK);
    // this.setModalEditing(true);
  }

  // @Override
  protected Canvas getExpansionComponent(ListGridRecord record) {
    Canvas canvas = super.getExpansionComponent(record);
    canvas.setMargin(5);
    return canvas;
  }

  public void setResultSet(List<ReportsDto> reportsDtos) {

    ReportsRecord[] reportsRecords = new ReportsRecord[reportsDtos.size()];

    for (int i = 0; i < reportsDtos.size(); i++) {
      reportsRecords[i] = createReportsRecord(reportsDtos.get(i));
    }

    // populate the List Grid
    this.setData(reportsRecords);
  }

  private ReportsRecord createReportsRecord(ReportsDto reportsDto) {
    return new ReportsRecord(REPORT_ICON, reportsDto.getReportId(), reportsDto.getReportName(),
        reportsDto.getEntityName(), reportsDto.getReportFilename(), reportsDto.getReportType(),
        reportsDto.getModifiedOn(), reportsDto.getDescription());
  }
}

