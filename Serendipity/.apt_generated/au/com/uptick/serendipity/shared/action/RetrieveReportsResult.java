package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Result;

public class RetrieveReportsResult implements Result { 

  java.util.List<au.com.uptick.serendipity.shared.dto.sales.ReportsDto> reportDtos;

  public RetrieveReportsResult(java.util.List<au.com.uptick.serendipity.shared.dto.sales.ReportsDto> reportDtos) {
    this.reportDtos = reportDtos;
  }

  protected RetrieveReportsResult() {
    // Possibly for serialization.
  }

  public java.util.List<au.com.uptick.serendipity.shared.dto.sales.ReportsDto> getReportDtos() {
    return reportDtos;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
        return true;
    if (obj == null)
        return false;
    if (getClass() != obj.getClass())
        return false;
    RetrieveReportsResult other = (RetrieveReportsResult) obj;
    if (reportDtos == null) {
      if (other.reportDtos != null)
        return false;
    } else if (!reportDtos.equals(other.reportDtos))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + (reportDtos == null ? 1 : reportDtos.hashCode());
    return hashCode;
  }

  @Override
  public String toString() {
    return "RetrieveReportsResult["
                 + reportDtos
    + "]";
  }
}
