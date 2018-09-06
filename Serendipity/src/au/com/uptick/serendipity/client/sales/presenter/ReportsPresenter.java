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
import au.com.uptick.serendipity.client.model.ReportsRecord;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.sales.view.handlers.ReportsUiHandlers;
import au.com.uptick.serendipity.client.widgets.StatusBar;
import au.com.uptick.serendipity.shared.action.RetrieveReportsAction;
import au.com.uptick.serendipity.shared.action.RetrieveReportsResult;
import au.com.uptick.serendipity.shared.dto.sales.ReportsDto;

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
import com.gwtplatform.mvp.client.proxy.Proxy;

public class ReportsPresenter extends
    SalesPresenter<ReportsPresenter.MyView, ReportsPresenter.MyProxy> implements
    ReportsUiHandlers {

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyCodeSplit
  @NameToken(NameTokens.reports)
  @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<ReportsPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<ReportsUiHandlers> {
    StatusBar getStatusBar();
    void refreshStatusBar();
    void setNumberOfElements(int numberOfElements);
    void setPageNumber(int pageNumber);
    void setResultSet(List<ReportsDto> resultSet);
  }

  @Inject
  public ReportsPresenter(EventBus eventBus, MyView view, MyProxy proxy, DispatchAsync dispatcher) {
    super(eventBus, view, proxy, dispatcher);

    getView().setUiHandlers(this);
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    MainPagePresenter.getNavigationPaneHeader().setContextAreaHeaderLabelContents(Serendipity.getConstants().reportsMenuItemName());
    MainPagePresenter.getNavigationPane().selectRecord(NameTokens.reports);
  }

  protected void retrieveResultSet() {

    getDispatcher().execute(new RetrieveReportsAction(getMaxResults(), getFirstResult()),
        new AsyncCallback<RetrieveReportsResult>() {
      @Override
      public void onFailure(Throwable caught) {
        Log.debug("onFailure() - " + caught.getLocalizedMessage());
      }

      @Override
      public void onSuccess(RetrieveReportsResult result) {

        setNumberOfElements(result.getReportDtos().size());

        // update Selected label e.g "0 of 50 selected"
        getView().setNumberOfElements(getNumberOfElements());
        getView().setPageNumber(getPageNumber());
        getView().refreshStatusBar();

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
        getView().setResultSet(result.getReportDtos());
      }
    });
  }

  @Override
  public void onNewButtonClicked() {
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

  public static final String DEFAULT_REPORTS_SERVICE_PATH = "reports/";
  private static final String HOST_FILENAME = "Reports.html";
  // private static final String PARAMETER_SEPERATOR = "&";
  private static final String NAME = "_blank";
  private static final String FEATURES = "width=760, height=480";

  @Override
  public void onRecordDoubleClicked(String reportFilename) {

    StringBuilder url = new StringBuilder();
    url.append(DEFAULT_REPORTS_SERVICE_PATH).append(HOST_FILENAME).append("?");

    String arg0Name = URL.encodeQueryString(ReportsRecord.REPORT_FILENAME);
    url.append(arg0Name);
    url.append("=");
    String arg0Value = URL.encodeQueryString(reportFilename);
    url.append(arg0Value);
    // url.append(encodeBase64(arg0Value));

    // Log.debug("Window.open() RelativeURL: " + Serendipity.getRelativeURL(url.toString()));
    Window.open(Serendipity.getRelativeURL(url.toString()), NAME, FEATURES);
  }
}