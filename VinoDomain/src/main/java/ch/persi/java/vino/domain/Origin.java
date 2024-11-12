package ch.persi.java.vino.domain;

public enum Origin {
	
	ACMC("AC/MC"),
	
	ACMO("AC/MO"),
	
	ACEA("AC/EA"),
		
	DOMO("DO/MO"),
	
	MODO("MO/DO"),
	
	MOIGT("MO/IGT"),
	
	MODOC("MO/DOC"),
	
	MODOCG("MO/DOCG"),
	
	MODOCA("MO/DOCA"),
	
	MODOCa("MO/DOCa"),
	
	MO("MO");
	
	private final String originIdentifier;
	
	Origin(String theOriginIdentifier)
	{
		originIdentifier=theOriginIdentifier;
	}
	
	public String getOriginIdentifier()
	{
		return originIdentifier;
	}
	
}

