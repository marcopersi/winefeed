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
import au.com.uptick.serendipity.client.sales.account.view.handlers.FileUploadUiHandlers;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.event.shared.EventBus;
import com.google.inject.Inject;
import com.gwtplatform.mvp.client.HasUiHandlers;
import com.gwtplatform.mvp.client.Presenter;
import com.gwtplatform.mvp.client.View;
import com.gwtplatform.mvp.client.annotations.NameToken;
import com.gwtplatform.mvp.client.annotations.ProxyStandard;
import com.gwtplatform.mvp.client.proxy.Place;
import com.gwtplatform.mvp.client.proxy.PlaceManager;
import com.gwtplatform.mvp.client.proxy.Proxy;
import com.gwtplatform.mvp.client.proxy.RevealRootContentEvent;

public class FileUploadPagePresenter extends
    Presenter<FileUploadPagePresenter.MyView, FileUploadPagePresenter.MyProxy> implements
    FileUploadUiHandlers {

  // don't forget to update SerendipityGinjector & ClientModule
  @ProxyStandard
  @NameToken(NameTokens.fileUploadPage)
  // @UseGatekeeper(LoggedInGatekeeper.class)
  public interface MyProxy extends Proxy<FileUploadPagePresenter>, Place {
  }

  public interface MyView extends View, HasUiHandlers<FileUploadUiHandlers> {
  }

  @Inject
  public FileUploadPagePresenter(EventBus eventBus, MyView view, MyProxy proxy,
      PlaceManager placeManager) {
    super(eventBus, view, proxy);

    getView().setUiHandlers(this);
  }

  @Override
  protected void onBind() {
    super.onBind();

    Log.debug("onBind()");
  }

  @Override
  protected void revealInParent() {
    RevealRootContentEvent.fire(this, this);
  }

  public static native void close() /*-{ $wnd.close(); }-*/;

  @Override
  public void onCancelButtonClicked() {
    close();
  }

  @Override
  public void onOkButtonClicked() {
    close();
  }
}

