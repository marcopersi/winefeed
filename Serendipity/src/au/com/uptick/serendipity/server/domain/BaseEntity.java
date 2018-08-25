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

import java.util.Date;

import javax.persistence.Column;
import javax.persistence.MappedSuperclass;
import javax.persistence.Temporal;
import javax.persistence.TemporalType;
import javax.persistence.Version;

// Don't forget to add the add the following line to persistence.xml:
// <class>au.com.uptick.serendipity.server.domain.BaseEntity</class>

// If you want support for version and auditing fields then place them in
// a super class so they can be inherited by the other entities.
// For example:
//
// @Entity
// public class Account extends BaseEntity { ... }
//

// @EntityListeners(BaseEntityListener.class)
@MappedSuperclass
public class BaseEntity {

  @Version
  @Column(name = EntityTokens.VERSION_COLUMN, nullable = EntityTokens.VERSION_COLUMN_NULLABLE)
  protected Integer version;

  @Column(name = EntityTokens.CREATED_BY_COLUMN, length = EntityTokens.CREATED_BY_COLUMN_LENGTH,
      nullable = EntityTokens.CREATED_BY_COLUMN_NULLABLE)
  protected String createdBy;

  @Column(name = EntityTokens.CREATED_TIMESTAMP_COLUMN, nullable = EntityTokens.CREATED_TIMESTAMP_COLUMN_NULLABLE)
  @Temporal(TemporalType.TIMESTAMP)
  protected Date createdTimestamp;

  @Column(name = EntityTokens.UPDATED_BY_COLUMN, length = EntityTokens.UPDATED_BY_COLUMN_LENGTH,
      nullable = EntityTokens.UPDATED_BY_COLUMN_NULLABLE)
  protected String updatedBy;

  @Column(name = EntityTokens.UPDATED_TIMESTAMP_COLUMN, nullable = EntityTokens.UPDATED_TIMESTAMP_COLUMN_NULLABLE)
  @Temporal(TemporalType.TIMESTAMP)
  protected Date updatedTimestamp;

  public Integer getVersion() {
    return version;
  }

  public void setVersion(Integer version) {
    this.version = version;
  }

  public String getCreatedBy() {
    return createdBy;
  }

  public void setCreatedBy(String createdBy) {
    this.createdBy = createdBy;
  }

  public Date getCreatedTimestamp() {
    return createdTimestamp;
  }

  public void setCreatedTimestamp(Date createdTimestamp) {
    this.createdTimestamp = createdTimestamp;
  }

  public String getUpdatedBy() {
    return updatedBy;
  }

  public void setUpdatedBy(String updatedBy) {
    this.updatedBy = updatedBy;
  }

  public Date getUpdatedTimestamp() {
    return updatedTimestamp;
  }

  public void setUpdatedTimestamp(Date updatedTimestamp) {
    this.updatedTimestamp = updatedTimestamp;
  }

  @Override
  public String toString() {
    StringBuilder sb = new StringBuilder();
    sb.append("Created By: ").append(createdBy).append(", ");
    sb.append("Created Timestamp: ").append(createdTimestamp).append(", ");
    sb.append("Updated By: ").append(updatedBy).append(", ");
    sb.append("Update Timestamp: ").append(updatedTimestamp).append(", ");
    sb.append("Version: ").append(version);

    return sb.toString();
  }
}
