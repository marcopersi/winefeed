package ch.persi.java.vino.domain;

public enum Provider {

	STEINFELS("Steinfels"),
	
	WERMUTH("Wermuth SA."),
	
	WEINBOERSE("Weinboerse");
	
	
	private String provider;

	Provider (String theProviderCode)
	{
		provider = theProviderCode;
	}
	
	public String getProviderCode()
	{
		return provider;
	}
	
}
