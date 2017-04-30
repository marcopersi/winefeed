package ch.persi.java.vino.importers.wermuth.format2015;

import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.math.NumberUtils.isNumber;

import java.io.File;
import java.math.BigDecimal;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.VinoConstants;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.AbstractImportTask;
import ch.persi.java.vino.importers.DateParsingStrategy;

public class Wermuth2015ImportTask extends AbstractImportTask {

	private static final Logger log = LoggerFactory.getLogger(Wermuth2015ImportTask.class);
	private static final String IMPORTDIRECTORY = "import//wermuth//";	
	
	@Override
	public void execute() {
		// checking for to be imported files at fileSystem.
		File anImportDirectory = new File(IMPORTDIRECTORY);
		String[] someFiles = anImportDirectory.list();

		if (someFiles == null || someFiles.length < 1) {
			log.warn("didn't find any files in the directory !");
		} else {
			for (int i = 0; i < someFiles.length; i++) {
				// Get filename of file or directory String
				String aFileName = someFiles[i];
				String[] someFileNameParts = aFileName.split("_");

				if (!aFileName.startsWith(".") && aFileName.contains("Resultate") && someFileNameParts != null && someFileNameParts.length == 3) {
					log.info("Start import of file:{}", aFileName);
					try {
						List<String> someLines = parser.parse(IMPORTDIRECTORY + aFileName);
						log.info("Received '{}' lines out of the PDF file !", someLines.size());
						setAuctionDate(new DateParsingStrategy(someFileNameParts[1]).getAuctionDate());
						
						Matcher compile = Pattern.compile("(WZ\\-[0-9]{1,4}).*").matcher(aFileName);
						if (compile.matches())
						{
							setEventIdentifier(compile.group(1));
						}

						importFile(someLines, Provider.WERMUTH);
					} catch (Exception anException) {
						log.error("Executing Wermuth Import Task has a serious problem: !" + anException.getMessage(), anException);
					}
				}
				log.info("Job successfully done !");
			}
		}
	}

