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

import java.util.Iterator;
import java.util.List;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import au.com.uptick.serendipity.server.dao.AccountDao;
import au.com.uptick.serendipity.server.domain.Account;
import au.com.uptick.serendipity.server.domain.Address;
import au.com.uptick.serendipity.shared.action.UpdateAccountAction;
import au.com.uptick.serendipity.shared.action.UpdateAccountResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;
import au.com.uptick.serendipity.shared.dto.sales.AddressDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

// don't forget to update bindHandler() in ServerModule

public class UpdateAccountHandler implements
    ActionHandler<UpdateAccountAction, UpdateAccountResult> {

  // private final Provider<HttpServletRequest> requestProvider;
  // private final ServletContext servletContext;

  @Inject
  UpdateAccountHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
    // this.servletContext = servletContext;
    // this.requestProvider = requestProvider;
  }

  @Override
  public UpdateAccountResult execute(final UpdateAccountAction action,
      final ExecutionContext context) throws ActionException {

    UpdateAccountResult result = null;
    AccountDao accountDao = new AccountDao();

    // DOMConfigurator.configure("log4j.xml");

    Log.info("Update Account");

    try {
      Account account = accountDao.retrieveAccount(action.getAccountDto().getAccountId());

      updateAccount(account, action.getAccountDto());

      accountDao.updateAccount(account);

      result = new UpdateAccountResult();
    }
    catch (Exception e) {
      Log.warn("Unable to update Account", e);

      throw new ActionException(e);
    }

    return result;
  }

  private void updateAccount(Account account, AccountDto accountDto) {

    account.setAccountName(accountDto.getAccountName());
    account.setAccountNumber(accountDto.getAccountNumber());
    // parentAccount;
    // primaryContact;
    // relationshipType;

    // get the list of Addresses
    List<Address> addresses = account.getAddresses();

    if (addresses.size() > 0) {

      // Address Information
      Iterator<Address> it = addresses.iterator();
      Address address = it.next();

      // AddressDto Information
      List<AddressDto> addressDtos = accountDto.getAddresses();
      Iterator<AddressDto> itDto = addressDtos.iterator();
      AddressDto addressDto = itDto.next();

      // Update Address with AddressDto Information
      address.setAddressName(addressDto.getAddressName());
      address.setAddressLine1(addressDto.getAddressLine1());
      address.setAddressLine2(addressDto.getAddressLine2());
      address.setAddressLine3(addressDto.getAddressLine3());
      address.setCity(addressDto.getCity());
      address.setState(addressDto.getState());
      address.setPostalCode(addressDto.getPostalCode());
      address.setCountry(addressDto.getCountry());
      address.setAddressType(addressDto.getAddressType());
    }

    // Electronic Address Information
  }

  @Override
  public Class<UpdateAccountAction> getActionType() {
    return UpdateAccountAction.class;
  }

  @Override
  public void undo(UpdateAccountAction action, UpdateAccountResult result,
      ExecutionContext context) throws ActionException {
  }
}

