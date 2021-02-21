package ch.persi.java.vino.importers.wermuth.prices;

import ch.persi.java.vino.importers.PricePageParser;
import ch.persi.java.vino.util.InputParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.StringUtils.isBlank;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

public class WermuthPricePageParser implements PricePageParser {

	private static final String CHF = "CHF";

	private static final String DUTZEND = "Dz.";

	private static final String LOT = "Lot";

	private static final String SFR = "Sfr.";

	public static final Pattern AUCTION_DATE_PATTERN = java.util.regex.Pattern.compile(".*(WZ)-([0-9]{3}).*");

	public static final Pattern LOT_AND_PRICE_PATTERN = Pattern.compile("^([0-9]{1,4})\\s.*(\\s[0-9\\'\\.]*\\s).*$");

	// third version, there are result files with and without the Sfr.
	// one has to make sure, not getting crazy with these different patterns
	// they have....
	// public static Pattern LOT_AND_PRICE_PATTERN =
	// Pattern.compile("^([0-9]{1,4}).*([0-9'\\.]*$)");

	private static final Logger log = LoggerFactory.getLogger(WermuthPricePageParser.class);

	private static final String WORKING_DIRECTORY = System.getProperty("user.dir") + "//import//Wermuth//";

	private InputParser parser;

	private String realizedPriceUrl;

	/**
	 * This method creates the file name where the results (resulting prices for
	 * an auction) may be found. The name of the files has a pattern -
	 * obviously.
	 *
	 * Therefore the method gets the auction catalogue file as input. Based on
	 * that auction catalogue, the method creates the expected result file name
	 * in PDF format.
	 *
	 * @param theSourceFileName
	 * @return a composed new FileName according to the pattern of the Wermuth
	 *         result files
	 */
	private static String createPDFResultFileName(final String theSourceFileName) {
		Matcher matcher = AUCTION_DATE_PATTERN.matcher(theSourceFileName);
		if (matcher.matches()) {
			StringBuilder aResultFileNameBuilder = new StringBuilder();
			aResultFileNameBuilder.append(matcher.group(1));
			aResultFileNameBuilder.append("-");
			aResultFileNameBuilder.append(matcher.group(2));
			aResultFileNameBuilder.append("_Resultate.pdf");
			return aResultFileNameBuilder.toString();
		}
		return null;
	}

	@Override
	public Map<Integer, Integer> extractPrices(final String theFileName) {
		realizedPriceUrl = createUrl(theFileName);

		if (realizedPriceUrl != null && new File(realizedPriceUrl).exists()) {
			Map<Integer, Integer> somePrices = Collections.emptyMap();
			try {
				somePrices = new HTMLPricePageExtractor().extractPrices(realizedPriceUrl);
			} catch (Exception ex) {
				log.error("Extracting prices from HTML page failed !: " + ex.getMessage(), ex);
			}
			return somePrices;
		}
		return extractPDFPrices(theFileName);
	}

	private final Map<Integer, Integer> extractPDFPrices(final String theFileName) {
		String aResultFileName = createPDFResultFileName(theFileName);
		if (isBlank(aResultFileName)) {
			log.error("Did not find a result file name based on input {}", theFileName);
			return Collections.emptyMap();
		}
		Map<Integer, Integer> someResults = new HashMap<>();
		List<String> someLines = parser.parse("import/Wermuth/" + aResultFileName);

		if (someLines != null && !someLines.isEmpty()) {
			int lotNumber = 1;
			StringBuilder aLineBuilder = new StringBuilder();
			for (int i = 0; i < someLines.size(); i++) {
				String aLine = someLines.get(i);

				if (aLine.startsWith(Integer.toString(lotNumber))) {
					aLineBuilder.append(aLine);

					int aNextLineIndex = i + 1;
					if (aNextLineIndex < someLines.size()) {
						String aNextLine = someLines.get(aNextLineIndex);

						while (aNextLine != null && !aNextLine.startsWith(Integer.toString(lotNumber + 1))) {
							if (!aNextLine.contains("Seite") && !aNextLine.contains("Resultate")) {
								aLineBuilder.append(" ");
								aLineBuilder.append(aNextLine);
							}

							aNextLine = ++aNextLineIndex < someLines.size() ? someLines.get(aNextLineIndex) : null;
						}
					}
					Integer aRealizedPrice = getRealizedPrice(aLineBuilder.toString());
					someResults.put(lotNumber, aRealizedPrice);
					lotNumber++;
					aLineBuilder.delete(0, aLineBuilder.length()); // cleaning
				}
			}
			log.info("Found {} price records out of {} lines in the result file !", someResults.keySet().size(), someLines.size());
		}
		return someResults;
	}

