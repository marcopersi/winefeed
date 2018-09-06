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

import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;

public class EntityMasthead extends HLayout {

  private static final int MASTHEAD_HEIGHT = 40;

  private static final String WEST_WIDTH = "20%";
  private static final String EAST_WIDTH = "*";
  private static final String ACCOUNT_NAME_LABEL = "New Account<br /><b>Information</b>";

  private Label accountNameLabel;

  public EntityMasthead() {
    super();

    // Log.debug("Masthead()");

    // initialise the Masthead layout container
    this.setStyleName("crm-Entity-Masthead");
    this.setHeight(MASTHEAD_HEIGHT);

    // initialise the Logo image
    // Img logo = new Img("icons/48/account.png", 46, 46);
    // logo.addStyleName("crm-Entity-Masthead-Logo");

    // initialise the West layout container
    HLayout westLayout = new HLayout();
    westLayout.setHeight(MASTHEAD_HEIGHT);
    westLayout.setWidth(WEST_WIDTH);
    // westLayout.addMember(logo);

    // initialise the Account Name label
    accountNameLabel = new Label();
    accountNameLabel.setStyleName("crm-Entity-Masthead-Name");
    accountNameLabel.setContents(ACCOUNT_NAME_LABEL);
    accountNameLabel.setWidth("*");

    // initialise the East layout container
    HLayout eastLayout = new HLayout();
    eastLayout.setHeight(MASTHEAD_HEIGHT);
    eastLayout.setWidth(EAST_WIDTH);
    eastLayout.addMember(accountNameLabel);

    // add the West and East layout containers to the Masthead layout container
    this.addMember(westLayout);
    this.addMember(eastLayout);
  }

  public void setAccountNameLabelContents(String contents) {
    accountNameLabel.setContents(contents);
  }
}
