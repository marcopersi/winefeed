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

import java.sql.Timestamp;
import java.util.Date;
import javax.persistence.PrePersist;
import javax.persistence.PreUpdate;

public class BaseEntityListener {
  
  private static final String DEFAULT_USER_NAME = "Administrator";  

  // Insert auditing fields

  @PrePersist
  public void insertAuditingField(Object obj) {
    if (!(obj instanceof BaseEntity)) {
      return;
    }

    BaseEntity baseEntity = (BaseEntity) obj;
    Timestamp currentTime = new Timestamp(new Date().getTime());
    baseEntity.setCreatedTimestamp(currentTime);
    baseEntity.setUpdatedTimestamp(currentTime);

    String user = RequestContext.getLocalInstance().getUserName();
    if (user == null) {
      user = DEFAULT_USER_NAME; 
    }
    
    baseEntity.setCreatedBy(user);
    baseEntity.setUpdatedBy(user); 
  }

  // Update auditing fields

  @PreUpdate
  public void updateAuditingField(Object obj) {
    if (!(obj instanceof BaseEntity)) {
      return;
    }

    BaseEntity baseEntity = (BaseEntity) obj;
    Timestamp currentTime = new Timestamp(new Date().getTime());
    baseEntity.setUpdatedTimestamp(currentTime);

    String user = RequestContext.getLocalInstance().getUserName();
    if (user == null) {
      user = DEFAULT_USER_NAME;
    }
    
    baseEntity.setUpdatedBy(user); 
  }
}
