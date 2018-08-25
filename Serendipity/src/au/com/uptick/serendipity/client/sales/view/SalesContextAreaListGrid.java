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

import com.smartgwt.client.widgets.grid.ListGrid;

public class SalesContextAreaListGrid extends ListGrid {

  public static final String EMPTY_FIELD = "emptyField";
  public static final String EMPTY_FIELD_DISPLAY_NAME = " ";
  public static final String URL_PREFIX = "icons/16/";
  public static final String URL_SUFFIX = ".png";

  public static final int ICON_COLUMN_WIDTH = 20; // 27

  public SalesContextAreaListGrid() {
    super();

    // initialise the List Grid
    // this.setBaseStyle("crm-ContextArea-GridCell");
    this.setShowAllRecords(true);
    // this.setSortField(1);

    // show the List Grid filter editor
    // this.setShowFilterEditor(true);
    // this.setFilterOnKeypress(true);
  }
}
