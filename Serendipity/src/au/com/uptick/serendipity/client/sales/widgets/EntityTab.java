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

package au.com.uptick.serendipity.client.sales.widgets;

import com.smartgwt.client.widgets.form.DynamicForm;
import com.smartgwt.client.widgets.tab.Tab;

public class EntityTab extends Tab {

  protected DynamicForm form;

  public EntityTab(String title) {
    super(title);

    this.setWidth(70);

    form = new DynamicForm();
    // generalForm.setWidth100();
    form.setMargin(2);
    form.setNumCols(4);
    form.setCellPadding(2);
    form.setAutoFocus(false);
    form.setWrapItemTitles(false);
    // no ":" after the field name
    form.setTitleSuffix(" ");
    form.setRequiredTitleSuffix(" ");
  }

  public DynamicForm getForm() {
    return form;
  }

  public void setFields(Object object) {
  }

  public void getFields(Object object) {
    // return null;
  }
}
