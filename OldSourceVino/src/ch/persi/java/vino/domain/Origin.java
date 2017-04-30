package ch.persi.java.vino.domain;

public enum Origin {
	
	ACMC("AC/MC"),
	
	ACMO("AC/MO"),
	
	ACEA("AC/EA"),
	
	MO("MO"),
	
	DOMO("DO/MO"),
	
	MOIGT("MO/IGT"),
	
	MODOC("MO/DOC"),
	
	MODOCG("MO/DOCG");
	
	
	private String originIdentifier;
	
	Origin(String theOriginIdentifier)
	{
		originIdentifier=theOriginIdentifier;
	}
	
	public String getOriginIdentifier()
	{
		return originIdentifier;
	}
	
}

