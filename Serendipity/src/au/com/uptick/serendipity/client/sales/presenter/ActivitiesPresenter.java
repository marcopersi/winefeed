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
import au.com.uptick.serendipity.client.sales.view.handlers.ActivitiesUiHandlers;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.inject.Inject;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyCodeSplit;
import com.gwtplatform.mvp.client.annotations.UseGatekeeper;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealContentEvent;

public class ActivitiesPresenter extends
    Presenter<ActivitiesPresenter.MyView, ActivitiesPresenter.MyProxy> implements
    ActivitiesUiHandlers {

  // private final PlaceManager placeManager;

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyCodeSplit
  @NameToken(NameTokens.activities)
  @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<ActivitiesPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<ActivitiesUiHandlers> {
    void setServerResponse();
  }

  @Inject
  public ActivitiesPresenter(EventBus eventBus, MyView view, MyProxy proxy) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);

    // this.placeManager = placeManager;
  }

  @Override
  protected void onBind() {
    super.onBind();

    // Log.debug("onBind()");

    // retrieveActivities();
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    // Log.debug("onReveal() - " + NameTokens.activities);

    MainPagePresenter.getNavigationPaneHeader().setContextAreaHeaderLabelContents(Serendipity.getConstants().activitiesMenuItemName());
    MainPagePresenter.getNavigationPane().selectRecord(NameTokens.activities);
  }

  @Override
  protected void onReset() {
    super.onReset();

    Log.debug("onReset()");
  }

  @Override
  protected void revealInParent() {
    RevealContentEvent.fire(this, MainPagePresenter.TYPE_SetContextAreaContent,
        this);
  }

  public void onNewButtonClicked() {
    // TO DO:
  }
}
