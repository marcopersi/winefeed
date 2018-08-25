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

package au.com.uptick.serendipity.client.widgets;

import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.widgets.Img;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;

public class Masthead extends HLayout {

  private static final int MASTHEAD_HEIGHT = 58;
  private static final int IMAGE_SIZE = 48;

  private static final String WEST_WIDTH = "50%";
  private static final String EAST_WIDTH = "50%";
  private static final String LOGO = "logo.png";
  private static final String NAME_LABEL = "Serendipity";
  private static final String SIGNED_IN_USER_LABEL = "<b>Administrator</b><br />upTick";

  public Masthead() {
    super();

    // Log.debug("Masthead()");

    // initialise the Masthead layout container
    this.setStyleName("crm-Masthead");
    this.setHeight(MASTHEAD_HEIGHT);

    // initialise the Logo image
    Img logo = new Img(LOGO, IMAGE_SIZE, IMAGE_SIZE);
    logo.setStyleName("crm-Masthead-Logo");

    // initialise the Name label
    Label name = new Label();
    name.setStyleName("crm-Masthead-Name");
    name.setContents(NAME_LABEL);

    // initialise the West layout container
    HLayout westLayout = new HLayout();
    westLayout.setHeight(MASTHEAD_HEIGHT);
    westLayout.setWidth(WEST_WIDTH);
    westLayout.addMember(logo);
    westLayout.addMember(name);

    // initialise the Signed In User label
    Label signedInUser = new Label();
    signedInUser.setStyleName("crm-Masthead-SignedInUser");
    signedInUser.setContents(SIGNED_IN_USER_LABEL);

    // initialise the East layout container
    HLayout eastLayout = new HLayout();
    eastLayout.setAlign(Alignment.RIGHT);
    eastLayout.setHeight(MASTHEAD_HEIGHT);
    eastLayout.setWidth(EAST_WIDTH);
    eastLayout.addMember(signedInUser);

    // add the West and East layout containers to the Masthead layout container
    this.addMember(westLayout);
    this.addMember(eastLayout);
  }
}

/*

  // initialise the Signed In Organisation label
  Label signedInOrganisation = new Label();
  signedInOrganisation.addStyleName("crm-MastHead-SignedInOrganisation");
  signedInOrganisation.setContents("upTick");

*/
