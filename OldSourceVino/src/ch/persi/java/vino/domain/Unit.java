package ch.persi.java.vino.domain;

import java.math.BigDecimal;

public class Unit {

	private BigDecimal deciliters;
	private long id;

	public Unit()
	{
		super();
	}
	
	public Unit(BigDecimal deciliters) {
		super();
		this.deciliters = deciliters;
	}

	public BigDecimal getDeciliters() {
		return deciliters;
	}

	public void setDeciliters(BigDecimal deciliters) {
		this.deciliters = deciliters;
	}


	public long getId() {
		return id;
	}


	public void setId(long id) {
		this.id = id;
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
