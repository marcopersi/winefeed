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

package au.com.uptick.serendipity.client.sales.account.view;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import com.allen_sauer.gwt.log.client.Log;
import com.smartgwt.client.util.SC;
import com.smartgwt.client.widgets.form.fields.ComboBoxItem;
import com.smartgwt.client.widgets.form.fields.PickerIcon;
import com.smartgwt.client.widgets.form.fields.RowSpacerItem;
import com.smartgwt.client.widgets.form.fields.SectionItem;
import com.smartgwt.client.widgets.form.fields.TextItem;
import com.smartgwt.client.widgets.form.fields.events.FormItemClickHandler;
import com.smartgwt.client.widgets.form.fields.events.FormItemIconClickEvent;

import au.com.uptick.serendipity.client.MultiPageEntryPoint;
import au.com.uptick.serendipity.client.sales.widgets.EntityTab;
import au.com.uptick.serendipity.shared.dto.sales.AccountDto;
import au.com.uptick.serendipity.shared.dto.sales.AddressDto;

public class AccountInformationGeneralTab extends EntityTab {

  private static final String ACCOUNT_NAME = "accountName";
  private static final String ACCOUNT_NUMBER = "accountNumber";
  private static final String PARENT_ACCOUNT = "parentAccount";
  private static final String PRIMARY_CONTACT = "primaryContact";
  private static final String RELATIONSHIP_TYPE = "relationshipType";
  private static final String MAIN_PHONE = "mainPhone";
  private static final String OTHER_PHONE = "otherPhone";
  private static final String FAX = "fax";
  private static final String WEB_SITE = "webSite";
  private static final String EMAIL = "email";

  private static final String ADDRESS_NAME = "addressName";
  private static final String ADDRESS_LINE_1 = "addressLine1";
  private static final String ADDRESS_LINE_2 = "addressLine2";
  private static final String ADDRESS_LINE_3 = "addressLine3";
  private static final String CITY = "city";
  private static final String STATE = "state";
  private static final String POSTAL_CODE = "postalCode";
  private static final String COUNTRY = "country";
  private static final String ADDRESS_TYPE = "addressType";

  // private static final String URL_PREFIX = "flags/16/";
  // private static final String URL_SUFFFIX = ".png";
  // private static final int ICON_HEIGHT = 16;

  protected Long accountId;
  protected TextItem accountName;
  protected TextItem accountNumber;
  protected TextItem parentAccount;
  protected TextItem primaryContact;
  protected ComboBoxItem relationshipType;

  protected TextItem addressName;
  protected TextItem addressLine1;
  protected TextItem addressLine2;
  protected TextItem addressLine3;
  protected TextItem city;
  protected TextItem state;
  protected TextItem postalCode;
  // protected SelectItem country;
  protected ComboBoxItem country;
  protected ComboBoxItem addressType;

  protected TextItem mainPhone;
  protected TextItem otherPhone;
  protected TextItem fax;
  protected TextItem webSite;
  protected TextItem email;

