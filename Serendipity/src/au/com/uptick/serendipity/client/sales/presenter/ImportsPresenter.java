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

import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.ImportsUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;

import com.google.gwt.event.shared.EventBus;
import com.google.gwt.user.client.Window;
import com.google.inject.Inject;
import com.gwtplatform.dispatch.client.DispatchAsync;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyCodeSplit;
import com.gwtplatform.mvp.client.annotations.UseGatekeeper;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.Proxy;

public class ImportsPresenter extends
    SalesPresenter<ImportsPresenter.MyView, ImportsPresenter.MyProxy> implements
    ImportsUiHandlers {

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyCodeSplit
  @NameToken(NameTokens.imports)
  @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<ImportsPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<ImportsUiHandlers> {
    StatusBar getStatusBar();
    void refreshStatusBar();
    void setNumberOfElements(int numberOfElements);
    void setPageNumber(int pageNumber);
    // void setResultSet(List<ImportsDto> resultSet);
  }

  @Inject
  public ImportsPresenter(EventBus eventBus, MyView view, MyProxy proxy, DispatchAsync dispatcher) {
    super(eventBus, view, proxy, dispatcher);

    getView().setUiHandlers(this);
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    MainPagePresenter.getNavigationPaneHeader().setContextAreaHeaderLabelContents(Serendipity.getConstants().importsMenuItemName());
    MainPagePresenter.getNavigationPane().selectRecord(NameTokens.imports);
  }

  protected void retrieveResultSet() {
  }

  // public static native String encodeBase64(String string) /*-{ return $wnd.btoa(string); }-*/;
  // public static native String decodeBase64(String string) /*-{ return $wnd.atob(string); }-*/;

  private static final String HOST_FILENAME = "FileUpload.html";
  private static final String NAME = "_blank";
  private static final String FEATURES = "width=360, height=280, location=no, resizable=no";

  @Override
  public void onNewButtonClicked() {
    StringBuilder url = new StringBuilder();
    url.append(HOST_FILENAME);

    Window.open(Serendipity.getRelativeURL(url.toString()), NAME, FEATURES);
  }

  @Override
  public void onDeleteButtonClicked(String accountId) {
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

  @Override
  public void onRecordDoubleClicked(String reportFilename) {
  }
}