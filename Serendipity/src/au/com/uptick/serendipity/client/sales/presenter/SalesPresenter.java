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

import au.com.uptick.serendipity.client.presenter.MainPagePresenter;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.inject.Inject;
import com.gwtplatform.dispatch.client.DispatchAsync;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealContentEvent;

public abstract class SalesPresenter<V extends View, Proxy_ extends Proxy<?>> extends Presenter<V, Proxy_> {

  public static final int DEFAULT_MAX_RESULTS = 50;

  private final DispatchAsync dispatcher;

  private int maxResults;
  private int firstResult;
  private int pageNumber;
  private int numberOfElements;

  @Inject
  public SalesPresenter(EventBus eventBus, V view, Proxy_ proxy, DispatchAsync dispatcher) {
    super(eventBus, view, proxy);

    this.dispatcher = dispatcher;
  }

  @Override
  protected void onBind() {
    super.onBind();

    maxResults = DEFAULT_MAX_RESULTS;
    firstResult = 0;
    pageNumber = 1;
    numberOfElements = maxResults;

    retrieveResultSet();
  }

  protected void retrieveResultSet() {
    Log.debug("Don't forget to @Override retrieveResultSet()");
  }

  protected void refreshButtonClicked() {
    retrieveResultSet();
  }

  protected void resultSetFirstButtonClicked() {
    firstResult = 0;
    pageNumber = 1;

    retrieveResultSet();
  }

  protected void resultSetPreviousButtonClicked() {
    firstResult -= maxResults;
    pageNumber--;

    retrieveResultSet();
  }

  protected void resultSetNextButtonClicked() {
    firstResult += numberOfElements;
    pageNumber++;

    retrieveResultSet();
  }

  @Override
  protected void revealInParent() {
    RevealContentEvent.fire(this, MainPagePresenter.TYPE_SetContextAreaContent, this);
  }

  protected DispatchAsync getDispatcher() {
    return dispatcher;
  }

  protected int getMaxResults() {
    return maxResults;
  }

  protected void setMaxResults(int maxResults) {
    this.maxResults = maxResults;
  }

  protected int getFirstResult() {
    return firstResult;
  }

  protected void setFirstResult(int firstResult) {
    this.firstResult = firstResult;
  }

  protected int getPageNumber() {
    return pageNumber;
  }

  protected void setPageNumber(int pageNumber) {
    this.pageNumber = pageNumber;
  }

  protected int getNumberOfElements() {
    return numberOfElements;
  }

  protected void setNumberOfElements(int numberOfElements) {
    this.numberOfElements = numberOfElements;
  }
}
