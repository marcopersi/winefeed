package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Result;

public class RetrieveAccountsResult implements Result { 

  java.util.List<au.com.uptick.serendipity.shared.dto.sales.AccountsDto> accountDtos;

  public RetrieveAccountsResult(java.util.List<au.com.uptick.serendipity.shared.dto.sales.AccountsDto> accountDtos) {
    this.accountDtos = accountDtos;
  }

  protected RetrieveAccountsResult() {
    // Possibly for serialization.
  }

  public java.util.List<au.com.uptick.serendipity.shared.dto.sales.AccountsDto> getAccountDtos() {
    return accountDtos;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
        return true;
    if (obj == null)
        return false;
    if (getClass() != obj.getClass())
        return false;
    RetrieveAccountsResult other = (RetrieveAccountsResult) obj;
    if (accountDtos == null) {
      if (other.accountDtos != null)
        return false;
    } else if (!accountDtos.equals(other.accountDtos))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + (accountDtos == null ? 1 : accountDtos.hashCode());
    return hashCode;
  }

  @Override
  public String toString() {
    return "RetrieveAccountsResult["
                 + accountDtos
    + "]";
  }
}
