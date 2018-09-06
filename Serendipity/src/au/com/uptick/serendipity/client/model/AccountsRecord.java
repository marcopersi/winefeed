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

package au.com.uptick.serendipity.client.model;

import com.smartgwt.client.widgets.grid.ListGridRecord;

public class AccountsRecord extends ListGridRecord {

  public static final String ICON = "icon";
  public static final String ICON_DISPLAY_NAME = "#";
  public static final String ACCOUNT_ID = "accountId";
  public static final String ACCOUNT_NAME = "accountName";
  public static final String MAIN_PHONE = "mainPhone";
  public static final String LOCATION = "location";
  public static final String PRIMARY_CONTACT = "primaryContact";
  public static final String EMAIL_PRIMARY_CONTACT = "emailPrimaryContact";

  public AccountsRecord() { }

  public AccountsRecord(String icon,
      Long accountId,
      String accountName,
      String mainPhone,
      String location,
      String primaryContact,
      String emailPrimaryContact) {
    setIcon(icon);
    setAccountId(accountId);
    setAccountName(accountName);
    setMainPhone(mainPhone);
    setLocation(location);
    setPrimaryContact(primaryContact);
    setEmailPrimaryContact(emailPrimaryContact);
  }

  public void setIcon(String attribute) {
    setAttribute(ICON, attribute);
  }

  public void setAccountId(Long attribute) {
    setAttribute(ACCOUNT_ID, attribute);
  }

  public void setAccountName(String attribute) {
    setAttribute(ACCOUNT_NAME, attribute);
  }

  public void setMainPhone(String attribute) {
    setAttribute(MAIN_PHONE, attribute);
  }

  public void setLocation(String attribute) {
    setAttribute(LOCATION, attribute);
  }

  public void setPrimaryContact(String primaryContact) {
    setAttribute(PRIMARY_CONTACT, primaryContact);
  }

  public void setEmailPrimaryContact(String emailPrimaryContact) {
    setAttribute(EMAIL_PRIMARY_CONTACT, emailPrimaryContact);
  }

  public String getIcon() {
    return getAttributeAsString(ICON);
  }

  public Long getAccountId() {
    return (Long) getAttributeAsObject(ACCOUNT_ID);
  }

  public String getAccountName() {
    return getAttributeAsString(ACCOUNT_NAME);
  }

  public String getMainPhone() {
    return getAttributeAsString(MAIN_PHONE);
  }

  public String getLocation() {
    return getAttributeAsString(LOCATION);
  }

  public String getPrimaryContact() {
    return getAttributeAsString(PRIMARY_CONTACT);
  }

  public String getEmailPrimaryContact() {
    return getAttributeAsString(EMAIL_PRIMARY_CONTACT);
  }
}
