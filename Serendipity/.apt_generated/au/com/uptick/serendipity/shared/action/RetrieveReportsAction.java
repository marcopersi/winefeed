package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Action;

public class RetrieveReportsAction implements Action<RetrieveReportsResult> { 

  int maxResults;
  int firstResult;

  public RetrieveReportsAction(int maxResults, int firstResult) {
    this.maxResults = maxResults;
    this.firstResult = firstResult;
  }

  protected RetrieveReportsAction() {
    // Possibly for serialization.
  }

  public int getMaxResults() {
    return maxResults;
  }

  public int getFirstResult() {
    return firstResult;
  }

  @Override
  public String getServiceName() {
    return "dispatch/";
  }

  @Override
  public boolean isSecured() {
    return true;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
        return true;
    if (obj == null)
        return false;
    if (getClass() != obj.getClass())
        return false;
    RetrieveReportsAction other = (RetrieveReportsAction) obj;
    if (maxResults != other.maxResults)
        return false;
    if (firstResult != other.firstResult)
        return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + new Integer(maxResults).hashCode();
    hashCode = (hashCode * 37) + new Integer(firstResult).hashCode();
    return hashCode;
  }

  @Override
  public String toString() {
    return "RetrieveReportsAction["
                 + maxResults
                 + ","
                 + firstResult
    + "]";
  }
}
