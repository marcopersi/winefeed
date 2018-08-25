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

package au.com.uptick.serendipity.client.view;

import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.Widget;

import com.google.inject.Inject;

import com.gwtplatform.mvp.client.ViewWithUiHandlers;

import com.smartgwt.client.data.Record;
import com.smartgwt.client.widgets.grid.events.RecordClickEvent;
import com.smartgwt.client.widgets.grid.events.RecordClickHandler;
import com.smartgwt.client.widgets.layout.HLayout;
import com.smartgwt.client.widgets.layout.SectionStackSection;
import com.smartgwt.client.widgets.layout.VLayout;
import com.smartgwt.client.widgets.layout.events.SectionHeaderClickEvent;
import com.smartgwt.client.widgets.layout.events.SectionHeaderClickHandler;
import com.smartgwt.client.widgets.menu.Menu;

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.data.ResourceCentreNpsDataSource;
import au.com.uptick.serendipity.client.data.SalesNpsDataSource;
import au.com.uptick.serendipity.client.data.SettingsNpsDataSource;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.view.handlers.MainPageUiHandlers;
import au.com.uptick.serendipity.client.widgets.ApplicationMenu;
import au.com.uptick.serendipity.client.widgets.Masthead;
import au.com.uptick.serendipity.client.widgets.NavigationPane;
import au.com.uptick.serendipity.client.widgets.NavigationPaneHeader;
import au.com.uptick.serendipity.client.widgets.NavigationPaneSection;

import com.allen_sauer.gwt.log.client.Log;

/**
 * @author Rob Ferguson
 *
 */
