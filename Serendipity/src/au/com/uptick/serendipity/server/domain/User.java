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
import javax.persistence.Id;
import javax.persistence.Table;

// Don't forget to add the add the following line to persistence.xml:
// <class>au.com.uptick.serendipity.server.domain.User</class>

@Entity
@Table(name = EntityTokens.USER_TABLE)
// @Cacheable(true)
public class User {

  // see BaseEntity.java
  // public class User extends BaseEntity {

  @Id
  @Column(name = EntityTokens.LOGIN_COLUMN, length = EntityTokens.LOGIN_COLUMN_LENGTH)
  protected String login;

  @Column(name = EntityTokens.SALT_COLUMN, length = EntityTokens.SALT_COLUMN_LENGTH)
  protected String salt;

  @Column(name = EntityTokens.PASSWORD_COLUMN, length = EntityTokens.PASSWORD_COLUMN_LENGTH)
  protected String password;

  // JPA requires a no-argument constructor
  public User() {
    // see BaseEntity.java
    // super();
  }

  public User(String login, String salt, String password) {
    this.login = login;
    this.salt = salt;
    this.password = password;
  }

  // public String getUsername()

  public String getLogin() {
    return login;
  }

  public void setLogin(String login) {
    this.login = login;
  }

  public String getSalt() {
    return salt;
  }

  public void setSalt(String salt) {
    this.salt = salt;
  }

  public String getPassword() {
    return password;
  }

  public void setPassword(String password) {
    this.password = password;
  }

  // public String getAuthorities();

  // public String getUsername();

  public boolean isAccountNonExpired() {
    return true;
  }

  public boolean isAccountNonLocked() {
    return true;
  }

  public boolean isCredentialsNonExpired() {
    return true;
  }

  public boolean isEnabled() {
    return true;
  }

  @Override
  public String toString() {
    StringBuilder builder = new StringBuilder();
    builder.append("User [login=");
    builder.append(login);
    builder.append(", salt=");
    builder.append(salt);
    builder.append(", password=");
    builder.append(password);
    builder.append("]");
    return builder.toString();
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((login == null) ? 0 : login.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (!(obj instanceof User))
      return false;
    User other = (User) obj;
    if (login == null) {
      if (other.login != null)
        return false;
    } else if (!login.equals(other.login))
      return false;
    if (password == null) {
      if (other.password != null)
        return false;
    } else if (!password.equals(other.password))
      return false;
    if (salt == null) {
      if (other.salt != null)
        return false;
    } else if (!salt.equals(other.salt))
      return false;
    return true;
  }
}
