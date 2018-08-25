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

package au.com.uptick.serendipity.server.handler.validator;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.google.inject.Singleton;
import com.gwtplatform.dispatch.server.actionvalidator.ActionValidator;
import com.gwtplatform.dispatch.shared.Action;
import com.gwtplatform.dispatch.shared.Result;

public class LoggedInActionValidator implements ActionValidator  {
  
  private final Provider<HttpServletRequest> requestProvider;

  @Inject
  LoggedInActionValidator(final Provider<HttpServletRequest> requestProvider) {
    this.requestProvider = requestProvider;
  }

  @Override
  @Singleton
  public boolean isValid(Action<? extends Result> action) {
    boolean result = true;

    Log.debug("LoggedIn Action Validator");

    HttpSession session = requestProvider.get().getSession();

    Object authenticated = session.getAttribute("login.authenticated");

    if (authenticated == null) {
      Log.debug("The User has not logged in.");
      result = false;
    }
    
    return result;
  }
}