package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Action;

public class DeleteAccountAction implements Action<DeleteAccountResult> { 

  java.lang.Long accountId;

  public DeleteAccountAction(java.lang.Long accountId) {
    this.accountId = accountId;
  }

  protected DeleteAccountAction() {
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
    DeleteAccountAction other = (DeleteAccountAction) obj;
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
    return "DeleteAccountAction["
                 + accountId
    + "]";
  }
}