	// public & static only for unit testing purposes
	public static Integer getRealizedPrice(final String theLine) {
		// what a pain but 'Sfr.', 'Lot', 'Dz.', and finally 'CHF' are available
		// tags to indicate price information afterwards.
		Integer aRealizedPrice = getPrice(theLine, SFR);

		if (aRealizedPrice == null) {
			aRealizedPrice = getPrice(theLine, LOT);
		}

		// tryin 'Lot' as indicator
		if (aRealizedPrice == null) {
			aRealizedPrice = getPrice(theLine, LOT);
		}

		// tryin 'Dz.' as indicator
		if (aRealizedPrice == null) {
			aRealizedPrice = getPrice(theLine, DUTZEND);
		}

		// finally tryin 'CHF' as indicator
		if (aRealizedPrice == null) {
			aRealizedPrice = getPrice(theLine, CHF);
		}

		return aRealizedPrice;
	}

	private static String createUrl(String theFileName) {
		// try to find the current auction tag
		Matcher matcher = AUCTION_DATE_PATTERN.matcher(theFileName);

		if (matcher.matches() && matcher.groupCount() == 2) {
			StringBuilder aFileNameBuilder = new StringBuilder();

			String anOperatingSystemName = System.getProperty("os.name");
			String aWorkingDirectory = null;
			if (anOperatingSystemName.contains("Windows")) {
				aWorkingDirectory = WORKING_DIRECTORY.substring(2);
			} else if (anOperatingSystemName.contains("Mac")) {
				aWorkingDirectory = WORKING_DIRECTORY;
			}
			aFileNameBuilder.append(aWorkingDirectory);
			aFileNameBuilder.append(matcher.group(1));
			aFileNameBuilder.append("-");
			aFileNameBuilder.append(matcher.group(2));
			aFileNameBuilder.append("_Resultate.html");
			return aFileNameBuilder.toString();
		}
		return null;
	}

	public InputParser getInputParser() {
		return parser;
	}

	public void setInputParser(final InputParser theParser) {
		this.parser = theParser;
	}

	private static Integer getPrice(final String theLine, final String thePriceTagIndicator) {
		String anImprovedLine = theLine.replaceAll("\\.00", "").replaceAll("\\'", "").replaceAll("\\t", "").replaceAll("\\r", "").trim();

		int anIndex = anImprovedLine.indexOf(thePriceTagIndicator);
		if (anIndex == -1) {
			log.error("parse start indicator '{0}', not found in line: {1}", thePriceTagIndicator, theLine);
			return null;
		}

		int aLength = anImprovedLine.length();

		String aSubString = anImprovedLine.substring(anIndex, aLength);
		anImprovedLine = aSubString.toLowerCase().replaceAll("chf", "").trim().replaceAll("sfr.", "").trim().replaceAll("[\\s\\u00A0]+$", "").trim();

		Integer aLowerLimit = 0;
		Integer anUpperLimit = 0;
		Integer aRealizedPrice = 0;

		String[] split = anImprovedLine.split(" ");

		if (split != null && split.length >= 2) {
			aLowerLimit = isCreatable(split[0]) ? parseInt(split[0]) : 0;
			anUpperLimit = isCreatable(split[1]) ? parseInt(split[1]) : 0;
			String aPossiblePrice = split[split.length - 1];
			aRealizedPrice = isCreatable(aPossiblePrice) ? parseInt(aPossiblePrice) : null;
		}

		if (log.isInfoEnabled()) {
			log.info("Found prices: lower Limit was: '{}', upper {} and most important, realized price {}", aLowerLimit.toString(),
					anUpperLimit.toString(), aRealizedPrice == null ? "" : aRealizedPrice.toString());
		}

		return aRealizedPrice;
	}
}