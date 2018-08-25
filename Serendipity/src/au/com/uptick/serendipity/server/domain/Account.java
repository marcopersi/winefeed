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

package au.com.uptick.serendipity.server.domain;

// Don't forget to add the add the following line to persistence.xml:
// <class>au.com.uptick.serendipity.server.domain.Account</class>

import java.util.Iterator;
import java.util.List;

import javax.persistence.CascadeType;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.FetchType;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.JoinColumn;
import javax.persistence.JoinTable;
import javax.persistence.OneToMany;
import javax.persistence.Table;


/*

   At the time of writing, the Hibernate JPA persistence provider has
   some known issues that can cause problems in web applications such as
   JavaServer Faces applications. While not specific to NetBeans, these
   issues can be worked around by choosing eager as the association fetch
   value and java.util.Set as the collection type in the Mapping Options pane.
   If you use the Hibernate JPA persistence provider and choose default or
   lazy as the association fetch value in the Mapping Options pane, an
   org.hibernate.LazyInitializationException exception can occur at runtime.
   If you choose an association fetch value of eager and you do not also
   choose java.util.Set as the collection type, an org.hibernate.HibernateException
   can occur (with the message "cannot simultaneously fetch multiple bags")
   at runtime. These issues pertain to the Hibernate JPA persistence provider
   and not to the default persistence provider.

*/

@Entity
@Table(name = EntityTokens.ACCOUNT_TABLE)
// @Cacheable(true)
public class Account {

  // see BaseEntity.java
  // public class Account extends BaseEntity {

  // When annotations are placed directly on entity fields it is referred to
  // as field-based access. JPA will persist the nominated fields directly to
  // the database. When using property-based access, the getter and setter
  // methods are used and the corresponding fields are ignored.
  //
  // Starting from JPA 2.0 you can mix access types (field or property)
  // within an entity.

  // Use a surrogate key as the Primary Key for the Entity.
  //
  // Sequencing using identity columns is not recommended in general, since the
  // generated ID is not assigned by the database until the row is inserted
  // (e.g. no preallocation). When managing related objects, the generated ID
  // needs to be retrieved via a select call to the database.
  //
  // Table sequencing provides good performance because it allows for sequence
  // preallocation which is very important to insert performance (e.g. use a
  // large sequence preallocation size and multiple sequence table).

  @Id
  @Column(name = EntityTokens.ACCOUNT_ID_COLUMN)
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  protected Long accountId;

  // When declaring instance variables in your POJOs always use the class type
  // e.g. Long rather than long.

  // Neither JPA nor Hibernate annotations support the notion of a default column value.
  // As a workaround to this limitation, set all default values just before you invoke
  // a Hibernate save() or update() on the session. This closely (short of Hibernate setting
  // the default values) mimics the behaviour of the database which sets default values
  // when it saves a row in a table.
  //
  // Unlike setting the default values in the model class, this approach also ensures that
  // criteria queries that use an Example object as a prototype for the search will continue
  // to work as before. When you set the default value of a nullable attribute (one that has
  // a non-primitive type) in a model class, a Hibernate query-by-example will no longer ignore
  // the associated column where previously it would ignore it because it was null.

  @Column(name = EntityTokens.ACCOUNT_NAME_COLUMN, length = EntityTokens.ACCOUNT_NAME_COLUMN_LENGTH)
  protected String accountName;

  @Column(name = EntityTokens.ACCOUNT_NUMBER_COLUMN, length = EntityTokens.ACCOUNT_NUMBER_COLUMN_LENGTH)
  protected String accountNumber;

  @Column(name = EntityTokens.PARENT_ACCOUNT_COLUMN, length = EntityTokens.PARENT_ACCOUNT_COLUMN_LENGTH)
  protected String parentAccount;

  @Column(name = EntityTokens.PRIMARY_CONTACT_COLUMN, length = EntityTokens.PRIMARY_CONTACT_COLUMN_LENGTH)
  protected String primaryContact;

