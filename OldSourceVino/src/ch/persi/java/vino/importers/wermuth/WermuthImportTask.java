package ch.persi.java.vino.importers.wermuth;

import static org.apache.commons.lang3.StringUtils.isNotBlank;

import java.io.File;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang3.math.NumberUtils;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Origin;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Rating;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.ImportTask;
import ch.persi.java.vino.util.iTextUtil;

public class WermuthImportTask implements ImportTask {

	private static final String RATING_AGENCY_PARKER = "Parker";
	private static final String IMPORTDIRECTORY = "import/wermuth/";
	private static final String PROVIDER = "Wermuth SA.";
	private static final Pattern RECORD_LINE_PATTERN = java.util.regex.Pattern.compile("(^[0-9]*)\\s([0-9]*)(.*[fF]lasche.*),?(\\s[0-9]{4}).*Sfr\\.\\s(.*)");
	private static final Pattern RATING_AGENCY_PATTERN = java.util.regex.Pattern.compile(".*" + RATING_AGENCY_PARKER + "\\s([0-9]*).*");

	// seems that those Wermuth auctions are always at Thursdays / donnerstag
	private static final Pattern AUCTION_DATE_PATTERN = Pattern.compile("[A-Za-z]*,\\s([0-9]*)\\.\\s([A-Za-z]*)\\s([0-9]{4}).*");

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

