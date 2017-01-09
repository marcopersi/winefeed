package ch.persi.java.vino.domain;

import java.math.BigDecimal;
import java.text.SimpleDateFormat;
import java.util.Date;

public class Offering {
	
	private Provider provider;
	private String providerOfferingId;
	
	private BigDecimal priceMin;
	private BigDecimal priceMax;
	private Date offeringDate;
	private long id;
	private BigDecimal realizedPrice;
	private boolean isOHK;
	private String note;
	private String eventIdentifier;
	private int noOfBottles;
	
	/**
	 * default constructor for hibernate
	 */
	public Offering()
	{
		super();
	}

	/**
	 * 
	 * @param provider	provider, meaning the company which runs the auction
	 * @param providerOfferingId	the official lot number at the providers auction
	 * @param priceMin				the bid minimum price
	 * @param priceMax				the bid maximum price
	 * @param offeringDate			the date of the auction
	 * @param isThisAOHKOffering	boolean indicator expressing if this is a original wooden case , german OHK
	 * @param theNoOfBottles		the number of bottles in this lot
	 */
	public Offering(Provider provider,String providerOfferingId,
			BigDecimal priceMin, BigDecimal priceMax, Date offeringDate, boolean isThisAOHKOffering, int theNoOfBottles) {
		super();
		this.provider = provider;
		this.providerOfferingId = providerOfferingId;
		this.priceMin = priceMin;
		this.priceMax = priceMax;
		this.offeringDate = offeringDate;
		this.isOHK=isThisAOHKOffering;
		this.noOfBottles = theNoOfBottles;
	}
	
	public int getNoOfBottles() {
		return noOfBottles;
	}

	public void setNoOfBottles(int noOfBottles) {
		this.noOfBottles = noOfBottles;
	}

	public boolean isOHK() {
		return isOHK;
	}

	public void setIsOHK(boolean theOHKIndicator)
	{
		isOHK = theOHKIndicator;
	}
	
	public String getNote() {
		return note;
	}

	public void setNote(String notes) {
		this.note = notes;
	}

	public String getEventIdentifier() {
		return eventIdentifier;
	}

	public void setEventIdentifier(String eventIdentifier) {
		this.eventIdentifier = eventIdentifier;
	}
	
	public BigDecimal getPriceMin() {
		return priceMin;
	}

	public void setPriceMin(BigDecimal priceMin) {
		this.priceMin = priceMin;
	}

	public BigDecimal getPriceMax() {
		return priceMax;
	}

	public void setPriceMax(BigDecimal priceMax) {
		this.priceMax = priceMax;
	}

	public Date getOfferingDate() {
		return offeringDate;
	}

	public void setOfferingDate(Date offeringDate) {
		this.offeringDate = offeringDate;
	}

	public Provider getProvider() {
		return provider;
	}
	
	public void setProvider(Provider provider) {
		this.provider = provider;
	}

	public long getId() {
		return id;
	}

	public void setId(long id) {
		this.id = id;
	}	
	
	public String getProviderOfferingId() {
		return providerOfferingId;
	}

	public void setProviderOfferingId(String providerOfferingId) {
		this.providerOfferingId = providerOfferingId;
	}

	public void setRealizedPrice(BigDecimal theRealizedPrice) {
		realizedPrice = theRealizedPrice;
	}

	public BigDecimal getRealizedPrice()
	{
		return realizedPrice;
	}
	
	@Override
	public String toString()
	{
		StringBuilder aBuilder = new StringBuilder();
		aBuilder.append("eventIdentifier=");
		aBuilder.append(this.eventIdentifier);
		aBuilder.append(",");
		
		aBuilder.append("isOHK=");
		aBuilder.append(this.isOHK);
		aBuilder.append(",");

		aBuilder.append("noOfBottles=");
		aBuilder.append(this.noOfBottles);
		aBuilder.append(",");

		aBuilder.append("providerOfferingId=");
		aBuilder.append(this.providerOfferingId);
		aBuilder.append(",");

		aBuilder.append("note=");
		aBuilder.append(this.note);
		aBuilder.append(",");

		aBuilder.append("offeringDate=");
		aBuilder.append(new SimpleDateFormat("dd.MM.yyyy").format(this.offeringDate));
		aBuilder.append(",");

		aBuilder.append("priceMin=");
		aBuilder.append(this.priceMin);
		aBuilder.append(",");

		aBuilder.append("priceMax=");
		aBuilder.append(this.priceMax);
		aBuilder.append(",");

		aBuilder.append("realizedPrice=");
		aBuilder.append(this.realizedPrice);
		aBuilder.append(",");

		aBuilder.append("provider=");
		aBuilder.append(this.provider.getName());
		return aBuilder.toString();
	}
	
}
