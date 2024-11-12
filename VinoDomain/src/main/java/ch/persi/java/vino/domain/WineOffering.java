package ch.persi.java.vino.domain;



public class WineOffering {

	private long id;

	private Wine wine;
	private Unit wineUnit;
	private Offering offering;

	/**
	 * default constructor for hibernate
	 */
	public WineOffering()
	{
		super();
	}

	/**
	 * Constructor, creates a wine offering for the wine in the specified unit (size)
     */
	public WineOffering(Wine theWine, Unit theWineUnit) {
		super();
		this.wine = theWine;
		this.wineUnit = theWineUnit;
	}

	/**
     */
	public WineOffering(Wine theWine, Unit theWineUnit,Offering theOffering) {
		this(theWine,theWineUnit);
		offering=theOffering;
	}
	
	public long getId() {
		return id;
	}
	
	public void setId(long theId) {
		this.id = theId;
	}
	
	public Unit getWineUnit() {
		return wineUnit;
	}

	public void setWineUnit(Unit theWineUnit) {
		this.wineUnit = theWineUnit;
	}

	public Wine getWine() {
		return wine;
	}
	
	public void setWine(Wine theWine) {
		this.wine = theWine;
	}

	public Offering getOffering() {
		return offering;
	}

	public void setOffering(Offering theOffering) {
		this.offering = theOffering;
	}	

	public final String toXLSString() {

        return getOffering().getProviderOfferingId() +
                ";" +
                getWine().getName() +
                ";" +
                getWine().getOrigin() +
                ";" +
                getWine().getProducer() +
                ";" +
                getWine().getVintage() +
                ";" +
                getOffering().getNoOfBottles() +
                ";" +
                getWineUnit().getDeciliters().toPlainString() +
                ";" +
                getOffering().isOHK() +
                ";" +
                getOffering().getPriceMin() +
                ";" +
                getOffering().getPriceMax() +
                ";" +
                getOffering().getRealizedPrice() +
                "\n";
	}
	
}
