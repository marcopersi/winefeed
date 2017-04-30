package ch.persi.java.vino.domain;

import java.math.BigDecimal;

import org.apache.commons.lang3.builder.ReflectionToStringBuilder;

public class Rating {

	private RatingAgency agency;
	private BigDecimal score;
	private long id;
	private Wine wine;

	public Rating()
	{
		super();
	}
	
	public Rating(RatingAgency theAgency, BigDecimal theScore) {
		super();
		this.agency = theAgency;
		this.score = theScore;
	}
	public Wine getWine() {
		return wine;
	}
	
	public void setWine(Wine theWine) {
		this.wine = theWine;
	}
	public RatingAgency getAgency() {
		return agency;
	}
	public void setAgency(RatingAgency theAgency) {
		this.agency = theAgency;
	}
	public BigDecimal getScore() {
		return score;
	}
	public void setScore(BigDecimal theScore) {
		this.score = theScore;
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
		ReflectionToStringBuilder aBuilder = new ReflectionToStringBuilder(this);
		return aBuilder.toString();		
	}
	
}
