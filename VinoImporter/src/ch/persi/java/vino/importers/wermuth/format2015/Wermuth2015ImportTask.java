package ch.persi.java.vino.importers.wermuth.format2015;

import ch.persi.java.vino.domain.*;
import ch.persi.java.vino.importers.AbstractImportTask;
import ch.persi.java.vino.importers.DateParsingStrategy;
import lombok.val;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.domain.VinoConstants.*;
import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

/**
 * The import task which cares about the Wermuth/Denz files which have changed since 2015.
 * Starting with first auction in 2015, Wermuth/Denz Weine provides the required info in one result file in the format PDF.
 * So there is no need to search a catalog, match the found lots with a result file and get the realized "hammer" prize then.
 *
 * @author marcopersi
 */
public class Wermuth2015ImportTask extends AbstractImportTask {

	private static final Logger log = LoggerFactory.getLogger(Wermuth2015ImportTask.class);
	public static Pattern aRecordLinePattern = Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})\\s(.*[fF]lasche.*),?\\s([0-9]{4}),?.*(pro[a-zA-Z\\.\\s]*\\s)([0-9]{2,5}.*$)");

	private String importDirectory = null;

	/**
	 * only public for testing purposes
	 *
	 * @param theLine
	 * @return a cleaned String
	 */
	public static String clean(String theLine) {
		return theLine.replaceAll("1er", "").replaceAll("2ème|3ème|4ème|5ème", "").replaceAll("cru burgoise", "").replaceAll("1 cru ", "")
				.replaceAll("1 er|cru", "").replaceAll("Total ", "").replaceAll("«|»|“|”|„", "").replaceAll("CHF ", "").replaceAll("SFr.", "").replaceAll("Fr.", "")
				.replace(".00", "").replaceAll("\\(.*\\)", "").replaceAll("\\s{2,}", SPACE).replaceAll("Cru|cru", "");
	}

	public static int processNoOfBottles(String theNoOfBottles, String theLotOrDozenIndicator) {
		int aNoOfUnits = parseInt(theNoOfBottles);

		if (theLotOrDozenIndicator.contains("pro Dutzend") || theLotOrDozenIndicator.contains("pro Dz")) {
			aNoOfUnits *= 12;
		}

		return aNoOfUnits;
	}

	public static LotPriceInfo processLotPricing(String theInput) {
		//the last part drops any characters, actually there should be only digits and probably a dash (-) character, but nothing else anymore.
		String aCleanedInputLine = theInput.replaceAll("[a-zA-Z\\.']", "");
//		String aCleanedInputLine = theInput.replaceAll("[a-zA-Z\\.]", "").trim(); //1st file 2015

		Pattern aPricePattern = Pattern.compile("^([0-9]{1,5})-([0-9]{1,5})\\s?{1,}([0-9\\-]{1,5})?\\s?$");
//		Pattern aPricePattern = Pattern.compile("^([0-9]{1,5})-([0-9]{1,5})\\s{1,}([0-9\\-]{1,5})\\s?$"); // 1st file 2015

		Matcher matcher = aPricePattern.matcher(aCleanedInputLine);
		if (!matcher.matches()) {
			throw new IllegalStateException("Price info did not look as expected!: " + aCleanedInputLine);
		}

		int aLowerPrice = parseInt(matcher.group(1));
		int anUpperPrice = parseInt(matcher.group(2));
		int aRealizedPrice = isCreatable(matcher.group(3)) ? parseInt(matcher.group(3)) : 0;
		return new LotPriceInfo(aLowerPrice, anUpperPrice, aRealizedPrice);
	}

	@Override
	public void saveWineOfferings(List<String> theLines) throws IOException {

		if (theLines.isEmpty()) {
			throw new IllegalStateException("Received no lines from parser, something's terribly wrong !");
		}

		int aProcessLineIndex = 0;
		for (String aLine : theLines) {
			// cleaning
			log.debug("Working on line: {}", aLine);
			String aCleanedLine = clean(aLine);

			// processing
			WineOffering aWineOffering = processLine(aCleanedLine);

			// writing results
			if (aWineOffering != null) {
				anOutputWriter.write(aWineOffering.toXLSString());
				anOutputWriter.flush();
			} else {
				aSkippedRowsWriter.write(aCleanedLine+"\n");
				aSkippedRowsWriter.flush();
			}
			aProcessLineIndex++;
		}
		log.info("Processed: {} out of:{} lines ! ", aProcessLineIndex, theLines.size());
	}
	
	
	public final WineOffering processLine(String theWineRecordLine) 
	{
		boolean isOHK = false;
		if (theWineRecordLine.contains(OHK) || theWineRecordLine.contains(OC))
		{
			isOHK =true;
		}

		// removing this OHK/OC tag
		String cleanedLine = theWineRecordLine.replace(OHK, "").replace(OC, "");
		
		Matcher aRecordLineMatcher = aRecordLinePattern.matcher(cleanedLine);
		if (aRecordLineMatcher.matches())
		{
			Offering anOffering = new Offering();
			anOffering.setProvider(Provider.WERMUTH.getProviderCode());
			anOffering.setOfferingDate(getAuctionDate());

			String aLotNumber = aRecordLineMatcher.group(1);
			anOffering.setProviderOfferingId(aLotNumber);

			anOffering.setIsOHK(isOHK);
			anOffering.setEventIdentifier(getEventIdentifier());

			String aLinePart = aRecordLineMatcher.group(6);
			int aNoOfBottles = processNoOfBottles(aRecordLineMatcher.group(3), aLinePart);
			anOffering.setNoOfBottles(aNoOfBottles);
			
			LotPriceInfo processLotPricing = processLotPricing(aRecordLineMatcher.group(7));
			anOffering.setPriceMax(processLotPricing.getUpperPrice());
			anOffering.setPriceMin(processLotPricing.getLowerPrice());
			anOffering.setRealizedPrice(processLotPricing.getRealizedPrice());

			Wine aWine = new Wine();
			String aWineText = aRecordLineMatcher.group(2);
			if (aWineText.contains(",")) {
				String[] split = aWineText.split(",");
				aWineText = split[0].trim();
				if (split.length==2)
				{
					aWine.setProducer(split[1].trim());
				}
			}
		
			aWine.setName(aWineText);

			String group = aRecordLineMatcher.group(5);
			int vintage = parseInt(group);
			aWine.setVintage(vintage);

			Unit aWineUnit = processBottleSize(aRecordLineMatcher.group(4));
			return new WineOffering(aWine, aWineUnit, anOffering);
		}
		return null;
	}

	@Override
	public String getImportDirectory() {
		return importDirectory;
	}

	public void setImportDirectory(String theImportDirectory) {
		importDirectory = theImportDirectory;
	}

	@Override
	public void execute() {
		// checking for to be imported files at fileSystem.
		val anImportDirectory = checkFiles();
		if (anImportDirectory == null) return;

		for (String aFileName : anImportDirectory.list()) {
			String[] someFileNameParts = aFileName.split("_");
			if (!aFileName.startsWith(".") && aFileName.contains("Resultate") && someFileNameParts.length >= 3) {
				try {
					log.info("Start import of file: {}", aFileName);
					String anImportFile = getImportDirectory() + aFileName;
					List<String> someLines = parser.parse(anImportFile);
					log.info("Received '{}' lines out of the PDF file !", someLines.size());
					setAuctionDate(new DateParsingStrategy(someFileNameParts[1]).getAuctionDate());

					Matcher compile = Pattern.compile("(WZ\\-[0-9]{1,4}).*").matcher(aFileName);
					if (compile.matches()) {
						setEventIdentifier(compile.group(1));
					}

					// PDFs are nasty, some have the tag of the auction (252 or 287..)in front of every single line. cleaning this.
//					someLines = ResultFilebasedLotLinePreparer.prepare(someLines);

					importFile(someLines, Provider.WERMUTH);
				} catch (Exception anException) {
					log.error("Executing Wermuth Import Task has a serious problem with file {}!, got exception {}", aFileName, anException);
				}
				log.info("Import of file {} successfully done", aFileName);
			}
		}
	}

	public final Unit processBottleSize(String theBottleSizeIndicator)
	{
		BigDecimal aSize = determineSize(theBottleSizeIndicator);
		return new Unit(aSize);
	}

}
