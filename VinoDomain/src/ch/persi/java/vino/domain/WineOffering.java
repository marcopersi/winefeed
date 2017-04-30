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
	 * @param theWine
	 * @param theWineUnit
	 */
	public WineOffering(Wine theWine, Unit theWineUnit) {
		super();
		this.wine = theWine;
		this.wineUnit = theWineUnit;
	}

	/**
	 * @param theWine
	 * @param theWineUnit
	 * @param theOffering
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

		StringBuilder aBuilder = new StringBuilder();
		aBuilder.append(getOffering().getProviderOfferingId());
		aBuilder.append(";");
		aBuilder.append(getWine().getName());
		aBuilder.append(";");
		aBuilder.append(getWine().getRegion());
		aBuilder.append(";");
		aBuilder.append(getWine().getVintage());
		aBuilder.append(";");
		aBuilder.append(getOffering().getOfferingDate()); // FIXME: format this date appropriately
		aBuilder.append(";");
		aBuilder.append(getOffering().getNoOfBottles());
		aBuilder.append(";");
		aBuilder.append(getWineUnit().getDeciliters().toPlainString());
		aBuilder.append(";");
		aBuilder.append(getOffering().getRealizedPrice());
		aBuilder.append("\n");
		return aBuilder.toString();
	}
	
}
