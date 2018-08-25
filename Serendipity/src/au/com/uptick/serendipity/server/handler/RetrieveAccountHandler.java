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

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import au.com.uptick.serendipity.server.dao.AccountDao;
import au.com.uptick.serendipity.server.domain.Account;
import au.com.uptick.serendipity.server.domain.Address;
import au.com.uptick.serendipity.shared.action.RetrieveAccountAction;
import au.com.uptick.serendipity.shared.action.RetrieveAccountResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;
import au.com.uptick.serendipity.shared.dto.sales.AddressDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

// don't forget to update bindHandler() in ServerModule

public class RetrieveAccountHandler implements
    ActionHandler<RetrieveAccountAction, RetrieveAccountResult> {

  // private final Provider<HttpServletRequest> requestProvider;
  // private final ServletContext servletContext;

  @Inject
  RetrieveAccountHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
    // this.servletContext = servletContext;
    // this.requestProvider = requestProvider;
  }

  @Override
  public RetrieveAccountResult execute(final RetrieveAccountAction action,
      final ExecutionContext context) throws ActionException {

    RetrieveAccountResult result = null;
    AccountDao accountDao = new AccountDao();

    // DOMConfigurator.configure("log4j.xml");

    Log.info("Retrieve Account: " + action.getAccountId());

    try {
      Account account = accountDao.retrieveAccount(action.getAccountId());

      if (account != null) {
        result = new RetrieveAccountResult(createAccountDto(account));
      }
    }
    catch (Exception e) {
      Log.warn("Unable to retrieve Account - ", e);

      throw new ActionException(e);
    }

    return result;
  }

  private AccountDto createAccountDto(Account account) {

    AccountDto accountDto = new AccountDto(account.getAccountId());

    // General Information
    accountDto.setAccountName(account.getAccountName());
    accountDto.setAccountNumber(account.getAccountNumber());
    // parentAccount;
    // primaryContact;
    // relationshipType;

    // Address Information
    List<Address> addresses = account.getAddresses();

    if (addresses != null) {

      List<AddressDto> addressDtos = new ArrayList<AddressDto>(addresses.size());

      for (Address address : addresses) {
        addressDtos.add(createAddressDto(address));
      }

      accountDto.setAddresses(addressDtos);
    }

    // Electronic Address Information
    // List<ElectronicAddress> electronicAddresses = account.getElectronicAddresses();

    return accountDto;
  }

  private AddressDto createAddressDto(Address address) {
    return new AddressDto(address.getAddressId(), address.getAddressName(),
        address.getAddressLine1(), address.getAddressLine2(), address.getAddressLine3(),
        address.getCity(), address.getState(), address.getPostalCode(),
        address.getCountry(), address.getAddressType());
  }

  @Override
  public Class<RetrieveAccountAction> getActionType() {
    return RetrieveAccountAction.class;
  }

  @Override
  public void undo(RetrieveAccountAction action, RetrieveAccountResult result,
      ExecutionContext context) throws ActionException {
  }
}

