package ch.persi.java.vino.importers.weinboerse;

import static ch.persi.java.vino.domain.VinoConstants.EMPTY;

import java.time.LocalDate;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.importers.DateExtractingStrategy;

//FIXME very similar with WermuthPre2015DateExtractingStrategy, fix this.
public class WeinboerseDateExtractingStrategy implements DateExtractingStrategy {

	private static final Logger log = LoggerFactory.getLogger(WeinboerseDateExtractingStrategy.class);
	private List<String> auctionLots;
	private static final Pattern AUCTION_DATE_PATTERN = Pattern.compile("^.*\\,\\s([0-9]*)\\.(.*)\\s([0-9]{4}).*");	
	
	public WeinboerseDateExtractingStrategy(List<String> theAuctionLots) {
		this.auctionLots = theAuctionLots;
	}
	
	@Override
	public LocalDate getAuctionDate() {
		for (String aLine : auctionLots) {
			LocalDate anAuctionDate = extractDate(aLine);
			if (anAuctionDate != null) {
				return anAuctionDate;
			}
		}
		return null;
	}

	private static LocalDate extractDate(final String theLine) {
		Matcher aDateMatcher = AUCTION_DATE_PATTERN.matcher(theLine.trim());
		if (aDateMatcher.matches() && aDateMatcher.groupCount() == 3) {
			if (log.isInfoEnabled()) {
				String anAuctionDate = aDateMatcher.group(1) + EMPTY + aDateMatcher.group(2) + EMPTY + aDateMatcher.group(3);
				log.info("Found auction date: {}", anAuctionDate);
			}
			LocalDate alocalDate = LocalDate.of(Integer.parseInt( aDateMatcher.group(3).trim()), MONTHS.get(aDateMatcher.group(2).trim()), Integer.parseInt(aDateMatcher.group(1).trim()));
			log.debug("Joda Time representation of date is: {}", alocalDate);
			return alocalDate;
		}
		return null;
	}	
}