	private DateTime auctionDate;
	private static final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.wermuth.WermuthImportTask.class);
	private IDao dao;
	private RatingAgency ratingAgency;
	private Provider aFoundProvider;

	public void setDao(IDao theDao) {
		dao = theDao;
	}

	@Override
	public void execute() {

		// this task is state full in the meaning of that the provider (here
		// wermuth) and the rating agency are kept as state full fields
		setupProvider();

		setupRatingAgency();

		// checking for to be imported files at fileSystem.
		File theImportDirectory = new File(IMPORTDIRECTORY);
		String[] children = theImportDirectory.list();

		if (children == null || children.length < 1) {
			log.warn("didn't find any files in the directory !");
		} else {
			for (int i = 0; i < children.length; i++) {
				// Get filename of file or directory String
				String fileName = children[i];
				log.info("Start import of file: " + fileName);

				try {
					// run run run
					importFile(fileName);
				} catch (Exception e) {
					log.error(
							"Executing Wermuth Import Task has a serious problem !",
							e);
				}
			}
		}
	}

	private void setupProvider() {
		aFoundProvider = dao.findProviderByName(PROVIDER);
		if (aFoundProvider == null) {
			aFoundProvider = dao.save(new Provider(PROVIDER));
		}
	}

	private void setupRatingAgency() {
		ratingAgency = dao.findRatingAgencyByName(RATING_AGENCY_PARKER);
		if (ratingAgency == null) {
			ratingAgency = dao.save(new RatingAgency(new BigDecimal(100),RATING_AGENCY_PARKER));
		}
	}

	private final void importFile(String theFileName) throws Exception {
		List<String> lines = iTextUtil.getLines(IMPORTDIRECTORY + theFileName);

		auctionDate = getAuctionDate(lines);

		saveWineOfferings(lines);

		// FIXME 1 use spring
		// FIXME 2 decouple task from using dao
		new WermuthUpdatePriceTask(theFileName, auctionDate).execute();
	}

	@Override
	public DateTime getAuctionDate(List<String> lines) {
		for (String string : lines) {
			String trim = string.trim();
			Matcher matcher = AUCTION_DATE_PATTERN.matcher(trim);
			if (matcher.matches() && matcher.groupCount() == 3) {
				log.info("Found auction date: "+ (matcher.group(1) + " " + matcher.group(2) + " " + matcher.group(3)));
				// extracting each element of a date isolated because of Joda Time does NOT provide a constructor based on a complete date string
				Integer day = Integer.valueOf(matcher.group(1));
				Integer month = MONTHS.get(matcher.group(2));
				Integer year = Integer.valueOf(matcher.group(3));
				DateTime dateTime = new DateTime(year, month, day, 0, 0, 0, 0);
				log.debug("Joda Time representation of date is: " + dateTime);
				return dateTime;
			}
		}
		log.error("Didn't find an auction date, this is a PROBLEM !!");
		return null;
	}

	private void handleOfferings(Wine aWine, List<String> offeringLines,
			StringBuilder theNote) {

		for (String aLine : offeringLines) {
			Offering anOffering = new Offering();

			String aNote = theNote.toString().trim();
			if (isNotBlank(aNote)) {
				anOffering.setNote(aNote);
			}
			anOffering.setProvider(aFoundProvider);
			anOffering.setOfferingDate(auctionDate.toDate());

			String aLotNumber = getLotNumber(aLine);
			anOffering.setProviderOfferingId(aLotNumber);
			int numberOfBottles = getNoOfBottles(aLine);
			log.debug("Extracted amount of bottles: {0} !", numberOfBottles);
			anOffering.setNoOfBottles(numberOfBottles);
			
			BigDecimal priceMinimum = getPriceMinimum(aLine);
			BigDecimal priceMaximum = getPriceMaximum(aLine);
			log.debug("Extracted min&max price of {0} and {1} !", priceMinimum,priceMaximum);

			// 1st: creating offering
			anOffering.setPriceMin(priceMinimum);
			anOffering.setPriceMax(priceMaximum);
			Offering savedOffering = dao.save(anOffering);
			// aWineOffering.setOffering(savedOffering);
			// aWineOffering.setWine(savedWine);

			Unit wineUnit = getUnit(aLine);

			int vintage = getVintage(aLine);
			log.debug("Extracted vintage: {0}", vintage);

			// 2nd, for each wine of this offering, try to find persisted wine,
			// if
			// available use it
			// else save the wine, then save the offering
			Wine savedWine = dao.findWineByNameAndYear(aWine.getName(),vintage);

			// FIXME 3: could validate the savedWine, if complete
			// (year,rating,...)
			if (savedWine == null) {
				aWine.setVintage(Integer.valueOf(vintage));
				savedWine = dao.save(aWine);
			}
			dao.save(new WineOffering(savedWine, wineUnit, savedOffering));
		}
		offeringLines.clear();
		theNote.delete(0, theNote.length());
	}

	private final void saveWineOfferings(List<String> theLines) {
		List<String> chunk = new ArrayList<String>();
		for (int i = 0; i < theLines.size(); i++) {

			String aLine = theLines.get(i);

			// detect line to start
			String origin = getOrigin(aLine);
			if (origin != null) {
				chunk.add(theLines.get(i - 1)); // the line before the origin
												// line is the line including
												// the wine name
				chunk.add(aLine); // the current line contains the origin info
				int aNextLineIndex = i + 1;
				String aNextLine = theLines.get(aNextLineIndex);
				boolean containsAtLeastOneRecordLine = false;
				while ((getOrigin(aNextLine) == null && !containsAtLeastOneRecordLine)
						|| isRecordLine(aNextLine)) {
					containsAtLeastOneRecordLine = isRecordLine(aNextLine);
					chunk.add(aNextLine);
					aNextLine = theLines.get(++aNextLineIndex);
				}

				if (containsAtLeastOneRecordLine) {
					// handle chunk
					handleOffering(chunk);
				}
				chunk.clear();
			}
		}
	}

	private void handleOffering(List<String> theLines) {
		List<String> someOfferingLines = new ArrayList<String>(
				theLines.size() - 2);
		StringBuilder aNoteBuilder = new StringBuilder();

		// creating wine
		Wine aWine = new Wine();
		aWine.setName(theLines.get(0).trim());

		// by contract, the second line is the origin line, which contains at
		// least origin, but probably some more info (like producer) too
		String anOriginLine = theLines.get(1);
		String origin = getOrigin(anOriginLine);
		aWine.setOrigin(origin);
		aWine.setProducer(getProducer(origin, anOriginLine));

		// go through each line of chunk, whereas it is guaranteed that first two are wine name & origin
		for (int i = 2; i < theLines.size(); i++) {
			String aCurrentLine = theLines.get(i);
			if (isRecordLine(aCurrentLine)) {
				someOfferingLines.add(aCurrentLine);
			} else {
				// line could contain parker points note info
				Rating aRating = getRating(aCurrentLine);
				if (aRating != null) {
					aRating.setWine(aWine);
					aWine.addRating(aRating);
				} else {
					aNoteBuilder.append(aCurrentLine);
				}
			}
		}
		handleOfferings(aWine, someOfferingLines, aNoteBuilder);
	}

	public String getProducer(String theOrigin, String anOriginLine) {
		if (anOriginLine.trim().contains(" ")) {
			// get the latest part out of the origin line, use this as part of the name or provider of the wine
			Pattern extendedWineInfoPattern = Pattern.compile(theOrigin+ "\\,\\s([A-Za-z].*)\\,\\s(.*)");
			Matcher matcher = extendedWineInfoPattern.matcher(anOriginLine.trim());
			if (matcher.matches()) {
				return matcher.group(2); // found a producer
			}
		}
		return null;
	}

	@Override
	public Integer getVintage(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine.trim());
		if (matcher.matches()) {
			String aVintage = matcher.group(4).trim();
			if (NumberUtils.isNumber(aVintage)) {
				return Integer.parseInt(aVintage);
			}
		}
		return null;
	}

	private final Unit getUnit(String theLine) {
		BigDecimal aWineContentInDeciliters = determineSize(theLine);
		log.debug("Extracted wine unit: {0}", aWineContentInDeciliters);
		Unit wineUnit = dao.findUnitByDeciliters(aWineContentInDeciliters);
		if (wineUnit == null) {
			wineUnit = dao.save(new Unit(aWineContentInDeciliters));
		}
		return wineUnit;
	}
	
	@Override
	public BigDecimal determineSize(String theLine) {
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

	@Override
	public Integer getNoOfBottles(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine.trim());
		if (matcher.matches()) {
			if (NumberUtils.isNumber(matcher.group(2))) {
				String furtherAmountDescription = matcher.group(3);
				if (furtherAmountDescription.contains("Dutzend")) {
					int amount = Integer.valueOf(matcher.group(2));
					return amount * 12;
					
				}
				return Integer.parseInt(matcher.group(2));
			}
		}
		return null;
	}

	private final Rating getRating(String theLine) {
		BigDecimal parkerRating = getParkerRating(theLine);
		if (parkerRating != null) {
			Rating aFoundRating = dao.findRatingByAgencyAndPoints(ratingAgency,
					parkerRating);
			if (aFoundRating == null) {
				return dao.save(new Rating(ratingAgency, parkerRating));
			}
			return aFoundRating;
		}
		return null;
	}

	private final BigDecimal getPriceMinimum(String theWermuthLine) {
		return extract(1, theWermuthLine);
	}

	private final BigDecimal getPriceMaximum(String theWermuthLine) {
		return extract(2, theWermuthLine);
	}

	private static BigDecimal extract(int index, String theWermuthLine) {
		Pattern compile = Pattern.compile("(^[0-9]*).{1}([0-9]*).*");
		Matcher matcher = compile.matcher(getPriceRange(theWermuthLine));
		if (matcher.matches() && matcher.groupCount() == 2) {
			if (NumberUtils.isNumber(matcher.group(index))) {
				return new BigDecimal(matcher.group(index), new MathContext(0,
						RoundingMode.HALF_UP));
			}
		}
		return null;
	}

	@Override
	public final boolean isRecordLine(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine.trim());
		if (matcher.matches() && matcher.groupCount() >= 5) {
			return true;
		}
		return false;
	}

	@Override
	public final String getOrigin(String theLine) {
		// is it the origin line ?
		for (Origin anOrigin : Origin.values()) {
			Pattern aCompiledOriginPattern = Pattern.compile("^(" + anOrigin.getOriginIdentifier() + ")\\,.*");
			Matcher matcher = aCompiledOriginPattern.matcher(theLine);
			if (matcher.matches()) {
				return matcher.group(1);
			}
		}
		return null;
	}

	private static String getPriceRange(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine.trim());
		if (matcher.matches()) {
			String aPriceRange = matcher.group(5).trim();
			return aPriceRange;
		}
		return null;
	}

	@Override
	public String getLotNumber(String theLine) {
		Matcher matcher = RECORD_LINE_PATTERN.matcher(theLine.trim());
		if (matcher.matches()) {
			if (NumberUtils.isNumber(matcher.group(1))) {
				log.debug("Extracted lot no: {0}", matcher.group(1));
				return matcher.group(1);
			}
		}
		return null;
	}

	@Override
	public BigDecimal getParkerRating(String theLine) {
		// is the line the one with parker points ?
		Matcher aParkerMatcher = RATING_AGENCY_PATTERN.matcher(theLine);
		if (aParkerMatcher.matches()) {
			String aParkerRating = aParkerMatcher.group(1);
			log.debug("Extracted parker point figure: {0}", aParkerRating);

			if (NumberUtils.isNumber(aParkerRating)) {
				return new BigDecimal(aParkerRating, new MathContext(0,RoundingMode.HALF_UP));
			}
		}
		return null;
	}


}
