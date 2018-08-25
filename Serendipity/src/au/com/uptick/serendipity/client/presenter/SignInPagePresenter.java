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

import au.com.uptick.serendipity.client.CurrentUser;
import au.com.uptick.serendipity.client.NameTokens;
import au.com.uptick.serendipity.client.view.handlers.SignInPageUiHandlers;
import au.com.uptick.serendipity.shared.action.LoginAction;
import au.com.uptick.serendipity.shared.action.LoginResult;
import au.com.uptick.serendipity.shared.exception.LoginException;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.gwt.user.client.rpc.AsyncCallback;
import com.google.inject.Inject;
import com.gwtplatform.dispatch.client.DispatchAsync;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.NoGatekeeper;
import com.gwtplatform.mvp.client.annotations.ProxyStandard;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.PlaceRequest;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealRootContentEvent;

public class SignInPagePresenter extends
    Presenter<SignInPagePresenter.MyView, SignInPagePresenter.MyProxy> implements
        SignInPageUiHandlers {

  private final EventBus eventBus;
  private final DispatchAsync dispatcher;
  private final PlaceManager placeManager;

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyStandard
  @NameToken(NameTokens.signInPage)
  @NoGatekeeper
  public interface MyProxy extends Proxy<SignInPagePresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<SignInPageUiHandlers> {
    String getUserName();
    String getPassword();
    void resetAndFocus();
  }

  @Inject
  public SignInPagePresenter(final EventBus eventBus, MyView view, MyProxy proxy,
      final DispatchAsync dispatcher, final PlaceManager placeManager) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);

    this.eventBus = eventBus;
    this.dispatcher = dispatcher;
    this.placeManager = placeManager;
  }

  @Override
  protected void onReset() {
    super.onReset();

    getView().resetAndFocus();
  }

  @Override
  protected void revealInParent() {
    RevealRootContentEvent.fire(this, this);
 }

  @Override
  public void onOkButtonClicked() {
    sendCredentialsToServer();
  }

  private void sendCredentialsToServer() {
    String login = getView().getUserName();
    String password = getView().getPassword();

    getDispatcher().execute(new LoginAction(login, password),
        new AsyncCallback<LoginResult>() {
        
      @Override
      public void onFailure(Throwable caught) {
        String message = "onFailure() - " + caught.getLocalizedMessage();
        
        if (caught instanceof LoginException) {
          message = "onFailure() - " + "Invalid User name or Password.";
        }
          
        getView().resetAndFocus();
        
        Log.debug(message);
      }

      @Override
      public void onSuccess(LoginResult result) {
        CurrentUser currentUser = new CurrentUser(getView().getUserName());
        
        LoginAuthenticatedEvent.fire(eventBus, currentUser);
        
        PlaceRequest placeRequest = new PlaceRequest(NameTokens.mainPage);
        getPlaceManager().revealPlace(placeRequest);
        
        Log.debug("onSuccess() - " + result.getSessionKey());        
      }
    });
  }

  private DispatchAsync getDispatcher() {
    return dispatcher;
  }

  private PlaceManager getPlaceManager()  {
    return placeManager;
  }
}

/*

  // String salt = Security.randomCharString();
  // String hash = Security.sha256(password);

  Log.debug("login: " + login + ", password: " + password);
    

  In JavaScript. most of the Java produced exceptions (such as NullPointerException or
  MemoryOverflowException) are replaced by JavaScriptException. 

  This means that when running in development mode, a NullPointerException will be thrown,
  so you will need to catch (NullPointerException) but in compiled mode, you need to 
  catch (JavaScriptException).

  catch (Exception e) {
    if (e instanceof JavaScriptException) {
      Log.warn("JavaScriptException - ", e);
    } else if (e instanceof NullPointerException) {
      Log.warn("NullPointerException", e);
    }   
  }

*/