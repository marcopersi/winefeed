package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Action;

public class RetrieveAccountAction implements Action<RetrieveAccountResult> { 

  java.lang.Long accountId;

  public RetrieveAccountAction(java.lang.Long accountId) {
    this.accountId = accountId;
  }

  protected RetrieveAccountAction() {
    // Possibly for serialization.
  }

  public java.lang.Long getAccountId() {
    return accountId;
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
    RetrieveAccountAction other = (RetrieveAccountAction) obj;
    if (accountId == null) {
      if (other.accountId != null)
        return false;
    } else if (!accountId.equals(other.accountId))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + (accountId == null ? 1 : accountId.hashCode());
    return hashCode;
  }

  @Override
  public String toString() {
    return "RetrieveAccountAction["
                 + accountId
    + "]";
  }
}
