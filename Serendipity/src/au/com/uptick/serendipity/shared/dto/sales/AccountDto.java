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

package au.com.uptick.serendipity.shared.dto.sales;

import java.io.Serializable;
import java.util.List;

public class AccountDto implements Serializable {

  private static final long serialVersionUID = 3434148714982575460L;

  protected Long accountId;
  protected String accountName;
  protected String accountNumber;
  protected String parentAccount;
  protected String primaryContact;
  // protected String emailPrimaryContact;
  protected String relationshipType;

  // Address details
  protected List<AddressDto> addresses;

  // Electronic Address details
  protected String mainPhone;
  protected String otherPhone;
  protected String fax;
  protected String webSite;
  protected String email;

  public AccountDto() {
    this.accountId = -1L;
  }

  public AccountDto(Long accountId) {
    this.accountId = accountId;
  }

  public Long getAccountId() {
    return accountId;
  }

  public void setAccountId(Long accountId) {
    this.accountId = accountId;
  }

  public String getAccountName() {
    return accountName;
  }

  public void setAccountName(String accountName) {
    this.accountName = accountName;
  }

  public String getAccountNumber() {
    return accountNumber;
  }

  public void setAccountNumber(String accountNumber) {
    this.accountNumber = accountNumber;
  }

  public String getParentAccount() {
    return parentAccount;
  }

  public void setParentAccount(String parentAccount) {
    this.parentAccount = parentAccount;
  }

  public String getPrimaryContact() {
    return primaryContact;
  }

  public void setPrimaryContact(String primaryContact) {
    this.primaryContact = primaryContact;
  }

  public String getRelationshipType() {
    return relationshipType;
  }

  public void setRelationshipType(String relationshipType) {
    this.relationshipType = relationshipType;
  }

  public List<AddressDto> getAddresses() {
    return addresses;
  }

  public void setAddresses(List<AddressDto> addresses) {
    this.addresses = addresses;
  }

  public String getMainPhone() {
    return mainPhone;
  }

  public void setMainPhone(String mainPhone) {
    this.mainPhone = mainPhone;
  }

  public String getOtherPhone() {
    return otherPhone;
  }

  public void setOtherPhone(String otherPhone) {
    this.otherPhone = otherPhone;
  }

  public String getFax() {
    return fax;
  }

  public void setFax(String fax) {
    this.fax = fax;
  }

  public String getWebSite() {
    return webSite;
  }

  public void setWebSite(String webSite) {
    this.webSite = webSite;
  }

  public String getEmail() {
    return email;
  }

  public void setEmail(String email) {
    this.email = email;
  }
}
