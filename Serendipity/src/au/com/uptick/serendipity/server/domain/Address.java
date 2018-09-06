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

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

// Don't forget to add the add the following line to persistence.xml:
// <class>au.com.uptick.serendipity.server.domain.Address</class>

@Entity
@Table(name = EntityTokens.ADDRESS_TABLE)
// @Cacheable(true)
public class Address {

  // see BaseEntity.java
  // public class Address extends BaseEntity {

  @Id
  @Column(name = EntityTokens.ADDRESS_ID_COLUMN)
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  protected Long addressId;

  @Column(name = EntityTokens.ADDRESS_NAME_COLUMN, length = EntityTokens.ADDRESS_NAME_COLUMN_LENGTH)
  protected String addressName;

  @Column(name = EntityTokens.ADDRESS_LINE_1_COLUMN, length = EntityTokens.ADDRESS_LINE_COLUMN_LENGTH)
  protected String addressLine1;

  @Column(name = EntityTokens.ADDRESS_LINE_2_COLUMN, length = EntityTokens.ADDRESS_LINE_COLUMN_LENGTH)
  protected String addressLine2;

  @Column(name = EntityTokens.ADDRESS_LINE_3_COLUMN, length = EntityTokens.ADDRESS_LINE_COLUMN_LENGTH)
  protected String addressLine3;

  @Column(name = EntityTokens.CITY_COLUMN, length = EntityTokens.CITY_COLUMN_LENGTH)
  protected String city;

  @Column(name = EntityTokens.STATE_COLUMN, length = EntityTokens.STATE_COLUMN_LENGTH)
  protected String state;

  @Column(name = EntityTokens.POSTAL_CODE_COLUMN, length = EntityTokens.POSTAL_CODE_COLUMN_LENGTH)
  protected String postalCode;

  @Column(name = EntityTokens.COUNTRY_COLUMN, length = EntityTokens.COUNTRY_COLUMN_LENGTH)
  protected String country;

  @Column(name = EntityTokens.ADDRESS_TYPE_COLUMN, length = EntityTokens.ADDRESS_TYPE_COLUMN_LENGTH)
  protected String addressType;

  // JPA requires a no-argument constructor
  public Address() {
    // see BaseEntity.java
    // super();
  }

  public Address(String addressName,
      String addressLine1, String addressLine2, String addressLine3,
      String city, String state, String postalCode,
      String country, String addressType) {
    this.addressName = addressName;
    this.addressLine1 = addressLine1;
    this.addressLine2 = addressLine2;
    this.addressLine3 = addressLine3;
    this.city = city;
    this.state = state;
    this.postalCode = postalCode;
    this.country = country;
    this.addressType = addressType;
  }

  public Long getAddressId() {  // no setter, PK cannot be changed
    return addressId;
  }

  public String getAddressName() {
    return addressName;
  }

  public void setAddressName(String addressName) {
    this.addressName = addressName;
  }

  public String getAddressLine1() {
    return addressLine1;
  }

  public void setAddressLine1(String addressLine1) {
    this.addressLine1 = addressLine1;
  }

  public String getAddressLine2() {
    return addressLine2;
  }

  public void setAddressLine2(String addressLine2) {
    this.addressLine2 = addressLine2;
  }

  public String getAddressLine3() {
    return addressLine3;
  }

  public void setAddressLine3(String addressLine3) {
    this.addressLine3 = addressLine3;
  }

  public String getCity() {
    return city;
  }

  public void setCity(String city) {
    this.city = city;
  }

  public String getState() {
    return state;
  }

  public void setState(String state) {
    this.state = state;
  }

  public String getPostalCode() {
    return postalCode;
  }

  public void setPostalCode(String postalCode) {
    this.postalCode = postalCode;
  }

  public String getCountry() {
    return country;
  }

  public void setCountry(String country) {
    this.country = country;
  }

  public String getAddressType() {
    return addressType;
  }

  public void setAddressType(String addressType) {
    this.addressType = addressType;
  }

  @Override
  public String toString() {
    StringBuilder sb = new StringBuilder();
    sb.append("Name: ").append(getAddressName()).append(" ");
    sb.append("Line 1: ").append(getAddressLine1()).append(" ");
    sb.append("Line 2: ").append(getAddressLine2()).append(" ");
    sb.append("Line 3: ").append(getAddressLine3()).append(" ");
    sb.append("City: ").append(getCity()).append(" ");
    sb.append("State: ").append(getState()).append(" ");
    sb.append("Postal Code: ").append(getPostalCode()).append(" ");
    sb.append("Country: ").append(getCountry()).append(" ");
    sb.append("Address Type").append(getAddressType());

    return sb.toString();
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((addressId == null) ? 0 : addressId.hashCode());
    result = prime * result
        + ((addressLine1 == null) ? 0 : addressLine1.hashCode());
    result = prime * result
        + ((addressLine2 == null) ? 0 : addressLine2.hashCode());
    result = prime * result
        + ((addressLine3 == null) ? 0 : addressLine3.hashCode());
    result = prime * result
        + ((addressName == null) ? 0 : addressName.hashCode());
    result = prime * result
        + ((addressType == null) ? 0 : addressType.hashCode());
    result = prime * result + ((city == null) ? 0 : city.hashCode());
    result = prime * result + ((country == null) ? 0 : country.hashCode());
    result = prime * result
        + ((postalCode == null) ? 0 : postalCode.hashCode());
    result = prime * result + ((state == null) ? 0 : state.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (!(obj instanceof Address))
      return false;
    Address other = (Address) obj;
    if (addressId == null) {
      if (other.addressId != null)
        return false;
    } else if (!addressId.equals(other.addressId))
      return false;
    if (addressLine1 == null) {
      if (other.addressLine1 != null)
        return false;
    } else if (!addressLine1.equals(other.addressLine1))
      return false;
    if (addressLine2 == null) {
      if (other.addressLine2 != null)
        return false;
    } else if (!addressLine2.equals(other.addressLine2))
      return false;
    if (addressLine3 == null) {
      if (other.addressLine3 != null)
        return false;
    } else if (!addressLine3.equals(other.addressLine3))
      return false;
    if (addressName == null) {
      if (other.addressName != null)
        return false;
    } else if (!addressName.equals(other.addressName))
      return false;
    if (addressType == null) {
      if (other.addressType != null)
        return false;
    } else if (!addressType.equals(other.addressType))
      return false;
    if (city == null) {
      if (other.city != null)
        return false;
    } else if (!city.equals(other.city))
      return false;
    if (country == null) {
      if (other.country != null)
        return false;
    } else if (!country.equals(other.country))
      return false;
    if (postalCode == null) {
      if (other.postalCode != null)
        return false;
    } else if (!postalCode.equals(other.postalCode))
      return false;
    if (state == null) {
      if (other.state != null)
        return false;
    } else if (!state.equals(other.state))
      return false;
    return true;
  }
}
