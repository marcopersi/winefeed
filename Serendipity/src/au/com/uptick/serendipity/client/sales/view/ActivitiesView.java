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

import com.google.gwt.user.client.ui.Widget;
import com.google.inject.Inject;

import com.gwtplatform.mvp.client.ViewWithUiHandlers;

import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.layout.VLayout;

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.model.ActivityData;
import au.com.uptick.serendipity.client.sales.presenter.ActivitiesPresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.ActivitiesUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;
import au.com.uptick.serendipity.client.widgets.ToolBar;

public class ActivitiesView extends ViewWithUiHandlers<ActivitiesUiHandlers> implements
    ActivitiesPresenter.MyView {

  private static final String CONTEXT_AREA_WIDTH = "*";

  private final ToolBar toolBar;
  private final ActivitiesContextAreaListGrid listGrid;
  private final StatusBar statusBar;

  private VLayout panel;

  @Inject
  public ActivitiesView(ToolBar toolbar, ActivitiesContextAreaListGrid listGrid,
      StatusBar statusBar) {
    super();

    // Log.debug("ActivitiesView()");

    this.toolBar = toolbar;
    this.listGrid = listGrid;
    this.statusBar = statusBar;

    panel = new VLayout();

    // initialise the Activities View layout container
    panel.setStyleName("crm-ContextArea");
    panel.setWidth(CONTEXT_AREA_WIDTH);

    // add the Tool Bar, List Grid, and Status Bar to the Activities View layout container
    panel.addMember(this.toolBar);
    panel.addMember(this.listGrid);
    panel.addMember(this.statusBar);

    bindCustomUiHandlers();
  }

  protected void bindCustomUiHandlers() {

    // initialise the ToolBar and register its handlers
    initToolBar();
  }

  @Override
  public Widget asWidget() {
    return panel;
  }

  // TO DO:
  public void setServerResponse() {
    listGrid.setData(ActivityData.getRecords());
  }

  protected void initToolBar() {

    toolBar.addButton(ToolBar.NEW_ACTIVITY_BUTTON, Serendipity.getConstants().newButton(),
        Serendipity.getConstants().newButtonTooltip(), new ClickHandler() {
    public void onClick(ClickEvent event) {
      if (getUiHandlers() != null) {
        getUiHandlers().onNewButtonClicked();
      }
      }}
    );

    toolBar.addSeparator();

    toolBar.addButton(ToolBar.PRINT_PREVIEW_BUTTON,
        Serendipity.getConstants().printPreviewButtonTooltip(), null);
    toolBar.addButton(ToolBar.EXPORT_BUTTON,
        Serendipity.getConstants().exportButtonTooltip(), null);
    // toolBar.addButton(ToolBar.MAIL_MERGE_BUTTON,
    //     Serendipity.getConstants().MailMergeButtonTooltip(), null);
    toolBar.addButton(ToolBar.REPORTS_BUTTON,
        Serendipity.getConstants().reportsButtonTooltip(), null);

    toolBar.addSeparator();

    toolBar.addButton(ToolBar.ASSIGN_BUTTON,
        Serendipity.getConstants().assignButtonTooltip(), null);

    toolBar.addButton(ToolBar.DELETE_BUTTON,
        Serendipity.getConstants().deleteButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onDeleteButtonClicked();
        }
      }}
    );

    // toolBar.addButton(ToolBar.EMAIL_BUTTON,
    //     Serendipity.getConstants().EmailButtonTooltip(), null);

    toolBar.addSeparator();

    toolBar.addButton(ToolBar.REFRESH_BUTTON,
        Serendipity.getConstants().refreshButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
      if (getUiHandlers() != null) {
        // getUiHandlers().onRefreshButtonClicked();
      }
      }}
    );
  }
}
