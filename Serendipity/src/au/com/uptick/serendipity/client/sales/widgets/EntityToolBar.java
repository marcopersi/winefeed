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

import com.smartgwt.client.widgets.Img;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.menu.Menu;
import com.smartgwt.client.widgets.menu.MenuItem;
import com.smartgwt.client.widgets.menu.MenuItemSeparator;
import com.smartgwt.client.widgets.toolbar.ToolStrip;
import com.smartgwt.client.widgets.toolbar.ToolStripButton;
import com.smartgwt.client.widgets.toolbar.ToolStripMenuButton;

import au.com.uptick.serendipity.client.widgets.ToolBar;

public class EntityToolBar extends HLayout {

  protected final ToolStrip toolStrip;

  public EntityToolBar() {
    super();

    // initialise the ToolBar layout container
    this.setStyleName("crm-Entity-ToolBar");
    this.setHeight(ToolBar.TOOLBAR_HEIGHT);

    // initialise the ToolBar's ToolStrip
    toolStrip = new ToolStrip();
    toolStrip.setStyleName("crm-Entity-ToolStrip");
    toolStrip.setHeight(ToolBar.TOOLBAR_HEIGHT);
    toolStrip.setWidth(ToolBar.TOOLSTRIP_WIDTH);

    Img logo = new Img("toolbar/logo.png", 48, 36);
    logo.setStyleName("crm-Entity-ToolBar-Logo");
    toolStrip.addChild(logo);

    // add the ToolStrip to the ToolBar's layout container
    this.addMember(toolStrip);
  }

  public ToolStripButton addButton(String icon, String tooltip, ClickHandler clickHandler) {
    ToolStripButton button = new ToolStripButton();
    button.setIcon(icon);
    button.setTooltip(tooltip);

    if (clickHandler != null)
      button.addClickHandler(clickHandler);

    toolStrip.addButton(button);

    return button;
  }

  public ToolStripButton addButton(String icon, String title, String tooltip, ClickHandler clickHandler) {
    ToolStripButton button = new ToolStripButton();
    button.setIcon(icon);
    button.setTitle(title);
    button.setTooltip(tooltip);

    if (clickHandler != null)
      button.addClickHandler(clickHandler);

    toolStrip.addButton(button);

    return button;
  }

  private static final int DEFAULT_SHADOW_DEPTH = 3;
  private static final String SEPARATOR = "separator";

  public ToolStripMenuButton addMenuButton(String title, String menuItemNames,
      com.smartgwt.client.widgets.menu.events.ClickHandler clickHandler) {

    ToolStripMenuButton button = new ToolStripMenuButton(title, addMenu(menuItemNames, clickHandler));
    // button.setWidth(100);

    toolStrip.addMenuButton(button);

    return button;
  }

  public Menu addMenu(String menuItemNames,
      com.smartgwt.client.widgets.menu.events.ClickHandler clickHandler) {

    // initialise the new menu
    Menu menu = new Menu();
    // menu.setTitle(menuName);
    menu.setShowShadow(true);
    menu.setShadowDepth(DEFAULT_SHADOW_DEPTH);
    // menu.setWidth(width);

    // create an array of menu item names
    String[] menuItems = process(menuItemNames);

    for (int i = 0; i < menuItems.length; i++) {
      // remove any whitespace
      String menuItemName = menuItems[i].replaceAll("\\W", "");

      if (menuItemName.contentEquals(SEPARATOR)) {
        MenuItemSeparator separator = new MenuItemSeparator();
        menu.addItem(separator);
        continue;
      }

      MenuItem menuItem = new MenuItem(menuItems[i]);
      if (clickHandler != null) {
        menuItem.addClickHandler(clickHandler);
      }

      menu.addItem(menuItem);
    }

    return menu;
  }

  public static final String DELIMITER = ",";

  public static String[] process(String line) {
    return line.split(DELIMITER);
  }

  public void addSeparator() {
    toolStrip.addSeparator();
  }
}
