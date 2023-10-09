
package ch.persi.java.vino.domain;

public enum Provider {

  STEINFELS("Steinfels"),

  WERMUTH("WermuthSA"),

  WEINBOERSE("Weinboerse"),

  SOTHEBYS("Sothebys");

  private String provider;

  Provider(String theProviderCode) {
    provider = theProviderCode;
  }

  public String getProviderCode() {
    return provider;
  }

}
