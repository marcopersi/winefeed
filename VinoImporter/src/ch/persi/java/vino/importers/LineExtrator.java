package ch.persi.java.vino.importers;

public interface LineExtrator {

	public boolean isRecordLine();
	
	public Integer getVintage();
	
	public boolean isOHK();
	
	public Integer getNoOfBottles();
	
	public Integer getMinPrice();
	
	public Integer getMaxPrice();
	
	public String getWine();
	
	public String getLotNumber();
	
	public Integer getRealizedPrice();
	
}
