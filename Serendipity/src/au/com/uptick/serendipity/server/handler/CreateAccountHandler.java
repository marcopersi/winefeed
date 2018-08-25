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
import au.com.uptick.serendipity.shared.action.CreateAccountAction;
import au.com.uptick.serendipity.shared.action.CreateAccountResult;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;
import au.com.uptick.serendipity.shared.dto.sales.AddressDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

// don't forget to update bindHandler() in ServerModule

public class CreateAccountHandler implements
    ActionHandler<CreateAccountAction, CreateAccountResult> {

  // private final Provider<HttpServletRequest> requestProvider;
  // private final ServletContext servletContext;

  @Inject
  CreateAccountHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
    // this.servletContext = servletContext;
    // this.requestProvider = requestProvider;
  }

  @Override
  public CreateAccountResult execute(final CreateAccountAction action,
      final ExecutionContext context) throws ActionException {

    CreateAccountResult result = null;
    AccountDao accountDao = new AccountDao();

    // DOMConfigurator.configure("log4j.xml");

    Log.info("Create Account");

    try {
      Long accountId = accountDao.createAccount(createAccount(action.getAccountDto()));

      Log.info("Created Account: " + accountId);

      result = new CreateAccountResult(accountId);
    }
    catch (Exception e) {
      Log.warn("Unable to create Account", e);

      throw new ActionException(e);
    }

    return result;
  }

  private Account createAccount(AccountDto accountDto) {

    Account account = new Account();

    account.setAccountName(accountDto.getAccountName());
    account.setAccountNumber(accountDto.getAccountNumber());
    // parentAccount;
    // primaryContact;
    // relationshipType;

    // Address Information
    List<AddressDto> addressDtos = accountDto.getAddresses();

    if (addressDtos != null) {

      List<Address> addresses = new ArrayList<Address>(addressDtos.size());

      for (AddressDto addressDto : addressDtos) {
        addresses.add(createAddress(addressDto));
      }

      account.setAddresses(addresses);
    }

    // Electronic Address Information
    // List<ElectronicAddress> electronicAddresses = account.getElectronicAddresses();

    return account;
  }

  private Address createAddress(AddressDto addressDto) {
    return new Address(addressDto.getAddressName(),
        addressDto.getAddressLine1(), addressDto.getAddressLine2(), addressDto.getAddressLine3(),
        addressDto.getCity(), addressDto.getState(), addressDto.getPostalCode(),
        addressDto.getCountry(), addressDto.getAddressType());
  }

  @Override
  public Class<CreateAccountAction> getActionType() {
    return CreateAccountAction.class;
  }

  @Override
  public void undo(CreateAccountAction action, CreateAccountResult result,
      ExecutionContext context) throws ActionException {
  }
}

