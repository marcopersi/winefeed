package ch.persi.java.vino.importers.wermuth.formatpre2015;

import ch.persi.java.vino.domain.*;
import ch.persi.java.vino.importers.AbstractImportTask;
import ch.persi.java.vino.importers.LineExtrator;
import ch.persi.java.vino.importers.PricePageParser;
import lombok.val;
import org.apache.commons.lang3.math.NumberUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.domain.VinoConstants.EMPTY;

public class WermuthPre2015ImportTask extends AbstractImportTask {

    private static final String RESULTFILE_TAG = "_Resultate";
    private static final Logger log = LoggerFactory.getLogger(WermuthPre2015ImportTask.class);
    private static final String RATING_AGENCY_PARKER = "Parker";

    // pimped version to deal with lines containing Total or any other word
    private static final Pattern RATING_AGENCY_PATTERN = java.util.regex.Pattern.compile(".*" + RATING_AGENCY_PARKER + "\\s([0-9]*).*");
    @SuppressWarnings("unused")
    private final RatingAgency ratingAgency = new RatingAgency(new BigDecimal(100), RATING_AGENCY_PARKER);
    private Map<Integer, Integer> someRealizedPrices;
    private String nextLotNumber = null;
    private PricePageParser pricePageParser;

    private String importDirectory = null;

    @Override
    public String getImportDirectory() {
        return importDirectory;
    }

    public void setImportDirectory(String theImportDirectory) {
        importDirectory = theImportDirectory;
    }

    @Override
    public void execute() {
        // checking for to be imported files at fileSystem.
        val anImportDirectory = checkFiles();
        if (anImportDirectory == null) return;

        for (String aFileName : anImportDirectory.list()) {
            if (!aFileName.contains(RESULTFILE_TAG) && !aFileName.startsWith(".")) {
                try {
                    log.info("Start import of file:{}", aFileName);

                    // extracting the realized prices, Wermuth is here unfortunately a bit special.
                    someRealizedPrices = pricePageParser.extractPrices(aFileName);

                    String anImportFile = getImportDirectory() + aFileName;
                    List<String> someLines = parser.parse(anImportFile);
                    log.info("Received '{}' lines out of the PDF file !", someLines.size());
                    setAuctionDate(new WermuthPre2015DateExtractingStrategy(someLines).getAuctionDate());

                    importFile(someLines, Provider.WERMUTH);
                } catch (Exception e) {
                    log.error("Executing Wermuth Import Task has a serious problem with file {}!, got exception {}", aFileName, e);
                }
            }
            log.info("Wermuth file {} successfully imported !", aFileName);
        }
    }

    @Override
    public final void saveWineOfferings(final List<String> theLines) throws IOException {
        List<String> aChunk = new ArrayList<>();
        log.info("Run through lines now, hopefully finding any origin (startline) at all !");
        for (int i = 0; i < theLines.size(); i++) {
            String aLine = theLines.get(i);
            String aOrigin = getOrigin(aLine);
            if (aOrigin != null) {
                /*
                 * according to the seen patterns in the Wermuth catalogue, the
                 * second line of a wine offering contains always the origin of
                 * the wine. So now, it's the problem of getting all the lines
                 * into one offering chunk
                 */
                aChunk.add(theLines.get(i - 1));
                aChunk.add(aLine);

                ++i;

                while (i < theLines.size() && getOrigin(theLines.get(i)) == null) {
                    aChunk.add(theLines.get(i));
                    ++i;
                }
                /*
                 * for the moment no better idea than this: since line
                 * containing the origin, is the 2nd line of a wine offering
                 * this means that above loop added one line too much, this
                 * needs to be removed now
                 */
                aChunk.remove(aChunk.size() - 1);

                /*
                 * one decrement because of the fact that the while incremented
                 * by one line too much, and one increment because of the fact
                 * that the for loop above does as first yet another increment.
                 * So to adjust the pointer to the start of the next block, here
                 * it's a reset of -2 required !
                 */
                i = i - 2;
                handleOffering(aChunk);
                aChunk.clear();
            }
        }
    }

