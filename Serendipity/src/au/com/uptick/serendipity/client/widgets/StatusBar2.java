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

import au.com.uptick.serendipity.client.Serendipity;

import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.Overflow;
import com.smartgwt.client.widgets.Label;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.toolbar.ToolStrip;
import com.smartgwt.client.widgets.toolbar.ToolStripButton;

public class StatusBar2 extends HLayout {

  private static final String STATUSBAR_HEIGHT = "23px";
  public static final String TOOLSTRIP_WIDTH = "*";

  private final Label selectedLabel;

  protected final ToolStrip toolStrip;
  private final StatusBarToolStripButton resultSetFirstButton;
  private final StatusBarToolStripButton resultSetPreviousButton;
  private final ToolStripButton pageNumberLabel;
  private final StatusBarToolStripButton resultSetNextButton;

  public StatusBar2() {
    super();

    // initialise the StatusBar layout container
    this.setStyleName("crm-StatusBar");
    this.setHeight(STATUSBAR_HEIGHT);

    // initialise the Selected label
    selectedLabel = new Label();
    selectedLabel.setStyleName("crm-StatusBar-Label");
    selectedLabel.setContents(Serendipity.getMessages().selected(0, 50));
    selectedLabel.setAlign(Alignment.LEFT);
    selectedLabel.setOverflow(Overflow.HIDDEN);

    // initialise the StatusBar's ToolStrip
    toolStrip = new ToolStrip();
    toolStrip.setStyleName("crm-StatusBar-ToolStrip");
    toolStrip.setHeight(STATUSBAR_HEIGHT);
    toolStrip.setWidth(TOOLSTRIP_WIDTH);
    toolStrip.setAlign(Alignment.RIGHT);

    // initialise the Result Set First button
    resultSetFirstButton = new StatusBarToolStripButton();
    resultSetFirstButton.setIcon("statusbar/resultsetfirst.png");
    resultSetFirstButton.setShowRollOver(false);
    resultSetFirstButton.setShowDisabled(true);
    resultSetFirstButton.setShowDown(false);
    // requires resultsetfirst_Disabled.png
    resultSetFirstButton.disable();

    // initialise the Result Set Previous button
    resultSetPreviousButton = new StatusBarToolStripButton();
    resultSetPreviousButton.setIcon("statusbar/resultsetprevious.png");
    resultSetPreviousButton.setShowRollOver(false);
    resultSetPreviousButton.setShowDisabled(true);
    resultSetPreviousButton.setShowDown(false);
    // requires resultsetprevious_Disabled.png
    resultSetPreviousButton.disable();

    // initialise the Page Number label
    pageNumberLabel = new ToolStripButton();
    toolStrip.setStyleName("crm-StatusBar-PageNumberLabel");
    pageNumberLabel.setTitle(Serendipity.getMessages().page(1));
    pageNumberLabel.setShowRollOver(false);
    pageNumberLabel.setShowDisabled(false);
    pageNumberLabel.setShowDown(false);

    // initialise the Result Set Next button
    resultSetNextButton = new StatusBarToolStripButton();
    resultSetNextButton.setIcon("statusbar/resultsetnext.png");
    resultSetNextButton.setShowRollOver(false);
    resultSetNextButton.setShowDisabled(true);
    resultSetNextButton.setShowDown(false);
    // requires resultsetnext_Disabled.png

    // add the Selected label to the StatusBar
    this.addMember(selectedLabel);

    // add the buttons to the ToolStrip
    toolStrip.addMember(resultSetFirstButton);
    toolStrip.addMember(resultSetPreviousButton);
    toolStrip.addMember(pageNumberLabel);
    toolStrip.addMember(resultSetNextButton);

    // add the ToolStrip to the StatusBar
    this.addMember(toolStrip);
  }

  public Label getSelectedLabel() {
    return selectedLabel;
  }

  public StatusBarToolStripButton getResultSetFirstButton() {
    return resultSetFirstButton;
  }

  public StatusBarToolStripButton getResultSetPreviousButton() {
    return resultSetPreviousButton;
  }

  public ToolStripButton getPageNumberLabel() {
    return pageNumberLabel;
  }

  public StatusBarToolStripButton getResultSetNextButton() {
    return resultSetNextButton;
  }
}
