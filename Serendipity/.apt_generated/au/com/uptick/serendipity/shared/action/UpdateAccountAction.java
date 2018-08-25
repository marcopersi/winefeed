package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Action;

public class UpdateAccountAction implements Action<UpdateAccountResult> { 

  au.com.uptick.serendipity.shared.dto.sales.AccountDto accountDto;

  public UpdateAccountAction(au.com.uptick.serendipity.shared.dto.sales.AccountDto accountDto) {
    this.accountDto = accountDto;
  }

  protected UpdateAccountAction() {
    // Possibly for serialization.
  }

  public au.com.uptick.serendipity.shared.dto.sales.AccountDto getAccountDto() {
    return accountDto;
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
    UpdateAccountAction other = (UpdateAccountAction) obj;
    if (accountDto == null) {
      if (other.accountDto != null)
        return false;
    } else if (!accountDto.equals(other.accountDto))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + (accountDto == null ? 1 : accountDto.hashCode());
    return hashCode;
  }

  @Override
  public String toString() {
    return "UpdateAccountAction["
                 + accountDto
    + "]";
  }
}
