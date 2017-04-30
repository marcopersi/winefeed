package ch.persi.java.vino.domain;

import java.math.BigDecimal;

public class Unit {

	private BigDecimal deciliters;
	private long id;

	public Unit()
	{
		super();
	}
	
	public Unit(BigDecimal theDeciliters) {
		super();
		this.deciliters = theDeciliters;
	}

	public BigDecimal getDeciliters() {
		return deciliters;
	}

	public void setDeciliters(BigDecimal theDeciliters) {
		this.deciliters = theDeciliters;
	}


	public long getId() {
		return id;
	}


	public void setId(long theId) {
		this.id = theId;
	}
	
	@Override
	public String toString()
	{
		StringBuilder aBuilder = new StringBuilder();
		aBuilder.append("deciliters=");
		aBuilder.append(this.deciliters);
		return aBuilder.toString();		
	}
}
