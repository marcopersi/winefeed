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

package au.com.uptick.serendipity.server.handler;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import com.google.inject.Inject;
import com.google.inject.Provider;

import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

import com.allen_sauer.gwt.log.client.Log;

import au.com.uptick.serendipity.server.dao.AccountDao;
import au.com.uptick.serendipity.shared.action.DeleteAccountAction;
import au.com.uptick.serendipity.shared.action.DeleteAccountResult;

// don't forget to update bindHandler() in ServerModule

public class DeleteAccountHandler implements
ActionHandler<DeleteAccountAction, DeleteAccountResult> {

  // private final Provider<HttpServletRequest> requestProvider;
  // private final ServletContext servletContext;

  @Inject
  DeleteAccountHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
    // this.servletContext = servletContext;
    // this.requestProvider = requestProvider;
  }

  @Override
  public DeleteAccountResult execute(final DeleteAccountAction action,
      final ExecutionContext context) throws ActionException {

    DeleteAccountResult result = null;
    AccountDao accountDao = new AccountDao();

    // DOMConfigurator.configure("log4j.xml");

    Log.info("Delete Account: " + action.getAccountId());

    try {
      accountDao.deleteAccount(accountDao.retrieveAccount(action.getAccountId()));

      result = new DeleteAccountResult();
    }
    catch (Exception e) {
      Log.warn("Unable to delete Account - ", e);

      throw new ActionException(e);
    }

    return result;
  }

  @Override
  public Class<DeleteAccountAction> getActionType() {
    return DeleteAccountAction.class;
  }

  @Override
  public void undo(DeleteAccountAction action, DeleteAccountResult result,
      ExecutionContext context) throws ActionException {
  }
}
