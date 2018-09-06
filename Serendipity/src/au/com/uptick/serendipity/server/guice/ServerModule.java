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

package au.com.uptick.serendipity.server.guice;

import au.com.uptick.serendipity.server.handler.CreateAccountHandler;
import au.com.uptick.serendipity.server.handler.DeleteAccountHandler;
import au.com.uptick.serendipity.server.handler.LoginHandler;
import au.com.uptick.serendipity.server.handler.RetrieveAccountHandler;
import au.com.uptick.serendipity.server.handler.RetrieveAccountsHandler;
import au.com.uptick.serendipity.server.handler.RetrieveReportsHandler;
import au.com.uptick.serendipity.server.handler.UpdateAccountHandler;
import au.com.uptick.serendipity.server.handler.validator.LoggedInActionValidator;
import au.com.uptick.serendipity.shared.action.CreateAccountAction;
import au.com.uptick.serendipity.shared.action.DeleteAccountAction;
import au.com.uptick.serendipity.shared.action.LoginAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountsAction;
import au.com.uptick.serendipity.shared.action.RetrieveReportsAction;
import au.com.uptick.serendipity.shared.action.UpdateAccountAction;

import com.gwtplatform.dispatch.server.guice.HandlerModule;

public class ServerModule extends HandlerModule {

  @Override
  protected void configureHandlers() {

    // Bind Action to Action Handler
    bindHandler(LoginAction.class, LoginHandler.class);

    // Bind Action to Action Handler and Action Validator
    // bindHandler(RetrieveAccountsAction.class, RetrieveAccountsHandler.class);
    bindHandler(RetrieveAccountsAction.class, RetrieveAccountsHandler.class, LoggedInActionValidator.class);
    
    bindHandler(CreateAccountAction.class, CreateAccountHandler.class, LoggedInActionValidator.class);
    bindHandler(RetrieveAccountAction.class, RetrieveAccountHandler.class, LoggedInActionValidator.class);
    bindHandler(UpdateAccountAction.class, UpdateAccountHandler.class, LoggedInActionValidator.class);
    bindHandler(DeleteAccountAction.class, DeleteAccountHandler.class, LoggedInActionValidator.class);
    
    bindHandler(RetrieveReportsAction.class, RetrieveReportsHandler.class, LoggedInActionValidator.class);

    // bind(Log.class).toProvider(LogProvider.class).in(Singleton.class);
  }
}
