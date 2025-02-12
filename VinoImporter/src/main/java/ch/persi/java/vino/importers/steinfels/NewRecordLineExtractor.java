package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.LineExtrator;
import lombok.extern.slf4j.Slf4j;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.domain.VinoConstants.OHK;
import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

@Slf4j
public class NewRecordLineExtractor implements LineExtrator {

    //	private static final Pattern RECORD_LINE_PATTERN = Pattern.compile("^(.*\\s)([0-9]*)\\s(.*(Magnum|Jéroboam|Flasche).*)\\s([0-9]*)\\s(([0-9']*)\\s)?+$");
    private static final Pattern RECORD_LINE_PATTERN = Pattern.compile("^(.*\\s)([0-9]{1,3})\\s(.*)\\s([0-9]{4})\\s([0-9']{1,5})\\s?+$");

    private final String offeringLine;
    private Matcher matcher = null;

    public NewRecordLineExtractor(String theLine) {
        this.offeringLine = theLine;
    }

    @Override
    public boolean isRecordLine() {
        return getMatcher().matches();
    }

    @Override
    public Integer getVintage() {
        if (getMatcher().matches()) {
            String aNumberAsString = matcher.group(4).trim();
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
        return offeringLine.contains(OHK);
    }

    @Override
    public Integer getNoOfBottles() {
        if (getMatcher().matches()) {
            String aPossibleNumber = getMatcher().group(2);
            if (isCreatable(aPossibleNumber.trim())) {
                return parseInt(aPossibleNumber);
            }
            log.error("Got '{}' what obviously is no number, therefore there is no 'number of sold bottles' !!", aPossibleNumber);
        }
        log.error("No number of bottles found in row '{}'", offeringLine);
        return null;
    }

    @Override
    public Integer getMinPrice() {
        // for the newer files, Steinfels doesn't provide the lower & upper limits anymore
        return -1;
    }

    @Override
    public Integer getMaxPrice() {
        // for the newer files, Steinfels doesn't provide the lower & upper limits anymore
        return -1;
    }

    @Override
    public String getWine() {
        if (getMatcher().matches()) {
            return getMatcher().group(1).trim();
        }
        return null;
    }

    @Override
    public String getLotNumber() {
        if (getMatcher().matches()) {
            return getMatcher().group(6).trim();
        }
        return null;
    }


    private Matcher getMatcher() {
        if (matcher == null) {
            matcher = RECORD_LINE_PATTERN.matcher(offeringLine);
        }
        return matcher;
    }

    @Override
    public Integer getRealizedPrice() {
        // FIXME: redundant
        if (getMatcher().matches()) {
            String aNumberValue = getMatcher().group(5).replaceAll("'", "").trim();
            if (isCreatable(aNumberValue)) // coud be the char - too , if not sold at auction !
            {
                return parseInt(aNumberValue);
            }
        }
        return 0;
    }
}