public class MainPageView extends ViewWithUiHandlers<MainPageUiHandlers> implements
    MainPagePresenter.MyView {

  // NORTH_HEIGHT = MASTHEAD_HEIGHT + APPLICATION_MENU_HEIGHT + NAVIGATION_PANE_HEADER_HEIGHT
  private static final int NORTH_HEIGHT = 85;
  private static final int DEFAULT_MENU_WIDTH = 70;
  private static final String DEFAULT_MARGIN = "0px";

  private final Masthead masthead;
  private final ApplicationMenu applicationMenu;
  private final NavigationPaneHeader navigationPaneHeader;
  private final NavigationPane navigationPane;

  private VLayout panel;
  private HLayout northLayout;
  private HLayout southLayout;
  private VLayout westLayout;

  @Inject
  public MainPageView(Masthead masthead, ApplicationMenu applicationMenu,
      NavigationPaneHeader navigationPaneHeader, NavigationPane navigationPane) {
    this.masthead = masthead;
    this.applicationMenu = applicationMenu;
    this.navigationPaneHeader = navigationPaneHeader;
    this.navigationPane = navigationPane;

    // get rid of scroll bars, and clear out the window's built-in margin,
    // because we want to take advantage of the entire client area
    Window.enableScrolling(false);
    Window.setMargin(DEFAULT_MARGIN);

    // initialise the main layout container
    panel = new VLayout();
    panel.setWidth100();
    panel.setHeight100();

    // initialise the North layout container
    northLayout = new HLayout();
    northLayout.setHeight(NORTH_HEIGHT);

    // initApplicationMenu();

    // initialise the nested layout container
    VLayout vLayout = new VLayout();
    vLayout.addMember(this.masthead);
    vLayout.addMember(this.applicationMenu);
    vLayout.addMember(this.navigationPaneHeader);

    // add the nested layout container to the North layout container
    northLayout.addMember(vLayout);

    // initNavigationPane();

    // initialise the West layout container
    westLayout = this.navigationPane;

    // initialise the South layout container
    southLayout = new HLayout();

    // add the North and South layout containers to the main layout container
    panel.addMember(northLayout);
    panel.addMember(southLayout);

    bindCustomUiHandlers();
  }

  // as per NavigationPaneDataSource
  private static final String NAME = "name";

  /**
   * SmartGWT Event and GWT Handler Mapping should be done here.
   */
  protected void bindCustomUiHandlers() {

    // initialise the ToolBar and register its handlers
    initApplicationMenu();

    // initialise the NavigationPane and register its handlers
    initNavigationPane();
  }

  private void onRecordClicked(RecordClickEvent event) {
    Record record = event.getRecord();
    String place = record.getAttributeAsString(NAME);

    if (getUiHandlers() != null) {
      getUiHandlers().onNavigationPaneSectionClicked(place);
    }
  }

  @Override
  public Widget asWidget() {
    return panel;
  }

  @Override
  public void setInSlot(Object slot, Widget content) {
    Log.debug("setInSlot()");

    if (slot == MainPagePresenter.TYPE_SetContextAreaContent) {
      if (content != null) {
        southLayout.setMembers(westLayout, (VLayout) content);
      }
    } else {
      super.setInSlot(slot, content);
    }
  }

  @Override
  public void removeFromSlot(Object slot, Widget content) {
    super.removeFromSlot(slot, content);

    Log.debug("removeFromSlot()");
  }

  private void initApplicationMenu() {

    applicationMenu.addMenu(Serendipity.getConstants().newActivityMenuName(),
        DEFAULT_MENU_WIDTH, Serendipity.getConstants().newActivityMenuItemNames(),
        null);
    applicationMenu.addMenu(Serendipity.getConstants().newRecordMenuName(),
        DEFAULT_MENU_WIDTH, Serendipity.getConstants().newRecordMenuItemNames(),
        null);
    Menu goToMenu = applicationMenu.addMenu(Serendipity.getConstants().goToMenuName(),
        DEFAULT_MENU_WIDTH - 30);
    applicationMenu.addSubMenu(goToMenu, Serendipity.getConstants().salesMenuItemName(),
        Serendipity.getConstants().salesMenuItemNames(),
        null);
    applicationMenu.addSubMenu(goToMenu, Serendipity.getConstants().settingsMenuItemName(),
        Serendipity.getConstants().settingsMenuItemNames(),
        null);
    applicationMenu.addSubMenu(goToMenu, Serendipity.getConstants().resourceCentreMenuItemName(),
        Serendipity.getConstants().resourceCentreMenuItemNames(),
        null);
    applicationMenu.addMenu(Serendipity.getConstants().toolsMenuName(),
        DEFAULT_MENU_WIDTH - 30, Serendipity.getConstants().toolsMenuItemNames(),
        null);
    applicationMenu.addMenu(Serendipity.getConstants().helpMenuName(),
        DEFAULT_MENU_WIDTH - 30, Serendipity.getConstants().helpMenuItemNames(),
        null);
  }

  private void initNavigationPane() {

    navigationPane.addSection(Serendipity.getConstants().salesStackSectionName(),
        SalesNpsDataSource.getInstance());
    navigationPane.addSection(Serendipity.getConstants().settingsStackSectionName(),
        SettingsNpsDataSource.getInstance());
    navigationPane.addSection(Serendipity.getConstants().resourceCentreStackSectionName(),
        ResourceCentreNpsDataSource.getInstance());

    navigationPane.addSectionHeaderClickHandler(new SectionHeaderClickHandler() {
      @Override
      public void onSectionHeaderClick(SectionHeaderClickEvent event) {
        SectionStackSection section = event.getSection();
        String name = ((NavigationPaneSection) section).getSelectedRecord();

        // If there is no selected record (e.g. the data hasn't finished loading)
        // then getSelectedRecord() will return an empty string.
        if (name.isEmpty()) {
          if (section.getTitle().equals(Serendipity.getConstants().settingsStackSectionName())) {
            // default to the first item e.g. "Administration" in Settings
            name = SettingsNpsDataSource.DEFAULT_RECORD_NAME;
          } else if (section.getTitle().equals(Serendipity.getConstants().resourceCentreStackSectionName())) {
            // default to the first item e.g. "Highlights" in Resource Centre
            name = ResourceCentreNpsDataSource.DEFAULT_RECORD_NAME;
          }
        }

        if (getUiHandlers() != null) {
          getUiHandlers().onNavigationPaneSectionHeaderClicked(name);
        }
      }
    });

    navigationPane.addRecordClickHandler(Serendipity.getConstants().salesStackSectionName(),
        new RecordClickHandler() {
      @Override
      public void onRecordClick(RecordClickEvent event) {
        onRecordClicked(event);
      }
    });

    navigationPane.addRecordClickHandler(Serendipity.getConstants().settingsStackSectionName(),
        new RecordClickHandler() {
      @Override
      public void onRecordClick(RecordClickEvent event) {
        onRecordClicked(event);
      }
    });

    navigationPane.addRecordClickHandler(Serendipity.getConstants().resourceCentreStackSectionName(),
        new RecordClickHandler() {
      @Override
      public void onRecordClick(RecordClickEvent event) {
        onRecordClicked(event);
      }
    });
  }

  public ApplicationMenu getApplicationMenu() {
    return applicationMenu;
  }

  public NavigationPaneHeader getNavigationPaneHeader() {
    return navigationPaneHeader;
  }

  public NavigationPane getNavigationPane() {
    return navigationPane;
  }
}
