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
	
	public RatingAgency(BigDecimal maxPoints, String ratingAgencyName) {
		super();
		this.maxPoints = maxPoints;
		this.ratingAgencyName = ratingAgencyName;
	}

	public String getRatingAgencyName() {
		return ratingAgencyName;
	}

	public void setRatingAgencyName(String ratingAgencyName) {
		this.ratingAgencyName = ratingAgencyName;
	}

	public BigDecimal getMaxPoints() {
		return maxPoints;
	}

	public void setMaxPoints(BigDecimal maxPoints) {
		this.maxPoints = maxPoints;
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
		ReflectionToStringBuilder aBuilder = new ReflectionToStringBuilder(this);
		return aBuilder.toString();		
	}
}
