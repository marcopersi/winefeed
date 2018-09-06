package au.com.uptick.serendipity.shared.action;

import com.gwtplatform.dispatch.shared.Result;

public class LoginResult implements Result { 

  java.lang.String sessionKey;

  public LoginResult(java.lang.String sessionKey) {
    this.sessionKey = sessionKey;
  }

  protected LoginResult() {
    // Possibly for serialization.
  }

  public java.lang.String getSessionKey() {
    return sessionKey;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
        return true;
    if (obj == null)
        return false;
    if (getClass() != obj.getClass())
        return false;
    LoginResult other = (LoginResult) obj;
    if (sessionKey == null) {
      if (other.sessionKey != null)
        return false;
    } else if (!sessionKey.equals(other.sessionKey))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 23;
    hashCode = (hashCode * 37) + (sessionKey == null ? 1 : sessionKey.hashCode());
    return hashCode;
  }

  @Override
  public String toString() {
    return "LoginResult["
                 + sessionKey
    + "]";
  }
}
