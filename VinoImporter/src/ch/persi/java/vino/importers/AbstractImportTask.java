package ch.persi.java.vino.importers;

import java.io.FileWriter;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.util.InputParser;

public abstract class AbstractImportTask implements ImportTask {

	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.AbstractImportTask.class);

	protected InputParser parser = null;

	protected FileWriter anOutputWriter = null;
	protected FileWriter aSkippedRowsWriter = null;
	
	protected DateExtractingStrategy dateExtractingStrategy = null;
	
	private LocalDate auctionDate = null;
	private String eventIdentifier = null;
	
	public void setInputParser(final InputParser theParser) {
		this.parser = theParser;
	}

	public void setEventIdentifier(String theEventIdentifier)
	{
		eventIdentifier = theEventIdentifier;
	}
	
	public String getEventIdentifier()
	{
		return eventIdentifier;
	}
	
	
	public void setAuctionDate(LocalDate theAuctionDate)
	{
		auctionDate = theAuctionDate;
	}
	
	public LocalDate getAuctionDate()
	{
		return auctionDate;
	}
	
	protected void importFile(final List<String> someLines, final Provider theProvider) throws Exception {
		if (getAuctionDate() == null) {
			throw new IllegalStateException("Cannot get an auction date, this is a serious problem !");
		}

		try {
			anOutputWriter = new FileWriter("output_"+theProvider.getProviderCode()+"_"+getAuctionDate().format(DateTimeFormatter.ofPattern("ddMMyyyy")));	
			aSkippedRowsWriter = new FileWriter("skippedRowsFrom_"+theProvider.getProviderCode()+"_"+getAuctionDate().format(DateTimeFormatter.ofPattern("ddMMyyyy")));
			saveWineOfferings(someLines);
		} catch (Exception theCause) {
			log.error(theCause.getMessage(), theCause);
		} finally {
			if (anOutputWriter != null) {
				anOutputWriter.flush();
				anOutputWriter.close();
			}
			
			if (aSkippedRowsWriter != null) {
				aSkippedRowsWriter.flush();
				aSkippedRowsWriter.close();
			}

		}
	}

}
