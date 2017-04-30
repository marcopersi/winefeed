package ch.persi.java.vino.domain;


public enum Month {

	JAN("Januar", 1),
	FEB("Februar",2),
	MAR("März",3),
	APR("April",4),
	MAY("Mai",5),
	JUN("Juni",6),
	JUL("Juli",7),
	AUG("August",8),
	SEP("September",9),
	OCT("Oktober",10),
	NOV("November",11),
	DEC("Dezember",12);
	
	
	
	private String anIdentifier;
	private int monthOfYear;

	public String getAnIdentifier() {
		return anIdentifier;
	}

	public void setAnIdentifier(String theIdentifier) {
		this.anIdentifier = theIdentifier;
	}

	public int getMonthOfYear() {
		return monthOfYear;
	}

	public void setMonthOfYear(int theMonthOfYear) {
		this.monthOfYear = theMonthOfYear;
	}

	Month(String theMonthIdentifier, int theMonthOfYear)
	{
		anIdentifier = theMonthIdentifier;
		monthOfYear=theMonthOfYear;
	}
}
