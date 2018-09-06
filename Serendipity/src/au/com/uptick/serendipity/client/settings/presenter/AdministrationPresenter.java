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

package au.com.uptick.serendipity.client.settings.presenter;

import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.presenter.MainPagePresenter;
import au.com.uptick.serendipity.client.settings.view.handlers.AdministrationUiHandlers;

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
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.PlaceRequest;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealContentEvent;

public class AdministrationPresenter extends
    Presenter<AdministrationPresenter.MyView, AdministrationPresenter.MyProxy> implements AdministrationUiHandlers {

  private final PlaceManager placeManager;

  @ProxyCodeSplit
  @NameToken(NameTokens.administration)
  @UseGatekeeper(LoggedInGatekeeper.class)
  // @UseGatekeeper(AdminGatekeeper.class)
  public interface MyProxy extends Proxy<AdministrationPresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<AdministrationUiHandlers> {
  }

  @Inject
  public AdministrationPresenter(EventBus eventBus, MyView view, MyProxy proxy,
      PlaceManager placeManager) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);

    this.placeManager = placeManager;
  }

  @Override
  protected void onBind() {
    super.onBind();

    Log.debug("onBind()");

    /*

    Timer timer = new Timer() {
      public void run() {
        MainPagePresenter.getNavigationPane().selectRecord(NameTokens.administration);

        Log.debug("onBind()- timer");
      }
    };

    timer.schedule(2000);

    */
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    Log.debug("onReveal() - " + NameTokens.administration);

    MainPagePresenter.getNavigationPaneHeader().setContextAreaHeaderLabelContents(Serendipity.getConstants().administrationMenuItemName());
    MainPagePresenter.getNavigationPane().selectRecord(NameTokens.administration);
  }

  @Override
  protected void onReset() {
    super.onReset();
  }

  @Override
  protected void revealInParent() {
    RevealContentEvent.fire(this, MainPagePresenter.TYPE_SetContextAreaContent,
        this);
  }

  public void onCellDoubleClicked(String place) {
    if (place.length() != 0) {
      PlaceRequest placeRequest = new PlaceRequest(place);
      placeManager.revealPlace(placeRequest);
    }
  }
}
