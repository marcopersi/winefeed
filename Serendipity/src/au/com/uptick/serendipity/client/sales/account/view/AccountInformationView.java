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

package au.com.uptick.serendipity.client.sales.account.view;

import au.com.uptick.serendipity.client.MultiPageEntryPoint;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountInformationPresenter;
import au.com.uptick.serendipity.client.sales.account.presenter.AccountPagePresenter;
import au.com.uptick.serendipity.client.sales.account.view.handlers.AccountInformationUiHandlers;
import au.com.uptick.serendipity.client.sales.widgets.EntityTab;
import au.com.uptick.serendipity.client.sales.widgets.EntityToolBar;
import au.com.uptick.serendipity.client.widgets.ToolBar;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.ui.Widget;
import com.google.inject.Inject;
import com.gwtplatform.mvp.client.ViewWithUiHandlers;
import com.smartgwt.client.widgets.events.ClickEvent;
import com.smartgwt.client.widgets.events.ClickHandler;
import com.smartgwt.client.widgets.layout.VLayout;
import com.smartgwt.client.widgets.menu.events.MenuItemClickEvent;
import com.smartgwt.client.widgets.tab.Tab;
import com.smartgwt.client.widgets.tab.TabSet;

public class AccountInformationView extends ViewWithUiHandlers<AccountInformationUiHandlers>
    implements AccountInformationPresenter.MyView {

  private AccountDto accountDto;
  private EntityToolBar toolBar;

  private VLayout panel;
  private TabSet tabSet;

  @Inject
  public AccountInformationView() {

    Log.debug("AccountInformationView()");

    accountDto = null;
    toolBar = AccountPagePresenter.getToolBar();

    // initialise the Information View layout container
    panel = new VLayout();
    panel.setStyleName("crm-Entity-ContextArea");
    panel.setWidth100();

    tabSet = new TabSet();
    tabSet.addTab(new AccountInformationGeneralTab());

    panel.addMember(tabSet);

    bindCustomUiHandlers();
  }

  protected void bindCustomUiHandlers() {

    // initialise the ToolBar and register its handlers
    initToolBar();
  }

  protected void initToolBar() {

    Log.debug("initToolBar()");

    toolBar.addButton(ToolBar.SAVE_BUTTON,
        MultiPageEntryPoint.getConstants().saveButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (validateTabs()) {
          if (getUiHandlers() != null) {
            Log.debug("onSaveAndCloseButtonClicked()");
            getUiHandlers().onSaveButtonClicked(getFields());
          }
        }
      }
    });

    toolBar.addButton(ToolBar.SAVE_AND_CLOSE_BUTTON,
        MultiPageEntryPoint.getConstants().saveAndCloseButton(),
        MultiPageEntryPoint.getConstants().saveAndCloseButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (validateTabs()) {
          if (getUiHandlers() != null) {
            Log.debug("onSaveAndCloseButtonClicked()");
            getUiHandlers().onSaveAndCloseButtonClicked(getFields());
          }
        }
      }
    });

    toolBar.addButton(ToolBar.PRINT_PREVIEW_BUTTON,
        MultiPageEntryPoint.getConstants().printPreviewButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onPrintPreviewClicked();
        }
      }
    });

    toolBar.addSeparator();

    toolBar.addButton(ToolBar.EMAIL_BUTTON,
        MultiPageEntryPoint.getConstants().emailButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onEmailButtonClicked();
        }
      }
    });

    toolBar.addButton(ToolBar.ATTACH_BUTTON,
        MultiPageEntryPoint.getConstants().attachButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onAttachButtonClicked();
        }
      }
    });

    toolBar.addMenuButton(MultiPageEntryPoint.getConstants().reportsButton(),
        "Account Overview, Account Summary, Product By Account",
        new com.smartgwt.client.widgets.menu.events.ClickHandler() {
          public void onClick(MenuItemClickEvent event) {
            if (getUiHandlers() != null) {
              // getUiHandlers().onAttachButtonClicked();
            }
          }
        });

    /*

    toolBar.addButton(ToolBar.REPORTS_BUTTON,
        MultiPageEntryPoint.getConstants().reportsButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onReportsButtonClicked();
        }
      }
    });

    */

    toolBar.addSeparator();

    toolBar.addButton(ToolBar.HELP_BUTTON,
        MultiPageEntryPoint.getConstants().helpButtonTooltip(), new ClickHandler() {
      public void onClick(ClickEvent event) {
        if (getUiHandlers() != null) {
          // getUiHandlers().onHelpButtonClicked();
        }
      }
    });
  }

  @Override
  public Widget asWidget() {
    return panel;
  }

  public void setAccountId(Long accountId) {

    Log.debug("setAccountId() - accountId: " + accountId);

    if (accountDto != null) {
      accountDto.setAccountId(accountId);

      // set Masthead Account Name label and the browser window's title
      setMastheadAccountNameLabel(accountDto.getAccountName());
    }
  }

  public void setResultSet(AccountDto accountDto) {

    Log.debug("setServerResponse()");

    try {
      if (accountDto != null) {
        this.accountDto = accountDto;
        setFields(this.accountDto);
      }
    } catch (Exception e) {
      Log.warn("Unable to set server response: ", e);
    }
  }

  public void setFields(AccountDto accountDto) {

    Log.debug("setFields()");

    Tab[] tabs = tabSet.getTabs();

    for (Tab tab : tabs) {
      EntityTab entityTab = (EntityTab) tab;

      entityTab.setFields(accountDto);
    }

    // set Masthead Account Name label and the browser window's title
    setMastheadAccountNameLabel(accountDto.getAccountName());
  }

  public AccountDto getFields() {

    Log.debug("getFields()");

    if (accountDto == null) {
      accountDto = new AccountDto();
    }

    Tab[] tabs = tabSet.getTabs();

    for (Tab tab : tabs) {
      EntityTab entityTab = (EntityTab) tab;

      entityTab.getFields(accountDto);
    }

    return accountDto;
  }

  public Boolean validateTabs() {
    Boolean result = true;

    Tab[] tabs = tabSet.getTabs();

    for (Tab tab : tabs) {
      EntityTab entityTab = (EntityTab) tab;

      if (! entityTab.getForm().validate(false)) {
        result = false;
        break;
      }
    }

    return result;
  }

  private void setMastheadAccountNameLabel(String accountName) {

    Log.debug("setMastheadAccountNameLabel()");

    AccountPagePresenter.getMasthead().setAccountNameLabelContents(accountName +
        "<br /><b>Information</b>");

    // set the browser window's title e.g. "Account: ABC Corporation Pty Ltd"
    Window.setTitle(MultiPageEntryPoint.getConstants().accountWindowTitle() + accountName);
  }
}