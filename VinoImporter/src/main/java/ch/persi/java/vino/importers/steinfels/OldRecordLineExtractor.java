package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.LineExtrator;
import lombok.extern.slf4j.Slf4j;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

@Slf4j
public class OldRecordLineExtractor implements LineExtrator {

    private final String offeringLine;
    private Matcher matcher = null;

    public OldRecordLineExtractor(String theLine) {
        this.offeringLine = theLine;
    }

    private static Pattern getRecordLineMatcher() {
        // 'dynamically' building the pattern. Consider to apply a Builder pattern
        String aWineSizePatternBuilder = "^([0-9]*)(\\s.*)(\\s([0-9]*)\\s" +
                "((Flaschen?)" +
                "|Magnum" +
                "|Jéroboam|Jeroboam" +
                "Imperial|Impèrial|Impérial))" +
                ".*([0-9]{1,5})\\s([0-9]*).*";
        return Pattern.compile(aWineSizePatternBuilder);
    }

    @Override
    public boolean isRecordLine() {
        return getRecordLineMatcher().matcher(offeringLine).matches();
    }

    @Override
    public Integer getVintage() {
        if (getMatcher().matches()) {
            String aNumberAsString = matcher.group(8).trim();
            if (isCreatable(aNumberAsString)) {
                return Integer.parseInt(aNumberAsString);
            }
            log.error("Got '{}' what obviously is no number, therefore there is no vintage !!", aNumberAsString);
        }
        log.error("No vintage found in row '{}'", offeringLine);
        return null;
    }

    @Override
    public boolean isOHK() {
        return offeringLine.contains("OHK");
    }

    @Override
    public Integer getNoOfBottles() {

        if (getMatcher().matches()) {
            String aPossibleNumber = matcher.group(4);
            if (isCreatable(aPossibleNumber.trim())) {
                return Integer.parseInt(aPossibleNumber);
            }
            log.error("Got '{}' what obviously is no number, therefore there is no 'number of sold bottles' !!", aPossibleNumber);
        }
        log.error("No number of bottles found in row '{}'", offeringLine);
        return null;
    }

    @Override
    public Integer getMinPrice() {
        return 0;
    }

    @Override
    public Integer getMaxPrice() {
        return 0;
    }

    @Override
    public String getWine() {
        if (getMatcher().matches()) {
            return matcher.group(2).trim();
        }
        return null;
    }

    @Override
    public String getLotNumber() {
        if (getMatcher().matches()) {
            return matcher.group(1).trim();
        }
        return null;
    }

    private Matcher getMatcher() {
        if (matcher == null) {
            matcher = getRecordLineMatcher().matcher(offeringLine);
        }
        return matcher;
    }

    @Override
    public Integer getRealizedPrice() {
        // FIXME: redundant
        String aPossibleRealizedPrice = getMatcher().group(8).trim();
        if (getMatcher().matches() && isCreatable(aPossibleRealizedPrice)) {
            return Integer.parseInt(aPossibleRealizedPrice);
        }
        return 0;
    }
}
