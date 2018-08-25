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

package au.com.uptick.serendipity.client.presenter;

import au.com.uptick.serendipity.client.LoggedInGatekeeper;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.view.handlers.MainPageUiHandlers;
import au.com.uptick.serendipity.client.widgets.NavigationPane;
import au.com.uptick.serendipity.client.widgets.NavigationPaneHeader;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.gwt.event.shared.GwtEvent.Type;
import com.google.inject.Inject;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.ContentSlot;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyCodeSplit;
import com.gwtplatform.mvp.client.annotations.UseGatekeeper;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.PlaceRequest;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealContentHandler;
import com.gwtplatform.mvp.client.proxy.RevealRootContentEvent;

public class MainPagePresenter extends
    Presenter<MainPagePresenter.MyView, MainPagePresenter.MyProxy> implements
        MainPageUiHandlers {

  private final PlaceManager placeManager;

  private static NavigationPaneHeader navigationPaneHeader;
  private static NavigationPane navigationPane;

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyCodeSplit
  @NameToken(NameTokens.mainPage)
  @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<MainPagePresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<MainPageUiHandlers> {
    NavigationPaneHeader getNavigationPaneHeader();
    NavigationPane getNavigationPane();
  }

  /**
   * Use this in leaf presenters, inside their {@link #revealInParent} method.
   */
  @ContentSlot
  public static final Type<RevealContentHandler<?>> TYPE_SetContextAreaContent = new Type<RevealContentHandler<?>>();

  @Inject
  public MainPagePresenter(EventBus eventBus, MyView view, MyProxy proxy,
      PlaceManager placeManager) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);

    this.placeManager = placeManager;

    MainPagePresenter.navigationPaneHeader = getView().getNavigationPaneHeader();
    MainPagePresenter.navigationPane = getView().getNavigationPane();
  }

  @Override
  protected void onBind() {
    super.onBind();

    Log.debug("onBind()");

    // expand the first Navigation Pane section
    getView().getNavigationPane().expandSection(Serendipity.getConstants().salesStackSectionName());

    // reveal the first nested Presenter
    PlaceRequest placRequest = new PlaceRequest(NameTokens.activities);
    placeManager.revealPlace(placRequest);
  }

  @Override
  protected void onReveal() {
    super.onReveal();

    Log.debug("onReveal()");
  }

  @Override
  protected void onReset() {
    super.onReset();

    Log.debug("onReset()");
  }

  @Override
  protected void revealInParent() {
    // RevealRootLayoutContentEvent.fire(this, this);
    RevealRootContentEvent.fire(this, this);
  }

  public void onNavigationPaneSectionHeaderClicked(String place) {
    if (place.length() != 0) {
      PlaceRequest placeRequest = new PlaceRequest(place);
      placeManager.revealPlace(placeRequest);
    }
  }

  public void onNavigationPaneSectionClicked(String place) {
    if (place.length() != 0) {
      PlaceRequest placeRequest = new PlaceRequest(place);
      placeManager.revealPlace(placeRequest);
    }
  }

  public static NavigationPaneHeader getNavigationPaneHeader() {
    return navigationPaneHeader;
  }

  public static NavigationPane getNavigationPane() {
    return navigationPane;
  }
}
