package ch.persi.java.vino.importers.weinboerse;

import static ch.persi.java.vino.domain.VinoConstants.OHK;

import java.io.File;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.AbstractImportTask;

public class WeinboerseImportTask extends AbstractImportTask {

	
	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.weinboerse.WeinboerseImportTask.class);
	private static final String IMPORTDIRECTORY = "import//Weinboerse//";

	@Override
	public void execute() {
		// checking for to be imported files at fileSystem, apply some
		// validation
		File theImportDirectory = new File(IMPORTDIRECTORY);
		if (theImportDirectory.list() == null || theImportDirectory.list().length < 1) {
			log.error("The import directory {0} does not exist or does not contain anything at all !");
			return;
		}

		for (String aFileName : theImportDirectory.list()) {
			try {
				log.info("Start import of file: " + aFileName);
				
				List<String> someLines = parser.parse(IMPORTDIRECTORY + aFileName);
				log.info("Received '{}' lines out of the PDF file !", someLines.size());
				setAuctionDate(new WeinboerseDateExtractingStrategy(someLines).getAuctionDate());
				
				importFile(someLines, Provider.WEINBOERSE);
			} catch (Exception e) {
				e.printStackTrace(System.out);
				log.error("Executing Steinfels Import Task has a serious problem with the import of the file '{}'", aFileName, e);
			}
		}
	}

	@Override
	public void saveWineOfferings(final List<String> theLines) {

		// TODO: move that behind the DAO as a provider of the DAO
		// Implementation
		for (String aRecordLine : theLines) {
			String aTrimmedRecordLine = aRecordLine.trim();

			WeinboerseLineExtractor lineExtractor = new WeinboerseLineExtractor(aTrimmedRecordLine);

			boolean isOHK = lineExtractor.isOHK();

			// 1st step: remove OHK if available
			String aCleanedRecordLine = aTrimmedRecordLine.replace(OHK, "");

			if (lineExtractor.isRecordLine()) {
				Wine aWine = new Wine();
				Offering anOffering = new Offering();
				WineOffering aWineOffering = new WineOffering(aWine, getUnit(aCleanedRecordLine));

				anOffering.setProvider(Provider.WEINBOERSE.getProviderCode());
				anOffering.setOfferingDate(getAuctionDate());

				// no validation of matcher needed, since isRecordLine already
				// checked if matcher is valid at this point or not
				anOffering.setProviderOfferingId(lineExtractor.getLotNumber());
				String[] someLineParts = null;

				// matcher seems to be somehow state full, without calling
				// matches the group access to item 2 fails , funny enough
				String aCompositeContentPart = lineExtractor.getWine();
				someLineParts = aCompositeContentPart.split(" ");

				String aPossibleRegion = someLineParts[someLineParts.length - 1].trim();
				aCompositeContentPart = aCompositeContentPart.replace(aPossibleRegion, ""); // reducing
				// the original string with the current part, intention is that the rest may be used as wine name

				if (aPossibleRegion.matches("[0-9]{1}.*")) {
					anOffering.setNote(aPossibleRegion); // obviously it was NOT the region, ..ok,next try, overwriting a aPossibleRegion variable

					// then we have to assume that's the next element before
					// this, if not we rely on the manual check of the excel
					// stating file
					aPossibleRegion = someLineParts[someLineParts.length - 2].trim();
				}

				aWine.setRegion(aPossibleRegion);
				// the 2nd time replacing, only because of the possibility that
				// aPossibleRegion has been overwritten within the first if
				// clause
				// even if not, this doesn't harm the code at all..
				// FIXME: second replace of again the same string does not work
				// ,Chateau Margaux Margaux......
				aCompositeContentPart = aCompositeContentPart.replace(aPossibleRegion, "");
				aWine.setName(aCompositeContentPart);

				// regular continuation with next fields...
				Integer vintage = lineExtractor.getVintage();
				aWine.setVintage((vintage != null ? vintage : 0));

				// TODO: after having name & vintage of the wine, could try to
				// find it in the database, DAO has findWineByNameAndYear
				// but this is part of the import task of the staging file !

				anOffering.setRealizedPrice(lineExtractor.getRealizedPrice());

				anOffering.setIsOHK(isOHK);
				anOffering.setNoOfBottles(lineExtractor.getNoOfBottles());
				aWineOffering.setOffering(anOffering);
				anExcelSheet.addRow(aWineOffering);
			} else {
				anExcelSheet.addSkippedRow(aRecordLine);
			}
			// reseting OHK
			isOHK = false;
		}

	}


	private final Unit getUnit(final String theLine) {
		return new Unit(determineSize(theLine));
	}


}
