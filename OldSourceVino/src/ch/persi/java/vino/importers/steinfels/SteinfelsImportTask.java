package ch.persi.java.vino.importers.steinfels;

import static org.apache.commons.lang3.math.NumberUtils.isNumber;

import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.common.excel.ExcelUtil;
import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.ImportTask;
import ch.persi.java.vino.util.iTextUtil;

public class SteinfelsImportTask implements ImportTask {

	private static final String PROVIDER = "Steinfels";
	private IDao dao;
	private Provider aFoundProvider;
	private static final Pattern anAuctionDatePattern = Pattern.compile("^.*\\,\\s([0-9]*)\\.(.*)\\s([0-9]{4}).*");
	private DateTime auctionDate;
	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.steinfels.SteinfelsImportTask.class);
	private static final String IMPORTDIRECTORY = "import//Steinfels//";
//	private static final Pattern RECORD_LINE_PATTERN = java.util.regex.Pattern.compile("^([0-9]*)(\\s.*)(\\s([0-9]*)\\s(Flaschen?)|(Magnum)).*([0-9]{4})\\s([0-9]*).*");
	private static final Pattern RECORD_LINE_PATTERN;

	
	static 
	{
		StringBuilder aWineSizePatternBuilder = new StringBuilder();
		aWineSizePatternBuilder.append("^([0-9]*)(\\s.*)(\\s([0-9]*)\\s");
		aWineSizePatternBuilder.append("((Flaschen?)");
		aWineSizePatternBuilder.append("|(Magnum)");
		aWineSizePatternBuilder.append("|Jéroboam|Jeroboam");
		aWineSizePatternBuilder.append("Imperial|Impérial))");
		aWineSizePatternBuilder.append(".*([0-9]{4})\\s([0-9]*).*");
		RECORD_LINE_PATTERN=java.util.regex.Pattern.compile(aWineSizePatternBuilder.toString());
		
	}
	
	// FIXME: copy & paste from WermuthImportTask....refactor
	private static final Map<String, Integer> MONTHS = new HashMap<String, Integer>() {
		/**
		 * 
		 */
		private static final long serialVersionUID = -1653781997868876737L;

		{
			put("Januar", 1);
			put("Februar", 2);
			put("März", 3);
			put("April", 4);
			put("Mai", 5);
			put("Juni", 6);
			put("Juli", 7);
			put("August", 8);
			put("September", 9);
			put("Oktober", 10);
			put("November", 11);
			put("Dezember", 12);
		}
	};
	
	@Override
	public void execute() {

		// this task is state full in the meaning of that the provider (here steinfels) and the rating agency are kept as state full fields
		setupProvider();

		// checking for to be imported files at fileSystem, apply some validation
		File theImportDirectory = new File(IMPORTDIRECTORY);
		if (theImportDirectory.list() == null || theImportDirectory.list().length<1)
		{
			log.error("The import directory {0} does not exist or does not contain anything at all !");
			return;
		}
		
		for (String aFileName : theImportDirectory.list()) {
			try {
				log.info("Start import of file: " + aFileName);
				importFile(aFileName);
			} catch (Exception e) {
				e.printStackTrace(System.out);
				log.error("Executing Steinfels Import Task has a serious problem with the import of the file '" + aFileName + "' !",e);
				// no return , other file imports could be successful
			}
		}
	}

	private void importFile(String theFileName) throws Exception {
		List<String> someLines = iTextUtil.getLines(IMPORTDIRECTORY + theFileName);
		auctionDate = getAuctionDate(someLines);
		saveWineOfferings(someLines);		
	}

	private void saveWineOfferings(List<String> theLines) throws IOException {
		boolean isOHK = false;
		
		// TODO: try catch, close excel handle in every case
		// TODO: move that behind the DAO as a provider of the DAO Implementation
		ExcelUtil anExcelSheet = new ExcelUtil();
		
		Workbook openFile = anExcelSheet.openFile(PROVIDER+"_"+auctionDate.toString("dd.MM.yyyy"));   
		Sheet workSheet = anExcelSheet.getWorkSheet(openFile);
		
		for (String aRecordLine : theLines) {
			String aTrimmedRecordLine = aRecordLine.trim();
			if (aTrimmedRecordLine.contains("OHK"))
			{
				isOHK = true;
			}
			
			// 1st step: remove OHK if available
			String aCleanedRecordLine = aTrimmedRecordLine.replace("OHK", "");
			
			if (isRecordLine(aCleanedRecordLine))
			{
				Wine aWine = new Wine();
				Offering anOffering = new Offering();
				WineOffering aWineOffering = new WineOffering(aWine, getUnit(aCleanedRecordLine));
				
				anOffering.setProvider(aFoundProvider);
				anOffering.setOfferingDate(auctionDate.toDate());
				
				Matcher matcher = RECORD_LINE_PATTERN.matcher(aCleanedRecordLine);
				// no validation of matcher needed, since isRecordLine already checked if matcher is valid at this point or not
				anOffering.setProviderOfferingId(getLotNumber(aCleanedRecordLine));
				String[] someLineParts =null;
				
				// matcher seems to be somehow state full, without calling matches the group access to item 2 fails , funny enough
				matcher.matches();
				String aCompositeContentPart = matcher.group(2).trim();
				someLineParts = aCompositeContentPart.split(" ");
				
				String aPossibleRegion = someLineParts[someLineParts.length-1].trim();
				aCompositeContentPart = aCompositeContentPart.replace(aPossibleRegion, ""); // reducing the original string with the current part, intention is that rest may be used as wine name
				
				if (aPossibleRegion.matches("[0-9]{1}.*")){
					anOffering.setNote(aPossibleRegion); //obviously it was NOT the region, ..ok, next try, overwriting aPossibleRegion
					
					// then we have to assume that's the next element before this, if not we rely on the manual check of the excel stating file
					aPossibleRegion = someLineParts[someLineParts.length-2].trim();  
				}
				
				aWine.setRegion(aPossibleRegion);
				// the 2nd time replacing, only because of the possibility that aPossibleRegion has been overwritten within the first if clause
				// even if not, this doesn't harm the code at all..
				// FIXME: second replace of again the same string does not work ,Chateau Margaux Margaux......
				aCompositeContentPart = aCompositeContentPart.replace(aPossibleRegion, "");
				aWine.setName(aCompositeContentPart);

				// regular continuation with next fields...
				Integer vintage = getVintage(aCleanedRecordLine);
				aWine.setVintage((vintage != null ? vintage:0));
				
				// TODO: after having name & vintage of the wine, could try to find it in the database, DAO has findWineByNameAndYear
				// but this is part of the import task of the staging file !
				
				String aRealizedPrice = matcher.group(9).trim();
				log.debug("Found realized price: '" + aRealizedPrice + " '");
				if (isNumber(aRealizedPrice))
				{
					long parseLong = Long.parseLong(aRealizedPrice);
					anOffering.setRealizedPrice(BigDecimal.valueOf(parseLong));
				}
				
				anOffering.setIsOHK(isOHK);
				anOffering.setNoOfBottles(getNoOfBottles(aCleanedRecordLine));
				aWineOffering.setOffering(anOffering);
				workSheet.addRow(aWineOffering);
			}		
			else
			{
				workSheet.addSkippedRow(aRecordLine);
			}
			// reseting OHK
			isOHK=false;
		}
		openFile.close();
	}
	
	public static DateTime extractDate(String theLine)
	{
		String aTrimmedLine = theLine.trim();
		Matcher matcher = anAuctionDatePattern.matcher(aTrimmedLine);
		if (matcher.matches() && matcher.groupCount() == 3)
		{
			log.info("Found auction date: "+ (matcher.group(1) + " " + matcher.group(2) + " " + matcher.group(3)));
			Integer day = Integer.valueOf(matcher.group(1).trim());
			Integer month = MONTHS.get(matcher.group(2).trim());
			Integer year = Integer.valueOf(matcher.group(3).trim());
			DateTime dateTime = new DateTime(year, month, day, 0, 0, 0, 0);
			log.debug("Joda Time representation of date is: " + dateTime);
			return dateTime;
		}
		return null;
	}
	
	private void setupProvider() {
		aFoundProvider = dao.findProviderByName(PROVIDER);
		if (aFoundProvider == null) {
			aFoundProvider = dao.save(new Provider(PROVIDER));
		}
	}

	public void setDao(IDao theDao) {
		dao = theDao;
	}

	@Override
	public boolean isRecordLine(String theLine) {
		String aLine = theLine.replace("OHK", "");
		Matcher matcher = RECORD_LINE_PATTERN.matcher(aLine.trim());
		return matcher.matches();
	}

	@Override
	public String getOrigin(String theLine) {
		// unfortunately so far, steinfels doesn't provide any origin info in its record line
		return null;
	}

	@Override
	public BigDecimal determineSize(String theLine) {
		// FIXME: this is 1:1 copy & paste from wermuth , refactor
		if (theLine.contains("3/8")) {
			return new BigDecimal("3.75", new MathContext(0,
					RoundingMode.HALF_UP));
		} else if (theLine.contains("Magnum")) {
			return new BigDecimal("15",
					new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Doppel")) {
			return new BigDecimal("30",
					new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Jeroboam") || theLine.contains("Jéroboam")) {
			return new BigDecimal("45",
					new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Imperial") || theLine.contains("Impérial")) {
			return new BigDecimal("60",
					new MathContext(0, RoundingMode.HALF_UP));
		}
		return new BigDecimal("7.5", new MathContext(0, RoundingMode.HALF_UP));
	}

	private final Unit getUnit(String theLine)
	{
		BigDecimal aWineContentInDeciliters = determineSize(theLine);
		log.debug("Extracted wine unit: {0}", aWineContentInDeciliters);
		Unit wineUnit = dao.findUnitByDeciliters(aWineContentInDeciliters);
		if (wineUnit == null) {
			wineUnit = dao.save(new Unit(aWineContentInDeciliters));
		}
		return wineUnit;
	}
	
	@Override
	public DateTime getAuctionDate(List<String> theLines) {
		// FIXME: this is actually the same code as with Wermuth, only micro code is different
		// pattern and groups. Define strategy which is injectable, then generic implementation
		for (String string : theLines) {
			DateTime extractDate = extractDate(string);
			if (extractDate != null)
			{
				return extractDate;
			}
		}
		log.error("Didn't find a date, this is a PROBLEM !!");
		return null;
	}

	@Override
	public BigDecimal getParkerRating(String theLine) {
		// unfortunately, Steinfels doesn't provide rating info in the record lines, at least not in the old style docs
		return null;
	}

	@Override
	public String getLotNumber(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine);
		if (matcher.matches())
		{
			// FIXME: replace hard coded 1 with const or enum or anything better
			return matcher.group(1).trim();
		}
		return null;
	}

	@Override
	public Integer getNoOfBottles(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine);
		if (matcher.matches())
		{
			
			String aPossibleNumber = matcher.group(4);
			if (isNumber(aPossibleNumber.trim()))
			{
				return Integer.parseInt(aPossibleNumber);
			}
			log.error("Got '" + aPossibleNumber + "' what obviously is no number, therefore there is no 'number of sold bottles' !!");
		}
		log.error("No number of bottles found in row '" + theLine + "'");
		return null;
	}

	@Override
	public Integer getVintage(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine);
		if (matcher.matches())
		{
			String aNumberAsString = matcher.group(8).trim();
			if (isNumber(aNumberAsString)) {
				return Integer.parseInt(aNumberAsString);
			}
			log.error("Got '" + aNumberAsString + "' what obviously is no number, therefore there is no vintage !!");
		}
		log.error("No vintage found in row '" + theLine + "'");
		return null;
	}
}
