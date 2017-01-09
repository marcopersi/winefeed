package ch.persi.java.vino.domain;

import java.math.BigDecimal;

import org.apache.commons.lang3.builder.ReflectionToStringBuilder;

public class RatingAgency {

	private BigDecimal maxPoints;
	private long id;
	private String ratingAgencyName; 
	
	public RatingAgency()
	{
		super();
	}
	
	public RatingAgency(BigDecimal theMaximumPoints, String theRatingAgencyName) {
		super();
		this.maxPoints = theMaximumPoints;
		this.ratingAgencyName = theRatingAgencyName;
	}

	public String getRatingAgencyName() {
		return ratingAgencyName;
	}

	public void setRatingAgencyName(String theRatingAgencyName) {
		this.ratingAgencyName = theRatingAgencyName;
	}

	public BigDecimal getMaxPoints() {
		return maxPoints;
	}

	public void setMaxPoints(BigDecimal theMaximumPoints) {
		this.maxPoints = theMaximumPoints;
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
