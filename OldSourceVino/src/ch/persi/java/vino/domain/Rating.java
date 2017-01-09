package ch.persi.java.vino.domain;

import java.math.BigDecimal;

public class Rating {

	private RatingAgency agency;
	private BigDecimal score;
	private long id;
	private Wine wine;

	public Rating()
	{
		super();
	}
	
	public Rating(RatingAgency agency, BigDecimal score) {
		super();
		this.agency = agency;
		this.score = score;
	}
	public Wine getWine() {
		return wine;
	}
	
	public void setWine(Wine wine) {
		this.wine = wine;
	}
	public RatingAgency getAgency() {
		return agency;
	}
	public void setAgency(RatingAgency agency) {
		this.agency = agency;
	}
	public BigDecimal getScore() {
		return score;
	}
	public void setScore(BigDecimal score) {
		this.score = score;
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
		aBuilder.append("agency=");
		aBuilder.append(this.agency.getRatingAgencyName());
		aBuilder.append(",");
		aBuilder.append("score=");
		aBuilder.append(this.score);
		aBuilder.append(",");
		return aBuilder.toString();		
	}
	
}
