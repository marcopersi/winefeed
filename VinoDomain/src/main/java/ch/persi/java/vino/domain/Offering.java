package ch.persi.java.vino.domain;

import java.time.LocalDate;

public class Offering {
	
	private String provider;
	private String providerOfferingId;
	
	private int priceMin;
	private int priceMax;
	private LocalDate offeringDate;
	private long id;
	private int realizedPrice=0;
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
	 * @param theProvider	provider, meaning the company which runs the auction
	 * @param theProviderOfferingId	the official lot number at the providers auction
	 * @param theMinimumPrice				the bid minimum price
	 * @param theMaximumPrice				the bid maximum price
	 * @param theOfferingDate			the date of the auction
	 * @param isThisAOHKOffering	boolean indicator expressing if this is a original wooden case , German OHK
	 * @param theNoOfBottles		the number of bottles in this lot
	 */
	public Offering(final String theProvider,final String theProviderOfferingId,
			final int theMinimumPrice, final int theMaximumPrice, final LocalDate theOfferingDate, final boolean isThisAOHKOffering, final int theNoOfBottles) {
		super();
		this.provider = theProvider;
		this.providerOfferingId = theProviderOfferingId;
		this.priceMin = theMinimumPrice;
		this.priceMax = theMaximumPrice;
		this.offeringDate = theOfferingDate;
		this.isOHK=isThisAOHKOffering;
		this.noOfBottles = theNoOfBottles;
	}
	
	public int getNoOfBottles() {
		return noOfBottles;
	}

	public void setNoOfBottles(int theNumberOfBottles) {
		this.noOfBottles = theNumberOfBottles;
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

	public void setEventIdentifier(String theEventIdentifier) {
		this.eventIdentifier = theEventIdentifier;
	}
	
	public int getPriceMin() {
		return priceMin;
	}

	public void setPriceMin(int theMinimumPrice) {
		this.priceMin = theMinimumPrice;
	}

	public int getPriceMax() {
		return priceMax;
	}

	public void setPriceMax(int theMaximumPrice) {
		this.priceMax = theMaximumPrice;
	}

	public LocalDate getOfferingDate() {
		return offeringDate;
	}

	public void setOfferingDate(LocalDate theOfferingDate) {
		this.offeringDate = theOfferingDate;
	}

	public String getProvider() {
		return provider;
	}
	
	public void setProvider(String theProvider) {
		this.provider = theProvider;
	}

	public long getId() {
		return id;
	}

	public void setId(long theId) {
		this.id = theId;
	}	
	
	public String getProviderOfferingId() {
		return providerOfferingId;
	}

	public void setProviderOfferingId(String theProviderOfferingId) {
		this.providerOfferingId = theProviderOfferingId;
	}

	public void setRealizedPrice(int theRealizedPrice) {
		realizedPrice = theRealizedPrice;
	}

	public int getRealizedPrice()
	{
		return realizedPrice;
	}
	
	@Override
	public String toString()
	{

        return "eventIdentifier=" +
                this.eventIdentifier +
                ";" +
                "isOHK=" +
                this.isOHK +
                ";" +
                "noOfBottles=" +
                this.noOfBottles +
                ";" +
                "providerOfferingId=" +
                this.providerOfferingId +
                ";" +
                "note=" +
                this.note +
                ";" +
                "offeringDate=" +
                VinoConstants.vinoDateFormat.format(this.offeringDate) +
                ";" +
                "priceMin=" +
                this.priceMin +
                ";" +
                "priceMax=" +
                this.priceMax +
                ";" +
                "realizedPrice=" +
                this.realizedPrice +
                ";" +
                "provider=" +
                this.provider;
	}

}