  @Column(name = EntityTokens.EMAIL_PRIMARY_CONTACT_COLUMN, length = EntityTokens.EMAIL_PRIMARY_CONTACT_COLUMN_LENGTH)
  protected String emailPrimaryContact;

  protected String relationshipType;

  // Address details
  @OneToMany(fetch = FetchType.EAGER, cascade = CascadeType.ALL)
  @JoinTable(name = EntityTokens.ACCOUNT_ADDRESS_JOIN_TABLE,
      joinColumns = {@JoinColumn(name = EntityTokens.ACCOUNT_ID_COLUMN)},
      inverseJoinColumns = {@JoinColumn(name = EntityTokens.ADDRESS_ID_COLUMN)})
  protected List<Address> addresses;

  // Electronic Address details
  @Column(name = EntityTokens.MAIN_PHONE_COLUMN, length = EntityTokens.MAIN_PHONE_COLUMN_LENGTH)
  protected String mainPhone;
  protected String fax;
  protected String otherPhone;
  protected String webSite;
  protected String email;

  // JPA requires a no-argument constructor
  public Account() {
    // see BaseEntity.java
    // super();
  }

  public Account(Long accountId) {
    this.accountId = accountId;
  }

  public Long getAccountId() {  // no setter, PK cannot be changed
    return accountId;
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

  public String getEmailPrimaryContact() {
    return emailPrimaryContact;
  }

  public void setEmailPrimaryContact(String emailPrimaryContact) {
    this.emailPrimaryContact = emailPrimaryContact;
  }

  public String getRelationshipType() {
    return relationshipType;
  }

  public void setRelationshipType(String relationshipType) {
    this.relationshipType = relationshipType;
  }

  public String getMainPhone() {
    return mainPhone;
  }

  public void setMainPhone(String mainPhone) {
    this.mainPhone = mainPhone;
  }

  public String getFax() {
    return fax;
  }

  public void setFax(String fax) {
    this.fax = fax;
  }

  public String getOtherPhone() {
    return otherPhone;
  }

  public void setOtherPhone(String otherPhone) {
    this.otherPhone = otherPhone;
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

  public List<Address> getAddresses() {
    return addresses;
  }

  public void setAddresses(List<Address> addresses) {
    this.addresses = addresses;
  }

  /*

  // Address details
  protected String addressName;
  protected String addressLine1;
  protected String addressLine2;
  protected String addressLine3;
  protected String city;
  protected String state;
  protected String postalCode;
  protected String country;
  protected String addressType;

  */

  public String getLocation() {

    if (addresses == null || (addresses.size() == 0)) {
      return "No Address details";
    }

    StringBuilder sb = new StringBuilder();
    String addressElement;

    Iterator<Address> it = addresses.iterator();
    Address address = it.next();

    addressElement = address.getAddressLine1();
    sb.append(addressElement).append(", ");
    addressElement = address.getAddressLine2();
    sb.append(addressElement).append(" ");
    addressElement = address.getCity();
    sb.append(addressElement).append(" ");
    addressElement = address.getState();
    sb.append(addressElement).append(" ");
    addressElement = address.getPostalCode();
    sb.append(addressElement);

    // e.g. "Level 111, 111 Kent Street Sydney NSW 2000"
    return sb.toString();
  }

  @Override
  public String toString() {
    StringBuilder sb = new StringBuilder();
    sb.append("Id: ").append(getAccountId()).append(", ");
    sb.append("Name: ").append(getAccountName()).append(", ");
    sb.append("Number: ").append(getAccountNumber()).append(", ");

    sb.append("Address: ").append(getLocation());

    return sb.toString();
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((accountName == null) ? 0 : accountName.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (!(obj instanceof Account))
      return false;
    Account other = (Account) obj;
    if (accountId == null) {
      if (other.accountId != null)
        return false;
    } else if (!accountId.equals(other.accountId))
      return false;
    if (accountName == null) {
      if (other.accountName != null)
        return false;
    } else if (!accountName.equals(other.accountName))
      return false;
    if (accountNumber == null) {
      if (other.accountNumber != null)
        return false;
    } else if (!accountNumber.equals(other.accountNumber))
      return false;
    return true;
  }
}
