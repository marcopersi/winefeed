package ch.persi.java.vino.importers;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.excel.VinoExcelUtil;
import ch.persi.java.vino.util.InputParser;

public abstract class AbstractImportTask implements ImportTask {

	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.AbstractImportTask.class);

	protected InputParser parser = null;
	protected VinoExcelUtil anExcelSheet = null;
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

		anExcelSheet = new VinoExcelUtil();

		try {
			anExcelSheet.openStagingFile(theProvider.getProviderCode(), theProvider.getProviderCode() + "_" + getAuctionDate().format(DateTimeFormatter.ofPattern("dd.MM.yyyy")));
			saveWineOfferings(someLines);
		} catch (Exception theCause) {
			log.error(theCause.getMessage(), theCause);
		} finally {
			anExcelSheet.close();
		}
	}

}