  public AccountInformationGeneralTab() {
    super(MultiPageEntryPoint.getConstants().generalTab());

    //
    // Section 1 Column 1
    //
    accountName = new TextItem(ACCOUNT_NAME, MultiPageEntryPoint.getConstants().accountNameLabel());
    accountName.setSelectOnFocus(true);
    // accountName.setWrapTitle(false);
    // accountName.setDefaultValue("[Account Name]");
    accountName.setRequired(true);

    accountNumber = new TextItem(ACCOUNT_NUMBER, MultiPageEntryPoint.getConstants().accountNumberLabel());

    PickerIcon searchParentAccount = new PickerIcon(PickerIcon.SEARCH, new FormItemClickHandler() {
      public void onFormItemClick(FormItemIconClickEvent event) {
        SC.say("Parent Account clicked!");
      }
    });
    parentAccount = new TextItem(PARENT_ACCOUNT, MultiPageEntryPoint.getConstants().parentAccountLabel());
    parentAccount.setIcons(searchParentAccount);

    PickerIcon searchPrimaryContact = new PickerIcon(PickerIcon.SEARCH, new FormItemClickHandler() {
      public void onFormItemClick(FormItemIconClickEvent event) {
        SC.say("Primary Contact clicked!");
      }
    });
    primaryContact = new TextItem(PRIMARY_CONTACT, MultiPageEntryPoint.getConstants().primaryContactLabel());
    primaryContact.setIcons(searchPrimaryContact);

    relationshipType = new ComboBoxItem(RELATIONSHIP_TYPE, MultiPageEntryPoint.getConstants().relationshipTypeLabel());
    relationshipType.setType("comboBox");
    relationshipType.setValueMap("Active", "Inactive");
    relationshipType.setDefaultToFirstOption(true);

    //
    // Section 1 Column 2
    //
    mainPhone = new TextItem(MAIN_PHONE, MultiPageEntryPoint.getConstants().mainPhoneLabel());
    otherPhone = new TextItem(OTHER_PHONE, MultiPageEntryPoint.getConstants().otherPhoneLabel());
    fax = new TextItem(FAX, MultiPageEntryPoint.getConstants().faxLabel());
    webSite = new TextItem(WEB_SITE, MultiPageEntryPoint.getConstants().webSiteLabel());
    email = new TextItem(EMAIL, MultiPageEntryPoint.getConstants().emailLabel());

    SectionItem generalSection = new SectionItem();
    generalSection.setDefaultValue(MultiPageEntryPoint.getConstants().generalInformationSectionItem());
    generalSection.setItemIds(ACCOUNT_NAME, MAIN_PHONE, ACCOUNT_NUMBER, OTHER_PHONE,
        PARENT_ACCOUNT, FAX, PRIMARY_CONTACT, WEB_SITE, RELATIONSHIP_TYPE, EMAIL);

    //
    // Section 2 Column 1
    //
    addressName = new TextItem(ADDRESS_NAME, MultiPageEntryPoint.getConstants().accountNameLabel());
    addressLine1 = new TextItem(ADDRESS_LINE_1, MultiPageEntryPoint.getConstants().addressLine1Label());
    addressLine2 = new TextItem(ADDRESS_LINE_2, MultiPageEntryPoint.getConstants().addressLine2Label());
    addressLine3 = new TextItem(ADDRESS_LINE_3, MultiPageEntryPoint.getConstants().addressLine3Label());
    city = new TextItem(CITY, MultiPageEntryPoint.getConstants().cityLabel());
    state = new TextItem(STATE, MultiPageEntryPoint.getConstants().stateLabel());

    //
    // Section 2 Column 2
    //
    postalCode = new TextItem(POSTAL_CODE, MultiPageEntryPoint.getConstants().postalCodeLabel());

    /*

    // TO DO - find out why the flag icons arn't working ???
    country = new SelectItem();
    country.setName(COUNTRY);
    country.setTitle(Serendipity.getConstants().countryLabel());
    LinkedHashMap<String, String> valueMap = new LinkedHashMap<String, String>();
    valueMap.put("au", "Australia");
    valueMap.put("nz", "New Zealand");
    country.setValueMap(valueMap);
    // country.setDefaultToFirstOption(true);
    country.setImageURLPrefix(URL_PREFIX);
    country.setImageURLSuffix(URL_SUFFFIX);
    country.setIconHeight(ICON_HEIGHT);

    */

    country = new ComboBoxItem(COUNTRY, MultiPageEntryPoint.getConstants().countryLabel());
    country.setType("comboBox");
    country.setValueMap("Australia", "New Zealand");

    addressType = new ComboBoxItem(ADDRESS_TYPE, MultiPageEntryPoint.getConstants().addressTypeLabel());
    addressType.setType("comboBox");
    addressType.setValueMap("Home", "Business", "Mailing", "Priority", "Other");
    // addressType.setDefaultToFirstOption(true);

    RowSpacerItem rowSpacer1 = new RowSpacerItem("rowSpacer1");
    // just want to skip a column, so don't start a new row
    rowSpacer1.setStartRow(false);

    RowSpacerItem rowSpacer2 = new RowSpacerItem("rowSpacer2");
    // just want to skip a column, so don't start a new row
    rowSpacer2.setStartRow(false);

    SectionItem addressSection = new SectionItem();
    addressSection.setDefaultValue(MultiPageEntryPoint.getConstants().addressInformationSectionItem());
    addressSection.setItemIds(ADDRESS_NAME, POSTAL_CODE, ADDRESS_LINE_1, COUNTRY,
        ADDRESS_LINE_2, ADDRESS_TYPE, ADDRESS_LINE_3, "rowSpacer1", CITY, "rowSpacer2",
        STATE);

    form.setFields(generalSection, accountName, mainPhone, accountNumber,
        otherPhone, parentAccount, fax, primaryContact, webSite, relationshipType,
        email, addressSection, addressName, postalCode,
        addressLine1, country, addressLine2, addressType, addressLine3, rowSpacer1, city,
        rowSpacer2, state);

    this.setPane(form);
  }

  @Override
  public void setFields(Object accountDto) {

    Log.debug("setFields()");

    accountName.setValue(((AccountDto) accountDto).getAccountName());
    accountNumber.setValue(((AccountDto) accountDto).getAccountNumber());

    int size = ((AccountDto) accountDto).getAddresses().size();

    if (size > 0) {
      // the first Address is displayed on the General Tab
      Iterator<AddressDto> it = ((AccountDto) accountDto).getAddresses().iterator();

      AddressDto addressDto = it.next();

      addressName.setValue(addressDto.getAddressName());
      addressLine1.setValue(addressDto.getAddressLine1());
      addressLine2.setValue(addressDto.getAddressLine2());
      addressLine3.setValue(addressDto.getAddressLine3());
      city.setValue(addressDto.getCity());
      state.setValue(addressDto.getState());
      postalCode.setValue(addressDto.getPostalCode());
      country.setValue(addressDto.getCountry());
      addressType.setValue(addressDto.getAddressType());
    }
  }

  @Override
  public void getFields(Object accountDto) {

    Log.debug("getFields()");

    ((AccountDto) accountDto).setAccountName(accountName.getValueAsString());
    ((AccountDto) accountDto).setAccountNumber(accountNumber.getValueAsString());
    // parentAccount;
    // primaryContact;
    // relationshipType;

    // Address Information
    List<AddressDto> addresseDtos = new ArrayList<AddressDto>();
    AddressDto addressDto = new AddressDto();

    addressDto.setAddressName(addressName.getValueAsString());
    addressDto.setAddressLine1(addressLine1.getValueAsString());
    addressDto.setAddressLine2(addressLine2.getValueAsString());
    addressDto.setAddressLine3(addressLine3.getValueAsString());
    addressDto.setCity(city.getValueAsString());
    addressDto.setState(state.getValueAsString());
    addressDto.setPostalCode(postalCode.getValueAsString());
    addressDto.setCountry(country.getValueAsString());
    addressDto.setAddressType(addressType.getValueAsString());

    addresseDtos.add(addressDto);
    ((AccountDto) accountDto).setAddresses(addresseDtos);

    // return accountDto;
  }

}
