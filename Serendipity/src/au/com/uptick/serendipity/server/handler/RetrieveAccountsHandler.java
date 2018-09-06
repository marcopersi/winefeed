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

import java.util.ArrayList;
import java.util.List;

import au.com.uptick.serendipity.server.dao.AccountDao;
import au.com.uptick.serendipity.server.domain.Account;
import au.com.uptick.serendipity.shared.action.RetrieveAccountsAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountsResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountsDto;

import com.allen_sauer.gwt.log.client.Log;
import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

// don't forget to update bindHandler() in ServerModule
public class RetrieveAccountsHandler implements
    ActionHandler<RetrieveAccountsAction, RetrieveAccountsResult> {

  /*
  
  private final Provider<HttpServletRequest> requestProvider;
  // private final ServletContext servletContext;

  @Inject
  RetrieveAccountsHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
    this.requestProvider = requestProvider;
    // this.servletContext = servletContext;
  }
  
  */

  @Override
  public RetrieveAccountsResult execute(RetrieveAccountsAction action,
      ExecutionContext context) throws ActionException {

    RetrieveAccountsResult result = null;
    AccountDao accountDao = new AccountDao();

    Log.debug("Retrieve Accounts");

    // if (! isLoggedIn(requestProvider)) {
    //   Log.debug("User has not logged in.");
    //   throw new ActionException("User has not logged in - Retrieve Accounts");
    // }

    try {
      List<Account> accounts = accountDao.retrieveAccounts(action.getMaxResults(),
          action.getFirstResult());

      if (accounts != null) {
        List<AccountsDto> accountsDtos = new ArrayList<AccountsDto>(accounts.size());

        for (Account account : accounts) {
          accountsDtos.add(createAccountsDto(account));
        }

        result = new RetrieveAccountsResult(accountsDtos);
      }
    }
    catch (Exception e) {
      Log.warn("Unable to retrieve Accounts - ", e);

      throw new ActionException(e);
    }

    return result;
  }
  
  /*

  private Boolean isLoggedIn(Provider<HttpServletRequest> requestProvider) {
    Boolean result = true;

    HttpSession session = requestProvider.get().getSession();

    Object authenticated = session.getAttribute("login.authenticated");

    if (authenticated == null) {
      result = false;
    }

    return result;
  }

  */

  private AccountsDto createAccountsDto(Account account) {
    return new AccountsDto(account.getAccountId(), account.getAccountName(), account.getMainPhone(),
        account.getLocation(), account.getPrimaryContact(), account.getEmailPrimaryContact());
  }

  @Override
  public Class<RetrieveAccountsAction> getActionType() {
    return RetrieveAccountsAction.class;
  }

  @Override
  public void undo(RetrieveAccountsAction action, RetrieveAccountsResult result,
      ExecutionContext context) throws ActionException {
  }
}