	@Override
	public void saveWineOfferings(List<String> theLines) {
		
		if (theLines == null || theLines.size() == 0) {
			throw new IllegalStateException("Received no lines from parser, something's terribly wrong !");
		}
		
		StringBuffer aBufferedLine = new StringBuffer();
		
		int aProcessLineIndex = 0;
		
		for (String aLine : theLines) {
			aBufferedLine.append(aLine);
			log.debug("Working on line: " + aBufferedLine);
			
			if (!aLine.endsWith("CHF"))
			{
				aBufferedLine.append(" ");
			}
			else
			{
				// cleaning & processing
				String aCleanedLine = clean(aBufferedLine);
				processLine(aCleanedLine);
				
				aBufferedLine.setLength(0); // resetting
				aProcessLineIndex++;
			}
		}
		log.info("Processed: " + aProcessLineIndex + " out of: " + theLines.size() + " lines !");
	}
	
	
	private final void processLine(String theCleanedLine)
	{
		// removing the currency Symbol at the EOL
		String aLineWithouthCurrencyEnding = theCleanedLine.substring(0, theCleanedLine.length()-3).trim();
		log.debug("1st revision:" + aLineWithouthCurrencyEnding);
		
		// removing the auction no at start
		String aLineWithoutAuctionNo = aLineWithouthCurrencyEnding.substring(4, aLineWithouthCurrencyEnding.length()).trim();
		log.debug("2nd revision:" + aLineWithoutAuctionNo);
		
		boolean isOHK = aLineWithoutAuctionNo.contains(VinoConstants.OHK);
		String cleanedLine = aLineWithoutAuctionNo.replace(VinoConstants.OHK, "");
		
		Pattern aRecordLinePattern = Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})((.*[fF]lasche.*),?)\\s([0-9]{4}),?(.*)(CHF.*$).*");
		Matcher aRecordLineMatcher = aRecordLinePattern.matcher(cleanedLine);
		if (aRecordLineMatcher.matches())
		{
//			Wine aWine = new Wine();
			
			Offering anOffering = new Offering();
			anOffering.setProvider(Provider.WERMUTH.getProviderCode());
			anOffering.setOfferingDate(getAuctionDate());

			String aLotNumber = aRecordLineMatcher.group(1);
			anOffering.setProviderOfferingId(aLotNumber);

			anOffering.setIsOHK(isOHK);
			anOffering.setEventIdentifier(getEventIdentifier());

			int aNoOfBottles = processNoOfBottles(aRecordLineMatcher.group(3), aRecordLineMatcher.group(7));
			anOffering.setNoOfBottles(aNoOfBottles);
			
			LotPriceInfo processLotPricing = processLotPricing(aRecordLineMatcher.group(8));
			anOffering.setPriceMax(processLotPricing.getUpperPrice());
			anOffering.setPriceMin(processLotPricing.getLowerPrice());
			anOffering.setRealizedPrice(processLotPricing.getRealizedPrice());
						
			String aWineText = processWine(aRecordLineMatcher.group(2));
			Wine aWine = new Wine();
			aWine.setName(aWineText);

			int vintage = parseInt(aRecordLineMatcher.group(6));
			aWine.setVintage(vintage);
			
			Unit aWineUnit = processBottleSize(aRecordLineMatcher.group(4));
			
			WineOffering aWineOffering = new WineOffering(aWine, aWineUnit, anOffering);
			log.info(aWineOffering.toXLSString());
			anExcelSheet.addRow(aWineOffering);
		} else
		{
			log.info("skipped row: " + cleanedLine);
			anExcelSheet.addSkippedRow(cleanedLine);
		}
		
	}
	
	private static final String clean(StringBuffer aBufferedLine)
	{
		return aBufferedLine.toString().replaceAll("1er", "").replaceAll("2ème", "").replaceAll("3ème", "").replaceAll("4ème", "").replaceAll("5ème", "")
				.replaceAll("cru burgoise", "").replaceAll("Cru", "").replaceAll("cru","").replaceAll("1 er", "");
	}
	
	private static final String processWine(String theWineText)
	{
		String aWineLine = theWineText; 
		
		if (theWineText.contains(","))
		{
			aWineLine = theWineText.split(",")[0];
		}
		
		return aWineLine;
	}

	public static final int processNoOfBottles(String theNoOfBottles, String theLotOrDozenIndicator)
	{
		int aNoOfUnits = parseInt(theNoOfBottles);

		if (theLotOrDozenIndicator.contains("pro Dutzend") || theLotOrDozenIndicator.contains("pro Dz"))
		{
			aNoOfUnits *= 12;
		}
		
		return aNoOfUnits;
	}
	
	public static final LotPriceInfo processLotPricing(String theInput)
	{
		String aCleanedInputLine = theInput.replace("CHF", "").replace("'", "").replace(".00", "").trim();
		Pattern aPricePattern = Pattern.compile("^([0-9]{1,5})-([0-9]{1,5})\\s([0-9\\-]{1,5})$");
		
		Matcher matcher = aPricePattern.matcher(aCleanedInputLine);
		if (!matcher.matches())
		{
			throw new IllegalStateException("Price info did not look as expected!: " + aCleanedInputLine);
		}
		
		int aLowerPrice = parseInt(matcher.group(1));
		int anUpperPrice = parseInt(matcher.group(2));
		
		int aRealizedPrice = isNumber(matcher.group(3)) ? parseInt(matcher.group(3)) : 0;
		
		return new LotPriceInfo(aLowerPrice, anUpperPrice, aRealizedPrice);
	}
	
	public final Unit processBottleSize(String theBottleSizeIndicator)
	{
		BigDecimal aSize = determineSize(theBottleSizeIndicator);
		return new Unit(aSize);
	}
	
}
