package ch.persi.java.vino.importers;

import java.math.BigDecimal;
import java.util.List;

import org.joda.time.DateTime;

public interface ImportTask extends Task{

	public boolean isRecordLine(String theLine);
	
	public String getOrigin(String theLine);
	
	public Integer getNoOfBottles(String theLine);
	
	public BigDecimal determineSize(String theLine);
	
	public DateTime getAuctionDate(List<String> theLines);
	
	public BigDecimal getParkerRating(String theLine);
	
	public String getLotNumber(String theLine);
	
	public Integer getVintage(String theLine);
}