    private void handleOfferings(final Wine theWine, final Map<String, LineExtrator> someOfferingLines, final StringBuilder theNote) throws IOException {

        for (Entry<String, LineExtrator> anEntry : someOfferingLines.entrySet()) {
            Offering anOffering = new Offering();
            String aLine = anEntry.getKey();
            LineExtrator aLineExtractor = anEntry.getValue();

            anOffering.setIsOHK(aLineExtractor.isOHK());
            anOffering.setProvider(Provider.WERMUTH.getProviderCode());
            anOffering.setOfferingDate(getAuctionDate());
            String aLotNumber = aLineExtractor.getLotNumber();
            anOffering.setProviderOfferingId(aLotNumber);

            Integer aRealizedPrice = someRealizedPrices.get(Integer.parseInt(anOffering.getProviderOfferingId()));
            if (aRealizedPrice == null) {
                log.error("No price for offering with Id:{}", anOffering.getProviderOfferingId());
            } else {
                log.info("Found the realized price:{}", aRealizedPrice.toString());
                anOffering.setRealizedPrice(aRealizedPrice);
            }

            int aNumberOfBottles = aLineExtractor.getNoOfBottles();
            log.debug("Extracted amount of bottles:{} !", aNumberOfBottles);
            anOffering.setNoOfBottles(aNumberOfBottles);

            Integer aPriceMinimum = aLineExtractor.getMinPrice();
            Integer aPriceMaximum = aLineExtractor.getMaxPrice();
            log.debug("Extracted min and max price of {} and {} !", aPriceMinimum, aPriceMaximum);

            // 1st: creating offering
            anOffering.setPriceMin(aPriceMinimum);
            anOffering.setPriceMax(aPriceMaximum);

            Unit aWineUnit = getUnit(aLine);

            int aVintage = aLineExtractor.getVintage();
            log.debug("Extracted vintage:{}", aVintage);
            theWine.setVintage(aVintage);

            WineOffering aWineOffering = new WineOffering(theWine, aWineUnit, anOffering);
            anOutputWriter.write(aWineOffering.toXLSString());
        }
        someOfferingLines.clear();
        theNote.delete(0, theNote.length());
    }

    public String getProducer(final String theOrigin, final String theOriginLine) {
        if (theOriginLine.trim().contains(EMPTY)) {
            // get the latest part out of the origin line, use this as part of
            // the name or provider of the wine
            Pattern aExtendedWineInfoPattern = Pattern.compile(theOrigin + "\\,\\s([A-Za-z].*)\\,\\s(.*)");
            Matcher aMatcher = aExtendedWineInfoPattern.matcher(theOriginLine.trim());
            if (aMatcher.matches()) {
                return aMatcher.group(2); // found a producer
            }
        }
        return null;
    }

    private void handleOffering(final List<String> theLines) throws IOException {

        Map<String, LineExtrator> someOfferingLines = new HashMap<>();
        StringBuilder aNoteBuilder = new StringBuilder();

        Wine aWine = new Wine();

        // replacing invalid characters (comma is later uses as delimiter in the
        // too string and is therefore not allowed here
        aWine.setName(theLines.get(0).replaceAll(",", ""));

        // by contract, the second line is the origin line, which contains at
        // least origin, but probably some more info (like producer) too
        String anOriginLine = theLines.get(1);
        String origin = getOrigin(anOriginLine);
        if (origin == null) {
            log.error("Contract broken: origin info in line expected but not contained!. Lines are ignored!!!");
            for (String aLine : theLines) {
                log.debug("Dropped line: {}", aLine);
            }
            return; // exit handling of offerings here since informal contract is broken
        }

        aWine.setOrigin(origin);
        aWine.setProducer(getProducer(origin, anOriginLine));

        // go through each line of chunk, whereas it is guaranteed that first
        // two are wine name & origin
        for (int i = 2; i < theLines.size(); i++) {
            String aCurrentLine = theLines.get(i);

            // hack for the PDF parser problem, with does not ensure a space
            // after the Lot Number
            // since this is pretty important for the whole pattern detection
            // this must be fixed here.
            if (nextLotNumber != null && aCurrentLine.startsWith(nextLotNumber)) {
                aCurrentLine = aCurrentLine.replaceAll("^" + nextLotNumber, nextLotNumber + EMPTY);
            }

            LineExtrator aLineExtractor = new WermuthRecordLineExtractor(aCurrentLine);

            if (aLineExtractor.isRecordLine()) {
                someOfferingLines.put(aCurrentLine, aLineExtractor);
                String aLastLotNumber = aLineExtractor.getLotNumber();

                Integer aLotNumber = Integer.valueOf(aLastLotNumber);
                aLotNumber++;
                nextLotNumber = aLotNumber.toString();
            } else {
                // line could contain parker points note info
                log.info("Line '{}' not recognized as record line !", aCurrentLine);
                aNoteBuilder.append(aCurrentLine);
            }
        }
        handleOfferings(aWine, someOfferingLines, aNoteBuilder);
    }

    private Unit getUnit(final String theLine) {
        return new Unit(determineSize(theLine));
    }

    public BigDecimal getParkerRating(final String theLine) {
        // is the line the one with parker points ?
        Matcher aParkerMatcher = RATING_AGENCY_PATTERN.matcher(theLine);
        if (aParkerMatcher.matches()) {
            String aParkerRating = aParkerMatcher.group(1);
            log.debug("Extracted parker point figure:{}", aParkerRating);

            if (NumberUtils.isCreatable(aParkerRating)) {
                return new BigDecimal(aParkerRating, new MathContext(0, RoundingMode.HALF_UP));
            }
        }
        return null;
    }

    public void setPriceParser(final PricePageParser thePricePageParser) {
        pricePageParser = thePricePageParser;
    }
}
