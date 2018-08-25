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

public class ReportsDto implements Serializable {

  private static final long serialVersionUID = -9050049510672663966L;

  protected Long reportId;
  protected String reportName;
  protected String entityName;
  protected String reportFilename;
  protected String reportType;
  protected String modifiedOn;
  protected String description;

  public ReportsDto() {
    this.reportId = -1L;
  }

  public ReportsDto(Long reportId) {
    this.reportId = reportId;
  }

  public ReportsDto(Long reportId, String reportName, String entityName, String reportFilename,
      String reportType, String modifiedOn, String description) {
    this.reportId = reportId;
    this.reportName = reportName;
    this.entityName = entityName;
    this.reportFilename = reportFilename;
    this.reportType = reportType;
    this.modifiedOn = modifiedOn;
    this.description = description;
  }

  public Long getReportId() {
    return reportId;
  }

  public void setReportId(Long reportId) {
    this.reportId = reportId;
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

  public String getModifiedOn() {
    return modifiedOn;
  }

  public void setModifiedOn(String modifiedOn) {
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
    builder.append("ReportsDto [reportId=");
    builder.append(reportId);
    builder.append(", reportName=");
    builder.append(reportName);
    builder.append(", reportFilename=");
    builder.append(reportFilename);
    builder.append(", reportType=");
    builder.append(reportType);
    builder.append(", modifiedOn=");
    builder.append(modifiedOn);
    builder.append(", description=");
    builder.append(description);
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
    if (!(obj instanceof ReportsDto))
      return false;
    ReportsDto other = (ReportsDto) obj;
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
