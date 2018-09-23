package ch.persi.java.vino.importers.wermuth.formatpre2015;

import static ch.persi.java.vino.domain.VinoConstants.EMPTY;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.domain.VinoConstants;
import ch.persi.java.vino.importers.LineExtrator;

public class WermuthRecordLineExtractor implements LineExtrator {

	private static final String DUTZEND = "Dutzend";
	private static final Pattern aPattern = java.util.regex.Pattern.compile("(^[0-9]{1,4})\\s(\\D*\\d{1,3})\\s(.*[fF]lasche.*),?(\\s[0-9]{4}).*(Sfr\\.?|CHF)\\s(.*)");
	
	private final String offeringLine;
	private Matcher matcher = null;
	private static final Logger log = LoggerFactory.getLogger(WermuthRecordLineExtractor.class);

	public  WermuthRecordLineExtractor(String theLine) {
		this.offeringLine = theLine.trim();
	}

	@Override
	public boolean isRecordLine() {
		return (getMatcher().matches() && getMatcher().groupCount() >= 5) ? Boolean.TRUE: Boolean.FALSE;
	}

	@Override
	public Integer getVintage() {
		if (getMatcher().matches()) {
			String aVintage = getMatcher().group(4).trim();
			if (isCreatable(aVintage)) {
				return Integer.parseInt(aVintage);
			}
		}
		return null;
	}

	@Override
	public boolean isOHK() {
		return offeringLine.contains(VinoConstants.OHK);
	}

	@Override
	public Integer getNoOfBottles() {
		if (getMatcher().matches()) {
			// could still be that the number of bottles contains a word or basically alpha numeric characters
			String aPossibleNumberOfBottlesString = getMatcher().group(2);
			// quick and simple check if there is another speciality...a non digit character within the number of bottles chunk
			if (aPossibleNumberOfBottlesString.matches(".*\\D.*"))
			{
				aPossibleNumberOfBottlesString = aPossibleNumberOfBottlesString.replaceAll("\\D", "");
			}
			
			if (isCreatable(aPossibleNumberOfBottlesString)) {
				String furtherAmountDescription = getMatcher().group(3);
				if (furtherAmountDescription.contains(DUTZEND)) {
					int anAmount = Integer.parseInt(aPossibleNumberOfBottlesString);
					return anAmount * 12;
					
				}
				return Integer.parseInt(aPossibleNumberOfBottlesString);
			}
		}
		return null;	
	}

	@Override
	public String getWine() {
		// FIXME: check this, not sure, added blind flying mode.
		if (getMatcher().matches()) {
			return getMatcher().group(1).trim();
		}
		return null;
	}

	@Override
	public String getLotNumber() {
		if (getMatcher().matches()) {
			String aPossibleLotNumber = getMatcher().group(1);
			if (isCreatable(aPossibleLotNumber)) {
				log.debug("Extracted lot no: {}", matcher.group(1));
				return aPossibleLotNumber;
			}
		}
		return null;
	}

	@Override
	public Integer getRealizedPrice() {
		// FIXME this is conceptually wrong, not all line extractors may deliver this price !!!
		// due to the nature of having two files ,....
		return null;
	}
	
	private final Matcher getMatcher()
	{
		if (matcher == null)
		{
			matcher = aPattern.matcher(offeringLine);
		}
		return matcher;
	}
	
	@Override
	public Integer getMinPrice() {
		return extract(0);
	}

	@Override
	public Integer getMaxPrice() {
		return extract(1);
	}
	
	private Integer extract(final int theIndex) {
		Matcher aMatcher = getMatcher();

		if (!aMatcher.matches() || aMatcher.groupCount() != 6)
		{
			log.error("Line does not match as expected, cannot! extract min/max price !!");
			return 0;
		}

		String aMinMaxString = aMatcher.group(6).replaceAll("[^0-9]", EMPTY).replaceAll("\\s{2,}", EMPTY);
		String[] someStringParts = aMinMaxString.split("\\s");
		if (someStringParts== null || someStringParts.length!=2)
		{
			log.error("The string operations in the price range(min/max) substring resulted in something unusable {}", aMinMaxString);
			return 0;
		}
		
		return Integer.parseInt(someStringParts[theIndex]);
	}
}
