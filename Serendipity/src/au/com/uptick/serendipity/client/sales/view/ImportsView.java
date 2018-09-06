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

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.sales.presenter.ImportsPresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.ImportsUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;
import au.com.uptick.serendipity.client.widgets.ToolBar;

import com.google.inject.Inject;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.grid.events.RecordDoubleClickEvent;
import com.smartgwt.client.widgets.grid.events.RecordDoubleClickHandler;

public class ImportsView extends SalesViewWithUiHandlers<ImportsUiHandlers> implements
    ImportsPresenter.MyView {


  @Inject
  public ImportsView(ToolBar toolBar, ImportsContextAreaListGrid listGrid,
      StatusBar statusBar) {
    super(toolBar, listGrid, statusBar);
  }

  protected void bindCustomUiHandlers() {
    super.bindCustomUiHandlers();

    // initialise the ToolBar and register its handlers
    initToolBar();

    // register the ListGird handlers
    getListGrid().addRecordDoubleClickHandler(new RecordDoubleClickHandler() {
      @Override
      public void onRecordDoubleClick(RecordDoubleClickEvent event) {
      }
    });

    // initialise the StatusBar and register its handlers
    initStatusBar();
  }

  protected void initToolBar() {

    getToolBar().addButton(ToolBar.NEW_IMPORT_BUTTON, Serendipity.getConstants().newButton(),
        Serendipity.getConstants().newButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onNewButtonClicked();
        }
      }
    });

    getToolBar().addSeparator();

    getToolBar().addButton(ToolBar.PRINT_PREVIEW_BUTTON,
        Serendipity.getConstants().printPreviewButtonTooltip(), null);
    getToolBar().addButton(ToolBar.ASSIGN_BUTTON,
        Serendipity.getConstants().assignButtonTooltip(), null);
    getToolBar().addButton(ToolBar.DELETE_BUTTON,
        Serendipity.getConstants().deleteButtonTooltip(), null);

    getToolBar().addSeparator();

    getToolBar().addButton(ToolBar.REFRESH_BUTTON,
        Serendipity.getConstants().refreshButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onRefreshButtonClicked();
        }
      }
    });
  }

  protected void initStatusBar() {

    getStatusBar().getResultSetFirstButton().addClickHandler(new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onResultSetFirstButtonClicked();
        }
      }
    });

    getStatusBar().getResultSetPreviousButton().addClickHandler(new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onResultSetPreviousButtonClicked();
        }
      }
    });

    getStatusBar().getResultSetNextButton().addClickHandler(new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onResultSetNextButtonClicked();
        }
      }
    });
  }
}

