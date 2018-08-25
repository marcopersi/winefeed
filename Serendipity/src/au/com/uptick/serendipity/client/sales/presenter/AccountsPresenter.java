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

package au.com.uptick.serendipity.client.sales.presenter;

import java.util.List;

import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.model.AccountsRecord;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.AccountsUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;
import au.com.uptick.serendipity.shared.action.DeleteAccountAction;
import au.com.uptick.serendipity.shared.action.DeleteAccountResult;
import au.com.uptick.serendipity.shared.action.RetrieveAccountsAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountsResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountsDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.gwt.http.client.URL;
import com.google.gwt.user.client.Window;
import com.google.gwt.user.client.rpc.AsyncCallback;
import com.google.inject.Inject;
import com.gwtplatform.dispatch.client.DispatchAsync;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyCodeSplit;
import com.gwtplatform.mvp.client.annotations.UseGatekeeper;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.Proxy;

public class AccountsPresenter extends
    SalesPresenter<AccountsPresenter.MyView, AccountsPresenter.MyProxy> implements
    AccountsUiHandlers {

  private final PlaceManager placeManager;

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyCodeSplit
  @NameToken(NameTokens.accounts)
  @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<AccountsPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<AccountsUiHandlers> {
    StatusBar getStatusBar();
    void refreshStatusBar();
    void setNumberOfElements(int numberOfElements);
    void setPageNumber(int pageNumber);
    void setResultSet(List<AccountsDto> resultSet);
    void removeSelectedData();
  }

  @Inject
  public AccountsPresenter(EventBus eventBus, MyView view, MyProxy proxy, 
      DispatchAsync dispatcher, PlaceManager placeManager) {
    super(eventBus, view, proxy, dispatcher);

    getView().setUiHandlers(this);

    // PlaceManager placeManager
    this.placeManager = placeManager;
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    Log.debug("onReveal() - " + NameTokens.accounts);

    MainPagePresenter.getNavigationPaneHeader().setContextAreaHeaderLabelContents(Serendipity.getConstants().accountsMenuItemName());
    MainPagePresenter.getNavigationPane().selectRecord(NameTokens.accounts);
  }

  @Override
  protected void onReset() {
    super.onReset();

    Log.debug("onReset()");
  }

  @Override
  protected void retrieveResultSet() {

    getDispatcher().execute(new RetrieveAccountsAction(getMaxResults(), getFirstResult()),
        new AsyncCallback<RetrieveAccountsResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(RetrieveAccountsResult result) {

        setNumberOfElements(result.getAccountDtos().size());

        // update Selected label e.g "0 of 50 selected"
        getView().setNumberOfElements(getNumberOfElements());
        getView().setPageNumber(getPageNumber());
        getView().refreshStatusBar();

        // Log.debug("onSuccess() - firstResult: " + firstResult +
        //     " pageNumber: " + pageNumber + " numberOfElements: " + numberOfElements);

        // enable/disable the pagination widgets
        if (getPageNumber() == 1) {
          getView().getStatusBar().getResultSetFirstButton().disable();
          getView().getStatusBar().getResultSetPreviousButton().disable();
        }

        // enable/disable the pagination widgets
        if (getNumberOfElements() < getMaxResults()) {
          getView().getStatusBar().getResultSetNextButton().disable();
        }
        else {
          getView().getStatusBar().getResultSetNextButton().enable();
        }

        // pass the result set to the View
        getView().setResultSet(result.getAccountDtos());
      }
    });
  }

  public static native String encodeBase64(String string) /*-{ return $wnd.btoa(string); }-*/;

  // public static native String decodeBase64(String string) /*-{ return $wnd.atob(string); }-*/;

  private static final String HOST_FILENAME = "Account.html";
  private static final String ACTIVITY = "activity";
  private static final String NEW = "new";
  private static final String EDIT = "edit";
  private static final String PARAMETER_SEPERATOR = "&";  // GWTP "?"
  private static final String NAME = "_blank";
  private static final String FEATURES = "width=760, height=480";
  // private static final String FEATURES = "width=760, height=480, location=no, resizable=no";

  @Override
  public void onNewButtonClicked() {
    StringBuilder url = new StringBuilder();
    url.append(HOST_FILENAME).append("?");

    String arg0Name = URL.encodeQueryString(AccountsRecord.ACCOUNT_ID);
    url.append(arg0Name);
    url.append("=");
    String arg0Value = URL.encodeQueryString("0");
    // url.append(arg0Value);
    url.append(encodeBase64(arg0Value));
    Log.debug("Window.open() arg0Value: " + arg0Value + " Base64: " + encodeBase64(arg0Value));
    url.append(PARAMETER_SEPERATOR);

    String arg1Name = URL.encodeQueryString(ACTIVITY);
    url.append(arg1Name);
    url.append("=");
    String arg1Value = URL.encodeQueryString(NEW);
    // url.append(arg1Value);
    url.append(encodeBase64(arg1Value));
    Log.debug("Window.open() arg1Value: " + arg1Value + " Base64: " + encodeBase64(arg1Value));

    // Log.debug("Window.open() RelativeURL: " + Serendipity.getRelativeURL(url.toString()));
    Window.open(Serendipity.getRelativeURL(url.toString()), NAME, FEATURES);

    // un-comment the following lines (and comment out the lines above) if you want
    // to open the new View in the current browser window

    // PlaceRequest placeRequest = new PlaceRequest(NameTokens.accountPage);
    // placeRequest = placeRequest.with(ACTIVITY, encodeBase64(EDIT)).with(AccountsRecord.ACCOUNT_ID, encodeBase64("0"));
    // placeManager.revealPlace(placeRequest);
  }

  public static final String DEFAULT_FILE_DOWNLOAD_SERVICE_PATH = "download/";
  private static final String FILE_DOWNLOAD_HOST_FILENAME = "FileDownload.html";
  private static final String RECORD_TYPE = "recordType";

  @Override
  public void onExportButtonClicked() {

    StringBuilder url = new StringBuilder();
    url.append(DEFAULT_FILE_DOWNLOAD_SERVICE_PATH).append(FILE_DOWNLOAD_HOST_FILENAME).append("?");

    String arg0Name = URL.encodeQueryString(RECORD_TYPE);
    url.append(arg0Name);
    url.append("=");
    String arg0Value = URL.encodeQueryString("Account");
    url.append(arg0Value);
    // url.append(encodeBase64(arg0Value));

    // Log.debug("Window.open() RelativeURL: " + Serendipity.getRelativeURL(url.toString()));
    Window.open(Serendipity.getRelativeURL(url.toString()), NAME, FEATURES);
  }

  @Override
  public void onRecordDoubleClicked(String accountId) {

    StringBuilder url = new StringBuilder();
    url.append(HOST_FILENAME).append("?");

    String arg0Name = URL.encodeQueryString(AccountsRecord.ACCOUNT_ID);
    url.append(arg0Name);
    url.append("=");
    String arg0Value = URL.encodeQueryString(accountId);
    // url.append(arg0Value);
    url.append(encodeBase64(arg0Value));
    Log.debug("Window.open() arg0Value: " + arg0Value + " Base64: " + encodeBase64(arg0Value));
    url.append(PARAMETER_SEPERATOR);

    String arg1Name = URL.encodeQueryString(ACTIVITY);
    url.append(arg1Name);
    url.append("=");
    String arg1Value = URL.encodeQueryString(EDIT);
    // url.append(arg1Value);
    url.append(encodeBase64(arg1Value));
    Log.debug("Window.open() arg1Value: " + arg1Value + " Base64: " + encodeBase64(arg1Value));

    // Log.debug("Window.open() RelativeURL: " + Serendipity.getRelativeURL(url.toString()));
    Window.open(Serendipity.getRelativeURL(url.toString()), NAME, FEATURES);

    // un-comment the following lines (and comment out the lines above) if you want
    // to open the new View in the current browser window

    // PlaceRequest placeRequest = new PlaceRequest(NameTokens.accountPage);
    // placeRequest = placeRequest.with(ACTIVITY, encodeBase64(EDIT)).with(AccountsRecord.ACCOUNT_ID, encodeBase64(accountId));
    // placeManager.revealPlace(placeRequest);
  }

  @Override
  public void onDeleteButtonClicked(String accountId) {
    Long id = -1L;

    try {
      id = Long.valueOf(accountId);
    }
    catch (NumberFormatException nfe) {
      Log.debug("NumberFormatException: " + nfe.getLocalizedMessage());
      return;
    }

    getDispatcher().execute(new DeleteAccountAction(id),
        new AsyncCallback<DeleteAccountResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(DeleteAccountResult result) {
        Log.debug("onSuccess()");
        getView().removeSelectedData();
      }
    });
  }

  @Override
  public void onRefreshButtonClicked() {
    super.refreshButtonClicked();
  }

  @Override
  public void onResultSetFirstButtonClicked() {
    super.resultSetFirstButtonClicked();

    getView().getStatusBar().getResultSetFirstButton().disable();
  }

  @Override
  public void onResultSetPreviousButtonClicked() {
    super.resultSetPreviousButtonClicked();
  }

  @Override
  public void onResultSetNextButtonClicked() {
    super.resultSetNextButtonClicked();

    getView().getStatusBar().getResultSetFirstButton().enable();
    getView().getStatusBar().getResultSetPreviousButton().enable();
  }
}