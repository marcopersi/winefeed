package ch.persi.java.vino.importers.weinboerse;

import ch.persi.java.vino.importers.LineExtrator;
import lombok.extern.slf4j.Slf4j;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.domain.VinoConstants.OHK;
import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

@Slf4j
public class WeinboerseLineExtractor implements LineExtrator {

    private final String offeringLine;
    private Matcher matcher = null;

    public WeinboerseLineExtractor(String theLine) {
        this.offeringLine = theLine;
    }

    private static Pattern getRecordLineMatcher() {
        // 'dynamically' building the pattern. Consider to apply a Builder pattern
        StringBuilder aWineSizePatternBuilder = new StringBuilder();
        aWineSizePatternBuilder.append("^([0-9]*)(\\s.*)(\\s([0-9]*)\\s");
        aWineSizePatternBuilder.append("((Flaschen?)");
        aWineSizePatternBuilder.append("|(Magnum)");
        aWineSizePatternBuilder.append("|Jéroboam|Jeroboam");
        aWineSizePatternBuilder.append("Imperial|Impèrial|Impèrial)))");
        aWineSizePatternBuilder.append(".*([0-9]{4})\\s([0-9]*).*");
        return java.util.regex.Pattern.compile(aWineSizePatternBuilder.toString());
    }

    @Override
    public boolean isRecordLine() {
        // FIXME: muss mich noch darum kümmern, dass das pattern offensichtlich ohne OHK erwartet........
        String aLine = offeringLine.replace(OHK, "");
        return getMatcher().matches();
    }

    @Override
    public Integer getVintage() {
        if (getMatcher().matches()) {
            // FIXME: replace hard coded 8 with const or enum or anything better
            String aNumberAsString = getMatcher().group(8).trim();
            if (isCreatable(aNumberAsString)) {
                return parseInt(aNumberAsString);
            }
            log.error("Got '{}' what obviously is no number, therefore there is no vintage !!", aNumberAsString);
        }
        log.error("No vintage found in row '{}'", offeringLine);
        return null;
    }

    @Override
    public boolean isOHK() {
        // TODO this was auto generated, not the business logic required
        return false;
    }

    @Override
    public Integer getNoOfBottles() {
        if (getMatcher().matches()) {
            // FIXME: replace hard coded 4 with const or enum or anything better
            String aPossibleNumber = getMatcher().group(4);
            if (isCreatable(aPossibleNumber.trim())) {
                return parseInt(aPossibleNumber);
            }
            log.error("Got '{}' what obviously is no number, therefore there is no 'number of sold bottles' !", aPossibleNumber);
        }
        log.error("No number of bottles found in row '{}'", offeringLine);
        return null;
    }

    @Override
    public Integer getMinPrice() {
        return null;
    }

    @Override
    public Integer getMaxPrice() {
        return null;
    }

    @Override
    public String getWine() {
        return null;
    }

    @Override
    public String getLotNumber() {
        if (getMatcher().matches()) {
            return getMatcher().group(1).trim();
        }
        return null;

    }

    @Override
    public Integer getRealizedPrice() {
        String aNumberValue = getMatcher().group(9).trim();
        log.debug("Found realized price: '{}'", aNumberValue);

        if (getMatcher().matches() && isCreatable(aNumberValue)) // coud be the char - too , if not sold at auction !
        {
            return parseInt(aNumberValue);
        }
        return 0;
    }

    private Matcher getMatcher() {
        if (matcher == null) {
            matcher = getRecordLineMatcher().matcher(offeringLine);
        }
        return matcher;
    }
}
