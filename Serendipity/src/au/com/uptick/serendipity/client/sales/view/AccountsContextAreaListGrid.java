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

package au.com.uptick.serendipity.client.sales.view;

import java.util.List;

import au.com.uptick.serendipity.client.Serendipity;
import au.com.uptick.serendipity.client.model.AccountsRecord;
import au.com.uptick.serendipity.shared.dto.sales.AccountsDto;

import com.smartgwt.client.types.Alignment;
import com.smartgwt.client.types.ExpansionMode;
import com.smartgwt.client.types.ListGridFieldType;
import com.smartgwt.client.widgets.grid.ListGridField;

public class AccountsContextAreaListGrid extends SalesContextAreaListGrid {

  private static final String ACCOUNT_ICON = "account";

  private static final int ACCOUNT_NAME_COLUMN_WIDTH = 140;
  private static final int MAIN_PHONE_COLUMN_WIDTH = 90;
  private static final int LOCATION_COLUMN_WIDTH = 220; // 80
  private static final int PRIMARY_CONTACT_COLUMN_WIDTH = 100;
  private static final int EMAIL_PRIMARY_CONTACT_COLUMN_WIDTH = 120;

  public AccountsContextAreaListGrid() {
    super();

    this.setCanExpandRecords(true);
    this.setExpansionMode(ExpansionMode.DETAIL_FIELD);
    this.setDetailField(AccountsRecord.ACCOUNT_ID);

    // initialise the List Grid fields
    ListGridField iconField = new ListGridField(AccountsRecord.ICON,
        AccountsRecord.ICON_DISPLAY_NAME, ICON_COLUMN_WIDTH);
    iconField.setImageSize(16);
    iconField.setAlign(Alignment.CENTER);
    iconField.setType(ListGridFieldType.IMAGE);
    iconField.setImageURLPrefix(URL_PREFIX);
    iconField.setImageURLSuffix(URL_SUFFIX);

    ListGridField accountNameField = new ListGridField(AccountsRecord.ACCOUNT_NAME,
        Serendipity.getConstants().accountName(), ACCOUNT_NAME_COLUMN_WIDTH);

    ListGridField mainPhoneField = new ListGridField(AccountsRecord.MAIN_PHONE,
        Serendipity.getConstants().mainPhone(), MAIN_PHONE_COLUMN_WIDTH);

    ListGridField locationField = new ListGridField(AccountsRecord.LOCATION,
        Serendipity.getConstants().location(), LOCATION_COLUMN_WIDTH);

    ListGridField primaryContactField = new ListGridField(AccountsRecord.PRIMARY_CONTACT,
        Serendipity.getConstants().primaryContact(), PRIMARY_CONTACT_COLUMN_WIDTH);
    primaryContactField.setType(ListGridFieldType.LINK);

    ListGridField emailPrimaryContactField = new ListGridField(AccountsRecord.EMAIL_PRIMARY_CONTACT,
        Serendipity.getConstants().emailPrimaryContact(), EMAIL_PRIMARY_CONTACT_COLUMN_WIDTH);

    ListGridField emptyField = new ListGridField(EMPTY_FIELD, EMPTY_FIELD_DISPLAY_NAME);

    // set the fields into the List Grid
    this.setFields(new ListGridField[] {iconField, accountNameField, mainPhoneField, locationField,
        primaryContactField, emailPrimaryContactField, emptyField});
  }

  public void setResultSet(List<AccountsDto> accountsDtos) {

    AccountsRecord[] accountsRecords = new AccountsRecord[accountsDtos.size()];

    for (int i = 0; i < accountsDtos.size(); i++) {
      accountsRecords[i] = createAccountsRecord(accountsDtos.get(i));
    }

    // populate the List Grid
    this.setData(accountsRecords);
  }

  private AccountsRecord createAccountsRecord(AccountsDto accountsDto) {
    return new AccountsRecord(ACCOUNT_ICON, accountsDto.getAccountId(), accountsDto.getAccountName(), accountsDto.getMainPhone(),
        accountsDto.getLocation(), accountsDto.getPrimaryContact(), accountsDto.getEmailPrimaryContact());
  }
}

