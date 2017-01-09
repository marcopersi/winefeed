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
	 * @param wine
	 * @param wineUnit
	 */
	public WineOffering(Wine wine, Unit wineUnit) {
		super();
		this.wine = wine;
		this.wineUnit = wineUnit;
	}

	/**
	 * @param wine
	 * @param wineUnit
	 * @param theOffering
	 */
	public WineOffering(Wine wine, Unit wineUnit,Offering theOffering) {
		this(wine,wineUnit);
		offering=theOffering;
	}
	
	public long getId() {
		return id;
	}
	
	public void setId(long id) {
		this.id = id;
	}
	
	public Unit getWineUnit() {
		return wineUnit;
	}

	public void setWineUnit(Unit wineUnit) {
		this.wineUnit = wineUnit;
	}

	public Wine getWine() {
		return wine;
	}
	
	public void setWine(Wine wine) {
		this.wine = wine;
	}

	public Offering getOffering() {
		return offering;
	}

	public void setOffering(Offering offering) {
		this.offering = offering;
	}	

	
}
