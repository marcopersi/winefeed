package ch.persi.java.vino.importers.steinfels;

import static java.lang.String.valueOf;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.AbstractImportTask;
import ch.persi.java.vino.importers.DateParsingStrategy;
import ch.persi.java.vino.importers.LineExtrator;

public class SteinfelsImportTask extends AbstractImportTask {

	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.steinfels.SteinfelsImportTask.class);
	private static final String IMPORTDIRECTORY = "import//Steinfels//";

	private static final Pattern getRegionMatcher() {
		StringBuilder aWineRegionPatternBuilder = new StringBuilder();
		aWineRegionPatternBuilder.append("^.*\\s");
		aWineRegionPatternBuilder.append("(Pomerol");
		aWineRegionPatternBuilder.append("|Saint Emilion");
		aWineRegionPatternBuilder.append("|Haut Médoc");
		aWineRegionPatternBuilder.append("|Sauternes");
		aWineRegionPatternBuilder.append("|Margaux");
		aWineRegionPatternBuilder.append("|Pauillac");
		aWineRegionPatternBuilder.append("|Pessac Léognan");
		aWineRegionPatternBuilder.append("|Saint Julien");
		aWineRegionPatternBuilder.append("|Moulis en Médoc");
		aWineRegionPatternBuilder.append("|Côtes de Castillon");
		aWineRegionPatternBuilder.append("|Saint Estéphe");
		aWineRegionPatternBuilder.append("|Graves");
		aWineRegionPatternBuilder.append("|Lussac St Emilion");
		aWineRegionPatternBuilder.append("|Puisseguin St Emilion");
		aWineRegionPatternBuilder.append("|Listrac");
		aWineRegionPatternBuilder.append("|Bordeaux");
		aWineRegionPatternBuilder.append("|Moulis en Médoc");
		aWineRegionPatternBuilder.append("|Canon Fronsac");
		aWineRegionPatternBuilder.append("|Premières Côtes de Blaye");
		aWineRegionPatternBuilder.append("|Bordeaux Supérieur");
		aWineRegionPatternBuilder.append("|Côtes de Bourg");
		aWineRegionPatternBuilder.append("|Listrac Cru Bourgeois");
		aWineRegionPatternBuilder.append("|Leroy");
		aWineRegionPatternBuilder.append("|Bourgogne");
		aWineRegionPatternBuilder.append("|Rhône");
		aWineRegionPatternBuilder.append("|Sicilia");
		aWineRegionPatternBuilder.append("|Columbia");
		aWineRegionPatternBuilder.append("|Piemont");
		aWineRegionPatternBuilder.append("|Toskana");
		aWineRegionPatternBuilder.append("|Priorat");
		aWineRegionPatternBuilder.append("|Ribera del Duero)");
		aWineRegionPatternBuilder.append(".*$");
		return Pattern.compile(aWineRegionPatternBuilder.toString());
		
		
	}

	@Override
	public void execute() {
		// checking for to be imported files at fileSystem, apply some
		// validation
		File anImportDirectory = new File(IMPORTDIRECTORY);
		if (anImportDirectory.list() == null || anImportDirectory.list().length < 1) {
			log.error("The import directory {} does not exist or does not contain anything at all !");
			return;
		}

		for (String aFileName : anImportDirectory.list()) {
			try {
				log.info("Start import of file: {}", aFileName);
				
				List<String> someLines = parser.parse(IMPORTDIRECTORY + aFileName);
				log.info("Received '{}' lines out of the PDF file !", someLines.size());
				
				evaluateAuctionEvent(aFileName, someLines);

				importFile(someLines, Provider.STEINFELS);
				
			} catch (Exception theException) {
				log.error("Executing Steinfels Import Task has a serious problem with the import of the file '" + aFileName + "'", theException);
			}
		}
	}
	
	
	private  final void evaluateAuctionEvent(String theFileName, List<String> theLines)
	{
		String[] split = theFileName.split("_");
		if (split != null && split.length==3)
		{
			setEventIdentifier(split[0]);
			setAuctionDate(new DateParsingStrategy(split[1]).getAuctionDate());
		} else
		{
			setAuctionDate(new SteinfelsDateExtractingStrategy(theLines).getAuctionDate());
		}
	}

	private static final String clean(String theLine) {
		return theLine.replaceAll("1er", "").replaceAll("2ème", "").replaceAll("3ème", "").replaceAll("4ème", "").replaceAll("5ème", "")
				.replaceAll("cru burgoise", "").replaceAll("Cru", "").replaceAll("-", " ");
	}

	@Override
	public void saveWineOfferings(final List<String> theLines) throws IOException {

		int anOfferingId = 1;
		for (String aRecordLine : theLines) {
			String anOptimizedLine = clean(aRecordLine).trim();
			log.debug("Working on offering Id: %s and line %s", anOfferingId, anOptimizedLine);

			// this nasty +1 thing below is required because the sequence of lot
			// numbers is sometimes broker - these fu****rs
			// obviously take some offerings sometimes out of the catalog,
			// without resetting the sequence of lot numbers
			String aLotString = valueOf(anOfferingId);
			if (anOptimizedLine.endsWith(aLotString)) {
				// ok, this was the initial start signal, knowing that now we
				// have seen at least the first record line.
				String aLineWithoutLotNumber = anOptimizedLine.replaceAll(valueOf(anOfferingId) + "$", "");
				processLine(aLineWithoutLotNumber, anOfferingId);
				anOfferingId++;
			} else if (anOptimizedLine.endsWith(valueOf(anOfferingId + 1))) {
				anOfferingId++;
				processLine(anOptimizedLine, anOfferingId);
				anOfferingId++;
			} else if (anOptimizedLine.startsWith(aLotString))
			{
				String aLineWithoutLotNumber = anOptimizedLine.replaceAll("^"+aLotString, "");
				processLine(aLineWithoutLotNumber, anOfferingId);
				anOfferingId++;
			}
		}
	}

	private final void processLine(String theRecordLineWithoutLotNo, int theOfferingId) throws IOException {

		LineExtrator lineExtractor = evaluateLineExtractor(theRecordLineWithoutLotNo);
		if (lineExtractor == null) {
			aSkippedRowsWriter.write(theRecordLineWithoutLotNo);
			log.warn("skipped row: %s", theRecordLineWithoutLotNo);
			return;
		}

		boolean isOHK = lineExtractor.isOHK();

		Offering anOffering = new Offering();
		anOffering.setProvider(Provider.STEINFELS.getProviderCode());
		anOffering.setOfferingDate(getAuctionDate());
		anOffering.setEventIdentifier(getEventIdentifier());

		// no validation of matcher needed, since isRecordLine already checked
		// if matcher is valid at this point or not
		anOffering.setProviderOfferingId(valueOf(theOfferingId));

		// matcher seems to be somehow state full, without calling matches the
		// group access to item 2 fails , funny enough
		String aCompositeContentPart = lineExtractor.getWine();
		String extractRegion = extractRegion(theRecordLineWithoutLotNo);

		Wine aWine = new Wine();
		if (extractRegion != null) {
			aWine.setRegion(extractRegion);
			aCompositeContentPart = aCompositeContentPart.replaceFirst(extractRegion, "");
		}

		aWine.setName(aCompositeContentPart);

		Integer vintage = lineExtractor.getVintage();
		aWine.setVintage((vintage != null ? vintage : 0));

		Integer aRealizedPrice = lineExtractor.getRealizedPrice();
		anOffering.setRealizedPrice(aRealizedPrice);
		anOffering.setIsOHK(isOHK);
		anOffering.setNoOfBottles(lineExtractor.getNoOfBottles());

		Unit unit = getUnit(theRecordLineWithoutLotNo);
		WineOffering aWineOffering = new WineOffering(aWine, unit, anOffering);
		log.info(aWineOffering.toXLSString());
		anOutputWriter.write(aWineOffering.toXLSString());
	}

	private static final String extractRegion(String theLine) {
		Matcher matcher = getRegionMatcher().matcher(theLine);
		if (matcher.matches()) {
			return matcher.group(1);
		}
		return null;
	}

	private static LineExtrator evaluateLineExtractor(String theRecordLine) {

		NewRecordLineExtractor aNewRecordLineExtractor = new NewRecordLineExtractor(theRecordLine);
		if (aNewRecordLineExtractor.isRecordLine()) {
			return aNewRecordLineExtractor;
		}
		
		OldRecordLineExtractor oldRecordLineExtractor = new OldRecordLineExtractor(theRecordLine);
		if (oldRecordLineExtractor.isRecordLine()) {
			return oldRecordLineExtractor;
		}

		return null;
	}

	public final Unit getUnit(final String theLine) {
		return new Unit(determineSize(theLine));
	}

}
