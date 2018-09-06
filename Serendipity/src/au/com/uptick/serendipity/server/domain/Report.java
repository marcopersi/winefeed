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
// <class>au.com.uptick.serendipity.server.domain.Report</class>

import java.util.Date;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import javax.persistence.Temporal;
import javax.persistence.TemporalType;

@Entity
@Table(name = EntityTokens.REPORT_TABLE)
// @Cacheable(true)
public class Report {

  // see BaseEntity.java
  // public class Report extends BaseEntity {

  @Id
  @Column(name = EntityTokens.REPORT_ID_COLUMN)
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  protected Long reportId;

  @Column(name = EntityTokens.REPORT_NAME_COLUMN, length = EntityTokens.REPORT_NAME_COLUMN_LENGTH)
  protected String reportName;

  @Column(name = EntityTokens.ENTITY_NAME_COLUMN, length = EntityTokens.ENTITY_NAME_COLUMN_LENGTH)
  protected String entityName;

  @Column(name = EntityTokens.REPORT_FILENAME_COLUMN, length = EntityTokens.REPORT_FILENAME_COLUMN_LENGTH)
  protected String reportFilename;

  @Column(name = EntityTokens.REPORT_TYPE_COLUMN, length = EntityTokens.REPORT_TYPE_COLUMN_LENGTH)
  protected String reportType;

  @Column(name = EntityTokens.MODIFIED_ON_COLUMN, nullable = EntityTokens.MODIFIED_ON_COLUMN_NULLABLE)
  @Temporal(TemporalType.TIMESTAMP)
  protected Date modifiedOn;

  @Column(name = EntityTokens.DESCRIPTION_COLUMN, length = EntityTokens.DESCRIPTION_COLUMN_LENGTH)
  protected String description;

  // JPA requires a no-argument constructor
  public Report() {
    // see BaseEntity.java
    // super();
  }

  public Report(Long reportId) {
    this.reportId = reportId;
  }

  public Long getReportId() { // no setter, PK cannot be changed
    return reportId;
  }

  public String getReportName() {
    return reportName;
  }

  public void setReportName(String reportName) {
    this.reportName = reportName;
  }

  public String getEntityName() {
    return entityName;
  }

  public void setEntityName(String entityName) {
    this.entityName = entityName;
  }

  public String getReportFilename() {
    return reportFilename;
  }

  public void setReportFilename(String reportFilename) {
    this.reportFilename = reportFilename;
  }

  public String getReportType() {
    return reportType;
  }

  public void setReportType(String reportType) {
    this.reportType = reportType;
  }

  public Date getModifiedOn() {
    return modifiedOn;
  }

  public void setModifiedOn(Date modifiedOn) {
    this.modifiedOn = modifiedOn;
  }

  public String getDescription() {
    return description;
  }

  public void setDescription(String description) {
    this.description = description;
  }

  @Override
  public String toString() {
    StringBuilder builder = new StringBuilder();
    builder.append("Report [reportId=");
    builder.append(reportId);
    builder.append(", reportName=");
    builder.append(reportName);
    builder.append(", reportType=");
    builder.append(reportType);
    builder.append(", reportFilename=");
    builder.append(reportFilename);
    builder.append("]");
    return builder.toString();
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((reportName == null) ? 0 : reportName.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (!(obj instanceof Report))
      return false;
    Report other = (Report) obj;
    if (description == null) {
      if (other.description != null)
        return false;
    } else if (!description.equals(other.description))
      return false;
    if (modifiedOn == null) {
      if (other.modifiedOn != null)
        return false;
    } else if (!modifiedOn.equals(other.modifiedOn))
      return false;
    if (reportFilename == null) {
      if (other.reportFilename != null)
        return false;
    } else if (!reportFilename.equals(other.reportFilename))
      return false;
    if (reportId == null) {
      if (other.reportId != null)
        return false;
    } else if (!reportId.equals(other.reportId))
      return false;
    if (reportName == null) {
      if (other.reportName != null)
        return false;
    } else if (!reportName.equals(other.reportName))
      return false;
    if (reportType == null) {
      if (other.reportType != null)
        return false;
    } else if (!reportType.equals(other.reportType))
      return false;
    return true;
  }
}
