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
import au.com.uptick.serendipity.client.model.AccountsRecord;
import au.com.uptick.serendipity.client.sales.presenter.AccountsPresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.AccountsUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;
import au.com.uptick.serendipity.client.widgets.ToolBar;
import au.com.uptick.serendipity.shared.dto.sales.AccountsDto;

import com.google.inject.Inject;
import com.smartgwt.client.data.Record;
import com.smartgwt.client.util.BooleanCallback;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.grid.ListGridRecord;
import com.smartgwt.client.widgets.grid.events.RecordDoubleClickEvent;
import com.smartgwt.client.widgets.grid.events.RecordDoubleClickHandler;

public class AccountsView extends SalesViewWithUiHandlers<AccountsUiHandlers> implements
    AccountsPresenter.MyView {

  private String recordId;

  @Inject
  public AccountsView(ToolBar toolBar, AccountsContextAreaListGrid listGrid,
      StatusBar statusBar) {
    super(toolBar, listGrid, statusBar);

    recordId = new String("-1");
  }

  @Override
  protected void bindCustomUiHandlers() {
    super.bindCustomUiHandlers();

    // initialise the ToolBar and register its handlers
    initToolBar();

    // register the ListGird handlers
    getListGrid().addRecordDoubleClickHandler(new RecordDoubleClickHandler() {
      @Override
      public void onRecordDoubleClick(RecordDoubleClickEvent event) {
        Record record = event.getRecord();
        recordId = record.getAttributeAsString(AccountsRecord.ACCOUNT_ID);

        if (getUiHandlers() != null) {
          getUiHandlers().onRecordDoubleClicked(recordId);
        }
      }
    });

    // initialise the StatusBar and register its handlers
    initStatusBar();
  }

  public void setResultSet(List<AccountsDto> resultSet) {
    // resultSet == null when there are no items in table
    if (resultSet != null) {
      ((AccountsContextAreaListGrid) getListGrid()).setResultSet(resultSet);
    }
  }

  protected void initToolBar() {

    getToolBar().addButton(ToolBar.NEW_ACCOUNT_BUTTON, Serendipity.getConstants().newButton(),
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

    getToolBar().addButton(ToolBar.EXPORT_BUTTON,
        Serendipity.getConstants().exportButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onExportButtonClicked();
        }
      }
    });

    getToolBar().addButton(ToolBar.MAIL_MERGE_BUTTON,
        Serendipity.getConstants().mailMergeButtonTooltip(), null);
    getToolBar().addButton(ToolBar.REPORTS_BUTTON,
        Serendipity.getConstants().reportsButtonTooltip(), null);

    getToolBar().addSeparator();

    getToolBar().addButton(ToolBar.ASSIGN_BUTTON,
        Serendipity.getConstants().assignButtonTooltip(), null);

    getToolBar().addButton(ToolBar.DELETE_BUTTON,
        Serendipity.getConstants().deleteButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {

          ListGridRecord[] records = getListGrid().getSelection();

          if (records.length == 1) {
            String title = Serendipity.getConstants().accountWindowTitle() +
                records[0].getAttributeAsString(AccountsRecord.ACCOUNT_NAME);
            recordId = records[0].getAttributeAsString(AccountsRecord.ACCOUNT_ID);

            event.cancel();
            SC.ask(title, "Are you sure you want to delete this Account?", new BooleanCallback()
            {
              @Override
              public void execute(Boolean value) {
                if (value != null && value) { // Yes
                  getUiHandlers().onDeleteButtonClicked(recordId);
                }
              }
            });
          } else {
            getListGrid().deselectAllRecords();
          }
            }
          }
        }
      );

    getToolBar().addButton(ToolBar.EMAIL_BUTTON,
        Serendipity.getConstants().emailButtonTooltip(), null);

    getToolBar().addButton(ToolBar.WORKFLOW_BUTTON, Serendipity.getConstants().workflowButton(),
        Serendipity.getConstants().workflowButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onWorkflowButtonClicked();
        }
      }
    });

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

    // "0 of 50 selected"
    // statusBar.getSelectedLabel().setContents(Serendipity.getConstants().selectedLabel());

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

    // "Page 1"
    // statusBar.getPageNumberLabel().setContents(Serendipity.getConstants().pageNumberLabel());

    getStatusBar().getResultSetNextButton().addClickHandler(new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          getUiHandlers().onResultSetNextButtonClicked();
        }
      }
    });
  }
}

