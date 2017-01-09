package ch.persi.java.vino.importers.wermuth.formatpre2015;

import static ch.persi.java.vino.domain.VinoConstants.EMPTY;

import java.time.LocalDate;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.importers.DateExtractingStrategy;

public class WermuthPre2015DateExtractingStrategy implements DateExtractingStrategy {

	private static final Logger log = LoggerFactory.getLogger(WermuthPre2015DateExtractingStrategy.class);
	private List<String> auctionLots;
	private static final Pattern AUCTION_DATE_PATTERN = Pattern.compile("[A-Za-z]*,\\s([0-9]*)\\.\\s([A-Za-z]*)\\s([0-9]{4}).*");
	
	public WermuthPre2015DateExtractingStrategy(List<String> theAuctionLots) {
		this.auctionLots = theAuctionLots;
	}
	
	@Override
	public LocalDate getAuctionDate() {
		for (String aLine : auctionLots) {
			LocalDate extractDate = extractDate(aLine);
			if (extractDate != null) {
				return extractDate;
			}
		}
		return null;
	}
	
	private static LocalDate extractDate(final String theLine) {
		String aTrimmedLine = theLine.trim();
		Matcher aMatcher = AUCTION_DATE_PATTERN.matcher(aTrimmedLine);
		if (aMatcher.matches() && aMatcher.groupCount() == 3) {
			log.debug("Found auction date: " + (aMatcher.group(1) + EMPTY + aMatcher.group(2) + EMPTY + aMatcher.group(3)));
			LocalDate anAuctionDate = LocalDate.of(Integer.parseInt( aMatcher.group(3)), MONTHS.get(aMatcher.group(2)), Integer.parseInt(aMatcher.group(1)));
			log.debug("Joda Time representation of date is: {}", anAuctionDate);
			return anAuctionDate;
		}
		return null;
	}	
}
