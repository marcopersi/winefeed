package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.DateExtractingStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDate;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

// FIXME very similar with WermuthPre2015DateExtractingStrategy, fix this.
public class SteinfelsDateExtractingStrategy implements DateExtractingStrategy {

    private static final Logger log = LoggerFactory.getLogger(SteinfelsDateExtractingStrategy.class);
    private final List<String> auctionLots;

    public SteinfelsDateExtractingStrategy(List<String> theAuctionLots) {
        this.auctionLots = theAuctionLots;
    }

    private static LocalDate extractDate(final String theLine) {
        String aTrimmedLine = theLine.trim();
        Matcher aDateMatcher = createAuctionDateMatcher().matcher(aTrimmedLine);
        if (aDateMatcher.matches()) {
            String aDay = aDateMatcher.group(1);
            String aMonth = aDateMatcher.group(2);
            String aYear = aDateMatcher.group(3);
            LocalDate aDate = LocalDate.of(Integer.parseInt(aYear), MONTHS.get(aMonth), Integer.parseInt(aDay));
            log.debug("Joda Time representation of date is: {}", aDate);
            return aDate;
        }
        return null;
    }

    private static Pattern createAuctionDateMatcher() {
        StringBuilder aWineRegionPatternBuilder = new StringBuilder();
        aWineRegionPatternBuilder.append("^.*\\,\\s");
        aWineRegionPatternBuilder.append("([0-9]{1,2})\\.\\s");
        aWineRegionPatternBuilder.append("(Januar|Februar|März|April");
        aWineRegionPatternBuilder.append("|Mai|Juni|Juli|August|September");
        aWineRegionPatternBuilder.append("|Oktober|November|Dezember");
        aWineRegionPatternBuilder.append(")\\s");
        aWineRegionPatternBuilder.append("([0-9]{4})\\s.*$");
        return Pattern.compile(aWineRegionPatternBuilder.toString());
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

}
