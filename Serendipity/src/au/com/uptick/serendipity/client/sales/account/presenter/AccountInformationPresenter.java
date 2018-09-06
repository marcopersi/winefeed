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

package au.com.uptick.serendipity.client.sales.account.presenter;

import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.model.AccountsRecord;
import au.com.uptick.serendipity.client.sales.account.view.handlers.AccountInformationUiHandlers;
import au.com.uptick.serendipity.shared.action.CreateAccountAction;
import au.com.uptick.serendipity.shared.action.CreateAccountResult;
import au.com.uptick.serendipity.shared.action.RetrieveAccountAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountResult;
import au.com.uptick.serendipity.shared.action.UpdateAccountAction;
import au.com.uptick.serendipity.shared.action.UpdateAccountResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.rpc.AsyncCallback;
import com.google.inject.Inject;
import com.gwtplatform.dispatch.client.DispatchAsync;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyCodeSplit;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealContentEvent;

public class AccountInformationPresenter extends
    Presenter<AccountInformationPresenter.MyView, AccountInformationPresenter.MyProxy> implements
    AccountInformationUiHandlers {

  private final DispatchAsync dispatcher;

  private String activity;
  private String accountId;

  @ProxyCodeSplit
  @NameToken(NameTokens.accountInformation)
  // @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<AccountInformationPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<AccountInformationUiHandlers> {
    void setResultSet(AccountDto account);
    void setAccountId(Long accountId);
  }

  @Inject
  public AccountInformationPresenter(EventBus eventBus, MyView view, MyProxy proxy,
      PlaceManager placeManager, DispatchAsync dispatcher) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);

    this.dispatcher = dispatcher;
  }

  // public static native String encodeBase64(String string) /*-{ return $wnd.btoa(string); }-*/;

  public static native String decodeBase64(String string) /*-{ return $wnd.atob(string); }-*/;

  private static final String ACTIVITY = "activity";
  // private static final String DEFAULT_ACTIVITY = "edit";
  private static final String EDIT = "edit";
  // private static final String NEW = "new";

  @Override
  protected void onBind() {
    super.onBind();

    Log.debug("onBind()");

    // activity = Window.Location.getParameter(ACTIVITY);
    // accountId = Window.Location.getParameter(AccountsRecord.ACCOUNT_ID);

    activity = decodeBase64(Window.Location.getParameter(ACTIVITY));
    accountId = decodeBase64(Window.Location.getParameter(AccountsRecord.ACCOUNT_ID));

    if (activity.equals(EDIT)) {
      Long id = -1L;

      try {
        id = Long.valueOf(accountId);
      }
      catch (NumberFormatException nfe) {
        Log.debug("NumberFormatException: " + nfe.getLocalizedMessage());
        return;
      }

      try {
        retrieveAccount(id);
      }
      catch (Exception e) {
        Log.warn("Unable to retrieve account: ", e);
      }
    }
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    Log.debug("onReveal() - " + NameTokens.accountInformation);

    AccountPagePresenter.getNavigationPane().selectRecord(NameTokens.accountInformation);
  }

  @Override
  protected void onReset() {
    super.onReset();

    Log.debug("onReset()");
  }

  @Override
  protected void revealInParent() {
    RevealContentEvent.fire(this, AccountPagePresenter.TYPE_SetContextAreaContent, this);
  }

  public void onSaveButtonClicked(AccountDto accountDto) {
    createOrUpdateAccount(accountDto);
  }

  public static native void close() /*-{ $wnd.close(); }-*/;

  public void onSaveAndCloseButtonClicked(AccountDto accountDto) {
    createOrUpdateAccount(accountDto);
    close();
  }

  public void createOrUpdateAccount(AccountDto accountDto) {

    if (accountDto.getAccountId() == -1) {
      createAccount(accountDto);
    } else {
      updateAccount(accountDto);
    }
  }

  public void createAccount(AccountDto accountDto) {

    dispatcher.execute(new CreateAccountAction(accountDto),
        new AsyncCallback<CreateAccountResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(CreateAccountResult result) {
        Log.debug("onSuccess() - accountId: " + result.getAccountId());
        getView().setAccountId(result.getAccountId());
      }
    });
  }

  public void updateAccount(AccountDto accountDto) {

    dispatcher.execute(new UpdateAccountAction(accountDto),
        new AsyncCallback<UpdateAccountResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(UpdateAccountResult result) {
        Log.debug("onSuccess()");
      }
    });
  }

  protected void retrieveAccount(Long accountId) {

    Log.debug("retrieveAccount()");

    dispatcher.execute(new RetrieveAccountAction(accountId),
        new AsyncCallback<RetrieveAccountResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(RetrieveAccountResult result) {
        Log.debug("onSuccess()");
        getView().setResultSet(result.getAccountDto());
      }
    });
  }
}